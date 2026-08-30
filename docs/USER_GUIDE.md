# AgriScope Earth 3D user guide

## What this application is

AgriScope Earth is a global agricultural and environmental **screening** console. It connects a real 3D globe to six transparent research engines. It helps decide where to investigate first and preserves an evidence receipt; it does not replace field measurement, official warnings, audited inventories or a validated causal model.

## The simple workflow

1. **Choose a mission** from the six buttons at the bottom.
2. **Choose a target** by searching any worldwide place or clicking the globe.
3. Open **Setup**, verify area and mission inputs, then select **Run analysis**.
4. Read the **Overview**, then check **Evidence** and **Method** before interpreting the score.
5. Download JSON, CSV, GeoJSON or Markdown from **Export**.

There is no static “worked example” button. Each run uses the current coordinate and current inputs. If anything changes after a run, the receipt is marked stale until rerun.

## Why some values change with place—and some do not

| Mission | Does changing only the coordinate change the result? | Reason |
|---|---|---|
| M01 Flood | Yes | River discharge and rainfall are fetched for the coordinate. |
| M02 Crop stress | Yes with Python API; partly in browser mode | Python uses a local Sentinel-2 sample plus weather. Browser mode uses live local weather plus visible NDVI/NDMI inputs. |
| M03 Land change | No, when class summaries are unchanged | Coordinates anchor the study. The actual evidence is the researcher-supplied baseline/current classification summary. |
| M04 Irrigation | Yes | ET₀ and rainfall are fetched for the coordinate. |
| M05 Farm carbon | No, when activity data are unchanged | Location alone is not an emissions factor. Activity data and selected factors determine Tier 1 emissions. |
| M06 Fire + heat | Yes | Heat, humidity, rain, wind and configured FIRMS detections are target-dependent. |

Identical values are therefore not automatically a bug. The Setup drawer states the mission's location behaviour before every run.

## What the 3D graphics mean

The circle is the selected target area, approximated from hectares. Pulses, local dots, spokes and columns are **analysis graphics derived from the active mission and score**. They are intentionally confined to the target. They are not observed field boundaries, fire perimeters, flood water, carbon plumes or connections to other regions unless a future data layer explicitly supplies that geometry.

The previous decorative intercontinental lines are not used.

## Results

- **Priority score:** 0–100 triage index, not a probability or accuracy percentage.
- **Risk band:** low, moderate, high or severe software default.
- **Evidence completeness:** rule-based traceability indicator, not statistical confidence.
- **Evidence status:** observed, near-real-time, forecast, modelled, calculated, user-supplied, demonstration or unavailable.
- **Source receipt:** provider, role, date/identifier when available and known limitations.

## Python API versus live browser mode

The top status shows the execution path:

- **Python API:** authoritative repository engine, including Sentinel processing and optional FIRMS.
- **Live preview:** operational client-side calculation using public Open-Meteo data and visible form inputs. It is labelled and includes an additional research-use warning.

Use the Python API for research workflows and cite the exact exported source receipt.

## Terrain and imagery

- Satellite, dark reference and OpenStreetMap basemaps are available from Earth layers.
- Satellite imagery does not require a key in the default configuration.
- Cesium World Terrain requires `VITE_CESIUM_ION_TOKEN`. Without it the application still displays a real WGS84 3D globe, but the surface is the ellipsoid rather than elevation terrain.
- Provider attributions must remain visible.

## Before using a result in research

1. Confirm the exact target and area.
2. Confirm all visible inputs and units.
3. Reject or replace demonstration and unavailable evidence.
4. Record product IDs, dates, resolution, masks and licensing.
5. Calibrate thresholds and factors for the crop, season, region and production system.
6. Validate against independent ground or authoritative reference data.
7. Run sensitivity and uncertainty analysis.
8. Export and retain the evidence receipt with the analysis code version.
