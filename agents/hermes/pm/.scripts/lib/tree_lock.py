"""Shim to the canonical Momo tree-lock library."""
import sys
from pathlib import Path

_SKILL_LIB = Path(__file__).resolve().parents[4] / "momo" / "skill" / "scripts" / "lib"
sys.path.insert(0, str(_SKILL_LIB))

from momo_tree_lock import (  # type: ignore[import]  # noqa: E402,F401
    DEFAULT_TTL_SECONDS,
    TreeLockError,
    TreeLockRecord,
    TreeLockedError,
    acquire,
    default_lockfile,
    guard,
    refresh,
    release,
    status,
)
