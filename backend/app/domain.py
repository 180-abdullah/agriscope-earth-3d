from __future__ import annotations

import hashlib
import math
from collections.abc import Iterable
from typing import Any

from .models import RiskLevel


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def risk_level(score: float) -> RiskLevel:
    if score < 25:
        return RiskLevel.LOW
    if score < 50:
        return RiskLevel.MODERATE
    if score < 75:
        return RiskLevel.HIGH
    return RiskLevel.SEVERE


def mean(values: Iterable[float], default: float = 0.0) -> float:
    clean = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    return sum(clean) / len(clean) if clean else default


def number(parameters: dict[str, Any], key: str, default: float) -> float:
    value = parameters.get(key, default)
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if math.isfinite(parsed) else default


def deterministic_unit(latitude: float, longitude: float, namespace: str) -> float:
    payload = f"{latitude:.4f}:{longitude:.4f}:{namespace}".encode()
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:8], "big") / float(2**64 - 1)


def heat_index_c(temperature_c: float, relative_humidity: float) -> float:
    """NOAA Rothfusz heat-index regression, returned in degrees Celsius."""
    temperature_f = temperature_c * 9 / 5 + 32
    rh = clamp(relative_humidity, 0, 100)
    hi = (
        -42.379
        + 2.04901523 * temperature_f
        + 10.14333127 * rh
        - 0.22475541 * temperature_f * rh
        - 0.00683783 * temperature_f**2
        - 0.05481717 * rh**2
        + 0.00122874 * temperature_f**2 * rh
        + 0.00085282 * temperature_f * rh**2
        - 0.00000199 * temperature_f**2 * rh**2
    )
    if temperature_f < 80:
        hi = temperature_f
    return (hi - 32) * 5 / 9


def point_geometry(latitude: float, longitude: float, properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [longitude, latitude]},
        "properties": properties,
    }
