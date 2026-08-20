# 0003: PDK-sourced process spread, temperature drift, and Iq — superseding four rows of 0002

- **Status**: Ratified — supersedes
  [0002](0002-target-spec-ratification.md) for four specific rows
  (untrimmed process spread; trim range/resolution; post-trim PVT accuracy;
  quiescent current). Every other row of 0002 remains in force.
- **Date**: 2026-08-20
- **Decided by**: Builder agent, issue #3

## Context

[0002](0002-target-spec-ratification.md) ratified this repo's target spec
without live web access, and said so: it flagged several figures inline as
**[unverified this session]** and stated explicitly that "if that
confirmation later shows a materially different spread, the trim range in
this record must be revisited via a superseding decision record — it does
not silently drift." This record is that revisit.

A verification pass with live access fetched and read all five primary
sources 0002 cited from recollection. Four of them confirm 0002's numbers;
the fifth — gf180mcu's own published electrical-specification tables —
contradicts two of 0002's flagged engineering assumptions by a wide enough
margin to move the trim range and to invalidate the ±2% post-trim target
outright. A fourth row (Iq) is corrected in the opposite direction: 0002's
target was *tighter* than the shipped vendor part it is anchored to, which
is the same "claim not backed by evidence" failure mode CLAUDE.md warns
about, just pointing the other way.

