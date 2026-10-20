// Figure stepping: an animated study figure placed with data-play gets one hidden fragment per step
// (span.figstep[data-for=<id prefix>]). The number of those fragments that are visible is the figure's step k.
// Step k shows every element with data-s <= k (and k <= data-e when data-e >= 0), moves every mover
// (<g data-mv>) to the end of its frame k, gliding along the frame when the presenter steps forward,
// and puts caption k under the figure. This is the same rule as the figures' own viewer script.
(function () {
  // fr: points of step k's path (offsets from the start position); ts: optional keyframe times (0..1) for those
  // points and dur the step's duration, both written by the deck's own figures (scripts/diagrams/fig_deck.py), so a
  // tray waits until its AGV arrives and both finish together.
  function place(el, fr, anim, ts, dur) {
    var p = fr[fr.length - 1];
    if (el.getAnimations) el.getAnimations().forEach(function (x) { x.cancel(); });
    el.setAttribute('transform', 'translate(' + p[0] + ' ' + p[1] + ')');
    if (!anim || fr.length < 2 || !el.animate) return;
    var kf;
    if (ts && ts.length === fr.length) {
      kf = fr.map(function (q, i) { return { transform: 'translate(' + q[0] + 'px,' + q[1] + 'px)', offset: ts[i] }; });
      kf[0].offset = 0;
      el.animate(kf, { duration: dur || 1500, easing: 'linear' });
      return;
    }
    var L = [0], t = 0;
    for (var i = 1; i < fr.length; i++) { t += Math.hypot(fr[i][0] - fr[i - 1][0], fr[i][1] - fr[i - 1][1]); L.push(t); }
    if (t > 0) el.animate(fr.map(function (q, i) { return { transform: 'translate(' + q[0] + 'px,' + q[1] + 'px)', offset: L[i] / t }; }),
      { duration: Math.min(1800, 400 + t * 2.2), easing: 'ease-in-out' });
  }
  function sync(slide, anim) {
    if (!slide) return;
    slide.querySelectorAll('[data-figid]').forEach(function (wrap) {
      var id = wrap.getAttribute('data-figid');
      var k = slide.querySelectorAll('.figstep.visible[data-for="' + id + '"]').length;
      if (wrap._k === k && wrap._capH) return;
      var forward = anim && wrap._k !== undefined && k === wrap._k + 1;
      wrap._k = k;
      var caps = JSON.parse(wrap.getAttribute('data-caps'));
      wrap.querySelectorAll('[data-s]').forEach(function (el) {
        var a = +el.getAttribute('data-s'), b = +el.getAttribute('data-e');
        el.classList.toggle('anim-on', a <= k && (b < 0 || k <= b));
      });
      wrap.querySelectorAll('[data-mv]').forEach(function (el) {
        var fr = JSON.parse(el.getAttribute('data-mv'));
        var j = Math.min(k, fr.length - 1);
        var mt = el.getAttribute('data-mt'), md = el.getAttribute('data-md');
        place(el, fr[j], forward, mt ? JSON.parse(mt)[j] : null, md ? JSON.parse(md)[j] : null);
      });
      var cap = slide.querySelector('.figcap[data-for="' + id + '"]');
      if (!cap) return;
      var html = function (i) { return '<span class="k">' + (i + 1) + ' / ' + caps.length + '</span>' + caps[i].replace(/&/g, '&amp;').replace(/</g, '&lt;'); };
      // reserve the height of the longest caption once the slide is laid out, so nothing shifts between steps
      if (!wrap._capH && cap.offsetWidth) {
        cap.style.boxSizing = 'border-box'; cap.style.minHeight = '0px';
        var h = 0;
        for (var i = 0; i < caps.length; i++) { cap.innerHTML = html(i); h = Math.max(h, cap.offsetHeight); }
        wrap._capH = h; cap.style.minHeight = h + 'px';
      }
      cap.innerHTML = html(k);
    });
  }

  // theme: html[data-theme] when chosen (button or T), else the OS setting; remembered per browser
  var root = document.documentElement, mq = matchMedia('(prefers-color-scheme: light)');
  try { var saved = localStorage.getItem('deck-theme'); if (saved === 'light' || saved === 'dark') root.dataset.theme = saved; } catch (e) {}
  function theme() { return root.dataset.theme || (mq.matches ? 'light' : 'dark'); }
  var btn = document.createElement('button');
  btn.className = 'theme-btn'; btn.type = 'button'; btn.setAttribute('aria-label', 'Switch light / dark theme'); btn.title = 'Light / dark theme (T)';
  function label() { btn.textContent = theme() === 'light' ? '\u263E' : '\u2600'; }
  function toggle() { root.dataset.theme = theme() === 'light' ? 'dark' : 'light'; try { localStorage.setItem('deck-theme', root.dataset.theme); } catch (e) {} label(); }
  btn.addEventListener('click', toggle); label(); document.body.appendChild(btn);
  if (mq.addEventListener) mq.addEventListener('change', label);

  Reveal.initialize({
    width: 1280, height: 720, margin: 0.03, center: false, hash: true,
    controls: true, progress: true, slideNumber: 'c/t', transition: 'fade', transitionSpeed: 'fast',
    backgroundTransition: 'none', pdfSeparateFragments: false,
    plugins: [RevealNotes],
    keyboard: { 84: function () { toggle(); } },
  });
  Reveal.on('ready', function (e) {
    document.querySelectorAll('.slides section').forEach(function (s) { sync(s, false); });
    sync(e.currentSlide, false);
  });
  Reveal.on('slidechanged', function (e) { sync(e.currentSlide, false); });
  Reveal.on('fragmentshown', function () { sync(Reveal.getCurrentSlide(), true); });
  Reveal.on('fragmenthidden', function () { sync(Reveal.getCurrentSlide(), false); });
})();
