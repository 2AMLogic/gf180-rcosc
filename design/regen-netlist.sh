#!/usr/bin/env bash
# Regenerate design/netlist/*.spice from the xschem schematics (issue #6),
# or -- since issue #348 -- verify the committed netlists are still current
# (--check) without writing anything.
#
# This is the reproducible derivation step the T1 "design sources" pass
# condition requires (docs/design-evidence-tiers.md, cited from klayout-tools
# in issue #6): committed schematics + a derived netlist that is
# *regenerated on schematic change*, not a one-off manual export. Re-run
# this script any time design/*.sch changes and commit the resulting
# design/netlist/*.spice alongside the schematic edit.
#
# Usage: design/regen-netlist.sh [--check]
#
# Netlisting goes through `klt netlist` (bounded by a timeout, real exit
# status), never raw xschem. PDK_ROOT (if already set) is used first, else
# `klt pdk find` (see docs in design/README.md).
#
# ---------------------------------------------------------------------------
# Netlist toolchain pin (issue #348). Netlisting runs on its OWN pinned
# klayout-tools build, KLT_NETLIST_VERSION_EXPECTED below, invoked ephemerally
# through `uv run` the same way layout/run_checks.sh's ERC step invokes its
# own pinned build. It is deliberately NOT the geometry pin run_checks.sh
# enforces: that build has no `klt netlist` subcommand at all, which is why
# run_checks.sh could not run end to end (DR-0042); moving that pin is
# issue #204, parked on a separate decision. Every klt call in this script
# (--version, pdk find, netlist) is routed through the pinned wrapper, and the
# resolved version is checked against the pin before anything runs.
#
# --check is a verify-only staleness gate -- this is the mode
# layout/run_checks.sh calls. For each entry point it netlists the schematic
# into a temporary directory and compares against the committed
# design/netlist/<name>.spice, normalising ONLY the `** sch_path:` /
# `** sym_path:` comment lines on both sides: those lines embed the
# checkout-absolute path of the machine that last regenerated the netlist
# (klayout-tools#4091), so a real regeneration from any other checkout can
# never be byte-identical. Any other difference -- a changed device, a renamed
# or reordered port -- fails, printing the diff. `klt netlist
# --ignore-comments` is NOT used for this: it drops every `*`-prefixed line on
# both sides, including the `**.subckt` / `*.iopin` / `**.ends` declarations
# that a port rename lives in, and would report `match` on a schematic whose
# ports no longer agree with the committed netlist. --check writes nothing
# under design/netlist/ -- not even the gitignored pdk_include.spice.
#
# Why run_checks.sh verifies instead of regenerating (issue #348): its
# geometry klt cannot netlist, and
# layout/build_cells.py consumes the committed
# design/netlist/rcosc_top.spice -- the run needs that file *current*, not
# rewritten. Regenerating it inside a layout-evidence run would rewrite
# committed evidence behind the run's back; a stale netlist must stop the run
# and be reported instead (regenerate deliberately, via this script without
# --check, and commit the result alongside the schematic edit).
# ---------------------------------------------------------------------------

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESIGN_DIR="$REPO_ROOT/design"
RCFILE="$DESIGN_DIR/xschemrc"
NETLIST_DIR="$DESIGN_DIR/netlist"

export PDK="${PDK:-gf180mcuC}"

KLT_NETLIST_VERSION_EXPECTED="0.9.2"
KLT_NETLIST=(uv run --quiet --no-project --with "klayout-tools==${KLT_NETLIST_VERSION_EXPECTED}" klt)

CHECK_ONLY=0
case "${1:-}" in
  "") ;;
  --check) CHECK_ONLY=1 ;;
  *)
    echo "usage: $0 [--check]" >&2
    exit 2
    ;;
esac

