/**
 * HTML sources (src/content/*.html) -> page HTML for the study site.
 *
 * The sources hold the prose; everything that can go stale is computed here:
 *   - section numbers (from <h2 data-num> / <h3 data-num>) and figure numbers (document order);
 *   - the text of every <a class="ref"> ("section 14.5", "Figure 12") from its target;
 *   - keyword links (src/data/glossary.yaml), "doc 02" links, MathML, code highlighting, figure frames.
 * The build fails on a broken reference, a missing id, or a glossary target that does not exist.
 */
import fs from 'node:fs';
import path from 'node:path';
import { unified } from 'unified';
import rehypeShiki from '@shikijs/rehype';
import rehypeStringify from 'rehype-stringify';
import katex from 'katex';
import { visit, SKIP } from 'unist-util-visit';
import { toString } from 'hast-util-to-string';
import { fromHtml } from 'hast-util-from-html';
import { h } from 'hastscript';
import YAML from 'yaml';
import type { Root, Element, ElementContent, Text, RootContent } from 'hast';
import { DOCS, docByNum, type DocConfig } from '../data/docs';

export const SITE_ROOT = process.cwd();
export const REPO_ROOT = path.resolve(SITE_ROOT, '..');
const FIG_DIR = path.join(REPO_ROOT, 'figures');

export interface Heading {
  depth: number;
  id: string;
  /** plain text without the number */
  title: string;
  /** inner HTML without the number (keeps inline code) */
  html: string;
  num?: string;
}

export interface RenderedDoc {
  config: DocConfig;
  title: string;
  html: string;
  headings: Heading[];
  figureCount: number;
}

interface GlossaryEntry {
  term: string;
  code?: string[];
  text?: string[];
  to: string;
  def: string;
  /** spelling in definitions.yaml / interfaces whose definition the hover window shows */
  decl?: string;
}

export interface ResolvedTerm extends GlossaryEntry {
  id: string;
  doc: string;
  targetTitle: string;
}

// ---------------------------------------------------------------------------------------------
// helpers

const isEl = (n: unknown, tag?: string): n is Element =>
  !!n && (n as Element).type === 'element' && (!tag || (n as Element).tagName === tag);
const text = (value: string): Text => ({ type: 'text', value });
const cls = (n: Element) => ([] as unknown[]).concat(n.properties?.className ?? []).map(String);
const NO_LINK_INSIDE = new Set(['math', 'a', 'code', 'pre', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'button', 'summary']);

/** Animated figures (an SVG with data-steps) are inlined so the page can step through them.
 *  Returns the SVG prepared for inlining, plus its step captions; null for a static figure. */
const ANIM_SVGS = new Map<string, string>();
function animFigure(file: string, name: string): { steps: string[]; poster: number } | null {
  const raw = fs.readFileSync(path.join(FIG_DIR, file), 'utf8');
  const m = /data-steps="(\d+)" data-poster="(\d+)"/.exec(raw.slice(0, 1200));
  if (!m) return null;
  const meta = /<metadata id="steps-[^"]*">([\s\S]*?)<\/metadata>/.exec(raw);
  if (!meta) throw new BuildError(`figure ${file}: data-steps without step captions`);
  const unescape = (s: string) => s.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&amp;/g, '&');
  const steps = (JSON.parse(unescape(meta[1])) as string[]).map((s) => s.replaceAll(' -> ', ' → '));
  const svg = raw
    .replace(/<\?xml[^>]*\?>\s*/, '')
    .replace(/<script>[\s\S]*?<\/script>\s*/g, '')
    .replace(/<metadata[\s\S]*?<\/metadata>\s*/, '')
    .replace(' id="viewport"', '')
    // the embedded font subsets get figure-local family names, so they cannot shadow the page's fonts
    .replaceAll("'IBM Plex Sans'", `'figsans-${name}'`)
    .replaceAll("'JetBrains Mono'", `'figmono-${name}'`)
    .replace(/(<svg [^>]*?) width="\d+" height="\d+"/, '$1 class="anim-svg" preserveAspectRatio="xMidYMid meet"');
  ANIM_SVGS.set(name, svg);
  return { steps, poster: +m[2] };
}

function svgSize(file: string): { width?: number; height?: number } {
  try {
    const head = fs.readFileSync(path.join(FIG_DIR, file), 'utf8').slice(0, 600);
    const w = /\bwidth="([\d.]+)"/.exec(head);
    const hh = /\bheight="([\d.]+)"/.exec(head);
    return { width: w ? Math.round(+w[1]) : undefined, height: hh ? Math.round(+hh[1]) : undefined };
  } catch {
    return {};
  }
}

function inlineHtml(children: ElementContent[]): string {
  return unified().use(rehypeStringify).stringify({ type: 'root', children: structuredClone(children) as RootContent[] });
}

