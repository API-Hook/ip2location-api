"""FastAPI application for offline IP geolocation."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from .config import Settings, get_settings
from .database import SQLiteDatabase
from .ip_lookup import LookupErrorResponse, lookup_ip
from .middleware import (
    RateLimitMiddleware,
    ResponseTimeMiddleware,
    SecurityHeadersMiddleware,
    get_client_ip,
)

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, database: SQLiteDatabase | None = None) -> FastAPI:
    """Create and configure the FastAPI app."""

    resolved_settings = settings or get_settings()
    resolved_database = database or SQLiteDatabase(resolved_settings.database_path)
    logging.basicConfig(
        level=getattr(logging, resolved_settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("Starting offline IP geolocation service")
        logger.info("Database status: %s", resolved_database.status())
        if resolved_database.exists():
            logger.info("Database file size: %s bytes", resolved_database.file_size())
        yield

    app = FastAPI(title="Free Offline IP Geolocation", version="1.0.0", lifespan=lifespan)
    app.state.settings = resolved_settings
    app.state.database = resolved_database

    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(ResponseTimeMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_window=resolved_settings.rate_limit_requests,
        window_seconds=resolved_settings.rate_limit_window_seconds,
        trust_proxy=resolved_settings.trust_proxy,
    )

    @app.exception_handler(LookupErrorResponse)
    async def lookup_exception_handler(
        request: Request,
        exc: LookupErrorResponse,
    ) -> JSONResponse:
        logger.info("Lookup error: %s", exc.error)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.error, "message": exc.message},
        )

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/health")
    async def health() -> dict[str, object]:
        db: SQLiteDatabase = app.state.database
        return {"status": "ok", "database": db.status(), "ipv4Only": True}

    @app.get("/api/v1/me")
    async def lookup_me(request: Request, response: Response) -> dict[str, object]:
        client_ip = get_client_ip(request, trust_proxy=app.state.settings.trust_proxy)
        result = lookup_ip(
            client_ip,
            database=app.state.database,
            allow_non_public=app.state.settings.allow_non_public_ips,
        )
        response.headers["Cache-Control"] = "public, max-age=86400"
        return result

    @app.get("/api/v1/lookup")
    async def lookup_query(ip: str, response: Response) -> dict[str, object]:
        result = lookup_ip(
            ip,
            database=app.state.database,
            allow_non_public=app.state.settings.allow_non_public_ips,
        )
        response.headers["Cache-Control"] = "public, max-age=86400"
        return result

    @app.get("/api/v1/lookup/{ip:path}")
    async def lookup_path(ip: str, response: Response) -> dict[str, object]:
        result = lookup_ip(
            ip,
            database=app.state.database,
            allow_non_public=app.state.settings.allow_non_public_ips,
        )
        response.headers["Cache-Control"] = "public, max-age=86400"
        return result

    return app


app = create_app()
