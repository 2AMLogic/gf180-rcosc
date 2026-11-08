#!/usr/bin/env bash
# repro.sh — read-only reproduction harness for issue #149.
#
# Feeds Bash-tool commands to the REAL vendored guard
# (.loom/hooks/guard-destructive.sh -> guard-destructive-generic.sh) inside a
# throwaway git repo that has a `.loom-managed` worktree, and prints one
# verdict line per case. It changes no guard behavior and writes only under a
# mktemp directory (commands are only passed to the guard as text, never
# executed).
#
# Usage: bash docs/guard-confinement-investigation/repro.sh
# Output: TSV  <case> <verdict> <reason> <command>
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SRC_HOOKS="$REPO_ROOT/.loom/hooks"
SRC_LIB="$REPO_ROOT/.loom/scripts/lib"

FX="$(mktemp -d)"
trap 'rm -rf "$FX"' EXIT
MAIN="$FX/main"
git init -q "$MAIN"
git -C "$MAIN" -c user.email=a@b -c user.name=n commit -q --allow-empty -m init
mkdir -p "$MAIN/.loom/hooks" "$MAIN/.loom/scripts/lib"
cp "$SRC_HOOKS"/guard-destructive*.sh "$MAIN/.loom/hooks/"
cp "$SRC_LIB"/*.sh "$MAIN/.loom/scripts/lib/"
git -C "$MAIN" worktree add -q "$MAIN/.loom/worktrees/issue-1" -b feature/issue-1
touch "$MAIN/.loom/worktrees/issue-1/.loom-managed"
WT="$MAIN/.loom/worktrees/issue-1"
# Symlink-escape fixture: a link inside the worktree that points at main.
ln -s "$MAIN" "$WT/escape-link"
mkdir -p "$MAIN/.loom/sweep-checkpoint"

# Sanitised env: no ambient LOOM_* overrides, builder role, isolation default-on.
run_guard() { # $1=cwd $2=command
    local input
    input=$(jq -n --arg c "$2" --arg d "$1" '{tool_name:"Bash",tool_input:{command:$c},cwd:$d}')
    printf '%s' "$input" | env -i HOME="$FX" PATH="$PATH" LOOM_ROLE=builder \
        LOOM_PROJECT_ROOT="$MAIN" bash "$MAIN/.loom/hooks/guard-destructive.sh" 2>/dev/null
}
case_row() { # id cwd command
    local out dec why=""
    out=$(run_guard "$2" "$3")
    dec=$(printf '%s' "$out" | jq -r '.hookSpecificOutput.permissionDecision // "allow"' 2>/dev/null || echo "?")
    [[ -z "$out" ]] && dec=allow
    case "$out" in
        *"unexpanded shell variable"*|*"unexpanded shell"*) why=unresolved-var ;;
        *"outside"*|*"main repository checkout"*|*"main checkout"*) why=main-checkout ;;
    esac
    printf '%s\t%s\t%s\t%s\n' "$1" "$dec" "${why:--}" "$3"
}

M="$MAIN"
# --- Checkpoint case (from sweep-wave-lifecycle.md step 0) -------------------
RID="sweep-20260722T231500Z-84213-a3f9c1b2"   # shape per sweep-run-registry.sh:405-407
B=".loom/sweep-checkpoint/main-clean-baseline-${RID}.txt"
echo -e "case\tverdict\treason\tcommand"
for cwd_label in main wt; do
    cwd="$M"; [[ $cwd_label == wt ]] && cwd="$WT"
    case_row "ckpt-mkdir-$cwd_label"  "$cwd" "mkdir -p .loom/sweep-checkpoint"
    case_row "ckpt-mkdir-bare-$cwd_label" "$cwd" "mkdir .loom/sweep-checkpoint"
    case_row "ckpt-snapshot-lit-$cwd_label" "$cwd" "./.loom/scripts/check-main-clean.sh --snapshot $B"
    case_row "ckpt-snapshot-var-$cwd_label" "$cwd" "MAIN_CLEAN_BASELINE=\"$B\"
./.loom/scripts/check-main-clean.sh --snapshot \"\$MAIN_CLEAN_BASELINE\""
    case_row "ckpt-snapshot-runid-var-$cwd_label" "$cwd" "MAIN_CLEAN_BASELINE=\".loom/sweep-checkpoint/main-clean-baseline-\${RUN_ID}.txt\"
./.loom/scripts/check-main-clean.sh --snapshot \"\$MAIN_CLEAN_BASELINE\""
done
# --- Checkpoint controls ----------------------------------------------------
case_row "ctl-ckpt-arbitrary-main-write" "$M" "echo x > $M/src.txt"
case_row "ctl-ckpt-redirect-checkpoint-dir" "$M" "echo x > .loom/sweep-checkpoint/x.txt"
case_row "ctl-ckpt-traversal" "$M" "./.loom/scripts/check-main-clean.sh --snapshot .loom/sweep-checkpoint/../../evil.txt"
case_row "ctl-ckpt-traversal-wt" "$WT" "./.loom/scripts/check-main-clean.sh --snapshot ../../../evil.txt"
case_row "ctl-ckpt-symlink-escape" "$WT" "./.loom/scripts/check-main-clean.sh --snapshot escape-link/evil.txt"
case_row "ctl-ckpt-unknown-var" "$M" "./.loom/scripts/check-main-clean.sh --snapshot \"\$UNKNOWN/x.txt\""
case_row "ctl-ckpt-cmd-subst" "$M" "./.loom/scripts/check-main-clean.sh --snapshot \"\$(pwd)/evil.txt\""
case_row "ctl-ckpt-proc-subst" "$M" "./.loom/scripts/check-main-clean.sh --snapshot >(cat > $M/evil.txt)"
case_row "ctl-ckpt-helper-identity" "$M" "./.loom/scripts/other-helper.sh --snapshot $B"
case_row "ctl-ckpt-extra-args" "$M" "./.loom/scripts/check-main-clean.sh --snapshot $B --quarantine; echo x > $M/evil.txt"
case_row "ctl-ckpt-mkdir-main-other" "$M" "mkdir $M/not-checkpoint"
# --- Download case (SYNTHETIC — original loop unrecovered) -------------------
case_row "dl-synth-nocd" "$WT" 'for f in alpha beta; do echo x > /tmp/e85/$f.rst; done'
case_row "dl-synth-cd" "$WT" 'cd /tmp/e85 && for f in alpha beta; do echo x > $f.rst; done'
case_row "dl-synth-curl-nocd" "$WT" 'for f in alpha beta; do curl -sSfL -o /tmp/e85/$f.rst https://example.invalid/$f.rst; done'
case_row "dl-synth-redirect-curl" "$WT" 'for f in alpha beta; do curl -sSfL https://example.invalid/$f.rst > /tmp/e85/$f.rst; done'
case_row "dl-synth-mkdir-cd" "$WT" 'mkdir -p /tmp/e85 && cd /tmp/e85 && for f in alpha beta; do curl -sSfL https://example.invalid/$f.rst > $f.rst; done'
# --- Download controls ------------------------------------------------------
case_row "ctl-dl-main-write" "$WT" "for f in a b; do echo x > $M/\$f.rst; done"
case_row "ctl-dl-traversal-list" "$WT" 'cd /tmp/e85 && for f in ../x; do echo x > $f.rst; done'
case_row "ctl-dl-slash-list" "$WT" 'cd /tmp/e85 && for f in sub/x; do echo x > $f.rst; done'
case_row "ctl-dl-abs-list" "$WT" "cd /tmp/e85 && for f in $M/x; do echo x > \$f.rst; done"
case_row "ctl-dl-unknown-var" "$WT" 'cd /tmp/e85 && echo x > $UNKNOWN.rst'
case_row "ctl-dl-cmd-subst-list" "$WT" 'cd /tmp/e85 && for f in $(ls); do echo x > $f.rst; done'
case_row "ctl-dl-dynamic-list" "$WT" 'cd /tmp/e85 && for f in $LIST; do echo x > $f.rst; done'
case_row "ctl-dl-glob-list" "$WT" 'cd /tmp/e85 && for f in *; do echo x > $f.rst; done'
case_row "ctl-dl-symlink-same-cmd" "$WT" "cd /tmp/e85 && ln -s $M link && for f in link; do echo x > \$f.rst; done"
case_row "ctl-dl-rebinding-read" "$WT" 'cd /tmp/e85 && for f in a; do read f; echo x > $f.rst; done'
case_row "ctl-dl-tmp-traversal-cwd" "$WT" 'cd /tmp/../home && for f in a; do echo x > $f.rst; done'
