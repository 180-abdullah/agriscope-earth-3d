export type MissionId =
  | "flood-watch"
  | "crop-stress"
  | "land-change"
  | "irrigation"
  | "carbon"
  | "fire-heat";

export type DataStatus =
  | "observed"
  | "near-real-time"
  | "forecast"
  | "modelled"
  | "calculated"
  | "user-supplied"
  | "demonstration"
  | "unavailable";

export type RiskLevel = "low" | "moderate" | "high" | "severe";
export type BasemapId = "satellite" | "dark" | "street";
export type ExecutionMode = "python-api" | "browser-live-preview";

export interface Metric {
  key: string;
  label: string;
  value: number | string | null;
  unit: string;
  interpretation: string;
}

export interface SourceRecord {
  name: string;
  url?: string | null;
  role: string;
  status: DataStatus;
  spatial_resolution?: string | null;
  temporal_resolution?: string | null;
  note?: string | null;
  identifier?: string | null;
  acquisition_datetime?: string | null;
  accessed_at?: string | null;
  license?: string | null;
}

export interface AnalysisResponse {
  analysis_id: string;
  generated_at: string;
  methodology_version: string;
  mission: MissionId;
  title: string;
  coordinates: { latitude: number; longitude: number };
  area_hectares: number;
  score: number;
  risk_level: RiskLevel;
  confidence: number;
  summary: string;
  data_status: DataStatus[];
  metrics: Metric[];
  sources: SourceRecord[];
  caveats: string[];
  geometry: {
    type: "Feature";
    geometry: { type: "Point"; coordinates: [number, number] };
    properties: Record<string, unknown>;
  };
}

export interface AnalysisRequest {
  mission: MissionId;
  latitude: number;
  longitude: number;
  area_hectares: number;
  name?: string;
  parameters: Record<string, string | number | boolean>;
}

export interface AnalysisRun {
  result: AnalysisResponse;
  mode: ExecutionMode;
  warning?: string;
}

export interface GeocodeResult {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
  country?: string;
  admin1?: string;
}

export interface ParameterField {
  key: string;
  label: string;
  type: "number" | "range" | "select" | "switch";
  defaultValue: string | number | boolean;
  help: string;
  unit?: string;
  min?: number;
  max?: number;
  step?: number;
  options?: { label: string; value: string }[];
}

export interface MissionDefinition {
  id: MissionId;
  code: string;
  shortName: string;
  name: string;
  question: string;
  description: string;
  accent: string;
  timeWindow: string;
  evidence: string;
  locationBehavior: string;
  defaultArea: number;
  fields: ParameterField[];
}
