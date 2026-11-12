"""Calibrate the similarity-score scales d0 in src/config.py (SCORE_D0) and show what the score does.

d0 for each feature set = the largest DTW distance between a synthetic voice (web/static/synth.js "reference") and
its same-voice variants (time-stretched 0.8x and 1.25x, pitch-shifted -6 % and +6 %, different noise), divided by
ln(100 / 70) and rounded to two significant figures, so every such variant scores at least about 70 on every
feature. Unrelated signals (another synthetic voice, a falling-intonation voice, a chirp, white noise) are listed to
show they score low. Run: python scripts/calibrate_score.py
"""
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import config  # noqa: E402
from dtw_comparator import DTWComparator  # noqa: E402
from make_engine_fixture import PRESETS, synth  # noqa: E402

FEATURES = ("mfcc", "chroma", "spectral")
SR = 44100


def _voice(**changes):
    p = dict(PRESETS["reference"])
    p.update(changes)
    return synth(p)


def signals():
    t = np.arange(SR) / SR
    same = {
        "time-stretched 1.25x": _voice(seconds=1.125),
        "time-stretched 0.8x": _voice(seconds=0.72),
        "pitch-shifted +6 %": _voice(f0a=140 * 1.06, f0b=190 * 1.06),
        "pitch-shifted -6 %": _voice(f0a=140 / 1.06, f0b=190 / 1.06),
        "different noise": _voice(seed=9),
    }
    unrelated = {
        "other voice (synth 'different')": synth(PRESETS["different"]),
        "falling intonation, other timbre": _voice(f0a=220, f0b=120, syl=3, harm=[1, 0.1, 0.6, 0.05, 0.4]),
        "chirp 300-1100 Hz": 0.5 * np.sin(2 * np.pi * (300 * t + 400 * t * t)),
        "white noise": np.random.default_rng(0).normal(0, 0.3, SR),
    }
    return _voice(), same, unrelated


def distances(ref, others, comp):
    return {k: {f: comp.compare_dtw(y, ref, f)[0] for f in FEATURES} for k, y in others.items()}


def calibrate():
    comp = DTWComparator()
    ref, same, unrelated = signals()
    ds = distances(ref, same, comp)
    d0 = {}
    for f in FEATURES:
        raw = max(d[f] for d in ds.values()) / math.log(100 / 70)
        d0[f] = float(f"{raw:.2g}")
    return d0, ds, distances(ref, unrelated, comp)


def main():
    d0, same, unrelated = calibrate()
    print("calibrated d0:", d0, "  (config.SCORE_D0:", config.SCORE_D0, ")")
    comp = DTWComparator()
    ref, s_sig, u_sig = signals()
    for title, sig in (("same voice", s_sig), ("unrelated", u_sig)):
        print(f"\n{title}:")
        for k, y in sig.items():
            r = comp.compare_multiple_features(y, ref)
            parts = "  ".join(f"{f} {r[f'dtw_{f}']:.3f}->{r[f'{f}_similarity']:.0f}" for f in FEATURES)
            print(f"  {k:34s} score {r['similarity_score']:5.1f}   {parts}")


if __name__ == "__main__":
    main()
