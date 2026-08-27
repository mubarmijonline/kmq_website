"""Route, content and validation checks.

Run with the project's venv:

    .venv/bin/python -m pytest tests/ -q

None of these need a database. The two views that use one degrade to a
notice, and that degradation is itself asserted below.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from app import content as C  # noqa: E402
from app.forms import validate_lead  # noqa: E402
from app.text import normalise_lookup, normalise_saudi_phone  # noqa: E402

LOCALES = ("ar", "en")


@pytest.fixture(scope="session")
def client():
    app = create_app({"ENV_NAME": "test", "WHATSAPP_NUMBER": ""})
    return app.test_client()


def all_paths() -> list[str]:
    paths = []
    for lang in LOCALES:
        paths += [
            f"/{lang}/", f"/{lang}/about-us", f"/{lang}/services",
            f"/{lang}/packages", f"/{lang}/warranty", f"/{lang}/branches",
            f"/{lang}/blog", f"/{lang}/contact-us",
        ]
        paths += [f"/{lang}/services/{s}" for s in C.SERVICE_SLUGS]
        paths += [f"/{lang}/blog/{p['slug']}" for p in C.content(lang)["posts"]]
    return paths


# --------------------------------------------------------------------------
# Content integrity
# --------------------------------------------------------------------------

def test_locales_have_identical_key_sets():
    assert set(C.AR) == set(C.EN)


def test_list_valued_keys_have_equal_length():
    for key, ar_value in C.AR.items():
        if isinstance(ar_value, list):
            assert len(ar_value) == len(C.EN[key]), f"{key} differs in length"


def test_records_have_matching_slugs():
    for key, id_key in (("services", "slug"), ("packages", "slug"),
                        ("posts", "slug"), ("branches", "id"),
                        ("categories", "slug")):
        ar = [row[id_key] for row in C.AR[key]]
        en = [row[id_key] for row in C.EN[key]]
        assert ar == en, f"{key} slugs differ between locales"


def test_no_branch_carries_an_unconfirmed_fact():
    """The content file leaves every branch phone, hour and address open."""
    for lang in LOCALES:
        for b in C.content(lang)["branches"]:
            assert not b["phone"], f"{b['id']} has an invented phone number"
            assert not b["hours"], f"{b['id']} has invented hours"
            assert not b["map_url"], f"{b['id']} has an invented map URL"


def test_the_branch_order_is_the_one_the_client_asked_for():
    """Al Rimal is the main branch and leads; Dammam runs Manar then Imam.

    Both halves came from the same client note, and both are easy to undo by
    editing one list and not the other — so the order is asserted here rather
    than trusted to review.
    """
    expected = ("al-rimal", "al-hamra", "tuwaiq", "jeddah-madinah-road",
                "dammam-al-manar", "dammam-imam")
    assert C.BRANCH_IDS == expected
    for lang in LOCALES:
        assert tuple(b["id"] for b in C.content(lang)["branches"]) == expected


def test_only_the_main_branch_is_marked_as_one(client):
    for lang in LOCALES:
        marked = [b["id"] for b in C.content(lang)["branches"] if b["main"]]
        assert marked == [C.MAIN_BRANCH]

        html = client.get(f"/{lang}/branches").get_data(as_text=True)
        assert html.count('class="kmq-branch__main"') == 1
        assert C.content(lang)["main_branch"] in html


def test_no_fabricated_phone_numbers_anywhere():
    """The design file shipped +966 55 000 000X placeholders. None survived."""
    blob = repr(C.AR) + repr(C.EN)
    assert not re.search(r"\+?966\s?5{1,2}\s?0{3,}", blob)


def test_no_specimen_warranty_record():
    """The design file shipped KMQ-2026-04812 as a canned lookup result."""
    blob = repr(C.AR) + repr(C.EN)
    assert "KMQ-2026-" not in blob


def test_no_fabricated_review_scores():
    """The design file shipped '4.9 / 5' Google ratings. Not imported."""
    blob = repr(C.AR) + repr(C.EN)
    assert not re.search(r"\d\.\d\s*/\s*5", blob)


def test_analytics_reports_only_from_the_published_site(client):
    """A dev process and this suite must not count as visitors."""
    html = client.get("/ar/").get_data(as_text=True)
    assert "googletagmanager" not in html


def _published(monkeypatch, ga_id: str):
    """The app as it runs published: prod, with a signing key in the env."""
    monkeypatch.setenv("SECRET_KEY", "test-key")
    return create_app({"ENV_NAME": "prod", "WHATSAPP_NUMBER": "",
                       "GA_MEASUREMENT_ID": ga_id}).test_client()


def test_analytics_tag_carries_the_configured_property(monkeypatch):
    html = _published(monkeypatch, "G-TEST123").get("/ar/").get_data(as_text=True)
    assert "https://www.googletagmanager.com/gtag/js?id=G-TEST123" in html
    assert "gtag('config', 'G-TEST123')" in html


def test_analytics_can_be_switched_off_in_production(monkeypatch):
    html = _published(monkeypatch, "").get("/ar/").get_data(as_text=True)
    assert "googletagmanager" not in html


def test_service_and_package_slugs_are_the_declared_ones():
    assert tuple(s["slug"] for s in C.AR["services"]) == C.SERVICE_SLUGS
    assert {p["slug"] for p in C.AR["packages"]} == set(C.PACKAGE_SLUGS)


def test_exactly_one_featured_package():
    for lang in LOCALES:
        featured = [p for p in C.content(lang)["packages"] if p["featured"]]
        assert len(featured) == 1


def test_every_post_category_exists():
    for lang in LOCALES:
        known = {c["slug"] for c in C.content(lang)["categories"]}
        for p in C.content(lang)["posts"]:
            assert p["category"] in known


# --------------------------------------------------------------------------
# Routing
# --------------------------------------------------------------------------

def test_root_redirects_to_arabic(client):
    r = client.get("/")
    assert r.status_code == 302
    assert r.headers["Location"].endswith("/ar/")


@pytest.mark.parametrize("path", all_paths())
def test_every_page_renders(client, path):
    r = client.get(path)
    assert r.status_code == 200, path


def test_unknown_locale_is_404(client):
    assert client.get("/fr/packages").status_code == 404


def test_unknown_service_is_404(client):
    assert client.get("/ar/services/nope").status_code == 404


def test_unknown_article_is_404(client):
    assert client.get("/en/blog/nope").status_code == 404


def test_direction_and_lang_attributes(client):
    ar = client.get("/ar/").get_data(as_text=True)
    en = client.get("/en/").get_data(as_text=True)
    assert 'lang="ar" dir="rtl"' in ar
    assert 'lang="en" dir="ltr"' in en


def test_language_switch_stays_on_the_same_page(client):
    html = client.get("/ar/blog/gloss-or-matte").get_data(as_text=True)
    assert "/en/blog/gloss-or-matte" in html


def test_page_count_is_the_documented_42(client):
    # 8 top-level + 5 service sub-pages + 8 articles, in each of 2 locales.
    assert len(all_paths()) == 42


# --------------------------------------------------------------------------
# What must not appear on a rendered page
# --------------------------------------------------------------------------

@pytest.mark.parametrize("path", all_paths())
def test_no_placeholder_whatsapp_link(client, path):
    """With no number configured, nothing may link to wa.me at all."""
    assert "wa.me" not in client.get(path).get_data(as_text=True), path


def test_whatsapp_links_appear_once_configured():
    app = create_app({"ENV_NAME": "test", "WHATSAPP_NUMBER": "+966511111111"})
    html = app.test_client().get("/ar/").get_data(as_text=True)
    assert "https://wa.me/966511111111" in html


def test_unconfirmed_facts_render_as_a_localised_notice(client):
    ar = client.get("/ar/branches").get_data(as_text=True)
    en = client.get("/en/branches").get_data(as_text=True)
    assert C.AR["tbd"] in ar
    assert C.EN["tbd"] in en


def test_faq_is_on_the_home_page(client):
    """Section 10 of the content file, which the design file omitted."""
    for lang in LOCALES:
        html = client.get(f"/{lang}/").get_data(as_text=True)
        for item in C.content(lang)["faq"]:
            assert item["q"] in html


# --------------------------------------------------------------------------
# Blog filtering — must work as plain query parameters
# --------------------------------------------------------------------------

def test_category_filter_narrows_the_list(client):
    html = client.get("/en/blog?cat=comparisons").get_data(as_text=True)
    assert "PPF vs nano ceramic" in html
    assert "How to care for your car" not in html


def test_search_filters_server_side(client):
    html = client.get("/en/blog?q=tint").get_data(as_text=True)
    assert "heat-insulating tint" in html.lower()


def test_search_with_no_match_shows_the_empty_state(client):
    html = client.get("/en/blog?q=zzzznothing").get_data(as_text=True)
    assert C.EN["no_results"] in html


def test_unknown_category_is_ignored_not_fatal(client):
    assert client.get("/en/blog?cat=nonsense").status_code == 200


def test_out_of_range_page_clamps(client):
    assert client.get("/en/blog?page=999").status_code == 200
    assert client.get("/en/blog?page=abc").status_code == 200


# --------------------------------------------------------------------------
# Warranty lookup, with no database configured
# --------------------------------------------------------------------------

def test_empty_warranty_query_is_reported(client):
    html = client.post("/ar/warranty", data={"q": ""}).get_data(as_text=True)
    assert C.AR["war_empty_query"] in html


def test_warranty_lookup_without_a_database_degrades(client):
    r = client.post("/en/warranty", data={"q": "ABC1234"})
    assert r.status_code == 200
    assert C.EN["war_none_body"] in r.get_data(as_text=True)


def test_warranty_record_carries_only_the_four_public_fields():
    """An unauthenticated lookup must not expose the rest of the row.

    The table also holds branch_id, technician and install_date. None of them
    may reach the view — asserted on the record and on the SELECT itself, so
    that widening either one fails here rather than in production.
    """
    import dataclasses
    import inspect

    from app.db import Database, Warranty

    assert {f.name for f in dataclasses.fields(Warranty)} == {
        "warranty_number", "service_type", "activation_date",
        "expiry_date", "status",
    }

    select = re.search(r"SELECT(.+?)FROM warranty",
                       inspect.getsource(Database.find_warranty), re.S).group(1)
    for column in ("branch_id", "technician", "install_date"):
        assert column not in select, f"{column} must not be selected"


# --------------------------------------------------------------------------
# Normalisation
# --------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("0512345678", "+966512345678"),
    ("512345678", "+966512345678"),
    ("+966512345678", "+966512345678"),
    ("00966512345678", "+966512345678"),
    ("05 1234 5678", "+966512345678"),
    ("05-1234-5678", "+966512345678"),
    ("٠٥١٢٣٤٥٦٧٨", "+966512345678"),
])
def test_saudi_phone_normalisation(raw, expected):
    assert normalise_saudi_phone(raw) == expected


@pytest.mark.parametrize("raw", [
    "0412345678",      # not a mobile prefix
    "+447700900000",   # not Saudi
    "051234567",       # too short
    "05123456789",     # too long
    "abc",
    "",
])
def test_rejected_phone_numbers(raw):
    assert normalise_saudi_phone(raw) is None


@pytest.mark.parametrize("raw,expected", [
    ("abj 1234", "ABJ1234"),
    ("ABJ-1234", "ABJ1234"),
    ("  ABJ1234  ", "ABJ1234"),
    ("ABJ١٢٣٤", "ABJ1234"),
    ("أ ب ح 1234", "ABJ1234"),      # Arabic plate letters -> Latin twins
    ("INV/9001", "INV9001"),
])
def test_lookup_normalisation(raw, expected):
    assert normalise_lookup(raw) == expected


# --------------------------------------------------------------------------
# Lead form validation
# --------------------------------------------------------------------------

def _good_lead() -> dict[str, str]:
    return {
        "full_name": "عمر",
        "phone": "0512345678",
        "service": "ppf-gloss",
        "car_model": "Porsche 911",
        "branch": "al-hamra",
        "timing": "this-week",
        "notes": "",
    }


def test_valid_lead_passes_and_normalises_the_phone():
    form = validate_lead(_good_lead(), "ar")
    assert form.ok
    assert form.values["phone_e164"] == "+966512345678"


def test_missing_required_field_fails():
    raw = _good_lead()
    raw["full_name"] = ""
    form = validate_lead(raw, "ar")
    assert not form.ok
    assert form.errors["full_name"] == "required"


def test_notes_are_optional():
    raw = _good_lead()
    raw.pop("notes")
    assert validate_lead(raw, "en").ok


def test_bad_phone_fails_with_a_localised_message():
    raw = _good_lead()
    raw["phone"] = "+447700900000"
    form = validate_lead(raw, "en")
    assert not form.ok
    assert form.error_for("phone") == C.LEAD_ERRORS["en"]["phone"]


def test_option_outside_the_list_fails():
    raw = _good_lead()
    raw["branch"] = "makkah"
    form = validate_lead(raw, "en")
    assert form.errors["branch"] == "choice"


def test_overlong_value_fails():
    raw = _good_lead()
    raw["car_model"] = "x" * 200
    assert validate_lead(raw, "en").errors["car_model"] == "too_long"


def test_failed_submission_returns_the_visitors_answers(client):
    raw = _good_lead()
    raw["phone"] = "not-a-phone"
    html = client.post("/en/contact-us", data=raw).get_data(as_text=True)
    assert "Porsche 911" in html
    assert "not-a-phone" in html


def test_honeypot_submission_looks_successful(client):
    raw = _good_lead()
    raw["company"] = "spam co"
    html = client.post("/ar/contact-us", data=raw).get_data(as_text=True)
    assert C.AR["contact_ok_title"] in html


def test_lead_without_a_database_tells_the_visitor_where_to_go(client):
    html = client.post("/en/contact-us", data=_good_lead()).get_data(as_text=True)
    assert C.LEAD_ERRORS["en"]["unavailable"] in html


# --------------------------------------------------------------------------
# Assets
# --------------------------------------------------------------------------

def test_bundle_is_fingerprinted_and_served(client):
    html = client.get("/ar/").get_data(as_text=True)
    match = re.search(r'href="(/static/build/kmq\.[0-9a-f]{10}\.css)"', html)
    assert match, "no fingerprinted stylesheet in the page"
    assert client.get(match.group(1)).status_code == 200


def test_every_brand_image_resolves(client):
    """A 404 on an <img> is silent — the header just goes blank."""
    html = client.get("/ar/").get_data(as_text=True)
    srcs = set(re.findall(r'"(/static/img/brand/[^"]+)"', html))
    assert srcs, "no brand image in the page"
    for src in srcs:
        assert client.get(src).status_code == 200, src


def test_each_logo_cut_sits_on_the_ground_it_was_drawn_for(client):
    """The two cuts are not interchangeable and the file names invite the
    mistake: `kmq-logo.svg` is drawn FOR a dark ground and `kmq-logo-light.svg`
    FOR a light one. On the wrong ground the letters that overhang the shield
    lose their keyline and disappear.

    The page is paper, but the header mark sits on a --deep plate — the white
    "SHIELD" overhangs the shield on every cut the client supplied and would
    vanish on a bare paper header — so the header wears the dark-ground cut on
    that plate. The footer is deep, so it wears the dark cut too. The favicon
    is the light cut, because a browser tab is white in half the browsers."""
    html = client.get("/ar/").get_data(as_text=True)

    brand = re.search(r'<a class="kmq-brand.*?</a>', html, re.DOTALL)
    assert brand, "no brand link in the header"
    assert "img/brand/kmq-logo.svg" in brand.group(0)
    assert "kmq-logo-light.svg" not in brand.group(0)

    footer = re.search(r'<footer class="kmq-footer.*?</footer>', html, re.DOTALL)
    assert footer, "no footer"
    assert "img/brand/kmq-logo.svg" in footer.group(0)
    assert "kmq-logo-light.svg" not in footer.group(0)

    assert 'rel="icon"' in html and "kmq-logo-light.svg" in html


def test_every_social_glyph_is_one_the_kit_supplies(client):
    """`icon` names a branch of brand_icon(); a typo renders an empty tile."""
    macro = (Path(__file__).resolve().parent.parent
             / "templates" / "partials" / "icons.html").read_text()
    known = set(re.findall(r'name == "([a-z]+)"', macro))
    for lang in LOCALES:
        for s in C.content(lang)["social"]:
            assert s["icon"] in known, s["icon"]


def test_no_style_attribute_uses_a_physical_side():
    """RTL depends on logical properties; a stray left/right breaks Arabic."""
    css = (Path(__file__).resolve().parent.parent / "design" / "components.css").read_text()
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    for prop in ("padding-left:", "padding-right:", "margin-left:",
                 "margin-right:", "border-left:", "border-right:"):
        assert prop not in css.replace(" ", ""), f"{prop} should be a logical property"
