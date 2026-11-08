// Builds the one-slide status update into one self-contained HTML file: dist/index.html.
//
//   src/slide.html  the <section> (reveal.js markup, speaker notes in <aside class="notes">)
//   src/slide.css   theme: light, the design tokens of design_system.md
//
// reveal.js, its notes plugin, the fonts (the study pack's woff2 files) and the icons are inlined, so the file works offline
// and can be emailed or shared in the meeting chat.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const read = (p) => fs.readFileSync(p, 'utf8');
const rv = (p) => read(path.join(here, 'node_modules/reveal.js', p));

// ---- fonts: IBM Plex Sans + JetBrains Mono, the same files as the scheduler study pack and its deck
const fontDir = path.join(here, '../scheduler_package/scripts/diagrams/fonts');
const faces = [
  ['IBM Plex Sans', 400, 'normal', 'ibm-plex-sans-latin-400-normal.woff2'],
  ['IBM Plex Sans', 500, 'normal', 'ibm-plex-sans-latin-500-normal.woff2'],
  ['IBM Plex Sans', 600, 'normal', 'ibm-plex-sans-latin-600-normal.woff2'],
  ['JetBrains Mono', 400, 'normal', 'jetbrains-mono-latin-400-normal.woff2'],
  ['JetBrains Mono', 600, 'normal', 'jetbrains-mono-latin-600-normal.woff2'],
  ['JetBrains Mono', 700, 'normal', 'jetbrains-mono-latin-700-normal.woff2'],
];
const fontCss = faces
  .map(([fam, w, st, f]) => {
    const b64 = fs.readFileSync(path.join(fontDir, f)).toString('base64');
    return `@font-face{font-family:'${fam}';font-weight:${w};font-style:${st};font-display:swap;src:url(data:font/woff2;base64,${b64}) format('woff2');}`;
  })
  .join('\n');

// ---- icons: <i data-icon="NAME"></i> becomes the Lucide icon NAME, inlined (lucide-static, ISC licence)
const icon = (name) => read(path.join(here, 'node_modules/lucide-static/icons', `${name}.svg`))
  .replace(/<!--[\s\S]*?-->\s*/, '')
  .replace(/\s*width="24"\s*height="24"/, '')
  .replace(/class="lucide lucide-[^"]*"/, 'class="icon" aria-hidden="true"')
  .replace(/\n\s*/g, ' ')
  .trim();

// ---- roadmap: an element with data-start="YYYY-MM-DD" [data-end="YYYY-MM-DD"] inside the .gantt gets --x (and --w)
// as a percentage of the window data-from .. data-to; bars that run past the window are clipped to it
const day = (d) => Date.parse(`${d}T00:00:00Z`) / 86400000;
function place(slide) {
  const [, from, to] = /data-from="([\d-]+)" data-to="([\d-]+)"/.exec(slide);
  const pct = (d) => Math.min(100, Math.max(0, (100 * (day(d) - day(from))) / (day(to) - day(from))));
  return slide.replace(/data-start="([\d-]+)"(?: data-end="([\d-]+)")?/g, (whole, s, e) => {
    const x = pct(s);
    const style = e ? `--x:${x.toFixed(3)}%;--w:${(pct(e) - x).toFixed(3)}%` : `--x:${x.toFixed(3)}%`;
    return `${whole} style="${style}"`;
  });
}

const slide = place(read(path.join(here, 'src/slide.html'))).replace(/<i data-icon="([a-z0-9-]+)"><\/i>/g, (_, n) => icon(n));

const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Scheduler status · Nov 6</title>
<style>${fontCss}</style>
<style>${rv('dist/reset.css')}</style>
<style>${rv('dist/reveal.css')}</style>
<style>${read(path.join(here, 'src/slide.css'))}</style>
</head>
<body>
<div class="reveal"><div class="slides">
${slide}
</div></div>
<script>${rv('dist/reveal.js')}</script>
<script>${rv('plugin/notes/notes.js')}</script>
<script>
Reveal.initialize({
  width: 1920, height: 1080, margin: 0, minScale: 0.1, maxScale: 2,
  center: false, controls: false, progress: false, hash: false, transition: 'none',
  plugins: [RevealNotes],
});
</script>
</body>
</html>
`;
fs.mkdirSync(path.join(here, 'dist'), { recursive: true });
fs.writeFileSync(path.join(here, 'dist/index.html'), html);
console.log(`slide: dist/index.html ${(html.length / 1024).toFixed(0)} KB`);
