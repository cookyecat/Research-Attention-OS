from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "eval/live/results/phase12d_multi_actor_dogfood_v0_1"


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _post(client: httpx.Client, path: str, payload: dict | None = None) -> dict:
    response = client.post(path, json=payload)
    response.raise_for_status()
    return response.json()


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 12D controlled localhost multi-actor dogfood")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000/agent/v1")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    topic = f"Phase12D Shared Arbitration Dogfood {stamp}"
    actor_a = "phase12d-dogfood-agent-a"
    actor_b = "phase12d-dogfood-agent-b"

    with httpx.Client(base_url=args.api_base, timeout=30.0) as client:
        capabilities = client.get("/capabilities")
        capabilities.raise_for_status()
        contract = capabilities.json().get("authority_contract") or {}
        first = _post(client, "/watch", {
            "actor_id": actor_a,
            "topic": topic,
            "target_type": "TREND",
            "active_acquisition": False,
        })
        second = _post(client, "/watch", {
            "actor_id": actor_b,
            "topic": topic.casefold(),
            "target_type": "TREND",
            "active_acquisition": False,
        })
        watch_id = first["watch"]["id"]
        cancel_a = _post(client, f"/watch/{watch_id}/cancel", {"actor_id": actor_a})
        cancel_b = _post(client, f"/watch/{watch_id}/cancel", {"actor_id": actor_b})
        final = client.get(f"/watch/{watch_id}")
        final.raise_for_status()
        final = final.json()

    checks = {
        "single_attention_authority": contract.get("attention_authority") == "canonical_raos_only",
        "agent_cannot_assign_attention": contract.get("agent_interface_may_assign_attention") is False,
        "same_canonical_watch": first["watch"]["id"] == second["watch"]["id"],
        "second_reused_shared_watch": second.get("shared_watch_reused") is True,
        "two_active_delegations_after_join": second["watch"].get("delegation_count") == 2,
        "cancel_a_preserves_watch": cancel_a["watch"]["status"] == "ACTIVE",
        "one_delegation_remains": cancel_a.get("remaining_active_delegations") == 1,
        "cancel_b_releases_agent_only_watch": cancel_b["watch"]["status"] == "CANCELLED",
        "no_delegation_remains": cancel_b.get("remaining_active_delegations") == 0,
        "final_watch_cancelled": final["watch"]["status"] == "CANCELLED",
        "no_external_acquisition_used": first.get("active_acquisition") is None and second.get("active_acquisition") is None,
    }
    passed = all(checks.values())
    out = {
        "phase": "12D",
        "instrument": "multi-actor-dogfood-v0.1",
        "timestamp_utc": stamp,
        "git_sha": _git_sha(),
        "topic": topic,
        "actors": [actor_a, actor_b],
        "watch_id": watch_id,
        "checks": checks,
        "pass": passed,
        "guardrails": [
            "Localhost Agent API only.",
            "Active Acquisition disabled; no external retrieval is needed for this arbitration smoke.",
            "Declared actor ids are provenance, not authentication or Attention authority.",
        ],
        "observed": {
            "first": first,
            "second": second,
            "cancel_a": cancel_a,
            "cancel_b": cancel_b,
            "final": final,
        },
    }
    args.output_root.mkdir(parents=True, exist_ok=True)
    path = args.output_root / f"phase12d_multi_actor_dogfood_v0.1_{stamp}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    print(f"pass={passed}")
    print(f"artifact={path.relative_to(ROOT)}")
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
