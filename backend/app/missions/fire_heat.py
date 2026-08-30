from __future__ import annotations

from ..domain import clamp, heat_index_c, number, point_geometry, risk_level
from ..models import AnalysisRequest, AnalysisResponse, Coordinates, DataStatus, Metric
from ..provenance import nasa_firms, open_meteo_weather
from .common import fire_snapshot, weather_snapshot


async def analyze(request: AnalysisRequest) -> AnalysisResponse:
    weather, weather_status = await weather_snapshot(request.latitude, request.longitude)
    fire, fire_status = await fire_snapshot(request.latitude, request.longitude)
    temperature = number(request.parameters, "temperature_max_c", weather["temperature_max_c"])
    humidity = clamp(number(request.parameters, "relative_humidity_pct", weather["relative_humidity_pct"]), 0, 100)
    rain = max(0.0, number(request.parameters, "rain_7d_mm", weather["rain_7d_mm"]))
    wind = max(0.0, number(request.parameters, "wind_max_kmh", weather["wind_max_kmh"]))
    hotspot_count = max(0.0, number(request.parameters, "hotspot_count", fire["hotspot_count"]))
    heat_index = heat_index_c(temperature, humidity)

    heat_component = clamp((heat_index - 28.0) / 18.0 * 100)
    dryness_component = clamp((35.0 - rain) / 35.0 * 100) * clamp((55.0 - humidity) / 35.0, 0.25, 1.0)
    wind_component = clamp(wind / 45.0 * 100)
    hotspot_component = clamp(hotspot_count / 8.0 * 100)
    score = clamp(0.35 * heat_component + 0.25 * dryness_component + 0.15 * wind_component + 0.25 * hotspot_component)
    weather_keys = {"temperature_max_c", "relative_humidity_pct", "rain_7d_mm", "wind_max_kmh"}
    supplied_weather_keys = weather_keys.intersection(request.parameters)
    external_weather_used = not weather_keys.issubset(request.parameters)
    hotspot_supplied = "hotspot_count" in request.parameters
    statuses = {DataStatus.MODELLED}
    if external_weather_used:
        statuses.add(weather_status)
    if not hotspot_supplied:
        statuses.add(fire_status)
    if supplied_weather_keys or hotspot_supplied:
        statuses.add(DataStatus.USER_SUPPLIED)
    if fire_status == DataStatus.NEAR_REAL_TIME and weather_status == DataStatus.FORECAST and not request.parameters:
        evidence_confidence = 0.80
    elif DataStatus.DEMONSTRATION in statuses:
        evidence_confidence = 0.42
    else:
        evidence_confidence = 0.62

    return AnalysisResponse(
        mission=request.mission,
        title="Global Agricultural Fire & Heat Watch",
        coordinates=Coordinates(latitude=request.latitude, longitude=request.longitude),
        area_hectares=request.area_hectares,
        score=round(score, 1),
        risk_level=risk_level(score),
        confidence=evidence_confidence,
        summary=(
            f"The combined heat, dryness, wind and hotspot screen indicates {risk_level(score).value} agricultural fire-and-heat concern. "
            "Verify every hotspot and follow official local warnings."
        ),
        data_status=sorted(statuses, key=lambda item: item.value),
        metrics=[
            Metric(key="heat_index", label="Heat index", value=round(heat_index, 1), unit="°C", interpretation="Screening apparent-temperature indicator."),
            Metric(key="hotspots", label="Nearby thermal detections", value=int(hotspot_count), unit="detections", interpretation="Satellite hotspots in the configured search area; not all are fires."),
            Metric(key="rain", label="Seven-day precipitation", value=round(rain, 1), unit="mm", interpretation="Lower rainfall increases the dryness component."),
            Metric(key="wind", label="Maximum wind", value=round(wind, 1), unit="km/h", interpretation="Weather-model wind used as a spread-risk proxy."),
        ],
        sources=([] if hotspot_supplied else [nasa_firms(fire_status)])
        + ([] if not external_weather_used else [open_meteo_weather(weather_status)]),
        caveats=[
            "FIRMS detects thermal anomalies; it does not identify cause, ownership or burned crop area.",
            "Heat-index guidance was designed for human heat exposure and is used here only as a screening indicator.",
            "Local fire agencies and meteorological services remain authoritative for warnings and response.",
        ],
        geometry=point_geometry(request.latitude, request.longitude, {"score": round(score, 1), "hotspots": hotspot_count, "mission": request.mission.value}),
    )
