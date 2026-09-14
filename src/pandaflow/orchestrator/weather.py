"""Resolve supplied, live, and fallback weather without changing rule logic."""

from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict

from pandaflow.integrations.open_meteo import (
    OpenMeteoError,
    WeatherSnapshot,
    fetch_open_meteo_current,
)
from pandaflow.shared.contracts import SkillStatus
from pandaflow.shared.rules import load_json_resource


WeatherFetcher = Callable[[], WeatherSnapshot]
NowProvider = Callable[[], datetime]
SHANGHAI_TIMEZONE = ZoneInfo("Asia/Shanghai")


class WeatherResolution(BaseModel):
    """Weather plus traceability and degradation state for orchestration."""

    model_config = ConfigDict(extra="forbid")

    status: SkillStatus
    snapshot: WeatherSnapshot
    source_refs: list[str]
    warnings: list[str]


def _demo_snapshot(source: Literal["provided_synthetic", "fixed_fallback"], temperature: float) -> WeatherSnapshot:
    config = load_json_resource("weather_config.json")
    fallback = config["fallback"]
    return WeatherSnapshot(
        temperature_celsius=temperature,
        apparent_temperature_celsius=(
            temperature if source == "provided_synthetic" else fallback["apparent_temperature_celsius"]
        ),
        precipitation_mm=fallback["precipitation_mm"],
        weather_code=fallback["weather_code"],
        wind_speed_kmh=fallback["wind_speed_kmh"],
        observed_at=None,
        fetched_at=None,
        timezone="Asia/Shanghai",
        location_label=config["location"]["label"],
        source=source,
        attribution="PandaFlow synthetic demo weather",
        attribution_url="https://example.invalid/pandaflow/demo-weather",
        demo_data=True,
    )


def _fallback(warning: str) -> WeatherResolution:
    fallback = load_json_resource("weather_config.json")["fallback"]
    return WeatherResolution(
        status=SkillStatus.DEGRADED,
        snapshot=_demo_snapshot("fixed_fallback", fallback["temperature_celsius"]),
        source_refs=["source_demo_weather_fallback"],
        warnings=[warning],
    )


def resolve_weather(
    *,
    mode: Literal["synthetic", "live_current"],
    temperature_celsius: float | None,
    visit_date: date,
    fetcher: WeatherFetcher | None = None,
    now: NowProvider | None = None,
) -> WeatherResolution:
    """Resolve weather while keeping current observations tied to today's visit."""

    if mode == "synthetic":
        if temperature_celsius is None:
            return _fallback("Synthetic temperature was missing; fixed demo weather was used.")
        return WeatherResolution(
            status=SkillStatus.OK,
            snapshot=_demo_snapshot("provided_synthetic", temperature_celsius),
            source_refs=["source_demo_weather_fallback"],
            warnings=["Weather values are synthetic demo input, not a live venue observation."],
        )
    current_time = (now or (lambda: datetime.now(SHANGHAI_TIMEZONE)))()
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=SHANGHAI_TIMEZONE)
    today_in_shanghai = current_time.astimezone(SHANGHAI_TIMEZONE).date()
    if visit_date != today_in_shanghai:
        return _fallback(
            "Live current weather cannot represent a different visit date; fixed demo weather was used."
        )
    try:
        snapshot = (fetcher or fetch_open_meteo_current)()
    except OpenMeteoError:
        return _fallback("Live weather was unavailable or invalid; fixed demo weather was used.")
    config = load_json_resource("weather_config.json")
    freshness = config["freshness"]
    observed_at = snapshot.observed_at
    if observed_at is None:
        return _fallback(
            "Live weather observation was stale or had invalid time metadata; fixed demo weather was used."
        )
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=SHANGHAI_TIMEZONE)
    else:
        observed_at = observed_at.astimezone(SHANGHAI_TIMEZONE)
    observation_age = current_time.astimezone(SHANGHAI_TIMEZONE) - observed_at
    max_age = timedelta(minutes=freshness["max_observation_age_minutes"])
    max_future_skew = timedelta(minutes=freshness["max_future_skew_minutes"])
    if observation_age > max_age or observation_age < -max_future_skew:
        return _fallback(
            "Live weather observation was stale or had invalid time metadata; fixed demo weather was used."
        )
    snapshot = snapshot.model_copy(
        update={
            "observed_at": observed_at,
            "fetched_at": current_time.astimezone(SHANGHAI_TIMEZONE),
        }
    )
    return WeatherResolution(
        status=SkillStatus.OK,
        snapshot=snapshot,
        source_refs=["source_open_meteo_forecast", "source_open_meteo_license"],
        warnings=[
            "Forecast data are model-derived and are not a real-time venue operating or animal-health status."
        ],
    )
