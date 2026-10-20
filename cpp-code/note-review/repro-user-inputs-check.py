#!/usr/bin/env python3
"""Independent optimizer reproduction for the user-updated planning inputs."""
import itertools
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np

REPO = Path(__file__).resolve().parents[2]
CODE = Path(__file__).resolve().parents[1]
inp = json.loads((CODE / "ccp-allocation-inputs.json").read_text())
note = (REPO / "chinese-couch-potato-technical-note.md").read_text()
with tempfile.TemporaryDirectory(prefix="ccp-optimizer-check-") as tempdir:
    output_path = Path(tempdir) / "optimizer-output.json"
    run = subprocess.run(
        [sys.executable, str(CODE / "ccp-allocation-optimize.py"), "--json", str(output_path)],
        cwd=CODE, capture_output=True, text=True, check=False)
    if run.returncode != 0:
        raise SystemExit(f"optimizer failed during independent check:\n{run.stdout}\n{run.stderr}")
    program = json.loads(output_path.read_text())
    run_text = run.stdout
checks = 0
passed = 0
failed = []


def check(label, condition, detail=""):
    global checks, passed
    checks += 1
    if bool(condition):
        passed += 1
        print(f"[PASS] {label}")
    else:
        failed.append(label)
        print(f"[FAIL] {label} {detail}")


def close(a, b, tol=1e-8):
    return abs(float(a) - float(b)) <= tol


def pct(w, digits=2):
    return "/".join(f"{100*x:.{digits}f}" for x in w)


expected_order = ["A_shares", "HK_listed", "US_largecap", "Europe", "Japan"]
order = [a["asset5"] for a in inp["assets"]]
assets = {a["asset5"]: a for a in inp["assets"]}
arithmetic = np.full(len(order), float(inp["gross_arithmetic_return"]))
vol = np.array([assets[k]["volatility"] for k in order])
compound = arithmetic - .5*vol*vol
R = np.array(inp["correlations"]["matrix"], dtype=float)
fees = np.array([assets[k]["fee"] for k in order])
taxdrag = np.array([assets[k]["dividend_yield"] * assets[k]["withholding_rate"] for k in order])
mu = arithmetic - fees - taxdrag
Sigma = np.outer(vol, vol) * R

# User-updated planning assumptions and net-return calculations.
check("single asset order defines correlation-matrix order", order == expected_order
      and inp["meta"]["correlation_matrix_order"] == "Same as the assets array.")
asset_fields = {"asset5", "fund", "ticker", "volatility", "fee",
                "dividend_yield", "withholding_rate"}
check("input schema contains one compact data set",
      set(inp) == {"meta", "gross_arithmetic_return", "assets", "correlations", "policy_benchmark"}
      and all(set(assets[k]) == asset_fields for k in order))
check("gross arithmetic return vector is equal at 7% as requested",
      np.allclose(arithmetic, [.07]*5, atol=1e-12))
check("geometric equivalents reflect arithmetic minus half variance",
      np.allclose(compound, [.05,.05,.05875,.05875,.05875], atol=1e-12)
      and np.allclose(compound, arithmetic-.5*vol*vol, atol=1e-12))
check("assumed volatility vector matches the technical note",
      np.allclose(vol, [.20,.20,.15,.15,.15], atol=1e-12))
check("user-updated planning correlation matrix matches the technical note", np.allclose(R, [
    [1,.55,.30,.30,.30], [.55,1,.50,.50,.50], [.30,.50,1,.80,.70],
    [.30,.50,.80,1,.70], [.30,.50,.70,.70,1]], atol=1e-12))
check("user planning return/correlation and volatility basis recorded",
      inp["meta"]["base_currency"] == "CNY" and inp["meta"]["currency_hedging"] == "none"
      and "assumptions, not forecasts" in inp["meta"]["purpose"].lower())
check("single common gross arithmetic return is 7%",
      inp["gross_arithmetic_return"] == .07 and np.allclose(arithmetic, [.07]*5))
check("one fee and withholding estimate is defined per asset",
      all("fee" in assets[k] and "withholding_rate" in assets[k] and "fee_scenarios" not in assets[k]
          for k in order)
      and "fee_scenarios" not in inp)
check("correlation matrix symmetric, unit diagonal, positive definite",
      np.allclose(R, R.T) and np.allclose(np.diag(R), 1) and np.linalg.eigvalsh(R).min() > 0)
check("covariance and Greater-China submatrix positive definite",
      np.linalg.eigvalsh(Sigma).min() > 0 and np.linalg.eigvalsh(Sigma[:3,:3]).min() > 0)


