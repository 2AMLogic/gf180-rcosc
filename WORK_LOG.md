# Work Log

Chronological record of merged pull requests and closed issues, maintained by the Loom Guide role. Newest activity appears first.

### 2026-11-12

- **PR #315**: feat(sim/mc): grade rows 4/5 by Monte Carlo on the DR-0028 netlist (DR-0032)
- **Issue #236** (closed): Item 6 Monte Carlo: ss row 4 supply span exceeds the ratified window, ff row 5 spread, and controls that do not discriminate

### 2026-11-11

- **PR #309**: sim(trim-dense): campaign slice 40, 42 more sch jobs on batch fleet (906/1536)
- **PR #308**: docs(signoff): cite DR-0020 fixed-trim ruling in row 10
- **Issue #287** (closed): signoff: drop stale 'awaits an operator ruling' on DR-0020 trim-code clause
- **PR #307**: sim(trim-dense): run campaign slice 39 on batch fleet (jobs 823-864 of 1536)
- **PR #225**: feat(sim): simulated 63-point startup factorial (61/63 pass, pre-re-centre design) and DR-0020 ratified
- **PR #305**: refactor(layout): remove unused wire_l and wire_z helpers
- **Issue #304** (closed): Remove dead Composer.wire_l/wire_z from layout/gen_lib.py
- **PR #302**: sim(trim-dense): run campaign slice 38 on batch fleet (jobs 793-822 of 1536)
- **PR #301**: docs(spec): attribute rows 4/5 fixed-code failure to process offset (DR-0031)

### 2026-11-10

- **PR #300**: sim(trim-dense): run campaign slice 37 on batch fleet (jobs 757-792 of 1536)
- **PR #298**: sim(trim-dense): run campaign slice 36 on batch fleet (jobs 721-756 of 1536)
- **PR #296**: sim(trim-dense): run campaign slice 35 on batch fleet (jobs 685-720 of 1536)
- **PR #295**: refactor(design): use klt netlist in regen-netlist.sh
- **PR #294**: sim(trim-dense): run campaign slice 34 on batch fleet (jobs 649-684 of 1536)
- **Issue #292** (closed): Simplify design/regen-netlist.sh: use klt netlist instead of raw xschem + hand-rolled PDK resolve
- **PR #291**: sim(trim-dense): run campaign slice 33 on batch fleet (jobs 625-648 of 1536)
- **PR #290**: sim(trim-dense): run campaign slice 32 on batch fleet (jobs 601-624 of 1536)
- **PR #289**: sim(trim-dense): run campaign slice 31 on batch fleet (jobs 589-600 of 1536)
- **PR #288**: sim(trim-dense): run campaign slice 30 on batch fleet (jobs 577-588 of 1536)
- **PR #286**: sim(trim-dense): run campaign slice 29 on batch fleet (jobs 565-576 of 1536)
- **PR #285**: sim(trim-dense): run campaign slice 28 on batch fleet (jobs 553-564 of 1536)
- **PR #284**: sim(trim-dense): run campaign slice 27 on batch fleet (jobs 542-552 of 1536)
- **PR #283**: sim(trim-dense): run campaign slice 26 on batch fleet (jobs 528-541 of 1536)
- **PR #281**: sim(trim-dense): run campaign slice 25 on batch fleet (jobs 512-527 of 1536)

### 2026-11-09

- **PR #279**: sim(trim-dense): run campaign slice 24 on batch fleet (jobs 496-511 of 1536)
- **PR #278**: sim(trim-dense): run campaign slice 23 on batch fleet (jobs 480-495 of 1536)
- **PR #277**: sim(trim-dense): run campaign slice 22 on batch fleet (jobs 464-479 of 1536)
- **PR #276**: sim(trim-dense): run campaign slice 21 on batch fleet (jobs 448-463 of 1536)
- **PR #275**: sim(trim-dense): run campaign slice 20 on batch fleet (jobs 434-447 of 1536)

### 2026-11-08

- **PR #273**: sim(trim-dense): run campaign slice 19 on batch fleet (jobs 418-433 of 1536)
- **PR #272**: sim(trim-dense): run campaign slice 18 on batch fleet (jobs 402-417 of 1536)
- **PR #271**: sim(trim-dense): run campaign slice 17 on batch fleet (jobs 386-401 of 1536)
- **PR #270**: sim(trim-dense): run campaign slice 16 on batch fleet (jobs 370-385 of 1536)
- **PR #269**: sim(trim-dense): run campaign slice 15 on batch fleet (jobs 354-369 of 1536)
- **PR #268**: sim(trim-dense): run campaign slice 14 on batch fleet (jobs 338-353 of 1536)

