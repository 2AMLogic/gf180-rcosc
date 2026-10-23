# `manifests/artifacts/` — stored-evidence manifests

One file per stored run: `<bench>-<run-id>.manifest.json`, written by the
campaign drivers (`sim/pvt`, `sim/iq`, `sim/pvt-postlayout`, `sim/recentre`)
through `sim/evidence_stage.py` and `sim/harness/evidence_store.py` (issue
#196). Each entry names one object in the fleet artifact store by its sha256,
with `size`, `kind` (`evidence`), `producer` (`tool`, `version`, `loom.repo`,
`commit`), `uri` (always `artifact:<key>`), and `name`, the path the bytes would
have had under `sim/`. The format is klayout-tools' `docs/cli/artifact.md`.

Evidence bytes are private; these manifests are public. The run's Markdown
summary is committed under `sim/<bench>/results/<run-id>/`.

**Fail closed.** If `$KLT_ARTIFACT_BROKER` is unset, `klt` lacks `artifact put`
(or predates klayout-tools `7e3561f`), or the broker is unreachable, the driver
refuses to start, or exits 10 after the run with nothing committed. There is no
fallback that commits the bytes. No storage location, account or broker URL
belongs in this repository.

Manifests are append-only evidence: never edit or delete one. CI
(`.github/workflows/artifact-manifests.yml`) runs
`python3 scripts/check_artifact_manifests.py check --tree <sha>`, which checks
the schema, accepts only `artifact:` URIs, and fails if a stored object's bytes
are also committed. To check the bytes themselves, run
`klt artifact verify <manifest>` (or
`python3 scripts/check_artifact_manifests.py verify <manifest>`) with
`KLT_ARTIFACT_BROKER` set. See `sim/README.md`, "Stored evidence".
