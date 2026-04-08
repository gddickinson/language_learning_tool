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
| `alignment_utils.py` | ~90 | Shared DTW warping helpers | `apply_dtw_warping()`, `calculate_path_smoothness()`, `smooth_warped_audio()` |
| `audio_processor.py` | ~340 | Audio I/O, features, MFCC, pitch | `AudioProcessor` |
| `dtw_comparator.py` | ~330 | DTW comparison engine | `DTWComparator` |
| `database_manager.py` | ~500 | SQLite CRUD for samples & recordings | `DatabaseManager` |
| `downloader.py` | ~260 | Forvo API client | `SampleDownloader` |
| `config.py` | ~45 | Constants, paths, settings | module-level constants |

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