### 2026-11-07

- **PR #266**: sim(trim-dense): run campaign slice 13 on batch fleet (jobs 322-337 of 1536)
- **PR #265**: sim(trim-dense): run campaign slice 12 on batch fleet (321 of 1536 jobs)
- **PR #263**: refactor(sim): share sha256, evidence banner and new-run guard across drivers
- **PR #262**: sim(trim-dense): run campaign slice 11 on batch fleet (jobs 290-305 of 1536)
- **PR #261**: sim(trim-dense): run campaign slice 10 on batch fleet (jobs 262-289 of 1536)
- **PR #259**: sim(trim-dense): run campaign slice 9 on batch fleet (jobs 222-261 of 1536)
- **Issue #260** (closed): Consolidate duplicated sim helpers (sha256, synthetic-evidence banner, new-run guard) into one shared module
- **PR #257**: sim(trim-dense): run campaign slice 8 on batch fleet (jobs 204-221 of 1536)

### 2026-11-06

- **PR #255**: sim(trim-dense): run campaign slice 7 on batch fleet (jobs 164-203 of 1536)
- **PR #253**: sim(trim-dense): run campaign slice 6 on batch fleet (jobs 118-163 of 1536)
- **PR #252**: sim(trim-dense): run campaign slice 5 on batch fleet (jobs 77-116 of 1536)
- **PR #250**: sim(trim-dense): run campaign slice 4 on batch fleet (jobs 62-76 of 1536)
- **PR #249**: docs: guard write-confinement investigation report and repro harness
- **PR #248**: sim(trim-dense): run campaign slice 3 on batch fleet (jobs 42-61 of 1536)
- **PR #245**: sim(trim-dense): campaign slice 2, 40 more batch jobs (42/1536)
- **PR #242**: sim(trim-dense): freeze campaign manifest, validate batch driver on live fleet slice
- **PR #241**: sim(trim-dense): resumable batch driver for the dense trim campaign
- **PR #240**: docs(item5): cite the 0xA4 -> 0xA5 step in ROWS row 2
- **PR #238**: sim(item5): re-centre calibration code to 0xA4 after the comparator-H fix (DR-0029)
- **PR #234**: fix(comparator): narrow the comparator-H output pull-down so a logic high is produced at fs / -40 C
- **PR #232**: sim(trim-transition): converge lsb_first bench and record nine-corner campaign
- **Issue #239** (closed): docs(item5): ROWS.md row 2 still says nominal LSB comes from the 0xA9 -> 0xAA step
- **Issue #235** (closed): Re-centre the calibration code after the comparator-H output-stage fix (row 1 fails at 0xA9)
- **Issue #229** (closed): Comparator-H output stage stalls oscillator at fs / -40 C, VDD >= 3.3 V (settled netlist)
- **Issue #103** (closed): Live trim-code transition bench: runt pulses and period excursions when code changes on a running oscillator
- **PR #230**: sim(startup): fs/-40 C no-oscillation is a real settled-netlist failure; settled startup bench run
- **PR #228**: sim(item5): run the 15-envelope corner campaign on the settled netlist; item 5 graded, still unmet
- **PR #224**: feat(sim): measured 27-point clk waveform campaign, convergence check and DR-0025
- **PR #223**: sim(recentre): P3 27-point batch confirmation and range/accuracy grader
- **Issue #227** (closed): Investigate fs / -40 C / VDD >= 3.3 V no-oscillation on the settled netlist; run startup bench (row 9) on it
- **Issue #213** (closed): Physical clock pulse-width and jitter campaign (deferred from #91)
- **Issue #201** (closed): T1 item 5 (corner verification): run the sim/item5 klt sim requests on the settled sizing and cite them with the row set
- **Issue #66** (closed): design: re-centre the oscillator for extracted parasitics and size a trim range that covers them (T1 item 5; operator ruling 2026-10-08)

### 2026-11-05

- **PR #221**: docs: record failed nine-corner batch re-run on v10 runner
- **PR #219**: sim: record second batch attempt of the P3 27-point grid
- **PR #220**: docs(sim): record startup batch attempt on runner v10 (worker lacks gf180mcuC PDK)

### 2026-11-04