KLT_NETLIST_VERSION_ACTUAL="$("${KLT_NETLIST[@]}" --version 2>/dev/null | head -1 | awk '{print $2}' || true)"
if [ "$KLT_NETLIST_VERSION_ACTUAL" != "$KLT_NETLIST_VERSION_EXPECTED" ]; then
  echo "ERROR: netlist klt ${KLT_NETLIST_VERSION_ACTUAL:-unresolved} != pinned ${KLT_NETLIST_VERSION_EXPECTED}" >&2
  echo "       design/regen-netlist.sh netlists through this separate pin because the" >&2
  echo "       0.4.0 geometry pin run_checks.sh enforces has no 'klt netlist' (DR-0042);" >&2
  echo "       the pinned invocation is:" >&2
  echo "         uv run --no-project --with \"klayout-tools==${KLT_NETLIST_VERSION_EXPECTED}\" klt ..." >&2
  exit 1
fi

# PDK_ROOT is only needed for MODEL_DIR (pdk_include.spice below); netlisting
# itself resolves the PDK through `klt netlist --pdk/--pdk-root`.
if [[ -z "${PDK_ROOT:-}" ]]; then
  RESOLVED_ROOT="$("${KLT_NETLIST[@]}" pdk find --pdk "$PDK" --format json 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin).get("root",""))' 2>/dev/null || true)"
  [[ -n "$RESOLVED_ROOT" ]] && export PDK_ROOT="$RESOLVED_ROOT"
fi
: "${PDK_ROOT:?PDK_ROOT not set and could not be resolved via 'klt pdk find --pdk gf180mcuC'. Set PDK_ROOT to the volare/ciel install root (parent of gf180mcuC/) and re-run.}"

MODEL_DIR="$PDK_ROOT/$PDK/libs.tech/ngspice"

# Every schematic that is netlisted directly (a real entry point, not a
# hierarchical building block only ever reached via another symbol).
# rcosc_top.sch is the oscillator block itself; smoke_test.sch is the
# bring-up testbench (issue #6 non-goals: functional/DC sanity only);
# pvt_tb.sch is the PVT-corner testbench (issue #12) whose per-run corner
# and .control halves are generated by sim/pvt/pvt_sweep.py.
ENTRY_POINTS=(rcosc_top smoke_test pvt_tb)

if [ "$CHECK_ONLY" -eq 1 ]; then
  # ---- verify-only: netlist into a temp dir, normalised diff, no writes ----
  # Normalise ONLY the checkout-absolute path comment lines (see the header
  # for why ONLY those lines are touched); any other difference is drift and
  # fails the check. Written to temp files with sed's status checked, never
  # piped blind into diff -- a failed normalisation must abort, not silently
  # compare two empty streams.
  normalize_netlist() {
    sed -E 's@^(\*\* s(ch|ym)_path:).*@\1 <checkout path normalised>@' "$1"
  }
  TMP_OUT="$(mktemp -d "${TMPDIR:-/tmp}/regen-netlist-check.XXXXXX")"
  trap 'rm -rf "$TMP_OUT"' EXIT
  check_rc=0
  for name in "${ENTRY_POINTS[@]}"; do
    sch="$DESIGN_DIR/$name.sch"
    committed="$NETLIST_DIR/$name.spice"
    if [[ ! -f "$sch" ]]; then
      echo "ERROR: expected schematic not found: $sch" >&2
      exit 1
    fi
    if [[ ! -f "$committed" ]]; then
      echo "ERROR: no committed netlist for design/$name.sch: $committed does not exist" >&2
      echo "       run design/regen-netlist.sh (without --check) and commit" >&2
      echo "       design/netlist/$name.spice alongside the schematic." >&2
      exit 1
    fi
    echo "-- checking design/$name.sch against design/netlist/$name.spice --"
    "${KLT_NETLIST[@]}" netlist "$sch" -o "$TMP_OUT/$name.spice" \
      --pdk "$PDK" --pdk-root "$PDK_ROOT" --rcfile "$RCFILE"
    norm_committed="$TMP_OUT/$name.committed.norm"
    norm_fresh="$TMP_OUT/$name.fresh.norm"
    normalize_netlist "$committed" > "$norm_committed" || {
      echo "ERROR: normalising $committed failed -- cannot judge drift" >&2
      exit 1
    }
    normalize_netlist "$TMP_OUT/$name.spice" > "$norm_fresh" || {
      echo "ERROR: normalising the fresh netlist of design/$name.sch failed -- cannot judge drift" >&2
      exit 1
    }
    if ! diff -u "$norm_committed" "$norm_fresh"; then
      echo "ERROR: design/netlist/$name.spice is stale against design/$name.sch" >&2
      echo "       (differences above, path comments aside). Re-run" >&2
      echo "       design/regen-netlist.sh (without --check) and commit the" >&2
      echo "       regenerated netlist -- do not edit it by hand." >&2
      check_rc=1
    fi
  done
  if [ "$check_rc" -eq 0 ]; then
    echo "== netlist check passed: committed design/netlist/*.spice are current =="
  fi
  exit "$check_rc"
