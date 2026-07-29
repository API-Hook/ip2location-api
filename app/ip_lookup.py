"""IPv4 validation, classification, and SQLite-backed geolocation lookup."""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from typing import Any

from .database import DatabaseUnavailableError, SQLiteDatabase

SOURCE_NAME = "IP2Location LITE DB5"
MAX_IP_LENGTH = 64


class LookupErrorResponse(Exception):
    """Domain error that maps directly to an API error response."""

    def __init__(self, status_code: int, error: str, message: str) -> None:
        self.status_code = status_code
        self.error = error
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class ParsedIp:
    """Normalized IP address and classification."""

    text: str
    number: int
    version: int
    is_public: bool


def parse_ipv4(value: str, allow_non_public: bool) -> ParsedIp:
    """Normalize and validate an IPv4 string."""

    candidate = value.strip()
    if not candidate or len(candidate) > MAX_IP_LENGTH:
        raise LookupErrorResponse(
            400,
            "invalid_ip",
            "The supplied value is not a valid IP address.",
        )

    try:
        ip = ipaddress.ip_address(candidate)
    except ValueError as exc:
        raise LookupErrorResponse(
            400,
            "invalid_ip",
            "The supplied value is not a valid IP address.",
        ) from exc

    if ip.version == 6:
        raise LookupErrorResponse(
            422,
            "ipv6_not_supported",
            "This database currently supports IPv4 only.",
        )

    ipv4 = ipaddress.IPv4Address(ip)
    is_public = ipv4.is_global
    if not is_public and not allow_non_public:
        raise LookupErrorResponse(
            403,
            "non_public_ip",
            "Private and non-public IP addresses are not supported.",
        )

    return ParsedIp(text=str(ipv4), number=int(ipv4), version=4, is_public=is_public)


def lookup_ip(value: str, database: SQLiteDatabase, allow_non_public: bool) -> dict[str, Any]:
    """Validate an IP address, perform an indexed SQLite lookup, and format the response."""

    parsed = parse_ipv4(value, allow_non_public=allow_non_public)
    try:
        row = database.lookup_range(parsed.number)
    except DatabaseUnavailableError as exc:
        raise LookupErrorResponse(
            503,
            "database_unavailable",
            "The geolocation database is missing or unavailable.",
        ) from exc

    if row is None or parsed.number > int(row["ip_to"]):
        raise LookupErrorResponse(
            404,
            "not_found",
            "The IP address was not found in the database.",
        )

    ip_from = int(row["ip_from"])
    ip_to = int(row["ip_to"])
    return {
        "ip": parsed.text,
        "ipNumber": parsed.number,
        "ipVersion": parsed.version,
        "isPublic": parsed.is_public,
        "range": {
            "from": str(ipaddress.IPv4Address(ip_from)),
            "to": str(ipaddress.IPv4Address(ip_to)),
            "fromNumber": ip_from,
            "toNumber": ip_to,
        },
        "countryCode": row["country_code"],
        "countryName": row["country_name"],
        "regionName": row["region_name"],
        "cityName": row["city_name"],
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "source": SOURCE_NAME,
    }

