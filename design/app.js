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

  /* ---- Hero cycle -------------------------------------------------------
     Four photographs of one car, crossfading on a timer.

     What this replaced was scroll-driven, and the rewrite is deliberately
     boring about how it animates. Rules it holds to, in order of how much
     each one mattered to the old version's frame times:

       1. Only opacity changes, and only via CSS transitions. No filters, no
          blend modes, no masks, no clip-path, no layout properties. The
          progress fill is a scaleX, not a width.
       2. No scroll listener. Nothing here reads scroll position, and nothing
          calls getBoundingClientRect.
       3. One timer, not one per state, and not a requestAnimationFrame loop —
          there is no per-frame value to compute, so asking for a frame
          callback 60 times a second to do nothing 59 of them is waste.
       4. Every image decodes before the first transition. A crossfade into an
          undecoded image stalls on the main thread mid-transition, which is
          the first-cycle hitch the old hero had and the reason the sequence
          waits here.
       5. The timer stops when the hero is off-screen and when the tab is
          hidden. An IntersectionObserver does the first, visibilitychange the
          second. A paused cycle also drops its compositor layers.

     Under prefers-reduced-motion the cycle never starts. State 1 stands, and
     the rail still switches states on click — the controls keep working, the
     autoplay does not. That is the opposite call from the old hero, and
     correctly so: that one was scroll-driven, so the visitor moved every
     frame of it themselves. This one moves on its own, which is exactly what
     the setting asks not to happen. */

  (function hero() {
    var root = d.querySelector('[data-kmq-cycle]');
    if (!root) return;

    var states = root.querySelectorAll('[data-kmq-state]');
    var steps = root.querySelectorAll('[data-kmq-step]');
    if (states.length < 2 || steps.length !== states.length) return;

    /* Per-state accents. Sampling the images was the original plan and does
       not survive contact with them: all four cars are black on transparent,
       so the dominant colour is the same near-black four times over and the
       glow would never visibly change. These are the palette's own accents,
       one per service, chosen so consecutive states differ in hue rather than
       only in brightness. Read from CSS rather than written here as hex, so
       the tokens stay the single source. */
    var ACCENTS = ['--brand-500', '--text-low', '--cyan-400', '--violet-500'];

    var HOLD = 2800;   /* dwell on a state, ms */
    var FADE = 700;    /* crossfade, ms — also the rail's colour transition */

    var css = getComputedStyle(d.documentElement);
    var accents = ACCENTS.map(function (name) {
      return css.getPropertyValue(name).trim();
    });

    root.style.setProperty('--kmq-fade', FADE + 'ms');
    root.style.setProperty('--kmq-hold', HOLD + 'ms');

    var current = 0;
    var timer = 0;
    var visible = true;
    var ready = false;
    var running = false;
    var generation = 0;

    function paint(next) {
      var previous = current;
      current = next;

      states.forEach(function (el, i) {
        el.setAttribute('data-on', i === current ? 'true' : 'false');
        /* Marks the layer on its way out, so it keeps its compositor layer
           for the length of the fade and loses it afterwards. */
        el.setAttribute('data-leaving', i === previous && i !== current ? 'true' : 'false');
      });

      steps.forEach(function (el, i) {
        /* "done" holds the fill at full without a transition; "live" runs it
           across the dwell. Setting live last, after a reflow-free attribute
           write, is enough — the transition is declared in CSS against the
           data-state value, so the browser starts it. */
        el.setAttribute('data-state', i === current ? 'live' : (i < current ? 'done' : 'idle'));
        el.setAttribute('aria-pressed', i === current ? 'true' : 'false');
      });

      root.style.setProperty('--kmq-accent', accents[current] || accents[0]);

      // This one first, and only then the one after it. Autoplay always
      // arrives at a state the previous tick already hydrated, but a click or
      // an arrow key can jump straight to a state the cycle has never
      // reached — and under prefers-reduced-motion that is the only way a
      // state is ever reached. Without this it would fade to an empty box.
      hydrate(current);
      hydrate((current + 1) % states.length);
    }

    function stop() {
      window.clearTimeout(timer);
      timer = 0;
      running = false;
      /* Bumped so a hydrate() still in flight from the run being stopped
         cannot paint into the next one. A boolean is not enough here: pause,
         resume and a click can all overlap inside one image's decode. */
      generation += 1;
      root.setAttribute('data-running', 'false');
    }

    /* The transition waits for its own image rather than the cycle waiting
       for every image up front. That is what keeps the second photograph off
       the critical path — it has the whole 3.5s dwell to arrive — while still
       guaranteeing that nothing fades into an undecoded bitmap. */
    function tick() {
      var era = generation;
      timer = window.setTimeout(function () {
        var next = (current + 1) % states.length;
        hydrate(next).then(function () {
          if (era !== generation || !running) return;
          paint(next);
          tick();
        });
      }, HOLD + FADE);
    }

    function start() {
      if (running || reduce || !ready || !visible || d.hidden) return;
      running = true;
      root.setAttribute('data-running', 'true');
      tick();
    }

    /* Clicking a state jumps to it and restarts the dwell, so the visitor
       gets a full look rather than whatever was left of the previous timer. */
    steps.forEach(function (el, i) {
      on(el, 'click', function () {
        stop();
        paint(i);
        start();
      });

      /* Arrow keys move along the rail. The buttons give Enter, Space, Tab
         and focus for free; this is the only part that has to be added. */
      on(el, 'keydown', function (e) {
        var delta = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
        if (!delta) return;
        e.preventDefault();
        /* In RTL the right arrow should walk the rail the way the rail is
           drawn, which is right to left. */
        if (d.documentElement.dir === 'rtl') delta = -delta;
        var next = (i + delta + steps.length) % steps.length;
        steps[next].focus();
        stop();
        paint(next);
        start();
      });
    });

    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (entries) {
        visible = entries[0].isIntersecting;
        if (visible) start(); else stop();
      }, { threshold: 0 }).observe(root);
    }

    on(d, 'visibilitychange', function () {
      if (d.hidden) stop(); else start();
    });

    /* Only state 1 ships with a live srcset. The rest carry their URLs in
       data- attributes, and this promotes one when it is nearly needed.

       Four live <picture> elements were measured at roughly 1100ms of extra
       main-thread work on a throttled mobile, and ten Lighthouse points — all
       of it image decode, at the moment of load, for three pictures nobody
       sees for another three seconds. A crossfade only ever needs the NEXT
       image ready, and the dwell is 3.5s, which is a long time to fetch and
       decode 30KB.

       img.decode() resolves once the bitmap is ready to paint, so nothing has
       to be decoded mid-fade — that stall was the first-cycle hitch the old
       hero had. It rejects on a broken image; catching keeps one missing file
       from stopping the rest. */
    var hydrated = {};

    function hydrate(i) {
      if (hydrated[i]) return hydrated[i];
      var state = states[i];
      var img = state.querySelector('img');

      [].forEach.call(state.querySelectorAll('source, img'), function (el) {
        var set = el.getAttribute('data-srcset');
        var src = el.getAttribute('data-src');
        if (set) { el.setAttribute('srcset', set); el.removeAttribute('data-srcset'); }
        if (src) { el.setAttribute('src', src); el.removeAttribute('data-src'); }
      });

      hydrated[i] = (img && img.decode)
        ? img.decode().catch(function () {})
        : Promise.resolve();
      return hydrated[i];
    }

    /* A slow or stalled image should degrade to a working cycle rather than
       to a still photograph, so whichever settles first wins. */
    function go() {
      if (ready) return;
      ready = true;
      start();
    }

    /* Only the first state gates the start. The second is fetched right
       away but nothing waits on it: the first transition is 3.5s out and
       tick() waits for its own image anyway, so putting state 2's decode in
       front of the cycle only delayed the cycle. */
    hydrate(0).then(go);
    hydrate(1);
    window.setTimeout(go, 3000);
  }());
}());
