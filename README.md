# gf180-rcosc

A free-running, digitally trimmable RC oscillator on
[GlobalFoundries gf180mcu](https://github.com/google/gf180mcu-pdk), a 180 nm
open PDK — designed by AI agents driving
[klayout-tools](https://github.com/2AMLogic/klayout-tools) and the
open-source xschem + ngspice flow.

**Status: spec ratified; T1 not awarded.**
<!-- current-t1-status:begin -->
The graded T1 verdict in
[`signoff/signoff-report.json`](signoff/signoff-report.json) is **8 of 11
items met, tier not yet awarded** — items 5 (corner verification), 6
(Monte Carlo) and 7 (post-layout) are unmet, with reasons `check_failed`,
`negative_control_not_detected` and `no_evidence`. The grade rests on the
2026-11-06 campaigns. Item 5, on
[`sim/item5/results/20261106T051832Z/`](sim/item5/results/20261106T051832Z/summary.md)
(trim code `0xA9` held across corners): **post-trim accuracy** — rows 4
and 5 — fails with one code held across process corners (7/21 and 22/63
points inside the ratified −2.9 %/+2.0 % and −10.8 %/+8.8 % windows);
**trim range** (row 2) fails on its LSB step, 0.501 %/code against the
ratified 0.314 %/code, with both range ends passing (28.202 / 73.502 MHz
against 28.8 / 67.2 MHz); row 8 draws 576.2 uA at `ff`/85 °C/3.6 V at the
`tt` calibration code against the < 500 uA limit. Item 6's Monte Carlo
campaign (`sim/mc/results/20261106T072000Z/`) reports
`negative_control_not_detected`. Item 7 has no `klt pex` report and is
owned by [issue #70](https://github.com/2AMLogic/gf180-rcosc/issues/70).
The design has moved since this grade — the current row-by-row position
is in [`docs/ROADMAP.md`](docs/ROADMAP.md) (§ "Where it stands") and
[`signoff/README.md`](signoff/README.md) (§ "Current verdict, and the
claims behind each row"), summarised in the ladder paragraph below — and
none of it is re-graded, so this verdict stands as the record of truth.
<!-- current-t1-status:end -->
The target spec (frequency, trim math, PVT accuracy budget) is ratified —
see below and [`spec/`](spec/README.md). Schematic capture, the PVT-corner
campaign and DRC-clean/LVS-matched layout are committed (see the maturity
ladder below).

**Built agent-native.** Every specification, decision record, testbench, and
line of documentation here is produced by AI agents working from a ratified
spec and an append-only evidence trail — not human-authored work that agents
merely assisted with. Verification is the product: every claim traces to a
recorded result under PVT corners. Where the agents hit friction with the
open-source tooling — most often
[klayout-tools](https://github.com/2AMLogic/klayout-tools) — that friction is
filed as a public issue against the tool itself, so the fix benefits everyone
using gf180mcu, not just this repo.

## Why this block

This is a **new block, not a port**. The fleet's existing clocking canaries
are PLLs; nothing in the fleet covers an internal RC-based clock source with
a digital trim interface. That is a different problem: no reference input,
no feedback loop to lean on — accuracy comes from the RC network itself,
from trim, and from how well the design cancels supply and temperature
dependence.

The anchor use case is well precedented in shipped commercial silicon:
crystal-less full-speed USB. The USB 2.0 specification's frequency-tolerance
clauses set the accuracy class, and multiple vendors ship MCUs that meet it
from an internal RC oscillator — post-trim accuracy plus runtime discipline
from an external timing reference such as USB start-of-frame timing (e.g.
ST's clock-recovery-system (CRS) peripheral, Silicon Labs' crystal-less USB
parts). This repo targets that public, well-documented accuracy class; the
spec will be derived from those public precedents and the USB 2.0 spec, and
from free-running accuracy figures in shipped RC-oscillator datasheets.

The sibling analog canaries on this PDK
([gf180-bandgap](https://github.com/2AMLogic/gf180-bandgap),
[gf180-temp-por](https://github.com/2AMLogic/gf180-temp-por)) are the style
reference for spec, decision-record, and evidence conventions — not the
circuit source. Topology selection (relaxation oscillator vs.
ring-with-RC-reference) was part of the spec work, decided in
[`spec/decision-records/0001`](spec/decision-records/0001-relaxation-oscillator-topology.md);
future spec changes go through their own decision record in `spec/`.

## Target specification (RATIFIED 2026-08-20, see issues #1 and #3)

Ratified per
[`spec/decision-records/0002-target-spec-ratification.md`](spec/decision-records/0002-target-spec-ratification.md),
as corrected by
[`spec/decision-records/0003-pdk-sourced-process-spread-tcr-and-iq.md`](spec/decision-records/0003-pdk-sourced-process-spread-tcr-and-iq.md),
which together derive every row below from cited public precedents or an
explicit, flagged engineering assumption and show the trim-math arithmetic.
DR-0003 supersedes DR-0002 for four rows (process spread, trim range/
resolution, post-trim accuracy, Iq) against gf180mcu's own published
electrical-specification tables; all other rows are DR-0002's, re-verified.

| Parameter | Target | Basis |
|---|---|---|
| Output frequency | 48.000 MHz | matches the crystal-less full-speed-USB precedent — ST `DS9826` Rev 6 Table 43 (`fHSI48` typ 48 MHz) and Silicon Labs CP2102N Rev 1.5 Table 3.5 (`fOSC` typ 48 MHz); explicit engineering choice, see DR-0002, citations verified in DR-0003 |
| Trim interface | 8-bit digital trim, ±40% range (28.8–67.2 MHz), 0.314%/code (150.6 kHz/code LSB), half-LSB ±0.157%, single-point trim at test | range covers the sourced untrimmed spread (required pull −32.3%/+38.4%) with margin; full arithmetic in DR-0003 §"Row 2" |
| Free-running, untrimmed (process spread, fixed T/V) | ±35% first-order (−27.7%/+47.6% exact in frequency) | **sourced** from gf180mcu-pdk `docs/analog/spice/elec_specs/`: poly-resistor spread ±20% (§5.1, §6.1A/B) + MIM-cap spread ±15.33% (§6.2(a)), summed worst-case as independent process modules — DR-0003 |
| Free-running, post-trim, **at calibration point** (T = 27 °C, process, VDD ±10%) | **−2.9% / +2.0%** worst-case | quantization ±0.157% + trim-DAC mismatch ±0.300% + comparator offset ±0.300% (both still flagged assumptions) + the **measured** supply span at per-corner calibrated codes (−2.07%/+1.17%, campaign `sim/pvt/results/20260923T030125Z/`; the low-side comparator's supply slope is flattened by the complementary PMOS-input cell of issue #57 — delay share of the span 62–82% → 7.6–33%, probe `sim/pvt/results/20260923T030905Z/` — so the residual is now dominated by the charge-path term) — DR-0017 supersedes DR-0016's −9.2%/+6.5% (which superseded DR-0003's ±1.1%). Against ST's shipped `ACC_HSI48` = −2.8/+2.9% at 25 °C: slightly looser on the low side (−2.9% vs −2.8%), tighter on the high side (+2.0% vs +2.9%); the charge-path supply term is the next lever |
| Free-running, post-trim, **full temperature range** (−40…+85 °C, VDD ±10%) | **+8.8% / −10.8%** worst-case | gf180mcu's published poly-resistor TCR of −1200 ppm/K (§6.1A), trimmed at 27 °C: ΔR/R = −6.96% at +85 °C (58 K) so f rises +6.84%, ΔR/R = +8.04% at −40 °C (67 K) so f falls −7.91%, plus the re-derived at-calibration figure above — DR-0017 (supersedes DR-0016's +13.4%/−17.1%; DR-0004 stands — no active TC compensation, the delay term is budgeted, not compensated — and closing the gap to USB compliance remains entirely the job of the runtime-disciplined row below) |
| Runtime-disciplined (reserved, not designed) | ≤ ±0.25% (2,500 ppm) — USB full-speed compliance | USB 2.0 Rev 2.0 §7.1.11 `TFDRATE`, verified verbatim; the clause covers temperature and supply, with no pre-/post-discipline distinction. Precedented by ST's CRS peripheral (`RM0091` Rev 10 §7, SOF-based) and Silicon Labs' crystal-less USB parts — see DR-0003 |
| Supply | 3.3 V core (3.0–3.6 V) | explicit engineering choice, matches gf180mcu's 3.3V-primary flavor and sibling canary `gf180-bandgap`'s own supply scope |
| Quiescent current (Iq) | < 500 µA (running) | anchored to ST `DS9826` Rev 6 Table 43 `IDDA(HSI48)` = 312 µA typ / 350 µA max, with headroom for gf180mcu's older 180 nm node — DR-0003 |
| Startup time | ≤ 10 µs to within trimmed accuracy | looser than the shipped precedent ST `DS9826` Rev 6 Table 43 `tsu(HSI48)` ≤ 6 µs max — DR-0002, citation verified in DR-0003 |
| Temperature range | −40 °C to +85 °C (industrial) | explicit engineering choice, standard industrial MCU/oscillator range |

An oscillator spec without its trim math is not a spec: every accuracy claim
above shows both the PVT-corner spread and the trim range/resolution that
covers it. The current ratified post-trim error budget and its arithmetic
are in
[`spec/decision-records/0017-low-side-comparator-pmos-respin-supply-slope.md`](spec/decision-records/0017-low-side-comparator-pmos-respin-supply-slope.md)
(DR-0017, superseding DR-0016, which superseded DR-0003's Row 3); DR-0003
remains the background derivation for process spread, trim range/
resolution and Iq, and DR-0002 for the rows neither changed. **The
free-running accuracy claim must always be quoted with its temperature
and supply conditions**: −2.9%/+2.0% holds only at the calibration point
(27 °C, 3.0–3.6 V), and the full-range figure (−40…+85 °C, same supply)
is −10.8%/+8.8%. In those budgets the supply span (−2.07%/+1.17%) is
**measured**, not assumed; two terms are still explicit, flagged
engineering assumptions rather than invented precision — trim-DAC
mismatch (±0.300%) and comparator offset (±0.300%). DR-0003 states what
would supersede them.

Maturity ladder: spec ratified → schematic simulated across PVT → layout
DRC/LVS-clean → post-layout re-verification → shuttle seat → measured
silicon. **Current position: spec ratified, schematic simulated across
PVT, layout DRC/LVS-clean — rebuilt for the comparator-H mirror-load
change (L 1.0 → 0.7 µm,
[DR-0039](spec/decision-records/0039-row5-comparator-h-mirror-load-l07-landed-in-schematic-and-netlist-layout-lvs-not-rebuilt.md),
[DR-0042](spec/decision-records/0042-row5-comparator-h-mirror-load-l07-layout-rebuilt-drc-clean-lvs-match-extraction-reconfirm-and-mismatch-open.md))
— with the graded T1 verdict still 8 of 11 items met (status block
above). The post-grade design position, by ratified row
([`docs/ROADMAP.md`](docs/ROADMAP.md) § "Where it stands";
[`signoff/README.md`](signoff/README.md) § "Current verdict, and the
claims behind each row"): row 5's `ff` accuracy miss is fixed — the
mirror-load change reads +1.66 pt on the rebuilt-layout extraction
against the +8.8 % full-temperature limit
([DR-0038](spec/decision-records/0038-row5-comparator-h-mirror-load-l07-clears-ff-hot-low-v-on-three-die-stage-rerun-schematic-not-yet-changed.md)
to
[DR-0044](spec/decision-records/0044-row5-comparator-h-mirror-load-l07-trim-range-and-running-iq-unchanged-on-the-extraction-of-the-rebuilt-layout.md))
— and the startup bench re-run on that netlist reads 63/63 at the
[DR-0029](spec/decision-records/0029-calibration-code-after-comparator-h-fix.md)
calibration code `0xA4`
([`sim/startup-settled/results/20261114T221218Z/`](sim/startup-settled/results/20261114T221218Z/summary.md));
row 4 is open — the `ss` supply span is 6.09 pt against the 4.9 pt
at-calibration window
([DR-0043](spec/decision-records/0043-row5-comparator-h-mirror-load-l07-reconfirmed-on-the-extraction-of-the-rebuilt-layout-ff-hot-low-v-clears.md)),
the `w3r65` bank candidate clears it at 4.68 pt on the extraction but
raises running Iq at code `0xFF` by 18–28 %
([DR-0045](spec/decision-records/0045-row4-w3r65-bank-candidate-measured-on-the-rebuilt-layout-extraction-ss-span-clears-but-code-0xff-running-iq-rises-20-28-percent.md))
and is therefore not adopted, with the ruling on
[issue #337](https://github.com/2AMLogic/gf180-rcosc/issues/337) open;
rows 2 and 8 fail on the current corner campaign
([`sim/item5/results/20261106T071555Z/`](sim/item5/results/20261106T071555Z/summary.md)):
row 2's nominal LSB step is 0.539 %/code against the ratified
0.314 %/code (the range ends pass) and row 8 draws 559.4 uA at
`ff`/85 °C/3.6 V. Every record behind this paragraph (DR-0038 through
DR-0045) is `Status: proposed` — none is ratified and none of it is
re-graded; the graded verdict in the status block above remains the
verdict of record. The post-layout rung is not complete (item 7 is owned
by [issue #70](https://github.com/2AMLogic/gf180-rcosc/issues/70)), so
the shuttle-seat rung is not yet in reach; no silicon exists.**

The comparator/bias-path PVT
revision ([issue #39](https://github.com/2AMLogic/gf180-rcosc/issues/39),
[DR-0012](spec/decision-records/0012-comparator-bias-path-pvt-revision.md))
changed `design/rcosc_bias.sch` and the trim-bank pass-switch restructure
([issue #43](https://github.com/2AMLogic/gf180-rcosc/issues/43),
[DR-0014](spec/decision-records/0014-trim-bank-pass-switch-restructure.md))
changed `design/rcosc_trim_bank.sch` after the layout was verified; both
cells have since been re-drawn and the whole hierarchy re-run through the
post-layout diagnostic campaign
([issue #44](https://github.com/2AMLogic/gf180-rcosc/issues/44),
[DR-0013](spec/decision-records/0013-bias-cell-respin-postlayout-pex-reverification.md);
[issue #50](https://github.com/2AMLogic/gf180-rcosc/issues/50),
[DR-0015](spec/decision-records/0015-trim-bank-respin-postlayout-pex-reverification.md)),
and the comparator re-reference ([issue
#61](https://github.com/2AMLogic/gf180-rcosc/issues/61),
[DR-0018](spec/decision-records/0018-comparator-pmos-respin-postlayout-pex-reverification.md))
re-ran that diagnostic on the post-#60 hierarchy, superseding
[DR-0010](spec/decision-records/0010-postlayout-pex-pvt-frequency-shift.md)'s,
DR-0013's and DR-0015's post-layout figures for it. Those DR-0018 figures
are historical — its 2026-09-23 post-layout campaign
([`sim/pvt-postlayout/results/20260923T152954Z/`](sim/pvt-postlayout/results/20260923T152954Z/summary.md))
is a diagnostic, not a row-level verdict: the parasitic shift measured
then was always slower, −18.78 % to −36.86 % (mean −25.65 %, worst at
`ff`/−40 °C/3.6 V), with both DR-0017 guardrails holding extracted-side
but the slow corner's trim headroom tightening to ≈ +4.7 % (`ss`
calibrating at `0xF7`); the November records cited in the ladder above
supersede them for the rows they re-measure. See
[`design/README.md`](design/README.md), [`layout/README.md`](layout/README.md),
and [`spec/decision-records/0018`](spec/decision-records/0018-comparator-pmos-respin-postlayout-pex-reverification.md)
for the evidence behind each stage.

## Repo layout

```
spec/          ratified spec + decision records
design/        schematics / netlists (xschem)
sim/           testbenches + PVT corner results (ngspice)
layout/        GDS + DRC/LVS reports (klayout-tools driven)
measurements/  silicon characterization (empty until tape-out)
```

The offline test suites are enumerated as a matrix of isolated jobs in
[`.github/workflows/offline-suites.yml`](.github/workflows/offline-suites.yml)
— run one at a time locally (e.g. `python3 -m pytest -p no:cacheprovider
sim/waveform/test_harness.py`); there is no repo-wide `pytest` entry point,
because several benches share the `test_harness.py` basename, which makes a
single rootdir-relative collection collide.

## Chipalooza

[`docs/chipalooza/challenge-5-proposal.md`](docs/chipalooza/challenge-5-proposal.md)
is this block's Chipalooza Challenge #5 proposal: block type, I/O list
mapped to the slot budget, functional description, a spec table re-derived
from `sim/` with every row's met/unmet verdict against the ratified spec,
and a bench test plan.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
