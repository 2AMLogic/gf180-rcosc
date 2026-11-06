# Trim-transition analysis analysis

**Analysis of simulator output; evidence status is set by the originating campaign record**

Note: batch run klt 0.9.2 client / runner 0.9.0, template v11

585 event row(s): 305 PASS, 249 FLAG, 22 VIOLATION, 9 FAIL.
Screens (bench thresholds, not ratified spec rows): VIOLATION = runt / missing-extra edge / never settles; FLAG = excursion > 5 % or settle > 3 cycles.

| process | VDD (V) | skew | step | dir | events | min P (ns) | max P (ns) | P old->new (ns) | excursion max (%) | runt | missing | settle max (cyc) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ff | 3 | lsb_first | None | None | 1 | - | - | -->- | - | - | - | - | FAIL (1 failed) |
| ff | 3 | msb_first | carry_3F_40 | down | 4 | 22.820 | 24.232 | 22.839->22.960 | 5.54 | False | False | 18 | FLAG |
| ff | 3 | msb_first | carry_3F_40 | up | 4 | 21.077 | 22.972 | 22.963->22.839 | 7.65 | False | False | 11 | FLAG |
| ff | 3 | msb_first | carry_7F_80 | down | 4 | 17.649 | 20.267 | 18.837->17.648 | 7.59 | False | False | 2 | FLAG |
| ff | 3 | msb_first | carry_7F_80 | up | 4 | 12.177 | 18.834 | 17.645->18.837 | 30.97 | False | False | 19 | FLAG |
| ff | 3 | msb_first | carry_BF_C0 | down | 4 | 13.340 | 15.418 | 13.748->13.341 | 12.16 | False | False | 2 | FLAG |
| ff | 3 | msb_first | carry_BF_C0 | up | 4 | 9.808 | 13.743 | 13.339->13.748 | 26.48 | False | False | 2 | FLAG |
| ff | 3 | msb_first | noncarry_A2_A3 | down | 4 | 15.726 | 15.805 | 15.754->15.838 | 0.18 | False | False | 2 | PASS |
| ff | 3 | msb_first | noncarry_A2_A3 | up | 4 | 15.749 | 16.063 | 15.837->15.754 | 1.44 | False | False | 1 | PASS |
| ff | 3 | none | carry_3F_40 | down | 4 | 22.828 | 23.843 | 22.838->22.965 | 3.88 | False | False | 21 | FLAG |
| ff | 3 | none | carry_3F_40 | up | 4 | 21.768 | 22.967 | 22.964->22.838 | 4.67 | False | False | 10 | FLAG |
| ff | 3 | none | carry_7F_80 | down | 4 | 17.644 | 19.542 | 18.836->17.643 | 3.77 | False | False | 23 | FLAG |
| ff | 3 | none | carry_7F_80 | up | 4 | 15.393 | 18.833 | 17.645->18.836 | 12.81 | False | False | 2 | FLAG |
| ff | 3 | none | carry_BF_C0 | down | 4 | 13.336 | 14.671 | 13.748->13.340 | 6.70 | False | False | 42 | FLAG |
| ff | 3 | none | carry_BF_C0 | up | 4 | 12.030 | 13.748 | 13.341->13.748 | 9.83 | False | False | 2 | FLAG |
| ff | 3 | none | noncarry_A2_A3 | down | 4 | 15.522 | 15.831 | 15.754->15.839 | 1.48 | False | False | 1 | PASS |
| ff | 3 | none | noncarry_A2_A3 | up | 4 | 15.745 | 15.916 | 15.838->15.754 | 0.51 | False | False | 1 | PASS |
| ss | 3 | lsb_first | None | None | 1 | - | - | -->- | - | - | - | - | FAIL (1 failed) |
| ss | 3 | msb_first | carry_3F_40 | down | 4 | 39.620 | 41.385 | 39.627->39.763 | 4.09 | False | False | 2 | PASS |
| ss | 3 | msb_first | carry_3F_40 | up | 4 | 37.341 | 39.772 | 39.762->39.627 | 5.74 | False | False | 2 | FLAG |
| ss | 3 | msb_first | carry_7F_80 | down | 4 | 30.302 | 34.396 | 32.092->30.302 | 7.18 | False | False | 2 | FLAG |
| ss | 3 | msb_first | carry_7F_80 | up | 4 | 23.595 | 32.091 | 30.302->32.092 | 22.13 | False | False | 2 | FLAG |
| ss | 3 | msb_first | carry_BF_C0 | down | 4 | 22.492 | 24.895 | 23.074->22.489 | 7.89 | False | False | 2 | FLAG |
| ss | 3 | msb_first | carry_BF_C0 | up | 4 | 18.509 | 23.073 | 22.489->23.074 | 17.70 | False | False | 2 | FLAG |
| ss | 3 | msb_first | noncarry_A2_A3 | down | 4 | 26.512 | 26.918 | 26.779->26.915 | 1.00 | False | False | 1 | PASS |
| ss | 3 | msb_first | noncarry_A2_A3 | up | 4 | 26.779 | 27.181 | 26.916->26.779 | 0.99 | False | False | 2 | PASS |
| ss | 3 | none | carry_3F_40 | down | 4 | 39.619 | 40.843 | 39.629->39.765 | 2.72 | False | False | 1 | PASS |
| ss | 3 | none | carry_3F_40 | up | 4 | 37.950 | 39.772 | 39.764->39.629 | 4.23 | False | False | 2 | PASS |
| ss | 3 | none | carry_7F_80 | down | 4 | 30.284 | 33.129 | 32.093->30.303 | 3.23 | False | False | 1 | PASS |
| ss | 3 | none | carry_7F_80 | up | 4 | 27.469 | 32.096 | 30.303->32.093 | 9.36 | False | False | 1 | FLAG |
| ss | 3 | none | carry_BF_C0 | down | 4 | 22.491 | 24.196 | 23.073->22.489 | 4.86 | False | False | 2 | PASS |
| ss | 3 | none | carry_BF_C0 | up | 4 | 20.968 | 23.076 | 22.489->23.073 | 6.76 | False | False | 2 | FLAG |
| ss | 3 | none | noncarry_A2_A3 | down | 4 | 26.554 | 26.921 | 26.778->26.914 | 0.84 | False | False | 1 | PASS |
| ss | 3 | none | noncarry_A2_A3 | up | 4 | 26.779 | 27.182 | 26.915->26.778 | 0.99 | False | False | 2 | PASS |
| tt | 3 | lsb_first | None | None | 1 | - | - | -->- | - | - | - | - | FAIL (1 failed) |
| tt | 3 | msb_first | carry_3F_40 | down | 4 | 30.715 | 32.243 | 30.728->30.865 | 4.48 | False | False | 2 | PASS |
| tt | 3 | msb_first | carry_3F_40 | up | 4 | 28.663 | 30.886 | 30.868->30.728 | 6.68 | False | False | 2 | FLAG |
| tt | 3 | msb_first | carry_7F_80 | down | 4 | 23.810 | 26.856 | 25.085->23.588 | 7.04 | False | False | 2 | FLAG |
| tt | 3 | msb_first | carry_7F_80 | up | 4 | 17.570 | 24.661 | 23.590->25.085 | 25.51 | False | False | 2 | FLAG |
| tt | 3 | msb_first | carry_BF_C0 | down | 4 | 17.625 | 19.945 | 18.124->17.617 | 10.06 | False | False | 2 | FLAG |
| tt | 3 | msb_first | carry_BF_C0 | up | 4 | 14.221 | 18.198 | 17.617->18.124 | 19.27 | False | False | 2 | FLAG |
| tt | 3 | msb_first | noncarry_A2_A3 | down | 4 | 20.729 | 21.031 | 20.924->21.027 | 0.93 | False | False | 1 | PASS |
| tt | 3 | msb_first | noncarry_A2_A3 | up | 4 | 20.982 | 21.048 | 21.026->20.924 | 0.11 | False | False | 2 | PASS |
| tt | 3 | none | carry_3F_40 | down | 4 | 30.716 | 31.845 | 30.726->30.863 | 3.20 | False | False | 8 | FLAG |
| tt | 3 | none | carry_3F_40 | up | 4 | 29.485 | 30.885 | 30.860->30.726 | 4.01 | False | False | 1 | PASS |
| tt | 3 | none | carry_7F_80 | down | 4 | 23.580 | 26.183 | 25.084->23.587 | 4.40 | False | False | 1 | PASS |
| tt | 3 | none | carry_7F_80 | up | 4 | 21.054 | 25.091 | 23.587->25.084 | 10.75 | False | False | 1 | FLAG |
| tt | 3 | none | carry_BF_C0 | down | 4 | 17.625 | 19.154 | 18.127->17.622 | 5.70 | False | False | 23 | FLAG |
| tt | 3 | none | carry_BF_C0 | up | 4 | 16.142 | 18.129 | 17.620->18.127 | 8.38 | False | False | 21 | FLAG |
| tt | 3 | none | noncarry_A2_A3 | down | 4 | 20.850 | 21.029 | 20.921->21.028 | 0.33 | False | False | 2 | PASS |
| tt | 3 | none | noncarry_A2_A3 | up | 4 | 20.913 | 21.289 | 21.026->20.921 | 1.26 | False | False | 1 | PASS |
| ff | 3.3 | lsb_first | None | None | 1 | - | - | -->- | - | - | - | - | FAIL (1 failed) |
| ff | 3.3 | msb_first | carry_3F_40 | down | 4 | 22.705 | 24.186 | 22.749->22.856 | 5.87 | False | False | - | VIOLATION |
| ff | 3.3 | msb_first | carry_3F_40 | up | 4 | 20.898 | 22.878 | 22.858->22.749 | 8.12 | False | False | 14 | FLAG |
| ff | 3.3 | msb_first | carry_7F_80 | down | 4 | 17.530 | 20.447 | 18.758->17.538 | 8.99 | False | False | 22 | FLAG |
| ff | 3.3 | msb_first | carry_7F_80 | up | 4 | 10.729 | 18.735 | 17.541->18.758 | 38.84 | False | False | 19 | FLAG |
| ff | 3.3 | msb_first | carry_BF_C0 | down | 4 | 13.210 | 14.979 | 13.645->13.209 | 9.80 | False | False | 2 | FLAG |
| ff | 3.3 | msb_first | carry_BF_C0 | up | 4 | 9.497 | 13.616 | 13.209->13.645 | 28.09 | False | False | 2 | FLAG |
| ff | 3.3 | msb_first | noncarry_A2_A3 | down | 4 | 15.393 | 15.731 | 15.644->15.728 | 1.61 | False | False | 1 | PASS |
| ff | 3.3 | msb_first | noncarry_A2_A3 | up | 4 | 15.644 | 15.967 | 15.726->15.644 | 1.53 | False | False | 2 | PASS |
| ff | 3.3 | none | carry_3F_40 | down | 4 | 22.751 | 23.758 | 22.743->22.854 | 3.98 | False | False | - | VIOLATION |
| ff | 3.3 | none | carry_3F_40 | up | 4 | 21.396 | 22.861 | 22.858->22.743 | 5.94 | False | False | 19 | FLAG |
| ff | 3.3 | none | carry_7F_80 | down | 4 | 17.526 | 19.792 | 18.759->17.539 | 5.54 | False | False | 27 | FLAG |
| ff | 3.3 | none | carry_7F_80 | up | 4 | 15.439 | 18.760 | 17.539->18.759 | 11.96 | False | False | 29 | FLAG |
| ff | 3.3 | none | carry_BF_C0 | down | 4 | 13.203 | 14.539 | 13.646->13.209 | 6.56 | False | False | 2 | FLAG |
| ff | 3.3 | none | carry_BF_C0 | up | 4 | 11.778 | 13.645 | 13.207->13.646 | 10.83 | False | False | 2 | FLAG |
| ff | 3.3 | none | noncarry_A2_A3 | down | 4 | 15.482 | 15.730 | 15.645->15.729 | 1.06 | False | False | 2 | PASS |
| ff | 3.3 | none | noncarry_A2_A3 | up | 4 | 15.636 | 15.962 | 15.727->15.645 | 1.50 | False | False | 28 | FLAG |
| ss | 3.3 | lsb_first | None | None | 1 | - | - | -->- | - | - | - | - | FAIL (1 failed) |
| ss | 3.3 | msb_first | carry_3F_40 | down | 4 | 39.319 | 41.146 | 39.344->39.506 | 4.16 | False | False | 2 | PASS |
| ss | 3.3 | msb_first | carry_3F_40 | up | 4 | 37.182 | 39.517 | 39.499->39.344 | 5.48 | False | False | 2 | FLAG |
| ss | 3.3 | msb_first | carry_7F_80 | down | 4 | 30.013 | 34.347 | 31.837->30.001 | 7.88 | False | False | 2 | FLAG |
| ss | 3.3 | msb_first | carry_7F_80 | up | 4 | 22.243 | 31.850 | 30.000->31.837 | 25.84 | False | False | 2 | FLAG |
| ss | 3.3 | msb_first | carry_BF_C0 | down | 4 | 22.122 | 24.675 | 22.747->22.118 | 8.47 | False | False | 2 | FLAG |
| ss | 3.3 | msb_first | carry_BF_C0 | up | 4 | 17.808 | 22.746 | 22.117->22.747 | 19.49 | False | False | 2 | FLAG |
| ss | 3.3 | msb_first | noncarry_A2_A3 | down | 4 | 26.133 | 26.580 | 26.437->26.580 | 1.15 | False | False | 1 | PASS |
| ss | 3.3 | msb_first | noncarry_A2_A3 | up | 4 | 26.437 | 26.676 | 26.577->26.437 | 0.35 | False | False | 1 | PASS |
| ss | 3.3 | none | carry_3F_40 | down | 4 | 39.316 | 40.524 | 39.348->39.504 | 2.58 | False | False | 2 | PASS |
| ss | 3.3 | none | carry_3F_40 | up | 4 | 37.672 | 39.513 | 39.505->39.348 | 4.24 | False | False | 1 | PASS |
| ss | 3.3 | none | carry_7F_80 | down | 4 | 30.002 | 33.164 | 31.840->30.004 | 4.16 | False | False | 2 | PASS |
| ss | 3.3 | none | carry_7F_80 | up | 4 | 27.006 | 31.848 | 30.005->31.840 | 9.98 | False | False | 2 | FLAG |
| ss | 3.3 | none | carry_BF_C0 | down | 4 | 22.115 | 23.923 | 22.743->22.115 | 5.16 | False | False | 2 | FLAG |
| ss | 3.3 | none | carry_BF_C0 | up | 4 | 20.506 | 22.756 | 22.116->22.743 | 7.27 | False | False | 2 | FLAG |
| ss | 3.3 | none | noncarry_A2_A3 | down | 4 | 26.253 | 26.583 | 26.439->26.581 | 0.71 | False | False | 1 | PASS |
| ss | 3.3 | none | noncarry_A2_A3 | up | 4 | 26.478 | 26.607 | 26.579->26.439 | 0.14 | False | False | 2 | PASS |
| tt | 3.3 | lsb_first | None | None | 1 | - | - | -->- | - | - | - | - | FAIL (1 failed) |
| tt | 3.3 | msb_first | carry_3F_40 | down | 4 | 30.531 | 32.186 | 30.549->30.688 | 4.87 | False | False | 3 | PASS |
| tt | 3.3 | msb_first | carry_3F_40 | up | 4 | 28.460 | 30.704 | 30.691->30.549 | 6.80 | False | False | 2 | FLAG |
| tt | 3.3 | msb_first | carry_7F_80 | down | 4 | 23.401 | 27.250 | 24.925->23.389 | 9.32 | False | False | 14 | FLAG |
| tt | 3.3 | msb_first | carry_7F_80 | up | 4 | 15.035 | 24.923 | 23.390->24.925 | 35.70 | False | False | 2 | FLAG |
| tt | 3.3 | msb_first | carry_BF_C0 | down | 4 | 17.401 | 19.794 | 17.923->17.389 | 10.43 | False | False | 24 | FLAG |
| tt | 3.3 | msb_first | carry_BF_C0 | up | 4 | 12.913 | 17.927 | 17.387->17.923 | 25.73 | False | False | 2 | FLAG |
| tt | 3.3 | msb_first | noncarry_A2_A3 | down | 4 | 20.427 | 20.833 | 20.714->20.825 | 1.41 | False | False | 2 | PASS |
| tt | 3.3 | msb_first | noncarry_A2_A3 | up | 4 | 20.708 | 21.083 | 20.827->20.714 | 1.22 | False | False | 2 | PASS |
| tt | 3.3 | none | carry_3F_40 | down | 4 | 30.530 | 31.756 | 30.548->30.691 | 3.47 | False | False | - | VIOLATION |
| tt | 3.3 | none | carry_3F_40 | up | 4 | 29.026 | 30.717 | 30.696->30.548 | 4.97 | False | False | 6 | FLAG |
| tt | 3.3 | none | carry_7F_80 | down | 4 | 23.395 | 26.030 | 24.923->23.390 | 4.43 | False | False | 2 | PASS |
| tt | 3.3 | none | carry_7F_80 | up | 4 | 20.750 | 24.922 | 23.391->24.923 | 11.28 | False | False | 2 | FLAG |
| tt | 3.3 | none | carry_BF_C0 | down | 4 | 17.397 | 19.004 | 17.923->17.387 | 6.05 | False | False | 2 | FLAG |
| tt | 3.3 | none | carry_BF_C0 | up | 4 | 15.828 | 17.921 | 17.386->17.923 | 8.95 | False | False | 2 | FLAG |
| tt | 3.3 | none | noncarry_A2_A3 | down | 4 | 20.422 | 20.823 | 20.715->20.825 | 1.41 | False | False | 2 | PASS |
| tt | 3.3 | none | noncarry_A2_A3 | up | 4 | 20.708 | 21.069 | 20.826->20.715 | 1.18 | False | False | 2 | PASS |
| ff | 3.6 | lsb_first | None | None | 1 | - | - | -->- | - | - | - | - | FAIL (1 failed) |
| ff | 3.6 | msb_first | carry_3F_40 | down | 4 | 22.664 | 24.155 | 22.657->22.774 | 6.14 | False | False | - | VIOLATION |
| ff | 3.6 | msb_first | carry_3F_40 | up | 4 | 20.981 | 22.781 | 22.776->22.657 | 7.38 | False | False | - | VIOLATION |
| ff | 3.6 | msb_first | carry_7F_80 | down | 4 | 17.438 | 20.606 | 18.687->17.435 | 10.27 | False | False | - | VIOLATION |
| ff | 3.6 | msb_first | carry_7F_80 | up | 4 | 11.094 | 18.236 | 17.436->18.687 | 36.40 | False | False | 27 | FLAG |
| ff | 3.6 | msb_first | carry_BF_C0 | down | 4 | 13.097 | 15.135 | 13.565->13.096 | 11.58 | False | False | 12 | FLAG |
| ff | 3.6 | msb_first | carry_BF_C0 | up | 4 | 9.755 | 13.451 | 13.097->13.565 | 25.50 | False | False | 32 | FLAG |
| ff | 3.6 | msb_first | noncarry_A2_A3 | down | 4 | 15.305 | 15.640 | 15.551->15.642 | 1.58 | False | False | - | VIOLATION |
| ff | 3.6 | msb_first | noncarry_A2_A3 | up | 4 | 15.549 | 15.888 | 15.641->15.551 | 1.57 | False | False | 35 | FLAG |
| ff | 3.6 | none | carry_3F_40 | down | 4 | 22.646 | 23.675 | 22.661->22.769 | 4.00 | False | False | - | VIOLATION |
| ff | 3.6 | none | carry_3F_40 | up | 4 | 21.245 | 22.789 | 22.768->22.661 | 6.24 | False | False | - | VIOLATION |
| ff | 3.6 | none | carry_7F_80 | down | 4 | 17.432 | 18.698 | 18.688->17.434 | 0.04 | False | False | - | VIOLATION |
| ff | 3.6 | none | carry_7F_80 | up | 4 | 14.982 | 18.681 | 17.434->18.688 | 14.09 | False | False | - | VIOLATION |
| ff | 3.6 | none | carry_BF_C0 | down | 4 | 13.095 | 14.521 | 13.563->13.097 | 7.02 | False | False | 22 | FLAG |
| ff | 3.6 | none | carry_BF_C0 | up | 4 | 11.804 | 13.566 | 13.097->13.563 | 9.87 | False | False | - | VIOLATION |
| ff | 3.6 | none | noncarry_A2_A3 | down | 4 | 15.397 | 15.641 | 15.550->15.641 | 0.97 | False | False | - | VIOLATION |
| ff | 3.6 | none | noncarry_A2_A3 | up | 4 | 15.540 | 15.802 | 15.639->15.550 | 1.01 | False | False | 31 | FLAG |
| ss | 3.6 | lsb_first | None | None | 1 | - | - | -->- | - | - | - | - | FAIL (1 failed) |
| ss | 3.6 | msb_first | carry_3F_40 | down | 4 | 39.106 | 40.618 | 39.123->39.264 | 3.48 | False | False | 4 | FLAG |
| ss | 3.6 | msb_first | carry_3F_40 | up | 4 | 37.004 | 39.300 | 39.267->39.123 | 5.40 | False | False | 2 | FLAG |
| ss | 3.6 | msb_first | carry_7F_80 | down | 4 | 29.751 | 31.968 | 31.625->29.760 | 1.11 | False | False | 1 | PASS |
| ss | 3.6 | msb_first | carry_7F_80 | up | 4 | 22.551 | 31.214 | 29.761->31.625 | 24.23 | False | False | 2 | FLAG |
| ss | 3.6 | msb_first | carry_BF_C0 | down | 4 | 21.836 | 24.475 | 22.490->21.830 | 8.82 | False | False | 2 | FLAG |
| ss | 3.6 | msb_first | carry_BF_C0 | up | 4 | 17.425 | 22.479 | 21.831->22.490 | 20.19 | False | False | 2 | FLAG |
| ss | 3.6 | msb_first | noncarry_A2_A3 | down | 4 | 25.956 | 26.318 | 26.171->26.316 | 0.82 | False | False | 2 | PASS |
| ss | 3.6 | msb_first | noncarry_A2_A3 | up | 4 | 26.175 | 26.612 | 26.315->26.171 | 1.13 | False | False | 1 | PASS |
| ss | 3.6 | none | carry_3F_40 | down | 4 | 39.097 | 40.317 | 39.120->39.272 | 2.67 | False | False | 9 | FLAG |
| ss | 3.6 | none | carry_3F_40 | up | 4 | 37.842 | 39.305 | 39.272->39.120 | 3.24 | False | False | 2 | PASS |
| ss | 3.6 | none | carry_7F_80 | down | 4 | 29.773 | 33.017 | 31.629->29.759 | 4.39 | False | False | 2 | PASS |
| ss | 3.6 | none | carry_7F_80 | up | 4 | 26.691 | 31.631 | 29.759->31.629 | 10.31 | False | False | 1 | FLAG |
| ss | 3.6 | none | carry_BF_C0 | down | 4 | 21.833 | 23.544 | 22.489->21.835 | 4.70 | False | False | 2 | PASS |
| ss | 3.6 | none | carry_BF_C0 | up | 4 | 19.959 | 22.500 | 21.834->22.489 | 8.59 | False | False | 1 | FLAG |
| ss | 3.6 | none | noncarry_A2_A3 | down | 4 | 25.872 | 26.326 | 26.171->26.316 | 1.14 | False | False | 1 | PASS |
| ss | 3.6 | none | noncarry_A2_A3 | up | 4 | 26.168 | 26.526 | 26.314->26.171 | 0.80 | False | False | 2 | PASS |
| tt | 3.6 | lsb_first | None | None | 1 | - | - | -->- | - | - | - | - | FAIL (1 failed) |
| tt | 3.6 | msb_first | carry_3F_40 | down | 4 | 30.374 | 32.065 | 30.394->30.529 | 5.05 | False | False | 11 | FLAG |
| tt | 3.6 | msb_first | carry_3F_40 | up | 4 | 28.242 | 30.536 | 30.529->30.394 | 7.05 | False | False | 2 | FLAG |
| tt | 3.6 | msb_first | carry_7F_80 | down | 4 | 23.225 | 26.338 | 24.780->23.218 | 6.28 | False | False | 2 | FLAG |
| tt | 3.6 | msb_first | carry_7F_80 | up | 4 | 15.547 | 24.735 | 23.218->24.780 | 33.04 | False | False | 2 | FLAG |
| tt | 3.6 | msb_first | carry_BF_C0 | down | 4 | 17.203 | 19.568 | 17.759->17.198 | 10.19 | False | False | 2 | FLAG |
| tt | 3.6 | msb_first | carry_BF_C0 | up | 4 | 12.883 | 17.754 | 17.196->17.759 | 25.09 | False | False | 2 | FLAG |
| tt | 3.6 | msb_first | noncarry_A2_A3 | down | 4 | 20.263 | 20.661 | 20.540->20.653 | 1.36 | False | False | 2 | PASS |
| tt | 3.6 | msb_first | noncarry_A2_A3 | up | 4 | 20.544 | 20.911 | 20.650->20.540 | 1.26 | False | False | 2 | PASS |
| tt | 3.6 | none | carry_3F_40 | down | 4 | 30.373 | 31.617 | 30.391->30.530 | 3.58 | False | False | 2 | PASS |
| tt | 3.6 | none | carry_3F_40 | up | 4 | 28.801 | 30.544 | 30.531->30.391 | 5.22 | False | False | 2 | FLAG |
| tt | 3.6 | none | carry_7F_80 | down | 4 | 23.209 | 25.946 | 24.784->23.214 | 4.69 | False | False | 16 | FLAG |
| tt | 3.6 | none | carry_7F_80 | up | 4 | 20.547 | 24.792 | 23.213->24.784 | 11.50 | False | False | 2 | FLAG |
| tt | 3.6 | none | carry_BF_C0 | down | 4 | 17.197 | 18.855 | 17.760->17.195 | 6.19 | False | False | 2 | FLAG |
| tt | 3.6 | none | carry_BF_C0 | up | 4 | 15.902 | 17.764 | 17.195->17.760 | 7.49 | False | False | 2 | FLAG |
| tt | 3.6 | none | noncarry_A2_A3 | down | 4 | 20.252 | 20.661 | 20.540->20.656 | 1.40 | False | False | 1 | PASS |
| tt | 3.6 | none | noncarry_A2_A3 | up | 4 | 20.545 | 20.923 | 20.653->20.540 | 1.28 | False | False | 16 | FLAG |

## Failed rows

- v30_lsb_first tt None None: FAIL: klt corner status 'error'
- v30_lsb_first ss None None: FAIL: klt corner status 'error'
- v30_lsb_first ff None None: FAIL: klt corner status 'error'
- v33_lsb_first tt None None: FAIL: klt corner status 'error'
- v33_lsb_first ss None None: FAIL: klt corner status 'error'
- v33_lsb_first ff None None: FAIL: klt corner status 'error'
- v36_lsb_first tt None None: FAIL: klt corner status 'error'
- v36_lsb_first ss None None: FAIL: klt corner status 'error'
- v36_lsb_first ff None None: FAIL: klt corner status 'error'
