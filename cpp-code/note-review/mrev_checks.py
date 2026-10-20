#!/usr/bin/env python3
"""Supplementary method diagnostics for the allocation optimizer."""
import itertools, json, math
from pathlib import Path
import numpy as np
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[1]
inp = json.loads((ROOT / "ccp-allocation-inputs.json").read_text())
order = [a["asset5"] for a in inp["assets"]]
assets = {a["asset5"]: a for a in inp["assets"]}
assert [a["asset5"] for a in inp["assets"]] == order
vols = np.array([assets[k]["volatility"] for k in order])
R0 = np.array(inp["correlations"]["matrix"], float)
SIG0 = np.outer(vols, vols) * R0
mu0 = np.array([inp["gross_arithmetic_return"] - a["fee"] - a["dividend_yield"] * a["withholding_rate"] for a in inp["assets"]])
REFMU = np.full(len(order), inp["gross_arithmetic_return"])


def qp_enum(mu, Sig, gamma):
    n = len(mu); best = None
    for r in range(1, n + 1):
        for S in itertools.combinations(range(n), r):
            A = Sig[np.ix_(S, S)]
            try:
                Ainv = np.linalg.inv(A)
            except np.linalg.LinAlgError:
                continue
            o = np.ones(len(S)); b = mu[list(S)]
            xi = (o @ Ainv @ b - gamma) / (o @ Ainv @ o)
            ws = Ainv @ (b - xi * o) / gamma
            if np.all(ws >= -1e-10):
                w = np.zeros(n); w[list(S)] = np.maximum(ws, 0.0)
                u = mu @ w - gamma / 2 * w @ Sig @ w
                vw = Sig @ w
                viol = max((mu[i] - gamma * vw[i] - xi) for i in range(n) if i not in S) if r < n else 0.0
                if best is None or u > best[0] + 1e-12:
                    best = (u, w, max(0.0, viol))
    return best


def minvol_enum(Sig):
    n = Sig.shape[0]; best = None
    for r in range(1, n + 1):
        for S in itertools.combinations(range(n), r):
            A = Sig[np.ix_(S, S)]; Ainv = np.linalg.inv(A)
            o = np.ones(len(S))
            wS = Ainv @ o / (o @ Ainv @ o)
            if np.all(wS >= -1e-10):
                w = np.zeros(n); w[list(S)] = np.maximum(wS, 0.0)
                v = w @ Sig @ w
                xi = 2.0 / (o @ Ainv @ o)
                vw = Sig @ w
                viol = max((xi - 2.0 * vw[i]) for i in range(n) if i not in S) if r < n else 0.0
                if best is None or v < best[0] - 1e-15:
                    best = (v, w, max(0.0, viol))
    return best


def sharpe_enum(mu, Sig, rf):
    n = len(mu); d = mu - rf; best = None
    for r in range(1, n + 1):
        for T in itertools.combinations(range(n), r):
            A = Sig[np.ix_(T, T)]; Ainv = np.linalg.inv(A)
            lam = d[list(T)] @ Ainv @ d[list(T)]
            if lam <= 1e-16: continue
            yT = Ainv @ d[list(T)] / lam
            if np.any(yT < -1e-10): continue
            y = np.zeros(n); y[list(T)] = np.maximum(yT, 0.0)
            nu = 2.0 / lam; g = Sig @ y
            viol = max((nu * d[i] - 2.0 * g[i]) for i in range(n) if i not in T) if r < n else 0.0
            if viol > 1e-10: continue
            w = y / y.sum()
            s = (mu @ w - rf) / math.sqrt(w @ Sig @ w)
            if best is None or s > best[0] + 1e-12:
                best = (s, w, max(0.0, viol))
    return best


def grid5():
    return np.array([(a * .05, b * .05, c * .05, e * .05, (20 - a - b - c - e) * .05)
                     for a in range(21) for b in range(21 - a)
                     for c in range(21 - a - b) for e in range(21 - a - b - c)])


def slsqp_check(fun_muSig, mu, Sig, seed=3, k=50):
    rng = np.random.default_rng(seed)
    W = np.vstack([np.full(len(mu), 1 / len(mu))] + [s / s.sum() for s in rng.dirichlet(np.ones(len(mu)), k)])
    cons = ({"type": "eq", "fun": lambda w: w.sum() - 1},)
    best = -np.inf
    for s in W:
        r = minimize(fun_muSig, s, bounds=[(0., 1.)] * len(mu), constraints=cons, method="SLSQP")
        best = max(best, -r.fun)
    return best


def wS(w): return "/".join(f"{100*x:6.2f}" for x in w)

W5 = grid5()
print("grid nodes:", len(W5), "(expect 10626)")

