# 07 — Admin auth

**Goal.** Staff can sign in at `/admin`. Nobody else can reach anything under
it.

**Includes**
- `admin_role` (`owner`, `editor`) as a table, `admin_user` referencing it.
  No `is_admin` column anywhere.
- `flask create-owner`: seeds one owner, prints the generated password once,
  stores only a `werkzeug.security` hash.
- `must_change_password` gating every admin page except the change-password
  form and logout.
- Session login on Flask's signed cookie. `SECRET_KEY` becomes mandatory when
  `KMQ_ENV=prod` — the current `os.urandom(32)` fallback gives each of the two
  gunicorn workers a different key and silently breaks sessions.
- Per-session CSRF token on every POST, compared with `compare_digest`.
- Login throttled on the salted IP hash the lead form already uses.
- `audit_log`, written on every mutating admin action.

**Acceptance.** Every admin URL redirects to login when signed out, POSTs
included. A POST with a missing or wrong CSRF token is rejected. The seeded
owner is bounced to the password form until the password is changed. An
`editor` gets 403 on settings and user management; an `owner` does not. Six
failed logins from one address are throttled. Starting with `KMQ_ENV=prod` and
no `SECRET_KEY` refuses to boot rather than starting insecurely.

**Status.** Done, 2026-08-19.

`app/auth.py` holds accounts, sessions and the guards; `app/audit.py` the
trail; `app/admin.py` the blueprint — sign in, sign out, change password, a
dashboard, and a read-only audit view. `design/admin.css` is a separate
bundle, so a visitor never downloads the staff interface and staff never wait
for the public site's components to load. `tests/test_admin.py` covers the
acceptance list and runs against `KMQ_TEST_DATABASE_URL`, skipping without it.

Three decisions worth recording:

- **The guard is a `before_request` hook, not a decorator.** A decorator is
  opt-in and the failure mode of forgetting one is an unprotected page. Every
  endpoint in the blueprint is refused by default; `ANONYMOUS` names the one
  that is not.
- **Sessions are the signed cookie plus `session_epoch`.** The account is
  re-read on every request and the epoch compared, which is what makes a
  disabled account, a changed role or a password reset take effect on the next
  click rather than at the next sign-out.
- **A missing database is 503, not 500.** There is nothing to edit and nobody
  to authenticate without Postgres, but the public site is unaffected and says
  so.

Role separation is proved against the audit view, which is owner-only; the
settings and user sections it also names arrive in milestone 09.
