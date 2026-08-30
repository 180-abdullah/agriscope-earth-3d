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
    weather, weather_status = await weather_snapshot(request.latitude, request.longitude)
    crop = str(request.parameters.get("crop", "maize")).strip().lower()
    kc = number(request.parameters, "crop_coefficient", CROP_COEFFICIENTS.get(crop, 1.0))
    et0 = max(0.0, number(request.parameters, "et0_7d_mm", weather["et0_7d_mm"]))
    rain = max(0.0, number(request.parameters, "rain_7d_mm", weather["rain_7d_mm"]))
    effective_rain_fraction = clamp(number(request.parameters, "effective_rain_fraction", 0.80), 0, 1)
    application_efficiency = clamp(number(request.parameters, "application_efficiency", 0.70), 0.1, 1)
    pump_efficiency = clamp(number(request.parameters, "pump_efficiency", 0.55), 0.1, 1)
    total_dynamic_head_m = max(0.0, number(request.parameters, "total_dynamic_head_m", 18.0))

    crop_et = kc * et0
    effective_rain = rain * effective_rain_fraction
    raw_water_balance = crop_et - effective_rain
    net_depth = max(0.0, raw_water_balance)
    gross_depth = net_depth / application_efficiency
    volume_m3 = gross_depth * request.area_hectares * 10.0
    hydraulic_kwh = 1000.0 * 9.80665 * total_dynamic_head_m * volume_m3 / 3_600_000.0
    electricity_kwh = hydraulic_kwh / pump_efficiency
    score = clamp(gross_depth / 65.0 * 100.0)
    et0_supplied = "et0_7d_mm" in request.parameters
    rain_supplied = "rain_7d_mm" in request.parameters
    external_weather_used = not (et0_supplied and rain_supplied)
    statuses = {DataStatus.CALCULATED, DataStatus.USER_SUPPLIED}
    if external_weather_used:
        statuses.add(weather_status)
    evidence_confidence = 0.74 if external_weather_used and weather_status == DataStatus.FORECAST else 0.62
    if external_weather_used and weather_status == DataStatus.DEMONSTRATION:
        evidence_confidence = 0.47
    if net_depth <= 0:
        summary = (
            f"No seven-day irrigation deficit is indicated: crop ET is {crop_et:.1f} mm and effective rainfall is "
            f"{effective_rain:.1f} mm, leaving a {raw_water_balance:.1f} mm balance. Gross depth, pumping volume and "
            "energy are therefore zero. Pump head and efficiency cannot change energy until the required volume is above zero."
        )
    else:
        summary = (
            f"The seven-day screening water requirement for {crop} is approximately {gross_depth:.1f} mm after "
            f"effective rainfall and {application_efficiency:.0%} application efficiency. Verify soil-water status and "
            "the crop coefficient before operating equipment."
        )

    return AnalysisResponse(
        mission=request.mission,
        title="Global Irrigation Intelligence",
        coordinates=Coordinates(latitude=request.latitude, longitude=request.longitude),
        area_hectares=request.area_hectares,
        score=round(score, 1),
        risk_level=risk_level(score),
        confidence=evidence_confidence,
        summary=summary,
        data_status=sorted(statuses, key=lambda item: item.value),
        metrics=[
            Metric(key="reference_et0", label="Reference ET₀", value=round(et0, 1), unit="mm / 7 d", interpretation="Forecast or supplied FAO-56 reference evapotranspiration at the target coordinate."),
            Metric(key="rainfall", label="Total rainfall", value=round(rain, 1), unit="mm / 7 d", interpretation="Forecast or supplied precipitation before the effective-rain fraction is applied."),
            Metric(key="crop_coefficient", label="Crop coefficient", value=round(kc, 2), unit="Kc", interpretation="Selected or supplied coefficient used to convert ET₀ to crop ET."),
            Metric(key="crop_et", label="Crop evapotranspiration", value=round(crop_et, 1), unit="mm / 7 d", interpretation="ET₀ multiplied by the selected crop coefficient."),
            Metric(key="effective_rain", label="Effective rainfall", value=round(effective_rain, 1), unit="mm / 7 d", interpretation="Forecast rainfall multiplied by the assumed effective fraction."),
            Metric(key="raw_balance", label="Crop ET minus effective rain", value=round(raw_water_balance, 1), unit="mm / 7 d", interpretation="A value at or below zero produces no irrigation deficit in this seven-day screening balance."),
            Metric(key="net_depth", label="Net irrigation deficit", value=round(net_depth, 1), unit="mm", interpretation="Positive part of crop ET minus effective rainfall, before application losses."),
            Metric(key="gross_depth", label="Gross irrigation depth", value=round(gross_depth, 1), unit="mm", interpretation="Net need adjusted for application efficiency."),
            Metric(key="water_volume", label="Irrigation volume", value=round(volume_m3, 0), unit="m³", interpretation="One millimetre over one hectare equals ten cubic metres."),
            Metric(key="energy", label="Estimated pumping electricity", value=round(electricity_kwh, 1), unit="kWh", interpretation="Hydraulic energy adjusted for pump efficiency."),
        ],
        sources=[open_meteo_weather(weather_status)] if external_weather_used else [],
        caveats=[
            "The calculation is a screening water balance and does not simulate root-zone storage or irrigation timing.",
            "A zero result means this seven-day forecast balance has no positive deficit; it does not mean the crop will never require irrigation.",
            "Crop coefficients vary by growth stage, climate, variety and management.",
            "Actual pumping energy also depends on motor, transmission, pipe friction and operating condition.",
        ],
        geometry=point_geometry(request.latitude, request.longitude, {"score": round(score, 1), "gross_irrigation_mm": gross_depth, "mission": request.mission.value}),
    )
