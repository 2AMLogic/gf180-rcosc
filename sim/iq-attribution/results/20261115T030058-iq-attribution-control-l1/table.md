# Row 8 per-stage running-Iq attribution (issue #347) -- results/20261115T030058-iq-attribution-control-l1 (L=1U control, sim/cmph-fix extraction, probed copy)

Source: `results/20261115T030058-iq-attribution-control-l1 (L=1U control, sim/cmph-fix extraction, probed copy)`

integration window: DR-0009 / DR-0044 `iq_run` basis -- 20 whole oscillation periods (clk rising edges 5 -> 25), supply charge integrated on 1 nF; not comparable to item-5's fixed 200-1200 ns window (its row-8 bench), which produced e.g. 559.4 uA at ff / 85 C / 3.6 V on a different netlist and basis

Zero by construction (no vdd terminal; the stage map asserts it): timing (XCTIMING), disch (X$26) -- these stages draw exactly 0 A of supply current; no measurement exists for them.

## Back-to-back check (probed DUT total vs DR-0044's committed figure, same window)

| cell | DR-0044 committed (uA) | this campaign probed total (uA) | delta | tolerance |
|---|---|---|---|---|
| 0xFF / 3.6 V / ff / 85 C | 779.4 | 781.0 | +0.20 % | +/-1 % |

## Per-cell attribution (uA)

Window as stated above. `>500` marks the cells over the ratified limit among DR-0044's 108-cell table (DR-0044's own figure quoted for reference; the campaign number is this campaign's probed total). Residue = total - sum(stages): where vdd-network parasitic displacement current and any unresolved terms land.

| code | VDD | die | T (C) | bias | comparator-H | comparator-L | latch (+clk drive) | trim bank | sum | total | residue (uA) | residue (%) | DR-0044 | |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0xFF | 3.6 | ff | -40 | 61.3 | 177.2 | 119.0 | 73.6 | 249.3 | 680.4 | **680.4** | -0.003 | -0.000 | - |  |
| 0xFF | 3.6 | ff | 27 | 67.7 | 192.4 | 127.6 | 72.2 | 254.3 | 714.2 | **714.2** | -0.004 | -0.001 | - |  |
| 0xFF | 3.6 | ff | 85 | 76.5 | 222.5 | 144.9 | 74.3 | 262.8 | 781.0 | **781.0** | 0.000 | +0.000 | 779.4 | **>500** |

Sum check: per-stage sum within +/-1 % of the measured total at 3/3 cells.
