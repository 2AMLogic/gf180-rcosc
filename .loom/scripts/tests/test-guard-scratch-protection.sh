#!/usr/bin/env bash
# test-guard-scratch-protection.sh — offline regression suite for the two
# scratch-work safety decisions in the installed destructive-command guard
# (issue #150):
#
#   1. rm-scope-unresolved-var (guard-destructive-generic.sh): a recursive
#      removal whose target is an unexpanded shell variable from the path
#      root down (`rm -rf "$UNKNOWN_RESULTS_ROOT/sim/iq/results"`) must be
#      DENIED — the guard cannot tell where the variable resolves at
#      runtime, so it fails closed.
#   2. stash-scope:create-redirect (guard-destructive-generic.sh, #5754):
#      a raw stash CREATE (`git stash -q`) issued from a linked managed
#      `issue-N` worktree — with the `.loom-managed` sentinel present, a
#      real `worktree.sh` at the main checkout, and two or more managed
#      worktrees active — must be DENIED, because `refs/stash` is a single
#      stack shared across every linked worktree of the repo.
#
# The suite invokes the REAL installed guard (the guard-destructive.sh
# dispatcher, which execs the vendored guard-destructive-generic.sh) with
# Bash-tool PreToolUse JSON on stdin and asserts the emitted decision, the
# hookEventName schema field, and the decision-telemetry record. The command
# inside the JSON is NEVER executed anywhere: the hook only inspects inert
# command text, and this suite never passes it to a shell. A canary file and
# before/after fixture-state digests prove non-execution and state
# preservation on every invocation, and a read-only allow control plus a
# main-checkout create control prove the denials are scoped (an always-deny
# hook cannot pass this suite).
#
# Everything runs inside ONE disposable mktemp fixture (paths deliberately
# contain spaces) — a throwaway git repo with two linked managed worktrees —
# so the live repository, its refs/stash, and the fixture's own refs/stash
# are never touched. The hook runs under `env -i` so ambient agent-session
# toggles (LOOM_FORCE_SCOPE, LOOM_GUARD_STASH_SCOPE, …) cannot skew the
# verdicts; the two LOOM_GUARD_DECISION_LOG* variables are the hook's own
# documented test seams for capturing telemetry.
#
# Fixture note: the real worktree.sh's full CREATE path additionally needs
# loom-daemon and forge (gh) access and rolls back without them, so this
# offline suite stages the real helper file (the guard only checks it
# exists) and builds the same managed-worktree filesystem contract — linked
# worktree plus `.loom-managed` sentinel in write_loom_sentinel()'s exact
# format — with plain `git worktree add`. The guard under test is never
# mocked or modified. See README-guard-scratch-protection.md.
#
# Usage (from any directory):
#   bash .loom/scripts/tests/test-guard-scratch-protection.sh
#
# Prerequisites: bash, git, jq, awk, and coreutils (mktemp, find, sort,
# sha256sum). No network, no PDK, no Python, no loom-daemon.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUITE_REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

GUARD_DISPATCHER="$SUITE_REPO_ROOT/.loom/hooks/guard-destructive.sh"
GUARD_GENERIC="$SUITE_REPO_ROOT/.loom/hooks/guard-destructive-generic.sh"
WORKTREE_HELPER="$SUITE_REPO_ROOT/.loom/scripts/worktree.sh"
CONFIG_RESOLVER="$SUITE_REPO_ROOT/.loom/scripts/lib/config-resolver.sh"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

pass() {
    TESTS_RUN=$((TESTS_RUN + 1))
    TESTS_PASSED=$((TESTS_PASSED + 1))
    echo -e "  ${GREEN}PASS${NC}: $1"
}

fail() {
    TESTS_RUN=$((TESTS_RUN + 1))
    TESTS_FAILED=$((TESTS_FAILED + 1))
    echo -e "  ${RED}FAIL${NC}: $1"
    [[ -n "${2:-}" ]] && echo "$2" | sed 's/^/      /'
}

assert_eq() {
    local expected="$1" actual="$2" msg="$3"
    if [[ "$expected" == "$actual" ]]; then
        pass "$msg"
    else
        fail "$msg" "expected: [$expected]
      actual: [$actual]"
    fi
}

assert_contains() {
    local haystack="$1" needle="$2" msg="$3"
    if [[ "$haystack" == *"$needle"* ]]; then
        pass "$msg"
    else
        fail "$msg" "expected to find: [$needle]
      in: [${haystack:0:300}…]"
    fi
}

# ---------------------------------------------------------------------------
# Prerequisites — fail clearly (nonzero) when anything is unavailable.
# ---------------------------------------------------------------------------
for _tool in jq git awk mktemp find sort sha256sum; do
    if ! command -v "$_tool" &>/dev/null; then
        echo "ERROR: required tool '$_tool' not found in PATH — cannot run this suite" >&2
        exit 1
    fi
