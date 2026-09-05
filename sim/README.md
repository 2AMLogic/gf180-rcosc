# sim — verification evidence (append-only)

Per `CLAUDE.md` ("Verification is the product: no claim without a
testbench... `sim/` results are append-only evidence"), everything under
this directory is a dated, immutable record of a simulation run. **Never
overwrite or edit a prior run's raw output** — a re-run adds a new,
timestamped directory alongside the old one, never in place of it.

```
sim/
  README.md              this file
  pvt/
    pvt_sweep.py          the PVT-corner campaign driver (issue #12)
    run-pvt-sweep.sh      wrapper: regenerates netlists, then runs pvt_sweep.py
    corners/<runid>/      raw ngspice logs, one file per simulated operating point
    results/<runid>/      results.csv, manifest.json, summary.md for that run
```

`<runid>` is a UTC timestamp (`YYYYMMDDTHHMMSSZ`) assigned at invocation
time. The driver refuses to start if a run id's directories already exist
and are non-empty, so a re-run can never clobber committed evidence.

## PVT-corner campaign (issue #12)

`sim/pvt/pvt_sweep.py` runs the full process x temperature x supply
factorial against `design/netlist/pvt_tb.spice` (derived from
`design/pvt_tb.sch` by `design/regen-netlist.sh`) and records every point's
measured frequency as append-only evidence.

**Regenerate / extend the evidence**:

```bash
# Requires: ngspice, xschem, python3, and a gf180mcuC PDK resolvable the same
# way design/regen-netlist.sh resolves it (PDK_ROOT env var, or `klt pdk find`).
sim/pvt/run-pvt-sweep.sh                # full campaign, a fresh runid
sim/pvt/run-pvt-sweep.sh --jobs 8       # limit parallel ngspice processes
sim/pvt/run-pvt-sweep.sh --keep-build   # keep the generated per-run decks under sim/build/<runid>/
```

**Sweep matrix** (full factorial, every combination simulated):

- **Process** (7 corners): `tt`, `ff`, `ss`, `fs`, `sf` (gf180mcuC's
  standard FET corners, each paired with the matching or typical
  resistor/MIM-cap corner) plus `rc_f`/`rc_s` (typical FETs, only the
  poly-resistor and MIM-cap corner moved) — the module split
  [DR-0003](../spec/decision-records/0003-pdk-sourced-process-spread-tcr-and-iq.md)'s
  ±35% untrimmed-spread derivation is sized from.
- **Temperature**: −40 °C, +27 °C, +85 °C.
- **Supply**: 3.0 V, 3.3 V, 3.6 V.

**Passes, every run**: a realized trim curve at the nominal reference
corner (`tt`/27 °C/3.3 V); single-point trim calibration (binary search per
process corner) against both the ratified 48.000 MHz target and a
surrogate target (see below); a pre-trim full factorial at a fixed
mid-scale code; and two post-trim full factorials — one holding the single
code the *reference* corner calibrated to (the literal single-point
methodology the ratified spec assumes), one holding each corner's own
per-corner calibrated code (the "trim every die at test" model). **Both
post-trim passes are reported together, and the full-temperature-range
figure is always reported alongside the calibration-point figure, never
alone** — per the acceptance criteria for issue #12.

**Why a surrogate calibration target exists**: the current schematic
(`design/rcosc_top.sch`, unchanged since DR-0004) does not reach anywhere
close to the ratified 48.000 MHz target at any simulated corner — see
[`spec/decision-records/0005`](../spec/decision-records/0005-pvt-campaign-frequency-shortfall-spec-unchanged.md)
for the full evidence and disposition. Calibrating against the unreachable
ratified target saturates every corner's trim code at `0xFF`, which would
make every "post-trim" pass degenerate into the pre-trim spread. The
surrogate target (the reference corner's own realized frequency at the
mid-scale code) is simulated *in addition to* the ratified-target pass so
the single-point trim methodology can still be exercised meaningfully; both
are reported, and neither silently substitutes for the other.

Every committed run's `results/<runid>/summary.md` states, for each
ratified spec row, the simulated value and an explicit met/exceeds verdict
against `README.md`'s target-spec table — see
[DR-0005](../spec/decision-records/0005-pvt-campaign-frequency-shortfall-spec-unchanged.md)
for the campaign's overall disposition of those verdicts.

## Committed runs

| Run id | Notes |
|---|---|
| [`20260905T211140Z`](pvt/results/20260905T211140Z/summary.md) | First full campaign against the DR-0004 schematic (issue #12). 210 unique operating points, 0 failed measurements, 49.5 minutes wall clock at 16 parallel jobs (gf180mcuC, ngspice-46). See [DR-0005](../spec/decision-records/0005-pvt-campaign-frequency-shortfall-spec-unchanged.md) for the resulting spec-compliance disposition. |
