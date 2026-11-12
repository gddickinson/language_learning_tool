// Feature extraction used by DTWComparator.extract_features, ported from librosa 1.0 defaults:
// MFCC (13 of 128 Slaney mel bands, dB, orthonormal DCT-II), chroma_stft (with librosa's tuning estimate),
// spectral centroid / rolloff / zero-crossing rate, and piptrack. All take the STFT from dsp.stft().
// Matrices are arrays of frames: feat[t][k] (time x features, as extract_features returns after .T).
import { SR, N_FFT, HOP, fftFrequencies } from './dsp.js';

const TINY = 2.2250738585072014e-308;  // np.finfo(float64).tiny (librosa.util.tiny)
const F_SP = 200.0 / 3, MIN_LOG_HZ = 1000.0, MIN_LOG_MEL = (MIN_LOG_HZ - 0.0) / F_SP, LOGSTEP = Math.log(6.4) / 27.0;
export const hzToMel = f => f >= MIN_LOG_HZ ? MIN_LOG_MEL + Math.log(f / MIN_LOG_HZ) / LOGSTEP : (f - 0.0) / F_SP;
export const melToHz = m => m >= MIN_LOG_MEL ? MIN_LOG_HZ * Math.exp(LOGSTEP * (m - MIN_LOG_MEL)) : 0.0 + F_SP * m;

const cache = new Map();
const memo = (key, fn) => { if (!cache.has(key)) cache.set(key, fn()); return cache.get(key); };

// librosa.filters.mel(sr, n_fft, n_mels=128, norm='slaney'), stored as float32 like librosa.
export function melFilter(sr = SR, n = N_FFT, nMels = 128) {
  return memo(`mel${sr}/${n}/${nMels}`, () => {
    const fft = fftFrequencies(sr, n), maxMel = hzToMel(sr / 2), step = maxMel / (nMels + 1);
    const melF = Array.from({ length: nMels + 2 }, (_, i) => melToHz(i === nMels + 1 ? maxMel : i * step + 0));
    const W = [];
    for (let i = 0; i < nMels; i++) {
      const row = new Float64Array(fft.length), d0 = melF[i + 1] - melF[i], d1 = melF[i + 2] - melF[i + 1];
      const enorm = 2.0 / (melF[i + 2] - melF[i]);
      for (let k = 0; k < fft.length; k++) {
        const lower = -(melF[i] - fft[k]) / d0, upper = (melF[i + 2] - fft[k]) / d1;
        row[k] = Math.fround(Math.fround(Math.max(0, Math.min(lower, upper))) * enorm);
      }
      W.push(row);
    }
    return W;
  });
}

// librosa.feature.mfcc(y, sr, n_mfcc=13): power_to_db(melspectrogram) (ref 1, amin 1e-10, floored topDb below the
// peak of the whole matrix), then scipy.fft.dct(type 2, norm='ortho') over the mel axis, first n_mfcc coefficients.
export function mfcc(pow, sr = SR, nMfcc = 13, topDb = 80.0) {
  const W = melFilter(sr, 2 * (pow[0].length - 1)), M = W.length;
  const logmel = pow.map(S => {
    const out = new Float64Array(M);
    for (let m = 0; m < M; m++) { let s = 0; const w = W[m]; for (let k = 0; k < S.length; k++) s += S[k] * w[k]; out[m] = 10.0 * Math.log10(Math.max(1e-10, s)) - 0; }
    return out;
  });
  let top = -Infinity; for (const r of logmel) for (const v of r) top = Math.max(top, v);
  const floor = top - topDb;
  const cosT = memo(`dct${M}/${nMfcc}`, () => Array.from({ length: nMfcc }, (_, k) =>
    Float64Array.from({ length: M }, (_, n) => Math.cos(Math.PI * k * (2 * n + 1) / (2 * M)))));
  return logmel.map(r => {
    for (let m = 0; m < M; m++) if (r[m] < floor) r[m] = floor;
    const c = new Float64Array(nMfcc);
    for (let k = 0; k < nMfcc; k++) {
      let s = 0; const ct = cosT[k]; for (let n = 0; n < M; n++) s += r[n] * ct[n];
      c[k] = 2 * s * (k === 0 ? Math.sqrt(1 / (4 * M)) : Math.sqrt(1 / (2 * M)));
    }
    return c;
  });
}

