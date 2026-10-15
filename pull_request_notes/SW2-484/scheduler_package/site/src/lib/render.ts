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
        if (numbered) num = String(++n2);
      } else if (node.tagName === 'h3' && numbered) {
        num = `${n2}.${++n3}`;
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
      node.children = [text(lead + t.num)];
      node.properties.className = t.kind === 'figure' ? ['xref', 'figref'] : ['xref'];
      if (t.title) node.properties.title = t.title;
    } else {
      node.properties.className = [...cls(node), 'xref'];
    }
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
  replaceInText(p.tree, /\b[Dd]oc (0[1-4])\b/g, (m) => {
    const d = docByNum(m[1]);
    if (!d || d.num === p.config.num) return null;
    return [h('a.xref.docref', { href: `#doc-${d.key}` }, m[0])];
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
  parts: string[];
  title?: string;
  only_h2?: string[];
}
export interface Decl {
  id: string;
  title: string;
  src: string;
  lang: 'cpp' | 'msg';
  code: string;
  lines: number;
}
interface DeclRule {
  decl: Decl;
  only?: Set<string>;
}
export type DeclIndex = Map<string, DeclRule[]>;

const DECL_MAX_LINES = 160;
const snapshots = new Map<string, string>();

function snapshotFile(from: string, file: string): string {
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
function extractDecl(src: string, prefix: string, where: string): string[] {
  const lines = src.split('\n');
  const i = lines.findIndex((l) => l.trimStart().startsWith(prefix));
  if (i < 0) throw new BuildError(`definitions: "${prefix}" not found in ${where}`);
  let a = i;
  while (a > 0 && /^\s*(\/\/|template\s*<)/.test(lines[a - 1])) a--;
  let depth = 0;
  let j = i;
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
    const src = snapshotFile(e.from, e.file);
    const blocks = e.parts.map((pfx) => extractDecl(src, pfx, `${e.from}:${e.file}`));
    let lines = blocks.flatMap((b, k) => (k ? ['', ...b] : b));
    const total = lines.length;
    if (total > DECL_MAX_LINES) {
      lines = [...lines.slice(0, DECL_MAX_LINES), `// ... ${total - DECL_MAX_LINES} more lines in ${e.file}`];
    }
    const title = e.title ?? e.names[0];
    const decl: Decl = { id: declId(title), title, src: e.file, lang: 'cpp', code: lines.join('\n'), lines: total };
    const rule: DeclRule = { decl, only: e.only_h2 ? new Set(e.only_h2) : undefined };
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

function declFor(index: DeclIndex, name: string, h2: string): DeclRule | undefined {
  return index.get(name)?.find((r) => !r.only || r.only.has(h2));
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
      const body =
        d.lines > DECL_OPEN_LINES
          ? h('details.decl-more', [h('summary', `Show definition (${d.lines} lines)`), pre])
          : pre;
      return h('div.decl', { 'data-decl': d.id }, [head, body]);
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
    out.push({ config: p.config, title: p.title, html: proc.stringify(tree), headings: p.headings, figureCount: p.figures });
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

