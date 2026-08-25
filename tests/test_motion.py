"""Browser checks for the public site's motion layer."""

from pathlib import Path
import re

import pytest
from playwright.sync_api import sync_playwright

from app import create_app

ROOT = Path(__file__).resolve().parent.parent
GSAP = "https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"
SCROLL_TRIGGER = (
    "https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/ScrollTrigger.min.js"
)


@pytest.fixture()
def browser():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        yield browser
        browser.close()


def motion_page(browser, *, reduced=False, mobile=False):
    context = browser.new_context(
        viewport={"width": 390, "height": 844} if mobile else {"width": 1280, "height": 720},
        reduced_motion="reduce" if reduced else "no-preference",
        has_touch=mobile,
    )
    page = context.new_page()
    page.set_content(
        """
        <style>
          body { margin: 0; }
          .spacer { height: 900px; }
          .kmq-sectionhead { min-height: 120px; }
        </style>
        <div class="spacer"></div>
        <section class="kmq-section">
          <div class="kmq-sectionhead" id="reveal"><h2>Protection</h2></div>
          <div class="kmq-grid">
            <article class="kmq-card" id="card">Paint protection</article>
            <article class="kmq-card">Window tint</article>
          </div>
          <div class="kmq-sectionhead" id="reveal-two"><h2>Warranty</h2></div>
        </section>
        <div class="spacer"></div>
        """
    )
    page.add_script_tag(url=GSAP)
    page.add_script_tag(url=SCROLL_TRIGGER)
    page.add_script_tag(path=str(ROOT / "design" / "app.js"))
    return context, page


def parallax_page(browser):
    context = browser.new_context(viewport={"width": 1280, "height": 720})
    page = context.new_page()
    page.set_content(
        """
        <style>
          body { margin: 0; }
          [data-kmq-stack] { height: 2400px; }
          .kmq-stack__pin { position: sticky; top: 0; height: 720px; }
          [data-kmq-car] { width: 300px; height: 120px; }
        </style>
        <section data-kmq-stack>
          <div class="kmq-stack__pin">
            <div class="kmq-stack__glow"></div>
            <div data-kmq-car id="car">Car</div>
            <div data-kmq-dull></div>
            <i data-kmq-bar></i>
          </div>
        </section>
        <div style="height:900px"></div>
        """
    )
    page.add_script_tag(url=GSAP)
    page.add_script_tag(url=SCROLL_TRIGGER)
    page.add_script_tag(path=str(ROOT / "design" / "app.js"))
    return context, page


def expanding_faq_page(browser):
    context = browser.new_context(viewport={"width": 1280, "height": 720})
    page = context.new_page()
    page.set_content(
        """
        <style>
          body { margin: 0; }
          .lead { height: 650px; }
          .spacer { height: 900px; }
          .kmq-faq__a { display: grid; grid-template-rows: 0fr; }
          .kmq-faq__a > div { overflow: hidden; }
          .answer { height: 600px; }
          .kmq-sectionhead { min-height: 120px; }
        </style>
        <div class="lead"></div>
        <div class="kmq-faq" data-kmq-faq>
          <details id="faq">
            <summary>Question</summary>
            <div class="kmq-faq__a"><div><p class="answer">Answer</p></div></div>
          </details>
        </div>
        <div class="kmq-sectionhead" id="late"><h2>Later section</h2></div>
        <div class="spacer"></div>
        """
    )
    page.add_script_tag(url=GSAP)
    page.add_script_tag(url=SCROLL_TRIGGER)
    page.add_script_tag(path=str(ROOT / "design" / "app.js"))
    return context, page


