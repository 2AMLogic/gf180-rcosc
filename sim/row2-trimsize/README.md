# sim/row2-trimsize - trim-bank sizing screen for ratified Row 2 (issue #460)

Simulation-only design iteration: name a trim-bank / ladder sizing whose
measured dense trim curve meets the ratified Row-2 step (0.314 %/code,
half-LSB +/-0.157 %) with monotone carries, or record with numbers that no
sizing in the screened family does. **No design file changes**: the committed
schematic, netlists-of-record and layout are untouched; every candidate is a
netlist-text edit of the #87 campaign's `ext` DUT
(`sim/cmph-fix/rcosc_top_p3_cmphfix.spice`, DR-0023 P3), the same mechanism
`sim/row4-nonron/variant.py` uses for `w<K>r<P>`.

## Method

1. **Attribution** (`fit_weights.py`, offline): the committed dense campaign's
   256-code curves are fitted exactly by `T(c) = intercept + sum_b bit_b(c) *
   beta_b` (max residual 1.1-2.4 % of T). The measured failures all reduce to
   the per-bit weight ratios `rho_b = |beta_b| / (W * 2^b)` (W = unit period
   step = sum|beta_b|/255): low bits 1.10-1.40x overweight, bit 7 ~0.90x
   underweight. The carry period step into bit b is
   `W*(sum_{k<b} rho_k 2^k - rho_b 2^b)`; with the measured rho this is
   +24 W at 0x7F->0x80 (the -9.4 % frequency step DR-0021 reports). The
   endpoint-span mean step (analyze.py convention
   `100*(f255/f0-1)/255`) is 0.63-0.69 %/code = 2.0-2.2x ratified because the
   curve spans f(0xFF)/f(0x00) = 2.6-2.8x, and the per-code relative steps grow
   with f (period-linear law) on top.
2. **Sizing rule** (ratio rule): `r_b' = r_b * (W' * 2^b) / |beta_b|` makes the
   effective weights binary-exact at the compensation corner; `RFIX'` places
   the curve. The two smallest segments are floored at 0.15 um (the ratio rule
   is Ron-dominated there; a floored low bit keeps a positive in-band step and
   the high bits own the monotonicity risk).
3. **Screen** (`gen_screen.py` + `run_set.py`): <= 6 sizings x 57 codes x 1
   corner (tt/27C/3.3V) on the batch fleet (`klt sim --batch-set`, nothing
   local). The code set covers endpoints, all carry +/-1 codes (power-of-two
   and the four DR-0021 top-of-range carries), single-bit codes and
   calibration-region codes. `analyze_screen.py` re-fits each variant's
   sparse curve (rho, carries, endpoints, non-positive steps).
4. **Full curves** (finalists only): `sim/trim-dense/prepare.py` over the
   finalist netlist (256 codes x the three dense-campaign corners), driven by
   `run_set.py`, analyzed by `sim/trim-dense/analyze.py` with a filled
   manifest - the same evidence shape as the committed campaign.
5. **Pricing** (`gen_pricing.py`): row-4 `ss` 27 C supply span (3.0/3.3/3.6 V
   at the calibrated code), running Iq (mean i(VDD) over the fosc window,
   DR-0046 basis) at the calibrated codes and 0xFF, per finalist.

## Files

| file | role |
|---|---|
| `fit_weights.py` | offline bit-weight fit on the committed campaign; sizing proposals |
| `variant.py` | sizing name -> netlist text edit (`s<RFIX>-<r0>-..<r7>[w<K>]`, `ctrl`) |
| `gen_screen.py` | sparse-code bench generator (reuses `sim/trim-dense/prepare.py` request/testbench bytes) |
| `run_set.py` | resumable `klt sim --batch-set` driver (fleet only, capacity wait, ledger) |
| `analyze_screen.py` | sparse-curve fit and step report per variant |
| `gen_pricing.py` | row-4 span / Iq request generator for finalists |
| `pricing_table.py` | offline calib / stage / iq tables from the pricing reports |
| `test_toolchain.py` | offline pytest suite (variant edits, switch doubling, LS, synthetic fit, ratio-rule floor) |
| `results/20261122T0550Z-screen/` | screen run: fit + bench + 342 batch reports + analysis (DR-0048) |
| `results/20261122T0810Z-full-s22-83/` | F2.50@tt full 256-code x 3-corner curve (batch reports + analyze.py output) |
| `results/20261122T0815Z-pricing/` | F2.50@tt pricing on the rebuilt-layout extraction (calib / stage / iq) |

## Reproduce

    python3 -I sim/row2-trimsize/fit_weights.py --out <run>/fit
    python3 -I sim/row2-trimsize/gen_screen.py --fit <run>/fit/fit.json --out <run>/bench
    python3 -I sim/row2-trimsize/run_set.py --bench-dir <run>/bench --out-dir <run>
    python3 -I sim/row2-trimsize/analyze_screen.py --reports <run>/reports --bench <run>/bench --out <run>/analysis
    python3 -I -m pytest -p no:cacheprovider sim/row2-trimsize/test_toolchain.py

Everything except `run_set.py` is offline. `run_set.py` submits single-corner
requests to the Spot batch fleet with `--wait-for-capacity 600` (host rule);
no local ngspice grid exists in this directory. The committed runs and their
verdict (decision record 0048: the screen is negative) are under `results/`.