// librosa.piptrack(S=S, sr, n_fft, fmin=150, fmax=4000, threshold=0.1): pitches[t][f], mags[t][f] (0 where none).
export function piptrack(S, sr = SR, fmin = 150.0, fmax = 4000.0, threshold = 0.1) {
  const n = 2 * (S[0].length - 1), freqs = fftFrequencies(sr, n), F = S[0].length;
  fmax = Math.min(fmax, sr / 2); fmin = Math.max(fmin, 0);
  const pitches = [], mags = [];
  for (const x of S) {
    const p = new Float64Array(F), mg = new Float64Array(F);
    let mx = -Infinity; for (const v of x) mx = Math.max(mx, v);
    const ref = threshold * mx;
    const xt = Float64Array.from(x, v => v * (v > ref ? 1 : 0));
    for (let f = 1; f < F - 1; f++) {
      if (!(fmin <= freqs[f] && freqs[f] < fmax)) continue;
      if (!(xt[f] > xt[f - 1] && xt[f] >= xt[f + 1])) continue;
      const a = x[f + 1] + x[f - 1] - 2 * x[f], b = (x[f + 1] - x[f - 1]) / 2;
      const shift = Math.abs(b) >= Math.abs(a) ? 0 : -b / a;
      const avg = (x[f + 1] - x[f - 1]) / 2;  // np.gradient (interior)
      p[f] = (f + shift) * sr / n;
      mg[f] = x[f] + 0.5 * avg * shift;
    }
    pitches.push(p); mags.push(mg);
  }
  return { pitches, mags };
}

// librosa.pitch_tuning(freqs, resolution=0.01, bins_per_octave=12) with numpy.histogram's edge rules.
export function pitchTuning(freqs, resolution = 0.01, bpo = 12) {
  const f = freqs.filter(v => v > 0);
  if (!f.length) return 0.0;
  const nb = Math.ceil(1.0 / resolution), step = 1.0 / nb;
  const edges = Array.from({ length: nb + 1 }, (_, i) => i === nb ? 0.5 : i * step + -0.5);
  const counts = new Array(nb).fill(0), norm = nb / 1.0;
  for (const v of f) {
    let r = bpo * Math.log2(v / (440.0 / 16));
    r = r - Math.floor(r);
    if (r >= 0.5) r -= 1.0;
    if (!(r >= -0.5 && r <= 0.5)) continue;
    let i = Math.trunc((r - -0.5) * norm);
    if (i === nb) i -= 1;
    if (r < edges[i]) i -= 1;
    if (r >= edges[i + 1] && i !== nb - 1) i += 1;
    counts[i]++;
  }
  let best = 0; for (let i = 1; i < nb; i++) if (counts[i] > counts[best]) best = i;
  return edges[best];
}

// librosa.estimate_tuning(S=power, sr, bins_per_octave=12)
export function estimateTuning(S, sr = SR) {
  const { pitches, mags } = piptrack(S, sr);
  const sel = [];
  for (let t = 0; t < pitches.length; t++) for (let f = 0; f < pitches[t].length; f++) if (pitches[t][f] > 0) sel.push(mags[t][f]);
  let thr = 0.0;
  if (sel.length) {
    sel.sort((a, b) => a - b);
    const h = sel.length >> 1;
    thr = sel.length % 2 ? sel[h] : (sel[h - 1] + sel[h]) / 2;
  }
  const keep = [];
  for (let t = 0; t < pitches.length; t++) for (let f = 0; f < pitches[t].length; f++) {
    if (pitches[t][f] > 0 && mags[t][f] >= thr) keep.push(pitches[t][f]);
  }
  return pitchTuning(keep);
}

