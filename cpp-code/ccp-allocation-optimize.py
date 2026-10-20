#!/usr/bin/env python3
"""ccp-allocation-optimize.py — five-asset CNY-unhedged allocation optimizer.

Purpose: the reproducible optimization program for the companion technical
note "Equity allocation across regional markets" (the five-asset revision
following the parent note "Chinese Couch Potato investing"), reading every
input from ccp-allocation-inputs.json (same directory; override with
--input). The operative brief items of the Oct 2026 revision mandate (items
2, 5, 10, 11) are summarized in the input file's _meta and in this file.

What it computes (user-updated planning inputs and one fee basis):
  a. return table - gross geometric anchors and approximate arithmetic
     returns, with net arithmetic used in optimization
     (brief item 11: fee/withholding robustness is not tested)
  b. equal-returns reference case - min-vol = max proxy-Sharpe = MV(gamma),
     self-tested; identical to the five-asset minimum-volatility portfolio
     because min-variance does not use expected returns
  c. best-estimate analysis - min-vol, max proxy-Sharpe (rf 2%), MV
     gamma {1,3,5} with 5pp-grid rounded policies and HK>=5% constrained
      variants, Greater-China (A/HK/US) companions, and the configured policy
     benchmark (brief item 10: the only policy benchmark, the parent note's
     current model split)
  d. utility improvement of adding Europe/Japan - best five-asset MV
     utility minus best Greater-China MV utility, in bp, per gamma
  e. range table - per-asset min/max across every reported optimum

Method: exact global optima on the long-only simplex by support enumeration
with a KKT system solved per support (off-support KKT inequalities reported
for zero-weight exclusions). The independent checker reconstructs and verifies
the reported optimizer results.

Usage:
    python3 ccp-allocation-optimize.py [--input PATH] [--json PATH]
Exits 0 iff every built-in gate passes (PSD, reference-case equivalence,
feasibility, utility round-trip, KKT off-support inequalities, grid
cardinality).
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import time
from pathlib import Path
from typing import Callable, Dict, List, Sequence, Tuple

import numpy as np
from scipy.optimize import minimize

T_START = time.time()
GAMMAS = (1, 3, 5)
RF = 0.02
GRID_STEP = 5  # percentage points; weights are multiples of GRID_STEP/100


# --------------------------------------------------------------------------
# Solvers (ported verbatim-in-semantics from the verified pass-1 template)
# --------------------------------------------------------------------------
def qp(mu: np.ndarray, Sig: np.ndarray, gamma: float = 3.0) -> Dict:
    """Global max of mu'w - (gamma/2) w'Sig w on {sum w = 1, w >= 0}.

    Exact support enumeration: for every nonempty subset S of assets, solve the
    KKT equality system restricted to S; keep it when the implied inner weights
    are long-only; the KKT inequality on off-support coordinates - max over
    i not in S of (mu_i - gamma (Sig w)_i - xi), required <= 0 - is reported as
    `kkt_max_viol` (0 for the true optimum; it is what rules out re-entry of
    zero-weighted assets). Near-ties (utilities within 1e-11) are resolved by
    smallest violation, then smallest support, for deterministic output.
    """
    n = len(mu)
    cands = []
    for r in range(1, n + 1):
        for sup in itertools.combinations(range(n), r):
            S = list(sup)
            A = Sig[np.ix_(S, S)]
            b = mu[S]
            try:
                Ainv = np.linalg.inv(A)
            except np.linalg.LinAlgError:
                continue
            o = np.ones(len(S))
            xi = (o @ Ainv @ b - gamma) / (o @ Ainv @ o)
            ws = Ainv @ (b - xi * o) / gamma
            if np.all(ws >= -1e-10):
                u = b @ ws - gamma / 2 * ws @ A @ ws
                w_full = np.zeros(n)
                w_full[S] = np.maximum(ws, 0.0)
                vw = Sig @ w_full
                viol = max((mu[i] - gamma * vw[i] - xi) for i in range(n) if i not in S) \
                    if r < n else 0.0
                cands.append((u, w_full, tuple(S), max(0.0, viol)))
    best_u = max(c[0] for c in cands)
    tie = [c for c in cands if c[0] >= best_u - 1e-11]
    tie.sort(key=lambda c: (-c[0], c[3], c[2]))
    u, w, S, viol = tie[0]
    return {"u": float(u), "w": w, "support": list(S),
            "kkt_max_viol": float(viol), "ties": len(tie)}


def minvol_exact(Sig: np.ndarray) -> Dict:
    """Global long-only minimum-variance portfolio (same support enumeration).

    KKT on the support: 2 Sigma w = xi 1 with xi = 2 / (1' Sig^-1 1);
    off-support requirement 2 (Sig w)_i >= xi, violations reported.
    """
    n = Sig.shape[0]
    cands = []
    for r in range(1, n + 1):
        for sup in itertools.combinations(range(n), r):
            S = list(sup)
            A = Sig[np.ix_(S, S)]
            Ainv = np.linalg.inv(A)
            o = np.ones(len(S))
            wS = Ainv @ o / (o @ Ainv @ o)
            if np.all(wS >= -1e-10):
                v = wS @ A @ wS
                w_full = np.zeros(n)
                w_full[S] = np.maximum(wS, 0.0)
                xi = 2.0 / (o @ Ainv @ o)
                vw = Sig @ w_full
                viol = max((xi - 2.0 * vw[i]) for i in range(n) if i not in S) \
                    if r < n else 0.0
                cands.append((v, w_full, max(0.0, viol)))
    best_v = min(c[0] for c in cands)
    tie = [c for c in cands if c[0] <= best_v + 1e-14]
    tie.sort(key=lambda c: (c[0], c[2]))
    v, w, viol = tie[0]
    return {"var": float(v), "w": w, "kkt_max_viol": float(viol)}


def sharpe_exact(mu: np.ndarray, Sig: np.ndarray, rf: float = RF) -> Dict:
    """Exact max of (mu'w - rf)/sqrt(w'Sig w) on the long-only simplex.

    Cone transformation (homogenized convex formulation): max Sharpe equals
    1/sqrt(min y'Sig y) over {d'y = 1, y >= 0} with d = mu - rf; support
    enumeration with off-support KKT checks nu d_i - 2 (Sig y)_i <= 0.
    """
    n = len(mu)
    d = mu - rf
    assert d.max() > 0, "max proxy-Sharpe needs some excess return > 0"
    cands = []
    for r in range(1, n + 1):
        for sup in itertools.combinations(range(n), r):
            T = list(sup)
            A = Sig[np.ix_(T, T)]
            Ainv = np.linalg.inv(A)
            Lam = d[T] @ Ainv @ d[T]
            if Lam <= 1e-16:
                continue
            yT = Ainv @ d[T] / Lam
            if np.any(yT < -1e-10):
                continue
            y = np.zeros(n)
            y[T] = np.maximum(yT, 0.0)
            nu = 2.0 / Lam
            g = Sig @ y
            viol = max((nu * d[i] - 2.0 * g[i]) for i in range(n) if i not in T) \
                if r < n else 0.0
            if viol > 1e-10:
                continue
            w = y / y.sum()
            s = (mu @ w - rf) / math.sqrt(w @ Sig @ w)
            cands.append((s, w, tuple(T), max(0.0, viol)))
    best_s = max(c[0] for c in cands)
    tie = [c for c in cands if c[0] >= best_s - 1e-12]
    tie.sort(key=lambda c: (-c[0], c[3], c[2]))
    s, w, T, viol = tie[0]
    return {"sharpe": float(s), "w": w, "kkt_max_viol": float(viol), "ties": len(tie)}


def sharpe_crosscheck(mu: np.ndarray, Sig: np.ndarray, rf: float = RF,
                      n_starts: int = 32, seed: int = 11) -> float:
    """SLSQP multistart cross-check; must never beat the exact enumeration."""
    rng = np.random.default_rng(seed)
    starts = [np.full(len(mu), 1 / len(mu))] + \
             [s / s.sum() for s in rng.dirichlet(np.ones(len(mu)), n_starts)]
    cons = ({"type": "eq", "fun": lambda w: w.sum() - 1},)
    bnds = [(0.0, 1.0)] * len(mu)
    best = -np.inf
    for s in starts:
        r = minimize(lambda w: -(mu @ w - rf) / math.sqrt(w @ Sig @ w), s,
                     bounds=bnds, constraints=cons, method="SLSQP")
        best = max(best, -r.fun)
    return float(best)


# --------------------------------------------------------------------------
# Grid utilities and formatting
# --------------------------------------------------------------------------
def grid_points(n_assets: int) -> np.ndarray:
    """All long-only weight vectors in GRID_STEP% increments summing to 100%.
    5 assets -> 10626 nodes; 3 assets -> 231 nodes. Order: (A, HK, US[, EU, JP])."""
    pts: List[Tuple[float, ...]] = []
    if n_assets == 3:
        for a in range(0, 21):
            for h in range(0, 21 - a):
                pts.append((a * .05, h * .05, 1 - (a + h) * .05))
    else:
        for a in range(0, 21):
            for b in range(0, 21 - a):
                for c in range(0, 21 - a - b):
                    for e in range(0, 21 - a - b - c):
                        pts.append((a * .05, b * .05, c * .05, e * .05, (20 - a - b - c - e) * .05))
    return np.array(pts)


def utils_pct(W: np.ndarray, mu: np.ndarray, Sig: np.ndarray, gamma: float) -> np.ndarray:
    """MV utilities of every grid row on the display % scale."""
    Wg = np.asarray(W, float)
    q = np.einsum("ij,jk,ik->i", Wg, np.asarray(Sig, float), Wg)
    return 100.0 * (Wg @ np.asarray(mu, float) - 0.5 * gamma * q)


def grid_best(W: np.ndarray, uvec: np.ndarray, fmt: Callable,
              near_tol: float = 1e-6) -> Dict:
    """Grid-argmax (round-2 A6 rounding rule) + near-ties within near_tol pp."""
    i = int(np.argmax(uvec))
    best = float(uvec[i])
    ties = [fmt(W[j]) for j in range(len(W)) if uvec[j] > best - near_tol]
    return {"index": i, "policy": fmt(W[i]), "u_pct": best, "near_ties": ties}


def pol(w: Sequence[float]) -> str:
    """"35/10/55/0/0" style rounding of a weight vector in %."""
    return "/".join(f"{x:.0f}" for x in 100 * np.asarray(w))


def w2(w: Sequence[float]) -> str:
    """"35.00/10.00/55.00" style 2dp string of a weight vector in %."""
    return "/".join(f"{x:.2f}" for x in 100 * np.asarray(w))


# --------------------------------------------------------------------------
# Input preparation
# --------------------------------------------------------------------------
def load_inputs(path: Path) -> Dict:
    with open(path) as f:
        return json.load(f)


def covariance(vols: Sequence[float], corr: Sequence[Sequence[float]],
               asset_idx: Sequence[int]) -> np.ndarray:
    """Sigma = diag(s) R diag(s) restricted to the asset_idx subset (keeps the
    submatrix of the full rounding to avoid rounding re-entrant-corner noise)."""
    idx = list(asset_idx)
    v = np.asarray(vols, float)[idx]
    R = np.asarray(corr, float)[np.ix_(idx, idx)]
    return np.outer(v, v) * R


# --------------------------------------------------------------------------
# Gates
# --------------------------------------------------------------------------
class Gates:
    """Collects PASS/FAIL verdicts; any FAIL forces a nonzero exit."""

    def __init__(self) -> None:
        self.items: List[Dict] = []

    def add(self, name: str, verdict: bool, detail: str = "") -> bool:
        self.items.append({"gate": name, "verdict": "PASS" if verdict else "FAIL",
                           "detail": detail})
        tag = "PASS" if verdict else "FAIL"
        print(f"[{tag}] {name}" + (f"  ({detail})" if detail else ""))
        return verdict

    @property
    def all_pass(self) -> bool:
        return all(g["verdict"] == "PASS" for g in self.items)


def to_json(o):
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


# --------------------------------------------------------------------------
# Analysis core
# --------------------------------------------------------------------------
ASSET_COLS = ("A", "HK", "US", "EU", "JP")


def analyze(inp: Dict) -> Dict:
    """Computes every reported table; returns the full result dict (which is
    what --json dumps). Gates run inside so JSON and console always agree."""
    G = Gates()
    order = [a["asset5"] for a in inp["assets"]]
    assets = {a["asset5"]: a for a in inp["assets"]}
    vols = [assets[k]["volatility"] for k in order]
    corr = inp["correlations"]["matrix"]
    SIG5 = covariance(vols, corr, range(5))
    SIGGC = covariance(vols, corr, [0, 1, 2])
    W5G = grid_points(5)
    W3G = grid_points(3)
    G.add("PSD/correlation structure", bool(
        np.all(np.linalg.eigvalsh(np.asarray(corr, float)) > 1e-12)
        and np.all(np.linalg.eigvalsh(SIG5) > 1e-12)
        and np.all(np.linalg.eigvalsh(SIGGC) > 1e-12)
        and np.allclose(np.diag(np.asarray(corr, float)), 1.0)),
        f"min eig corr {np.linalg.eigvalsh(np.asarray(corr, float)).min():.6f}")

    res: Dict = {"population": []}

    # ---------- (a) best-estimate CNY return table (single planning basis) ----------
    rows = []
    for k, a in zip(order, inp["assets"]):
        fee = a["fee"]
        drag = a["dividend_yield"] * a["withholding_rate"]
        gross_arithmetic = inp["gross_arithmetic_return"]
        gross_compound = gross_arithmetic - 0.5 * a["volatility"] ** 2
        net_compound = gross_compound - fee - drag
        net_arithmetic = gross_arithmetic - fee - drag
        rows.append({"asset5": k, "ticker": a["ticker"], "fund": a["fund"],
                      "fee": fee, "withholding": a["withholding_rate"],
                      "dividend_yield": a["dividend_yield"], "drag": drag,
                     "gross_compound_pct": 100 * gross_compound,
                     "gross_arithmetic_pct": 100 * gross_arithmetic,
                     "net_compound_pct": 100 * net_compound,
                     "net_dec": net_arithmetic,
                     "net_arithmetic_pct_4dp": round(100 * net_arithmetic, 4)})
    res["net_table"] = rows
    mu_best = np.array([r["net_dec"] for r in rows])

    # ---------- (b) equal-returns reference case ----------
    ref_rate = float(inp["gross_arithmetic_return"])
    ref_mu = np.full(len(order), ref_rate)
    mv_ref = minvol_exact(SIG5)
    sh_ref = sharpe_exact(ref_mu, SIG5)
    mv_ref_g = {g: qp(ref_mu, SIG5, float(g)) for g in GAMMAS}
    sigma_ref = 100 * math.sqrt(mv_ref["var"])
    G.add("reference equivalence: max-Sharpe = min-vol", bool(
        np.max(np.abs(sh_ref["w"] - mv_ref["w"])) < 1e-8
        and abs(sh_ref["sharpe"] - (ref_rate - RF) / (sigma_ref / 100)) < 1e-9),
        f"max|dw| = {np.max(np.abs(sh_ref['w'] - mv_ref['w'])):.2e}")
    G.add("reference equivalence: MV(argmax gamma) = min-vol", bool(
        all(np.max(np.abs(mv_ref_g[g]["w"] - mv_ref["w"])) < 1e-8 for g in GAMMAS)),
        "all three optimizers agree")
    res["reference_case"] = {
        "w": mv_ref["w"], "w_display": w2(mv_ref["w"]),
        "gross_arithmetic_return_pct": 100 * ref_rate,
        "sigma_pct": sigma_ref, "sharpe_display": f"{sh_ref['sharpe']:.3f}",
        "w_max_sharpe_display": w2(sh_ref["w"])}

    # ---------- (c) best-estimate analysis ----------
    def block(mu, Sig, Wg, heading):
        mv = minvol_exact(Sig)
        sh = sharpe_exact(mu, Sig)
        assert sharpe_crosscheck(mu, Sig) <= sh["sharpe"] + 1e-9, "SLSQP beat exact"
        mvg = {g: qp(mu, Sig, float(g)) for g in GAMMAS}
        n = Sig.shape[0]
        cols = ASSET_COLS[:n]
        out = {"minvol": {"w": mv["w"], "w_display": w2(mv["w"]),
                          "sigma_pct": 100 * math.sqrt(mv["var"]),
                          "kkt_max_viol": mv["kkt_max_viol"]},
               "max_sharpe": {"w": sh["w"], "w_display": w2(sh["w"]),
                              "Rp_pct": 100 * mu @ sh["w"],
                              "sigma_pct": 100 * math.sqrt(sh["w"] @ Sig @ sh["w"]),
                              "sharpe": sh["sharpe"],
                              "kkt_max_viol": sh["kkt_max_viol"]},
               "mv": {}}
        for g in GAMMAS:
            r = mvg[g]
            u = 100 * r["u"]
            gb = grid_best(Wg, utils_pct(Wg, mu, Sig, float(g)), pol)
            mask5 = Wg[:, 1] >= 0.049999 if n == 5 else None
            hk5 = grid_best(Wg[mask5], utils_pct(Wg[mask5], mu, Sig, float(g)), pol) \
                if mask5 is not None else None
            out["mv"][str(g)] = {
                "w": r["w"], "w_display": w2(r["w"]), "Rp_pct": 100 * mu @ r["w"],
                "sigma_pct": 100 * math.sqrt(r["w"] @ Sig @ r["w"]), "u_pct": u,
                "kkt_max_viol": r["kkt_max_viol"], "support": r["support"],
                "grid_best": gb["policy"], "grid_best_u_pct": gb["u_pct"],
                "grid_near_ties": gb["near_ties"][:6],
                "hkge5_grid_best": hk5["policy"] if hk5 else None,
                "hkge5_grid_u_pct": hk5["u_pct"] if hk5 else None}
        out["cols"] = cols
        out["heading"] = heading
        return out

    be = block(mu_best, SIG5, W5G, "best-estimate (five assets)")
    res["best_estimate"] = be
    gc = block(mu_best[:3], SIGGC, W3G, "Greater-China 3 assets (A/HK/US)")
    res["greater_china_3"] = gc

    benchmark = inp["policy_benchmark"]
    w = np.asarray(benchmark["weights_a_hk_us"], float)
    Sig3 = SIG5[:3, :3]
    res["policy_benchmarks"] = {benchmark["name"]: {
        "w_display": w2(np.pad(w, (0, 2))),
        "sigma_pct": 100 * math.sqrt(w @ Sig3 @ w),
        "Rp_pct": 100 * mu_best[:3] @ w,
        "u_pct": {str(g): 100 * (mu_best[:3] @ w - 0.5 * g * w @ Sig3 @ w)
                  for g in GAMMAS}}}

    # ---------- (d) utility improvement of adding Europe/Japan ----------
    imp = {"definition": "(best five-asset MV utility - best Greater-China 3-asset MV "
                         "utility) at the same gamma, under the best-estimate net "
                         "returns and the best-estimate covariance (Sigma5 vs its "
                         "A/HK/US submatrix); bp = percentage points x 1e4. Exact "
                         "support-enumeration optima. Never negative because the "
                         "five-market feasible set contains the restriction's."}
    for g in GAMMAS:
        u5 = qp(mu_best, SIG5, float(g))["u"]
        u3 = qp(mu_best[:3], SIGGC, float(g))["u"]
        imp[str(g)] = {"bp": round(1e4 * (u5 - u3), 2),
                       "bp_exact": round(1e4 * (u5 - u3), 4),
                       "u5_pct": round(100 * u5, 4), "u3_pct": round(100 * u3, 4)}
    res["improvement_bp"] = imp

    # ---------- (e) range table ----------
    pop: list = [
        ("reference (equal returns; = min-vol = max-Sharpe = MV)", mv_ref["w"]),
        ("best-estimate min-vol", be["minvol"]["w"]),
        ("best-estimate max-Sharpe", be["max_sharpe"]["w"])]
    for g in GAMMAS:
        row = be["mv"][str(g)]
        pop.append((f"best-estimate MV gamma={g}", row["w"]))
        pop.append((f"best-estimate MV gamma={g} grid best",
                    W5G[gb5_index(W5G, mu_best, SIG5, g)]))
    for g in GAMMAS:
        row = gc["mv"][str(g)]
        w5 = np.zeros(5)
        w5[:3] = row["w"]
        pop.append((f"Greater-China MV gamma={g}", w5))
    # feasibility + utility round-trip gates over every reported row
    sum_err = 0.0
    for lab, w in pop:
        sum_err = max(sum_err, abs(w.sum() - 1.0), max(0.0, -w.min()))
    G.add("feasibility: every reported row sums to 100, bounds [0,100]",
          sum_err < 1e-9, f"max err {sum_err:.2e}")
    u_err = 0.0
    for g in GAMMAS:
        be_row = be["mv"][str(g)]
        # w2() displays percentages to 2 decimal places, so reconstruct those
        # printed weights (rather than rounding to whole percentage points).
        wr = np.round(10000 * be_row["w"]) / 10000.0
        u_re = 100 * (mu_best @ wr - 0.5 * g * wr @ SIG5 @ wr)
        u_err = max(u_err, abs(u_re - be_row["u_pct"]))
    G.add("utility round-trip from printed 2dp weights (best-estimate MV)",
          u_err < 5e-3, f"max err {u_err:.2e} pp")
    res["population"] = [{"label": lab, "w": w} for lab, w in pop]
    ends = {}
    for j, col in enumerate(ASSET_COLS):
        ws = np.array([w[j] for _, w in pop]) * 100
        lo_i = int(np.argmin(ws))
        hi_i = int(np.argmax(ws))
        ends[col] = {"min_pct": round(float(ws.min()), 4),
                     "max_pct": round(float(ws.max()), 4),
                     "min_by": pop[lo_i][0], "max_by": pop[hi_i][0]}
    res["ranges"] = ends
    kkt_records = {"best_minvol": be["minvol"]["kkt_max_viol"],
                   "gc_minvol": gc["minvol"]["kkt_max_viol"],
                   "reference_minvol": mv_ref["kkt_max_viol"],
                   "max_sharpe_be": be["max_sharpe"]["kkt_max_viol"],
                   "max_sharpe_gc": gc["max_sharpe"]["kkt_max_viol"]}
    for g in GAMMAS:
        kkt_records[f"mv_be_g{g}"] = be["mv"][str(g)]["kkt_max_viol"]
        kkt_records[f"mv_gc_g{g}"] = gc["mv"][str(g)]["kkt_max_viol"]
    res["kkt_max_violations"] = kkt_records
    G.add("KKT off-support inequalities (zero-weight exclusions)", max(
        kkt_records.values()) <= 1e-9,
        f"max viol {max(kkt_records.values()):.2e}")
    G.add("grid cardinalities 5pp (10626 five-asset / 231 three-asset nodes)",
          len(W5G) == 10626 and len(W3G) == 231, f"{len(W5G)}/{len(W3G)}")
    res["gates"] = G.items
    res["runtime_sec"] = round(time.time() - T_START, 2)
    return res


def gb5_index(W5G: np.ndarray, mu: np.ndarray, Sig: np.ndarray, gamma: int) -> int:
    return int(np.argmax(utils_pct(W5G, mu, Sig, float(gamma))))


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------
def report(res: Dict, rows: List[Dict]) -> None:
    """Prints the human-readable report, sections (a)-(f), as markdown fragments."""
    ln = print
    ln("")
    ln("(a) USER-UPDATED CNY PLANNING RETURNS (one fee/tax basis) -")
    ln("    Net geometric = gross geometric minus fee and withholding drag.")
    ln("    Net arithmetic is the MVO input after fees and withholding drag.")
    ln("    Exact values and assumptions are in the input JSON.")
    ln("")
    ln("| Asset (fund) | Gross geometric approx. | Gross arithmetic input | Fee | WHT rate | Drag | Net geometric | Net arithmetic (MVO) |")
    ln("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for r in rows:
        ln(f"| {r['asset5']} ({r['ticker']}) | {r['gross_compound_pct']:.2f}% | "
            f"{r['gross_arithmetic_pct']:.3f}% | {r['fee']*100:.2f}% | "
            f"{r['withholding']*100:.0f}% | {r['drag']*100:.2f}% | "
           f"{r['net_compound_pct']:.2f}% | {r['net_dec']*100:.3f}% |")
    ln("")
    ln("    Exact 4dp net arithmetic: " + ", ".join(
        f"{r['asset5']} {r['net_arithmetic_pct_4dp']:.4f}" for r in rows))
    ln("")
    rc = res["reference_case"]
    ref_return = rc["gross_arithmetic_return_pct"]
    ln(f"(b) REFERENCE CASE (equal {ref_return:.1f}% arithmetic returns everywhere, no fees, no tax) -")
    ln("    the max proxy-Sharpe, the MV optimum for every gamma, and the minimum-vol")
    ln("    portfolio all coincide here; the weights are also the five-asset")
    ln("    minimum-volatility optimum verified directly (min-variance uses no returns).")
    ln("")
    ln(f"- Minimum-vol / reference optimum: **{rc['w_display']}** (A/HK/US/EU/JP %), "
       f"sigma_p = **{rc['sigma_pct']:.2f}%**")
    ln(f"- Max proxy-Sharpe (rf 2%): same weights (by construction), "
       f"Sharpe = **{rc['sharpe_display']}** = ({ref_return:.1f} - 2.0)/{rc['sigma_pct']:.2f}.")
    ln("")
    for tag, key in (("BEST-ESTIMATE (five assets)", "best_estimate"),
                     ("GREATER-CHINA 3 ASSETS (A/HK/US)", "greater_china_3")):
        blk = res[key]
        ln(f"(c) {tag}")
        M = blk["minvol"]
        gcol = "/".join(ASSET_COLS[:len(M["w"])])
        ln("")
        ln(f"- Minimum-vol: **{M['w_display']}** ({gcol}, %), sigma_p = "
           f"**{M['sigma_pct']:.2f}%**")
        Sx = blk["max_sharpe"]
        ln(f"- Max proxy-Sharpe (rf 2%): **{Sx['w_display']}**, Rp = {Sx['Rp_pct']:.2f}%, "
           f"sigma_p = {Sx['sigma_pct']:.2f}%, Sharpe = **{Sx['sharpe']:.3f}**")
        ln("")
        ln("| Objective | " + " | ".join(gcol.split("/")) + " | Rp % | sigma_p % | Utility % | Grid best |")
        ln("| --- | " + " | ".join("---" for _ in range(len(M["w"]))) + " | ---: | ---: | ---: | --- |")
        for g in GAMMAS:
            row = blk["mv"][str(g)]
            ws = [f"{x:.2f}" for x in 100 * row["w"]]
            ln(f"| MV gamma={g} | " + " | ".join(ws) + f" | {row['Rp_pct']:.2f} | "
               f"{row['sigma_pct']:.2f} | {row['u_pct']:.2f} | "
               f"{row['grid_best']} ({row['grid_best_u_pct']:.2f}%) |")
        ln("")
        for g in GAMMAS:
            hl = blk["mv"][str(g)]
            if hl["hkge5_grid_best"] is not None:
                ln(f"- HK >= 5% constrained grid variant (gamma={g}): "
                   f"{hl['hkge5_grid_best']} ({hl['hkge5_grid_u_pct']:.2f}%)")
        ln("")
    policy_name = next(iter(res["policy_benchmarks"]))
    ln(f"(d) POLICY BENCHMARK ({policy_name}) on the best-estimate")
    ln("    net returns")
    ln("")
    ln("| Policy | A/HK/US % | sigma_p % | Rp % | Utility gamma=1/3/5 % |")
    ln("| --- | --- | --- | --- | --- |")
    pb = res["policy_benchmarks"]
    for name, p in pb.items():
        ln(f"| {name} | {p['w_display']} | {p['sigma_pct']:.2f} | {p['Rp_pct']:.2f} | "
           f"{p['u_pct']['1']:.2f} / {p['u_pct']['3']:.2f} / {p['u_pct']['5']:.2f} |")
    ln("")
    imp = res["improvement_bp"]
    ln("(e) UTILITY IMPROVEMENT of adding Europe/Japan (best five-asset MV utility")
    ln("    minus best Greater-China MV utility, under best-estimate inputs)")
    ln("")
    ln("| gamma | Improvement (bp) | u5 % | u3 % |")
    ln("| ---: | ---: | ---: | ---: |")
    for g in GAMMAS:
        row = imp[str(g)]
        ln(f"| {g} | {row['bp']:.2f} | {row['u5_pct']:.2f} | {row['u3_pct']:.2f} |")
    ln("")
    ln("(f) RANGE TABLE over every reported optimum (continuous + 5pp grid policies)")
    ln("")
    ln("| Asset | Min % | Min set by | Max % | Max set by |")
    ln("| --- | ---: | --- | ---: | --- |")
    for col in ASSET_COLS:
        e = res["ranges"][col]
        ln(f"| {col} | {e['min_pct']:.2f} | {e['min_by']} | {e['max_pct']:.2f} | {e['max_by']} |")
    ln("")
    ln(f"Runtime: {res['runtime_sec']} s. Solver: exact support enumeration + KKT")
    ln("with off-support inequality certificates and SLSQP max-Sharpe cross-checks.")


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(
        description="Five-asset CNY-unhedged allocation optimizer (five named funds).")
    here = Path(__file__).resolve().parent
    ap.add_argument("--input", type=Path, default=here / "ccp-allocation-inputs.json",
                    help="optimizer input file (same directory by default)")
    ap.add_argument("--json", type=Path, default=None,
                    help="optional path for the machine-readable result file")
    args = ap.parse_args()

    inp = load_inputs(args.input)
    print("Loaded inputs from", args.input)
    res = analyze(inp)
    res["inputs_echo"] = inp
    res["meta"] = {"script": "ccp-allocation-optimize.py",
                   "input_file": str(args.input),
                   "rf": RF, "gammas": list(GAMMAS), "grid_step_pp": GRID_STEP,
                   "solver": "exact support enumeration with per-support KKT and "
                             "off-support inequality certificates; SLSQP max-Sharpe "
                             "cross-checks",
                   "gates_note": "gate list in 'gates'; PASS/FAIL verdicts; nonzero exit on FAIL"}
    print()
    print("GATE SUMMARY:", sum(g["verdict"] == "PASS" for g in res["gates"]), "PASS,",
          sum(g["verdict"] == "FAIL" for g in res["gates"]), "FAIL")
    print("=" * 100)
    report(res, res["net_table"])
    if args.json is not None:
        with open(args.json, "w") as f:
            json.dump(res, f, indent=2, ensure_ascii=False, default=to_json)
        n = Path(args.json)
        print(f"\nwrote {n} ({n.stat().st_size} bytes)")
    ok = all(g["verdict"] == "PASS" for g in res["gates"])
    print("=" * 100)
    print("ALL GATES PASS - optimizer outputs verified." if ok
          else "GATE FAILURES - see [FAIL] lines above.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
