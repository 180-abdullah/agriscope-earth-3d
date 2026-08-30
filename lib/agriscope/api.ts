import { MISSION_BY_ID } from "./missions";
import type {
  AnalysisRequest,
  AnalysisResponse,
  AnalysisRun,
  DataStatus,
  GeocodeResult,
  Metric,
  RiskLevel,
  SourceRecord,
} from "./types";

const configuredApi = (import.meta.env.VITE_API_BASE_URL ?? "").trim().replace(/\/$/, "");
const WEATHER_URL = "https://api.open-meteo.com/v1/forecast";
const FLOOD_URL = "https://flood-api.open-meteo.com/v1/flood";

interface Weather {
  temp: number;
  rain: number;
  et0: number;
  humidity: number;
  soilMoisture: number;
  wind: number;
}

function apiBase() {
  if (configuredApi) return configuredApi;
  if (typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname)) {
    return "http://localhost:8000";
  }
  return "";
}

async function fetchWithTimeout(url: string, init: RequestInit = {}, timeout = 15_000) {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeout);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } finally {
    window.clearTimeout(timer);
  }
}

export async function checkApiHealth() {
  const base = apiBase();
  if (!base) return false;
  try {
    return (await fetchWithTimeout(`${base}/api/v1/health`, {}, 4_000)).ok;
  } catch {
    return false;
  }
}

export async function geocode(query: string): Promise<GeocodeResult[]> {
  const clean = query.trim();
  if (clean.length < 2) return [];
  const response = await fetchWithTimeout(
    `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(clean)}&count=7&language=en&format=json`,
    { headers: { Accept: "application/json" } },
    10_000,
  );
  if (!response.ok) throw new Error("Location search is temporarily unavailable.");
  const body = (await response.json()) as { results?: Array<Record<string, unknown>> };
  return (body.results ?? []).map((row) => ({
    id: Number(row.id ?? 0),
    name: String(row.name ?? "Unknown location"),
    latitude: Number(row.latitude),
    longitude: Number(row.longitude),
    country: row.country ? String(row.country) : undefined,
    admin1: row.admin1 ? String(row.admin1) : undefined,
  }));
}

export async function runAnalysis(request: AnalysisRequest): Promise<AnalysisRun> {
  const base = apiBase();
  if (base) {
    try {
      const response = await fetchWithTimeout(
        `${base}/api/v1/analyze`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify(request),
        },
        request.mission === "crop-stress" ? 50_000 : 22_000,
      );
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return { result: (await response.json()) as AnalysisResponse, mode: "python-api" };
    } catch (error) {
      return {
        result: await runBrowserEngine(request),
        mode: "browser-live-preview",
        warning: `The Python research service was unavailable (${error instanceof Error ? error.message : "connection error"}). The app used its labelled live browser calculation instead.`,
      };
    }
  }
  return {
    result: await runBrowserEngine(request),
    mode: "browser-live-preview",
    warning: "This public interface is using live browser calculations. Deploy the included FastAPI backend and set VITE_API_BASE_URL for Sentinel processing, FIRMS and the authoritative research engine.",
  };
}

function clamp(value: number, low = 0, high = 100) {
  return Math.max(low, Math.min(high, value));
}

function n(request: AnalysisRequest, key: string, fallback: number) {
  const value = Number(request.parameters[key] ?? fallback);
  return Number.isFinite(value) ? value : fallback;
}

function mean(values: Array<number | null | undefined>, fallback = 0) {
  const clean = values.filter((value): value is number => typeof value === "number" && Number.isFinite(value));
  return clean.length ? clean.reduce((sum, value) => sum + value, 0) / clean.length : fallback;
}

function sum(values: Array<number | null | undefined>) {
  return values.reduce<number>((total, value) => total + (typeof value === "number" && Number.isFinite(value) ? value : 0), 0);
}

function max(values: Array<number | null | undefined>, fallback = 0) {
  const clean = values.filter((value): value is number => typeof value === "number" && Number.isFinite(value));
  return clean.length ? Math.max(...clean) : fallback;
}

function risk(score: number): RiskLevel {
  if (score < 25) return "low";
  if (score < 50) return "moderate";
  if (score < 75) return "high";
  return "severe";
}

async function publicJson(url: string, params: Record<string, string | number>) {
  const query = new URLSearchParams(Object.entries(params).map(([key, value]) => [key, String(value)]));
  const response = await fetchWithTimeout(`${url}?${query}`, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`Earth-data service returned HTTP ${response.status}.`);
  return (await response.json()) as Record<string, unknown>;
}

