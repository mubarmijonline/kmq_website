# 11 — The icon kit leads

**Goal.** The client's delivered icons carry the pages. Where a section used a
traced 24-square line glyph beside a heading, the client's own drawing now sits
above the words at display size, and the words read under it.

**Why.** `WEBSITE/` holds thirty-seven SVGs the client's designer drew for this
site — a car under a shield, a droplet, a plate with a number on it, a hand
holding a set of gears. Until now the pages ignored all but eight of them (the
header's social row) and drew twelve generic line icons of their own instead,
26px, tucked in a bordered tile beside the text. The delivered set is better
art than the placeholder, it is on brand by construction, and the client paid
for it.

**Includes**

- `scripts/build_icons.py` — re-emits the kit as `templates/partials/icons.html`:
  wrappers dropped, `#00B3FF` become `currentColor`, path data untouched. Two
  names may share a drawing only if the files are byte-identical. Thirty-two
  names out of thirty-seven files.
- `content.py`'s `ICONS` becomes what the admin hint always claimed it was —
  a set of names, not twelve strings of path data. `why`, `wb_points` and the
  warranty blocks gain an `icon` each; `editors.py` gains the field so those
  are editable too.
- `design/components.css` — one new block, `.kmq-glyph` and the plates that
  carry it (`--lead`, `--tile`, `--bare`), plus the section rules that turn a
  row into a column: trust strip, service cards, why cells, warranty points,
  branch cards, contact aside, packages add-ons.
- The five payment marks in `4 Packages/` are shown on the packages page on a
  light plate, since they are third-party logos in their own colours. Each is
  stripped to its wordmark first — Tabby's green pill and Tamara's rainbow one
  are backgrounds the shared chip already provides — and sized to fill that
  chip rather than to a fixed height. `scripts/build_paymarks.py` does the
  Tamara cut, which is a PNG and so outside the SVG kit's build.

**Acceptance.** Every `icon` value in both locales resolves to a name the kit
emits — asserted in `tests/test_site.py`, so a typo fails the build rather
than rendering an empty tile. Both locales of all 42 URLs still return 200.
The traced `ICONS` path data is gone from the tree. Screenshots of the home,
services, warranty and contact pages show the glyph above its text, not beside
it, at every width down to 360px.

**Status.** Done.
