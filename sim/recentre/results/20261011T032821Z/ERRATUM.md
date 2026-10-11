# Erratum: raw-log collision in run 20261011T032821Z (PR #158 review)

`explore.py points` named each raw log `<candidate>_pt_<code>.log`, without the corner, so points of
this run that share a trim code wrote the same file and only the last one survived. The `log` column of
`results.csv` is therefore wrong for the rows marked *overwritten* below: the file it names holds a
different corner (its first line states which). `results.csv` and the surviving logs are left as
committed. Each overwritten row was re-run as its own single-corner `explore.py points` invocation
(one ngspice process) under a new run id, with the corner in the log name; every re-run reproduced
`f_hz` and `iq_a` bit-identically. `report_explore.py` takes the newest run per key, so summaries
generated after this erratum cite the re-run logs.

| corner | code | f_hz | committed log | status | re-run (new run id) and its log |
|---|---|---|---|---|---|
| tt:27:3.3 | 0xAE | 46171000.0 | `prop_r080_17x10_pt_0xAE.log` | intact (last writer of that file) | - |
| ff:27:3.3 | 0x5F | 47933600.0 | `prop_r080_17x10_pt_0x5F.log` | overwritten | `sim/recentre/results/20261011T035602Z/`, `sim/recentre/corners/explore-20261011T035602Z-points/prop_r080_17x10_pt_ff_27C_3.3V_0x5F.log` |
| ff:-40:3.6 | 0x5F | 46355320.0 | `prop_r080_17x10_pt_0x5F.log` | intact (last writer of that file) | - |
| ss:27:3.3 | 0xDB | 44887070.0 | `prop_r080_17x10_pt_0xDB.log` | intact (last writer of that file) | - |
