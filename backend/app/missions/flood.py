from __future__ import annotations

from ..domain import clamp, number, point_geometry, risk_level
from ..models import AnalysisRequest, AnalysisResponse, Coordinates, DataStatus, Metric
from ..provenance import open_meteo_flood, open_meteo_weather
from .common import flood_snapshot, weather_snapshot


async def analyze(request: AnalysisRequest) -> AnalysisResponse:
    weather, weather_status = await weather_snapshot(
        request.latitude,
        request.longitude
    )

    flood, flood_status = await flood_snapshot(
        request.latitude,
        request.longitude
    )

    discharge_ratio = number(
        request.parameters,
        "discharge_ratio",
        flood["discharge_ratio"]
    )

    rain = max(
        0.0,
        number(
            request.parameters,
            "rain_7d_mm",
            weather["rain_7d_mm"]
        )
    )

    crop_stage_sensitivity = clamp(
        number(
            request.parameters,
            "crop_stage_sensitivity",
            0.75
        ),
        0,
        1
    )

    drainage_vulnerability = clamp(
        number(
            request.parameters,
            "drainage_vulnerability",
            0.55
        ),
        0,
        1
    )


    # ------------------------------------
    # Flood hazard model
    # ------------------------------------
    # Flood occurrence is controlled by
    # water availability first.
    # Vulnerability modifies impact,
    # but cannot create flood hazard.
    

    # River discharge anomaly
    discharge_component = clamp(
        (discharge_ratio - 0.9) / 1.5 * 100
    )


    # Rainfall contribution
    # Rainfall increases flood pressure,
    # but rainfall alone does not equal flooding.

    if rain >= 200:
        rain_component = 100

    elif rain >= 100:
        rain_component = 60

    elif rain >= 50:
        rain_component = 30

    else:
        rain_component = 10


    # Combined physical hazard
    hazard_score = (
        0.65 * discharge_component
        +
        0.35 * rain_component
    )


    # Vulnerability adjustment
    # Maximum approximately 30% increase

    vulnerability_factor = (
        1
        +
        0.15 * crop_stage_sensitivity
        +
        0.15 * drainage_vulnerability
    )


    score = clamp(
        hazard_score * vulnerability_factor
    )


    # Screened exposure
    exposed_fraction = clamp(
        score / 100.0,
        0,
        0.80
    )

    exposed_area = (
        request.area_hectares
        *
        exposed_fraction
    )


    discharge_supplied = (
        "discharge_ratio"
        in request.parameters
    )

    rain_supplied = (
        "rain_7d_mm"
        in request.parameters
    )


    user_status = (
        {DataStatus.USER_SUPPLIED}
        if request.parameters
        else set()
    )


    used_flood_status = (
        DataStatus.USER_SUPPLIED
        if discharge_supplied
        else flood_status
    )


    used_weather_status = (
        DataStatus.USER_SUPPLIED
        if rain_supplied
        else weather_status
    )


    confidence = (
        0.78
        if (
            used_flood_status == DataStatus.FORECAST
            and
            used_weather_status == DataStatus.FORECAST
        )
        else 0.58
    )


    if (
        DataStatus.DEMONSTRATION
        in {
            used_flood_status,
            used_weather_status
        }
    ):
        confidence = 0.43


    statuses = sorted(
        {
            used_weather_status,
            used_flood_status,
            DataStatus.MODELLED,
            *user_status
        },
        key=lambda item: item.value
    )


    return AnalysisResponse(

        mission=request.mission,

        title="Global Flood & Crop Exposure Watch",


        coordinates=Coordinates(
            latitude=request.latitude,
            longitude=request.longitude
        ),


        area_hectares=request.area_hectares,


        score=round(
            score,
            1
        ),


        risk_level=risk_level(score),


        confidence=confidence,


        summary=(
            f"Screening indicates "
            f"{risk_level(score).value} flood-exposure potential "
            "for the selected agricultural area. "
            "Flood likelihood is primarily driven by river discharge "
            "and rainfall pressure, while crop stage and drainage "
            "modify potential impact."
        ),


        data_status=statuses,


        metrics=[

            Metric(
                key="discharge_ratio",
                label="Forecast peak / mean discharge",
                value=round(
                    discharge_ratio,
                    2
                ),
                unit="ratio",
                interpretation=(
                    "Relative river discharge anomaly "
                    "indicator used for flood screening."
                )
            ),


            Metric(
                key="rain_7d",
                label="Forecast precipitation",
                value=round(
                    rain,
                    1
                ),
                unit="mm / 7 d",
                interpretation=(
                    "Recent precipitation contributes "
                    "to flood pressure but does not alone "
                    "confirm flooding."
                )
            ),


            Metric(
                key="exposed_area",
                label="Screened crop exposure",
                value=round(
                    exposed_area,
                    1
                ),
                unit="ha",
                interpretation=(
                    "Modelled screening area, "
                    "not measured flood loss."
                )
            ),


            Metric(
                key="exposed_fraction",
                label="Screened exposure share",
                value=round(
                    exposed_fraction * 100,
                    1
                ),
                unit="%",
                interpretation=(
                    "Derived from flood hazard "
                    "and vulnerability adjustment."
                )
            ),
        ],


        sources=(
            []
            if discharge_supplied
            else [
                open_meteo_flood(
                    flood_status
                )
            ]
        )
        +
        (
            []
            if rain_supplied
            else [
                open_meteo_weather(
                    weather_status
                )
            ]
        ),


        caveats=[

            "Discharge is assigned from the largest modelled river near the coordinate and may not represent small canals or isolated fields.",

            "Crop exposure is a screening calculation, not a flood-depth, damage or yield-loss model.",

            "A demonstration status means upstream data were unavailable and deterministic sample values were used.",

        ],


        geometry=point_geometry(
            request.latitude,
            request.longitude,
            {
                "score": round(
                    score,
                    1
                ),
                "mission": request.mission.value
            }
        ),
    )
