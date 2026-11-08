// Exports dist/index.html to exports/slide.png (3840x2160) and exports/slide.pdf (one 1920x1080 page) with headless
// Chrome over the DevTools protocol: reveal.js lays out its print view asynchronously, which --print-to-pdf doesn't wait for.
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const chrome = process.env.CHROME ?? 'google-chrome';
const page = `file://${path.join(here, 'dist/index.html')}`;
const proc = spawn(chrome, ['--headless=new', '--disable-gpu', '--remote-debugging-port=0', 'about:blank']);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const wsUrl = await new Promise((resolve, reject) => {
  proc.stderr.on('data', (d) => { const m = /DevTools listening on (ws:\/\/\S+)/.exec(d.toString()); if (m) resolve(m[1]); });
  let err = '';
  proc.stderr.on('data', (d) => { err += d; });
  proc.on('exit', (code) => reject(new Error(`chrome exited (${code}): ${err.slice(-500)}`)));
});
const browser = new WebSocket(wsUrl);
await new Promise((r) => browser.addEventListener('open', r));
let id = 0;
const pending = new Map();
browser.addEventListener('message', (e) => {
  const msg = JSON.parse(e.data);
  if (pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); }
});
const send = (method, params = {}, sessionId) => new Promise((resolve, reject) => {
  const n = ++id;
  pending.set(n, (m) => (m.error ? reject(new Error(`${method}: ${m.error.message}`)) : resolve(m.result)));
  browser.send(JSON.stringify({ id: n, method, params, sessionId }));
});

try {
  const { targetId } = await send('Target.createTarget', { url: 'about:blank' });
  const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true });
  const s = (m, p) => send(m, p, sessionId);
  await s('Emulation.setDeviceMetricsOverride', { width: 1920, height: 1080, deviceScaleFactor: 2, mobile: false });
  await s('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] });
  await s('Page.navigate', { url: page });
  await sleep(1500);
  const png = await s('Page.captureScreenshot', { format: 'png' });
  fs.mkdirSync(path.join(here, 'exports'), { recursive: true });
  fs.writeFileSync(path.join(here, 'exports/slide.png'), Buffer.from(png.data, 'base64'));

  await s('Page.navigate', { url: `${page}?print-pdf` });
  await sleep(2000);
  const pdf = await s('Page.printToPDF', { printBackground: true, preferCSSPageSize: true });
  fs.writeFileSync(path.join(here, 'exports/slide.pdf'), Buffer.from(pdf.data, 'base64'));
  console.log('slide: exports/slide.png, exports/slide.pdf');
} finally {
  browser.close();
  proc.kill();
}
