# Guard write-confinement investigation (issue #149)

**Status: confinement preserved. No exception granted. No guard or helper file
is modified by this PR.** This is a bounded investigation per the operator
ruling of 2026-10-15 (preserve-and-reproduce). It proposes no relaxation.

- Base: origin/main `03ee19cb`, 2026-11-06.
- Harness: `docs/guard-confinement-investigation/repro.sh` (read-only; builds
  a throwaway git repo + `.loom-managed` worktree under `mktemp -d`, feeds each
  command to the real `guard-destructive.sh` → vendored
  `guard-destructive-generic.sh` as Bash-tool JSON with `LOOM_ROLE=builder` and a
  scrubbed env; commands are passed as text and never executed).
- Re-run: `bash docs/guard-confinement-investigation/repro.sh` (output is TSV
  `case / verdict / reason / command`; the temp fixture path varies per run).
- The harness reports only `allow`/`deny` plus a coarse reason keyword derived
  from the message text; it does not read the decision-tag. `ask` verdicts
  would print as `ask` (none occurred).

## Upstream surface

- Logic: the "BASH-TOOL WRITE CONFINEMENT" section of
  `.loom/hooks/guard-destructive-generic.sh` (starts line 9951 at `03ee19cb`),
  decision tags `worktree-write-confinement` / `worktree-write-confinement-unresolved-var`.
- `.loom/hooks/guard-destructive.sh:123` carries the capability marker; the
  dispatcher prefers a Repo Skills guard only if it passes all four probes.
- Install contract: `.loom/docs/guard-hooks.md`. Files under `.loom/hooks/` are
  Loom-managed and vendored, so a local patch is overwritten on resync. Any
  change belongs in `rjwalters/loom` `defaults/hooks/`.

## Case 1 — checkpoint bookkeeping

Source: `.claude/commands/loom/sweep-wave-lifecycle.md` step 0 (lines 51-55 at
`03ee19cb`):

```bash
MAIN_CLEAN_BASELINE=".loom/sweep-checkpoint/main-clean-baseline-${RUN_ID}.txt"
./.loom/scripts/check-main-clean.sh --snapshot "$MAIN_CLEAN_BASELINE"
```

`RUN_ID` shape is from `.loom/scripts/sweep-run-registry.sh:405-407`:
`sweep-<UTC ts>-<pid part>-<8 hex>`, e.g. `sweep-20260722T231500Z-84213-a3f9c1b2`.
The `mkdir .loom/sweep-checkpoint` in the telemetry is not in that step; it is
presumably issued by the orchestrator before it. The telemetry's complete
original commands and cwd were **not recoverable** here (only the two
truncated denial summaries in the issue body), so the cwd below is the two
plausible ones, main checkout vs. issue worktree.

| Case | cwd | Verdict |
|---|---|---|
| `mkdir .loom/sweep-checkpoint` (also `-p`) | main checkout | **deny** (main-checkout confinement) |
| same | issue worktree | allow (lands inside worktree) |
| `check-main-clean.sh --snapshot <literal path>` | main | allow |
| `--snapshot "$MAIN_CLEAN_BASELINE"` (var set in same command) | main | allow |
| same with `${RUN_ID}` in the assignment | main | allow |
| all three above | worktree | allow |

So the `mkdir` denial reproduces from the main-checkout cwd. The `--snapshot`
denial in the telemetry **did not reproduce** in any shape tried; the guard
never sees `--snapshot` as a write idiom (it only scans `>`, `tee`, `sed -i`,
`cp`, `mv`, `mkdir`). The reported `--snapshot` denial may have come from a
compound command (e.g. `mkdir … && check-main-clean.sh …`) whose `mkdir`
triggered it; this is unconfirmed.

### Checkpoint controls

| Control | Verdict | Note |
|---|---|---|
| arbitrary main write `echo x > <main>/src.txt` | deny | as required |
| `echo x > .loom/sweep-checkpoint/x.txt` from main | deny | as required |
| `mkdir <main>/not-checkpoint` | deny | as required |
| process substitution writing into main | deny | |
| helper + `--snapshot` + `; echo x > <main>/evil.txt` (extra command) | deny | caught by the redirect, not by the helper |
| **`--snapshot` with `..` traversal** | **allow** | **finding** |
| **`--snapshot escape-link/evil.txt` (symlink to main)** | **allow** | **finding** |
| **`--snapshot "$UNKNOWN/x.txt"`** | **allow** | **finding** |
| **`--snapshot "$(pwd)/evil.txt"`** | **allow** | **finding** |
| **different helper `other-helper.sh --snapshot …`** | **allow** | **finding** |

