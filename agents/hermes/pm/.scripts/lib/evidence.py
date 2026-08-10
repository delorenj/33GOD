"""Shim to the canonical Momo evidence-capture library."""
import sys
from pathlib import Path

_SKILL_LIB = Path(__file__).resolve().parents[4] / "momo" / "skill" / "scripts" / "lib"
sys.path.insert(0, str(_SKILL_LIB))

from momo_evidence import (  # type: ignore[import]  # noqa: E402,F401
    Baseline,
    EvidenceError,
    baseline_path,
    capture,
    evidence_path,
    gather_mutation_metrics,
    load_baseline,
    render_evidence,
    save_baseline,
)
