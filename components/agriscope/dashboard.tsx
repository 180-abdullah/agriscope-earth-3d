"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  BarChart3,
  Database,
  Download,
  FileJson,
  FileText,
  Globe2,
  Layers,
  MapPin,
  Mountain,
  Pause,
  Play,
  Search,
  Settings2,
  Table2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverDescription,
  PopoverHeader,
  PopoverTitle,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { checkApiHealth, geocode, runAnalysis } from "@/lib/agriscope/api";
import { downloadResult, type ExportFormat } from "@/lib/agriscope/export";
import { defaultParameters, MISSIONS, MISSION_BY_ID } from "@/lib/agriscope/missions";
import type {
  AnalysisResponse,
  BasemapId,
  GeocodeResult,
  MissionId,
  ParameterField,
} from "@/lib/agriscope/types";

import { EarthGlobe } from "./earth-globe";

const METHODS: Record<MissionId, { equation: string; steps: string[] }> = {
  "flood-watch": {
    equation: "Priority = 0.50D + 0.20P + 15C + 15V",
    steps: [
      "Fetch seven-day river-discharge and rainfall forecasts for the target.",
      "Normalize peak-to-mean discharge (D) and rainfall (P).",
      "Add crop-stage (C) and drainage (V) vulnerability assumptions.",
      "Convert the bounded score to a screening exposure area—not measured loss.",
    ],
  },
  "crop-stress": {
    equation: "Priority = 0.32Nᵥ + 0.23Nₘ + 0.20S + 0.15H + 0.10R",
    steps: [
      "Search recent Sentinel-2 L2A scenes and apply the documented quality mask.",
      "Calculate clear-pixel median NDVI and NDMI over a bounded target sample.",
      "Combine vegetation, moisture, heat and rainfall stress components.",
      "Use the output to prioritize inspection; it does not diagnose disease or deficiency.",
    ],
  },
  "land-change": {
    equation: "Pressure = 6.5(max(0,−Δwater)+max(0,−Δtree)) + 3.5max(0,Δcrop)",
    steps: [
      "Receive baseline and current class shares from validated classifications.",
      "Calculate percentage-point differences for water, cropland and tree cover.",
      "Summarize ecological-loss and conversion-pressure components.",
      "Require pixel-level transitions and accuracy evidence for confirmatory research.",
    ],
  },
  irrigation: {
    equation: "ETc = Kc×ET₀;  Igross = max(0, ETc−Peff)/Ea;  E = ρgHV/(3.6×10⁶ηp)",
    steps: [
      "Fetch seven-day FAO reference ET₀ and rainfall for the coordinate.",
      "Convert ET₀ to crop ET using the selected crop coefficient.",
      "Subtract effective rain and adjust positive deficit for application efficiency.",
      "Convert depth to volume and hydraulic work to pumping electricity.",
    ],
  },
  carbon: {
    equation: "CO₂e = fertilizer N₂O + rice CH₄ + diesel/electricity CO₂ + enteric CH₄",
    steps: [
      "Apply visible Tier 1 factors to supplied farm activity data.",
      "Convert CH₄ and N₂O to CO₂-equivalent with consistent GWP values.",
      "Report totals and area intensity inside the stated inventory boundary.",
      "Replace defaults with jurisdiction- and system-specific factors where available.",
    ],
  },
  "fire-heat": {
    equation: "Priority = 0.35H + 0.25D + 0.15W + 0.25F",
    steps: [
      "Fetch forecast heat, humidity, rain and wind for the target.",
      "Optionally retrieve nearby NASA FIRMS thermal detections.",
      "Combine heat (H), dryness (D), wind (W) and hotspot (F) components.",
      "Verify each detection and follow official local warnings.",
    ],
  },
};

function initialParameterState() {
  return Object.fromEntries(MISSIONS.map((mission) => [mission.id, defaultParameters(mission)])) as Record<
    MissionId,
    Record<string, string | number | boolean>
  >;
}