**Prominent finding:** the guard does not confine writes performed *by a
helper*. Every `--snapshot` variant is allowed from the main cwd, including
traversal, symlink and unknown-variable targets, and identity of the helper is
irrelevant. The guard only confines the idioms it can lex. This confirms the
issue's premise that `check-main-clean.sh --snapshot` takes a caller-supplied
path (`:367-370`, `:603-611`) and the guard provides no containment for it. A
"trusted helper" allowlist would therefore not add safety by itself and, as the
ruling says, helper identity alone is insufficient. It is also out of scope
to change here. The only denied piece of the real sequence is the `mkdir`.

## Case 2 — temporary downloads

**The original loop and its literal filename list were not recovered.** The
issue body carries only a path fragment (`/tmp/e85/$f.rst`) and the tag
`worktree-write-confinement-unresolved-var`. Nothing under `.loom/logs`,
`.loom/state` or `docs/` in this checkout mentions `e85`. Filenames are not
invented. Everything below is **synthetic, not the original**
(finite literal list `alpha beta`, fixed `/tmp/e85` root, curl to a reserved
`.invalid` host that is never contacted).

| Synthetic case | Verdict |
|---|---|
| `for f in alpha beta; do echo x > /tmp/e85/$f.rst; done` | allow |
| `cd /tmp/e85 && for f in alpha beta; do echo x > $f.rst; done` | allow |
| `curl -o /tmp/e85/$f.rst …` in the same loop | allow |
| `curl … > /tmp/e85/$f.rst` in the same loop | allow |
| `mkdir -p /tmp/e85 && cd /tmp/e85 && for … curl … > $f.rst` | allow |

The guard already carries a bounded resolver for this shape,
`wt_write_tmp_cwd_loop_var_safe()` (#12285, doc at line ~8131): literal
`cd /tmp/<dir>`, literal `for var in <words>` and no `ln`. The reported denial
did **not** reproduce for the synthetic loops; the original most likely had a
target rooted in a variable (e.g. `$DIR/$f.rst`) or a non-literal list, which
cannot be confirmed without the original. **Download case: evidence-incomplete / deferred; no exception proposal.**

### Download controls (all with a leading `cd /tmp/e85` unless noted)

| Control | Verdict |
|---|---|
| loop writing to `<main>/$f.rst` (no cd) | deny |
| list item `../x` | deny (unresolved-var) |
| list item `sub/x` | deny |
| list item absolute path into main | deny |
| unknown variable `$UNKNOWN.rst` | deny |
| list from `$(ls)` | deny |
| list from `$LIST` | deny |
| list `*` | deny |
| `ln -s <main> link` in same command, then `for f in link` | deny |
| variable rebound by `read` | deny |
| cwd `/tmp/../home` | deny |

All stayed denied. The literal-path forms (first four synthetic rows) were
allowed, which is expected: a literal `/tmp/...` target is outside both the
main checkout and every worktree.

Residual gap already acknowledged in the guard's own comment: a symlink that
exists from an *earlier* command is not seen (lexical guard). Not tested.

## Conclusions

1. Nothing here supports a relaxation. The one reproducible denial
   (`mkdir .loom/sweep-checkpoint` from the main cwd) is the guard working as
   designed, and the sweep step can avoid it by running from a worktree or
   with the directory pre-created by an install/daemon step. That is a
   caller-side change for Loom, not a guard change.
2. The `--snapshot` helper is not confined by the guard at all; do not treat
   guard allowlisting of that helper as a safety property.
3. The download denial is unreproduced; reopen only with the original command.

## Drafted upstream issue (text only, unfiled)

Not drafted as a relaxation: the evidence does not support a bounded exception.
If an operator wants a follow-up for `rjwalters/loom`, the evidence-supported
text is: "sweep-wave-lifecycle step 0 should create `.loom/sweep-checkpoint`
before the first guarded write (or via a trusted script) instead of a bare
`mkdir` from the main checkout; and `check-main-clean.sh --snapshot/--baseline`
accepts unconstrained paths while the Bash write-confinement guard does not
inspect helper-mediated writes." Filing is for the operator/Champion.
