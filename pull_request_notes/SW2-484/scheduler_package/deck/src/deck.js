// Figure stepping: an animated study figure placed with data-play gets one hidden fragment per step
// (span.figstep[data-for=<id prefix>]). The number of those fragments that are visible is the figure's step k.
// Step k shows every element with data-s <= k (and k <= data-e when data-e >= 0), moves every mover
// (<g data-mv>) to the end of its frame k, gliding along the frame when the presenter steps forward,
// and puts caption k under the figure. This is the same rule as the figures' own viewer script.
(function () {
  function place(el, fr, anim) {
    var p = fr[fr.length - 1];
    if (el.getAnimations) el.getAnimations().forEach(function (x) { x.cancel(); });
    el.setAttribute('transform', 'translate(' + p[0] + ' ' + p[1] + ')');
    if (anim && fr.length > 1 && el.animate) {
      var L = [0], t = 0;
      for (var i = 1; i < fr.length; i++) { t += Math.hypot(fr[i][0] - fr[i - 1][0], fr[i][1] - fr[i - 1][1]); L.push(t); }
      if (t > 0) el.animate(fr.map(function (q, i) { return { transform: 'translate(' + q[0] + 'px,' + q[1] + 'px)', offset: L[i] / t }; }),
        { duration: Math.min(1800, 400 + t * 2.2), easing: 'ease-in-out' });
    }
  }
  function sync(slide, anim) {
    if (!slide) return;
    slide.querySelectorAll('[data-figid]').forEach(function (wrap) {
      var id = wrap.getAttribute('data-figid');
      var k = slide.querySelectorAll('.figstep.visible[data-for="' + id + '"]').length;
      if (wrap._k === k) return;
      var forward = anim && wrap._k !== undefined && k === wrap._k + 1;
      wrap._k = k;
      var caps = JSON.parse(wrap.getAttribute('data-caps'));
      wrap.querySelectorAll('[data-s]').forEach(function (el) {
        var a = +el.getAttribute('data-s'), b = +el.getAttribute('data-e');
        el.classList.toggle('anim-on', a <= k && (b < 0 || k <= b));
      });
      wrap.querySelectorAll('[data-mv]').forEach(function (el) {
        var fr = JSON.parse(el.getAttribute('data-mv'));
        place(el, fr[Math.min(k, fr.length - 1)], forward);
      });
      var cap = slide.querySelector('.figcap[data-for="' + id + '"]');
      if (cap) cap.innerHTML = '<span class="k">' + (k + 1) + ' / ' + caps.length + '</span>' + caps[k].replace(/&/g, '&amp;').replace(/</g, '&lt;');
    });
  }

  Reveal.initialize({
    width: 1280, height: 720, margin: 0.03, center: false, hash: true,
    controls: true, progress: true, slideNumber: 'c/t', transition: 'fade', transitionSpeed: 'fast',
    backgroundTransition: 'none', pdfSeparateFragments: false,
    plugins: [RevealNotes],
  });
  Reveal.on('ready', function (e) {
    document.querySelectorAll('.slides section').forEach(function (s) { sync(s, false); });
    sync(e.currentSlide, false);
  });
  Reveal.on('slidechanged', function (e) { sync(e.currentSlide, false); });
  Reveal.on('fragmentshown', function () { sync(Reveal.getCurrentSlide(), true); });
  Reveal.on('fragmenthidden', function () { sync(Reveal.getCurrentSlide(), false); });
})();
