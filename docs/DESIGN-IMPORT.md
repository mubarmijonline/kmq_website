# Design import — Claude Design "KMQ Premium Car Protection"

Imported 2026-08-15 from the Claude Design project
`f33c6981-1c08-4837-9ff6-6fd22568afea`.

| Source file | Became |
|---|---|
| `KMQ Website.dc.html` | the visual system and page structure |
| `uploads/kmq_content.docx` | `app/content.py` — the copy, in both languages |
| `uploads/KMQ_Website_Content_File (2).docx` | nothing: **byte-identical** to `kmq_content.docx` (both SHA-256 `26764ca1…`). One document, uploaded twice |
| `content.txt` | nothing: a lossy text dump of the same `.docx`, with raw WordprocessingML markup interleaved into the prose. The `.docx` was parsed directly instead |
| `support.js` | not imported — it is the design tool's React runtime |
| `uploads/*.png` | not imported — conversation screenshots, referenced by neither file |

The design file's inline `<style>`, its ~800 `style="…"` attributes and its
`AR`/`EN` constants became `design/tokens.css`, `design/base.css`,
`design/components.css` and `design/app.js`. Its `class Component extends
DCLogic` — state, `go(page)`, `renderVals()` — became real routes.

## The two sources disagree, and the document wins

The design file is a single-page prototype: one URL, `state.page`, and a
`go(page)` handler. The Word document is a signed-off content specification
with a sitemap, slugs and an SEO table pointed at them. Where they conflict the
document is authoritative, because it is the artefact the client approved.

**Six conflicts, and how each resolved:**

1. **No URLs at all.** The prototype had one address for eight screens —
   unlinkable, unshareable, invisible to search. The document's sitemap
   (`/about-us`, `/services`, `/packages`, `/warranty`, `/branches`, `/blog`,
   `/contact-us`) is now the routing table, under `/ar/` and `/en/` prefixes.

2. **No contact page.** The document specifies one, with a seven-field lead
   form (name, phone, service, car model, branch, timing, notes) and its option
   lists. The prototype's "تواصل معنا / Contact" nav item just opened WhatsApp.
   The page and the form now exist; the form is `app/forms.py` and the `lead`
   table.

3. **One service page instead of five.** The document defines PPF gloss, PPF
   matte, nano ceramic, window tint and colour change, each with its own copy,
   feature list and warranty. The prototype detailed only gloss and reduced the
   rest to a card. All five now have `/services/<slug>`.

4. **No FAQ.** Section 10 of the document is nine questions and answers. The
   prototype has none. They are now an accordion on the home page — the
   document does not give the FAQ its own slug, so it did not get one.

5. **The blog articles differ.** The prototype invented seven titles; the
   document lists eight. The document's eight are what shipped.

6. **The about copy was invented.** The prototype told a story about growing
   from a single branch, with values and a five-step process, none of it in the
   document. The document's own about text — including "more than three and a
   half years" in the market — replaced it.

## Fabricated data that was not imported

The prototype hardcoded four things that would have been false on a live
commercial site. The document's "Pending Items" section confirms the client has
not supplied any of them.

| Prototype shipped | Why it is not here |
|---|---|
| `+966 55 000 0001` … `0004` as branch phone numbers | Not KMQ's numbers. The document asks the client for them |
| `4.9 / 5`, `4.8 / 5` Google review scores | Fabricated third-party ratings. Not a placeholder — a false claim about what customers said |
| `KMQ-2026-04812`, "PPF Gloss (Full)", `2026/03/14 → 2036/03/14` returned by the warranty checker for **any** input | A specimen record presented as a real lookup. The checker now queries Postgres and says "not found" when there is nothing |
| `966500000000` as the WhatsApp fallback number | Not KMQ's number. `KMQ_WHATSAPP` is unset by default and every CTA falls back to the contact form |

Each is covered by a test: `test_no_fabricated_phone_numbers_anywhere`,
`test_no_fabricated_review_scores`, `test_no_specimen_warranty_record`,
`test_no_placeholder_whatsapp_link`.

Where a fact is simply unknown, `content.py` holds the `TBD` sentinel and the
template prints the localised "to be confirmed" — `يُحدَّد لاحقًا` / "To be
confirmed" — in the same slot, so the card keeps its shape.

## What the runtime did, and what replaced it

