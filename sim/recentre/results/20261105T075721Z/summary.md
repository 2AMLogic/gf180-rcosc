# P3 27-point confirmation: second batch submission FAILED (new gap: runner has no PDK)

Same three requests as `../20261011T034200Z/` (`sim/recentre/p3/request_{tt,ff,ss}.json`, 3 x 9 corners),
submitted on 2026-11-05 with `KLT_SIM_BACKEND=batch klt sim <request> -o out_<p> --format json`
from client `klt 0.9.1.dev17+gd76e6fe1cb7a`. Raw reports `report_<p>.json`, client stderr `stderr_<p>.txt`,
receipts `out_<p>/batch-receipt.json`.

| request | batch job id | state | exit | runner klt | runner_compatibility | corners errored |
|---|---|---|---|---|---|---|
| tt | `klt-sim-6db2baa6f30f` | failed | 1 | 0.9.0 | match | 9 of 9 |
| ff | `klt-sim-562932977223` | failed | 1 | 0.9.0 | match | 9 of 9 |
| ss | `klt-sim-2bc31d972ae2` | failed | 1 | 0.9.0 | match | 9 of 9 |

The version mismatch of the earlier record (klayout-tools#2851) and the include-file failure (#2882) are
gone. The jobs now fail earlier for a different reason (`batch_job_failed`, 5-6 s): the runner image
(`eda-batch-runner` v10, `ami-04591566329422a44`) has no `gf180mcuC` PDK under `PDK_ROOT=/opt/pdk` or any
search root, and `models_staged` is false. Filed generically as 2AMLogic/klayout-tools#4947.

No grid was run locally. **There is still no 27-point result and none may be claimed.** AC 3 stays open;
re-submit the same three requests once the runner carries the PDK (or `klt sim` stages the models).
