"""Shim to the canonical Momo hand-back library.

The canonical implementation lives in momo/skill/scripts/lib/momo_handback.py.
This file re-exports it so Hermes PM role scripts can import a stable name.
"""
import sys
from pathlib import Path

_SKILL_LIB = Path(__file__).resolve().parents[4] / "momo" / "skill" / "scripts" / "lib"
sys.path.insert(0, str(_SKILL_LIB))

from momo_handback import (  # type: ignore[import]  # noqa: E402,F401
    Checks,
    GitPointer,
    HandbackBundle,
    HandbackError,
    HandbackValidationError,
    Heartbeat,
    RetryState,
    WorkerIdentity,
    bundle_path,
    collect_git_pointer,
    default_spool,
    finalize,
    is_stale,
    load,
    next_retry_wait,
    repo_root,
    save,
    write_diff,
)
