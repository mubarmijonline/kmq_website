# 03 — Pages

**Goal.** All 8 pages plus 5 service sub-pages and 8 articles render in both
languages — 42 URLs.

**Includes**
- home, about-us, services index, service detail, packages, warranty,
  branches, blog listing, article, contact-us.
- Blog category filter, search and pagination — working without JavaScript
  (query parameters), enhanced with it.
- FAQ accordion as `<details>`/`<summary>`.
- Before/after comparison as a range input over two layers.

**Acceptance.** 42 URLs return 200 in both locales. No template raises. Arabic
headings do not clip or overflow at 360px, 768px and 1440px. Prices show as
ranges or "to be confirmed", never blank.

**Status.** Done.
