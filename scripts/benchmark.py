"""Benchmark random SQLite IP range lookups."""

from __future__ import annotations

import argparse
import random
import sqlite3
import statistics
import time
from pathlib import Path
from urllib.parse import quote

LOOKUP_SQL = """
SELECT ip_from, ip_to
FROM ip_ranges
WHERE ip_from <= ?
ORDER BY ip_from DESC
LIMIT 1;
"""


def database_uri(path: Path) -> str:
    """Build an immutable read-only SQLite URI."""

    return f"file:{quote(path.resolve().as_posix(), safe='/:')}?mode=ro&immutable=1"


def run_benchmark(database: Path, count: int) -> dict[str, float]:
    """Perform random lookups and return latency metrics."""

    if count <= 0:
        raise ValueError("count must be greater than zero")

    latencies_ms: list[float] = []
    started = time.perf_counter()
    with sqlite3.connect(database_uri(database), uri=True) as connection:
        connection.execute("PRAGMA query_only=ON;")
        connection.execute("PRAGMA mmap_size=268435456;")
        connection.execute("PRAGMA cache_size=-32768;")
        for _ in range(count):
            ip_number = random.randint(0, 4_294_967_295)
            item_started = time.perf_counter_ns()
            row = connection.execute(LOOKUP_SQL, (ip_number,)).fetchone()
            if row is not None and ip_number > int(row[1]):
                row = None
            _ = row
            latencies_ms.append((time.perf_counter_ns() - item_started) / 1_000_000)
    elapsed = time.perf_counter() - started
    sorted_latencies = sorted(latencies_ms)
    return {
        "average_ms": statistics.fmean(latencies_ms),
        "median_ms": statistics.median(latencies_ms),
        "p95_ms": percentile(sorted_latencies, 95),
        "p99_ms": percentile(sorted_latencies, 99),
        "lookups_per_second": count / elapsed,
    }


def percentile(sorted_values: list[float], percent: int) -> float:
    """Return a nearest-rank percentile from an already sorted list."""

    index = min(len(sorted_values) - 1, max(0, round((percent / 100) * len(sorted_values) + 0.5) - 1))
    return sorted_values[index]


def main() -> None:
    """Run the benchmark command."""

    parser = argparse.ArgumentParser(description="Benchmark random IP range lookups.")
    parser.add_argument("--database", default=Path("data/ip2location.sqlite"), type=Path)
    parser.add_argument("--count", default=10_000, type=int)
    args = parser.parse_args()

    metrics = run_benchmark(args.database, args.count)
    print(f"Lookups: {args.count:,}")
    print(f"Average latency: {metrics['average_ms']:.4f} ms")
    print(f"Median latency: {metrics['median_ms']:.4f} ms")
    print(f"P95 latency: {metrics['p95_ms']:.4f} ms")
    print(f"P99 latency: {metrics['p99_ms']:.4f} ms")
    print(f"Lookups per second: {metrics['lookups_per_second']:.2f}")


if __name__ == "__main__":
    main()

