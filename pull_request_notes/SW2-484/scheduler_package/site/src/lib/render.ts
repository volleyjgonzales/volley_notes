/**
 * Markdown -> HTML for the study site.
 *
 * Two phases, because links can point across documents:
 *   1. parse every document to a HAST tree and give every heading a stable, prefixed id;
 *   2. with all headings known, rewrite links, link section / figure references and keywords,
 *      wrap figures, highlight code, and serialise.
 */
import fs from 'node:fs';
import path from 'node:path';
import { unified } from 'unified';
import remarkParse from 'remark-parse';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import remarkRehype from 'remark-rehype';
import rehypeRaw from 'rehype-raw';
import rehypeShiki from '@shikijs/rehype';
import rehypeStringify from 'rehype-stringify';
import GithubSlugger from 'github-slugger';
import { visit, SKIP } from 'unist-util-visit';
import { toString } from 'hast-util-to-string';
import { h } from 'hastscript';
import YAML from 'yaml';
import type { Root, Element, ElementContent, Text, RootContent } from 'hast';
import { DOCS, docByFile, docByNum, type DocConfig } from '../data/docs';

export const REPO_ROOT = path.resolve(process.cwd(), '..');
const FIG_DIR = path.join(REPO_ROOT, 'figures');

export interface Heading {
  depth: number;
  id: string;
  text: string;
  html: string;
  num?: string;
  title: string;
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
const isBlank = (n: RootContent | ElementContent) => n.type === 'text' && !n.value.trim();
const text = (value: string): Text => ({ type: 'text', value });
const NO_LINK_INSIDE = new Set(['math', 'a', 'code', 'pre', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'button', 'summary']);

function stripTocAndTitle(md: string): { title: string; body: string } {
  const lines = md.split('\n');
  let title = '';
  if (lines[0].startsWith('# ')) title = lines.shift()!.slice(2).trim();
  const start = lines.findIndex((l) => /^## Contents\s*$/.test(l));
  const end = lines.findIndex((l) => l.trim() === '<!-- /toc -->');
  if (start >= 0 && end > start) lines.splice(start, end - start + 1);
  return { title, body: lines.join('\n') };
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

/** Inline HTML for a heading's content (keeps `code` formatting in the sidebar). */
function inlineHtml(node: Element): string {
  const clone: Root = { type: 'root', children: structuredClone(node.children) as RootContent[] };
  return unified().use(rehypeStringify).stringify(clone);
}

// ---------------------------------------------------------------------------------------------
// phase 1

interface Parsed {
  config: DocConfig;
  title: string;
  tree: Root;
  headings: Heading[];
}

function parse(config: DocConfig): Parsed {
  const raw = fs.readFileSync(path.join(REPO_ROOT, config.file), 'utf8');
  const { title, body } = stripTocAndTitle(raw);
  const proc = unified()
    .use(remarkParse)
    .use(remarkGfm)
    .use(remarkMath)
    .use(remarkRehype, { allowDangerousHtml: true })
    .use(rehypeRaw)
    // MathML output: rendered natively by current browsers, no KaTeX stylesheet or fonts to ship
    .use(rehypeKatex, { output: 'mathml', throwOnError: false });
  const tree = proc.runSync(proc.parse(body)) as Root;
  const slugger = new GithubSlugger();
  const headings: Heading[] = [];
  visit(tree, 'element', (node) => {
    const m = /^h([2-4])$/.exec(node.tagName);
    if (!m) return;
    const t = toString(node).trim();
    const id = `${config.prefix}-${slugger.slug(t)}`;
    node.properties = { ...node.properties, id };
    const num = /^(\d+(?:\.\d+)?)\.?\s/.exec(t)?.[1];
    headings.push({ depth: +m[1], id, text: t, html: inlineHtml(node), num, title: num ? t.slice(t.indexOf(' ') + 1) : t });
  });
  return { config, title, tree, headings };
}

// ---------------------------------------------------------------------------------------------
// phase 2 transforms

type Registry = Map<string, Parsed>; // by doc num

function sectionId(reg: Registry, docNum: string, num: string): string | undefined {
  return reg.get(docNum)?.headings.find((hd) => hd.num === num)?.id;
}

function resolveTarget(reg: Registry, to: string): { id: string; doc: string; title: string } | undefined {
  const m = /^(0[123])([#:])(.+)$/.exec(to);
  if (!m) return undefined;
  const doc = reg.get(m[1]);
  if (!doc) return undefined;
  const norm = (s: string) => s.replace(/[`*]/g, '').toLowerCase();
  const hd =
    m[2] === '#'
      ? doc.headings.find((x) => x.num === m[3])
      : doc.headings.find((x) => norm(x.text).includes(norm(m[3])));
  return hd ? { id: hd.id, doc: m[1], title: hd.text } : undefined;
}

/** Wrap `![..](figures/x.svg)` + pan/zoom line + caption paragraph into <figure>. */
function wrapFigures(p: Parsed): number {
  const kids = p.tree.children;
  let count = 0;
  for (let i = 0; i < kids.length; i++) {
    const para = kids[i];
    if (!isEl(para, 'p')) continue;
    const content = para.children.filter((c) => !isBlank(c));
    if (content.length !== 1 || !isEl(content[0], 'img')) continue;
    const img = content[0];
    const src = String(img.properties?.src ?? '');
    if (!src.startsWith('figures/')) continue;
    const file = src.slice('figures/'.length);
    const name = file.replace(/\.svg$/, '');
    // following siblings: optional <p><sub>Pan / zoom ...</sub></p>, then the caption paragraph
    let j = i + 1;
    const next = () => {
      while (j < kids.length && isBlank(kids[j])) j++;
      return kids[j];
    };
    let n = next();
    if (isEl(n, 'p') && n.children.some((c) => isEl(c, 'sub'))) {
      j++;
      n = next();
    }
    let caption: ElementContent[] | undefined;
    let label = '';
    if (isEl(n, 'p')) {
      const first = n.children[0];
      const lead = isEl(first) && (first.tagName === 'em' || first.tagName === 'strong') ? first : undefined;
      const leadText = lead ? toString(lead) : '';
      const lm = /^Figure (\d+)\s*—\s*/.exec(leadText);
      if (lead && lm) {
        label = `Figure ${lm[1]}`;
        // strip the "Figure N — " prefix from the first text inside the lead element
        let stripped = false;
        visit(lead, 'text', (t: Text) => {
          if (stripped) return;
          t.value = t.value.replace(/^Figure \d+\s*—\s*/, '');
          stripped = true;
        });
        // doc 01: the whole caption is <em>; unwrap it. docs 02/03: keep the bold title.
        caption = lead.tagName === 'em' ? [...lead.children, ...n.children.slice(1)] : n.children;
        j++;
      }
    }
    count++;
    const figNum = label ? label.split(' ')[1] : String(count);
    const size = svgSize(file);
    const alt = String(img.properties?.alt ?? label);
    const fig = h('figure.fig', { id: `${p.config.prefix}-fig-${figNum}` }, [
      h(
        'button.fig-media',
        { type: 'button', 'data-zoom': '', 'aria-label': `Enlarge ${label || 'figure'}: ${alt}` },
        [h('img', { src, alt, width: size.width, height: size.height, loading: 'lazy', decoding: 'async' })],
      ),
      h('figcaption', [
        label ? h('span.fig-label', label) : text(''),
        ...(caption ?? [text(alt)]),
        h('span.fig-tools', [
          h('a', { href: `figures/viewer.html#${name}`, target: '_blank', rel: 'noopener' }, 'Pan / zoom viewer'),
          h('a', { href: src, target: '_blank', rel: 'noopener' }, 'SVG'),
        ]),
      ]),
    ]);
    kids.splice(i, j - i, fig);
  }
  return count;
}

