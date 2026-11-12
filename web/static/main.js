// Entry point: lazy page modules, the mode label, a subtle scrolling-waveform background, then the router.
import { $, app, isStatic, lazy, route, start } from './core.js';

const PAGES = { 'home.js': ['home'], 'practice.js': ['practice'], 'analyse.js': ['analyse'], 'library.js': ['library'],
  'verify.js': ['verify'], 'about.js': ['about'] };
lazy(Object.fromEntries(Object.entries(PAGES).flatMap(([file, names]) => names.map(n => [n, () => import('./' + file)]))));
route('notfound', () => { app().innerHTML = '<h1>Not found</h1><p><a href="#/">Back to the start</a></p>'; });

$('#mode').textContent = isStatic()
  ? 'static site: recording and analysis run in your browser; audio never leaves this page'
  : 'local app: analysis in the browser, with Python cross-checks and your sample library on this computer';

// Background: two faint waveforms drifting past (reference and attempt colours). Off under prefers-reduced-motion.
function background(canvas) {
  if (!canvas || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const g = canvas.getContext('2d');
  const fit = () => { canvas.width = innerWidth; canvas.height = innerHeight; };
  fit(); addEventListener('resize', fit);
  let last = 0;
  const tick = t => {
    requestAnimationFrame(tick);
    if (document.hidden || t - last < 50) return;
    last = t;
    g.clearRect(0, 0, canvas.width, canvas.height);
    [['#3fd8ff', 0, 0.55], ['#ff5c8a', 0.7, 0.62]].forEach(([c, lag, yy]) => {
      g.strokeStyle = c; g.globalAlpha = 0.35; g.lineWidth = 1.2; g.beginPath();
      for (let x = 0; x <= canvas.width; x += 3) {
        const s = x / 90 + t / 1400 - lag, env = Math.sin(x / canvas.width * Math.PI * 3 + t / 5000) ** 2;
        const y = canvas.height * yy + 40 * env * (Math.sin(s * 3) + 0.5 * Math.sin(s * 7.3));
        x ? g.lineTo(x, y) : g.moveTo(x, y);
      }
      g.stroke();
    });
  };
  requestAnimationFrame(tick);
}
background($('#bg'));
start();