done

for _subj in "$GUARD_DISPATCHER" "$GUARD_GENERIC" "$WORKTREE_HELPER" "$CONFIG_RESOLVER"; do
    if [[ ! -f "$_subj" ]]; then
        echo "ERROR: subject file $_subj not found — run this suite from a Loom-managed checkout of the repository" >&2
        exit 1
    fi
done

# ---------------------------------------------------------------------------
# Fixture: one disposable root whose paths contain spaces (AC: the suite must
# resolve paths from its own location and inside JSON cwd correctly even with
# spaces). Removed by trap on success AND failure.
# ---------------------------------------------------------------------------
FIXTURE_ROOT=""
cleanup() {
    if [[ -n "$FIXTURE_ROOT" && -d "$FIXTURE_ROOT" ]]; then
        rm -rf -- "$FIXTURE_ROOT"
    fi
}
trap cleanup EXIT INT TERM

FIXTURE_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/loom scratch guard.XXXXXX")"
MAIN="$FIXTURE_ROOT/main repo"
CANARY="$FIXTURE_ROOT/canary root"
TELEMETRY="$FIXTURE_ROOT/telemetry log.jsonl"
RUN_DIR="$FIXTURE_ROOT/.run"
WT1="$MAIN/.loom/worktrees/issue-4211"
WT2="$MAIN/.loom/worktrees/issue-4212"

# The rm command under test references $UNKNOWN_RESULTS_ROOT. It is assigned
# ONLY here, in the suite's own shell, pointing at the canary: the hook
# process itself runs under `env -i` and never sees the assignment (it only
# parses the inert command text), but if anything ever EXECUTED the JSON
# command through this shell the canary would vanish and the suite would
# fail loudly.
export UNKNOWN_RESULTS_ROOT="$CANARY"

# Write the `.loom-managed` sentinel in write_loom_sentinel()'s exact format
# (scripts/worktree.sh) so the fixture worktrees carry the same marker the
# real helper leaves.
write_sentinel() {
    local wt="$1" issue="$2"
    local branch="feature/issue-$issue"
    cat > "$wt/.loom-managed" <<EOF
# Loom-managed worktree marker
# Created by .loom/scripts/worktree.sh
# Issue: $issue
# Branch: $branch
# Removing this file makes Loom treat the worktree as user-owned and refuse
# to clean it up automatically.
EOF
}

build_fixture() {
    mkdir -p "$MAIN/.loom/hooks" "$MAIN/.loom/scripts" "$RUN_DIR" "$CANARY/sim/iq/results"

    cp "$GUARD_DISPATCHER" "$MAIN/.loom/hooks/guard-destructive.sh"
    cp "$GUARD_GENERIC" "$MAIN/.loom/hooks/guard-destructive-generic.sh"
    cp -R "$SUITE_REPO_ROOT/.loom/scripts/lib" "$MAIN/.loom/scripts/lib"
    cp "$WORKTREE_HELPER" "$MAIN/.loom/scripts/worktree.sh"
    chmod +x "$MAIN/.loom/hooks/guard-destructive.sh" \
             "$MAIN/.loom/hooks/guard-destructive-generic.sh" \
             "$MAIN/.loom/scripts/worktree.sh"

    git -c init.defaultBranch=main init -q "$MAIN"
    git -C "$MAIN" config user.email "guard-scratch-test@example.invalid"
    git -C "$MAIN" config user.name "Guard Scratch Test"
    echo "seed" > "$MAIN/README.md"
    git -C "$MAIN" add README.md
    git -C "$MAIN" commit -qm "seed"

    mkdir -p "$MAIN/.loom/worktrees"
    git -C "$MAIN" worktree add -q -b feature/issue-4211 "$WT1"
    git -C "$MAIN" worktree add -q -b feature/issue-4212 "$WT2"
    write_sentinel "$WT1" 4211
    write_sentinel "$WT2" 4212

    # Tracked-but-uncommitted WIP inside worktree 4211: if the denied
    # `git stash -q` were ever executed, this modification would disappear
    # from the worktree and a refs/stash entry would appear — both caught
    # by the state digest below.
    echo "wip for stash fixture" >> "$WT1/README.md"

    # Canary the rm command would delete if anything executed it.
    echo "keepme" > "$CANARY/sim/iq/results/keepme"

    : > "$TELEMETRY"
}

