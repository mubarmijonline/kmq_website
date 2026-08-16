# KMQ — functional PRD

KMQ (كي إم كيو) is a Saudi car protection and window-tinting business: paint
protection film (PPF), nano ceramic, heat-insulating tint and colour change.
Six branches across Riyadh (3), Jeddah (1) and Dammam (2).

This document describes behaviour. Stack, schema and file layout are in
[PLAN.md](PLAN.md).

## Who uses it

| Role | Reaches the site how | Wants |
|---|---|---|
| **Prospective customer** | Search, Instagram/TikTok/Snapchat, word of mouth | A price before talking to anyone; proof the warranty is real; the nearest branch |
| **Existing customer** | Direct, after installation | To check that their warranty is active and when it expires |
| **Quality team** | The admin UI | Activates warranties after inspection, and records their status |
| **Editor** | The admin UI | Changes any wording, price, branch detail or article the public site shows |
| **Owner** | The admin UI | Everything an editor can do, plus site settings and staff accounts |

There is no public login. Every **visitor** is anonymous. Staff sign in at
`/admin`, which is not part of the public site — see "Administration".

## The primary action

Every page funnels to one of two things:

1. **WhatsApp** — a pre-filled message. This is the business's real sales
   channel; the content file specifies WhatsApp CTAs on the hero, every package
   card, every branch card and every article.
2. **The lead form** on Contact — for visitors who will not open WhatsApp.

Both must be reachable from every page. A visitor must never be more than one
click from a way to start a conversation.

## Pages

The content file fixes eight top-level pages and their URLs. These are
contractual — they are what the client signed off and what the SEO table
targets.

| # | Page | URL | What it does |
|---|---|---|---|
| 1 | Home | `/` | Hero, trust strip, four service cards, three package cards, why-KMQ, warranty pitch, before/after proof, branches, journal teaser, FAQ, closing CTA |
| 2 | About us | `/about-us` | Who KMQ is, values, film specification table |
| 3 | Services | `/services` | Index of the five services |
| 3a–e | A service | `/services/<slug>` | One page each for PPF gloss, PPF matte, nano ceramic, window tint, colour change |
| 4 | Packages | `/packages` | The five packages with price ranges and warranties, plus add-ons |
| 5 | Warranty | `/warranty` | What each warranty covers, what it does not, conditions, after-sales, and a warranty lookup |
| 6 | Branches | `/branches` | Six branch cards with hours, WhatsApp and directions |
| 7 | Blog | `/blog` | Article listing with category filter, search and pagination |
| 7a | An article | `/blog/<slug>` | One article |
| 8 | Contact us | `/contact-us` | WhatsApp CTA and the lead form |

Every URL exists under both language prefixes: `/ar/...` and `/en/...`. Bare
`/` redirects to the Arabic site.

## Language

The site is bilingual Arabic and English. **Arabic is the default** — it is the
customer's language, and the content file's first and larger half is Arabic.

- Arabic renders right-to-left; English left-to-right.
- A visitor switches language from the header, on any page, and stays on the
  page they were reading.
- The choice is remembered for the next visit.
- Nothing is half-translated: a string exists in both languages or the feature
  does not ship.

## Rules the system enforces

**Pricing.** Prices are ranges, shown in Saudi Riyal, exactly as the content
file states them. A package whose price is not yet agreed shows "to be
confirmed", never a number and never a blank. Prices can be hidden site-wide
without a code change, because the design exposes that as a setting.

**Warranty lookup.** A visitor enters a plate number or an invoice number.

- A match shows: status, service, activation date, expiry date.
- No match shows a plain "no warranty found" and invites them to WhatsApp.
- The lookup is read-only and reveals nothing beyond those four fields — no
  name, no phone number, no address.
- A warranty exists in the system only after the quality team activates it
  following inspection. Booking does not create one. The page says so.

**Lead form.** Seven fields: full name, phone, service of interest, car
brand/model, preferred branch, timing, notes. All required except notes.

- Phone must be a Saudi number.
- A submitted lead is stored and confirmed on screen.
- A failed submission returns the visitor's answers to them, not an empty form.
- The form is protected against automated submission.

**Facts that are not yet decided are not invented.** The content file ends with
seven pending items — branch phone numbers, exact addresses and hours, final
prices, before/after photography, brand assets. Wherever one of those is
missing the page says "to be confirmed" in the visitor's language. The site
never displays a placeholder phone number, a stand-in review score, or a
specimen warranty record as though it were real.

## Flows

