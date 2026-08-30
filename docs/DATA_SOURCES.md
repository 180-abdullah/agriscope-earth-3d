# Data sources and limitations

AgriScope Earth adapters use fixed, allow-listed endpoints. Upstream availability, licences, quotas and product definitions may change; review provider terms before public or commercial deployment.

| Source | Mission use | Access | Important limitation |
|---|---|---|---|
| Open-Meteo Weather Forecast API | Weather, precipitation, model soil moisture, FAO-56 ET₀ | Keyless API | Numerical weather-model output, not a local station or soil probe. |
| Open-Meteo Global Flood API / GloFAS | River-discharge forecast | Keyless API | Returns discharge for the largest modelled river near the coordinate; not inundation depth. |
| NASA LANCE FIRMS | Thermal anomalies | Optional free map key | Hotspots are not automatically agricultural fires or burned-area polygons. |
| Copernicus Sentinel-2 L2A via Element 84 Earth Search | Recent NDVI/NDMI target summary | Keyless STAC + public COG access | Single optical scene; quality masking is not a crop mask and cloud/network availability varies. |
| Open-Meteo Geocoding API / GeoNames | Worldwide place lookup | Keyless API | Search result is a place centroid, not a farm boundary. |
| IPCC Guidelines | GHG equation structure/defaults | Public documents | Tier 1 factors can be inappropriate for a specific production system. |

M03 does not claim that a particular land-cover product was used. The user must record the actual classified products in the exported study record.

## Fallback policy

If a public service is unreachable, the Python engine can return a deterministic demonstration value and labels it `demonstration`. It never silently presents fallback data as live, observed or forecast. A result containing demonstration data receives a prominent red trust banner and must not be cited as an observation.

## Satellite inputs

ASE-0.3 can calculate a bounded single-scene Sentinel-2 NDVI/NDMI summary for M02 or accept a complete user-prepared pair. The live receipt records the item identifier, acquisition time, scene cloud metadata, target valid-pixel fraction and sampled area. The engine does not automatically identify field boundaries or crop type.

M03 accepts two-period class-share summaries because defensible automatic land-change classification requires study-specific product selection, spatial alignment, seasonal control, quality masks, classification validation and a pixel transition analysis. An uploaded CSV is schema-validated, but its scientific quality is not independently verified.

## Provider terms and operational use

Open-Meteo access modes and licensing differ by use case. NASA FIRMS requires a free MAP_KEY for API access and applies transaction limits. Copernicus, Element 84/AWS, basemap and geocoding terms remain with their providers. Review current terms before commercial, high-volume or redistributed use.

## Attribution

The CesiumJS globe keeps provider credits visible. The default satellite layer uses Esri World Imagery; dark and street references use CARTO and OpenStreetMap. Cesium World Terrain requires an ion token and retains Cesium attribution. Review each provider's current licence before commercial or redistributed use. Cite the exact upstream data products and item identifiers used in a study, not only this software. See each exported source receipt and [Scientific validation and integrity status](SCIENTIFIC_VALIDATION.md).