class BuildError extends Error {}

// ---------------------------------------------------------------------------------------------
// phase 1: parse, number headings and figures

interface Target {
  kind: 'section' | 'figure';
  doc: string;
  num: string;
  title: string;
}

interface Parsed {
  config: DocConfig;
  title: string;
  tree: Root;
  headings: Heading[];
  figures: number;
}

/** every element id in every document (headings, figures, table cells, ...) */
const ALL_IDS = new Set<string>();

function parse(config: DocConfig, targets: Map<string, Target>): Parsed {
  const source = fs.readFileSync(path.join(SITE_ROOT, config.file), 'utf8');
  const tree = fromHtml(source, { fragment: true }) as Root;
  // drop comments and the whitespace-only text between blocks
  tree.children = tree.children.filter((c) => c.type !== 'comment' && !(c.type === 'text' && !c.value.trim()));
  let title = '';
  const h1 = tree.children.findIndex((c) => isEl(c, 'h1'));
  if (h1 >= 0) {
    title = toString(tree.children[h1] as Element).trim();
    tree.children.splice(h1, 1);
  }
  const headings: Heading[] = [];
  let n2 = 0;
  let n3 = 0;
  let n4 = 0;
  let figs = 0;
  const seen = new Set<string>();
  visit(tree, 'element', (node) => {
    if (node.properties?.id) {
      const anyId = String(node.properties.id);
      if (ALL_IDS.has(anyId)) throw new BuildError(`${config.file}: duplicate id ${anyId}`);
      ALL_IDS.add(anyId);
    }
    const m = /^h([2-4])$/.exec(node.tagName);
    if (m) {
      const id = String(node.properties.id ?? '');
      if (!id) throw new BuildError(`${config.file}: heading without id: "${toString(node)}"`);
      if (seen.has(id)) throw new BuildError(`${config.file}: duplicate id ${id}`);
      seen.add(id);
      const numbered = node.properties.dataNum !== undefined;
      let num: string | undefined;
      if (node.tagName === 'h2') {
        n3 = 0;
        n4 = 0;
        if (numbered) num = String(++n2);
      } else if (node.tagName === 'h3') {
        n4 = 0;
        if (numbered) num = `${n2}.${++n3}`;
      } else if (node.tagName === 'h4' && numbered) {
        num = `${n2}.${n3}.${++n4}`;
      }
      delete node.properties.dataNum;
      const t = toString(node).trim();
      headings.push({ depth: +m[1], id, title: t, html: inlineHtml(node.children), num });
      if (num) targets.set(id, { kind: 'section', doc: config.num, num, title: t });
      else targets.set(id, { kind: 'section', doc: config.num, num: '', title: t });
      return SKIP;
    }
    if (node.tagName === 'figure') {
      const id = String(node.properties.id ?? '');
      if (!id) throw new BuildError(`${config.file}: figure without id`);
      figs++;
      targets.set(id, { kind: 'figure', doc: config.num, num: String(figs), title: '' });
      node.properties.dataFigNum = String(figs);
    }
  });
  return { config, title, tree, headings, figures: figs };
}

// ---------------------------------------------------------------------------------------------
// phase 2 transforms

function resolveRefs(p: Parsed, targets: Map<string, Target>) {
  visit(p.tree, 'element', (node) => {
    if (node.tagName !== 'a') return;
    const href = String(node.properties.href ?? '');
    if (!href.startsWith('#')) return;
    const id = href.slice(1);
    const isRef = cls(node).includes('ref');
    if (id.startsWith('doc-')) {
      if (!DOCS.some((d) => `doc-${d.key}` === id)) throw new BuildError(`${p.config.file}: unknown document link ${href}`);
      node.properties.className = ['xref'];
      return;
    }
    const t = targets.get(id);
    if (!t) {
      if (!ALL_IDS.has(id) || isRef) throw new BuildError(`${p.config.file}: link to missing id ${href} ("${toString(node)}")`);
      node.properties.className = [...cls(node), 'xref'];
      return;
    }
    if (isRef) {
      // keep the lead word the author wrote ("section", "Sections", "Figure"), replace the number
      const old = toString(node);
      const lead = /^([A-Za-z]+\s+)?/.exec(old)?.[1] ?? '';
      if (!t.num) throw new BuildError(`${p.config.file}: ref ${href} points at an unnumbered heading`);
      // a reference into another document names that tab: "section 3.2 in Task planning"
      // class "bare" suppresses the tab name, for ranges and lists whose sentence names the tab once
      const other = t.doc !== p.config.num && !cls(node).includes('bare') ? docByNum(t.doc) : undefined;
      node.children = other ? [text(lead + t.num), text(` in ${other.tab}`)] : [text(lead + t.num)];
      if (other) node.properties.dataXdoc = other.num;
      node.properties.className = t.kind === 'figure' ? ['xref', 'figref'] : ['xref'];
      if (t.title) node.properties.title = t.title;
    } else {
      node.properties.className = [...cls(node), 'xref'];
    }
  });
}

