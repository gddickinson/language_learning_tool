// DTW comparison, ported from src/dtw_comparator.py (DTWComparator) and the fastdtw 0.3.4 package it calls
// (pure-Python algorithm, same tie-breaking). Distances between frames are Euclidean (scipy.spatial.distance).
import { SR, normalize, stft, nFrames } from './dsp.js';
import { allFeatures, piptrack } from './features.js';

export const DTW_RADIUS = 1;  // config.DTW_RADIUS
// Similarity score settings: config.MFCC_TOP_DB, MFCC_SCALE_DB, SCORE_D0, SCORE_WEIGHTS (see config.py for the
// rationale; scripts/calibrate_score.py derives SCORE_D0). engine.test.mjs checks these equal the Python values.
export const SCORE = { mfccTopDb: 40.0, mfccScaleDb: 10.0, d0: { mfcc: 0.71, chroma: 0.15, spectral: 0.023 },
  weights: { mfcc: 0.5, chroma: 0.3, spectral: 0.2 } };

export function euclidean(a, b) {
  let s = 0; for (let i = 0; i < a.length; i++) { const d = a[i] - b[i]; s += d * d; }
  return Math.sqrt(s);
}

// fastdtw.dtw restricted to a window (list of [i, j]); window null = full matrix. Returns [distance, path].
function dtwWindow(x, y, window, dist) {
  const lx = x.length, ly = y.length, W = ly + 1;
  const cost = new Map(), from = new Map();
  cost.set(0, 0);
  const get = k => (cost.has(k) ? cost.get(k) : Infinity);
  const cells = window || (function* () { for (let i = 0; i < lx; i++) for (let j = 0; j < ly; j++) yield [i, j]; })();
  for (const [i0, j0] of cells) {
    const i = i0 + 1, j = j0 + 1, dt = dist(x[i - 1], y[j - 1]);
    // min((D[i-1,j]+dt, ...), (D[i,j-1]+dt, ...), (D[i-1,j-1]+dt, ...)): first minimum wins
    const c = [[get((i - 1) * W + j) + dt, i - 1, j], [get(i * W + j - 1) + dt, i, j - 1], [get((i - 1) * W + j - 1) + dt, i - 1, j - 1]];
    let best = c[0];
    if (c[1][0] < best[0]) best = c[1];
    if (c[2][0] < best[0]) best = c[2];
    cost.set(i * W + j, best[0]); from.set(i * W + j, [best[1], best[2]]);
  }
  const path = [];
  let i = lx, j = ly;
  while (!(i === 0 && j === 0)) {
    path.push([i - 1, j - 1]);
    const f = from.get(i * W + j);
    if (!f) throw new Error('DTW path broken');
    [i, j] = f;
  }
  path.reverse();
  return [get(lx * W + ly), path];
}

const reduceByHalf = x => {
  const out = [];
  for (let i = 0; i < x.length - (x.length % 2); i += 2) out.push(Float64Array.from(x[i], (v, k) => (v + x[i + 1][k]) / 2));
  return out;
};

function expandWindow(path, lx, ly, radius) {
  const K = 2 * ly + 4 * radius + 8, key = (a, b) => (a + 2 * radius + 4) * K + (b + 2 * radius + 4);
  const near = [];
  const seen = new Set();
  for (const [i, j] of path) for (let a = -radius; a <= radius; a++) for (let b = -radius; b <= radius; b++) {
    const k = key(i + a, j + b);
    if (!seen.has(k)) { seen.add(k); near.push([i + a, j + b]); }
  }
  const win = new Set();
  for (const [i, j] of near) for (const [a, b] of [[i * 2, j * 2], [i * 2, j * 2 + 1], [i * 2 + 1, j * 2], [i * 2 + 1, j * 2 + 1]]) win.add(key(a, b));
  const window = [];
  let startJ = 0;
  for (let i = 0; i < lx; i++) {
    let newStart = null;
    if (startJ === null) throw new Error('fastdtw window has an empty row');
    for (let j = startJ; j < ly; j++) {
      if (win.has(key(i, j))) { window.push([i, j]); if (newStart === null) newStart = j; }
      else if (newStart !== null) break;
    }
    startJ = newStart;
  }
  return window;
}

// fastdtw.fastdtw(x, y, radius, dist): approximate DTW. x, y are arrays of feature vectors.
export function fastdtw(x, y, radius = DTW_RADIUS, dist = euclidean) {
  const minSize = radius + 2;
  if (x.length < minSize || y.length < minSize) return dtwWindow(x, y, null, dist);
  const [, p] = fastdtw(reduceByHalf(x), reduceByHalf(y), radius, dist);
  return dtwWindow(x, y, expandWindow(p, x.length, y.length, radius), dist);
}

