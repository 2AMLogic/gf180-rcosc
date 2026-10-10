#!/usr/bin/env bash
# Append-only guard for sim/*/results/* (issue #84).
# Usage: sim/check-append-only.sh <base-sha> [head-ref]   (head-ref default HEAD)
# Fails if the diff base..head modifies, deletes, renames, or type-changes any
# tracked file under sim/*/results/. Pure additions pass. Paths covered by a
# line "<path prefix> | <reason>" in sim/append-only-exceptions.txt are
# allowed and the reason is printed.
set -euo pipefail

base="${1:?usage: $0 <base-sha> [head-ref]}"
head="${2:-HEAD}"
root="$(git rev-parse --show-toplevel)"
exc="$root/sim/append-only-exceptions.txt"

prefixes=(); reasons=()
if [ -f "$exc" ]; then
  n=0
  while IFS= read -r line || [ -n "$line" ]; do
    n=$((n+1))
    case "$line" in ''|'#'*) continue ;; esac
    if [[ "$line" != *'|'* ]]; then
      echo "ERROR: $exc:$n: expected '<path prefix> | <reason>'" >&2; exit 2
    fi
    p="${line%%|*}"; r="${line#*|}"
    p="$(echo "$p" | xargs)"; r="$(echo "$r" | xargs)"
    if [ -z "$p" ] || [ -z "$r" ]; then
      echo "ERROR: $exc:$n: empty path prefix or empty reason" >&2; exit 2
    fi
    prefixes+=("$p"); reasons+=("$r")
  done < "$exc"
fi

excepted() { # path -> prints reason, returns 0 if covered
  local i
  for i in "${!prefixes[@]}"; do
    case "$1" in "${prefixes[$i]}"*) echo "${reasons[$i]}"; return 0 ;; esac
  done
  return 1
}

for rev in "$base" "$head"; do
  if ! git rev-parse --verify --quiet "$rev^{commit}" >/dev/null; then
    echo "ERROR: cannot resolve revision '$rev'; append-only comparison not performed." >&2
    exit 2
  fi
done

# Run the diff as an explicitly checked command (not in process substitution,
# whose failure would be silently ignored) before evaluating any paths.
if ! difflist="$(git diff --name-status --find-renames --diff-filter=ACDMRTUXB "$base" "$head" -- 'sim/*/results/*')"; then
  echo "ERROR: git diff $base $head failed; append-only comparison not performed." >&2
  exit 2
fi

fail=0
while IFS=$'\t' read -r status p1 p2; do
  [ -z "$status" ] && continue
  [ "${status:0:1}" = "A" ] && continue
  paths=("$p1"); [ -n "${p2:-}" ] && paths+=("$p2")
  # Every path touched (old and, for renames, new) must be excepted.
  ok=1; why=""
  for p in "${paths[@]}"; do
    if r="$(excepted "$p")"; then why="$r"; else ok=0; fi
  done
  if [ "$ok" = 1 ]; then
    echo "ALLOWED   $status ${paths[*]}  (exception: $why)"
  else
    echo "VIOLATION $status ${paths[*]}" >&2; fail=1
  fi
done <<< "$difflist"

if [ "$fail" = 1 ]; then
  echo "sim results are append-only: add a new timestamped run dir instead of editing prior runs." >&2
  echo "If truly unavoidable, add '<run path prefix> | <reason>' to sim/append-only-exceptions.txt." >&2
  exit 1
fi
echo "append-only check passed ($base..$head)"