- **PR #217**: refactor: share git HEAD/dirty capture across sim drivers
- **Issue #216** (closed): Consolidate duplicated git-revision helpers across sim drivers (inconsistent provenance on failure)

### 2026-10-28

- **PR #237**: build: attest T1 items 1, 9 and 10 with klt --attest inventories and CI drift checks
- **PR #208**: docs: state graded T1 verdict and missed ratified rows in README status
- **Issue #207** (closed): T1 status: correct README status and maturity-ladder claim — graded 8/11, items 5/6/7 unmet, two ratified rows missed

### 2026-10-27

- **PR #235**: refactor: share stream-generator scaffolding in flow/_stream_gen.py
- **PR #233**: build: re-stamp LVS/STA evidence under klt 0.8.0, cite functional-verification for T1 item 5
- **PR #229**: build: pin signoff grader to klayout-tools 0.8.0 and regenerate tier report
- **PR #226**: refactor: share one load_module helper across flow scripts and tests
- **PR #222**: docs(sim): document generated inputs and cold-clone runnability of benches
- **PR #205**: chore: move signoff and ERC klt pins to 0.8.0
- **Issue #203** (closed): Bump klayout-tools pin 0.4.0, 0.7.0, 2b1e55e51bb8 → 0.8.0

### 2026-10-23

- **PR #197**: feat(sim): store new campaign evidence via klt artifact, commit only manifests
- **Issue #196** (closed): Adopt the common artifact store for sim evidence (manifests in git, bytes via klt artifact)
- **PR #214**: feat(sim): device-inclusive C_SN of the compact v2 array

### 2026-10-21

- **PR #183**: ci: fold five offline-suite workflows into offline-suites matrix
- **Issue #182** (closed): Consolidate five remaining offline-suite workflows into offline-suites.yml matrix

### 2026-10-20

- **PR #209**: feat: re-characterise C_SN, parasitics and leakage for the compact bitcell layouts
- **Issue #100** (closed): Decision: 2T bitcell is 2.4x larger than public sky130 6T SRAM cell; README density requirement unmet

### 2026-10-17

- **PR #215**: feat: add paired netlist/SDF identifier sanitizer and item 7 retry record
- **PR #191**: sim(mc-groundwork): record retried batch smoke as a second diagnostic
- **PR #189**: docs(signoff): record item-6 Monte Carlo groundwork status and open gaps
- **Issue #186** (closed): T1 item 6: wire the DR-0022 mismatch injector into the MC bench, prove a klt yield envelope end to end, and declare the statistical row set
- **PR #188**: feat(mc-groundwork): add --inject-mismatch flag to gen_bench
- **PR #187**: feat(sim): add item-5 corner request set, row map and offline check
- **Issue #185** (closed): T1 item 5: express the ratified spec rows as klt sim corner requests and declare the item-5 row set in the manifest
- **PR #199**: refactor: share anchor-mutant helpers across integration mutation scripts
- **PR #198**: refactor: share klt sim request skeleton across sim generators
- **PR #193**: refactor: share mutation-check harness across digital run_mutation.sh scripts
- **PR #186**: refactor(sim): share sha256 and decided() helpers via _evidence_common
- **Issue #197** (closed): Consolidate anchor-style mutant helpers left over after #191 (3 run_mutation scripts)
- **Issue #191** (closed): Consolidate duplicated mutation-harness loop across digital/*/run_mutation.sh
- **Issue #187** (closed): Consolidate 6 copies of the gzip-aware JSON report loader into _evidence_common

### 2026-10-16

- **PR #181**: sim: re-qualify sense-stage under open_pdks f6eeac7
- **PR #178**: docs(layout): re-qualify G5 layout and sign-off records under open_pdks f6eeac7
- **Issue #172** (closed): Re-verify G5 layout and sign-off evidence under open_pdks f6eeac7
- **Issue #170** (closed): Re-qualify G3 sense-path records under open_pdks f6eeac7

### 2026-10-15

- **PR #176**: docs(spec): DR-0024 free-running rcosc_top, no enable pin
- **Issue #131** (closed): Decision record: enable/standby interface for rcosc_top and the start event behind the Startup and Iq rows
- **PR #173**: docs(pdk): inventory reference records to re-qualify under open_pdks f6eeac7
- **Issue #175** (closed): docs(pdk): reconcile stamped-file counts in pdk-requalification-inventory.md
- **Issue #117** (closed): Isolation-gate sizing and offset study: stored-'1' sense input erodes at fs/27 C with the #114 column slice
- **Issue #114** (closed): Design the column periphery (precharge, write driver, column select) to replace ideal sources in the read/write studies

