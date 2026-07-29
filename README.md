# Free Offline IP Geolocation

A production-ready FastAPI web service for offline IPv4 geolocation using IP2Location LITE DB5 data. The large CSV is converted once into an indexed SQLite database, and runtime requests use fast B-tree range lookups without Pandas, CSV scans, or loading all ranges into memory.

## Why not query the CSV directly?

The IP2Location LITE DB5 CSV can be hundreds of megabytes. Scanning it for every request is slow, CPU-heavy, and unsuitable for small 512 MB servers. Keeping the whole file in memory is also fragile. SQLite gives durable storage, indexes, OS page cache behavior, and low memory overhead.

## How lookup works

IPv4 addresses are converted to unsigned 32-bit integers. The service asks SQLite for the range with the largest `ip_from` less than or equal to the IP number:

```sql
SELECT *
FROM ip_ranges
WHERE ip_from <= ?
ORDER BY ip_from DESC
LIMIT 1;
```

Python then verifies that the IP number is less than or equal to `ip_to`. If not, the IP is outside the selected range and returns `404`.

## Download DB5 CSV

Download the IP2Location LITE DB5 CSV from [https://lite.ip2location.com](https://lite.ip2location.com). Place the extracted file at:

```powershell
data/IP2LOCATION-LITE-DB5.CSV
```

The importer supports the common DB5 order:

```text
IP_FROM, IP_TO, COUNTRY_CODE, COUNTRY_NAME, REGION_NAME, CITY_NAME, LATITUDE, LONGITUDE
```

Headerless files are treated as that order.

## Inspect the CSV

```powershell
python scripts/inspect_csv.py --input data/IP2LOCATION-LITE-DB5.CSV
```

## Build SQLite

```powershell
python scripts/build_database.py --input data/IP2LOCATION-LITE-DB5.CSV --output data/ip2location.sqlite
```

The builder streams the CSV, imports 10,000 rows per batch, prints progress every 100,000 rows, skips invalid rows, runs `ANALYZE` and `VACUUM`, then reports record counts, invalid rows, file size, and elapsed time.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

## API

```text
GET /health
GET /api/v1/lookup?ip=8.8.8.8
GET /api/v1/lookup/8.8.8.8
GET /api/v1/me
```

By default, private, loopback, multicast, reserved, unspecified, and link-local addresses are rejected. Set `ALLOW_NON_PUBLIC_IPS=true` only when you explicitly want non-public lookups.

## Configuration

```text
DATABASE_PATH=data/ip2location.sqlite
ALLOW_NON_PUBLIC_IPS=false
TRUST_PROXY=false
RATE_LIMIT_REQUESTS=60
RATE_LIMIT_WINDOW_SECONDS=60
CORS_ORIGINS=*
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO
```

`CORS_ORIGINS=*` is convenient for demos. Production deployments should use explicit domains. `TRUST_PROXY=true` allows `X-Forwarded-For` to determine the client IP, which is appropriate only behind a trusted proxy such as Cloud Run, Koyeb, or Render.

## Run tests

```powershell
pip install -r requirements-dev.txt
pytest
```

Tests create a small temporary SQLite database and do not depend on the full CSV.

## Benchmark

```powershell
python scripts/benchmark.py --database data/ip2location.sqlite --count 10000
```

## Docker

Build the SQLite database locally before building the image.

```powershell
docker build -t ip-location-api .
docker run --rm -p 8000:8000 ip-location-api
```

For development with a mounted database:

```powershell
docker compose up --build
```

The final image excludes the original CSV and runs Uvicorn with one worker to keep memory low.

## Deploy to Koyeb

Build `data/ip2location.sqlite` locally, commit or package the database with the deploy artifact, and deploy the Dockerfile. Set environment variables in Koyeb, especially `DATABASE_PATH=/app/data/ip2location.sqlite`, `TRUST_PROXY=true`, and explicit `CORS_ORIGINS`.

## Deploy to Google Cloud Run

Build and push the container after generating `data/ip2location.sqlite`:

```powershell
gcloud builds submit --tag gcr.io/PROJECT_ID/ip-location-api
gcloud run deploy ip-location-api --image gcr.io/PROJECT_ID/ip-location-api --platform managed --allow-unauthenticated --set-env-vars TRUST_PROXY=true,DATABASE_PATH=/app/data/ip2location.sqlite
```

Use one container instance CPU/memory profile appropriate for the SQLite file size and expected traffic.

## Memory notes for 512 MB servers

The runtime opens SQLite read-only using immutable mode and one connection per thread. It does not read the full database into Python memory. `mmap_size` and SQLite cache settings are limits and hints; the OS pages data on demand. Use one Uvicorn worker by default.

## Attribution

This product includes IP2Location LITE data available from [https://lite.ip2location.com](https://lite.ip2location.com). Follow IP2Location LITE attribution requirements for your public deployment.

## Limitations

IP-based geolocation is approximate and may reflect ISP routing, VPNs, proxies, corporate networks, or registry data rather than a person's exact position. Latitude and longitude represent approximate city or regional locations, not GPS coordinates.

