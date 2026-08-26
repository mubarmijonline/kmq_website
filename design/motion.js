/* KMQ motion.
 *
 * GSAP and ScrollTrigger, in their own bundle so the hero does not wait for
 * them. Everything here is decoration: the page is complete and readable with
 * this file absent, and every element it touches is visible before it runs.
 *
 * That last point is the rule the whole file is built around. Reveals use
 * gsap.from(), never a CSS class that starts an element at opacity 0 — if the
 * bundle 404s, or the browser is too old for GSAP, or a ScrollTrigger never
 * fires because a section is inside a container it did not expect, a
 * from() tween leaves the element exactly where the stylesheet put it.
 * A .is-hidden class waiting for JS to remove it would leave a blank page.
 *
 * Two hard constraints carried over from the hero rebuild:
 *
 *   1. transform and opacity only. Nothing here animates a layout property,
 *      a filter or a box-shadow.
 *   2. ScrollTrigger owns the scroll listener. It is one rAF-batched listener
 *      for every trigger on the page rather than one per element, which is
 *      the thing that made the old hero slow. Do not add another.
 */
(function () {
  'use strict';

  if (!window.gsap || !window.ScrollTrigger) return;

  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  /* Under the setting nothing moves and nothing is hidden — which is the
     whole point of never hiding anything in CSS. Bail before registering a
     single trigger, so there is no scroll work either. */
  if (reduce) return;

  gsap.registerPlugin(ScrollTrigger);

  var d = document;
  var EASE = 'power2.out';

  /* Two sets, and the difference matters.

     CARDS is everything that arrives on scroll. A reveal is safe anywhere
     because every element ends exactly where the stylesheet put it.

     FLOATERS is the subset that may also drift and tilt: free-standing cards
     sitting in a grid with a real gap. The one left out is not an oversight —
     .kmq-grid--hairline has a 1px gap and paints its rules *with* that gap, so
     drifting or tilting a cell slides it off the line that is supposed to
     separate it, which does not read as motion, it reads as broken. */
  var CARDS = [
    '[data-kmq-section="services"] .kmq-card',
    '.kmq-grid--pkgs .kmq-pkg',
    '.kmq-branch',
    '.kmq-post',
    '.kmq-grid--hairline .kmq-cell',
    '.kmq-strip__cell'
  ].join(',');

  var FLOATERS = [
    '.kmq-card--shot',
    '.kmq-grid--pkgs .kmq-pkg',
    '.kmq-branch',
    '.kmq-post',
    /* Joined the list once the proof strip stopped being four cells divided by
       borders and became four cards with a gap. Nothing else changed here. */
    '.kmq-strip__cell'
  ].join(',');

  function isFloater(el) { return el.matches(FLOATERS); }

  function each(selector, fn) {
    Array.prototype.forEach.call(d.querySelectorAll(selector), fn);
  }

  /* Every reveal goes through here, and the reason is a bug this had.

     A scroll reveal starting at "top 85%" hides anything whose top has not
     reached 85% of the viewport. On the English home page the proof strip sat
     at 820px in a 900px viewport — on screen, plainly visible, and 10px short
     of its own trigger line. It stayed at opacity 0 until the visitor
     scrolled. The Arabic page was 126px shorter above it and fired, which is
     why it only showed up in one locale.

     So the rule is: if any part of the element is on screen when this runs, it
     animates now and never gets a trigger. Only things genuinely below the
     fold wait to be scrolled to. An element that is visible is never
     invisible, whatever the numbers say. */
  function reveal(targets, vars, triggerEl) {
    var box = triggerEl.getBoundingClientRect();
    var onScreen = box.top < window.innerHeight && box.bottom > 0;

    if (onScreen) return gsap.from(targets, vars);

    var scrolled = {};
    for (var k in vars) scrolled[k] = vars[k];
    scrolled.scrollTrigger = { trigger: triggerEl, start: 'top 85%', once: true };
    return gsap.from(targets, scrolled);
  }

  /* ---- Cards arrive ------------------------------------------------------
     Per grid, not per card: a stagger only reads as a stagger when the row
     it belongs to enters together. Triggering each card separately gives
     eleven independent fades that look like a slow page rather than a
     deliberate one. */

  (function cardsArrive() {
    var grids = {};
    each(CARDS, function (el) {
      var parent = el.parentElement;
      if (!parent) return;
      var key = parent.getAttribute('data-kmq-grid');
      if (!key) {
        key = 'g' + Object.keys(grids).length;
        parent.setAttribute('data-kmq-grid', key);
        grids[key] = { parent: parent, items: [] };
      }
      grids[key].items.push(el);
    });

    Object.keys(grids).forEach(function (key) {
      var grid = grids[key];
      reveal(grid.items, {
        y: 26,
        opacity: 0,
        duration: .55,
        ease: EASE,
        stagger: .07,
        /* clearProps so the cards are left with no inline transform once the
           tween is done. Without it every card keeps a matrix() that beats
           the hover lift declared in CSS, and the hover silently stops
           working — a bug that only shows up after you have scrolled past. */
        clearProps: 'transform,opacity',
        onComplete: function () { float(grid.items); }
      }, grid.parent);
    });
  }());

  /* ---- Cards keep moving -------------------------------------------------
     A slow vertical drift that never stops, so a grid is alive whether or not
     a pointer is anywhere near it.

     Started from the reveal's onComplete rather than at init, because both
     write `y` and the reveal's clearProps would wipe the float's transform if
     they overlapped. By the time this runs the reveal is finished and gone.

     Each card gets its own duration and its own delay. Identical timings look
     like the whole grid is on one hinge; a couple of tenths of drift between
     neighbours is what makes it read as several separate objects. The offsets
     are derived from the index rather than random so a reload looks the same
     as the last one. */

  var FLOAT_Y = 16;   /* px of travel, peak to rest */

  function float(items) {
    var cards = items.filter(isFloater);
    if (!cards.length) return;

    /* Phase comes from the column, not from the index, and that is what makes
       a visible amplitude safe. Cards in the same column share a phase, so two
       cards stacked in a grid rise and fall together and the gap between rows
       never closes — at 16px with independent phases, neighbours would shut a
       22px gap and briefly overlap. Across a row the phases differ, which is
       where the movement is actually seen. */
    var columns = {};
    cards.forEach(function (el) {
      var x = Math.round(el.offsetLeft / 8);
      if (!(x in columns)) columns[x] = Object.keys(columns).length;
    });

    cards.forEach(function (el) {
      var col = columns[Math.round(el.offsetLeft / 8)];
      gsap.to(el, {
        y: -FLOAT_Y,
        /* A touch of roll, on the z axis the pointer tilt does not use. Half a
           degree is under what reads as rotation and over what reads as
           nothing — it stops the drift looking like a lift. */
        rotation: col % 2 ? -0.5 : 0.5,
        duration: 3 + (col % 3) * .35,
        delay: col * .55,
        ease: 'sine.inOut',
        repeat: -1,
        yoyo: true
      });
    });
  }

  /* ---- Proof strip icons -------------------------------------------------
     The wells lift a beat after their card lands, so each proof point reads as
     two pieces arriving rather than one slab. Scale and opacity only, on an
     element the drift and the tilt do not touch. */

  (function proofIcons() {
    var wells = d.querySelectorAll('.kmq-strip__cell .kmq-iconframe');
    if (!wells.length) return;
    reveal(wells, {
      scale: .6,
      opacity: 0,
      duration: .45,
      ease: 'back.out(2)',
      stagger: .08,
      delay: .15,
      clearProps: 'transform,opacity'
    }, d.querySelector('.kmq-strip'));
  }());

  /* ---- Section heads ----------------------------------------------------- */

  (function heads() {
    each('.kmq-sectionhead, .kmq-cycle__kicker', function (el) {
      reveal(el, {
        y: 18,
        opacity: 0,
        duration: .5,
        ease: EASE,
        clearProps: 'transform,opacity'
      }, el);
    });
  }());

  /* ---- Cards move --------------------------------------------------------
     Two things, both cheap.

     A slow parallax drift on the photograph inside a card, so a grid has
     depth as it passes rather than being a flat sheet. The image is already
     object-fit: cover in a fixed-ratio well, so there is room to move it
     without exposing an edge — 6% of its own height, which the well crops.

     And a pointer tilt on the card itself. Rotation is tiny on purpose: this
     is a protection company, and a card that flops toward the cursor reads as
     a toy. 4 degrees is enough to say the surface is glossy. */

  (function photosDrift() {
    each('.kmq-card--shot .kmq-shot img, .kmq-branch .kmq-shot img, .kmq-post__shot img',
      function (img) {
        gsap.fromTo(img,
          { yPercent: -3 },
          {
            yPercent: 3,
            ease: 'none',
            scrollTrigger: {
              trigger: img,
              start: 'top bottom',
              end: 'bottom top',
              scrub: true
            }
          });
      });
  }());

  (function cardsTilt() {
    /* Pointer only. A touch device fires pointerenter on tap and would leave
       the card tilted with no pointerleave to put it back. */
    if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;

    var MAX = 4;  /* degrees */

    /* Same subset as the float, for the same reason: tilting a cell whose
       divider is a border on its neighbour slides it off that line. */

    each(FLOATERS, function (card) {
      /* rotationY, not rotateY. GSAP's canonical CSS property names are
         rotation / rotationX / rotationY; the rotateY spelling reads fine and
         silently animates nothing, which is worse than an error because the
         tween still exists and still owns the transform — it just holds it at
         zero forever, clobbering anything else that writes to it. */
      var to = gsap.quickTo(card, 'rotationY', { duration: .5, ease: EASE });
      var toX = gsap.quickTo(card, 'rotationX', { duration: .5, ease: EASE });

      /* The lift moves to scale here, and that is forced rather than chosen.
         The idle float owns `y` for the life of the page, so the CSS
         :hover translateY is overridden the moment GSAP touches the element —
         it is left in the stylesheet on purpose, because without this bundle
         it is the only lift there is. With the bundle, scale does the job and
         does not contend for a property something else is already animating. */
      var toScale = gsap.quickTo(card, 'scale', { duration: .35, ease: EASE });

      /* quickTo keeps one tween alive per property and retargets it, so
         moving the pointer across a card is not a new tween per event. */
      card.addEventListener('pointermove', function (e) {
        var b = card.getBoundingClientRect();
        to(((e.clientX - b.left) / b.width - .5) * 2 * MAX);
        toX(((e.clientY - b.top) / b.height - .5) * -2 * MAX);
      });

      card.addEventListener('pointerenter', function () { toScale(1.02); });
      card.addEventListener('pointerleave', function () {
        to(0); toX(0); toScale(1);
      });
    });

    /* Perspective has to live on the parent or the rotation is an affine squash
       rather than a rotation. Set here rather than in the stylesheet because
       it is meaningless without this module. */
    each('[data-kmq-grid]', function (grid) {
      grid.style.perspective = '1200px';
    });
  }());

  /* ---- The warranty seal -------------------------------------------------
     The two diamonds counter-rotate and the halo breathes, so the seal reads
     as a mark being stamped rather than a graphic sitting still. Slow on
     purpose: a full turn takes a minute, which is under the threshold where
     the eye starts tracking it instead of reading the copy beside it.

     The numeral counts up when the band arrives. It ends on exactly the
     string the content file holds — the tween drives a number and the last
     frame writes the original text back, so nothing here can leave a value
     the copy did not say. */

  (function seal() {
    var seal = d.querySelector('.kmq-seal');
    if (!seal) return;

    var outer = seal.querySelector('.kmq-seal__ring:not(.kmq-seal__ring--inner)');
    var inner = seal.querySelector('.kmq-seal__ring--inner');
    var halo = seal.querySelector('.kmq-seal__halo');
    var num = seal.querySelector('.kmq-seal__num');

    /* The rings sway a few degrees either side of 45 rather than turning all
       the way round. A full rotation was tried and rejected: these are squares
       rotated 45deg to read as diamonds, so anywhere except 45 is a tilted
       square, and a continuous turn spends almost all of its time with the
       mark out of shape. Six degrees of sway keeps the diamond and still
       moves. They lean opposite ways so the pair counter-rotates. */
    if (outer) {
      gsap.fromTo(outer, { rotation: 45 }, {
        rotation: 51, duration: 7, ease: 'sine.inOut', repeat: -1, yoyo: true
      });
    }
    if (inner) {
      gsap.fromTo(inner, { rotation: 45 }, {
        rotation: 39, duration: 5.5, ease: 'sine.inOut', repeat: -1, yoyo: true
      });
    }

    if (halo) {
      gsap.to(halo, {
        scale: 1.06, opacity: .72,
        duration: 3.4, ease: 'sine.inOut', repeat: -1, yoyo: true
      });
    }

    if (num) {
      var text = num.textContent.trim();
      var target = parseInt(text, 10);
      if (!isNaN(target)) {
        var box = { v: 0 };
        gsap.to(box, {
          v: target,
          duration: 1.1,
          ease: 'power2.out',
          scrollTrigger: { trigger: seal, start: 'top 80%', once: true },
          onUpdate: function () { num.textContent = String(Math.round(box.v)); },
          /* Whatever the tween rounded to on its last frame, the element ends
             holding the exact string the content file shipped. */
          onComplete: function () { num.textContent = text; }
        });
      }
    }
  }());

  /* ---- The CTA band lifts ------------------------------------------------ */

  (function closing() {
    var band = d.querySelector('.kmq-close__body');
    if (!band) return;
    reveal(band, {
      y: 24,
      opacity: 0,
      duration: .6,
      ease: EASE,
      clearProps: 'transform,opacity'
    }, band);
  }());

  /* Fonts land after the first triggers are computed, and a heading that
     rewraps from two lines to three moves every start position below it.
     One refresh once the faces are in costs nothing and stops reveals firing
     at the wrong scroll offset. */
  if (d.fonts && d.fonts.ready) {
    d.fonts.ready.then(function () { ScrollTrigger.refresh(); });
  }
}());
