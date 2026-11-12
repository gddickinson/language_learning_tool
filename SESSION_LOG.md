# Session log

## 2026-11-12: web interface and static site (branch `web-interface`)

Built with Claude Code, following the shared web kit (`add_webpage/webkit`).

**Bugs fixed in existing code** (each in its own commit, regression tests in `tests/test_bugfixes.py`):
1. `AudioProcessor.record()` returned int16 samples (config `FORMAT = 'int16'`); librosa rejects non-float audio, so
   Record in the Practice and Recording tabs crashed in `trim_silence`. Now returns float32 in [-1, 1].
2. `alignment_utils.apply_dtw_warping()` used the MFCC-frame indices of the DTW path as sample indices, so the
   "DTW-aligned" waveform was the first few hundred samples stretched over the reference and the reported waveform
   correlation was meaningless (~0 for identical audio). Frame k now maps to sample k * 512.
3. The "Focus on matching pitch contour" recommendation could never appear (`"pitch" in analysis`, but the key is
   `pitch_feedback`). Fixed in both tabs; the Practice report text moved to Qt-free `src/feedback_report.py`.
4. Tests: `test_trim_silence` used silences shorter than one analysis frame; `test_get_similarity_feedback` expected
   bands that contradict the code and the README. Both corrected to the README.

**Needs George's decision:** the similarity score `100 * (1 - mean(dtw_mfcc, dtw_chroma, dtw_spectral) / 10)` is
0 for any non-identical audio (spectral distances are in Hz, MFCC distances are tens). Three tests that expect a
calibrated score are marked `xfail(strict=True)` until the calibration is decided. The web pages show the per-feature
distances and explain this.

**Web:** `web/` (FastAPI app on port 8163 + ES-module front end). The static site runs the whole analysis in the
browser (JS port of the librosa / fastdtw / scipy steps), tested against Python on synthetic signals (max relative
error ~1e-11, DTW paths identical). `sounddevice` is now imported tolerantly so the analysis modules load without
PortAudio (CI / server). No audio ships with the repo; references are user-recorded or user-loaded.

Tests: `pytest tests` 48 passed, 3 xfailed; `node web/static/engine.test.mjs` 9825 checks; screenshots.py static and
`--base` all ok, phone width ok. (Local macOS env: sqlite needs `DYLD_LIBRARY_PATH=/opt/anaconda3/pkgs/libsqlite-3.53.3-h1b79a29_0/lib`.)
