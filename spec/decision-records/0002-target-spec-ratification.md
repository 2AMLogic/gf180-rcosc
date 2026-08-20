# 0002: Target spec ratification — frequency, trim, and PVT accuracy budget

- **Status**: Ratified
- **Date**: 2026-08-20
- **Decided by**: Builder agent, issue #1

## Context

`README.md` carried a DRAFT "Target specification" table with every numeric
row marked TBD, pending the spec work tracked by issue #1. Per CLAUDE.md,
this repo's accuracy class is anchored to crystal-less full-speed USB: the
USB 2.0 specification's frequency-tolerance clause sets the compliance bar,
and shipped commercial MCUs (ST's clock-recovery-system-class parts,
Silicon Labs' crystal-less USB parts) show that bar is reachable from an
internal RC oscillator via post-trim accuracy plus optional runtime
discipline from an external timing reference (USB start-of-frame, "SOF").
[0001-relaxation-oscillator-topology.md](0001-relaxation-oscillator-topology.md)
fixed the oscillator topology (relaxation/RC-timed core, switched-RC trim
bank) that this record's trim math assumes.

**A note on citation confidence.** This record is written without live web
access in this session (per the issue's own instruction, "if live web
access is unavailable in this environment, use well-established public
knowledge... clearly cite document names/part numbers/section references as
best known; flag explicitly if a number could not be independently verified
in this session"). Every citation below is the author's best recollection of
public, well-established documents — the USB 2.0 specification and named
vendor datasheets/application notes — cited by document name, part number,
or section as specifically as can be recalled. Where a specific clause
number, exact wording, or precise numeric figure could not be independently
re-verified against primary source text in this session, it is flagged
inline as **[unverified this session]**. These flags are the concrete
"suspected risk areas" the Curator called out and are intentionally left
visible rather than silently resolved, so a future pass with live source
access can confirm or correct them without re-deriving the whole spec.

## Decision

Ratify the following target spec, replacing the DRAFT table in
`README.md`.

### Target frequency: 48.000 MHz

USB full-speed data signaling is 12 Mbit/s; a full-speed device's serial
interface engine (SIE) commonly runs its bit/NRZI-recovery and low-level
timing off a clock that is an integer multiple of that bit rate — 4x
oversampling (48 MHz) is the conventional choice in industry USB PHY/SIE
design and is the frequency shipped crystal-less-USB MCUs use for their
internal oscillator directly: ST's HSI48 (STM32F0/F3/L0 crystal-less-USB
parts, e.g. STM32F042x4/x6) is nominally 48 MHz and clocks the USB
peripheral without a crystal **[unverified this session: exact ST part
numbers and the 48 MHz figure are cited from well-established public
knowledge of the STM32F0 family; the precise datasheet section was not
re-read against primary text in this session]**. Choosing 48 MHz over some
other multiple is an **explicit engineering choice** (match the shipped
precedent, and keep this block directly comparable to it) rather than a
number the USB 2.0 spec itself mandates — the USB 2.0 spec fixes the 12
Mbit/s bit rate and its tolerance (see below), not the internal SIE clock
frequency a given implementation chooses.

### Trim interface: 8-bit digital trim, ±35% range, single-point trim at test

**Untrimmed process spread this trim range must cover.** On-chip RC
relaxation oscillators without trim commonly show large frequency spread
across process corners, driven by poly-resistor sheet-resistance spread
(process corners commonly quoted in the ±15–25% range for unsalicided poly
resistors in mixed-signal/analog processes) combined with capacitor value
spread (commonly a few to ~10% for MiM/MOM-class capacitors), which combine
(the RC time constant is a product) into an untrimmed frequency spread on
the order of **±30%** at a fixed temperature and supply. **This ±30% figure
is an explicit engineering assumption, not sourced from gf180mcu's own
device data** — this session did not have access to gf180mcu's resistor/
capacitor process-corner or Monte-Carlo mismatch models (no SPICE device
models for `gf180mcu_fd_pr` resistor/cap flavors were available in this
environment; only GDS/layout-level PDK data was reachable). It is flagged
here explicitly, per the issue's own instruction, as an assumption pending
confirmation against gf180mcu-specific device data during the
schematic/corner-simulation phase (per the maturity ladder in `README.md`).
If that confirmation later shows a materially different spread, the trim
range in this record must be revisited via a superseding decision record —
it does not silently drift.

**Trim range chosen: ±35%** (31.2 MHz – 64.8 MHz raw achievable range at 48
MHz nominal), i.e. 5 percentage points of margin on each side beyond the
assumed ±30% process spread, to absorb additional spread from trim-time
supply/temperature variation and from the process-spread assumption's own
uncertainty.

**Trim word: 8 bits (256 codes), linear mapping across the ±35% range.**

```
Total trim span      = 70% of nominal   = 0.70 x 48.000 MHz = 33.60 MHz
LSB step size         = span / 255 codes = 33.60 MHz / 255  ≈ 131.8 kHz/code
LSB step size (ratio) = 70% / 255                             ≈ 0.2745 %/code
Worst-case quantization error = 1/2 LSB   ≈ 65.9 kHz  ≈ 0.137 % of nominal
```

**Why this resolution reaches the post-trim accuracy target.** The
post-trim (free-running, no runtime discipline) accuracy target this record
sets below is ±2% (see PVT budget). Trim quantization alone (±0.137%)
consumes only a small fraction of that budget, leaving headroom for the
other post-trim error sources (trim-DAC element mismatch/INL, comparator
offset residual after trim, temperature and supply drift the single-point
trim does not correct) — see the budget breakdown below. A coarser trim
(e.g. 6 bits, ~1.1%/code, ~0.55% worst-case quantization) would already
consume roughly a quarter of the ±2% budget on quantization alone before
any other error source is counted, leaving materially less margin; 8 bits
was chosen as the point where quantization stops being a first-order
contributor to the post-trim budget.

**Trim timing**: single-point trim, performed at test (assumed 27 °C,
nominal VDD) — this record does not ratify a multi-point (temperature- or
voltage-aware) trim scheme; see the PVT budget below for what a
single-point trim does and does not correct.

### PVT accuracy budget

Three distinct numbers, kept explicitly separate per CLAUDE.md's
requirement that a claim show "both the PVT-corner spread and the trim
range/resolution":

| Stage | Target | What it covers | What it does NOT cover |
|---|---|---|---|
| **Free-running, untrimmed** | ±30% (assumption, flagged above) | process-corner spread at fixed T/V | temperature and supply drift on top of this |
| **Free-running, post-trim** | ±2% (20,000 ppm) worst-case, over full PVT (process, −40…+85 °C, VDD ±10%) | process spread (absorbed by the one-time trim), plus the residual error sources below | continuous correction — a single-point trim cannot track temperature or supply drift after trim |
| **Runtime-disciplined** (reserved, out of scope this issue) | ≤ ±0.25% (2,500 ppm) — USB full-speed compliance | closes the remaining gap between ±2% free-running and USB's tolerance, via continuous correction from an external timing reference (e.g. USB SOF) | not designed in this repo yet — see "Consequences" |

**Post-trim (±2%) budget breakdown** (worst-case linear sum, not RSS — a
conservative choice appropriate for a first-pass budget with several
flagged assumptions):

| Contributor | Budget | Basis |
|---|---|---|
| Trim quantization | ±0.14% | derived above from the 8-bit/±35% trim design |
| Trim-DAC element mismatch / INL | ±0.30% | engineering assumption, flagged — pending trim-bank device sizing |
| Comparator/reference offset residual after trim | ±0.30% | engineering assumption, flagged — pending comparator/bias design |
| Temperature drift, −40…+85 °C, single-point trim at 27 °C | ±1.00% | engineering assumption, flagged as the single largest open risk — depends on the RC network's net temperature coefficient after any compensation, not yet characterized on gf180mcu devices |
| Supply drift, VDD ±10% | ±0.30% | engineering assumption, flagged — assumes a reasonably supply-independent bias per 0001's "Consequences" |
| **Worst-case sum** | **≈2.04% ≈ ±2%** | sum of the above; rounds to the ±2% target |

Every row above except trim quantization is an **explicit engineering
assumption**, not yet backed by gf180mcu device data or a circuit-level
design — flagged consistently with this record's citation-confidence note.
The temperature-drift row in particular assumes the schematic-phase design
includes some temperature-coefficient mitigation (e.g. a resistor-flavor
choice or ratio compensating first-order TC, following the general pattern
`gf180-bandgap`'s own TC-mitigation work used for its resistor flavor
choice) — an uncompensated RC network's raw temperature coefficient over a
125 °C span (poly resistor TC on the order of 1,000+ ppm/°C is common in
mixed-signal processes) could otherwise consume the entire ±2% budget on
this row alone. This is exactly the kind of budget-vs-evidence gap
`gf180-bandgap`'s own issue #1 hit (an unreviewed accuracy claim that later
proved not credible against that repo's own device-mismatch data) — the
budget above is written to be checked, and is expected to be revisited by a
superseding decision record once schematic-phase corner sweeps produce real
numbers, not treated as self-evidently correct because it is written down.

### USB 2.0 anchor: ±0.25% (2,500 ppm) full-speed data-rate tolerance

The USB 2.0 specification sets a full-speed (12 Mbit/s) data-rate tolerance
of **±0.25% (2,500 ppm)** — this is the compliance figure CLAUDE.md and this
repo's README cite as the "±2,500 ppm class." **[unverified this session:**
the exact clause number in the USB 2.0 specification (commonly cited around
the electrical/clock-related sections, in the vicinity of what is often
referenced informally as "7.1.11 Data Signaling Rate") was not re-read
against primary source text in this session; the ±0.25%/2,500 ppm figure
itself is well-established public knowledge repeatedly cited across USB
hardware-design literature and vendor app notes, but this record does not
independently confirm whether the clause applies identically pre- and
post-SOF-discipline, or whether the spec text itself distinguishes a
free-running tolerance from a disciplined one at that clause. The working
assumption carried through this whole record — consistent with how ST and
Silicon Labs market their CRS-class / crystal-less-USB peripherals — is
that ±0.25% is the **compliance target achieved with runtime discipline**
(SOF-based correction), and that a free-running (undisciplined) internal
RC oscillator is not expected to meet ±0.25% on its own, which is exactly
why this record's free-running post-trim target (±2%) is set looser and
relies on a reserved future runtime-discipline stage to close the gap.
This distinction should be confirmed against primary USB 2.0 spec text
before any compliance claim is made downstream.**]**

