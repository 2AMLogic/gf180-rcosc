# gf180-rcosc — agent instructions

Open-source canary block: a free-running, digitally trimmable RC oscillator
on GlobalFoundries gf180mcu, a 180 nm open PDK, designed and verified by AI
agents.

- **PDK**: GlobalFoundries gf180mcu (open PDK, fully supported plain CMOS).
  Open-source flow: xschem + ngspice for design/sim, klayout-tools (`klt`)
  for layout work.
- **This is a new block, not a port.** The fleet's existing clocking canaries
  are PLLs; no sibling repo covers a trimmable free-running oscillator. The
  sibling analog canaries (`gf180-bandgap`, `gf180-temp-por`) are the style
  reference — follow their spec, decision-record, and evidence conventions —
  but do not copy circuits from them; the topology decision starts here.
- **What the block is**: an internal RC-based clock source with a digital
  trim interface. Not a crystal oscillator, not a PLL. The anchor accuracy
  class is the one shipped MCUs use for crystal-less full-speed USB:
  post-trim accuracy plus optional runtime discipline from an external
  timing reference (e.g. USB start-of-frame timing). Cite only public
  precedents — vendor datasheets and app notes (e.g. ST's clock-recovery-
  system peripheral, Silicon Labs' crystal-less USB parts) and the USB 2.0
  spec's frequency-tolerance clauses.
- **Friction protocol (the canary's job)**: every time klayout-tools is
  awkward, missing a capability, or wrong for what you need, file an issue at
  `2AMLogic/klayout-tools` describing the tool gap generically — that tracker
  is scoped to the tool, so keep design-specific detail out of it and describe
  the gap, not the design.
- **Verification is the product**: no claim without a testbench. A frequency
  accuracy claim requires both the PVT-corner spread *and* trim-range /
  trim-resolution evidence — an oscillator spec without its trim math is not
  a spec. `sim/` results are append-only evidence.
- Spec changes go through `spec/` with a decision record; agents do not relax
  the ratified spec to make results pass.

<!-- BEGIN LOOM ORCHESTRATION -->
This repository uses [Loom](https://github.com/rjwalters/loom) for AI-powered development orchestration — see the Loom repository for the full guide (roles, labels, worktrees, configuration). When installed, Loom also writes a locally-substituted copy of that guide to `.loom/CLAUDE.md`.
<!-- END LOOM ORCHESTRATION -->
