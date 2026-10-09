# Trim-transition analysis analysis

**Analysis of simulator output; evidence status is set by the originating campaign record**

Note: single-corner local debug probe (tt, 3.3 V, 27 C, lsb_first skew), klt sim --backend local; NOT the nine-corner campaign

32 event row(s): 23 PASS, 9 FLAG, 0 VIOLATION, 0 FAIL.
Screens (bench thresholds, not ratified spec rows): VIOLATION = runt / missing-extra edge / never settles; FLAG = excursion > 5 % or settle > 3 cycles.

| process | VDD (V) | skew | step | dir | events | min P (ns) | max P (ns) | P old->new (ns) | excursion max (%) | runt | missing | settle max (cyc) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tt | 3.3 | lsb_first | carry_3F_40 | down | 4 | 30.547 | 30.978 | 30.555->30.690 | 0.95 | False | False | 2 | PASS |
| tt | 3.3 | lsb_first | carry_3F_40 | up | 4 | 29.543 | 30.695 | 30.690->30.555 | 3.32 | False | False | 14 | FLAG |
| tt | 3.3 | lsb_first | carry_7F_80 | down | 4 | 18.687 | 25.000 | 24.928->23.393 | 18.85 | False | False | 2 | FLAG |
| tt | 3.3 | lsb_first | carry_7F_80 | up | 4 | 22.406 | 24.921 | 23.391->24.928 | 4.22 | False | False | 2 | PASS |
| tt | 3.3 | lsb_first | carry_BF_C0 | down | 4 | 16.137 | 19.134 | 17.924->17.387 | 6.98 | False | False | 2 | FLAG |
| tt | 3.3 | lsb_first | carry_BF_C0 | up | 4 | 16.943 | 17.922 | 17.386->17.924 | 2.55 | False | False | 2 | PASS |
| tt | 3.3 | lsb_first | noncarry_A2_A3 | down | 4 | 20.432 | 20.826 | 20.712->20.823 | 1.36 | False | False | 2 | PASS |
| tt | 3.3 | lsb_first | noncarry_A2_A3 | up | 4 | 20.713 | 21.072 | 20.825->20.712 | 1.20 | False | False | 2 | PASS |
