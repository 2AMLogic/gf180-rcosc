# sim/discipline - runtime-discipline trim math and SOF loop model (issue #79)

Behavioural model of a USB-SOF-style discipline loop acting on the ratified
8-bit trim interface, run against the **committed** frequency-vs-code data.
It answers one question for the reserved README row "Runtime-disciplined,
<= +/-0.25 %": can the 8-bit / 0.314 %/code interface reach and hold that band?
Verdict and rationale: [DR-0021](../../spec/decision-records/0021-runtime-discipline-trim-resolution-sof-loop-model.md).
The loop is a candidate reference design, not a ratified block; nothing here
relaxes a ratified row or reclassifies DR-0019 row 6 (it stays reserved).

```
sim/discipline/
  discipline_model.py     the model (stdlib only, python3 -I); writes a NEW results/<runid>/, refuses to overwrite
  results/20261009T010000Z/
    summary.md            all tables (generated)
    results.csv           one row per (experiment, plant, policy, SOF jitter)
    trim_math.csv         static best-code / step / saturation per plant x T x V
    plant_checks.csv      model-vs-measured validation of the plant construction
    trace_ss_ext_cold_start.csv   frame-by-frame code/error, post-layout ss, all four policies
    manifest.json         inputs' sha256, git HEAD, seed, all loop parameters
```

Run: `python3 -I sim/discipline/discipline_model.py` (about 30 s, one core, no
ngspice, no network). Results are append-only: a new run gets a new run id.

## Plant (cited, not regenerated)

