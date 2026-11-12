// About: what the tool is, how the analysis works, how to run it, and what differs from the desktop app.
import { app, route } from './core.js';
import { getInfo } from './state.js';

const PORT = [
  ['AudioProcessor.get_spectrogram (scipy.signal.spectrogram)', 'dsp.js spectrogramDb'],
  ['AudioProcessor.trim_silence / normalize_audio (librosa.effects.trim)', 'dsp.js trimSilence / normalize'],
  ['librosa.stft, mfcc, chroma_stft (+ estimate_tuning), spectral_centroid, spectral_rolloff, zero_crossing_rate, piptrack', 'dsp.js, features.js'],
  ['DTWComparator.compare_dtw / compare_multiple_features / analyze_pronunciation_errors (fastdtw 0.3.4)', 'dtw.js'],
  ['alignment_utils.apply_dtw_warping / calculate_path_smoothness (scipy interp1d cubic, savgol_filter)', 'align.js'],
  ['feedback_report.practice_report (Practice tab text)', 'align.js practiceReport'],
  ['AudioProcessor.get_audio_features', 'summary.js'],
];

route('about', async () => {
  const { settings: s } = await getInfo();
  app().innerHTML = `
  <section class="hero"><p class="kicker">About</p><h1 class="glow">Language Learning Pronunciation Tool</h1>
    <p class="lead">A modular Python application for learning foreign language pronunciation through audio recording,
    waveform visualization and comparison using Dynamic Time Warping (DTW). This web version runs the same analysis in
    the browser.</p></section>

  <h2>How a comparison works</h2>
  <ol>
    <li><b>Prepare.</b> Audio is mono at ${s.sample_rate} Hz. Recordings are trimmed (frames more than 40 dB below the
      loudest are dropped from the ends) and normalised to a peak of 1, as the desktop app does after Record.</li>
    <li><b>Features.</b> Every ${s.hop_length} samples a ${s.nfft}-sample Hann window is Fourier transformed. From it come
      ${s.n_mfcc} MFCCs (128 Slaney mel bands, dB, orthonormal DCT), ${s.n_chroma} chroma values (with librosa's tuning
      estimate) and three spectral values (centroid, 85 % roll-off, zero-crossing rate).</li>
    <li><b>Common scale.</b> For the comparison both clips are peak-normalised (loudness is judged separately) and
      each feature set is scaled: MFCCs from a log-mel spectrogram floored ${s.score.mfcc_top_db} dB below its peak, in
      units of ${s.score.mfcc_scale_db} dB; centroid and roll-off as fractions of the Nyquist frequency; chroma and
      zero-crossing rate as they are. Each frame is divided by √(number of coefficients).</li>
    <li><b>DTW.</b> For each feature set, FastDTW (radius ${s.dtw_radius}, Euclidean frame distance) finds the cheapest
      monotonic alignment between your frames and the reference's; the total cost divided by the path length is the
      distance d.</li>
    <li><b>Score and feedback.</b> Each distance becomes a match 100 × exp(−d / d0) with d0 = MFCC ${s.score.d0.mfcc},
      chroma ${s.score.d0.chroma}, spectral ${s.score.d0.spectral}; the score is the weighted mean (weights
      ${s.score.weights.mfcc} / ${s.score.weights.chroma} / ${s.score.weights.spectral}), with the feedback bands
      ${s.feedback_bands.map(b => `≥ ${b.min_score}`).join(', ')}. Speed compares durations (±20 %), pitch the mean
      piptrack pitch (±20 %), volume the RMS ratio (0.6 to 1.5).</li>
    <li><b>Display.</b> Your recording is warped onto the reference timeline along the MFCC path and drawn over it with
      the |difference| band, and both spectrograms (${s.nfft}-sample Tukey windows, ${s.noverlap} overlap, up to 8 kHz).</li>
  </ol>
  <div class="callout">How d0 was chosen (<code>scripts/calibrate_score.py</code>): for a synthetic voice, the largest
    distance to its time-stretched (0.8×, 1.25×), pitch-shifted (±6 %) and re-noised copies, divided by ln(100/70), so
    each copy scores at least 70 on every feature. With these values the copies score 74–96 overall and unrelated
    signals (another voice, a different intonation, a chirp, noise) 3–25. They are calibrated on synthetic signals, not
    on a corpus of learners' speech.</div>

  <h2>Python and JavaScript</h2>
  <p>Each step is a direct port of the Python code it names, and is tested against it on synthetic signals
    (<a href="#/verify">Verify</a> runs the check in your browser; the largest difference is about 1e-11).</p>
  <div class="scroll"><table><thead><tr><th>Python (desktop app)</th><th>Browser</th></tr></thead><tbody>
    ${PORT.map(([a, b]) => `<tr><td>${a}</td><td class="mono">${b}</td></tr>`).join('')}</tbody></table></div>

  <h2>Differences from the desktop app</h2>
  <ul>
    <li>Audio files and recordings are resampled to 44.1 kHz by the browser's Web Audio resampler instead of
      librosa.resample, so a file at another rate gives slightly different numbers. Browser recordings go through the
      browser's audio codec (echo cancellation, noise suppression and auto gain are switched off).</li>
    <li>Not in the browser: the Live Comparison tab, the pYIN pitch extractor, saving samples and practice history to the
      database, statistics, and the Forvo downloader (it needs your own API key and a network service, so it stays in
      the desktop app). The local web app can read your sample library.</li>
    <li>Reference recordings: none ship with the repository. Use recordings you have the rights to, or your own voice.</li>
  </ul>

  <h2>Run it yourself</h2>
  <h3>Desktop app (PyQt5)</h3>
  <pre>pip install -r requirements.txt
python run.py</pre>
  <h3>Local web app</h3>
  <pre>pip install -r requirements-web.txt
python run_web.py          # http://127.0.0.1:8163</pre>
  <p>The local web app adds a <b>Check with Python</b> button on the Practice page (the same clips through the Python
    code) and the sample library. Everything stays on your computer.</p>

  <h2>Privacy</h2>
  <p>The microphone is only opened when you press Record, and only for the length you chose. On this site audio is
    analysed in the page and never uploaded; the local app sends clips only to the Python server on your own computer.</p>

  <h2>Credits</h2>
  <p>By George Dickinson, MIT licence. Built with AI assistance from Claude (Anthropic). Analysis built on
    <a href="https://librosa.org/">librosa</a>, <a href="https://github.com/slaypni/fastdtw">fastdtw</a>,
    <a href="https://scipy.org/">SciPy</a> and NumPy. The README lists the research areas behind the design:
    computer-assisted pronunciation training, DTW for speech, visual feedback in language learning and high-variability
    phonetic training.</p>`;
});
