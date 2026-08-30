import { access, readFile } from "node:fs/promises";

const requiredFiles = [
  "dist/server/index.js",
  "dist/server/wrangler.json",
  "dist/client/.vite/manifest.json",
  "dist/client/cesium/Assets",
  "dist/client/cesium/Workers",
  "dist/client/cesium/Widgets/widgets.css",
];

for (const path of requiredFiles) {
  try {
    await access(path);
  } catch {
    throw new Error(`Cloudflare deployment file is missing: ${path}. Run npm run build first.`);
  }
}

const config = JSON.parse(await readFile("dist/server/wrangler.json", "utf8"));
if (config.main !== "index.js") {
  throw new Error("The generated Cloudflare Worker entry point is invalid.");
}
if (config.assets?.directory !== "../client") {
  throw new Error("The generated Cloudflare static-asset directory is invalid.");
}
if (!Array.isArray(config.compatibility_flags) || !config.compatibility_flags.includes("nodejs_compat")) {
  throw new Error("The generated Cloudflare Worker is missing the nodejs_compat flag.");
}

console.log("Cloudflare deployment output is complete.");
