# 0015: Trim-bank layout re-spin against the post-#43 schematic + post-layout (PEX) PVT re-verification — DR-0010/DR-0013 superseded for the re-spun GDS, ratified rows unchanged

- **Status**: Ratified — records layout and verification evidence. Supersedes
  [0010](0010-postlayout-pex-pvt-frequency-shift.md)'s and
  [0013](0013-bias-cell-respin-postlayout-pex-reverification.md)'s post-layout
  figures **for the re-spun hierarchy**: DR-0010 remains the valid post-layout
  characterization of the *pre-#39* `rcosc_bias` GDS (issue #13's cell) and
  DR-0013 of the *post-#39, pre-#43* pair (issue #44's re-spin), and neither
  may be quoted against the post-#43 schematic. Does not supersede any
  ratified spec-table row of
  [0002](0002-target-spec-ratification.md)/[0003](0003-pdk-sourced-process-spread-tcr-and-iq.md);
  re-executes and retires the "layout consequence" paragraph of
  [0014](0014-trim-bank-pass-switch-restructure.md) (this issue, #50).
- **Date**: 2026-09-22
- **Decided by**: Builder agent, issue #50

## Context

Issue #43 restructured `design/rcosc_trim_bank.sch`'s per-bit shunts from
single NFET pass switches to transmission gates with locally inverted pfet
gates ([DR-0014](0014-trim-bank-pass-switch-restructure.md)) *after* the
committed layout had been drawn and post-layout-verified against the
pre-#43 schematic: the `rcosc_trim_bank` GDS, its LVS reference, and —
because `rcosc_top.gds` instantiates the cell — the top-composition
geometry and every DRC/extract/LVS/ERC report under `layout/reports/`
described a schematic revision that no longer existed on `main` (exactly
the stale-cell shape DR-0012 had left the bias cell in before #44's
re-spin). DR-0014 blocked quoting DR-0010's/DR-0013's post-layout figures
against the post-#43 trim tree until this re-spin landed (issue #50).
Issue #43 deliberately froze the `ppolyf_u_1k` segment values
(`RFIX`/`R0..R7`) and touched no cell other than the trim bank (the top
gains only the wired `vdd` pin), so the bias and comparator cells, their
committed GDS, and their per-cell evidence were to stay out of this
re-spin's blast radius.

## Decision

**The `rcosc_trim_bank` cell is re-drawn against the post-#43
`design/netlist/rcosc_top.spice` device set and the whole hierarchy is
re-verified (DRC + LVS + supply ERC + PEX PVT). No ratified spec-table
row's disposition changes: the post-trim accuracy rows this evidence bears
on were already `exceeds` at the schematic level in every campaign since
DR-0005, and this record adds the re-spun layout's own post-layout finding
on top — it does not flip, relax, or close any of them.**

The re-spin at a glance (all numbers from `layout/reports/`,
`layout/reports/rcosc_top.erc.json`, and
`sim/pvt-postlayout/results/20260922T004322Z/`):

- **Cell**: same `klt gen` primitive flow (`layout/build_cells.py`, issue
  #13's composer), same sub-cell boundary plus the new pin
  (`p m vss t0..t7 vdd` — `vdd` new, `vss` back to being a real routed net
  as the per-bit inverter nfets' source terminal, where pre-#43 it was a
  bulk-only tie the LVS reference modeled as `vsubs` and dropped). The
  restructure forced the one structural change the old cell did not have:
  `tb<i>` must reach each `PW<i>`'s gate across every c-node column
  between the per-bit inverter and the pfet group, and `vdd`/`vss` must
  cross the `t<i>` columns, which is not planar in metal1 — so the cell is
  routed on `gen_lib.Channel`'s two-layer discipline (metal1 columns,
  metal2 tracks) exactly as `rcosc_comparator` (issue #27) and the
  re-spun `rcosc_bias` (#44) are, and all sixteen PMOS (the eight
  transmission-gate pfets and the eight inverter pfets) share one drawn
  n-well with a `well_island` tap on `vdd`, for the same reason the
  comparator's PMOS group does. The reference netlist's MOS cards are
  emitted with normalized `W`/`L` micrometre literals because the
  post-#43 schematic spells the transmission-gate widths with xschem's
  double-u suffix (`W=24uu`), a spelling `klt`'s reference normalizer is
  not documented to accept — `24u` is the same value in the canonical
  spelling. The recomposed `rcosc_top` also fixes a latent mapping bug the
  new pin exposed: `build_rcosc_top`'s sub-cell pad table was keyed by
  top-level net, and the trim bank now exports two pins that land on the
  top's `vdd` (`p` and `vdd`) — one pad's coordinates silently overwrote
  the other's, leaving the ladder end unrouted; the table is a list of
  (net, pad) pairs now.
- **DRC/LVS**: `rcosc_trim_bank` and the recomposed `rcosc_top` are DRC
  `clean` (0 violations each) and LVS `match` against the regenerated
  references (trim bank: the same 6 `device.parameter_tolerated`
  grid-rounding entries the pre-#43 cell disclosed; top: those 6 + 1
  `topology.flattened`, unchanged shape). The extraction's cross-check
  against the schematic's own port list — not just LVS-clean status, the
  edge case the issue called out — confirms 12 pins on the re-spun cell
  (`p m vss t0..t7 vdd`, the post-#43 `.subckt` order) and 41 devices
  (9 `ppolyf_u_1k` + 8 `SW` + 8 `PW` + 8 `NINV` + 8 `PINV`), and the
  top-level envelope records 95 devices / 45 nets / 11 pins. The bias and
  comparator cells and their committed per-cell reports are untouched and
  byte-reproducible under the recorded toolchain (below).
- **Supply ERC (T1 item 11)**: still one electrical island per supply
  (zero `erc.unconnected_net` / `erc.supply_short` /
  `erc.multiply_driven_net` findings naming a supply) and zero
  `erc.missing_tie` as *computed, graded* evidence: the re-spun trim
  bank's sixteen-pfet drawn well with its `well_island` tap is a fourth
  merged well polygon the check covers alongside the comparator's, the
  latch's, and the bias core's. `erc.floating_gate` artifacts rise
  36 → **60** on the re-spun GDS — the re-spun trim bank's 24 additional
  contacted gates (`PW<i>`/`NINV<i>`/`PINV<i>` beside the eight `SW<i>`
  the pre-#43 cell already had) — still the disclosed
  `Contact`-omission artifact (klayout-tools#2183) that item 11's own
  text pre-declares non-blocking.
- **Post-layout PEX re-verification**
  (`sim/pvt-postlayout/results/20260922T004322Z/`, issue #28's flow
  unchanged): 27-point corner-endpoint subset × 2 sides = 54 runs, 0
  failed, 338.0 s at 8 jobs, at the post-#43 schematic campaign's own
  ratified-target calibration code `0x9D` (auto-read from
  [`sim/pvt/results/20260921T173529Z`](../sim/pvt/results/20260921T173529Z/)
  — DR-0014's campaign — not the pre-#43 `0xD0`). **The re-spun layout
  still runs slower than the schematic at all 27 points: delta
  −17.46 % … −40.92 %** (mean −27.32 %), worst at `ff`/−40 °C/3.6 V —
  the same always-slower sign and the same ff-cold-high-VDD worst-corner
  signature DR-0010/DR-0013 reported, deeper on the mean than the
  pre-#43 pair (DR-0013: −11.24 % … −41.42 %, mean −19.56 %, at `0xD0`)
  with a slightly narrower worst point. The in-run schematic-side
  cross-check against the committed post-#43 campaign bounds host/run
  noise at 0.18 % at matched points — an order of magnitude smaller than
  the deltas reported, so the finding is not noise.
- **Interpretation**: DR-0010's mechanism stands — a first-order
  lumped-RC model adding real capacitance to an RC-timed core's switching
  nodes lengthens the period — and the deepened mean is the expected cost
  of the restructure: the transmission-gate shunts sit directly on the
  timing ladder's nodes with per-position widths up to 24 µm (gate +
  diffusion capacitance the pre-#43 single 4 µm nfets did not carry
  there), plus the eight inverter pairs' wiring on the `tb` buses. The
  trim-range and accuracy verdicts DR-0014 reports are schematic-level
  findings and are untouched by this penalty; the ±1.1 %
  calibration-point budget remains unmeetable from layout parasitics
  alone, same as before the re-spin.

**Toolchain provenance (load-bearing for reproducibility).** Every
committed per-cell report records `klt 0.4.0` / `klayout 0.30.12`; under
exactly that pair the unchanged bias/comparator cells rebuild
byte-identically (verified before the re-spin: fresh `sha256` ==
committed) and this issue's regenerated trim/top evidence is produced by
the same pair (`uv run --with klayout==0.30.12 --with klayout-tools==0.4.0`
around `layout/run_checks.sh`); the newer pinned erc/grading environment
(`klt 0.5.0+g2b1e55e51bb8…`, the version string `rcosc_top.erc.json`
records) is used only where 0.4.0 cannot go: the `klt erc` run and
`klt signoff` re-grading. `klt gen`'s drawn output is **not stable across
`klayout-tools` versions** (the 0.5.0-era generators render different
`res_array` footprints and an output grid), so the layout's
byte-reproducibility stays pinned to the 0.4.0-era toolchain its reports
record — [klayout-tools#2246](https://github.com/2AMLogic/klayout-tools/issues/2246).

## Alternatives considered

- **Quoting DR-0013 as-is and skipping the re-verification.** Rejected:
  DR-0014 explicitly blocked DR-0010's/DR-0013's figures against the
  post-#43 trim tree; issue #50's deliverables exist because a re-spin
  without a PEX re-verification would leave the evidence chain asserting
  figures from a GDS that no longer matches its own schematic.
- **Keeping the two-row planar floorplan and routing the restructure in
  metal1 with jumps.** Rejected: the `tb<i>` buses and the two rails cross
  the c-node and `t<i>` terminal runs in both directions; a per-jog
  metal2 escape set is exactly the hand-rolled maze routing
  `gen_lib.Channel` exists to replace, and the bias re-spin (#44) had
  just proven the channel discipline on this PDK.
- **Per-bit pfet wells (one `PW<i>`+`PINV<i>` well per bit, interleaved
  with the NMOS).** Rejected: eight separate well rectangles each need
  their own tap island and `vdd` route to avoid floating bodies, against
  one shared well + one tap for the grouped layout; the comparator's
  grouped-well construction is the established pattern on this block.
- **Re-deriving `docs/chipalooza/challenge-5-proposal.md`'s §4
  schematic-level rows from the DR-0014 campaign.** Rejected as out of
  scope, same as #44's call: the proposal's pinned sections describe the
  frozen evidence by earlier design and a wholesale characterization
  refresh is tracked separately. Only the post-layout divergence note is
  updated here, because DR-0014's block on quoting DR-0013 against the
  post-#43 tree would otherwise leave that note citing superseded
  figures.

## Consequences

- `layout/cells/rcosc_trim_bank.gds`, `layout/cells/rcosc_top.gds`,
  `layout/lvs_ref/rcosc_trim_bank.spice`, `layout/lvs_ref/rcosc_top.spice`,
  and the trim/top set of `layout/reports/*` are regenerated; the bias
  and comparator committed cells and per-cell evidence are unchanged
  (byte-verified).
- `signoff/block-manifest.json`'s T1 item-2/item-3 pins, the item-11
  compound citation's erc pin, the item-8 characterization pin (the
  record's post-layout note is updated per the block above), and the
  graded `signoff/signoff-report.json` are refreshed per
  signoff/README.md's refresh contract (regenerate → re-pin from the
  envelopes' provenance → re-grade → `verify-report.py` passes — still
  5/11 T1 items met).
- **DR-0010 and DR-0013 are superseded for the post-#43 schematic**:
  quote this record (and
  `sim/pvt-postlayout/results/20260922T004322Z/`) for post-layout figures
  from now on. The status paragraphs in `README.md`, `layout/README.md`,
  `sim/pvt-postlayout/README.md`, `sim/README.md`'s campaign index, and
  `signoff/README.md`'s item-2/item-11 counts are updated accordingly.
- Closing the post-trim accuracy gap must budget a ~−27 % mean
  layout-parasitic frequency penalty across the corner subset (worse than
  the ~−20 % DR-0013 left) on top of the schematic-level residuals
  DR-0014 leaves. The trim bank's wide transmission-gate devices sitting
  directly on the timing ladder nodes are now the dominant added
  parasitic surface; any layout compaction or critical-net extraction
  pass that wants to shrink this penalty needs its own record with
  before/after PEX campaigns.
