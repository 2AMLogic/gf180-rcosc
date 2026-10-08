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
| `characterization-envelope.json` | the hand-rolled **generic evidence envelope** for T1 item 8 (the characterization report, which no `klt` verb produces) wrapping this repo's characterization report |
| `design-sources-envelope.json` | artifact-bound generic envelope for T1 item 1, bound to `design-sources-inventory.md` |
| `design-sources-inventory.md` | the committed design-source inventory: xschem sources, the derived netlist, the regeneration command, and its audit |
| `layout-envelope.json` | artifact-bound generic envelope for T1 item 2, bound to `layout/cells/rcosc_top.gds` |
| `testbench-envelope.json` | artifact-bound generic envelope for T1 item 9, bound to `testbench-inventory.md` |
| `testbench-inventory.md` | the committed testbench inventory: every claimed measurement against its run, bench, cold-start command and recorded PDK identity |
| `repo-hygiene-envelope.json` | artifact-bound generic envelope for T1 item 10, bound to `.github/workflows/signoff.yml` |
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
python -m pip install "klayout-tools==0.7.0"
klt signoff --manifest signoff/block-manifest.json --format json > signoff/signoff-report.json
python3 signoff/verify-report.py
```

Without installing anything into the host Python, the same two steps run in
a throwaway `uv` environment (`uv run --with` puts the pinned `klt` beside the
interpreter, which is where `verify-report.py` looks first):

```bash
PIN="klayout-tools==0.7.0"
uv run --no-project --with "$PIN" klt signoff --manifest signoff/block-manifest.json --format json > signoff/signoff-report.json
uv run --no-project --with "$PIN" python3 signoff/verify-report.py
```

(The report is committed with the trailing-newline form `klt` emits; regenerate
it with the exact command above rather than by hand.)

**Grade from a git checkout.** The four artifact-bound envelopes (items 1,
2, 9, 10) name their artifacts repo-relatively (`"scope": "repo"`), and the
grader resolves that scope against the nearest ancestor that contains
`.git`. From a source archive or any copy without `.git`, those four rows
grade `unmet`/`unverifiable_provenance` even though no bytes changed, and
`verify-report.py` reports the drift. CI's `actions/checkout` is a git
checkout. This was found during issue #64 and filed upstream as
klayout-tools#2878.

**The grader pin is load-bearing.** The committed report records the build
that graded it (`build.git_commit`) and the hash of the rulebook it graded
under (`source_doc_content_hash`), and `verify-report.py` fails if either
differs from a fresh grade. The pin is the klayout-tools **0.7.0** release from PyPI
(`klt --version`: `0.7.0`; the report records `git_tag: v0.7.0`,
`is_release: true`, `git_commit: 0e2362bd…`). Its rulebook is the one that first graded T1
items 1, 2, 9 and 10 from an **artifact-bound generic envelope**
(klayout-tools#2718; see "Items 1, 2, 9, and 10: bind them to an audited
artifact" in klayout-tools `docs/cli/signoff.md`). When moving it, follow the
refresh contract below, starting with a pin-only re-grade of the unchanged
manifest.

**Pin move to 0.7.0 (issue #72).** The pin was klayout-tools commit
`3a75c3ae…` (`0.6.0+g3a75c3ae705b`, a development build, git-pinned). The
unchanged manifest graded identically under both builds: no row changed,
`source_doc_content_hash` is identical, and the only differences in the whole
report are the `build` block (`version`, `package_version`, `git_commit`,
`git_tag`, `is_release`) and the item-10 envelope hash.
The workflow bytes changed (item 10 binds them), so the repo-hygiene
envelope, manifest pin and report were refreshed together.

**Earlier pin history.** Before `3a75c3ae…`, the pin was `2b1e55e5…` (`0.5.0+g2b1e55e51bb8`),
chosen because the 11-item rulebook (item 11, klayout-tools#2025) had not
shipped in a release. Issue #64 moved it. Before any manifest change, the
unchanged manifest was graded under both builds:

- **No row changed status or reason.** Items 2, 3, 4, 8 and 11 stayed `met`.
  Items 1, 5, 6, 7, 9 and 10 stayed `unmet`/`no_evidence`, at 5 of 11.
- What did change: `source_doc_content_hash` (the bundled rulebook text was
  revised; the item texts of 6, 8 and 11 changed wording). New block-level
  keys appeared: `build` and `build_t1_item_count` (11). Every row gained
  `graded_by_build: true`, and every citation gained an `input_verified`
  field. Items 2, 3, 4 and 8 render it `null` (they rest on their recorded
  hash). Item 11's ERC part renders `true`, because the newer grader
  re-hashes the GDS it names. Item 11's `power_delivery` block gained three
  empty fields (`ties_checked_by_assertion`, `ties_checked_by_well_assertion`,
  `supply_unlabelled_islands`).
- Items 4 and 11 rest on the klt-0.4.0-era LVS envelope, which has no
  recorded input hash. The newer grader accepts it unchanged
  (`content_hash: null`, `input_verified: null`), so no LVS regeneration was
  needed. Item 11's ERC half was written by the old build. The new grader
  re-reads the spec it names and verifies the recorded spec hash, and grades
  it `met`, so no ERC regeneration was needed either.
- Not moved: `layout/run_checks.sh` keeps running `klt erc` on the
  `2b1e55e5` build. The `3a75c3ae` build's `klt erc` refuses
  `layout/erc-supply-spec.json` because of its `_comment` annotation key
  (klayout-tools#2822). See the comment above `ERC_KLT` in that script.

## Current verdict, and the claims behind each row

`klt signoff` exits `3` when the block grades below T1 — that exit code is
**data** ("some items are unmet"), not an error; the JSON report is the payload.
Today the machine grades this block (`klt signoff --manifest`, committed
`signoff-report.json`):

- **met, 8 of 11: item 1 (Design sources), item 2 (Layout), item 3 (DRC
  clean), item 4 (LVS clean), item 8 (Characterization report), item 9
  (Testbenches shipped), item 10 (Repo hygiene), item 11 (Power delivery,
  structural)**
- **unmet, reason `no_evidence`: items 5, 6, 7**

The block therefore still grades **below T1** (`tier: null`, exit `3`).

Items 1, 2, 9 and 10 are met through artifact-bound generic envelopes. Each
envelope declares `t1_item`, names its audited artifact in
`provenance.input.path` (repo-scoped) with that artifact's sha256, and the
manifest pins the same sha256. The grader re-hashes the artifact and records
`citation.artifact_binding` with `input_verified: true` on the row. The
envelope's `status: "pass"` is still this repo's own assertion. The grader
does not re-audit an inventory. What the binding adds is that the assertion
names the exact bytes it was made about, cannot be cited for another item,
and turns `unmet` (`stale_evidence`) the moment those bytes change.

`no_evidence` means exactly what it says mechanically: the manifest names no
citation for that item. It is **not** an assertion that the underlying work is
absent — for items 5 and 7 the substance exists but no envelope of the kind
the item requires backs it. What exists, per item, is stated below — this is
the claim side the grader cannot grade, and it is stated here precisely so
nobody has to guess whether an unmet row means "missing" or "present but
ungradeable".

The two-tier honesty rule from the tier doc cuts both ways: **`met` rows are
weaker than they look** (their coverage gaps are disclosed below) and **`unmet`
rows may be stronger than they look** (the substance noted below) — the
machine verdict is the starting point for each read, not the whole of it.

### met — item 1 (Design sources): `signoff/design-sources-envelope.json` → `signoff/design-sources-inventory.md`

The inventory lists the committed xschem sources of the whole hierarchy
(`rcosc_top`, `rcosc_bias`, `rcosc_comparator`, `rcosc_comparator_p`,
`rcosc_trim_bank`: `.sch` + `.sym` each, plus `design/xschemrc`), the
derived netlist `design/netlist/rcosc_top.spice`, and the regeneration
command `design/regen-netlist.sh`. That script is invoked first by every
evidence generator (`layout/run_checks.sh` and the `sim/` wrappers). Its
audit section records that the committed netlist re-derives from the
committed schematics (identical after normalising xschem 3.4.4-vs-3.4.7
line wrapping and the absolute `sch_path`/`sym_path` comments). The binding
covers the inventory's bytes, not each listed source's. Every listed path
is checked to exist by `verify-report.py`. This item attests that the
sources and their derivation are committed. It does not attest that the
design meets the spec (that is item 8's record, and issue #66).

### met — item 2 (Layout): `signoff/layout-envelope.json` → `layout/cells/rcosc_top.gds`

The envelope binds directly to the committed GDS, the same bytes items 3
and 11 pin (`sha256:8cd7c47a…`). Until issue #64 this row was met through
the `klt extract` report (`layout/reports/rcosc_top.extract.json`). The
grader accepts any passing native envelope for item 2 without checking
that it bears on the item (no `artifact_binding` on the row), so that
citation was replaced. The extraction report is still committed and still
the documented-provenance statement of the GDS: on the current, issue-#50
re-spun GDS it records **95 devices** (53 `nfet` + 28 `pfet` + 13
`ppolyf_u_1k` + 1 MiM cap; the #44 re-spin GDS recorded 71 devices, the
pre-#44 one 60), **45 nets, 11 pins**. `rcosc_top.gds` instantiates
`rcosc_bias`, `rcosc_trim_bank`, `rcosc_comparator` and
`rcosc_comparator_p` as real GDS sub-cells, so the pinned artifact is the
composed whole block. The manifest pin, the envelope's recorded hash, and
the current bytes of the GDS are cross-checked on every CI run by
`verify-report.py`.

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
below) from this same envelope's `net_correspondence` rows plus an ERC
half written by a post-0.4.0 build (`2b1e55e5`, the ERC pin in
`layout/run_checks.sh`); the `power_connectivity`/`body_verification`
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
  findings (60 on the current, issue-#50 re-spun GDS — the #44 re-spin's
  36 plus the re-spun trim bank's 24 additional contacted gates; 32
  pre-#44) — the
  pre-declared artifact of omitting `Contact` from `vias[]`
  (klayout-tools#2183, declared non-blocking by item 11's own text,
  klayout-tools#1994); and this tie grades the *drawn-well* half only —
  gf180mcu has no drawn p-tub layer, so per `klt erc`'s own contract a
  substrate tie "cannot be declared at all" and the p-substrate half of
  the question is outside what this run can ask. Layout-side detail lives
  in `layout/README.md`'s "Supply ERC (T1 item 11)" section; why `ties[]`
  was previously omitted (the pre-#2169 collapse that made a declared tie
  report a false supply short) and why the klayout-tools#2169 fix (in the
  `2b1e55e5` ERC build and every later one) retires
  that rationale is recorded in both that section and the spec's own
  `_comment`.
- **LVS half.** Item 4's own `rcosc_top.lvs.json` at `status: "match"`,
  carrying `VDD`/`VSS` in `net_correspondence` paired to reference-side
  nets as pins — the analog branch's "the reference includes the supply
  nets" clause, satisfied by a SPICE reference by construction. This
  resolves the LVS-envelope open question of issue #42 by grader output:
  the freshly graded committed report shows the pinned grader (both the
  previous `2b1e55e5` pin and the current `3a75c3ae` one) accepting the
  committed klt-0.4.0-era envelope on this branch — no LVS regeneration
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

There is no Monte Carlo or `klt yield` run anywhere under `sim/`, so the
machine row is `no_evidence`. The repo **does** have statistical claims to
back: [DR-0019](../spec/decision-records/0019-statistical-vs-deterministic-spec-rows-and-monte-carlo-evidence-plan.md)
(status `proposed`) classifies every ratified spec row and finds the trim
coverage/resolution row and both post-trim accuracy rows statistical (their
budgets contain per-die trim-DAC mismatch and comparator offset), while the
remaining rows are corner-bounded or reserved. Until now the README treated
every accuracy figure as a worst-case-corner figure and the item as vacuous;
that reading is withdrawn -- a corner matrix cannot validate an accuracy row.
The record states each claim (ratified limit, 99 % yield, 95 % confidence),
the Monte Carlo design (500 samples per corner, recorded seed, deterministic
negative controls, run on top of the corner matrix rather than replacing it),
the evidence verb (`klt yield`, `klayout-tools[yield]` extra, fed by a `klt
sim` `monte_carlo` request submitted to the batch fleet), and the sequencing:
the campaign runs after #66 settles the sizing. The item stays `unmet` until
that campaign lands a `yield` envelope; both the MC run and this row change
together.

### unmet — item 7 (Post-layout verification): campaign committed, not a `klt pex` report

The post-layout re-verification is committed under
`sim/pvt-postlayout/results/20260922T004322Z/` — a real `klt extract
--parasitics` run (`rcosc_top.pex.extract.json`, klt 0.4.0) against the same
GDS item 2 pins (`provenance.input.content_hash` matches), re-simulated by the
custom `pex_pvt_sweep.py` harness over a 27-point corner-endpoint subset at
the post-#43 schematic campaign's own ratified-target calibration code
`0x9D`, with the schematic-vs-extracted deltas recorded per point
(oscillator runs −17.46% to −40.92% slower than schematic at every point —
DR-0015; DR-0013's `20260921T164434Z` run remains the committed evidence
for the pre-#43 GDS pair). The grader accepts **only a `klt pex` report**
for this item
(a clean DRC or a custom re-sim proves nothing about post-layout behavior in
its eyes — `wrong_kind` by design), so mechanically: `no_evidence`. Body-bias
disclosure for the committed extractions: both the plain and the parasitic
extraction report **no unbiased PMOS body nets** (`unbiased_pmos_body_nets:
[]`) — the extracted netlist's device bodies have DC bias paths, so the
post-layout numbers were not measured on a physically-wrong netlist.

### met — item 9 (Testbenches shipped): `signoff/testbench-envelope.json` → `signoff/testbench-inventory.md`

The inventory lists every measured figure the top-level `README.md` and the
characterization report currently quote. Each figure is tied to the
committed run it comes from, the bench that produced it, the bench's
cold-start command (`sim/pvt/run-pvt-sweep.sh`, `sim/pvt/delay_probe.py`
(no wrapper script), `sim/iq/run-iq-sweep.sh`,
`sim/pvt-postlayout/run-pex-pvt-sweep.sh`, `design/run-smoke-test.sh`), the
run's git sha and dirty flag, and the PDK identity the run recorded. It
also names the ratified rows with no claimed measurement (runtime
discipline, startup time) so their absence is visible rather than
implied.

**PDK identity is disclosed, not repaired.** Every pre-layout PVT
campaign and both delay-probe runs record only the family name
(`gf180mcuC`) and an install path, with no PDK revision. The cited Iq
run's `manifest.json` records only the install path; the family name
appears only in its generated README. The smoke-test log records no PDK
identity at all. Only the post-layout runs' `klt extract` envelopes record
an open_pdks commit. The current run records `c6d73a35…`, while two
earlier post-layout runs record `f6eeac7d…`, so runs were not all on one
revision. (This section previously said the post-layout extraction pins
`c6d73a35…`. That holds for the current run only.) Historical revisions
that were not recorded stay unknown. Recording the revision on new runs is
issue #65.

### met — item 10 (Repo hygiene): `signoff/repo-hygiene-envelope.json` → `.github/workflows/signoff.yml`

Bound to the CI workflow that keeps the evidence formats valid: it re-grades
this manifest and re-verifies every pin on each push and pull request. The
envelope's summary records the rest of the audit: the top-level `README.md`
states what the block is, carries the ratified spec table with its basis
citations, and documents evidence reproduction, and `LICENSE` (Apache-2.0)
is committed. Only the workflow's bytes are bound. **Any edit to the
workflow, including moving the grader pin, must refresh this envelope,
its manifest pin and the report together**, or CI fails on its own
workflow.

## Freshness and the refresh contract

Every `content_hash` pin in the manifest names the **current bytes** of a
committed artifact, and `verify-report.py` proves it: manifest pin == the
cited envelope's recorded hash == the artifact's sha256 today. For the
artifact-bound items (1, 2, 9, 10) it also checks the envelope's `t1_item`
and `provenance.input.path`, that the fresh grade carries
`artifact_binding.input_verified: true`, and that every path the two
inventories list exists. The
klt-0.4.0-era LVS envelope is the one citation without a manifest pin, and
its two inputs are re-hashed against its own recorded digests instead. Write
the pins from what the evidence actually records — never by hand from hope.

After changing any cited artifact or any cited envelope:

1. regenerate the evidence the documented way (`sim/` campaigns append a new
   timestamped results directory; `layout/run_checks.sh` regenerates
   `layout/reports/` wholesale);
2. update the affected manifest pins (and, if a new citation kind is added,
   the artifact table at the top of `verify-report.py`) from the regenerated
   envelopes' `provenance` blocks. For the four hand-written bound envelopes
   (items 1, 2, 9, 10) that means: re-audit the changed artifact (an
   inventory edit is an audit change, not a formality), write its new
   sha256 into the envelope's `provenance.input.content_hash`, and pin the
   same value in the manifest;
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
