"""Live dogfood comparison: legacy broad APIs vs bounded User Space v0.1."""
from pathlib import Path
import json
import statistics
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
BASE = "http://127.0.0.1:8000"
REPEATS = 10

ENDPOINTS = (
    ("legacy_sources", "/sources?compact=true"),
    ("user_inbox_30", "/user-space/inbox?limit=30"),
    ("legacy_attention_compact", "/kernel/attention?compact=true"),
    ("user_attention_30", "/user-space/attention?limit=30"),
    ("user_today", "/user-space/today"),
)


def fetch(path):
    started = time.perf_counter()
    with urllib.request.urlopen(BASE + path, timeout=20) as response:
        body = response.read()
    return (time.perf_counter() - started) * 1000.0, body


def pct(values, q):
    ordered = sorted(values)
    index = min(
        len(ordered) - 1,
        max(0, round((len(ordered) - 1) * q)),
    )
    return ordered[index]


def main():
    results = []
    for name, path in ENDPOINTS:
        cold_ms, cold_body = fetch(path)
        warm = []
        body = cold_body
        for _ in range(REPEATS):
            elapsed, body = fetch(path)
            warm.append(elapsed)

        decoded = json.loads(body)
        if isinstance(decoded, list):
            row_count = len(decoded)
        else:
            row_count = len(decoded.get("items") or [])
            if name == "user_today":
                row_count = (
                    (1 if decoded.get("lead") else 0)
                    + len(decoded.get("briefs") or [])
                )

        results.append(
            {
                "name": name,
                "path": path,
                "cold_ms": cold_ms,
                "warm_median_ms": statistics.median(warm),
                "warm_p95_ms": pct(warm, 0.95),
                "payload_bytes": len(body),
                "row_count": row_count,
            }
        )

    result = {
        "benchmark": "user-space-projection-dogfood-v0.1",
        "repeats": REPEATS,
        "results": results,
        "warning": (
            "Live localhost dogfood measurement. Existing in-process caches "
            "may serve legacy endpoints; this compares user-facing request "
            "shape/payload as well as latency."
        ),
    }
    output = (
        ROOT
        / "eval/live/results/user_space_projection_dogfood_v0_1"
        / "user_space_projection_dogfood_v0_1.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
