# 0025: clk pulse-width / duty / rise-fall measurements are informational; no spec row changes

- **Status**: proposed (informational record; ratifies nothing)
- **Date**: 2026-11-06
- **Decided by**: Loom Builder (issue #213), pending review

## Context

Issue #91 delivered the offline waveform harness (`sim/waveform/`); issue #213
runs its 27-point campaign through the batch fleet. Run
`sim/waveform/results/20261106T044600Z/` measured clk pulse widths, duty,
rise/fall and period statistics at tt/ss/ff x -40/27/85 C x 3.0/3.3/3.6 V with
the code held per process (tt `0xA3`, ss `0xCD`, ff `0x59`). No ratified spec
row covers clk pulse width, duty or edge rates.

## Decision

- The measured figures are **informational**, recorded as evidence in
  `sim/waveform/results/20261106T044600Z/` (table, provenance, per-point
  status). **No ratified spec row changes** and none is proposed here.
- Reported (26 of 27 points; ff/85/3.6 V is an analyzer end-of-window failure,
  see the run README): clk is a narrow positive pulse, duty 0.073-0.117, high
  pulse 1.55-2.46 ns, mean period 19.72-21.97 ns, rise 608-1222 ps, fall
  359-518 ps.
- **Convergence limits what is quoted.** At tt/27 C/3.3 V a tighter solver
  setting moved period/pulse means by 0.4-2 %, fall time by 21 %, and
  removed the period peak-to-peak and cycle-to-cycle differences entirely
  (160 ps -> 7e-7 ps). Therefore: fall times are not converged at default
  settings, and the grid's period-spread and cycle-to-cycle columns are
  numerical artifacts, not physical jitter or a spec quantity. This is one
  corner and one refinement; no convergence order is claimed.
- **Deterministic spread is not jitter.** No stochastic noise was applied to
  the DUT. `trnoise` on an independent source runs under `klt sim`, which does
  not establish noise coverage of the gf180mcu devices; the stochastic-noise
  question remains a stated limitation and no RMS jitter figure exists.
- The +/-500 ns SOF-arrival jitter in `sim/discipline/README.md` stays an
  external-reference assumption; these measurements neither validate nor
  replace it.

## Alternatives considered

- **Quote the default-setting spread as period jitter** - rejected; the
  convergence check shows it is a solver artifact.
- **Propose a duty or edge-rate spec row** - rejected; out of scope for this
  work item, and a row needs a converged measurement and its own record.
- **Change the analyzer so ff/85/3.6 V yields numbers** - rejected here; the
  harness is out of scope for #213. The failure is recorded as is.

## Consequences

- Downstream consumers (clock-tree, I/O timing) may cite the duty and mean
  widths as unratified, unconverged evidence only.
- A follow-up could re-run the grid at the tight settings and fix the
  analyzer's end-of-window handling; neither is done here.
- Evidence: `sim/waveform/results/20261106T044600Z/README.md`,
  `manifests/artifacts/waveform-20261106T044600Z.manifest.json`.
