# signoff/ — the machine-graded T1 verdict of record

This directory carries this block's `klt signoff` block manifest (klayout-tools
[design-evidence-tiers](https://github.com/2AMLogic/klayout-tools/blob/main/docs/design-evidence-tiers.md)
T1 checklist), the graded report it produces, and the verifier that keeps both
honest. **The gap-to-T1 tracker (issue #5) points here as the verdict of
record** — the hand-maintained checkbox list it used to carry is retired: "what
is the block's T1 state" is now answered by re-running a grader, not by
re-reading prose that was written against whatever the checklist said that day.

## Contents

| file | what it is |
|---|---|
| `block-manifest.json` | the block manifest `klt signoff --manifest` grades: `block`, `kind`, and per-T1-item evidence citations with pinned `content_hash` |
| `characterization-envelope.json` | the hand-rolled **generic evidence envelope** (the one wrapper shape `klt signoff` accepts for T1 item 8, the one item no `klt` verb produces) wrapping this repo's characterization report |
| `signoff-report.json` | the committed output of the grading run — the graded T1 item table, per item `met`/`unmet` + machine-readable `reason` |
| `verify-report.py` | the anti-rot verifier CI runs on every push and PR (see below) |

## Block kind: `analog`

Confirmed against the block, not assumed from the filing issue: the whole of
`rcosc_top` — bias generator, comparator, the SR latch, the discharge switch,
the trim bank — is designed and captured as transistor-level SPICE
(xschem schematics in `design/`), verified by PVT corner sweeps, with no RTL,
no synthesis step, and no place-and-route anywhere in the flow. The 8-bit trim
interface is a digitally-*driven* switch bank on the timing capacitor, not a
digital partition; there is no boundary across which a `digital` column's
artifacts (RTL, P&R output, STA) could apply, so `mixed-signal` (which demands
an explicit partition boundary and both columns' evidence) would assert a
partition that does not exist. `analog` is the honest declaration.

## How to re-run the grading

`klt signoff --manifest` is PDK-free — it grades the committed JSON envelopes,
it does not run the gates — so the grading can be re-run anywhere:

```bash
python -m pip install "klayout-tools @ git+https://github.com/2AMLogic/klayout-tools@2b1e55e51bb803c082e8857da44687f3e37ebfc0"
klt signoff --manifest signoff/block-manifest.json --format json > signoff/signoff-report.json
python3 signoff/verify-report.py
```

(The report is committed with the trailing-newline form `klt` emits; regenerate
it with the exact command above rather than by hand.)

**The grader pin is load-bearing.** The committed report was graded under the
**11-item** T1 rulebook — including item 11, *Power delivery (structural)*,
added 2026-09-17 (klayout-tools#2025) — which shipped after the klayout-tools
`0.5.0` release. Released klt 0.5.0 bundles the older **10-item** checklist and
renders no item-11 row at all, so it cannot reproduce the committed report
(it disagrees on `t1_item_count` and item count). The pin is the public commit
the grading install was built from (`klt --version` reports a
`0.5.0+g2b1e55e51bb8` prefix), and the committed report was re-verified
**item-for-item identical** against a clean `pip install` from this exact
git pin — the same install command CI runs — so the committed record is
reproducible from the public commit alone. When a klayout-tools release
carrying the 11-item rulebook ships, move the pin in
`.github/workflows/signoff.yml` and here, then re-grade. The release lag
and the version-string/grading-rule identity behind this pin are tracked
upstream: klayout-tools#2173 (release cadence) and klayout-tools#2216 (a
version string does not identify the grading rules behind it).

## Current verdict, and the claims behind each row

`klt signoff` exits `3` when the block grades below T1 — that exit code is
**data** ("some items are unmet"), not an error; the JSON report is the payload.
Today the machine grades this block (`klt signoff --manifest`, committed
`signoff-report.json`):

- **met — item 2 (Layout), item 3 (DRC clean), item 4 (LVS clean), item 8
  (Characterization report), item 11 (Power delivery, structural)**
- **unmet, reason `no_evidence` — items 1, 5, 6, 7, 9, 10**

`no_evidence` means exactly what it says mechanically: the manifest names no
citation for that item. It is **not** an assertion that the underlying work is
absent — for several items the substance exists but no `klt` envelope backs it
(the grader's own design: it only reads the evidence shapes named in
`docs/cli/signoff.md`). What exists, per item, is stated below — this is the
claim side the grader cannot grade, and it is stated here precisely so nobody
has to guess whether an unmet row means "missing" or "present but ungradeable".

The two-tier honesty rule from the tier doc cuts both ways: **`met` rows are
weaker than they look** (their coverage gaps are disclosed below) and **`unmet`
rows may be stronger than they look** (the substance noted below) — the
machine verdict is the starting point for each read, not the whole of it.

### met — item 2 (Layout): `layout/reports/rcosc_top.extract.json`

The extraction report is the documented-provenance statement of the committed
GDS: it pins `layout/cells/rcosc_top.gds` by content hash (`provenance.input
.content_hash`, mirrored in the manifest pin), records the extracted device/
net inventory and the netlist it produced. On the current, issue-#44
re-spun GDS the envelope records **71 devices** (45 `nfet` + 12 `pfet` +
13 `ppolyf_u_1k` + 1 MiM cap: the pre-re-spin GDS recorded 60 devices),
**37 nets, 11 pins**. `rcosc_top.gds` instantiates the three sub-blocks as
real GDS sub-cells, so the pinned artifact is the composed whole block. The
manifest pin, the envelope's recorded hash, and the current bytes of the
GDS are cross-checked on every CI run by `verify-report.py`.

### met — item 3 (DRC clean): `layout/reports/rcosc_top.drc.json`

`status: clean`, 0 violations, deck `gf180mcu`, pinned to the same GDS hash as
item 2. **Coverage disclosure (the part the grader does not grade — quoted from
the cited envelope's own `coverage` block, not from memory):**

- `layers_in_stream_without_rules` — 8 layers drawn in this stream the deck
  has no rule for: `31/0`, `32/0`, `36/10`, `49/0`, `62/0`, `110/5`, `117/5`,
  `117/10`
- `rules_skipped` — 6 rules the deck carries but this run did not evaluate:
  `bjt.separation.comp.1`, `comp.space.mv.1`, `comp.width.mv.1`,
  `metaltop.space.1`, `metaltop.width.1`, `pad.enclosing.metal5.1`
- `deck_scope` — which DRM chapters the deck transcribes at all:
  `10.4.2 MIM Option B`, `10.7 DRC_BJT Mark Layer`, `7.12 Contact`,
  `7.13 Metaln`, `7.14 Vian`, `7.15 MetalTop`, `7.4 Nwell`, `7.5 Comp`,
  `7.7 Poly2`, `9.1 Bond Pad`

"Clean" therefore means *clean within that scope* — a defect class outside it
(for instance on a rule-free drawn layer) is not excluded by this verdict. The
three sub-blocks are additionally committed with their own standalone
DRC reports (`rcosc_bias`, `rcosc_trim_bank`, `rcosc_comparator` — all `clean`,
all under `layout/reports/`), regenerated by the same flow.

### met — item 4 (LVS clean): `layout/reports/rcosc_top.lvs.json`

`status: match`, engine `klayout`, against the committed extraction
(`rcosc_top.extracted.spice`) and the reference netlist
(`layout/lvs_ref/rcosc_top.spice`, generated from the schematic's own device
geometry via `layout/netlist_parse.py`). Two disclosures the grader does not
grade:

- **Warnings-only mismatches (7, all disclosed by the envelope itself):**
  6× `device.parameter_tolerated` (matched resistor `r` differing by
  0.27%–0.34% ×10⁻¹ scale within the requested 0.1% `parameter_tolerance` —
  the sub-0.1% grid-rounding deltas the 1 nm database unit introduces on the
  trim bank's short segments; both original values are in the JSON) and
  1× `topology.flattened` (the hierarchical reference flattened to meet the
  extract's flat netlist). No error-count entries; `category_error_counts` is
  empty.
- **No pin.** The committed envelope was generated by klt 0.4.0, which predates
  the `provenance.input.content_hash` population that `klt lvs` gained later
  (klayout-tools#1969) — there is no recorded input hash a manifest pin could
  be checked against, and an unpinned bare-string citation is the tool's own
  documented pattern for that case (see `examples/signoff/manifest.json` in
  klayout-tools). Its freshness is instead verified mechanically on every CI
  run: `verify-report.py` re-hashes the two committed netlists the envelope
  did compare and matches them against the digests its own `environment` block
  records (`layout_sha256` = `rcosc_top.extracted.spice`, `reference_sha256` =
  `lvs_ref/rcosc_top.spice`).

Also disclosed: this klt-0.4.0-era envelope predates both the
`power_connectivity` block (klayout-tools#1952) and the `body_verification`
block — neither question was *asked* by this compare, so the match says
nothing about per-instance power pin-to-net reach or body ties. The supply
question itself is now item 11's, graded met (see the met-item-11 section
below) from this same envelope's `net_correspondence` rows plus a
current-pinned-klt ERC half; the `power_connectivity`/`body_verification`
blocks stay unasked by this pair, which is why item 11's analog branch
does not lean on them.

### met — item 8 (Characterization report): `signoff/characterization-envelope.json`

`docs/chipalooza/challenge-5-proposal.md` is this repo's single aggregated,
current artifact summarizing per-spec-row performance — 11 ratified rows, each
with a per-row verdict citing the `sim/` evidence path it rests on. The generic
envelope's `status: "pass"` asserts **the record is present and current** — it
is **not** a claim that every spec row passes. In the record's own §4 verdict
vocabulary: **Met** (rows 1, 3, 8, 11), **Within** the ratified bound (row 4),
**Not met** (row 2 — trim range), **Exceeds** (rows 5–6 — post-trim accuracy,
both methodologies — and row 9 — Iq off-reference), **Not evaluated** (rows 7,
10) — every miss undisguised, with causes traced in §4 and DR-0009/DR-0011. The
envelope pins the document's content hash (`provenance.input.content_hash`),
mirrored in the manifest pin, so a citation against a stale characterization
record rots in CI the same way the layout pins do.

### met — item 11 (Power delivery, structural): `layout/reports/rcosc_top.erc.json` + `layout/reports/rcosc_top.lvs.json`

The one compound citation in the manifest (klayout-tools#2025): item 11 is
the single T1 item no one artifact proves, so its manifest entry is a *list*
of evidence parts — the ERC report of the supply-spec run (pinned to the
GDS the way items 2/3 are) and the same `rcosc_top.lvs.json` item 4 grades
(unpinned, klt-0.4.0-era, re-verified through its own recorded netlist
digests). The committed report's `power_delivery` citation block records
the branch that graded it: `partition_kind: "analog"`, no PDN citation, so
the analog path — ERC supply-continuity plus LVS `net_correspondence` — is
what the grade rests on. What each half proves, and the disclosures the
grader does not grade:

- **ERC half.** `layout/erc-supply-spec.json` declares `vdd`/`vss`
  (`kind: "supply"`, the one-island-per-supply clauses) and one `ties[]`
  entry — the upstream deck's own gf180mcu tap boolean (an `Nplus`-covered
  `Comp` shape inside `Nwell`, wired to `Metal1`, net `vdd`; the
  `tap_requires` intersection key the klayout-tools#2169 fix added). The
  committed run reports zero `erc.unconnected_net`, zero `erc.supply_short`,
  and zero `erc.missing_tie` — with `erc.missing_tie` listed under
  `checked` in the envelope's `erc_coverage`, so the zero is graded
  evidence, not an uncomputed absence. Disclosed, not graded: the report's
  overall `status` is `"violations"` from its `erc.floating_gate`
  findings (36 on the current, issue-#44 re-spun GDS — the re-spun
  beta-multiplier core's contacted gates; 32 pre-re-spin) — the
  pre-declared artifact of omitting `Contact` from `vias[]`
  (klayout-tools#2183, declared non-blocking by item 11's own text,
  klayout-tools#1994); and this tie grades the *drawn-well* half only —
  gf180mcu has no drawn p-tub layer, so per `klt erc`'s own contract a
  substrate tie "cannot be declared at all" and the p-substrate half of
  the question is outside what this run can ask. Layout-side detail lives
  in `layout/README.md`'s "Supply ERC (T1 item 11)" section; why `ties[]`
  was previously omitted (the pre-#2169 collapse that made a declared tie
  report a false supply short) and why the pinned grader's fix retires
  that rationale is recorded in both that section and the spec's own
  `_comment`.
- **LVS half.** Item 4's own `rcosc_top.lvs.json` at `status: "match"`,
  carrying `VDD`/`VSS` in `net_correspondence` paired to reference-side
  nets as pins — the analog branch's "the reference includes the supply
  nets" clause, satisfied by a SPICE reference by construction. This
  resolves the LVS-envelope open question of issue #42 by grader output:
  the freshly graded committed report shows the pinned grader accepting
  the committed klt-0.4.0-era envelope on this branch — no LVS regeneration
  was needed, and with no PDN citation the `power_connectivity` block the
  PDN branch would read is never consulted (`power_connectivity_status`
  is `null` in the citation, and that null is why the analog branch, not
  the PDN branch, applied).

The flip itself (evidence landed in PR #41, citation + re-grade made here)
is the refresh contract's step sequence executed once: regenerate the
affected evidence the documented way, pin from the regenerated envelopes'
`provenance` blocks, re-grade with the exact pinned command, and let
`verify-report.py` fail until all three agree. The ERC part's manifest pin
names the GDS input hash the envelope records, and the spec hash the
envelope records is re-verified against the spec's current bytes on every
CI run alongside it — the compound-entry extension of the artifact table
at the top of `verify-report.py`.

### unmet — item 1 (Design sources): substance present, no gradeable citation

The substance exists: committed xschem sources (`design/*.sch`/`*.sym`), the
derived netlist (`design/netlist/rcosc_top.spice`), and the regeneration flow
(`design/regen-netlist.sh`, invoked first by `layout/run_checks.sh` so the
layout evidence is always regenerated against the current schematic). No
`klt` verb envelope can be cited for "committed schematic sources plus the
derived netlist" — items 2/3/4's envelopes cover the *layout* end of that
chain, and `klt sim` does not exist in this repo (see item 5). The row stays
`no_evidence` rather than being painted green with a citation that does not
prove the item.

### unmet — item 5 (Full corner verification vs a ratified spec): campaign committed, not a gradeable envelope — and the record shows missed rows

The pre-layout PVT campaign is committed under `sim/pvt/results/`
(`20260907T090653Z`: full 7-process × 3-temp × 3-VDD factorial, 277 unique
points, 0 sim failures) as this repo's own append-only evidence format
(`manifest.json` + `results.csv` + `summary.md`), not a `klt sim` JSON
envelope — so the grader has nothing it can read, mechanically `no_evidence`.
Beyond the format gap, in the characterization record's own §4 verdict
vocabulary: row 2 is **Not met** (trim range: ±35.50% realized vs ±40%
ratified) and rows 5–6 **Exceed** the ratified post-trim accuracy budget
(−34.85%/+54.78% at the calibration point vs ±1.1%, both methodologies; row
9 likewise exceeds off-reference for Iq) — whether a full-corner campaign with
missing spec rows can satisfy this item is a separate question the tracker
has deliberately parked as needing a human/Architect call, since it is
evidence-vs-passes, not evidence-existence. Making this row gradeable means
running the campaign through `klt sim` — distinct follow-up work, tracked via
the tracker's "Next" section (the design-side gap itself is issue #39's
PVT-sensitivity work).

### unmet — item 6 (Statistical claims carry Monte Carlo evidence): nothing to back, nothing cited

There is no Monte Carlo or `klt yield` run anywhere under `sim/`. The repo
also makes **no statistical accuracy/yield claim**: every accuracy figure in
the README and the characterization report is a worst-case-corner figure, not
a distributional one (the buckets and reasons are recorded in the tracker's
2026-09-15 re-verification). The tier doc's own pass condition ("any accuracy/
yield claim carries MC evidence") is vacuously satisfied on the claim side;
the machine row stays `no_evidence` because no `yield` envelope exists — if a
distributional claim is ever ratified into the spec, both the MC run and this
row change together.

### unmet — item 7 (Post-layout verification): campaign committed, not a `klt pex` report

The post-layout re-verification is committed under
`sim/pvt-postlayout/results/20260921T164434Z/` — a real `klt extract
--parasitics` run (`rcosc_top.pex.extract.json`, klt 0.4.0) against the same
GDS item 2 pins (`provenance.input.content_hash` matches), re-simulated by the
custom `pex_pvt_sweep.py` harness over a 27-point corner-endpoint subset at
fixed trim `0xD0`, with the schematic-vs-extracted deltas recorded per point
(oscillator runs −11.24% to −41.42% slower than schematic at every point —
DR-0013). The grader accepts **only a `klt pex` report** for this item
(a clean DRC or a custom re-sim proves nothing about post-layout behavior in
its eyes — `wrong_kind` by design), so mechanically: `no_evidence`. Body-bias
disclosure for the committed extractions: both the plain and the parasitic
extraction report **no unbiased PMOS body nets** (`unbiased_pmos_body_nets:
[]`) — the extracted netlist's device bodies have DC bias paths, so the
post-layout numbers were not measured on a physically-wrong netlist.

### unmet — item 9 (Testbenches shipped): substance present, no gradeable citation

Every claimed measurement's bench is committed and runnable cold:
`design/pvt_tb.sch` + `sim/pvt/pvt_sweep.py` (+ `run-pvt-sweep.sh`),
`sim/pvt-postlayout/pex_pvt_sweep.py` (+ `run-pex-pvt-sweep.sh`),
`sim/iq/iq_sweep.py` (+ `run-iq-sweep.sh`), `design/smoke_test.sch`, with the
invocations documented in each directory's README. PDK identity is recorded
per run in the committed manifests (family `gf180mcuC`; the post-layout
extraction additionally pins the open_pdks install,
`c6d73a35f524070e85faff4a6a9eef49553ebc2b`). Per tracker history the PDK
version pin remains a cheap follow-up (recording it in the pre-layout
campaign's manifest too). None of this is a `klt` envelope the grader can
read — the row is `no_evidence`, and the substance stands.

### unmet — item 10 (Repo hygiene): README + license present; the CI half arrives with this change

The top-level `README.md` states what the block is, carries the ratified
spec table with its basis citations, and documents evidence reproduction;
`LICENSE` is committed. The "CI that keeps the harness and evidence formats
valid" half is satisfied by the signoff workflow itself
(`.github/workflows/signoff.yml`, added with this directory) — but no `klt`
envelope can cite a README, a license, or a CI file, so the row stays
`no_evidence` rather than being painted green with an adjacent citation.

## Freshness and the refresh contract

Every `content_hash` pin in the manifest names the **current bytes** of a
committed artifact, and `verify-report.py` proves it: manifest pin == the
cited envelope's recorded hash == the artifact's sha256 today. The
klt-0.4.0-era LVS envelope is the one citation without a manifest pin, and
its two inputs are re-hashed against its own recorded digests instead. Write
the pins from what the evidence actually records — never by hand from hope.

After changing any cited artifact or any cited envelope:

1. regenerate the evidence the documented way (`sim/` campaigns append a new
   timestamped results directory; `layout/run_checks.sh` regenerates
   `layout/reports/` wholesale);
2. update the affected manifest pins (and, if a new citation kind is added,
   the artifact table at the top of `verify-report.py`) from the regenerated
   envelopes' `provenance` blocks;
3. re-grade and commit `signoff-report.json` with the exact command above;
4. run `python3 signoff/verify-report.py` — it fails until 1–3 are all true
   together, including in CI.

Provenance-hygiene note: the tier doc's "repo-relative paths only" rule binds
writers *from now on*; the committed layout/sim envelopes predate this
manifest and record the absolute paths of the worktrees they were generated
in. They are not rewritten — rewriting evidence records destroys their
verifiability, which is the point of publishing them. This directory's own
artifacts (manifest, envelopes, report) contain no machine or author
identifiers: paths are repo-relative throughout.
