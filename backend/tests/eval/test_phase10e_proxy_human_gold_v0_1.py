from pathlib import Path

from eval.live.phase10e_proxy_human_gold_v0_1 import evaluate_case, load_manifest

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "eval/live/manifest.phase10e_proxy_human_gold.v0_1.json"


def test_proxy_manifest_is_explicitly_delegated_not_direct_user_gold() -> None:
    manifest = load_manifest(MANIFEST)
    assert manifest["label_author"] == "assistant_proxy_for_user"
    assert len(manifest["cases"]) == 10


def test_all_proxy_cases_are_deterministically_evaluable() -> None:
    manifest = load_manifest(MANIFEST)
    rows = [evaluate_case(case, i) for i, case in enumerate(manifest["cases"])]
    assert all(row["predicted_disposition"] in {"DROP", "AWARE", "WATCH", "ENGAGE"} for row in rows)
    assert all(row["strategy"]["strategy_id"].startswith("pareto-multidelta") for row in rows)
