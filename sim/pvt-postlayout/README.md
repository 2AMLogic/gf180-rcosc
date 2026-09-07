# sim/pvt-postlayout — post-layout (PEX-extracted) PVT re-verification (issue #28)

Per `CLAUDE.md` ("Verification is the product... `sim/` results are
append-only evidence"), this directory holds the post-layout counterpart to
`sim/pvt/`'s schematic-level PVT campaign: the same corner-endpoint subset
(process = `tt`/`ff`/`ss` x temperature = -40/+27/+85 C x
VDD = 3.0/3.3/3.6 V, 27 points) re-simulated against a parasitic-annotated
netlist extracted from the full-hierarchy `layout/cells/rcosc_top.gds`
(issue #27), at the fixed post-#24 (DR-0009) single-code post-trim
methodology's own calibration code.

```
sim/pvt-postlayout/
  README.md               this file
  pex_pvt_sweep.py         the driver (issue #28)
  run-pex-pvt-sweep.sh     wrapper: regenerates netlists, then runs pex_pvt_sweep.py
  corners/<runid>/         raw ngspice logs, one per (side, operating point)
  results/<runid>/         results.csv, manifest.json, summary.md, plus the
                            extracted netlist (rcosc_top.pex.spice) and the
                            `klt extract` JSON report -- exactly what was
                            compared, committed as evidence
```

**Regenerate / extend the evidence**:

```bash
# Requires: ngspice, xschem, klt, python3, and a gf180mcuC PDK resolvable
# the same way design/regen-netlist.sh resolves it.
sim/pvt-postlayout/run-pex-pvt-sweep.sh
sim/pvt-postlayout/run-pex-pvt-sweep.sh --jobs 8
```

## Methodology

Each of the 27 points is simulated **twice**, sharing everything (the
`design/netlist/pvt_tb.spice` harness -- VDD/VT0..VT7 sources, transient
measurement window) except the DUT body:

- **schematic side**: `design/netlist/pvt_tb.spice` unmodified -- the exact
  netlist `sim/pvt/pvt_sweep.py` itself simulates.
- **extracted side**: the same harness with only the embedded
  `.subckt rcosc_top ... .ends` region swapped for `klt extract
  --parasitics`'s own output (header pin order rewritten to match, see
  `pex_pvt_sweep.py`'s `reorder_extracted_header` docstring).

## Why not `klt pex` / `klt sim` request JSON files verbatim

`klt pex --help` (confirmed on the installed build, `klt 0.4.0`) is real and
does exactly what its docstring says: "extract a parasitic-annotated
netlist from a routed layout (`klt extract --parasitics`), re-run one or
more `klt sim` testbench requests against it per corner, and report a
per-corner, per-spec-row schematic-vs-extracted delta." It was not used
directly here for two concrete, checked reasons:

1. **No `--deck-option`/`--pins` passthrough.** `klt extract` (the
   subcommand `klt pex` drives internally) accepts `--deck-option
   poly_res=1k --deck-option mim_cap=cap_mim_1f0_m4m5_noshield` to select
   the exact resistor sheet-rho and MiM-cap density this design commits to
   (`layout/run_checks.sh`, DR-0003 sec 5.1/6.1) -- `klt pex`'s own
   `--help` output has no equivalent flags. `poly_res` happens to default
   to this design's `1k` choice, but `mim_cap` defaults to
   `cap_mim_2f0_m4m5_noshield` (2x this design's actual 1.0 fF/um^2
   density) -- running `klt pex` directly would silently extract the
   *wrong* MiM-cap density for this design's own drawn timing capacitor,
   invalidating every delta it reports. Confirmed by reading
   `klayout_tools/decks/gf180mcu.py`'s own flavour-default documentation,
   not assumed.
2. Even with that gap fixed, `klt sim`'s request-JSON `corners.supply_v`
   axis only supports `alter <source>=<value>` (an independent-source
   magnitude), not a `.param` sweep -- and this testbench's `.meas ...
   when v(clk)=<vdd/2> rise=N` threshold needs the VDD value at `.meas`-card
   authoring time, not post-elaboration. Reusing `sim/pvt/pvt_sweep.py`'s
   own already-proven deck composition (`compose_deck`, run per point) both
   sidesteps this and is the literal "reuse `sim/pvt/`'s existing
   testbench/sweep infrastructure" the issue asks for.

`klt extract --parasitics` (the extraction half) **is** used directly, with
the correct deck options -- see `pex_pvt_sweep.py`'s `run_extract`. Both
gaps above, plus a third (`klt extract --pdk <variant> --parasitics`
annotating its one recognised MiM-cap *device* card with a non-numeric,
non-`.model`-backed flavour-name token that ngspice's native `C`-element
parser refuses to parse -- see `pex_pvt_sweep.py`'s
`CAP_MODEL_TAG_RE`/`strip_capacitor_model_annotations` docstring for the
full mechanism and the one-line fix applied here) were filed as friction
against `2AMLogic/klayout-tools` per `CLAUDE.md`'s friction protocol
(tool-generic description, no design-specific detail):
[2AMLogic/klayout-tools#1558](https://github.com/2AMLogic/klayout-tools/issues/1558).

## Committed runs

| Run id | Notes |
|---|---|
| [`20260907T131703Z`](results/20260907T131703Z/summary.md) | First post-layout PEX PVT re-verification (issue #27's `rcosc_top.gds`, issue #28). 27-point corner-endpoint subset, both sides, 0 failed runs. **Materially diverges**: schematic-vs-extracted delta is negative (slower) at every point, -1.88% to -29.52%, exceeding the +-1.1% calibration-point accuracy budget on its own. See [DR-0010](../../spec/decision-records/0010-postlayout-pex-pvt-frequency-shift.md). |