def catchy_page(browser, *, reduced=False, mobile=False, landscape_touch=False):
    viewport = {"width": 844, "height": 390} if landscape_touch else (
        {"width": 390, "height": 844} if mobile else {"width": 1280, "height": 720}
    )
    context = browser.new_context(
        viewport=viewport,
        reduced_motion="reduce" if reduced else "no-preference",
        has_touch=mobile or landscape_touch,
    )
    page = context.new_page()
    page.set_content(
        """
        <style>
          body { margin: 0; min-height: 2600px; }
          .kmq-glyph-plate, .kmq-seal__ring, .kmq-seal__halo,
          .kmq-fab, .kmq-btn, .kmq-card { display: block; width: 100px; height: 100px; }
          .kmq-btn { background: linear-gradient(90deg, #0878ad, #57bfee, #0878ad); }
          .kmq-btn--blue { box-shadow: 0 0 0 6px rgba(46, 168, 229, .10); }
          #ambient-card, #catchy-cta {
            rotate: var(--kmq-ambient-rotate, 0deg);
            scale: var(--kmq-ambient-scale, 1);
          }
          .kmq-btn__sheen { position: absolute; inset-block: -55%; width: 34%; }
          .kmq-card__photo { margin-top: 900px; width: 600px; height: 360px; overflow: hidden; }
          .kmq-card__photo img { display: block; width: 100%; height: 100%; object-fit: cover; }
          .kmq-stack__stage { width: 600px; height: 320px; }
          .kmq-mobilenav[data-open="false"] { display: none; }
          .kmq-mobilenav[data-open="true"] { display: block; }
          @media (max-width: 1023px) { .kmq-header__cta { display: none; } }
        </style>
        <span class="kmq-glyph-plate" id="floating-icon"><span class="kmq-glyph"></span></span>
        <div class="kmq-seal">
          <span class="kmq-seal__ring" id="seal-ring"></span>
          <span class="kmq-seal__ring kmq-seal__ring--inner"></span>
          <span class="kmq-seal__halo"></span>
        </div>
        <a class="kmq-btn kmq-btn--blue" id="catchy-cta">Book now</a>
        <a class="kmq-btn kmq-btn--blue kmq-header__cta" id="desktop-header-cta">Header CTA</a>
        <button type="button" data-kmq-burger aria-expanded="false" aria-controls="test-mobile-nav">Menu</button>
        <div class="kmq-mobilenav" id="test-mobile-nav" data-kmq-mobilenav data-open="false">
          <a class="kmq-btn kmq-btn--blue" id="mobile-menu-cta">Mobile CTA</a>
        </div>
        <article class="kmq-card" id="ambient-card">Card</article>
        <a class="kmq-fab" id="catchy-fab"><span class="kmq-fab__pulse">Chat</span></a>
        <div class="kmq-hero__layer--glow"></div>
        <div class="kmq-band__layer--glow"></div>
        <div class="kmq-close__glow"></div>
        <div class="kmq-stack__stage" id="hero-stage"><div class="kmq-stack__car"></div></div>
        <div class="kmq-card__photo">
          <img id="moving-photo" alt="Car" src="data:image/gif;base64,R0lGODlhAQABAAAAACw=">
        </div>
        """
    )
    page.add_script_tag(url=GSAP)
    page.add_script_tag(url=SCROLL_TRIGGER)
    page.add_script_tag(path=str(ROOT / "design" / "app.js"))
    return context, page


def test_section_reveals_when_it_enters_the_viewport(browser):
    context, page = motion_page(browser)
    reveal = page.locator("#reveal")

    assert float(reveal.evaluate("el => getComputedStyle(el).opacity")) < 0.1
    reveal.scroll_into_view_if_needed()
    page.wait_for_timeout(900)
    assert float(reveal.evaluate("el => getComputedStyle(el).opacity")) > 0.95

    context.close()


def test_section_entrances_alternate_horizontal_direction(browser):
    context, page = motion_page(browser)
    first_x = page.locator("#reveal").evaluate(
        "el => new DOMMatrix(getComputedStyle(el).transform).m41"
    )
    second_x = page.locator("#reveal-two").evaluate(
        "el => new DOMMatrix(getComputedStyle(el).transform).m41"
    )

    assert abs(first_x) > 10
    assert abs(second_x) > 10
    assert first_x * second_x < 0

    context.close()


