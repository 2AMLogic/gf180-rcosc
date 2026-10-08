# Design-source inventory (T1 item 1)

The audited artifact `signoff/design-sources-envelope.json` is bound to (the
envelope pins this file's sha256; `klt signoff` re-hashes it on every grade,
and `signoff/verify-report.py` re-checks the pin in CI). Editing this file
without refreshing the envelope and the manifest pin turns item 1 `unmet`
(`stale_evidence`) and fails the verifier — that is the point.

What the binding proves, and what it does not: it proves that this list is
the exact text that was audited. It does **not** re-hash each listed source
(the grader does not open them), so the list is kept honest the other way:
`signoff/verify-report.py` checks that every path in the first column of the
tables below exists in the tree, and the regeneration check under "Audit"
is a recorded result, not a standing guarantee.

## Block sources (xschem, hand-authored)

The `rcosc_top` hierarchy is captured entirely as transistor-level xschem
schematics. Each cell is a `.sch` (the schematic) plus a `.sym` (the symbol
the parent instantiates).

| path | what it is |
|---|---|
| `design/rcosc_top.sch` | the composed oscillator block, top of the hierarchy (SR latch, discharge switch, timing capacitor, instances of the four cells below) |
| `design/rcosc_top.sym` | its symbol (instantiated by the testbenches) |
| `design/rcosc_bias.sch` | ratiometric V_H/V_L threshold + tail-current bias generator |
| `design/rcosc_bias.sym` | its symbol |
| `design/rcosc_comparator.sch` | NMOS-input differential-pair comparator + output buffer (high side, `XCMPH`) |
| `design/rcosc_comparator.sym` | its symbol |
| `design/rcosc_comparator_p.sch` | complementary PMOS-input comparator (low side, `XCMPL`; issue #57 / DR-0017) |
| `design/rcosc_comparator_p.sym` | its symbol |
| `design/rcosc_trim_bank.sch` | 8-bit binary-weighted switched-resistor trim bank (transmission-gate shunts; issue #43 / DR-0014) |
| `design/rcosc_trim_bank.sym` | its symbol |
| `design/xschemrc` | project-local xschem configuration (symbol search path, PDK resolution) the netlister reads |

## Derived netlist

| path | what it is |
|---|---|
| `design/netlist/rcosc_top.spice` | the xschem-derived SPICE netlist of the whole block (all five cells as subcircuits); **derived, never hand-edited** |

Downstream of it (not design sources, listed so the derivation chain is
visible): `layout/lvs_ref/rcosc_top.spice`, the LVS reference netlist
`layout/netlist_parse.py` generates from the derived netlist's own device
geometry when `layout/run_checks.sh` runs. The testbench schematics
(`design/pvt_tb.sch`, `design/smoke_test.sch`) and their derived netlists
are testbenches, inventoried for item 9 in
`signoff/testbench-inventory.md`, not here.

## Regeneration

| path | what it is |
|---|---|
| `design/regen-netlist.sh` | re-exports `design/netlist/*.spice` from the `.sch` sources (`xschem -n -x -q -r --rcfile design/xschemrc`, entry points `rcosc_top`, `smoke_test`, `pvt_tb`) and writes the per-machine, uncommitted `design/netlist/pdk_include.spice` |

Command (repo root; needs `xschem` and a gf180mcuC PDK install, resolved from
`PDK_ROOT` or `klt pdk find --pdk gf180mcuC`):

```bash
design/regen-netlist.sh
```

Every evidence generator in this repo runs it first, so evidence is always
regenerated against the current schematics rather than a stale export:
`layout/run_checks.sh`, `sim/pvt/run-pvt-sweep.sh`,
`sim/iq/run-iq-sweep.sh`, `sim/pvt-postlayout/run-pex-pvt-sweep.sh` and
`design/run-smoke-test.sh`.

## Audit (issue #64, against `origin/main` @ `dfb95bf`)

- Every path above is committed (`git ls-files`).
- The committed `design/netlist/rcosc_top.spice` was re-derived from the
  committed schematics with the same `xschem` invocation into a scratch
  directory (not into the tree) and compared after normalising SPICE
  line continuations, blank lines and the `** sch_path:`/`** sym_path:`
  comment lines (which record the absolute path of whichever checkout ran
  the netlister): **identical**. The scratch run used xschem 3.4.4; the
  committed export was written by xschem 3.4.7 (the version the `sim/`
  manifests record). The two versions wrap continuation lines differently,
  which is why the comparison is normalised rather than byte-for-byte.
- Known provenance wart, disclosed rather than rewritten: the committed
  netlist's `sch_path`/`sym_path` comment lines name the absolute path of
  the worktree that last regenerated it (`.../worktrees/issue-57/...`).
  These are comments, so they do not affect simulation. A fresh
  `design/regen-netlist.sh` run rewrites them to the running checkout's
  path.
- Design *conformance* (that these schematics implement the ratified spec
  and the decision records) is out of scope here. This item attests that
  the sources and their reproducible derivation are committed. Conformance
  is tracked separately (issue #66).
