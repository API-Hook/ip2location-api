"""Thread-local SQLite access for IP range lookup."""

from __future__ import annotations

import logging
import sqlite3
import threading
from pathlib import Path
from typing import Any
from urllib.parse import quote

logger = logging.getLogger(__name__)


class DatabaseUnavailableError(RuntimeError):
    """Raised when the SQLite database cannot be used."""


class SQLiteDatabase:
    """Read-only, immutable SQLite database with one connection per thread."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._local = threading.local()

    def exists(self) -> bool:
        """Return whether the configured database file exists."""

        return self.path.exists() and self.path.is_file()

    def file_size(self) -> int:
        """Return the database file size in bytes, or zero if missing."""

        if not self.exists():
            return 0
        return self.path.stat().st_size

    def status(self) -> str:
        """Return a compact status string for health checks."""

        return "ready" if self.exists() else "missing"

    def connect(self) -> sqlite3.Connection:
        """Return the current thread's configured SQLite connection."""

        connection = getattr(self._local, "connection", None)
        if connection is not None:
            return connection
        if not self.exists():
            raise DatabaseUnavailableError("database is missing")

        uri = self._build_uri()
        try:
            connection = sqlite3.connect(uri, uri=True, check_same_thread=False)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only=ON;")
            connection.execute("PRAGMA mmap_size=268435456;")
            connection.execute("PRAGMA cache_size=-32768;")
            self._local.connection = connection
            return connection
        except sqlite3.Error as exc:
            logger.warning("SQLite connection failed: %s", exc.__class__.__name__)
            raise DatabaseUnavailableError("database is unavailable") from exc

    def lookup_range(self, ip_number: int) -> dict[str, Any] | None:
        """Find the closest range whose lower bound is less than or equal to ip_number."""

        try:
            row = self.connect().execute(
                """
                SELECT
                    ip_from,
                    ip_to,
                    country_code,
                    country_name,
                    region_name,
                    city_name,
                    latitude,
                    longitude
                FROM ip_ranges
                WHERE ip_from <= ?
                ORDER BY ip_from DESC
                LIMIT 1;
                """,
                (ip_number,),
            ).fetchone()
        except sqlite3.Error as exc:
            logger.warning("SQLite lookup failed: %s", exc.__class__.__name__)
            raise DatabaseUnavailableError("database lookup failed") from exc

        if row is None:
            return None
        return dict(row)

    def close_current_thread(self) -> None:
        """Close the connection owned by the current thread, if any."""

        connection = getattr(self._local, "connection", None)
        if connection is not None:
            connection.close()
            self._local.connection = None

    def _build_uri(self) -> str:
        path = self.path.resolve().as_posix()
        encoded_path = quote(path, safe="/:")
        return f"file:{encoded_path}?mode=ro&immutable=1"

