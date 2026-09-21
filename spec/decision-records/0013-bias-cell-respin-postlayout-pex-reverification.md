# 0013: Bias-cell layout re-spin against the post-#39 schematic + post-layout (PEX) PVT re-verification — DR-0010 superseded for the re-spun GDS, ratified rows unchanged

- **Status**: Ratified — records layout and verification evidence. Supersedes
  [0010](0010-postlayout-pex-pvt-frequency-shift.md)'s post-layout figures
  **for the re-spun hierarchy**: DR-0010 remains the valid post-layout
  characterization of the *pre-#39* `rcosc_bias` GDS (issue #13's cell) and
  must not be quoted against the post-#39 schematic. Does not supersede any
  ratified spec-table row of
  [0002](0002-target-spec-ratification.md)/[0003](0003-pdk-sourced-process-spread-tcr-and-iq.md);
  re-executes and retires the "layout consequence" paragraph of
  [0012](0012-comparator-bias-path-pvt-revision.md) (this issue, #44).
- **Date**: 2026-09-21
- **Decided by**: Builder agent, issue #44

## Context

DR-0012 re-architected `design/rcosc_bias.sch` to the self-biased
beta-multiplier current reference (issue #39) *after* the committed layout
had been drawn and post-layout-verified against the pre-#39 schematic: the
`rcosc_bias` GDS, DR-0010's PEX PVT figures, and every pin they produced
described a schematic revision that no longer existed on `main`. DR-0012
blocked quoting DR-0010's figures against the post-#39 schematic until the
re-spin landed (issue #44). Issue #39 deliberately kept the trim bank,
comparator, and top-level schematics untouched, so those cells' committed
GDS, DRC/LVS, and PEX evidence were to stay out of this re-spin's blast
radius.

## Decision

**The `rcosc_bias` cell is re-drawn against the post-#39
`design/netlist/rcosc_top.spice` device set and the whole hierarchy is
re-verified (DRC + LVS + supply ERC + PEX PVT). No ratified spec-table row's
disposition changes: the post-trim accuracy rows this evidence bears on were
already `exceeds` at the schematic level in every campaign since DR-0005,
and this record adds the re-spun layout's own post-layout finding on top —
it does not flip, relax, or close any of them.**

The re-spin at a glance (all numbers from `layout/reports/`,
`layout/reports/rcosc_top.erc.json`, and
`sim/pvt-postlayout/results/20260921T164434Z/`):

- **Cell**: same `klt gen` primitive flow (`layout/build_cells.py`, issue
  #13's composer), same sub-cell boundary (`vdd vss vh vl ibias`, unchanged
  order). The core's make-up forced the one structural change the old cell
  did not have: `pb` (the PMOS gate bus) must reach five terminals across
  the cell and `vl` must reach `SEED`'s gate across them, which is not
  planar in metal1 — so the cell is routed on `gen_lib.Channel`'s two-layer
  discipline (metal1 columns, metal2 tracks) exactly as
  `rcosc_comparator` is (issue #27), and `P1`/`P2` share one drawn n-well
  with a `well_island` tap on `vdd` for the same reason the comparator's
  PMOS group does. `rcosc_bias`'s own `klt lvs` run therefore gains
  `options.combine_devices: ["nfet"]` (folds `N2`'s eight drawn fingers
  into the reference's single wide card), matching the comparator's
  already-disclosed arrangement in `layout/run_checks.sh`.
- **DRC/LVS**: `rcosc_bias` and the recomposed `rcosc_top` are DRC `clean`
  (0 violations each) and LVS `match` against the regenerated references
  (bias: 0 tolerated deltas; top: the same 6 `device.parameter_tolerated`
  trim-bank grid-rounding entries + 1 `topology.flattened` as before — the
  bias cell contributes none). The trim bank, comparator, and their
  committed per-cell reports are untouched and byte-reproducible under the
  recorded toolchain (below).
- **Supply ERC (T1 item 11)**: still one electrical island per supply
  (zero `erc.unconnected_net` / `erc.supply_short` /
  `erc.multiply_driven_net` findings naming a supply) and — since the
  tie declaration #42/#46 landed on `main` mid-re-spin, giving the spec a
  `ties[]` n-well tap entry — zero `erc.missing_tie` as *computed,
  graded* evidence: the re-spun core's `P1`/`P2` drawn well with its
  `well_island` tap is a third merged well polygon the check covers
  alongside the comparator's and the latch's. `erc.floating_gate`
  artifacts rise 32 → **36** on the re-spun GDS — the re-spun core's
  contacted gates (N1, N2's folded gate rail, P1, P2, SEED replacing
  MBIASD's one gate), still the disclosed `Contact`-omission artifact
  (klayout-tools#2183) that item 11's own text pre-declares non-blocking.
  The erc was re-run with the #46 spec against the re-spun GDS, so its
  envelope pins both the new GDS and the declared-tie spec.
- **Post-layout PEX re-verification** (`sim/pvt-postlayout/results/
  20260921T164434Z/`, issue #28's flow unchanged): 27-point corner-endpoint
  subset × 2 sides = 54 runs, 0 failed, 203.4 s at 8 jobs, at the
  post-revision schematic campaign's own calibration code `0xD0` (auto-read
  from [`sim/pvt/results/20260921T075822Z`](../sim/pvt/results/20260921T075822Z/) —
  DR-0012's campaign — not the pre-#39 `0xC0`). **The re-spun layout still
  runs slower than the schematic at all 27 points: delta −11.24 % …
  −41.42 %** (mean −19.56 %), worst at `ff`/−40 °C/3.6 V — the same
  always-slower sign and the same ff-cold-high-VDD worst-corner signature
  DR-0010 reported, now materially deeper (DR-0010 against the pre-#39
  pair: −1.88 % … −29.52 %, mean −10.32 %, at `0xC0`). The in-run
  schematic-side cross-check against the committed post-#39 campaign bounds
  host/run noise at 0.00 % at matched points, so the finding is not noise.
- **Interpretation**: DR-0010's mechanism stands — a first-order
  lumped-RC model adding real capacitance to an RC-timed core's switching
  nodes lengthens the period — and the deepening is the expected cost of
  the new core: more devices and real wiring on `ibias`/`pb`/`n2s` inside
  the bias cell, on a core the schematic-level campaign showed is the more
  supply-robust but *slower-running* one. Nothing here contradicts
  DR-0012's schematic-level results; the post-layout penalty on top of them
  is simply larger than the pre-#39 layout's. The ±1.1 % calibration-point
  budget remains unmeetable from layout parasitics alone, same as before
  the re-spin.

**Toolchain provenance (load-bearing for reproducibility).** Every
committed per-cell report records `klt 0.4.0` / `klayout 0.30.12`, and
under exactly that pair the unchanged cells rebuild byte-identically
(verified for `rcosc_trim_bank` and `rcosc_comparator` before the re-spin:
fresh `sha256` == committed), and this issue's regenerated bias/top
evidence is produced by the same pair; the newer pinned erc/grading
environment (`klt 0.5.0+g2b1e55e51bb8` with klayout 0.30.12 — the same
version string the committed `rcosc_top.erc.json` already records) is used
only where 0.4.0 cannot go: the `klt erc` run and `klt signoff` re-grading.
Current newer `klayout-tools` generation code (the 0.5.0-era and later)
renders different `res_array` footprints/output grid, so
`layout/build_cells.py --check` *stales* the committed cells under it —
the layout's byte-reproducibility is pinned to the 0.4.0-era toolchain its
reports record, which is why this record names it. Filed as friction
against `2AMLogic/klayout-tools` per CLAUDE.md's protocol (gen output
stability across versions, no generator-revision stamp):
[klayout-tools#2246](https://github.com/2AMLogic/klayout-tools/issues/2246).

## Alternatives considered

- **Quoting DR-0010 as-is and skipping the re-verification.** Rejected:
  DR-0012 explicitly blocked DR-0010's figures against the post-#39
  schematic; issue #44's deliverables exist because a re-spin without a
  PEX re-verification would leave the evidence chain asserting figures
  from a GDS that no longer matches its own schematic.
- **Also re-spinning the trim-bank switches (issue #43) in one combined
  campaign.** Considered by the issue itself (its own edge-case note) and
  rejected at build time: #43 was still in flight (`loom:building`) when
  this pass started, so no combined campaign was possible without waiting
  on or duplicating another worker's cell; the combined re-spin remains
  #43's call to make when it lands.
- **Re-deriving `docs/chipalooza/challenge-5-proposal.md`'s §4 rows from
  the post-#39 + post-re-spin evidence chains.** Rejected as out of scope:
  the proposal's pinned sections already describe the pre-#39 evidence by
  earlier design (DR-0012's landing likewise did not rewrite it), and a
  wholesale characterization-record refresh that picks up every DR since
  it was frozen is its own tracked follow-up —
  [#47](https://github.com/2AMLogic/gf180-rcosc/issues/47) — not something
  to fold into a layout-re-spin PR.

## Consequences

- `layout/cells/rcosc_bias.gds`, `layout/cells/rcosc_top.gds`,
  `layout/lvs_ref/rcosc_bias.spice`, `layout/lvs_ref/rcosc_top.spice`,
  and the bias/top set of `layout/reports/*` are regenerated; the trim
  bank's and comparator's committed cells and per-cell evidence are
  unchanged (byte-verified).
- `signoff/block-manifest.json`'s T1 item-2/item-3 pins **and the
  item-11 compound citation's erc pin** (the tie-declaration item
  [#42](https://github.com/2AMLogic/gf180-rcosc/issues/42)/PR #46 landed
  while this re-spin was in review — item 11 grades `met` on a compound
  erc+lvs citation, and both parts are re-verified against the re-spun
  evidence), and the graded `signoff/signoff-report.json`, are refreshed
  per signoff/README.md's refresh contract (regenerate → re-pin from the
  envelopes' provenance → re-grade → `verify-report.py` passes — still
  5/11 T1 items met, the erc/lvs evidence behind the merged-verdict rows
  now pinning the re-spun GDS).
- **DR-0010 is superseded for the post-#39 schematic**: quote this record
  (and `sim/pvt-postlayout/results/20260921T164434Z/`) for post-layout
  figures from now on. The status paragraphs in `README.md`,
  `design/README.md`, `layout/README.md`, `sim/pvt-postlayout/README.md`,
  and `sim/README.md`'s campaign index are updated accordingly.
- The upstream friction issue
  ([klayout-tools#2246](https://github.com/2AMLogic/klayout-tools/issues/2246))
  records the toolchain-stability gap so the next re-spin does not
  re-derive this archaeology (gen output changed between `klt` releases
  with no version-selection mechanism for layout reproducibility).
- Closing the post-trim accuracy gap must budget the same order of
  layout-parasitic frequency penalty DR-0010 warned about — now ~−20 %
  mean across the corner subset rather than ~−10 % — on top of the
  schematic-level residuals DR-0012 leaves. Any future layout compaction
  or critical-net extraction pass that wants to shrink this penalty needs
  its own record with before/after PEX campaigns.
