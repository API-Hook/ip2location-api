from pathlib import Path

import pytest

from app.database import SQLiteDatabase
from app.ip_lookup import LookupErrorResponse, lookup_ip


def assert_lookup_error(value: str, database: Path, status_code: int, code: str) -> None:
    with pytest.raises(LookupErrorResponse) as exc_info:
        lookup_ip(value, SQLiteDatabase(database), allow_non_public=False)
    assert exc_info.value.status_code == status_code
    assert exc_info.value.error == code


def test_invalid_ip(sample_database: Path) -> None:
    assert_lookup_error("not-an-ip", sample_database, 400, "invalid_ip")


def test_ipv6_rejection(sample_database: Path) -> None:
    assert_lookup_error("2001:4860:4860::8888", sample_database, 422, "ipv6_not_supported")


def test_private_ip_rejection(sample_database: Path) -> None:
    assert_lookup_error("10.0.0.1", sample_database, 403, "non_public_ip")


def test_loopback_rejection(sample_database: Path) -> None:
    assert_lookup_error("127.0.0.1", sample_database, 403, "non_public_ip")

