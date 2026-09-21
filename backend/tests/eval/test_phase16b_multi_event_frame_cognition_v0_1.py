from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.live.run_phase16b_multi_event_frame_cognition_v0_1 import run


def test_multi_event_source_frame_conditioning_separates_decisions():
    report = run()
    d = report["diagnostics"]

    assert d["frame_a_engage"] is True
    assert d["frame_b_drop"] is True
    assert d["whole_source_engage"] is True
    assert d["whole_source_masks_irrelevant_event"] is True
    assert d["frame_unit_sets_disjoint"] is True

    a = report["frames"]["A_PERFORMANCE"]
    b = report["frames"]["B_MEMORY_CHALLENGE"]
    assert len(a["authorized_effects"]) == 1
    assert a["authorized_effects"][0]["operation"] == "CHALLENGE"
    assert b["authorized_effects"] == []
