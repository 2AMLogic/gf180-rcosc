# 0049: Row 2: dense 256-code trim analysis - the current bank misses the 0.314 %/code step and is non-monotonic at the four carries

- **Status**: proposed - extends [0021](0021-runtime-discipline-trim-resolution-sof-loop-model.md) (carry questions) and records the measurement #87 left uncommitted.
  Changes no ratified row, range, step or half-LSB ([0003](0003-pdk-sourced-process-spread-tcr-and-iq.md) untouched); sizes no bank change (that is #460).
- **Date**: 2026-11-20
- **Decided by**: Loom Builder (issue #459), pending operator ratification

## Context

T1 item 5 reads `check_failed` partly on row 2 (8-bit trim, +/-40 % range, 0.314 %/code). The range ends pass at the nominal corner; the step does not. #87 ran the dense 256-code frequency-vs-code campaign
(`sim/trim-dense/results/20261106T1115Z-campaign/`, 1536/1536 jobs, all `pass`, frozen manifest) but closed with the analysis uncommitted and no record. This record and
`sim/trim-dense/results/20261120T2330Z-verdict/` (`results.json`, `steps.csv`, `summary.md`, README with the exact command) close that gap. Every number below is read from those three files.

**What the data is.** Six curves (`ext`, `sch` x tt 27 C 3.3 V / ss -40 C 3.0 V / ff 85 C 3.6 V), 256 valid frequencies and 255 adjacent steps each, step = 100 (f[c+1]/f[c] - 1).

- `ext` = `sim/cmph-fix/rcosc_top_p3_cmphfix.spice`, the P3 extraction with L = 1 um (the control identified in [0044](0044-row5-comparator-h-mirror-load-l07-trim-range-and-running-iq-unchanged-on-the-extraction-of-the-rebuilt-layout.md)). The rebuilt layout uses L = 0.7 um; its endpoints were measured in 0044
  but its 255 individual steps were **not** measured, so these step and carry verdicts are for the frozen P3 extraction and are the input to the #460 sizing screen, not a statement about the rebuild.
- `sch` = `sim/pvt-postlayout/klt-pex/rcosc_top_schematic.spice`, the **pre-P3 trim sizing** (campaign `README.md`). `sch` verdicts apply to that named netlist only.

**Engine split, and why it is accepted.** The frozen manifest pins ngspice 46; the reports are `ext` 768 x 46, `sch_ff` 180 x 46 + 76 x 47 (the only internally split curve), `sch_ss` 256 x 47, `sch_tt` 256 x 47.
`analyze.py` refuses this by default. #378 (`results/20261115T160955Z-engine-ab/comparison.json`, sha256 `cfdeb1f5...d6e3`) paired 47 codes over `ext_tt`, `ext_ss` and `sch_ff`: max |delta| 0.1328 % = 0.85 x half-LSB (0.156863 %), 0/47 over, and #378 records that no escalation or successor campaign is justified.
The new `--engine-ab` option re-derives every pair, cross-checks each pair's frequency against the campaign report for that code and fails on any pair over the half-LSB; the verdict run passes it (47 pairs, 0 over). Not sampled by the A/B: `ext_ff`, `sch_ss`, `sch_tt`
(all single-engine, so unaffected by a mix, but their cross-version bound rests on the sampled curves).

**PDK.** All 1536 reports carry one stamp, `open_pdks f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7` (`.environment.remote.worker_environment.pdk.stamp_text`), and one `models_lib_sha256` `f6f4a96e18fc5ad11270ad3451aaecc7ac37fc81eb61e15b0d7d94c7bc594a24`.
The stamp is uniform campaign-wide, not only on newly run jobs (correcting `SLICE-46.md`, which gives a different JSON path and implies new-jobs-only; `SLICE-47.md` is also corrected on three points: endpoint-span multiples are 2.0-2.8x not 2.0-2.7x;
the append-only check is the two-argument `sim/check-append-only.sh <base> HEAD`; the ledger is append-ordered with one discontinuity, not globally chronological). The frozen files are not edited.

## Evidence

Two different "mean step" statistics exist and both are given. **Endpoint span** = 100 (f[255]/f[0] - 1) / 255 (the analyzer's `mean_step_pct`; the same convention as the ratified 80 %/255).
**Arithmetic mean** = mean of the 255 per-code steps in `steps.csv` (the figure comparable to 0021). Ratified: 0.313725 %/code, half-LSB 0.156863 %.

| curve | f[0x00] MHz | f[0xFF] MHz | 0x00 <= 28.8 | 0xFF >= 67.2 | endpoint-span step (x nominal) | arithmetic-mean step (x nominal) | worst positive step | steps outside nominal +/- half-LSB | non-positive steps |
|---|---|---|---|---|---|---|---|---|---|
| ext tt | 28.652 | 76.419 | yes | yes | 0.6538 (2.08) | 0.3889 (1.24) | +1.064 at 0xF9 | 119 | 5 |
| ext ss | 21.319 | 58.719 | yes | **no** | 0.6880 (2.19) | 0.4029 (1.28) | +1.094 at 0xF5 | 133 | 8 |
| ext ff | 39.610 | 103.388 | **no** | yes | 0.6314 (2.01) | 0.3799 (1.21) | +1.274 at 0x9F | 95 | 5 |
| sch tt (pre-P3) | 26.639 | 85.137 | yes | yes | 0.8612 (2.74) | 0.4585 (1.46) | +2.443 at 0xFB | 148 | 10 |
| sch ss (pre-P3) | 19.374 | 63.267 | yes | **no** | 0.8884 (2.83) | 0.4673 (1.49) | +2.385 at 0xFB | 159 | 10 |
| sch ff (pre-P3) | 37.677 | 116.053 | **no** | yes | 0.8158 (2.60) | 0.4438 (1.41) | +2.253 at 0xFB | 125 | 12 |

Range ends are assessed per curve against 28.8 / 67.2 MHz (48 MHz -/+ 40 %). Each curve is its own corner: ss tops out below 67.2 MHz and ff starts above 28.8 MHz, so the end limits are met only on the tt curves. This is a per-corner reading of the dense data,
not the item-5 grading (unchanged).

**Every non-positive step (code transition, step %), per curve.** A frequency decrease, never merely a small step.

| curve | non-positive transitions |
|---|---|
| ext tt (5) | 0x7F->0x80 -9.399; 0xBF->0xC0 -5.599; 0xDF->0xE0 -3.640; 0xEF->0xF0 -2.644; 0xF7->0xF8 -0.781 |
| ext ss (8) | 0x3F->0x40 -0.463; 0x7F->0x80 -10.483; 0x9F->0xA0 -0.325; 0xBF->0xC0 -7.128; 0xCF->0xD0 -0.057; 0xDF->0xE0 -4.337; 0xEF->0xF0 -3.168; 0xF7->0xF8 -1.212 |
| ext ff (5) | 0x7F->0x80 -8.693; 0xBF->0xC0 -4.984; 0xDF->0xE0 -3.346; 0xEF->0xF0 -1.953; 0xF7->0xF8 -0.322 |
| sch tt (10) | the four carries; 0xF0->0xF1 -0.139; 0xF4->0xF5 -0.190; 0xF8->0xF9 -0.824; 0xFA->0xFB -0.855; 0xFC->0xFD -0.998; 0xFE->0xFF -0.995 |
| sch ss (10) | 0x3F->0x40 -0.224; the four carries; 0xF6->0xF7 -0.070; 0xF8->0xF9 -0.647; 0xFA->0xFB -0.693; 0xFC->0xFD -1.116; 0xFE->0xFF -1.027 |
| sch ff (12) | the four carries; 0xE8->0xE9 -0.007; 0xF2->0xF3 -0.161; 0xF4->0xF5 -0.133; 0xF6->0xF7 -0.084; 0xF8->0xF9 -0.653; 0xFA->0xFB -0.346; 0xFC->0xFD -0.674; 0xFE->0xFF -0.590 |

**The four 0021 carries: confirmed, on all six curves.** Each is a frequency decrease (step %):

| carry | ext tt | ext ss | ext ff | sch tt | sch ss | sch ff |
|---|---|---|---|---|---|---|
| 0x7F->0x80 | -9.399 | -10.483 | -8.693 | -6.176 | -6.722 | -5.759 |
| 0xBF->0xC0 | -5.599 | -7.128 | -4.984 | -2.928 | -3.913 | -2.668 |
| 0xDF->0xE0 | -3.640 | -4.337 | -3.346 | -1.556 | -1.698 | -1.542 |
| 0xEF->0xF0 | -2.644 | -3.168 | -1.953 | -0.418 | -0.835 | -0.177 |

The worst, 0x7F->0x80 on `ext ss`, is -10.483 % (34.4 LSB of deviation from nominal); even the smallest (`sch ff` 0xEF->0xF0, -0.177 %) is a frequency decrease. Beyond the carries, the extracted curves hold 1, 4 and 1 further non-positive steps (tt, ss, ff),
and the pre-P3 curves 6, 6 and 8: listing only the carries would omit measured failures.

## Decision

Recorded for the row-2 design iteration; nothing in the spec changes.

1. **Row 2 step size is missed by the current bank.** On the P3 extraction the endpoint-span step is 2.01-2.19 x the ratified 0.3137 %/code and the arithmetic mean of per-code steps is 1.21-1.28 x; 95-133 of 255 steps lie outside nominal +/- half-LSB per curve.
   The range ends are a separate question and are assessed per curve above; the step is what the bank misses.
2. **Row 2 monotonicity is missed at the four carries on every curve** (table above), by 1.95-10.5 % of frequency per carry on `ext`, plus 1 to 4 further non-positive steps per extracted curve (0xF7->0xF8 on all three; 0x3F->0x40, 0x9F->0xA0, 0xCF->0xD0 on `ext ss`).
3. **The 0.7 um rebuild is not covered** by these step verdicts (only its endpoints, per 0044), and `sch` is the pre-P3 sizing. The sizing screen (#460) must take the `ext` figures as the baseline to beat.
4. This record does **not** adopt "record the measured step as the design's resolution" (ROADMAP option) and does not size a bank change. The ratified step, range and half-LSB are unchanged.

## Verification

- `python3 -I -m pytest -q sim/trim-dense/test_harness.py sim/trim-dense/test_compare_engine.py`; accept, refuse-without-A/B, refuse-over-half-LSB and provenance-failure-with-valid-A/B cases are fixtures in `test_harness.py`.
- Reproduction (README of the verdict directory) re-runs byte-identically from the committed reports.
- `signoff/signoff-report.json` statuses are unchanged; no design, netlist or layout file changes.
