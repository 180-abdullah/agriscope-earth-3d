# GitHub to public launch — complete beginner guide

This guide publishes the complete AgriScope Earth system from one GitHub
repository:

- **Cloudflare Worker:** the Cesium 3D website;
- **Render web service:** the Python FastAPI research engine;
- **Custom domain:** `https://agriscope-earth-v3.site`.

The requested spelling `agriscope-earth_v3.site` cannot be used as a website
address because `_` is not valid in a web hostname. The equivalent valid name
uses a hyphen: `agriscope-earth-v3.site`.

GitHub stores and updates the source. It does not by itself run this full-stack
application. Cloudflare and Render deploy the two runnable services whenever
you push an update to GitHub.

## 0. What you need

Create these accounts before starting:

1. [GitHub](https://github.com/) — source repository.
2. [Render](https://render.com/) — Python API.
3. [Cloudflare](https://dash.cloudflare.com/) — 3D frontend and DNS.
4. A domain registrar — buy `agriscope-earth-v3.site` if it is available.

The domain has an annual registration cost. Hosting plans can have usage limits
or sleep behaviour, so read the current provider terms before selecting a plan.

Optional accounts:

- [Cesium ion](https://ion.cesium.com/) for elevation terrain;
- [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/api/) for live M06 fire detections.

The satellite, dark and street maps work without either optional token.

## 1. Extract and check the repository

1. Download the AgriScope repository ZIP.
2. Right-click the ZIP and select **Extract all**.
3. Open the extracted `agriscope-earth-3d` folder.
4. Confirm that it contains `README.md`, `package.json`, `render.yaml`,
   `backend`, `app`, `components`, `docs` and `.github`.
5. Do not upload the ZIP as a single file. GitHub must contain the extracted
   files and folders.

Never put passwords or keys in `.env.local`, `backend/.env` or any file that
will be committed. Production variables are entered in provider dashboards.

## 2. Upload the extracted project to GitHub

### Easiest method: GitHub Desktop

1. Install [GitHub Desktop](https://desktop.github.com/) and sign in.
2. Select **File → Add local repository**.
3. Choose the extracted `agriscope-earth-3d` folder.
4. If GitHub Desktop says it is not yet a repository, choose **Create a
   repository here**.
5. Use repository name `agriscope-earth-3d` and branch `main`.
6. In the commit summary enter `Initial AgriScope Earth release`.
7. Select **Commit to main**.
8. Select **Publish repository**.
9. Choose **Public** if you want anyone to inspect the scientific methods;
   otherwise leave it private and grant Render and Cloudflare access.
10. Open GitHub in your browser and confirm that `package.json`, `render.yaml`
    and the folders are visible.

### Command-line alternative

From inside the extracted folder:

```bash
git init
git add .
git commit -m "Initial AgriScope Earth release"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/agriscope-earth-3d.git
git push -u origin main
```

Replace `YOUR-USERNAME` with your GitHub username. Create the empty GitHub
repository before running the final two commands.

## 3. Deploy the Python research API on Render

Do this before the frontend because Cloudflare needs the API URL while building.

1. Sign in to [Render](https://dashboard.render.com/).
2. Select **New → Blueprint**.
3. Connect GitHub and choose `agriscope-earth-3d`.
4. Render detects the root `render.yaml` file.
5. Approve the proposed service named `agriscope-earth-api`.
6. Enter these environment variables when Render asks:

| Variable | Exact value |
|---|---|
| `CORS_ORIGINS` | `https://agriscope-earth-v3.site` |
| `SENTINEL_MAX_SAMPLE_HECTARES` | `2500` |
| `FIRMS_MAP_KEY` | Leave blank initially, or enter your private NASA FIRMS key |

Do not add a trailing slash to either CORS origin. Never put the FIRMS key in
the frontend.

7. Select **Apply** or **Deploy Blueprint**.
8. Wait until the service status is **Live**.
9. Render gives an address similar to:

   `https://agriscope-earth-api.onrender.com`

10. Copy your actual address. Do not copy `/docs` or `/api/v1/health`.
11. Open this check in a browser:

    `https://YOUR-RENDER-ADDRESS/api/v1/health`

12. Continue only when the response includes `"status":"ok"` and
    `"missions":6`.

## 4. Buy and connect the valid domain to Cloudflare

First search for `agriscope-earth-v3.site`. If another person already owns it,
choose another valid hyphenated name and replace the domain everywhere in this
guide.

### If you buy it through Cloudflare Registrar

1. In Cloudflare, open **Domain Registration → Register Domains**.
2. Search for `agriscope-earth-v3.site`.
3. Purchase it if available.
4. Cloudflare automatically manages its nameservers and DNS zone.

### If you buy it from another registrar

1. In Cloudflare, select **Add a domain**.
2. Enter `agriscope-earth-v3.site`.
3. Select a plan.
4. Cloudflare shows two authoritative nameservers.
5. Sign in to your registrar and replace its current nameservers with the two
   Cloudflare nameservers exactly.
6. Return to Cloudflare and wait until the zone status is **Active**.

Do not create a random A record. Cloudflare will attach the Worker to the domain
in a later step.

## 5. Deploy the 3D frontend from GitHub to Cloudflare

1. In Cloudflare, open **Workers & Pages**.
2. Select **Create application**.
3. Select **Import a repository**.
4. Connect GitHub and authorize access to `agriscope-earth-3d`.
5. Select that repository.
6. Use these project settings:

| Setting | Value |
|---|---|
| Worker name | `agriscope-earth-v3` |
| Production branch | `main` |
| Root directory | `/` or leave blank |
| Build command | `npm ci && npm run build` |
| Deploy command | `npm run deploy:cloudflare` |

7. Add these build environment variables:

| Variable | Value |
|---|---|
| `NODE_VERSION` | `22.13.0` |
| `VITE_API_BASE_URL` | Your Render origin, such as `https://agriscope-earth-api.onrender.com` |
| `VITE_CESIUM_ION_TOKEN` | Leave blank initially, or enter a domain-restricted Cesium ion token |

`VITE_API_BASE_URL` must not end with `/`. A Cesium token is not required for
the globe or satellite imagery; it is only needed for Cesium World Terrain.

8. Select **Save and Deploy**.
9. Wait for both the build and deploy stages to succeed.
10. Open the temporary `workers.dev` URL. The page should show the 3D interface.

Cloudflare uses the generated `dist/server/wrangler.json` file. Do not change
the deploy command to a static-site upload and do not point it only at
`dist/client`; the Vinext server and Cesium assets are both required.

## 6. Attach the custom domain

1. Open **Workers & Pages → agriscope-earth-v3**.
2. Open **Settings → Domains & Routes**.
3. Select **Add → Custom Domain**.
4. Enter `agriscope-earth-v3.site`.
5. Confirm **Add Custom Domain**.
6. Wait until the domain and TLS certificate show as active.
7. Repeat with `www.agriscope-earth-v3.site` only if you also want the `www`
   address.

If you add the `www` address, update Render's `CORS_ORIGINS` to
`https://agriscope-earth-v3.site,https://www.agriscope-earth-v3.site` and
redeploy the API.

Cloudflare creates the required DNS routing and HTTPS certificate. Your public
website is then:

`https://agriscope-earth-v3.site`

## 7. Confirm that the frontend is using Python

1. Open `https://agriscope-earth-v3.site` in a new Chrome or Edge tab.
2. Press `Ctrl + F5` once to avoid an older cached build.
3. Open **Setup** and run any mission.
4. Check the result's engine/evidence label. It should say **Python API**, not
   **Browser live preview**.

If it says **Browser live preview**:

1. Open the Cloudflare Worker.
2. Go to **Settings → Build → Variables and Secrets**.
3. Confirm that `VITE_API_BASE_URL` is the exact Render origin.
4. Open Render and confirm `CORS_ORIGINS` contains the exact custom frontend
   origin.
5. Redeploy both services after correcting a value.

## 8. Optional genuine elevation terrain

1. Create a Cesium ion token with access to World Terrain.
2. Restrict the token to these allowed origins:

   - `https://agriscope-earth-v3.site`
   - `https://www.agriscope-earth-v3.site` if used

3. Add it in Cloudflare as `VITE_CESIUM_ION_TOKEN`.
4. Trigger a new frontend deployment.
5. Open **Earth layers** and enable **Terrain**.

The token is delivered to browsers by design, so restriction and least
privilege are essential. Never use a general-purpose private account token.

## 9. Final scientific and interface verification

Complete every check before sharing the project:

- The domain opens with HTTPS and no certificate warning.
- The globe rotates, tilts and zooms.
- Satellite, dark and street basemaps load with attribution.
- Search Bangladesh, Brazil and Kenya; the target moves to each place.
- Run M04 for two distant places and confirm live weather inputs can differ.
- Change a guided parameter and rerun; the result changes when the method uses
  that parameter.
- Run all six missions.
- The engine label reads **Python API**.
- Evidence, method, caveats and source records open.
- JSON, CSV, GeoJSON and Markdown exports download.
- No Cesium ellipse error appears.
- Terrain works only after a valid token is added.
- The Render health endpoint still reports six missions.

## 10. How future updates work

After GitHub, Render and Cloudflare are connected:

1. Edit the project locally.
2. Commit the changes in GitHub Desktop.
3. Select **Push origin**.
4. GitHub Actions checks the frontend build and Python tests.
5. Render redeploys the Python service from `main`.
6. Cloudflare redeploys the frontend from `main`.
7. Recheck the health endpoint and one mission on the public domain.

Do not deploy a change if GitHub Actions is red.

## 11. Troubleshooting

### Cloudflare build fails

- Confirm the build command is `npm ci && npm run build`.
- Confirm the deploy command is `npm run deploy:cloudflare`.
- Confirm Node is `22.13.0` or newer.
- Open the first red build line; later messages are often consequences.

### Globe area is blank

- Use a current Chrome, Edge or Firefox version.
- Enable browser hardware acceleration and restart the browser.
- Update the graphics driver.
- Press `Ctrl + F5`.
- Test without privacy extensions that block map tiles.
- A Cesium token is not required for the basic globe.

### Python API is unavailable

- Open the Render health URL.
- Confirm the Render service is **Live**.
- Confirm `VITE_API_BASE_URL` has `https://` and no trailing slash.
- Confirm `CORS_ORIGINS` exactly matches the browser address.
- Free or low-cost services can take time to wake after inactivity.

### Domain does not open

- Confirm the spelling uses `-`, not `_`.
- Confirm the Cloudflare zone is **Active**.
- Confirm the Worker custom domain shows active.
- Do not add `https://` when Cloudflare asks only for the hostname.

## 12. Security rules

- Never commit `.env.local`, `backend/.env`, FIRMS keys or provider secrets.
- Store backend secrets only in Render.
- Store frontend build values only in Cloudflare.
- Restrict the public Cesium token to the production domain.
- Keep `CORS_ORIGINS` limited to the exact frontend origins.
- Review dependency and GitHub security alerts before production updates.

## Official provider instructions

- [GitHub Desktop: publish an existing project](https://docs.github.com/en/desktop/adding-and-cloning-repositories/adding-an-existing-project-to-github-using-github-desktop)
- [Cloudflare Workers Builds](https://developers.cloudflare.com/workers/ci-cd/builds/)
- [Cloudflare Workers build configuration](https://developers.cloudflare.com/workers/ci-cd/builds/configuration/)
- [Cloudflare Worker custom domains](https://developers.cloudflare.com/workers/configuration/routing/custom-domains/)
- [Render Blueprints](https://render.com/docs/infrastructure-as-code)
- [Render custom domains](https://render.com/docs/custom-domains)
