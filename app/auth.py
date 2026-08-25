"""Accounts, sessions and the two guards every admin view sits behind.

Three decisions worth stating, because each of them shows up in the code
below and none of them is the obvious default:

* **Roles are rows.** ``admin_role`` is a table with a rank, so adding a third
  role is an INSERT rather than a migration plus a scattering of new
  conditionals. Nothing here asks "is this user an admin"; it asks whether
  their role outranks what the view requires.
* **Sessions are a signed cookie plus an epoch.** There is no server-side
  session table. ``admin_user.session_epoch`` is carried in the cookie and
  compared on every request, which is what makes "sign this account out
  everywhere" — a password reset, a disabled account — a single UPDATE.
* **Nothing here trusts the database to be up.** Every read goes through the
  same pool the public site degrades around. A Postgres outage means nobody
  can sign in; it must not mean the site stops serving pages.
"""

from __future__ import annotations

import logging
import secrets
from typing import Any

from flask import abort, current_app, g, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

log = logging.getLogger(__name__)

#: Failed sign-ins from one address before it is refused, and the window they
#: are counted over. Deliberately generous — an editor who has forgotten which
#: of two passwords is current should not lock themselves out — and paired with
#: a 20-character generated password, which is what actually makes guessing
#: hopeless.
MAX_ATTEMPTS = 6
ATTEMPT_WINDOW_SECONDS = 900

#: Session keys. Namespaced because the public site keeps a language
#: preference in the same cookie.
_UID = "admin_uid"
_EPOCH = "admin_epoch"
_CSRF = "admin_csrf"


