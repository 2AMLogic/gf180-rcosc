# Waveform analysis analysis

**Analysis of simulator output; evidence status is set by the originating campaign record**

Spread columns are deterministic (noiseless transient); they are not stochastic
RMS jitter and not the external SOF-arrival jitter assumption.

Note: issue #213 convergence: tmax/tstep 50p, reltol 1e-4, abstol 1e-13, vntol 1e-7

1 corner row(s), 0 failing.

| process | T (C) | VDD (V) | status | cycles | period (ns) | p2p (ps) | std det (ps) | max abs c2c (ps) | high (ns) | low (ns) | duty | rise (ps) | fall (ps) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tt | 27 | 3.3 | OK | 95 | 20.7 | 7.115e-07 | 1.601e-07 | 5.963e-07 | 1.936 | 18.77 | 0.09353 | 830.6 | 326.2 |
