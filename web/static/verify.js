// Verify: run the browser engine on the synthetic test signals and compare with the Python pipeline's results
// (tests/fixtures/engine_cases.json, served as /verify). Same checks as engine.test.mjs, shown as a table.
import { api, app, esc, route } from './core.js';
import { normalize, spectrogramDb, trimSilence } from './dsp.js';
import { analyseClip, compareClips, similarityFeedback } from './dtw.js';
import { alignedComparison, practiceReport } from './align.js';
import { audioFeatures } from './summary.js';
import { PRESETS, synth } from './synth.js';

function run(fx) {
  const rows = [], add = (what, js, py, tol) => {
    const a = [].concat(js).map(Number), b = [].concat(py).map(Number);
    let worst = a.length === b.length ? 0 : Infinity;
    if (a.length === b.length) a.forEach((v, i) => { worst = Math.max(worst, Math.abs(v - b[i]) / Math.max(1e-9, Math.abs(b[i]))); });
    rows.push({ what, n: b.length, worst, ok: worst <= tol });
  };
  const exact = (what, ok, n = 1) => rows.push({ what, n, worst: ok ? 0 : Infinity, ok, exact: true });
  const sig = Object.fromEntries(Object.entries(PRESETS).map(([k, p]) => [k, synth(p)]));
  const clips = {};
  for (const [name, py] of Object.entries(fx.clips)) {
    const c = clips[name] = analyseClip(sig[name]);
    add(`${name}: MFCC`, c.feats.mfcc.flatMap(r => [...r]), py.mfcc.flat(), 1e-6);
    add(`${name}: chroma (tuning ${py.tuning.toFixed(2)})`, c.feats.chroma.flatMap(r => [...r]), py.chroma.flat(), 1e-6);
    add(`${name}: spectral centroid / roll-off / ZCR`, c.feats.spectral.flatMap(r => [...r]), py.spectral.flat(), 1e-6);
    const af = audioFeatures(c);
    add(`${name}: get_audio_features`, Object.keys(py.audio_features).map(k => { const m = k.match(/^mfcc_(\d+)_(mean|std)$/); return m ? af.mfcc[m[1] - 1][m[2]] : af[k]; }), Object.values(py.audio_features), 1e-6);
    const sp = spectrogramDb(sig[name]);
    add(`${name}: spectrogram (every 64th bin, dB)`, py.spectrogram.rows.flatMap((row, r) => row.map((_, s) => sp.db[s][r * 64])), py.spectrogram.rows.flat(), 1e-6);
    add(`${name}: mean piptrack pitch`, c.meanPitch, py.mean_pitch, 1e-9);
  }
  const tr = trimSilence(sig.padded);
  exact('trim_silence bounds (top_db 40)', tr.start === fx.trim.start && tr.end === fx.trim.end);
  for (const [user, py] of Object.entries(fx.pairs)) {
    const cmp = compareClips(clips[user], clips.reference);
    for (const ft of ['mfcc', 'chroma', 'spectral']) {
      exact(`${user} vs reference: ${ft} DTW path`, JSON.stringify(cmp.paths[ft]) === JSON.stringify(py.paths[ft]), py.paths[ft].length);
      add(`${user} vs reference: ${ft} DTW distance`, cmp.results[`dtw_${ft}`], py.results[`dtw_${ft}`], 1e-6);
    }
    exact(`${user} vs reference: speed / pitch / volume feedback`, ['speed_feedback', 'pitch_feedback', 'volume_feedback'].every(k => cmp.analysis[k] === py.analysis[k]), 3);
    const al = alignedComparison(normalize(sig[user]), normalize(sig.reference), cmp.paths.mfcc);
    add(`${user} vs reference: DTW-warped waveform (every 97th sample)`, py.warped_every_97.map((_, i) => al.aligned[i * 97]), py.warped_every_97, 1e-6);
    add(`${user} vs reference: correlation, smoothness`, [al.correlation, al.smoothness], [py.correlation, py.smoothness], 1e-6);
    const s = cmp.results.similarity_score;
    exact(`${user} vs reference: report text`, practiceReport(s, al.correlation, al.quality, sig[user].length / sig.reference.length, cmp.results, cmp.analysis, similarityFeedback(s)) === py.report);
  }
  return rows;
}

route('verify', async () => {
  app().innerHTML = `<section class="hero"><p class="kicker">Verify · JavaScript against Python</p><h1 class="glow">Does the browser agree with Python?</h1>
    <p class="lead">Four synthetic signals (harmonic tones with a gliding pitch, syllable-like loudness and seeded noise;
    not speech) were run through the repo's Python code (librosa ${'<span id="lv"></span>'}, fastdtw, scipy). The same signals are
    generated and analysed here, now, by the browser engine.</p></section><div id="res"><p class="mute">Running...</p></div>`;
  const fx = await api('/verify');
  document.getElementById('lv').textContent = fx.versions.librosa;
  await new Promise(r => setTimeout(r, 20));
  const t0 = performance.now(), rows = run(fx), ms = performance.now() - t0, ok = rows.every(r => r.ok);
  document.getElementById('res').innerHTML = `<p class="${ok ? 'ok' : 'err'}"><b>${ok ? 'All checks agree' : 'Some checks differ'}</b>
    · ${rows.reduce((a, r) => a + r.n, 0).toLocaleString()} values in ${rows.length} groups · ${ms.toFixed(0)} ms in this browser</p>
    <div class="scroll"><table><thead><tr><th>Quantity</th><th class="n">values</th><th class="n">largest relative difference</th><th>result</th></tr></thead><tbody>
    ${rows.map(r => `<tr><td>${esc(r.what)}</td><td class="n">${r.n}</td><td class="n">${r.exact ? (r.ok ? 'identical' : 'differs') : r.worst.toExponential(1)}</td>
      <td class="${r.ok ? 'pass' : 'fail'}">${r.ok ? 'pass' : 'FAIL'}</td></tr>`).join('')}</tbody></table></div>
    <p class="small mute">Tolerance 1e-6 relative; paths, feedback and report text must be identical. The same comparison
      runs in CI (<code>web/static/engine.test.mjs</code>, tolerance 1e-7).</p>`;
});