// DTWComparator.compare_dtw on precomputed features: distance normalised by path length.
export function compareFeatures(f1, f2, radius = DTW_RADIUS) {
  const [d, path] = fastdtw(f1, f2, radius);
  return { distance: d / path.length, path };
}

// DTWComparator.comparison_features: peak-normalised audio, MFCC floored SCORE.mfccTopDb below the peak in units of
// SCORE.mfccScaleDb, centroid / roll-off as fractions of Nyquist, every frame divided by sqrt(number of coefficients).
export function comparisonFeatures(y, sr = SR) {
  const yn = normalize(y), f = allFeatures(yn, stft(yn), sr, SCORE.mfccTopDb);
  const scale = (rows, fn) => rows.map(r => { const k = Math.sqrt(r.length); return Float64Array.from(r, (v, i) => fn(v, i) / k); });
  return {
    mfcc: scale(f.mfcc, v => v / SCORE.mfccScaleDb),
    chroma: scale(f.chroma, v => v),
    spectral: scale(f.spectral, (v, i) => (i < 2 ? v / (sr / 2) : v)),
  };
}

// Everything DTWComparator computes for one clip (raw features from one STFT, the comparison features, and
// piptrack for the pitch check).
export function analyseClip(y, sr = SR) {
  const spec = stft(y);
  const feats = allFeatures(y, spec, sr), cmpFeats = comparisonFeatures(y, sr);
  const pitch = piptrack(spec.mag, sr), { pitches } = pitch;
  let s = 0, n = 0;
  for (const row of pitches) for (const v of row) if (v > 0) { s += v; n++; }
  let e = 0; for (const v of y) e += v * v;
  return { y, length: y.length, frames: nFrames(y.length), feats, cmpFeats, spec, pitch, meanPitch: n ? s / n : NaN, rms: Math.sqrt(e / y.length) };
}

// DTWComparator.get_similarity_feedback
export function similarityFeedback(score) {
  if (score >= 90) return 'Excellent! Your pronunciation is very accurate.';
  if (score >= 75) return 'Good! Your pronunciation is quite close to the target.';
  if (score >= 60) return 'Fair. Your pronunciation has some similarities, keep practicing.';
  if (score >= 40) return 'Needs improvement. Try to match the rhythm and intonation.';
  return 'Significant differences detected. Listen carefully and try again.';
}

// DTWComparator.compare_multiple_features(user, ref) + analyze_pronunciation_errors(user, ref) on analysed clips.
export function compareClips(user, ref) {
  const r = {}, paths = {};
  let overall = 0, wsum = 0;
  for (const ft of ['mfcc', 'chroma', 'spectral']) {
    const { distance, path } = compareFeatures(user.cmpFeats[ft], ref.cmpFeats[ft]);
    r[`dtw_${ft}`] = distance; paths[ft] = path;
    r[`${ft}_similarity`] = 100.0 * Math.exp(-distance / SCORE.d0[ft]);
    overall += SCORE.weights[ft] * r[`${ft}_similarity`];
  }
  for (const ft of ['mfcc', 'chroma', 'spectral']) wsum += SCORE.weights[ft];
  const score = overall / wsum;
  const results = { ...r, similarity_score: score, duration_ratio: user.length / ref.length, is_similar: score > 70 };

  const analysis = {};
  const speed = user.length / ref.length;
  analysis.speed_feedback = speed > 1.2 ? "You're speaking too slowly" : speed < 0.8 ? "You're speaking too fast" : 'Good speaking speed';
  if (!Number.isNaN(user.meanPitch) && !Number.isNaN(ref.meanPitch)) {
    const diff = Math.abs(user.meanPitch - ref.meanPitch) / ref.meanPitch;
    analysis.pitch_feedback = diff > 0.2 ? 'Pitch/tone differs significantly' : 'Good pitch/tone';
  }
  const er = user.rms / ref.rms;
  analysis.volume_feedback = er > 1.5 ? "You're speaking too loudly" : er < 0.6 ? "You're speaking too softly" : 'Good volume';
  analysis.similarity_score = score;
  analysis.feedback = similarityFeedback(score);
  return { results, analysis, paths, distance: r.dtw_mfcc, meanPitch: { user: user.meanPitch, ref: ref.meanPitch } };
}