class Denied(Exception):
    """A sign-in that failed, with the reason to show the person trying."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


# --------------------------------------------------------------------------
# Accounts
# --------------------------------------------------------------------------

def create_user(database, *, email: str, display_name: str, password: str,
                role: str) -> int:
    """Create an account that must change its password at first sign-in.

    Raises :class:`ValueError` for a duplicate address or an unknown role —
    both are user error at the CLI, not exceptional conditions.
    """
    email = email.strip().lower()
    with database.cursor() as conn:
        known = conn.execute(
            "SELECT code FROM admin_role WHERE code = %s", (role,)
        ).fetchone()
        if known is None:
            raise ValueError(f"No such role: {role}")

        taken = conn.execute(
            "SELECT id FROM admin_user WHERE email = %s", (email,)
        ).fetchone()
        if taken is not None:
            raise ValueError(f"{email} already has an account.")

        row = conn.execute(
            """
            INSERT INTO admin_user (email, display_name, password_hash, role,
                                    must_change_password)
            VALUES (%(email)s, %(name)s, %(hash)s, %(role)s, true)
            RETURNING id
            """,
            {
                "email": email,
                "name": display_name.strip(),
                "hash": generate_password_hash(password),
                "role": role,
            },
        ).fetchone()
        conn.commit()
    return int(row["id"])


def set_password(database, *, email: str, password: str, must_change: bool,
                 revoke_sessions: bool) -> bool:
    """Replace an account's password. ``False`` if there is no such account.

    ``revoke_sessions`` bumps the epoch, which invalidates every cookie the
    account holds. A reset that left the old sessions signed in would not be a
    reset.
    """
    with database.cursor() as conn:
        row = conn.execute(
            """
            UPDATE admin_user
               SET password_hash = %(hash)s,
                   must_change_password = %(must_change)s,
                   session_epoch = session_epoch + %(bump)s
             WHERE email = %(email)s
            RETURNING id
            """,
            {
                "hash": generate_password_hash(password),
                "must_change": must_change,
                "bump": 1 if revoke_sessions else 0,
                "email": email.strip().lower(),
            },
        ).fetchone()
        conn.commit()
    return row is not None


def change_own_password(database, *, user_id: int, current: str,
                        replacement: str) -> None:
    """Change a signed-in user's own password, verifying the current one.

    Raises :class:`Denied` rather than returning a flag: every caller has to
    show the reason, and a boolean would lose which of the two checks failed.
    """
    with database.cursor() as conn:
        row = conn.execute(
            "SELECT password_hash FROM admin_user WHERE id = %s", (user_id,)
        ).fetchone()
        if row is None:
            raise Denied("no_account")
        if not check_password_hash(row["password_hash"], current):
            raise Denied("wrong_password")

        conn.execute(
            """
            UPDATE admin_user
               SET password_hash = %s, must_change_password = false
             WHERE id = %s
            """,
            (generate_password_hash(replacement), user_id),
        )
        conn.commit()


def find_user(database, user_id: int) -> dict[str, Any] | None:
    with database.cursor() as conn:
        return conn.execute(
            """
            SELECT u.id, u.email, u.display_name, u.role, u.is_disabled,
                   u.must_change_password, u.session_epoch, u.last_login_at,
                   r.label AS role_label, r.rank AS role_rank
              FROM admin_user u
              JOIN admin_role r ON r.code = u.role
             WHERE u.id = %s
            """,
            (user_id,),
        ).fetchone()


def list_users(database) -> list[dict[str, Any]]:
    with database.cursor() as conn:
        return conn.execute(
            """
            SELECT u.id, u.email, u.display_name, u.role, u.is_disabled,
                   u.must_change_password, u.created_at, u.last_login_at,
                   r.label AS role_label, r.rank AS role_rank
              FROM admin_user u
              JOIN admin_role r ON r.code = u.role
             ORDER BY r.rank DESC, u.display_name
            """
        ).fetchall()


def roles(database) -> list[dict[str, Any]]:
    with database.cursor() as conn:
        return conn.execute(
            "SELECT code, label, rank FROM admin_role ORDER BY rank DESC"
        ).fetchall()


# --------------------------------------------------------------------------
# Signing in
# --------------------------------------------------------------------------

def authenticate(database, *, email: str, password: str,
                 ip_hash: str) -> dict[str, Any]:
    """Verify a sign-in, or raise :class:`Denied` saying why.

    A wrong address and a wrong password give the same answer, and both cost
    the same hash comparison — checking the password against a dummy hash when
    the account does not exist keeps the response time from saying which of the
    two it was.
    """
    email = email.strip().lower()
    if throttled(database, ip_hash):
        raise Denied("throttled")

    with database.cursor() as conn:
        row = conn.execute(
            """
            SELECT id, email, display_name, password_hash, role, is_disabled,
                   must_change_password, session_epoch
              FROM admin_user WHERE email = %s
            """,
            (email,),
        ).fetchone()

        ok = check_password_hash(
            row["password_hash"] if row else _DUMMY_HASH, password
        )
        if row is None or not ok:
            _record_attempt(conn, ip_hash, email)
            conn.commit()
            raise Denied("bad_credentials")

        if row["is_disabled"]:
            # Counted as a failed attempt too: a disabled account being tried
            # repeatedly is exactly the pattern the throttle exists for.
            _record_attempt(conn, ip_hash, email)
            conn.commit()
            raise Denied("disabled")

        conn.execute(
            "UPDATE admin_user SET last_login_at = now() WHERE id = %s",
            (row["id"],),
        )
        conn.execute("DELETE FROM admin_login_attempt WHERE ip_hash = %s", (ip_hash,))
        conn.commit()

    return dict(row)


#: A real hash of a value nobody knows, compared against when the address does
#: not exist so that the failure costs the same as a wrong password.
_DUMMY_HASH = generate_password_hash(secrets.token_urlsafe(32))


def throttled(database, ip_hash: str) -> bool:
    """Whether this address has burned through its attempts.

    Fails open, like the lead form's throttle: a counter that cannot be read
    must not become a wall that locks the whole team out.
    """
    try:
        with database.cursor() as conn:
            row = conn.execute(
                """
                SELECT count(*) AS n
                  FROM admin_login_attempt
                 WHERE ip_hash = %(ip)s
                   AND created_at > now() - make_interval(secs => %(secs)s)
                """,
                {"ip": ip_hash, "secs": ATTEMPT_WINDOW_SECONDS},
            ).fetchone()
    except Exception:
        log.exception("Login throttle check failed; allowing the attempt.")
        return False
    return int(row["n"]) >= MAX_ATTEMPTS


def _record_attempt(conn, ip_hash: str, email: str | None) -> None:
    conn.execute(
        "INSERT INTO admin_login_attempt (ip_hash, email) VALUES (%s, %s)",
        (ip_hash, email),
    )
    # Sweep anything past the window on the way through, so the table stays
    # the size of the last quarter of an hour rather than growing forever.
    conn.execute(
        """
        DELETE FROM admin_login_attempt
         WHERE created_at < now() - make_interval(secs => %s)
        """,
        (ATTEMPT_WINDOW_SECONDS * 4,),
    )


# --------------------------------------------------------------------------
# The session
# --------------------------------------------------------------------------

def sign_in(user: dict[str, Any]) -> None:
    # The view asked for current_user() before the credentials were checked,
    # which cached "nobody" for this request. Drop it, or everything that runs
    # after the sign-in — the audit row, most of all — records nobody as the
    # actor.
    g.pop("admin_user", None)
    session.clear()
    session[_UID] = int(user["id"])
    session[_EPOCH] = int(user["session_epoch"])
    session[_CSRF] = secrets.token_urlsafe(32)
    session.permanent = False


def sign_out() -> None:
    for key in (_UID, _EPOCH, _CSRF):
        session.pop(key, None)
    g.pop("admin_user", None)


def current_user() -> dict[str, Any] | None:
    """The signed-in account, or ``None``. Cached for the request.

    Re-read from the database on every request rather than trusted from the
    cookie: that is what makes disabling an account, changing its role, or
    resetting its password take effect on the next click instead of whenever
    the person happens to sign out.
    """
    if "admin_user" in g:
        return g.admin_user

    g.admin_user = None
    uid = session.get(_UID)
    if not uid:
        return None

    database = current_app.extensions["kmq_db"]
    try:
        user = find_user(database, int(uid))
    except Exception:
        # A pool that cannot answer means nobody is signed in, which sends
        # them to a sign-in page that will say so.
        log.warning("Could not load the signed-in account; treating as signed out.")
        return None

    if user is None or user["is_disabled"]:
        sign_out()
        return None
    if int(session.get(_EPOCH, -1)) != int(user["session_epoch"]):
        # The password was reset, or the account was signed out everywhere.
        sign_out()
        return None

    g.admin_user = dict(user)
    return g.admin_user


#: Rank per role code, read from admin_role once per process. A third role is
#: an INSERT, and this picks it up on the next restart; the seeded pair is the
#: fallback for a database that cannot be reached mid-request.
_RANKS: dict[str, int] = {"editor": 10, "owner": 20}
_ranks_loaded = False


def role_ranks(database) -> dict[str, int]:
    global _ranks_loaded
    if _ranks_loaded:
        return _RANKS
    try:
        for row in roles(database):
            _RANKS[row["code"]] = int(row["rank"])
        _ranks_loaded = True
    except Exception:
        log.warning("Could not read admin_role; using the seeded ranks.")
    return _RANKS


def outranks(user: dict[str, Any] | None, role: str) -> bool:
    """Whether ``user``'s role is ``role`` or better.

    Compares ranks rather than codes, so a role added between the two — a
    "viewer" below editor, say — needs no change here.
    """
    if user is None:
        return False
    ranks = role_ranks(current_app.extensions["kmq_db"])
    required = ranks.get(role)
    if required is None:
        # An unknown requirement is a programming error; refuse rather than
        # let a view fall open because its role name was misspelled.
        log.error("Unknown role required: %s", role)
        return False
    return int(user.get("role_rank", 0)) >= required


# --------------------------------------------------------------------------
# CSRF
# --------------------------------------------------------------------------

def csrf_token() -> str:
    """The token for this session, minted on first use."""
    token = session.get(_CSRF)
    if not token:
        token = secrets.token_urlsafe(32)
        session[_CSRF] = token
    return token


def check_csrf() -> None:
    """Abort with 400 unless the POST carries this session's token."""
    sent = request.form.get("csrf_token", "")
    held = session.get(_CSRF, "")
    if not held or not sent or not secrets.compare_digest(sent, held):
        log.warning("Rejected a POST to %s on a missing or wrong CSRF token.",
                    request.path)
        abort(400)


# --------------------------------------------------------------------------
# Guards
# --------------------------------------------------------------------------

def require(role: str = "editor"):
    """Refuse the request unless a signed-in account holds ``role`` or better.

    Returns a response to send instead, or ``None`` to carry on — shaped for a
    ``before_request`` hook rather than as a decorator, so that adding a view
    to the admin cannot forget to guard it.
    """
    user = current_user()
    if user is None:
        # full_path keeps the query string, which a filtered leads list needs;
        # it also appends a bare "?" to paths that had none, hence the strip.
        return redirect(url_for("admin.login", next=request.full_path.rstrip("?")))
    if not outranks(user, role):
        abort(403)
    return None
