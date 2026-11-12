// Practice results: run the comparison in the browser and draw it; optionally re-run it in Python (local app).
import { api, esc } from './core.js';
import { SR, normalize, spectrogramDb } from './dsp.js';
import { SCORE, analyseClip, compareClips, similarityFeedback } from './dtw.js';
import { alignedComparison, practiceReport, scoreColour } from './align.js';
import { wavBlob } from './audio_io.js';
import { clips } from './state.js';
import { dtwPath, heatmap, waveform } from './plots.js';

const analysed = new WeakMap();
const analyse = c => { if (!analysed.has(c)) analysed.set(c, analyseClip(c.y)); return analysed.get(c); };
const f = (v, d = 3) => (v == null || Number.isNaN(v) ? 'n/a' : (+v).toFixed(d));
const FEAT = {
  mfcc: ['MFCC', '13 mel-frequency cepstral coefficients (log-mel floored 40 dB below the peak): which sound'],
  chroma: ['Chroma', '12 pitch classes of the spectrum, with librosa\'s tuning estimate (tonal content)'],
  spectral: ['Spectral', 'centroid (Hz), 85 % roll-off (Hz) and zero-crossing rate per frame'],
};

export function compute(refClip = clips.reference, userClip = clips.user) {
  const ref = analyse(refClip), user = analyse(userClip);
  const cmp = compareClips(user, ref);
  const al = alignedComparison(normalize(userClip.y), normalize(refClip.y), cmp.paths.mfcc);
  const score = cmp.results.similarity_score, ratio = userClip.y.length / refClip.y.length;
  const report = practiceReport(score, al.correlation, al.quality, ratio, cmp.results, cmp.analysis, similarityFeedback(score));
  return { ref, user, cmp, al, score, ratio, report };
}

export function compareNow(host) {
  if (!clips.reference || !clips.user) return;
  host.innerHTML = '<p class="mute">Analysing...</p>';
  setTimeout(() => {
    try { render(host, compute()); } catch (e) { console.error(e); host.innerHTML = `<p class="err">${esc(e.message)}</p>`; }
  }, 20);
}

function render(host, r) {
  const { cmp, al, score } = r, a = cmp.analysis;
  host.innerHTML = `
  <section class="panel"><h2 style="margin-top:0">Result</h2>
    <div class="score"><b class="${scoreColour(score)}">${score.toFixed(1)}</b><span>/ 100 · ${esc(similarityFeedback(score))}</span></div>
    <p class="small mute">How the score is made: both clips are peak-normalised and each feature set is put on a common
      scale; DTW gives a distance per frame for each set, which becomes a 0–100 match with
      <code>100 × exp(−d / d0)</code>; the score is the weighted mean (MFCC ${SCORE.weights.mfcc}, chroma
      ${SCORE.weights.chroma}, spectral ${SCORE.weights.spectral}). d0 is set so a time-stretched or ±6 % pitch-shifted
      copy of the same synthetic voice still scores at least 70 on every feature (see About).</p>
    <div class="scroll"><table><thead><tr><th>Features</th><th class="n">DTW distance / frame</th><th class="n">match (0–100)</th><th class="n">path length</th><th>What it measures</th></tr></thead>
    <tbody>${Object.entries(FEAT).map(([k, [n, d]]) => `<tr><td>${n}</td><td class="n">${f(cmp.results['dtw_' + k])}</td><td class="n">${f(cmp.results[k + '_similarity'], 1)}</td>
      <td class="n">${cmp.paths[k].length}</td><td class="small mute">${d}</td></tr>`).join('')}</tbody></table></div>
    <h3>Pronunciation analysis</h3>
    <dl class="kv">
      <dt>Speed</dt><dd>${esc(a.speed_feedback)} (duration ratio ${f(r.ratio, 2)}×)</dd>
      <dt>Pitch</dt><dd>${esc(a.pitch_feedback ?? 'no pitch found (piptrack, 150–4000 Hz)')} · mean piptrack pitch: you ${f(cmp.meanPitch.user, 0)} Hz, reference ${f(cmp.meanPitch.ref, 0)} Hz</dd>
      <dt>Volume</dt><dd>${esc(a.volume_feedback)}</dd>
      <dt>Alignment</dt><dd>${esc(al.quality)}${al.smoothness != null ? ` (path smoothness ${f(al.smoothness)})` : ''} · waveform correlation after warping ${f(al.correlation, 2)}</dd>
    </dl>
    <h3>Report (the desktop Practice tab's text)</h3><pre>${esc(r.report)}</pre>
  </section>
  <section class="panel"><h2 style="margin-top:0">DTW-aligned comparison</h2>
    <p class="small mute">Your attempt is time-warped onto the reference timeline along the MFCC path (frame k = sample k × 512).</p>
    <div class="legend"><span><i style="background:var(--ref)"></i>reference</span><span><i style="background:var(--you)"></i>you (aligned)</span><span><i style="background:var(--diff)"></i>|difference|</span></div>
    <canvas id="ov" class="plot" role="img" aria-label="Overlaid reference and aligned attempt waveforms"></canvas>
    <div class="two"><div><canvas id="sr" class="plot" role="img" aria-label="Reference spectrogram"></canvas></div>
      <div><canvas id="su" class="plot" role="img" aria-label="Aligned attempt spectrogram"></canvas></div></div>
  </section>
  <section class="panel"><h2 style="margin-top:0">Warping path</h2>
    <p class="small mute">Distance between every frame of your attempt and every reference frame (dark = similar), with the
      fastdtw path (radius ${1}) on top. A straight diagonal means the same timing; flat or steep stretches show where you were faster or slower.</p>
    <div class="seg" role="group" aria-label="Feature set">${Object.entries(FEAT).map(([k, [n]], i) => `<button type="button" data-f="${k}" class="${i ? '' : 'on'}">${n}</button>`).join('')}</div>
    <canvas id="dp" class="plot" role="img" aria-label="DTW distance matrix and warping path"></canvas>
  </section>`;
  const refN = normalize(clips.reference.y);
  waveform(host.querySelector('#ov'), { series: [{ y: refN, color: '#3fd8ff' }, { y: al.aligned, color: '#ff5c8a' }], diff: true, ylim: [-1.2, 1.2], title: 'DTW-aligned waveforms' });
  const spec = (cv, y, title) => {
    const sp = spectrogramDb(y), kmax = sp.freqs.findIndex(v => v > 8000) - 1;
    heatmap(cv, { rows: sp.db, x1: y.length / SR, yr: [0, sp.freqs[kmax]], kmax, ylabel: 'Hz', title, h: 180 });
  };
  spec(host.querySelector('#sr'), refN, 'reference spectrogram');
  spec(host.querySelector('#su'), al.aligned, 'your spectrogram (time-warped)');
  const drawPath = k => dtwPath(host.querySelector('#dp'), { fu: r.user.feats[k], fr: r.ref.feats[k], path: cmp.paths[k], title: `${FEAT[k][0]} frame distances` });
  drawPath('mfcc');
  host.querySelectorAll('.seg button').forEach(b => b.addEventListener('click', () => {
    host.querySelectorAll('.seg button').forEach(x => x.classList.toggle('on', x === b)); drawPath(b.dataset.f);
  }));
}

