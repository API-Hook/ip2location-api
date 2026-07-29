import sqlite3
from pathlib import Path

import pytest


SCHEMA = """
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


@pytest.fixture()
def sample_database(tmp_path: Path) -> Path:
    database_path = tmp_path / "ip2location.sqlite"
    with sqlite3.connect(database_path) as connection:
        connection.executescript(SCHEMA)
        connection.executemany(
            """
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
            """,
            [
                (16843008, 16843263, "AU", "Australia", "Queensland", "Brisbane", -27.46754, 153.02809),
                (134744064, 134744319, "US", "United States", "California", "Mountain View", 37.4056, -122.0775),
            ],
        )
    return database_path

