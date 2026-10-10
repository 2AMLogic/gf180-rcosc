#!/usr/bin/env python3
"""CLI entry point; logic lives in netlist_consistency.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from netlist_consistency import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
