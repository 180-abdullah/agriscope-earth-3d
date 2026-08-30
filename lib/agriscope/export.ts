import type { AnalysisResponse } from "./types";

export type ExportFormat = "json" | "csv" | "geojson" | "markdown";

function quote(value: unknown) {
  const text = value == null ? "" : String(value);
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

function toMarkdown(result: AnalysisResponse) {
  const metrics = result.metrics.map((metric) => `| ${metric.label} | ${metric.value ?? "—"} | ${metric.unit} | ${metric.interpretation} |`).join("\n");
  const sources = result.sources.map((source) => `- **${source.name}** — ${source.role} (${source.status})${source.url ? ` — ${source.url}` : ""}`).join("\n");
  const caveats = result.caveats.map((caveat) => `- ${caveat}`).join("\n");
  return `# ${result.title}\n\n- Analysis ID: ${result.analysis_id}\n- Generated: ${result.generated_at}\n- Method: ${result.methodology_version}\n- Target: ${result.coordinates.latitude.toFixed(5)}, ${result.coordinates.longitude.toFixed(5)}\n- Area: ${result.area_hectares.toLocaleString()} ha\n- Priority: ${result.score.toFixed(1)} / 100 (${result.risk_level})\n- Evidence confidence: ${(result.confidence * 100).toFixed(0)}%\n- Evidence status: ${result.data_status.join(", ")}\n\n## Interpretation\n\n${result.summary}\n\n## Metrics\n\n| Metric | Value | Unit | Interpretation |\n|---|---:|---|---|\n${metrics}\n\n## Sources\n\n${sources || "- No external source recorded."}\n\n## Limitations\n\n${caveats}\n`;
}

export function downloadResult(result: AnalysisResponse, format: ExportFormat) {
  let body: string;
  let mime: string;
  const extension = format === "markdown" ? "md" : format;
  if (format === "json") {
    body = JSON.stringify(result, null, 2);
    mime = "application/json";
  } else if (format === "geojson") {
    body = JSON.stringify({ type: "FeatureCollection", features: [{ ...result.geometry, properties: { ...result.geometry.properties, analysis_id: result.analysis_id, mission: result.mission, score: result.score, risk_level: result.risk_level, generated_at: result.generated_at } }] }, null, 2);
    mime = "application/geo+json";
  } else if (format === "csv") {
    const rows: unknown[][] = [
      ["analysis_id", result.analysis_id],
      ["mission", result.mission],
      ["generated_at", result.generated_at],
      ["latitude", result.coordinates.latitude],
      ["longitude", result.coordinates.longitude],
      ["area_hectares", result.area_hectares],
      ["score", result.score],
      ["risk_level", result.risk_level],
      [],
      ["metric_key", "metric_label", "value", "unit", "interpretation"],
      ...result.metrics.map((metric) => [metric.key, metric.label, metric.value, metric.unit, metric.interpretation]),
    ];
    body = rows.map((row) => row.map(quote).join(",")).join("\n");
    mime = "text/csv";
  } else {
    body = toMarkdown(result);
    mime = "text/markdown";
  }
  const url = URL.createObjectURL(new Blob([body], { type: `${mime};charset=utf-8` }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `agriscope-${result.mission}-${result.analysis_id.slice(0, 8)}.${extension}`;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
