# Work Log

Chronological record of merged pull requests and closed issues, maintained by the Loom Guide role. Newest activity appears first.

### 2026-10-10

- **Issue #112** (closed): Guard decision: preserve confinement for raw sweep checkpoint setup in main
- **Issue #109** (closed): Guard decision: keep unresolved write confinement for temporary research downloads
- **Issue #120** (closed): Add offline regression tests and CI job for the DR-0021 discipline model (sim/discipline has none)
- **PR #124**: test(discipline): offline regression tests and CI job for the DR-0021 model
- **Issue #121** (closed): Add offline unit tests and CI for legacy sim drivers' analysis cores (pvt_sweep calibrate/spread, startup_report, iq verdict)
- **PR #123**: test(sim): offline tests and CI for legacy sim drivers' analysis cores
- **Issue #115** (closed): Validate the layout builder Python runtime against the geometry toolchain pins
- **PR #118**: fix(layout): validate builder Python runtime against geometry pins (#115)
- **Issue #107** (closed): CI guard: offline consistency check between pvt_tb.spice, rcosc_top.spice and the per-bench DUT netlist copies
- **PR #116**: CI guard: offline netlist consistency check (#107)
- **PR #114**: Offline trim-input DC selection and static-current characterization harness
- **Issue #106** (closed): Prepare offline trim-input DC selection and static-current characterization harness

### 2026-10-09

- **Issue #97** (closed): Guard decision: preserve rejection of gh api literal body=@path
- **Issue #95** (closed): Keep stash scope guard and document explicit scoped alternatives
- **PR #108**: sim/supply-transient: offline supply-step and ripple bench (generator, analyzer, tests, CI)
- **PR #105**: Live trim-code transition bench: generator, analyzer, offline suite (results pending batch runner) (#103)
- **Issue #92** (closed): Dynamic supply-transient and ripple response bench (only static VDD corners are characterized today)
- **PR #102**: ci: run offline waveform fixture suite (#101)
- **PR #100**: feat(waveform): offline clk waveform-shape harness (#91, offline subset)
- **Issue #101** (closed): Run the offline waveform fixture suite in CI
- **PR #96**: feat(signoff): doc-citation check for sim/ run dirs
- **PR #94**: docs(spec): DR-0022 Monte Carlo matching model for trim-ladder resistors and MIM cap
- **PR #90**: docs: index DR-0020 and un-indexed committed runs
- **PR #89**: ci(sim): append-only guard for sim results (#84)
- **PR #86**: feat(sim): runtime-discipline SOF loop model and trim-math note; DR-0021 (#79)
- **PR #83**: feat(sim): item-6 Monte Carlo groundwork - mismatch feasibility verdict and per-sample trim-selection bench (#77)
- **Issue #93** (closed): CI check that prose citations of sim result directories are not stale (recurring doc-drift issues)
- **Issue #88** (closed): Docs: index DR-0020 in spec/README.md and add committed-runs tables for sim/startup, mc-groundwork, discipline
- **Issue #85** (closed): Decision record: Monte Carlo matching model for trim-ladder resistors and MIM capacitor (before the item-6 campaign)
- **Issue #84** (closed): CI guard: mechanically enforce append-only sim/ results
- **Issue #79** (closed): Runtime-discipline trim-math: behavioural SOF loop model against the committed freq-vs-code data
- **Issue #77** (closed): Item 6 groundwork: verify gf180mcu mismatch models under klt sim monte_carlo and build the per-sample-trim MC bench
- **Issue #76** (closed): Keep unresolved removal scope guard for historical external-checkout cleanup

### 2026-10-08

- **PR #80**: feat(sim): startup-time testbench for the 10 us row (partial evidence) (#78)
- **Issue #78** (closed): Add a startup-time testbench for the ratified 10 us row (currently not evaluated)
- **PR #75**: Item 7: klt pex inputs + single-corner probe (grid blocked by fleet runner version) (#70)
- **PR #74**: docs(spec): DR-0019 classify spec rows statistical vs deterministic, MC evidence plan
- **PR #73**: chore(signoff): move grader pin to klayout-tools 0.7.0 release
- **PR #67**: signoff: bind T1 items 1, 2, 9, 10 to audited artifacts; move grader pin to klayout-tools 3a75c3ae
- **Issue #72** (closed): Evaluate moving the signoff grader pin from a klayout-tools git commit to the 0.7.0 release
- **Issue #71** (closed): Item 6: decision record classifying spec rows as statistical vs deterministic, with the Monte Carlo evidence plan
- **Issue #64** (closed): T1 items 1, 9, 10 (and item 2's binding): cite artifact-anchored evidence now that klt signoff can bind it (klayout-tools#2843)

### 2026-09-23

