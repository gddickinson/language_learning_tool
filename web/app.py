"""FastAPI web app for the Language Learning Pronunciation Tool: serves the front end in static/ and the JSON API under /api.

Run with `python run_web.py` (http://127.0.0.1:8163, local only). `scripts/build_static.py` exports every path in
STATIC_ENDPOINTS to JSON for the GitHub Pages site, so keep that list in step with the GET routes below. The analysis
itself also runs in the browser (static/dsp.js, features.js, dtw.js, align.js); POST /api/compare re-runs a comparison
with the repo's Python code so the two can be checked against each other, and /api/library reads the local database.
"""
import json
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from web import service

STATIC = Path(__file__).resolve().parent / "static"
FIXTURE = service.ROOT / "tests" / "fixtures" / "engine_cases.json"

app = FastAPI(title="Language Learning Pronunciation Tool")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/info")
def info():
    """Project summary and the settings the analysis uses (from src/config.py)."""
    return {
        "title": "Language Learning Pronunciation Tool",
        "description": ("Learn foreign language pronunciation through audio recording, waveform visualization, and "
                        "comparison using Dynamic Time Warping (DTW)."),
        "settings": service.settings(),
    }


@app.get("/api/verify")
def verify():
    """Python results on the synthetic test signals (tests/fixtures/engine_cases.json) for the in-browser check."""
    return json.loads(FIXTURE.read_text())


@app.post("/api/compare")
async def compare(user: UploadFile = File(...), reference: UploadFile = File(...), prepare_user: bool = Form(False)):
    """Compare two uploaded clips with the repo's Python pipeline (DTWComparator + alignment_utils)."""
    try:
        u = service.load_bytes(await user.read())
        r = service.load_bytes(await reference.read())
        return service.compare(u, r, prepare_user)
    except HTTPException:
        raise
    except Exception as e:  # unreadable audio, too short, ...
        raise HTTPException(400, f"Could not compare: {e}") from e


@app.get("/api/library")
def library():
    """Reference samples stored in the local library (data/samples.db). Local app only."""
    return service.library()


@app.get("/api/library/{sample_id}/audio")
def library_audio(sample_id: int):
    path = service.sample_file(sample_id)
    if not path:
        raise HTTPException(404, "No such sample (or its audio file is missing)")
    return FileResponse(path)


# GET paths (without the /api prefix) written to the static site as api/<path>.json.
STATIC_ENDPOINTS = ["/info", "/verify"]
