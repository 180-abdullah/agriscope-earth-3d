from __future__ import annotations

from ..domain import clamp, deterministic_unit, number, point_geometry, risk_level
from ..models import AnalysisRequest, AnalysisResponse, Coordinates, DataStatus, Metric
from ..provenance import user_class_summaries


async def analyze(request: AnalysisRequest) -> AnalysisResponse:
    seed = deterministic_unit(request.latitude, request.longitude, "land")
    class_keys = {
        "baseline_water_pct", "current_water_pct",
        "baseline_cropland_pct", "current_cropland_pct",
        "baseline_tree_pct", "current_tree_pct",
    }
    supplied = class_keys.issubset(request.parameters) and bool(request.parameters.get("class_data_confirmed", False))
    baseline_water = clamp(number(request.parameters, "baseline_water_pct", 18 + seed * 35), 0, 100)
    current_water = clamp(number(request.parameters, "current_water_pct", baseline_water - 4 + seed * 7), 0, 100)
    baseline_crop = clamp(number(request.parameters, "baseline_cropland_pct", 30 + (1 - seed) * 35), 0, 100)
    current_crop = clamp(number(request.parameters, "current_cropland_pct", baseline_crop + 3 - seed * 5), 0, 100)
    baseline_tree = clamp(number(request.parameters, "baseline_tree_pct", 22 + seed * 20), 0, 100)
    current_tree = clamp(number(request.parameters, "current_tree_pct", baseline_tree - 5 + seed * 6), 0, 100)

    water_change = current_water - baseline_water
    crop_change = current_crop - baseline_crop
    tree_change = current_tree - baseline_tree
    ecological_loss = max(0.0, -water_change) + max(0.0, -tree_change)
    conversion_pressure = max(0.0, crop_change)
    score = clamp(ecological_loss * 6.5 + conversion_pressure * 3.5)
    changed_area = request.area_hectares * (abs(water_change) + abs(crop_change) + abs(tree_change)) / 300.0
    status = DataStatus.USER_SUPPLIED if supplied else DataStatus.DEMONSTRATION

    return AnalysisResponse(
        mission=request.mission,
        title="Global Wetland & Land-Use Change Audit",
        coordinates=Coordinates(latitude=request.latitude, longitude=request.longitude),
        area_hectares=request.area_hectares,
        score=round(score, 1),
        risk_level=risk_level(score),
        confidence=0.76 if supplied else 0.38,
        summary=(
            f"The {'confirmed user-supplied' if supplied else 'unconfirmed demonstration'} class summaries indicate {risk_level(score).value} ecological-conversion pressure. "
            "Run the same workflow on quality-controlled classified rasters before reporting real change."
        ),
        data_status=[status, DataStatus.CALCULATED],
        metrics=[
            Metric(key="water_change", label="Water / wetland change", value=round(water_change, 2), unit="percentage points", interpretation="Current minus baseline classified share."),
            Metric(key="cropland_change", label="Cropland change", value=round(crop_change, 2), unit="percentage points", interpretation="Current minus baseline classified share."),
            Metric(key="tree_change", label="Tree-cover change", value=round(tree_change, 2), unit="percentage points", interpretation="Current minus baseline classified share."),
            Metric(key="changed_area", label="Approximate changed area", value=round(changed_area, 1), unit="ha", interpretation="Non-overlap screening estimate from class summaries."),
        ],
        sources=[user_class_summaries(status)],
        caveats=[
            "Class totals alone do not reveal exactly where transitions occurred; a pixel-level transition matrix is preferred.",
            "Differences in season, sensor, classification method and cloud masking can create false change.",
            "Default values are demonstrations and must not be cited as observations for the selected coordinate.",
        ],
        geometry=point_geometry(request.latitude, request.longitude, {"score": round(score, 1), "water_change_pp": water_change, "mission": request.mission.value}),
    )