Per CLAUDE.md ("agents do not relax the ratified spec to make results
pass") and `spec/README.md`'s append-only convention, this is a new record.
**`0002` is not edited** — not its numbers, not its Status field. It stands
as the historical record of what was ratified on the evidence then
available. `spec/README.md`'s index annotates 0002 as partially superseded
by this record rather than restating its Status, because `TEMPLATE.md`
models Status as binary (`ratified | superseded by NNNN`) and this record
supersedes only four of 0002's rows, not the whole document. That choice is
made here deliberately and is noted so a later reader does not mistake it
for an oversight.

Note that this record **loosens** three targets and does not claim any
improvement. It is not a relaxation to make a result pass — no result
exists yet; this repo is pre-schematic. It is a correction of targets that
were set against assumed device data before the real device data was read,
made now, before schematic work locks to figures that gf180mcu's own tables
say are unreachable.

### Primary sources, re-fetched and re-read for this record

All fetched 2026-08-20 and quoted from primary-source text, not from
recollection and not from issue #3's transcription of them.

| Source | Where | What was read |
|---|---|---|
| **USB 2.0 Specification, Revision 2.0** (April 27, 2000), §7.1.11 "Data Signaling Rate" | `usb.org/sites/default/files/usb_20_20250603.zip` → `usb_20.pdf`, p. 159 | full-speed transmit tolerance and the list of contributions it covers |
| **ST `RM0091` Rev 10** (STM32F0x1/F0x2/F0x8 Reference Manual), §6.2.3 "HSI48 clock" and §7 "Clock recovery system (CRS)" | `st.com` (via Internet Archive snapshot — see note below), pp. 131, 138 | HSI48 free-running factory-calibration accuracy; the SOF-discipline mechanism |
| **ST `DS9826` Rev 6** (STM32F072x8/STM32F072xB datasheet), §6.3.8 "Internal clock source characteristics", Table 43 "HSI48 oscillator characteristics" | `st.com` (via Internet Archive snapshot), p. 72 | `ACC_HSI48`, `TRIM` step, `tsu(HSI48)`, `IDDA(HSI48)` |
| **Silicon Labs CP2102N Data Sheet, Rev. 1.5**, §3.1.5 Table 3.5 "Internal Oscillator" | `silabs.com/documents/public/data-sheets/cp2102n-datasheet.pdf`, p. 11 | `fOSC`, `TSOSC`, `PSSOSC` |
| **`google/gf180mcu-pdk`**, `docs/analog/spice/elec_specs/` on `main` | GitHub contents API | §5.1 sheet resistance; §6.1A/B/C high-sheet poly resistors; §6.2 MIM capacitors |

**Access note (documented, not hidden).** `st.com` refused all direct
requests from this environment (HTTP/2 `INTERNAL_ERROR`, then connection
timeout — an anti-automation block, not a missing document). Both ST
documents were therefore read from Internet Archive snapshots of ST's own
canonical URLs (`web.archive.org/web/20251222062721id_/https://www.st.com/resource/en/datasheet/DM00090510.pdf`
and the corresponding `rm0091-…-stmicroelectronics.pdf` snapshot). The
files are ST's own unmodified PDFs — the document IDs, revision numbers
(`DS9826 Rev 6`, `RM0091 Rev 10`), page footers, and table numbering quoted
below are read from those files. This is a public mirror of a public
document, which satisfies CLAUDE.md's public-sources-only constraint, but a
future pass with direct `st.com` access should re-confirm against the
current revision, since a newer revision may have moved these figures.

### Corrections to issue #3's own transcription

Issue #3 described what to check; checking it turned up six places where
the issue's transcription and the primary sources disagree. **The verified
figures below are used throughout; the issue's are not.**

1. **MIM-capacitor file path.** The issue cites `elec_specs_6_2.rst` for
   the MIM capacitor tables. `elec_specs_6_2.rst` is §6.1B, the 2000 Ω/sq
   poly resistor. The MIM tables (doc §6.2, CSVs
   `6_Passive_Elements{4,5,6}.csv`) are in **`elec_specs_6_4.rst`**. The
   doc section number in the issue was right; the filename was not.
2. **`RM0091` section for the factory-calibration quote.** The issue
   attributes "factory calibrated by ST for ~3% accuracy at T_A = 25 °C" to
   §7 (CRS). It is in **§6.2.3 "HSI48 clock"** (the RCC chapter). §7 was
   read separately and confirms the CRS/SOF-discipline mechanism, but does
   not contain that sentence.
3. **Sign of the temperature-drift legs — the issue has them backwards.**
   The issue computes resistance shifts (−7.0% hot, +8.0% cold — both
   confirmed) and then reports the combined post-trim range as "+9%/−8%".
   Because `f ∝ 1/(RC)`, a *falling* resistance at hot *raises* frequency:
   the up-leg is the hot leg (smaller |ΔT| = 58 K) and the down-leg is the
   cold leg (larger |ΔT| = 67 K). The larger magnitude therefore belongs to
   the **negative** frequency leg. This record ratifies **+8% / −9%**, the
   mirror of the issue's figure. Magnitudes agree; leg assignment does not.
4. **Resistor flavors the issue did not mention.** §6.1C's 3000 Ω/sq poly
   resistor is **±25%**, not ±20%, and §6.1B's 2000 Ω/sq flavor has TCR
   **−1300…−1900 ppm/K**, worse than the −1200 ppm/K this record uses. Both
   are named below so the ±20% / −1200 ppm/K basis is traceable rather than
   cherry-picked.
5. **No published TCR exists for the §5.1 standard poly resistors.**
   §5.7 "Temperature Coefficient" covers metals, contacts, and vias only.
   The only poly-resistor TCR gf180mcu publishes in these tables is
   §6.1A/§6.1B's, for the optional extra-mask (L63) high-sheet SAB
   resistors. The design cannot assume a better TCR for the standard
   unsalicided poly without characterizing it.
6. **CP2102N drift specs the issue did not cite.** Table 3.5 also gives
   `TSOSC` = 45 ppm/°C typ and `PSSOSC` = 0.02 %/V typ. These are the most
   directly load-bearing numbers in that datasheet for this record's open
   question (see "Consequences"), and are used below.

## Decision

Four rows of 0002's ratified spec are replaced. Every other row of 0002 —
target frequency (48.000 MHz), 8-bit trim word, single-point trim at test,
supply, startup time, temperature range, and the reserved runtime-discipline
stage — is unchanged and remains in force.

### Verified device data this decision rests on

From `google/gf180mcu-pdk`, `docs/analog/spice/elec_specs/`, read on `main`:

| Device | File / table | Min / Typ / Max | Spread vs. typ |
|---|---|---|---|
| N+ poly, unsalicided | §5.1, `5_General_Specification1.csv` | 250 / 310 / 370 Ω/sq | ±19.35% |
| P+ poly, unsalicided | §5.1, `5_General_Specification1.csv` | 280 / 350 / 420 Ω/sq | ±20.00% |
| 1000 Ω/sq SAB poly (L63) | §6.1A, `6_Passive_Elements1.csv` | 800 / 1000 / 1200 Ω/sq | ±20.00% |
| — its TCR1 (W > 3 µm) | same | **−1200 / −1000 / −800 ppm/K** | — |
| 2000 Ω/sq SAB poly (L63) | §6.1B, `6_Passive_Elements2.csv` | 1600 / 2000 / 2400 Ω/sq | ±20.00% |
| — its TCR1 (W > 3 µm) | same | −1300 / −1650 / −1900 ppm/K | — |
| 3000 Ω/sq SAB poly (L63) | §6.1C, `6_Passive_Elements3.csv` | 2250 / 3000 / 3750 Ω/sq | ±25.00% |
| — its TCR1 | same | not published (`--`) | — |
| MIM cap, 1.5 fF/µm² | §6.2(a), `6_Passive_Elements4.csv` | 1.27 / 1.5 / 1.73 fF/µm² | **±15.33%** |
| — its TC1 | same | 9.9 / 13.3 / 16.6 ppm/K | — |
| MIM cap, 1.0 fF/µm² | §6.2(b), `6_Passive_Elements5.csv` | 0.9 / 1.0 / 1.1 fF/µm² | ±10.00% |
| — its TC1 | same | — / 10 / 20 ppm/K | — |
| MIM cap, 2.0 fF/µm² | §6.2(c), `6_Passive_Elements6.csv` | 1.8 / 2.0 / 2.2 fF/µm² | ±10.00% |
| — its TC1 | same | — / 18.8 / — ppm/K | — |

**Basis chosen, and why.** Resistor spread **±20%** — the worst case across
every flavor that is either standard (§5.1 P+ poly, exactly ±20%) or has
publishable TCR data (§6.1A, §6.1B, both ±20%). §6.1C's ±25% is excluded
because it publishes no TCR at all and is therefore not a candidate for an
oscillator's timing resistor; if a later design selects it anyway, this row
must be revisited. Capacitor spread **±15.33%** — the worst of the three
offered MIM flavors. Resistor TCR **−1200 ppm/K** — the worst-magnitude
corner of §6.1A, the flavor with the *best* published TCR; §6.1B is worse
(−1900 ppm/K), so −1200 ppm/K is a floor on the problem, not a ceiling.
Capacitor TC **+20 ppm/K** — the worst published across flavors, and >50×
smaller than the resistor's TCR, so it is carried through the arithmetic
for completeness rather than because it matters.

### Row 1 — Untrimmed process spread: ±30% (assumed) → ±35% (sourced)

0002 assumed ±30%, explicitly flagged as "not sourced from gf180mcu's own
device data." It is now sourced. `R` and `C` are independent process
modules (separate masks, separate films), so their spreads are summed
worst-case rather than RSS'd — the same conservative convention 0002 used
for its own error budget:

```
Resistor spread   dR = +/-20.00%      (P+ poly 280/350/420; 1000 ohm/sq 800/1000/1200)
Capacitor spread  dC = +/-15.33%      (MIM 1.5 fF/um2: 1.27/1.5/1.73 -> 0.23/1.5)
First-order worst-case sum  = +/-35.33%  -> ratified as +/-35%
```

Because `f ∝ 1/(RC)`, the exact product form is asymmetric in frequency and
is the figure the trim range must actually be sized against:

```
RC(max)/RC(nom) = 1.20 x 1.15333 = 1.3840   -> f = 1/1.3840 = 0.7225  -> -27.75%
RC(min)/RC(nom) = 0.80 x 0.84667 = 0.67734  -> f = 1/0.67734 = 1.4764 -> +47.64%

Untrimmed frequency spread (exact) = -27.75% / +47.64%   at fixed T, V
```

**Ratified: ±35% first-order (−27.7% / +47.6% exact in frequency).** The
±35% figure is the headline, directly comparable with 0002's ±30%; the
exact asymmetric figure is what Row 2 is sized against.

### Row 2 — Trim range: ±35% → ±40%; 8-bit word retained, LSB recomputed

0002 chose ±35% to leave ~5 percentage points of margin over its assumed
±30% spread. Against the now-sourced ±35%, ±35% of trim range would leave
**zero** margin. Restoring 0002's intended margin gives **±40%**.

Sizing against the exact form: correcting a part whose `RC` sits at a
corner requires a frequency trim multiplier `m = RC(actual)/RC(nom)`, so
the required pull is the mirror of the RC spread, not of the frequency
spread:

```
Required trim pull = [0.67734, 1.38400]  ->  -32.27% (down) / +38.40% (up)
Ratified range     = +/-40%              ->  margin: 7.73 pts down, 1.60 pts up
```

**Trim word: 8 bits (256 codes), linear across ±40%** — the width is
unchanged from 0002; only the span it maps to changes.

```
Trim range            = 48.000 MHz x [0.60, 1.40] = 28.80 MHz .. 67.20 MHz
Total trim span       = 80% of nominal   = 0.80 x 48.000 MHz  = 38.400 MHz
LSB step size         = span / 255 codes = 38.400 MHz / 255   = 150.588 kHz/code
LSB step size (ratio) = 80% / 255                              = 0.31373 %/code
Worst-case quantization error = 1/2 LSB  = 75.294 kHz          = 0.15686 % of nominal
```

Compare 0002's ratified ±35% arithmetic, re-derived and confirmed correct
on its own premise: span 33.600 MHz, 131.765 kHz/code, 0.27451 %/code,
half-LSB 0.13725%. The move to ±40% coarsens the LSB by 14.3%
(0.27451% → 0.31373% per code).

**Why 8 bits still holds.** Half-LSB quantization rises from ±0.137% to
±0.157%. Against the at-calibration-point budget ratified in Row 3
(±1.06%), quantization is 14.8% of the budget — still not a first-order
contributor, which was 0002's stated criterion for choosing 8 bits. A 9-bit
word would halve it to ±0.078% and buy ~0.08% of budget, which is not worth
an extra trim bit and its bank element; a 7-bit word (±0.315% half-LSB)
would consume 30% of the at-calibration budget on quantization alone. 8
bits remains the right point. For scale, ST's shipped part uses a **6-bit**
runtime `TRIM` word (`RM0091` Rev 10, §7.3, Table 20) at 0.09–0.2%/code
(typ 0.14%, `DS9826` Rev 6 Table 43) — but over a far narrower span, since
CRS trims a part that is already factory-calibrated.

**Ratified: ±40% range, 8-bit word, 150.6 kHz/code (0.3137 %/code),
half-LSB ±0.157%.**

### Row 3 — Post-trim PVT accuracy: flat ±2% → split, +8% / −9% full-range

0002's flat ±2% budget allotted a flagged, unsourced **±1.00%** to
"temperature drift, −40…+85 °C, single-point trim at 27 °C." 0002 itself
named this "the single largest open risk" and wrote that an uncompensated
RC network "could otherwise consume the entire ±2% budget on this row
alone." gf180mcu's published TCR says it consumes roughly **eight times**
the whole budget. A single flat number can no longer honestly describe the
part, so the row is split in two.

**(a) At the calibration point** — T = 27 °C (the trim temperature), over
process and VDD ±10%. This is 0002's budget with the temperature row
removed and quantization updated for the ±40% range:

| Contributor | Budget | Basis |
|---|---|---|
| Trim quantization | ±0.157% | derived above from the 8-bit/±40% trim design |
| Trim-DAC element mismatch / INL | ±0.300% | **unchanged flagged assumption from 0002** — pending trim-bank device sizing |
| Comparator/reference offset residual after trim | ±0.300% | **unchanged flagged assumption from 0002** — pending comparator/bias design |
| Supply drift, VDD ±10% | ±0.300% | **unchanged flagged assumption from 0002** — assumes a reasonably supply-independent bias per 0001 |
| **Worst-case sum** | **±1.057% ≈ ±1.1%** | linear sum, same convention as 0002 |

Three of these four rows are still unsourced engineering assumptions
carried forward verbatim from 0002. This record sources the temperature
term and nothing else; it does not upgrade the confidence of the rest, and
they stay flagged.

**(b) Over the full temperature range** — −40…+85 °C, single-point trim at
27 °C. Dominated entirely by the resistor TCR:

```
TCR (worst-case, gf180mcu 6.1A, min column)  = -1200 ppm/K
MIM TC1 (worst-case across flavors)          =   +20 ppm/K
Trim/calibration temperature                 =    27 degC

Hot leg:   dT = +85 - 27      = +58 K
           dR/R = -1200e-6 x  58 = -6.960 %
           dC/C =   +20e-6 x  58 = +0.116 %
           df/f = -(dR/R + dC/C)  = +6.844 %      (f ~ 1/RC: R falls -> f rises)

Cold leg:  dT = -40 - 27      = -67 K
           dR/R = -1200e-6 x -67 = +8.040 %
           dC/C =   +20e-6 x -67 = -0.134 %
           df/f = -(dR/R + dC/C)  = -7.906 %      (R rises -> f falls)

Combined with the at-calibration budget (+/-1.057%), worst-case linear sum:
           up   leg = +6.844 % + 1.057 % = +7.901 %   -> +8 %
           down leg = -7.906 % - 1.057 % = -8.963 %   -> -9 %
```

Exact multiplicative cross-check (not the ratified form, shown to bound the
first-order error): `1/((1-0.06960)(1+0.00116)) x 1.01057 = +8.49%` and
`1/((1+0.08040)(1-0.00134)) x 0.98943 = -8.30%`. The linear sum is the more
conservative of the two on the down leg and within 0.6 points on the up
leg; the linear sum is ratified, matching 0002's convention.

| Stage | Target | Covers | Does NOT cover |
|---|---|---|---|
| **Free-running, untrimmed** | ±35% first-order (−27.7%/+47.6% exact), sourced | process-corner spread at fixed T/V | temperature and supply drift on top of this |
| **Free-running, post-trim, at calibration point** | ±1.1% (T = 27 °C, process, VDD ±10%) | process spread (absorbed by the one-time trim) + residual trim/mismatch/offset/supply terms | any temperature excursion away from 27 °C |
| **Free-running, post-trim, full temperature range** | **+8% / −9%** (−40…+85 °C, VDD ±10%) | the above, plus the sourced −1200 ppm/K resistor TCR term | continuous correction — a single-point trim cannot track temperature after trim |
| **Runtime-disciplined** (reserved, still not designed) | ≤ ±0.25% (2,500 ppm) — USB full-speed compliance | closes the gap from the free-running figure to USB's tolerance | not designed in this repo yet |

**Ratified: ±1.1% at the calibration point; +8% / −9% over −40…+85 °C.**
The ±2% figure ratified in 0002 is withdrawn: it is not reachable with a
single-point trim on an uncompensated gf180mcu RC network, by that PDK's
own published TCR.

### Row 4 — Quiescent current: < 200 µA → < 500 µA

`DS9826` Rev 6, §6.3.8, Table 43, read directly:

| Symbol | Parameter | Min | Typ | Max | Unit |
|---|---|---|---|---|---|
| `IDDA(HSI48)` | HSI48 oscillator power consumption | — | **312** | **350** | µA |

0002's `< 200 µA` target is **43% below ST's typical** and 57% below its
max, on a shipped, production-qualified 48 MHz RC oscillator built on a
finer geometry than gf180mcu's 180 nm. 0002 flagged that target as having
"no specific shipped-part Iq figure … independently verified" and called it
"deliberately … conservative"; with the figure now in hand it is the
opposite of conservative. Claiming to beat a finer-node vendor's shipped
part by ~1.75× with no design basis is the same unbacked-claim failure mode
CLAUDE.md warns about.

**Ratified: < 500 µA (running).** That is ~1.43× ST's max and ~1.60× ST's
typ — the same order of magnitude, with headroom for a node roughly two
generations older. This is an explicit engineering target, not a
measurement, and remains subject to schematic-phase confirmation.

### Rows confirmed, not changed

These 0002 rows were re-checked against primary text and stand as ratified;
the flags on them are cleared but the values do not move.

- **USB full-speed tolerance = ±0.25% (2,500 ppm).** USB 2.0 Rev 2.0
  §7.1.11, verbatim: *"The full-speed data rate is nominally 12.000 Mb/s.
  For full-speed only functions, the required data-rate when transmitting
  (TFDRATE) is 12.000 Mb/s ±0.25% (2,500 ppm)."* (High-speed: ±0.05%/500
  ppm; low-speed: ±1.5%/15,000 ppm — same clause.) **This resolves 0002's
  own flagged open question** about whether the clause distinguishes
  pre- from post-discipline tolerance: it does not. The clause continues,
  verbatim: *"The above accuracy numbers include contributions from all
  sources: Initial frequency accuracy; Crystal capacitive loading; Supply
  voltage on the oscillator; Temperature; Aging."* It is a single,
  continuously-required transmit-accuracy figure covering temperature and
  supply — so a compliant design must hold ±0.25% across the whole
  operating range, not merely at a calibration point. 0002's working
  assumption (that ±0.25% is the figure reached *with* runtime discipline,
  and that a free-running RC oscillator is not expected to meet it alone)
  is confirmed as the correct reading, and is now load-bearing rather than
  provisional: with this record's +8%/−9% free-running figure, runtime
  discipline is not an optional refinement, it is the only path to
  compliance.