// Local app only: send both clips (as analysed here, 32-bit float WAV) to POST /api/compare and compare the numbers.
export async function pythonCheck(host) {
  if (!clips.reference || !clips.user) return;
  host.innerHTML = '<p class="mute">Running the Python pipeline...</p>';
  try {
    // both sides analyse exactly the float32 samples in the WAV files
    const f32 = c => ({ ...c, y: Float64Array.from(Float32Array.from(c.y)) });
    const js = compute(f32(clips.reference), f32(clips.user)), fd = new FormData();
    fd.append('user', wavBlob(clips.user.y), 'user.wav');
    fd.append('reference', wavBlob(clips.reference.y), 'reference.wav');
    const py = await api('/compare', { body: fd });
    const rows = [['MFCC distance', js.cmp.results.dtw_mfcc, py.results.dtw_mfcc], ['Chroma distance', js.cmp.results.dtw_chroma, py.results.dtw_chroma],
      ['Spectral distance', js.cmp.results.dtw_spectral, py.results.dtw_spectral], ['Score', js.score, py.results.similarity_score],
      ['Waveform correlation', js.al.correlation, py.correlation], ['Path smoothness', js.al.smoothness, py.smoothness]];
    const rel = (a, b) => Math.abs(a - b) / Math.max(1e-12, Math.abs(b));
    host.innerHTML = `<section class="panel"><h2 style="margin-top:0">Python cross-check</h2>
      <p class="small mute">The same two clips (sent as 32-bit float WAV) through src/dtw_comparator.py,
      alignment_utils.py and feedback_report.py on this computer; the browser numbers here are recomputed from the same float32 samples.</p>
      <div class="scroll"><table><thead><tr><th>Quantity</th><th class="n">browser (JS)</th><th class="n">Python</th><th class="n">relative difference</th></tr></thead>
      <tbody>${rows.map(([n, a, b]) => `<tr><td>${n}</td><td class="n">${f(a, 6)}</td><td class="n">${f(b, 6)}</td><td class="n">${a == null || b == null ? '' : rel(a, b).toExponential(1)}</td></tr>`).join('')}
      <tr><td>Report text</td><td colspan="3" class="${js.report === py.report ? 'pass' : 'fail'}">${js.report === py.report ? 'identical' : 'differs'}</td></tr></tbody></table></div></section>`;
  } catch (e) {
    host.innerHTML = `<p class="err">${esc(e.message)}</p>`;
  }
}