def test_mobile_reveals_stay_vertical_without_horizontal_overflow(browser):
    context, page = motion_page(browser, mobile=True)
    reveal = page.locator("#reveal")
    matrix = reveal.evaluate(
        """el => {
          const m = new DOMMatrix(getComputedStyle(el).transform);
          return { x: m.m41, y: m.m42 };
        }"""
    )

    assert abs(matrix["x"]) < 0.1
    assert matrix["y"] > 20
    assert page.evaluate(
        "document.documentElement.scrollWidth === document.documentElement.clientWidth"
    )
    context.close()


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_rendered_mobile_home_stays_inside_viewport(browser, monkeypatch, lang):
    monkeypatch.setenv("SECRET_KEY", "motion-layout-test")
    app = create_app({"ENV_NAME": "prod", "WHATSAPP_NUMBER": ""})
    html = app.test_client().get(f"/{lang}/").get_data(as_text=True)
    html = re.sub(r"<script\b.*?</script>", "", html, flags=re.DOTALL)
    html = re.sub(r"<link\b[^>]*rel=\"stylesheet\"[^>]*>", "", html)

    context = browser.new_context(viewport={"width": 390, "height": 844}, has_touch=True)
    page = context.new_page()
    page.set_content(html)
    for source in ("tokens.css", "base.css", "components.css"):
        page.add_style_tag(path=str(ROOT / "design" / source))
    page.add_script_tag(url=GSAP)
    page.add_script_tag(url=SCROLL_TRIGGER)
    page.add_script_tag(path=str(ROOT / "design" / "app.js"))
    page.wait_for_timeout(250)

    assert page.evaluate(
        "document.documentElement.scrollWidth === document.documentElement.clientWidth"
    )
    overflow = page.evaluate(
        """() => [...document.querySelectorAll(
          '.kmq-sectionhead, .kmq-close__body, .kmq-strip__cell'
        )].filter(el => {
          const r = el.getBoundingClientRect();
          return r.left < -0.5 || r.right > innerWidth + 0.5;
        }).length"""
    )
    assert overflow == 0
    context.close()


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_home_trust_strip_uses_prominent_icons_and_type(browser, monkeypatch, lang):
    """The home trust claims must stay visually prominent in both locales."""
    monkeypatch.setenv("SECRET_KEY", "trust-strip-layout-test")
    app = create_app({"ENV_NAME": "prod", "WHATSAPP_NUMBER": ""})
    html = app.test_client().get(f"/{lang}/").get_data(as_text=True)
    html = re.sub(r"<script\b.*?</script>", "", html, flags=re.DOTALL)
    html = re.sub(r"<link\b[^>]*rel=\"stylesheet\"[^>]*>", "", html)

    context = browser.new_context(viewport={"width": 1280, "height": 720})
    page = context.new_page()
    page.set_content(html)
    for source in ("tokens.css", "base.css", "components.css"):
        page.add_style_tag(path=str(ROOT / "design" / source))

    sizes = page.locator(".kmq-strip__cell").first.evaluate(
        """cell => {
          const plate = cell.querySelector('.kmq-glyph-plate');
          const glyph = cell.querySelector('.kmq-glyph');
          const title = cell.querySelector('.kmq-strip__title');
          const meta = cell.querySelector('.kmq-strip__meta');
          return {
            plate: plate.getBoundingClientRect().width,
            glyph: glyph.getBoundingClientRect().width,
            title: parseFloat(getComputedStyle(title).fontSize),
            meta: parseFloat(getComputedStyle(meta).fontSize)
          };
        }"""
    )

    assert 116 <= sizes["plate"] <= 120
    assert 68 <= sizes["glyph"] <= 72
    assert 17.5 <= sizes["title"] <= 18.5
    assert 11.5 <= sizes["meta"] <= 12.5
    context.close()


def test_visible_decorations_have_continuous_ambient_motion(browser):
    context, page = catchy_page(browser)

    page.wait_for_function(
        """() => {
          const m = new DOMMatrix(getComputedStyle(document.querySelector('#seal-ring')).transform);
          return Math.abs(m.m12) > 0.01;
        }""",
        timeout=1600,
    )
    page.wait_for_function(
        """() => {
          const m = new DOMMatrix(getComputedStyle(document.querySelector('#floating-icon .kmq-glyph')).transform);
          return Math.abs(m.m42) > 1;
        }""",
        timeout=1600,
    )

    context.close()


