"""Inspect an IP2Location DB5 CSV file without loading it into memory."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

COMMON_DB5_FIELDS = [
    "ip_from",
    "ip_to",
    "country_code",
    "country_name",
    "region_name",
    "city_name",
    "latitude",
    "longitude",
]


@dataclass(frozen=True)
class CsvLayout:
    """Detected CSV layout and DB5 field mapping."""

    delimiter: str
    has_header: bool
    column_count: int
    field_order: list[str]


def normalize_field(value: str) -> str:
    """Normalize a CSV header field for comparison."""

    return value.strip().strip('"').lower()


def detect_delimiter(sample: str) -> str:
    """Detect the delimiter used by a CSV sample."""

    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        return dialect.delimiter
    except csv.Error:
        return ","


def inspect_csv(path: Path, sample_rows: int = 5) -> tuple[CsvLayout, list[list[str]]]:
    """Inspect delimiter, header presence, column count, and field order."""

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        sample = file.read(8192)
        if not sample:
            raise ValueError("CSV file is empty")
        delimiter = detect_delimiter(sample)
        file.seek(0)
        reader = csv.reader(file, delimiter=delimiter)
        rows: list[list[str]] = []
        for _ in range(sample_rows):
            try:
                rows.append(next(reader))
            except StopIteration:
                break

    if not rows:
        raise ValueError("CSV file has no rows")

    first_row = [normalize_field(value) for value in rows[0]]
    common_prefix = COMMON_DB5_FIELDS[: len(first_row)]
    has_header = first_row == common_prefix or all(field in COMMON_DB5_FIELDS for field in first_row)
    column_count = len(rows[0])
    field_order = first_row if has_header else COMMON_DB5_FIELDS[:column_count]
    return CsvLayout(delimiter, has_header, column_count, field_order), rows


def format_row(row: Sequence[str]) -> str:
    """Return a compact printable CSV row."""

    return " | ".join(row)


def main() -> None:
    """Run the CSV inspector command."""

    parser = argparse.ArgumentParser(description="Inspect an IP2Location DB5 CSV file.")
    parser.add_argument("--input", required=True, type=Path, help="Path to the source CSV file.")
    parser.add_argument("--rows", default=5, type=int, help="Number of rows to preview.")
    args = parser.parse_args()

    layout, rows = inspect_csv(args.input, sample_rows=args.rows)
    print(f"Delimiter: {repr(layout.delimiter)}")
    print(f"Has header: {layout.has_header}")
    print(f"Columns: {layout.column_count}")
    print(f"Field order: {', '.join(layout.field_order)}")
    print("Preview:")
    for row in rows:
        print(f"  {format_row(row)}")


if __name__ == "__main__":
    main()

