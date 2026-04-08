# Language Learning Pronunciation Tool -- Roadmap

## Current State
A well-structured modular app for pronunciation learning with DTW-based audio comparison. Source in `src/` (audio_processor.py 339 lines, dtw_comparator.py 327 lines, database_manager.py 497 lines, main_gui.py 2218 lines, config.py, downloader.py), tests in `tests/` (3 test files), examples, and documentation. Uses PyQt5, librosa, sounddevice, and SQLite. The `main_gui.py` at 2218 lines is extremely oversized. The test suite and modular backend are strong points, but the GUI is monolithic.

## Short-term Improvements
- [ ] Split `main_gui.py` (2218 lines) into: `practice_tab.py`, `library_tab.py`, `download_tab.py`, `stats_tab.py`, `waveform_canvas.py`, and a slim `main_gui.py` that assembles them
- [ ] Add type hints to `database_manager.py` and `downloader.py` (other modules have some)
- [ ] Add input validation for recording duration, language codes, and file paths
- [ ] Verify the Forvo API integration in `downloader.py` still works (APIs change frequently)
- [ ] Add error handling for missing audio devices in `audio_processor.py`
- [ ] Run and fix any failures in the existing test suite (`tests/test_*.py`)
- [ ] Add integration tests that exercise the full record-compare-score pipeline

## Feature Enhancements
- [ ] Add phoneme-level analysis using forced alignment (e.g., Montreal Forced Aligner)
- [ ] Implement spaced repetition scheduling for practice words
- [ ] Add real-time pitch contour overlay during recording (visual feedback while speaking)
- [ ] Support multiple reference recordings per word for high-variability training
- [ ] Add progress charts and streak tracking in the statistics tab
- [ ] Implement a "challenge mode" with timed pronunciation drills
- [ ] Add IPA (International Phonetic Alphabet) display for each word
- [ ] Support importing word lists from CSV or Anki decks

## Long-term Vision
- [ ] Integrate speech-to-text (Whisper) for content accuracy checking alongside pronunciation
- [ ] Add tone analysis for tonal languages (Mandarin, Vietnamese, Thai)
- [ ] Build a web version with WebAudio API for browser-based practice
- [ ] Implement cloud sync for practice history across devices
- [ ] Add social features -- share scores, compete with other learners
- [ ] Create a mobile companion app (React Native or Flutter)

## Technical Debt
- [ ] `main_gui.py` at 2218 lines is the most critical file to split -- it contains all 4 tabs, canvas widgets, and the main window
- [ ] `database_manager.py` (497 lines) mixes schema creation, CRUD, and statistics -- consider splitting into `db_schema.py` and `db_queries.py`
- [ ] `config.py` likely contains the Forvo API key placeholder -- ensure it is in `.gitignore` or uses environment variables
- [ ] The `data/` directory structure (samples, temp, samples.db) should be created automatically on first run
- [ ] `run.py` in project root may duplicate the entry point in `src/main_gui.py` -- consolidate
- [ ] No linting configuration (flake8, black) -- add `pyproject.toml` with tool settings
