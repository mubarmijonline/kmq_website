# kmq_website

KMQ — كي إم كيو لخدمات حماية وتظليل السيارات. A bilingual (Arabic-first,
right-to-left) marketing site for a Saudi car protection and window-tinting
business with six branches across Riyadh, Jeddah and Dammam.

Imported from the Claude Design project "KMQ Premium Car Protection". Flask +
Jinja + PostgreSQL, deployed the house way.

**This is not part of `mubarmijonline_website`.** Different client, different
brand, its own project directory.

## Where things are

| Path | What |
|---|---|
| `docs/PRD.md` | What the site does, for whom, and how "done" is judged |
| `docs/PLAN.md` | Stack, data model, URL scheme, sequencing, risks |
| `docs/DESIGN-IMPORT.md` | What came from the design project, what diverged, what is outstanding |
| `docs/milestones/` | Delivery order, one file each, 01 to 05 |
| `app/content.py` | Every string, both languages, as typed records |
| `app/routes.py` | The 42 URLs |
| `app/forms.py` | Lead-form validation |
| `app/text.py` | Saudi phone and plate/invoice normalisation |
| `app/db.py` | The public site's two queries: write a lead, read a warranty |
| `app/store.py` | The editable-content store and the overlay over `content.py` |
| `app/editors.py` | What the admin lets people edit: copy groups, record specs |
| `app/auth.py` | Admin accounts, sessions, roles, CSRF, the sign-in throttle |
| `app/admin.py` | The `/admin` blueprint |
| `app/audit.py` | Who changed what, when |
| `db/migrations/002_admin.sql` | The admin and content-store tables |
| `db/migrations/003_branch_editable.sql` | Branch display strings, in both languages |
| `db/schema.sql` | PostgreSQL schema. Applies clean to PG 16.14 |
| `db/test_schema.sql` | 22 constraint checks. Runnable |
| `design/` | Design system: tokens, base, components, `app.js`, `admin.css` |
| `templates/partials/icons.html` | The client's icon kit, generated from `WEBSITE/` by `scripts/build_icons.py` |
| `static/img/pay/tamara-mark.png` | The Tamara wordmark, cut off its brand pill by `scripts/build_paymarks.py` |
| `templates/` | Jinja templates, one per page |
| `tests/` | 162 checks without a database, 188 with one |
| `static/build/` | Generated CSS/JS. Not in git |

## Run it

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/python -m flask --app wsgi:application run --port 5200
```

`http://127.0.0.1:5200/` redirects to `/ar/`. The CSS and JS bundles rebuild
whenever a file under `design/` changes; set `KMQ_ENV=prod` to turn that off
and build explicitly with `scripts/build_assets.py`.

The icon partial is generated too, but only when the client sends new artwork:

```bash
.venv/bin/python scripts/build_icons.py
```

It reads `WEBSITE/`, drops the Illustrator wrappers, turns the kit's #00B3FF
into `currentColor` and writes `templates/partials/icons.html`. Never edit
that file by hand.

Tamara's mark arrives as a PNG rather than as kit SVG, so it has its own
one-liner. It lifts the wordmark off the brand's rainbow pill and writes
`static/img/pay/tamara-mark.png` on transparency:

```bash
.venv/bin/pip install Pillow && .venv/bin/python scripts/build_paymarks.py
```

Pillow is a build-time dependency only, which is why it is not in
`requirements.txt`; the script says so if it is missing.

The site runs **without a database**. Forty of the forty-two pages never touch
one; the warranty lookup and the lead form degrade to a notice that points the
visitor at WhatsApp.

## Deploying

**One session owns the deploy. Do not run `scripts/build_assets.py`, and do
not restart the service, unless you are that session.**

The site is served straight out of this directory — there is no copy step and
no separate release. `deploy/kmq.service` runs gunicorn from
`/projects/kmq_website` and nginx serves `static/` from the same path, so
publishing sends up whatever is on disk at that moment, including anyone
else's half-written file.

Publishing is two commands, in this order, back to back:

```bash
.venv/bin/python scripts/build_assets.py
sudo systemctl restart kmq
```

Both steps are required, and the order is not negotiable:

- **Build without restart is the origin 404.** In prod the manifest is read
  once at boot into `app.extensions["kmq_assets"]` and never re-read, while
  `build()` deletes every fingerprint that is not in the manifest it just
  wrote. So a build under a running service leaves the app emitting HTML that
  names a file the build has just deleted. The CDN keeps serving its cached
  copy for a while, which is what makes this easy to miss — check the origin
  directly, with a cache-busting query string.
- **Restart without build silently ships nothing.** `create_app` calls
  `_wire_assets(app, rebuild=not is_prod)`; under `KMQ_ENV=prod` that is
  `rebuild=False`, and `_wire_assets` builds only when `manifest.json` is
  missing entirely. The mtime-driven rebuild hook is registered in dev only.
  A restart therefore publishes template and Python changes but keeps serving
  whatever bundle `manifest.json` already names, so a `design/` change looks
  deployed and is not.