function rewriteLinks(p: Parsed, reg: Registry) {
  visit(p.tree, 'element', (node) => {
    if (node.tagName !== 'a') return;
    const href = String(node.properties?.href ?? '');
    const m = /^(0[123]-[\w-]+\.md)?(#(.*))?$/.exec(href);
    if (m && (m[1] || m[2])) {
      const target = m[1] ? docByFile(m[1]) : p.config;
      if (!target) return;
      if (m[3]) {
        // GitHub anchors from add_toc.py; ours use github-slugger on the same text, so only the prefix differs
        const want = `${target.prefix}-${m[3]}`;
        const t = reg.get(target.num)?.headings.find((x) => x.id === want);
        node.properties.href = `#${t ? t.id : want}`;
      } else {
        node.properties.href = `#doc-${target.key}`;
      }
      node.properties.className = ['xref'];
      return;
    }
    if (/^(sources|scripts)\//.test(href) || href === 'README.md') {
      // repository files are not part of the site; keep the name, drop the link
      node.tagName = 'span';
      node.properties = { className: ['repo-path'], title: `Repository file: ${href}` };
      return;
    }
    if (/^https?:/.test(href)) {
      node.properties.target = '_blank';
      node.properties.rel = ['noopener'];
    }
  });
}

/** Split text nodes by a regex and replace matches with generated nodes. */
function replaceInText(
  tree: Root,
  re: RegExp,
  make: (m: RegExpExecArray, parent: Element | Root, index: number, node: Text) => ElementContent[] | null,
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
      const repl = make(m, parent as Element, index, node as Text);
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

const SECTION_RE =
  /\b(?:([Dd]oc) (0[123])(?:,? \(?| )?)?([Ss]ections?) (\d+(?:\.\d+)?(?:(?:, | and | or |–| to )\d+(?:\.\d+)?)*)/g;

function linkSectionRefs(p: Parsed, reg: Registry) {
  replaceInText(p.tree, SECTION_RE, (m, parent, index, node) => {
    let docNum = m[2] ?? p.config.num;
    // "sections 7–10 and 16 of [01 — ...](01-...md)": the target doc is named by the following link
    if (!m[2]) {
      const after = node.value.slice(m.index + m[0].length);
      const sib = (parent as Element).children[index + 1];
      if (/^ of \[?$/.test(after) || /^ of $/.test(after)) {
        const href = isEl(sib, 'a') ? String(sib.properties?.href ?? '') : '';
        const d = DOCS.find((x) => href.startsWith(`#doc-${x.key}`) || href.startsWith(x.file) || href.startsWith(`#${x.prefix}-`));
        if (d) docNum = d.num;
      }
    }
    const lead = m[0].slice(0, m[0].length - m[4].length);
    const nums = m[4];
    const parts: ElementContent[] = [];
    const single = /^\d+(?:\.\d+)?$/.test(nums);
    if (single) {
      const id = sectionId(reg, docNum, nums);
      if (!id) return null;
      return [h('a.xref', { href: `#${id}` }, m[0])];
    }
    parts.push(text(lead));
    let last = 0;
    const numRe = /\d+(?:\.\d+)?/g;
    let k: RegExpExecArray | null;
    while ((k = numRe.exec(nums))) {
      if (k.index > last) parts.push(text(nums.slice(last, k.index)));
      const id = sectionId(reg, docNum, k[0]);
      parts.push(id ? h('a.xref', { href: `#${id}` }, k[0]) : text(k[0]));
      last = k.index + k[0].length;
    }
    if (last < nums.length) parts.push(text(nums.slice(last)));
    return parts;
  });
}

/** "(6.1)" style references to numbered subsections of the same document. */
function linkParenRefs(p: Parsed, reg: Registry) {
  replaceInText(p.tree, /\((\d+\.\d+)\)/g, (m) => {
    const id = sectionId(reg, p.config.num, m[1]);
    if (!id) return null;
    return [text('('), h('a.xref', { href: `#${id}` }, m[1]), text(')')];
  });
}

function linkFigureRefs(p: Parsed) {
  const re = /\bFigures? (\d+)((?:(?:, | and | or |–)\d+)*)/g;
  replaceInText(p.tree, re, (m) => {
    const out: ElementContent[] = [];
    const word = m[0].startsWith('Figures') ? 'Figures ' : 'Figure ';
    out.push(text(word));
    const rest = m[0].slice(word.length);
    let last = 0;
    const numRe = /\d+/g;
    let k: RegExpExecArray | null;
    while ((k = numRe.exec(rest))) {
      if (k.index > last) out.push(text(rest.slice(last, k.index)));
      out.push(h('a.xref.figref', { href: `#${p.config.prefix}-fig-${k[0]}` }, k[0]));
      last = k.index + k[0].length;
    }
    if (last < rest.length) out.push(text(rest.slice(last)));
    return out;
  }, new Set([...NO_LINK_INSIDE, 'figcaption']));
}

function linkDocMentions(p: Parsed) {
  replaceInText(p.tree, /\b[Dd]oc (0[123])\b/g, (m) => {
    const d = docByNum(m[1]);
    if (!d || d.num === p.config.num) return null;
    return [h('a.xref.docref', { href: `#doc-${d.key}` }, m[0])];
  });
}

function escapeRe(s: string) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function linkKeywords(p: Parsed, terms: ResolvedTerm[]) {
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
  const kwLink = (t: ResolvedTerm, children: ElementContent[]) =>
    h('a.kw', { href: `#${t.id}`, 'data-term': t.term, 'data-def': t.def, 'data-target': t.targetTitle }, children);
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
    // inline code
    visit(block, 'element', (node, index, parent) => {
      if (node.tagName === 'pre' || node.tagName === 'a' || /^h\d$/.test(node.tagName)) return SKIP;
      if (node.tagName !== 'code' || !parent || index === undefined) return;
      const t = byCode.get(toString(node).trim());
      if (!t || used.has(t.term) || inTarget(t)) return SKIP;
      used.add(t.term);
      (parent as Element).children[index] = kwLink(t, [node]);
      return SKIP;
    });
    // plain-text phrases
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
    if (isEl(parent) && (parent as Element).properties?.className?.toString().includes('table-wrap')) return;
    (parent as Element).children[index] = h('div.table-wrap', { tabindex: 0, role: 'region', 'aria-label': 'Table' }, [node]);
    return SKIP;
  });
}

function decorateHeadings(p: Parsed) {
  visit(p.tree, 'element', (node) => {
    if (!/^h[2-4]$/.test(node.tagName)) return;
    const id = String(node.properties.id);
    const t = toString(node);
    const num = /^(\d+(?:\.\d+)?)\.?\s/.exec(t);
    if (num) {
      // move the number into its own span so it can be styled
      const first = node.children[0];
      if (first && first.type === 'text') {
        first.value = first.value.slice(num[0].length);
        node.children.unshift(h('span.secnum', num[1]));
      }
    }
    node.children.push(h('a.anchor', { href: `#${id}`, 'aria-label': `Link to this section` }, '#'));
    return SKIP;
  });
}

function insertPartDividers(p: Parsed) {
  if (!p.config.parts) return;
  const kids = p.tree.children;
  for (let i = 0; i < kids.length; i++) {
    const k = kids[i];
    if (!isEl(k, 'h2')) continue;
    const n = /^(\d+)\./.exec(toString(k));
    const part = n && p.config.parts.findIndex((pt) => pt.from === +n[1]);
    if (part === null || part === undefined || part < 0) continue;
    const pt = p.config.parts[part];
    kids.splice(
      i,
      0,
      h('div.part', { id: `${p.config.prefix}-part-${part + 1}` }, [
        h('span.part-num', `Part ${['I', 'II', 'III', 'IV', 'V'][part]}`),
        h('span.part-title', pt.title),
        h('span.part-range', `Sections ${pt.from}–${pt.to}`),
      ]),
    );
    i++;
  }
}

// ---------------------------------------------------------------------------------------------
// public

let cache: { docs: RenderedDoc[]; terms: ResolvedTerm[] } | undefined;

export async function renderAll(): Promise<{ docs: RenderedDoc[]; terms: ResolvedTerm[] }> {
  if (cache) return cache;
  const reg: Registry = new Map();
  for (const d of DOCS) reg.set(d.num, parse(d));

  const glossary = YAML.parse(fs.readFileSync(path.join(process.cwd(), 'src/data/glossary.yaml'), 'utf8')) as GlossaryEntry[];
  const terms: ResolvedTerm[] = [];
  for (const g of glossary) {
    const t = resolveTarget(reg, g.to);
    if (!t) throw new Error(`glossary: cannot resolve target "${g.to}" for "${g.term}"`);
    terms.push({ ...g, id: t.id, doc: t.doc, targetTitle: t.title });
  }

  const out: RenderedDoc[] = [];
  for (const d of DOCS) {
    const p = reg.get(d.num)!;
    const figs = wrapFigures(p);
    rewriteLinks(p, reg);
    linkSectionRefs(p, reg);
    linkParenRefs(p, reg);
    linkFigureRefs(p);
    linkDocMentions(p);
    linkKeywords(p, terms);
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
    out.push({ config: d, title: p.title, html: proc.stringify(tree), headings: p.headings, figureCount: figs });
  }
  cache = { docs: out, terms };
  return cache;
}