/** "sections 4 in Task planning–5 in Task planning" -> "sections 4–5 in Task planning": in a run of
 *  references into the same other tab joined by "–", ",", "and", "or" or "to", only the last names the tab. */
function mergeXdocRuns(p: Parsed) {
  visit(p.tree, 'element', (node) => {
    const kids = node.children;
    for (let i = 0; i + 2 < kids.length; i++) {
      const a = kids[i];
      const sep = kids[i + 1];
      const b = kids[i + 2];
      if (!isEl(a, 'a') || !isEl(b, 'a') || sep.type !== 'text') continue;
      const da = a.properties.dataXdoc;
      if (!da || da !== b.properties.dataXdoc) continue;
      if (!/^\s*(–|-|,|, and|and|or|to)\s*$/.test((sep as Text).value)) continue;
      if (a.children.length === 2) a.children.pop();
    }
  });
  visit(p.tree, 'element', (node) => {
    if (node.properties?.dataXdoc) delete node.properties.dataXdoc;
  });
}

function repoLinks(p: Parsed) {
  visit(p.tree, 'element', (node) => {
    if (node.tagName !== 'a') return;
    const href = String(node.properties.href ?? '');
    if (/^(sources|scripts|site)\//.test(href) || /\.md$/.test(href)) {
      // repository files are not part of the site; keep the name, drop the link
      node.tagName = 'span';
      node.properties = { className: ['repo-path'], title: `Repository file: ${href}` };
    } else if (/^https?:/.test(href)) {
      node.properties.target = '_blank';
      node.properties.rel = ['noopener'];
    }
  });
}

function renderMath(p: Parsed) {
  visit(p.tree, 'element', (node, index, parent) => {
    if (!cls(node).includes('math') || !parent || index === undefined) return;
    const display = node.tagName === 'div';
    // MathML output: rendered natively by current browsers, no KaTeX stylesheet or fonts to ship
    const html = katex.renderToString(toString(node), { output: 'mathml', displayMode: display, throwOnError: true });
    const frag = fromHtml(html, { fragment: true });
    (parent as Element).children.splice(index, 1, ...(frag.children as ElementContent[]));
    return [SKIP, index + frag.children.length];
  });
}

