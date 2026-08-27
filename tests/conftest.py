"""Shared fixtures for the tests that need a database and an admin session.

The database tests write. Point ``KMQ_TEST_DATABASE_URL`` at a development
copy — never at production — and they are skipped without it:

    KMQ_TEST_DATABASE_URL=postgresql:///kmq_dev .venv/bin/python -m pytest tests/ -q
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import auth, create_app  # noqa: E402
from app import content as C  # noqa: E402

TEST_DSN = os.environ.get("KMQ_TEST_DATABASE_URL")
needs_db = pytest.mark.skipif(not TEST_DSN, reason="KMQ_TEST_DATABASE_URL is unset")

#: Every account these tests make. The cleanup deletes by this suffix, so it
#: can never touch a real one.
TEST_SUFFIX = "@kmq.test"
PASSWORD = "a-long-test-password"


@pytest.fixture()
def admin_app():
    app = create_app({"ENV_NAME": "test", "SECRET_KEY": "test-key",
                      "WHATSAPP_NUMBER": "", "DATABASE_URL": TEST_DSN})
    _clear(app)
    yield app
    _clear(app)
    _restore(app)
    C.use_overlay(None)


@pytest.fixture()
def owner(admin_app):
    """A signed-in owner's client."""
    make_account(admin_app, email=f"owner{TEST_SUFFIX}", role="owner")
    client = admin_app.test_client()
    sign_in(client, f"owner{TEST_SUFFIX}")
    return client


def make_account(app, *, email: str, role: str, must_change: bool = False) -> int:
    database = app.extensions["kmq_db"]
    uid = auth.create_user(database, email=email, display_name=email.split("@")[0],
                           password=PASSWORD, role=role)
    if not must_change:
        auth.set_password(database, email=email, password=PASSWORD,
                          must_change=False, revoke_sessions=False)
    return uid


def csrf(client, path: str) -> str:
    html = client.get(path).data.decode()
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, f"no CSRF token on {path}"
    return match.group(1)


def sign_in(client, email: str) -> None:
    response = client.post("/admin/login", data={
        "csrf_token": csrf(client, "/admin/login"),
        "email": email, "password": PASSWORD,
    })
    assert response.status_code == 302, response.data[:400]


def _clear(app) -> None:
    database = app.extensions["kmq_db"]
    with database.cursor() as conn:
        conn.execute("DELETE FROM audit_log WHERE actor_email LIKE %s",
                     (f"%{TEST_SUFFIX}",))
        conn.execute("DELETE FROM admin_login_attempt")
        conn.execute("DELETE FROM admin_user WHERE email LIKE %s",
                     (f"%{TEST_SUFFIX}",))
        conn.commit()


def _restore(app) -> None:
    """Put the content store back the way the repository ships it.

    These tests edit real rows in the development database. Re-seeding with
    force is the same operation an operator would run to undo an experiment,
    and it leaves the branch table's editable columns as they were seeded.
    """
    from app import store

    database = app.extensions["kmq_db"]
    try:
        with store.writing(database) as conn:
            conn.execute("DELETE FROM copy_string")
            # Seeding rewrites data and order but deliberately leaves publish
            # state alone, so a test that unpublished something has to put it
            # back itself.
            conn.execute("UPDATE content_entry SET is_published = true")
            conn.execute("UPDATE branch SET phone_e164 = NULL, "
                         "whatsapp_e164 = NULL, map_url = NULL, "
                         "is_published = true")
        store.seed(database, force=True)
        with database.cursor() as conn:
            store.bump_version(conn)
            conn.commit()
    except Exception:  # pragma: no cover - the pool is gone in one test
        pass
