import type { MissionDefinition, MissionId } from "./types";

const crops = ["rice", "maize", "wheat", "soybean", "cotton", "potato", "vegetables", "orchard"];

export const MISSIONS: MissionDefinition[] = [
  {
    id: "flood-watch",
    code: "M01",
    shortName: "Flood",
    name: "Global Flood & Crop Exposure Watch",
    question: "Where could forecast river conditions expose agricultural land?",
    description: "A transparent screening score from forecast discharge, rain, crop-stage sensitivity and drainage vulnerability.",
    accent: "#63d7cc",
    timeWindow: "7-day forecast",
    evidence: "Open-Meteo Flood / GloFAS + weather forecast",
    locationBehavior: "Location-sensitive: river discharge and rainfall are fetched for the selected coordinate.",
    defaultArea: 25_000,
    fields: [
      { key: "crop_stage_sensitivity", label: "Crop-stage sensitivity", type: "range", defaultValue: 0.75, min: 0, max: 1, step: 0.05, help: "Relative sensitivity of the crop at its current stage." },
      { key: "drainage_vulnerability", label: "Drainage vulnerability", type: "range", defaultValue: 0.55, min: 0, max: 1, step: 0.05, help: "Local ponding and drainage susceptibility." },
    ],
    researchFields: [
      {
        key:"river_distance_km",
        label:"Distance from river",
        type:"number",
        defaultValue:5,
        min:0,
        max:100,
        step:1,
        unit:"km",
        help:"Distance between agricultural area and major river system."
      },
      {
        key:"soil_drainage_class",
        label:"Soil drainage condition",
        type:"select",
        defaultValue:"medium",
        options:[
          {label:"Poor",value:"poor"},
          {label:"Medium",value:"medium"},
          {label:"Good",value:"good"}
        ],
        help:"Local drainage condition."
      },
      {
        key:"flood_history_years",
        label:"Historical flood frequency",
        type:"number",
        defaultValue:5,
        min:0,
        max:100,
        step:1,
        unit:"events",
        help:"Number of significant flood events recorded."
      }
    ],
  },
  {
    id: "crop-stress",
    code: "M02",
    shortName: "Crop stress",
    name: "Global Crop Stress Patrol",
    question: "Which fields should be checked first for vegetation, moisture or heat stress?",
    description: "Combines cloud-masked vegetation indices, modelled soil moisture and forecast heat without claiming a disease diagnosis.",
    accent: "#a9d96c",
    timeWindow: "Latest clear scene + 7-day forecast",
    evidence: "Sentinel-2 L2A via Earth Search + Open-Meteo",
    locationBehavior: "Location-sensitive with the Python API. Browser mode uses live local weather plus the visible NDVI/NDMI values.",
    defaultArea: 8_000,
    fields: [
      { key: "use_live_sentinel", label: "Use live Sentinel-2", type: "switch", defaultValue: true, help: "Search and quality-mask a recent Level-2A scene in the Python API." },
      { key: "ndvi", label: "NDVI override", type: "number", defaultValue: 0.55, min: -1, max: 1, step: 0.01, unit: "index", help: "Processed field summary used in browser mode or as an override." },
      { key: "ndmi", label: "NDMI override", type: "number", defaultValue: 0.18, min: -1, max: 1, step: 0.01, unit: "index", help: "Processed canopy-moisture proxy." },
      { key: "sentinel_max_cloud_pct", label: "Scene cloud ceiling", type: "range", defaultValue: 35, min: 0, max: 80, step: 5, unit: "%", help: "Maximum whole-scene cloud metadata accepted during search." },
    ],
    researchFields: [
      {
        key:"crop_type",
        label:"Crop type",
        type:"select",
        defaultValue:"rice",
        options:[
          {label:"Rice",value:"rice"},
          {label:"Maize",value:"maize"},
          {label:"Wheat",value:"wheat"},
          {label:"Vegetable",value:"vegetable"}
        ],
        help:"Dominant crop system."
      },
      {
        key:"growth_stage",
        label:"Crop growth stage",
        type:"select",
        defaultValue:"vegetative",
        options:[
          {label:"Vegetative",value:"vegetative"},
          {label:"Flowering",value:"flowering"},
          {label:"Maturity",value:"maturity"}
        ],
        help:"Current crop stage."
      },
      {
        key:"irrigation_available",
        label:"Irrigation available",
        type:"switch",
        defaultValue:true,
        help:"Availability of supplemental irrigation."
      },
      {
        key:"farmer_stress_observation",
        label:"Observed crop stress",
        type:"range",
        defaultValue:0.5,
        min:0,
        max:1,
        step:0.05,
        help:"Researcher observation score."
      }
    ],
  },
  {
    id: "land-change",
    code: "M03",
    shortName: "Land change",
    name: "Global Wetland & Land-Use Change Audit",
    question: "How have water, cropland and tree-cover shares changed between two observations?",
    description: "Calculates percentage-point changes from baseline and current classified summaries with an explicit verification flag.",
    accent: "#71aee8",
    timeWindow: "User-defined baseline → current",
    evidence: "Validated classified raster summaries supplied by the researcher",
    locationBehavior: "Input-driven: coordinates anchor the study area, but identical class summaries correctly produce identical results.",
    defaultArea: 50_000,
    fields: [
      { key: "baseline_water_pct", label: "Baseline water / wetland", type: "number", defaultValue: 36, min: 0, max: 100, step: 0.1, unit: "%", help: "Classified share at the baseline date." },
      { key: "current_water_pct", label: "Current water / wetland", type: "number", defaultValue: 30, min: 0, max: 100, step: 0.1, unit: "%", help: "Classified share at the current date." },
      { key: "baseline_cropland_pct", label: "Baseline cropland", type: "number", defaultValue: 32, min: 0, max: 100, step: 0.1, unit: "%", help: "Cropland share at baseline." },
      { key: "current_cropland_pct", label: "Current cropland", type: "number", defaultValue: 39, min: 0, max: 100, step: 0.1, unit: "%", help: "Cropland share currently." },
      { key: "baseline_tree_pct", label: "Baseline tree cover", type: "number", defaultValue: 22, min: 0, max: 100, step: 0.1, unit: "%", help: "Tree-cover share at baseline." },
      { key: "current_tree_pct", label: "Current tree cover", type: "number", defaultValue: 18, min: 0, max: 100, step: 0.1, unit: "%", help: "Tree-cover share currently." },
      { key: "class_data_confirmed", label: "I verified the classifications", type: "switch", defaultValue: false, help: "Confirm only after checking products, dates, masks and accuracy evidence." },
    ],
    researchFields: [
      {
        key:"baseline_year",
        label:"Baseline year",
        type:"number",
        defaultValue:2018,
        min:1980,
        max:2026,
        step:1
      },
      {
        key:"current_year",
        label:"Current year",
        type:"number",
        defaultValue:2026,
        min:1980,
        max:2026,
        step:1
      },
      {
        key:"change_detection_verified",
        label:"Change detection verified",
        type:"switch",
        defaultValue:false,
        help:"Confirm after checking satellite classification."
      },
      {
        key:"land_use_category",
        label:"Main land-use type",
        type:"select",
        defaultValue:"cropland",
        options:[
          {label:"Cropland",value:"cropland"},
          {label:"Wetland",value:"wetland"},
          {label:"Forest",value:"forest"},
          {label:"Urban",value:"urban"}
        ]
      }
    ],
  },
  {
    id: "irrigation",
    code: "M04",
    shortName: "Irrigation",
    name: "Global Irrigation Intelligence",
    question: "How much water and pumping energy may be needed in seven days?",
    description: "Uses FAO-56 reference evapotranspiration, crop coefficients, effective rainfall and hydraulic energy equations.",
    accent: "#6fc9e6",
    timeWindow: "7-day forecast",
    evidence: "Open-Meteo ET₀ + rainfall + user system inputs",
    locationBehavior: "Location-sensitive: ET₀ and rainfall are refreshed for the selected coordinate on every run.",
    defaultArea: 1_200,
    fields: [
      { key: "crop", label: "Crop", type: "select", defaultValue: "maize", options: crops.map((crop) => ({ label: crop[0].toUpperCase() + crop.slice(1), value: crop })), help: "Selects a visible default crop coefficient." },
      { key: "effective_rain_fraction", label: "Effective-rain fraction", type: "range", defaultValue: 0.8, min: 0, max: 1, step: 0.05, help: "Share of forecast rain assumed available to the root zone." },
      { key: "application_efficiency", label: "Application efficiency", type: "range", defaultValue: 0.7, min: 0.1, max: 1, step: 0.05, help: "Share of applied water reaching the root zone." },
      { key: "pump_efficiency", label: "Pump efficiency", type: "range", defaultValue: 0.55, min: 0.1, max: 1, step: 0.05, help: "Wire-to-water efficiency." },
      { key: "total_dynamic_head_m", label: "Total dynamic head", type: "number", defaultValue: 18, min: 0, max: 500, step: 1, unit: "m", help: "Static lift plus pressure and friction losses." },
    ],
    researchFields: [
      {
        key:"water_source",
        label:"Water source",
        type:"select",
        defaultValue:"groundwater",
        options:[
          {label:"Groundwater",value:"groundwater"},
          {label:"River",value:"river"},
          {label:"Rainwater",value:"rainwater"}
        ]
      },
      {
        key:"irrigation_method",
        label:"Irrigation method",
        type:"select",
        defaultValue:"flood",
        options:[
          {label:"Flood irrigation",value:"flood"},
          {label:"Sprinkler",value:"sprinkler"},
          {label:"Drip",value:"drip"}
        ]
      },
      {
        key:"soil_water_holding",
        label:"Soil water holding capacity",
        type:"range",
        defaultValue:0.5,
        min:0,
        max:1,
        step:0.05
      },
      {
        key:"farmer_water_constraint",
        label:"Water availability constraint",
        type:"range",
        defaultValue:0.4,
        min:0,
        max:1,
        step:0.05
      }
    ],
  },
  {
    id: "carbon",
    code: "M05",
    shortName: "Farm carbon",
    name: "Global Agricultural Carbon Scanner",
    question: "What is the Tier 1 footprint of supplied farm activity data?",
    description: "Screens direct fertilizer N₂O, flooded-rice CH₄, energy CO₂ and livestock CH₄ with a visible inventory boundary.",
    accent: "#e7b96d",
    timeWindow: "Selected inventory period",
    evidence: "User activity data + IPCC Tier 1 equations",
    locationBehavior: "Activity-driven: identical activity data correctly produce identical emissions regardless of the map coordinate.",
    defaultArea: 500,
    fields: [
      { key: "fertilizer_n_kg_ha", label: "Fertilizer nitrogen", type: "number", defaultValue: 110, min: 0, max: 1000, step: 1, unit: "kg N/ha", help: "Nitrogen included in the direct soil N₂O calculation." },
      { key: "rice_area_hectares", label: "Flooded rice area", type: "number", defaultValue: 200, min: 0, max: 1_000_000, step: 1, unit: "ha", help: "Area subject to the rice methane factor." },
      { key: "rice_cultivation_days", label: "Rice cultivation period", type: "number", defaultValue: 110, min: 0, max: 365, step: 1, unit: "days", help: "Cultivation days in the inventory period." },
      { key: "diesel_litres", label: "Diesel use", type: "number", defaultValue: 32_500, min: 0, max: 100_000_000, step: 100, unit: "L", help: "On-farm combustion in the boundary." },
      { key: "electricity_kwh", label: "Electricity use", type: "number", defaultValue: 0, min: 0, max: 1_000_000_000, step: 100, unit: "kWh", help: "Inventory-period electricity consumption." },
      { key: "livestock_head", label: "Livestock head", type: "number", defaultValue: 0, min: 0, max: 10_000_000, step: 1, help: "Head count for Tier 1 enteric methane." },
    ],
    researchFields: [
      {
        key:"farm_system",
        label:"Farming system",
        type:"select",
        defaultValue:"mixed",
        options:[
          {label:"Crop only",value:"crop"},
          {label:"Livestock only",value:"livestock"},
          {label:"Mixed farming",value:"mixed"}
        ]
      },
      {
        key:"organic_fertilizer_use",
        label:"Organic fertilizer used",
        type:"switch",
        defaultValue:false
      },
      {
        key:"residue_management",
        label:"Crop residue management",
        type:"select",
        defaultValue:"removed",
        options:[
          {label:"Removed",value:"removed"},
          {label:"Burned",value:"burned"},
          {label:"Returned to soil",value:"returned"}
        ]
      },
      {
        key:"carbon_reduction_practice",
        label:"Climate-smart practices",
        type:"switch",
        defaultValue:false
      }
    ],
  },
  {
    id: "fire-heat",
    code: "M06",
    shortName: "Fire + heat",
    name: "Global Agricultural Fire & Heat Watch",
    question: "Where do heat, dryness, wind and hotspots justify rapid verification?",
    description: "Combines weather indicators and optional NASA FIRMS detections without treating every thermal anomaly as a fire.",
    accent: "#e98569",
    timeWindow: "2-day hotspots + 7-day forecast",
    evidence: "NASA FIRMS (optional key) + Open-Meteo",
    locationBehavior: "Location-sensitive: forecast heat, humidity, rain, wind and configured FIRMS detections are refreshed.",
    defaultArea: 10_000,
    fields: [
      { key: "hotspot_count", label: "Verified hotspot override", type: "number", defaultValue: 0, min: 0, max: 10_000, step: 1, unit: "detections", help: "Leave zero to use the backend FIRMS search when configured." },
    ],
    researchFields: [
      {
        key:"temperature_max_c",
        label:"Maximum temperature",
        type:"number",
        defaultValue:37,
        min:-20,
        max:60,
        step:0.1,
        unit:"°C"
      },
      {
        key:"relative_humidity",
        label:"Relative humidity",
        type:"number",
        defaultValue:35,
        min:0,
        max:100,
        step:1,
        unit:"%"
      },
      {
        key:"rainfall_7d",
        label:"7-day rainfall",
        type:"number",
        defaultValue:5,
        min:0,
        max:1000,
        step:1,
        unit:"mm"
      },
      {
        key:"wind_max_kmh",
        label:"Maximum wind",
        type:"number",
        defaultValue:28,
        min:0,
        max:200,
        step:1,
        unit:"km/h"
      },
      {
        key:"vegetation_dryness",
        label:"Vegetation dryness",
        type:"range",
        defaultValue:0.5,
        min:0,
        max:1,
        step:0.05
      }
    ],
  },
];

export const MISSION_BY_ID = Object.fromEntries(MISSIONS.map((mission) => [mission.id, mission])) as Record<MissionId, MissionDefinition>;

export function defaultParameters(mission: MissionDefinition) {
  return Object.fromEntries(mission.fields.map((field) => [field.key, field.defaultValue])) as Record<string, string | number | boolean>;
}
