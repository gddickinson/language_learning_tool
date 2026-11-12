// Signal-processing primitives ported from the Python stack the desktop app uses (numpy / scipy / librosa 1.0):
// radix-2 FFT, scipy windows, librosa's centred STFT and scipy.signal.spectrogram. Pure functions, no DOM.
// Tested against Python in engine.test.mjs (fixture: tests/fixtures/engine_cases.json).

export const SR = 44100;       // config.SAMPLE_RATE
export const N_FFT = 2048;     // librosa default n_fft (features) and config.NFFT (spectrogram)
export const HOP = 512;        // librosa default hop_length
export const NOVERLAP = 1024;  // config.NOVERLAP

const twiddles = new Map();
function tables(n) {
  if (!twiddles.has(n)) {
    const cos = new Float64Array(n / 2), sin = new Float64Array(n / 2);
    for (let k = 0; k < n / 2; k++) { cos[k] = Math.cos(2 * Math.PI * k / n); sin[k] = Math.sin(2 * Math.PI * k / n); }
    const rev = new Uint32Array(n);
    const bits = Math.log2(n);
    for (let i = 0; i < n; i++) { let r = 0; for (let b = 0; b < bits; b++) r |= ((i >> b) & 1) << (bits - 1 - b); rev[i] = r; }
    twiddles.set(n, { cos, sin, rev });
  }
  return twiddles.get(n);
}

// In-place forward complex FFT (n a power of two).
export function fft(re, im) {
  const n = re.length;
  const { cos, sin, rev } = tables(n);
  for (let i = 0; i < n; i++) {
    const j = rev[i];
    if (j > i) { let t = re[i]; re[i] = re[j]; re[j] = t; t = im[i]; im[i] = im[j]; im[j] = t; }
  }
  for (let size = 2; size <= n; size *= 2) {
    const half = size / 2, step = n / size;
    for (let i = 0; i < n; i += size) {
      for (let k = 0; k < half; k++) {
        const wr = cos[k * step], wi = -sin[k * step];
        const a = i + k, b = a + half;
        const xr = re[b] * wr - im[b] * wi, xi = re[b] * wi + im[b] * wr;
        re[b] = re[a] - xr; im[b] = im[a] - xi; re[a] += xr; im[a] += xi;
      }
    }
  }
}

// |rfft(frame)|^2 for bins 0..n/2 (frame is overwritten-safe: copied).
export function rfftPower(frame) {
  const n = frame.length, re = Float64Array.from(frame), im = new Float64Array(n);
  fft(re, im);
  const out = new Float64Array(n / 2 + 1);
  for (let k = 0; k <= n / 2; k++) out[k] = re[k] * re[k] + im[k] * im[k];
  return out;
}

// scipy.signal.get_window('hann', n) (periodic): general_cosine with fac = linspace(-pi, pi, n + 1)[:-1].
export function hannPeriodic(n) {
  const w = new Float64Array(n), step = 2 * Math.PI / n;
  for (let i = 0; i < n; i++) w[i] = 0.5 + 0.5 * Math.cos(i * step - Math.PI);
  return w;
}

// scipy.signal.get_window(('tukey', alpha), n) (periodic: n + 1 symmetric points, last dropped).
export function tukeyPeriodic(n, alpha = 0.25) {
  const M = n + 1, w = new Float64Array(n);
  const width = Math.floor(alpha * (M - 1) / 2.0);
  for (let i = 0; i < n; i++) {
    if (i <= width) w[i] = 0.5 * (1 + Math.cos(Math.PI * (-1 + 2.0 * i / alpha / (M - 1))));
    else if (i < M - width - 1) w[i] = 1;
    else w[i] = 0.5 * (1 + Math.cos(Math.PI * (-2.0 / alpha + 1 + 2.0 * i / alpha / (M - 1))));
  }
  return w;
}

// numpy.fft.rfftfreq(n, 1/sr) == librosa.fft_frequencies
export function fftFrequencies(sr = SR, n = N_FFT) {
  const val = 1.0 / (n * (1.0 / sr)), out = new Float64Array(n / 2 + 1);
  for (let k = 0; k < out.length; k++) out[k] = k * val;
  return out;
}

export const nFrames = len => 1 + Math.floor(len / HOP);