**Vendor precedents for the free-running/runtime-discipline split**
(citations, with confidence flags):

- **ST clock-recovery-system (CRS) peripheral**, shipped on STM32F0/F3/L0
  crystal-less-USB parts: uses USB SOF packets (nominally every 1 ms) as a
  running correction reference for the internal HSI48 RC oscillator,
  continuously trimming it to stay within the USB tolerance without an
  external crystal. **[unverified this session: exact application-note
  number (recollection points toward an ST AN in the AN2xxx/AN4xxx range
  describing CRS/HSI48 USB use) and exact pre-trim/free-running accuracy
  figures quoted by ST for HSI48 were not re-read against primary source
  text in this session — cited as well-established public knowledge of
  the CRS peripheral's existence and purpose, not as a verified numeric
  citation.]**
- **Silicon Labs crystal-less USB parts** (e.g., the C8051F34x /
  C8051F320-family and EFM8UB-family USB microcontrollers): ship an
  internal precision oscillator plus a USB clock-recovery mechanism that
  trims the oscillator using USB SOF timing, marketed specifically as
  eliminating the external crystal for full-speed USB compliance.
  **[unverified this session: exact part numbers, datasheet section, and
  numeric accuracy figures were not re-read against primary source text
  in this session — cited as well-established public knowledge of the
  product family's existence and marketed capability, not as a verified
  numeric citation.]**