| input | what it supplies |
|---|---|
| `sim/pvt/results/20260923T030125Z/results.csv` (DR-0017, post-#60 schematic; ngspice-46) | the dense tt/27 C/3.3 V `trim_curve` (24 codes, 0x00..0xFF); `pretrim` (0x80) and `posttrim_spec` (0xA3) for all 63 process/T/V points; per-corner calibration codes |
| `sim/pvt-postlayout/results/20260923T152954Z/{results,guardrails}.csv` (DR-0018, extracted netlist) | f(0x00), f(0xFF), calibration code for tt/ff/ss at 27 C/3.3 V; f(0xA3) over 3 T x 3 V x {tt,ff,ss} |

The issue named `sim/pvt/results/20260905T211140Z/`; that campaign predates the
DR-0006..0017 respins (17.7-20 MHz at tt, f(0x80) = 20.2 MHz) and is not the
current design, so the latest committed run of each kind is used instead.

Construction, `f(code,T,V) = F_p(code) * g_p(T,V)`:

- `F_p`: piecewise-linear interpolation of ln f over the 24 committed tt codes,
  then a two-point affine map in ln f per process (schematic: the corner's own
  f(0x80) and f(0xA3); post-layout: the corner's f(0x00) and f(0xFF)).
- `g_p(T,V)`: bilinear over the 3x3 grid, f(0xA3,p,T,V)/f(0xA3,p,27 C,3.3 V).
- Validation against held-out measured points (`plant_checks.csv`): model f at
  the measured per-corner calibration code is within -0.57..+0.28 % (schematic)
  and +0.30..+2.62 % (post-layout) of the measured value; f(0xA3) post-layout
  within +1.18..+1.62 % (exact table in summary.md). The temperature/
  supply factor is assumed code-independent; comparing the 0x80 and 0xA3
  grids bounds that assumption at 0.95-1.24 % (max, over the 63 points).
  A calibration-anchored 3-point post-layout fit was tried and rejected (it
  made the independent 0xA3 check worse: ss -6.2 % vs +1.2 %).

Model limits that matter for the verdict: the committed curve has 24 codes, so
the **sub-16-code structure of the real curve is not in the data**. Steps
inside a 16-code span are the linear interpolation (the per-segment mean), and
the 0x?F->0x?0 carry dips are known only at the four boundaries that were
sampled (0x7F->0x80, 0xBF->0xC0, 0xDF->0xE0, 0xEF->0xF0). Real
code-to-code steps are therefore at least as irregular as modelled, not less.
The model error in f (up to 2.6 % post-layout) is several codes of position,
so quoted codes (e.g. 0xD5 vs the measured 0xD9) are model values.

## Trim math, worked

Ratified: +/-40 % over 255 steps = 0.314 %/code, half-LSB 0.157 %
(DR-0003 Row 2). Row to check: +/-0.25 %.

1. **Required resolution.** A single static code can place f anywhere in a
   cell of width `step`; the worst-case residual is `step/2`. Staying within
   +/-0.25 % for every target position requires `step <= 0.50 %/code`. The
   ratified 0.314 %/code passes this (0.157 % < 0.25 %) - **on paper**.
2. **Realized step, from the committed curve.** The curve is not a +/-40 %
   linear range: f(0xFF)/f(0x00) = 3.16x at tt (26.3 -> 83.2 MHz), i.e. a
   geometric-mean step of 0.447 %/code (schematic, tt), 0.42 % (post-layout tt),
   0.418 % (post-layout ss), with local steps up to 0.80-0.83 % (schematic)
   and 0.72-0.74 % (post-layout). Every one of the ten
   plants has a mean step 1.3-1.5x the ratified 0.314 %, and the worst local step
   is 2.3-2.6x. Half of the worst local step is 0.36-0.42 %, above the 0.25 % band.
3. **Non-monotone carries.** The measured curve drops at four code boundaries
   by 1.4-6.1 % (127->128: 42.55 -> 39.95 MHz; 191->192; 223->224; 239->240).
   The "min step" column of the static table (-5.3 .. -6.3 %) is this. The
   interface is not monotone, which the 0.314 %/code figure and the
   half-LSB claim both assume. The 48 MHz target is crossed more than once at
   some post-layout T/V points (up to 3 crossings, `trim_math.csv`).
4. **Best static code vs +/-0.25 %.** Over the 90 plant x T x V points the best
   single code is within +/-0.25 % at 75 points (83 %); the worst best-code
   error is 0.387 % (schematic ss at the T/V extreme where the target falls in
   the coarsest cell). A static code therefore cannot guarantee the band.
5. **Counting resolution of the measurement is not the limit.** One SOF is
   1 ms = 48 000 counts of the nominal clock; one count = 0.0021 %, 120x finer
   than the band. SOF jitter (assumed +/-500 ns on each SOF arrival, a
   parameter not a cited figure) is +/-0.05 % of a frame per edge, up to
   0.1 % per count difference.
6. **Hence two readings of "+/-0.25 %".** (a) *instantaneous*: every frame's
   frequency inside the band; the interface cannot do that (item 4, and the
   dither in the table below). (b) *average over a window* (the SOF-disciplined
   claim, comparable to a long-term tolerance): reachable by dithering the
   code with a fractional accumulator. Which reading the row means is a
   spec-owner decision; this record does not choose the lenient one silently.

## Controller policies (all update once per 1 ms SOF)

| policy | rule |
|---|---|
| `bangbang` | code -= sign(count error), every frame |
| `deadband` | step 1 code only if |error| > 75 counts (0.157 %, the ratified half-LSB) |
| `avg32` | average count error over 32 frames, then deadband step |
| `fracdither` | integrator, gain 0.8 code per % per frame, 4 fractional code bits, first-order sigma-delta onto the 8-bit code; clamped at 0x00/0xFF (no wind-up). Needs 4 extra accumulator bits, no analogue change |

Cold start: code 0x80 (mid-scale; an assumption), 27 C, 3.3 V. Temperature
ramps: -40 -> +85 C at 1 C/s and 20 C/s at 3.3 V. Supply steps 3.3 -> 3.0 ->
3.6 -> 3.3 V at 27 C and at -40 C. 10 plants (7 schematic corners, tt/ff/ss
post-layout), SOF jitter 0 and +/-500 ns, fixed seed 20261009.

## Results (run 20261009T010000Z; all numbers from `results.csv`, jitter 0 unless stated)

Steady state at 27 C / 3.3 V (last 2000 of 8000 frames), 10 plants:

| policy | instantaneous |error| max, range over plants | plants inside +/-0.25 % instantaneous | 16-frame mean |error| max | 64-frame mean |error| max |
|---|---|---|---|---|
| bangbang | 0.302 - 0.593 % | 0 / 10 | 0.254 % | 0.254 % |
| deadband | 0.038 - 0.535 % | 6 / 10 | 0.166 % | 0.166 % |
| avg32 | 0.038 - 0.535 % | 6 / 10 | 0.535 % | 0.166 % |
| fracdither | 0.302 - 0.937 % | 0 / 10 | 0.060 % | 0.015 % |

The four plants where `deadband` does not settle to one code (sf/sch, rc_s/sch,
tt/ext, ff/ext) are exactly those whose two straddling codes are both
outside +/-0.25 % (e.g. tt/ext -0.253 % / +0.471 %): the code-to-code step there
is 0.72 %.

Lock time from 0x80 (frames = ms; first frame after which the quantity stays in
+/-0.25 % for 256 frames):

| policy | lock time on 16 ms mean | lock time instantaneous |
|---|---|---|
| bangbang | 28 - 114 ms (never at tt/sch: 0.253 %, marginal) | never |
| deadband | 30 - 113 ms | 32 - 117 ms where it settles (6/10), else never |
| avg32 | 1019 - 3731 ms (never where deadband never) | same |
| fracdither | 5 - 8 ms | never (inst +/-0.3..0.9 %) |

Lock time is the code distance divided by 1 code/ms for the 1-code policies
(post-layout ss: 128 -> 0xF5, 117 ms); `avg32` is 32x slower. Convergence of
`fracdither` assumes the plant slope is inside the integrator's stable range
(0.8 x slope < 2, slope up to 0.83 %/code observed).

Temperature ramp -40 -> +85 C at 1 C/s, 3.3 V (125 000 frames): drift is
about 1e-7 %/ms (0.12 %/K x 1 K/s), negligible against one code (0.4-0.9 %); the loop never
loses lock (no rail contact at 3.3 V, any plant). Instantaneous error is the
quantization of the plant, not the drift:

| policy | inst |error| max, range over plants | 16-frame mean max | 64-frame mean max | worst in-band fraction (inst) |
|---|---|---|---|---|
| bangbang | 0.415 - 0.812 % | 0.404 % | 0.402 % | 0.340 |
| deadband | 0.258 - 0.623 % | 0.232 % | 0.230 % | 0.551 |
| avg32 | 0.262 - 0.626 % | 0.625 % | 0.286 % | 0.549 |
| fracdither | 0.479 - 1.077 % | 0.086 % | 0.033 % | 0.441 |

The 20 C/s ramp gives the same picture (`deadband` 64-frame mean max 0.185 %,
`fracdither` 0.037 %). With +/-500 ns SOF jitter the 64-frame means stay
at 0.192 % (`deadband`), 0.285 % (`avg32`) and 0.032 % (`fracdither`) over the
cold-start and 1 C/s experiments.

## DR-0018 `ss` / 0xF7 rail case (post-layout ss)

- Calibration code 0xF7, f(0xFF) = 50.28 MHz, headroom +4.7 % at 27 C/3.3 V
  (DR-0018). In this model the required code is 0xF5 at 27 C/3.3 V (model
  position error, see above), 0xFC at -40 C/3.3 V, 0xFF-saturated at
  **-40 C / 3.0 V**: f(0xFF) is 0.343 % below 48 MHz there - the single
  T/V point of the 90 where the interface runs out of range. The next-tightest
  point (-40 C / 3.3 V) has 1.5 % of headroom; at the 27 C corner the model
  puts it at 4.7 %.
- Behaviour with the loop: it holds 0xFF, the error equals the static -0.343 %
  (outside +/-0.25 %), the integrator is clamped (`fracdither`) so there is no
  wind-up, and after the supply returns the loop leaves the rail in 2 frames
  (`bangbang`, `fracdither`; 4 frames `deadband`; 163 frames `avg32`).
  The saturated point is a **range** failure, not a resolution failure: it
  needs a further 0.34 % of pull (about one more code at the local step), plus
  whatever the model error (up to +/-2.6 % in f) and mismatch (DR-0019 S1)
  consume. The sign of that margin is within the model's own uncertainty and
  must be re-checked with the extracted netlist before any rail claim is made.

## Not done / not claimed

- No RTL, area, power or analogue-loop claim; the SOF reference is ideal apart
  from the jitter parameter. No USB-host jitter figure is cited (not verified).
- No mismatch (trim-DAC element error, DR-0019 S1) and no sub-16-code curve
  structure: both would add irregularity and can only worsen resolution.
- No post-layout 3x3 grid beyond tt/ff/ss; fs/sf/rc_f/rc_s post-layout absent.
- A successive-approximation acquisition (binary search over frames) was not
  modelled; the non-monotone carries make it unsafe without a monotone code
  mapping, which is a design question for the discipline stage, not this model.
