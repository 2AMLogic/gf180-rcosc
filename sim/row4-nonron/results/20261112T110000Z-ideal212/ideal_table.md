# Real bank vs ideal-switch bank (generated)

ss, 27 C. tau = t_chg / ln((VDD-v0)/(VDD-vh)) (ps). Spans are eps(3.6 V) - eps(3.0 V) in pt against the same netlist and code at 3.3 V.

| bank | code | tau 3.0 V | tau 3.3 V | tau 3.6 V | tau(3.0)/tau(3.6) | RC-term span | total span | f(3.3 V) MHz |
|---|---|---|---|---|---|---|---|---|
| committed (TGs) | 0 | 33747 | 33559 | 33574 | 1.0052 | +0.43 | +1.84 | 22.62 |
| committed (TGs) | 212 | 13792 | 13475 | 13210 | 1.0440 | +3.03 | +6.13 | 47.95 |
| committed (TGs) | 255 | 10076 | 9694 | 9408 | 1.0709 | +4.33 | +7.91 | 61.23 |
| ideal switches | 0 | 32673 | 32630 | 32531 | 1.0044 | +0.37 | +1.89 | 23.22 |
| ideal switches | 212 | 10376 | 10356 | 10338 | 1.0037 | +0.24 | +3.95 | 58.26 |
| ideal switches | 255 | 5263 | 5254 | 5265 | 0.9996 | -0.03 | +6.01 | 89.13 |
