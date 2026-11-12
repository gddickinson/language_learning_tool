// Canvas plots: waveforms (with the desktop app's orange |difference| band), spectrogram / feature heatmaps in a
// viridis-like colour map, line charts and the DTW path over the frame distance matrix.
const VIRIDIS = [[68, 1, 84], [72, 40, 120], [62, 74, 137], [49, 104, 142], [38, 130, 142], [31, 158, 137],
  [53, 183, 121], [109, 205, 89], [180, 222, 44], [253, 231, 37]];
export function viridis(v) {
  const x = Math.max(0, Math.min(1, v)) * (VIRIDIS.length - 1), i = Math.min(VIRIDIS.length - 2, Math.floor(x)), f = x - i;
  return VIRIDIS[i].map((c, k) => Math.round(c + f * (VIRIDIS[i + 1][k] - c)));
}
const INK = '#94a3c6', LINE = '#212c4c';
const M = { l: 52, r: 10, t: 22, b: 30 };

function setup(canvas, h = 220) {
  const w = Math.max(280, Math.round(canvas.parentElement?.clientWidth || 600));
  const dpr = window.devicePixelRatio || 1;
  canvas.width = w * dpr; canvas.height = h * dpr;
  canvas.style.aspectRatio = `${w} / ${h}`;
  const g = canvas.getContext('2d');
  g.setTransform(dpr, 0, 0, dpr, 0, 0);
  g.clearRect(0, 0, w, h);
  g.font = '11px ui-monospace, Menlo, monospace';
  return { g, w, h, x0: M.l, y0: M.t, pw: w - M.l - M.r, ph: h - M.t - M.b };
}

const nice = (lo, hi, n = 5) => {
  const span = hi - lo || 1, step0 = span / n, p = 10 ** Math.floor(Math.log10(step0));
  const step = [1, 2, 2.5, 5, 10].map(m => m * p).find(s => s >= step0) || step0;
  const out = []; for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9 * span; v += step) out.push(+v.toFixed(10));
  return out;
};
const fmt = v => Math.abs(v) >= 1000 ? (v / 1000) + 'k' : String(+v.toPrecision(3));

function axes(b, { xr, yr, xlabel = '', ylabel = '', title = '' }) {
  const { g, x0, y0, pw, ph } = b;
  g.strokeStyle = LINE; g.fillStyle = INK; g.lineWidth = 1;
  g.strokeRect(x0 + 0.5, y0 + 0.5, pw, ph);
  g.textAlign = 'center'; g.textBaseline = 'top';
  for (const v of nice(xr[0], xr[1])) {
    const x = x0 + (v - xr[0]) / (xr[1] - xr[0]) * pw;
    g.fillRect(x, y0 + ph, 1, 4); g.fillText(fmt(v), x, y0 + ph + 5);
  }
  g.textAlign = 'right'; g.textBaseline = 'middle';
  for (const v of nice(yr[0], yr[1], 4)) {
    const y = y0 + ph - (v - yr[0]) / (yr[1] - yr[0]) * ph;
    g.fillRect(x0 - 4, y, 4, 1); g.fillText(fmt(v), x0 - 6, y);
  }
  g.textAlign = 'right'; g.textBaseline = 'bottom';
  if (xlabel) g.fillText(xlabel, x0 + pw, b.h - 1);
  g.save(); g.translate(11, y0 + ph / 2); g.rotate(-Math.PI / 2); g.textAlign = 'center'; g.textBaseline = 'middle';
  if (ylabel) g.fillText(ylabel, 0, 0);
  g.restore();
  g.textAlign = 'left'; g.textBaseline = 'bottom'; g.fillStyle = '#c6d4ee';
  if (title) g.fillText(title, x0, y0 - 5);
}

// Min/max envelope of y over each pixel column.
function envelope(y, cols) {
  const lo = new Float64Array(cols), hi = new Float64Array(cols), per = y.length / cols;
  for (let c = 0; c < cols; c++) {
    const a = Math.floor(c * per), z = Math.max(a + 1, Math.floor((c + 1) * per));
    let mn = Infinity, mx = -Infinity;
    for (let i = a; i < z && i < y.length; i++) { if (y[i] < mn) mn = y[i]; if (y[i] > mx) mx = y[i]; }
    lo[c] = mn === Infinity ? 0 : mn; hi[c] = mx === -Infinity ? 0 : mx;
  }
  return { lo, hi };
}

// series: [{ y, color }] sharing one sample rate; diff: shade +-|a - b| of the first two (desktop: orange band).
export function waveform(canvas, { series, sr = 44100, title = '', diff = false, ylim = null, h = 200 }) {
  const b = setup(canvas, h), { g, x0, y0, pw, ph } = b;
  const n = Math.max(...series.map(s => s.y.length));
  let yr = ylim;
  if (!yr) { let m = 0; for (const s of series) for (const v of s.y) m = Math.max(m, Math.abs(v)); m = m || 1; yr = [-1.1 * m, 1.1 * m]; }
  axes(b, { xr: [0, n / sr], yr, xlabel: 'time (s)', ylabel: 'amplitude', title });
  const Y = v => y0 + ph - (v - yr[0]) / (yr[1] - yr[0]) * ph;
  const cols = Math.max(1, Math.floor(pw));
  g.save(); g.beginPath(); g.rect(x0, y0, pw, ph); g.clip();
  if (diff && series.length >= 2) {
    const a = series[0].y, c = series[1].y, d = Float64Array.from(a, (v, i) => Math.abs(v - (c[i] ?? 0)));
    const { hi } = envelope(d, cols);
    g.fillStyle = 'rgba(255,181,71,.25)';
    for (let k = 0; k < cols; k++) g.fillRect(x0 + k, Y(hi[k]), 1, Math.max(1, Y(-hi[k]) - Y(hi[k])));
  }
  for (const s of series) {
    const sc = Math.floor(cols * s.y.length / n), { lo, hi } = envelope(s.y, Math.max(1, sc));
    g.fillStyle = s.color; g.globalAlpha = series.length > 1 ? 0.75 : 1;
    for (let k = 0; k < lo.length; k++) g.fillRect(x0 + k, Y(hi[k]), 1, Math.max(1, Y(lo[k]) - Y(hi[k])));
  }
  g.restore();
}

