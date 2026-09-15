from __future__ import annotations

import argparse
import json
import os
import sys
from uuid import UUID

import httpx

DEFAULT_API_BASE = os.getenv(
    "RAOS_AGENT_API_BASE", "http://127.0.0.1:8000/agent/v1"
).rstrip("/")
DEFAULT_ACTOR_ID = os.getenv("RAOS_AGENT_ACTOR_ID", "agent-default")


def _client(args) -> httpx.Client:
    return httpx.Client(base_url=args.api_base, timeout=args.timeout)


def _request(args, method: str, path: str, *, payload: dict | None = None):
    try:
        with _client(args) as client:
            response = client.request(method, path, json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        body = exc.response.text.strip()
        raise SystemExit(f"RAOS API {exc.response.status_code}: {body[:500]}") from exc
    except httpx.HTTPError as exc:
        raise SystemExit(f"Cannot reach RAOS at {args.api_base}: {exc}") from exc


def _print_plan(row: dict) -> None:
    source = row.get("source") or {}
    title = source.get("title") or row.get("candidate_id")
    print(f"[{row.get('disposition')}] {title}")
    print(f"  urgency: {row.get('urgency')} · output: {row.get('expected_output')}")
    if row.get("reason"):
        print(f"  {row['reason']}")
    if source.get("canonical_url"):
        print(f"  {source['canonical_url']}")


def _print_watch(row: dict) -> None:
    print(f"[{row.get('status')}] {row.get('target_ref')}")
    print(f"  id: {row.get('id')} · type: {row.get('target_type')}")
    checks = row.get("checks") or []
    if checks:
        latest = checks[-1]
        print(f"  latest: {latest.get('disposition')} / {latest.get('outcome')}")


def _emit(args, data: dict) -> None:
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    command = args.command
    if command == "capabilities":
        print("RAOS Agent Interface", data.get("version"))
        contract = data.get("authority_contract") or {}
        print("attention authority:", contract.get("attention_authority"))
        for name, desc in (data.get("commands") or {}).items():
            print(f"  {name:12} {desc}")
    elif command == "today":
        items = data.get("items") or []
        print(f"Today: {len(items)} item(s) need human-visible attention")
        for row in items:
            _print_plan(row)
        watches = data.get("delegated_watches") or []
        print(f"Delegated WATCH responsibilities: {data.get('delegated_watch_count', len(watches))}")
        for row in watches[:10]:
            _print_watch(row)
    elif command == "attention":
        items = data.get("items") or []
        print(f"Attention states: {len(items)}")
        for row in items:
            _print_plan(row)
    elif command == "watch":
        _print_watch(data["watch"])
        delegation = data.get("delegation") or {}
        if delegation:
            print(f"  delegation: {delegation.get('declared_actor_id')} · {delegation.get('status')}")
        acquisition = data.get("active_acquisition")
        if acquisition:
            print("  active acquisition: enabled")
    elif command in {"watch-status", "unwatch"}:
        _print_watch(data["watch"])
        if command == "unwatch":
            cancelled = data.get("cancelled_delegation") or {}
            if cancelled:
                print("  cancelled delegation:", cancelled.get("declared_actor_id"))
            print("  remaining delegations:", data.get("remaining_active_delegations"))
            print("  active acquisition disabled:", data.get("active_acquisition_disabled"))
    elif command == "why":
        source = data.get("source") or {}
        decision = data.get("decision") or {}
        print(f"Why: {source.get('title') or source.get('id')}")
        print(f"  {decision.get('disposition')} / {decision.get('urgency')}")
        print(f"  {decision.get('reason')}")
        if decision.get("delta_content"):
            print(f"  delta: {decision.get('delta_content')}")
        print("  reanalysis performed:", data.get("reanalysis_performed"))
    elif command == "analyze":
        source = data.get("source") or {}
        plan = (data.get("analysis") or {}).get("attention_plan") or {}
        print(f"Analyzed: {source.get('title') or source.get('id')}")
        print(f"  disposition: {plan.get('disposition')} · urgency: {plan.get('urgency')}")
        print(f"  reason: {plan.get('reason')}")
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))


def _is_uuid(value: str) -> bool:
    try:
        UUID(value)
        return True
    except ValueError:
        return False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="raos", description="RAOS Agent Interface CLI")
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--actor-id", default=DEFAULT_ACTOR_ID, help="Declared Agent provenance id (not authentication)")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("capabilities")
    sub.add_parser("today")
    attention = sub.add_parser("attention")
    attention.add_argument("--exclude-drop", action="store_true")

    analyze = sub.add_parser("analyze")
    analyze.add_argument("target", help="URL or existing Source UUID")
    analyze.add_argument("--reprocess", action="store_true")

    watch = sub.add_parser("watch")
    watch.add_argument("topic")
    watch.add_argument("--type", dest="target_type", default="TREND")
    watch.add_argument("--reason", default="Delegated through the RAOS Agent Interface CLI.")
    watch.add_argument("--trigger", action="append", default=[])
    watch.add_argument("--no-active-acquisition", action="store_true")
    status = sub.add_parser("watch-status")
    status.add_argument("watch_id")
    unwatch = sub.add_parser("unwatch")
    unwatch.add_argument("watch_id")
    why = sub.add_parser("why")
    why.add_argument("source_id")
    return parser


def _dispatch(args):
    if args.command == "capabilities":
        return _request(args, "GET", "/capabilities")
    if args.command == "today":
        return _request(args, "GET", "/today")
    if args.command == "attention":
        flag = "false" if args.exclude_drop else "true"
        return _request(args, "GET", f"/attention?include_drop={flag}")
    if args.command == "analyze":
        payload = {"reprocess": args.reprocess}
        if _is_uuid(args.target):
            payload["source_id"] = args.target
        else:
            payload["url"] = args.target
        return _request(args, "POST", "/analyze", payload=payload)
    if args.command == "watch":
        payload = {
            "actor_id": args.actor_id,
            "topic": args.topic,
            "target_type": args.target_type,
            "reason": args.reason,
            "triggers": args.trigger or ["NEW_EVIDENCE"],
            "active_acquisition": not args.no_active_acquisition,
        }
        return _request(args, "POST", "/watch", payload=payload)
    if args.command == "watch-status":
        return _request(args, "GET", f"/watch/{args.watch_id}")
    if args.command == "unwatch":
        return _request(args, "POST", f"/watch/{args.watch_id}/cancel", payload={"actor_id": args.actor_id})
    if args.command == "why":
        return _request(args, "GET", f"/why/{args.source_id}")
    raise SystemExit(f"Unsupported command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    data = _dispatch(args)
    _emit(args, data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
