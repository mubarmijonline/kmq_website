"""Admin auth: the guard, the CSRF check, the roles and the throttle.

Two halves. The first needs no database and asserts what the admin does
without one — a 503 rather than a traceback, and a refusal to boot in
production without a signing key. The second needs Postgres and is skipped
without it:

    KMQ_TEST_DATABASE_URL=postgresql:///kmq_dev .venv/bin/python -m pytest tests/ -q

That database is written to. Point it at a development copy, never at prod.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402

TEST_DSN = os.environ.get("KMQ_TEST_DATABASE_URL")
needs_db = pytest.mark.skipif(not TEST_DSN, reason="KMQ_TEST_DATABASE_URL is unset")

TEST_EMAIL_SUFFIX = "@kmq.test"


# --------------------------------------------------------------------------
# Without a database
# --------------------------------------------------------------------------

def test_admin_says_503_without_a_database():
    app = create_app({"ENV_NAME": "test", "DATABASE_URL": None})
    client = app.test_client()
    for path in ("/admin/", "/admin/login", "/admin/audit"):
        assert client.get(path).status_code == 503


def test_public_site_is_unaffected_by_the_admin():
    app = create_app({"ENV_NAME": "test", "DATABASE_URL": None})
    assert app.test_client().get("/ar/").status_code == 200


def test_production_refuses_to_boot_without_a_secret_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app({"ENV_NAME": "prod"})


# --------------------------------------------------------------------------
# With one
# --------------------------------------------------------------------------

@pytest.fixture()
def app():
    app = create_app({"ENV_NAME": "test", "SECRET_KEY": "test-key",
                      "DATABASE_URL": TEST_DSN})
    _clear(app)
    yield app
    _clear(app)


def _clear(app) -> None:
    """Remove only what these tests create. Content rows are left alone."""
    database = app.extensions["kmq_db"]
    with database.cursor() as conn:
        conn.execute("DELETE FROM audit_log WHERE actor_email LIKE %s",
                     (f"%{TEST_EMAIL_SUFFIX}",))
        conn.execute("DELETE FROM admin_login_attempt")
        conn.execute("DELETE FROM admin_user WHERE email LIKE %s",
                     (f"%{TEST_EMAIL_SUFFIX}",))
        conn.commit()


def _account(app, *, email: str, role: str, password: str = "a-long-password",
             must_change: bool = False) -> dict:
    from app import auth

    database = app.extensions["kmq_db"]
    uid = auth.create_user(database, email=email, display_name=email.split("@")[0],
                           password=password, role=role)
    if not must_change:
        auth.set_password(database, email=email, password=password,
                          must_change=False, revoke_sessions=False)
    return {"id": uid, "email": email, "password": password}


def _token(client, path: str) -> str:
    html = client.get(path).data.decode()
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, f"no CSRF token on {path}"
    return match.group(1)


def _sign_in(client, account) -> None:
    response = client.post("/admin/login", data={
        "csrf_token": _token(client, "/admin/login"),
        "email": account["email"], "password": account["password"],
    })
    assert response.status_code == 302, response.data[:400]


@needs_db
def test_every_admin_url_redirects_to_login_when_signed_out(app):
    client = app.test_client()
    for path in ("/admin/", "/admin/audit", "/admin/password"):
        response = client.get(path)
        assert response.status_code == 302
        assert response.headers["Location"].startswith("/admin/login")


@needs_db
def test_a_post_without_a_csrf_token_is_rejected(app):
    client = app.test_client()
    account = _account(app, email=f"owner{TEST_EMAIL_SUFFIX}", role="owner")
    assert client.post("/admin/login", data={
        "email": account["email"], "password": account["password"],
    }).status_code == 400


@needs_db
def test_a_post_with_the_wrong_csrf_token_is_rejected(app):
    client = app.test_client()
    account = _account(app, email=f"owner{TEST_EMAIL_SUFFIX}", role="owner")
    client.get("/admin/login")  # mint a token for this session
    assert client.post("/admin/login", data={
        "csrf_token": "not-the-token",
        "email": account["email"], "password": account["password"],
    }).status_code == 400


@needs_db
def test_a_seeded_account_is_held_at_the_password_form(app):
    client = app.test_client()
    account = _account(app, email=f"owner{TEST_EMAIL_SUFFIX}", role="owner",
                       must_change=True)
    _sign_in(client, account)

    assert client.get("/admin/").headers["Location"] == "/admin/password"
    assert client.get("/admin/audit").headers["Location"] == "/admin/password"

    response = client.post("/admin/password", data={
        "csrf_token": _token(client, "/admin/password"),
        "current_password": account["password"],
        "new_password": "a-much-longer-password",
        "confirm_password": "a-much-longer-password",
    })
    assert response.headers["Location"] == "/admin/"
    assert client.get("/admin/").status_code == 200


@needs_db
def test_an_editor_is_refused_the_owner_only_sections(app):
    client = app.test_client()
    _sign_in(client, _account(app, email=f"editor{TEST_EMAIL_SUFFIX}", role="editor"))
    assert client.get("/admin/").status_code == 200
    assert client.get("/admin/audit").status_code == 403


@needs_db
def test_an_owner_is_not(app):
    client = app.test_client()
    _sign_in(client, _account(app, email=f"owner{TEST_EMAIL_SUFFIX}", role="owner"))
    assert client.get("/admin/audit").status_code == 200


@needs_db
def test_six_failed_attempts_throttle_the_address(app):
    from app import auth

    client = app.test_client()
    account = _account(app, email=f"owner{TEST_EMAIL_SUFFIX}", role="owner")

    for _ in range(auth.MAX_ATTEMPTS):
        client.post("/admin/login", data={
            "csrf_token": _token(client, "/admin/login"),
            "email": account["email"], "password": "wrong",
        })

    response = client.post("/admin/login", data={
        "csrf_token": _token(client, "/admin/login"),
        "email": account["email"], "password": account["password"],
    })
    assert response.status_code == 200
    assert "Too many failed attempts" in response.data.decode()


@needs_db
def test_a_disabled_account_cannot_sign_in(app):
    client = app.test_client()
    account = _account(app, email=f"editor{TEST_EMAIL_SUFFIX}", role="editor")
    with app.extensions["kmq_db"].cursor() as conn:
        conn.execute("UPDATE admin_user SET is_disabled = true WHERE id = %s",
                     (account["id"],))
        conn.commit()

    response = client.post("/admin/login", data={
        "csrf_token": _token(client, "/admin/login"),
        "email": account["email"], "password": account["password"],
    })
    assert response.status_code == 200
    assert "do not match an account" in response.data.decode()


@needs_db
def test_a_password_reset_signs_the_account_out_everywhere(app):
    from app import auth

    client = app.test_client()
    account = _account(app, email=f"owner{TEST_EMAIL_SUFFIX}", role="owner")
    _sign_in(client, account)
    assert client.get("/admin/").status_code == 200

    auth.set_password(app.extensions["kmq_db"], email=account["email"],
                      password="another-long-password", must_change=True,
                      revoke_sessions=True)

    assert client.get("/admin/").status_code == 302


@needs_db
def test_signing_in_and_out_is_recorded(app):
    from app import audit

    client = app.test_client()
    account = _account(app, email=f"owner{TEST_EMAIL_SUFFIX}", role="owner")
    _sign_in(client, account)
    client.post("/admin/logout", data={"csrf_token": _token(client, "/admin/")})

    rows = audit.recent(app.extensions["kmq_db"], limit=10)
    actions = [row["action"] for row in rows if row["actor_email"] == account["email"]]
    assert "login" in actions and "logout" in actions