function frameFigures(p: Parsed) {
  visit(p.tree, 'element', (node) => {
    if (node.tagName !== 'figure') return;
    const num = String(node.properties.dataFigNum);
    delete node.properties.dataFigNum;
    const img = node.children.find((c): c is Element => isEl(c, 'img'));
    const cap = node.children.find((c): c is Element => isEl(c, 'figcaption'));
    if (!img) throw new BuildError(`${p.config.file}: figure ${node.properties.id} has no <img>`);
    const src = String(img.properties.src);
    const file = src.replace(/^figures\//, '');
    if (!fs.existsSync(path.join(FIG_DIR, file))) throw new BuildError(`${p.config.file}: missing figure file ${src}`);
    const name = file.replace(/\.svg$/, '');
    const alt = String(img.properties.alt ?? '');
    const size = svgSize(file);
    const anim = animFigure(file, name);
    if (anim) {
      node.properties.className = ['fig', 'fig-anim'];
      node.properties.dataCaptions = JSON.stringify(anim.steps);
      const btn = (act: string, label: string, title: string) =>
        h('button.anim-btn', { type: 'button', 'data-act': act, title, 'aria-label': title }, label);
      node.children = [
        h('div.anim-stage', { 'data-anim': name, role: 'img', 'aria-label': alt }),
        h('div.anim-bar', [
          btn('reset', '⟲', 'Reset to the first step'),
          btn('prev', '◀', 'Previous step (←)'),
          btn('play', '▶ Play', 'Play / pause (space)'),
          btn('next', '▶|', 'Next step (→)'),
          h('span.anim-count', `Step 1 / ${anim.steps.length}`),
          h('span.anim-dots', anim.steps.map((_, i) => h('button.anim-dot', { type: 'button', 'data-go': String(i), 'aria-label': `Go to step ${i + 1}` }))),
          h('span.anim-view', [
            btn('zoom-out', '−', 'Zoom out (−)'),
            h('span.anim-zoom', '100%'),
            btn('zoom-in', '+', 'Zoom in (+)'),
            btn('fit', 'Fit', 'Fit the whole figure (0)'),
            btn('full', '⛶ Full screen', 'Full screen (F, Esc to exit)'),
          ]),
        ]),
        h('p.anim-caption', { 'aria-live': 'polite' }, anim.steps[0]),
        h('figcaption', [
          h('span.fig-label', `Figure ${num}`),
          h('span.fig-anim-tag', 'Animated'),
          ...((cap?.children ?? [text(alt)]) as ElementContent[]),
          h('span.fig-tools', [
            h('a', { href: `figures/viewer.html#${name}`, target: '_blank', rel: 'noopener' }, 'Gallery viewer (final step)'),
            h('a', { href: src, target: '_blank', rel: 'noopener' }, 'SVG'),
          ]),
        ]),
      ];
      return SKIP;
    }
    node.properties.className = ['fig'];
    node.children = [
      h('button.fig-media', { type: 'button', 'data-zoom': '', 'aria-label': `Enlarge Figure ${num}: ${alt}` }, [
        h('img', { src, alt, width: size.width, height: size.height, loading: 'lazy', decoding: 'async' }),
      ]),
      h('figcaption', [
        h('span.fig-label', `Figure ${num}`),
        ...((cap?.children ?? [text(alt)]) as ElementContent[]),
        h('span.fig-tools', [
          h('a', { href: `figures/viewer.html#${name}`, target: '_blank', rel: 'noopener' }, 'Pan / zoom viewer'),
          h('a', { href: src, target: '_blank', rel: 'noopener' }, 'SVG'),
        ]),
      ]),
    ];
    return SKIP;
  });
}

/** Split text nodes by a regex and replace matches with generated nodes. */
function replaceInText(
  tree: Root,
  re: RegExp,
  make: (m: RegExpExecArray) => ElementContent[] | null,
  skip: Set<string> = NO_LINK_INSIDE,
) {
  visit(tree, (node, index, parent) => {
    if (isEl(node) && skip.has(node.tagName)) return SKIP;
    if (node.type !== 'text' || !parent || index === undefined) return;
    const value = (node as Text).value;
    re.lastIndex = 0;
    let m: RegExpExecArray | null;
    let last = 0;
    const out: ElementContent[] = [];
    let changed = false;
    while ((m = re.exec(value))) {
      const repl = make(m);
      if (!repl) continue;
      if (m.index > last) out.push(text(value.slice(last, m.index)));
      out.push(...repl);
      last = m.index + m[0].length;
      changed = true;
    }
    if (!changed) return;
    if (last < value.length) out.push(text(value.slice(last)));
    (parent as Element).children.splice(index, 1, ...out);
    return [SKIP, index + out.length];
  });
}

function linkDocMentions(p: Parsed) {
  // Documents are named by their tab ("the Task planning tab"), never by number: numbers change
  // when tabs are reordered. Fail the build on a leftover "doc 02".
  replaceInText(p.tree, /\b[Dd]oc (0[1-9])\b/g, (m) => {
    throw new BuildError(`${p.config.file}: "${m[0]}" in text; name the tab instead`);
  });
}

function escapeRe(s: string) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// ---------------------------------------------------------------------------------------------
// type definitions for the hover window (src/data/definitions.yaml + the source snapshots)

interface DeclEntry {
  names: string[];
  from: string;
  file: string;
  /** line prefix, or {start, lines} to take a fixed number of lines (e.g. a template's signature) */
  parts: (string | { start: string; lines: number })[];
  title?: string;
  only_h2?: string[];
  /** limit to sections whose h2 id starts with this (e.g. "pr-" for doc 02) */
  only_prefix?: string | string[];
  /** For code that is not in any snapshot: a sketch reconstructed from call sites, shown with `note`. */
  sketch?: string;
  note?: string;
}
export interface Decl {
  id: string;
  title: string;
  src: string;
  lang: 'cpp' | 'msg';
  code: string;
  lines: number;
  note?: string;
}
interface DeclRule {
  decl: Decl;
  only?: { has(h2: string): boolean };
}
export type DeclIndex = Map<string, DeclRule[]>;

const DECL_MAX_LINES = 280;
const snapshots = new Map<string, string>();

const onlyOf = (e: DeclEntry): DeclRule['only'] =>
  e.only_h2 ? new Set(e.only_h2) : e.only_prefix
      ? { has: (h2: string) => [e.only_prefix!].flat().some((p) => h2.startsWith(p)) }
      : undefined;

const unescapeHtml = (x: string) =>
  x.replace(/<[^>]+>/g, '').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, '&');

