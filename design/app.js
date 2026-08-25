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

  function refreshMotion(delay) {
    window.setTimeout(function () {
      if (window.ScrollTrigger) window.ScrollTrigger.refresh(true);
    }, delay || 0);
  }

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
      refreshMotion();
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
      refreshMotion();
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
      var sync = function () {
        panel.style.gridTemplateRows = item.open ? '1fr' : '0fr';
        refreshMotion(320);
      };
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

  /* ---- GSAP motion ----------------------------------------------------- */

  (function motion() {
    var gsap = window.gsap;
    var ScrollTrigger = window.ScrollTrigger;
    if (!gsap || !ScrollTrigger) return;

    gsap.registerPlugin(ScrollTrigger);
    var media = gsap.matchMedia();

    function floatButton(button, lift, i, scrollTrigger, paused) {
      return gsap.fromTo(button, {
        translate: '0px 0px',
        '--kmq-ambient-scale': 1
      }, {
        translate: '0px ' + lift + 'px',
        '--kmq-ambient-scale': 1.04,
        duration: 1.3 + (i % 3) * 0.15,
        repeat: -1,
        yoyo: true,
        ease: 'sine.inOut',
        paused: !!paused,
        scrollTrigger: scrollTrigger || undefined
      });
    }

    media.add('(prefers-reduced-motion: no-preference)', function () {
      var revealing = [];
      var cleanups = [];

      d.querySelectorAll('.kmq-grid, .kmq-strip__grid, .kmq-points, .kmq-faq').forEach(function (group) {
        var items = Array.prototype.filter.call(group.children, function (el) { return !el.hidden; });
        if (!items.length) return;
        revealing = revealing.concat(items);
        items.forEach(function (el) { el.setAttribute('data-kmq-revealing', ''); });
        gsap.from(items, {
          opacity: 0,
          y: 28,
          duration: 0.72,
          stagger: 0.12,
          ease: 'power3.out',
          clearProps: 'opacity,transform',
          onComplete: function () {
            items.forEach(function (el) { el.removeAttribute('data-kmq-revealing'); });
          },
          scrollTrigger: { trigger: group, start: 'top 88%', once: true }
        });
      });

      d.querySelectorAll('.kmq-seal__ring').forEach(function (ring, i) {
        gsap.to(ring, {
          rotation: i ? '-=360' : '+=360',
          duration: i ? 14 : 18,
          repeat: -1,
          ease: 'none',
          scrollTrigger: {
            trigger: ring.closest('.kmq-seal') || ring,
            start: 'top bottom',
            end: 'bottom top',
            toggleActions: 'play pause resume pause'
          }
        });
      });

      d.querySelectorAll('.kmq-seal__halo').forEach(function (halo) {
        gsap.to(halo, {
          scale: 1.15,
          opacity: 0.82,
          duration: 1.8,
          repeat: -1,
          yoyo: true,
          ease: 'sine.inOut',
          scrollTrigger: {
            trigger: halo.closest('.kmq-seal') || halo,
            start: 'top bottom',
            end: 'bottom top',
            toggleActions: 'play pause resume pause'
          }
        });
      });

      d.querySelectorAll('.kmq-hero__layer--glow, .kmq-band__layer--glow, .kmq-close__glow, .kmq-stack__glow').forEach(function (glow, i) {
        gsap.to(glow, {
          xPercent: i % 2 ? 2.5 : -2.5,
          yPercent: i % 2 ? -1.5 : 1.5,
          scale: 1.08,
          duration: 4.5 + (i % 3),
          repeat: -1,
          yoyo: true,
          ease: 'sine.inOut',
          scrollTrigger: {
            trigger: glow.parentElement || glow,
            start: 'top bottom',
            end: 'bottom top',
            toggleActions: 'play pause resume pause'
          }
        });
      });

      d.querySelectorAll('.kmq-fab__pulse').forEach(function (pulse) {
        gsap.to(pulse, {
          scale: 1.12,
          opacity: 0.78,
          duration: 1.4,
          repeat: -1,
          yoyo: true,
          ease: 'sine.inOut'
        });
      });

      d.querySelectorAll('.kmq-btn--blue').forEach(function (button, i) {
        var sheen = d.createElement('span');
        sheen.className = 'kmq-btn__sheen';
        sheen.setAttribute('aria-hidden', 'true');
        button.appendChild(sheen);
        cleanups.push(function () { sheen.remove(); });
        gsap.fromTo(sheen, {
          xPercent: -320,
          rotation: 18
        }, {
          xPercent: 520,
          rotation: 18,
          duration: 2.4 + (i % 3) * 0.25,
          repeat: -1,
          repeatDelay: 1.2,
          ease: 'power1.inOut',
          scrollTrigger: {
            trigger: button,
            start: 'top bottom',
            end: 'bottom top',
            toggleActions: 'play pause resume pause'
          }
        });
      });

      d.querySelectorAll('.kmq-btn').forEach(function (button) {
        function press() {
          gsap.to(button, { scale: 0.96, duration: 0.12, ease: 'power2.out', overwrite: 'auto' });
        }

        function release() {
          gsap.to(button, {
            scale: 1,
            duration: 0.28,
            ease: 'back.out(2)',
            clearProps: 'transform',
            overwrite: 'auto'
          });
        }

        button.addEventListener('pointerdown', press);
        button.addEventListener('pointerup', release);
        button.addEventListener('pointercancel', release);
        button.addEventListener('pointerleave', release);
        cleanups.push(function () {
          button.removeEventListener('pointerdown', press);
          button.removeEventListener('pointerup', release);
          button.removeEventListener('pointercancel', release);
          button.removeEventListener('pointerleave', release);
        });
      });

      var heroStage = d.querySelector('.kmq-stack__stage');
      if (heroStage) {
        gsap.timeline({
          scrollTrigger: {
            trigger: heroStage.closest('.kmq-stack') || heroStage,
            start: 'top bottom',
            end: 'bottom top',
            toggleActions: 'play pause resume pause'
          }
        }).from(heroStage, {
          opacity: 0,
          y: 72,
          scale: 0.84,
          duration: 1.05,
          ease: 'power4.out',
          clearProps: 'opacity'
        }).to(heroStage, {
          y: -14,
          rotation: 0.45,
          scale: 1.018,
          duration: 2.6,
          repeat: -1,
          yoyo: true,
          ease: 'sine.inOut'
        });
      }

      var stack = d.querySelector('[data-kmq-stack]');
      var car = stack && stack.querySelector('[data-kmq-car]');
      if (car) {
        gsap.to(car, {
          y: -24,
          scale: 1.025,
          ease: 'none',
          scrollTrigger: {
            trigger: stack,
            start: 'top top',
            end: 'bottom top',
            scrub: 0.6
          }
        });
      }

      return function () {
        revealing.forEach(function (el) { el.removeAttribute('data-kmq-revealing'); });
        cleanups.forEach(function (cleanup) { cleanup(); });
      };
    });

    media.add({
      motion: '(prefers-reduced-motion: no-preference)',
      compact: '(max-width: 1023px)'
    }, function (context) {
      if (!context.conditions.motion) return;
      var compact = context.conditions.compact;
      var cards = d.querySelectorAll(
        '.kmq-card, .kmq-pkg, .kmq-branch, .kmq-post, .kmq-panel--card, ' +
        '.kmq-cell, .kmq-strip__cell, .kmq-formcard, .kmq-aside__card'
      );

      cards.forEach(function (card, i) {
        var direction = i % 2 ? 1 : -1;
        var lift = direction * (compact ? 10 : 28);
        gsap.fromTo(card, {
          translate: '0px 0px',
          '--kmq-ambient-scale': 1,
          '--kmq-ambient-rotate': '0deg'
        }, {
          translate: '0px ' + lift + 'px',
          '--kmq-ambient-scale': compact ? 1.01 : 1.028,
          '--kmq-ambient-rotate': direction * (compact ? 0.3 : 0.9) + 'deg',
          duration: 1.45 + (i % 4) * 0.18,
          delay: -(i % 5) * 0.2,
          repeat: -1,
          yoyo: true,
          ease: 'sine.inOut',
          scrollTrigger: {
            trigger: card,
            start: 'top bottom',
            end: 'bottom top',
            toggleActions: 'play pause resume pause'
          }
        });
      });

      d.querySelectorAll('.kmq-btn--blue').forEach(function (button, i) {
        if (button.classList.contains('kmq-header__cta') || button.closest('.kmq-mobilenav')) return;
        floatButton(button, compact ? -6 : -12, i, {
          trigger: button,
          start: 'top bottom',
          end: 'bottom top',
          toggleActions: 'play pause resume pause'
        });
      });
    });

    media.add({
      motion: '(prefers-reduced-motion: no-preference)',
      compact: '(max-width: 1023px)'
    }, function (context) {
      if (!context.conditions.motion) return;
      d.querySelectorAll('.kmq-sectionhead, .kmq-pagehead__body, .kmq-close__body').forEach(function (el, i) {
        var direction = (i % 2 ? -1 : 1) * (d.documentElement.dir === 'rtl' ? -1 : 1);
        gsap.from(el, {
          opacity: 0,
          x: context.conditions.compact ? 0 : direction * 42,
          y: 36,
          duration: 0.95,
          ease: 'power3.out',
          clearProps: 'opacity,transform',
          scrollTrigger: { trigger: el, start: 'top 88%', once: true }
        });
      });
    });

    media.add({
      motion: '(prefers-reduced-motion: no-preference)',
      desktopHeader: '(min-width: 1024px)'
    }, function (context) {
      if (!context.conditions.motion || !context.conditions.desktopHeader) return;
      d.querySelectorAll('.kmq-header__cta').forEach(function (button, i) {
        floatButton(button, -12, i);
      });
    });

    media.add({
      motion: '(prefers-reduced-motion: no-preference)',
      mobileHeader: '(max-width: 1023px)'
    }, function (context) {
      if (!context.conditions.motion || !context.conditions.mobileHeader) return;
      var nav = d.querySelector('.kmq-mobilenav');
      var button = nav && nav.querySelector('.kmq-btn--blue');
      if (!nav || !button) return;
      var tween = floatButton(button, -6, 0, null, true);
      var sync = function () {
        if (nav.getAttribute('data-open') === 'true') tween.play();
        else tween.pause(0);
      };
      var observer = new MutationObserver(sync);
      observer.observe(nav, { attributes: true, attributeFilter: ['data-open'] });
      sync();
      return function () { observer.disconnect(); };
    });

    media.add({
      motion: '(prefers-reduced-motion: no-preference)',
      desktop: '(min-width: 701px) and (hover: hover) and (pointer: fine)'
    }, function (context) {
      if (!context.conditions.motion || !context.conditions.desktop) return;

      d.querySelectorAll('.kmq-glyph-plate .kmq-glyph').forEach(function (icon, i) {
        gsap.to(icon, {
          y: i % 2 ? 7 : -7,
          rotation: i % 2 ? 1.5 : -1.5,
          duration: 2.4 + (i % 4) * 0.25,
          repeat: -1,
          yoyo: true,
          ease: 'sine.inOut',
          scrollTrigger: {
            trigger: icon.closest('.kmq-glyph-plate') || icon,
            start: 'top bottom',
            end: 'bottom top',
            toggleActions: 'play pause resume pause'
          }
        });
      });

      d.querySelectorAll('.kmq-shot--filled img, .kmq-card__photo img, .kmq-points__photo img').forEach(function (photo) {
        gsap.to(photo, {
          yPercent: -5,
          scale: 1.14,
          ease: 'none',
          scrollTrigger: {
            trigger: photo,
            start: 'top bottom',
            end: 'bottom top',
            scrub: 0.8
          }
        });
      });
    });

    media.add({
      motion: '(prefers-reduced-motion: no-preference)',
      hover: '(hover: hover) and (pointer: fine)'
    }, function (context) {
      if (!context.conditions.motion || !context.conditions.hover) return;
      var cleanups = [];

      d.querySelectorAll('.kmq-card, .kmq-pkg, .kmq-branch, .kmq-post, .kmq-panel--card').forEach(function (card) {
        var bounds = null;
        var tiltX = gsap.quickTo(card, 'rotationX', { duration: 0.35, ease: 'power2.out' });
        var tiltY = gsap.quickTo(card, 'rotationY', { duration: 0.35, ease: 'power2.out' });
        var lift = gsap.quickTo(card, 'y', { duration: 0.35, ease: 'power2.out' });
        var grow = gsap.quickTo(card, 'scale', { duration: 0.35, ease: 'power2.out' });

        function enter() {
          if (card.hasAttribute('data-kmq-revealing')) return;
          bounds = {
            rect: card.getBoundingClientRect(),
            scrollX: window.scrollX,
            scrollY: window.scrollY,
            width: window.innerWidth,
            height: window.innerHeight
          };
          gsap.set(card, { transformPerspective: 900 });
        }

        function move(e) {
          if (card.hasAttribute('data-kmq-revealing')) return;
          if (bounds && (bounds.scrollX !== window.scrollX || bounds.scrollY !== window.scrollY ||
                         bounds.width !== window.innerWidth || bounds.height !== window.innerHeight)) {
            bounds = null;
          }
          if (!bounds) enter();
          if (!bounds) return;
          tiltX(-((e.clientY - bounds.rect.top) / bounds.rect.height - 0.5) * 6);
          tiltY(((e.clientX - bounds.rect.left) / bounds.rect.width - 0.5) * 6);
          lift(-6);
          grow(1.01);
        }

        function leave() {
          bounds = null;
          if (card.hasAttribute('data-kmq-revealing')) return;
          tiltX(0);
          tiltY(0);
          lift(0);
          grow(1);
        }

        card.addEventListener('pointerenter', enter);
        card.addEventListener('pointermove', move);
        card.addEventListener('pointerleave', leave);
        cleanups.push(function () {
          card.removeEventListener('pointerenter', enter);
          card.removeEventListener('pointermove', move);
          card.removeEventListener('pointerleave', leave);
        });
      });

      return function () {
        cleanups.forEach(function (cleanup) { cleanup(); });
      };
    });
  }());

  /* ---- Hero protection stack -------------------------------------------
     Scroll drives four coating stages, then the car leaves and hands the page
     to the Trust strip. The CSS leaves the bare car and the first caption
     standing when this does not run at all.

     This DOES run under prefers-reduced-motion. The build is scroll-driven,
     so the visitor controls every frame of it and nothing animates on its own;
     bailing out here just deleted the hero for anyone with the setting on.
     What `reduce` suppresses below is the travel — the caption slide and the
     car's exit translate and scale. Opacity is left alone: a cross-fade is
     not motion. */

  (function stack() {
    var track = d.querySelector('[data-kmq-stack]');
    if (!track) return;

    var dull = track.querySelector('[data-kmq-dull]');
    var bar = track.querySelector('[data-kmq-bar]');
    var glow = track.querySelector('.kmq-stack__glow');
    if (!dull || !bar || !glow) return;

    var caps = track.querySelectorAll('[data-kmq-cap]');
    var dots = track.querySelectorAll('[data-kmq-dot]');
    var lbls = track.querySelectorAll('[data-kmq-lbl]');

    /* Stage 2 and 4 each wipe two layers at once: a rim glow and a coating. */
    var groups = [['1a', '1b'], ['2'], ['3a', '3b']].map(function (ids) {
      return ids.map(function (id) {
        return track.querySelector('[data-kmq-layer="' + id + '"]');
      });
    });

    /* Fifths of the track, matching the five scroll steps --kmq-stack-step
       cuts it into: one on the bare car, three wipes, one dwelling on the
       finished car so the buttons can be read. Fractions, not distances —
       retiming the hero is a one-line change in the stylesheet and these
       follow it. Nothing runs the frame out: the pin's own release scrolls
       the finished car away, so the hero hands over to the section below
       without a blank screen in between. */
    var HOLD = 1 / 5;   /* stage 0 dwell */
    var BUILD = 4 / 5;  /* three wipes finish here, then the frame dwells */
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
        /* A fraction, not a clip-path: the stylesheet turns it into one, so
           the halo the cut has to clear stays a CSS number. 1 is hidden. */
        var wipe = (1 - e).toFixed(4);
        els.forEach(function (el) { if (el) el.style.setProperty('--kmq-wipe', wipe); });
      });

      var active = Math.min(3, Math.floor(seg + 0.35));

      function mark(el, i) {
        el.setAttribute('data-state', i === active ? 'now' : i < active ? 'done' : 'next');
      }

      caps.forEach(function (c, i) {
        c.setAttribute('data-lit', i === active ? 'true' : 'false');
        if (!reduce) c.style.transform = i === active ? 'translateY(0)' : 'translateY(20px)';
      });
      dots.forEach(mark);
      lbls.forEach(mark);

      /* Unprotected paint reads flat, then each coating lifts it back. The
         ceiling is high because the dull pass now cross-fades to a flat grey
         copy rather than screening white over black paint; at 0.17 the swap to
         a silver car left it invisible. */
      dull.style.opacity = (0.55 * Math.min(1, p / HOLD) * (1 - Math.min(1, Math.max(0, seg)))).toFixed(3);
      bar.style.width = (p * 100).toFixed(2) + '%';
      glow.style.opacity = (0.5 + 0.5 * t).toFixed(3);
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
