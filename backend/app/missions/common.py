from __future__ import annotations

import os
from typing import Any

from ..domain import deterministic_unit, mean
from ..models import DataStatus
from ..services.earth_data import earth_data


def _series(payload: dict[str, Any], section: str, key: str) -> list[float]:
    values = payload.get(section, {}).get(key, []) if payload else []
    return [float(value) for value in values if value is not None]


async def weather_snapshot(latitude: float, longitude: float) -> tuple[dict[str, float], DataStatus]:
    try:
        payload = await earth_data.weather(latitude, longitude)
        daily_max = _series(payload, "daily", "temperature_2m_max")
        rain = _series(payload, "daily", "precipitation_sum")
        et0 = _series(payload, "daily", "et0_fao_evapotranspiration")
        humidity = _series(payload, "hourly", "relative_humidity_2m")
        soil_moisture = _series(payload, "hourly", "soil_moisture_0_to_7cm")
        wind = _series(payload, "hourly", "wind_speed_10m")
        return (
            {
                "temperature_max_c": max(daily_max, default=28.0),
                "rain_7d_mm": sum(rain),
                "et0_7d_mm": sum(et0),
                "relative_humidity_pct": mean(humidity, 60.0),
                "soil_moisture_m3_m3": mean(soil_moisture, 0.24),
                "wind_max_kmh": max(wind, default=12.0),
            },
            DataStatus.FORECAST,
        )
    except Exception:
        seed = deterministic_unit(latitude, longitude, "weather")
        return (
            {
                "temperature_max_c": 24.0 + seed * 16.0,
                "rain_7d_mm": (1.0 - seed) * 70.0,
                "et0_7d_mm": 18.0 + seed * 32.0,
                "relative_humidity_pct": 42.0 + (1.0 - seed) * 40.0,
                "soil_moisture_m3_m3": 0.12 + (1.0 - seed) * 0.28,
                "wind_max_kmh": 10.0 + seed * 30.0,
            },
            DataStatus.DEMONSTRATION,
        )


async def flood_snapshot(latitude: float, longitude: float) -> tuple[dict[str, float], DataStatus]:
    try:
        payload = await earth_data.flood(latitude, longitude)
        discharge = _series(payload, "daily", "river_discharge")
        ensemble_mean = _series(payload, "daily", "river_discharge_mean")
        ensemble_max = _series(payload, "daily", "river_discharge_max")
        q = max(discharge, default=0.0)
        q_mean = mean(ensemble_mean, mean(discharge, max(q, 1.0)))
        q_max = max(ensemble_max, default=max(q_mean, q, 1.0))
        return (
            {
                "discharge_peak_m3_s": q_max,
                "discharge_mean_m3_s": q_mean,
                "discharge_ratio": q_max / max(q_mean, 0.001),
            },
            DataStatus.FORECAST,
        )
    except Exception:
        seed = deterministic_unit(latitude, longitude, "flood")
        q_mean = 80.0 + seed * 1_500.0
        ratio = 0.65 + seed * 1.7
        return (
            {
                "discharge_peak_m3_s": q_mean * ratio,
                "discharge_mean_m3_s": q_mean,
                "discharge_ratio": ratio,
            },
            DataStatus.DEMONSTRATION,
        )


async def fire_snapshot(latitude: float, longitude: float) -> tuple[dict[str, float], DataStatus]:
    try:
        rows = await earth_data.fires(latitude, longitude)
        if os.getenv("FIRMS_MAP_KEY", "").strip():
            frp_values = []
            for row in rows:
                try:
                    frp_values.append(float(row.get("frp", 0)))
                except (TypeError, ValueError):
                    pass
            return {
                "hotspot_count": float(len(rows)),
                "maximum_frp_mw": max(frp_values, default=0.0),
            }, DataStatus.NEAR_REAL_TIME
    except Exception:
        pass
    seed = deterministic_unit(latitude, longitude, "fire")
    return {
        "hotspot_count": float(int(seed * 8)),
        "maximum_frp_mw": round(seed * 55.0, 1),
    }, DataStatus.DEMONSTRATION