async function fetchWeather(latitude: number, longitude: number): Promise<Weather> {
  const payload = await publicJson(WEATHER_URL, {
    latitude,
    longitude,
    hourly: "relative_humidity_2m,soil_moisture_0_to_7cm,wind_speed_10m",
    daily: "temperature_2m_max,precipitation_sum,et0_fao_evapotranspiration",
    forecast_days: 7,
    timezone: "auto",
  });
  const daily = (payload.daily ?? {}) as Record<string, Array<number | null>>;
  const hourly = (payload.hourly ?? {}) as Record<string, Array<number | null>>;
  return {
    temp: max(daily.temperature_2m_max ?? [], 28),
    rain: sum(daily.precipitation_sum ?? []),
    et0: sum(daily.et0_fao_evapotranspiration ?? []),
    humidity: mean(hourly.relative_humidity_2m ?? [], 60),
    soilMoisture: mean(hourly.soil_moisture_0_to_7cm ?? [], 0.24),
    wind: max(hourly.wind_speed_10m ?? [], 12),
  };
}

function weatherSource(): SourceRecord {
  return {
    name: "Open-Meteo Weather Forecast API",
    url: "https://open-meteo.com/en/docs",
    role: "Forecast temperature, precipitation, soil moisture, wind and FAO reference evapotranspiration",
    status: "forecast",
    spatial_resolution: "Model-dependent; commonly 1–25 km",
    temporal_resolution: "Hourly and daily",
    note: "Model output; not an on-farm sensor observation.",
    accessed_at: new Date().toISOString(),
  };
}

function makeResult(
  request: AnalysisRequest,
  score: number,
  confidence: number,
  summary: string,
  statuses: DataStatus[],
  metrics: Metric[],
  sources: SourceRecord[],
  caveats: string[],
): AnalysisResponse {
  const bounded = clamp(score);
  return {
    analysis_id: globalThis.crypto?.randomUUID?.() ?? `browser-${Date.now()}`,
    generated_at: new Date().toISOString(),
    methodology_version: "ASE-1.0-browser-preview",
    mission: request.mission,
    title: MISSION_BY_ID[request.mission].name,
    coordinates: { latitude: request.latitude, longitude: request.longitude },
    area_hectares: request.area_hectares,
    score: +bounded.toFixed(1),
    risk_level: risk(bounded),
    confidence,
    summary,
    data_status: [...new Set(statuses)],
    metrics,
    sources,
    caveats: [
      ...caveats,
      "Browser-mode output is for transparent screening. Use the Python API and evidence receipt before formal research use.",
    ],
    geometry: {
      type: "Feature",
      geometry: { type: "Point", coordinates: [request.longitude, request.latitude] },
      properties: { mission: request.mission, score: bounded },
    },
  };
}

async function floodResult(request: AnalysisRequest) {
  const [weather, floodPayload] = await Promise.all([
    fetchWeather(request.latitude, request.longitude),
    publicJson(FLOOD_URL, {
      latitude: request.latitude,
      longitude: request.longitude,
      daily: "river_discharge,river_discharge_mean,river_discharge_max",
      forecast_days: 7,
    }),
  ]);
  const daily = (floodPayload.daily ?? {}) as Record<string, Array<number | null>>;
  const discharge = daily.river_discharge ?? [];
  const qMean = mean(daily.river_discharge_mean ?? discharge, max(discharge, 1));
  const qPeak = max(daily.river_discharge_max ?? discharge, Math.max(qMean, 1));
  const ratio = qPeak / Math.max(qMean, 0.001);
  const sensitivity = clamp(n(request, "crop_stage_sensitivity", 0.75), 0, 1);
  const drainage = clamp(n(request, "drainage_vulnerability", 0.55), 0, 1);
  const score = clamp(0.5 * clamp(((ratio - 0.7) / 1.6) * 100) + 0.2 * clamp((weather.rain / 120) * 100) + 15 * sensitivity + 15 * drainage);
  const exposed = request.area_hectares * clamp(score / 115, 0, 0.88);
  return makeResult(request, score, 0.72, `The live seven-day river and rainfall screen indicates ${risk(score)} flood-exposure potential. Verify flood depth, field elevation and crop stage locally.`, ["forecast", "modelled", "user-supplied"], [
    { key: "discharge_ratio", label: "Peak / mean discharge", value: +ratio.toFixed(2), unit: "ratio", interpretation: "Seven-day forecast maximum relative to mean." },
    { key: "rain_7d", label: "Forecast precipitation", value: +weather.rain.toFixed(1), unit: "mm / 7 d", interpretation: "Weather-model total at the selected coordinate." },
    { key: "exposed_area", label: "Screened exposure", value: +exposed.toFixed(1), unit: "ha", interpretation: "Priority area, not measured crop loss." },
  ], [
    { name: "Open-Meteo Global Flood API / GloFAS", url: "https://open-meteo.com/en/docs/flood-api", role: "River-discharge forecast near the target", status: "forecast", spatial_resolution: "Largest modelled river within approximately 5 km", accessed_at: new Date().toISOString() },
    weatherSource(),
  ], ["Discharge does not directly represent inundation depth.", "The exposed area is a screening estimate, not a damage map."]);
}

