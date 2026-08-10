#!/usr/bin/env python3
"""Hermes PM role wrapper for the Momo lane-gate CLI."""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SKILL_BIN = _REPO_ROOT / "momo" / "skill" / "scripts"
sys.path.insert(0, str(_SKILL_BIN / "lib"))

from momo_lane_gate import main  # type: ignore[import]  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
