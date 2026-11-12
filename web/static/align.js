// DTW-aligned display, ported from src/alignment_utils.py and the Practice tab (src/practice_tab.py,
// src/feedback_report.py): warp the recording onto the reference timeline, path smoothness, correlation, report text.
import { HOP } from './dsp.js';

// scipy interp1d(kind='cubic') == make_interp_spline(k=3) with not-a-knot ends, on x = 0..n-1; returns f(t).
export function cubicSpline(y) {
  const n = y.length;
  if (n < 4) throw new Error('cubic interpolation needs at least 4 samples');
  const M = new Float64Array(n), r = new Float64Array(n);
  for (let i = 1; i < n - 1; i++) r[i] = 6 * (y[i + 1] - 2 * y[i] + y[i - 1]);
  // not-a-knot: M0 = 2M1 - M2 and M[n-1] = 2M[n-2] - M[n-3] turn the end rows into 6 M1 = r1, 6 M[n-2] = r[n-2]
  M[1] = r[1] / 6; M[n - 2] = r[n - 2] / 6;
  const m = n - 4;  // unknowns M[2..n-3]: M[i-1] + 4 M[i] + M[i+1] = r[i]
  if (m > 0) {
    const c = new Float64Array(m), d = new Float64Array(m);
    for (let k = 0; k < m; k++) {
      const i = k + 2;
      let rhs = r[i];
      if (k === 0) rhs -= M[1];
      if (k === m - 1) rhs -= M[n - 2];
      const den = 4 - (k > 0 ? c[k - 1] : 0);
      c[k] = 1 / den;
      d[k] = (rhs - (k > 0 ? d[k - 1] : 0)) / den;
    }
    for (let k = m - 1; k >= 0; k--) M[k + 2] = d[k] - (k < m - 1 ? c[k] * M[k + 3] : 0);
  }
  M[0] = 2 * M[1] - M[2]; M[n - 1] = 2 * M[n - 2] - M[n - 3];
  return t => {
    if (!(t >= 0 && t <= n - 1)) return 0.0;  // fill_value=0 outside
    const i = Math.min(n - 2, Math.floor(t)), a = i + 1 - t, b = t - i;
    return M[i] * a * a * a / 6 + M[i + 1] * b * b * b / 6 + (y[i] - M[i] / 6) * a + (y[i + 1] - M[i + 1] / 6) * b;
  };
}

// scipy interp1d(kind='linear', fill_value='extrapolate') for sorted x.
export function linearInterp(x, y) {
  const n = x.length;
  return v => {
    let lo = 0, hi = n;  // searchsorted(x, v, side='left')
    while (lo < hi) { const mid = (lo + hi) >> 1; if (x[mid] < v) lo = mid + 1; else hi = mid; }
    const k = Math.min(n - 1, Math.max(1, lo)), a = k - 1;
    const slope = (y[k] - y[a]) / (x[k] - x[a]);
    return slope * (v - x[a]) + y[a];
  };
}

// Least-squares quadratic over 5 points evaluated at position p (Savitzky-Golay edge fit, mode='interp').
function edgeWeights(p, n = 5) {
  const S = [0, 0, 0, 0, 0];
  for (let t = 0; t < n; t++) for (let e = 0; e < 5; e++) S[e] += t ** e;
  const A = [[S[0], S[1], S[2]], [S[1], S[2], S[3]], [S[2], S[3], S[4]]];
  const inv = (() => {  // 3x3 inverse
    const [[a, b, c], [d, e, f], [g, h, i]] = A, det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g);
    return [[e * i - f * h, c * h - b * i, b * f - c * e], [f * g - d * i, a * i - c * g, c * d - a * f], [d * h - e * g, b * g - a * h, a * e - b * d]].map(r => r.map(v => v / det));
  })();
  const q = [1, p, p * p].map((_, r) => inv[0][r] + inv[1][r] * p + inv[2][r] * p * p);
  return Array.from({ length: n }, (_, t) => q[0] + q[1] * t + q[2] * t * t);
}

// alignment_utils.smooth_warped_audio: scipy.signal.savgol_filter(audio, 5, 2) (mode='interp').
export function savgol5(x) {
  const n = x.length;
  if (n < 5) return Float64Array.from(x);
  const c = [-3 / 35, 12 / 35, 17 / 35, 12 / 35, -3 / 35], out = new Float64Array(n);
  for (let i = 2; i < n - 2; i++) out[i] = c[0] * x[i - 2] + c[1] * x[i - 1] + c[2] * x[i] + c[3] * x[i + 1] + c[4] * x[i + 2];
  for (const p of [0, 1]) { const w = edgeWeights(p); out[p] = w.reduce((s, v, t) => s + v * x[t], 0); }
  for (const p of [3, 4]) { const w = edgeWeights(p); out[n - 5 + p] = w.reduce((s, v, t) => s + v * x[n - 5 + t], 0); }
  return out;
}

