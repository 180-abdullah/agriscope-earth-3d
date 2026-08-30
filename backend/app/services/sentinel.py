from __future__ import annotations

import asyncio
import math
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx


EARTH_SEARCH_URL = "https://earth-search.aws.element84.com/v1/search"
COLLECTION = "sentinel-2-l2a"
DEFAULT_LOOKBACK_DAYS = 120
DEFAULT_MAX_CLOUD_PCT = 35.0
DEFAULT_MAX_SAMPLE_HECTARES = 2_500.0
MAX_SCENES_TO_TRY = 3


class SentinelUnavailable(RuntimeError):
    """Raised when a defensible Sentinel-2 sample cannot be produced."""


def _bounded_sample_area(area_hectares: float) -> float:
    configured = float(os.getenv("SENTINEL_MAX_SAMPLE_HECTARES", DEFAULT_MAX_SAMPLE_HECTARES))
    return max(0.1, min(float(area_hectares), max(1.0, configured)))


def area_bbox(latitude: float, longitude: float, area_hectares: float) -> tuple[list[float], float]:
    """Return a WGS84 square around the target and the bounded sampled area."""
    sampled_hectares = _bounded_sample_area(area_hectares)
    side_m = math.sqrt(sampled_hectares * 10_000.0)
    half_side_m = side_m / 2.0
    lat_delta = half_side_m / 111_320.0
    lon_scale = max(0.05, math.cos(math.radians(latitude)))
    lon_delta = half_side_m / (111_320.0 * lon_scale)
    return (
        [
            max(-180.0, longitude - lon_delta),
            max(-90.0, latitude - lat_delta),
            min(180.0, longitude + lon_delta),
            min(90.0, latitude + lat_delta),
        ],
        sampled_hectares,
    )


async def search_scenes(
    latitude: float,
    longitude: float,
    area_hectares: float,
    *,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    max_cloud_pct: float = DEFAULT_MAX_CLOUD_PCT,
    timeout_seconds: float = 12.0,
) -> tuple[list[dict[str, Any]], list[float], float]:
    bbox, sampled_hectares = area_bbox(latitude, longitude, area_hectares)
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=max(14, min(int(lookback_days), 730)))
    payload = {
        "collections": [COLLECTION],
        "bbox": bbox,
        "datetime": f"{start.isoformat()}/{end.isoformat()}",
        "limit": 10,
        "query": {"eo:cloud_cover": {"lte": max(0.0, min(float(max_cloud_pct), 100.0))}},
        "sortby": [
            {"field": "properties.eo:cloud_cover", "direction": "asc"},
            {"field": "properties.datetime", "direction": "desc"},
        ],
    }
    async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=False) as client:
        response = await client.post(EARTH_SEARCH_URL, json=payload)
        response.raise_for_status()
        body = response.json()
    features = body.get("features", [])
    if not isinstance(features, list) or not features:
        raise SentinelUnavailable("No Sentinel-2 Level-2A scene met the date and cloud filters.")
    return features, bbox, sampled_hectares


def _read_asset(
    href: str,
    bbox: list[float],
    output_size: int,
    *,
    categorical: bool = False,
):
    try:
        import numpy as np
        import rasterio
        from rasterio.enums import Resampling
        from rasterio.windows import from_bounds
        from rasterio.warp import transform_bounds
    except ImportError as exc:  # pragma: no cover - depends on optional runtime build
        raise SentinelUnavailable("The optional raster processing dependencies are not installed.") from exc

    env_options = {
        "AWS_NO_SIGN_REQUEST": "YES",
        "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
        "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif,.TIF",
        "GDAL_HTTP_MULTIRANGE": "YES",
        "GDAL_HTTP_MERGE_CONSECUTIVE_RANGES": "YES",
    }
    ca_bundle = os.getenv("SSL_CERT_FILE") or os.getenv("REQUESTS_CA_BUNDLE")
    if ca_bundle and os.path.isfile(ca_bundle):
        env_options["GDAL_HTTP_CA_BUNDLE"] = ca_bundle
        env_options["CURL_CA_BUNDLE"] = ca_bundle
    if os.getenv("SENTINEL_ALLOW_INSECURE_SSL", "").strip() == "1":
        # Local diagnostics only (for example, a controlled TLS-inspection
        # proxy). This switch is deliberately undocumented in the UI and must
        # never be enabled on a public deployment.
        env_options["GDAL_HTTP_UNSAFESSL"] = "YES"
    with rasterio.Env(**env_options), rasterio.open(href) as dataset:
        projected_bounds = transform_bounds("EPSG:4326", dataset.crs, *bbox, densify_pts=21)
        window = from_bounds(*projected_bounds, transform=dataset.transform)
        values = dataset.read(
            1,
            window=window,
            out_shape=(output_size, output_size),
            boundless=True,
            fill_value=0,
            resampling=Resampling.nearest if categorical else Resampling.bilinear,
        )
    return np.asarray(values)


