# fs / -40 C no-oscillation root cause (issue #227)

Single-corner local probes explaining why the settled P3 netlist does not oscillate at fs / -40 C for
VDD >= 3.3 V (finding from the item-5 corner campaign, `sim/item5/results/20261106T051832Z/`).

| file | role |
|---|---|
| `gen_probes.py` | writes `probes/` (one `klt sim` request + testbench per probe; every request is one process x one temperature, so it stays local: `klt sim --backend local`) |
| `probes/` | generated requests, testbenches and DUT copies (settled P3 netlist; pre-re-centre schematic for `schem_*`) |
| `results/<runid>/` | append-only evidence: `summary.md` (probe table, node states, root cause), `report_<probe>.json`, `out_<probe>/` (deck, ngspice log, waveforms of the two ramp probes) |

Result (see `results/20261106T061000Z/summary.md`): a real design failure of the settled netlist at that
corner, not a simulator artifact. Reproduce: `python3 -I gen_probes.py` then
`klt sim --backend local probes/request_<probe>.json -o OUT --format json`.
The follow-up design issue is #229. The settled-netlist startup bench is in
`sim/startup-settled/`.
