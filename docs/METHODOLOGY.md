# AgriScope Earth methodology

Methodology version: **ASE-0.3**

## Scientific contract

AgriScope Earth is a screening system. Each response contains the input status, score, confidence, source register, caveats and a methodology version. A score is a prioritization indicator—not a probability of loss, diagnosis, official warning or causal estimate.

The field called `confidence` in the machine-readable schema is displayed as **evidence completeness**. It is a fixed rule-based summary of source traceability and fallback use, not statistical confidence, calibrated probability, validation accuracy or an uncertainty interval.

Each executed request receives a new analysis ID and generation time. The web client compares the current target and parameters with the executed request. If any input changes, the old receipt is visibly marked stale and its score layer is removed until the user runs the changed request; an old result is never relabelled as current.

The status vocabulary is mandatory:

- **observed:** derived from an observation product.
- **near-real-time:** recently processed observation with a stated latency.
- **forecast:** numerical model output for a future period.
- **modelled:** estimated through a model or proxy.
- **calculated:** arithmetic transformation of inputs.
- **user-supplied:** provided in the request and not independently verified.
- **demonstration:** deterministic sample value used only to demonstrate the interface.
- **unavailable:** requested source could not supply a usable value.

## 1. Flood and crop-exposure screening

The engine combines:

- seven-day ensemble maximum-to-mean modelled river-discharge ratio;
- seven-day forecast precipitation;
- crop-stage sensitivity; and
- drainage vulnerability.

The 0–100 score is:

```text
score = 0.50(discharge component)
      + 0.20(rain component)
      + 15(crop-stage sensitivity)
      + 15(drainage vulnerability)
```

Components are bounded to 0–100, while sensitivities are bounded to 0–1. GloFAS `river_discharge_mean` and `river_discharge_max` are forecast-ensemble statistics; ASE-0.3 does not describe them as a historical baseline. Screened exposed area is a heuristic transformation of the selected agricultural area. River discharge does not directly provide flood depth, inundation boundary or crop loss.

## 2. Crop-stress screening

The crop-stress score combines:

```text
0.32 NDVI stress
+ 0.23 NDMI stress
+ 0.20 surface-soil-moisture stress
+ 0.15 heat stress
+ 0.10 rainfall-deficit stress
```

Index evidence follows this precedence: a complete user-supplied NDVI/NDMI pair; otherwise an explicitly requested live Sentinel-2 sample; otherwise clearly labelled demonstration values. Live processing searches the Element 84 Earth Search `sentinel-2-l2a` collection, reads a bounded target sample, excludes SCL classes 0, 1, 3, 8, 9, 10 and 11, and reports clear-pixel median NDVI and NDMI with the STAC item ID, acquisition time, scene cloud metadata, valid-pixel fraction and sampled area.

The live calculation uses `(NIR − Red)/(NIR + Red)` for NDVI and `(NIR8A − SWIR1)/(NIR8A + SWIR1)` for NDMI. It is a single-scene summary, not a multi-date composite or crop mask. Default stress thresholds are generic screening assumptions. Valid confirmatory use requires crop-, stage-, season- and region-specific calibration. The engine never converts stress into a pest, disease or nutrient-deficiency diagnosis.

## 3. Wetland and land-use change

The engine accepts baseline and current class shares from the form or validated CSV schema. Values are labelled `user-supplied` only when the user confirms that they came from comparable classified observations; otherwise they remain `demonstration`. Change is reported in **percentage points**:

```text
class change = current classified share − baseline classified share
```

Ecological-conversion pressure increases with loss of water/wetland or tree cover and with cropland expansion. Class-share summaries cannot locate transitions; a pixel-level transition matrix and accuracy assessment should be used for publication.

## 4. Irrigation intelligence

The engine uses the standard crop-water balance:

```text
ETc = Kc × ET0
effective rainfall = precipitation × effective-rain fraction
net irrigation depth = max(0, ETc − effective rainfall)
gross irrigation depth = net depth / application efficiency
volume (m³) = gross depth (mm) × area (ha) × 10
```

