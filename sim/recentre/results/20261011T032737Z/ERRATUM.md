# Erratum: raw-log collision in run 20261011T032737Z (PR #158 review)

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
| tt:27:3.3 | 0xAE | 47894870.0 | `prop_r080_17x10_pt_0xAE.log` | overwritten | `sim/recentre/results/20261011T035524Z/`, `sim/recentre/corners/explore-20261011T035524Z-points/prop_r080_17x10_pt_tt_27C_3.3V_0xAE.log` |
| tt:-40:3 | 0xAE | 46157030.0 | `prop_r080_17x10_pt_0xAE.log` | overwritten | `sim/recentre/results/20261011T035530Z/`, `sim/recentre/corners/explore-20261011T035530Z-points/prop_r080_17x10_pt_tt_m40C_3V_0xAE.log` |
| tt:85:3.6 | 0xAE | 49143990.0 | `prop_r080_17x10_pt_0xAE.log` | intact (last writer of that file) | - |
| ff:27:3.3 | 0x5F | 48007080.0 | `prop_r080_17x10_pt_0x5F.log` | overwritten | `sim/recentre/results/20261011T035537Z/`, `sim/recentre/corners/explore-20261011T035537Z-points/prop_r080_17x10_pt_ff_27C_3.3V_0x5F.log` |
| ff:-40:3.6 | 0x5F | 43743760.0 | `prop_r080_17x10_pt_0x5F.log` | overwritten | `sim/recentre/results/20261011T035543Z/`, `sim/recentre/corners/explore-20261011T035543Z-points/prop_r080_17x10_pt_ff_m40C_3.6V_0x5F.log` |
| ff:85:3 | 0x5F | 51699210.0 | `prop_r080_17x10_pt_0x5F.log` | intact (last writer of that file) | - |
| ss:27:3.3 | 0xDB | 48042150.0 | `prop_r080_17x10_pt_0xDB.log` | overwritten | `sim/recentre/results/20261011T035550Z/`, `sim/recentre/corners/explore-20261011T035550Z-points/prop_r080_17x10_pt_ss_27C_3.3V_0xDB.log` |
| ss:-40:3 | 0xDB | 46330950.0 | `prop_r080_17x10_pt_0xDB.log` | overwritten | `sim/recentre/results/20261011T035556Z/`, `sim/recentre/corners/explore-20261011T035556Z-points/prop_r080_17x10_pt_ss_m40C_3V_0xDB.log` |
| ss:85:3.6 | 0xDB | 49321910.0 | `prop_r080_17x10_pt_0xDB.log` | intact (last writer of that file) | - |
