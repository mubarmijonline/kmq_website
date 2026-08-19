# 09 — Operations

**Goal.** The admin is useful for running the business, not only for editing
words.

**Includes**
- **Dashboard.** Lead count, warranties by status, recent activity.
- **Leads.** List with filters (branch, service, date), detail view, a handled
  flag with who marked it, CSV export. Adds `handled_at` and `handled_by` to
  `lead`; the public insert path is untouched.
- **Warranties.** Full CRUD per the amended PRD — create, edit, and set status
  to `active` / `expired` / `void`. Plate and invoice are normalised through
  `text.normalise_lookup` on write, exactly as the lookup normalises its query,
  so admin-created records are findable.
- **Settings.** `WHATSAPP_NUMBER` and `SHOW_PRICES` move to
  `site_setting`. An environment variable, where set, still wins — a deploy can
  pin a value the admin cannot override.
- **Users.** Owner only: invite, change role, disable. An account is disabled,
  never deleted, so audit rows keep pointing at a real person.
- **Audit.** Filterable list of who changed what, with the previous value.

**Acceptance.** A warranty created in the admin is found by the public lookup by
plate and by invoice, in both Arabic-Indic and Latin digits. Voiding it changes
what the lookup reports. Setting a WhatsApp number in settings makes every CTA
open a chat, with no restart. Clearing it returns every CTA to the contact page.
An editor gets 403 on settings, users and audit. A disabled account cannot sign
in, and its past audit rows still name it. CSV export opens in a spreadsheet
with Arabic intact.

**Status.** Not started.