Do not "fix" the second point by deleting `manifest.json` to force a boot-time
build. `deploy/gunicorn.conf.py` runs 2 workers with `preload_app=False`, so
`create_app` runs once per worker and both would build at once, each deleting
what the other just wrote.

### Run local servers with `KMQ_ENV=prod`

```bash
KMQ_ENV=prod SECRET_KEY=local-verify-only \
  .venv/bin/python -m flask --app wsgi:application run --port 5200
```

A plain dev server against this working tree rebuilds `static/build/` whenever
a `design/` mtime moves — no `build_assets.py`, no intent required — and that
rebuild deletes the fingerprint the production workers are serving just as a
manual build does. It cuts the other way too: because the rebuild writes a new
`manifest.json`, a forgotten dev server is also a silent *publisher*, staging
whatever happens to be in `design/` at that moment for the next restart to
pick up. `KMQ_ENV=prod` turns the rebuild hook off, so the server reads the
existing manifest and never writes. Prod also refuses to boot without
`SECRET_KEY`, hence the throwaway one above.

### File modes in `static/build/`

Build output must stay group-writable. `static/build/` is setgid and both
`omar_ashraf` and the interactive accounts are in `developers`, so either can
create or delete there — but a fingerprint left at `0644` by one account
cannot be overwritten by the other. That matters in one specific way: if
`manifest.json` ever goes missing, `_wire_assets` calls `build()` inside
`create_app`, in the worker, as `omar_ashraf`. If the hashes are unchanged it
tries to overwrite the existing files, and a `PermissionError` there is not a
failed build — it is gunicorn failing to boot. `scripts/build_assets.py` sets
`umask(0o002)` so new files land `0664`; if you see `0644` appear again,
something built with a stricter umask.

### Before and after

Sweep every public page in both locales before restarting — the routes are
cheap to walk in-process with `app.test_client()`. Afterwards, confirm the
page and the bundle agree: fetch the fingerprint the live HTML names, with a
cache-busting query, straight from the origin rather than through the CDN.

## Test it

```bash
.venv/bin/python -m pytest tests/ -q
```

The admin and overlay tests need a database and skip without one. They write
to it, so point them at a development copy and never at production:

```bash
KMQ_TEST_DATABASE_URL=postgresql:///kmq_dev .venv/bin/python -m pytest tests/ -q
```

## The admin

`/admin` edits the copy the public site renders. It needs the migration, the
content seeded from `app/content.py`, and one account:

```bash
psql -q -v ON_ERROR_STOP=1 -d kmq -f db/migrations/002_admin.sql -f db/migrations/003_branch_editable.sql
```

```bash
.venv/bin/python -m flask --app wsgi:application seed-content
```

```bash
.venv/bin/python -m flask --app wsgi:application create-owner you@example.com "Your Name"
```

`create-owner` prints a password once and stores only its hash; the account
cannot reach anything until it has been changed. `reset-password` issues a new
one and signs that account out everywhere. Seeding is idempotent — re-running
it leaves edits alone, and `--force` (which discards them) asks first.

Branches are the one exception to "content is a document": they stay in the
`branch` table, where the E.164 and HTTPS checks live and where every lead and
warranty points, and the overlay builds the branches list out of it.

Stored content is layered *over* the copy in `app/content.py`, never in place
of it: a database that is down means edits stop applying, not that the site
stops. Deleting a `copy_string` row is the revert.

## Verify the schema

```bash
sudo -u postgres psql -q -c 'DROP DATABASE IF EXISTS kmq_schema_check' -c 'CREATE DATABASE kmq_schema_check' && sudo -u postgres psql -q -v ON_ERROR_STOP=1 -d kmq_schema_check -f db/schema.sql -f db/test_schema.sql
```

Ends with `ALL SCHEMA CHECKS PASSED`. Drop the database afterwards.

## The one thing to know before touching content

Facts the client has not supplied are the `TBD` sentinel in `app/content.py`,
and templates render them as "to be confirmed" in the reader's language. **Do
not fill them in with plausible values.** The design project shipped invented
branch phone numbers, invented Google review scores and a specimen warranty
record; none was imported, and four tests exist specifically to keep them out.

See [DESIGN-IMPORT.md](docs/DESIGN-IMPORT.md) for the full list.

## Current blockers

**No WhatsApp number.** `KMQ_WHATSAPP` is unset, so every WhatsApp call to
action — the hero, the floating button, all five package cards, all six branch
cards — routes to `/contact-us` instead. WhatsApp is the business's primary
sales channel, so this is the single highest-value thing to unblock. Set the
environment variable and every CTA switches over; no code change.

**Three of six branches have no phone number, and none has confirmed hours or
an address.** The pages render honestly around this, but launching that way is
a business decision, not a technical one.

**Not deployed.** Milestone 05 has not run. It needs a go-ahead: deploying
creates a public DNS record and a public HTTPS endpoint.
