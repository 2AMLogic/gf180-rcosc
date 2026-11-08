# Slice 6 (#87, `Part of #87`)

Ran `run_batch.py` in three invocations (`--limit 14`, then `--limit 16` twice) on the batch fleet
(`uvx --from klayout-tools==0.9.0 klt`) against the bench regenerated with the manifest's netlists and
`--capacity-wait-s 1200`; its `provenance.json` hashed to `manifest.json:provenance_sha256` (`d1d24253...`).

Result: ledger now holds 163 of 1536 jobs (`ext_ff_85C_3p6V_c00..cA2`), all `done`, 163 distinct tags, 163 reports,
all submitted with `--backend batch`; this slice: 46 done, 0 not done. Supersedes the counts in `README.md` and
earlier `SLICE-*.md` (append-only, left unedited).

Disclosure: the last two 16-job invocations were issued in the same tool turn and overlapped, so up to 4 jobs were in
flight at once on this host instead of the 2-job cap (each invocation kept its own cap of 2). The ledger shows no
duplicate or conflicting entries. Later slices run one invocation at a time.

No step, monotonicity or carry claim follows; 1373 jobs remain, then `analyze.py --manifest` and the verdict DR (0030).
