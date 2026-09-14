import asyncio
import json
from time import monotonic
from datetime import UTC, date, datetime, timedelta
from http.client import IncompleteRead
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import pytest

from pandaflow.integrations.open_meteo import (
    OpenMeteoError,
    WeatherSnapshot,
    _default_transport,
    fetch_open_meteo_current,
)
from pandaflow.orchestrator.weather import resolve_weather
from pandaflow.shared.contracts import SkillStatus
from pandaflow.shared.rules import load_json_resource


SHANGHAI_NOW = datetime(2026, 9, 8, 12, tzinfo=ZoneInfo("Asia/Shanghai"))


def _live_payload(*, observed_at: str = "2026-09-08T12:00") -> bytes:
    return json.dumps(
        {
            "latitude": 30.75,
            "longitude": 104.125,
            "timezone": "Asia/Shanghai",
            "current_units": {
                "time": "iso8601",
                "interval": "seconds",
                "temperature_2m": "°C",
                "apparent_temperature": "°C",
                "precipitation": "mm",
                "weather_code": "wmo code",
                "wind_speed_10m": "km/h",
            },
            "current": {
                "time": observed_at,
                "interval": 900,
                "temperature_2m": 33.1,
                "apparent_temperature": 36.2,
                "precipitation": 0.2,
                "weather_code": 3,
                "wind_speed_10m": 8.4,
            },
        }
    ).encode()


def test_fetch_requests_only_the_approved_current_fields_with_three_second_timeout():
    captured: dict[str, object] = {}

    def transport(url: str, timeout_seconds: float) -> bytes:
        captured.update(url=url, timeout=timeout_seconds)
        return _live_payload()

    snapshot = fetch_open_meteo_current(transport=transport)

    parsed = urlparse(str(captured["url"]))
    query = parse_qs(parsed.query)
    assert parsed.scheme == "https"
    assert parsed.netloc == "api.open-meteo.com"
    assert parsed.path == "/v1/forecast"
    assert query["current"] == [
        "temperature_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m"
    ]
    assert query["timezone"] == ["Asia/Shanghai"]
    assert query["temperature_unit"] == ["celsius"]
    assert query["wind_speed_unit"] == ["kmh"]
    assert query["precipitation_unit"] == ["mm"]
    assert captured["timeout"] == 3.0
    assert snapshot.temperature_celsius == 33.1
    assert snapshot.apparent_temperature_celsius == 36.2
    assert snapshot.precipitation_mm == 0.2
    assert snapshot.weather_code == 3
    assert snapshot.wind_speed_kmh == 8.4
    assert snapshot.observed_at.isoformat() == "2026-09-08T12:00:00+08:00"
    assert snapshot.source == "open_meteo"
    assert snapshot.demo_data is False


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda payload: payload["current_units"].update(temperature_2m="°F"), "units"),
        (lambda payload: payload["current"].update(temperature_2m=float("nan")), "finite"),
        (lambda payload: payload["current"].pop("weather_code"), "schema"),
    ],
)
def test_fetch_rejects_wrong_units_non_finite_values_and_incomplete_schema(mutate, message):
    payload = json.loads(_live_payload())
    mutate(payload)

    with pytest.raises(OpenMeteoError, match=message):
        fetch_open_meteo_current(transport=lambda _url, _timeout: json.dumps(payload).encode())


def test_fetch_rejects_oversized_response_before_parsing():
    with pytest.raises(OpenMeteoError, match="large"):
        fetch_open_meteo_current(transport=lambda _url, _timeout: b"{" + b" " * 70_000)


def test_truncated_http_body_is_wrapped_and_resolves_to_the_fixed_fallback():
    calls = 0

    def truncated() -> WeatherSnapshot:
        nonlocal calls
        calls += 1
        return fetch_open_meteo_current(
            transport=lambda _url, _timeout: (_ for _ in ()).throw(
                IncompleteRead(b'{"current":', 20)
            )
        )

    resolution = resolve_weather(
        mode="live_current",
        temperature_celsius=None,
        visit_date=SHANGHAI_NOW.date(),
        fetcher=truncated,
        now=lambda: SHANGHAI_NOW,
    )

    assert calls == 1
    assert resolution.status is SkillStatus.DEGRADED
    assert resolution.snapshot.source == "fixed_fallback"


def test_default_transport_applies_one_wall_clock_deadline_across_response_reads():
    async def slow_chunked_reader(_url: str) -> bytes:
        chunks = []
        for _ in range(20):
            await asyncio.sleep(0.01)
            chunks.append(b"{}")
        return b"".join(chunks)

    started = monotonic()
    with pytest.raises(OpenMeteoError, match="deadline"):
        _default_transport(
            "https://api.open-meteo.com/v1/forecast?current=temperature_2m",
            0.03,
            async_reader=slow_chunked_reader,
        )
    assert monotonic() - started < 0.12


def test_supplied_synthetic_temperature_stays_deterministic_and_does_not_fetch():
    def unexpected_fetch() -> WeatherSnapshot:
        raise AssertionError("synthetic mode must not call the live dependency")

    resolution = resolve_weather(
        mode="synthetic",
        temperature_celsius=22,
        visit_date=date(2026, 7, 4),
        fetcher=unexpected_fetch,
    )

    assert resolution.status is SkillStatus.OK
    assert resolution.snapshot.temperature_celsius == 22
    assert resolution.snapshot.source == "provided_synthetic"
    assert resolution.snapshot.demo_data is True