def qp(mu_, sig, gamma):
    n = len(mu_); best = None
    for size in range(1, n+1):
        for support in itertools.combinations(range(n), size):
            Q = sig[np.ix_(support, support)]
            Qi = np.linalg.inv(Q); one = np.ones(size); b = mu_[list(support)]
            lam = (one @ Qi @ b - gamma) / (one @ Qi @ one)
            ws = Qi @ (b - lam*one) / gamma
            if np.min(ws) < -1e-10:
                continue
            w = np.zeros(n); w[list(support)] = np.maximum(ws, 0)
            u = mu_ @ w - gamma/2 * w @ sig @ w
            violation = max((mu_[i] - gamma*(sig@w)[i] - lam for i in range(n) if i not in support), default=0)
            if best is None or u > best[0]:
                best = (u, w, support, max(0.0, violation))
    return best


def minvol(sig):
    n = sig.shape[0]; best = None
    for size in range(1,n+1):
        for support in itertools.combinations(range(n),size):
            Q=sig[np.ix_(support,support)]; Qi=np.linalg.inv(Q); one=np.ones(size)
            ws=Qi@one/(one@Qi@one)
            if np.min(ws)<-1e-10: continue
            w=np.zeros(n); w[list(support)]=np.maximum(ws,0)
            v=w@sig@w
            xi=2/(one@Qi@one)
            violation=max((xi-2*(sig@w)[i] for i in range(n) if i not in support),default=0)
            if best is None or v<best[0]: best=(v,w,support,max(0.0,violation))
    return best


def sharpe(mu_, sig, rf=.02):
    n=len(mu_); d=mu_-rf; best=None
    for size in range(1,n+1):
        for support in itertools.combinations(range(n),size):
            Q=sig[np.ix_(support,support)]; Qi=np.linalg.inv(Q); ds=d[list(support)]
            lam=ds@Qi@ds
            if lam<=1e-16: continue
            yS=Qi@ds/lam
            if np.min(yS)<-1e-10: continue
            y=np.zeros(n); y[list(support)]=np.maximum(yS,0)
            w=y/y.sum(); ratio=(mu_@w-rf)/math.sqrt(w@sig@w)
            violation=max(((2/lam)*d[i]-2*(sig@y)[i] for i in range(n) if i not in support),default=0)
            if violation>1e-9: continue
            if best is None or ratio>best[0]: best=(ratio,w,support,max(0.0,violation))
    return best


def grid(n):
    step=.05
    if n==5:
        return np.array([(a*step,b*step,c*step,d*step,(20-a-b-c-d)*step)
                         for a in range(21) for b in range(21-a) for c in range(21-a-b)
                         for d in range(21-a-b-c)])
    return np.array([(a*step,b*step,1-(a+b)*step) for a in range(21) for b in range(21-a)])


def utils(W, mu_, sig, gamma):
    return W@mu_ - gamma/2*np.einsum("ij,jk,ik->i",W,sig,W)


mv5=minvol(Sigma); mv3=minvol(Sigma[:3,:3]); sh5=sharpe(mu,Sigma); sh3=sharpe(mu[:3],Sigma[:3,:3])
qp5={g:qp(mu,Sigma,g) for g in (1,3,5)}; qp3={g:qp(mu[:3],Sigma[:3,:3],g) for g in (1,3,5)}
check("independent min-vol matches program weights and risk",
      np.max(np.abs(mv5[1]-program["best_estimate"]["minvol"]["w"]))<1e-9
      and close(100*math.sqrt(mv5[0]),program["best_estimate"]["minvol"]["sigma_pct"],1e-8))
check("reference identity: equal-returns Sharpe and MV equal min-vol",
      np.max(np.abs(sharpe(arithmetic,Sigma)[1]-mv5[1]))<1e-9
      and all(np.max(np.abs(qp(arithmetic,Sigma,g)[1]-mv5[1]))<1e-9 for g in (1,3,5)))
check("independent maximum Sharpe matches program weights and ratio",
      np.max(np.abs(sh5[1]-program["best_estimate"]["max_sharpe"]["w"]))<1e-9
      and close(sh5[0],program["best_estimate"]["max_sharpe"]["sharpe"],1e-8))
for g in (1,3,5):
    row=program["best_estimate"]["mv"][str(g)]
    gcrow=program["greater_china_3"]["mv"][str(g)]
    check(f"independent MV gamma={g} matches program weights/utility",
          np.max(np.abs(qp5[g][1]-row["w"]))<1e-9 and close(100*qp5[g][0],row["u_pct"],1e-8))
    check(f"independent Greater-China gamma={g} matches program",
          np.max(np.abs(qp3[g][1]-gcrow["w"]))<1e-9 and close(100*qp3[g][0],gcrow["u_pct"],1e-8))
    check(f"MV gamma={g} KKT certificate is nonpositive", qp5[g][3]<1e-9 and qp3[g][3]<1e-9)

