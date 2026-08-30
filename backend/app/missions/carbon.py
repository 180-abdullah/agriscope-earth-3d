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


    fertilizer_n = max(
        0,
        number(
            p,
            "fertilizer_n_kg_ha",
            110
        )
    )


    rice_area = clamp(
        number(
            p,
            "rice_area_hectares",
            request.area_hectares * 0.45
        ),
        0,
        request.area_hectares
    )


    rice_days = max(
        0,
        number(
            p,
            "rice_cultivation_days",
            110
        )
    )


    water_factor = max(
        0,
        number(
            p,
            "rice_water_regime_factor",
            1.0
        )
    )


    organic_factor = max(
        0,
        number(
            p,
            "rice_organic_amendment_factor",
            1.0
        )
    )


    diesel = max(
        0,
        number(
            p,
            "diesel_litres",
            65 * request.area_hectares
        )
    )


    electricity = max(
        0,
        number(
            p,
            "electricity_kwh",
            0
        )
    )


    grid_factor = max(
        0,
        number(
            p,
            "grid_kg_co2_per_kwh",
            0.45
        )
    )


    livestock = max(
        0,
        number(
            p,
            "livestock_head",
            0
        )
    )


    enteric_factor = max(
        0,
        number(
            p,
            "enteric_kg_ch4_head_year",
            47
        )
    )



    inventory_fraction = clamp(
        number(
            p,
            "inventory_fraction_year",
            1
        ),
        0,
        1
    )



    # Fertilizer N2O

    total_n = fertilizer_n * request.area_hectares

    direct_n2o_n = total_n * EF1_DIRECT_N2O_N

    n2o_kg = direct_n2o_n * 44 / 28

    fertilizer_co2e = n2o_kg * GWP_N2O



    # Rice methane

    rice_ch4 = (
        RICE_CH4_EF_KG_HA_DAY
        *
        rice_area
        *
        rice_days
        *
        water_factor
        *
        organic_factor
    )

    rice_co2e = rice_ch4 * GWP_CH4



    # Energy

    diesel_co2e = diesel * DIESEL_KG_CO2_L

    electricity_co2e = electricity * grid_factor



    # Livestock

    enteric_ch4 = (
        livestock
        *
        enteric_factor
        *
        inventory_fraction
    )

    livestock_co2e = enteric_ch4 * GWP_CH4



    total_co2e = (
        fertilizer_co2e
        +
        rice_co2e
        +
        diesel_co2e
        +
        electricity_co2e
        +
        livestock_co2e
    )



    intensity = (
        total_co2e
        /
        1000
        /
        request.area_hectares
    )



    # Carbon intensity scoring

    if intensity < 2:
        score = 15

    elif intensity < 5:
        score = 40

    elif intensity < 8:
        score = 70

    else:
        score = 90



    score = clamp(score)



    # Dominant source

    sources = {

        "Rice methane": rice_co2e,

        "Fertilizer N2O": fertilizer_co2e,

        "Energy": diesel_co2e + electricity_co2e,

        "Livestock": livestock_co2e,

    }


    dominant_source = max(
        sources,
        key=sources.get
    )



    status = (
        DataStatus.DEMONSTRATION
        if defaults_used
        else DataStatus.USER_SUPPLIED
    )



    return AnalysisResponse(

        mission=request.mission,

        title="Global Agricultural Carbon Scanner",

        coordinates=Coordinates(
            latitude=request.latitude,
            longitude=request.longitude
        ),

        area_hectares=request.area_hectares,

        score=round(score,1),

        risk_level=risk_level(score),

        confidence=(
            0.70
            if not defaults_used
            else 0.38
        ),


        summary=(

            f"The estimated agricultural carbon intensity is "
            f"{intensity:.2f} t CO₂e/ha. "

            f"The dominant emission source is {dominant_source}. "

            "This is a Tier-1 screening estimate and not an audited carbon inventory."

        ),


        data_status=[
            status,
            DataStatus.MODELLED,
            DataStatus.CALCULATED
        ],


        metrics=[


            Metric(
                key="total",
                label="Total emissions",
                value=round(total_co2e/1000,2),
                unit="t CO₂e",
                interpretation="Combined estimated agricultural emissions."
            ),


            Metric(
                key="intensity",
                label="Carbon intensity",
                value=round(intensity,3),
                unit="t CO₂e/ha",
                interpretation="Emission intensity per agricultural hectare."
            ),


            Metric(
                key="rice",
                label="Rice methane",
                value=round(rice_co2e/1000,2),
                unit="t CO₂e",
                interpretation="Methane emission from flooded rice cultivation."
            ),


            Metric(
                key="fertilizer",
                label="Fertilizer N2O",
                value=round(fertilizer_co2e/1000,2),
                unit="t CO₂e",
                interpretation="Direct soil nitrous oxide estimate."
            ),


            Metric(
                key="livestock",
                label="Livestock methane",
                value=round(livestock_co2e/1000,2),
                unit="t CO₂e",
                interpretation="Enteric methane estimate."
            ),


            Metric(
                key="energy",
                label="Energy emissions",
                value=round((diesel_co2e+electricity_co2e)/1000,2),
                unit="t CO₂e",
                interpretation="Fuel and electricity emissions."
            ),

        ],


        sources=[
            ipcc(DataStatus.MODELLED)
        ],


        caveats=[

            "Tier-1 emission factors are screening values; local inventory factors improve accuracy.",

            "Soil carbon change, upstream fertilizer production and transport emissions are excluded.",

            "Comparisons require the same boundary, emission factors and GWP values."

        ],


        geometry=point_geometry(

            request.latitude,

            request.longitude,

            {
                "score":round(score,1),
                "carbon_intensity":round(intensity,3),
                "mission":request.mission.value
            }

        )

    )