// librosa.filters.chroma(sr, n_fft, tuning, n_chroma=12, ctroct=5, octwidth=2, norm=2, base_c=True) (float32).
export function chromaFilter(sr, n, tuning, nC = 12) {
  return memo(`chroma${sr}/${n}/${tuning}`, () => {
    const A440 = 440.0 * 2.0 ** (tuning / nC), bins = new Float64Array(n);
    for (let i = 1; i < n; i++) bins[i] = nC * Math.log2((i * (sr / n)) / (A440 / 16));
    bins[0] = bins[1] - 1.5 * nC;
    const bw = new Float64Array(n);
    for (let i = 0; i < n - 1; i++) bw[i] = Math.max(bins[i + 1] - bins[i], 1.0);
    bw[n - 1] = 1;
    const half = Math.round(nC / 2), wts = Array.from({ length: nC }, () => new Float64Array(n));
    for (let c = 0; c < nC; c++) for (let k = 0; k < n; k++) {
      const x = bins[k] - c + half + 10 * nC, D = (x % nC) - half;
      wts[c][k] = Math.exp(-0.5 * (2 * D / bw[k]) ** 2);
    }
    for (let k = 0; k < n; k++) {
      let s = 0; for (let c = 0; c < nC; c++) s += wts[c][k] ** 2;
      let len = s ** (1.0 / 2); if (len < TINY) len = 1.0;
      const oct = Math.exp(-0.5 * ((bins[k] / nC - 5.0) / 2) ** 2);
      for (let c = 0; c < nC; c++) wts[c][k] = wts[c][k] / len * oct;
    }
    const keep = 1 + n / 2;
    return Array.from({ length: nC }, (_, c) => Float64Array.from(wts[(c + 3 * (nC / 12)) % nC].subarray(0, keep), Math.fround));
  });
}

// librosa.feature.chroma_stft(y, sr) from the power spectrogram; columns max-normalised. Returns { chroma, tuning }.
export function chromaStft(pow, sr = SR) {
  const n = 2 * (pow[0].length - 1), tuning = estimateTuning(pow, sr), fb = chromaFilter(sr, n, tuning);
  const chroma = pow.map(S => {
    const c = new Float64Array(fb.length);
    let mx = 0;
    for (let i = 0; i < fb.length; i++) { let s = 0; for (let k = 0; k < S.length; k++) s += fb[i][k] * S[k]; c[i] = s; mx = Math.max(mx, Math.abs(s)); }
    const len = mx < TINY ? 1.0 : mx;
    for (let i = 0; i < c.length; i++) c[i] /= len;
    return c;
  });
  return { chroma, tuning };
}

// librosa.feature.spectral_centroid and spectral_rolloff(roll_percent=0.85) on |STFT|.
export function centroidRolloff(mag, sr = SR) {
  const freq = fftFrequencies(sr, 2 * (mag[0].length - 1));
  const centroid = new Float64Array(mag.length), rolloff = new Float64Array(mag.length);
  mag.forEach((S, t) => {
    let tot = 0; for (const v of S) tot += v;
    const len = tot < TINY ? 1.0 : tot;
    let c = 0; for (let k = 0; k < S.length; k++) c += freq[k] * (S[k] / len);
    centroid[t] = c;
    const thr = 0.85 * tot;
    let cum = 0, r = NaN;
    for (let k = 0; k < S.length; k++) { cum += S[k]; if (!(cum < thr)) { r = freq[k]; break; } }
    rolloff[t] = r;
  });
  return { centroid, rolloff };
}

// librosa.feature.zero_crossing_rate(y, frame_length=2048, hop_length=512, center=True) (edge padding).
export function zeroCrossingRate(y, n = N_FFT, hop = HOP) {
  const half = n / 2, T = 1 + Math.floor(y.length / hop), out = new Float64Array(T);
  const at = j => { const v = y[Math.min(y.length - 1, Math.max(0, j))]; return Math.abs(v) <= 1e-10 ? 0 : v; };
  const neg = v => v < 0 || Object.is(v, -0);
  for (let t = 0; t < T; t++) {
    let c = 0, prev = neg(at(t * hop - half));
    for (let i = 1; i < n; i++) { const cur = neg(at(t * hop - half + i)); if (cur !== prev) c++; prev = cur; }
    out[t] = c / n;
  }
  return out;
}

// DTWComparator.extract_features for 'mfcc', 'chroma' and 'spectral' from one STFT (time x features).
// mfccTopDb: 80 (librosa default, extract_features) or config.MFCC_TOP_DB (comparison_features).
export function allFeatures(y, spec, sr = SR, mfccTopDb = 80.0) {
  const { centroid, rolloff } = centroidRolloff(spec.mag, sr), zcr = zeroCrossingRate(y);
  const { chroma, tuning } = chromaStft(spec.pow, sr);
  return {
    mfcc: mfcc(spec.pow, sr, 13, mfccTopDb), chroma, tuning,
    spectral: Array.from(centroid, (c, t) => Float64Array.of(c, rolloff[t], zcr[t])),
  };
}
