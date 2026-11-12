// Node test: the JS engine (dsp, features, dtw, align, synth) reproduces the repo's Python pipeline on synthetic
// signals (tests/fixtures/engine_cases.json, written by scripts/make_engine_fixture.py). Run: node web/static/engine.test.mjs
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { normalize, spectrogramDb, stft, trimSilence } from './dsp.js';
import { estimateTuning } from './features.js';
import { SCORE, analyseClip, compareClips, similarityFeedback } from './dtw.js';
import { alignedComparison, practiceReport } from './align.js';
import { PRESETS, synth } from './synth.js';
import { audioFeatures } from './summary.js';

const fx = JSON.parse(readFileSync(new URL('../../tests/fixtures/engine_cases.json', import.meta.url), 'utf8'));
let checks = 0, worst = 0;
const close = (a, b, what, rtol = 1e-7, atol = 1e-9) => {
  const err = Math.abs(a - b), lim = atol + rtol * Math.abs(b);
  assert.ok(err <= lim, `${what}: JS ${a} vs Python ${b}`);
  worst = Math.max(worst, err / Math.max(1e-300, Math.abs(b) + atol)); checks++;
};
const closeMat = (A, B, what, rtol, atol) => {
  assert.equal(A.length, B.length, `${what}: frame count`);
  A.forEach((row, t) => { assert.equal(row.length, B[t].length, `${what}[${t}] length`); row.forEach((v, k) => close(v, B[t][k], `${what}[${t}][${k}]`, rtol, atol)); });
};

assert.deepEqual(SCORE, { mfccTopDb: fx.score.mfcc_top_db, mfccScaleDb: fx.score.mfcc_scale_db, d0: fx.score.d0, weights: fx.score.weights },
  'dtw.js SCORE constants equal src/config.py');
const sig = Object.fromEntries(Object.entries(PRESETS).map(([k, p]) => [k, synth(p)]));
const clips = {};
for (const [name, py] of Object.entries(fx.clips)) {
  const y = sig[name];
  assert.equal(y.length, py.n, `${name} length`);
  py.head.forEach((v, i) => close(y[i], v, `${name} sample ${i}`, 1e-12, 1e-15));
  const c = clips[name] = analyseClip(y);
  closeMat(c.feats.mfcc, py.mfcc, `${name} mfcc`, 1e-7, 1e-7);
  closeMat(c.feats.chroma, py.chroma, `${name} chroma`, 1e-7, 1e-9);
  closeMat(c.feats.spectral, py.spectral, `${name} spectral`, 1e-7, 1e-9);
  for (const ft of ['mfcc', 'chroma', 'spectral']) closeMat(c.cmpFeats[ft], py.comparison[ft], `${name} comparison ${ft}`, 1e-7, 1e-9);
  close(c.feats.tuning, py.tuning, `${name} tuning`, 0, 1e-12);
  close(estimateTuning(stft(y).pow), py.tuning, `${name} estimateTuning`, 0, 1e-12);
  close(c.meanPitch, py.mean_pitch, `${name} mean pitch`, 1e-9);
  const af = audioFeatures(c);
  for (const [k, v] of Object.entries(py.audio_features)) {
    const m = k.match(/^mfcc_(\d+)_(mean|std)$/);
    close(m ? af.mfcc[m[1] - 1][m[2]] : af[k], v, `${name} get_audio_features ${k}`, 1e-7, 1e-9);
  }
  const sp = spectrogramDb(y);
  assert.deepEqual([sp.db[0].length, sp.db.length], py.spectrogram.shape, `${name} spectrogram shape`);
  py.spectrogram.times.forEach((v, i) => close(sp.times[i], v, `${name} spec time ${i}`, 1e-12));
  py.spectrogram.rows.forEach((row, r) => row.forEach((v, s) => close(sp.db[s][r * 64], v, `${name} spec dB [${r * 64}][${s}]`, 1e-7, 1e-6)));
}

// trim_silence (librosa.effects.trim, top_db=40)
const tr = trimSilence(sig.padded);
assert.deepEqual([tr.start, tr.end, tr.audio.length], [fx.trim.start, fx.trim.end, fx.trim.n_out], 'trim bounds');
checks++;

for (const [user, py] of Object.entries(fx.pairs)) {
  const cmp = compareClips(clips[user], clips.reference);
  for (const ft of ['mfcc', 'chroma', 'spectral']) {
    assert.deepEqual(cmp.paths[ft], py.paths[ft], `${user} ${ft} DTW path`); checks++;
    close(cmp.results[`dtw_${ft}`], py.results[`dtw_${ft}`], `${user} dtw_${ft}`, 1e-7, 1e-9);
    close(cmp.results[`${ft}_similarity`], py.results[`${ft}_similarity`], `${user} ${ft}_similarity`, 1e-7, 1e-9);
  }
  close(cmp.results.similarity_score, py.results.similarity_score, `${user} score`, 1e-7, 1e-9);
  assert.deepEqual(Object.keys(cmp.results).sort(), Object.keys(py.results).sort(), `${user} result keys`);
  close(cmp.results.duration_ratio, py.results.duration_ratio, `${user} duration ratio`, 1e-12);
  assert.equal(cmp.results.is_similar, py.results.is_similar);
  for (const [k, v] of Object.entries(py.analysis)) {
    if (typeof v === 'string') assert.equal(cmp.analysis[k], v, `${user} ${k}`); else close(cmp.analysis[k], v, `${user} ${k}`, 1e-9, 1e-9);
    checks++;
  }
  assert.deepEqual(Object.keys(cmp.analysis).sort(), Object.keys(py.analysis).sort());
  const al = alignedComparison(normalize(sig[user]), normalize(sig.reference), cmp.paths.mfcc);
  close(al.smoothness, py.smoothness, `${user} smoothness`, 1e-12);
  close(al.correlation, py.correlation, `${user} correlation`, 1e-8, 1e-10);
  py.warped_every_97.forEach((v, i) => close(al.aligned[i * 97], v, `${user} warped[${i * 97}]`, 1e-7, 1e-9));
  const rep = practiceReport(cmp.results.similarity_score, al.correlation, al.quality, sig[user].length / sig.reference.length,
    cmp.results, cmp.analysis, similarityFeedback(cmp.results.similarity_score));
  assert.equal(rep, py.report, `${user} report text`); checks++;
}

assert.equal(similarityFeedback(80).split('!')[0], 'Good');
console.log(`engine.test.mjs: ${checks} checks passed (max relative error ${worst.toExponential(1)})`);