def test_first_screen_hero_visibly_enters_and_keeps_floating(browser):
    context, page = catchy_page(browser)
    stage = page.locator("#hero-stage")
    stage.scroll_into_view_if_needed()

    page.wait_for_function(
        """() => {
          const m = new DOMMatrix(getComputedStyle(document.querySelector('#hero-stage')).transform);
          return Math.abs(m.m42) > 8 || Math.hypot(m.m11, m.m12) < 0.98;
        }""",
        timeout=1800,
    )
    page.wait_for_timeout(1400)
    first = stage.evaluate("el => getComputedStyle(el).transform")
    page.wait_for_timeout(350)
    second = stage.evaluate("el => getComputedStyle(el).transform")

    assert first != second
    context.close()


def test_cards_keep_floating_without_hover(browser):
    context, page = catchy_page(browser)
    card = page.locator("#ambient-card")

    page.wait_for_function(
        """() => {
          const value = getComputedStyle(document.querySelector('#ambient-card')).translate;
          return value !== 'none' && Math.abs(parseFloat(value.split(' ')[1])) > 1;
        }""",
        timeout=1800,
    )
    first = card.evaluate("el => getComputedStyle(el).translate")
    page.wait_for_timeout(300)
    second = card.evaluate("el => getComputedStyle(el).translate")

    assert first != second
    context.close()


def test_blue_ctas_keep_moving_without_interaction(browser):
    context, page = catchy_page(browser)
    cta = page.locator("#catchy-cta")

    page.wait_for_function(
        """() => {
          const value = getComputedStyle(document.querySelector('#catchy-cta')).translate;
          return value !== 'none' && Math.abs(parseFloat(value.split(' ')[1])) > 1;
        }""",
        timeout=1800,
    )
    first = cta.evaluate("el => getComputedStyle(el).translate")
    page.wait_for_timeout(300)
    second = cta.evaluate("el => getComputedStyle(el).translate")

    assert first != second
    context.close()


def test_card_ambient_motion_is_visibly_strong(browser):
    context, page = catchy_page(browser)
    page.wait_for_function(
        """() => {
          const style = getComputedStyle(document.querySelector('#ambient-card'));
          const y = parseFloat(style.translate.split(' ')[1]);
          return Math.abs(y) > 20 && parseFloat(style.scale) > 1.015 &&
            Math.abs(parseFloat(style.rotate)) > 0.4;
        }""",
        timeout=2200,
    )
    context.close()


def test_cta_ambient_motion_has_visible_lift_scale_and_glow(browser):
    context, page = catchy_page(browser)
    page.wait_for_function(
        """() => {
          const style = getComputedStyle(document.querySelector('#catchy-cta'));
          const y = parseFloat(style.translate.split(' ')[1]);
          return Math.abs(y) > 9 && parseFloat(style.scale) > 1.02 &&
            style.boxShadow !== 'none';
        }""",
        timeout=2200,
    )
    context.close()


def test_hidden_desktop_header_cta_does_not_animate_on_mobile(browser):
    context, page = catchy_page(browser, mobile=True)
    cta = page.locator("#desktop-header-cta")
    page.wait_for_timeout(500)

    assert cta.evaluate("el => getComputedStyle(el).display") == "none"
    assert cta.evaluate("el => getComputedStyle(el).translate") == "none"
    context.close()


def test_mobile_menu_cta_starts_moving_when_menu_opens(browser):
    context, page = catchy_page(browser, mobile=True)
    cta = page.locator("#mobile-menu-cta")

    page.locator("[data-kmq-burger]").click()
    page.wait_for_function(
        """() => {
          const value = getComputedStyle(document.querySelector('#mobile-menu-cta')).translate;
          return value !== 'none' && Math.abs(parseFloat(value.split(' ')[1])) > 0.5;
        }""",
        timeout=1800,
    )
    context.close()


def test_glows_warranty_halo_and_chat_button_pulse(browser):
    context, page = catchy_page(browser)

    for selector in (".kmq-seal__halo", ".kmq-fab__pulse", ".kmq-hero__layer--glow"):
        page.wait_for_function(
            """selector => {
              const m = new DOMMatrix(getComputedStyle(document.querySelector(selector)).transform);
              return Math.abs(m.m11 - 1) > 0.005 || Math.abs(m.m42) > 1;
            }""",
            arg=selector,
            timeout=1800,
        )

    context.close()


