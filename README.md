# IP2Location API

[![CI](https://github.com/API-Hook/ip2location-api/actions/workflows/ci.yml/badge.svg)](https://github.com/API-Hook/ip2location-api/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/github/license/API-Hook/ip2location-api)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED.svg)](Dockerfile)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

A production-ready FastAPI service for offline IPv4 geolocation using IP2Location LITE DB5 data. The raw CSV is converted once into an indexed SQLite database, then runtime lookups use fast B-tree range queries with low memory overhead.

This project is useful when you want a self-hosted IP lookup API without calling a third-party geolocation service on every request.

## Features

- Offline IPv4 geolocation from IP2Location LITE DB5 data.
- Fast SQLite range lookup with an index on `ip_from`.
- No Pandas, no full CSV scans, and no full database load into Python memory.
- JSON API, static demo page, CORS support, cache headers, and security headers.
- Optional rate limiting and trusted proxy support.
- Docker-ready runtime using one Uvicorn worker by default for small servers.
- Tests use a temporary SQLite fixture, so CI does not need the full IP2Location database.

## Requirements

- Python 3.12+
- IP2Location LITE DB5 CSV from [lite.ip2location.com](https://lite.ip2location.com)
- Docker, optional

The generated SQLite file and source CSV are not committed because they are large data artifacts and have separate data licensing terms.

## Quick Start

Clone the repository:

```bash
git clone https://github.com/API-Hook/ip2location-api.git
cd ip2location-api
```

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Download and extract the IP2Location LITE DB5 CSV, then place it at:

```text
data/IP2LOCATION-LITE-DB5.CSV
```

Build the SQLite database:

```bash
python scripts/build_database.py --input data/IP2LOCATION-LITE-DB5.CSV --output data/ip2location.sqlite
```

Run the API:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

Open:

```text
http://127.0.0.1:8000
```

## API Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Service and database health |
| `GET` | `/api/v1/lookup?ip=8.8.8.8` | Lookup by query parameter |
| `GET` | `/api/v1/lookup/8.8.8.8` | Lookup by path parameter |
| `GET` | `/api/v1/me` | Lookup the caller IP |

Example:

```bash
curl "http://127.0.0.1:8000/api/v1/lookup?ip=8.8.8.8"
```

Example response:

```json
{
  "ip": "8.8.8.8",
  "ipNumber": 134744072,
  "ipVersion": 4,
  "isPublic": true,
  "range": {
    "from": "8.8.8.0",
    "to": "8.8.8.255",
    "fromNumber": 134744064,
    "toNumber": 134744319
  },
  "countryCode": "US",
  "countryName": "United States of America",
  "regionName": "California",
  "cityName": "Mountain View",
  "latitude": 37.40599,
  "longitude": -122.078514,
  "source": "IP2Location LITE DB5"
}
```

Health response:

```json
{
  "status": "ok",
  "database": "ready",
  "ipv4Only": true
}
```

Error response:

```json
{
  "error": "invalid_ip",
  "message": "IP address is invalid"
}
```

By default, private, loopback, multicast, reserved, unspecified, and link-local addresses are rejected. Set `ALLOW_NON_PUBLIC_IPS=true` only when you intentionally want non-public lookups.

## Configuration

Configuration is loaded from environment variables. See [.env.example](.env.example).

| Variable | Default | Description |
| --- | --- | --- |
| `DATABASE_PATH` | `data/ip2location.sqlite` | SQLite database path |
| `ALLOW_NON_PUBLIC_IPS` | `false` | Allow private, loopback, reserved, and other non-public IPs |
| `TRUST_PROXY` | `false` | Trust `X-Forwarded-For` when resolving `/api/v1/me` |
| `RATE_LIMIT_REQUESTS` | `60` | Requests allowed per client per window |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Rate limit window in seconds |
| `CORS_ORIGINS` | `*` | Comma-separated allowed CORS origins |
| `APP_HOST` | `0.0.0.0` | App host used by deployment scripts |
| `APP_PORT` | `8000` | App port used by deployment scripts |
| `LOG_LEVEL` | `INFO` | Python logging level |

Production notes:

- Use explicit `CORS_ORIGINS` instead of `*`.
- Set `TRUST_PROXY=true` only behind a trusted reverse proxy or managed platform.
- Keep `ALLOW_NON_PUBLIC_IPS=false` for public APIs unless you have a specific internal use case.

## Build the Database

Inspect the CSV:

```bash
python scripts/inspect_csv.py --input data/IP2LOCATION-LITE-DB5.CSV
```

Build SQLite:

```bash
python scripts/build_database.py --input data/IP2LOCATION-LITE-DB5.CSV --output data/ip2location.sqlite
```

The importer expects the common DB5 column order:

```text
IP_FROM, IP_TO, COUNTRY_CODE, COUNTRY_NAME, REGION_NAME, CITY_NAME, LATITUDE, LONGITUDE
```

Headerless files are treated as that order. The builder streams the CSV, inserts rows in batches, creates indexes, runs `ANALYZE` and `VACUUM`, then prints record counts, invalid rows, file size, and elapsed time.

## Docker

Build the SQLite database before building the Docker image:

```bash
python scripts/build_database.py --input data/IP2LOCATION-LITE-DB5.CSV --output data/ip2location.sqlite
docker build -t ip2location-api .
docker run --rm -p 8000:8000 ip2location-api
```

For development with a mounted database:

```bash
docker compose up --build
```

The final image excludes the original CSV and runs Uvicorn with one worker to keep memory usage predictable.

## Deployment

### Koyeb, Render, Fly.io, or similar Docker platforms

1. Build `data/ip2location.sqlite` locally.
2. Build and deploy the Docker image.
3. Set `DATABASE_PATH=/app/data/ip2location.sqlite`.
4. Set `TRUST_PROXY=true` only if the platform forwards the original client IP through trusted proxy headers.
5. Configure explicit `CORS_ORIGINS` for your domain.

### Google Cloud Run

```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/ip2location-api
gcloud run deploy ip2location-api \
  --image gcr.io/PROJECT_ID/ip2location-api \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars TRUST_PROXY=true,DATABASE_PATH=/app/data/ip2location.sqlite
```

Use a CPU and memory profile appropriate for the generated SQLite file size and your traffic.

## How Lookup Works

IPv4 addresses are converted to unsigned 32-bit integers. The service asks SQLite for the range with the largest `ip_from` less than or equal to the IP number:

```sql
SELECT *
FROM ip_ranges
WHERE ip_from <= ?
ORDER BY ip_from DESC
LIMIT 1;
```

Python then verifies that the requested IP number is less than or equal to `ip_to`. If not, the request returns `404`.

This gives efficient B-tree range lookups without scanning the CSV or keeping all ranges in memory.

## Testing

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

Run tests:

```bash
pytest
```

Tests create a small temporary SQLite database and do not depend on the full IP2Location CSV.

## Benchmark

```bash
python scripts/benchmark.py --database data/ip2location.sqlite --count 10000
```

Benchmark numbers depend on your disk, OS page cache, SQLite file size, and server configuration.

## Data, License, and Attribution

Source code is released under the [MIT License](LICENSE).

This product includes or is designed to use IP2Location LITE data available from [lite.ip2location.com](https://lite.ip2location.com). IP2Location data is distributed under its own terms and attribution requirements. Follow the IP2Location LITE license terms for public deployments.

Do not commit:

- `data/*.sqlite`
- `data/*.CSV`
- `data/*.csv`
- Secrets or production environment files

## Security

Please read [SECURITY.md](SECURITY.md) before reporting vulnerabilities.

Security-related defaults:

- Non-public IPs are rejected unless explicitly allowed.
- `X-Forwarded-For` is ignored unless `TRUST_PROXY=true`.
- Responses include basic security headers.
- Rate limiting is enabled by default.

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

Good first areas:

- IPv6 support
- Additional deployment examples
- More benchmark profiles
- Better observability and metrics
- Packaging examples for serverless platforms

## Limitations

- IPv4 only.
- IP geolocation is approximate and can be affected by VPNs, proxies, corporate networks, mobile carriers, and registry data.
- Latitude and longitude represent approximate city or regional locations, not GPS coordinates.
- Database freshness depends on when you download and rebuild the IP2Location data.
