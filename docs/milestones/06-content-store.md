# 06 — Content store

**Goal.** Everything the public site renders comes from the database when it is
reachable, and from the shipped Python dicts when it is not. No template
changes, no visible difference.

**Includes**
- `db/migrations/002_admin.sql`: `copy_string`, `content_entry`,
  `site_setting`, `content_version`, and the admin tables milestone 07 needs.
- `app/store.py`: reads and writes for the above.
- The overlay inside `app/content.py`'s eight accessors — DB values layered
  over the `AR` / `EN` dicts, never replacing them.
- A 5-second TTL cache keyed on `content_version`, so both gunicorn workers
  pick up an edit without a restart.
- `flask seed-content`: walks the dicts and fills `copy_string` and
  `content_entry`. Idempotent.
- `post` entries gain a `body` key, empty on seed.

**Acceptance.** Seeding a fresh database changes nothing a visitor sees: all 42
URLs return 200 and render byte-identically before and after. Editing a
`copy_string` row directly in psql changes the rendered page within five
seconds. Stopping Postgres leaves all 42 URLs returning 200 with the shipped
copy. Running the seed twice is a no-op.

**Status.** Not started.