// alignment_utils.apply_dtw_warping(user, ref, path, hop_length=512): path over feature frames.
export function applyDtwWarping(user, ref, path, hop = HOP) {
  const refLen = ref.length, userLen = user.length;
  let ur = [], rr = [];
  const seen = new Set();
  for (const [u, r] of path) {
    const ui = Math.min(u * hop, userLen - 1), ri = Math.min(r * hop, refLen - 1);
    if (!seen.has(ri)) { seen.add(ri); rr.push(ri); ur.push(ui); }
  }
  if (rr[0] !== 0) { rr.unshift(0); ur.unshift(0); }
  if (rr[rr.length - 1] !== refLen - 1) { rr.push(refLen - 1); ur.push(Math.min(userLen - 1, ur[ur.length - 1] + 1)); }
  const f = linearInterp(rr, ur), g = cubicSpline(user), out = new Float64Array(refLen);
  for (let i = 0; i < refLen; i++) out[i] = g(Math.min(userLen - 1, Math.max(0, f(i))));
  return savgol5(out);
}

// alignment_utils.calculate_path_smoothness: 1 / (1 + var(slopes)).
export function pathSmoothness(path) {
  if (path.length < 3) return 0.0;
  const s = [];
  for (let i = 0; i < path.length - 1; i++) { const dx = path[i + 1][0] - path[i][0], dy = path[i + 1][1] - path[i][1]; if (dx !== 0) s.push(dy / dx); }
  if (!s.length) return 0.0;
  const m = s.reduce((a, b) => a + b, 0) / s.length;
  return 1.0 / (1.0 + s.reduce((a, b) => a + (b - m) ** 2, 0) / s.length);
}

export const alignmentQuality = sm => sm > 0.5 ? 'Excellent' : sm > 0.3 ? 'Good' : sm > 0.15 ? 'Fair' : 'Poor';

// np.corrcoef(a, b)[0, 1]
export function corrcoef(a, b) {
  const n = a.length; let ma = 0, mb = 0;
  for (let i = 0; i < n; i++) { ma += a[i]; mb += b[i]; }
  ma /= n; mb /= n;
  let sab = 0, saa = 0, sbb = 0;
  for (let i = 0; i < n; i++) { const x = a[i] - ma, y = b[i] - mb; sab += x * y; saa += x * x; sbb += y * y; }
  return sab / Math.sqrt(saa * sbb);
}

// PracticeTab.display_aligned_comparison: warp the normalised recording onto the reference (fallback: pad/cut).
export function alignedComparison(userNorm, refNorm, mfccPath) {
  let aligned, quality, smoothness = null;
  try {
    aligned = applyDtwWarping(userNorm, refNorm, mfccPath);
    smoothness = pathSmoothness(mfccPath);
    quality = alignmentQuality(smoothness);
  } catch (e) {
    quality = 'Fallback';
    aligned = new Float64Array(refNorm.length);
    aligned.set(userNorm.subarray(0, Math.min(userNorm.length, refNorm.length)));
  }
  return { aligned, quality, smoothness, correlation: corrcoef(refNorm, aligned) };
}

export const scoreColour = s => s >= 85 ? 'green' : s >= 70 ? 'lightgreen' : s >= 50 ? 'orange' : 'red';

const f1 = v => v.toFixed(1), f2 = v => v.toFixed(2);
// feedback_report.practice_report
export function practiceReport(score, correlation, quality, durationRatio, results, analysis, overall) {
  const p = ['=== PRONUNCIATION ANALYSIS ===\n', `Overall: ${overall}\n`, '\nDetailed Metrics:',
    `\n  Similarity Score: ${f1(score)}/100`, `\n  Alignment Quality: ${quality}`,
    `\n  Waveform Correlation: ${f2(correlation)}`, `\n  Duration Ratio: ${f2(durationRatio)}x reference`];
  if ('mfcc_similarity' in results) p.push(`\n  Phonetic Match: ${f1(results.mfcc_similarity)}%`);
  if ('chroma_similarity' in results) p.push(`\n  Tonal Match: ${f1(results.chroma_similarity)}%`);
  if ('spectral_similarity' in results) p.push(`\n  Spectral Match: ${f1(results.spectral_similarity)}%`);
  p.push('\n\nSpecific Feedback:');
  for (const k of ['speed_feedback', 'pitch_feedback', 'volume_feedback']) p.push(`\n  ${analysis[k] ?? 'N/A'}`);
  p.push('\n\nRecommendations:');
  if (score < 85) {
    if (quality === 'Poor' || quality === 'Fallback') p.push('\n  Poor alignment - check recording quality');
    if (durationRatio > 1.2) p.push('\n  Speak slower to match reference rhythm');
    else if (durationRatio < 0.8) p.push('\n  Speak faster to match reference pace');
    if ((analysis.pitch_feedback || '').toLowerCase().includes('differs')) p.push('\n  Focus on matching pitch contour');
    if (correlation < 0.6) p.push('\n  Low correlation - pronunciation very different');
    p.push('\n  Compare the spectrograms for frequency differences');
    p.push('\n  Orange shading shows pronunciation differences');
  } else p.push('\n  Excellent work! Keep practicing to maintain this level.');
  return p.join('');
}
