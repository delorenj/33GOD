"""Shim to the canonical Momo reporter library."""
import sys
from pathlib import Path

_SKILL_LIB = Path(__file__).resolve().parents[4] / "momo" / "skill" / "scripts" / "lib"
sys.path.insert(0, str(_SKILL_LIB))

from momo_reporter import (  # type: ignore[import]  # noqa: E402,F401
    ReportCommand,
    ReporterError,
    already_posted,
    load_log,
    post,
    reports_path,
    save_log,
)
