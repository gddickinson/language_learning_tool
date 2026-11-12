// A clip slot (reference, attempt, or a single clip to analyse): record from the microphone after a click, load a
// file, or pick a synthetic demo; then show the waveform and spectrogram (AudioProcessor.get_spectrogram, <= 8 kHz).
import { esc } from './core.js';
import { SR, spectrogramDb } from './dsp.js';
import { decodeFile, play, record, stop, wavBlob } from './audio_io.js';
import { DEMOS, clips, demoClip, makeClip } from './state.js';
import { heatmap, waveform } from './plots.js';

const COLORS = { reference: '#3fd8ff', user: '#ff5c8a', single: '#ffb547' };

export function drawClipPlots(host, clip, color) {
  const [cw, cs] = host.querySelectorAll('canvas');
  waveform(cw, { series: [{ y: clip.y, color }], title: 'waveform', h: 150 });
  const sp = spectrogramDb(clip.y), kmax = sp.freqs.findIndex(f => f > 8000) - 1;
  heatmap(cs, { rows: sp.db, x1: clip.y.length / SR, yr: [0, sp.freqs[kmax]], kmax, ylabel: 'Hz', title: 'spectrogram (dB)', h: 170 });
}

// slot: 'reference' | 'user' | 'single'. prepare: trim + normalise recordings/attempts like the desktop app.
export function clipPanel(host, { slot, title, cls, hint, prepareRecord = true, prepareFile = false, extra = '', onChange }) {
  const id = `clip-${slot}`;
  host.innerHTML = `<section class="panel clip ${cls}" aria-labelledby="${id}-h">
    <h2 id="${id}-h">${esc(title)}</h2>
    <p class="small mute">${hint}</p>
    <div class="src">
      <button class="rec" type="button">Record</button>
      <label for="${id}-dur">for</label>
      <select id="${id}-dur" aria-label="Recording length">${[1, 2, 3, 4, 5, 8].map(s => `<option value="${s}" ${s === 3 ? 'selected' : ''}>${s} s</option>`).join('')}</select>
      <label class="btn alt">Load file<input type="file" accept="audio/*,.wav,.mp3,.ogg,.flac" aria-label="Load an audio file"></label>
      <select class="demo" aria-label="Synthetic demo clip"><option value="">Synthetic demo...</option>
        ${Object.entries(DEMOS).map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join('')}</select>
      ${extra}
    </div>
    <div class="meta" aria-live="polite"></div>
    <div class="plots ${clips[slot] ? '' : 'hide'}"><canvas class="plot" role="img" aria-label="${esc(title)} waveform"></canvas>
      <canvas class="plot" role="img" aria-label="${esc(title)} spectrogram"></canvas>
      <button class="alt play" type="button">Play</button><button class="alt wav" type="button">Download WAV</button></div>
  </section>`;
  const $ = s => host.querySelector(s), meta = $('.meta'), color = COLORS[slot];
  const show = () => {
    const c = clips[slot];
    if (!c) return;
    $('.plots').classList.remove('hide');
    const t = c.trimmed ? ` · silence trimmed (${((c.trimmed.n - c.y.length) / SR).toFixed(2)} s removed), normalised` : '';
    meta.innerHTML = `${esc(c.label)} · ${esc(c.source)} · ${(c.y.length / SR).toFixed(2)} s${t}`;
    drawClipPlots($('.plots'), c, color);
  };
  const set = (c) => {
    if (c.y.length < 2048) throw new Error('This clip is shorter than one 2048-sample analysis frame (after trimming silence).');
    clips[slot] = c; show(); onChange?.(c);
  };
  const fail = e => { meta.innerHTML = `<span class="err">${esc(e.message || e)}</span>`; };

  const rec = $('.rec');
  rec.addEventListener('click', async () => {
    if (rec.classList.contains('on')) return;
    const secs = +$(`#${id}-dur`).value;
    rec.classList.add('on'); rec.disabled = true;
    try {
      const y = await record(secs, left => { rec.textContent = `Recording ${left.toFixed(1)} s`; });
      set(makeClip(y, `Recording (${secs} s)`, 'microphone', prepareRecord));
    } catch (e) { fail(e); } finally { rec.classList.remove('on'); rec.disabled = false; rec.textContent = 'Record'; }
  });
  $('input[type=file]').addEventListener('change', async e => {
    const f = e.target.files[0];
    if (!f) return;
    meta.textContent = 'Decoding...';
    try { set(makeClip(await decodeFile(f), f.name, 'file', prepareFile)); } catch (err) { fail(new Error(`Could not read ${f.name}: ${err.message || err}`)); }
  });
  $('.demo').addEventListener('change', e => {
    if (!e.target.value) return;
    try { set(demoClip(e.target.value, prepareFile)); } catch (err) { fail(err); }
    e.target.value = '';
  });
  $('.play').addEventListener('click', () => clips[slot] && play(clips[slot].y));
  $('.wav').addEventListener('click', () => {
    if (!clips[slot]) return;
    const a = document.createElement('a');
    a.href = URL.createObjectURL(wavBlob(clips[slot].y)); a.download = `${slot}.wav`; a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  });
  show();
  return { set, show, stop };
}
