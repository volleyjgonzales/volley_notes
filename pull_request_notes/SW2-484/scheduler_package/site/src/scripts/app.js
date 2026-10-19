// Scheduler Refactor Study — client behaviour (plain JS, inlined into index.html at build time).
// Tabs and deep links: the URL hash is always an element id ("doc-<key>" for a tab, or a heading / figure id).
(() => {
  'use strict';
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const store = {
    get(k) {
      try {
        return localStorage.getItem(k);
      } catch (e) {
        return null;
      }
    },
    set(k, v) {
      try {
        localStorage.setItem(k, v);
      } catch (e) {}
    },
  };

  const docs = $$('.doc');
  const tabs = $$('.tab');
  const tocs = $$('.toc');
  const rails = $$('.rail-section');
  const scrollMemory = {};
  let current = null; // active doc key
  let headings = []; // h2/h3/h4 of the active doc
  let activeH2 = null;

  // ---------------------------------------------------------------- tabs
  function activate(key) {
    if (current === key) return false;
    if (current) scrollMemory[current] = window.scrollY;
    current = key;
    for (const d of docs) d.hidden = d.dataset.doc !== key;
    for (const t of tabs) t.setAttribute('aria-selected', String(t.dataset.doc === key));
    for (const t of tocs) t.hidden = t.dataset.doc !== key;
    headings = $$(`#doc-${key} .prose h2[id], #doc-${key} .prose h3[id], #doc-${key} .prose h4[id]`);
    activeH2 = null;
    for (const r of rails) r.hidden = true;
    applyFilter();
    store.set('study-doc', key);
    return true;
  }

  function scrollToEl(el, smooth) {
    const y = el.getBoundingClientRect().top + window.scrollY - (topbarHeight() + 12);
    window.scrollTo({ top: Math.max(0, y), behavior: smooth && !reduceMotion ? 'smooth' : 'auto' });
  }
  function topbarHeight() {
    return $('.topbar').getBoundingClientRect().height;
  }

  function route(smooth) {
    const id = decodeURIComponent(location.hash.slice(1));
    if (!id) {
      const remembered = store.get('study-doc');
      activate(docs.some((d) => d.dataset.doc === remembered) ? remembered : docs[0].dataset.doc);
      onScroll();
      return;
    }
    const el = document.getElementById(id);
    if (!el) return;
    const doc = el.classList.contains('doc') ? el : el.closest('.doc');
    if (!doc) return;
    const switched = activate(doc.dataset.doc);
    if (el === doc) {
      window.scrollTo({ top: switched ? scrollMemory[doc.dataset.doc] || 0 : 0 });
    } else {
      // figures and images above may still be loading; scroll now and once more after layout settles
      scrollToEl(el, smooth && !switched);
      if (switched) {
        // late layout shifts (web fonts, images) can move the target; settle once more unless the reader scrolled
        const y0 = window.scrollY;
        requestAnimationFrame(() => scrollToEl(el, false));
        setTimeout(() => {
          if (Math.abs(window.scrollY - y0) < 4 || Math.abs(el.getBoundingClientRect().top - topbarHeight() - 16) < 400)
            scrollToEl(el, false);
        }, 450);
      }
      el.classList.remove('target-flash');
      void el.offsetWidth;
      el.classList.add('target-flash');
      revealInToc(id);
    }
    closeNav();
    onScroll();
  }

  // in-page links: push history ourselves so links into hidden tabs work and repeat clicks re-scroll
  document.addEventListener('click', (e) => {
    const a = e.target.closest('a[href^="#"]');
    if (!a || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey) return;
    const id = a.getAttribute('href').slice(1);
    if (!id || !document.getElementById(id)) return;
    e.preventDefault();
    if (location.hash.slice(1) !== id) history.pushState(null, '', '#' + id);
    route(true);
  });
  window.addEventListener('popstate', () => route(false));
  window.addEventListener('hashchange', () => route(false));

  // ---------------------------------------------------------------- scroll spy
  let ticking = false;
  function onScroll() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => {
      ticking = false;
      spy();
      progress();
    });
  }
  function spy() {
    if (!headings.length) return;
    const line = topbarHeight() + Math.min(160, window.innerHeight * 0.25);
    let h2 = null;
    let sub = null;
    for (const h of headings) {
      if (h.getBoundingClientRect().top > line) break;
      if (h.tagName === 'H2') {
        h2 = h;
        sub = null;
      } else sub = h;
    }
    const toc = tocs.find((t) => t.dataset.doc === current);
    if (!toc) return;
    const h3 = sub && sub.tagName === 'H4' ? findParentH3(sub) : sub;
    $$('.toc-h2.active, .toc-h3.active', toc).forEach((n) => n.classList.remove('active'));
    if (h2) {
      const li = $(`.toc-h2[data-id="${h2.id}"]`, toc);
      if (li) {
        li.classList.add('active');
        if (h2 !== activeH2) {
          // auto-expand the current section, collapse the one we left (unless filtering)
          $$('.toc-h2.open.auto', toc).forEach((n) => {
            if (n !== li) setOpen(n, false);
          });
          if (!li.classList.contains('open')) {
            setOpen(li, true);
            li.classList.add('auto');
          }
        }
        if (h3) $(`.toc-h3[data-id="${h3.id}"]`, li)?.classList.add('active');
        keepVisible(h3 ? $(`.toc-h3[data-id="${h3.id}"]`, li) || li : li);
      }
    }
    if (h2 !== activeH2) {
      activeH2 = h2;
      for (const r of rails) r.hidden = !(h2 && r.dataset.h2 === h2.id && r.dataset.doc === current);
    }
    const rail = rails.find((r) => !r.hidden);
    if (rail) {
      $$('a.active', rail).forEach((a) => a.classList.remove('active'));
      if (sub) $(`a[data-id="${sub.id}"]`, rail)?.classList.add('active');
    }
  }
  function findParentH3(h4) {
    const i = headings.indexOf(h4);
    for (let j = i - 1; j >= 0; j--) {
      if (headings[j].tagName === 'H3') return headings[j];
      if (headings[j].tagName === 'H2') return null;
    }
    return null;
  }
  function keepVisible(el) {
    const box = $('#sidebar-scroll');
    if (!el || !box) return;
    const r = el.getBoundingClientRect();
    const b = box.getBoundingClientRect();
    if (r.top < b.top + 8 || r.bottom > b.bottom - 8) box.scrollTop += r.top - b.top - b.height / 3;
  }
  function revealInToc(id) {
    const toc = tocs.find((t) => t.dataset.doc === current);
    const li = toc && $(`[data-id="${CSS.escape(id)}"]`, toc);
    if (li && li.classList.contains('toc-h3')) setOpen(li.closest('.toc-h2'), true);
  }
  function progress() {
    const doc = docs.find((d) => !d.hidden);
    const bar = $('#progress-bar');
    if (!doc || !bar) return;
    const total = doc.offsetHeight - window.innerHeight;
    const p = total > 0 ? Math.min(1, Math.max(0, (window.scrollY - doc.offsetTop + 80) / total)) : 0;
    bar.style.width = (p * 100).toFixed(2) + '%';
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll);

  // ---------------------------------------------------------------- sidebar: toggles and filter
  function setOpen(li, open) {
    if (!li) return;
    li.classList.toggle('open', open);
    li.classList.remove('auto');
    const b = $('.toc-toggle', li);
    if (b) b.setAttribute('aria-expanded', String(open));
  }
  document.addEventListener('click', (e) => {
    const b = e.target.closest('.toc-toggle');
    if (!b) return;
    const li = b.closest('.toc-h2');
    setOpen(li, !li.classList.contains('open'));
  });
  const filter = $('#toc-filter');
  function applyFilter() {
    const q = (filter.value || '').trim().toLowerCase();
    const toc = tocs.find((t) => t.dataset.doc === current);
    if (!toc) return;
    let any = false;
    for (const li of $$('.toc-h2', toc)) {
      const own = li.querySelector('.toc-row').textContent.toLowerCase().includes(q);
      let childHit = false;
      for (const c of $$('.toc-h3', li)) {
        const hit = !q || c.textContent.toLowerCase().includes(q);
        c.classList.toggle('filtered-out', !!q && !hit && !own);
        if (q && hit) childHit = true;
      }
      const show = !q || own || childHit;
      li.classList.toggle('filtered-out', !show);
      if (q) li.classList.toggle('open', childHit);
      if (show) any = true;
    }
    $$('.toc-part', toc).forEach((p) => p.classList.toggle('filtered-out', !!q));
    $('#toc-empty').hidden = any;
  }
  filter.addEventListener('input', applyFilter);
  filter.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      filter.value = '';
      applyFilter();
    }
  });

  // mobile drawer
  const menuBtn = $('#menu-btn');
  function closeNav() {
    document.body.classList.remove('nav-open');
    menuBtn.setAttribute('aria-expanded', 'false');
    $('#scrim').hidden = true;
  }
  menuBtn.addEventListener('click', () => {
    const open = !document.body.classList.contains('nav-open');
    document.body.classList.toggle('nav-open', open);
    menuBtn.setAttribute('aria-expanded', String(open));
    $('#scrim').hidden = !open;
    if (open) filter.focus({ preventScroll: true });
  });
  $('#scrim').addEventListener('click', closeNav);

  // ---------------------------------------------------------------- theme
  $('#theme-btn').addEventListener('click', () => {
    const root = document.documentElement;
    const isDark = root.dataset.theme ? root.dataset.theme === 'dark' : !matchMedia('(prefers-color-scheme: light)').matches;
    root.dataset.theme = isDark ? 'light' : 'dark';
    store.set('study-theme', root.dataset.theme);
  });

  // ---------------------------------------------------------------- keyword tooltip
  // a.kw = glossary link (definition text, and the type definition when it has one);
  // span.ty = any other mention of a type that has a definition. The window is interactive so a
  // long definition can be expanded and scrolled: it stays open while the pointer is over it.
  const tip = $('#kw-tip');
  const TRIGGER = 'a.kw, .ty';
  let tipFor = null;
  let hideTimer = 0;
  function place() {
    if (!tipFor) return;
    const r = tipFor.getBoundingClientRect();
    const w = tip.offsetWidth;
    const hgt = tip.offsetHeight;
    const x = Math.min(Math.max(8, r.left), window.innerWidth - w - 8);
    let y = r.bottom + 6;
    if (y + hgt > window.innerHeight - 8) y = Math.max(8, r.top - hgt - 6);
    tip.style.left = x + 'px';
    tip.style.top = y + 'px';
  }
  // opening a long definition keeps the window where it is (so the pointer stays on it) and lets it
  // grow down to the bottom of the viewport, scrolling inside
  function grow() {
    const top = tip.getBoundingClientRect().top;
    tip.style.maxHeight = Math.max(160, window.innerHeight - top - 8) + 'px';
  }
  function showTip(a) {
    clearTimeout(hideTimer);
    if (a === tipFor) return;
    tipFor = a;
    tip.innerHTML = '';
    if (a.dataset.term) {
      const b = document.createElement('b');
      b.textContent = a.dataset.term;
      const p = document.createElement('span');
      p.textContent = a.dataset.def;
      const s = document.createElement('small');
      s.textContent = '→ ' + a.dataset.target;
      tip.append(b, p, s);
    }
    const decl = a.dataset.decl && document.querySelector(`#decls [data-decl="${a.dataset.decl}"]`);
    tip.classList.toggle('has-decl', !!decl);
    if (decl) tip.append(decl.cloneNode(true));
    tip.style.maxHeight = '';
    tip.hidden = false;
    tip.scrollTop = 0;
    place();
  }
  function hideTip() {
    clearTimeout(hideTimer);
    tipFor = null;
    tip.hidden = true;
  }
  const hideSoon = () => {
    clearTimeout(hideTimer);
    hideTimer = setTimeout(hideTip, 220);
  };
  tip.addEventListener('toggle', grow, true); // <details> opened or closed
  // hover only for a real mouse; on touch screens a tap opens the window and a tap elsewhere closes it
  document.addEventListener('pointerover', (e) => {
    if (e.pointerType !== 'mouse') return;
    const a = e.target.closest(TRIGGER);
    if (a) showTip(a);
    else if (tip.contains(e.target)) clearTimeout(hideTimer);
    else if (tipFor) hideSoon();
  });
  document.addEventListener('focusin', (e) => {
    const a = e.target.closest && e.target.closest(TRIGGER);
    if (a) showTip(a);
    else if (!tip.contains(e.target)) hideTip();
  });
  // touch: a tap on a type mention opens its definition (glossary links still navigate)
  document.addEventListener('click', (e) => {
    const ty = e.target.closest('.ty');
    if (ty) showTip(ty);
    else if (tipFor && !tip.contains(e.target)) hideTip();
  });
  document.addEventListener('keydown', (e) => e.key === 'Escape' && tipFor && hideTip());
  window.addEventListener('scroll', () => tipFor && hideTip(), { passive: true });

  // ---------------------------------------------------------------- code copy buttons
  for (const pre of $$('.prose pre')) {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'copy-btn';
    b.textContent = 'Copy';
    b.addEventListener('click', () => {
      const code = pre.querySelector('code') || pre;
      const done = () => {
        b.textContent = 'Copied';
        setTimeout(() => (b.textContent = 'Copy'), 1400);
      };
      const fallback = () => {
        const sel = getSelection();
        const range = document.createRange();
        range.selectNodeContents(code);
        sel.removeAllRanges();
        sel.addRange(range);
        b.textContent = 'Selected';
        setTimeout(() => (b.textContent = 'Copy'), 1400);
      };
      try {
        navigator.clipboard.writeText(code.innerText).then(done, fallback);
      } catch (e) {
        fallback();
      }
    });
    pre.appendChild(b);
  }

  // ---------------------------------------------------------------- search palette
  const index = JSON.parse($('#search-index').textContent);
  const meta = JSON.parse($('#doc-meta').textContent);
  const docNumToKey = Object.fromEntries(meta.map((m) => [m.num, m.key]));
  const palette = $('#palette');
  const q = $('#palette-q');
  const list = $('#palette-list');
  let results = [];
  let sel = 0;
  const norm = (s) => s.toLowerCase().replace(/[`*_]/g, '');
  function score(item, terms) {
    const hay = norm(`${item.num || ''} ${item.t} ${item.alias || ''} ${item.def || ''}`);
    const title = norm(item.t);
    let s = 0;
    for (const t of terms) {
      if (!hay.includes(t)) return -1;
      if (title.startsWith(t)) s += 6;
      else if (title.includes(t)) s += 3;
      else s += 1;
    }
    if (item.k === 'g') s += 1;
    if (item.d === 2) s += 1;
    if (item.doc === (meta.find((m) => m.key === current) || {}).num) s += 0.5;
    return s;
  }
  function search() {
    const terms = norm(q.value).split(/\s+/).filter(Boolean);
    if (!terms.length) {
      results = index.filter((i) => i.k === 'h' && i.d === 2 && i.doc === (meta.find((m) => m.key === current) || {}).num);
    } else {
      results = index
        .map((i) => [score(i, terms), i])
        .filter(([s]) => s >= 0)
        .sort((a, b) => b[0] - a[0])
        .slice(0, 40)
        .map(([, i]) => i);
    }
    sel = 0;
    render();
  }
  function render() {
    list.innerHTML = '';
    if (!results.length) {
      const li = document.createElement('li');
      li.className = 'palette-empty';
      li.textContent = 'Nothing matches. Try a function name, a field, or a section number.';
      list.append(li);
      return;
    }
    results.forEach((r, i) => {
      const li = document.createElement('li');
      li.id = 'pl-' + i;
      li.setAttribute('role', 'option');
      li.setAttribute('aria-selected', String(i === sel));
      const d = document.createElement('span');
      d.className = 'pl-doc';
      d.textContent = r.doc;
      const t = document.createElement('span');
      t.className = 'pl-title';
      if (r.k === 'g') {
        const k = document.createElement('span');
        k.className = 'pl-kind';
        k.textContent = 'term';
        t.append(k);
      } else if (r.num) {
        const n = document.createElement('span');
        n.className = 'toc-num';
        n.textContent = r.num;
        t.append(n);
      }
      t.append(r.t);
      const sub = document.createElement('span');
      sub.className = 'pl-sub';
      sub.textContent = r.k === 'g' ? r.def : (meta.find((m) => m.num === r.doc) || {}).tab;
      li.append(d, t, sub);
      li.addEventListener('mousemove', () => {
        if (sel !== i) {
          sel = i;
          highlight();
        }
      });
      li.addEventListener('click', () => go(r));
      list.append(li);
    });
    q.setAttribute('aria-activedescendant', 'pl-' + sel);
  }
  function highlight() {
    $$('li[role="option"]', list).forEach((li, i) => li.setAttribute('aria-selected', String(i === sel)));
    const li = $('#pl-' + sel);
    if (li) li.scrollIntoView({ block: 'nearest' });
    q.setAttribute('aria-activedescendant', 'pl-' + sel);
  }
  function go(r) {
    palette.close();
    if (location.hash.slice(1) !== r.id) history.pushState(null, '', '#' + r.id);
    route(false);
  }
  function openPalette() {
    if (palette.open) return;
    q.value = '';
    search();
    palette.showModal();
    q.focus();
  }
  q.addEventListener('input', search);
  q.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown') {
      sel = Math.min(results.length - 1, sel + 1);
      highlight();
      e.preventDefault();
    } else if (e.key === 'ArrowUp') {
      sel = Math.max(0, sel - 1);
      highlight();
      e.preventDefault();
    } else if (e.key === 'Enter' && results[sel]) {
      go(results[sel]);
      e.preventDefault();
    }
  });
  palette.addEventListener('click', (e) => {
    if (e.target === palette) palette.close();
  });
  document.addEventListener('click', (e) => {
    const b = e.target.closest('[data-action]');
    if (!b) return;
    if (b.dataset.action === 'search') openPalette();
    if (b.dataset.action === 'top') {
      history.pushState(null, '', '#doc-' + current);
      window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
    }
  });
  document.addEventListener('keydown', (e) => {
    const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName);
    if ((e.key === 'k' || e.key === 'K') && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      openPalette();
    } else if (e.key === '/' && !typing && !lightbox.open) {
      e.preventDefault();
      openPalette();
    } else if (!typing && !palette.open && !lightbox.open && /^[123]$/.test(e.key) && !e.ctrlKey && !e.metaKey && !e.altKey) {
      const key = docNumToKey['0' + e.key];
      if (key) {
        history.pushState(null, '', '#doc-' + key);
        route(false);
      }
    }
  });

  // ---------------------------------------------------------------- figure lightbox (pan / zoom)
  const lightbox = $('#lightbox');
  const stage = $('#lb-stage');
  const img = $('#lb-img');
  const zoomLabel = $('#lb-zoom');
  let view = { s: 1, x: 0, y: 0 };
  let natural = { w: 1, h: 1 };
  function apply() {
    img.style.transform = `translate(${view.x}px, ${view.y}px) scale(${view.s})`;
    zoomLabel.textContent = Math.round(view.s * 100) + '%';
  }
  function fit() {
    const r = stage.getBoundingClientRect();
    const s = Math.min((r.width - 32) / natural.w, (r.height - 32) / natural.h);
    view = { s, x: (r.width - natural.w * s) / 2, y: (r.height - natural.h * s) / 2 };
    apply();
  }
  function zoomAt(f, cx, cy) {
    const s = Math.min(8, Math.max(0.1, view.s * f));
    const k = s / view.s;
    view = { s, x: cx - (cx - view.x) * k, y: cy - (cy - view.y) * k };
    apply();
  }
  function openLightbox(btn) {
    const src = btn.querySelector('img');
    const fig = btn.closest('figure');
    const label = fig.querySelector('.fig-label');
    $('#lb-title').textContent = (label ? label.textContent + ' · ' : '') + src.alt;
    $('#lb-open').href = src.getAttribute('src');
    img.alt = src.alt;
    img.onload = () => {
      natural = { w: img.naturalWidth || +src.getAttribute('width') || 1200, h: img.naturalHeight || +src.getAttribute('height') || 800 };
      img.style.width = natural.w + 'px';
      img.style.height = natural.h + 'px';
      fit();
    };
    img.src = src.getAttribute('src');
    lightbox.showModal();
    if (img.complete && img.naturalWidth) img.onload();
  }
  document.addEventListener('click', (e) => {
    const b = e.target.closest('[data-zoom]');
    if (b) openLightbox(b);
    const t = e.target.closest('[data-lb]');
    if (!t) return;
    const r = stage.getBoundingClientRect();
    if (t.dataset.lb === 'in') zoomAt(1.25, r.width / 2, r.height / 2);
    if (t.dataset.lb === 'out') zoomAt(0.8, r.width / 2, r.height / 2);
    if (t.dataset.lb === 'fit') fit();
    if (t.dataset.lb === 'close') lightbox.close();
  });
  stage.addEventListener(
    'wheel',
    (e) => {
      e.preventDefault();
      const r = stage.getBoundingClientRect();
      zoomAt(Math.exp(-e.deltaY * 0.0015), e.clientX - r.left, e.clientY - r.top);
    },
    { passive: false },
  );
  const pointers = new Map();
  let pinch = null;
  stage.addEventListener('pointerdown', (e) => {
    stage.setPointerCapture(e.pointerId);
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    stage.classList.add('dragging');
  });
  stage.addEventListener('pointermove', (e) => {
    if (!pointers.has(e.pointerId)) return;
    const prev = pointers.get(e.pointerId);
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pointers.size === 2) {
      const [a, b] = Array.from(pointers.values());
      const d = Math.hypot(a.x - b.x, a.y - b.y);
      const r = stage.getBoundingClientRect();
      if (pinch) zoomAt(d / pinch, (a.x + b.x) / 2 - r.left, (a.y + b.y) / 2 - r.top);
      pinch = d;
      return;
    }
    view.x += e.clientX - prev.x;
    view.y += e.clientY - prev.y;
    apply();
  });
  const up = (e) => {
    pointers.delete(e.pointerId);
    if (pointers.size < 2) pinch = null;
    if (!pointers.size) stage.classList.remove('dragging');
  };
  stage.addEventListener('pointerup', up);
  stage.addEventListener('pointercancel', up);
  stage.addEventListener('dblclick', fit);
  lightbox.addEventListener('keydown', (e) => {
    const r = stage.getBoundingClientRect();
    if (e.key === '0') fit();
    if (e.key === '+' || e.key === '=') zoomAt(1.25, r.width / 2, r.height / 2);
    if (e.key === '-') zoomAt(0.8, r.width / 2, r.height / 2);
  });
  window.addEventListener('resize', () => lightbox.open && fit());

  // ---------------------------------------------------------------- animated figures
  // An animated SVG marks its elements with data-s / data-e (first and last step, -1 = to the end).
  for (const fig of $$('.fig-anim')) {
    const svg = fig.querySelector('.anim-stage svg');
    if (!svg) continue;
    const caps = JSON.parse(fig.dataset.captions || '[]');
    const n = caps.length;
    const els = [...svg.querySelectorAll('[data-s]')].map((el) => [el, +el.getAttribute('data-s'), +el.getAttribute('data-e')]);
    const count = fig.querySelector('.anim-count');
    const capEl = fig.querySelector('.anim-caption');
    const playBtn = fig.querySelector('[data-act="play"]');
    const dots = [...fig.querySelectorAll('.anim-dot')];
    // movers: groups that glide along a route between steps (data-mv = per-step list of offsets)
    const movers = [...svg.querySelectorAll('[data-mv]')].map((el) => [el, JSON.parse(el.getAttribute('data-mv'))]);
    const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const place = (el, fr, anim) => {
      const p = fr[fr.length - 1];
      if (el.getAnimations) el.getAnimations().forEach((x) => x.cancel());
      el.setAttribute('transform', `translate(${p[0]} ${p[1]})`);
      if (!anim || reduce || fr.length < 2 || !el.animate) return;
      const L = [0];
      let t = 0;
      for (let i = 1; i < fr.length; i++) {
        t += Math.hypot(fr[i][0] - fr[i - 1][0], fr[i][1] - fr[i - 1][1]);
        L.push(t);
      }
      if (t <= 0) return;
      el.animate(fr.map((q, i) => ({ transform: `translate(${q[0]}px, ${q[1]}px)`, offset: L[i] / t })),
        { duration: Math.min(1700, 400 + t * 2.2), easing: 'ease-in-out' });
    };
    let k = 0;
    let prevK = 0;
    let timer = null;
    const show = () => {
      const anim = k === prevK + 1;
      prevK = k;
      for (const [el, fr] of movers) place(el, fr[Math.min(k, fr.length - 1)], anim);
      for (const [el, a, b] of els) el.classList.toggle('anim-on', a <= k && (b < 0 || k <= b));
      count.textContent = `Step ${k + 1} / ${n}`;
      capEl.textContent = caps[k];
      dots.forEach((d, i) => d.classList.toggle('on', i === k));
      fig.querySelector('[data-act="prev"]').disabled = k === 0;
      fig.querySelector('[data-act="next"]').disabled = k === n - 1;
    };
    const stop = () => {
      clearInterval(timer);
      timer = null;
      playBtn.textContent = '▶ Play';
      fig.classList.remove('playing');
    };
    const go = (i) => {
      k = Math.max(0, Math.min(n - 1, i));
      show();
    };
    const play = () => {
      if (timer) return stop();
      if (k === n - 1) go(0);
      playBtn.textContent = 'Pause';
      fig.classList.add('playing');
      timer = setInterval(() => {
        if (k >= n - 1) return stop();
        go(k + 1);
      }, 2200);
    };

    // ---- zoom / pan: changes the SVG viewBox, so the figure stays vector at any zoom
    const stage = fig.querySelector('.anim-stage');
    const zoomLabel = fig.querySelector('.anim-zoom');
    const fullBtn = fig.querySelector('[data-act="full"]');
    const b0 = svg.viewBox.baseVal;
    const vb0 = { x: b0.x, y: b0.y, w: b0.width, h: b0.height };
    let vb = { ...vb0 };
    const MAX = 12;
    const applyVb = () => {
      const z = vb0.w / vb.w;
      // keep at least half a screen of the figure in view
      vb.x = Math.max(vb0.x - vb.w / 2, Math.min(vb0.x + vb0.w - vb.w / 2, vb.x));
      vb.y = Math.max(vb0.y - vb.h / 2, Math.min(vb0.y + vb0.h - vb.h / 2, vb.y));
      svg.setAttribute('viewBox', `${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
      zoomLabel.textContent = `${Math.round(z * 100)}%`;
      stage.classList.toggle('zoomed', z > 1.001);
      fig.querySelector('[data-act="zoom-out"]').disabled = z <= 1.001;
      fig.querySelector('[data-act="zoom-in"]').disabled = z >= MAX - 0.01;
    };
    const toUser = (cx, cy) => {
      const m = svg.getScreenCTM();
      if (!m) return { x: vb.x + vb.w / 2, y: vb.y + vb.h / 2 };
      const p = new DOMPoint(cx, cy).matrixTransform(m.inverse());
      return { x: p.x, y: p.y };
    };
    const zoomBy = (f, cx, cy) => {
      const z = vb0.w / vb.w;
      const nz = Math.max(1, Math.min(MAX, z * f));
      f = nz / z;
      if (Math.abs(f - 1) < 1e-6) return;
      if (cx === undefined) {
        const r = svg.getBoundingClientRect();
        cx = r.left + r.width / 2;
        cy = r.top + r.height / 2;
      }
      const p = toUser(cx, cy);
      vb = { x: p.x - (p.x - vb.x) / f, y: p.y - (p.y - vb.y) / f, w: vb.w / f, h: vb.h / f };
      if (nz <= 1.001) vb = { ...vb0 };
      applyVb();
    };
    const fitView = () => { vb = { ...vb0 }; applyVb(); };
    const isFull = () => fig.classList.contains('is-full');
    const setFull = (on) => {
      fig.classList.toggle('is-full', on);
      document.body.classList.toggle('anim-full-open', on);
      fullBtn.textContent = on ? '✕ Exit full screen' : '⛶ Full screen';
      fullBtn.title = on ? 'Exit full screen (Esc)' : 'Full screen (F, Esc to exit)';
      fitView();
      if (on) fig.focus({ preventScroll: true });
      else fig.scrollIntoView({ block: 'nearest' });
    };
    stage.addEventListener('wheel', (e) => {
      // in the page, plain wheel scrolls; Ctrl/⌘ + wheel (or a trackpad pinch) zooms. Full screen: wheel zooms.
      if (!isFull() && !e.ctrlKey && !e.metaKey) return;
      e.preventDefault();
      zoomBy(Math.exp(-e.deltaY * (e.ctrlKey && !isFull() ? 0.01 : 0.0018)), e.clientX, e.clientY);
    }, { passive: false });
    const ptrs = new Map();
    let pinch = null;
    stage.addEventListener('pointerdown', (e) => {
      if (e.button !== 0) return;
      ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY });
      if (ptrs.size === 2) {
        const [a, b] = [...ptrs.values()];
        pinch = { d: Math.hypot(a.x - b.x, a.y - b.y) };
      }
      if (vb0.w / vb.w > 1.001 || ptrs.size === 2) {
        stage.setPointerCapture(e.pointerId);
        stage.classList.add('dragging');
      }
    });
    stage.addEventListener('pointermove', (e) => {
      const prev = ptrs.get(e.pointerId);
      if (!prev) return;
      const cur = { x: e.clientX, y: e.clientY };
      ptrs.set(e.pointerId, cur);
      if (ptrs.size === 2 && pinch) {
        const [a, b] = [...ptrs.values()];
        const d = Math.hypot(a.x - b.x, a.y - b.y);
        if (pinch.d > 0) zoomBy(d / pinch.d, (a.x + b.x) / 2, (a.y + b.y) / 2);
        pinch.d = d;
        return;
      }
      if (vb0.w / vb.w <= 1.001) return;
      const m = svg.getScreenCTM();
      const s = m ? m.a : 1;
      vb.x -= (cur.x - prev.x) / s;
      vb.y -= (cur.y - prev.y) / s;
      applyVb();
    });
    const endPtr = (e) => {
      ptrs.delete(e.pointerId);
      if (ptrs.size < 2) pinch = null;
      if (!ptrs.size) stage.classList.remove('dragging');
    };
    stage.addEventListener('pointerup', endPtr);
    stage.addEventListener('pointercancel', endPtr);
    stage.addEventListener('dblclick', (e) => (vb0.w / vb.w > 1.001 ? fitView() : zoomBy(2, e.clientX, e.clientY)));

    fig.addEventListener('click', (e) => {
      const b = e.target.closest('[data-act], [data-go]');
      if (!b) return;
      if (b.dataset.go !== undefined) { stop(); return go(+b.dataset.go); }
      const act = b.dataset.act;
      if (act === 'play') return play();
      if (act === 'zoom-in') return zoomBy(1.4);
      if (act === 'zoom-out') return zoomBy(1 / 1.4);
      if (act === 'fit') return fitView();
      if (act === 'full') return setFull(!isFull());
      stop();
      if (act === 'reset') go(0);
      if (act === 'prev') go(k - 1);
      if (act === 'next') go(k + 1);
    });
    fig.addEventListener('keydown', (e) => {
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      if (e.key === 'ArrowRight') { stop(); go(k + 1); }
      else if (e.key === 'ArrowLeft') { stop(); go(k - 1); }
      else if (e.key === ' ' && e.target.tagName !== 'BUTTON') play();
      else if (e.key === '+' || e.key === '=') zoomBy(1.4);
      else if (e.key === '-') zoomBy(1 / 1.4);
      else if (e.key === '0') fitView();
      else if (e.key === 'f' || e.key === 'F') setFull(!isFull());
      else if (e.key === 'Escape' && isFull()) setFull(false);
      else return;
      e.preventDefault();
      e.stopPropagation();
    });
    applyVb();
    fig.tabIndex = 0;
    show();
  }

  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    const f = $('.fig-anim.is-full');
    if (f) { f.querySelector('[data-act="full"]').click(); e.preventDefault(); }
  });

  // ---------------------------------------------------------------- start
  route(false);
})();