function snapshotFile(from: string, file: string): string {
  if (from === 'repo') {
    const f = path.join(REPO_ROOT, file);
    if (!fs.existsSync(f)) throw new BuildError(`definitions: ${f} not found`);
    return fs.readFileSync(f, 'utf8');
  }
  if (from === 'content') {
    // proposed code that exists only in a doc: all its C++ code blocks, in order
    const f = path.join(SITE_ROOT, 'src/content', file);
    if (!fs.existsSync(f)) throw new BuildError(`definitions: content file ${f} not found`);
    const html = fs.readFileSync(f, 'utf8');
    return [...html.matchAll(/<pre><code class="language-cpp">([\s\S]*?)<\/code><\/pre>/g)].map((m) => unescapeHtml(m[1])).join('\n');
  }
  let s = snapshots.get(from);
  if (s === undefined) {
    const f = path.join(REPO_ROOT, 'sources', `repomix-${from}.xml`);
    if (!fs.existsSync(f)) throw new BuildError(`definitions: snapshot ${f} not found`);
    s = fs.readFileSync(f, 'utf8');
    snapshots.set(from, s);
  }
  const head = `<file path="${file}">\n`;
  const a = s.indexOf(head);
  if (a < 0) throw new BuildError(`definitions: ${file} is not in repomix-${from}.xml`);
  return s.slice(a + head.length, s.indexOf('\n</file>', a));
}

/** One declaration: from the line starting with `prefix` (plus the comments/template line above it)
 *  to the first ';' outside braces. */
function extractDecl(src: string, prefix: string, where: string, take?: number): string[] {
  const lines = src.split('\n');
  const i = lines.findIndex((l) => l.trimStart().startsWith(prefix));
  if (i < 0) throw new BuildError(`definitions: "${prefix}" not found in ${where}`);
  let a = i;
  while (a > 0 && /^\s*(\/\/|template\s*<)/.test(lines[a - 1])) a--;
  let depth = 0;
  let j = i;
  if (take !== undefined) {
    const block = lines.slice(a, i + take);
    const ind = Math.min(...block.filter((l) => l.trim()).map((l) => /^ */.exec(l)![0].length));
    return [...block.map((l) => l.slice(ind)), '  // ... (body omitted)'];
  }
  for (; j < lines.length; j++) {
    const code = lines[j].replace(/"(?:[^"\\]|\\.)*"/g, '""').replace(/\/\/.*$/, '');
    for (const ch of code) {
      if (ch === '{') depth++;
      else if (ch === '}') depth--;
    }
    if (depth === 0 && code.includes(';')) break;
  }
  const block = lines.slice(a, j + 1);
  const ind = Math.min(...block.filter((l) => l.trim()).map((l) => /^ */.exec(l)![0].length));
  return block.map((l) => l.slice(ind));
}

const declId = (title: string) => 'decl-' + title.replace(/[^A-Za-z0-9]+/g, '-').replace(/^-|-$/g, '');

function loadDecls(): DeclIndex {
  const cfg = YAML.parse(fs.readFileSync(path.join(SITE_ROOT, 'src/data/definitions.yaml'), 'utf8')) as {
    bare_msgs: string[];
    cpp: DeclEntry[];
  };
  const index: DeclIndex = new Map();
  const add = (name: string, rule: DeclRule) => {
    const list = index.get(name) ?? [];
    list.push(rule);
    index.set(name, list);
  };
  for (const e of cfg.cpp) {
    if (e.sketch !== undefined) {
      if (!e.note) throw new BuildError(`definitions: sketch for ${e.names[0]} needs a note`);
      const code = e.sketch.replace(/\s+$/, '');
      const title = e.title ?? e.names[0];
      const decl: Decl = { id: declId(title), title, src: e.file, lang: 'cpp', code, lines: code.split('\n').length, note: e.note };
      for (const n of e.names) add(n, { decl, only: onlyOf(e) });
      continue;
    }
    const src = snapshotFile(e.from, e.file);
    const blocks = e.parts.map((pt) =>
      typeof pt === 'string'
        ? extractDecl(src, pt, `${e.from}:${e.file}`)
        : extractDecl(src, pt.start, `${e.from}:${e.file}`, pt.lines),
    );
    let lines = blocks.flatMap((b, k) => (k ? ['', ...b] : b));
    const total = lines.length;
    if (total > DECL_MAX_LINES) {
      lines = [...lines.slice(0, DECL_MAX_LINES), `// ... ${total - DECL_MAX_LINES} more lines in ${e.file}`];
    }
    const title = e.title ?? e.names[0];
    const src_ = e.from === 'content' ? `proposed code in ${e.file}` : e.file;
    const decl: Decl = { id: declId(title), title, src: src_, lang: 'cpp', code: lines.join('\n'), lines: total };
    const rule: DeclRule = { decl, only: onlyOf(e) };
    for (const n of e.names) add(n, rule);
  }
  const all = (() => {
    snapshotFile('interfaces', 'interfaces/msg/GaragePose.msg');
    return snapshots.get('interfaces')!;
  })();
  const bare = new Set(cfg.bare_msgs);
  for (const m of all.matchAll(/<file path="(interfaces\/msg\/(\w+)\.msg)">\n([\s\S]*?)\n<\/file>/g)) {
    const [, file, name, body] = m;
    const code = body.replace(/\s+$/, '');
    const decl: Decl = { id: declId(name + 'Msg'), title: `${name}Msg`, src: file, lang: 'msg', code, lines: code.split('\n').length };
    const rule: DeclRule = { decl };
    for (const n of [`${name}Msg`, `${name}Msg[]`, ...(bare.has(name) ? [name, `${name}[]`] : [])]) add(n, rule);
  }
  for (const b of bare) if (!index.has(b)) throw new BuildError(`definitions: bare_msgs ${b} has no interfaces/msg/${b}.msg`);
  return index;
}

