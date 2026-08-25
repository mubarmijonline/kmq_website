"""The content editors: the specs, the parser, and what a save does to a page.

The database half signs in as an owner and edits the development database
through the admin's own forms, then reads the public page back. That is the
only way to assert the milestone's acceptance list, which is written in terms
of what a visitor sees after an editor presses Save.
"""

from __future__ import annotations

import time

from conftest import csrf, needs_db  # noqa: F401 - fixtures come from conftest

from app import audit, editors, store
from app import content as C


def settle() -> None:
    """Wait out the overlay's TTL, the way an editor does."""
    time.sleep(store.CACHE_TTL_SECONDS + 0.4)


def body(client, path: str) -> str:
    response = client.get(path)
    assert response.status_code == 200, path
    return response.data.decode()


# --------------------------------------------------------------------------
# The specs cover the copy file
# --------------------------------------------------------------------------

def test_every_scalar_key_is_in_exactly_one_group():
    scalars = {k for k, v in C.AR.items() if isinstance(v, str)}
    grouped: list[str] = []
    for _label, keys in editors.COPY_GROUPS:
        grouped += list(keys)

    assert sorted(grouped) == sorted(set(grouped)), "a key is in two groups"
    assert set(grouped) == scalars


def test_every_list_has_a_spec_or_a_table():
    lists = {k for k, v in C.AR.items() if isinstance(v, list)}
    specs = {spec.kind for spec in editors.COLLECTIONS}
    # Branches are the one collection stored as typed columns; see
    # db/migrations/003_branch_editable.sql.
    assert specs == lists - {store.BRANCH_KIND}


def test_every_field_a_record_carries_is_declared():
    for spec in editors.COLLECTIONS:
        if spec.scalar:
            continue
        record = C.AR[spec.kind][0]
        declared = {field.name for field in spec.fields} | {spec.id_field}
        # `body` is declared before any record carries one: it is the field the
        # journal editor adds.
        assert set(record) - declared == set(), spec.kind


def test_group_slugs_are_unique():
    slugs = [editors.group_slug(label) for label, _ in editors.COPY_GROUPS]
    assert len(slugs) == len(set(slugs))


# --------------------------------------------------------------------------
# The parser
# --------------------------------------------------------------------------

class _Form(dict):
    """Enough of a Werkzeug MultiDict for the parser."""

    def get(self, key, default=""):
        return dict.get(self, key, default)


def test_a_cleared_price_becomes_the_pending_sentinel():
    spec = editors.spec("packages")
    form = _Form({"name__ar": "أ", "name__en": "A",
                  "price__ar": "", "price__en": ""})
    records, errors = editors.parse_record(spec, form, slug="gloss")
    assert errors == []
    assert records["ar"]["price"] is C.TBD
    assert records["en"]["price"] is C.TBD


def test_a_list_field_is_one_item_per_line():
    spec = editors.spec("services")
    form = _Form({"name__ar": "أ", "name__en": "A",
                  "points__en": "one\r\n\r\n  two  \r\nthree"})
    records, errors = editors.parse_record(spec, form, slug="ppf")
    assert errors == []
    assert records["en"]["points"] == ["one", "two", "three"]


def test_a_required_field_reports_itself():
    spec = editors.spec("services")
    records, errors = editors.parse_record(spec, _Form({}), slug="ppf")
    assert any("required" in error for error in errors)


def test_a_url_must_be_https():
    spec = editors.spec("social")
    form = _Form({"name": "Instagram", "url": "http://example.com"})
    _records, errors = editors.parse_record(spec, form, slug="Instagram")
    assert any("https" in error for error in errors)


def test_minutes_must_be_a_number():
    spec = editors.spec("posts")
    form = _Form({"title__ar": "أ", "title__en": "A", "minutes": "ten"})
    _records, errors = editors.parse_record(spec, form, slug="a-post")
    assert any("whole number" in error for error in errors)


def test_form_value_round_trips_a_list():
    spec = editors.spec("services")
    field = spec.field("points")
    assert editors.form_value(field, {"points": ["a", "b"]}, spec) == "a\nb"
    assert editors.form_value(spec.field("name"), {"name": C.TBD}, spec) == ""


# --------------------------------------------------------------------------
# What a save does to the page
# --------------------------------------------------------------------------

@needs_db
def test_editing_a_string_changes_both_languages(admin_app, owner):
    label, keys = editors.copy_group("home-hero")
    form = {"csrf_token": csrf(owner, "/admin/copy/home-hero")}
    for key in keys:
        for locale in C.LOCALES:
            form[f"{key}__{locale}"] = C.shipped(locale)[key]
    form["hero_sub__ar"] = "نص عربي جديد"
    form["hero_sub__en"] = "A new English subtitle"

    assert owner.post("/admin/copy/home-hero", data=form).status_code == 302
    settle()

    client = admin_app.test_client()
    assert "نص عربي جديد" in body(client, "/ar/")
    assert "A new English subtitle" in body(client, "/en/")


