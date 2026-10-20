# Injected-mismatch pipeline smoke, retry (issue #186) -- DIAGNOSTIC, no simulation result

Pipeline proof, **not a yield claim**. Retry of `../20261017T200500Z/` after
klayout-tools#3746 was closed. Benches generated with
`python3 gen_bench.py --inject-mismatch` (DR-0022 section 4 injector, symbolic
`mm_scale`=1); per-instance manifests are the `*.mismatch.json` files.

Submitted once: `uvx --from "klayout-tools==0.7.0" klt sim request_smoke_mm_inj.json --backend batch`
(seed 20261008, n=5), run 2026-10-17. The Spot fleet job `klt-sim-42f468fd4585`
**failed in 6 s with exit 1, before any ngspice run**: the runner's klt found no
`gf180mcuC` PDK install (searched `PDK_ROOT=/opt/pdk`, `/root/.ciel`,
`/root/.volare`, ...). All 5 corners errored (`batch_job_failed`); no
waveforms or measurements exist. Client and runner klt are both 0.7.0
(`runner_compatibility: match`).

Why it still fails: #3746 was closed as not planned. The missing variant is an
infra backfill of the batch image (operator step), not a tool change. The
suggested workarounds do not apply: `--backend local` for a multi-sample run is
barred by the host rule, and `models.pdk: gf180mcuD` would change the design's
PDK variant. The 3x-sigma and zero-mismatch negative controls were not
submitted (same failure expected). `klayout-tools[yield]==0.7.0` still does not
resolve (`klt-yield-native` absent from the registry; klayout-tools#2900), so
`klt yield` was not run.
