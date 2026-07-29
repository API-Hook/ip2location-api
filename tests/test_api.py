from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def make_client(database: Path, **overrides: object) -> TestClient:
    settings = Settings(
        database_path=database,
        rate_limit_requests=overrides.pop("rate_limit_requests", 100),
        rate_limit_window_seconds=overrides.pop("rate_limit_window_seconds", 60),
        trust_proxy=overrides.pop("trust_proxy", False),
        allow_non_public_ips=overrides.pop("allow_non_public_ips", False),
        cors_origins=["*"],
    )
    return TestClient(create_app(settings=settings))


def test_lookup_endpoint(sample_database: Path) -> None:
    client = make_client(sample_database)
    response = client.get("/api/v1/lookup", params={"ip": "8.8.8.8"})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "public, max-age=86400"
    assert response.json()["countryName"] == "United States"


def test_lookup_path_endpoint(sample_database: Path) -> None:
    client = make_client(sample_database)
    response = client.get("/api/v1/lookup/8.8.8.8")
    assert response.status_code == 200
    assert response.json()["ip"] == "8.8.8.8"


def test_invalid_ip_endpoint(sample_database: Path) -> None:
    client = make_client(sample_database)
    response = client.get("/api/v1/lookup", params={"ip": "bad"})
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_ip"


def test_missing_database(tmp_path: Path) -> None:
    client = make_client(tmp_path / "missing.sqlite")
    response = client.get("/api/v1/lookup", params={"ip": "8.8.8.8"})
    assert response.status_code == 503
    assert response.json()["error"] == "database_unavailable"


def test_health_endpoint(sample_database: Path) -> None:
    client = make_client(sample_database)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ready", "ipv4Only": True}


def test_frontend_response(sample_database: Path) -> None:
    client = make_client(sample_database)
    response = client.get("/")
    assert response.status_code == 200
    assert "Free Offline IP Geolocation" in response.text


def test_rate_limit(sample_database: Path) -> None:
    client = make_client(sample_database, rate_limit_requests=2, rate_limit_window_seconds=60)
    assert client.get("/health").status_code == 200
    assert client.get("/health").status_code == 200
    response = client.get("/health")
    assert response.status_code == 429
    assert response.json()["error"] == "rate_limited"


def test_me_without_trusted_proxy(sample_database: Path) -> None:
    client = make_client(sample_database, trust_proxy=False)
    response = client.get("/api/v1/me", headers={"X-Forwarded-For": "1.1.1.1"})
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_ip"


def test_me_with_trusted_proxy(sample_database: Path) -> None:
    client = make_client(sample_database, trust_proxy=True)
    response = client.get("/api/v1/me", headers={"X-Forwarded-For": "1.1.1.1, 203.0.113.1"})
    assert response.status_code == 200
    assert response.json()["ip"] == "1.1.1.1"
    assert response.json()["countryCode"] == "AU"
