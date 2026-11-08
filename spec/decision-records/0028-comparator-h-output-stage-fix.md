# 0028: Comparator-H output stage: narrow the buffer pull-down (MBUFN W 2u -> 1u) so a logic high is produced at fs / -40 C

- **Status**: proposed
- **Date**: 2026-11-06
- **Decided by**: Loom Builder (issue #229), pending operator ratification

## Context

Issue #227 (PR #230) showed that the settled P3 netlist (DR-0023) never starts at
fs / -40 C for VDD >= 3.3 V: the SR latch is never set, the discharge device stays off and
the timing node charges to VDD and stays there
([`sim/startup-fs-m40c/results/20261106T061000Z/summary.md`](../../sim/startup-fs-m40c/results/20261106T061000Z/summary.md)).
Ratified rows 7, 9 and 10 failed at that corner (no spec row is edited here). The node-level
mechanism: with `vc` far above `vh` the NMOS pair is overdriven and `dp` cannot fall below the
tail node (about 0.8-1.2 V); the output inverter (MBUFN 2u/0.5u, MBUFP 4u/0.5u: fast cold NMOS,
slow cold PMOS) has its switching threshold in that range, so `cmph_out` settles at 0.5-0.7 V
instead of a high.

### Which P3 change moves the comparator into that state (AC 1)

None of the three. [`sim/startup-bisect/`](../../sim/startup-bisect/README.md) runs single-corner
local probes (fs / -40 C, 3.3 V and 3.6 V, DC step) on variants of the settled netlist with each P3 edit
reverted:

| variant | 3.3 V | 3.6 V |
|---|---|---|
| settled P3 | no start | no start |
| ladder x0.70 reverted | no start | no start |
| MiM card reverted | no start | no start |
| both reverted (the committed extraction) | no start | no start |

So the committed extracted netlist already had the defect; the pre-re-centre *schematic* oscillates
only because it lacks the extracted layout geometry/parasitics. Removing the extracted device geometry
(`AS/AD/PS/PD`) makes the circuit start, but so does removing it on only the comparator-H devices or on
only every other device, and removing the extracted R or C alone does not: the stuck state is a second,
coexisting stable operating point of the comparator-H output stage, and which basin the start-up lands in
is set by small perturbations. It is therefore a design margin defect of the output stage, not an artifact
of one P3 change, and the fix has to remove the stuck point rather than rely on a favourable perturbation.

## Decision

Narrow the comparator-H output-stage pull-down: **MBUFN W = 2u -> 1u** (L = 0.5u unchanged) in
`design/rcosc_comparator.sch`. This raises the output inverter's switching threshold, so a `dp` level of
0.8-1.2 V reads as a low and `cmph_out` reaches the rail. Nothing else changes: pair, tail, load and
MBUFP are untouched, the low-side comparator (`rcosc_comparator_p`) is untouched, and no spec row, DR,
corner list or bench stimulus is edited.

## Alternatives considered

All were tried on the settled netlist and on the committed extraction at fs / -40 C, 3.3 V and 3.6 V
(`sim/startup-bisect/probes/`, variants `p3_c1..c4`, `pex_c1..c4`); every one starts.

- **MBUFP W 4u -> 8u** — works, but doubles the load on `dp`, adds quiescent-path capacitance and larger
  layout area for the same threshold shift.
- **MBUFN L 0.5u -> 1u** — works, but slows the 3.3 V frequency by 2.4 % relative to the chosen change.
- **MBUFN 1u and MBUFP 8u** — works, +1.6 % faster than the chosen change, two edits for no extra margin.
- **`.ic`, longer window, bench changes** — rejected: they hide a real failure (#227 finding).
- **Relaxing rows 7/9/10 or removing the fs / -40 C corner** — forbidden.

## Consequences

- Layout: `layout/cells/rcosc_comparator.gds` and `rcosc_top.gds` regenerated with the pinned toolchain
  (klayout-tools 0.4.0 / klayout 0.30.12); DRC clean and LVS match for both, supply ERC findings unchanged
  (no supply findings). The other three cells are byte-identical.
- Netlists regenerated with `klt netlist` (`design/netlist/{rcosc_top,pvt_tb,smoke_test}.spice`); the five
  tracked schematic bench copies (`sim/**/rcosc_top_schematic.spice`) and the two `provenance.json` files
  that pin them carry the same one-device edit so `design/check-netlist-consistency.py` stays green.
  Archived `results/` directories are untouched and still describe the pre-fix schematic.
- Settled DUT: [`sim/cmph-fix/`](../../sim/cmph-fix/README.md) holds the P3 transformation (same recipe as
  `sim/recentre/gen_requests.py`) of a fresh parasitic extraction of the revised layout, the 15 item-5
  requests and the settled startup requests, and their batch-fleet results.
- Results are in `sim/cmph-fix/README.md` and cited from `sim/item5/ROWS.md` (rows 7, 9, 10).
  `sim/recentre/p3/` and the earlier item-5 and startup-settled results are unchanged append-only evidence of the
  pre-fix netlist.
- Frequency and calibration code (not hidden): the revised stage shifts the oscillator up. At the unchanged code 0xA9,
  tt / 27 C / 3.3 V goes 48.05 -> 49.14 MHz (+2.4 %), so item-5 **row 1 now FAILS** (it passed at +0.10 %); single-corner
  probes (`sim/cmph-fix/calib/`) put 0xA4 at -0.24 % and 0xA5 at +0.30 %. At the fs corner the old netlist was marginal
  rather than only stuck (fs / -40 C / 3.0 V 26.1 -> 47.4 MHz; fs / 27 C / 3.6 V 30.6 -> 50.5 MHz), at sf +1.2 %, at
  ff / -40 C / 3.6 V +21 %. Re-centring the calibration code and re-deriving rows 1-5 on it is a DR-0023 follow-up for
  the operator; this record does not change the code, a ratified row or a corner list. Rows 2, 4, 5 and 8 failed before
  this change and still fail (row 8 worst 564.5 uA, was 576.2 uA).
- Alternatives' relative frequency (adopted change = 100 %, tt-ish probe at fs / -40 C / 3.3 V): MBUFN L=1u -2.4 %,
  MBUFN 1u + MBUFP 8u +1.6 %, MBUFP 8u -0.1 %.
