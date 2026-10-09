# 0021: Runtime-discipline row - the 8-bit / 0.314 %/code interface does not meet +/-0.25 % per frame; it meets it only as a windowed average with a fractional-code dither

- **Status**: proposed (evidence record; the ratified spec is **not** changed)
- **Date**: 2026-10-09
- **Decided by**: Builder agent, issue #79 (needs human ratification of how "+/-0.25 %" is read)

## Context

[0004](0004-no-active-tc-compensation-runtime-discipline.md) puts the whole closure of the free-running gap (+8.8 % / -10.8 %, README target table) onto the reserved runtime-discipline row (<= +/-0.25 %, USB 2.0 `TFDRATE`), and `CLAUDE.md` requires trim math for every accuracy claim. That row was "reserved, not designed" with no evidence that the ratified trim interface (8 bit, 0.314 %/code, half-LSB +/-0.157 %, DR-0003 Row 2) can reach it. Issue #79 adds a behavioural SOF-loop model, `sim/discipline/`, run against the committed frequency-vs-code data (DR-0017 schematic campaign `sim/pvt/results/20260923T030125Z/`, DR-0018 post-layout run `sim/pvt-postlayout/results/20260923T152954Z/`; not regenerated). Full method, validation and tables: `sim/discipline/README.md`, run `sim/discipline/results/20261009T010000Z/`.

## Decision

Nothing in the ratified spec is changed or relaxed, and DR-0019 row 6 stays "reserved" (a discipline loop has not been designed; this is a candidate model). The finding is recorded as follows.

1. **The ratified 0.314 %/code is not what the realized trim curve delivers.** Realized geometric-mean step is 0.41-0.47 %/code over the ten plants (1.3-1.5x the ratified figure), local steps reach 0.72-0.83 %/code (2.3-2.6x), and the curve has four non-monotone carries of -1.4 % to -6.1 % (0x7F->0x80, 0xBF->0xC0, 0xDF->0xE0, 0xEF->0xF0). Half of the worst local step (0.36-0.42 %) is above the 0.25 % band; the half-LSB +/-0.157 % claim does not hold per code on the committed data. (The sub-16-code structure of the curve is not in the committed data - 24 sampled codes - so real steps are at least this irregular.)
2. **Instantaneous +/-0.25 % per 1 ms frame is not met.** The best static code is outside +/-0.25 % at 15 of 90 plant x T x V points (worst 0.387 %). Under SOF loops on an 8-bit code the per-frame error stays at 0.30-0.59 % (bang-bang), 0.04-0.54 % (deadband; 6 of 10 plants settle to one code inside the band at 27 C/3.3 V, 4 do not) and 0.3-0.9 % with the dithering loop, and over a -40..+85 C ramp 0.26-1.08 % for every policy; no policy holds all ten plants inside the band instantaneously.
3. **A windowed average is met, with a fractional dither.** A loop with 4 extra fractional code bits and a first-order sigma-delta onto the 8-bit code holds the 16-frame mean within 0.06 % at 27 C/3.3 V and 0.086 % on a 1 C/s -40..+85 C ramp (64-frame mean 0.015 % / 0.033 %; 0.032 % with +/-500 ns SOF jitter), and locks in 5-8 ms from mid-scale. A deadband loop on the plain 8-bit code reaches 0.166 % (cold start, mean) / 0.232 % (ramp) but only by parking one code, so it relies on luck of the cell position. The dither needs digital accumulator bits only, no change to the trim DAC. Drift of a temperature ramp is negligible (about 1e-7 %/ms at 1 C/s), so the limit is quantization, not tracking.
4. **Lock time** from 0x80: 28-114 ms (bang-bang), 30-117 ms (deadband), 1.0-3.7 s (32-frame averaging, which also fails to hold the band where deadband does), 5-8 ms (fractional dither). One code per 1 ms frame is the speed limit of the 1-code policies.
5. **DR-0018 `ss`/0xF7 rail case.** Post-layout `ss` needs 0xF5 at 27 C/3.3 V in the model (0xF7 measured; model position error up to +/-2.6 % in f), 0xFC at -40 C/3.3 V, and saturates at **-40 C / 3.0 V**: f(0xFF) is 0.343 % below 48 MHz, the only saturated point of the 90. There the loop sits at 0xFF with a -0.343 % error (outside the band), the clamped integrator has no wind-up, and it leaves the rail in 2-4 frames when the supply returns. This is a range shortfall of about one code, within the model's own error and well inside what trim-DAC mismatch (DR-0019 S1) can consume; it must be re-measured on the extracted netlist before being relied on in either direction.

**Verdict.** The 8-bit / 0.314 %/code interface, as realized, does **not** suffice for +/-0.25 % per frame; it suffices only for a +/-0.25 % *windowed-average* reading (tens of ms), and only with an added fractional-code dither in the digital loop and with the `ss` rail margin confirmed. Which reading the ratified row means (per-frame vs long-term frequency, cf. `TFDRATE`) is a decision for a human spec owner; this record does not pick the lenient one.

## Alternatives considered

- **Relax the row to +/-0.5 % or reclassify DR-0019 row 6** - rejected; the task and `CLAUDE.md` forbid relaxing the ratified spec to fit a result, and the windowed reading may already satisfy the row.
- **Report only the favourable windowed result** - rejected; the per-frame failure and the non-monotone carries are the harder facts and are reported first.
- **Regenerate the plant with an analogue sweep** - rejected: the committed data is the stated plant; a denser 256-code sweep would sharpen the sub-16-code structure but is a follow-up, not needed for the verdict's sign.
- **Use the originally named `20260905T211140Z` campaign** - rejected: it predates the DR-0006..DR-0017 respins and is not the current design (17.7-20 MHz at tt).

## Consequences

- Follow-ups worth filing: (a) a dense 256-code freq-vs-code sweep (schematic and extracted) to replace the 24-code interpolation; (b) a trim-bank question - the four non-monotone carries and the 1.3-1.5x step excess are a trim-bank property (cf. DR-0014/0015) that the half-LSB claim should be re-derived from; (c) the `ss` extracted rail margin at -40 C/3.0 V on the extracted netlist.
- If the row is read per-frame, no digital policy can meet it without a finer trim DAC (about 0.2 %/code or less, monotone) - a design change, not made here.
- Not covered: mismatch (DR-0019 S1), RTL/area, real SOF-jitter figures (+/-500 ns is an assumed parameter), successive-approximation acquisition over the non-monotone code map, post-layout fs/sf/rc_f/rc_s.