// rows[t][k] (time-major), shown with k upwards. kmax limits rows (e.g. bins <= 8000 Hz); yr is the y-axis range.
export function heatmap(canvas, { rows, x1, yr, kmin = 0, kmax = null, title = '', ylabel = '', xlabel = 'time (s)', h = 200, vr = null }) {
  const b = setup(canvas, h), { g, x0, y0, pw, ph } = b;
  if (!rows.length) { axes(b, { xr: [0, 1], yr: [0, 1], title: title + ' (too short)' }); return; }
  const K = (kmax ?? rows[0].length - 1) - kmin + 1, T = rows.length;
  let lo = Infinity, hi = -Infinity;
  if (vr) [lo, hi] = vr; else for (const r of rows) for (let k = kmin; k < kmin + K; k++) { lo = Math.min(lo, r[k]); hi = Math.max(hi, r[k]); }
  const img = document.createElement('canvas'); img.width = T; img.height = K;
  const ig = img.getContext('2d'), data = ig.createImageData(T, K);
  for (let t = 0; t < T; t++) for (let k = 0; k < K; k++) {
    const [r, gg, bb] = viridis((rows[t][kmin + k] - lo) / (hi - lo || 1)), o = 4 * ((K - 1 - k) * T + t);
    data.data[o] = r; data.data[o + 1] = gg; data.data[o + 2] = bb; data.data[o + 3] = 255;
  }
  ig.putImageData(data, 0, 0);
  g.imageSmoothingEnabled = K < 60 ? false : true;
  g.drawImage(img, x0, y0, pw, ph);
  axes(b, { xr: [0, x1], yr, xlabel, ylabel, title });
}

// Line chart: x array, series [{ y, color, dots }].
export function lines(canvas, { x, series, title = '', ylabel = '', xlabel = 'time (s)', h = 180, yr = null }) {
  const b = setup(canvas, h), { g, x0, y0, pw, ph } = b;
  let lo = Infinity, hi = -Infinity;
  for (const s of series) for (const v of s.y) if (Number.isFinite(v)) { lo = Math.min(lo, v); hi = Math.max(hi, v); }
  if (!Number.isFinite(lo)) { lo = 0; hi = 1; }
  if (hi === lo) hi = lo + 1;
  const r = yr || [lo - 0.05 * (hi - lo), hi + 0.05 * (hi - lo)], xr = [x[0] ?? 0, x[x.length - 1] || 1];
  axes(b, { xr, yr: r, xlabel, ylabel, title });
  const X = v => x0 + (v - xr[0]) / (xr[1] - xr[0] || 1) * pw, Y = v => y0 + ph - (v - r[0]) / (r[1] - r[0]) * ph;
  g.save(); g.beginPath(); g.rect(x0, y0, pw, ph); g.clip();
  for (const s of series) {
    g.strokeStyle = g.fillStyle = s.color; g.lineWidth = 1.4;
    if (s.dots) { s.y.forEach((v, i) => Number.isFinite(v) && g.fillRect(X(x[i]) - 1, Y(v) - 1, 2.5, 2.5)); continue; }
    g.beginPath(); let pen = false;
    s.y.forEach((v, i) => { if (!Number.isFinite(v)) { pen = false; return; } pen ? g.lineTo(X(x[i]), Y(v)) : g.moveTo(X(x[i]), Y(v)); pen = true; });
    g.stroke();
  }
  g.restore();
}

// DTW: Euclidean distance between every user frame (x) and reference frame (y), with the fastdtw path on top.
export function dtwPath(canvas, { fu, fr, path, title = '', h = 260 }) {
  const rows = fu.map(a => Float64Array.from(fr, b => { let s = 0; for (let k = 0; k < a.length; k++) s += (a[k] - b[k]) ** 2; return Math.sqrt(s); }));
  const hop = 512 / 44100;
  heatmap(canvas, { rows, x1: fu.length * hop, yr: [0, fr.length * hop], title, ylabel: 'reference (s)', xlabel: 'your recording (s)', h });
  const b = { x0: M.l, y0: M.t }, w = canvas.width / (window.devicePixelRatio || 1);
  const pw = w - M.l - M.r, ph = h - M.t - M.b, g = canvas.getContext('2d');
  g.strokeStyle = '#ff5c8a'; g.lineWidth = 2; g.beginPath();
  path.forEach(([i, j], n) => {
    const x = b.x0 + (i + 0.5) / fu.length * pw, y = b.y0 + ph - (j + 0.5) / fr.length * ph;
    n ? g.lineTo(x, y) : g.moveTo(x, y);
  });
  g.stroke();
}
