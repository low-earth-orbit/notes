# Equity allocation across regional markets

Companion technical analysis to [Chinese Couch Potato investing](chinese-couch-potato.md).

The allocation universe is five regional sleeves, all held in CNY with no currency hedging:

| Asset class           | Index proxy | Fund                         | Ticker |
| --------------------- | ----------- | ---------------------------- | ------ |
| A-shares              | CSI 800     | 易方达中证800ETF联接A        | 007856 |
| Hang Seng Index       | Hang Seng   | 华夏沪港通恒生ETF联接A       | 000948 |
| U.S. large-cap stocks | S&P 500     | 摩根标普500指数(QDII)人民币A | 017641 |
| European stocks       | MSCI Europe | 摩根欧洲动力策略股票(QDII)A  | 006282 |
| Japanese stocks       | MSCI Japan  | 摩根日本精选股票(QDII)A      | 007280 |

Funds 006282/007280 are active and modeled at zero alpha. Their benchmarks are implementation gaps: 006282 blends 90% MSCI Europe net return with 10% cash; 007280 blends 90% TOPIX total return with 10% after-tax bank-deposit return. The modeled sleeves are pure equity.

Weights are percentages of the **equity sleeve** and sum to 100%; choose the stock/bond split first. The parent note's **18/12/70** is the sole policy benchmark, reflecting domestic-income correlation and property exposure.

_Last updated: Oct 2026. Assumptions and implementation costs may change._

**Not financial advice.** A planning framework, not a personal recommendation.

## Inputs

Basis: mainland CNY investor, unhedged via Stock Connect/QDII.

### Returns and volatilities

| Asset class     | Gross arithmetic return | Geometric equivalent approx. | Volatility |
| --------------- | ----------------------: | ---------------------------: | ---------: |
| A-shares        |                    7.0% |                        5.00% |        20% |
| Hang Seng Index |                    7.0% |                        5.00% |        20% |
| US              |                    7.0% |                        5.88% |        15% |
| Europe          |                    7.0% |                        5.88% |        15% |
| Japan           |                    7.0% |                        5.88% |        15% |

They are assumptions, not forecasts.

### Correlations

| Asset class     | A-shares |   HK | U.S. | Europe | Japan |
| --------------- | -------: | ---: | ---: | -----: | ----: |
| A-shares        |     1.00 | 0.55 | 0.30 |   0.30 |  0.30 |
| Hang Seng Index |     0.55 | 1.00 | 0.50 |   0.50 |  0.50 |
| US              |     0.30 | 0.50 | 1.00 |   0.80 |  0.70 |
| Europe          |     0.30 | 0.50 | 0.80 |   1.00 |  0.70 |
| Japan           |     0.30 | 0.50 | 0.70 |   0.70 |  1.00 |

They are assumptions, not forecasts.

### Costs, withholding, and net returns

| Asset class     |   Fee | WHT rate | Yield |  Drag | Net geometric | Net arithmetic MVO |
| --------------- | ----: | -------: | ----: | ----: | ------------: | -----------------: |
| A-shares        |  0.3% |       0% | 2.15% | 0.00% |         4.70% |            6.7000% |
| Hang Seng Index |  0.6% |      20% | 3.10% | 0.62% |         3.78% |            5.7800% |
| US              |  0.7% |      10% | 1.10% | 0.11% |         5.07% |            6.1900% |
| Europe          | 1.50% |      15% | 2.89% | 0.43% |         3.94% |            5.0665% |
| Japan           | 1.40% |      10% | 2.02% | 0.20% |         4.27% |            5.3980% |

These are estimates, not actual.

## Method

Fully invested, long-only weights; σ_p = √(wᵀΣw). Continuous optima use support enumeration, per-support KKT systems, and off-support certificates:

- **Minimum volatility:** min wᵀΣw.
- **Maximum proxy-Sharpe:** max (wᵀμ_net − r_f)/σ_p, r_f = 2% CNY-rate placeholder.
- **Mean-variance expected utility:** max wᵀμ_net,arith − (γ/2) wᵀΣw, γ ∈ {1, 3, 5}.

The equal 7% gross arithmetic return is the return-neutral input; MVO uses net arithmetic return = gross arithmetic return − fee − withholding drag. For wealth-growth reporting, geometric equivalents are approximated as arithmetic return − half the assumed variance, and net geometric return = gross geometric return − fee − withholding drag. Sharpe also depends on the 2% CNY-rate placeholder. Rounded policies use the parent note's 5-point grid, A/HK/US/EU/JP; HK ≥ 5% is reported separately.

**Robustness.** Black–Litterman remains rejected: its cap-weighted anchor hard-codes the contested Greater-China allocation and no views are available. Checks: equal-return/no-fee reference case; γ grid; Greater-China restriction. Fee/tax scenarios and alternate return forecasts remain excluded. Assumed volatilities and correlations are planning inputs, not forecasts or measured CNY covariances.

## Best-estimate results

The minimum-variance portfolio uses no returns, so it equals the reference-case optimum (equal 7.0% arithmetic returns, no fees or tax). All three objectives coincide there (Sharpe = (7.0 − 2.0)/12.74 = 0.392 — script self-test):

| Policy                   |      A |    HK |   U.S. |     EU |     JP | Volatility | Sharpe |
| ------------------------ | -----: | ----: | -----: | -----: | -----: | ---------: | -----: |
| Min-vol = reference case | 23.36% | 0.00% | 22.99% | 22.99% | 30.66% |     12.74% |  0.392 |
| Maximum proxy-Sharpe     | 33.74% | 0.00% | 57.42% |  0.00% |  8.84% |     13.33% |  0.322 |

