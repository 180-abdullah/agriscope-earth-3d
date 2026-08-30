from __future__ import annotations

from ..domain import clamp, number, point_geometry, risk_level
from ..models import AnalysisRequest, AnalysisResponse, Coordinates, DataStatus, Metric
from ..provenance import open_meteo_weather
from .common import weather_snapshot


CROP_COEFFICIENTS = {
    "rice": 1.10,
    "maize": 1.05,
    "wheat": 1.00,
    "soybean": 1.00,
    "cotton": 1.05,
    "potato": 1.05,
    "vegetables": 1.00,
    "orchard": 0.90,
}


async def analyze(request: AnalysisRequest) -> AnalysisResponse:

    weather, weather_status = await weather_snapshot(
        request.latitude,
        request.longitude
    )


    crop = str(
        request.parameters.get("crop", "rice")
    ).strip().lower()


    kc = number(
        request.parameters,
        "crop_coefficient",
        CROP_COEFFICIENTS.get(crop, 1.0)
    )


    et0 = max(
        0.0,
        number(
            request.parameters,
            "et0_7d_mm",
            weather["et0_7d_mm"]
        )
    )


    rain = max(
        0.0,
        number(
            request.parameters,
            "rain_7d_mm",
            weather["rain_7d_mm"]
        )
    )


    soil_moisture = clamp(
        number(
            request.parameters,
            "soil_moisture_m3_m3",
            weather["soil_moisture_m3_m3"]
        ),
        0,
        0.7
    )


    effective_rain_fraction = clamp(
        number(
            request.parameters,
            "effective_rain_fraction",
            0.80
        ),
        0,
        1
    )


    application_efficiency = clamp(
        number(
            request.parameters,
            "application_efficiency",
            0.70
        ),
        0.1,
        1
    )


    pump_efficiency = clamp(
        number(
            request.parameters,
            "pump_efficiency",
            0.55
        ),
        0.1,
        1
    )


    total_dynamic_head_m = max(
        0.0,
        number(
            request.parameters,
            "total_dynamic_head_m",
            18.0
        )
    )


    # Water balance

    crop_et = kc * et0

    effective_rain = rain * effective_rain_fraction

    water_balance = crop_et - effective_rain

    deficit = max(
        0,
        water_balance
    )


    # Adjust deficit using soil moisture

    soil_adjustment = clamp(
        (0.30 - soil_moisture) / 0.30,
        0,
        1
    )


    adjusted_deficit = deficit * (
        0.7 + 0.3 * soil_adjustment
    )


    gross_depth = adjusted_deficit / application_efficiency


    volume_m3 = (
        gross_depth
        *
        request.area_hectares
        *
        10
    )


    hydraulic_kwh = (
        1000
        *
        9.80665
        *
        total_dynamic_head_m
        *
        volume_m3
        /
        3600000
    )


    electricity_kwh = (
        hydraulic_kwh
        /
        pump_efficiency
    )


    # Irrigation need score

    if gross_depth <= 10:
        score = 10

    elif gross_depth <= 30:
        score = 30

    elif gross_depth <= 60:
        score = 60

    else:
        score = 85


    # Rainfall correction

    if rain >= 100:
        score *= 0.5

    elif rain >= 50:
        score *= 0.75


    score = clamp(score)


    et0_supplied = "et0_7d_mm" in request.parameters

    rain_supplied = "rain_7d_mm" in request.parameters


    external_weather_used = not (
        et0_supplied
        and rain_supplied
    )


    statuses = {
        DataStatus.CALCULATED,
        DataStatus.USER_SUPPLIED
    }


    if external_weather_used:
        statuses.add(weather_status)


    confidence = (
        0.74
        if weather_status == DataStatus.FORECAST
        else 0.47
    )


    if adjusted_deficit <= 0:

        summary = (
            f"No irrigation deficit detected for {crop}. "
            f"Crop ET was {crop_et:.1f} mm and effective rainfall was "
            f"{effective_rain:.1f} mm."
        )

    else:

        summary = (
            f"The seven-day water balance suggests approximately "
            f"{gross_depth:.1f} mm irrigation requirement for {crop}. "
            "Verify soil moisture and crop growth stage before irrigation."
        )


    return AnalysisResponse(

        mission=request.mission,

        title="Global Irrigation Intelligence",

        coordinates=Coordinates(
            latitude=request.latitude,
            longitude=request.longitude
        ),

        area_hectares=request.area_hectares,

        score=round(score,1),

        risk_level=risk_level(score),

        confidence=confidence,

        summary=summary,

        data_status=sorted(
            statuses,
            key=lambda item:item.value
        ),

        metrics=[

            Metric(
                key="reference_et0",
                label="Reference ET₀",
                value=round(et0,1),
                unit="mm / 7 d",
                interpretation="Atmospheric water demand."
            ),

            Metric(
                key="crop_et",
                label="Crop evapotranspiration",
                value=round(crop_et,1),
                unit="mm / 7 d",
                interpretation="Crop water requirement."
            ),

            Metric(
                key="rainfall",
                label="Rainfall",
                value=round(rain,1),
                unit="mm / 7 d",
                interpretation="Available precipitation."
            ),

            Metric(
                key="soil_moisture",
                label="Soil moisture",
                value=round(soil_moisture,3),
                unit="m³/m³",
                interpretation="Available soil water condition."
            ),

            Metric(
                key="gross_depth",
                label="Required irrigation depth",
                value=round(gross_depth,1),
                unit="mm",
                interpretation="Adjusted irrigation requirement."
            ),

            Metric(
                key="water_volume",
                label="Irrigation volume",
                value=round(volume_m3,0),
                unit="m³",
                interpretation="Required field water volume."
            ),

            Metric(
                key="energy",
                label="Pumping electricity",
                value=round(electricity_kwh,1),
                unit="kWh",
                interpretation="Estimated pumping energy."
            ),
        ],


        sources=[
            open_meteo_weather(weather_status)
        ]
        if external_weather_used
        else [],


        caveats=[

            "This is a seven-day water balance screening model, not a full irrigation scheduling model.",

            "Crop coefficient changes with variety, growth stage and management.",

            "Field soil moisture measurement improves irrigation decisions."

        ],


        geometry=point_geometry(
            request.latitude,
            request.longitude,
            {
                "score":round(score,1),
                "gross_irrigation_mm":gross_depth,
                "mission":request.mission.value
            }
        )

    )