**Find a price.** Home → package card → WhatsApp with the package name
pre-filled. Or Home → "all packages" → `/packages` → same. Three clicks
maximum from landing to an open WhatsApp conversation.

**Check a warranty.** `/warranty` → enter plate or invoice → result. No
account, no email, no waiting.

**Choose a service.** Home service card → `/services/<slug>` → that service's
detail and warranty → package CTA → WhatsApp.

**Reach a branch.** Home or `/branches` → branch card → branch WhatsApp, or
directions in Google Maps.

**Ask something specific.** Any page → floating WhatsApp button. Or
`/contact-us` → lead form → confirmation.

## Administration

Staff sign in at `/admin`. It is one interface, not a bilingual one: it edits
Arabic and English side by side.

**Roles.** Two, and they are records rather than a flag on an account:

| Role | Can |
|---|---|
| `editor` | Edit every piece of content the public site shows; read and handle leads; manage warranty records |
| `owner` | Everything an editor can, plus site settings and staff accounts |

**First run.** One `owner` account is created by a command that prints its
password once and never again. Only a hash is stored. That account cannot reach
any other admin page until it has changed the password.

**What is editable.** Everything the public site renders as copy or as a
record: the flat page strings in both languages, the five services, the five
packages and their prices, the six branches, articles and their categories, the
warranty page's blocks, the FAQ, and the three settings that are deployment
flags today — the WhatsApp number, whether prices are shown, whether the
before/after block is shown.

**Articles gain a body.** Articles previously carried a title and excerpt only,
and the article page said so in place of body copy. An article now has a body,
and the page renders it. An article with no body still shows the old notice
rather than an empty page.

**Warranty records.** The admin creates, edits and sets the status of warranty
records — `active`, `expired`, `void`. This replaces the arrangement where a
separate back-office system owned them; that system must stop writing them, or
the two will disagree. The public lookup is unchanged and still reveals only
status, service and the two dates.

**Every change is attributed.** Who changed what, and when, is recorded and
readable in the admin. Content changes are not versioned — the log says a value
changed and what it changed from, but there is no one-click rollback.

**Rules that still hold.** Nothing about the admin loosens the public site's
rules. "To be confirmed" is still what an unset branch phone renders as; the
admin lets someone set it, not fake it. A price left blank still reads as "to
be confirmed" rather than as zero.

**If the database is unreachable**, the public site keeps serving the last
copy shipped in the repository rather than failing. Edits stop applying until
it returns; the admin itself is unavailable.

## Out of scope

- **Online payment and booking.** Instalments (Tabby, Tamara, Emkan) are
  mentioned as a fact about the business, not offered as a checkout.
- **Public accounts.** Visitors never sign in. The warranty lookup stays
  anonymous.
- **Revision history.** Changes are logged and attributed, but there is no
  version history, no draft/preview of an unpublished revision, and no
  scheduled publishing.
- **Media management.** There is no image upload; before/after photography and
  brand assets remain pending client deliverables.
- **The five pending facts** listed above, until the client supplies them.

## How "done" is verified

1. All 8 pages, 5 service sub-pages and 8 articles render in both languages
   — 42 URLs, all returning 200.
2. Arabic renders right-to-left and English left-to-right, with no clipped or
   mirrored layout in either.
3. Every WhatsApp CTA opens a conversation with the correct pre-filled message.
4. The lead form rejects a non-Saudi phone number, accepts a valid one, and the
   lead survives a restart.
5. The warranty lookup returns a match for a seeded record and a clean "not
   found" for anything else.
6. No page shows a fabricated phone number, review score or warranty record.
7. Every page works with JavaScript disabled: navigation, the blog filter, the
   FAQ and the lead form all function.
8. Keyboard alone can reach and operate the navigation, the language switch,
   the blog filter, the FAQ and both forms.

For the admin:

9. Seeding the content store from the shipped copy changes nothing a visitor
   sees — all 42 URLs return 200 and render identically before and after.
10. Every admin URL redirects to the login page when signed out, including
    POSTs, and a POST without a valid CSRF token is rejected.
11. The seeded owner cannot reach any admin page other than the password change
    until the password is changed.
12. An editor cannot reach settings or user management; an owner can.
13. Editing a string in the admin changes the public page in both languages
    within five seconds, and the change is attributed in the audit log.
14. Stopping the database leaves all 42 public URLs returning 200, rendering
    the copy shipped in the repository.
15. A warranty created in the admin is found by the public lookup, by plate and
    by invoice, in Arabic-Indic and Latin digits; voiding it changes what the
    lookup reports.