These two precedents are the basis for this record's overall shape (a
free-running RC oscillator, trimmed once at test, with an SOF-style
runtime-discipline mechanism closing the remaining gap to USB compliance) —
not for any specific numeric value in the tables above, all of which are
independently derived or flagged as engineering assumptions.

### Supply, Iq, startup, temperature range

| Parameter | Target | Basis |
|---|---|---|
| Supply | 3.3 V core (3.0–3.6 V, ±10%-class range) | explicit engineering choice — matches this PDK's 3.3 V-primary device flavor and this project's sibling analog canary `gf180-bandgap`'s own 3.3V-primary scope choice (see that repo's DR-0002), and is consistent with typical USB device-side logic-level/MCU-core supply precedent in the crystal-less-USB MCU class cited above |
| Quiescent current (Iq) | < 200 µA (running) | explicit engineering target, flagged — no specific shipped-part Iq figure was independently verified in this session; order-of-magnitude target pending schematic-phase confirmation, deliberately left order-of-magnitude conservative rather than aggressive given the lack of a verified precedent number |
| Startup time | ≤ 10 µs to within trimmed accuracy | explicit engineering target — motivated by the general, well-established distinction (repeatedly cited in crystal-less-oscillator marketing/app-note literature) that RC/relaxation oscillators start in microseconds versus the millisecond-scale startup of crystal oscillators; specific numeric precedent **[unverified this session]** |
| Temperature range | −40 °C to +85 °C (industrial) | explicit engineering choice — standard industrial-grade MCU/oscillator commercial temperature range; some shipped MCU families in this class also offer −40…+105 °C variants, but −40…+85 °C is chosen here as the baseline target, consistent with the temperature range already used in the PVT budget above |

