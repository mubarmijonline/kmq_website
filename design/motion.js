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

  /* One place to say what a "card" is, so a new grid picks up the treatment
     by using an existing class rather than by editing this file. */
  var CARDS = [
    '[data-kmq-section="services"] .kmq-card',
    '.kmq-grid--pkgs .kmq-pkg',
    '.kmq-branch',
    '.kmq-post',
    '.kmq-grid--hairline .kmq-cell',
    '.kmq-strip__cell'
  ].join(',');

  function each(selector, fn) {
    Array.prototype.forEach.call(d.querySelectorAll(selector), fn);
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
      gsap.from(grid.items, {
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
        scrollTrigger: {
          trigger: grid.parent,
          start: 'top 85%',
          once: true
        }
      });
    });
  }());

  /* ---- Section heads ----------------------------------------------------- */

  (function heads() {
    each('.kmq-sectionhead, .kmq-cycle__kicker', function (el) {
      gsap.from(el, {
        y: 18,
        opacity: 0,
        duration: .5,
        ease: EASE,
        clearProps: 'transform,opacity',
        scrollTrigger: { trigger: el, start: 'top 88%', once: true }
      });
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

    each(CARDS, function (card) {
      /* rotationY, not rotateY. GSAP's canonical CSS property names are
         rotation / rotationX / rotationY; the rotateY spelling reads fine and
         silently animates nothing, which is worse than an error because the
         tween still exists and still owns the transform — it just holds it at
         zero forever, clobbering anything else that writes to it. */
      var to = gsap.quickTo(card, 'rotationY', { duration: .5, ease: EASE });
      var toX = gsap.quickTo(card, 'rotationX', { duration: .5, ease: EASE });

      /* quickTo keeps one tween alive per property and retargets it, so
         moving the pointer across a card is not a new tween per event. */
      card.addEventListener('pointermove', function (e) {
        var b = card.getBoundingClientRect();
        to(((e.clientX - b.left) / b.width - .5) * 2 * MAX);
        toX(((e.clientY - b.top) / b.height - .5) * -2 * MAX);
      });

      card.addEventListener('pointerleave', function () { to(0); toX(0); });
    });

    /* Perspective has to live on the parent or the rotation is an affine squash
       rather than a rotation. Set here rather than in the stylesheet because
       it is meaningless without this module. */
    each('[data-kmq-grid]', function (grid) {
      grid.style.perspective = '1200px';
    });
  }());

  /* ---- The CTA band lifts ------------------------------------------------ */

  (function closing() {
    var band = d.querySelector('.kmq-close__body');
    if (!band) return;
    gsap.from(band, {
      y: 24,
      opacity: 0,
      duration: .6,
      ease: EASE,
      clearProps: 'transform,opacity',
      scrollTrigger: { trigger: band, start: 'top 85%', once: true }
    });
  }());

  /* Fonts land after the first triggers are computed, and a heading that
     rewraps from two lines to three moves every start position below it.
     One refresh once the faces are in costs nothing and stops reveals firing
     at the wrong scroll offset. */
  if (d.fonts && d.fonts.ready) {
    d.fonts.ready.then(function () { ScrollTrigger.refresh(); });
  }
}());
