"""Strict, attributed boundary for Open-Meteo current conditions."""

import asyncio
import json
import math
from collections.abc import Awaitable, Callable
from datetime import datetime
from http.client import HTTPException
from typing import Literal
from urllib.parse import urlencode, urlsplit

import httpx
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field

from pandaflow.shared.rules import load_json_resource


OPEN_METEO_ENDPOINT = "https://api.open-meteo.com/v1/forecast"
CURRENT_FIELDS = (
    "temperature_2m",
    "apparent_temperature",
    "precipitation",
    "weather_code",
    "wind_speed_10m",
)
MAX_RESPONSE_BYTES = 65_536
Transport = Callable[[str, float], bytes]
AsyncReader = Callable[[str], Awaitable[bytes]]
SHANGHAI_TIMEZONE = "Asia/Shanghai"


class OpenMeteoError(RuntimeError):
    """A safe adapter error that does not expose response or transport details."""


class WeatherSnapshot(BaseModel):
    """Normalized weather fields consumed by the deterministic risk Skill."""

    model_config = ConfigDict(extra="forbid")

    temperature_celsius: float = Field(ge=-50, le=60)
    apparent_temperature_celsius: float = Field(ge=-80, le=80)
    precipitation_mm: float = Field(ge=0, le=2_000)
    weather_code: int = Field(ge=0, le=99)
    wind_speed_kmh: float = Field(ge=0, le=500)
    observed_at: datetime | None
    fetched_at: datetime | None = None
    timezone: str
    location_label: str
    source: Literal["open_meteo", "provided_synthetic", "fixed_fallback"]
    attribution: str
    attribution_url: str
    demo_data: bool


async def _read_httpx_response(url: str) -> bytes:
    parsed = urlsplit(url)
    endpoint = urlsplit(OPEN_METEO_ENDPOINT)
    if (parsed.scheme, parsed.netloc, parsed.path) != (
        endpoint.scheme,
        endpoint.netloc,
        endpoint.path,
    ):
        raise OpenMeteoError("Open-Meteo transport refused an unexpected endpoint.")

    chunks: list[bytes] = []
    size = 0
    async with httpx.AsyncClient(
        timeout=None,
        follow_redirects=False,
        headers={"User-Agent": "PandaFlow/0.1 weather-demo"},
    ) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                size += len(chunk)
                if size > MAX_RESPONSE_BYTES:
                    raise OpenMeteoError("Open-Meteo response is too large.")
                chunks.append(chunk)
    return b"".join(chunks)


def _default_transport(
    url: str,
    timeout_seconds: float,
    *,
    async_reader: AsyncReader | None = None,
) -> bytes:
    async def read_with_deadline() -> bytes:
        async with asyncio.timeout(timeout_seconds):
            return await (async_reader or _read_httpx_response)(url)

    try:
        return asyncio.run(read_with_deadline())
    except TimeoutError as exc:
        raise OpenMeteoError("Open-Meteo total request deadline was exceeded.") from exc
    except httpx.HTTPError as exc:
        raise OpenMeteoError("Open-Meteo transport failed.") from exc


def _number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OpenMeteoError(f"Open-Meteo schema field {field} is not numeric.")
    number = float(value)
    if not math.isfinite(number):
        raise OpenMeteoError(f"Open-Meteo field {field} must be finite.")
    return number


def _weather_code(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise OpenMeteoError("Open-Meteo schema field weather_code is not an integer.")
    return value


def fetch_open_meteo_current(
    *, transport: Transport | None = None, timeout_seconds: float = 3.0
) -> WeatherSnapshot:
    """Fetch and normalize one current snapshot from the fixed demo location."""

    config = load_json_resource("weather_config.json")
    location = config["location"]
    query = urlencode(
        {
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "current": ",".join(CURRENT_FIELDS),
            "timezone": SHANGHAI_TIMEZONE,
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh",
            "precipitation_unit": "mm",
            "timeformat": "iso8601",
        }
    )
    try:
        raw = (transport or _default_transport)(f"{OPEN_METEO_ENDPOINT}?{query}", timeout_seconds)
    except OpenMeteoError:
        raise
    except (OSError, TimeoutError, ValueError, HTTPException) as exc:
        raise OpenMeteoError("Open-Meteo transport failed.") from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise OpenMeteoError("Open-Meteo response is too large.")
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise OpenMeteoError("Open-Meteo response is not valid JSON.") from exc
    try:
        current = payload["current"]
        units = payload["current_units"]
        timezone = payload["timezone"]
        observed_at = current["time"]
    except (KeyError, TypeError) as exc:
        raise OpenMeteoError("Open-Meteo response schema is incomplete.") from exc
    expected_units = {
        "temperature_2m": "°C",
        "apparent_temperature": "°C",
        "precipitation": "mm",
        "weather_code": "wmo code",
        "wind_speed_10m": "km/h",
    }
    if not isinstance(units, dict) or any(units.get(key) != value for key, value in expected_units.items()):
        raise OpenMeteoError("Open-Meteo response units are not supported.")
    if timezone != SHANGHAI_TIMEZONE or not isinstance(observed_at, str):
        raise OpenMeteoError("Open-Meteo response schema has invalid time metadata.")
    try:
        parsed_observed_at = datetime.fromisoformat(observed_at)
    except ValueError as exc:
        raise OpenMeteoError("Open-Meteo response schema has invalid time metadata.") from exc
    if parsed_observed_at.tzinfo is None:
        parsed_observed_at = parsed_observed_at.replace(tzinfo=ZoneInfo(SHANGHAI_TIMEZONE))
    else:
        parsed_observed_at = parsed_observed_at.astimezone(ZoneInfo(SHANGHAI_TIMEZONE))
    try:
        return WeatherSnapshot(
            temperature_celsius=_number(current["temperature_2m"], "temperature_2m"),
            apparent_temperature_celsius=_number(
                current["apparent_temperature"], "apparent_temperature"
            ),
            precipitation_mm=_number(current["precipitation"], "precipitation"),
            weather_code=_weather_code(current["weather_code"]),
            wind_speed_kmh=_number(current["wind_speed_10m"], "wind_speed_10m"),
            observed_at=parsed_observed_at,
            timezone=timezone,
            location_label=location["label"],
            source="open_meteo",
            attribution="Weather data by Open-Meteo.com",
            attribution_url="https://open-meteo.com/",
            demo_data=False,
        )
    except (KeyError, TypeError) as exc:
        raise OpenMeteoError("Open-Meteo response schema is incomplete.") from exc
    except ValueError as exc:
        raise OpenMeteoError("Open-Meteo response values are outside supported ranges.") from exc
