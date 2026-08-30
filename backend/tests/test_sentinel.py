from __future__ import annotations

import numpy as np
import pytest

from app.services import sentinel


def test_area_bbox_is_bounded_and_reports_sample_area(monkeypatch):
    monkeypatch.setenv("SENTINEL_MAX_SAMPLE_HECTARES", "2500")
    bbox, sampled = sentinel.area_bbox(12.0, 77.0, 50_000)
    assert sampled == 2_500
    assert bbox[0] < 77.0 < bbox[2]
    assert bbox[1] < 12.0 < bbox[3]


def test_process_scene_masks_clouds_and_reports_provenance(monkeypatch):
    size = 20
    red = np.full((size, size), 2_000, dtype=np.uint16)
    nir = np.full((size, size), 6_000, dtype=np.uint16)
    nir08 = np.full((size, size), 5_000, dtype=np.uint16)
    swir = np.full((size, size), 3_000, dtype=np.uint16)
    scl = np.full((size, size), 4, dtype=np.uint8)
    scl[:2, :] = 9
    arrays = {"red": red, "nir": nir, "nir08": nir08, "swir16": swir, "scl": scl}

    def fake_read(href, _bbox, _size, *, categorical=False):
        return arrays[href]

    monkeypatch.setattr(sentinel, "_read_asset", fake_read)
    item = {
        "id": "S2-test-item",
        "collection": "sentinel-2-l2a",
        "properties": {"datetime": "2026-08-01T10:00:00Z", "eo:cloud_cover": 12.5},
        "assets": {name: {"href": name} for name in arrays},
    }
    result = sentinel.process_scene(item, [76.9, 11.9, 77.1, 12.1], 25)
    assert result["ndvi"] == pytest.approx(0.5)
    assert result["ndmi"] == pytest.approx(0.25)
    assert result["valid_pixel_fraction"] == pytest.approx(0.9)
    assert result["item_id"] == "S2-test-item"
