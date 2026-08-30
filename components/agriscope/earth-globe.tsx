"use client";

import { useEffect, useRef, useState } from "react";

import type { AnalysisResponse, BasemapId, MissionDefinition } from "@/lib/agriscope/types";

interface EarthGlobeProps {
  latitude: number;
  longitude: number;
  areaHectares: number;
  mission: MissionDefinition;
  result: AnalysisResponse | null;
  basemap: BasemapId;
  terrainEnabled: boolean;
  animationEnabled: boolean;
  opacity: number;
  onPick: (latitude: number, longitude: number) => void;
  onReady: (ready: boolean) => void;
}

function areaRadius(areaHectares: number) {
  return Math.sqrt(Math.max(areaHectares, 0.1) * 10_000 / Math.PI);
}

function offsetPoint(latitude: number, longitude: number, distance: number, angle: number) {
  const earthRadius = 6_378_137;
  const lat = (latitude * Math.PI) / 180;
  const dLat = (distance * Math.cos(angle)) / earthRadius;
  const dLon = (distance * Math.sin(angle)) / (earthRadius * Math.max(0.08, Math.cos(lat)));
  return {
    latitude: latitude + (dLat * 180) / Math.PI,
    longitude: longitude + (dLon * 180) / Math.PI,
  };
}

