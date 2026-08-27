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

10. **Prices are a switch; the before/after band is gone.** The prototype
    exposed `showPrices` and `showBeforeAfter` as design settings. Prices
    became `KMQ_SHOW_PRICES`. The before/after slider was dropped from the
    homepage: it only ever compared two CSS gradients, and the photography
    that would make it a real proof block is still a pending deliverable.

## Two contradictions inside the client's own document

Neither was invented away — both rendered exactly as the document stated them.
The first has since been answered; the second still needs a line from the
client.

1. **Window tint warranty — settled.** The packages table said the tint
   package's warranty "varies by film type" (`حسب نوع العازل`); the warranty
   section said tint is warranted for **10 years**. The client resolved it in
   favour of ten, and in the same note gave ten years to the front-end,
   quarter-front and combo packages, whose warranty terms had been open. All
   four now read 10 years and agree with the warranty page.

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
- ~~Brand visual identity — logo files, palette~~. **Delivered 2026-08-19**,
  in `WEBSITE/header - footer/`. See "The brand kit" and "The recolour" below.
  Typography is still the prototype's.
- Confirmation on pickup and delivery coverage in Jeddah.
- Warranty coverage terms per service — the document supplies these for PPF,
  nano ceramic and tint, so this appears to be already resolved.

**Article bodies.** The document supplies eight titles and nothing else.
`/blog/<slug>` renders the title, the excerpt and a plain statement that the
text is being written, rather than generated copy nobody at KMQ has approved.

**Photography.** The delivered photographs now fill the about page, the
branch cards and all eight article slots — `static/img/`, resized to 1080px
and saved progressive, one file per article named after its slug. The article
alt text is the article's own title, so the retired `[ article thumbnail ]`
placeholder string is gone from both locales.

One slot is still a placeholder: the branch map on `/branches`, which renders
`t.map_shot` as a labelled block. It is waiting on the same pending item as
the "Directions" links — the exact address of each branch.

**Self-hosted fonts.** Tajawal, Almarai and Space Grotesk load from Google
Fonts, as the prototype specifies. Self-hosting is the better answer for a
Saudi audience — one less cross-origin dependency and one less round trip.

## The brand kit

`WEBSITE/header - footer/` — ten files, all of them Illustrator exports. The
folder is gitignored with the rest of the client source; what ships is under
`static/img/`.

| Source file | Became |
|---|---|
| `Logo Dark mode.svg` | `static/img/brand/kmq-logo.svg` — the header and footer mark |
| `Logo Light mode.svg` | `static/img/brand/kmq-logo-light.svg` — the favicon |
| `H instagram.svg`, `H tiktok.svg`, `H snap.svg`, `H facebook.svg` | the four social tiles in the footer |
| `H whatsapp.svg` | the floating WhatsApp button, replacing the glyph ported from the prototype |
| `H clock.svg`, `H mobile.svg` | the footer's "Working hours" and "Branch phones" headings |
| `location.svg` | not used yet — it belongs on the branch cards, which are waiting on the addresses |

**The two cuts are not interchangeable.** Both draw the same lockup, but the
dark cut's white letters overhang the shield, so on a light ground the parts
outside the silhouette disappear — the K's stem, the S and the D of SHIELD.
That is what the light cut's blue keyline is for. Every surface on this site is
#0D0D0D, so the dark cut is the site logo. The browser tab is not ours to
colour, so the favicon is the light one.

**Both are cropped.** The delivered files centre a 320×332 mark in a 512
square, so sizing by the box renders the artwork at 62% of the height asked
for and pads the header with dead space the gutter cannot see. Each copy's
`viewBox` is narrowed to its own `getBBox()` plus 6 units — `90 83 332 345`
dark, `84 78 342 355` light. Nothing else in either file is touched.