def test_photography_zooms_and_drifts_with_scroll(browser):
    context, page = catchy_page(browser)
    photo = page.locator("#moving-photo")

    target_scroll = photo.evaluate(
        "el => el.getBoundingClientRect().top + scrollY - innerHeight / 2"
    )
    page.evaluate("y => window.scrollTo(0, y)", target_scroll)
    page.wait_for_timeout(500)
    moved = photo.evaluate(
        """el => {
          const m = new DOMMatrix(getComputedStyle(el).transform);
          return { y: m.m42, scale: Math.hypot(m.m11, m.m12, m.m13) };
        }"""
    )
    assert moved["scale"] > 1.03
    assert moved["y"] < -3

    context.close()


def test_primary_cta_has_moving_sheen_and_press_feedback(browser):
    context, page = catchy_page(browser)
    cta = page.locator("#catchy-cta")
    sheen = cta.locator(".kmq-btn__sheen")
    sheen.wait_for(state="attached")
    initial_transform = sheen.evaluate("el => getComputedStyle(el).transform")

    page.wait_for_function(
        """initial => getComputedStyle(document.querySelector('#catchy-cta .kmq-btn__sheen')).transform !== initial""",
        arg=initial_transform,
        timeout=1800,
    )

    cta.dispatch_event("pointerdown")
    page.wait_for_timeout(180)
    pressed_scale = cta.evaluate(
        """el => {
          const m = new DOMMatrix(getComputedStyle(el).transform);
          return Math.hypot(m.m11, m.m12, m.m13);
        }"""
    )
    assert pressed_scale < 0.98

    cta.dispatch_event("pointerup")
    page.wait_for_timeout(350)
    released_scale = cta.evaluate(
        """el => {
          const m = new DOMMatrix(getComputedStyle(el).transform);
          return Math.hypot(m.m11, m.m12, m.m13);
        }"""
    )
    assert released_scale > 0.995

    context.close()


def test_catchy_motion_stays_still_when_reduced_motion_is_enabled(browser):
    context, page = catchy_page(browser, reduced=True)
    cta = page.locator("#catchy-cta")
    page.wait_for_timeout(500)

    for selector in (
        "#floating-icon .kmq-glyph", "#seal-ring", ".kmq-seal__halo",
        ".kmq-fab__pulse", ".kmq-hero__layer--glow", "#hero-stage", "#moving-photo",
    ):
        assert page.locator(selector).evaluate(
            "el => getComputedStyle(el).transform"
        ) == "none"
    for selector in ("#ambient-card", "#catchy-cta"):
        assert page.locator(selector).evaluate(
            "el => getComputedStyle(el).translate"
        ) == "none"
    assert cta.locator(".kmq-btn__sheen").count() == 0

    context.close()


def test_mobile_keeps_heavier_parallax_stationary(browser):
    context, page = catchy_page(browser, mobile=True)
    icon = page.locator("#floating-icon .kmq-glyph")
    photo = page.locator("#moving-photo")

    page.wait_for_timeout(500)
    assert icon.evaluate("el => getComputedStyle(el).transform") == "none"

    page.evaluate(
        """el => scrollTo(0, el.getBoundingClientRect().top + scrollY - innerHeight / 2)""",
        photo.element_handle(),
    )
    page.wait_for_timeout(500)
    assert photo.evaluate("el => getComputedStyle(el).transform") == "none"
    assert page.locator(".kmq-fab__pulse").evaluate(
        "el => getComputedStyle(el).transform"
    ) != "none"

    context.close()


def test_mobile_ambient_motion_is_smaller_but_still_visible(browser):
    context, page = catchy_page(browser, mobile=True)
    card = page.locator("#ambient-card")
    cta = page.locator("#catchy-cta")
    card_values = []
    cta_values = []

    for _ in range(18):
        card_values.append(card.evaluate(
            "el => Math.abs(parseFloat(getComputedStyle(el).translate.split(' ')[1]) || 0)"
        ))
        cta_values.append(cta.evaluate(
            "el => Math.abs(parseFloat(getComputedStyle(el).translate.split(' ')[1]) || 0)"
        ))
        page.wait_for_timeout(100)

    assert 7 < max(card_values) <= 10.5
    assert 4 < max(cta_values) <= 6.5
    context.close()


