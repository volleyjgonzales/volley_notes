/* Contents sidebar: scrollspy with an AGV "you are here" marker, filter box,
   and an off-canvas drawer on small screens. No dependencies. */
(function () {
  const route = document.getElementById('route');
  const agv = document.getElementById('route-agv');
  const sidebar = document.getElementById('sidebar');
  const menuBtn = document.querySelector('.menu-btn');
  const filter = document.getElementById('toc-filter');
  const hit = document.getElementById('filter-hit');
  const stops = Array.from(route.querySelectorAll('.stop'));
  const subs = Array.from(route.querySelectorAll('.sub li'));

  // ---------- scrollspy
  const targets = [];
  stops.forEach((li) => {
    const el = document.getElementById(li.dataset.target);
    if (el) targets.push({ el, li, stop: li });
    li.querySelectorAll('.sub li').forEach((s) => {
      const t = document.getElementById(s.dataset.target);
      if (t) targets.push({ el: t, li: s, stop: li });
    });
  });

  let current = null;
  function update() {
    const line = window.innerHeight * 0.3;
    let best = null;
    for (const t of targets) {
      const top = t.el.getBoundingClientRect().top;
      if (top - line <= 0) best = t; else break;
    }
    if (!best) best = targets[0];
    if (best === current) return;
    current = best;
    let passed = true;
    stops.forEach((s) => {
      const on = s === best.stop;
      if (on) passed = false;
      s.classList.toggle('active', on);
      s.classList.toggle('open', on);
      s.classList.toggle('passed', passed && !on);
    });
    subs.forEach((s) => s.classList.toggle('active', s === best.li));
    placeAgv(best.stop);
  }
  function placeAgv(stop) {
    const link = stop.querySelector('.stop-link');
    const wrap = route.parentElement;
    const r = link.getBoundingClientRect();
    const w = wrap.getBoundingClientRect();
    const y = r.top - w.top + wrap.scrollTop;          // position inside the scrolling sidebar
    agv.style.top = (y + 4) + 'px';                     // centre the marker on the node dot
    if (!route.classList.contains('filtered') && (r.top < w.top || r.bottom > w.bottom - 60)) {
      wrap.scrollTo({ top: y - 80, behavior: 'smooth' });
    }
  }
  let ticking = false;
  window.addEventListener('scroll', () => {
    if (!ticking) { requestAnimationFrame(() => { update(); ticking = false; }); ticking = true; }
  }, { passive: true });
  window.addEventListener('resize', () => current && placeAgv(current.stop));
  update();

  // ---------- filter
  const reqs = window.REQ_INDEX || [];
  filter.addEventListener('input', () => {
    const q = filter.value.trim().toLowerCase();
    route.classList.toggle('filtered', q.length > 0);
    hit.hidden = true;
    if (!q) { current = null; update(); return; }
    stops.forEach((s) => {
      let any = false;
      s.querySelectorAll('.sub li').forEach((li) => {
        const m = li.textContent.toLowerCase().includes(q);
        li.classList.toggle('match', m);
        any = any || m;
      });
      const own = s.querySelector('.stop-title').textContent.toLowerCase().includes(q) ||
                  (' ' + s.dataset.keywords + ' ').includes(' ' + q + ' ');
      s.classList.toggle('match', own || any);
      if (own) s.querySelectorAll('.sub li').forEach((li) => li.classList.add('match'));
    });
    const r = reqs.find((x) => x.id === q);
    if (r) {
      hit.hidden = false;
      hit.innerHTML = '';
      const a = document.createElement('a');
      a.href = '#' + r.anchor;
      a.textContent = 'Requirement ' + r.id;
      const span = document.createElement('span');
      span.textContent = ': ' + (r.text.length > 90 ? r.text.slice(0, 88) + '…' : r.text);
      hit.append(a, span);
    }
  });
  filter.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const first = hit.hidden ? route.querySelector('.match a') : hit.querySelector('a');
      if (first) { first.click(); }
    }
    if (e.key === 'Escape') { filter.value = ''; filter.dispatchEvent(new Event('input')); }
  });

  // ---------- drawer on small screens
  function setOpen(open) {
    sidebar.classList.toggle('open', open);
    menuBtn.setAttribute('aria-expanded', String(open));
  }
  menuBtn.addEventListener('click', () => setOpen(!sidebar.classList.contains('open')));
  sidebar.addEventListener('click', (e) => {
    if (e.target.closest('a') && window.matchMedia('(max-width: 960px)').matches) setOpen(false);
  });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') setOpen(false); });
})();