function declExact(index: DeclIndex, name: string, h2: string): DeclRule | undefined {
  return index.get(name)?.find((r) => !r.only || r.only.has(h2));
}

const WRAPPERS = /^(?:const\s+)?(?:std::(?:optional|shared_ptr|unique_ptr|vector|set|unordered_set|reference_wrapper)<(.*)>)$/;

/** Exact spelling first; then the same type with decorations removed: `const`, `&`, `*`, `[]`,
 *  std wrappers, lower-case namespace qualifiers, template arguments, and finally `Type::member`
 *  falls back to `Type` (the class shows the member's declaration). */
function declFor(index: DeclIndex, name: string, h2: string): DeclRule | undefined {
  const exact = declExact(index, name, h2);
  if (exact) return exact;
  if (!/^[\w:<>,\s&*\[\]]+$/.test(name) || !/[A-Z]/.test(name)) return undefined;
  let n = name.trim().replace(/^const\s+/, '').replace(/(?:\s*[&*]|\[\])+$/, '');
  for (let m = WRAPPERS.exec(n); m; m = WRAPPERS.exec(n)) n = m[1].trim().replace(/(?:\s*[&*])+$/, '');
  const tries: string[] = [n];
  const unq = n.replace(/^(?:[a-z_][a-z0-9_]*::)+/, '');
  tries.push(unq, unq.replace(/<.*>$/, ''), unq.replace(/<.*?>/g, ''));
  const parts = unq.replace(/<.*?>/g, '').split('::');
  for (let k = parts.length - 1; k >= 1; k--) tries.push(parts.slice(0, k).join('::'));
  for (const t of tries) {
    if (!t || !/^[A-Z]/.test(t)) continue;
    const r = declExact(index, t, h2);
    if (r) return r;
  }
  return undefined;
}

/** ROS .msg highlighting: field types and comments (Shiki has no grammar for it). */
function msgCode(code: string): ElementContent[] {
  const out: ElementContent[] = [];
  code.split('\n').forEach((line, k) => {
    if (k) out.push(text('\n'));
    const hash = line.indexOf('#');
    const body = hash >= 0 ? line.slice(0, hash) : line;
    const cm = hash >= 0 ? line.slice(hash) : '';
    const m = /^(\s*)(\S+)(.*)$/.exec(body);
    if (m) out.push(text(m[1]), h('span.m-t', m[2]), text(m[3]));
    else out.push(text(body));
    if (cm) out.push(h('span.m-c', cm));
  });
  return out;
}

const DECL_OPEN_LINES = 24;

function declTree(decls: Decl[]): Root {
  return {
    type: 'root',
    children: decls.map((d) => {
      const pre =
        d.lang === 'msg'
          ? h('pre.decl-msg', [h('code', msgCode(d.code))])
          : h('pre', [h('code.language-cpp', d.code)]);
      const head = h('div.decl-head', [h('code', d.title), h('span', d.src)]);
      const note = d.note ? [h('p.decl-note', d.note)] : [];
      const body =
        d.lines > DECL_OPEN_LINES
          ? h('details.decl-more', [h('summary', `Show definition (${d.lines} lines)`), pre])
          : pre;
      return h('div.decl', { 'data-decl': d.id }, [head, ...note, body]);
    }),
  };
}

