import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const missions = await readFile(new URL("../lib/agriscope/missions.ts", import.meta.url), "utf8");
const globe = await readFile(new URL("../components/agriscope/earth-globe.tsx", import.meta.url), "utf8");
const dashboard = await readFile(new URL("../components/agriscope/dashboard.tsx", import.meta.url), "utf8");
const packageJson = JSON.parse(await readFile(new URL("../package.json", import.meta.url), "utf8"));
const deploymentGuide = await readFile(new URL("../docs/DEPLOYMENT.md", import.meta.url), "utf8");

test("publishes exactly the six research missions", () => {
  for (const mission of ["flood-watch", "crop-stress", "land-change", "irrigation", "carbon", "fire-heat"]) {
    assert.match(missions, new RegExp(`id: \\"${mission}\\"`));
  }
  assert.equal((missions.match(/\bid:\s*"/g) ?? []).length, 6);
});

test("uses Cesium 3D with target-local graphics", () => {
  assert.match(globe, /new C\.Viewer/);
  assert.match(globe, /Terrain\.fromWorldTerrain/);
  assert.match(globe, /viewer = createViewer\(false\)/);
  assert.match(globe, /viewer = createViewer\(true\)/);
  assert.match(globe, /powerPreference: "default"/);
  assert.match(globe, /Retry 3D Earth/);
  assert.match(globe, /Click Earth to move the research target/);
  assert.doesNotMatch(globe, /intercontinental|global arc|connection line/i);
});

test("keeps every animated Cesium ellipse geometrically valid", () => {
  assert.match(globe, /const majorAxis = new C\.CallbackProperty/);
  assert.match(globe, /const minorAxis = new C\.CallbackProperty/);
  assert.match(globe, /pulseRadiusAt\(time\) \* 0\.995/);
  assert.match(globe, /semiMajorAxis: majorAxis/);
  assert.match(globe, /semiMinorAxis: minorAxis/);
  assert.doesNotMatch(globe, /semiMajorAxis: axis[\s\S]{0,100}semiMinorAxis: axis/);
});

test("protects stale receipts and offers all four exports", () => {
  assert.match(dashboard, /Inputs changed/);
  for (const format of ["json", "csv", "geojson", "markdown"]) {
    assert.match(dashboard, new RegExp(`format=\\"${format}\\"`));
  }
});

test("ships a GitHub-to-public Cloudflare and Render deployment path", () => {
  assert.equal(
    packageJson.scripts["deploy:cloudflare"],
    "node scripts/validate-cloudflare-build.mjs && wrangler deploy --config dist/server/wrangler.json",
  );
  assert.match(deploymentGuide, /https:\/\/agriscope-earth-v3\.site/);
  assert.match(deploymentGuide, /CORS_ORIGINS/);
  assert.match(deploymentGuide, /npm run deploy:cloudflare/);
  assert.match(deploymentGuide, /GitHub.*Cloudflare.*Render/is);
});
