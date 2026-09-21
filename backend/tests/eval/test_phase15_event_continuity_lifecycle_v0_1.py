from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.live.run_phase15_event_continuity_lifecycle_v0_1 import run


def test_event_continuity_routes_existing_vs_new_lifecycle_without_conflating_same_event():
    report = run()
    d = report["diagnostics"]

    assert d["same_event_routes_existing_lifecycle"] is True
    assert d["distinct_same_actor_product_routes_new_path"] is True
    assert d["same_event_reuses_watch_identity"] is True

    # EventLineage is not yet consumed by the current continuous-attention router.
    assert d["lineage_only_routes_existing_lifecycle"] is False

    # The legacy Source-level contradiction proxy does route the successor case.
    assert d["source_proxy_routes_successor_existing_lifecycle"] is True
    assert d["successor_proxy_reuses_watch_identity"] is True

    assert d["same_event_processing_added_unexpected_event_membership"] is False
    assert d["successor_proxy_processing_added_unexpected_event_membership"] is False