// librosa.stft(y, n_fft=2048, hop=512, window='hann', center=True, pad_mode='constant'): returns the magnitude
// |STFT| and the power |STFT|^2 as arrays of frames (each Float64Array of n_fft/2 + 1 bins).
export function stft(y, n = N_FFT, hop = HOP) {
  const win = hannPeriodic(n), half = n / 2, T = 1 + Math.floor(y.length / hop);
  const mag = [], pow = [];
  const frame = new Float64Array(n);
  for (let t = 0; t < T; t++) {
    const start = t * hop - half;
    for (let i = 0; i < n; i++) {
      const j = start + i;
      frame[i] = j >= 0 && j < y.length ? y[j] * win[i] : 0;
    }
    const p = rfftPower(frame);
    const m = new Float64Array(p.length);
    for (let k = 0; k < p.length; k++) m[k] = Math.sqrt(p[k]);
    const p2 = new Float64Array(p.length);
    for (let k = 0; k < p.length; k++) p2[k] = m[k] * m[k];
    mag.push(m); pow.push(p2);
  }
  return { mag, pow };
}

// scipy.signal.spectrogram(y, fs, nperseg=NFFT, noverlap=NOVERLAP, scaling='density') then 10*log10(S + 1e-10),
// as AudioProcessor.get_spectrogram. Returns { freqs, times, db } with db[segment][bin].
export function spectrogramDb(y, fs = SR, nperseg = N_FFT, noverlap = NOVERLAP) {
  if (y.length < nperseg) return { freqs: fftFrequencies(fs, nperseg), times: new Float64Array(0), db: [] };
  const step = nperseg - noverlap, nseg = Math.floor((y.length - noverlap) / step);
  const win = tukeyPeriodic(nperseg, 0.25);
  let s2 = 0; for (const v of win) s2 += v * v;
  const scale = 1.0 / (fs * s2);
  const times = new Float64Array(nseg), db = [];
  const frame = new Float64Array(nperseg);
  for (let s = 0; s < nseg; s++) {
    const off = s * step;
    let mean = 0; for (let i = 0; i < nperseg; i++) mean += y[off + i];
    mean /= nperseg;
    for (let i = 0; i < nperseg; i++) frame[i] = (y[off + i] - mean) * win[i];
    const p = rfftPower(frame), row = new Float64Array(p.length);
    for (let k = 0; k < p.length; k++) {
      let v = p[k] * scale;
      if (k > 0 && k < p.length - 1) v *= 2;
      row[k] = 10 * Math.log10(v + 1e-10);
    }
    db.push(row);
    times[s] = (nperseg / 2 + s * step) / fs;
  }
  return { freqs: fftFrequencies(fs, nperseg), times, db };
}

// AudioProcessor.normalize_audio: divide by the peak absolute value (unchanged if silent).
export function normalize(y) {
  let m = 0; for (const v of y) m = Math.max(m, Math.abs(v));
  if (!(m > 0)) return Float64Array.from(y);
  const out = new Float64Array(y.length);
  for (let i = 0; i < y.length; i++) out[i] = y[i] / m;
  return out;
}

// AudioProcessor.trim_silence(threshold_db=-40) == librosa.effects.trim(y, top_db=40): frame RMS (2048/512,
// centred, zero padded) in dB relative to the loudest frame; keeps whole hops from the first to the last frame
// above -top_db. Returns { audio, start, end }.
export function trimSilence(y, topDb = 40, n = N_FFT, hop = HOP) {
  const half = n / 2, T = 1 + Math.floor(y.length / hop), rms = new Float64Array(T);
  for (let t = 0; t < T; t++) {
    let s = 0;
    for (let i = 0; i < n; i++) { const j = t * hop - half + i; if (j >= 0 && j < y.length) s += y[j] * y[j]; }
    rms[t] = Math.fround(Math.sqrt(s / n));  // librosa.feature.rms computes in float32
  }
  let ref = 0; for (const v of rms) ref = Math.max(ref, v);
  const refDb = 10 * Math.log10(Math.max(1e-10, ref * ref));
  let first = -1, last = -1;
  for (let t = 0; t < T; t++) {
    const db = 10 * Math.log10(Math.max(1e-10, rms[t] * rms[t])) - refDb;
    if (db > -topDb) { if (first < 0) first = t; last = t; }
  }
  if (first < 0) return { audio: new Float64Array(0), start: 0, end: 0 };
  const start = first * hop, end = Math.min(y.length, (last + 1) * hop);
  return { audio: y.slice(start, end), start, end };
}
