# loam-paddock-analyser

A simple web app for uploading paddock **GeoJSON**, grouping by owner and project, and surfacing useful metrics (total area, paddock counts, invalid geometry stats) with an interactive map.

Built the way I'd approach a data engineering problem: validate early, compute correctly (geodesic areas), make failures explicit, and keep the stack simple and dependable.

---

## Why these choices

- **FastAPI + orjson** — fast, typed, minimal ceremony for file upload and JSON responses.
- **Shapely + pyproj** — battle-tested geometry tools with **geodesic** area (WGS84) so results are accurate even at high latitudes.
- **Vanilla JavaScript + Leaflet** — no build step, no framework complexity, just clean HTML/CSS/JS for the map.
- **Pipenv** — deterministic environments with `Pipfile.lock`.
- **Tests** — unit tests for geometry calculations and API endpoints.

---

## What it does

1. Upload a GeoJSON `FeatureCollection` of paddocks.
2. The backend:
   - Validates GeoJSON structure.
   - Repairs invalid geometries where possible (falls back to marking invalid).
   - Groups by owner and project name (uses `properties.Project__Name`, `project_name`, or `project`).
   - Computes **geodesic** area per paddock and aggregates per project.
   - Returns a summary, grouped projects, and **normalized** GeoJSON to render on the map.
3. The frontend displays summary cards, sortable project tables, individual paddock details, and a color-coded map.

Assumptions:
- Coordinates are lon/lat (WGS84).
- Holes in polygons are subtracted from area.
- Paddocks without project names are grouped as "Invalid Paddocks".
- Infrastructure (shed, house, building) is flagged but included in totals.

---

## Quick start

**First time setup:**
```bash
cd backend
pipenv install
cd ..
```

**Start the app:**
```bash
./start.sh
```
This starts both backend (port 8000) and frontend (port 8080). Open http://localhost:8080 in your browser and upload `sample_paddocks.geojson` to see it in action.

Press Ctrl+C to stop both servers.

**Or run manually in separate terminals:**

Backend:
```bash
cd backend
pipenv run uvicorn app.main:app --reload
```

Frontend:
```bash
cd frontend
python3 -m http.server 8080
```

---

## Running tests

```bash
cd backend
pipenv run pytest
```

---

## Project structure

```
loam-paddock-analyser/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app and upload endpoint
│   │   ├── geometry.py      # Geodesic calculations and validation
│   │   └── models.py        # Pydantic response models
│   └── tests/
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
└── sample_paddocks.geojson
```