| Behaviour | Was | Now |
|---|---|---|
| Page switching | `state.page` + `go(page)`, one URL | Real routes; `url_for` throughout |
| Language | `state.lang` toggling between two JS objects | `/ar/` and `/en/` prefixes, a URL converter, and `url_value_preprocessor` |
| Mobile header | `window.innerWidth < 1024` in JS deciding what to render | A CSS media query at the same 1024px, so it is right before the script loads |
| Scroll-spy | `getBoundingClientRect()` over every section on every scroll event | One `IntersectionObserver` |
| Sticky header | `state.scrolled`, re-rendering the header | `data-scrolled` attribute, CSS transition |
| Blog filter, search, pagination | `state.blogCat`, `blogSearch`, `blogPage`, re-rendering the list | Query parameters, filtered server-side; JS narrows in place and syncs the URL |
| FAQ | did not exist | `<details>`/`<summary>`, animated on `grid-template-rows` |
| Before/after slider | `state.reveal` driving an inline width | A range input driving `--kmq-reveal` via `clip-path` |
| Warranty check | `onWarrantyCheck` setting a flag that revealed a constant | `POST /warranty`, a real query, four outcomes |

## Deliberate divergences

1. **Logical CSS properties.** The prototype computed `startSide`/`endSide` in
   JavaScript and wrote `left:`/`right:` into every style attribute. This port
   uses `padding-inline`, `border-inline-start`, `inset-inline-end`,
   `text-align: start`. RTL is now a `dir` flip, not a second stylesheet. A
   test fails the build if a physical side reappears.

2. **The site works without JavaScript.** Navigation, the blog filter and
   search, the FAQ, the language switch and both forms are all plain HTML.
   `app.js` only improves them.

3. **`prefers-reduced-motion` caps iteration count, not just duration.**
   Setting `animation-duration: .001ms` alone — which is what the sibling
   project inherited from its own design source — makes an *infinite*
   animation loop about a million times a second, i.e. vibrate at full speed.
   `animation-iteration-count: 1` is the other half.

4. **Keyboard focus styles.** The prototype had none at all, on a site whose
   only purpose is starting a conversation.

5. **A skip link and landmark structure**, also absent.

6. **The warranty lookup is a POST.** A plate number in a query string ends up
   in the nginx access log and in the `Referer` header of every outbound link
   on the result page.

7. **The lookup returns four fields and no more.** The row also holds a branch,
   a technician name and an install date. An unauthenticated endpoint does not
   get to expose staff names.

8. **`© 2026` is the current year.**

9. **The newsletter box was dropped.** The prototype had a subscribe field
   wired to nothing, and the document never mentions a newsletter. A form that
   silently discards an email address is worse than no form; it returns when
   there is somewhere to send it.

10. **Prices and the before/after band are switches.** The prototype exposed
    `showPrices` and `showBeforeAfter` as design settings; they are
    `KMQ_SHOW_PRICES` and `KMQ_SHOW_BEFORE_AFTER`.

## Two contradictions inside the client's own document

Neither was invented away — both render exactly as the document states them,
and both need a one-line answer from the client.

1. **Window tint warranty.** The packages table says the tint package's
   warranty "varies by film type" (`حسب نوع العازل`); the warranty section
   says tint is warranted for **10 years**. Both appear, in their own sections.

2. **The colour-change package is missing from the Arabic pricing table.** The
   Arabic table (section 5) lists four packages; the English pricing table
   (Part Two, section 3) lists five, including colour change at 7,500–9,000 SAR
   with a 7-year warranty. Five shipped, since the English table is the more
   complete one and the prototype agreed with it.

## Outstanding

**The seven pending items** from the document's own last section. Three are
load-bearing:

- **Branch WhatsApp numbers.** All six are unknown. Until they arrive, every
  branch card's WhatsApp button routes to the contact form.
- **Exact addresses and working hours per branch.** The footer's generic hours
  are shown; per-branch hours and the "Directions" links are `TBD`.
- **Final fixed prices.** The nano ceramic package has no price at all.

And four that are not:

- Before/after photography for the home page.
- Brand visual identity — logo files, palette, typography. The header and
  footer draw the diamond mark as inline SVG, ported faithfully from the
  prototype, which is all the design project actually contains.
- Confirmation on pickup and delivery coverage in Jeddah.
- Warranty coverage terms per service — the document supplies these for PPF,
  nano ceramic and tint, so this appears to be already resolved.

**Article bodies.** The document supplies eight titles and nothing else.
`/blog/<slug>` renders the title, the excerpt and a plain statement that the
text is being written, rather than generated copy nobody at KMQ has approved.

**Photography.** Every image slot renders the prototype's own art-direction
note (`[ branch photo ]`, `[ hero image: PPF film being applied … ]`) as a
labelled placeholder. They are a brief for the photographer and should not
survive launch.

**Self-hosted fonts.** Tajawal, Almarai and Space Grotesk load from Google
Fonts, as the prototype specifies. Self-hosting is the better answer for a
Saudi audience — one less cross-origin dependency and one less round trip.