def test_landscape_touch_device_skips_desktop_only_motion(browser):
    context, page = catchy_page(browser, landscape_touch=True)
    page.wait_for_timeout(500)

    assert page.locator("#floating-icon .kmq-glyph").evaluate(
        "el => getComputedStyle(el).transform"
    ) == "none"
    assert page.locator("#moving-photo").evaluate(
        "el => getComputedStyle(el).transform"
    ) == "none"

    context.close()


def test_desktop_only_motion_reverts_after_resizing_to_mobile(browser):
    context, page = catchy_page(browser)
    icon = page.locator("#floating-icon .kmq-glyph")
    page.wait_for_function(
        """() => getComputedStyle(document.querySelector('#floating-icon .kmq-glyph')).transform !== 'none'"""
    )

    page.set_viewport_size({"width": 390, "height": 844})
    page.wait_for_timeout(250)
    assert icon.evaluate("el => getComputedStyle(el).transform") == "none"

    context.close()


def test_section_bound_ambient_motion_pauses_offscreen(browser):
    context, page = catchy_page(browser)
    ring = page.locator("#seal-ring")
    page.wait_for_timeout(250)
    page.evaluate("scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(150)
    paused_angle = ring.evaluate(
        "el => new DOMMatrix(getComputedStyle(el).transform).m12"
    )
    page.wait_for_timeout(400)
    later_angle = ring.evaluate(
        "el => new DOMMatrix(getComputedStyle(el).transform).m12"
    )

    assert abs(later_angle - paused_angle) < 0.001
    context.close()


def test_runtime_reduced_motion_stops_ambient_tweens(browser):
    context, page = catchy_page(browser)
    page.wait_for_function(
        """() => getComputedStyle(document.querySelector('#floating-icon .kmq-glyph')).transform !== 'none'"""
    )
    assert page.locator("#catchy-cta .kmq-btn__sheen").count() == 1

    page.emulate_media(reduced_motion="reduce")
    page.wait_for_timeout(250)

    for selector in (
        "#floating-icon .kmq-glyph", "#seal-ring", ".kmq-seal__halo",
        ".kmq-fab__pulse", ".kmq-hero__layer--glow", "#hero-stage", "#moving-photo",
    ):
        assert page.locator(selector).evaluate(
            "el => getComputedStyle(el).transform"
        ) == "none"
    for selector in ("#ambient-card", "#catchy-cta"):
        assert page.locator(selector).evaluate(
            "el => getComputedStyle(el).translate"
        ) == "none"
    assert page.locator(".kmq-btn__sheen").count() == 0

    context.close()


def test_reduced_motion_leaves_content_visible_and_stationary(browser):
    context, page = motion_page(browser, reduced=True)
    reveal = page.locator("#reveal")

    assert float(reveal.evaluate("el => getComputedStyle(el).opacity")) == 1
    assert reveal.evaluate("el => getComputedStyle(el).transform") == "none"

    context.close()


def test_enabling_reduced_motion_reverts_staged_content(browser):
    context, page = motion_page(browser)
    reveal = page.locator("#reveal")
    assert float(reveal.evaluate("el => getComputedStyle(el).opacity")) < 0.1

    page.emulate_media(reduced_motion="reduce")
    page.wait_for_timeout(150)

    assert float(reveal.evaluate("el => getComputedStyle(el).opacity")) == 1
    assert reveal.evaluate("el => getComputedStyle(el).transform") == "none"

    context.close()


def test_pointer_capability_change_does_not_replay_scroll_reveals(browser):
    context, page = motion_page(browser)
    reveal = page.locator("#reveal")
    reveal.scroll_into_view_if_needed()
    page.wait_for_timeout(1000)
    assert float(reveal.evaluate("el => getComputedStyle(el).opacity")) > 0.95
    page.evaluate(
        """() => {
          window.revealStyleMutations = 0;
          new MutationObserver(records => {
            window.revealStyleMutations += records.length;
          }).observe(document.querySelector('#reveal'), {
            attributes: true,
            attributeFilter: ['style']
          });
        }"""
    )

    cdp = context.new_cdp_session(page)
    cdp.send("Emulation.setTouchEmulationEnabled", {
        "enabled": True,
        "maxTouchPoints": 1,
    })
    page.wait_for_timeout(250)

    assert not page.evaluate("matchMedia('(hover: hover) and (pointer: fine)').matches")
    assert page.evaluate("window.revealStyleMutations") == 0

    context.close()


def test_cards_stagger_into_view(browser):
    context, page = motion_page(browser)
    cards = page.locator(".kmq-card")

    assert float(cards.nth(0).evaluate("el => getComputedStyle(el).opacity")) < 0.1
    cards.nth(0).scroll_into_view_if_needed()
    page.wait_for_function(
        "() => parseFloat(getComputedStyle(document.querySelector('#card')).opacity) > 0.2"
    )
    first = float(cards.nth(0).evaluate("el => getComputedStyle(el).opacity"))
    second = float(cards.nth(1).evaluate("el => getComputedStyle(el).opacity"))
    assert first > second + 0.05

    page.wait_for_timeout(900)
    assert float(cards.nth(0).evaluate("el => getComputedStyle(el).opacity")) > 0.95
    assert float(cards.nth(1).evaluate("el => getComputedStyle(el).opacity")) > 0.95

    context.close()


def test_card_tracks_the_pointer_then_returns_to_rest(browser):
    context, page = motion_page(browser)
    card = page.locator("#card")
    card.scroll_into_view_if_needed()
    page.wait_for_timeout(1000)
    box = card.bounding_box()
    assert box

    page.mouse.move(box["x"] + box["width"] * 0.85,
                    box["y"] + box["height"] * 0.2)
    page.wait_for_timeout(400)
    moving = card.evaluate(
        """el => {
          const m = new DOMMatrix(getComputedStyle(el).transform);
          return { tilt: Math.abs(m.m13) + Math.abs(m.m23), lift: m.m42 };
        }"""
    )
    assert moving["tilt"] > 0.005
    assert moving["lift"] < -3

    page.mouse.move(2, 2)
    page.wait_for_timeout(500)
    resting = card.evaluate(
        """el => {
          const m = new DOMMatrix(getComputedStyle(el).transform);
          return { tilt: Math.abs(m.m13) + Math.abs(m.m23), lift: m.m42 };
        }"""
    )
    assert resting["tilt"] < 0.001
    assert resting["lift"] > -0.5

    context.close()


def test_pointer_tilt_waits_for_the_card_reveal(browser):
    context, page = motion_page(browser)
    card = page.locator("#card")
    card.scroll_into_view_if_needed()
    page.wait_for_function(
        "() => parseFloat(getComputedStyle(document.querySelector('#card')).opacity) > 0.2"
    )
    box = card.bounding_box()
    assert box

    page.mouse.move(box["x"] + box["width"] * 0.85,
                    box["y"] + box["height"] * 0.2)
    page.wait_for_timeout(250)
    tilt = card.evaluate(
        """el => {
          const m = new DOMMatrix(getComputedStyle(el).transform);
          return Math.abs(m.m13) + Math.abs(m.m23);
        }"""
    )
    assert tilt < 0.001

    context.close()


def test_hero_car_has_scroll_linked_parallax(browser):
    context, page = parallax_page(browser)
    car = page.locator("#car")

    page.evaluate("window.scrollTo(0, 700)")
    page.wait_for_timeout(600)
    moved = car.evaluate(
        """el => {
          const m = new DOMMatrix(getComputedStyle(el).transform);
          return { y: m.m42, scale: Math.hypot(m.m11, m.m12, m.m13) };
        }"""
    )
    assert moved["y"] < -5
    assert moved["scale"] > 1.005

    context.close()


def test_faq_expansion_remeasures_later_scroll_reveals(browser):
    context, page = expanding_faq_page(browser)
    late = page.locator("#late")
    old_start = late.evaluate(
        "el => el.getBoundingClientRect().top + scrollY - innerHeight * 0.88 + 5"
    )

    page.locator("#faq summary").click()
    page.wait_for_function(
        """oldStart => {
          const late = document.querySelector('#late');
          const trigger = ScrollTrigger.getAll().find(item => item.trigger === late);
          return trigger && trigger.start > oldStart + 500;
        }""",
        arg=old_start,
    )
    page.evaluate("y => window.scrollTo(0, y)", old_start)
    page.wait_for_timeout(900)

    assert late.evaluate("el => el.getBoundingClientRect().top") > 720
    assert float(late.evaluate("el => getComputedStyle(el).opacity")) < 0.1

    context.close()
