// Analyse one clip: everything the desktop app extracts from audio (AudioProcessor + DTWComparator.extract_features),
// computed in the browser: waveform, spectrogram, MFCC, chroma, spectral centroid / roll-off, zero-crossing rate,
// piptrack pitch and the AudioProcessor.get_audio_features summary.
import { app, route } from './core.js';
import { HOP, SR } from './dsp.js';
import { analyseClip } from './dtw.js';
import { audioFeatures } from './summary.js';
import { clips, demoClip } from './state.js';
import { clipPanel } from './clip_panel.js';
import { heatmap, lines } from './plots.js';

const NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];

route('analyse', (args, query) => {
  if (query.demo) clips.single = demoClip('reference', false);
  app().innerHTML = `
  <section class="hero"><p class="kicker">Analyse · one clip, every feature</p>
    <h1 class="glow">What the comparison sees</h1>
    <p class="lead">Record or load a clip to see the features the DTW comparison works on, frame by frame
      (2048-sample windows every 512 samples at 44.1 kHz), computed here with a JavaScript port of the librosa routines
      the desktop app calls.</p></section>
  <div id="clip"></div><div id="feat"></div>`;
  const out = document.getElementById('feat');
  const draw = c => { out.innerHTML = '<p class="mute">Analysing...</p>'; setTimeout(() => render(out, c), 20); };
  clipPanel(document.getElementById('clip'), { slot: 'single', title: 'Clip', cls: 'you', prepareRecord: true, prepareFile: false,
    hint: 'Recordings are trimmed and normalised as in the desktop app; files are analysed as they are.', onChange: draw });
  if (clips.single) draw(clips.single);
});

function render(out, clip) {
  const a = analyseClip(clip.y), s = audioFeatures(a), T = a.frames, dur = clip.y.length / SR;
  const t = Array.from({ length: T }, (_, i) => i * HOP / SR);
  const pt = strongestPitch(a.pitch);
  out.innerHTML = `
  <section class="panel"><h2 style="margin-top:0">Summary</h2>
    <p class="small mute">AudioProcessor.get_audio_features: the numbers the desktop app reports for a clip.</p>
    <div class="tiles">
      <div class="tile"><b>${s.duration.toFixed(2)} s</b><span>duration</span></div>
      <div class="tile"><b>${s.rms_energy.toFixed(3)}</b><span>RMS energy</span></div>
      <div class="tile"><b>${Math.round(s.spectral_centroid_mean)} Hz</b><span>mean spectral centroid (sd ${Math.round(s.spectral_centroid_std)})</span></div>
      <div class="tile"><b>${s.zero_crossing_rate_mean.toFixed(3)}</b><span>mean zero-crossing rate</span></div>
      <div class="tile"><b>${Number.isNaN(a.meanPitch) ? 'n/a' : Math.round(a.meanPitch) + ' Hz'}</b><span>mean piptrack pitch (used for the pitch feedback)</span></div>
      <div class="tile"><b>${a.feats.tuning.toFixed(2)}</b><span>tuning estimate (fraction of a semitone, for chroma)</span></div>
    </div>
    <details><summary class="small">MFCC means and standard deviations</summary><div class="scroll"><table><thead><tr><th>MFCC</th>
      ${s.mfcc.map((_, i) => `<th class="n">${i + 1}</th>`).join('')}</tr></thead><tbody>
      <tr><td>mean</td>${s.mfcc.map(m => `<td class="n">${m.mean.toFixed(1)}</td>`).join('')}</tr>
      <tr><td>sd</td>${s.mfcc.map(m => `<td class="n">${m.std.toFixed(1)}</td>`).join('')}</tr></tbody></table></div></details>
  </section>
  <div class="charts">
    <div class="panel"><h3>MFCC (13 coefficients)</h3><canvas id="mf" class="plot" role="img" aria-label="MFCC heatmap"></canvas>
      <p class="small mute">Coefficient 1 (bottom) follows loudness; the higher ones describe the spectral envelope, i.e. which vowel or consonant.</p></div>
    <div class="panel"><h3>Chroma (12 pitch classes)</h3><canvas id="ch" class="plot" role="img" aria-label="Chroma heatmap"></canvas>
      <p class="small mute">Rows C (bottom) to B; each frame scaled so its strongest class is 1.</p></div>
    <div class="panel"><h3>Spectral centroid and roll-off</h3><canvas id="sc" class="plot" role="img" aria-label="Spectral centroid and roll-off"></canvas>
      <div class="legend"><span><i style="background:#ffb547"></i>centroid</span><span><i style="background:#b48cff"></i>85 % roll-off</span></div></div>
    <div class="panel"><h3>Zero-crossing rate</h3><canvas id="zc" class="plot" role="img" aria-label="Zero-crossing rate"></canvas>
      <p class="small mute">High for hissy consonants (s, f, sh), low for voiced sounds.</p></div>
    <div class="panel"><h3>Pitch (piptrack)</h3><canvas id="pp" class="plot" role="img" aria-label="Pitch track"></canvas>
      <p class="small mute">Strongest piptrack peak per frame (dots). The desktop pitch feedback compares the mean of all peaks.</p></div>
  </div>`;
  heatmap(out.querySelector('#mf'), { rows: a.feats.mfcc, x1: dur, yr: [1, 13], ylabel: 'coefficient', h: 200 });
  heatmap(out.querySelector('#ch'), { rows: a.feats.chroma, x1: dur, yr: [0, 11], ylabel: 'pitch class', h: 200, vr: [0, 1] });
  lines(out.querySelector('#sc'), { x: t, series: [{ y: a.feats.spectral.map(r => r[0]), color: '#ffb547' }, { y: a.feats.spectral.map(r => r[1]), color: '#b48cff' }], ylabel: 'Hz' });
  lines(out.querySelector('#zc'), { x: t, series: [{ y: a.feats.spectral.map(r => r[2]), color: '#3fd8ff' }], ylabel: 'rate' });
  lines(out.querySelector('#pp'), { x: t, series: [{ y: pt, color: '#ff5c8a', dots: true }], ylabel: 'Hz' });
  out.querySelector('#ch').setAttribute('aria-label', 'Chroma heatmap, rows ' + NOTES.join(' '));
}

// The strongest piptrack candidate in each frame (librosa.piptrack on |STFT|, 150-4000 Hz); NaN if none.
function strongestPitch({ pitches, mags }) {
  return pitches.map((p, t) => {
    let best = NaN, bm = 0;
    for (let f = 0; f < p.length; f++) if (p[f] > 0 && mags[t][f] > bm) { bm = mags[t][f]; best = p[f]; }
    return best;
  });
}
