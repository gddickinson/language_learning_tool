// Home: hero, the settings the analysis uses (from /info, i.e. src/config.py), and cards to the pages.
import { app, isStatic, route } from './core.js';
import { getInfo } from './state.js';

route('home', async () => {
  const { settings: s } = await getInfo();
  app().innerHTML = `
  <section class="hero">
    <p class="kicker">Pronunciation practice · waveform · MFCC · Dynamic Time Warping</p>
    <h1 class="glow">Hear it, see it, match it</h1>
    <p class="lead">The Language Learning Pronunciation Tool records your attempt at a word or phrase and compares it with
      a reference: waveforms and spectrograms side by side, speech features (MFCC, chroma, spectral), and a Dynamic Time
      Warping alignment that copes with speaking faster or slower. This site <b>is</b> the tool: recording and analysis
      run in your browser, and your audio never leaves the page.</p>
    <a class="btn" href="#/practice">Start practising</a><a class="btn alt" href="#/practice?demo=close">Try the demo clips</a><a class="btn alt" href="#/analyse">Analyse one clip</a>
  </section>
  <div class="tiles">
    <div class="tile"><b>${(s.sample_rate / 1000).toFixed(1)} kHz</b><span>mono sample rate</span></div>
    <div class="tile"><b>${s.n_mfcc}</b><span>MFCCs per frame (of 128 mel bands)</span></div>
    <div class="tile"><b>${s.feature_types.length}</b><span>feature sets compared: MFCC, chroma, spectral</span></div>
    <div class="tile"><b>${(s.hop_length / s.sample_rate * 1000).toFixed(1)} ms</b><span>between feature frames</span></div>
    <div class="tile"><b>${s.dtw_radius}</b><span>FastDTW search radius</span></div>
  </div>
  ${isStatic() ? `<div class="callout">No reference recordings ship with the repository, so bring your own: record a
    teacher or native speaker (with their permission), load an audio file you have the rights to, or record yourself as
    the reference. The synthetic demo clips are generated tones, not speech, and are there to show how everything works.</div>` : ''}
  <h2>Pages</h2>
  <div class="grid">
    <a class="card" href="#/practice"><b>Practice</b><span>Reference and attempt, then compare: per-feature DTW distances, speed, pitch and volume feedback, the DTW-aligned waveforms and spectrograms, and the warping path.</span></a>
    <a class="card" href="#/analyse"><b>Analyse</b><span>One clip in detail: spectrogram, MFCC and chroma heatmaps, spectral centroid and roll-off, zero-crossing rate, pitch track and the summary statistics.</span></a>
    <a class="card" href="#/library"><b>Library</b><span>${isStatic() ? 'Your saved reference samples (desktop app database); available in the local web app.' : 'Your saved reference samples from the desktop app, ready to use as references.'}</span></a>
    <a class="card" href="#/verify"><b>Verify</b><span>Runs the browser engine on synthetic signals and checks every number against the Python results (librosa, fastdtw, scipy).</span></a>
    <a class="card" href="#/about"><b>About</b><span>How it works, how to run the desktop and local web apps, and what differs from the desktop app.</span></a>
  </div>`;
});