### 2026-10-14

- **PR #172**: Item 7: batch klt pex campaign attempt (blocked on fleet PDK variant)

### 2026-10-13

- **PR #132**: ci: reproduce routability-corpus fixtures with flow/corpus.sh (#129)
- **PR #155**: feat(leakage): geometry-matched access-device leakage at extracted AD/AS/PD/PS (#149)
- **Issue #149** (closed): Geometry-matched access-device leakage: re-measure with extracted AD/AS/PD/PS (testbench passes none)

### 2026-10-12

- **Issue #148** (closed): Auditor Capability Request: Python runtime for offline signoff validation

### 2026-10-11

- **PR #168**: test: offline negative fixtures for signoff artifact provenance and binding guards
- **Issue #165** (closed): Signoff: add offline negative fixtures for artifact provenance and binding guards
- **Issue #68** (closed): signoff docs: correct post-layout open_pdks revision disclosure and stale 'pinned grader' wording (follow-up to #67)
- **Issue #98** (closed): Prepare offline trim-code batch requests and step-analysis harness
- **Issue #150** (closed): Tests: cover unresolved recursive deletion and shared-stash guard denials
- **Issue #153** (closed): CI: preserve all started signoff checks while superseding pending runs
- **Issue #161** (closed): Guard decision: preserve installed-file write protection for unresolved scratch fixture copies
- **Issue #163** (closed): Signoff: reject duplicate item keys before comparing fresh and committed grades
- **PR #160**: test: add offline regression suite for guard scratch-protection denials
- **PR #162**: CI: preserve all started signoff checks while superseding pending runs
- **PR #164**: docs: correct per-run open_pdks record and ERC/grader wording (#68)
- **PR #166**: signoff: reject duplicate item keys before comparing grades
- **PR #167**: Offline dense trim-code batch request generator and step analyzer (#98)
- **PR #158**: design: re-centre the timing ladder for extracted parasitics, DR-0023 proposed (Part of #66)
- **PR #157**: refactor(sim): consolidate remaining importlib loaders onto _module_loader
- **Issue #155** (closed): Consolidate remaining importlib loaders in sim analyzers and tests onto _module_loader
- **PR #153**: feat(layout): pin the array generation toolchain and compare --check output with the committed 4x4
- **PR #151**: feat(digital): SPI-configured scheduler driving the phase sequencer (#146)
- **PR #150**: Array-context C_SN comparison and proposed retention-input decision (#89)
- **Issue #91** (closed): Committed 4x4 array GDS no longer reproduces from generate_array.sh with current klt (0.6.0 vs 0.7.0 geometry drift)
- **Issue #89** (closed): Array-context storage-node capacitance is 17-22% below the single-cell C_SN used by retention
- **Issue #157** (closed): Define the physical SPI crossing and reset architecture before controller synthesis
- **Issue #156** (closed): Guard telemetry: retain confinement for unresolved scratch writes

### 2026-10-10

