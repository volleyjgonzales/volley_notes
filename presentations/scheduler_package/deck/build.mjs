// Builds the stakeholder deck into one self-contained HTML file: dist/index.html.
//
//   src/slides.html  the <section> slides (reveal.js markup)
//   src/deck.css     theme (same palette and fonts as the study site)
//   src/deck.js      figure stepping (animated figures advance with reveal.js fragments)
//
// A placeholder  <div class="fig" data-fig="NAME" [data-crop="header"] [data-play]></div>  is replaced by the
// figure ../figures/NAME.svg, inlined, with its ids prefixed, its scripts removed and, for animated figures
// with data-play, one hidden fragment per step so that the presenter's "next" walks through the animation.
// reveal.js, its notes plugin and the fonts are inlined, so the file works offline and can be emailed.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import { codeToHtml } from 'shiki';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');
const read = (p) => fs.readFileSync(p, 'utf8');
const rv = (p) => read(path.join(here, 'node_modules/reveal.js', p));

// ---- fonts (the same woff2 files the figures embed)
const fontDir = path.join(root, 'scripts/diagrams/fonts');
const faces = [
  ['IBM Plex Sans', 400, 'normal', 'ibm-plex-sans-latin-400-normal.woff2'],
  ['IBM Plex Sans', 400, 'italic', 'ibm-plex-sans-latin-400-italic.woff2'],
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

// ---- figures
let figCount = 0;
function figure(attrs) {
  const name = /data-fig="([^"]+)"/.exec(attrs)[1];
  const crop = /data-crop="([^"]+)"/.exec(attrs)?.[1];
  const play = /data-play\b/.test(attrs);
  const cls = /class="([^"]+)"/.exec(attrs)?.[1] ?? 'fig';
  // the deck's own figures (scripts/diagrams/fig_deck.py) live in deck/figures; the study's in figures/
  const own = path.join(here, 'figures', `${name}.svg`);
  const file = fs.existsSync(own) ? own : path.join(root, 'figures', `${name}.svg`);
  let svg = read(file).replace(/<\?xml[^>]*>\s*/, '');
  svg = svg.replace(/<script>[\s\S]*?<\/script>/g, '');
  const p = `f${++figCount}-`;
  svg = svg.replace(/\bid="([^"]+)"/g, (_, id) => `id="${p}${id}"`);
  svg = svg.replace(/url\(#([^)]+)\)/g, (_, id) => `url(#${p}${id})`);
  svg = svg.replace(/href="#([^"]+)"/g, (_, id) => `href="#${p}${id}"`);
  svg = svg.replace(/aria-labelledby="[^"]*"/, '');
  // crop the figure's own title block (everything above y = -16): the slide has its own title
  const vb = /viewBox="(-?[\d.]+) (-?[\d.]+) ([\d.]+) ([\d.]+)"/.exec(svg);
  let [x0, y0, w, h] = vb.slice(1).map(Number);
  if (crop === 'header') {
    // cut just below the last header line (title and subtitle sit above y = -16; content starts near 0)
    const ys = [...svg.matchAll(/<text[^>]* y="(-[\d.]+)"/g)].map((m) => Number(m[1])).filter((y) => y < -16);
    const cut = ys.length ? Math.max(...ys) + 12 : -16;
    if (y0 < cut) { h -= cut - y0; y0 = cut; }
  }
  svg = svg.replace(vb[0], `viewBox="${x0} ${y0} ${w} ${h}" preserveAspectRatio="xMidYMid meet"`);
  svg = svg.replace(/ width="\d+" height="\d+"/, '');
  const steps = Number(/data-steps="(\d+)"/.exec(svg)?.[1] ?? 0);
  const caps0 = steps ? JSON.parse(/<metadata[^>]*>([\s\S]*?)<\/metadata>/.exec(svg)[1].replace(/&quot;/g, '"').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')) : [];
  const caps = caps0.map(describe);
  let extra = '';
  if (steps && play) {
    for (let k = 1; k < steps; k++) extra += `<span class="fragment figstep" data-for="${p}"></span>`;
  }
  const cap = steps && play ? `<div class="figcap" data-for="${p}"></div>` : '';
  const data = steps && play ? ` data-figid="${p}" data-caps='${JSON.stringify(caps).replace(/'/g, '&#39;')}'` : '';
  return `<div class="${cls}"${data}>${svg}</div>${cap}${extra}`;
}

let slides = read(path.join(here, 'src/slides.html'));

// ---- code: <pre data-lang="cpp"><code>…</code></pre> is highlighted at build time with Shiki, in both themes
// (github-dark-default / github-light-default, the site's themes); deck.css picks one with --shiki-dark / --shiki-light
const unescapeHtml = (t) => t.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&amp;/g, '&');
const blocks = [...slides.matchAll(/<pre data-lang="([a-z]+)"><code>([\s\S]*?)<\/code><\/pre>/g)];
for (const [whole, lang, code] of blocks) {
  const html = await codeToHtml(unescapeHtml(code), {
    lang, themes: { dark: 'github-dark-default', light: 'github-light-default' }, defaultColor: false,
  });
  slides = slides.replace(whole, html.replace('<pre class="shiki', '<pre class="code shiki'));
}

