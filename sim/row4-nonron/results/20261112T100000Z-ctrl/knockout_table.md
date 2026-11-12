# Knock-out isolation of the ss charge RC term (generated)

ss, 27 C, code 212. tau = t_chg / ln((VDD-v0)/(VDD-vh)); span = eps(3.6 V) - eps(3.0 V) in pt vs the same netlist at 3.3 V.

| variant | tau 3.0 V (ps) | tau 3.3 V | tau 3.6 V | tau(3.0)/tau(3.6) | RC-term span | total span | f(3.3 V) MHz |
|---|---|---|---|---|---|---|---|
| ctrl: unmodified DUT | 13791.7 | 13475.3 | 13210.0 | 1.0440 | +3.03 | +6.13 | 47.95 |
| nojb: bank switch junctions removed | 13221.2 | 12914.3 | 12683.9 | 1.0424 | +2.89 | +6.13 | 49.43 |
| nojd: discharge device junction removed | 13589.9 | 13285.3 | 13001.1 | 1.0453 | +3.09 | +6.16 | 48.14 |
| nojall: both removed | 13048.7 | 12724.5 | 12482.6 | 1.0454 | +3.06 | +6.16 | 49.63 |
| capx: +200 fF linear on vc | 19119.4 | 18662.9 | 18332.4 | 1.0429 | +3.18 | +5.80 | 37.15 |