- **PR #62**: feat(sim): post-layout PEX re-verify of DR-0017 respin + guardrails
- **PR #60**: feat(design): re-reference the low-side comparator to a complementary PMOS-input cell — supply slope flattened, post-trim rows re-derived (DR-0017)
- **Issue #61** (closed): Post-layout PEX PVT re-verification for the DR-0017 re-spun rcosc_comparator_p/rcosc_top hierarchy
- **Issue #57** (closed): Flatten the low-side comparator's supply-dependent delay (near-ground common mode) to tighten the DR-0016 post-trim accuracy rows

### 2026-09-22

- **PR #58**: feat(spec): budget the measured comparator/latch delay residue into the post-trim rows (DR-0016)
- **PR #56**: feat(layout): re-spin rcosc_trim_bank (post-#43 shunts) + PEX re-verify
- **Issue #51** (closed): Comparator/latch delay residue now dominates the remaining post-trim accuracy rows (3x period weight; supply+temperature share grows as trim mass falls)
- **Issue #50** (closed): Trim-bank + top layout re-spin for the #43 transmission-gate shunts: regenerate GDS/LVS/extract evidence and re-grade signoff

### 2026-09-21

- **PR #54**: docs: cite the DR-0013 post-re-spin PEX campaign in signoff item 7
- **PR #53**: docs: refresh §4 accuracy rows 5/6/9 + post-layout note to the DR-0012/DR-0013 evidence chain
- **PR #52**: feat(design): replace trim-bank pass switches with per-position transmission gates — trim range restored (issue #43)
- **PR #48**: feat(layout): re-spin rcosc_bias (post-#39 core) + PEX re-verify
- **PR #46**: feat(signoff): declare nwell supply tie and cite compound erc+lvs evidence to grade T1 item 11 met
- **PR #45**: rcosc_bias: self-biased supply-independent current reference (comparator/bias-path PVT revision)
- **PR #41**: feat(layout): add klt erc supply spec and report for T1 item 11
- **PR #40**: feat: add klt signoff block manifest with CI re-grade gate
- **Issue #49** (closed): signoff/README.md item-7 section still cites pre-re-spin PEX campaign (DR-0010) after PR #48's DR-0013 re-spin
- **Issue #47** (closed): Characterization record (challenge-5-proposal.md) still cites the pre-#39 evidence chain: refresh its rows from DR-0012/DR-0013
- **Issue #43** (closed): Trim-bank pass switches lose effectiveness over the top of the charge ramp (body-effect VGS collapse): dead mid-block trim steps and PVT-dependent phantom resistance
- **Issue #44** (closed): Re-spin rcosc_bias layout + redo PEX PVT re-verification for the issue #39 self-biased current-reference core
- **Issue #42** (closed): T1 item 11 graded flip: cite the landed erc+lvs evidence in signoff/block-manifest.json and re-grade the signoff report
- **Issue #39** (closed): Post-trim accuracy misses the ratified rows by 15-50x — target the comparator/bias path's PVT sensitivity, not the timing R/C (DR-0006 follow-up)
- **Issue #37** (closed): T1 item 11 (power delivery, structural): no klt erc supply spec or report in this repo
- **Issue #38** (closed): Commit a klt signoff block manifest so this block's T1 state is graded, not hand-read

### 2026-09-12

- **Issue #9** (closed): [Epic #542] 3A — gf180-rcosc maturation + Challenge #5 brief

### 2026-09-09

- **PR #36**: PVT-corner factorial for quiescent current (Iq) — DR-0003 Row 4 exceeds off-reference
- **Issue #35** (closed): PVT-corner factorial for quiescent current (Iq) — close the reference-corner-only gap on DR-0003 Row 4

### 2026-09-07

- **PR #34**: docs: update stale maturity-status text to reflect post-layout evidence
- **PR #32**: docs: add Chipalooza Challenge #5 proposal document
- **PR #31**: feat(sim): post-layout (PEX-extracted) PVT re-verification subset (issue #28)
- **PR #30**: feat(layout): DRC-clean + LVS-matched GDS for rcosc_comparator + rcosc_top
- **PR #29**: feat(layout): DRC-clean + LVS-matched GDS for rcosc_bias and rcosc_trim_bank
- **PR #26**: fix(design): re-derive RBIAS against the running Iq metric to recover trim range (issue #24)
- **Issue #33** (closed): Stale maturity-status text in README.md / design/README.md (pre-layout claims, post-layout evidence exists)
- **Issue #14** (closed): [Epic #542 / 3A, 4 of 4] Chipalooza Challenge #5 proposal document
- **Issue #13** (closed): [Epic #542 / 3A, 3 of 4] Layout: DRC-clean + LVS-matched GDS, post-layout PVT re-verification
- **Issue #28** (closed): [Epic #542 / 3A] Post-layout (PEX-extracted) PVT re-verification subset
- **Issue #27** (closed): [Epic #542 / 3A] Layout: rcosc_comparator + rcosc_top composition (DRC-clean, LVS-matched)
- **Issue #24** (closed): Re-derive bias sizing against the running-Iq metric to recover trim range lost in issue #22
