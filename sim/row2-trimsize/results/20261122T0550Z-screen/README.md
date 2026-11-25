# #460 row-2 trim-bank sizing screen (COMPLETE: 342/342 batch reports, 6 variants x 57 codes, tt 27 C / 3.3 V)

Simulation-only design iteration for issue #460 (T1 item 5). Append-only evidence;
the reading of these numbers is decision record **0048**
(`spec/decision-records/0048-*.md`). Nothing here edits a design file: every
candidate is a netlist-text re-sizing of the #87 campaign `ext` DUT
(`sim/cmph-fix/rcosc_top_p3_cmphfix.spice`, DR-0023 P3), the same mechanism
`sim/row4-nonron/variant.py` uses.

## Contents

| path | what |
|---|---|
| `fit/` | offline bit-weight fit of the committed #87 dense campaign (`fit_weights.py`): per-curve `beta_b`, weight ratios `rho_b`, Ron decomposition, and the three ratio-rule sizing proposals (F1.85 / F1.95 / F2.50) |
| `bench/` | frozen request set: `provenance.json` (sha256 per netlist/request), per-variant DUT copies, 57 testbenches + requests per variant at `tt_27C_3p3V` |
| `jobs/`, `reports/`, `ledger.jsonl` | batch-fleet execution (`run_set.py`, `klt sim --batch-set`, `--wait-for-capacity 600`); one report per request, `report_<variant>_<corner>_cXX.json` |
| `analysis/` | `analyze_screen.py` output: `screen.json` + `screen.md`, the per-variant sparse-curve table quoted in DR-0048 |

## Screened family (from `fit/fit.json` proposals, `gen_screen.py` defaults)

| label | sizing name (RFIX-r0..r7, um) | intent |
|---|---|---|
| ctrl | (unchanged P3 bank) | reproduces the committed #87 `ext_tt` numbers (f 0x00 = 28.652 MHz, 0x7F->0x80 = -9.40 %) |
| F1.85@tt | `s30.87078-0.18093-0.45059-0.97650-2.08666-4.29269-8.85515-19.14635-44.82498` | step-true, tt-compensated, balanced ends |
| F1.85@ss | `s30.87078-0.15000-0.23868-0.61435-1.41375-3.01906-6.37425-13.96053-32.48512` | step-true, ss-compensated (monotone margin probe) |
| F1.95@tt | `s28.37900-0.21230-0.50606-1.07899-2.28837-4.69161-9.66190-20.87300-48.84701` | margin variant |
| F2.50@tt | `s22.83669-0.40055-0.83895-1.69398-3.49886-7.08542-14.50304-31.23440-72.98256` | range-true pole (covers 28.8-67.2 MHz at tt with headroom) |
| F1.85@tt-w2 | F1.85@tt + `w2` | the #337 lever: all 16 bank pass devices doubled |

## Verdict (see `analysis/screen.md` and DR-0048)

**No sizing in the family meets the ratified row.** Every candidate misses the
0.3137 %/code step (0.03x-1.20x nominal, none inside the half-LSB band),
keeps 3-4 negative DR-0021 carries plus further non-positive steps, and
undershoots its designed span (targets 1.85-2.50x, measured 1.03-1.96x). The
`w2` diagnostic doubles the switches and makes ALL four carries negative while
the span falls to 1.026x - wider bank switches (#337's direction) do not
repair the ladder, they break it. The one-shot ratio rule fails because the
effective bit weights respond non-linearly to drawn re-sizing (switch Ron +
ladder node caps).

## Incident: 28 cross-wired reports, quarantined and re-run

The first submission mixed variants inside each `klt sim --batch-set` group;
28 of 342 member reports came back `pass` but were measurements of ANOTHER
variant's testbench (netlists share the basename `tb_cXX.spice`; tool gap
2AMLogic/klayout-tools#7180). Caught by comparing every report's
`environment.netlist_sha256` against the bench provenance; the 28 files are
preserved under `reports-quarantined/` (with the mismatch table), re-run one
variant per invocation, and `analyze_screen.py` now refuses any report whose
netlist sha does not match its own request (a mismatched code is reported
`netlist_sha_mismatch`, never silently accepted). The committed `analysis/`
is the sha-verified regeneration.

F2.50@tt, the least-bad candidate, was carried to the full 256-code x 3-corner
curve: `../20261122T0810Z-full-s22-83/` (same stamp family), and priced on the
rebuilt-layout extraction: `../20261122T0815Z-pricing/`.

## Reproduce (offline parts; fleet parts need the Spot batch backend)

```
python3 -I sim/row2-trimsize/fit_weights.py  --out <fresh>/fit
python3 -I sim/row2-trimsize/gen_screen.py   --fit <fresh>/fit/fit.json --out <fresh>/bench
python3 -I sim/row2-trimsize/run_set.py      --bench-dir <fresh>/bench --out-dir <fresh>   # batch fleet
python3 -I sim/row2-trimsize/analyze_screen.py --reports <fresh>/reports --bench <fresh>/bench --out <fresh>/analysis
python3 -I -m pytest -p no:cacheprovider sim/row2-trimsize/test_toolchain.py
```

Execution window (ledger.jsonl / batch receipts): 2026-11-22T05:51-07:03 UTC,
engine ngspice 47 on every report, open_pdks stamp
`f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7` (same stamp set as the #87 campaign).