fi

if [[ ! -f "$MODEL_DIR/design.ngspice" || ! -f "$MODEL_DIR/sm141064.ngspice" ]]; then
  echo "ERROR: gf180mcu ngspice models not found under $MODEL_DIR" >&2
  echo "       Did you 'volare fetch --pdk gf180mcu <hash>' and 'volare enable ...'?" >&2
  exit 1
fi

mkdir -p "$NETLIST_DIR"

echo "== gf180-rcosc netlist regen: $(date -u +%Y-%m-%dT%H:%M:%SZ) =="
echo "PDK_ROOT=$PDK_ROOT PDK=$PDK"
echo "klt: $("${KLT_NETLIST[@]}" --version 2>&1 | head -1)"

for name in "${ENTRY_POINTS[@]}"; do
  sch="$DESIGN_DIR/$name.sch"
  if [[ ! -f "$sch" ]]; then
    echo "ERROR: expected schematic not found: $sch" >&2
    exit 1
  fi
  echo "-- netlisting $name.sch --"
  "${KLT_NETLIST[@]}" netlist "$sch" -o "$NETLIST_DIR/$name.spice" \
    --pdk "$PDK" --pdk-root "$PDK_ROOT" --rcfile "$RCFILE"
done

# pdk_include.spice: the model-library recipe smoke_test.spice's
# `.include pdk_include.spice` line pulls in. Generated here (not
# hardcoded in the schematic, so smoke_test.sch has no machine-specific
# path) -- overwritten each run by design, not evidence itself.
#
# Recipe notes (see issue #6 PR description for the debugging trail):
#   - `.lib <file> typical`       activates the nfet_03v3/pfet_03v3 device
#                                  subckts (nested inside gf180mcu's own
#                                  'fets_mm' library section) plus their
#                                  typical-corner model parameters.
#   - `.lib <file> res_typical`   sets rsh_* sheet-resistance parameters and
#                                  activates the 'res' library section that
#                                  defines ppolyf_u_1k (and siblings).
#   - `.lib <file> mimcap_typical` sets the mim_corner_* parameters the MIM
#                                  cap subckts below use.
#   - `.lib <file> cap_mim`        defines cap_mim_1f0fF (and cap_mim_1f5fF /
#                                  cap_mim_2f0fF) -- the LEGACY/local model
#                                  set xschem's cap_mim_*.sym symbols use, as
#                                  distinct from the "cap_mim_new" /
#                                  *_m2m3_noshield-style subckts in
#                                  sm141064_mim.ngspice, which model a
#                                  different (metal-stack-specific) device.
#   A blanket `.include sm141064.ngspice` was deliberately NOT used: it
#   parses every top-level `.LIB ... .ENDL` block unconditionally, which
#   redefines several subckts (nfet_03v3, ppolyf_u_1k, ...) once per corner
#   block and produced spurious "too few parameters" subcircuit-expansion
#   errors -- always resolve gf180mcu devices via targeted `.lib` calls.
cat > "$NETLIST_DIR/pdk_include.spice" <<EOF
* Generated by design/regen-netlist.sh from \$PDK_ROOT/\$PDK -- do not edit
* by hand; re-run design/regen-netlist.sh to refresh.
.include $MODEL_DIR/design.ngspice
.lib $MODEL_DIR/sm141064.ngspice typical
.lib $MODEL_DIR/sm141064.ngspice res_typical
.lib $MODEL_DIR/sm141064.ngspice mimcap_typical
.lib $MODEL_DIR/sm141064.ngspice cap_mim
EOF

echo "== netlist regen complete: $NETLIST_DIR =="
