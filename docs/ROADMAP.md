# gf180-rcosc roadmap

A free-running, digitally trimmable 48 MHz RC relaxation oscillator on gf180mcu,
built to a ratified spec with an append-only evidence trail.

Status as of 2026-11-13, `main` @ `256beb5f`.

[`WORK_PLAN.md`](../WORK_PLAN.md) is the generated label view of the tracker and
[`signoff/signoff-report.json`](../signoff/signoff-report.json) the graded
verdict of record. Row numbers follow [`sim/item5/ROWS.md`](../sim/item5/ROWS.md).

## Where it stands

Graded T1 verdict: **8 of 11 items met, tier not awarded**
([`signoff/README.md`](../signoff/README.md), tracker [#5](https://github.com/2AMLogic/gf180-rcosc/issues/5)).

| Item | State | Evidence or reason |
|---|---|---|
| 1 Design sources, 2 Layout, 3 DRC, 4 LVS | met | `signoff/*-envelope.json`, `layout/reports/rcosc_top.{drc,lvs}.json` |
| 8 Characterization, 9 Testbenches, 10 Hygiene, 11 Power delivery | met | `signoff/` envelopes, `layout/reports/rcosc_top.erc.json` |
| 5 Corner verification | unmet, `check_failed` | cites `sim/item5/results/20261106T051832Z/`, a campaign older than the current netlist |
| 6 Monte Carlo | unmet, `negative_control_not_detected` | cites `sim/mc/results/20261106T072000Z/`; DR-0019 and DR-0022 are still `proposed` |
| 7 Post-layout | unmet, `no_evidence` | no `klt pex` report is cited ([#70](https://github.com/2AMLogic/gf180-rcosc/issues/70)) |

Design state, by ratified row:

- **Row 1 (48.000 MHz)** passes at calibration code `0xA4` (DR-0029,
  `sim/item5/results/20261106T071555Z/`).
- **Rows 7, 9, 10** pass on the DR-0028 netlist: the comparator-H output-stage
  fix cleared the fs / -40 C no-start, and the startup bench reads 63/63
  (`sim/startup-settled/results/20261106T0735Z/`). Startup has not been re-run
  since comparator-H changed again (see Now).
- **Row 5 (accuracy over temperature)**: the `ff` 85 C / 3.0 V miss is fixed.
  Comparator-H mirror-load L 0.7 um is in the schematic, netlist and a rebuilt
  DRC-clean, LVS-matched layout, and reads +1.66 pt on the extraction against a
  +8.8 % limit (DR-0038 to DR-0044, PRs #328 to #336). Its Monte Carlo yield on
  this netlist is not yet measured.
- **Row 4 (accuracy at the calibration point)**: one open design failure. The
  `ss` supply span is 6.09 pt against a 4.9 pt window (DR-0043). The `w3r65`
  bank candidate reads 4.68 pt on the extraction but raises running Iq at code
  `0xFF` by 18 to 28 % (DR-0045, PR #339). Not adopted.
- **Row 2 (trim)**: the range ends pass; the nominal LSB step is 0.539 %/code
  against 0.314 %/code (`sim/item5/results/20261106T071555Z/summary.md`).
- **Row 8 (running Iq < 500 uA)**: fails at `ff` corners, 559.4 uA at
  ff / 85 C / 3.6 V on the calibration code (same summary). No issue owns it.

The README status block is stale: issue #66 (re-centre) closed on 2026-11-06
and items 5 and 6 now have campaigns behind them.

## Now

1. **Finish the dense 256-code trim sweep** ([#87](https://github.com/2AMLogic/gf180-rcosc/issues/87), in progress).
   Done when `sim/trim-dense/results/20261106T1115Z-campaign/` holds all 1536
   jobs, `analyze.py` output is committed, and a decision record states each of
   the four DR-0021 carries confirmed or refuted. PR #312 (948 of 1536) is
   approved and unmerged.
2. **Re-run the startup bench on the current netlist** ([#346](https://github.com/2AMLogic/gf180-rcosc/issues/346), filed, `loom:triage`).
   Comparator-H caused the earlier no-start and has changed since the last
   startup run. Done when a new `sim/startup-settled/results/<stamp>/` reports
   all 63 points on the L 0.7 um netlist at code `0xA4` (the last run held `0xA9`).
3. **Attribute running Iq at the `ff` corners by stage** ([#347](https://github.com/2AMLogic/gf180-rcosc/issues/347), filed, `loom:triage`).
   Done when a new `sim/` results directory and a decision record give the
   per-stage supply current at the cells over 500 uA and name the candidate
   lever, with no design file changed.
4. **Make `layout/run_checks.sh` runnable end to end under its pins** ([#348](https://github.com/2AMLogic/gf180-rcosc/issues/348), filed, `loom:triage`). DR-0042 records that the geometry pin (klt 0.4.0) lacks the
   `klt netlist` command the script's first step calls. Done when one
   documented invocation completes and the preflight test covers it.
5. **Refresh the README status block and maturity-ladder paragraph** ([#349](https://github.com/2AMLogic/gf180-rcosc/issues/349), filed, `loom:triage`). Done when both match `signoff/README.md` and this file, and no
   closed issue is named as owning open work.

## Next

- **Adopt the row-4 bank change, or record that no knob meets the window** ([#337](https://github.com/2AMLogic/gf180-rcosc/issues/337)).
  Done when the schematic, netlist and layout carry the change with DRC clean,
  LVS match and a re-extraction, or a decision record closes row 4 as a known
  miss. Needs the ruling on #337.
- **500-die Monte Carlo on the final netlist, rows 4 and 5** ([#317](https://github.com/2AMLogic/gf180-rcosc/issues/317)). Done when
  `sim/mc/results/<stamp>/` holds the campaign with zero and inflated controls
  and a decision record gives per-row, per-corner yield. Needs #337.
- **Item 6 re-grade** ([#202](https://github.com/2AMLogic/gf180-rcosc/issues/202)).
  Done when `signoff/signoff-report.json` cites that campaign for rows 2, 4
  and 5. Needs #317; reads `met` only once DR-0019 is ratified.
- **Item 5 re-run and re-cite on the final netlist.** Done when
  `sim/item5/requests/` is regenerated on the adopted netlist, the 15 envelopes
  are committed, and the manifest cites them. Needs #337. No issue yet.
- **Row 2 step-size decision.** Done when a decision record, using the #87
  verdict, either sizes a bank change or records the measured step as the
  design's resolution. Needs #87.
- **Row 8 design change.** Done when the lever from Now item 3 is in the
  schematic and the item-5 Iq limit passes at every corner. Needs Now item 3
  and the #337 outcome, since `w3r65` moves Iq.
- **Item 7 `klt pex` report** ([#70](https://github.com/2AMLogic/gf180-rcosc/issues/70)).
  Done when a `klt pex` report for the current `rcosc_top` GDS is cited for
  item 7 and its `body_bias` block is restated in `signoff/README.md`. The
  committed requests under `sim/pvt-postlayout/klt-pex/` hold code `0xA3` and
  predate the rebuilt layout, so they need regenerating first.

## Later

- **Layout geometry pin 0.4.0 to 0.8.0** ([#204](https://github.com/2AMLogic/gf180-rcosc/issues/204)). A rebuild under
  0.8.0 gave 203 DRC violations in `rcosc_bias` and a changed database unit.
  Question first: adapt `layout/gen_lib.py` to the newer generators, or keep
  the old pin and say why, in a decision record.
- **Runtime discipline loop (row 6)**, reserved and not designed. Question
  first: is the loop part of this block or of its user (DR-0004, DR-0021)?
- **Shuttle seat and measured silicon**, the last rungs of the README maturity
  ladder. Question first: do rows 2, 4, 5 and 8 pass, or are any carried as
  stated misses? [`docs/chipalooza/challenge-5-proposal.md`](chipalooza/challenge-5-proposal.md)
  predates the November fixes and would need the same refresh.

## Blocked and waiting

- **#337 waits on an operator ruling**: is `w3r65` one re-centred change, and
  is the `0xFF` Iq cost accepted. #317 and #202 are parked behind it.
- **#70 is held for an operator step whose premise has changed.** The hold says
  the batch runner lacks the `gf180mcuC` variant; the item-5 and Monte Carlo
  campaigns of 2026-11-06 ran on it with that variant
  (`sim/item5/results/20261106T051832Z/summary.md`).
- **DR-0019 and DR-0022 are `proposed`.** Until they are ratified, item 6 can
  grade `unratified_rows` at best.
- **[#310](https://github.com/2AMLogic/gf180-rcosc/issues/310)** (remove the guard-confinement investigation files) was ruled
  on 2026-11-11 and still carries a blocked label.

Apart from #87, in progress, nothing in the tracker is dispatchable today; Now
items 2 to 5 are filed as `loom:triage` (#346 to #349) and become dispatchable once
curated and promoted.

## Not planned

- Active temperature compensation (DR-0004), and an enable pin (DR-0024).
- Per-corner trim, or relaxing a ratified window to make a row pass (DR-0032).
- Clock pulse width as a graded row: it is informational (DR-0025).
