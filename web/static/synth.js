// Synthetic test signals (not speech): a harmonic "voice" with a gliding pitch, syllable-like loudness envelope and
// a little seeded noise. Used for the Python-vs-JS tests (scripts/make_engine_fixture.py builds the same signals)
// and as clearly labelled demo clips on the site. No recorded audio ships with the repo.
import { SR } from './dsp.js';

// mulberry32, as core.rng (copied so this module also runs under node without the DOM helpers)
export function rng(seed = 1) {
  let a = seed >>> 0;
  return () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

// Parameters: seconds, f0 start/end (Hz), syllables, harmonic amplitudes, noise level, seed, silence pad (s).
export const PRESETS = {
  reference: { seconds: 0.9, f0a: 140, f0b: 190, syl: 2, harm: [1, 0.6, 0.35, 0.2, 0.1], noise: 0.01, seed: 1, pad: 0 },
  close: { seconds: 1.05, f0a: 146, f0b: 196, syl: 2, harm: [1, 0.55, 0.4, 0.2, 0.1], noise: 0.01, seed: 2, pad: 0 },
  different: { seconds: 0.7, f0a: 260, f0b: 210, syl: 3, harm: [1, 0.1, 0.5, 0.05, 0.3], noise: 0.03, seed: 3, pad: 0 },
  padded: { seconds: 0.9, f0a: 140, f0b: 190, syl: 2, harm: [1, 0.6, 0.35, 0.2, 0.1], noise: 0.01, seed: 1, pad: 0.3 },
};

export function synth(p, sr = SR) {
  const n = Math.round(p.seconds * sr), np_ = Math.round(p.pad * sr), out = new Float64Array(n + 2 * np_);
  const r = rng(p.seed), k = (p.f0b - p.f0a) / p.seconds;
  for (let i = 0; i < n; i++) {
    const t = i / sr, phase = p.f0a * t + 0.5 * k * t * t;
    const env = 0.15 + Math.sin(Math.PI * p.syl * t / p.seconds) ** 2;
    let s = 0;
    for (let h = 0; h < p.harm.length; h++) s += p.harm[h] * Math.sin(2 * Math.PI * (h + 1) * phase);
    out[np_ + i] = 0.4 * env * s + p.noise * (2 * r() - 1);
  }
  return out;
}
