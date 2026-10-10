#!/usr/bin/env bash
# Regression tests for sim/check-append-only.sh (issue #146).
# Uses only synthetic temporary git repos; needs no PDK or simulator.
set -uo pipefail
src="$(cd "$(dirname "$0")" && pwd)/check-append-only.sh"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
fails=0

t() { # name expected(0|nz) -- runs $GUARD args in $repo; checks status and no pass msg on failure
  local name="$1" want="$2"; shift 2
  local out rc
  out="$("$@" 2>&1)"; rc=$?
  if [ "$want" = 0 ] && [ $rc -ne 0 ]; then echo "FAIL $name: rc=$rc"; echo "$out"; fails=$((fails+1))
  elif [ "$want" = nz ] && { [ $rc -eq 0 ] || grep -q 'append-only check passed' <<<"$out"; }; then
    echo "FAIL $name: expected failure, rc=$rc"; echo "$out"; fails=$((fails+1))
  else echo "ok   $name"; fi
}

new_repo() {
  repo="$tmp/r$RANDOM$RANDOM"; mkdir -p "$repo/sim/blk/results/run1" "$repo/sim"
  cd "$repo" && git init -q && git config user.email t@t && git config user.name t
  cp "$src" sim/check-append-only.sh
  echo one > sim/blk/results/run1/a.txt; echo two > sim/blk/results/run1/b.txt
  git add -A && git commit -q -m base && base="$(git rev-parse HEAD)"
}
g() { bash "$repo/sim/check-append-only.sh" "$@"; }

new_repo
t identical-revisions 0 g "$base" HEAD
t missing-base nz g no-such-base HEAD
t missing-head nz g "$base" no-such-head
mkdir -p "$tmp/fakebin"
cat > "$tmp/fakebin/git" <<FAKE
#!/usr/bin/env bash
if [ "\$1" = diff ]; then echo "simulated diff failure" >&2; exit 128; fi
exec $(command -v git) "\$@"
FAKE
chmod +x "$tmp/fakebin/git"
t failing-diff nz env PATH="$tmp/fakebin:$PATH" bash "$repo/sim/check-append-only.sh" "$base" HEAD

new_repo; mkdir sim/blk/results/run2; echo n > sim/blk/results/run2/c.txt
git add -A; git commit -q -m add
t new-file-passes 0 g "$base" HEAD

new_repo; echo changed > sim/blk/results/run1/a.txt; git commit -qam mod
t modify-fails nz g "$base" HEAD

new_repo; git rm -q sim/blk/results/run1/a.txt; git commit -qm del
t delete-fails nz g "$base" HEAD

new_repo; git mv sim/blk/results/run1/a.txt sim/blk/results/run1/z.txt; git commit -qm mv
t rename-fails nz g "$base" HEAD

new_repo; echo changed > sim/blk/results/run1/a.txt
echo 'sim/blk/results/run1/ | test exception' > sim/append-only-exceptions.txt
git add -A; git commit -qm exc
t exception-allows 0 g "$base" HEAD

new_repo; echo changed > sim/blk/results/run1/a.txt
echo 'sim/blk/results/run9/ | other run' > sim/append-only-exceptions.txt
git add -A; git commit -qm exc2
t narrow-exception-fails nz g "$base" HEAD

[ $fails -eq 0 ] && echo "all tests passed" || { echo "$fails failed"; exit 1; }
