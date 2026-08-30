from __future__ import annotations

from ..domain import clamp, heat_index_c, number, point_geometry, risk_level
from ..models import AnalysisRequest, AnalysisResponse, Coordinates, DataStatus, Metric
from ..provenance import nasa_firms, open_meteo_weather
from .common import fire_snapshot, weather_snapshot


async def analyze(request: AnalysisRequest) -> AnalysisResponse:
    weather, weather_status = await weather_snapshot(request.latitude, request.longitude)
    fire, fire_status = await fire_snapshot(request.latitude, request.longitude)

    temperature = number(
        request.parameters,
        "temperature_max_c",
        weather["temperature_max_c"]
    )

    humidity = clamp(
        number(
            request.parameters,
            "relative_humidity_pct",
            weather["relative_humidity_pct"]
        ),
        0,
        100
    )

    rain = max(
        0.0,
        number(
            request.parameters,
            "rain_7d_mm",
            weather["rain_7d_mm"]
        )
    )

    wind = max(
        0.0,
        number(
            request.parameters,
            "wind_max_kmh",
            weather["wind_max_kmh"]
        )
    )

    hotspot_count = max(
        0.0,
        number(
            request.parameters,
            "hotspot_count",
            fire["hotspot_count"]
        )
    )

    # Heat index retained only as an informational metric.
    # It is not used as the fire-risk driver.
    heat_index = heat_index_c(temperature, humidity)


    # -----------------------------
    # Agricultural fire risk model
    # -----------------------------

    # Temperature contribution
    heat_component = clamp(
        (temperature - 30.0) / 15.0 * 100
    )


    # Rainfall deficit contribution
    # Recent rainfall suppresses fire potential.
    if rain >= 100:
        rain_component = 0

    elif rain >= 50:
        rain_component = 30

    else:
        rain_component = clamp(
            (50 - rain) / 50 * 100
        )


    # Humidity correction
    # Moist air reduces vegetation ignition potential.
    if humidity >= 75:
        humidity_factor = 0.4

    elif humidity >= 50:
        humidity_factor = 0.7

    else:
        humidity_factor = 1.0


    dryness_component = clamp(
        rain_component * humidity_factor
    )


    # Wind increases fire spread potential
    wind_component = clamp(
        wind / 50.0 * 100
    )


    # Thermal detections
    hotspot_component = clamp(
        hotspot_count / 10.0 * 100
    )


    score = clamp(
        0.20 * heat_component
        +
        0.35 * dryness_component
        +
        0.20 * wind_component
        +
        0.25 * hotspot_component
    )


    weather_keys = {
        "temperature_max_c",
        "relative_humidity_pct",
        "rain_7d_mm",
        "wind_max_kmh"
    }

    supplied_weather_keys = weather_keys.intersection(
        request.parameters
    )

    external_weather_used = not weather_keys.issubset(
        request.parameters
    )

    hotspot_supplied = "hotspot_count" in request.parameters

    statuses = {DataStatus.MODELLED}

    if external_weather_used:
        statuses.add(weather_status)

    if not hotspot_supplied:
        statuses.add(fire_status)

    if supplied_weather_keys or hotspot_supplied:
        statuses.add(DataStatus.USER_SUPPLIED)


    if (
        fire_status == DataStatus.NEAR_REAL_TIME
        and weather_status == DataStatus.FORECAST
        and not request.parameters
    ):
        evidence_confidence = 0.80

    elif DataStatus.DEMONSTRATION in statuses:
        evidence_confidence = 0.42

    else:
        evidence_confidence = 0.62


    return AnalysisResponse(
        mission=request.mission,

        title="Global Agricultural Fire & Heat Watch",

        coordinates=Coordinates(
            latitude=request.latitude,
            longitude=request.longitude
        ),

        area_hectares=request.area_hectares,

        score=round(score, 1),

        risk_level=risk_level(score),

        confidence=evidence_confidence,


        summary=(
            f"The agricultural fire screening indicates "
            f"{risk_level(score).value} concern based on temperature, "
            "moisture availability, wind and thermal hotspot indicators. "
            "High humidity and recent rainfall reduce fire likelihood, "
            "while dry conditions and confirmed hotspots increase concern."
        ),


        data_status=sorted(
            statuses,
            key=lambda item: item.value
        ),


        metrics=[

            Metric(
                key="heat_index",
                label="Heat index",
                value=round(heat_index, 1),
                unit="°C",
                interpretation=(
                    "Human apparent-temperature indicator shown for context; "
                    "not used as the primary fire-risk driver."
                )
            ),

            Metric(
                key="hotspots",
                label="Nearby thermal detections",
                value=int(hotspot_count),
                unit="detections",
                interpretation=(
                    "Satellite hotspots in the configured search area; "
                    "not all thermal anomalies are fires."
                )
            ),

            Metric(
                key="rain",
                label="Seven-day precipitation",
                value=round(rain, 1),
                unit="mm",
                interpretation=(
                    "Low recent rainfall increases dryness risk, "
                    "while wet conditions reduce immediate fire potential."
                )
            ),

            Metric(
                key="wind",
                label="Maximum wind",
                value=round(wind, 1),
                unit="km/h",
                interpretation=(
                    "Weather-model wind used as a fire-spread proxy."
                )
            ),

        ],


        sources=(
            []
            if hotspot_supplied
            else [nasa_firms(fire_status)]
        )
        +
        (
            []
            if not external_weather_used
            else [open_meteo_weather(weather_status)]
        ),


        caveats=[

            "FIRMS detects thermal anomalies; it does not identify cause, ownership or burned crop area.",

            "Fire likelihood depends strongly on fuel moisture, vegetation condition and local management practices.",

            "Local fire agencies and meteorological services remain authoritative for warnings and response.",

        ],


        geometry=point_geometry(
            request.latitude,
            request.longitude,
            {
                "score": round(score, 1),
                "hotspots": hotspot_count,
                "mission": request.mission.value
            }
        ),
    )