# Deterministic digest of everything the hook invocations must leave
# untouched: porcelain + stash lists + worktree registry + refs/stash
# presence in the main checkout and both worktrees, plus content hashes of
# every fixture file outside the telemetry log, the hook's .loom/logs
# spillover dir, and the run-capture dir.
fixture_state() {
    {
        git -C "$MAIN" status --porcelain
        git -C "$MAIN" stash list
        git -C "$MAIN" worktree list --porcelain
        if git -C "$MAIN" rev-parse -q --verify refs/stash >/dev/null 2>&1; then
            echo "REFS_STASH_PRESENT"
        else
            echo "NO_REFS_STASH"
        fi
        local wt
        for wt in "$WT1" "$WT2"; do
            [[ -d "$wt" ]] || continue
            git -C "$wt" status --porcelain
            git -C "$wt" stash list
        done
        ( cd "$MAIN" && find . -type f ! -path './.loom/logs/*' -print0 | sort -z | xargs -0 sha256sum )
        find "$CANARY" -type f -print0 | sort -z | xargs -0 sha256sum
    } | sha256sum | cut -d' ' -f1
}

# ---------------------------------------------------------------------------
# Hook runner: feeds `{tool_name:"Bash",tool_input:{command:…},cwd:…}` JSON
# to the staged REAL dispatcher. `env -i` isolates the hook from every
# ambient LOOM_* toggle of the invoking session; the two decision-log
# variables are the hook's documented test seams (#3771).
# ---------------------------------------------------------------------------
HOOK_RC=0
HOOK_STDOUT=""
STATE_BEFORE=""
STATE_AFTER=""

run_hook() {
    local cwd="$1" cmd="$2"
    STATE_BEFORE=$(fixture_state)
    jq -cn --arg cmd "$cmd" --arg cwd "$cwd" \
        '{tool_name:"Bash",tool_input:{command:$cmd},cwd:$cwd}' \
      | env -i PATH="$PATH" HOME="${HOME:-/tmp}" \
            LOOM_GUARD_DECISION_LOG=1 \
            LOOM_GUARD_DECISION_LOG_FILE="$TELEMETRY" \
            bash "$MAIN/.loom/hooks/guard-destructive.sh" \
            > "$RUN_DIR/hook.stdout" 2> "$RUN_DIR/hook.stderr"
    HOOK_RC=$?
    HOOK_STDOUT=$(cat "$RUN_DIR/hook.stdout")
    STATE_AFTER=$(fixture_state)
}

assert_state_unchanged() {
    local label="$1"
    assert_eq "$STATE_BEFORE" "$STATE_AFTER" "fixture state unchanged across: $label"
}

telemetry_lines() {
    wc -l < "$TELEMETRY" 2>/dev/null || echo 0
}

# Assert the telemetry record at 1-based line $1 has field $2 == $3.
assert_telemetry_field() {
    local line_no="$1" field="$2" expected="$3" label="$4"
    local actual
    actual=$(sed -n "${line_no}p" "$TELEMETRY" | jq -r ".$field" 2>/dev/null) || actual="<jq-error>"
    assert_eq "$expected" "$actual" "$label"
}

assert_deny_schema() {
    local label="$1"
    if [[ -z "$HOOK_STDOUT" ]]; then
        fail "$label: hook produced no stdout" ""
        return 1
    fi
    if ! printf '%s' "$HOOK_STDOUT" | jq -e . >/dev/null 2>&1; then
        fail "$label: stdout is not valid JSON" "$HOOK_STDOUT"
        return 1
    fi
    pass "$label: stdout is valid JSON"
    local field
    field=$(printf '%s' "$HOOK_STDOUT" | jq -r '.hookSpecificOutput.hookEventName // ""')
    assert_eq "PreToolUse" "$field" "$label: hookEventName is PreToolUse"
    field=$(printf '%s' "$HOOK_STDOUT" | jq -r '.hookSpecificOutput.permissionDecision // ""')
    assert_eq "deny" "$field" "$label: permissionDecision is deny"
    return 0
}

# ===========================================================================
echo "== Building disposable fixture (spaces in paths) =="
build_fixture
if [[ ! -f "$WT1/.loom-managed" || ! -f "$WT2/.loom-managed" ]]; then
    echo "ERROR: fixture worktrees or sentinels missing — cannot continue" >&2
    exit 1
fi
echo "Fixture ready: $FIXTURE_ROOT"
echo ""

# ---------------------------------------------------------------------------
echo "== Test 1: unresolved-variable recursive removal is denied (rm-scope-unresolved-var) =="
run_hook "$MAIN" 'rm -rf "$UNKNOWN_RESULTS_ROOT/sim/iq/results"'
assert_eq "0" "$HOOK_RC" "rm deny: hook exits 0 (never non-zero)"
if assert_deny_schema "rm deny"; then
    REASON=$(printf '%s' "$HOOK_STDOUT" | jq -r '.hookSpecificOutput.permissionDecisionReason')
    assert_contains "$REASON" "unexpanded shell variable" \
        "rm deny: reason names the unresolved-target cause"
