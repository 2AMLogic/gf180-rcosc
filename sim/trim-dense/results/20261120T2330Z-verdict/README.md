# #459 verdict analysis directory (COMPLETE: 1536 jobs, 6 curves x 256 codes, engine split disclosed)

Analyzer outputs for the frozen dense campaign `../20261106T1115Z-campaign/` (#87). This is the one
directory under `results/` where `results.json`, `steps.csv` and `summary.md` are permitted
(`test_no_measured_artifacts_in_tree`). **Append-only evidence**; the reading of these numbers is
decision record 0049 (`spec/decision-records/0049-*.md`).

Reproduce from the repository root into a fresh directory, then byte-compare with the committed copies:

```
D=sim/trim-dense/results
python3 -I sim/trim-dense/analyze.py \
  --bench-dir $D/20261106T1115Z-campaign --reports-dir $D/20261106T1115Z-campaign/reports \
  --manifest $D/20261106T1115Z-campaign/manifest.json \
  --engine-ab $D/20261115T160955Z-engine-ab/comparison.json \
  --outdir /tmp/verdict-check
cmp /tmp/verdict-check/results.json $D/20261120T2330Z-verdict/results.json   # likewise steps.csv, summary.md
```

Without `--engine-ab` the same command exits 1 (`PROVENANCE INCOMPLETE`, mixed ngspice 46/47): the engine split is
accepted only on the committed paired A/B (#378: 47 pairs, 0 over the half-LSB). The `sch` curves use the pre-P3
trim sizing; `ext` is the P3 L = 1 um extraction.
