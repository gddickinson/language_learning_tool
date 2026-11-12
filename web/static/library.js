// Library: the reference samples in the local SQLite database (data/samples.db) of the desktop app. Local app only.
import { api, app, esc, go, isStatic, needsServer, route } from './core.js';
import { decode } from './audio_io.js';
import { clips, makeClip } from './state.js';

route('library', async () => {
  const head = `<section class="hero"><p class="kicker">Library · your saved references</p><h1 class="glow">Sample library</h1>
    <p class="lead">Samples you added in the desktop app (Record Samples, Library, Download tabs) live in a local SQLite
    database. Pick one to use as the reference on the Practice page.</p></section>`;
  if (isStatic()) {
    app().innerHTML = head + needsServer('The sample library') + `<p class="small mute">On this static site, use Record or
      Load file on the Practice page instead; nothing is stored.</p>`;
    return;
  }
  const lib = await api('/library', { fresh: true });
  app().innerHTML = head + (lib.samples.length ? `<div class="scroll"><table><thead><tr><th>Word</th><th>Language</th><th>Category</th>
    <th>Source</th><th>Speaker</th><th class="n">Duration (s)</th><th></th></tr></thead><tbody>
    ${lib.samples.map(s => `<tr><td>${esc(s.word)}</td><td>${esc(s.language)}</td><td>${esc(s.category ?? '')}</td><td>${esc(s.source ?? '')}</td>
      <td>${esc(s.speaker ?? '')}</td><td class="n">${s.duration == null ? '' : (+s.duration).toFixed(2)}</td>
      <td>${s.file_exists ? `<button type="button" class="alt" data-id="${s.id}" data-label="${esc(s.word)} (${esc(s.language)})" style="margin:0">Use as reference</button>` : '<span class="mute small">file missing</span>'}</td></tr>`).join('')}
    </tbody></table></div>` : `<p class="mute">The library is empty${lib.db === 'none' ? ' (no database yet)' : ''}. Add samples in the desktop app.</p>`);
  app().querySelectorAll('button[data-id]').forEach(b => b.addEventListener('click', async () => {
    b.disabled = true;
    const r = await fetch(`api/library/${b.dataset.id}/audio`);
    clips.reference = makeClip(await decode(await r.arrayBuffer()), b.dataset.label, 'library sample', false);
    go('#/practice');
  }));
});
