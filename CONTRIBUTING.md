# Contributing

AgriScope Earth welcomes fixes, tests, documentation and scientifically justified mission improvements.

## Before proposing a scientific change

1. State the research question and intended population or system.
2. Cite the primary methodology or authoritative data specification.
3. Define units, spatial and temporal support, missing-data behaviour and uncertainty.
4. Add tests for equations, boundaries and evidence-status handling.
5. Update `docs/METHODOLOGY.md`, `docs/DATA_SOURCES.md` and the method version when interpretation changes.

Do not present demonstration values as observed, remove provider attribution, add uncited universal thresholds, or use animated map graphics as evidence geometry.

## Development

```bash
npm ci
npm run dev
```

In a second terminal:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

Run focused checks before a pull request:

```bash
npx eslint app components/agriscope lib/agriscope
cd backend && pytest -q
```
