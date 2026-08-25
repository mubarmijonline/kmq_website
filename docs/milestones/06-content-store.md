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

**Status.** Done, 2026-08-19.

Verified against `kmq_dev`: seeding writes 278 copy strings and 212 content
entries, and all 42 public URLs render byte-identically with the seeded
database and with `DATABASE_URL` unset — `tests/test_overlay.py` asserts the
comparison page by page. Editing `copy_string` directly in psql reaches the
page after the 5-second TTL; deleting the row returns it to the shipped copy.
Closing the pool mid-run leaves all 42 URLs at 200. A second `seed-content`
inserts nothing.

Two departures from the plan as written:

- The overlay is installed by the factory through `content.use_overlay()`
  rather than imported by `content.py`, which would have made the copy file
  depend on the store that reads it. `content.shipped()` is the new name for
  the un-overlaid dicts; the overlay and the seeder both read through it, and
  the accessors read through `content()` exactly as before. No template
  changed.
- The merge happens once per rebuild rather than once per call. `content()`
  runs several times a request and a request that changes nothing should cost
  a dictionary lookup.

`post` entries do not yet carry a `body` key: the field is added with the
editor that writes it, in milestone 08. Nothing reads it before then.
