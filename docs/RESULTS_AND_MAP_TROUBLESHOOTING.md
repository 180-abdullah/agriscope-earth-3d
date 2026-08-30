# Results and 3D globe troubleshooting

## A result does not change after moving the target

Check the receipt banner first. Moving the target marks the previous result **stale**; the new coordinate is not analysed until **Run analysis** is selected again.

For M03 and M05, identical output can be scientifically correct:

- M03 is driven by supplied baseline/current class summaries.
- M05 is driven by farm activity data and emission factors.

For M01, M02, M04 and M06, rerunning at a different coordinate should refresh location-dependent data. The source receipt shows whether live forecast/observation data or a fallback was used.

## The globe is round but terrain looks smooth

CesiumJS always renders the WGS84 globe. Elevation relief additionally requires a Cesium ion token:

```env
VITE_CESIUM_ION_TOKEN=your_public_cesium_ion_token
```

Restart or rebuild after setting the variable, then enable Terrain in Earth layers. A browser-exposed Cesium token must be scoped and domain-restricted in the ion dashboard. Never commit private service credentials.

## Satellite tiles do not load

1. Check the browser network tab for blocked `server.arcgisonline.com` requests.
2. Confirm corporate/firewall policy permits the imagery host.
3. Switch temporarily to OpenStreetMap to confirm Cesium itself is working.
4. Review provider terms and availability; tile services can change independently of AgriScope.

Attribution is required and intentionally cannot be hidden.

## The globe is blank

For local development, run the asset preparation through the normal command:

```bash
npm run dev
```

The command copies Cesium `Workers`, `Assets`, `ThirdParty` and `Widgets` to `public/cesium`. If using a custom build process, run `npm run prepare:cesium` first and ensure `/cesium/Workers` is publicly served.

## The public site says Live preview

The frontend cannot reach the Python service. Verify:

1. the FastAPI health URL returns JSON at `/api/v1/health`;
2. the frontend build variable `VITE_API_BASE_URL` contains the backend origin without a trailing slash;
3. backend `CORS_ORIGINS` contains the exact public frontend origin;
4. the backend host is awake and HTTPS is valid.

If the API fails during a run, the interface uses its labelled live browser calculation when possible. It never silently calls that result Python output.

## Sentinel-2 does not complete

Sentinel processing can fail because no scene met the date/cloud filters, the target has too few clear pixels, a STAC asset changed, or the cloud host cannot read public COG ranges. The receipt should report `unavailable` and must not present a demonstration index as observed.

Try a longer lookback, higher scene-cloud ceiling, smaller area or a researcher-prepared NDVI/NDMI pair with its processing documentation.

## NASA FIRMS is unavailable

Set `FIRMS_MAP_KEY` only in the backend environment. Without it, M06 still evaluates weather but labels FIRMS unavailable. Do not place the FIRMS key in `VITE_*` variables or browser code.

## Why the research graphics are not literal maps

Animated circles, dots, spokes and columns communicate the selected mission and score around the target. They are not measurements of the exact spatial pattern. Only a returned, cited geometry should be interpreted as a mapped observation. This boundary prevents visually persuasive but scientifically unsupported claims.