|   γ |      A |    HK |   U.S. |    EU |     JP | Net arithmetic return | Volatility | Utility | Grid policy  |
| --: | -----: | ----: | -----: | ----: | -----: | --------------------: | ---------: | ------: | ------------ |
|   1 | 41.80% | 0.00% | 58.20% | 0.00% |  0.00% |                 6.40% |     13.78% |   5.45% | 40/0/60/0/0  |
|   3 | 31.96% | 0.00% | 53.57% | 0.00% | 14.46% |                 6.24% |     13.18% |   3.63% | 30/0/55/0/15 |
|   5 | 29.03% | 0.00% | 47.22% | 0.00% | 23.75% |                 6.15% |     13.00% |   1.93% | 30/0/45/0/25 |

The proxy-Sharpe optimum includes A/U.S./Japan; HK and Europe are KKT-gated corner zeros. Japan is 0% at γ=1, 14.46% at γ=3, and 23.75% at γ=5. With HK ≥ 5%, grid policies are **40/5/55/0/0**, **30/5/50/0/15**, and **25/5/45/0/25** at γ=1/3/5.

### Three-fund (A/HK/US only) and the 18/12/70 benchmark

| Objective / policy     |      A |     HK |   U.S. | Volatility | Utility (γ shown) | Grid policy |
| ---------------------- | -----: | -----: | -----: | ---------: | ----------------: | ----------- |
| Minimum volatility     | 27.78% |  5.56% | 66.67% |     13.54% |                 – | –           |
| Expected utility, γ=1  | 41.80% |  0.00% | 58.20% |     13.78% |             5.45% | 40/0/60     |
| Expected utility, γ=3  | 34.16% |  0.00% | 65.84% |     13.59% |             3.59% | 35/0/65     |
| Expected utility, γ=5  | 32.63% |  0.00% | 67.37% |     13.57% |             1.75% | 35/0/65     |
| **Benchmark 18/12/70** | 18.00% | 12.00% | 70.00% |     13.65% |             3.44% | –           |

Benchmark utility shown is at γ=3. Restricted Greater-China totals are 33.33% (min-vol), 100% (γ=1), 34.16% (γ=3), and 32.63% (γ=5). Benchmark utilities are 5.30/3.44/1.57 at γ=1/3/5. Versus the five-asset 5pp grid, 18/12/70 gives up 0.15/0.19/0.35pp at γ=1/3/5. Europe/Japan improve best utility over the Greater-China restriction by **0.00/3.91/17.60 bp** at γ=1/3/5.

## Conclusions

- **The U.S. is the largest sleeve in the minimum-volatility portfolio** (22.99%) and at γ=3/5 (53.57%/47.22%). The 18/12/70 policy's 70% U.S. weight remains a deliberate policy tilt.
- **Japan is a diversifier in return-seeking optima:** 0% at γ=1, 14.46% at γ=3, and 23.75% at γ=5. It reaches 30.66% in the equal-return, no-fee minimum-volatility reference portfolio.
- **Europe is useful only in the equal-return reference here.** It drops from 22.99% reference weight to zero in the return-seeking optima, reflecting the input cost and correlation assumptions.

## Verification appendix

The optimization program and its input file sit in `cpp-code/`:

```
ccp-allocation-optimize.py      # the optimizer: reference case, min-vol, max-Sharpe,
                                # MV(γ) five-asset + Greater-China, 18/12/70 benchmark,
                                # utility improvement, range table
ccp-allocation-inputs.json      # every number the program and this note use
python3 ccp-allocation-optimize.py [--json out.json]    # run
```

The optimizer calculates results from that input file; the tables here are transcribed from its report and cross-checked independently. Source figures and assumptions are documented in the input file. The program exits successfully only if all 7 built-in gates pass:

|   # | Built-in gate (all PASS)                              | Detail                                     |
| --: | ----------------------------------------------------- | ------------------------------------------ |
|   1 | Correlation matrix positive semi-definite             | minimum eigenvalue 0.200000                |
|   2 | Reference case: max proxy-Sharpe = min-vol            | weight max-deviation 1.67e-16              |
|   3 | Reference case: MV(γ) = min-vol for every γ           | all three optimizers agree                 |
|   4 | Feasibility: rows sum to 100, bounds [0, 100]         | max error 2.22e-16                         |
|   5 | Utility recomputed from printed weights               | max error 1.03e-04 pp                      |
|   6 | KKT off-support inequalities (zero-weight exclusions) | max violation 0.00e+00                     |
|   7 | Grid cardinalities, 5-point grid                      | 10626 five-asset / 231 Greater-China nodes |

Verification (run from `cpp-code/`): `python3 ccp-allocation-optimize.py` (7/7 built-in gates), independent reproduction (`python3 note-review/repro-user-inputs-check.py`, 55/55 checks), and supplementary methodology diagnostics (`python3 note-review/mrev_checks.py`). See `cpp-code/note-review/reproduction-user-updated.md` for the current reproduction record. “Verified” means calculations reproduce; it does not validate planning returns, correlations, or allocations.

_Last regenerated: 2026-10-20. Program lives in `cpp-code/ccp-allocation-optimize.py` with `cpp-code/ccp-allocation-inputs.json`._