- **Startup time ≤ 10 µs.** `DS9826` Rev 6 Table 43: `tsu(HSI48)` ≤ **6 µs**
  max (guaranteed by design). 0002's ≤ 10 µs target is looser than the
  shipped precedent and stands, now with a real citation.
- **Target frequency 48.000 MHz.** Confirmed independently by two vendors:
  `DS9826` Table 43 `fHSI48` typ = 48 MHz, and CP2102N Rev 1.5 Table 3.5
  `fOSC` typ = 48 MHz ("Integrated clock; no external crystal required",
  "USB 2.0 full-speed compatible").
- **SOF-based runtime discipline is real and precedented.** `RM0091` Rev
  10 §7.1, verbatim: *"The clock recovery system (CRS) is an advanced
  digital controller acting on the internal fine-granularity trimmable RC
  oscillator HSI48 … The CRS is ideally suited to provide a precise clock
  to the USB peripheral. In such case, the synchronization signal can be
  derived from the start-of-frame (SOF) packet signalization on the USB
  bus, which is sent by a USB host at 1 ms intervals."* §6.2.3, verbatim:
  *"When the CRS is not used, the HSI48 RC oscillator runs on its default
  frequency which is subject to manufacturing process variations, this is
  why each device is factory calibrated by ST for ~3% accuracy at
  T_A = 25 °C."* 0002's flagged vendor-precedent citations are hereby
  confirmed as numeric citations, not merely as recollections.

