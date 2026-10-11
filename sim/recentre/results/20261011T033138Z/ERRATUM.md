# Erratum: raw-log collision in run 20261011T033138Z (PR #158 review)

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
| tt:27:3.3 | 0xAF | 47885880.0 | `optB_r066_24x10_pt_0xAF.log` | overwritten | `sim/recentre/results/20261011T035443Z/`, `sim/recentre/corners/explore-20261011T035443Z-points/optB_r066_24x10_pt_tt_27C_3.3V_0xAF.log` |
| tt:-40:3 | 0xAF | 46219240.0 | `optB_r066_24x10_pt_0xAF.log` | overwritten | `sim/recentre/results/20261011T035450Z/`, `sim/recentre/corners/explore-20261011T035450Z-points/optB_r066_24x10_pt_tt_m40C_3V_0xAF.log` |
| tt:85:3.6 | 0xAF | 49088660.0 | `optB_r066_24x10_pt_0xAF.log` | intact (last writer of that file) | - |
| ff:27:3.3 | 0x65 | 47992700.0 | `optB_r066_24x10_pt_0x65.log` | overwritten | `sim/recentre/results/20261011T035457Z/`, `sim/recentre/corners/explore-20261011T035457Z-points/optB_r066_24x10_pt_ff_27C_3.3V_0x65.log` |
| ff:-40:3.6 | 0x65 | 43323320.0 | `optB_r066_24x10_pt_0x65.log` | overwritten | `sim/recentre/results/20261011T035503Z/`, `sim/recentre/corners/explore-20261011T035503Z-points/optB_r066_24x10_pt_ff_m40C_3.6V_0x65.log` |
| ff:85:3 | 0x65 | 51826560.0 | `optB_r066_24x10_pt_0x65.log` | intact (last writer of that file) | - |
| ss:27:3.3 | 0xDB | 48017090.0 | `optB_r066_24x10_pt_0xDB.log` | overwritten | `sim/recentre/results/20261011T035510Z/`, `sim/recentre/corners/explore-20261011T035510Z-points/optB_r066_24x10_pt_ss_27C_3.3V_0xDB.log` |
| ss:-40:3 | 0xDB | 46292760.0 | `optB_r066_24x10_pt_0xDB.log` | overwritten | `sim/recentre/results/20261011T035517Z/`, `sim/recentre/corners/explore-20261011T035517Z-points/optB_r066_24x10_pt_ss_m40C_3V_0xDB.log` |
| ss:85:3.6 | 0xDB | 49307640.0 | `optB_r066_24x10_pt_0xDB.log` | intact (last writer of that file) | - |
