"""Synthetic scale diagnostic for RAOS User Space read-model queries.

This does not benchmark canonical cognition. It isolates the proposed read-path:
indexed materialized rows + keyset pagination + bounded payload.
"""
import json
import sqlite3
import statistics
import time


ROW_COUNTS = (10_000, 200_000)
REPEATS = 100
PAGE_SIZE = 50


def percentile(values, q):
    ordered = sorted(values)
    index = min(
        len(ordered) - 1,
        max(0, round((len(ordered) - 1) * q)),
    )
    return ordered[index]


def build_db(row_count):
    db = sqlite3.connect(":memory:")
    db.execute("""
        CREATE TABLE user_source_projection (
            surface_seq INTEGER PRIMARY KEY,
            user_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            event_id TEXT,
            disposition TEXT,
            title TEXT NOT NULL,
            publisher TEXT,
            excerpt TEXT
        )
    """)
    db.execute("""
        CREATE INDEX ix_user_source_surface
        ON user_source_projection(user_id, surface_seq DESC)
    """)
    db.execute("""
        CREATE INDEX ix_user_attention_surface
        ON user_source_projection(
            user_id,
            disposition,
            surface_seq DESC
        )
    """)

    dispositions = ("DROP", "AWARE", "WATCH", "ENGAGE")
    rows = (
        (
            seq,
            "u1",
            f"s{seq}",
            f"e{seq // 2}",
            dispositions[seq % len(dispositions)],
            f"Source title {seq}",
            "Publisher",
            "x" * 240,
        )
        for seq in range(1, row_count + 1)
    )
    db.executemany(
        """
        INSERT INTO user_source_projection(
            surface_seq, user_id, source_id, event_id,
            disposition, title, publisher, excerpt
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    db.commit()
    return db


def timed(db, sql, params):
    started = time.perf_counter()
    rows = db.execute(sql, params).fetchall()
    return (time.perf_counter() - started) * 1000.0, rows


def measure(row_count):
    build_started = time.perf_counter()
    db = build_db(row_count)
    build_ms = (time.perf_counter() - build_started) * 1000.0

    first_page_times = []
    aware_page_times = []
    cursor_page_times = []
    payload_sizes = []

    cursor = row_count - PAGE_SIZE
    for _ in range(REPEATS):
        elapsed, rows = timed(
            db,
            """
            SELECT surface_seq, source_id, event_id, disposition,
                   title, publisher, excerpt
            FROM user_source_projection
            WHERE user_id = ?
            ORDER BY surface_seq DESC
            LIMIT ?
            """,
            ("u1", PAGE_SIZE),
        )
        first_page_times.append(elapsed)
        payload_sizes.append(
            len(
                json.dumps(
                    rows,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
            )
        )

        elapsed, _ = timed(
            db,
            """
            SELECT surface_seq, source_id, event_id, disposition,
                   title, publisher, excerpt
            FROM user_source_projection
            WHERE user_id = ?
              AND disposition = ?
            ORDER BY surface_seq DESC
            LIMIT ?
            """,
            ("u1", "AWARE", PAGE_SIZE),
        )
        aware_page_times.append(elapsed)

        elapsed, _ = timed(
            db,
            """
            SELECT surface_seq, source_id, event_id, disposition,
                   title, publisher, excerpt
            FROM user_source_projection
            WHERE user_id = ?
              AND surface_seq < ?
            ORDER BY surface_seq DESC
            LIMIT ?
            """,
            ("u1", cursor, PAGE_SIZE),
        )
        cursor_page_times.append(elapsed)

    def stats(values):
        return {
            "median_ms": statistics.median(values),
            "p95_ms": percentile(values, 0.95),
            "max_ms": max(values),
        }

    result = {
        "row_count": row_count,
        "build_ms": build_ms,
        "first_page": stats(first_page_times),
        "aware_page": stats(aware_page_times),
        "cursor_page": stats(cursor_page_times),
        "page_payload_bytes_median": int(
            statistics.median(payload_sizes)
        ),
    }
    db.close()
    return result


def main():
    result = {
        "benchmark": "user-space-projection-scale-v0.1",
        "database": "SQLite in-memory synthetic read model",
        "page_size": PAGE_SIZE,
        "repeats": REPEATS,
        "results": [measure(n) for n in ROW_COUNTS],
        "warning": (
            "This isolates read-model query complexity and is not "
            "a production Postgres or end-to-end latency benchmark."
        ),
    }
    output = (
        __import__("pathlib").Path(__file__).resolve().parents[2]
        / "eval/live/results/user_space_projection_scale_v0_1"
        / "user_space_projection_scale_v0_1.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
