# KMQ — implementation plan

Behaviour is in [PRD.md](PRD.md). This is how it gets built.

## Stack

- **Flask + Jinja**, application factory, blueprint-free (one route module —
  the site is 42 URLs, not 420).
- **PostgreSQL.** The house rule is Postgres for anything transactional. Leads
  and warranty records both qualify: a lead is a commercial record the sales
  team acts on, and a warranty record is written by a separate back-office
  system and read here. SQLite would have been the call for a pure content
  site; this is not one.
- **gunicorn behind nginx**, HTTPS, systemd, auto-chosen port, Cloudflare DNS —
  the `deploy-flask-site` skill, unchanged.
- No JS framework. The design's React runtime is not imported (see
  [DESIGN-IMPORT.md](DESIGN-IMPORT.md)).

## Where content lives

Content arrives as one Word document, not a database. Two consequences:

1. `app/content.py` holds it as Python literals, keyed by locale — `AR` and
   `EN` dicts mirroring the design source's own two dicts. This is the single
   source of copy.
2. Articles, services, packages, branches, warranty blocks and FAQ entries are
   **typed records with slugs**, not loose strings. They are shaped the way a
   `content_item` table would be, so moving them into Postgres later is a
   repository swap rather than a template rewrite.

Anything the content file lists as pending resolves to a sentinel
(`TBD`) that templates render as the localised "to be confirmed". Templates
never test for `None` or an empty string.

## URL and locale scheme

```
/                     → 302 /ar/
/<lang>/              home
/<lang>/about-us
/<lang>/services
/<lang>/services/<slug>
/<lang>/packages
/<lang>/warranty
/<lang>/branches
/<lang>/blog
/<lang>/blog/<slug>
/<lang>/contact-us
```

`<lang>` is `ar` or `en`, enforced by a URL converter — anything else 404s
rather than falling through to a default. A `url_value_preprocessor` pulls the
locale off every request so no view signature carries it, and a
`url_defaults` handler puts it back so `url_for('page.home')` works without the
caller naming a language.

Slugs are stable and identical in both languages — `/ar/about-us` and
`/en/about-us`, not `/ar/من-نحن`. The content file specifies English slugs and
they are what the SEO table targets.

Language switching preserves the page: the switcher builds its href from the
current endpoint and view args with the locale swapped.

## Data model

Two tables, plus a lookup.

**`lead`** — one row per contact-form submission.
`id, created_at, full_name, phone, service, car_model, branch_id, timing,
notes, locale, ip_hash, user_agent`.

Phone stored normalised to E.164 (`+9665XXXXXXXX`). `ip_hash` is a salted
hash, not an address: it exists to rate-limit, not to identify.

**`warranty`** — written by the back office, read by this site.
`id, warranty_number, plate_number, invoice_number, service_type, branch_id,
install_date, activation_date, expiry_date, status, created_at`.

Lookup is by `plate_number` **or** `invoice_number`, both indexed, both
normalised (upper-cased, whitespace and Arabic-Indic digits folded) on write
and on query so that `أ ب ج ١٢٣٤` and `ABC1234` find the same row.

`status` is an enum-backed table (`active`, `expired`, `void`), not a boolean —
a voided warranty is not the same as an expired one and the quality team needs
to say which.

**`branch`** — six seeded rows. Phone, address and hours are nullable *because
they are genuinely unknown*, and the template renders the localised "to be
confirmed" for a null. This is the mechanism that keeps invented data out.

Schema in `db/schema.sql`, constraint checks in `db/test_schema.sql`, both
runnable the same way as the sibling project.

## Front end

`design/` holds the system, `static/build/` holds the bundle. Three
stylesheets, one script, concatenated and fingerprinted by
`scripts/build_assets.py`:

- `tokens.css` — the palette, type scale, spacing and the two font stacks,
  as custom properties. Every colour in the design source appears here once.
- `base.css` — reset, document defaults, focus-visible, reduced-motion.
- `components.css` — header, nav, buttons, cards, package cards, tables,
  accordion, blog grid, forms, footer.
- `app.js` — mobile menu, language persistence, scroll-spy, blog
  filter/search, FAQ, and the home hero's protection stack. Roughly 6 KB;
  every behaviour is an enhancement over markup that already works.

**The hero's pace is one number.** `--kmq-stack-step` in `components.css` is
the scroll distance of one stage — a wheel flick on a desktop, a swipe on a
phone. The track is six of those (bare car, three coating wipes, a dwell on
the finished car with the buttons, the exit) and `app.js` splits its stages on
the same sixths, so retiming the sequence is that one declaration.