export function EarthGlobe({
  latitude,
  longitude,
  areaHectares,
  mission,
  result,
  basemap,
  terrainEnabled,
  animationEnabled,
  opacity,
  onPick,
  onReady,
}: EarthGlobeProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const viewerRef = useRef<import("cesium").Viewer | null>(null);
  const cesiumRef = useRef<typeof import("cesium") | null>(null);
  const handlerRef = useRef<import("cesium").ScreenSpaceEventHandler | null>(null);
  const lastTargetRef = useRef("");
  const [ready, setReady] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function initialize() {
      if (!containerRef.current) return;
      try {
        const cesiumBaseUrl = "/cesium/";
        window.CESIUM_BASE_URL = cesiumBaseUrl;
        const C = await import("cesium");
        if (cancelled || !containerRef.current) return;
        C.buildModuleUrl.setBaseUrl(cesiumBaseUrl);

        // Cesium defaults to a high-performance WebGL 2 context. That can fail
        // on otherwise capable laptops, remote desktops and power-saving GPUs.
        // Start with neutral WebGL 2 settings and retry the real viewer with
        // WebGL 1 after a failed construction. This avoids a separate probe
        // canvas consuming one of the browser's limited graphics contexts.
        const webglOptions: WebGLContextAttributes = {
          alpha: false,
          antialias: false,
          depth: true,
          failIfMajorPerformanceCaveat: false,
          powerPreference: "default",
          premultipliedAlpha: true,
          preserveDrawingBuffer: false,
          stencil: true,
        };
        const token = (import.meta.env.VITE_CESIUM_ION_TOKEN ?? "").trim();
        if (token) C.Ion.defaultAccessToken = token;
        const createViewer = (requestWebgl1: boolean) => new C.Viewer(containerRef.current as HTMLDivElement, {
          animation: false,
          baseLayer: false,
          baseLayerPicker: false,
          fullscreenButton: false,
          geocoder: false,
          homeButton: false,
          infoBox: false,
          navigationHelpButton: false,
          scene3DOnly: true,
          sceneModePicker: false,
          selectionIndicator: false,
          timeline: false,
          shouldAnimate: true,
          requestRenderMode: false,
          terrainProvider: new C.EllipsoidTerrainProvider(),
          contextOptions: {
            requestWebgl1,
            allowTextureFilterAnisotropic: false,
            webgl: webglOptions,
          },
        });

        let viewer: import("cesium").Viewer;
        try {
          viewer = createViewer(false);
        } catch (webgl2Error) {
          console.warn("WebGL 2 globe startup failed; retrying with WebGL 1.", webgl2Error);
          containerRef.current.replaceChildren();
          viewer = createViewer(true);
        }
        viewer.scene.globe.enableLighting = true;
        viewer.scene.globe.showGroundAtmosphere = true;
        viewer.scene.globe.depthTestAgainstTerrain = true;
        viewer.scene.fog.enabled = true;
        viewer.scene.screenSpaceCameraController.minimumZoomDistance = 180;
        viewer.clock.shouldAnimate = true;
        viewer.camera.setView({ destination: C.Cartesian3.fromDegrees(16, 18, 18_500_000) });

        const handler = new C.ScreenSpaceEventHandler(viewer.scene.canvas);
        handler.setInputAction((movement: { position: import("cesium").Cartesian2 }) => {
          const ray = viewer.camera.getPickRay(movement.position);
          if (!ray) return;
          const point = viewer.scene.globe.pick(ray, viewer.scene);
          if (!point) return;
          const cartographic = C.Cartographic.fromCartesian(point);
          onPick(C.Math.toDegrees(cartographic.latitude), C.Math.toDegrees(cartographic.longitude));
        }, C.ScreenSpaceEventType.LEFT_CLICK);

        cesiumRef.current = C;
        viewerRef.current = viewer;
        handlerRef.current = handler;
        setReady(true);
        onReady(true);
      } catch (error) {
        console.error("AgriScope 3D globe failed to initialize", error);
        containerRef.current?.replaceChildren();
        const detail = error instanceof Error ? error.message : "The 3D globe could not start.";
        setLoadError(
          detail.toLowerCase().includes("webgl")
            ? "Your browser could not start 3D graphics. Turn on hardware acceleration in Chrome or Edge, restart the browser, then retry."
            : detail,
        );
        onReady(false);
      }
    }
    void initialize();
    return () => {
      cancelled = true;
      handlerRef.current?.destroy();
      handlerRef.current = null;
      if (viewerRef.current && !viewerRef.current.isDestroyed()) viewerRef.current.destroy();
      viewerRef.current = null;
      cesiumRef.current = null;
    };
  }, [onPick, onReady, retryKey]);

  useEffect(() => {
    const viewer = viewerRef.current;
    const C = cesiumRef.current;
    if (!ready || !viewer || !C) return;
    viewer.imageryLayers.removeAll(true);
    const providers: Record<BasemapId, import("cesium").ImageryProvider> = {
      satellite: new C.UrlTemplateImageryProvider({
        url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        credit: "Esri, Maxar, Earthstar Geographics and contributors",
        maximumLevel: 19,
      }),
      dark: new C.UrlTemplateImageryProvider({
        url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        subdomains: ["a", "b", "c", "d"],
        credit: "CARTO © OpenStreetMap contributors",
        maximumLevel: 20,
      }),
      street: new C.OpenStreetMapImageryProvider({
        url: "https://tile.openstreetmap.org/",
        credit: "© OpenStreetMap contributors",
        maximumLevel: 19,
      }),
    };
    const layer = viewer.imageryLayers.addImageryProvider(providers[basemap]);
    layer.brightness = basemap === "dark" ? 0.82 : 0.92;
    layer.contrast = basemap === "satellite" ? 1.1 : 1.02;
    layer.saturation = basemap === "satellite" ? 0.82 : 0.74;
  }, [basemap, ready]);

  useEffect(() => {
    const viewer = viewerRef.current;
    const C = cesiumRef.current;
    if (!ready || !viewer || !C) return;
    const token = (import.meta.env.VITE_CESIUM_ION_TOKEN ?? "").trim();
    if (terrainEnabled && token) {
      viewer.scene.setTerrain(C.Terrain.fromWorldTerrain({ requestVertexNormals: true, requestWaterMask: true }));
    } else {
      viewer.terrainProvider = new C.EllipsoidTerrainProvider();
    }
  }, [terrainEnabled, ready]);

  useEffect(() => {
    const viewer = viewerRef.current;
    const C = cesiumRef.current;
    if (!ready || !viewer || !C) return;
    viewer.entities.removeAll();
    const radius = areaRadius(areaHectares);
    const color = C.Color.fromCssColorString(mission.accent);
    const alpha = clampOpacity(opacity);
    const position = C.Cartesian3.fromDegrees(longitude, latitude);
    const score = result?.score ?? 35;

    viewer.entities.add({
      name: "Selected research boundary",
      position,
      ellipse: {
        semiMajorAxis: radius,
        semiMinorAxis: radius,
        material: color.withAlpha(0.08 * alpha),
        outline: true,
        outlineColor: color.withAlpha(0.92),
        heightReference: C.HeightReference.CLAMP_TO_GROUND,
      },
    });

    viewer.entities.add({
      position,
      point: {
        pixelSize: 10,
        color,
        outlineColor: C.Color.WHITE.withAlpha(0.9),
        outlineWidth: 2,
        heightReference: C.HeightReference.CLAMP_TO_GROUND,
      },
      label: {
        text: result ? `${mission.code} · ${result.score.toFixed(1)}` : `${mission.code} · TARGET`,
        font: "600 13px Inter, sans-serif",
        fillColor: C.Color.WHITE,
        showBackground: true,
        backgroundColor: C.Color.fromCssColorString("#10211f").withAlpha(0.82),
        pixelOffset: new C.Cartesian2(0, -28),
        verticalOrigin: C.VerticalOrigin.BOTTOM,
        heightReference: C.HeightReference.CLAMP_TO_GROUND,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    });

    const pulseCount = mission.id === "flood-watch" ? 3 : mission.id === "fire-heat" ? 2 : 1;
    for (let index = 0; index < pulseCount; index += 1) {
      const phaseOffset = index / pulseCount;
      const pulsePhaseAt = (time: import("cesium").JulianDate) => {
        if (!animationEnabled) return 0.55;
        const milliseconds = C.JulianDate.toDate(time).getTime();
        return (milliseconds / 2400 + phaseOffset) % 1;
      };
      const pulseRadiusAt = (time: import("cesium").JulianDate) => {
        if (!animationEnabled) return radius * (0.45 + phaseOffset * 0.22);
        return radius * (0.22 + 0.83 * pulsePhaseAt(time));
      };
      const majorAxis = new C.CallbackProperty((time: import("cesium").JulianDate) => {
        return pulseRadiusAt(time);
      }, false);
      const minorAxis = new C.CallbackProperty((time: import("cesium").JulianDate) => {
        return pulseRadiusAt(time) * 0.995;
      }, false);
      const pulseColor = new C.CallbackProperty((time: import("cesium").JulianDate) => {
        const phase = pulsePhaseAt(time);
        return color.withAlpha((0.36 * (1 - phase) + 0.05) * alpha);
      }, false);
      viewer.entities.add({
        position,
        ellipse: {
          semiMajorAxis: majorAxis,
          semiMinorAxis: minorAxis,
          material: new C.ColorMaterialProperty(pulseColor),
          heightReference: C.HeightReference.CLAMP_TO_GROUND,
        },
      });
    }

    addMissionLayer(C, viewer, mission.id, latitude, longitude, radius, score, color, alpha, animationEnabled);

    const targetKey = `${latitude.toFixed(5)}:${longitude.toFixed(5)}:${areaHectares}:${mission.id}`;
    if (lastTargetRef.current !== targetKey) {
      lastTargetRef.current = targetKey;
      const height = Math.max(4_000, Math.min(1_800_000, radius * 6.5));
      viewer.camera.flyTo({
        destination: C.Cartesian3.fromDegrees(longitude, latitude, height),
        orientation: { heading: C.Math.toRadians(8), pitch: C.Math.toRadians(-57), roll: 0 },
        duration: 1.7,
      });
    }
  }, [latitude, longitude, areaHectares, mission, result, opacity, animationEnabled, ready]);

  return (
    <div className="earth-stage" aria-label="Interactive 3D Earth research map">
      <div ref={containerRef} className="earth-canvas" />
      {!ready && !loadError && <div className="earth-loading"><span />Preparing the 3D Earth…</div>}
      {loadError && (
        <div className="earth-error">
          <strong>3D Earth unavailable</strong>
          <span>{loadError}</span>
          <button
            type="button"
            onClick={() => {
              setLoadError("");
              setReady(false);
              setRetryKey((value) => value + 1);
            }}
          >
            Retry 3D Earth
          </button>
        </div>
      )}
      <div className="earth-hint">Click Earth to move the research target</div>
    </div>
  );
}

