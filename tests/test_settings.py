"""Tracking ids: stored in the admin, rendered on the published site only.

The rule these hold in place is the one that is easy to break by accident and
expensive to notice: a tag must never fire anywhere but production. A pixel
that counts the test suite reports conversions that did not happen, to an ad
account that pays for them.
"""

from __future__ import annotations

import pytest
from conftest import PASSWORD, csrf, make_account, needs_db, sign_in  # noqa: F401

from app import create_app, store

PIXEL = "123456789012345"
GA = "G-TESTONLY1"


@pytest.fixture()
def clean_settings(admin_app):
    """The settings table emptied before and after: these tests write it."""
    _clear(admin_app)
    yield admin_app
    _clear(admin_app)


def _clear(app) -> None:
    with app.extensions["kmq_db"].cursor() as conn:
        conn.execute("DELETE FROM site_setting WHERE key IN "
                     "('ga_id', 'meta_pixel_id')")
        conn.commit()


def published(app, monkeypatch):
    """A client for the same database, as the site runs when published."""
    monkeypatch.setenv("SECRET_KEY", "settings-test")
    live = create_app({"ENV_NAME": "prod", "WHATSAPP_NUMBER": "",
                       "DATABASE_URL": app.config["DATABASE_URL"]})
    return live.test_client()


def save(owner, **values):
    form = {"csrf_token": csrf(owner, "/admin/settings")}
    form.update(values)
    response = owner.post("/admin/settings", data=form)
    assert response.status_code == 302, response.data[:400]


@needs_db
def test_an_owner_can_store_a_pixel_id(clean_settings, owner):
    save(owner, ga_id=GA, meta_pixel_id=PIXEL)

    stored = store.settings(clean_settings.extensions["kmq_db"])
    assert stored["meta_pixel_id"] == PIXEL
    assert stored["ga_id"] == GA
    assert PIXEL in owner.get("/admin/settings").data.decode()


@needs_db
def test_a_stored_pixel_reaches_the_published_page(clean_settings, owner, monkeypatch):
    save(owner, meta_pixel_id=PIXEL)

    html = published(clean_settings, monkeypatch).get("/ar/").data.decode()
    assert f"fbq('init', '{PIXEL}')" in html
    # The no-script fallback carries the same id, or it counts nobody.
    assert f"facebook.com/tr?id={PIXEL}" in html


@needs_db
def test_a_stored_measurement_id_reaches_the_published_page(
        clean_settings, owner, monkeypatch):
    save(owner, ga_id=GA)

    html = published(clean_settings, monkeypatch).get("/en/").data.decode()
    assert f"gtag/js?id={GA}" in html
    assert f"gtag('config', '{GA}')" in html


@needs_db
def test_no_tag_fires_off_the_published_site(clean_settings, owner):
    save(owner, ga_id=GA, meta_pixel_id=PIXEL)

    # admin_app runs with ENV_NAME "test", which is every environment that is
    # not the live site: a developer's machine, CI, this suite.
    html = clean_settings.test_client().get("/ar/").data.decode()
    assert "googletagmanager" not in html
    assert "fbevents" not in html
    assert PIXEL not in html


@needs_db
def test_clearing_a_field_takes_the_tag_off_the_site(
        clean_settings, owner, monkeypatch):
    save(owner, meta_pixel_id=PIXEL)
    save(owner, meta_pixel_id="")

    assert "meta_pixel_id" not in store.settings(clean_settings.extensions["kmq_db"])
    assert "fbevents" not in published(clean_settings, monkeypatch).get("/ar/").data.decode()


@needs_db
def test_an_unset_measurement_id_means_no_analytics_at_all(
        clean_settings, owner, monkeypatch):
    """Clearing the field has to stop the tag, not fall back to a default."""
    save(owner, ga_id=GA)
    save(owner, ga_id="")

    assert "googletagmanager" not in published(
        clean_settings, monkeypatch).get("/ar/").data.decode()


@needs_db
def test_the_environment_pins_a_setting_against_the_admin(
        clean_settings, owner, monkeypatch):
    """A deploy must be able to take a tag off a site nobody wants measured."""
    save(owner, meta_pixel_id=PIXEL)
    monkeypatch.setenv("KMQ_META_PIXEL", "999999999999999")

    page = owner.get("/admin/settings").data.decode()
    assert "pinned by the deploy" in page
    assert "disabled" in page

    html = published(clean_settings, monkeypatch).get("/ar/").data.decode()
    assert "999999999999999" in html
    assert PIXEL not in html


@needs_db
def test_a_pinned_setting_ignores_a_posted_value(clean_settings, owner, monkeypatch):
    monkeypatch.setenv("KMQ_META_PIXEL", "999999999999999")
    save(owner, meta_pixel_id="111111111111111")

    assert "meta_pixel_id" not in store.settings(clean_settings.extensions["kmq_db"])


@needs_db
def test_settings_are_owner_only(admin_app):
    """An editor may write copy; wiring the site to an ad account is not copy."""
    make_account(admin_app, email="editor-settings@kmq.test", role="editor")
    client = admin_app.test_client()
    sign_in(client, "editor-settings@kmq.test")

    assert client.get("/admin/settings").status_code == 403


@needs_db
def test_a_saved_setting_is_audited(clean_settings, owner):
    from app import audit

    save(owner, meta_pixel_id=PIXEL)
    rows = audit.recent(clean_settings.extensions["kmq_db"], entity="setting")
    assert rows and rows[0]["entity_id"] == "meta_pixel_id"
