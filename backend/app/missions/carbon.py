from __future__ import annotations

from ..domain import clamp, number, point_geometry, risk_level
from ..models import AnalysisRequest, AnalysisResponse, Coordinates, DataStatus, Metric
from ..provenance import ipcc


GWP_CH4 = 27.2
GWP_N2O = 273.0
EF1_DIRECT_N2O_N = 0.01
RICE_CH4_EF_KG_HA_DAY = 1.19
DIESEL_KG_CO2_L = 2.68


async def analyze(request: AnalysisRequest) -> AnalysisResponse:
    p = request.parameters
    defaults_used = len(p) == 0
    nitrogen_kg_ha = max(0.0, number(p, "fertilizer_n_kg_ha", 110.0))
    rice_area_ha = clamp(number(p, "rice_area_hectares", request.area_hectares * 0.45), 0, request.area_hectares)
    rice_days = max(0.0, number(p, "rice_cultivation_days", 110.0))
    rice_water_factor = max(0.0, number(p, "rice_water_regime_factor", 1.0))
    rice_organic_factor = max(0.0, number(p, "rice_organic_amendment_factor", 1.0))
    diesel_litres = max(0.0, number(p, "diesel_litres", 65.0 * request.area_hectares))
    electricity_kwh = max(0.0, number(p, "electricity_kwh", 0.0))
    grid_factor = max(0.0, number(p, "grid_kg_co2_per_kwh", 0.45))
    livestock_head = max(0.0, number(p, "livestock_head", 0.0))
    enteric_kg_ch4_head_year = max(0.0, number(p, "enteric_kg_ch4_head_year", 47.0))
    inventory_fraction_year = clamp(number(p, "inventory_fraction_year", 1.0), 0, 1)

    total_n = nitrogen_kg_ha * request.area_hectares
    direct_n2o_n = total_n * EF1_DIRECT_N2O_N
    n2o_kg = direct_n2o_n * 44.0 / 28.0
    fertilizer_co2e = n2o_kg * GWP_N2O

    rice_ch4_kg = RICE_CH4_EF_KG_HA_DAY * rice_area_ha * rice_days * rice_water_factor * rice_organic_factor
    rice_co2e = rice_ch4_kg * GWP_CH4
    diesel_co2e = diesel_litres * DIESEL_KG_CO2_L
    electricity_co2e = electricity_kwh * grid_factor
    enteric_ch4_kg = livestock_head * enteric_kg_ch4_head_year * inventory_fraction_year
    livestock_co2e = enteric_ch4_kg * GWP_CH4
    total_co2e = fertilizer_co2e + rice_co2e + diesel_co2e + electricity_co2e + livestock_co2e
    intensity_t_ha = total_co2e / 1000.0 / request.area_hectares
    score = clamp(intensity_t_ha / 12.0 * 100.0)
    input_status = DataStatus.DEMONSTRATION if defaults_used else DataStatus.USER_SUPPLIED

    return AnalysisResponse(
        mission=request.mission,
        title="Global Agricultural Carbon Scanner",
        coordinates=Coordinates(latitude=request.latitude, longitude=request.longitude),
        area_hectares=request.area_hectares,
        score=round(score, 1),
        risk_level=risk_level(score),
        confidence=0.70 if not defaults_used else 0.38,
        summary=(
            f"The Tier 1 screening estimate is {total_co2e/1000:,.1f} t CO₂e for the supplied activity data, or {intensity_t_ha:.2f} t CO₂e/ha. "
            "This is a decision-support estimate, not an audited product footprint or national inventory."
        ),
        data_status=sorted({input_status, DataStatus.MODELLED, DataStatus.CALCULATED}, key=lambda item: item.value),
        metrics=[
            Metric(key="total", label="Total screening emissions", value=round(total_co2e / 1000.0, 2), unit="t CO₂e", interpretation="Sum of included Tier 1 source categories."),
            Metric(key="intensity", label="Area-based intensity", value=round(intensity_t_ha, 3), unit="t CO₂e/ha", interpretation="Total divided by selected agricultural area."),
            Metric(key="fertilizer", label="Direct fertilizer N₂O", value=round(fertilizer_co2e / 1000.0, 2), unit="t CO₂e", interpretation="Direct soil N₂O only; indirect pathways are not included in this release."),
            Metric(key="rice", label="Rice methane", value=round(rice_co2e / 1000.0, 2), unit="t CO₂e", interpretation="Baseline daily factor adjusted by water and organic-amendment scalars."),
            Metric(key="energy", label="Diesel + electricity", value=round((diesel_co2e + electricity_co2e) / 1000.0, 2), unit="t CO₂e", interpretation="Combustion and user-supplied grid-factor estimate."),
            Metric(key="livestock", label="Enteric methane", value=round(livestock_co2e / 1000.0, 2), unit="t CO₂e", interpretation="Tier 1 head-count estimate for the selected inventory fraction."),
        ],
        sources=[ipcc(DataStatus.MODELLED)],
        caveats=[
            "Default factors are illustrative Tier 1 screening values; use country, species, system and technology-specific factors where available.",
            "Indirect soil N₂O, manure management, upstream input production, soil carbon change and transport are outside the default boundary.",
            "Global-warming potentials and inventory boundaries must be kept consistent when comparing scenarios.",
        ],
        geometry=point_geometry(request.latitude, request.longitude, {"score": round(score, 1), "total_t_co2e": total_co2e / 1000.0, "mission": request.mission.value}),
    )
