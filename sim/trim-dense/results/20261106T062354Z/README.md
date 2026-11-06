# #87 trim-dense: Step 0 fleet gate only (PARTIAL; the 1536-job campaign was NOT run)

Step 0 (issue #87 acceptance 1): one single-corner request from `sim/trim-dense/prepare.py`,
ext variant (`sim/recentre/p3/rcosc_top_p3.spice`, P3), tt / 27 C / 3.3 V, trim code 0x80,
`gf180mcuC`, submitted with `uvx --from klayout-tools==0.9.0 klt sim request_c80.json --backend batch --format json`.

- Result: batch job `klt-sim-9f035a0aab64` returned `status: pass`, 1/1 corner, `fosc` = 39.4758 MHz,
  runner klt 0.9.0 (`runner_compatibility: match`), ngspice-46, AMI ami-095c25ae241a4d360, spot m7i.4xlarge.
- Files: `step0/stdout.txt` (report, incl. `environment.remote`), `step0/out_ext_tt_c80/batch-receipt.json`,
  `step0/request_c80.json`, `step0/tb_c80.spice`; `provenance.json` / `manifest.template.json` describe the
  full generated bench (regenerate with `prepare.py`; the 1536 request files are not committed).
- No local ngspice was run. This is a gate result, not a trim-step verdict: no DNL/monotonicity claim follows.
- Netlist note: `sch` = `sim/pvt-postlayout/klt-pex/rcosc_top_schematic.spice` (pre-P3 sizing), `ext` = P3.
  P3 pins are `vdd vss clk t0..t7`; `prepare.py` was extended to follow the netlist's pin order.
