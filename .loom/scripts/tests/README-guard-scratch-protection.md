# Guard scratch-protection regression suite

Offline regression coverage for the two scratch-work safety decisions of the
installed destructive-command guard (issue #150). This suite is repo-owned
(pinned in `.loom/resync-ignore`); it exercises the guard as installed in
this repository and changes no guard behavior.

## What it covers

| Case | Expected decision | Telemetry pattern |
|---|---|---|
| `rm -rf "$UNKNOWN_RESULTS_ROOT/sim/iq/results"` (unassigned variable at the path root) | `deny`, reason names the unexpanded-variable cause | `rm-scope-unresolved-var` |
| `git stash -q` from a linked managed `issue-N` worktree (two `.loom-managed` worktrees active, real `worktree.sh` at the main checkout) | `deny`, reason names the shared `refs/stash` stack and the per-issue `worktree.sh snapshot <N>` replacement | `stash-scope:create-redirect` |
| `git stash -q` with cwd = main checkout (control) | allow (create-side deny is worktree-only by design) | none |
| `git status --short` with cwd = managed worktree (control) | allow | none |

For every invocation the suite also asserts: exit status 0 (the hook must
never exit non-zero), stdout is valid PreToolUse JSON with
`hookEventName == "PreToolUse"` on denials, the expected
`guard-decisions.log` JSONL record (decision/tier/pattern), and — via a
before/after digest plus a canary file — that fixture files, worktree state,
sentinels, and `refs/stash` are unchanged and the JSON command was never
executed.

## Run

```bash
bash .loom/scripts/tests/test-guard-scratch-protection.sh
```

Works from any directory (all paths resolve from the suite's own location).
Exit status: `0` all assertions pass, `1` any assertion failed or a
prerequisite was missing.

## Prerequisites

- `bash`, `git`, `jq`, `awk`, and coreutils `mktemp`, `find`, `sort`,
  `sha256sum` on `PATH`.
- The installed Loom surfaces of THIS checkout: `.loom/hooks/guard-destructive.sh`,
  `.loom/hooks/guard-destructive-generic.sh`, `.loom/scripts/worktree.sh`,
  `.loom/scripts/lib/config-resolver.sh`.
- No network, no PDK, no Python, no circuit simulation, no loom-daemon.

Missing tools or subject files abort the suite with a clear `ERROR:` message
and exit status 1.

## Fixture requirements and isolation

- Everything runs inside ONE disposable `mktemp -d` root whose paths
  deliberately contain spaces (`loom scratch guard.XXXXXX`), removed by an
  `EXIT`/`INT`/`TERM` trap on both success and failure. Nothing touches the
  live repository, its worktrees, or its `refs/stash`.
- The fixture is a throwaway git repo staging copies of the real installed
  `guard-destructive.sh` dispatcher (which execs the vendored
  `guard-destructive-generic.sh` — the implementation under test),
  `.loom/scripts/lib/`, and `worktree.sh`, plus two linked
  `.loom/worktrees/issue-<N>` worktrees carrying `.loom-managed` sentinels
  and a tracked-but-uncommitted WIP file (so an actually-executed stash would
  be observable).
- The hook is invoked under `env -i`, so ambient agent-session toggles
  (`LOOM_FORCE_SCOPE`, `LOOM_GUARD_STASH_SCOPE`, …) cannot skew verdicts.
  Telemetry is captured through the hook's own documented test seams
  (`LOOM_GUARD_DECISION_LOG=1`, `LOOM_GUARD_DECISION_LOG_FILE`).
- The command strings inside the JSON are never passed to a shell by this
  suite; the hook only inspects inert text.

## Declared prerequisite deviation (worktree.sh)

The guard's create-side deny only checks that a real
`.loom/scripts/worktree.sh` exists at the main checkout — it never executes
it. Running that helper's full CREATE path, however, additionally requires
`loom-daemon` and forge (`gh`) access: without both it rolls the worktree
back after `git worktree add` (verified while building this suite; with
`LOOM_DEFAULT_BRANCH=main` preset it still fails at the claim/lease step).
Because this suite must run offline, it stages the real helper file and
builds the identical managed-worktree filesystem contract — linked worktree
plus `.loom-managed` sentinel in `write_loom_sentinel()`'s exact format —
with plain `git worktree add`. The guard under test is never mocked or
modified.
