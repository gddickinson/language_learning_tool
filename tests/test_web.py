"""Web interface tests: every exported endpoint answers, the static build is complete, and the JS engine tests pass.

Run: python -m pytest -q tests/test_web.py
"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from web.app import STATIC, STATIC_ENDPOINTS, app  # noqa: E402

client = TestClient(app)


def test_index_served():
    r = client.get("/")
    assert r.status_code == 200 and "static/main.js" in r.text


@pytest.mark.parametrize("path", STATIC_ENDPOINTS)
def test_endpoint(path):
    r = client.get("/api" + path)
    assert r.status_code == 200, r.text
    assert r.json() is not None


def test_static_build(tmp_path):
    sys.path.insert(0, str(ROOT / "scripts"))
    import build_static
    build_static.build(tmp_path / "site")
    assert (tmp_path / "site" / "index.html").read_text().count("APP_STATIC") == 1
    for path in STATIC_ENDPOINTS:
        assert (tmp_path / "site" / "api" / (path.strip("/") + ".json")).exists()


def test_static_assets_referenced_exist():
    html = (STATIC / "index.html").read_text()
    for name in ("style.css", "main.js"):
        assert f"static/{name}" in html and (STATIC / name).exists()


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_js_engine():
    tests = sorted(STATIC.glob("*.test.mjs"))
    for t in tests:
        r = subprocess.run(["node", str(t)], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr


# --- project-specific API tests ------------------------------------------------------------------------------------
import io  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402

import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402

from web import service  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "engine_cases.json"


def _fixture_module():
    sys.path.insert(0, str(ROOT / "scripts"))
    import make_engine_fixture
    return make_engine_fixture


def _wav(y, subtype="DOUBLE"):
    buf = io.BytesIO()
    sf.write(buf, y, 44100, format="WAV", subtype=subtype)
    return buf.getvalue()


def _same(a, b, path="fixture"):
    """Recursive comparison: floats with rtol 1e-9 (libm differs between macOS and Linux), everything else exact."""
    if isinstance(a, float) or isinstance(b, float):
        assert math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12), f"{path}: {a} vs {b}"
    elif isinstance(a, dict):
        assert a.keys() == b.keys(), path
        for k in a:
            _same(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, list):
        assert len(a) == len(b), f"{path}: length"
        for i, (x, y) in enumerate(zip(a, b)):
            _same(x, y, f"{path}[{i}]")
    else:
        assert a == b, f"{path}: {a!r} vs {b!r}"


def test_engine_fixture_is_current():
    """tests/fixtures/engine_cases.json (used by engine.test.mjs and /api/verify) still matches the Python code."""
    stored = json.loads(FIXTURE.read_text())
    fresh = json.loads(json.dumps(_fixture_module().build()))
    stored.pop("versions"), fresh.pop("versions")
    _same(stored, fresh)


def test_info_settings_come_from_config():
    import config
    s = client.get("/api/info").json()["settings"]
    assert (s["sample_rate"], s["nfft"], s["noverlap"], s["dtw_radius"]) == (
        config.SAMPLE_RATE, config.NFFT, config.NOVERLAP, config.DTW_RADIUS)
    assert [b["min_score"] for b in s["feedback_bands"]] == [90, 75, 60, 40, 0]


def test_verify_endpoint_serves_fixture():
    assert client.get("/api/verify").json()["pairs"].keys() == {"close", "different", "reference"}


def test_compare_matches_fixture():
    """POST /api/compare on the synthetic clips gives the fixture's Python numbers and report."""
    m = _fixture_module()
    u, r = m.synth(m.PRESETS["close"]), m.synth(m.PRESETS["reference"])
    res = client.post("/api/compare", files={"user": ("u.wav", _wav(u)), "reference": ("r.wav", _wav(r))})
    assert res.status_code == 200, res.text
    out, fx = res.json(), json.loads(FIXTURE.read_text())["pairs"]["close"]
    for k in ("dtw_mfcc", "dtw_chroma", "dtw_spectral", "similarity_score"):
        assert math.isclose(out["results"][k], fx["results"][k], rel_tol=1e-9, abs_tol=1e-12)
    assert math.isclose(out["correlation"], fx["correlation"], rel_tol=1e-9)
    assert out["report"] == fx["report"] and out["computed_by"] == "python"


def test_compare_prepare_user_trims_and_normalises():
    m = _fixture_module()
    padded, r = 0.5 * m.synth(m.PRESETS["padded"]), m.synth(m.PRESETS["reference"])
    res = client.post("/api/compare", files={"user": ("u.wav", _wav(padded)), "reference": ("r.wav", _wav(r))},
                      data={"prepare_user": "true"}).json()
    fx = json.loads(FIXTURE.read_text())["trim"]
    assert res["n_user"] == fx["n_out"] < len(padded)


def test_compare_errors():
    bad = client.post("/api/compare", files={"user": ("u.wav", b"not audio"), "reference": ("r.wav", b"x")})
    assert bad.status_code == 400
    short = client.post("/api/compare", files={"user": ("u.wav", _wav(np.zeros(100))), "reference": ("r.wav", _wav(np.zeros(100)))})
    assert short.status_code == 400 and "2048" in short.text


def test_library(tmp_path, monkeypatch):
    monkeypatch.setenv("LLT_DB_PATH", str(tmp_path / "none.db"))
    assert client.get("/api/library").json() == {"samples": [], "db": "none"}
    from database_manager import DatabaseManager
    db = tmp_path / "samples.db"
    wav = tmp_path / "hola.wav"
    wav.write_bytes(_wav(np.zeros(4410), "PCM_16"))
    mgr = DatabaseManager(str(db))
    sid = mgr.add_sample("hola", "es", str(wav), source="test", duration=0.1, sample_rate=44100)
    mgr.add_sample("gone", "es", str(tmp_path / "missing.wav"))
    monkeypatch.setenv("LLT_DB_PATH", str(db))
    lib = client.get("/api/library").json()
    assert sorted((s["word"], s["file_exists"]) for s in lib["samples"]) == [("gone", False), ("hola", True)]
    assert all("filepath" not in s for s in lib["samples"])
    audio = client.get(f"/api/library/{sid}/audio")
    assert audio.status_code == 200 and audio.content == wav.read_bytes()
    assert client.get(f"/api/library/{sid + 1}/audio").status_code == 404