// ---- captions of the study figures: name the kind of every place and tray ("tray T17", "stall P17"), as the slides do
const KIND = { T: 'tray', P: 'stall', W: 'waypoint', B: 'bay', C: 'charger' };
const describe = (t) => t.replace(/(?<![\w-])([TPWBC])(\d+)\b/g, (m, k, n, off, all) => {
  const before = all.slice(Math.max(0, off - 12), off).toLowerCase();
  const word = KIND[k];
  return new RegExp(`${word}s? $|${word}s? and $|${word}s?, $`).test(before) ? m : `${word} ${m}`;
});
slides = slides.replace(/<div ((?:class="[^"]*" )?data-fig="[^"]+"[^>]*)><\/div>/g, (_, attrs) => figure(attrs));

// ---- light theme: recolour every SVG on the slides (study figures and the deck's own diagrams) with the colour map
// that scripts/diagrams/lightmode.py derives from the figure palette (refreshed here, so new deck colours are mapped)
execFileSync('python3', [path.join(root, 'scripts/diagrams/lightmode.py'), '--map'], { stdio: 'inherit' });
const cmap = JSON.parse(read(path.join(root, 'figures/theme-map.json')));
const used = new Set();
for (const m of slides.matchAll(/\b(fill|stroke|stop-color)="(#[0-9A-Fa-f]{6})"/g)) used.add(`${m[1]}|${m[2].toUpperCase()}`);
for (const m of slides.matchAll(/style="([^"]*)"/g)) {
  for (const n of m[1].matchAll(/\b(fill|stroke):\s*(#[0-9A-Fa-f]{6})/g)) used.add(`style-${n[1]}|${n[2].toUpperCase()}`);
}
const rules = [];
for (const key of [...used].sort()) {
  const [a, c] = key.split('|');
  const lc = cmap[c];
  if (!lc) throw new Error(`no light colour for ${c}: run python3 scripts/diagrams/lightmode.py --map`);
  if (lc === c) continue;
  if (a.startsWith('style-')) {
    const prop = a.slice(6);
    rules.push(`S [style*="${prop}:${c}" i]{${prop}:${lc}!important}`);
  } else rules.push(`S [${a}="${c}" i]{${a}:${lc}}`);
}
const ruleText = rules.join('\n');
const lightCss = ruleText.replaceAll('S ', ":root[data-theme='light'] .reveal svg ") +
  '\n@media (prefers-color-scheme: light) {\n' + ruleText.replaceAll('S ', ':root:not([data-theme]) .reveal svg ') + '\n}\n';

const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Scheduler core refactor</title>
<style>${fontCss}</style>
<style>${rv('dist/reset.css')}</style>
<style>${rv('dist/reveal.css')}</style>
<style>${read(path.join(here, 'src/deck.css'))}</style>
<style>${lightCss}</style>
<script>try{var t=localStorage.getItem('deck-theme');if(t==='light'||t==='dark')document.documentElement.dataset.theme=t}catch(e){}</script>
</head>
<body>
<div class="reveal"><div class="slides">
${slides}
</div></div>
<script>${rv('dist/reveal.js')}</script>
<script>${rv('plugin/notes/notes.js')}</script>
<script>${read(path.join(here, 'src/deck.js'))}</script>
</body>
</html>
`;
fs.mkdirSync(path.join(here, 'dist'), { recursive: true });
fs.writeFileSync(path.join(here, 'dist/index.html'), html);
console.log(`deck: dist/index.html ${(html.length / 1024).toFixed(0)} KB, ${figCount} figures, ${rules.length} light-theme colour rules`);