## Alternatives considered

- **Target a lower frequency (e.g. 12 MHz, the raw USB bit rate, or 24 MHz,
  2x oversampling) instead of 48 MHz.** Rejected — 48 MHz directly matches
  the shipped crystal-less-USB precedent this project is anchored to
  (ST HSI48), keeping this repo's PVT/trim evidence directly comparable to
  that precedent's own numbers once measured; a different frequency
  multiple would not change the trim-math structure but would break that
  direct comparability for no benefit.
- **Ratify the free-running post-trim target at ±0.25% directly (skip the
  ±2%-plus-runtime-discipline split).** Rejected — nothing in this record's
  evidence (an unverified process-spread assumption, no gf180mcu device
  characterization yet) supports claiming USB-compliant accuracy from a
  single-point trim alone; the vendor precedents this record cites
  themselves rely on continuous SOF-based correction to reach that figure,
  not trim alone. Ratifying ±0.25% as a free-running target would repeat
  the exact failure mode CLAUDE.md and the Curator's guidance both flagged
  from `gf180-bandgap` issue #1 — an accuracy claim not backed by evidence.
- **Leave the PVT-budget rows as open items rather than pinning numbers.**
  Rejected for most rows — the issue's own acceptance criteria require the
  trim math to be "explicit and traceable," which needs concrete numbers to
  check arithmetic against. Where a number is genuinely unpinned by
  evidence (the untrimmed process spread, and every non-quantization row of
  the post-trim budget), this record pins an explicit, flagged *engineering
  assumption* rather than leaving a blank — consistent with the issue's own
  instruction ("an explicit engineering-choice rationale where no precedent
  applies"). This differs from leaving the row's *value* wholly open, which
  the issue reserves for rows that "genuinely cannot be pinned to a number
  yet" — here, a defensible placeholder number with its assumption stated
  is preferred over no number, precisely so the schematic phase has a
  concrete target to design against and a documented number to correct if
  wrong.
- **Design and ratify the runtime-discipline (SOF-correction) loop as part
  of this record.** Rejected — out of scope for issue #1, which is a
  spec-only deliverable; the SOF-correction mechanism is a separate,
  substantial design (comparable in complexity to ST's CRS peripheral) that
  belongs in its own future decision record once the free-running core
  itself is designed and characterized. This record only reserves the
  interface compatibility (0001's "Consequences") and states the gap it
  would need to close.

## Consequences

- `README.md`'s "Target specification" table is replaced with the ratified
  values above, and the "DRAFT — engineering to ratify, see issue #1"
  heading is updated to a ratified state referencing this record.
- The **±30% untrimmed process-spread assumption** and every
  non-quantization row of the **post-trim ±2% budget** are flagged
  engineering assumptions pending gf180mcu-specific device characterization
  — this is the single largest open risk this record carries forward. The
  next design-phase work (schematic entry and PVT corner simulation, per
  the maturity ladder in `README.md`) must either confirm these assumptions
  or trigger a superseding decision record if the real numbers diverge
  materially. This record does not invent a false precision by rounding
  away that uncertainty.
- The **runtime-discipline (SOF-correction) stage** is explicitly reserved,
  not designed — a future issue is expected to scope that work once the
  free-running core is designed and its actual post-trim accuracy is
  measured in sim, since the size of the gap it must close depends on that
  measurement rather than this record's a priori ±2% target.
- Device sizing for the trim bank (resistor/capacitor segment values
  implementing the 8-bit, ±35%, ~0.27%/code trim word) is schematic-phase
  work, constrained by but not fixed by this record.
- If schematic-phase corner sweeps show the assumed ±30% untrimmed spread,
  or any row of the post-trim budget, is materially wrong, the fix is a
  superseding decision record (adjusting trim range/resolution and/or the
  post-trim target) — not a silent edit to this record or to the ratified
  `README.md` table, per CLAUDE.md ("agents do not relax the ratified spec
  to make results pass").
