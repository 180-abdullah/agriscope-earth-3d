# Scientific validation and integrity status

Release: **ASE-0.3**  
Scope: global agricultural and environmental **screening and prioritization**

## Read this before using results in research

AgriScope Earth is method-transparent and software-tested, but its generic 0–100 priority indices have **not** been externally validated as universal predictors of crop loss, flood damage, fire occurrence, disease, yield, or policy impact. A working data pipeline is not the same as a validated scientific instrument.

Use the platform to formulate questions, acquire traceable screening evidence, compare scenarios, identify field-verification priorities, and create a reproducible record. Do not use the default score bands as inferential results until they have been calibrated and validated for the study population.

## Mission evidence contract

| Mission | Evidence the engine can use | Defensible output | Claims that remain blocked |
|---|---|---|---|
| M01 Flood exposure | GloFAS seven-day ensemble discharge statistics, weather forecast, user vulnerability assumptions | Relative screening priority and scenario comparison | Field-level flood depth, inundation footprint, crop loss, official warning |
| M02 Crop stress | Sentinel-2 L2A clear-pixel NDVI/NDMI or user indices, weather-model soil moisture and weather | Scouting priority and a traceable single-scene index summary | Crop diagnosis, cause of stress, yield loss, field boundary classification |
| M03 Land change | Confirmed user-supplied class shares from two comparable classified observations | Percentage-point class differences and screening pressure | Pixel transition location, causation, legal land-use determination, accuracy without confusion matrices |
| M04 Irrigation | Forecast FAO-56 ET₀ and precipitation or user overrides, crop/system assumptions | Seven-day preliminary depth, volume, and hydraulic-energy estimate | Operational schedule, root-zone depletion, equipment safety, guaranteed water saving |
| M05 Carbon | User activity data and stated Tier 1 factors | Included-source screening inventory and scenario comparison | Audited footprint, complete life-cycle assessment, national inventory, carbon-credit claim |
| M06 Fire and heat | Forecast weather and optional NASA FIRMS detections or verified user observations | Verification and heat-precaution priority | Fire cause, perimeter, ownership, damage, emergency warning |

## Sentinel-2 processing receipt

Live M02 processing performs a bounded, reproducible single-scene sample:

1. Build a square WGS84 sample around the target. The sample is capped at 2,500 ha by default to control memory and network use; the returned record states the actual sampled area.
2. Search Element 84 Earth Search for recent `sentinel-2-l2a` STAC items using a date window and whole-scene cloud metadata filter.
3. Try up to three candidate scenes.
4. Read red, NIR, narrow NIR, SWIR1, and Scene Classification Layer assets from cloud-optimized GeoTIFFs.
5. Exclude SCL classes 0, 1, 3, 8, 9, 10, and 11 and non-positive reflectance pixels.
6. Calculate clear-pixel NDVI `(NIR − Red)/(NIR + Red)` and NDMI `(NIR8A − SWIR1)/(NIR8A + SWIR1)`.
7. Report the median indices, valid-pixel fraction, valid-pixel count, whole-scene cloud metadata, acquisition timestamp, STAC item identifier, and sampled area.

This is a transparent screening summary, not a multi-date crop-specific composite. The Scene Classification Layer is a quality mask, not a crop mask. A confirmatory study should define field polygons, crop and phenological strata, compositing rules, atmospheric/BRDF handling, quality thresholds, and ground validation before analysis.

## Quality and integrity audit

| Domain | Status | Evidence and next requirement |
|---|---|---|
| Contribution and fit | Ready for screening studies | Six decision-relevant workflows and global data adapters are defined. Journal fit must be assessed per study. |
| Question and alignment | Needs revision per study | Each mission has a fixed screening question; researchers must define their population, estimand, outcome, and hypotheses. |
| Design validity | Blocked for confirmatory inference | No universal sampling frame, power analysis, field ground truth, confounder plan, or external validation dataset is bundled. |
| Statistical integrity | Needs revision | Equations and bounds are explicit; generic scores lack calibrated probabilities, confidence intervals, and sensitivity analysis. |
| Evidence integrity | Ready for traceability | Status labels, source records, item IDs, timestamps, inputs, methodology version, and fallbacks are exported. User inputs are not independently verified. |
| Reporting | Needs revision per design | Exports support an audit trail; ethics, registration, reporting guideline, data license, and study-specific methods remain the researcher's responsibility. |
| Communication | Ready for screening use | The interface distinguishes priority indices from probability, loss, diagnosis, and official warnings. |

## Minimum study protocol

Before collecting or analysing confirmatory data, record:

1. Practical problem and primary research question.
2. Population, spatial unit, time window, inclusion/exclusion rules, and sampling frame.
3. Primary outcome or estimand and any secondary outcomes.
4. Exposure/predictor definitions, crop stage, management, soil, weather, and other candidate confounders.
5. Ground-reference method, instrument validity, observer protocol, and quality control.
6. Sample-size or spatial-coverage justification.
7. Missing-data, cloud, outlier, temporal-compositing, and exclusion rules.
8. Model, diagnostics, effect measure, uncertainty interval, multiple-testing policy, and sensitivity analyses.
9. Internal or external validation plan, including calibration and discrimination for predictive use.
10. Ethics, consent, registration, licensing, data management, code version, and dissemination plan where applicable.

Use this analysis-plan matrix:

| Objective | Outcome/estimand | Predictors/groups | Method | Assumptions/diagnostics | Effect measure and interval | Robustness check |
|---|---|---|---|---|---|---|
| Define per study | Define per study | Define per study | Define per study | Define per study | Define per study | Define per study |

## External-validation roadmap

1. Freeze a mission version and preregister the intended estimand.
2. Assemble multi-region, multi-season ground truth independent of model development.
3. Evaluate source data quality, missingness, spatial leakage, class imbalance, and temporal leakage.
4. Calibrate thresholds on training regions only.
5. Report external discrimination, calibration, error distributions, uncertainty, and subgroup performance.
6. Compare against simple baselines and relevant operational products.
7. Run sensitivity analyses for source resolution, cloud filters, crop stage, field size, and missing data.
8. Publish the full data provenance, exclusions, code commit, environment, and limitations where licenses permit.

## Verified primary documentation

- [Element 84 Earth Search and Sentinel-2 STAC collection](https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a)
- [Copernicus Sentinel-2 product documentation](https://documentation.dataspace.copernicus.eu/Data/Sentinel2.html)
- [Open-Meteo Weather Forecast API](https://open-meteo.com/en/docs)
- [Open-Meteo Global Flood API and GloFAS definitions](https://open-meteo.com/en/docs/flood-api)
- [NASA LANCE FIRMS API](https://firms.modaps.eosdis.nasa.gov/api/)
- [IPCC 2019 Refinement](https://www.ipcc-nggip.iges.or.jp/public/2019rf/)
- [FAO Irrigation and Drainage Paper 56](https://www.fao.org/4/x0490e/x0490e00.htm)
- [STAC Item Search specification](https://api.stacspec.org/v1.0.0/item-search/)

## Integrity rules

- Never relabel `demonstration` output as observed evidence.
- Trace every numerical result to an input, source receipt, or stated calculation.
- Do not treat “evidence completeness” as accuracy, uncertainty, probability, or a confidence interval.
- Do not infer causation from a screening association.
- Preserve exported records and the exact Git commit for every reported analysis.
- Document all post-export exclusions, transformations, factor changes, and model changes.
