# 02 — Content

**Goal.** Every string from `kmq_content.docx` is in `app/content.py`, in both
languages, as typed records.

**Includes**
- `AR` and `EN` dicts, same keys, verified equal key sets.
- Typed records with slugs: services (5), packages (5), branches (6),
  warranty blocks (3), FAQ (9), articles (8), film spec, add-ons, values.
- `TBD` sentinel for every pending fact.
- Lead-form field definitions (7 fields) from the content file's table.

**Acceptance.** `set(AR) == set(EN)`. Every list-valued key has equal length in
both. No branch carries a phone number, no review carries a score, no warranty
carries a specimen record. A key-coverage test passes.

**Status.** Done.