## Alternatives considered

- **Edit 0002 in place.** Rejected — `spec/README.md` and CLAUDE.md both
  require append-only supersession. 0002 is the honest record of a decision
  made on weaker evidence and its flags are what made this correction
  findable; erasing them would erase the mechanism that worked.
- **Keep the ±2% post-trim target and treat the TCR data as pessimistic.**
  Rejected — this is exactly "relax the evidence to make the spec pass,"
  inverted. −1200 ppm/K is gf180mcu's own published worst-case corner for
  its *best*-characterized resistor flavor; the alternative flavor is
  worse, and the standard §5.1 poly resistors publish no TCR at all. There
  is no reading of the PDK's own data on which ±2% survives an uncompensated
  single-point trim.
- **Keep ±2% by ratifying active TC compensation here.** Rejected — that is
  a topology decision with real circuit cost, and this record has no
  evidence about what compensation is achievable on gf180mcu devices.
  Ratifying a target that *presumes* an undesigned mechanism is how 0002's
  ±1.00% temperature row got its number. Left as an explicit open item
  below instead.
- **Set the trim range from the exact +47.6% frequency excursion rather
  than the ±35% first-order figure.** Rejected as the *headline* framing
  (it would suggest a ±48% range) but adopted as the *sizing* basis: the
  required correction is the mirror of the RC spread (−32.3%/+38.4%), not
  of the frequency spread, and ±40% covers it. Both figures are stated
  above so a reader cannot conflate them.
