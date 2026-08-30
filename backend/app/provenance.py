from __future__ import annotations

from datetime import datetime, timezone

from .models import DataStatus, SourceRecord


def open_meteo_weather(status: DataStatus = DataStatus.FORECAST) -> SourceRecord:
    return SourceRecord(
        name="Open-Meteo Weather Forecast API",
        url="https://open-meteo.com/en/docs",
        role="Weather, precipitation, soil moisture and FAO-56 reference evapotranspiration",
        status=status,
        spatial_resolution="Model-dependent; commonly 1–25 km",
        temporal_resolution="Hourly and daily",
        note="Model output; not an on-farm sensor observation.",
        accessed_at=datetime.now(timezone.utc).isoformat(),
        license="Open-Meteo terms and upstream provider licences apply",
    )


def open_meteo_flood(status: DataStatus = DataStatus.FORECAST) -> SourceRecord:
    return SourceRecord(
        name="Open-Meteo Global Flood API / GloFAS",
        url="https://open-meteo.com/en/docs/flood-api",
        role="River discharge forecast near the selected coordinate",
        status=status,
        spatial_resolution="Largest modelled river within approximately 5 km",
        temporal_resolution="Daily",
        note="River discharge does not directly equal inundation depth or crop loss.",
        accessed_at=datetime.now(timezone.utc).isoformat(),
        license="Open-Meteo terms and Copernicus/GloFAS conditions apply",
    )


def nasa_firms(status: DataStatus = DataStatus.NEAR_REAL_TIME) -> SourceRecord:
    return SourceRecord(
        name="NASA LANCE FIRMS",
        url="https://firms.modaps.eosdis.nasa.gov/",
        role="MODIS and VIIRS active-fire or thermal-anomaly detections",
        status=status,
        spatial_resolution="Sensor-dependent; VIIRS nominally 375 m",
        temporal_resolution="Near-real-time; global detections generally within 3 hours",
        note="A hotspot is not automatically an agricultural fire.",
        accessed_at=datetime.now(timezone.utc).isoformat(),
        license="NASA FIRMS data-use and acknowledgement requirements apply",
    )


def user_vegetation_indices(status: DataStatus) -> SourceRecord:
    return SourceRecord(
        name="User-supplied vegetation-index summaries" if status == DataStatus.USER_SUPPLIED else "Demonstration vegetation-index values",
        role="NDVI and NDMI values used when live Sentinel-2 processing is not selected",
        status=status,
        note="AgriScope does not independently verify a user-supplied sensor, date, atmospheric correction, mask, field boundary or processing chain.",
    )


def earth_search_sentinel(sample: dict, status: DataStatus = DataStatus.OBSERVED) -> SourceRecord:
    acquisition = sample.get("acquisition_datetime")
    cloud = sample.get("scene_cloud_cover_pct")
    valid = float(sample.get("valid_pixel_fraction", 0.0)) * 100
    sampled = sample.get("sampled_area_hectares")
    return SourceRecord(
        name="Copernicus Sentinel-2 L2A via Element 84 Earth Search",
        url="https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a",
        role="Cloud-masked target summaries of NDVI and NDMI from surface-reflectance assets",
        status=status,
        spatial_resolution="20 m analysis grid; red and NIR assets originate at 10–20 m",
        temporal_resolution="Single selected acquisition within the configured lookback window",
        note=(
            f"Scene cloud metadata {cloud}%; {valid:.1f}% of sampled pixels passed the quality mask; "
            f"sampled area {sampled} ha. Scene metadata cloud cover is not target-specific."
        ),
        identifier=str(sample.get("item_id", "unknown")),
        acquisition_datetime=str(acquisition) if acquisition else None,
        accessed_at=datetime.now(timezone.utc).isoformat(),
        license="Copernicus Sentinel data terms; Earth Search access terms also apply",
    )


def earth_search_unavailable(note: str) -> SourceRecord:
    return SourceRecord(
        name="Copernicus Sentinel-2 L2A via Element 84 Earth Search",
        url="https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a",
        role="Optional acquisition of surface-reflectance imagery for NDVI and NDMI",
        status=DataStatus.UNAVAILABLE,
        spatial_resolution="10–20 m source assets",
        temporal_resolution="Configured recent-lookback search",
        note=note[:500],
        accessed_at=datetime.now(timezone.utc).isoformat(),
        license="Copernicus Sentinel data terms; Earth Search access terms also apply",
    )


def user_class_summaries(status: DataStatus) -> SourceRecord:
    return SourceRecord(
        name="User-selected classified Earth-observation summaries",
        role="Baseline and current water, cropland and tree-cover shares supplied through the form or CSV template",
        status=status,
        note=(
            "AgriScope did not create or independently validate the classifications. Record the actual products, dates, "
            "processing chain, confusion matrices and citations in the exported research package."
        ),
    )


def ipcc(status: DataStatus = DataStatus.CALCULATED) -> SourceRecord:
    return SourceRecord(
        name="IPCC 2006 Guidelines and 2019 Refinement",
        url="https://www.ipcc-nggip.iges.or.jp/public/2019rf/",
        role="Tier 1 agricultural greenhouse-gas calculation structure and defaults",
        status=status,
        spatial_resolution="Activity-data dependent",
        temporal_resolution="Inventory period",
        note="Screening estimate; official inventories require jurisdiction-specific factors and QA.",
    )
