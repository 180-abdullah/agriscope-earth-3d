from __future__ import annotations

from ..domain import clamp, deterministic_unit, number, point_geometry, risk_level
from ..models import AnalysisRequest, AnalysisResponse, Coordinates, DataStatus, Metric
from ..provenance import (
    earth_search_sentinel,
    earth_search_unavailable,
    open_meteo_weather,
    user_vegetation_indices,
)
from ..services.sentinel import sentinel2_indices
from .common import weather_snapshot


async def analyze(request: AnalysisRequest) -> AnalysisResponse:
    weather, weather_status = await weather_snapshot(
        request.latitude,
        request.longitude
    )

    seed = deterministic_unit(
        request.latitude,
        request.longitude,
        "crop"
    )

    has_ndvi = "ndvi" in request.parameters
    has_ndmi = "ndmi" in request.parameters
    supplied_indices = has_ndvi and has_ndmi

    live_requested = bool(
        request.parameters.get(
            "use_live_sentinel",
            not (has_ndvi or has_ndmi)
        )
    )

    satellite: dict | None = None
    satellite_error: str | None = None
    index_statuses: list[DataStatus] = []


    # -----------------------------
    # Vegetation index acquisition
    # -----------------------------

    if supplied_indices:

        ndvi = clamp(
            number(request.parameters, "ndvi", 0.5),
            -1,
            1
        )

        ndmi = clamp(
            number(request.parameters, "ndmi", 0.2),
            -1,
            1
        )

        index_statuses.append(
            DataStatus.USER_SUPPLIED
        )


    elif live_requested:

        try:

            satellite = await sentinel2_indices(
                request.latitude,
                request.longitude,
                request.area_hectares,
                lookback_days=int(
                    number(
                        request.parameters,
                        "sentinel_lookback_days",
                        120
                    )
                ),
                max_cloud_pct=number(
                    request.parameters,
                    "sentinel_max_cloud_pct",
                    35
                ),
            )


            ndvi = clamp(
                float(satellite["ndvi"]),
                -1,
                1
            )

            ndmi = clamp(
                float(satellite["ndmi"]),
                -1,
                1
            )


            index_statuses.append(
                DataStatus.OBSERVED
            )


        except Exception as exc:

            satellite_error = str(exc)

            ndvi = clamp(
                number(
                    request.parameters,
                    "ndvi",
                    0.32 + seed * 0.38
                ),
                -1,
                1
            )

            ndmi = clamp(
                number(
                    request.parameters,
                    "ndmi",
                    0.05 + (1 - seed) * 0.34
                ),
                -1,
                1
            )

            index_statuses.extend(
                [
                    DataStatus.UNAVAILABLE,
                    DataStatus.DEMONSTRATION
                ]
            )


    else:

        ndvi = clamp(
            number(
                request.parameters,
                "ndvi",
                0.32 + seed * 0.38
            ),
            -1,
            1
        )

        ndmi = clamp(
            number(
                request.parameters,
                "ndmi",
                0.05 + (1 - seed) * 0.34
            ),
            -1,
            1
        )


        if has_ndvi or has_ndmi:

            index_statuses.extend(
                [
                    DataStatus.USER_SUPPLIED,
                    DataStatus.DEMONSTRATION
                ]
            )

        else:

            index_statuses.append(
                DataStatus.DEMONSTRATION
            )


    # -----------------------------
    # Weather inputs
    # -----------------------------

    soil_moisture = clamp(
        number(
            request.parameters,
            "soil_moisture_m3_m3",
            weather["soil_moisture_m3_m3"]
        ),
        0,
        0.7
    )


    max_temp = number(
        request.parameters,
        "temperature_max_c",
        weather["temperature_max_c"]
    )


    rainfall = max(
        0,
        number(
            request.parameters,
            "rain_7d_mm",
            weather["rain_7d_mm"]
        )
    )


    weather_keys = {
        "soil_moisture_m3_m3",
        "temperature_max_c",
        "rain_7d_mm",
    }


    supplied_weather_keys = weather_keys.intersection(
        request.parameters
    )


    external_weather_used = not weather_keys.issubset(
        request.parameters
    )


    # -----------------------------
    # Crop stress model
    # Bangladesh/Sylhet calibration
    # -----------------------------


    # Vegetation anomaly
    # Lower NDVI indicates possible stress,
    # while allowing normal crop-stage variation.

    ndvi_stress = clamp(
        (0.45 - ndvi) / 0.35 * 100
    )


    # Canopy moisture condition

    ndmi_stress = clamp(
        (0.15 - ndmi) / 0.35 * 100
    )


    # Soil moisture deficit

    moisture_stress = clamp(
        (0.18 - soil_moisture) / 0.18 * 100
    )


    # Extreme heat stress only
    # Normal tropical warmth is not treated as stress.

    heat_stress = clamp(
        (max_temp - 35.0) / 8.0 * 100
    )


    # Rainfall deficit adjustment
    # Bangladesh monsoon adaptation

    if rainfall >= 80:

        rainfall_stress = 0

    elif rainfall >= 40:

        rainfall_stress = 30

    else:

        rainfall_stress = clamp(
            (40 - rainfall) / 40 * 100
        )


    score = clamp(
        0.35 * ndvi_stress
        +
        0.25 * ndmi_stress
        +
        0.15 * moisture_stress
        +
        0.15 * heat_stress
        +
        0.10 * rainfall_stress
    )


    affected_area = (
        request.area_hectares
        *
        clamp(
            score / 100,
            0,
            0.80
        )
    )


    # -----------------------------
    # Confidence
    # -----------------------------

    if satellite and external_weather_used and weather_status == DataStatus.FORECAST:

        evidence_confidence = 0.78

    elif supplied_indices and external_weather_used and weather_status == DataStatus.FORECAST:

        evidence_confidence = 0.72

    elif (
        DataStatus.DEMONSTRATION in index_statuses
        or
        (
            external_weather_used
            and
            weather_status == DataStatus.DEMONSTRATION
        )
    ):

        evidence_confidence = 0.42

    else:

        evidence_confidence = 0.58



    # -----------------------------
    # Metrics
    # -----------------------------

    metrics = [

        Metric(
            key="ndvi",
            label="NDVI",
            value=round(ndvi, 3),
            unit="index",
            interpretation=(
                "Vegetation greenness indicator. "
                "Crop-stage specific baselines are required "
                "for detailed diagnosis."
            ),
        ),


        Metric(
            key="ndmi",
            label="NDMI",
            value=round(ndmi, 3),
            unit="index",
            interpretation=(
                "Canopy moisture proxy derived from vegetation reflectance."
            ),
        ),


        Metric(
            key="soil_moisture",
            label="Surface soil moisture",
            value=round(soil_moisture, 3),
            unit="m³/m³",
            interpretation=(
                "Modelled moisture estimate, not direct field measurement."
            ),
        ),


        Metric(
            key="temperature",
            label="Maximum temperature",
            value=round(max_temp, 1),
            unit="°C",
            interpretation=(
                "Extreme heat contribution only; normal tropical temperatures "
                "are not classified as crop stress."
            ),
        ),


        Metric(
            key="rainfall",
            label="Seven-day rainfall",
            value=round(rainfall, 1),
            unit="mm",
            interpretation=(
                "Rainfall availability modifies moisture stress; recent wet "
                "conditions reduce drought-related crop stress."
            ),
        ),


        Metric(
            key="affected_area",
            label="Priority verification area",
            value=round(affected_area, 1),
            unit="ha",
            interpretation=(
                "Screened area requiring field verification, "
                "not confirmed damage."
            ),
        ),
    ]


    sources = (
        [open_meteo_weather(weather_status)]
        if external_weather_used
        else []
    )


    caveats = [

        "NDVI and NDMI thresholds vary with crop type, growth stage, cultivar, soil background and atmospheric conditions.",

        "Optical vegetation indices indicate abnormal vegetation response but cannot identify the exact cause of stress.",

        "Field observations are required to distinguish drought, disease, nutrient deficiency or management problems.",

    ]


    if satellite:

        metrics.extend(
            [

                Metric(
                    key="sentinel_valid_pixels",
                    label="Clear valid pixels",
                    value=round(
                        float(
                            satellite["valid_pixel_fraction"]
                        )
                        * 100,
                        1
                    ),
                    unit="% of sample",
                    interpretation=(
                        "Pixels retained after Sentinel-2 quality masking."
                    ),
                ),


                Metric(
                    key="sentinel_scene_cloud",
                    label="Scene cloud metadata",
                    value=float(
                        satellite["scene_cloud_cover_pct"]
                    ),
                    unit="%",
                    interpretation=(
                        "Whole-scene cloud metadata, not target-only cloud fraction."
                    ),
                ),

            ]
        )


        sources.insert(
            0,
            earth_search_sentinel(satellite)
        )


        caveats.append(
            f"Sentinel processing used scene {satellite['item_id']} "
            "and should be complemented with multi-date analysis "
            "for research applications."
        )


    elif satellite_error:

        sources.insert(
            0,
            earth_search_unavailable(satellite_error)
        )


        caveats.append(
            "Live Sentinel-2 processing failed; vegetation indices shown are demonstration values."
        )


    else:

        sources.insert(
            0,
            user_vegetation_indices(
                DataStatus.USER_SUPPLIED
                if supplied_indices
                else DataStatus.DEMONSTRATION
            )
        )


    return AnalysisResponse(

        mission=request.mission,

        title="Global Crop Stress Patrol",

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

        confidence=evidence_confidence,


        summary=(
            f"The crop stress screening indicates "
            f"{risk_level(score).value} stress potential. "
            "Vegetation condition, moisture availability and climate indicators "
            "are combined to prioritize field verification. "
            "The result does not diagnose a specific pest, disease or nutrient deficiency."
        ),


        data_status=sorted(
            {
                *index_statuses,
                *(
                    {weather_status}
                    if external_weather_used
                    else set()
                ),
                *(
                    {DataStatus.USER_SUPPLIED}
                    if supplied_weather_keys
                    else set()
                ),
                DataStatus.MODELLED,
            },
            key=lambda item: item.value,
        ),


        metrics=metrics,

        sources=sources,

        caveats=caveats,


        geometry=point_geometry(
            request.latitude,
            request.longitude,
            {
                "score": round(score, 1),
                "ndvi": ndvi,
                "ndmi": ndmi,
                "mission": request.mission.value,
                "sentinel_item_id": (
                    satellite.get("item_id")
                    if satellite
                    else None
                ),
                "acquisition_datetime": (
                    satellite.get("acquisition_datetime")
                    if satellite
                    else None
                ),
            },
        ),
    )
