# Which P3 change stops the comparator-H start-up at fs / -40 C? (issue #229)

Follow-up to `sim/startup-fs-m40c/` (#227). Every probe is **one corner** (fs process, -40 C, one supply, DC-step
supply, trim code 0xA9, 1.2 us transient), run locally with `klt sim --backend local`; no grid was launched
locally. DUT variants are derived from the settled P3 netlist (`sim/recentre/p3/rcosc_top_p3.spice`) by
`gen_probes.py`, which imports the #227 probe generator read-only. `probes/` holds the generated requests,
testbenches, DUT variants, `report_<probe>.json` and `out_<probe>/` (deck + ngspice log; raw waveforms not kept).

Reproduce: `python3 -I gen_probes.py` then
`klt sim --backend local probes/request_<probe>.json -o OUT --format json`.

## Results (fosc over edges 5..25; "no start" = the clk stays flat, Iq 463 uA at 3.3 V / 522 uA at 3.6 V)

| probe | what is changed vs. settled P3 | 3.3 V | 3.6 V |
|---|---|---|---|
| `p3` | nothing (control; reproduces #227) | no start | no start |
| `noladder` | ladder lengths back to the committed extraction | no start | no start |
| `nomim` | fixed 217.2 fF MiM card back | no start | no start |
| `pex_orig` | both reverted = the committed extraction | no start | no start |
| `noC` / `noR` | extracted net C removed / series R set to 1 mohm | no start | - |
| `nogeom` | layout `AS/AD/PS/PD` dropped on every device | 49.73 MHz | - |
| `g_cmph`, `g_notcmph` | geometry dropped on comparator-H devices only / on all other devices only | 47.49 / 49.28 MHz | - |
| `g_pair`, `g_load` | geometry dropped on the input pair / the mirror loads only | no start | - |
| `g_out`, `g_tail` | geometry dropped on the output inverter / the tail only | 47.13 / 47.08 MHz | - |
| `p3_c1` .. `p3_c4` | MBUFN 1u / MBUFP 8u / MBUFN L 1u / both W changes | 48.39 / 48.33 / 47.23 / 49.18 MHz | 49.19 / 49.13 / 47.73 / 50.04 MHz |
| `pex_c1` .. `pex_c4` | same four candidates on the committed extraction | 36.90 / 36.79 / 36.16 / 37.33 MHz | 37.39 / 37.29 / 36.47 / 37.87 MHz |
| `cmphfix` | the **adopted** fix on a fresh extraction of the revised layout (`sim/cmph-fix/rcosc_top_p3_cmphfix.spice`) | 48.37 MHz | 49.19 MHz |

Reading: (1) neither the ladder x0.70 nor the MiM card of DR-0023 is the cause - the committed extraction
already does not start; (2) the layout-extracted diffusion geometry moves the start-up (dropping it on any
sufficiently large subset flips the outcome), series R and net C alone do not, so the stuck state is a coexisting
stable operating point of the output stage whose basin is set by small perturbations, not a one-parameter
artifact; (3) every output-stage candidate removes it, with Iq 287-380 uA (limit 500 uA). The adopted fix is `c1`
(narrowest, smallest frequency shift versus its alternatives); see DR-0028.