G5=grid(5); G3=grid(3)
check("5pp grid cardinalities are 10626 and 231",len(G5)==10626 and len(G3)==231)
gridw={}; grid3w={}
for g in (1,3,5):
    i=int(np.argmax(utils(G5,mu,Sigma,g))); j=int(np.argmax(utils(G3,mu[:3],Sigma[:3,:3],g)))
    gridw[g]=G5[i]; grid3w[g]=G3[j]
    out_grid=np.array([float(x) for x in program["best_estimate"]["mv"][str(g)]["grid_best"].split("/")])/100
    check(f"5-asset grid gamma={g} matches program policy and score",
          np.max(np.abs(gridw[g]-out_grid))<1e-12
          and close(100*utils(G5,mu,Sigma,g)[i],program["best_estimate"]["mv"][str(g)]["grid_best_u_pct"],1e-8))
    check(f"Greater-China grid gamma={g} matches program policy",
          "/".join(f"{100*x:.0f}" for x in grid3w[g])==program["greater_china_3"]["mv"][str(g)]["grid_best"])

bench=inp["policy_benchmark"]; wb=np.array(bench["weights_a_hk_us"])
check("18/12/70 configured benchmark matches program",bench["name"] in program["policy_benchmarks"])
ub={g:mu[:3]@wb-g/2*wb@Sigma[:3,:3]@wb for g in (1,3,5)}
pb=program["policy_benchmarks"][bench["name"]]
check("benchmark return and volatility independently reproduce",
      close(100*mu[:3]@wb,pb["Rp_pct"]) and close(100*math.sqrt(wb@Sigma[:3,:3]@wb),pb["sigma_pct"]))
check("benchmark utilities independently reproduce",all(close(100*ub[g],pb["u_pct"][str(g)]) for g in (1,3,5)))
check("option value utility improvement independently reproduces",
      all(f"{1e4*(qp5[g][0]-qp3[g][0]):.2f}"==f"{program['improvement_bp'][str(g)]['bp']:.2f}" for g in (1,3,5)))

# Rebuild the range population independently and compare to the program.
population=[mv5[1],sh5[1]]
for g in (1,3,5): population.extend([qp5[g][1],gridw[g]])
for g in (1,3,5): population.append(np.r_[qp3[g][1],[0,0]])
for i,key in enumerate(("A","HK","US","EU","JP")):
    values=np.array([w[i] for w in population])*100
    got=program["ranges"][key]
    check(f"independent {key} allocation range matches program",close(values.min(),got["min_pct"],5e-5) and close(values.max(),got["max_pct"],5e-5),f"{values.min():.4f}/{values.max():.4f} vs {got['min_pct']:.4f}/{got['max_pct']:.4f}")

# Input outputs, prose/table consistency, and all optimizer gates.
for row,k in zip(program["net_table"],order):
    check(f"net arithmetic return {k} matches independent fee/tax calculation",
          close(row["net_dec"],mu[order.index(k)]) and close(row["net_arithmetic_pct_4dp"],100*mu[order.index(k)],5e-5))
    check(f"note reports {k} geometric-equivalent/arithmetic/volatility inputs",
          f"{100*compound[order.index(k)]:.2f}%" in note
          and f"{100*arithmetic[order.index(k)]:.1f}%" in note
          and f"{100*vol[order.index(k)]:.0f}%" in note)
check("note documents user-updated return, volatility, correlation assumptions",
      "Gross arithmetic return" in note and "7.0%" in note and "20%" in note and "0.55" in note and "0.80" in note)
check("note documents the Japan pure-equity/007280 benchmark mismatch",
      "90% TOPIX" in note and "pure equity" in note.lower())
check("current note has no superseded 21/9/70 or old CMA references",
      all(x not in note for x in ("21/9/70","instructions.md","J.P. Morgan 2026 LTCMA CNY matrix","HSBC Oct 2026","Invesco Q3 2026","Southbound Universal")))
check("program reports all seven gates passing",len(program["gates"])==7 and all(g["verdict"]=="PASS" for g in program["gates"]))
check("captured optimizer run reports seven gates passing","GATE SUMMARY: 7 PASS, 0 FAIL" in run_text and "ALL GATES PASS" in run_text)
check("serialized optimizer inputs echo current JSON",program["inputs_echo"]==inp)

print(f"\n=== CHECKS: {checks} run, {passed} PASS, {checks-passed} FAIL ===")
if failed: print("FAILED:", *failed, sep="\n  ")
raise SystemExit(0 if not failed else 1)
