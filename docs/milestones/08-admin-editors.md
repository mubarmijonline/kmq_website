# 08 — Admin editors

**Goal.** Every piece of copy and every record the public site renders is
editable through the admin, in both languages.

**Includes**
- Admin shell: base template, nav, and `design/admin.css` bundled separately
  from the public stylesheet.
- **Copy.** The flat strings, Arabic and English side by side, grouped by the
  page that uses them rather than listed as one wall of keys.
- **Services.** Five records: name, tagline, lede, bullet points, warranty
  text, icon, order, published.
- **Packages.** Name, inclusions, price range, warranty, featured flag. A
  cleared price stores the pending sentinel, so the page keeps saying "to be
  confirmed" rather than showing a blank or a zero.
- **Branches.** Name, city, location, phone, WhatsApp, hours, map URL — writing
  the typed `branch` columns, so the E.164 and HTTPS constraints still apply.
- **Journal.** Articles including the new body field, plus categories.
- **Warranty page.** The warranty blocks and the FAQ entries.
- Every save writes an `audit_log` row and bumps `content_version`.

**Acceptance.** Changing a string in the admin changes both the Arabic and
English public pages within five seconds. Clearing a branch phone returns the
page to "to be confirmed", not to an empty line. A price cleared in the admin
renders as "to be confirmed". An article given a body renders it; one without
still shows the existing notice. Unpublishing a service removes it from the
index and makes its URL a 404. Every save appears in the audit log against the
account that made it.

**Status.** Done, 2026-08-19.

`app/editors.py` declares what is editable — the 139 flat strings grouped by
the page that uses them, and one spec per list naming its fields, which are
localised and how each is edited. `app/admin.py` renders and validates every
one of them through a single pair of views, because twenty near-identical
views would drift apart the first time a field was added to one. Adding a
field to a record is now a line in `editors.py`.

Verified against `kmq_dev`, by editing through the admin's own forms and
reading the public page back (`tests/test_editors.py`): an edited string
reaches both languages within the five-second TTL; a string edited back to
what the repository ships deletes its row rather than storing a copy; a
cleared price and a cleared branch phone both print "to be confirmed"; an
unpublished service 404s and leaves the index in both languages; an article
given a body renders it while every other article still shows the standing
notice; a new article added in the admin reaches the blog; reordering moves
the page; every save lands in the audit log against the account that made it.

Three things went differently from the plan:

- **Branches became typed columns rather than documents**
  (`db/migrations/003_branch_editable.sql`). The plan said the branch editor
  would write the typed table; what it did not say was that the table had no
  Arabic city, no short label and one un-localised `hours` column, because
  nothing had read it yet. It now carries both languages of each, the overlay
  builds the branches list out of it, and `content_entry` no longer holds a
  competing copy. Phone numbers normalise through `text.normalise_saudi_phone`
  on the way in and the CHECK constraint is still behind them, because the
  back office writes this table too.
- **A branch's own WhatsApp number is now used.** The field was in the plan's
  list; without a template change it would have been a field that did nothing,
  so `branch_card` prefers it and falls back to the site-wide number.
- **Article bodies are plain text, not HTML.** Blank lines separate
  paragraphs, `##` opens a subheading, and nothing else is interpreted. A
  textarea that renders as markup is an injection surface, and the people
  filling it in are pasting out of Word.

Not included, because they are milestone 09: the settings section, users, and
the leads inbox.
