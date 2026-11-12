# Language Learning Tool — Interface Map

## Source: `src/`

| File | Lines | Purpose | Key classes / functions |
|------|-------|---------|----------------------|
| `main_gui.py` | ~80 | Thin assembler — creates MainWindow with all tabs | `MainWindow`, `main()` |
| `practice_tab.py` | ~290 | Record + DTW-compare pronunciation | `PracticeTab` |
| `live_comparison_tab.py` | ~350 | Real-time mic monitoring with DTW | `LiveComparisonTab` |
| `recording_tab.py` | ~160 | Record new samples to database | `RecordingTab` |
| `library_tab.py` | ~120 | Browse / search sample library | `LibraryTab` |
| `download_tab.py` | ~200 | Forvo search & batch download | `DownloadTab` |
| `stats_tab.py` | ~90 | Statistics / practice history | `StatisticsTab` |
| `waveform_canvas.py` | ~150 | Matplotlib canvas (waveform + spectrogram) | `WaveformCanvas` |
| `alignment_utils.py` | ~110 | Shared DTW warping helpers (path in feature frames, `FEATURE_HOP_LENGTH` = 512) | `apply_dtw_warping()`, `calculate_path_smoothness()`, `smooth_warped_audio()` |
| `feedback_report.py` | ~70 | Qt-free Practice tab report text and score colour | `practice_report()`, `score_colour()` |
| `audio_processor.py` | ~340 | Audio I/O, features, MFCC, pitch | `AudioProcessor` |
| `dtw_comparator.py` | ~330 | DTW comparison engine | `DTWComparator` |
| `database_manager.py` | ~500 | SQLite CRUD for samples & recordings | `DatabaseManager` |
| `downloader.py` | ~260 | Forvo API client | `SampleDownloader` |
| `config.py` | ~45 | Constants, paths, settings | module-level constants |

## Web interface: `web/`

| File | Purpose |
|------|---------|
| `web/app.py` | FastAPI app: `/api/info`, `/api/verify` (exported to the static site), `POST /api/compare`, `/api/library`, `/api/library/{id}/audio`; `STATIC_ENDPOINTS` |
| `web/service.py` | Runs the `src/` pipeline on uploads (`compare`, `load_bytes`), settings from `config`, read-only library (`LLT_DB_PATH` overrides the DB path) |
| `web/static/dsp.js` | FFT, Hann / Tukey windows, librosa STFT, scipy spectrogram, trim_silence, normalize |
| `web/static/features.js` | Mel filterbank, MFCC, piptrack, estimate_tuning, chroma_stft, spectral centroid / roll-off, ZCR |
| `web/static/dtw.js` | fastdtw port, `analyseClip`, `compareClips` (compare_multiple_features + analyze_pronunciation_errors) |
| `web/static/align.js` | DTW warping (not-a-knot cubic spline, savgol), smoothness, correlation, `practiceReport` |
| `web/static/summary.js` | `get_audio_features` port |
| `web/static/synth.js` | Seeded synthetic test / demo signals (mirrored in `scripts/make_engine_fixture.py`) |
| `web/static/audio_io.js` | Decode / resample to 44.1 kHz, microphone recording (after a click), playback, WAV export |
| `web/static/plots.js` | Canvas waveform, heatmap, line and DTW-path plots |
| `web/static/state.js`, `clip_panel.js` | Shared clips; record / load / demo panel with waveform + spectrogram |
| `web/static/{home,practice,practice_results,analyse,library,verify,about}.js` | Pages |
| `web/static/engine.test.mjs` | Node test of the JS engine against `tests/fixtures/engine_cases.json` |
| `web/static/core.js`, `style.css` | Shared web kit (unchanged); `style_app.css` project colours |

Scripts: `run_web.py` (port 8163), `scripts/build_static.py` (static site to `site/`), `scripts/screenshots.py`
(smoke test / README images in `docs/img/`), `scripts/make_engine_fixture.py` (Python results for the JS tests).

## Entry Points

| File | Purpose |
|------|---------|
| `run.py` (project root) | Adds `src/` to path and calls `main()` |
| `src/main_gui.py` | Direct execution (`python main_gui.py`) |

## Tests: `tests/`

| File | Coverage |
|------|----------|
| `test_audio_processor.py` | AudioProcessor save/load, waveform, spectrogram, MFCC, pitch |
| `test_dtw_comparator.py` | DTW comparison |
| `test_database_manager.py` | Database CRUD |
| `test_bugfixes.py` | Regression tests for fixed bugs (int16 recording, DTW warping units, pitch recommendation) |
| `test_web.py` | Web API, static build, fixture current, node engine test |

## Data Flow

```
MainWindow
  ├── PracticeTab      ─▶ AudioProcessor ─▶ DTWComparator ─▶ DatabaseManager
  ├── LiveComparisonTab ─▶ (same pipeline, real-time)
  ├── RecordingTab     ─▶ AudioProcessor ─▶ DatabaseManager
  ├── LibraryTab       ─▶ DatabaseManager ─▶ AudioProcessor (playback)
  ├── DownloadTab      ─▶ SampleDownloader ─▶ DatabaseManager
  └── StatisticsTab    ─▶ DatabaseManager
```
