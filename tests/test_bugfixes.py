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