- **Go to 9 bits of trim to recover the LSB lost to the wider range.**
  Rejected — quantization stays at 14.8% of the at-calibration budget at 8
  bits and is not the limiting term; the extra bit buys ~0.08% of budget
  for a real cost in trim-bank elements and decode. 0002's own criterion
  ("the point where quantization stops being a first-order contributor")
  still selects 8.
- **Round Iq to `< 400 µA` rather than `< 500 µA`.** Rejected — 400 µA is
  only 1.14× ST's 350 µA max, which reintroduces the same problem in
  smaller form: an implicit claim of near-parity with a finer-node shipped
  part, on a 180 nm process, with no design to back it.
- **Also loosen the ±1.1% at-calibration figure to match ST's shipped
  `ACC_HSI48` at 25 °C (−2.8%/+2.9%).** Rejected as out of scope for this
  record, but flagged loudly below — it is the most likely next correction.

## Consequences

- `README.md`'s "Target specification" table is updated for these four rows
  and now cites this record alongside 0002. `spec/README.md`'s index gains
  a row for 0003 and annotates 0002 as partially superseded; **0002's own
  file is unchanged, including its Status field**, per the reasoning in
  "Context".
- **The headline accuracy story changes shape.** This block can no longer
  be described as "±2% free-running." It is ≈±1% *at its calibration
  temperature* and roughly ±8–9% *across the industrial temperature range*.
  Any downstream text, README, or external claim that quotes a single
  free-running accuracy number without naming the temperature condition is
  now wrong. This is a materially weaker claim than 0002's and is stated as
  such rather than averaged away.
