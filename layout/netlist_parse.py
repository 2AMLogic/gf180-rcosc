"""Tiny SPICE subckt-call parser scoped to `design/netlist/rcosc_top.spice`'s
own device-line shapes (issue #13's layout build).

Not a general SPICE parser -- reads exactly the `X<name> <nodes...> <model>
<key=value...>` device-call lines `design/regen-netlist.sh`'s xschem export
produces (merging `+` continuation lines first), so `layout/build_cells.py`
derives every drawn device's geometry from the same netlist the schematic
LVS reference is generated from, rather than retyping `r_length`/`r_width`/
`L`/`W`/`nf` values that could silently drift from a schematic edit.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Device:
    name: str  # e.g. "XRBA" (leading X kept)
    nodes: list[str]
    model: str
    params: dict[str, str] = field(default_factory=dict)

    def param_um(self, key: str) -> float:
        """Parse a `<num><suffix>` SPICE literal (e.g. `100u`, `0.7482u`) in
        `self.params[key]` to micrometres."""
        raw = self.params[key]
        match = re.match(r"^([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)([a-zA-Z]*)$", raw)
        if match is None:
            raise ValueError(f"{self.name}.{key}={raw!r} is not a plain numeric literal")
        mantissa = float(match.group(1))
        suffix = match.group(2).lower()
        multipliers = {
            "meg": 1e6,
            "t": 1e12,
            "g": 1e9,
            "k": 1e3,
            "m": 1e-3,
            "u": 1e-6,
            "n": 1e-9,
            "p": 1e-12,
            "f": 1e-15,
            "a": 1e-18,
            "": 1.0,
        }
        mult = 1.0
        for name, value in sorted(multipliers.items(), key=lambda kv: -len(kv[0])):
            if suffix.startswith(name):
                mult = value
                break
        return mantissa * mult * 1e6

    def param_int(self, key: str) -> int:
        return int(float(self.params[key]))


def _merge_continuations(lines: list[str]) -> list[str]:
    logical: list[str] = []
    for raw in lines:
        if raw.lstrip().startswith("+") and logical:
            logical[-1] = f"{logical[-1]} {raw.lstrip()[1:].strip()}"
        else:
            logical.append(raw)
    return logical


def _tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    current: list[str] = []
    depth = 0
    quote: str | None = None
    for char in text:
        if quote is not None:
            current.append(char)
            if char == quote:
                quote = None
            continue
        if char in "'\"":
            quote = char
            current.append(char)
            continue
        if char in "{(":
            depth += 1
            current.append(char)
            continue
        if char in "})":
            depth = max(0, depth - 1)
            current.append(char)
            continue
        if char.isspace() and depth == 0:
            if current:
                tokens.append("".join(current))
                current = []
            continue
        current.append(char)
    if current:
        tokens.append("".join(current))
    return tokens


def _subckt_header(stripped: str) -> list[str] | None:
    """Split a `.subckt <name> <pins...>` header into its tokens, accepting
    xschem's own **commented** spelling of the *top-level* block.

    A hierarchical xschem export writes the top cell's own header/footer as
    `**.subckt rcosc_top ...` / `**.ends` -- commented out, because the top
    cell is emitted as a flat deck rather than a callable subcircuit. Its
    device lines are ordinary, uncommented cards in that commented block, so
    treating the commented header as a real one is what lets the same parser
    read `rcosc_top` and its sub-blocks (issue #27)."""
    low = stripped.lower()
    for prefix in (".subckt ", "**.subckt "):
        if low.startswith(prefix):
            return stripped[len(prefix) :].split()
    return None


def _is_subckt_end(stripped: str) -> bool:
    low = stripped.lower()
    return low.startswith(".ends") or low.startswith("**.ends")


def parse_subckt_pins(netlist_text: str, subckt_name: str) -> list[str]:
    """Return the ordered pin list from `.subckt <subckt_name> <pins...>`.

    Needed by the top-level composition (issue #27) to map a sub-block
    instance's positional nodes onto that block's own pin names -- so a
    schematic pin reorder shows up as a build failure rather than as silently
    swapped layout connections."""
    for line in _merge_continuations(netlist_text.splitlines()):
        tokens = _subckt_header(line.strip())
        if tokens and tokens[0] == subckt_name:
            return tokens[1:]
    raise KeyError(f".subckt {subckt_name} not found")


def parse_subckt(netlist_text: str, subckt_name: str) -> dict[str, Device]:
    """Return `{device_name: Device}` for every `X...` device-call line
    inside `.subckt <subckt_name> ... .ends` (case-insensitive on the
    directive, exact-case on `subckt_name`, matching this repo's netlist
    convention of lowercase subckt names; xschem's commented `**.subckt`
    top-level header counts, see `_subckt_header`)."""
    lines = _merge_continuations(netlist_text.splitlines())
    devices: dict[str, Device] = {}
    in_block = False
    for line in lines:
        stripped = line.strip()
        header = _subckt_header(stripped)
        if header is not None:
            in_block = header[0] == subckt_name
            continue
        if _is_subckt_end(stripped):
            in_block = False
            continue
        if not in_block or not stripped or stripped.startswith("*"):
            continue
        if stripped[0] not in "Xx":
            continue
        tokens = _tokenize(stripped)
        name = tokens[0]
        positional: list[str] = []
        params: dict[str, str] = {}
        for tok in tokens[1:]:
            if "=" in tok:
                key, _, value = tok.partition("=")
                params[key.strip().lower()] = value.strip()
            else:
                positional.append(tok)
        model = positional[-1]
        nodes = positional[:-1]
        devices[name] = Device(name=name, nodes=nodes, model=model, params=params)
    return devices
