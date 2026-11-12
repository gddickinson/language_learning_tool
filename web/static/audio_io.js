// Browser audio: decode files, record from the microphone (only after a click), play, and export WAV.
// Everything is resampled to the app's 44.1 kHz mono, as AudioProcessor.load_audio does (Web Audio's resampler
// stands in for librosa.resample, so resampled files differ slightly from the desktop app's).
import { SR } from './dsp.js';

let ctx = null;
const audioCtx = () => (ctx ||= new (window.AudioContext || window.webkitAudioContext)());

// Decode any browser-supported audio file (ArrayBuffer) to mono Float64Array at 44.1 kHz.
export async function decode(buf) {
  const decoded = await audioCtx().decodeAudioData(buf.slice(0));
  const n = Math.max(1, Math.ceil(decoded.duration * SR));
  const off = new OfflineAudioContext(1, n, SR);  // 1 output channel: stereo is down-mixed to (L + R) / 2
  const src = off.createBufferSource();
  src.buffer = decoded; src.connect(off.destination); src.start();
  const out = await off.startRendering();
  return Float64Array.from(out.getChannelData(0));
}

export async function decodeFile(file) { return decode(await file.arrayBuffer()); }

// Record `seconds` from the microphone. onTick(remaining) is called every 100 ms. Returns Float64Array (44.1 kHz).
export async function record(seconds, onTick = () => {}) {
  if (!navigator.mediaDevices?.getUserMedia) throw new Error('This browser cannot record audio (no getUserMedia).');
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false, channelCount: 1 } });
  try {
    const rec = new MediaRecorder(stream), chunks = [];
    rec.ondataavailable = e => e.data.size && chunks.push(e.data);
    const done = new Promise(res => { rec.onstop = res; });
    rec.start();
    const t0 = performance.now();
    await new Promise(res => {
      const iv = setInterval(() => {
        const left = seconds - (performance.now() - t0) / 1000;
        onTick(Math.max(0, left));
        if (left <= 0) { clearInterval(iv); res(); }
      }, 100);
    });
    rec.stop();
    await done;
    return decode(await new Blob(chunks, { type: rec.mimeType }).arrayBuffer());
  } finally {
    stream.getTracks().forEach(t => t.stop());
  }
}

let playing = null;
export function play(y) {
  stop();
  const c = audioCtx(), b = c.createBuffer(1, Math.max(1, y.length), SR);
  b.getChannelData(0).set(Float32Array.from(y));
  const s = c.createBufferSource();
  s.buffer = b; s.connect(c.destination); s.start();
  playing = s;
  return new Promise(res => { s.onended = res; });
}
export function stop() { if (playing) { try { playing.stop(); } catch { /* already stopped */ } playing = null; } }

// 32-bit float mono WAV (lossless for the analysis; soundfile reads it in the Python cross-check).
export function wavBlob(y, sr = SR) {
  const n = y.length, buf = new ArrayBuffer(44 + 4 * n), v = new DataView(buf);
  const str = (o, s) => [...s].forEach((ch, i) => v.setUint8(o + i, ch.charCodeAt(0)));
  str(0, 'RIFF'); v.setUint32(4, 36 + 4 * n, true); str(8, 'WAVE'); str(12, 'fmt ');
  v.setUint32(16, 16, true); v.setUint16(20, 3, true); v.setUint16(22, 1, true); v.setUint32(24, sr, true);
  v.setUint32(28, sr * 4, true); v.setUint16(32, 4, true); v.setUint16(34, 32, true); str(36, 'data'); v.setUint32(40, 4 * n, true);
  for (let i = 0; i < n; i++) v.setFloat32(44 + 4 * i, y[i], true);
  return new Blob([buf], { type: 'audio/wav' });
}
