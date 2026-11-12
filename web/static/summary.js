// AudioProcessor.get_audio_features, from an analysed clip (dtw.analyseClip): duration, RMS, peak, spectral centroid
// mean / sd, zero-crossing-rate mean and per-coefficient MFCC mean / sd (numpy population sd).
import { SR } from './dsp.js';

const meanSd = xs => {
  const n = xs.length, m = xs.reduce((a, b) => a + b, 0) / n;
  return { mean: m, std: Math.sqrt(xs.reduce((a, b) => a + (b - m) ** 2, 0) / n) };
};

export function audioFeatures(a) {
  const y = a.y;
  let e = 0, mx = 0; for (const v of y) { e += v * v; mx = Math.max(mx, Math.abs(v)); }
  const c = meanSd(a.feats.spectral.map(r => r[0]));
  return {
    duration: y.length / SR, sample_rate: SR, rms_energy: Math.sqrt(e / y.length), max_amplitude: mx,
    spectral_centroid_mean: c.mean, spectral_centroid_std: c.std,
    zero_crossing_rate_mean: meanSd(a.feats.spectral.map(r => r[2])).mean,
    mfcc: Array.from(a.feats.mfcc[0], (_, k) => meanSd(a.feats.mfcc.map(r => r[k]))),
  };
}
