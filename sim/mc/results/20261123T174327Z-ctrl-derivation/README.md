# Defect-magnitude derivation, issue #461 (rounds 1-5)

Zero-mismatch (deterministic) bench, 2 identical draws per request, batch backend, DUT
`sim/row45-rerun/results/20261112T200335Z-extract-l07/rcosc_top_p3_cmphfix.spice`
(sha256 01e06daeb8cf341189207770f982c32a4b288b3bca504614262353ef324d16a1).
Run before any pilot draw. Selection rules were fixed in `gen_campaign.py` (`DERIVE_GRID`) ahead of each round.

| round | run dir | candidate | outcome |
|---|---|---|---|
| 1 | 20261123T170809Z-ctrl-derivation | resistor vdd -> timing plate, 2e5 / 1e6 ohm (partial) | rejected: leak current scales with vdd like the charge current; row-4 span unchanged (ff s2 +1.21 at 2e5 vs +1.24 at 1e6) |
| 2 | 20261123T171911Z-ctrl-derivation | trim-bank scale 4 / 13 | **trimbank x4 selected**: every corner measurable, calibrated code on the rail (255), headroom 0, residual 17-48 %. x13: tt unmeasurable (code 0, no values), rejected |
| 3 | 20261123T173030Z-ctrl-derivation | diode-connected nfet plate -> vss (7e4, 1e5 ohm); reverse junction leak IS 3e-9 / 1e-8 / 3e-8 A | nfet-to-vss rejected for row 4 (tt s2 >= +0.66). **Junction IS = 1e-8 A selected for row 5** (s3 -21.4 / -34.0 / -15.9 at tt / ff / ss, all measurable). 3e-9 leaves ff s3 +0.56; 3e-8 is non-monotone (the 85 C error returns to +0.8..2.8) and is rejected |
| 4 | 20261123T173706Z-ctrl-derivation | vdd -> R -> diode-connected nfet -> plate, 1e5 / 3e5 / 1e6 ohm | none reaches the criterion (tt s2 +0.01 .. +0.34) |
| 5 | 20261123T174327Z-ctrl-derivation (this dir) | same, 5e4 / 7e4 ohm | none reaches s2 <= -1.0 at tt/ff. 5e4: ff trim range exhausted (code 0, headroom 0), rejected. **7e4 ohm carried as the row-4 control**: tt s2 -0.41, ff -0.04, ss -1.28; every corner inside the trim range (codes 112 / 16 / 191) |

**Honest miss on the pre-fixed rule.** No row-4 magnitude reached s2 <= -1.0 at tt and ff on the
deterministic draw. 7e4 ohm is the strongest candidate that keeps every corner inside the trim
range; it is not tuned further and the pilot reports whatever it detects. Where the control is not
detected the cell is reported not detected, with the bench limit stated.

Frozen for the pilot (before any pilot draw): N = 40 draws per corner, seed 20261008, trim-bank
scale 4.0 on X$91 (row 2), nfet leak 7e4 ohm vdd -> plate (row 4), junction IS 1e-8 A on the plate
(row 5), fine step `tran 50p`, detection = the pinned grader's per-measurement verdict.
