"""Python side of the web API: runs the repo's own pipeline (src/) on uploaded audio, and reads the local library.

Nothing here talks to the network; the Forvo downloader stays in the desktop app.
"""
import io
import os
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import config  # noqa: E402
from alignment_utils import apply_dtw_warping, calculate_path_smoothness  # noqa: E402
from audio_processor import AudioProcessor  # noqa: E402
from dtw_comparator import DTWComparator  # noqa: E402
from feedback_report import practice_report  # noqa: E402

_proc, _comp = AudioProcessor(), DTWComparator()


def settings():
    """Audio and DTW settings from src/config.py plus the feedback bands of DTWComparator."""
    bands = [(s, _comp.get_similarity_feedback(s)) for s in (90, 75, 60, 40, 0)]
    return {
        "sample_rate": config.SAMPLE_RATE, "nfft": config.NFFT, "noverlap": config.NOVERLAP,
        "dtw_radius": config.DTW_RADIUS, "max_recording_s": config.MAX_RECORDING_DURATION,
        "supported_formats": config.SUPPORTED_FORMATS, "n_mfcc": 13, "n_chroma": 12, "hop_length": 512,
        "feature_types": ["mfcc", "chroma", "spectral"],
        "feedback_bands": [{"min_score": s, "text": t} for s, t in bands],
    }


def load_bytes(data: bytes):
    """Decode an uploaded audio file like AudioProcessor.load_audio (mono, resampled to the app's rate)."""
    audio, sr = sf.read(io.BytesIO(data), dtype="float64")
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)
    if sr != _proc.sample_rate:
        import librosa
        audio = librosa.resample(audio, orig_sr=sr, target_sr=_proc.sample_rate)
    return audio


def compare(user: np.ndarray, reference: np.ndarray, prepare_user: bool = False):
    """The Practice tab's Compare: scores, analysis, DTW-aligned correlation and the report text."""
    if prepare_user:  # as after Record: trim silence, then normalise
        user = _proc.normalize_audio(_proc.trim_silence(user))
    if len(user) < 2048 or len(reference) < 2048:
        raise ValueError("Each clip must be at least 2048 samples (~0.05 s) long")
    results = _comp.compare_multiple_features(user, reference)
    analysis = _comp.analyze_pronunciation_errors(user, reference)
    ref_n, user_n = _proc.normalize_audio(reference), _proc.normalize_audio(user)
    quality, smooth = "Good", None
    try:
        _, path = _comp.compare_dtw(user, reference, "mfcc")
        aligned = apply_dtw_warping(user_n, ref_n, path)
        smooth = float(calculate_path_smoothness(path))
        quality = "Excellent" if smooth > 0.5 else "Good" if smooth > 0.3 else "Fair" if smooth > 0.15 else "Poor"
    except Exception:  # same fallback as the desktop app
        quality = "Fallback"
        aligned = np.pad(user_n, (0, max(0, len(ref_n) - len(user_n))))[:len(ref_n)]
    corr = float(np.corrcoef(ref_n, aligned)[0, 1])
    score = float(results["similarity_score"])
    clean = lambda d: {k: (bool(v) if isinstance(v, (bool, np.bool_)) else v if isinstance(v, str) else float(v))  # noqa: E731
                       for k, v in d.items()}
    return {
        "results": clean(results), "analysis": clean(analysis), "alignment_quality": quality,
        "smoothness": smooth, "correlation": corr, "n_user": len(user), "n_reference": len(reference),
        "report": practice_report(score, corr, quality, len(user) / len(reference), results, analysis,
                                  _comp.get_similarity_feedback(score)),
        "computed_by": "python",
    }


def db_path():
    return os.environ.get("LLT_DB_PATH", config.DB_PATH)


def library():
    """Samples in the local SQLite library (read-only). Empty list if there is no database yet."""
    path = db_path()
    if not os.path.exists(path):
        return {"samples": [], "db": "none"}
    from database_manager import DatabaseManager
    rows = DatabaseManager(path).get_samples()
    keep = ("id", "word", "language", "source", "speaker", "category", "duration", "sample_rate", "added_date")
    return {"samples": [{k: r.get(k) for k in keep} | {"file_exists": os.path.exists(r["filepath"])} for r in rows],
            "db": "local"}


def sample_file(sample_id: int):
    from database_manager import DatabaseManager
    for r in DatabaseManager(db_path()).get_samples():
        if r["id"] == sample_id and os.path.exists(r["filepath"]):
            return r["filepath"]
    return None