function linkKeywords(p: Parsed, terms: ResolvedTerm[], decls: DeclIndex, usedDecls: Map<string, Decl>) {
  const byCode = new Map<string, ResolvedTerm>();
  const phrases: { phrase: string; term: ResolvedTerm }[] = [];
  for (const t of terms) {
    for (const c of t.code ?? []) byCode.set(c, t);
    for (const ph of t.text ?? []) phrases.push({ phrase: ph, term: t });
  }
  phrases.sort((a, b) => b.phrase.length - a.phrase.length);
  const phraseRe = phrases.length
    ? new RegExp(`(?<![\\w-])(${phrases.map((x) => escapeRe(x.phrase)).join('|')})(?![\\w-])`, 'g')
    : null;
  const phraseMap = new Map(phrases.map((x) => [x.phrase, x.term]));

  let h2 = '';
  let h3 = '';
  let used = new Set<string>();
  const useDecl = (r?: DeclRule) => {
    if (!r) return undefined;
    usedDecls.set(r.decl.id, r.decl);
    return r.decl.id;
  };
  const kwLink = (t: ResolvedTerm, children: ElementContent[], rule?: DeclRule) =>
    h(
      'a.kw',
      {
        href: `#${t.id}`,
        'data-term': t.term,
        'data-def': t.def,
        'data-target': t.targetTitle,
        'data-decl': useDecl(rule ?? (t.decl ? declFor(decls, t.decl, h2) : undefined)),
      },
      children,
    );
  const inTarget = (t: ResolvedTerm) => t.id === h2 || t.id === h3;

  for (const block of p.tree.children) {
    if (isEl(block) && /^h[23]$/.test(block.tagName)) {
      const id = String(block.properties?.id ?? '');
      if (block.tagName === 'h2') {
        h2 = id;
        h3 = '';
      } else h3 = id;
      used = new Set();
      continue;
    }
    if (!isEl(block)) continue;
    visit(block, 'element', (node, index, parent) => {
      if (['pre', 'a', 'summary'].includes(node.tagName) || /^h\d$/.test(node.tagName)) return SKIP;
      if (node.tagName !== 'code' || !parent || index === undefined) return;
      const spelling = toString(node).trim();
      const rule = declFor(decls, spelling, h2);
      // a section-specific definition (e.g. DagBase's Vertex) also turns off the glossary link
      const t = rule?.only ? undefined : byCode.get(spelling);
      if (t && !used.has(t.term) && !inTarget(t)) {
        used.add(t.term);
        (parent as Element).children[index] = kwLink(t, [node], rule);
      } else if (rule) {
        (parent as Element).children[index] = h('span.ty', { tabindex: 0, 'data-decl': useDecl(rule) }, [node]);
      }
      return SKIP;
    });
    if (phraseRe) {
      const holder: Root = { type: 'root', children: [block] };
      replaceInText(holder, phraseRe, (m) => {
        const t = phraseMap.get(m[1]);
        if (!t || used.has(t.term) || inTarget(t)) return null;
        used.add(t.term);
        return [kwLink(t, [text(m[1])])];
      });
    }
  }
}

/** Code blocks (after highlighting): the first mention of each type with a known definition in a
 *  block becomes a hover/tap target, like inline code mentions (span.ty). Only identifiers that
 *  start with an upper-case letter are considered (types, messages, classes, enum-like names). */
function linkCodeTypes(tree: Root, decls: DeclIndex, usedDecls: Map<string, Decl>) {
  let h2 = '';
  const ID = /[A-Z][A-Za-z0-9_]*/g;
  for (const block of tree.children) {
    if (isEl(block, 'h2')) {
      h2 = String(block.properties?.id ?? '');
      continue;
    }
    // a highlighted top-level <pre> comes back from Shiki wrapped in a root node, so walk any node
    visit(block as Root, 'element', (pre) => {
      if (pre.tagName !== 'pre') return;
      if ((pre.properties?.className as string[] | undefined)?.includes('decl-msg')) return SKIP;
      const seen = new Set<string>();
      visit(pre, 'text', (node, index, parent) => {
        if (!parent || index === undefined || (parent as Element).tagName === 'a') return;
        if (isEl(parent as Element) && ((parent as Element).properties?.className as string[] | undefined)?.includes('ty')) return;
        const v = node.value;
        const out: ElementContent[] = [];
        let last = 0;
        for (const m of v.matchAll(ID)) {
          const name = m[0];
          const prev = v[m.index! - 1];
          if (prev && /[\w]/.test(prev)) continue;
          if (seen.has(name)) continue;
          const rule = declFor(decls, name, h2);
          if (!rule) continue;
          seen.add(name);
          usedDecls.set(rule.decl.id, rule.decl);
          if (m.index! > last) out.push(text(v.slice(last, m.index)));
          out.push(h('span.ty.ty-code', { tabindex: 0, 'data-decl': rule.decl.id }, name));
          last = m.index! + name.length;
        }
        if (!out.length) return;
        if (last < v.length) out.push(text(v.slice(last)));
        (parent as Element).children.splice(index, 1, ...out);
        return index + out.length;
      });
      return SKIP;
    });
  }
}

function wrapTables(p: Parsed) {
  visit(p.tree, 'element', (node, index, parent) => {
    if (node.tagName !== 'table' || !parent || index === undefined) return;
    (parent as Element).children[index] = h('div.table-wrap', { tabindex: 0, role: 'region', 'aria-label': 'Table' }, [node]);
    return SKIP;
  });
}

