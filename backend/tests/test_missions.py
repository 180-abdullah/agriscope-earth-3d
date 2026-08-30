from __future__ import annotations

import pytest

from app.missions import carbon, crop_stress, fire_heat, flood, irrigation, land_change
from app.models import AnalysisRequest, DataStatus, MissionId


WEATHER = {
    "temperature_max_c": 36.0,
    "rain_7d_mm": 12.0,
    "et0_7d_mm": 38.0,
    "relative_humidity_pct": 48.0,
    "soil_moisture_m3_m3": 0.17,
    "wind_max_kmh": 31.0,
}


async def fixed_weather(_latitude: float, _longitude: float):
    return WEATHER, DataStatus.FORECAST


async def fixed_flood(_latitude: float, _longitude: float):
    return {
        "discharge_peak_m3_s": 300.0,
        "discharge_mean_m3_s": 150.0,
        "historical_peak_m3_s": 480.0,
        "discharge_ratio": 2.0,
    }, DataStatus.FORECAST


async def fixed_fire(_latitude: float, _longitude: float):
    return {"hotspot_count": 5.0, "maximum_frp_mw": 22.0}, DataStatus.NEAR_REAL_TIME


def request(mission: MissionId, **parameters):
    return AnalysisRequest(
        mission=mission,
        latitude=10.0,
        longitude=20.0,
        area_hectares=100.0,
        parameters=parameters,
    )


@pytest.mark.asyncio
async def test_flood_screen_is_bounded_and_reports_exposure(monkeypatch):
    monkeypatch.setattr(flood, "weather_snapshot", fixed_weather)
    monkeypatch.setattr(flood, "flood_snapshot", fixed_flood)
    result = await flood.analyze(request(MissionId.FLOOD))
    assert 0 <= result.score <= 100
    assert result.metrics[2].value > 0
    assert DataStatus.FORECAST in result.data_status


@pytest.mark.asyncio
async def test_crop_stress_accepts_processed_indices(monkeypatch):
    monkeypatch.setattr(crop_stress, "weather_snapshot", fixed_weather)
    result = await crop_stress.analyze(request(MissionId.CROP_STRESS, ndvi=0.31, ndmi=0.02))
    assert result.score > 40
    assert DataStatus.USER_SUPPLIED in result.data_status
    assert result.confidence >= 0.7


@pytest.mark.asyncio
async def test_crop_stress_uses_live_sentinel_receipt(monkeypatch):
    monkeypatch.setattr(crop_stress, "weather_snapshot", fixed_weather)

    async def fixed_sentinel(*_args, **_kwargs):
        return {
            "ndvi": 0.51,
            "ndmi": 0.18,
            "valid_pixel_fraction": 0.82,
            "sampled_area_hectares": 100.0,
            "item_id": "S2-live-test",
            "acquisition_datetime": "2026-08-01T10:00:00Z",
            "scene_cloud_cover_pct": 8.4,
        }

    monkeypatch.setattr(crop_stress, "sentinel2_indices", fixed_sentinel)
    result = await crop_stress.analyze(request(MissionId.CROP_STRESS, use_live_sentinel=True))
    assert DataStatus.OBSERVED in result.data_status
    assert result.sources[0].identifier == "S2-live-test"
    assert {metric.key for metric in result.metrics} >= {"sentinel_valid_pixels", "sentinel_scene_cloud"}


@pytest.mark.asyncio
async def test_land_change_uses_percentage_point_differences():
    result = await land_change.analyze(
        request(
            MissionId.LAND_CHANGE,
            baseline_water_pct=40,
            current_water_pct=25,
            baseline_cropland_pct=30,
            current_cropland_pct=42,
            baseline_tree_pct=20,
            current_tree_pct=15,
        )
    )
    values = {metric.key: metric.value for metric in result.metrics}
    assert values["water_change"] == -15
    assert values["cropland_change"] == 12
    assert result.score > 70


@pytest.mark.asyncio
async def test_irrigation_volume_identity(monkeypatch):
    monkeypatch.setattr(irrigation, "weather_snapshot", fixed_weather)
    result = await irrigation.analyze(
        request(MissionId.IRRIGATION, crop="maize", effective_rain_fraction=0.8, application_efficiency=0.7)
    )
    values = {metric.key: float(metric.value) for metric in result.metrics}
    assert values["gross_depth"] > 0
    assert values["water_volume"] == pytest.approx(values["gross_depth"] * 100 * 10, abs=60)


@pytest.mark.asyncio
async def test_irrigation_explains_zero_deficit_and_zero_pumping_energy(monkeypatch):
    async def wet_weather(_latitude: float, _longitude: float):
        return {**WEATHER, "rain_7d_mm": 80.0, "et0_7d_mm": 22.0}, DataStatus.FORECAST

    monkeypatch.setattr(irrigation, "weather_snapshot", wet_weather)
    result = await irrigation.analyze(
        request(
            MissionId.IRRIGATION,
            crop="rice",
            effective_rain_fraction=0.8,
            application_efficiency=0.7,
            pump_efficiency=0.2,
            total_dynamic_head_m=200,
        )
    )
    values = {metric.key: float(metric.value) for metric in result.metrics}
    assert values["raw_balance"] < 0
    assert values["gross_depth"] == 0
    assert values["energy"] == 0
    assert "Pump head and efficiency cannot change energy" in result.summary


@pytest.mark.asyncio
async def test_carbon_total_equals_included_components():
    result = await carbon.analyze(
        request(
            MissionId.CARBON,
            fertilizer_n_kg_ha=100,
            rice_area_hectares=40,
            rice_cultivation_days=100,
            diesel_litres=1000,
            livestock_head=10,
        )
    )
    values = {metric.key: float(metric.value) for metric in result.metrics}
    component_sum = values["fertilizer"] + values["rice"] + values["energy"] + values["livestock"]
    assert values["total"] == pytest.approx(component_sum, abs=0.05)
    assert DataStatus.CALCULATED in result.data_status


@pytest.mark.asyncio
async def test_fire_heat_uses_near_real_time_hotspots(monkeypatch):
    monkeypatch.setattr(fire_heat, "weather_snapshot", fixed_weather)
    monkeypatch.setattr(fire_heat, "fire_snapshot", fixed_fire)
    result = await fire_heat.analyze(request(MissionId.FIRE_HEAT))
    assert result.score > 30
    assert DataStatus.NEAR_REAL_TIME in result.data_status
    assert result.metrics[1].value == 5