- **OPEN ITEM, explicitly NOT resolved by this record: active
  temperature-coefficient compensation.** The schematic phase must choose
  one of two paths, and this record deliberately declines to choose:
  1. **Add active TC compensation** — a compensated bias/reference, a
     resistor-flavor ratio cancelling first-order TC, or a
     temperature-aware trim — targeting a full-range figure approaching
     the at-calibration ≈±1%, at real cost in area, current, and design
     risk.
  2. **Accept ≈+8%/−9% full-range** and place the entire burden of USB
     compliance on the reserved SOF-style runtime-discipline stage, which
     would then need to close a ~35× gap (from ±9% to ±0.25%) rather than
     0002's assumed ~8× gap (from ±2%).

  0001 assumed only that "some temperature-coefficient mitigation" would
  exist, without committing to a mechanism; that assumption is now
  load-bearing rather than incidental, and a future decision record must
  resolve it before or during schematic entry. **The public evidence
  strongly favors path 1 but does not settle it here.** Silicon Labs'
  CP2102N (Rev 1.5, Table 3.5) specifies `TSOSC` = 45 ppm/°C typ on its
  shipped internal 48 MHz oscillator — **26.7× better than gf180mcu's raw
  −1200 ppm/K poly resistor** — giving ≈0.56% of drift over a 125 K span
  and a total `fOSC` window of 47.3–48.7 MHz (±1.46%) over full temperature
  and supply. Shipped crystal-less-USB oscillators are demonstrably not
  running on an uncompensated RC network's raw TCR. Whether that is
  reachable on gf180mcu devices is precisely what this record has no
  evidence for.