async function cropResult(request: AnalysisRequest) {
  const weather = await fetchWeather(request.latitude, request.longitude);
  const ndvi = clamp(n(request, "ndvi", 0.55), -1, 1);
  const ndmi = clamp(n(request, "ndmi", 0.18), -1, 1);
  const score = clamp(
    0.32 * clamp(((0.6 - ndvi) / 0.48) * 100) +
      0.23 * clamp(((0.28 - ndmi) / 0.43) * 100) +
      0.2 * clamp(((0.26 - weather.soilMoisture) / 0.2) * 100) +
      0.15 * clamp(((weather.temp - 29) / 13) * 100) +
      0.1 * clamp(((24 - weather.rain) / 24) * 100),
  );
  return makeResult(request, score, 0.56, `Visible vegetation-index inputs and live weather indicate ${risk(score)} crop-stress potential. This prioritizes field inspection and does not diagnose a cause.`, ["user-supplied", "forecast", "modelled"], [
    { key: "ndvi", label: "NDVI", value: +ndvi.toFixed(3), unit: "index", interpretation: "Visible override used in browser mode." },
    { key: "ndmi", label: "NDMI", value: +ndmi.toFixed(3), unit: "index", interpretation: "Visible canopy-moisture proxy." },
    { key: "soil_moisture", label: "Surface soil moisture", value: +weather.soilMoisture.toFixed(3), unit: "m³/m³", interpretation: "Model grid value, not a field probe." },
    { key: "temperature", label: "Forecast maximum", value: +weather.temp.toFixed(1), unit: "°C", interpretation: "Maximum over seven days." },
  ], [
    { name: "User-visible NDVI / NDMI", role: "Vegetation-index summary for browser mode", status: "user-supplied" },
    weatherSource(),
  ], ["Connect the Python API for recorded Sentinel-2 search, quality masking and scene metadata.", "Index thresholds vary by crop, stage, soil and atmosphere."]);
}

function landResult(request: AnalysisRequest) {
  const bw = clamp(n(request, "baseline_water_pct", 36));
  const cw = clamp(n(request, "current_water_pct", 30));
  const bc = clamp(n(request, "baseline_cropland_pct", 32));
  const cc = clamp(n(request, "current_cropland_pct", 39));
  const bt = clamp(n(request, "baseline_tree_pct", 22));
  const ct = clamp(n(request, "current_tree_pct", 18));
  const water = cw - bw;
  const crop = cc - bc;
  const tree = ct - bt;
  const score = clamp((Math.max(0, -water) + Math.max(0, -tree)) * 6.5 + Math.max(0, crop) * 3.5);
  const confirmed = Boolean(request.parameters.class_data_confirmed);
  return makeResult(request, score, confirmed ? 0.76 : 0.36, `The ${confirmed ? "verified" : "unconfirmed example"} class summaries indicate ${risk(score)} ecological-conversion pressure. Changing only the coordinate should not change supplied class totals.`, [confirmed ? "user-supplied" : "demonstration", "calculated"], [
    { key: "water_change", label: "Water / wetland change", value: +water.toFixed(2), unit: "percentage points", interpretation: "Current minus baseline share." },
    { key: "cropland_change", label: "Cropland change", value: +crop.toFixed(2), unit: "percentage points", interpretation: "Current minus baseline share." },
    { key: "tree_change", label: "Tree-cover change", value: +tree.toFixed(2), unit: "percentage points", interpretation: "Current minus baseline share." },
  ], [{ name: "Researcher-supplied classified summaries", role: "Baseline and current land-cover shares", status: confirmed ? "user-supplied" : "demonstration" }], ["Class totals do not locate individual transitions; use a pixel-level transition matrix.", "Season, sensor, classifier and masks can create false change."]);
}