@needs_db
def test_a_string_edited_back_to_the_shipped_copy_stops_being_an_edit(admin_app, owner):
    _label, keys = editors.copy_group("home-hero")

    def submit(value: str) -> None:
        form = {"csrf_token": csrf(owner, "/admin/copy/home-hero")}
        for key in keys:
            for locale in C.LOCALES:
                form[f"{key}__{locale}"] = C.shipped(locale)[key]
        form["hero_sub__en"] = value
        owner.post("/admin/copy/home-hero", data=form)

    submit("Something else")
    submit(C.shipped("en")["hero_sub"])

    with admin_app.extensions["kmq_db"].cursor() as conn:
        row = conn.execute(
            "SELECT count(*) AS n FROM copy_string WHERE locale = 'en' "
            "AND key = 'hero_sub'"
        ).fetchone()
    assert row["n"] == 0


@needs_db
def test_a_cleared_price_renders_as_to_be_confirmed(admin_app, owner):
    database = admin_app.extensions["kmq_db"]
    record = store.entry(database, "packages", "gloss")

    form = {"csrf_token": csrf(owner, "/admin/lists/packages/gloss")}
    for locale in C.LOCALES:
        data = record["data"][locale]
        form[f"name__{locale}"] = data["name"]
        form[f"includes__{locale}"] = data["includes"]
        form[f"warranty__{locale}"] = data["warranty"]
        form[f"price__{locale}"] = ""
    assert owner.post("/admin/lists/packages/gloss", data=form).status_code == 302
    settle()

    stored = store.entry(database, "packages", "gloss")
    assert stored["data"]["en"]["price"] is C.TBD

    page = body(admin_app.test_client(), "/en/packages")
    assert C.shipped("en")["tbd"] in page


@needs_db
def test_unpublishing_a_service_removes_it_from_the_site(admin_app, owner):
    form = {"csrf_token": csrf(owner, "/admin/lists/services"), "published": "0"}
    assert owner.post("/admin/lists/services/ppf-gloss/publish",
                      data=form).status_code == 302
    settle()

    client = admin_app.test_client()
    for locale in C.LOCALES:
        assert client.get(f"/{locale}/services/ppf-gloss").status_code == 404
        assert "/services/ppf-gloss" not in body(client, f"/{locale}/services")


@needs_db
def test_an_article_with_a_body_renders_it(admin_app, owner):
    database = admin_app.extensions["kmq_db"]
    slug = "what-is-self-healing"
    record = store.entry(database, "posts", slug)
    shared = record["data"]["en"]

    form = {"csrf_token": csrf(owner, f"/admin/lists/posts/{slug}"),
            "category": shared["category"], "date": shared["date"],
            "image": shared["image"], "minutes": str(shared["minutes"])}
    for locale in C.LOCALES:
        data = record["data"][locale]
        for field in ("title", "excerpt", "author"):
            form[f"{field}__{locale}"] = data[field]
        form[f"body__{locale}"] = ""
    form["body__en"] = "## Why it heals\n\nHeat closes the scratch.\n\nSo it goes."

    assert owner.post(f"/admin/lists/posts/{slug}", data=form).status_code == 302
    settle()

    client = admin_app.test_client()
    page = body(client, f"/en/blog/{slug}")
    assert "Heat closes the scratch." in page
    assert "<h2" in page and "Why it heals" in page
    assert C.shipped("en")["article_pending"] not in page

    # An article nobody has written a body for still says so.
    other = body(client, "/en/blog/ppf-vs-nano-ceramic")
    assert C.shipped("en")["article_pending"] in other


@needs_db
def test_a_branch_phone_is_normalised_stored_and_cleared(admin_app, owner):
    database = admin_app.extensions["kmq_db"]
    row = store.branch(database, "al-hamra")
    base = {"csrf_token": csrf(owner, "/admin/branches/al-hamra"),
            "city": row["city"], "city_ar": row["city_ar"],
            "name_ar": row["name_ar"], "name_en": row["name_en"],
            "location_ar": row["location_ar"], "location_en": row["location_en"],
            "short_ar": row["short_ar"], "short_en": row["short_en"],
            "hours_ar": "", "hours_en": "", "whatsapp_e164": "",
            "map_url": "", "is_published": "1"}

    # Typed the way a person types it, stored the way E.164 requires.
    assert owner.post("/admin/branches/al-hamra",
                      data=dict(base, phone_e164="٠٥١٢٣٤٥٦٧٨")).status_code == 302
    assert store.branch(database, "al-hamra")["phone_e164"] == "+966512345678"
    settle()
    assert "+966512345678" in body(admin_app.test_client(), "/en/contact-us")

    # Cleared, the page goes back to saying it is not confirmed.
    owner.post("/admin/branches/al-hamra",
               data=dict(base, csrf_token=csrf(owner, "/admin/branches/al-hamra"),
                         phone_e164=""))
    assert store.branch(database, "al-hamra")["phone_e164"] is None
    settle()
    page = body(admin_app.test_client(), "/en/contact-us")
    assert "+966512345678" not in page
    assert C.shipped("en")["tbd"] in page