Pumping energy is:

```text
hydraulic energy (kWh) = ρ × g × total dynamic head × volume / 3,600,000
input electricity = hydraulic energy / pump efficiency
```

The output receipt reports ET₀, total precipitation, crop coefficient, crop ET, effective rain, the signed pre-clipping balance, net deficit, gross depth, volume and energy. When `ETc − effective rainfall ≤ 0`, net depth, gross depth, volume and energy are zero. Changing pump head or efficiency cannot alter energy while volume is zero. This is a seven-day screening result, not a statement that irrigation is unnecessary throughout the season.

Open-Meteo exposes FAO-56 reference evapotranspiration derived from temperature, wind, humidity and solar radiation. Local scheduling should include root-zone storage, rainfall effectiveness, field capacity, allowable depletion and growth-stage coefficients.

## 5. Agricultural carbon screening

The default boundary includes:

- direct fertilizer-related soil N₂O;
- rice-cultivation CH₄;
- diesel CO₂;
- electricity CO₂ using a user-supplied grid factor; and
- enteric CH₄.

Direct fertilizer N₂O:

```text
N2O-N = applied N × EF1
N2O = N2O-N × 44/28
CO2e = N2O × GWP100(N2O)
```

Rice methane:

```text
CH4 = daily baseline EF × rice area × cultivation days
      × water-regime factor × organic-amendment factor
CO2e = CH4 × GWP100(CH4)
```

ASE-0.3 defaults include EF1 = 0.01 kg N₂O-N/kg N, a rice daily baseline of 1.19 kg CH₄/ha/day, GWP100 CH₄ = 27.2 and GWP100 N₂O = 273. These defaults are modelled screening factors and must be replaced when validated national, technology, species or system-specific factors exist.

Excluded by default: indirect N₂O, manure management, upstream fertilizer manufacture, embedded machinery emissions, land-use change, soil-carbon change, transport, processing and avoided emissions.

## 6. Fire and heat screening

The score combines apparent heat, recent dryness, wind and nearby satellite thermal detections. Heat index uses the NOAA Rothfusz regression as a screening indicator. NASA FIRMS hotspots are thermal anomalies; they do not establish cause, land ownership, crop damage or fire perimeter.

## Risk bands

| Score | Label |
|---:|---|
| 0–24.9 | Low |
| 25–49.9 | Moderate |
| 50–74.9 | High |
| 75–100 | Severe |

These bands are software defaults for triage. They have not been externally validated as universal probabilities or outcome thresholds and require empirical calibration before operational use.

## Reproducibility checklist

Record and report:

1. AgriScope methodology version and commit.
2. Coordinates, area, date and mission parameters.
3. Every data product, product version, spatial resolution and access date.
4. Whether each value was observed, forecast, modelled or user-supplied.
5. Missing-data handling and any fallback.
6. Calibration and ground-validation procedure.
7. Sensitivity or uncertainty analysis.

For confirmatory or publication-oriented work, also read [Scientific validation and integrity status](SCIENTIFIC_VALIDATION.md) and pre-specify the population, estimand, sampling frame, ground-reference method, missing-data rules, diagnostics and validation design.

## Core references

- IPCC. *2019 Refinement to the 2006 IPCC Guidelines for National Greenhouse Gas Inventories*. https://www.ipcc-nggip.iges.or.jp/public/2019rf/
- IPCC. *Climate Change 2021: The Physical Science Basis*, Chapter 7. https://www.ipcc.ch/report/ar6/wg1/chapter/chapter-7/
- Open-Meteo Weather Forecast API. https://open-meteo.com/en/docs
- Open-Meteo Global Flood API. https://open-meteo.com/en/docs/flood-api
- NASA LANCE FIRMS. https://firms.modaps.eosdis.nasa.gov/
- Copernicus Data Space Ecosystem. https://dataspace.copernicus.eu/
- Element 84 Earth Search Sentinel-2 L2A STAC collection. https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a
- STAC Item Search specification. https://api.stacspec.org/v1.0.0/item-search/