- **PR #201**: verification: validate ConfigMem map and transaction input before functional verdicts (#200)
- **PR #194**: docs(flow): document gate-sim scripts and add script-to-evidence index
- **PR #192**: Gate verification: replay route diagnostics on the synthesized tile (#189)
- **PR #190**: feat(flow): enforce append-only on sim/ evidence ledgers at PR time (#183)
- **PR #185**: feat(sim): control-jump directional route diagnostic through frame programming (#181)
- **PR #182**: Pin-index experiment: registered regcasc case with one-register transition equivalence (#160)
- **PR #179**: feat(sim): LUT-input directional route diagnostic through frame programming (#176)
- **PR #175**: G5: LUT basis diagnostic, every truth-table address on every BEL through the generated tile (#172)
- **PR #174**: ci: select generated-tile differential replay on its RTL and helper dependencies
- **PR #171**: ci: trigger harness-format drift check on document and fixture changes
- **PR #159**: Bound simulator processes; timeouts are infrastructure failures (#157)
- **PR #154**: fix(sim): default legacy sweep drivers to --jobs 2 (#139)
- **PR #152**: docs(readme): reconcile accuracy summary and ST comparison with DR-0017
- **Issue #139** (closed): Cap legacy sweep drivers' default --jobs and point grid runs at klt sim requests
- **Issue #143** (closed): README: reconcile accuracy summary and signed comparisons with DR-0017
- **Issue #146** (closed): Append-only guard: fail when Git comparison fails instead of certifying unchecked evidence
- **PR #147**: fix(sim): append-only guard fails when git comparison fails
- **Issue #65** (closed): T1 item 9: record the PDK revision in every simulation campaign manifest, not only the PDK family name
- **PR #145**: feat(sim): record PDK revision in campaign manifests (#65)
- **Issue #140** (closed): Align netlist-consistency workflow action pins with the rest of CI (checkout@v4/setup-python@v5 -> v7)
- **PR #142**: ci: align netlist-consistency action pins to v7 and split pytest install
- **Issue #119** (closed): Consolidate five copy-pasted offline pytest workflows into one matrix workflow
- **PR #141**: ci: consolidate offline pytest workflows into one matrix (#119)
- **Issue #130** (closed): Consolidate copy-pasted importlib module loaders in sim harnesses
- **PR #138**: refactor(sim): consolidate importlib module loaders in request generators
- **Issue #135** (closed): Implement and unit-test the DR-0022 mismatch-injection generator offline ahead of the item-6 campaign
- **PR #137**: feat(sim): offline DR-0022 mismatch-injection generator (#135)
- **Issue #134** (closed): CI never runs sim/discipline/test_outage.py (SOF-loss model tests); add it and an orphaned-test guard
- **PR #136**: ci: run discipline test_outage.py and guard against orphaned test files
- **Issue #128** (closed): Runtime discipline: model SOF reference loss and reacquisition offline
- **PR #133**: feat(sim): model SOF reference loss and reacquisition offline
- **Issue #125** (closed): Interior-temperature sweep: measure frequency-vs-T curvature between the -40/27/85 C grid points
- **PR #129**: feat(sim): offline interior-temperature curvature harness (#125)
- **Issue #122** (closed): Clk output-load sensitivity: frequency and edge shift vs capacitive load (no load ever swept; --load-f unused)
- **PR #127**: feat(waveform): offline clk output-load sensitivity sweep (#122)
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
- **PR #140**: Couple scheduler budgets to phase durations and verify executed-refresh deadlines (#138)
- **PR #126**: docs(sim): narrow 'a PR cannot weaken the check' claim
- **PR #122**: sim: closed-loop refresh operation, measured t_row_refresh_op (#110)
- **Issue #62** (closed): CI: enforce append-only sim/ results mechanically
- **Issue #138** (closed): Couple scheduler budgets to phase durations and verify executed-refresh deadlines
- **Issue #132** (closed): Auditor guard review: worktree-write-confinement-unresolved-var
- **Issue #110** (closed): Measure t_row_refresh_op with a closed-loop sense and write-back refresh operation
- **Issue #104** (closed): Auditor: worktree confinement rejects scratch-directory layout validation with shell variables

### 2026-10-09

