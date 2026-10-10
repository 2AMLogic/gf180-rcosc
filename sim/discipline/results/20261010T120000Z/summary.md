# SOF reference-loss model run 20261010T120000Z

BEHAVIOURAL SIMULATION ONLY (issue #128). Extends the DR-0021 candidate discipline loop with a reference-availability schedule and the `freeze_reacquire` policy. Nothing here is a hardware, USB-compliance, or ratified-spec claim; the reserved runtime-disciplined row is unchanged. Plant = the interpolated 24-code model of DR-0021 (see its uncertainty; sub-16-code structure absent). Outage lengths (1 / 16 / 256 lost SOFs) and the freeze behaviour are engineering assumptions.

Policy: lost SOF -> observation not delivered, trim code and controller state frozen; the first SOF back is a baseline only; updates resume at the next one-frame interval. No 'locked' flag is carried across an outage. True frequency during the outage is reported separately from observed count error (none exists while the reference is absent). Per-frame (`inst`) and 16-frame-mean (`avg16`) readings are separate; neither is chosen as the spec interpretation. Status: `recovered`; `plant_unreachable` (no code / dither can reach the band at the final condition); `controller_not_recovered` (reachable, but the loop did not hold the band for 256 frames). Each row also carries the no-loss baseline of the same profile.

No-loss regression against committed 20261009T010000Z cold-start values: {'compared_values': 120, 'max_abs_diff_pct': 4.6663184399553526e-05, 'committed_precision_pct': 5e-05}


## constant_27C_3p3V

Aggregated over the 10 plants; `worst` = maximum. Frames = ms.

| lost SOFs | policy | holdover true drift absmax % | holdover true |err| max % | excursion max % (baseline max) | rail contact (baseline) | resume frames | avg16: recovered / plant_unreach / ctl_fail (baseline recovered) | avg16 reacq worst | inst: recovered / plant_unreach / ctl_fail | inst reacq worst |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | bangbang | 0.000 | 0.545 | 0.593 (0.593) | 0 (0) of 10 | 1 | 9 / 0 / 1 (9) | never | 0 / 1 / 9 | never |
| 1 | deadband | 0.000 | 0.536 | 0.536 (0.536) | 0 (0) of 10 | 1 | 10 / 0 / 0 (10) | 0 | 6 / 1 / 3 | never |
| 1 | avg32 | 0.000 | 0.536 | 0.536 (0.536) | 0 (0) of 10 | 1 | 6 / 0 / 4 (6) | never | 6 / 1 / 3 | never |
| 1 | fracdither | 0.000 | 0.630 | 0.937 (0.937) | 0 (0) of 10 | 1 | 10 / 0 / 0 (10) | 0 | 0 / 1 / 9 | never |
| 16 | bangbang | 0.000 | 0.545 | 0.593 (0.593) | 0 (0) of 10 | 1 | 9 / 0 / 1 (9) | never | 0 / 1 / 9 | never |
| 16 | deadband | 0.000 | 0.536 | 0.536 (0.536) | 0 (0) of 10 | 1 | 10 / 0 / 0 (10) | 14 | 6 / 1 / 3 | never |
| 16 | avg32 | 0.000 | 0.536 | 0.536 (0.536) | 0 (0) of 10 | 1 | 6 / 0 / 4 (6) | never | 6 / 1 / 3 | never |
| 16 | fracdither | 0.000 | 0.630 | 0.937 (0.937) | 0 (0) of 10 | 1 | 10 / 0 / 0 (10) | 10 | 0 / 1 / 9 | never |
| 256 | bangbang | 0.000 | 0.545 | 0.593 (0.593) | 0 (0) of 10 | 1 | 9 / 0 / 1 (9) | never | 0 / 1 / 9 | never |
| 256 | deadband | 0.000 | 0.536 | 0.536 (0.536) | 0 (0) of 10 | 1 | 10 / 0 / 0 (10) | 14 | 6 / 1 / 3 | never |
| 256 | avg32 | 0.000 | 0.536 | 0.536 (0.536) | 0 (0) of 10 | 1 | 6 / 0 / 4 (6) | never | 6 / 1 / 3 | never |
| 256 | fracdither | 0.000 | 0.630 | 0.972 (0.937) | 0 (0) of 10 | 1 | 10 / 0 / 0 (10) | 10 | 0 / 1 / 9 | never |

## ramp_1C_per_s

Aggregated over the 10 plants; `worst` = maximum. Frames = ms.

| lost SOFs | policy | holdover true drift absmax % | holdover true |err| max % | excursion max % (baseline max) | rail contact (baseline) | resume frames | avg16: recovered / plant_unreach / ctl_fail (baseline recovered) | avg16 reacq worst | inst: recovered / plant_unreach / ctl_fail | inst reacq worst |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | bangbang | 0.000 | 0.529 | 0.677 (0.677) | 0 (0) of 10 | 1 | 10 / 0 / 0 (10) | 0 | 2 / 1 / 7 | never |
| 1 | deadband | 0.000 | 0.494 | 0.583 (0.583) | 0 (0) of 10 | 1 | 10 / 0 / 0 (10) | 0 | 9 / 0 / 1 | never |
| 1 | avg32 | 0.000 | 0.453 | 0.585 (0.585) | 0 (0) of 10 | 1 | 9 / 0 / 1 (9) | never | 9 / 0 / 1 | never |
| 1 | fracdither | 0.000 | 0.529 | 0.997 (0.986) | 0 (0) of 10 | 1 | 10 / 0 / 0 (10) | 0 | 2 / 1 / 7 | never |
| 16 | bangbang | 0.002 | 0.529 | 0.677 (0.678) | 0 (0) of 10 | 1 | 10 / 0 / 0 (10) | 14 | 2 / 1 / 7 | never |
| 16 | deadband | 0.002 | 0.494 | 0.583 (0.583) | 0 (0) of 10 | 1 | 10 / 0 / 0 (10) | 12 | 9 / 0 / 1 | never |
| 16 | avg32 | 0.002 | 0.453 | 0.586 (0.585) | 0 (0) of 10 | 1 | 9 / 0 / 1 (9) | never | 9 / 0 / 1 | never |
| 16 | fracdither | 0.002 | 0.529 | 0.987 (0.986) | 0 (0) of 10 | 1 | 10 / 0 / 0 (10) | 10 | 2 / 1 / 7 | never |
| 256 | bangbang | 0.025 | 0.529 | 0.691 (0.691) | 0 (0) of 10 | 1 | 10 / 0 / 0 (10) | 12 | 2 / 1 / 7 | never |
| 256 | deadband | 0.025 | 0.494 | 0.583 (0.583) | 0 (0) of 10 | 1 | 10 / 0 / 0 (10) | 12 | 9 / 0 / 1 | never |
| 256 | avg32 | 0.025 | 0.453 | 0.585 (0.585) | 0 (0) of 10 | 1 | 9 / 0 / 1 (9) | never | 9 / 0 / 1 | never |
| 256 | fracdither | 0.025 | 0.529 | 0.983 (0.986) | 0 (0) of 10 | 1 | 10 / 0 / 0 (10) | 10 | 2 / 1 / 7 | never |

## ramp_20C_per_s

Aggregated over the 10 plants; `worst` = maximum. Frames = ms.

| lost SOFs | policy | holdover true drift absmax % | holdover true |err| max % | excursion max % (baseline max) | rail contact (baseline) | resume frames | avg16: recovered / plant_unreach / ctl_fail (baseline recovered) | avg16 reacq worst | inst: recovered / plant_unreach / ctl_fail | inst reacq worst |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | bangbang | 0.004 | 0.529 | 0.741 (0.741) | 0 (0) of 10 | 1 | 10 / 0 / 0 (10) | 2149 | 2 / 1 / 7 | never |
| 1 | deadband | 0.004 | 0.494 | 0.583 (0.583) | 0 (0) of 10 | 1 | 10 / 0 / 0 (10) | 0 | 10 / 0 / 0 | 3123 |
| 1 | avg32 | 0.004 | 0.494 | 0.610 (0.608) | 0 (0) of 10 | 1 | 10 / 0 / 0 (10) | 3152 | 10 / 0 / 0 | 3148 |
| 1 | fracdither | 0.004 | 0.529 | 0.974 (0.952) | 0 (0) of 10 | 1 | 10 / 0 / 0 (10) | 0 | 2 / 1 / 7 | never |
| 16 | bangbang | 0.033 | 0.529 | 0.741 (0.741) | 0 (0) of 10 | 1 | 10 / 0 / 0 (10) | 867 | 2 / 1 / 7 | never |
| 16 | deadband | 0.033 | 0.494 | 0.584 (0.583) | 0 (0) of 10 | 1 | 10 / 0 / 0 (10) | 10 | 9 / 0 / 1 | never |
| 16 | avg32 | 0.033 | 0.507 | 0.623 (0.608) | 0 (0) of 10 | 1 | 10 / 0 / 0 (10) | 3086 | 10 / 0 / 0 | 3084 |
| 16 | fracdither | 0.033 | 0.529 | 0.987 (0.952) | 0 (0) of 10 | 1 | 10 / 0 / 0 (10) | 10 | 2 / 1 / 7 | never |
| 256 | bangbang | 0.509 | 0.984 | 0.984 (0.741) | 0 (0) of 10 | 1 | 10 / 0 / 0 (10) | 1383 | 2 / 1 / 7 | never |
| 256 | deadband | 0.506 | 0.570 | 0.583 (0.583) | 0 (0) of 10 | 1 | 10 / 0 / 0 (10) | 14 | 10 / 0 / 0 | 2868 |
| 256 | avg32 | 0.509 | 0.984 | 1.005 (0.608) | 0 (0) of 10 | 1 | 10 / 0 / 0 (10) | 2896 | 10 / 0 / 0 | 2892 |
| 256 | fracdither | 0.509 | 0.984 | 1.003 (0.952) | 0 (0) of 10 | 1 | 10 / 0 / 0 (10) | 14 | 2 / 1 / 7 | never |

## vdd_step_+27C

Aggregated over the 10 plants; `worst` = maximum. Frames = ms.

| lost SOFs | policy | holdover true drift absmax % | holdover true |err| max % | excursion max % (baseline max) | rail contact (baseline) | resume frames | avg16: recovered / plant_unreach / ctl_fail (baseline recovered) | avg16 reacq worst | inst: recovered / plant_unreach / ctl_fail | inst reacq worst |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | bangbang | 1.761 | 1.628 | 1.628 (2.070) | 0 (0) of 10 | 1 | 7 / 0 / 3 (7) | never | 0 / 0 / 10 | never |
| 1 | deadband | 1.761 | 1.628 | 1.628 (1.628) | 0 (0) of 10 | 1 | 10 / 0 / 0 (10) | 17 | 7 / 0 / 3 | never |
| 1 | avg32 | 1.761 | 1.628 | 1.628 (1.628) | 0 (0) of 10 | 1 | 7 / 0 / 3 (7) | never | 7 / 0 / 3 | never |
| 1 | fracdither | 1.761 | 1.628 | 1.628 (1.630) | 0 (0) of 10 | 1 | 10 / 0 / 0 (10) | 17 | 0 / 0 / 10 | never |
| 16 | bangbang | 1.761 | 1.628 | 1.628 (2.070) | 0 (0) of 10 | 1 | 7 / 0 / 3 (7) | never | 0 / 0 / 10 | never |
| 16 | deadband | 1.761 | 1.628 | 1.628 (1.628) | 0 (0) of 10 | 1 | 10 / 0 / 0 (10) | 17 | 7 / 0 / 3 | never |
| 16 | avg32 | 1.761 | 1.628 | 1.628 (1.628) | 0 (0) of 10 | 1 | 7 / 0 / 3 (7) | never | 7 / 0 / 3 | never |
| 16 | fracdither | 1.761 | 1.628 | 1.628 (1.630) | 0 (0) of 10 | 1 | 10 / 0 / 0 (10) | 17 | 0 / 0 / 10 | never |
| 256 | bangbang | 1.761 | 1.628 | 1.628 (2.070) | 0 (0) of 10 | 1 | 7 / 0 / 3 (7) | never | 0 / 0 / 10 | never |
| 256 | deadband | 1.761 | 1.628 | 1.628 (1.628) | 0 (0) of 10 | 1 | 10 / 0 / 0 (10) | 17 | 7 / 0 / 3 | never |
| 256 | avg32 | 1.761 | 1.628 | 1.628 (1.628) | 0 (0) of 10 | 1 | 7 / 0 / 3 (7) | never | 7 / 0 / 3 | never |
| 256 | fracdither | 1.761 | 1.628 | 1.628 (1.630) | 0 (0) of 10 | 1 | 10 / 0 / 0 (10) | 17 | 0 / 0 / 10 | never |

## vdd_step_-40C

Aggregated over the 10 plants; `worst` = maximum. Frames = ms.

| lost SOFs | policy | holdover true drift absmax % | holdover true |err| max % | excursion max % (baseline max) | rail contact (baseline) | resume frames | avg16: recovered / plant_unreach / ctl_fail (baseline recovered) | avg16 reacq worst | inst: recovered / plant_unreach / ctl_fail | inst reacq worst |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | bangbang | 1.834 | 2.222 | 2.222 (2.052) | 1 (1) of 10 | 1 | 7 / 1 / 2 (7) | never | 0 / 3 / 7 | never |
| 1 | deadband | 1.834 | 2.121 | 2.121 (1.679) | 1 (1) of 10 | 1 | 9 / 1 / 0 (9) | never | 6 / 3 / 1 | never |
| 1 | avg32 | 1.834 | 2.121 | 2.121 (1.679) | 1 (1) of 10 | 1 | 6 / 1 / 3 (6) | never | 6 / 3 / 1 | never |
| 1 | fracdither | 1.834 | 2.222 | 2.222 (1.880) | 1 (1) of 10 | 1 | 9 / 1 / 0 (9) | never | 0 / 3 / 7 | never |
| 16 | bangbang | 1.834 | 2.222 | 2.222 (2.052) | 1 (1) of 10 | 1 | 7 / 1 / 2 (7) | never | 0 / 3 / 7 | never |
| 16 | deadband | 1.834 | 2.121 | 2.121 (1.679) | 1 (1) of 10 | 1 | 9 / 1 / 0 (9) | never | 6 / 3 / 1 | never |
| 16 | avg32 | 1.834 | 2.121 | 2.121 (1.679) | 1 (1) of 10 | 1 | 6 / 1 / 3 (6) | never | 6 / 3 / 1 | never |
| 16 | fracdither | 1.834 | 2.222 | 2.222 (1.880) | 1 (1) of 10 | 1 | 9 / 1 / 0 (9) | never | 0 / 3 / 7 | never |
| 256 | bangbang | 1.834 | 2.222 | 2.222 (2.052) | 1 (1) of 10 | 1 | 7 / 1 / 2 (7) | never | 0 / 3 / 7 | never |
| 256 | deadband | 1.834 | 2.121 | 2.121 (1.679) | 1 (1) of 10 | 1 | 9 / 1 / 0 (9) | never | 6 / 3 / 1 | never |
| 256 | avg32 | 1.834 | 2.121 | 2.121 (1.679) | 1 (1) of 10 | 1 | 6 / 1 / 3 (6) | never | 6 / 3 / 1 | never |
| 256 | fracdither | 1.834 | 2.222 | 2.222 (1.880) | 1 (1) of 10 | 1 | 9 / 1 / 0 (9) | never | 0 / 3 / 7 | never |

Per plant x policy x outage detail: `outage_results.csv`. Inputs, schedules, policy and limitations: `manifest.json`.

