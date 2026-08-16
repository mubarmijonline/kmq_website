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

**Status.** Not started.
