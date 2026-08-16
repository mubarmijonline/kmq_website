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

**Status.** Not started.
