# 04 — Data

**Goal.** The lead form persists and the warranty lookup reads real records.

**Includes**
- `db/schema.sql`: `branch`, `lead`, `warranty`, `warranty_status`.
- `db/test_schema.sql`: constraint checks.
- Saudi phone normalisation to E.164, server-side.
- Plate/invoice normalisation: case, whitespace, Arabic-Indic digits.
- Lead POST with validation, re-render on failure preserving input.
- Warranty lookup returning status + three dates, nothing else.
- Rate limiting on both endpoints, keyed on a salted IP hash.

**Acceptance.** Schema applies clean to a fresh database and the checks end
with `ALL SCHEMA CHECKS PASSED`. A bad phone number is rejected with the
visitor's answers preserved. A seeded warranty is found by plate and by
invoice, in both Arabic-Indic and Latin digits. An unknown query returns the
"not found" state, not an error.

**Status.** Done. Verified 2026-08-15 against PostgreSQL 16.14: schema applies
clean, 22 constraint checks pass, a seeded warranty is found by plate and by
invoice (including Arabic plate letters and Arabic-Indic digits), an expired
record reads as expired, a lead persists with its phone normalised to E.164 and
its address stored only as a salted hash, and a fourth rapid submission is
throttled.
