"""What the admin lets people edit, declared once.

Two tables of contents, both derived from :mod:`app.content` rather than
invented here:

* :data:`COPY_GROUPS` — the flat strings, in the order they appear in the copy
  file, grouped by the page that uses them. A wall of 139 keys is not an
  editing surface; "Home: hero" is.
* :data:`COLLECTIONS` — one spec per list in the locale dicts, naming the
  fields, which of them are localised, and how each is edited. The specs are
  what the generic editor renders and validates, so adding a field to a record
  is a line here rather than a new template.

``tests/test_editors.py`` asserts that both cover the copy file exactly: every
scalar key is in a group, every list has a spec, and every field a record
carries has a declaration.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any

from . import content as C

#: Keys that describe the language rather than say anything in it. Editing
#: ``dir`` would mirror the layout; editing ``lang`` would lie to a screen
#: reader. They are seeded like everything else and shown as read-only.
LOCKED_KEYS = ("lang", "dir", "other_lang", "other_label")


#: Flat strings, grouped by the page they appear on. Order follows the copy
#: file, which follows the Word document, which is the order the client thinks
#: about their own site in.
COPY_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("General", ('lang', 'dir', 'other_lang', 'other_label', 'locale_name', 'brand_tagline', 'tbd')),
    ("Global calls to action", ('cta_book', 'cta_whatsapp', 'cta_contact', 'learn_more')),
    # One line answers the phone for the whole site: the floating call button,
    # every branch card and the contact page. The E.164 form is what tel: and
    # wa.me carry, so the two are edited together or they drift apart.
    ("Phone line", ('phone_primary', 'phone_primary_e164', 'call_us')),
    ("WhatsApp message templates", ('wa_default', 'wa_order', 'wa_book', 'wa_contact', 'wa_pickup')),
    ("Home: hero", ('hero_kicker', 'hero_a', 'hero_b', 'hero_sub', 'hero_cta1', 'hero_cta2', 'hero_shot')),
    ("Home: hero protection stack", ('stack_kicker', 'stack_shot')),
    ("Services", ('services_title', 'services_page_title', 'services_page_sub')),
    ("Packages", ('packages_title', 'packages_page_title', 'most_chosen', 'sar', 'warranty_label', 'order_package', 'order_on_whatsapp', 'all_packages_link', 'addons_title', 'unsure_title', 'unsure_body', 'ask_whatsapp')),
    ("Why KMQ", ('why_title',)),
    ("Warranty pitch on the home page", ('wb_title', 'wb_sub', 'wb_years', 'wb_years_label', 'wb_seal', 'wb_cta', 'wb_cta2')),
    ("Branches", ('branches_title', 'branch_page_title', 'all_branches_link', 'hours_label', 'branch_wa', 'directions', 'map_shot', 'pickup_title', 'pickup_cta', 'branch_shot', 'branch_alt', 'main_branch')),
    ("Warranty page", ('warranty_page_title', 'war_check_title', 'war_check_sub', 'war_placeholder', 'war_check_btn', 'war_note', 'war_found', 'war_expired', 'war_void', 'war_none', 'war_none_body', 'war_empty_query', 'covered', 'not_covered_title', 'conditions_title', 'after_sales_title', 'after_sales_body', 'no_maintenance_note')),
    ("Film spec", ('spec_title', 'spec_sub', 'other_services_title')),
    ("About", ('about_title', 'about_lead', 'about_lead2', 'about_values', 'about_numbers', 'about_cta', 'about_shot')),
    ("FAQ", ('faq_title',)),
    ("Blog", ('blog_title', 'blog_page_title', 'blog_page_sub', 'all_blog_link', 'featured', 'search_placeholder', 'all_cats', 'results_one', 'results_many', 'no_results', 'popular', 'by_category', 'tags_title', 'news_title', 'news_body', 'news_placeholder', 'news_cta', 'blog_aside_cta', 'prev', 'next', 'min_read', 'article_shot', 'article_cta', 'article_pending', 'back_to_blog')),
    ("Contact", ('contact_title', 'contact_sub', 'contact_form_title', 'contact_form_sub', 'contact_form_note', 'contact_submit', 'contact_ok_title', 'contact_ok_body', 'contact_bad', 'contact_phones_title', 'required_mark', 'optional_mark', 'choose')),
    ("Footer", ('footer_blurb', 'footer_nav', 'footer_phones', 'footer_hours', 'hours_week', 'hours_fri', 'installments', 'skip_link', 'menu_label', 'final_title', 'final_sub', 'not_found_title', 'not_found_body', 'error_title', 'error_body')),
)


def group_slug(label: str) -> str:
    """A URL-safe id for a group label."""
    out = "".join(ch.lower() if ch.isalnum() else "-" for ch in label)
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")


def copy_group(slug: str) -> tuple[str, tuple[str, ...]] | None:
    for label, keys in COPY_GROUPS:
        if group_slug(label) == slug:
            return label, keys
    return None


def editable_keys(keys: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(k for k in keys if k not in LOCKED_KEYS)


# --------------------------------------------------------------------------
# Collections
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Field:
    """One editable value on a record.

    ``shared`` marks a value that is the same in both languages — an icon
    name, a photograph, a date, a price. Those are edited once; everything
    else is edited twice, Arabic and English side by side.
    """

    name: str
    label: str
    kind: str = "text"          # text | textarea | list | bool | int | url
    shared: bool = False
    hint: str = ""
    required: bool = False
    #: A value the editor may clear to mean "the client has not decided".
    #: Cleared, it stores null and the page prints "to be confirmed".
    pending_when_blank: bool = False


@dataclass(frozen=True)
class Spec:
    """One list in the locale dicts, as the admin presents it."""

    kind: str
    label: str
    section: str
    fields: tuple[Field, ...]
    #: The record's own identifier, or ``None`` for lists keyed by position.
    id_field: str | None = None
    #: Records that may be added and unpublished. False for the fixed
    #: structural lists — the nav has eight entries because the site has eight
    #: pages, and adding a ninth here would not create a page for it.
    open_ended: bool = True
    note: str = ""
    scalar: bool = False        # list[str] rather than list[dict]
    label_field: str | None = None  # what to show in the list view

    def field(self, name: str) -> Field | None:
        for spec in self.fields:
            if spec.name == name:
                return spec
        return None

    def title_of(self, record: dict[str, Any], locale: str = "ar") -> str:
        key = self.label_field or (self.fields[0].name if self.fields else None)
        data = record.get("data", {}).get(locale, {})
        return str(data.get(key) or record.get("slug", ""))


#: Shown under every icon field. Content icons are SVG path data, drawn by the
#: ``icon`` macro; the names below are the set app/content.py ships, and
#: pasting one of those paths is what an editor is meant to do here.
ICON_HINT = ("SVG path data, as shipped for: " + ", ".join(sorted(C.ICONS))
             + ". Copy the path from one of those rather than inventing one.")


def _f(name, label, kind="text", **kw) -> Field:
    return Field(name=name, label=label, kind=kind, **kw)


#: Every list in the locale dicts. The sections are how the sidebar groups
#: them; the order within a section is the order they are listed.
COLLECTIONS: tuple[Spec, ...] = (
    Spec("services", "Services", "services", id_field="slug", label_field="name",
         open_ended=True,
         note="Unpublishing a service removes it from the index and makes its "
              "own page a 404, in both languages.",
         fields=(
             _f("name", "Name", required=True),
             _f("tagline", "Tagline"),
             _f("lede", "Lede", "textarea"),
             _f("points", "Points", "list", hint="One per line."),
             _f("warranty", "Warranty line"),
             _f("icon", "Icon", shared=True, hint=ICON_HINT),
             _f("image", "Photograph", shared=True,
                hint="A stem under static/, without the extension, e.g. "
                     "img/services/ppf-gloss. The build writes the sizes."),
             _f("alt", "Photograph description",
                hint="What the photograph shows, for a screen reader. Written "
                     "per language, since it is read aloud."),
         )),

    Spec("packages", "Packages", "packages", id_field="slug", label_field="name",
         fields=(
             _f("name", "Name", required=True),
             _f("includes", "Includes", "textarea"),
             _f("price", "Price", pending_when_blank=True,
                hint="Clear it to print \u201cto be confirmed\u201d rather than a blank."),
             _f("warranty", "Warranty line"),
             _f("featured", "Most chosen", "bool", shared=True,
                hint="Marks one package on the packages page."),
         )),

    Spec("posts", "Journal", "journal", id_field="slug", label_field="title",
         note="An article with no body still shows the standing notice in "
              "place of one.",
         fields=(
             _f("title", "Title", required=True),
             _f("excerpt", "Excerpt", "textarea"),
             _f("body", "Body", "textarea",
                hint="Blank line between paragraphs. A line starting with "
                     "## is a subheading. No HTML."),
             _f("author", "Author"),
             _f("category", "Category", shared=True,
                hint="A category slug from the list below."),
             _f("date", "Date", shared=True, hint="As it should read, e.g. 2026-03-14."),
             _f("minutes", "Reading minutes", "int", shared=True),
             _f("image", "Image", shared=True,
                hint="A path under static/, e.g. img/blog/my-article.jpg."),
         )),

    Spec("categories", "Journal categories", "journal", id_field="slug",
         label_field="label",
         fields=(_f("label", "Label", required=True),)),

    Spec("tags", "Journal tags", "journal", scalar=True,
         fields=(_f("value", "Tag", required=True),)),

    Spec("warranty_blocks", "Warranty blocks", "warranty", label_field="title",
         fields=(
             _f("title", "Title", required=True),
             _f("icon", "Icon", shared=True, hint=ICON_HINT),
             _f("years", "Years", shared=True),
             _f("years_label", "Years label"),
             _f("covered", "Covered", "list", hint="One per line."),
         )),

    Spec("faq", "FAQ", "warranty", label_field="q",
         fields=(_f("q", "Question", required=True), _f("a", "Answer", "textarea"))),

    Spec("war_rows", "Warranty lookup labels", "warranty", scalar=True,
         open_ended=False,
         note="The four labels on the warranty result. The lookup renders them "
              "in this order.",
         fields=(_f("value", "Label", required=True),)),

    Spec("not_covered", "Not covered", "warranty", scalar=True,
         fields=(_f("value", "Item", required=True),)),

    Spec("conditions", "Conditions", "warranty", scalar=True,
         fields=(_f("value", "Condition", required=True),)),

    Spec("film_spec", "Film specification", "warranty", label_field="k",
         fields=(_f("k", "Property", required=True), _f("v", "Value"))),

    Spec("trust", "Home: trust strip", "pages", label_field="title",
         fields=(
             _f("title", "Title", required=True),
             _f("meta", "Meta"),
             _f("icon", "Icon", shared=True, hint=ICON_HINT),
         )),

    Spec("stack", "Home: protection stack", "pages", id_field="code",
         label_field="a", open_ended=False,
         note="Four layers, tied to the hero illustration. Adding a fifth "
              "here would not draw one.",
         fields=(
             _f("a", "Line one", required=True),
             _f("b", "Line two"),
             _f("body", "Body", "textarea"),
         )),

    Spec("why", "Home: why KMQ", "pages", label_field="title",
         fields=(_f("title", "Title", required=True), _f("body", "Body", "textarea"),
                 _f("icon", "Icon", shared=True, hint=ICON_HINT))),

    Spec("wb_points", "Home: warranty points", "pages", label_field="title",
         fields=(_f("title", "Title", required=True), _f("body", "Body", "textarea"),
                 _f("icon", "Icon", shared=True, hint=ICON_HINT))),

    Spec("addons", "Packages: add-ons", "pages", label_field="text",
         fields=(_f("text", "Text", required=True),
                 _f("icon", "Icon", shared=True, hint=ICON_HINT))),

    Spec("about_value_list", "About: values", "pages", label_field="title",
         fields=(_f("title", "Title", required=True), _f("body", "Body", "textarea"),
                 _f("icon", "Icon", shared=True, hint=ICON_HINT))),

    Spec("about_stats", "About: figures", "pages", label_field="label",
         note="Figures shown as fact. Only put a number here the client has "
              "given you.",
         fields=(_f("value", "Figure", shared=True, required=True),
                 _f("label", "Label"))),

    Spec("nav", "Navigation labels", "site", id_field="key", label_field="label",
         open_ended=False,
         note="One entry per page. The key routes it; only the label is text.",
         fields=(_f("label", "Label", required=True),)),

    Spec("social", "Social links", "site", id_field="name", label_field="name",
         fields=(
             _f("name", "Name", shared=True, required=True),
             _f("icon", "Icon", shared=True),
             _f("url", "URL", "url", shared=True,
                hint="Must start with https://. Clear it to hide the link."),
         )),
)

#: Sidebar sections, in order, with the collections each holds.
SECTIONS: tuple[tuple[str, str], ...] = (
    ("services", "Services"),
    ("packages", "Packages"),
    ("journal", "Journal"),
    ("warranty", "Warranty page"),
    ("pages", "Home & About"),
    ("site", "Site"),
)


def spec(kind: str) -> Spec | None:
    for candidate in COLLECTIONS:
        if candidate.kind == kind:
            return candidate
    return None


def specs_in(section: str) -> tuple[Spec, ...]:
    return tuple(s for s in COLLECTIONS if s.section == section)


def section_label(section: str) -> str:
    for slug, label in SECTIONS:
        if slug == section:
            return label
    return section


# --------------------------------------------------------------------------
# Reading a submitted form
# --------------------------------------------------------------------------
# One parser for every collection, driven by the specs above. The alternative
# — a view per kind — would be twenty near-identical views that drift apart
# the first time a field is added to one of them.

#: How a localised field is named in the form: ``title__ar``. Shared fields
#: keep their plain name.
def field_name(field: "Field", locale: str) -> str:
    return field.name if field.shared else f"{field.name}__{locale}"


def parse_record(spec: "Spec", form, *, slug: str) -> tuple[dict[str, Any], list[str]]:
    """Turn a submitted form into ``{locale: record}``, with any errors.

    Errors are returned rather than raised: a form with three problems should
    show all three at once, next to the fields, rather than one per round
    trip.
    """
    errors: list[str] = []
    records: dict[str, Any] = {}

    for locale in C.LOCALES:
        if spec.scalar:
            value, problem = _read(spec.fields[0], form, locale)
            if problem:
                errors.append(problem)
            records[locale] = value
            continue

        record: dict[str, Any] = {}
        if spec.id_field:
            record[spec.id_field] = slug
        for field in spec.fields:
            value, problem = _read(field, form, locale)
            if problem and problem not in errors:
                errors.append(problem)
            record[field.name] = value
        records[locale] = record

    return records, errors


def _read(field: "Field", form, locale: str) -> tuple[Any, str | None]:
    raw = form.get(field_name(field, locale), "")

    if field.kind == "bool":
        return bool(form.get(field_name(field, locale))), None

    raw = raw.replace("\r\n", "\n").strip()

    if field.kind == "list":
        items = [line.strip() for line in raw.split("\n") if line.strip()]
        if field.required and not items:
            return items, f"{field.label} cannot be empty."
        return items, None

    if field.kind == "int":
        if not raw:
            return None, None
        try:
            return int(raw), None
        except ValueError:
            return None, f"{field.label} must be a whole number."

    if field.kind == "url":
        if not raw:
            return None, None
        if not raw.startswith("https://"):
            return raw, f"{field.label} must start with https://."
        return raw, None

    if not raw:
        if field.required:
            return raw, f"{field.label} is required."
        if field.pending_when_blank:
            # Cleared means "not decided yet", not "blank". The page prints
            # the localised "to be confirmed" for it.
            return C.TBD, None
    return raw, None


def form_value(field: "Field", record: dict[str, Any] | Any, spec: "Spec") -> str:
    """What to put in the input for ``field``, given the stored record."""
    value = record if spec.scalar else (record or {}).get(field.name)

    if value is C.TBD or value is None:
        return ""
    if field.kind == "list":
        return "\n".join(str(item) for item in value)
    if field.kind == "bool":
        return "on" if value else ""
    return str(value)
