"""Pydantic models returned by the API."""

from pydantic import BaseModel, ConfigDict, Field


class ErrorResponse(BaseModel):
    """Standard API error response."""

    error: str
    message: str


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    database: str
    ipv4Only: bool


class IpRangeResponse(BaseModel):
    """Matched IPv4 range details."""

    from_: str = Field(alias="from")
    to: str
    fromNumber: int
    toNumber: int

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class LookupResponse(BaseModel):
    """Successful geolocation lookup response."""

    ip: str
    ipNumber: int
    ipVersion: int
    isPublic: bool
    range: IpRangeResponse
    countryCode: str | None
    countryName: str | None
    regionName: str | None
    cityName: str | None
    latitude: float | None
    longitude: float | None
    source: str