- **Flagged residual credibility risk on the at-calibration ±1.1%.**
  `DS9826` Rev 6 Table 43 gives `ACC_HSI48` = −2.8%/+2.9% at T_A = 25 °C
  for ST's factory-calibrated shipped part — roughly **2.6× looser** than
  the ±1.06% this record ratifies at its calibration point. Three of that
  budget's four rows are still unsourced assumptions inherited from 0002.
  This is the same shape of problem as the Iq row corrected above (a target
  tighter than the shipped precedent it is anchored to), and it is not
  corrected here only because this record's scope is the four rows named in
  issue #3 and because the fix requires trim-bank and comparator design
  data that does not exist yet. **Schematic-phase work must either justify
  beating ST's 25 °C figure or trigger a further superseding record.** It
  is recorded here so it is not rediscovered as a surprise.
- **Full-range plausibility cross-check.** `ACC_HSI48` over −40…+105 °C is
  −4.9%/+4.7% (`DS9826` Table 43, characterization data). This record's
  +8%/−9% over a *narrower* −40…+85 °C range is roughly 1.8× looser than
  ST's shipped part — the expected direction for an older node with no
  committed TC compensation, which supports the figure's plausibility. If
  schematic-phase corner sweeps ever return a full-range figure *better*
  than ST's without an explicit compensation mechanism in the design, that
  result should be treated as suspect and re-verified before it is
  recorded.
