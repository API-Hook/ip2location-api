from pathlib import Path

import pytest

from app.database import SQLiteDatabase
from app.ip_lookup import LookupErrorResponse, lookup_ip


def test_valid_ipv4(sample_database: Path) -> None:
    result = lookup_ip("8.8.8.8", SQLiteDatabase(sample_database), allow_non_public=False)
    assert result["countryCode"] == "US"
    assert result["range"]["from"] == "8.8.8.0"
    assert result["range"]["to"] == "8.8.8.255"


def test_exact_ip_from_boundary(sample_database: Path) -> None:
    result = lookup_ip("8.8.8.0", SQLiteDatabase(sample_database), allow_non_public=False)
    assert result["ipNumber"] == 134744064


def test_exact_ip_to_boundary(sample_database: Path) -> None:
    result = lookup_ip("8.8.8.255", SQLiteDatabase(sample_database), allow_non_public=False)
    assert result["ipNumber"] == 134744319


def test_ip_outside_range(sample_database: Path) -> None:
    with pytest.raises(LookupErrorResponse) as exc_info:
        lookup_ip("8.8.9.1", SQLiteDatabase(sample_database), allow_non_public=False)
    assert exc_info.value.status_code == 404
    assert exc_info.value.error == "not_found"

