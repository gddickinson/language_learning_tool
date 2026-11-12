"""Web interface for the Language Learning Pronunciation Tool.

- app.py      FastAPI app: front end in static/, JSON API under /api, STATIC_ENDPOINTS for the static site
- service.py  Python side of the API: the repo's AudioProcessor / DTWComparator / alignment pipeline on uploaded audio,
              and read-only access to the local sample library (SQLite)
- static/     ES-module front end; dsp.js, features.js, dtw.js, align.js port the analysis to the browser
"""
