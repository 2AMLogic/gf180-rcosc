# sim/row45-rerun - candidate-lever re-runs on a sim-only variant of the DR-0028 netlist (issue #317)

`variant.py` applies a candidate change to the extracted P3 netlist (`sim/cmph-fix/rcosc_top_p3_cmphfix.spice`) as text; the layout is
NOT re-extracted, so the variant carries the old wiring parasitics. Row 4 candidate: all 16 bank pass devices at 2x W (AS/AD/PS/PD
re-derived by the extractor's own rule). Append-only.

- `gen_calib_requests.py`: one request per (process, code) at 27 C / 3.3 V (`BASELINE=1` leaves the DUT unmodified).
  `results/20261112T090000Z-calib`, `results/20261112T091500Z-calib`: variant scans -> per-die codes **tt 171, ff 80, ss 218**
  (tt 171 is interpolated between the measured 170 / 172; the stage run reports its own 3.3 V / 27 C reference).
  `results/20261112T092500Z-calib-baseline-ends`: 0x00 / 0xFF endpoints of the unmodified DUT, for the trim-range comparison.
- `gen_stage_rerun.py` -> `results/20261112T094000Z-stage`: the 9-request stage re-run (same benches, `stage_attribution.py` unchanged).
  **Reading `stage_attribution.md` there:** the script prints its own constants "tt 165, ff 78, ss 212" in the header and the
  reference-point `code` column; the codes actually simulated are tt 171, ff 80, ss 218 (`tb_*.spice`).

Result and interpretation: `spec/decision-records/0034-*.md`.

Row 5 (issue #321): `variant.comparator_h_buffer` resizes the comparator-H output inverter (X$21 MBUFN, X$67 MBUFP);
`gen_screen.py OUTDIR [a|b]` writes the screening requests (ff median die, code 0x4E, 3.3 V / 27 C reference + 3.0 V at -40 / 85 C),
`screen_table.py RESULT_DIR` tabulates them. `results/20261112T100000Z-screen-cmph` (set a) and `results/20261112T101500Z-screen-cmph`
(set b): no variant helps; see `spec/decision-records/0035-*.md`.

First stage (issue #321, second increment): `variant.first_stage` (pair W / mirror-load L / tail factor) and `gen_screen.py OUTDIR c|d`.
`results/20261112T110000Z-screen-cmph-first` (set c) and `results/20261112T112000Z-screen-cmph-first` (set d), with `table.md`:
mirror-load L and tail current are the lever; see `spec/decision-records/0036-*.md`.
