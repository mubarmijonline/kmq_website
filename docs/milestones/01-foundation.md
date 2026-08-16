# 01 — Foundation

**Goal.** A request to any URL returns a correctly-shaped page: header, footer,
locale, direction, fonts and the design system. No page content yet.

**Includes**
- `app/__init__.py` factory, config from `.env`.
- Locale URL converter, `url_value_preprocessor` + `url_defaults`.
- `design/tokens.css`, `base.css`, `components.css`, `app.js`.
- `scripts/build_assets.py`, dev rebuild-on-change.
- `templates/base.html`, `partials/header.html`, `partials/footer.html`.
- Floating WhatsApp button, mobile menu, language switch.

**Acceptance.** `/` redirects to `/ar/`. `/ar/` and `/en/` render with the
right `dir` and font stack. `/xx/` 404s. The language switch on any page lands
on the same page in the other language. Header and footer match the design
source. Keyboard reaches every control.

**Status.** Done.
