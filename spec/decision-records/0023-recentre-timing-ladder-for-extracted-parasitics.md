# 0023: Re-centre the timing ladder for extracted parasitics (R x0.70, MiM unchanged) and size the trim range from the extracted spread

- **Status**: proposed
- **Date**: 2026-10-11
- **Decided by**: Loom Builder (issue #66), pending operator ratification

## Context

Operator ruling 2026-10-08: the two missed ratified rows (post-trim accuracy,
trim range) are fixed in the design, not re-specified. The committed record
([`docs/chipalooza/challenge-5-proposal.md`](../../docs/chipalooza/challenge-5-proposal.md)
section 4, [0018](0018-comparator-pmos-respin-postlayout-pex-reverification.md),
[`sim/pvt-postlayout/results/20260923T152954Z/`](../../sim/pvt-postlayout/results/20260923T152954Z/summary.md))
shows the extracted oscillator 18.8 % to 36.9 % slow against the schematic at
the fixed trim code 0xA3, so the 48.000 MHz target sits at code 0xD9 (tt), 0xB3
(ff), 0xF7 (ss) with almost no code left at the slow process corner. This is the
first, bounded increment: attribute the slow-down, propose the re-centre, show it
with the layout parasitics held as lumped elements. No layout change, no ratified
row edited, no earlier `sim/` result edited. All evidence:
[`sim/recentre/`](../../sim/recentre/README.md).

### Where the slow-down comes from (AC 1)

Single-corner ablations of the committed extracted netlist (93 serial runs,
[`attribution.md`](../../sim/recentre/results/attribution/20261011T031527Z/attribution.md)).
Shares are of the period shift (ns), telescoping order, rows sum to 100 % with zero residual:

| contributor | worst ff/-40/3.6 (+9.58 ns) | best ss/-40/3.6 (+6.39 ns) | centre tt/27/3.3 (+7.08 ns) |
|---|---|---|---|
| timing node `vc` net-to-substrate C (MiM bottom plate side + routing + comparator-input/discharge wiring) and its coupling C | 28.3 % | 63.2 % | 45.0 % |
| trim-ladder node C (c1..c8: switch diffusion + routing; not anticipated by the issue) | 21.8 % | 49.3 % | 34.2 % |
| comparator / latch / clk node C (comparator delay) | 12.9 % | 29.5 % | 22.9 % |
| series R, all nets (resistor parasitics) | 2.3 % | 3.3 % | 2.7 % |
| bias / trim-control / rail C | 0.2 % | 1.0 % | 0.5 % |
| device geometry (layout AS/AD/PS/PD, W/L; includes the comparator-input junction caps) | 15.9 % | -11.1 % | 8.8 % |
| substrate-node modelling (extractor's 1 Tohm shunt vs hard ground) | 18.6 % | -35.1 % | -14.1 % |

Reading: the slow-down is capacitive (series R is <= 3.3 %), and two thirds of it
loads the RC itself (`vc` plus ladder nodes). The 56 fF on `vc` plus about 320 fF
of ladder-node C is comparable to the 217 fF MiM, which is why a schematic sizing
that budgeted none of it lands 25 % slow. The last row is not layout: how the
extractor holds the substrate node moves the frequency by -6 % to +7 % between
corners (filed: klayout-tools#3089). "Comparator input capacitance" cannot be
isolated as a parasitic; its layout-dependent junction part is inside the
device-geometry row.

## Decision

Proposed sizing **P3**: shorten all nine trim-ladder polysilicon resistors
(`RFIX`, `R0`..`R7`, width unchanged at 2 um) to **0.70x** their committed length,
and leave the timing MiM at **20 x 10 um (217.2 fF)**.

| element | committed length (um) | proposed (um) |
|---|---|---|
| RFIX | 17.198 | 12.039 |
| R0 | 0.7482 | 0.5237 |
| R1 | 1.4965 | 1.0476 |
| R2 | 2.993 | 2.0951 |
| R3 | 5.9859 | 4.1901 |
| R4 | 11.9719 | 8.3803 |
| R5 | 23.9438 | 16.7607 |
| R6 | 47.8876 | 33.5213 |
| R7 | 95.7751 | 67.0426 |

Bias-divider resistors, switches, comparators and the MiM are untouched.
Nominal ladder resistance at the 1 kohm/sq model value (500 ohm/um body, about
85 ohm per resistor of model head): 0xFF = RFIX = 6.1 kohm (was 8.7 kohm), 0x00 =
73.7 kohm (was 105 kohm).

**Trim range** (tt/27 C/3.3 V, extracted netlist, committed MiM-subckt form):

| substrate model | f(0x00) | f(0xFF) | vs ratified 28.800-67.200 MHz |
|---|---|---|---|
| A (as extracted) | 28.203 MHz | 73.524 MHz | +2.1 % below / +9.4 % above |
| B (vsubs hard-tied) | 27.705 MHz | 69.043 MHz | +4.0 % below / +2.7 % above |

(committed sizing: 20.804 / 60.553 MHz, 9.9 % short at the top.) Margin rule used:
both ends of the ratified +/-40 % window covered under both substrate models.
The binding corners of the 0xA3 record also fit: ss/-40 C/3.0 V reaches 57.7 MHz
(A) / 50.4 MHz (B, +5.0 % over 48) at 0xFF; ff/85 C/3.0 V is 40.0 / 38.5 MHz at 0x00.

**Calibration codes and LSB** (27 C/3.3 V, target 48.000 MHz, model A; B in brackets):

| process | code | f (MHz) | error | LSB at the code |
|---|---|---|---|---|
| tt | 0xA9 (0xAF) | 48.048 (47.940) | +0.10 % (-0.12 %) | 0.50 % (0.30 %) per code |
| ff | 0x59 (0x59) | 48.081 (48.033) | +0.17 % (+0.07 %) | 0.33 % (0.34 %) |
| ss | 0xD7 (0xE7) | 48.124 (48.119) | +0.26 % (+0.25 %) | 0.69 % (0.36 %) |

(committed sizing, tt: 0xD9, LSB 0.87 %/code.) The codes sit at 0x59..0xD7: 40 codes of headroom to 0xFF at ss (24 under B) and 89 codes to
0x00 at ff, versus 0xD9..0xF7 (8 codes of headroom at ss) before.

**Predicted post-trim accuracy** (P3, model A, one trim code per process):

* At the calibration point: |error| <= 0.26 % measured at tt/ff/ss, bounded by half
  the worst LSB (0.35 %). That is inside the ratified +/-1.1 % with 4x margin.
* Across temperature and supply (six extreme probes, not the 27-point grid): tt
  -3.76 % / +2.80 %, ss -3.21 % / +2.84 %, **ff -9.41 % / +8.16 %** (ff/-40 C/3.6 V and
  ff/85 C/3.0 V) against 48 MHz. Against the ratified +8 % / -9 % this misses at ff by
  0.41 and 0.16 points. Under model B the same probes give at worst -6.94 % / +5.17 %
  (ss), all inside.

**Cost** (against the committed sizing, extracted netlist, tt/27 C/3.3 V):

* Area: ladder resistor drawn body -124.8 um^2 (208.0 -> 145.6 um of length x 2 um);
  MiM 0. The effect on the trim-bank bounding box (428 x 54 um) is for the respin to
  measure.
* Running current (mean `i(VDD)` over the frequency window, not the `sim/iq` metric of
  ratified row 9): at 48 MHz calibration 335.3 -> 327.0 uA (-8.3 uA, -2.5 %); at the
  fast end (0xFF) 414.7 -> 466.4 uA (+51.7 uA, +12.5 %) because the end code is faster.
  ff/27 C/3.3 V at its calibration code: 415.0 uA. The 63-point Iq grid was not re-run;
  its existing off-reference exceedance ([0011](0011-iq-pvt-corner-factorial-row-4-exceeds-off-reference.md))
  is not changed by this record in either direction as far as shown.

## Is +/-1.1 % reachable with this topology?

Yes, as the calibration-point residual; no, as an in-field accuracy; and the
re-centre does not make the ratified LSB row true.

* **Calibration point**: reachable. With the target now inside every process corner's range, a
  per-process single-point trim at 27 C/3.3 V lands within +/-0.26 % (measured, tt/ff/ss),
  bounded by LSB/2, which is at most 0.35 % here. The earlier "exceeds +/-1.1 %" rows were
  produced by an unreachable 48 MHz target (per-corner code row: surrogate target) and by one global
  code across a process spread (global-code row), not by the trim resolution.
* **A single global code**: not reachable by construction. The calibrated codes differ by 126
  (0x59 to 0xD7), i.e. tens of percent; this row cannot be met without per-part trim.
* **Across T and V after the trim**: bounded by the oscillator's own drift, not by R, C or
  LSB. The topology has no TC compensation ([0004](0004-no-active-tc-compensation-runtime-discipline.md)).
  The fast-process droop at -40 C/3.6 V is -8.9 % (R x0.80, MiM 17x10), -9.4 % (P3) and
  -9.7 % (R x0.66, MiM 24x10): it does not move with R or C over that range, so the ratified
  +8 % / -9 % band is at the edge in model A and not met at ff by 0.2-0.7 points. It is
  inside the band under model B. Which model is right is a modelling question for the
  respin extraction, not something to resolve by widening the band here. Closing the
  remaining gap to +/-0.25 % is the reserved runtime-discipline stage (row 7).
* **Trim step row** (ratified 0.314 %/code, 150.6 kHz/code): not met by P3 at tt (0.50 %/code,
  240 kHz) or ss (0.69 %); met at ff (0.33 %, within 5 %). It was not met before (0.87 %/code
  at tt). The average over the ratified window is already 0.332 %/code for 8 binary bits on
  a 1/R-shaped curve, so this row cannot be met by sizing alone; it needs a ratified
  clarification or more resolution. Not hidden, not relaxed here.

## Alternatives considered

* **R x0.80, MiM 17 x 10 um (185.6 fF)** (`prop_r080_17x10`) - smaller (MiM -15 %), best ff droop
  (-8.87 % / +7.71 %), Iq -13.8 uA at tt, but under model B its top end is 66.07 MHz, 1.7 %
  short of 67.2. It also assumes the lumped `vc` capacitance is independent of MiM area; if it is
  all bottom plate and scales with area the tt frequency rises 1.4 %.
* **R x0.66, MiM 24 x 10 um (260 fF)** (`optB_r066_24x10`) - covers the window under both models
  (margins +7.2/+8.2 % under A, +9.0/+2.2 % under B) but costs +20 % MiM area, saves only 2.5 uA
  at tt, and has the worst ff droop (-9.74 % / +7.97 %).
* **Shrink the MiM alone** - the extracted parasitic floor (about 56 fF on `vc` plus 320 fF of
  ladder-node C) does not scale, so C alone has about a third of the leverage of R and cannot reach
  48 MHz at a usable code.
* **Widen the spec / disclose an exception** - declined by the operator ruling.

## Consequences

* **Not shown (open)**: the 27-point confirmation (issue AC 3). The three `klt sim` corners requests
  went to the batch fleet and all failed with exit 87 (runner klt 0.5.0 vs client 0.7.0,
  klayout-tools#2851; jobs `klt-sim-71b47285a46d`, `klt-sim-06e10de5dae5`,
  `klt-sim-4e4b4ff9a358`,
  [`summary.md`](../../sim/recentre/results/p3-27pt/20261011T034200Z/summary.md)). No local grid was run. The
  numbers above are single-corner probes (tt/ff/ss at the calibration point, six T/V extremes,
  two binding-corner range checks) and must not be read as the 27-point result.
* **Follow-ups named, not done here**: (1) layout respin of the trim bank and `klt pex` post-layout
  campaign on the new sizing (item 7) - including the 0.52 um minimum-length resistor `R0` against the
  poly-resistor length rule and the head-resistance share of the smallest ladder elements (the
  weights stop being exactly binary), and a decision on the substrate tie used for sign-off;
  (2) Monte Carlo on the accuracy rows (item 6) once the sizing is settled; (3) the 27-point
  confirmation when the fleet runner matches the client; (4) the 63-point Iq grid on the new sizing.
* **Risk the proposal carries**: the lumped parasitics are those of the *current* layout. The respin
  will change the ladder-node and `vc` capacitance, so the code positions and the margins in the
  table move; the +2.1 % lower-end margin under model A is the thinnest number and is why this
  record asks for a re-extraction before ratifying the range.
* No ratified row is edited by this record. If ratified, it replaces the committed ladder lengths
  only; superseding or amending rows 2, 3, 5, 6 is a separate operator decision.
