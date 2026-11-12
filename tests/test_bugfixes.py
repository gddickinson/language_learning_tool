"""Regression tests for bugs fixed in existing code (see SESSION_LOG.md, 2026-11-12)."""
import os
import sys
from unittest import mock

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import audio_processor  # noqa: E402
from audio_processor import AudioProcessor  # noqa: E402

SR = 44100


def _tone(seconds=1.0, f=220.0):
    t = np.arange(int(seconds * SR)) / SR
    return np.sin(2 * np.pi * f * t)


def test_record_returns_float_audio_that_trim_silence_accepts():
    """record() asked sounddevice for int16 and returned it unchanged; librosa (trim_silence, MFCC) only accepts
    floating-point audio, so Record in the Practice and Recording tabs raised ParameterError."""
    quiet = np.zeros(SR // 2)
    sig = np.concatenate([quiet, 0.5 * _tone(1.0), quiet])
    as_int16 = np.round(sig * 32767).astype(np.int16).reshape(-1, 1)
    with mock.patch.object(audio_processor.sd, 'rec', return_value=as_int16), \
            mock.patch.object(audio_processor.sd, 'wait'):
        proc = AudioProcessor()
        audio = proc.record(len(sig) / SR)
    assert np.issubdtype(audio.dtype, np.floating)
    assert np.max(np.abs(audio)) <= 1.0
    np.testing.assert_allclose(audio, sig, atol=1 / 32767)
    trimmed = proc.trim_silence(audio)
    assert len(trimmed) < len(audio)


def _speechlike(seconds=1.0, seed=0):
    """Chirp with a syllable-like envelope: frames differ from each other, so the DTW path is well defined."""
    t = np.arange(int(seconds * SR)) / SR
    env = 0.2 + np.sin(np.pi * 3 * t / seconds) ** 2
    return env * np.sin(2 * np.pi * (180 * t + 200 * t ** 2)) + 0.01 * np.random.default_rng(seed).normal(size=len(t))


def test_dtw_warping_maps_feature_frames_to_samples():
    """apply_dtw_warping() treated the MFCC frame indices of the DTW path as sample indices, so the "aligned" user
    waveform was the first ~N_frames samples stretched over the whole reference (correlation with an identical
    reference was near zero). Frame indices are now scaled by the feature hop length (512 samples)."""
    from alignment_utils import apply_dtw_warping
    from dtw_comparator import DTWComparator
    ref = _speechlike()
    ref = ref / np.max(np.abs(ref))
    _, path = DTWComparator().compare_dtw(ref, ref, 'mfcc')
    warped = apply_dtw_warping(ref, ref, path)
    assert len(warped) == len(ref)
    assert np.corrcoef(ref, warped)[0, 1] > 0.99


def test_practice_report_recommends_pitch_when_pitch_differs():
    """The Practice/Live tabs tested `"pitch" in analysis`, but the analysis dict only has "pitch_feedback", so
    "Focus on matching pitch contour" was never shown."""
    from feedback_report import practice_report
    analysis = {'speed_feedback': 'Good speaking speed', 'pitch_feedback': 'Pitch/tone differs significantly',
                'volume_feedback': 'Good volume'}
    text = practice_report(40.0, 0.8, 'Good', 1.0, {}, analysis, 'Needs improvement.')
    assert 'Focus on matching pitch contour' in text
    analysis['pitch_feedback'] = 'Good pitch/tone'
    assert 'Focus on matching pitch contour' not in practice_report(40.0, 0.8, 'Good', 1.0, {}, analysis, 'x')
