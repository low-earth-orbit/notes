# Current reproduction record: user-updated arithmetic-return inputs

Date: 2026-10-20. This is the current run for the input tables in the repo-root note `../chinese-couch-potato-technical-note.md`, which are authoritative. All commands below run from the `cpp-code/` directory.

## Input convention

- Gross arithmetic return: 7.0% for each sleeve; assumed volatility is 20%/20%/15%/15%/15% (A/HK/US/EU/JP).
- Approximate gross geometric equivalents for reporting: arithmetic return minus half variance (5.00%/5.00%/5.88%/5.88%/5.88%).
- Net geometric return: gross geometric return minus fee and withholding drag. Net arithmetic MVO return: gross arithmetic return minus fee and withholding drag. The two return measures are kept distinct.
- Equal 7% arithmetic-return reference case ignores fees and tax. Its min-vol, max-proxy-Sharpe, and mean-variance optima coincide; this also verifies the optimizer's structural identity.
- User-updated correlation matrix and sole 18/12/70 benchmark are retained. Fee/tax scenario tests are not run.

## Reproduction and checks

- `python3 ccp-allocation-optimize.py`: exit 0; **7/7** built-in gates pass.
- `python3 note-review/repro-user-inputs-check.py`: **55/55** independent checks pass. The checker runs the optimizer in a temporary directory, then independently reconstructs net arithmetic returns, covariance, continuous optima and KKT certificates, grid policies, Greater-China restriction, benchmark utilities, and allocation ranges; it also checks note/input/output consistency.
- `python3 note-review/mrev_checks.py`: supplementary methodology diagnostics covering covariance-scale identities, correlation stresses, risk-free-rate sensitivity, the arithmetic/geometric approximation, benchmark utility gaps, reference identities, and KKT checks.

## Selected results

- Five-asset minimum-volatility and equal-return/no-fee reference weights: **23.36/0.00/22.99/22.99/30.66** (A/HK/US/EU/JP); volatility **12.74%**.
- Best-estimate net-arithmetic MVO weights for γ=1/3/5: **41.80/0.00/58.20/0.00/0.00**, **31.96/0.00/53.57/0.00/14.46**, and **29.03/0.00/47.22/0.00/23.75**.
- The Greater-China minimum-volatility portfolio is **27.78/5.56/66.67** (A/HK/US), with **13.54%** volatility.
- The 18/12/70 benchmark has **13.65%** volatility and net arithmetic return **6.23%**; utilities are **5.30/3.44/1.57%** at γ=1/3/5.
- Adding Europe/Japan improves best utility over the Greater-China restriction by **0.00/3.91/17.60 bp** at γ=1/3/5.

“Verified” means the calculations reproduce under the stated assumptions; it does not validate the planning returns, volatilities, correlations, or resulting allocation.