print("\n=== A. Correlation-matrix eigen-structure (M2b / gate 1 claim) ===")
ev = np.linalg.eigvalsh(R0)
print("corr min eig exact:", f"{ev.min():.9f}", " max eig:", f"{ev.max():.9f}", " all>0:", bool(ev.min() > 0))
print("SIG5 min eig:", f"{np.linalg.eigvalsh(SIG0).min():.6f}")

print("\n=== B. Uniform-covariance mis-scale invariance (M2a) ===")
for c in (1.10, 1.21, 0.81):
    S_c = c * SIG0
    gm = {}
    for g in (1, 3, 5):
        u1, w1, v1 = qp_enum(mu0, SIG0, g)
        u2, w2, v2 = qp_enum(mu0, S_c, g)          # mis-scaled Sigma, same gamma
        u3, w3, v3 = qp_enum(mu0, SIG0, g * c)     # true Sigma, rescaled gamma
        gm[g] = (np.max(np.abs(w2 - w3)), w1 @ [1,0,0,0,0])
    mv1 = minvol_enum(SIG0); mv2 = minvol_enum(S_c)
    sh1 = sharpe_enum(mu0, SIG0, .02); sh2 = sharpe_enum(mu0, S_c, .02)
    # grid-rounding invariance
    gpol = []
    for g in (1, 3, 5):
        uu1 = W5 @ mu0 - g / 2 * np.einsum("ij,jk,ik->i", W5, SIG0, W5)
        uu2 = W5 @ mu0 - g / 2 * np.einsum("ij,jk,ik->i", W5, S_c, W5)
        uu3 = W5 @ mu0 - g * c / 2 * np.einsum("ij,jk,ik->i", W5, SIG0, W5)
        p1 = tuple(W5[int(np.argmax(uu1))]); p2 = tuple(W5[int(np.argmax(uu2))]); p3 = tuple(W5[int(np.argmax(uu3))])
        gpol.append((g, p2 == p3, p3))
    print(f"c={c}: MV argmax |w(c*Sig,g)-w(Sig,gc)|={gm[3][0]:.2e}; minvol |dw|={np.max(np.abs(mv2[1]-mv1[1])):.2e}; "
          f"Sharpe |dw|={np.max(np.abs(sh2[1]-sh1[1])):.2e}, Sharpe*sqrt(c)-invariance err={abs(sh2[0]*math.sqrt(c)-sh1[0]):.2e}; "
          f"grid pols identical to (Sig,gc): {[f'g{g}:{ok}' for g, ok, _ in gpol]}")
# non-uniform counterexample (US vol +50%): shows the 'uniform' qualifier is load-bearing
v_nu = vols.copy(); v_nu[2] *= 1.5
SIG_nu = np.outer(v_nu, v_nu) * R0
_, w_base, _ = qp_enum(mu0, SIG0, 3); _, w_nu, _ = qp_enum(mu0, SIG_nu, 3)
print("non-uniform (US vol+50%): gamma=3 weights change by", np.round(100*(w_nu-w_base), 2), "%  (invariance broken, as 'uniform' wording implies)")

print("\n=== C. Illustrative correlation stresses (not adopted input changes) ===")
def Redit(R, pairs):
    R2 = R.copy()
    for i, j, v in pairs: R2[i, j] = R2[j, i] = v
    return R2

variants = {
    "base user-updated matrix": [],
    "higher A-JP correlation stress": [(0, 4, 0.40)],
    "lower HK-JP correlation stress": [(1, 4, 0.40)],
    "lower HK-JP and A-JP stress": [(1, 4, 0.40), (0, 4, 0.40)],
    "lower Asia and A-foreign stress": [(1, 4, 0.40), (0, 4, 0.40), (0, 2, 0.35), (0, 3, 0.35)],
}
for name, edits in variants.items():
    Rv = Redit(R0, edits); e = np.linalg.eigvalsh(Rv)
    assert e.min() > 0, name
    Sv = np.outer(vols, vols) * Rv
    mv = minvol_enum(Sv); sh = sharpe_enum(mu0, Sv, .02)
    out = [f"minvol A+HK={100*(mv[1][0]+mv[1][1]):5.2f} Asia(A+HK+JP)={100*(mv[1][0]+mv[1][1]+mv[1][4]):5.2f} eig={e.min():.3f}"]
    for g in (1, 3, 5):
        u, w, viol = qp_enum(mu0, Sv, g)
        out.append(f"g{g}: A+HK={100*(w[0]+w[1]):5.2f} Asia={100*(w[0]+w[1]+w[4]):5.2f}")
    u, w, _ = sh
    out.append(f"Sharpe: A+HK={100*(w[0]+w[1]):5.2f} Asia={100*(w[0]+w[1]+w[4]):5.2f}")
    print(f"{name:34s} " + " | ".join(out))
