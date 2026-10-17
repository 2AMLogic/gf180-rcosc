# Injected-mismatch pipeline smoke (issue #186) -- DIAGNOSTIC, no simulation result

Pipeline proof, **not a yield claim**. Benches generated with
`python3 gen_bench.py --inject-mismatch` (DR-0022 section 4 injector, symbolic
`mm_scale`=1); per-instance manifests are the `*.mismatch.json` files.

Submitted with `uvx --from "klayout-tools==0.7.0" klt sim <request> --backend batch`
(seed 20261008; control n=3, smoke n=5), run 2026-10-17. Both requests went to
the Spot batch fleet (jobs `klt-sim-3123505a837e`, `klt-sim-88c46ab81697`) and
**failed in ~5 s with exit 1, before any ngspice run**: the fleet runner's klt
reported that no `gf180mcuC` PDK install was found (it searched `PDK_ROOT=/opt/pdk`,
`/root/.ciel`, `/root/.volare`, `/root/pdks`, `/usr/local/share/pdk`, ...). All
corners errored (`batch_job_failed`); no waveforms or measurements exist. No
local fallback was run (host rule). The negative-control (3x sigma) run was not
attempted for the same reason. The `klayout-tools[yield]==0.7.0` extra does not
resolve (`klt-yield-native` absent from the registry), so `klt yield` was not run.

Tool versions: client and runner klt 0.7.0 (`runner_compatibility: match`).
