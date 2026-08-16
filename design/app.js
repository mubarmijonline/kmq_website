/* KMQ front end.
 *
 * Replaces the design source's React runtime (support.js, ~70 KB). Every
 * behaviour below is an enhancement: the markup it attaches to already works
 * without this file. Navigation is real links, the blog filter is real query
 * parameters, the FAQ is <details>, and both forms submit normally.
 */
(function () {
  'use strict';

  var d = document;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function on(el, ev, fn, opts) { if (el) el.addEventListener(ev, fn, opts); }

  /* ---- Header: opaque past 40px --------------------------------------- */

  (function header() {
    var el = d.querySelector('[data-kmq-header]');
    if (!el) return;
    var was = null;
    function sync() {
      var now = window.scrollY > 40;
      if (now !== was) { was = now; el.setAttribute('data-scrolled', String(now)); }
    }
    on(window, 'scroll', sync, { passive: true });
    sync();
  }());

  /* ---- Mobile menu ----------------------------------------------------- */

  (function menu() {
    var btn = d.querySelector('[data-kmq-burger]');
    var nav = d.querySelector('[data-kmq-mobilenav]');
    if (!btn || !nav) return;

    function set(open) {
      btn.setAttribute('aria-expanded', String(open));
      nav.setAttribute('data-open', String(open));
    }

    on(btn, 'click', function () {
      set(btn.getAttribute('aria-expanded') !== 'true');
    });

    on(d, 'keydown', function (e) {
      if (e.key === 'Escape' && btn.getAttribute('aria-expanded') === 'true') {
        set(false);
        btn.focus();
      }
    });

    /* The CSS breakpoint owns visibility; this only clears a stale open
       state when the viewport grows past it. */
    var mq = window.matchMedia('(min-width: 1024px)');
    var onChange = function (e) { if (e.matches) set(false); };
    if (mq.addEventListener) mq.addEventListener('change', onChange);
    else if (mq.addListener) mq.addListener(onChange);
  }());

  /* ---- Language preference --------------------------------------------
     Remembers the last language chosen so a returning visitor landing on
     bare "/" goes where they left off. Only ever set from a real click on
     the switcher — never inferred, and never used to redirect a visitor
     who asked for a specific locale by URL. */

  (function lang() {
    d.querySelectorAll('[data-kmq-lang]').forEach(function (el) {
      on(el, 'click', function () {
        try {
          localStorage.setItem('kmq.lang', el.getAttribute('data-kmq-lang'));
        } catch (err) { /* private mode: the href still works */ }
      });
    });
  }());

  /* ---- Scroll-spy ------------------------------------------------------
     Lights the nav item for the home-page section in view. The source ran
     getBoundingClientRect over every section on every scroll event; an
     observer does the same job without touching layout per frame. */

  (function spy() {
    var sections = d.querySelectorAll('[data-kmq-section]');
    var links = d.querySelectorAll('[data-kmq-navlink]');
    if (!sections.length || !links.length || !window.IntersectionObserver) return;

    var seen = Object.create(null);

    function paint() {
      /* Topmost section currently intersecting wins, matching the source's
         "last one whose top is above the 220px line" rule. */
      var active = null;
      sections.forEach(function (s) {
        if (seen[s.getAttribute('data-kmq-section')]) {
          if (!active || s.getBoundingClientRect().top <= active.top) {
            active = { id: s.getAttribute('data-kmq-section'), top: s.getBoundingClientRect().top };
          }
        }
      });
      links.forEach(function (a) {
        var lit = !!active && a.getAttribute('data-kmq-navlink') === active.id;
        if (lit) a.setAttribute('data-lit', 'true');
        else a.removeAttribute('data-lit');
      });
    }

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        seen[e.target.getAttribute('data-kmq-section')] = e.isIntersecting;
      });
      paint();
    }, { rootMargin: '-220px 0px -60% 0px' });

    sections.forEach(function (s) { io.observe(s); });
  }());

  /* ---- Before / after slider ------------------------------------------
     Drives --kmq-reveal. The input carries value="50" in the markup, so the
     split renders correctly before this runs. */

  (function compare() {
    d.querySelectorAll('[data-kmq-compare]').forEach(function (box) {
      var range = box.querySelector('input[type="range"]');
      if (!range) return;
      function sync() { box.style.setProperty('--kmq-reveal', range.value + '%'); }
      on(range, 'input', sync);
      sync();
    });
  }());

  /* ---- Blog filter and search ------------------------------------------
     The chips are links and the search box sits in a GET form, so both work
     with the script absent. With it, typing filters in place — one request
     saved per keystroke, and the URL still updates so the result is
     shareable and the back button behaves. */

  (function blog() {
    var root = d.querySelector('[data-kmq-blog]');
    if (!root) return;

    var input = root.querySelector('[data-kmq-search]');
    var cards = Array.prototype.slice.call(root.querySelectorAll('[data-kmq-post]'));
    var count = root.querySelector('[data-kmq-count]');
    var empty = root.querySelector('[data-kmq-empty]');
    var pager = root.querySelector('[data-kmq-pager]');
    if (!input || !cards.length) return;

    var one = root.getAttribute('data-count-one') || '1';
    var many = root.getAttribute('data-count-many') || '';
    var timer = null;

    function apply() {
      var q = input.value.trim().toLowerCase();
      var shown = 0;

      cards.forEach(function (card) {
        var hay = (card.getAttribute('data-kmq-post') || '').toLowerCase();
        var hit = !q || hay.indexOf(q) !== -1;
        card.hidden = !hit;
        if (hit) shown++;
      });

      if (count) count.textContent = shown === 1 ? one : shown + many;
      if (empty) empty.hidden = shown !== 0;
      /* Pagination counts the unfiltered set; hide it while searching. */
      if (pager) pager.hidden = !!q;

      var url = new URL(window.location.href);
      if (q) url.searchParams.set('q', input.value.trim());
      else url.searchParams.delete('q');
      url.searchParams.delete('page');
      window.history.replaceState(null, '', url);
    }

    on(input, 'input', function () {
      window.clearTimeout(timer);
      timer = window.setTimeout(apply, 120);
    });

    /* Stop the GET form navigating when we can filter in place. */
    on(input.form, 'submit', function (e) { e.preventDefault(); apply(); });
  }());

  /* ---- FAQ -------------------------------------------------------------
     <details> already opens and closes. This adds the height animation and
     closes siblings, and is skipped entirely under reduced motion. */

  (function faq() {
    var group = d.querySelector('[data-kmq-faq]');
    if (!group) return;
    var items = Array.prototype.slice.call(group.querySelectorAll('details'));

    items.forEach(function (item) {
      on(item, 'toggle', function () {
        if (!item.open) return;
        items.forEach(function (other) { if (other !== item) other.open = false; });
      });
    });

    if (reduce) return;

    items.forEach(function (item) {
      var panel = item.querySelector('.kmq-faq__a');
      if (!panel) return;
      /* Animate rows rather than max-height: it resolves to the answer's
         real height, so long answers are never clipped. */
      panel.style.transition = 'grid-template-rows .3s cubic-bezier(.4,0,.2,1)';
      var sync = function () { panel.style.gridTemplateRows = item.open ? '1fr' : '0fr'; };
      sync();
      on(item, 'toggle', sync);
    });
  }());

  /* ---- Forms -----------------------------------------------------------
     Blocks the double submit. Validation itself is server-side; this only
     stops the same lead arriving twice. */

  (function forms() {
    d.querySelectorAll('[data-kmq-once]').forEach(function (form) {
      on(form, 'submit', function () {
        var btn = form.querySelector('button[type="submit"]');
        if (!btn) return;
        window.setTimeout(function () {
          btn.disabled = true;
          btn.setAttribute('aria-busy', 'true');
        }, 0);
      });
    });
  }());

  /* ---- Hero protection stack -------------------------------------------
     Scroll drives four coating stages, then the car leaves and hands the page
     to the Trust strip. Nothing here is required to read the section: the CSS
     leaves the bare car and the first caption standing when this does not run,
     and the reduced-motion rules collapse the track to one screen. */

  (function stack() {
    var track = d.querySelector('[data-kmq-stack]');
    if (!track || reduce) return;

    var car = track.querySelector('[data-kmq-car]');
    var dull = track.querySelector('[data-kmq-dull]');
    var bar = track.querySelector('[data-kmq-bar]');
    var glow = track.querySelector('.kmq-stack__glow');
    var grid = track.querySelector('.kmq-stack__grid');
    if (!car || !dull || !bar || !glow || !grid) return;

    var caps = track.querySelectorAll('[data-kmq-cap]');
    var dots = track.querySelectorAll('[data-kmq-dot]');
    var lbls = track.querySelectorAll('[data-kmq-lbl]');

    /* Stage 2 and 4 each wipe two layers at once: a rim glow and a coating. */
    var groups = [['1a', '1b'], ['2'], ['3a', '3b']].map(function (ids) {
      return ids.map(function (id) {
        return track.querySelector('[data-kmq-layer="' + id + '"]');
      });
    });

    var HOLD = 0.08;   /* stage 0 dwell */
    var BUILD = 0.70;  /* three wipes finish here */
    var EXIT = 0.86;   /* car starts leaving */
    var frame = 0;

    function paint() {
      var rect = track.getBoundingClientRect();
      var span = Math.max(1, track.offsetHeight - window.innerHeight);
      var p = Math.min(1, Math.max(0, -rect.top / span));
      var t = Math.min(1, Math.max(0, (p - HOLD) / (BUILD - HOLD)));
      var seg = t * 3;

      groups.forEach(function (els, i) {
        var local = Math.min(1, Math.max(0, seg - i));
        var e = local < 0.5 ? 2 * local * local : 1 - Math.pow(-2 * local + 2, 2) / 2;
        var clip = 'inset(0 0 0 ' + ((1 - e) * 100).toFixed(2) + '%)';
        els.forEach(function (el) { if (el) el.style.clipPath = clip; });
      });

      var active = Math.min(3, Math.floor(seg + 0.35));

      function mark(el, i) {
        el.setAttribute('data-state', i === active ? 'now' : i < active ? 'done' : 'next');
      }

      caps.forEach(function (c, i) {
        c.setAttribute('data-lit', i === active ? 'true' : 'false');
        c.style.transform = i === active ? 'translateY(0)' : 'translateY(20px)';
      });
      dots.forEach(mark);
      lbls.forEach(mark);

      /* Unprotected paint reads flat, then each coating lifts it back. */
      dull.style.opacity = (0.17 * Math.min(1, p / HOLD) * (1 - Math.min(1, Math.max(0, seg)))).toFixed(3);
      bar.style.width = (p * 100).toFixed(2) + '%';
      glow.style.opacity = (0.5 + 0.5 * t).toFixed(3);

      var x = Math.min(1, Math.max(0, (p - EXIT) / (1 - EXIT)));
      var xe = x * x;
      car.style.transform = 'translateY(' + (xe * 62).toFixed(2) + 'vh) scale(' + (1 - xe * 0.12).toFixed(3) + ')';
      car.style.opacity = (1 - xe * 0.9).toFixed(3);
      grid.style.opacity = (1 - Math.min(1, xe * 1.15)).toFixed(3);
    }

    function sync() {
      if (frame) return;
      frame = window.requestAnimationFrame(function () { frame = 0; paint(); });
    }

    on(window, 'scroll', sync, { passive: true });
    on(window, 'resize', sync);
    paint();
  }());
}());
