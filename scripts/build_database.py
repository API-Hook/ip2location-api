"""Build an indexed SQLite database from an IP2Location DB5 CSV file."""

from __future__ import annotations

import argparse
import csv
import logging
import sqlite3
import time
from pathlib import Path
from typing import Iterable

from inspect_csv import COMMON_DB5_FIELDS, CsvLayout, inspect_csv

BATCH_SIZE = 10_000
PROGRESS_EVERY = 100_000

logger = logging.getLogger("build_database")

SCHEMA = """
DROP TABLE IF EXISTS ip_ranges;

CREATE TABLE ip_ranges (
    ip_from INTEGER PRIMARY KEY,
    ip_to INTEGER NOT NULL,
    country_code TEXT,
    country_name TEXT,
    region_name TEXT,
    city_name TEXT,
    latitude REAL,
    longitude REAL,
    CHECK (ip_from >= 0),
    CHECK (ip_to >= ip_from)
);

CREATE INDEX idx_ip_ranges_ip_to
ON ip_ranges(ip_to);
"""

INSERT_SQL = """
INSERT INTO ip_ranges (
    ip_from,
    ip_to,
    country_code,
    country_name,
    region_name,
    city_name,
    latitude,
    longitude
) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
"""


def parse_float(value: str) -> float | None:
    """Parse a floating point value, accepting empty strings as null."""

    stripped = value.strip()
    if stripped == "":
        return None
    return float(stripped)


def validate_row(row: list[str], layout: CsvLayout) -> tuple[int, int, str, str, str, str, float | None, float | None] | None:
    """Validate and normalize one CSV row into a database record."""

    if len(row) < len(COMMON_DB5_FIELDS):
        return None
    try:
        values = dict(zip(layout.field_order, row, strict=False))
        ip_from = int(values["ip_from"])
        ip_to = int(values["ip_to"])
        if ip_from < 0 or ip_to < ip_from or ip_to > 4_294_967_295:
            return None
        return (
            ip_from,
            ip_to,
            values.get("country_code", "").strip(),
            values.get("country_name", "").strip(),
            values.get("region_name", "").strip(),
            values.get("city_name", "").strip(),
            parse_float(values.get("latitude", "")),
            parse_float(values.get("longitude", "")),
        )
    except (KeyError, TypeError, ValueError):
        return None


def apply_import_pragmas(connection: sqlite3.Connection) -> None:
    """Apply SQLite settings optimized for a one-time bulk import."""

    connection.execute("PRAGMA journal_mode=OFF;")
    connection.execute("PRAGMA synchronous=OFF;")
    connection.execute("PRAGMA temp_store=MEMORY;")
    connection.execute("PRAGMA locking_mode=EXCLUSIVE;")
    connection.execute("PRAGMA cache_size=-65536;")


def insert_batch(connection: sqlite3.Connection, batch: Iterable[tuple[object, ...]]) -> int:
    """Insert a batch, falling back to row-by-row insertion on rare constraint errors."""

    records = list(batch)
    if not records:
        return 0
    try:
        connection.executemany(INSERT_SQL, records)
        return 0
    except sqlite3.IntegrityError:
        invalid = 0
        for record in records:
            try:
                connection.execute(INSERT_SQL, record)
            except sqlite3.IntegrityError:
                invalid += 1
        return invalid


def build_database(input_path: Path, output_path: Path) -> tuple[int, int, float]:
    """Stream a DB5 CSV into a compact indexed SQLite database."""

    started = time.perf_counter()
    layout, _ = inspect_csv(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    total = 0
    invalid = 0
    batch: list[tuple[object, ...]] = []

    with sqlite3.connect(output_path) as connection:
        apply_import_pragmas(connection)
        connection.executescript(SCHEMA)
        connection.execute("BEGIN;")
        with input_path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.reader(file, delimiter=layout.delimiter)
            if layout.has_header:
                next(reader, None)
            for row in reader:
                record = validate_row(row, layout)
                if record is None:
                    invalid += 1
                    continue
                batch.append(record)
                if len(batch) >= BATCH_SIZE:
                    batch_invalid = insert_batch(connection, batch)
                    invalid += batch_invalid
                    total += len(batch) - batch_invalid
                    batch.clear()
                    if total % PROGRESS_EVERY == 0:
                        print(f"Imported {total:,} rows; invalid skipped: {invalid:,}")
            if batch:
                batch_invalid = insert_batch(connection, batch)
                invalid += batch_invalid
                total += len(batch) - batch_invalid
                batch.clear()
        connection.commit()
        connection.execute("ANALYZE;")
        connection.commit()
        connection.execute("VACUUM;")

    elapsed = time.perf_counter() - started
    return total, invalid, elapsed


def main() -> None:
    """Run the database build command."""

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Build SQLite database from IP2Location DB5 CSV.")
    parser.add_argument("--input", required=True, type=Path, help="Path to IP2Location DB5 CSV.")
    parser.add_argument("--output", required=True, type=Path, help="Path to output SQLite database.")
    args = parser.parse_args()

    total, invalid, elapsed = build_database(args.input, args.output)
    size = args.output.stat().st_size if args.output.exists() else 0
    print(f"Total records: {total:,}")
    print(f"Invalid records: {invalid:,}")
    print(f"Database file size: {size:,} bytes")
    print(f"Total build time: {elapsed:.2f} seconds")


if __name__ == "__main__":
    main()