function decorateHeadings(p: Parsed) {
  const byId = new Map(p.headings.map((x) => [x.id, x]));
  visit(p.tree, 'element', (node) => {
    if (!/^h[2-4]$/.test(node.tagName)) return;
    const id = String(node.properties.id);
    const hd = byId.get(id);
    if (hd?.num) node.children.unshift(h('span.secnum', hd.num));
    node.children.push(h('a.anchor', { href: `#${id}`, 'aria-label': 'Link to this section' }, '#'));
    return SKIP;
  });
}

function insertPartDividers(p: Parsed) {
  const parts = p.config.parts;
  if (!parts) return;
  const nums = new Map(p.headings.filter((x) => x.depth === 2).map((x) => [x.id, x.num]));
  const kids = p.tree.children;
  parts.forEach((pt, k) => {
    const i = kids.findIndex((c) => isEl(c, 'h2') && c.properties.id === pt.first);
    if (i < 0) throw new BuildError(`${p.config.file}: part "${pt.title}" starts at missing heading ${pt.first}`);
    const from = nums.get(pt.first);
    const nextFirst = parts[k + 1]?.first;
    const h2s = p.headings.filter((x) => x.depth === 2 && x.num);
    const to = nextFirst ? Number(nums.get(nextFirst)) - 1 : Number(h2s[h2s.length - 1].num);
    pt.range = `${from}–${to}`;
    kids.splice(
      i,
      0,
      h('div.part', { id: `${p.config.prefix}-part-${k + 1}` }, [
        h('span.part-num', `Part ${['I', 'II', 'III', 'IV', 'V'][k]}`),
        h('span.part-title', pt.title),
        h('span.part-range', `Sections ${pt.range}`),
      ]),
    );
  });
}

// ---------------------------------------------------------------------------------------------
// public

let cache: { docs: RenderedDoc[]; terms: ResolvedTerm[]; decls: string } | undefined;

export async function renderAll(): Promise<{ docs: RenderedDoc[]; terms: ResolvedTerm[]; decls: string }> {
  if (cache) return cache;
  const targets = new Map<string, Target>();
  const parsed = DOCS.map((d) => parse(d, targets));

  const glossary = YAML.parse(fs.readFileSync(path.join(SITE_ROOT, 'src/data/glossary.yaml'), 'utf8')) as GlossaryEntry[];
  const terms: ResolvedTerm[] = glossary.map((g) => {
    const t = targets.get(g.to);
    if (!t || t.kind !== 'section') throw new BuildError(`glossary: "${g.term}" points at missing heading ${g.to}`);
    return { ...g, id: g.to, doc: t.doc, targetTitle: (t.num ? `${t.num} ` : '') + t.title };
  });

  const declIndex = loadDecls();
  for (const g of glossary) {
    if (g.decl && !declIndex.has(g.decl)) throw new BuildError(`glossary: "${g.term}" decl ${g.decl} has no definition`);
  }
  const usedDecls = new Map<string, Decl>();

  const out: RenderedDoc[] = [];
  for (const p of parsed) {
    resolveRefs(p, targets);
    mergeXdocRuns(p);
    repoLinks(p);
    renderMath(p);
    frameFigures(p);
    linkDocMentions(p);
    linkKeywords(p, terms, declIndex, usedDecls);
    wrapTables(p);
    decorateHeadings(p);
    insertPartDividers(p);
    const proc = unified()
      .use(rehypeShiki, {
        themes: { dark: 'github-dark-default', light: 'github-light-default' },
        defaultColor: false,
        fallbackLanguage: 'text',
      })
      .use(rehypeStringify);
    const tree = (await proc.run(p.tree)) as Root;
    linkCodeTypes(tree, declIndex, usedDecls);
    // inline the animated SVGs last, so no text pass (keywords, links) ever touches them
    const html = proc.stringify(tree).replace(/<div class="anim-stage" data-anim="([^"]+)"([^>]*)><\/div>/g, (m0, name, rest) => {
      const svg = ANIM_SVGS.get(name);
      if (!svg) throw new BuildError(`animated figure ${name}: SVG not prepared`);
      return `<div class="anim-stage" data-anim="${name}"${rest}>${svg}</div>`;
    });
    out.push({ config: p.config, title: p.title, html, headings: p.headings, figureCount: p.figures });
  }
  const shiki = unified()
    .use(rehypeShiki, {
      themes: { dark: 'github-dark-default', light: 'github-light-default' },
      defaultColor: false,
      fallbackLanguage: 'text',
    })
    .use(rehypeStringify);
  const dtree = (await shiki.run(declTree([...usedDecls.values()]))) as Root;
  cache = { docs: out, terms, decls: shiki.stringify(dtree) };
  return cache;
}

