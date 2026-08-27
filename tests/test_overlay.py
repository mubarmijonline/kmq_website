"""The content overlay: stored edits over shipped copy, and the fallback.

Skipped without ``KMQ_TEST_DATABASE_URL``. See tests/test_admin.py for what
that database is expected to be.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import content as C  # noqa: E402
from app import create_app, store  # noqa: E402

TEST_DSN = os.environ.get("KMQ_TEST_DATABASE_URL")
needs_db = pytest.mark.skipif(not TEST_DSN, reason="KMQ_TEST_DATABASE_URL is unset")

#: A key that appears on the English home page, edited and reverted by the
#: tests below. Chosen because it is rendered verbatim, with no truncation.
PROBE_KEY = "hero_sub"
PROBE_VALUE = "OVERLAY-PROOF-9f3a"


def paths() -> list[str]:
    out = []
    for lang in ("ar", "en"):
        out += [f"/{lang}/", f"/{lang}/about-us", f"/{lang}/services",
                f"/{lang}/packages", f"/{lang}/warranty", f"/{lang}/branches",
                f"/{lang}/blog", f"/{lang}/contact-us"]
        out += [f"/{lang}/services/{s}" for s in C.SERVICE_SLUGS]
        out += [f"/{lang}/blog/{p['slug']}" for p in C.shipped(lang)["posts"]]
    return out


@pytest.fixture()
def app():
    app = create_app({"ENV_NAME": "test", "WHATSAPP_NUMBER": "",
                      "DATABASE_URL": TEST_DSN})
    yield app
    _revert(app)
    # The overlay is a module-level install; leaving one app's pool wired into
    # content.py would leak into the next test.
    C.use_overlay(None)


def _revert(app) -> None:
    database = app.extensions["kmq_db"]
    try:
        with store.writing(database) as conn:
            store.revert_copy(conn, locale="en", key=PROBE_KEY)
    except Exception:
        pass


def test_shipped_copy_is_reachable_without_an_overlay():
    """content.shipped never consults the database, whatever is installed."""
    assert C.shipped("en")["hero_sub"] == C.EN["hero_sub"]


@needs_db
def test_a_seeded_database_changes_nothing_a_visitor_sees(app):
    """Seed first, then compare. Both bodies must be byte-identical."""
    plain = create_app({"ENV_NAME": "test", "WHATSAPP_NUMBER": "",
                        "DATABASE_URL": None}).test_client()
    C.use_overlay(app.extensions["kmq_overlay"])
    stored = app.test_client()

    for path in paths():
        without = plain.get(path)
        with_db = stored.get(path)
        assert without.status_code == 200, path
        assert with_db.status_code == 200, path
        assert without.data == with_db.data, path


@needs_db
def test_an_edited_string_reaches_the_page(app):
    client = app.test_client()
    C.use_overlay(app.extensions["kmq_overlay"])
    assert PROBE_VALUE not in client.get("/en/").data.decode()

    database = app.extensions["kmq_db"]
    with store.writing(database) as conn:
        store.set_copy(conn, locale="en", key=PROBE_KEY, value=PROBE_VALUE,
                       actor_id=None)

    # A worker checks the version counter at most once per TTL; a just-saved
    # edit is visible no later than that.
    time.sleep(store.CACHE_TTL_SECONDS + 0.5)
    assert PROBE_VALUE in client.get("/en/").data.decode()


@needs_db
def test_reverting_a_string_restores_the_shipped_copy(app):
    client = app.test_client()
    C.use_overlay(app.extensions["kmq_overlay"])
    shipped = client.get("/en/").data

    database = app.extensions["kmq_db"]
    with store.writing(database) as conn:
        store.set_copy(conn, locale="en", key=PROBE_KEY, value=PROBE_VALUE,
                       actor_id=None)
    time.sleep(store.CACHE_TTL_SECONDS + 0.5)
    assert client.get("/en/").data != shipped

    with store.writing(database) as conn:
        store.revert_copy(conn, locale="en", key=PROBE_KEY)
    time.sleep(store.CACHE_TTL_SECONDS + 0.5)
    assert client.get("/en/").data == shipped


@needs_db
def test_the_site_survives_the_database_going_away(app):
    """Every page keeps returning 200 when the pool stops answering."""
    C.use_overlay(app.extensions["kmq_overlay"])
    client = app.test_client()
    assert client.get("/en/").status_code == 200

    app.extensions["kmq_db"].close()
    app.extensions["kmq_overlay"].invalidate()

    for path in paths():
        assert client.get(path).status_code == 200, path


@needs_db
def test_seeding_twice_changes_nothing(app):
    database = app.extensions["kmq_db"]
    first = store.seed(database)
    second = store.seed(database)
    assert second == {"copy": 0, "entries": 0, "settings": 0, "branches": 0}, \
        (first, second)
