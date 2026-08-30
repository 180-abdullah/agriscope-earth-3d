from __future__ import annotations

from ..domain import clamp, deterministic_unit, number, point_geometry, risk_level
from ..models import AnalysisRequest, AnalysisResponse, Coordinates, DataStatus, Metric
from ..provenance import user_class_summaries


async def analyze(request: AnalysisRequest) -> AnalysisResponse:
    seed = deterministic_unit(request.latitude, request.longitude, "land")

    class_keys = {
        "baseline_water_pct",
        "current_water_pct",
        "baseline_cropland_pct",
        "current_cropland_pct",
        "baseline_tree_pct",
        "current_tree_pct",
    }

    supplied = (
        class_keys.issubset(request.parameters)
        and bool(request.parameters.get("class_data_confirmed", False))
    )


    # Land-cover percentages

    baseline_water = clamp(
        number(
            request.parameters,
            "baseline_water_pct",
            25 + seed * 15
        ),
        0,
        100
    )

    current_water = clamp(
        number(
            request.parameters,
            "current_water_pct",
            baseline_water - seed * 3
        ),
        0,
        100
    )


    baseline_crop = clamp(
        number(
            request.parameters,
            "baseline_cropland_pct",
            35 + seed * 20
        ),
        0,
        100
    )

    current_crop = clamp(
        number(
            request.parameters,
            "current_cropland_pct",
            baseline_crop + seed * 2
        ),
        0,
        100
    )


    baseline_tree = clamp(
        number(
            request.parameters,
            "baseline_tree_pct",
            35 + seed * 20
        ),
        0,
        100
    )

    current_tree = clamp(
        number(
            request.parameters,
            "current_tree_pct",
            baseline_tree - seed * 2
        ),
        0,
        100
    )


    # Change calculation

    water_change = current_water - baseline_water
    crop_change = current_crop - baseline_crop
    tree_change = current_tree - baseline_tree


    # Negative environmental changes

    wetland_loss = max(0, -water_change)
    tree_loss = max(0, -tree_change)

    # Agricultural expansion pressure

    crop_expansion = max(0, crop_change)


    # Normalize impacts

    wetland_component = clamp(
        wetland_loss / 10 * 100
    )

    tree_component = clamp(
        tree_loss / 10 * 100
    )

    conversion_component = clamp(
        crop_expansion / 10 * 100
    )


    # Weighted land-change pressure score

    score = clamp(
        0.45 * wetland_component
        +
        0.40 * tree_component
        +
        0.15 * conversion_component
    )


    # Estimated changed area

    changed_fraction = clamp(
        (
            abs(water_change)
            +
            abs(tree_change)
            +
            abs(crop_change)
        ) / 100,
        0,
        0.50
    )

    changed_area = (
        request.area_hectares
        *
        changed_fraction
    )


    status = (
        DataStatus.USER_SUPPLIED
        if supplied
        else DataStatus.DEMONSTRATION
    )


    return AnalysisResponse(

        mission=request.mission,

        title="Global Wetland & Land-Use Change Audit",

        coordinates=Coordinates(
            latitude=request.latitude,
            longitude=request.longitude
        ),

        area_hectares=request.area_hectares,

        score=round(score, 1),

        risk_level=risk_level(score),

        confidence=0.76 if supplied else 0.38,


        summary=(
            f"The land-cover transition screening indicates "
            f"{risk_level(score).value} ecological change pressure. "
            "The result identifies possible wetland, vegetation and land-use transition signals "
            "and requires satellite-based validation before reporting actual change."
        ),


        data_status=[
            status,
            DataStatus.CALCULATED
        ],


        metrics=[

            Metric(
                key="water_change",
                label="Wetland / water change",
                value=round(water_change,2),
                unit="percentage points",
                interpretation=(
                    "Negative values indicate possible wetland or surface-water reduction."
                )
            ),


            Metric(
                key="tree_change",
                label="Tree-cover change",
                value=round(tree_change,2),
                unit="percentage points",
                interpretation=(
                    "Negative values indicate vegetation-cover reduction."
                )
            ),


            Metric(
                key="cropland_change",
                label="Cropland change",
                value=round(crop_change,2),
                unit="percentage points",
                interpretation=(
                    "Positive values indicate agricultural expansion."
                )
            ),


            Metric(
                key="changed_area",
                label="Approximate changed area",
                value=round(changed_area,1),
                unit="ha",
                interpretation=(
                    "Screening estimate based on class percentage differences."
                )
            ),

        ],


        sources=[
            user_class_summaries(status)
        ],


        caveats=[

            "Class percentages cannot identify exact transition locations; pixel-level change detection is preferred.",

            "Seasonal variation in wetlands and vegetation can create apparent change.",

            "Default values are demonstrations and must not be interpreted as observed land-cover change."

        ],


        geometry=point_geometry(
            request.latitude,
            request.longitude,
            {
                "score":round(score,1),
                "water_change_pp":water_change,
                "tree_change_pp":tree_change,
                "mission":request.mission.value
            }
        ),

    )
