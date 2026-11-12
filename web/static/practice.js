// Practice: the desktop Practice tab in the browser. Reference + attempt -> DTW comparison on MFCC, chroma and
// spectral features, the pronunciation analysis, and the DTW-aligned waveform and spectrograms.
import { api, app, esc, isStatic, needsServer, route } from './core.js';
import { clips, demoClip } from './state.js';
import { clipPanel } from './clip_panel.js';
import { compareNow, pythonCheck } from './practice_results.js';

route('practice', async (args, query) => {
  if (query.demo) {  // e.g. #/practice?demo=close : load synthetic demo clips (used for screenshots)
    clips.reference = demoClip('reference', false);
    clips.user = demoClip(query.demo in { close: 1, different: 1, reference: 1 } ? query.demo : 'close', true);
  }
  app().innerHTML = `
  <section class="hero"><p class="kicker">Practice · record, compare, repeat</p>
    <h1 class="glow">Compare your pronunciation</h1>
    <p class="lead">Give a reference (your teacher, a native speaker, a file you have the rights to, or yourself on a good
    day) and record your attempt. Both are analysed here, in your browser: features every 512 samples (11.6 ms), then
    Dynamic Time Warping lines up the two clips however fast you spoke.</p></section>
  <div class="two"><div id="ref"></div><div id="you"></div></div>
  <div class="row" style="align-items:center">
    <div style="flex:0 1 auto"><button id="go" type="button" disabled>Compare</button>
    <button id="py" type="button" class="alt ${isStatic() ? 'hide' : ''}" disabled>Check with Python</button></div>
    <p id="why" class="small mute" style="margin:10px 0 0">Add a reference and an attempt to compare.</p></div>
  <div id="out"></div><div id="pyout"></div>`;
  const ready = () => {
    const ok = clips.reference && clips.user;
    document.getElementById('go').disabled = !ok;
    document.getElementById('py').disabled = !ok;
    document.getElementById('why').textContent = ok ? 'Ready.' : 'Add a reference and an attempt to compare.';
  };
  let libOpts = '';
  if (!isStatic()) {
    try {
      const lib = await api('/library', { fresh: true });
      if (lib.samples.length) libOpts = `<select class="lib" aria-label="Reference from your library"><option value="">From library...</option>
        ${lib.samples.filter(s => s.file_exists).map(s => `<option value="${s.id}">${esc(s.word)} (${esc(s.language)})</option>`).join('')}</select>`;
    } catch { /* no library */ }
  }
  const refPanel = clipPanel(document.getElementById('ref'), { slot: 'reference', title: 'Reference', cls: 'ref', extra: libOpts,
    hint: 'Recordings are trimmed and normalised (as the desktop Recording tab does); files are used as they are.',
    prepareRecord: true, prepareFile: false, onChange: ready });
  clipPanel(document.getElementById('you'), { slot: 'user', title: 'Your attempt', cls: 'you',
    hint: 'Silence is trimmed and the level normalised, as the desktop Practice tab does after Record.',
    prepareRecord: true, prepareFile: true, onChange: ready });
  const lib = document.querySelector('#ref .lib');
  if (lib) lib.addEventListener('change', async e => {
    if (!e.target.value) return;
    const { decode } = await import('./audio_io.js'), { makeClip } = await import('./state.js');
    const r = await fetch(`api/library/${e.target.value}/audio`);
    const opt = e.target.selectedOptions[0].textContent;
    refPanel.set(makeClip(await decode(await r.arrayBuffer()), opt, 'library sample', false));
    e.target.value = '';
  });
  ready();
  document.getElementById('go').addEventListener('click', () => compareNow(document.getElementById('out')));
  document.getElementById('py').addEventListener('click', () => pythonCheck(document.getElementById('pyout')));
  if (query.demo || (clips.reference && clips.user && query.run)) compareNow(document.getElementById('out'));
  if (isStatic()) document.getElementById('pyout').innerHTML = needsServer('Re-running the comparison with the Python code');
});