def process_scene(item: dict[str, Any], bbox: list[float], sampled_hectares: float) -> dict[str, Any]:
    """Compute clear-pixel median NDVI and NDMI from one STAC item."""
    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover - depends on optional runtime build
        raise SentinelUnavailable("NumPy is required for Sentinel-2 processing.") from exc

    assets = item.get("assets", {})
    required = ("red", "nir", "nir08", "swir16", "scl")
    if not all(assets.get(name, {}).get("href") for name in required):
        raise SentinelUnavailable("The selected STAC item is missing required reflectance or quality assets.")

    # A bounded output size protects modest cloud instances from reading a full
    # Sentinel tile while still producing a spatial sample of the target.
    side_m = math.sqrt(sampled_hectares * 10_000.0)
    output_size = max(16, min(256, int(math.ceil(side_m / 20.0))))
    red = _read_asset(assets["red"]["href"], bbox, output_size).astype("float32")
    nir = _read_asset(assets["nir"]["href"], bbox, output_size).astype("float32")
    nir08 = _read_asset(assets["nir08"]["href"], bbox, output_size).astype("float32")
    swir16 = _read_asset(assets["swir16"]["href"], bbox, output_size).astype("float32")
    scl = _read_asset(assets["scl"]["href"], bbox, output_size, categorical=True)

    # SCL 0, 1, 3, 8, 9, 10 and 11 represent no-data, defective pixels,
    # shadows, cloud/cirrus or snow/ice and are excluded. The remaining pixels
    # are still not assumed to be cropland; interpretation stays explicitly
    # conditional on the user's target and field verification.
    rejected_scl = np.isin(scl, [0, 1, 3, 8, 9, 10, 11])
    reflectance_valid = (red > 0) & (nir > 0) & (nir08 > 0) & (swir16 > 0)
    valid = (~rejected_scl) & reflectance_valid
    valid_count = int(valid.sum())
    total_count = int(valid.size)
    valid_fraction = valid_count / max(total_count, 1)
    if valid_count < 25 or valid_fraction < 0.05:
        raise SentinelUnavailable("The scene has too few clear, valid pixels over the target sample.")

    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi_grid = (nir - red) / (nir + red)
        ndmi_grid = (nir08 - swir16) / (nir08 + swir16)
    ndvi_values = ndvi_grid[valid & np.isfinite(ndvi_grid)]
    ndmi_values = ndmi_grid[valid & np.isfinite(ndmi_grid)]
    if ndvi_values.size < 25 or ndmi_values.size < 25:
        raise SentinelUnavailable("The scene did not produce enough finite index pixels.")

    properties = item.get("properties", {})
    return {
        "ndvi": round(float(np.median(ndvi_values)), 4),
        "ndmi": round(float(np.median(ndmi_values)), 4),
        "ndvi_p25": round(float(np.percentile(ndvi_values, 25)), 4),
        "ndvi_p75": round(float(np.percentile(ndvi_values, 75)), 4),
        "ndmi_p25": round(float(np.percentile(ndmi_values, 25)), 4),
        "ndmi_p75": round(float(np.percentile(ndmi_values, 75)), 4),
        "valid_pixel_fraction": round(valid_fraction, 4),
        "valid_pixel_count": valid_count,
        "sampled_area_hectares": round(sampled_hectares, 2),
        "item_id": str(item.get("id", "unknown")),
        "acquisition_datetime": properties.get("datetime") or properties.get("start_datetime"),
        "scene_cloud_cover_pct": round(float(properties.get("eo:cloud_cover", 0.0)), 2),
        "thumbnail_url": assets.get("thumbnail", {}).get("href"),
        "collection": item.get("collection", COLLECTION),
    }


async def sentinel2_indices(
    latitude: float,
    longitude: float,
    area_hectares: float,
    *,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    max_cloud_pct: float = DEFAULT_MAX_CLOUD_PCT,
) -> dict[str, Any]:
    """Search recent scenes and return the first usable clear-pixel sample."""
    features, bbox, sampled_hectares = await search_scenes(
        latitude,
        longitude,
        area_hectares,
        lookback_days=lookback_days,
        max_cloud_pct=max_cloud_pct,
    )
    failures: list[str] = []
    for item in features[:MAX_SCENES_TO_TRY]:
        try:
            return await asyncio.to_thread(process_scene, item, bbox, sampled_hectares)
        except Exception as exc:
            failures.append(f"{item.get('id', 'unknown')}: {exc}")
    detail = "; ".join(failures[:MAX_SCENES_TO_TRY])
    raise SentinelUnavailable(f"No searched scene produced a valid target sample. {detail}")
