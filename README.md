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
| `app/db.py` | The only two queries: write a lead, read a warranty |
| `db/schema.sql` | PostgreSQL schema. Applies clean to PG 16.14 |
| `db/test_schema.sql` | 22 constraint checks. Runnable |
| `design/` | Design system: tokens, base, components, `app.js` |
| `templates/` | Jinja templates, one per page |
| `tests/` | 142 checks, no database required |
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

The site runs **without a database**. Forty of the forty-two pages never touch
one; the warranty lookup and the lead form degrade to a notice that points the
visitor at WhatsApp.

## Test it

```bash
.venv/bin/python -m pytest tests/ -q
```

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