mv_b = minvol_enum(SIG0)
print(f"{'base':34s} minvol A+HK={100*(mv_b[1][0]+mv_b[1][1]):5.2f} Asia={100*mv_b[1][[0,1,4]].sum():5.2f}  (baseline)")
# SLSQP cross-check on the stressed gamma=3 optimum
Rv = Redit(R0, variants["lower HK-JP and A-JP stress"]); Sv = np.outer(vols, vols) * Rv
u, w, viol = qp_enum(mu0, Sv, 3)
best = slsqp_check(lambda w_: -(mu0 @ w_ - 1.5 * w_ @ Sv @ w_), mu0, Sv)
print(f"stress g=3: enum u={100*u:.4f} vs SLSQP {100*best:.4f} (SLSQP must not beat), kkt viol={viol:.1e}")

print("\n=== D. rf sensitivity of max proxy-Sharpe argmax (M3) ===")
for rf in (0.00, 0.01, 0.02, 0.03):
    s, w, _ = sharpe_enum(mu0, SIG0, rf)
    print(f"rf={rf*100:4.1f}%: w={wS(w)}  Sharpe={s:.3f}")

print("\n=== E. Arithmetic/geometric-equivalent spread and half-variance diagnostic (M3) ===")
for k, s in zip(order, vols):
    spread = 100 * (inp["gross_arithmetic_return"] - (inp["gross_arithmetic_return"] - 0.5*s*s))
    print(f"{k:12s} sigma={100*s:5.2f}%  arithmetic-geometric spread={spread:5.2f}pp  sigma^2/2={100*s*s/2:5.2f}pp")
print("Geometric equivalent is approximated as gross arithmetic minus 0.5*assumed variance; MVO uses arithmetic returns.")

print(f"\n=== F. Benchmark utility gaps {inp['policy_benchmark']['name']} vs five-market grid policy (M4) and GC variants ===")
wb = np.array(inp["policy_benchmark"]["weights_a_hk_us"], dtype=float)
ub = {g: mu0[:3] @ wb - g / 2 * wb @ SIG0[:3, :3] @ wb for g in (1, 3, 5)}
w_pad = np.append(wb, [0, 0])
assert all(abs((mu0 @ w_pad - g / 2 * w_pad @ SIG0 @ w_pad) - ub[g]) < 1e-14 for g in (1, 3, 5)), "padding equivalence"
for g in (1, 3, 5):
    uu = W5 @ mu0 - g / 2 * np.einsum("ij,jk,ik->i", W5, SIG0, W5)
    i = int(np.argmax(uu))
    print(f"g={g}: grid-best u={100*uu[i]:.4f}  bench u={100*ub[g]:.4f}  gap exact={(uu[i]-ub[g])*100:.4f}pp -> 2dp {round((uu[i]-ub[g])*100,2)}")
gaps = []
for g in (1, 3, 5):
    uu = W5 @ mu0 - g / 2 * np.einsum("ij,jk,ik->i", W5, SIG0, W5)
    gaps.append(float(np.max(uu) - ub[g]))
print("five-asset grid-best minus benchmark utility gaps (pp): " + "/".join(f"{100*x:.2f}" for x in gaps))

print("\n=== G. Structural identities (M6) ===")
mv_ref = minvol_enum(SIG0)
print("minvol weights:", wS(mv_ref[1]))
for g in (1, 3, 5):
    u, w, _ = qp_enum(REFMU, SIG0, g)
    assert np.max(np.abs(w - mv_ref[1])) < 1e-9
s_ref = sharpe_enum(REFMU, SIG0, .02)
assert np.max(np.abs(s_ref[1] - mv_ref[1])) < 1e-9
print("reference case: MV(g) and max-Sharpe all coincide with min-vol: OK")
print("ref Sharpe identity (7-2)/sigma:", f"{(0.07-.02)/math.sqrt(mv_ref[0]):.4f}")
for g in (1, 3, 5):
    u5 = qp_enum(mu0, SIG0, g); u3 = qp_enum(mu0[:3], SIG0[:3, :3], g)
    print(f"g={g}: u5-u3 = {1e4*(u5[0]-u3[0]):+.2f} bp (>=0 always: {u5[0] >= u3[0]-1e-12})")
gc_g5 = qp_enum(mu0[:3], SIG0[:3, :3], 5)
gc_g3 = qp_enum(mu0[:3], SIG0[:3, :3], 3)
mv3 = minvol_enum(SIG0[:3, :3])
print(f"GC totals exact: minvol {100*(mv3[1][0]+mv3[1][1]):.4f}  g3 {100*(gc_g3[1][0]+gc_g3[1][1]):.4f}  g5 {100*(gc_g5[1][0]+gc_g5[1][1]):.4f}")

print("\n=== H. KKT certificates on stressed and base optima (M6 zeros) ===")
res = qp_enum(mu0, SIG0, 3)
print("base g=3 kkt viol:", f"{res[2]:.2e}")
sh_be = sharpe_enum(mu0, SIG0, .02)
print("max-Sharpe kkt viol:", f"{sh_be[2]:.2e}")
