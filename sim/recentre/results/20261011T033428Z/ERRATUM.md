# Erratum: raw-log collision in run 20261011T033428Z (PR #158 review)

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
| tt:27:3.3 | 0xA9 | 48047720.0 | `r070_20x10_pt_0xA9.log` | overwritten | `sim/recentre/results/20261011T035323Z/`, `sim/recentre/corners/explore-20261011T035323Z-points/r070_20x10_pt_tt_27C_3.3V_0xA9.log` |
| tt:-40:3 | 0xA9 | 46193180.0 | `r070_20x10_pt_0xA9.log` | overwritten | `sim/recentre/results/20261011T035327Z/`, `sim/recentre/corners/explore-20261011T035327Z-points/r070_20x10_pt_tt_m40C_3V_0xA9.log` |
| tt:85:3.6 | 0xA9 | 49345170.0 | `r070_20x10_pt_0xA9.log` | intact (last writer of that file) | - |
| ff:27:3.3 | 0x59 | 48081100.0 | `r070_20x10_pt_0x59.log` | overwritten | `sim/recentre/results/20261011T035337Z/`, `sim/recentre/corners/explore-20261011T035337Z-points/r070_20x10_pt_ff_27C_3.3V_0x59.log` |
| ff:-40:3.6 | 0x59 | 43482340.0 | `r070_20x10_pt_0x59.log` | overwritten | `sim/recentre/results/20261011T035313Z/`, `sim/recentre/corners/explore-20261011T035313Z-points/r070_20x10_pt_ff_m40C_3.6V_0x59.log` |
| ff:85:3 | 0x59 | 51915870.0 | `r070_20x10_pt_0x59.log` | intact (last writer of that file) | - |
| ss:27:3.3 | 0xD7 | 48123600.0 | `r070_20x10_pt_0xD7.log` | overwritten | `sim/recentre/results/20261011T035344Z/`, `sim/recentre/corners/explore-20261011T035344Z-points/r070_20x10_pt_ss_27C_3.3V_0xD7.log` |
| ss:-40:3 | 0xD7 | 46460850.0 | `r070_20x10_pt_0xD7.log` | overwritten | `sim/recentre/results/20261011T035350Z/`, `sim/recentre/corners/explore-20261011T035350Z-points/r070_20x10_pt_ss_m40C_3V_0xD7.log` |
| ss:85:3.6 | 0xD7 | 49363070.0 | `r070_20x10_pt_0xD7.log` | intact (last writer of that file) | - |
