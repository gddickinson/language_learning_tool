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

**Was open, fixed below (same day):** the similarity score `100 * (1 - mean(dtw_mfcc, dtw_chroma, dtw_spectral) / 10)` is
0 for any non-identical audio (spectral distances are in Hz, MFCC distances are tens). Three tests that expect a
calibrated score are marked `xfail(strict=True)` until the calibration is decided. The web pages show the per-feature
distances and explain this.

**Web:** `web/` (FastAPI app on port 8163 + ES-module front end). The static site runs the whole analysis in the
browser (JS port of the librosa / fastdtw / scipy steps), tested against Python on synthetic signals (max relative
error ~1e-11, DTW paths identical). `sounddevice` is now imported tolerantly so the analysis modules load without
PortAudio (CI / server). No audio ships with the repo; references are user-recorded or user-loaded.

Tests: `pytest tests` 48 passed, 3 xfailed; `node web/static/engine.test.mjs` 9825 checks; screenshots.py static and
`--base` all ok, phone width ok. (Local macOS env: sqlite needs `DYLD_LIBRARY_PATH=/opt/anaconda3/pkgs/libsqlite-3.53.3-h1b79a29_0/lib`.)

## 2026-11-12 (later): meaningful similarity score

Fixed the uncalibrated score (George's "fix any other problems" rule, via the lead). `DTWComparator.comparison_features`
puts the features on a common scale before DTW: peak-normalised audio; MFCC from log-mel floored 40 dB below the peak
(`config.MFCC_TOP_DB`; a quiet noise floor no longer dominates), in units of 10 dB; centroid / roll-off / Nyquist;
each frame / sqrt(n coefficients). Each per-path-length DTW distance becomes `100 * exp(-d / d0)` (also returned as
`mfcc_similarity`, `chroma_similarity`, `spectral_similarity`, which the Practice report already printed if present),
and the score is the weighted mean (0.5 / 0.3 / 0.2). `scripts/calibrate_score.py` derives d0 (0.71 / 0.15 / 0.023)
so that time-stretched (0.8x, 1.25x), pitch-shifted (+-6 %) and re-noised copies of a synthetic voice score >= 70 on
each feature: they now score 74-96 overall, unrelated signals 3-25, identical audio 100. The three strict xfails pass
unchanged; new tests check the behaviour and that config.SCORE_D0 matches the calibration. JS port updated
(dtw.js SCORE constants checked against config by engine.test.mjs). Caveat: calibrated on synthetic signals only.
`extract_features` (raw librosa features) is unchanged; the DTW path used for the aligned display now comes from the
scaled features.
