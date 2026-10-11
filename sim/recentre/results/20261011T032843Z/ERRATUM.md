# Erratum: raw-log collision in run 20261011T032843Z (PR #158 review)

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
| tt:27:3.3 | 0x00 | 26834970.0 | `prop_r080_17x10_pt_0x00.log` | overwritten | `sim/recentre/results/20261011T035609Z/`, `sim/recentre/corners/explore-20261011T035609Z-points/prop_r080_17x10_pt_tt_27C_3.3V_0x00.log` |
| tt:27:3.3 | 0xFF | 66068930.0 | `prop_r080_17x10_pt_0xFF.log` | overwritten | `sim/recentre/results/20261011T035616Z/`, `sim/recentre/corners/explore-20261011T035616Z-points/prop_r080_17x10_pt_tt_27C_3.3V_0xFF.log` |
| ss:27:3.3 | 0xFF | 52622170.0 | `prop_r080_17x10_pt_0xFF.log` | intact (last writer of that file) | - |
| ff:27:3.3 | 0x00 | 35215630.0 | `prop_r080_17x10_pt_0x00.log` | intact (last writer of that file) | - |