fi
assert_eq "1" "$(telemetry_lines)" "rm deny: exactly one telemetry record appended"
assert_telemetry_field 1 pattern rm-scope-unresolved-var "rm deny: telemetry pattern is rm-scope-unresolved-var"
assert_telemetry_field 1 decision deny "rm deny: telemetry decision is deny"
assert_telemetry_field 1 tier catastrophic "rm deny: telemetry tier is catastrophic"
if [[ -f "$CANARY/sim/iq/results/keepme" ]]; then
    pass "rm deny: canary file intact — JSON command was never executed"
else
    fail "rm deny: canary file intact — JSON command was never executed" "canary vanished: something executed the command"
fi
assert_state_unchanged "rm deny"
echo ""

# ---------------------------------------------------------------------------
echo "== Test 2: raw stash create from linked managed worktree is denied (stash-scope:create-redirect) =="
run_hook "$WT1" 'git stash -q'
assert_eq "0" "$HOOK_RC" "stash deny: hook exits 0 (never non-zero)"
if assert_deny_schema "stash deny"; then
    REASON=$(printf '%s' "$HOOK_STDOUT" | jq -r '.hookSpecificOutput.permissionDecisionReason')
    assert_contains "$REASON" "refs/stash" \
        "stash deny: reason names the shared refs/stash stack"
    assert_contains "$REASON" "snapshot 4211" \
        "stash deny: reason redirects to the per-issue worktree.sh replacement"
fi
assert_eq "2" "$(telemetry_lines)" "stash deny: exactly one new telemetry record appended"
assert_telemetry_field 2 pattern stash-scope:create-redirect "stash deny: telemetry pattern is stash-scope:create-redirect"
assert_telemetry_field 2 decision deny "stash deny: telemetry decision is deny"
assert_telemetry_field 2 tier catastrophic "stash deny: telemetry tier is catastrophic"
if git -C "$MAIN" rev-parse -q --verify refs/stash >/dev/null 2>&1; then
    fail "stash deny: refs/stash still absent" "a stash entry was created"
else
    pass "stash deny: refs/stash still absent"
fi
if git -C "$WT1" diff --quiet 2>/dev/null; then
    fail "stash deny: WIP still present in worktree" "the tracked WIP modification vanished (stash was executed?)"
else
    pass "stash deny: WIP still present in worktree"
fi
assert_state_unchanged "stash deny"
echo ""

# ---------------------------------------------------------------------------
echo "== Test 3: main-checkout stash create stays allowed (deny is worktree-scoped) =="
run_hook "$MAIN" 'git stash -q'
assert_eq "0" "$HOOK_RC" "main-checkout control: hook exits 0"
if [[ -z "$HOOK_STDOUT" ]]; then
    pass "main-checkout control: no decision emitted (allow)"
elif printf '%s' "$HOOK_STDOUT" | jq -e '.hookSpecificOutput.permissionDecision == "deny"' >/dev/null 2>&1; then
    fail "main-checkout control: no decision emitted (allow)" "got a deny: $HOOK_STDOUT"
else
    pass "main-checkout control: no decision emitted (allow)"
fi
assert_eq "2" "$(telemetry_lines)" "main-checkout control: no new telemetry record"
if git -C "$MAIN" rev-parse -q --verify refs/stash >/dev/null 2>&1; then
    fail "main-checkout control: refs/stash still absent" "a stash entry was created"
else
    pass "main-checkout control: refs/stash still absent"
fi
assert_state_unchanged "main-checkout control"
echo ""

# ---------------------------------------------------------------------------
echo "== Test 4: read-only allow control (an always-deny hook cannot pass) =="
run_hook "$WT1" 'git status --short'
assert_eq "0" "$HOOK_RC" "allow control: hook exits 0"
if [[ -z "$HOOK_STDOUT" ]]; then
    pass "allow control: silent allow for read-only command"
else
    if printf '%s' "$HOOK_STDOUT" | jq -e '.hookSpecificOutput.permissionDecision == "deny"' >/dev/null 2>&1; then
        fail "allow control: silent allow for read-only command" "$HOOK_STDOUT"
    else
        pass "allow control: silent allow for read-only command"
    fi
fi
assert_eq "2" "$(telemetry_lines)" "allow control: no telemetry record for an allow"
assert_state_unchanged "allow control"
echo ""

# ---------------------------------------------------------------------------
if [[ -s "$RUN_DIR/hook.stderr" ]]; then
    echo "note: last hook stderr (diagnostics only):"
    sed 's/^/      /' "$RUN_DIR/hook.stderr"
fi

echo "Tests run: $TESTS_RUN, Passed: $TESTS_PASSED, Failed: $TESTS_FAILED"

if [[ $TESTS_FAILED -gt 0 ]]; then
    exit 1
fi
exit 0