export function AgriScopeDashboard() {
  const [missionId, setMissionId] = useState<MissionId>("irrigation");
  const [analysisMode, setAnalysisMode] = useState<"guided" | "research">("guided");
  const [interfaceMode, setInterfaceMode] = useState<"guided" | "research">("guided");
  const researchMode = interfaceMode === "research";
  const [researchObjective, setResearchObjective] = useState("");
  const [cropSystem, setCropSystem] = useState("");
  const mission = MISSION_BY_ID[missionId];
  const [latitude, setLatitude] = useState(23.685);
  const [longitude, setLongitude] = useState(90.3563);
  const [placeName, setPlaceName] = useState("Bangladesh sample target");
  const [areaHectares, setAreaHectares] = useState(mission.defaultArea);
  const [parameters, setParameters] = useState(initialParameterState);
  const [query, setQuery] = useState("");
  const [searchRows, setSearchRows] = useState<GeocodeResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [setupOpen, setSetupOpen] = useState(false);
  const [resultsOpen, setResultsOpen] = useState(false);
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState("");
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [history, setHistory] = useState<AnalysisResponse[]>([]);
  const [runWarning, setRunWarning] = useState("");
  const [runMode, setRunMode] = useState<"python-api" | "browser-live-preview" | null>(null);
  const [lastRunSignature, setLastRunSignature] = useState("");
  const [apiConnected, setApiConnected] = useState<boolean | null>(null);
  const [globeReady, setGlobeReady] = useState(false);
  const [basemap, setBasemap] = useState<BasemapId>("satellite");
  const hasTerrainToken = Boolean((import.meta.env.VITE_CESIUM_ION_TOKEN ?? "").trim());
  const [terrainEnabled, setTerrainEnabled] = useState(hasTerrainToken);
  const [animationEnabled, setAnimationEnabled] = useState(true);
  const [layerOpacity, setLayerOpacity] = useState(0.82);

  useEffect(() => {
    void checkApiHealth().then(setApiConnected);
  }, []);

  const currentParameters = parameters[missionId];
  const signature = useMemo(
    () => JSON.stringify({ missionId, latitude, longitude, areaHectares, currentParameters }),
    [missionId, latitude, longitude, areaHectares, currentParameters],
  );
  const stale = Boolean(result && signature !== lastRunSignature);

  const pickTarget = useCallback((nextLatitude: number, nextLongitude: number) => {
    setLatitude(+nextLatitude.toFixed(6));
    setLongitude(+nextLongitude.toFixed(6));
    setPlaceName(`Map point · ${nextLatitude.toFixed(4)}, ${nextLongitude.toFixed(4)}`);
  }, []);
  const readyCallback = useCallback((value: boolean) => setGlobeReady(value), []);

  function chooseMission(next: MissionId) {
    setMissionId(next);
    setAreaHectares(MISSION_BY_ID[next].defaultArea);
    setRunError("");
  }

  function updateParameter(key: string, value: string | number | boolean) {
    setParameters((previous) => ({
      ...previous,
      [missionId]: { ...previous[missionId], [key]: value },
    }));
  }

  async function searchLocation(event: React.FormEvent) {
    event.preventDefault();
    setSearchError("");
    setSearching(true);
    try {
      const rows = await geocode(query);
      setSearchRows(rows);
      if (!rows.length) setSearchError("No matching place found. Try a city, district or country.");
    } catch (error) {
      setSearchError(error instanceof Error ? error.message : "Location search failed.");
    } finally {
      setSearching(false);
    }
  }

  function selectPlace(row: GeocodeResult) {
    setLatitude(row.latitude);
    setLongitude(row.longitude);
    setPlaceName([row.name, row.admin1, row.country].filter(Boolean).join(", "));
    setQuery("");
    setSearchRows([]);
  }

  async function analyze() {
    setRunError("");
    setRunWarning("");
    if (!Number.isFinite(latitude) || latitude < -90 || latitude > 90 || !Number.isFinite(longitude) || longitude < -180 || longitude > 180) {
      setRunError("Latitude must be −90 to 90 and longitude −180 to 180.");
      return;
    }
    if (!Number.isFinite(areaHectares) || areaHectares <= 0 || areaHectares > 10_000_000) {
      setRunError("Analysis area must be greater than 0 and no more than 10,000,000 ha.");
      return;
    }
    setRunning(true);
    try {
      const run = await runAnalysis({
        mission: missionId,
        latitude,
        longitude,
        area_hectares: areaHectares,
        name: placeName,
        parameters: {
          ...currentParameters,
          research_objective: researchObjective,
          crop_system: cropSystem,
          analysis_mode: analysisMode,
        },
      });
      setResult(run.result);
      setRunMode(run.mode);
      setRunWarning(run.warning ?? "");
      setLastRunSignature(signature);
      setHistory((previous) => [run.result, ...previous].slice(0, 10));
      setSetupOpen(false);
      setResultsOpen(true);
      setApiConnected(run.mode === "python-api");
    } catch (error) {
      setRunError(error instanceof Error ? error.message : "Analysis could not be completed.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <main className="app-root">
      <EarthGlobe
        latitude={latitude}
        longitude={longitude}
        areaHectares={areaHectares}
        mission={mission}
        result={stale ? null : result}
        basemap={basemap}
        terrainEnabled={terrainEnabled}
        animationEnabled={animationEnabled}
        opacity={layerOpacity}
        onPick={pickTarget}
        onReady={readyCallback}
      />

      <header className="topbar">
        <div className="brand-lockup">
          <span className="brand-mark"><Globe2 /></span>
          <span><strong>AgriScope</strong><small>Earth intelligence</small></span>
        </div>

        <form className="place-search" onSubmit={searchLocation}>
          <Search aria-hidden="true" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search any place worldwide"
            aria-label="Search any place worldwide"
          />
          <button type="submit" disabled={searching || query.trim().length < 2}>
            {searching ? "Finding…" : "Go"}
          </button>
          {(searchRows.length > 0 || searchError) && (
            <div className="search-results">
              {searchError && <p>{searchError}</p>}
              {searchRows.map((row) => (
                <button key={`${row.id}-${row.latitude}-${row.longitude}`} type="button" onClick={() => selectPlace(row)}>
                  <MapPin />
                  <span><strong>{row.name}</strong><small>{[row.admin1, row.country].filter(Boolean).join(", ")}</small></span>
                </button>
              ))}
            </div>
          )}
        </form>

        <div className="top-actions">
          <div className="mode-selector">
            <Button
              variant={analysisMode === "guided" ? "default" : "outline"}
              onClick={() => setAnalysisMode("guided")}
            >
              Guided Mode
            </Button>
            <Button
              variant={analysisMode === "research" ? "default" : "outline"}
              onClick={() => setAnalysisMode("research")}
            >
              Research Mode
            </Button>
          </div>
          <span className={`data-state ${apiConnected ? "connected" : "preview"}`} title={apiConnected ? "Python FastAPI is connected" : "Live browser mode"}>
            <i />{apiConnected ? "Python API" : "Live preview"}
          </span>
          <Button variant="outline" onClick={() => setSetupOpen(true)}><Settings2 /> Setup</Button>
          <Button variant="outline" disabled={!result} onClick={() => setResultsOpen(true)}><BarChart3 /> Results</Button>
        </div>
      </header>

      <div className="target-chip">
        <MapPin />
        <span><strong>{placeName}</strong><small>{latitude.toFixed(4)}, {longitude.toFixed(4)} · {areaHectares.toLocaleString()} ha</small></span>
      </div>

      <div className="map-tools">
        <Popover>
          <PopoverTrigger asChild>
            <Button size="icon" variant="outline" aria-label="Open Earth layer controls"><Layers /></Button>
          </PopoverTrigger>
          <PopoverContent align="end" className="layer-popover">
            <PopoverHeader>
              <PopoverTitle>Earth layers</PopoverTitle>
              <PopoverDescription>Satellite imagery is keyless. Cesium World Terrain uses a free ion token.</PopoverDescription>
            </PopoverHeader>
            <label className="compact-field"><span>Basemap</span>
              <Select value={basemap} onValueChange={(value) => setBasemap(value as BasemapId)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="satellite">Satellite</SelectItem>
                  <SelectItem value="dark">Dark reference</SelectItem>
                  <SelectItem value="street">OpenStreetMap</SelectItem>
                </SelectContent>
              </Select>
            </label>
            <label className="switch-row"><span><Mountain /> Terrain<small>{hasTerrainToken ? "Cesium World Terrain" : "Add VITE_CESIUM_ION_TOKEN"}</small></span><Switch checked={terrainEnabled} disabled={!hasTerrainToken} onCheckedChange={setTerrainEnabled} /></label>
            <label className="switch-row"><span>{animationEnabled ? <Play /> : <Pause />} Layer animation<small>Target-local research graphics</small></span><Switch checked={animationEnabled} onCheckedChange={setAnimationEnabled} /></label>
            <label className="range-field"><span>Research layer opacity <b>{Math.round(layerOpacity * 100)}%</b></span><Slider value={[layerOpacity]} min={0.2} max={1} step={0.05} onValueChange={([value]) => setLayerOpacity(value)} /></label>
          </PopoverContent>
        </Popover>
      </div>

      <nav className="mission-dock" aria-label="Research missions">
        {MISSIONS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={item.id === missionId ? "active" : ""}
            style={{ "--mission-accent": item.accent } as React.CSSProperties}
            onClick={() => chooseMission(item.id)}
            title={item.name}
          >
            <span>{item.code}</span><strong>{item.shortName}</strong>
          </button>
        ))}
      </nav>

      <div className="mission-summary">
        <span style={{ background: mission.accent }} />
        <div><small>{mission.code} · {mission.timeWindow}</small><strong>{mission.question}</strong></div>
        <Button onClick={() => setSetupOpen(true)}>
          {analysisMode === "guided" ? "Start Guided Analysis" : "Open Research Console"}
        </Button>
      </div>

      <div className="globe-status"><i className={globeReady ? "ready" : ""} /> {globeReady ? "3D Earth ready" : "Loading globe"}</div>

      <Sheet open={setupOpen} onOpenChange={setSetupOpen}>
        <SheetContent side="left" className="research-sheet setup-sheet">
          <SheetHeader>
            <span className="sheet-kicker" style={{ color: mission.accent }}>{mission.code} · ANALYSIS SETUP</span>
            <SheetTitle>{mission.name}</SheetTitle>
            <SheetDescription>{mission.question}</SheetDescription>
          </SheetHeader>
          <div className="sheet-scroll">
            <section className="form-section">
              <div className="section-heading">
                <span>0</span>
                <div><strong>Interface mode</strong><small>Choose workflow depth</small></div>
              </div>
              <div className="field-pair">
                <Button
                  variant={interfaceMode === "guided" ? "default" : "outline"}
                  onClick={() => { setInterfaceMode("guided"); setAnalysisMode("guided"); }}
                >
                  Guided
                </Button>
                <Button
                  variant={interfaceMode === "research" ? "default" : "outline"}
                  onClick={() => { setInterfaceMode("research"); setAnalysisMode("research"); }}
                >
                  Research
                </Button>
              </div>
            </section>

            {researchMode && (
              <section className="form-section">
                <div className="section-heading">
                  <span>R</span>
                  <div><strong>Research context</strong><small>Additional scientific metadata</small></div>
                </div>
                <label className="text-field">
                  <span>Research objective</span>
                  <input
                    value={researchObjective}
                    onChange={(event) => setResearchObjective(event.target.value)}
                    placeholder="Example: Assess climate risk for rice production in Sylhet"
                  />
                </label>
                <label className="text-field">
                  <span>Crop or agricultural system</span>
                  <input
                    value={cropSystem}
                    onChange={(event) => setCropSystem(event.target.value)}
                    placeholder="Rice, tea, maize, livestock..."
                  />
                </label>
              </section>
            )}

            <div className="quiet-note">
              <strong>{analysisMode === "guided" ? "Guided analysis workflow" : "Research analysis workflow"}</strong>
              <p>
                {analysisMode === "guided"
                  ? "Select a mission and location. AgriScope automatically prepares the required Earth observation analysis."
                  : "Configure scientific parameters manually for reproducible research analysis."}
              </p>
            </div>

            <section className="form-section">
              <div className="section-heading"><span>1</span><div><strong>Research target</strong><small>Search above or click the globe</small></div></div>
              <label className="text-field"><span>Target name</span><input value={placeName} onChange={(event) => setPlaceName(event.target.value)} /></label>
              <div className="field-pair">
                <label className="text-field"><span>Latitude</span><input type="number" value={latitude} min={-90} max={90} step={0.000001} onChange={(event) => setLatitude(Number(event.target.value))} /></label>
                <label className="text-field"><span>Longitude</span><input type="number" value={longitude} min={-180} max={180} step={0.000001} onChange={(event) => setLongitude(Number(event.target.value))} /></label>
              </div>
              <label className="text-field"><span>Analysis area <em>hectares</em></span><input type="number" value={areaHectares} min={0.1} max={10_000_000} step={1} onChange={(event) => setAreaHectares(Number(event.target.value))} /></label>
            </section>

            {analysisMode === "research" && (
              <section className="form-section">
                <div className="section-heading">
                  <span>Research</span>
                  <div>
                    <strong>Research context</strong>
                    <small>Additional scientific metadata</small>
                  </div>
                </div>

                <label className="text-field">
                  <span>Research objective</span>
                  <textarea
                    value={researchObjective}
                    onChange={(event) => setResearchObjective(event.target.value)}
                    placeholder="Example: Assess climate risk for rice production in Sylhet"
                  />
                </label>

                <label className="text-field">
                  <span>Crop or agricultural system</span>
                  <input
                    value={cropSystem}
                    onChange={(event) => setCropSystem(event.target.value)}
                    placeholder="Rice, tea, maize, livestock..."
                  />
                </label>
              </section>
            )}

            <section className="form-section">
              <div className="section-heading"><span>2</span><div><strong>Mission inputs</strong><small>Every value is recorded in the result</small></div></div>
              <div className="parameter-list">
                {mission.fields.map((field) => (
                  <ParameterControl key={field.key} field={field} value={currentParameters[field.key]} onChange={(value) => updateParameter(field.key, value)} />
                ))}
              </div>
            </section>

            <details className="method-preview">
              <summary><Database /> Evidence & method preview</summary>
              <p>{mission.description}</p>
              <dl><div><dt>Primary evidence</dt><dd>{mission.evidence}</dd></div><div><dt>Time window</dt><dd>{mission.timeWindow}</dd></div></dl>
              <code>{METHODS[missionId].equation}</code>
            </details>
            {runError && <div className="error-banner">{runError}</div>}
          </div>
          <div className="sheet-runbar">
            <span>{apiConnected ? "Authoritative Python engine" : "Live browser engine available"}</span>
            <div className="field-pair">
              <Button
                variant="outline"
                onClick={() => {
                  setLatitude(23.685);
                  setLongitude(90.3563);
                  setAreaHectares(mission.defaultArea);
                  setPlaceName("Bangladesh worked example");
                }}
              >
                ▶ RUN WORKED EXAMPLE
              </Button>
              <Button size="lg" onClick={analyze} disabled={running}>{running ? "Retrieving Earth data…" : "Run analysis"}</Button>
            </div>
          </div>
        </SheetContent>
      </Sheet>

      <Sheet open={resultsOpen} onOpenChange={setResultsOpen}>
        <SheetContent side="right" className="research-sheet results-sheet">
          <SheetHeader>
            <span className="sheet-kicker">ANALYSIS RECEIPT</span>
            <SheetTitle>{result?.title ?? "No analysis yet"}</SheetTitle>
            <SheetDescription>{result ? `${result.analysis_id.slice(0, 8).toUpperCase()} · ${new Date(result.generated_at).toLocaleString()}` : "Configure and run a mission first."}</SheetDescription>
          </SheetHeader>
          {!result ? (
            <div className="empty-result"><BarChart3 /><strong>No result yet</strong><p>Choose a mission, set a worldwide target and run the analysis.</p><Button onClick={() => { setResultsOpen(false); setSetupOpen(true); }}>Open setup</Button></div>
          ) : (
            <Tabs defaultValue="overview" className="result-tabs">
              <TabsList variant="line" className="result-tab-list">
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="evidence">Evidence</TabsTrigger>
                <TabsTrigger value="method">Method</TabsTrigger>
                <TabsTrigger value="export">Export</TabsTrigger>
                <TabsTrigger value="history">History</TabsTrigger>
              </TabsList>
              <div className="sheet-scroll result-scroll">
                {stale && <div className="stale-banner"><strong>Inputs changed</strong><span>This receipt belongs to the previous target or parameters. Run again before using it.</span></div>}
                {runWarning && <div className="warning-banner"><strong>Execution note</strong><span>{runWarning}</span></div>}
                <TabsContent value="overview">
                  <div className="score-block">
                    <div className={`score-orb ${result.risk_level}`} style={{ "--score": result.score } as React.CSSProperties}><strong>{result.score.toFixed(1)}</strong><span>/ 100</span></div>
                    <div><small>SCREENING PRIORITY</small><h3>{result.risk_level.toUpperCase()}</h3><p>Not a probability, diagnosis or measured loss.</p></div>
                  </div>
                  <div className="confidence-row"><span>Evidence completeness <b>{Math.round(result.confidence * 100)}%</b></span><Progress value={result.confidence * 100} /></div>
                  <div className="status-list">{result.data_status.map((status) => <span key={status}>{status}</span>)}</div>
                  <p className="result-summary">{result.summary}</p>
                  <div className="metric-grid">{result.metrics.map((metric) => <article key={metric.key}><small>{metric.label}</small><strong>{metric.value ?? "—"} <em>{metric.unit}</em></strong><p>{metric.interpretation}</p></article>)}</div>
                </TabsContent>
                <TabsContent value="evidence">
                  <h3 className="content-title">Source receipt</h3>
                  <div className="source-list">{result.sources.length ? result.sources.map((source, index) => <article key={`${source.name}-${index}`}><header><strong>{source.name}</strong><span>{source.status}</span></header><p>{source.role}</p>{source.identifier && <code>{source.identifier}</code>}{source.acquisition_datetime && <small>Acquired {source.acquisition_datetime}</small>}{source.note && <small>{source.note}</small>}{source.url && <a href={source.url} target="_blank" rel="noreferrer">Open source documentation</a>}</article>) : <p>No external source was recorded for this input-only calculation.</p>}</div>
                  <h3 className="content-title">Research-use boundaries</h3>
                  <ul className="caveat-list">{result.caveats.map((caveat) => <li key={caveat}>{caveat}</li>)}</ul>
                </TabsContent>
                <TabsContent value="method">
                  <div className="method-card"><small>{result.methodology_version}</small><code>{METHODS[result.mission].equation}</code><ol>{METHODS[result.mission].steps.map((step) => <li key={step}>{step}</li>)}</ol></div>
                  <div className="method-card"><small>REPRODUCIBILITY</small><p>The complete request, coordinates, area, time, statuses, metrics, sources, caveats and method version are preserved in JSON and Markdown exports. GeoJSON preserves the target geometry.</p></div>
                </TabsContent>
                <TabsContent value="export">
                  <h3 className="content-title">Download research package</h3>
                  <p className="export-intro">Use JSON for reproducibility, CSV for analysis, GeoJSON for GIS, and Markdown for a readable methods receipt.</p>
                  <div className="export-grid">
                    <ExportButton icon={<FileJson />} label="JSON receipt" format="json" result={result} />
                    <ExportButton icon={<Table2 />} label="CSV metrics" format="csv" result={result} />
                    <ExportButton icon={<Globe2 />} label="GeoJSON target" format="geojson" result={result} />
                    <ExportButton icon={<FileText />} label="Markdown report" format="markdown" result={result} />
                  </div>
                  <div className="receipt-meta"><span>Execution</span><strong>{runMode === "python-api" ? "Python FastAPI" : "Browser live preview"}</strong><span>Method</span><strong>{result.methodology_version}</strong><span>Coordinate</span><strong>{result.coordinates.latitude.toFixed(5)}, {result.coordinates.longitude.toFixed(5)}</strong></div>
                </TabsContent>
                <TabsContent value="history">
                  <h3 className="content-title">This-session history</h3>
                  <div className="history-list">{history.map((item) => <button key={item.analysis_id} onClick={() => { setResult(item); setLastRunSignature(""); }}><span style={{ background: MISSION_BY_ID[item.mission].accent }} /><div><strong>{MISSION_BY_ID[item.mission].shortName}</strong><small>{item.coordinates.latitude.toFixed(3)}, {item.coordinates.longitude.toFixed(3)} · {new Date(item.generated_at).toLocaleTimeString()}</small></div><b>{item.score.toFixed(1)}</b></button>)}</div>
                </TabsContent>
              </div>
            </Tabs>
          )}
        </SheetContent>
      </Sheet>
    </main>
  );
}

function ParameterControl({ field, value, onChange }: { field: ParameterField; value: string | number | boolean; onChange: (value: string | number | boolean) => void }) {
  if (field.type === "switch") {
    return <label className="switch-row parameter-control"><span><strong>{field.label}</strong><small>{field.help}</small></span><Switch checked={Boolean(value)} onCheckedChange={onChange} /></label>;
  }
  if (field.type === "select") {
    return <label className="select-field parameter-control"><span><strong>{field.label}</strong><small>{field.help}</small></span><Select value={String(value)} onValueChange={onChange}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{field.options?.map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}</SelectContent></Select></label>;
  }
  if (field.type === "range") {
    const numeric = Number(value);
    return <label className="range-field parameter-control"><span><strong>{field.label}</strong><b>{numeric.toFixed(field.step && field.step < 1 ? 2 : 0)}{field.unit ? ` ${field.unit}` : ""}</b></span><Slider value={[numeric]} min={field.min} max={field.max} step={field.step} onValueChange={([next]) => onChange(next)} /><small>{field.help}</small></label>;
  }
  return <label className="text-field parameter-control"><span>{field.label}<em>{field.unit}</em></span><input type="number" value={Number(value)} min={field.min} max={field.max} step={field.step} onChange={(event) => onChange(Number(event.target.value))} /><small>{field.help}</small></label>;
}

function ExportButton({ icon, label, format, result }: { icon: React.ReactNode; label: string; format: ExportFormat; result: AnalysisResponse }) {
  return <button type="button" onClick={() => downloadResult(result, format)}>{icon}<span><strong>{label}</strong><small>Download .{format === "markdown" ? "md" : format}</small></span><Download /></button>;
}
