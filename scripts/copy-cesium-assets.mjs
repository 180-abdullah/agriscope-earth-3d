import { cp, mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const cesiumRoot = path.join(root, "node_modules", "cesium", "Build", "Cesium");
const publicRoot = path.join(root, "public", "cesium");

await mkdir(publicRoot, { recursive: true });
for (const name of ["Assets", "ThirdParty", "Widgets", "Workers"]) {
  await cp(path.join(cesiumRoot, name), path.join(publicRoot, name), {
    recursive: true,
    force: true,
  });
}

console.log("Cesium runtime assets copied to public/cesium.");