async function irrigationResult(request: AnalysisRequest) {
  const weather = await fetchWeather(request.latitude, request.longitude);
  const coefficients: Record<string, number> = { rice: 1.1, maize: 1.05, wheat: 1, soybean: 1, cotton: 1.05, potato: 1.05, vegetables: 1, orchard: 0.9 };
  const crop = String(request.parameters.crop ?? "maize");
  const kc = coefficients[crop] ?? 1;
  const effectiveRain = weather.rain * clamp(n(request, "effective_rain_fraction", 0.8), 0, 1);
  const cropEt = kc * weather.et0;
  const raw = cropEt - effectiveRain;
  const net = Math.max(0, raw);
  const gross = net / clamp(n(request, "application_efficiency", 0.7), 0.1, 1);
  const volume = gross * request.area_hectares * 10;
  const head = Math.max(0, n(request, "total_dynamic_head_m", 18));
  const pumpEfficiency = clamp(n(request, "pump_efficiency", 0.55), 0.1, 1);
  const energy = (1000 * 9.80665 * head * volume) / 3_600_000 / pumpEfficiency;
  const score = clamp((gross / 65) * 100);
  const summary = net <= 0
    ? `No positive seven-day irrigation deficit is indicated: crop ET is ${cropEt.toFixed(1)} mm and effective rain is ${effectiveRain.toFixed(1)} mm. Pumping is zero for this forecast balance.`
    : `The live seven-day screen estimates ${gross.toFixed(1)} mm gross irrigation for ${crop}. Verify root-zone water and crop stage before operating equipment.`;
  return makeResult(request, score, 0.72, summary, ["forecast", "calculated", "user-supplied"], [
    { key: "et0", label: "Reference ET₀", value: +weather.et0.toFixed(1), unit: "mm / 7 d", interpretation: "FAO reference evapotranspiration from the selected coordinate." },
    { key: "rain", label: "Forecast rainfall", value: +weather.rain.toFixed(1), unit: "mm / 7 d", interpretation: "Forecast before the effective-rain fraction." },
    { key: "raw_balance", label: "Crop ET − effective rain", value: +raw.toFixed(1), unit: "mm", interpretation: "Values at or below zero produce no deficit." },
    { key: "gross_depth", label: "Gross irrigation depth", value: +gross.toFixed(1), unit: "mm", interpretation: "Net deficit adjusted for application efficiency." },
    { key: "water_volume", label: "Irrigation volume", value: Math.round(volume), unit: "m³", interpretation: "1 mm over 1 ha equals 10 m³." },
    { key: "energy", label: "Pumping electricity", value: +energy.toFixed(1), unit: "kWh", interpretation: "Hydraulic work adjusted for pump efficiency." },
  ], [weatherSource()], ["This balance does not simulate root-zone storage or irrigation timing.", "Crop coefficients vary by stage, climate and management.", "Actual energy depends on motor, transmission and pipe condition."]);
}