**The glyphs are re-emitted, not copied.** `templates/partials/icons.html`
holds the eight paths behind a `brand_icon(name, size)` macro. Two changes from
the kit: the wrapping `<defs>`/`<style>`/`<g>` are dropped, carrying the one
`fill-rule: evenodd` they held onto the paths that need it; and every glyph is
`fill="currentColor"`. The kit paints them #00B3FF, which is the logo's blue —
right on the logo, wrong on a gold section heading and wrong on a green
WhatsApp button.

Facebook joined `social` in `content.py` on the strength of the kit shipping
that glyph. Its URL is `TBD` like the other three, so all four render as
unlinked tiles. The `abbr` key — the "IG"/"TT"/"SC" two-letter stand-ins the
tiles used to show — is gone, replaced by `icon`.

## The recolour

The prototype's accent was gold — `#C9A84C` and three neighbours. The logo is
blue. Rather than leave the logo as the one blue object on a gold page, the
accent moved to the logo's own colour on 2026-08-19. The reasoning, the
measurements and the traps are in `docs/recolour-brief.md`; what actually
shipped:

| Was | Is | Contrast on `--kmq-bg` |
|---|---|---|
| `--kmq-gold` `#C9A84C` | `--kmq-blue` `#2EA8E5` — the logo's light blue | 8.50 → 7.26 |
| `--kmq-gold-bright` `#D4AF37` | `--kmq-blue-bright` `#57BFEE` | 9.24 → 9.34 |
| `--kmq-gold-hi` `#E4C674` | `--kmq-blue-hi` `#7ACDF5` | 11.69 → 10.99 |
| `--kmq-gold-deep` `#B4913C` | `--kmq-blue-deep` `#1B8FD6` | 6.53 → 5.50 |
| `--kmq-line-gold` | deleted — it had no references | — |

**The logo's other blue is not in the palette.** `#0C6BBF` measures 3.58 on
`#0D0D0D`, which fails AA at any body size. The one role it could plausibly
fill is the CTA gradient's tail, and that is precisely where the failure would
land — on a button label. Reusing the logo's gradient end to end leaves no
label colour that survives it: dark ink reads 7.26 at one end and 3.58 at the
other, white reads 5.42 and 2.68 the other way. `--kmq-grad-cta` therefore
stops at `--kmq-blue-deep`, worst case 5.50.

**23 declarations hardcoded gold rather than referencing a token**, and would
have survived a token-only swap. Twenty-one were `rgba()` literals in
`components.css`; the other two were easy to miss — an inline
`rgba(201,168,76,.9)` on the featured category label in `blog.html`, and a
URL-encoded `%23C9A84C` inside the select chevron's `data:image/svg+xml` URI,
which no search for `#C9A84C` will ever find. All are tokens now.

**The hero's coat layers had no colour to swap.** The protection-stack
animation tints a black silhouette with `sepia()` and `saturate()`, so the gold
was a filter chain, not a value. Both chains were re-derived by measuring the
colour they actually produce on a canvas: the ceramic wash was `hsv(60, 9%)`
and is now `hsv(198, 9%)` — the same strength at the logo's hue. The tint rim
was `hsv(58, 35%)` and reaches `hsv(198, 31%)`; blue saturation clips there,
because the blue channel is already at 255, so `saturate()` above 18 changes
nothing. That four-point shortfall is the only place the recolour could not
match the original exactly.

**`.kmq-btn--gold` became `.kmq-btn--blue`** across eight templates and the
stylesheet, 17 occurrences, and `.kmq-coat--rim-gold` became
`.kmq-coat--rim-blue`. A class named for a colour it no longer has is worse
than no name at all.

**The admin panel shares `tokens.css`**, so its ten token references moved with
everything else. It could not be rendered for review here — `/admin/login`
returns 503 without a database — but its bundle resolves every custom property
it uses.

Verified with a sweep over every route in both locales: no warm colour survives
in any computed style, and every text node on a flat background clears its WCAG
AA floor. The CTA family sits on the gradient and was checked against both of
its stops.