- **PR #146**: Gate-sim negative controls: require completed functional rejection (#141)
- **PR #139**: G5: replay routability corpus against composed-tile gate netlist
- **PR #134**: G6: generate as-built harness bitstream-format table with drift check
- **PR #128**: G5: bounded single-tile routability corpus to inform ADR-0004 (#115)
- **PR #121**: feat(sim): gate-level bitstream-driven run on composed-tile netlist (#119)
- **PR #111**: feat(layout): experimental DRC/LVS/ERC observations + routing pitch on composed tile (G3, #108)
- **PR #110**: ci: run flow/audit-evidence.sh on PRs (#109)
- **PR #107**: feat(layout): experimental composed-tile physical canary (G2, #102)
- **PR #104**: Verify switch-matrix RTL against FABulous; fix generator select order (#96)
- **PR #93**: feat(rtl): composed LOGIC4 tile (BELs + switch matrix), RTL-only (#90)
- **PR #91**: G1: run pinned nextpnr on the generated LOGIC4 model (#87)
- **PR #88**: Generate LOGIC4 switch-matrix RTL and verify in sim/
- **PR #84**: spec: ADR-0004 for the five G1 tile-description discrepancies
- **PR #81**: feat(timing): cite a multi-corner klt sta envelope for T1 item 5 (#68)
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
- **PR #99**: feat(digital): integrate SPI config with runtime refresh scheduler (#93)
- **PR #95**: Monte Carlo mismatch study of the sense stage: input-referred offset at the restricted corners (#81)
- **PR #87**: feat(digital): proposed SPI control interface model (#83)
- **PR #79**: Refresh scheduler behavioral model with deadline-invariant testbench (#24 item 3)
- **PR #77**: Sense-stage characterization at the restricted corners (#60)
- **PR #71**: ci(sim): guard simulation evidence with exact byte-prefix comparisons
- **PR #70**: spec: proposed operating-range restriction for the cold corner (outcome C)
- **PR #69**: fix(signoff): scope T1 items 3/4 evidence to analog partition (met 5 -> 3)
- **PR #66**: refactor(sim): consolidate duplicated SPICE/waveform helpers (#58)
- **PR #65**: feat: refresh-overhead envelope (N_rows x t_row_refresh_op) (#59)
- **PR #64**: ci: run evidence-chain Python checks (test_analysis, test_variants, check_evidence_index)
- **PR #113**: feat(digital): analog phase-control contract, sequencer and mutation suite
- **PR #112**: design: sense latch schematic + derived netlist tied to sense-stage deck (#109)
- **PR #106**: CI: run behavioral SPI and refresh Verilog regressions with pinned Icarus (#105)
- **PR #103**: docs(sim): define correction-record mechanism for appended evidence
- **PR #101**: Density vs 6T SRAM: area per bit from committed 4x4 array (#97)
- **Issue #83** (closed): Propose the SPI control interface spec with a behavioral SPI-slave model and testbench (#24 item 4)
- **Issue #82** (closed): Draft macro-level pass conditions for epic #24 items 2-6 as a PROPOSED record
- **Issue #81** (closed): Monte Carlo mismatch study of the sense stage: input-referred offset at the restricted corners
- **Issue #80** (closed): Extract read-bitline and wordline parasitics from the 4x4 array to replace the C_RBL assumption
- **Issue #74** (closed): Refresh scheduler behavioral model with deadline-invariant testbench (#24 item 3)
- **Issue #67** (closed): CI: guard simulation evidence with exact byte-prefix comparisons
- **Issue #63** (closed): README: reflect cold-corner finding and restricted operating range by reference (after #56)
- **Issue #60** (closed): Sense-stage characterization at the restricted corners (after #56)
- **Issue #59** (closed): Refresh-overhead envelope: evaluate the ratified §7 formula over N_rows x t_row_refresh_op
- **Issue #58** (closed): Consolidate duplicated waveform/SPICE helpers in sim runners into _evidence_common
- **Issue #56** (closed): spec: write the operating-range restriction for the cold corner as a proposed decision record (outcome C, operator ruling 2026-10-08)
- **Issue #55** (closed): T1 items 3 and 4: stop the bitcell's DRC/LVS reports grading the unbuilt digital partition
- **Issue #108** (closed): Define the digital-to-analog phase-control contract with an ordering-checked sequencer model
- **Issue #105** (closed): CI: run behavioral SPI and refresh Verilog regressions with a pinned simulator

### 2026-10-08

- **PR #76**: feat(design): pin FABulous 2.2.0 and commit LOGIC4 tile description (G1)
- **PR #80**: feat(sim): startup-time testbench for the 10 us row (partial evidence) (#78)
- **Issue #78** (closed): Add a startup-time testbench for the ratified 10 us row (currently not evaluated)
- **PR #75**: Item 7: klt pex inputs + single-corner probe (grid blocked by fleet runner version) (#70)
- **PR #74**: docs(spec): DR-0019 classify spec rows statistical vs deterministic, MC evidence plan
- **PR #73**: chore(signoff): move grader pin to klayout-tools 0.7.0 release
- **PR #67**: signoff: bind T1 items 1, 2, 9, 10 to audited artifacts; move grader pin to klayout-tools 3a75c3ae
- **Issue #72** (closed): Evaluate moving the signoff grader pin from a klayout-tools git commit to the 0.7.0 release
- **Issue #71** (closed): Item 6: decision record classifying spec rows as statistical vs deterministic, with the Monte Carlo evidence plan
- **Issue #64** (closed): T1 items 1, 9, 10 (and item 2's binding): cite artifact-anchored evidence now that klt signoff can bind it (klayout-tools#2843)
- **PR #57**: feat: cite T1 item 11 (analog) via psub substrate tie; pin klt v0.6.0 (#54)
- **Issue #54** (closed): T1 item 11 (analog): declare the array's substrate tie, re-run klt erc and LVS, and cite the power-delivery row

### 2026-10-07

- **PR #50**: Prepare supply and reliability decision record for the sense-path contract (#49)

### 2026-10-05

- **Issue #45** (closed): [Epic #24] Characterize achievable stored levels and loaded-column read separation

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