def test_live_failure_uses_fixed_high_heat_fallback_and_marks_degraded():
    calls = 0

    def unavailable() -> WeatherSnapshot:
        nonlocal calls
        calls += 1
        raise OpenMeteoError("timeout")

    resolution = resolve_weather(
        mode="live_current",
        temperature_celsius=None,
        visit_date=SHANGHAI_NOW.date(),
        fetcher=unavailable,
        now=lambda: SHANGHAI_NOW,
    )

    assert calls == 1
    assert resolution.status is SkillStatus.DEGRADED
    assert resolution.snapshot.temperature_celsius == 33
    assert resolution.snapshot.apparent_temperature_celsius == 36
    assert resolution.snapshot.source == "fixed_fallback"
    assert resolution.snapshot.demo_data is True
    assert resolution.source_refs == ["source_demo_weather_fallback"]
    assert "timeout" not in " ".join(resolution.warnings).lower()


def test_live_current_for_another_date_degrades_without_calling_the_dependency():
    def unexpected_fetch() -> WeatherSnapshot:
        raise AssertionError("a current observation must not be used for another visit date")

    resolution = resolve_weather(
        mode="live_current",
        temperature_celsius=None,
        visit_date=SHANGHAI_NOW.date() + timedelta(days=1),
        fetcher=unexpected_fetch,
        now=lambda: SHANGHAI_NOW,
    )

    assert resolution.status is SkillStatus.DEGRADED
    assert resolution.snapshot.source == "fixed_fallback"
    assert any("visit date" in warning.lower() for warning in resolution.warnings)


def test_today_is_evaluated_in_shanghai_even_when_the_server_clock_is_utc():
    utc_time_after_shanghai_midnight = datetime(2026, 9, 7, 16, 30, tzinfo=UTC)

    resolution = resolve_weather(
        mode="live_current",
        temperature_celsius=None,
        visit_date=date(2026, 9, 8),
        fetcher=lambda: fetch_open_meteo_current(
            transport=lambda _url, _timeout: _live_payload(
                observed_at="2026-09-08T00:30"
            )
        ),
        now=lambda: utc_time_after_shanghai_midnight,
    )

    assert resolution.status is SkillStatus.OK
    assert resolution.snapshot.source == "open_meteo"


@pytest.mark.parametrize(
    ("observed_at", "expected_status", "expected_source"),
    [
        (SHANGHAI_NOW - timedelta(minutes=30), SkillStatus.OK, "open_meteo"),
        (
            SHANGHAI_NOW - timedelta(minutes=30, seconds=1),
            SkillStatus.DEGRADED,
            "fixed_fallback",
        ),
        (SHANGHAI_NOW + timedelta(minutes=5), SkillStatus.OK, "open_meteo"),
        (
            SHANGHAI_NOW + timedelta(minutes=5, seconds=1),
            SkillStatus.DEGRADED,
            "fixed_fallback",
        ),
    ],
)
def test_live_observation_freshness_boundaries(
    observed_at, expected_status, expected_source
):
    snapshot = fetch_open_meteo_current(
        transport=lambda _url, _timeout: _live_payload(
            observed_at=observed_at.strftime("%Y-%m-%dT%H:%M:%S")
        )
    )

    resolution = resolve_weather(
        mode="live_current",
        temperature_celsius=None,
        visit_date=SHANGHAI_NOW.date(),
        fetcher=lambda: snapshot,
        now=lambda: SHANGHAI_NOW,
    )

    assert resolution.status is expected_status
    assert resolution.snapshot.source == expected_source
    if expected_status is SkillStatus.OK:
        assert resolution.snapshot.observed_at == observed_at
        assert resolution.snapshot.fetched_at == SHANGHAI_NOW
    else:
        assert any("stale" in warning.lower() for warning in resolution.warnings)


def test_freshness_accepts_an_observation_from_before_shanghai_midnight():
    now = datetime(2026, 9, 9, 0, 5, tzinfo=ZoneInfo("Asia/Shanghai"))
    observed_at = datetime(2026, 9, 8, 23, 50, tzinfo=ZoneInfo("Asia/Shanghai"))
    snapshot = fetch_open_meteo_current(
        transport=lambda _url, _timeout: _live_payload(
            observed_at="2026-09-08T23:50"
        )
    )

    resolution = resolve_weather(
        mode="live_current",
        temperature_celsius=None,
        visit_date=now.date(),
        fetcher=lambda: snapshot,
        now=lambda: now,
    )

    assert resolution.status is SkillStatus.OK
    assert resolution.snapshot.observed_at == observed_at
    assert resolution.snapshot.fetched_at == now


@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload: payload.update(timezone="UTC"),
        lambda payload: payload["current"].update(time="not-a-time"),
    ],
)
def test_fetch_rejects_wrong_timezone_and_malformed_observation_time(mutate):
    payload = json.loads(_live_payload())
    mutate(payload)

    with pytest.raises(OpenMeteoError, match="time"):
        fetch_open_meteo_current(transport=lambda _url, _timeout: json.dumps(payload).encode())


def test_every_weather_resolution_source_reference_is_registered():
    registered = {
        source["source_id"] for source in load_json_resource("source_registry.json")["sources"]
    }
    live = resolve_weather(
        mode="live_current",
        temperature_celsius=None,
        visit_date=SHANGHAI_NOW.date(),
        fetcher=lambda: fetch_open_meteo_current(
            transport=lambda _url, _timeout: _live_payload()
        ),
        now=lambda: SHANGHAI_NOW,
    )
    fallback = resolve_weather(
        mode="live_current",
        temperature_celsius=None,
        visit_date=SHANGHAI_NOW.date() + timedelta(days=1),
        now=lambda: SHANGHAI_NOW,
    )

    assert live.source_refs == ["source_open_meteo_forecast", "source_open_meteo_license"]
    assert set(live.source_refs) <= registered
    assert set(fallback.source_refs) <= registered