@needs_db
def test_a_phone_that_is_not_a_saudi_mobile_is_refused(admin_app, owner):
    row = store.branch(admin_app.extensions["kmq_db"], "al-hamra")
    response = owner.post("/admin/branches/al-hamra", data={
        "csrf_token": csrf(owner, "/admin/branches/al-hamra"),
        "city": row["city"], "city_ar": row["city_ar"],
        "name_ar": row["name_ar"], "name_en": row["name_en"],
        "location_ar": row["location_ar"], "location_en": row["location_en"],
        "phone_e164": "12345", "is_published": "1",
    })
    assert response.status_code == 200
    assert "Saudi mobile" in response.data.decode()
    assert store.branch(admin_app.extensions["kmq_db"], "al-hamra")["phone_e164"] is None


@needs_db
def test_a_map_link_must_be_https(admin_app, owner):
    row = store.branch(admin_app.extensions["kmq_db"], "al-hamra")
    response = owner.post("/admin/branches/al-hamra", data={
        "csrf_token": csrf(owner, "/admin/branches/al-hamra"),
        "city": row["city"], "city_ar": row["city_ar"],
        "name_ar": row["name_ar"], "name_en": row["name_en"],
        "location_ar": row["location_ar"], "location_en": row["location_en"],
        "map_url": "http://maps.example.com", "is_published": "1",
    })
    assert "https" in response.data.decode()
    assert store.branch(admin_app.extensions["kmq_db"], "al-hamra")["map_url"] is None


@needs_db
def test_a_new_article_can_be_added_and_reaches_the_blog(admin_app, owner):
    slug = "a-test-article"
    form = {"csrf_token": csrf(owner, "/admin/lists/posts/new"), "slug": slug,
            "category": C.shipped("en")["categories"][0]["slug"],
            "date": "2026-08-19", "image": "img/blog/what-is-self-healing.jpg",
            "minutes": "4"}
    for locale in C.LOCALES:
        form[f"title__{locale}"] = f"Test article ({locale})"
        form[f"excerpt__{locale}"] = "Excerpt."
        form[f"author__{locale}"] = "KMQ"
        form[f"body__{locale}"] = "A paragraph."

    assert owner.post("/admin/lists/posts/new", data=form).status_code == 302
    settle()

    client = admin_app.test_client()
    try:
        # New records go to the end of the list, which is the second page of
        # the blog index; the search the index offers finds it either way.
        assert f"/blog/{slug}" in body(client, "/en/blog?q=Test+article")
        assert "A paragraph." in body(client, f"/en/blog/{slug}")
    finally:
        with admin_app.extensions["kmq_db"].cursor() as conn:
            conn.execute("DELETE FROM content_entry WHERE kind = 'posts' "
                         "AND slug = %s", (slug,))
            conn.commit()


@needs_db
def test_every_save_is_audited(admin_app, owner):
    form = {"csrf_token": csrf(owner, "/admin/lists/services"), "published": "0"}
    owner.post("/admin/lists/services/ppf-gloss/publish", data=form)

    rows = audit.recent(admin_app.extensions["kmq_db"], limit=20)
    latest = rows[0]
    assert latest["action"] == "unpublish"
    assert latest["entity"] == "services"
    assert latest["entity_id"] == "ppf-gloss"
    assert latest["actor_email"].endswith("@kmq.test")


@needs_db
def test_an_editor_may_edit_content(admin_app):
    from conftest import PASSWORD, TEST_SUFFIX, make_account, sign_in  # noqa: F401

    make_account(admin_app, email=f"editor{TEST_SUFFIX}", role="editor")
    client = admin_app.test_client()
    sign_in(client, f"editor{TEST_SUFFIX}")

    assert client.get("/admin/copy").status_code == 200
    assert client.get("/admin/lists/services").status_code == 200
    assert client.get("/admin/branches").status_code == 200
    # ...but not the owner-only sections.
    assert client.get("/admin/audit").status_code == 403


@needs_db
def test_reordering_moves_a_record_and_the_page_follows(admin_app, owner):
    database = admin_app.extensions["kmq_db"]
    before = [row["slug"] for row in store.entries(database, "services")]

    owner.post("/admin/lists/services/order", data={
        "csrf_token": csrf(owner, "/admin/lists/services"),
        "slug": before[1], "direction": "up",
    })

    after = [row["slug"] for row in store.entries(database, "services")]
    assert after[0] == before[1] and after[1] == before[0]

    settle()
    page = body(admin_app.test_client(), "/en/services")
    assert page.index(after[0]) < page.index(after[1])
