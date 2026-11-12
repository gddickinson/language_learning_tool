// Static site: answers api(path) from the JSON exported at build time (scripts/build_static.py). The analysis runs in
// the browser anyway; only the Python cross-check (/compare) and the local library need the server.
const EXPORTED = new Set(['/info', '/verify']);

export async function staticApi(path, body) {
  const p = path.split('?')[0];
  if (!body && EXPORTED.has(p)) {
    const r = await fetch('api' + p + '.json');
    if (!r.ok) throw new Error(`${r.status} for ${p}`);
    return r.json();
  }
  const e = new Error('needs the local app');
  e.needsServer = true;
  throw e;
}