**Two of the hero's assets are generated, not drawn.** The coatings are
filtered copies of `static/img/car-suv.png` confined by its own alpha, but the
thermal tint belongs on the glass alone, which the silhouette cannot tell it.
`scripts/trace_car.py` writes `car-suv-glass.png` next to the photo — an alpha
cut of the greenhouse thresholded off the image itself — and the grid overlay
the cutout is measured on. Swapping the hero photograph means re-running that
script, not re-tracing anything by hand.

The admin is a fourth file, `admin.css`, bundled separately with `tokens.css`
and nothing else. Two bundles rather than one because the two audiences share
a palette and no components: a visitor should never download the staff
interface, and staff editing a string should not wait for 56 KB of public-site
components.

**Logical properties throughout.** The design source computes `startSide` /
`endSide` in JavaScript and writes `left:` / `right:`. This port uses
`padding-inline`, `border-inline-start`, `inset-inline-end`, `text-align:
start`. RTL becomes a `dir` attribute flip instead of a second stylesheet.

**Fonts.** Tajawal (Arabic headings), Almarai (Arabic body), Space Grotesk
(Latin, numerals, meta labels) — as the design specifies, from Google Fonts
with `preconnect`. Self-hosting is the better answer for a Saudi audience and
is listed as outstanding, not done.

## Phase two — the admin UI

The PRD originally put an admin UI out of scope. That changed: the client now
wants everything the frontend renders to be editable, warranty records
included. See the amended "Administration" section of [PRD.md](PRD.md).

### The overlay, not a rewrite

"Where content lives" above promised that moving content into Postgres would be
"a repository swap rather than a template rewrite". This is that swap, and the
promise holds: no template changes.

Every template reads content through eight accessors in `app/content.py` —
`content()`, `service()`, `package()`, `post()`, `branch()`, `home_packages()`,
`category_label()`, `branch_options()`. Those accessors gain a database overlay
layered *over* the existing Python dicts:

```
template → accessor → overlay cache → DB rows      (when present and reachable)
                                   ↘ AR/EN dicts   (fallback, always)
```

The dicts stay in the repository as both the seed and the fallback, reachable
as `content.shipped()` — the overlay and the seeder read through that, and
everything else keeps reading through `content()`. This is
load-bearing, not sentimental: `db.py` opens its pool with `open=False`
specifically so that a Postgres outage never stops the site serving its static
pages. An admin that made content a hard database dependency would throw that
away. With the overlay, a database that is down means edits stop applying — the
site keeps rendering the last shipped copy.

### Storage shape

Collections are stored as documents, flat copy as key/value.

**`content_entry`** — `(kind, slug, locale)` unique, plus `sort_order`,
`is_published`, `data jsonb`, `updated_at`, `updated_by`.
`kind` is one of `service | package | post | category | faq | warranty_block`.
`data` holds exactly the keys the existing `_svc` / `_pkg` / `_post` builders
produce, so seeding is a straight copy and the overlay is a dict merge.

A JSON column rather than a table per kind: the application is the only writer,
the shapes are already fixed by those builder functions, and six typed tables
plus six i18n siblings would be twelve tables to express what the templates
consume as six lists of dicts. Validation lives in Python, where the shape is
already declared.

**`copy_string`** — `(locale, key)` → `value`. The couple of hundred flat
strings (`contact_title`, `hero_sub`, …). Grouped in the UI by the page that
uses them.

**`site_setting`** — `key` → `value`. The two settings that are environment
variables today (`WHATSAPP_NUMBER`, `SHOW_PRICES`) become editable.
Environment keeps precedence where set, so a deploy can still pin them.

**`branch`** and **`warranty`** keep their existing typed columns. They have
real constraints (E.164 checks, the status foreign key, the normalisation
contract) and those constraints are the point.

### Cache and invalidation

Two gunicorn workers, so an edit in one must reach the other. A single-row
`content_version` counter bumps on every write; each worker re-reads it at most
once every 5 seconds and rebuilds its overlay when it moves. Steady-state cost
is one trivial indexed query per worker per 5 seconds, against the current cost
of zero — acceptable for making the site editable. Worst case an edit is
visible 5 seconds later.

### Auth

Role-based from the first commit, per the house rule: `admin_role` is a table,
not an `is_admin` column. Two roles to start — `owner` (users, settings,
everything) and `editor` (content, leads). One `owner` is seeded by a CLI
command that prints the password exactly once; only the hash is stored, and
`must_change_password` blocks every other admin page until it is changed.

Sessions are Flask's signed cookie. **This requires a persistent `SECRET_KEY`**
— the factory currently falls back to `os.urandom(32)`, which gives each of the
two workers a different key and would log admins out on alternate requests.
Making it mandatory in production is part of milestone 07.

CSRF tokens on every POST, generated per session, compared with
`secrets.compare_digest`. Login attempts throttled on the same salted-IP-hash
mechanism the lead form already uses.

### Admin surface