- **Trim-bank sizing gets harder.** The bank must now realize a
  ±40% (28.80–67.20 MHz) monotonic range in 256 codes across the full RC
  corner box, with only **1.6 percentage points** of margin on the pull-up
  leg (required +38.40% vs. ratified +40%). That is thinner than the ~5
  points 0002 intended and is a real risk. **A concrete mitigation exists
  and is worth taking:** selecting the 1.0 fF/µm² or 2.0 fF/µm² MIM flavor
  (both ±10%, per §6.2(b)/(c)) instead of the 1.5 fF/µm² flavor (±15.33%)
  reduces the required pull to −28.00%/+32.00%, restoring 8 points of
  margin on both legs. That is a schematic-phase device-selection decision,
  not ratified here, but it is the cheapest available fix and should be
  evaluated first. If a design must use the 1.5 fF/µm² flavor, the ±40%
  range should be re-examined by a superseding record.
- **Corner simulation must be temperature-swept, not just process-swept.**
  With temperature now the dominant term by ~7×, a PVT corner set that
  sweeps process at 27 °C would miss essentially the entire error budget.
  Every accuracy claim recorded in `sim/` must state its temperature.
- **What is invalidated.** No simulation or layout work is invalidated —
  none exists; this repo is pre-schematic, which is why correcting now is
  cheap. What is invalidated is any design plan sized against ±35% of trim
  range, ±2% of post-trim accuracy, or a 200 µA current budget.
- **What is not settled.** The runtime-discipline (SOF-correction) stage
  remains reserved and undesigned, as in 0002 — but the gap it may have to
  close is now up to ~35×, not ~8×, which makes the compensation question
  above materially more urgent than 0002 implied.
- If schematic-phase corner sweeps show any figure in this record is
  materially wrong, the fix is a further superseding decision record — not
  a silent edit to this record, to 0002, or to the ratified `README.md`
  table.