function carbonResult(request: AnalysisRequest) {
  const nitrogen = Math.max(0, n(request, "fertilizer_n_kg_ha", 110));
  const riceArea = clamp(n(request, "rice_area_hectares", request.area_hectares * 0.4), 0, request.area_hectares);
  const riceDays = Math.max(0, n(request, "rice_cultivation_days", 110));
  const diesel = Math.max(0, n(request, "diesel_litres", 65 * request.area_hectares));
  const electricity = Math.max(0, n(request, "electricity_kwh", 0));
  const livestock = Math.max(0, n(request, "livestock_head", 0));
  const fertilizer = nitrogen * request.area_hectares * 0.01 * (44 / 28) * 273;
  const rice = 1.19 * riceArea * riceDays * 27.2;
  const energy = diesel * 2.68 + electricity * 0.45;
  const animals = livestock * 47 * 27.2;
  const total = fertilizer + rice + energy + animals;
  const intensity = total / 1000 / request.area_hectares;
  const score = clamp((intensity / 12) * 100);
  return makeResult(request, score, 0.66, `The Tier 1 screen estimates ${(total / 1000).toFixed(1)} t CO₂e, or ${intensity.toFixed(2)} t CO₂e/ha. Location alone is not an emission factor, so identical activity data correctly return the same value.`, ["user-supplied", "modelled", "calculated"], [
    { key: "total", label: "Total screening emissions", value: +(total / 1000).toFixed(2), unit: "t CO₂e", interpretation: "Sum of included sources." },
    { key: "intensity", label: "Area-based intensity", value: +intensity.toFixed(3), unit: "t CO₂e/ha", interpretation: "Total divided by selected area." },
    { key: "fertilizer", label: "Direct fertilizer N₂O", value: +(fertilizer / 1000).toFixed(2), unit: "t CO₂e", interpretation: "Direct soil N₂O only." },
    { key: "rice", label: "Rice methane", value: +(rice / 1000).toFixed(2), unit: "t CO₂e", interpretation: "Tier 1 flooded-rice factor." },
    { key: "energy", label: "Energy", value: +(energy / 1000).toFixed(2), unit: "t CO₂e", interpretation: "Diesel plus default grid factor." },
    { key: "livestock", label: "Enteric methane", value: +(animals / 1000).toFixed(2), unit: "t CO₂e", interpretation: "Tier 1 head-count estimate." },
  ], [{ name: "IPCC 2006 Guidelines and 2019 Refinement", url: "https://www.ipcc-nggip.iges.or.jp/public/2019rf/", role: "Tier 1 agricultural GHG equations and defaults", status: "modelled" }], ["Use jurisdiction- and system-specific factors where available.", "Indirect N₂O, manure management, upstream inputs, soil-carbon change and transport are outside the default boundary."]);
}

function heatIndexC(tempC: number, humidity: number) {
  const t = (tempC * 9) / 5 + 32;
  const r = clamp(humidity, 0, 100);
  let hi = -42.379 + 2.04901523 * t + 10.14333127 * r - 0.22475541 * t * r - 0.00683783 * t ** 2 - 0.05481717 * r ** 2 + 0.00122874 * t ** 2 * r + 0.00085282 * t * r ** 2 - 0.00000199 * t ** 2 * r ** 2;
  if (t < 80) hi = t;
  return ((hi - 32) * 5) / 9;
}

async function fireResult(request: AnalysisRequest) {
  const weather = await fetchWeather(request.latitude, request.longitude);
  const hotspots = Math.max(0, n(request, "hotspot_count", 0));
  const hi = heatIndexC(weather.temp, weather.humidity);
  const score = clamp(0.35 * clamp(((hi - 28) / 18) * 100) + 0.25 * clamp(((35 - weather.rain) / 35) * 100) * clamp((55 - weather.humidity) / 35, 0.25, 1) + 0.15 * clamp((weather.wind / 45) * 100) + 0.25 * clamp((hotspots / 8) * 100));
  return makeResult(request, score, 0.54, `Live heat, rain and wind plus the visible hotspot input indicate ${risk(score)} concern. Connect the Python API with NASA FIRMS for near-real-time detections.`, ["forecast", "modelled", hotspots > 0 ? "user-supplied" : "unavailable"], [
    { key: "heat_index", label: "Heat index", value: +hi.toFixed(1), unit: "°C", interpretation: "Apparent-temperature screening indicator." },
    { key: "hotspots", label: "Hotspot input", value: Math.round(hotspots), unit: "detections", interpretation: "Visible override, not a live FIRMS result in browser mode." },
    { key: "rain", label: "Seven-day precipitation", value: +weather.rain.toFixed(1), unit: "mm", interpretation: "Lower rain increases dryness concern." },
    { key: "wind", label: "Maximum wind", value: +weather.wind.toFixed(1), unit: "km/h", interpretation: "Weather-model spread proxy." },
  ], [weatherSource(), { name: "NASA FIRMS backend connection", role: "Near-real-time thermal detections", status: hotspots > 0 ? "user-supplied" : "unavailable" }], ["A thermal anomaly is not automatically an agricultural fire.", "Follow authoritative local warnings and verify detections."]);
}

async function runBrowserEngine(request: AnalysisRequest) {
  switch (request.mission) {
    case "flood-watch": return floodResult(request);
    case "crop-stress": return cropResult(request);
    case "land-change": return landResult(request);
    case "irrigation": return irrigationResult(request);
    case "carbon": return carbonResult(request);
    case "fire-heat": return fireResult(request);
  }
}
