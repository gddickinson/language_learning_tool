// Shared state between pages: the reference and attempt clips (kept while you move around the site) and the
// /info settings. A clip is { y: Float64Array at 44.1 kHz, label, source, prepared }.
import { api } from './core.js';
import { normalize, trimSilence } from './dsp.js';
import { PRESETS, synth } from './synth.js';

export const clips = { reference: null, user: null, single: null };
export const getInfo = () => api('/info');

// The desktop app trims silence and normalises right after recording (Practice and Recording tabs); references loaded
// from a file are used as they are. prepare=true applies the recording treatment.
export function makeClip(y, label, source, prepare) {
  let out = y, trimmed = null;
  if (prepare) {
    const t = trimSilence(y);
    trimmed = { start: t.start, end: t.end, n: y.length };
    out = normalize(t.audio);
  }
  return { y: out, label, source, prepared: !!prepare, trimmed };
}

export const DEMOS = {
  reference: 'Synthetic voice A (gliding 140 to 190 Hz, 2 syllables)',
  close: 'Synthetic voice A, slower and slightly higher',
  different: 'Synthetic voice B (falling 260 to 210 Hz, 3 syllables)',
};
export const demoClip = (name, prepare) => makeClip(synth(PRESETS[name]), DEMOS[name], 'synthetic demo (not speech)', prepare);