function clampOpacity(value: number) {
  return Math.max(0.1, Math.min(1, value));
}

function addMissionLayer(
  C: typeof import("cesium"),
  viewer: import("cesium").Viewer,
  mission: MissionDefinition["id"],
  latitude: number,
  longitude: number,
  radius: number,
  score: number,
  color: import("cesium").Color,
  alpha: number,
  animated: boolean,
) {
  const count = mission === "crop-stress" || mission === "land-change" ? 16 : 10;
  for (let index = 0; index < count; index += 1) {
    const angle = (Math.PI * 2 * index) / count + (index % 3) * 0.13;
    const distance = radius * (0.28 + 0.58 * ((index * 37) % 100) / 100);
    const point = offsetPoint(latitude, longitude, distance, angle);
    const local = (score + index * 11) % 100;
    const localColor = mission === "land-change"
      ? (index % 3 === 0 ? C.Color.fromCssColorString("#6daedb") : index % 3 === 1 ? C.Color.fromCssColorString("#86ba7a") : C.Color.fromCssColorString("#d6b36a"))
      : mission === "crop-stress"
        ? (local > 68 ? C.Color.fromCssColorString("#e68164") : local > 38 ? C.Color.fromCssColorString("#d8c36a") : C.Color.fromCssColorString("#88c77a"))
        : color;

    if (mission === "irrigation") {
      viewer.entities.add({
        polyline: {
          positions: [C.Cartesian3.fromDegrees(longitude, latitude), C.Cartesian3.fromDegrees(point.longitude, point.latitude)],
          width: 1.5,
          material: new C.PolylineGlowMaterialProperty({ color: localColor.withAlpha(0.55 * alpha), glowPower: 0.15 }),
          clampToGround: true,
        },
      });
      continue;
    }

    if (mission === "carbon") {
      const height = 150 + (score + index * 7) * 9;
      viewer.entities.add({
        polyline: {
          positions: C.Cartesian3.fromDegreesArrayHeights([point.longitude, point.latitude, 0, point.longitude, point.latitude, height]),
          width: 3,
          material: new C.PolylineGlowMaterialProperty({ color: localColor.withAlpha(0.72 * alpha), glowPower: 0.22 }),
        },
      });
      continue;
    }

    const size = new C.CallbackProperty(() => {
      const pulse = animated ? (Math.sin(performance.now() / 430 + index) + 1) / 2 : 0.5;
      return mission === "fire-heat" ? 7 + pulse * 9 : 5 + (local / 100) * 6;
    }, false);
    viewer.entities.add({
      position: C.Cartesian3.fromDegrees(point.longitude, point.latitude),
      point: {
        pixelSize: size,
        color: localColor.withAlpha((mission === "fire-heat" ? 0.78 : 0.64) * alpha),
        outlineColor: C.Color.WHITE.withAlpha(0.45),
        outlineWidth: 1,
        heightReference: C.HeightReference.CLAMP_TO_GROUND,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    });
  }
}