`/admin`, outside the `<locale>` prefix — it is one interface for staff, not a
bilingual public page. It edits both languages side by side.

| Section | Manages |
|---|---|
| Dashboard | Counts, recent leads, pending warranties |
| Copy | Flat strings, AR and EN side by side, grouped by page |
| Services | The five services, ordering, publish state |
| Packages | Prices, inclusions, warranty text, featured flag |
| Branches | Names, locations, phone, hours, map URL |
| Journal | Articles including a new body field, categories |
| Warranty page | The warranty blocks and FAQ |
| Leads | List, filter, view, mark handled, CSV export |
| Warranties | Full CRUD — create, activate, expire, void |
| Settings | WhatsApp number, price visibility, before/after |
| Users | Owner only |
| Audit | Who changed what, when |

### What this changes in the public site

One template change only: `article.html` currently prints a deliberate
placeholder where a body would go, because no body copy was ever approved. With
a body editor that gap closes, so the placeholder is replaced by the stored body
and falls back to the placeholder when a post has none.

## Sequencing

Milestones in `docs/milestones/`, delivered in order:

1. **01 — foundation.** Layout, design system, base template, header, footer,
   locale routing. Nothing page-specific.
2. **02 — content.** `app/content.py` complete from the Word document, both
   languages, every record typed.
3. **03 — pages.** All 8 pages and the 5 service sub-pages rendering.
4. **04 — data.** Postgres schema, lead form writing, warranty lookup reading.
5. **05 — launch.** Deploy, DNS, HTTPS, verification.
6. **06 — content store.** Admin schema, seeding from the dicts, the overlay.
7. **07 — admin auth.** Roles, owner seed, forced password change, CSRF.
8. **08 — admin editors.** Every content section above.
9. **09 — operations.** Leads inbox, warranty CRUD, settings, users, audit.
10. **10 — admin launch.** Tests, migration against prod, verification.

## Risks

**The pending seven.** The content file's own last section lists seven
undecided facts, three of which are load-bearing for pages that otherwise look
finished: branch phone numbers, branch hours, and final prices. The site is
built to display "to be confirmed" for each rather than to wait for them, so
none of them blocks launch — but a launch with three of six branches showing no
phone number is a business decision, not a technical one, and belongs to the
client.

**The design's fabricated data.** The design source ships placeholder phone
numbers (`+966 55 000 0001`), Google review scores (`4.9 / 5`) and a specimen
warranty record (`KMQ-2026-04812`). None is imported. The review scores in
particular would be fabricated third-party ratings on a live commercial site;
the block renders only once real figures with a source arrive.

**The admin is now the system of record for warranties.** Phase two gives the
admin full CRUD over `warranty`, which the PRD previously said belonged to the
quality team's CRM. Whichever of the two writes a record, the other must not
also write it — two systems writing the same warranty numbers will collide on
`warranty_number`'s unique index and, worse, disagree about status. Deciding
which system retires is a business decision and belongs to the client.

**Content edits are unversioned.** The overlay stores current values, and the
audit log records who changed what, but there is no revision history and no
rollback beyond reading the audit entry and retyping. Acceptable for a site
this size; worth revisiting if the journal grows.

**Warranty lookup is an unauthenticated read.** Plate numbers are semi-public
but guessable. Mitigation: the response carries only status and dates, the
endpoint is rate-limited per IP hash, and there is no enumeration surface —
no listing, no count, no "did you mean".

**Arabic typography.** Tajawal and Almarai at the design's weights (900/800)
are heavy; Arabic diacritics and the `text-wrap: balance` in the source
headings need checking on real strings, not lorem. Verified per page in
milestone 03.

**Brand assets — delivered 2026-08-19.** The client's kit arrived as
`WEBSITE/header - footer/`: the logo in a dark-mode and a light-mode cut, plus
eight glyphs. It supersedes the ported diamond mark, which is gone from both
the header and the footer. The site wears the dark cut, because every surface
it sits on is `--kmq-bg` #0D0D0D; the light cut is the favicon, since a browser
tab is white as often as not. Both are cropped to their artwork — the delivered
files sit in a 512-square with a fifth of the height as padding, which sizes
the mark by its whitespace instead of by itself. The glyphs are re-emitted as
`templates/partials/icons.html` with `fill="currentColor"`, so they take the
gold of whatever they label rather than the kit's #00B3FF.

**Recoloured 2026-08-19.** The accent is now the logo's blue and the gold is
gone from the source tree entirely — tokens, the 23 declarations that hardcoded
it, the `.kmq-btn--gold` class name in eight templates, the select chevron's
data URI, and the two hero filter chains that made gold out of a silhouette
rather than out of a colour value. `docs/recolour-brief.md` carries the
reasoning and the measurements. Typography is the last open brand item.
