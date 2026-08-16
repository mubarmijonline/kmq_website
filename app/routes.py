"""Routes.

The Word document's sitemap fixes eight pages and their slugs; services and
the journal add a detail route each. Every one of them exists under both
language prefixes.
"""

from __future__ import annotations

from flask import (Blueprint, abort, current_app, g, redirect, render_template,
                   request, url_for)

from . import client_hash
from . import content as C
from .db import Unavailable
from .forms import lead_payload, validate_lead

bp = Blueprint("site", __name__)

#: Articles per page on the journal listing.
PER_PAGE = 6


# --------------------------------------------------------------------------
# Root
# --------------------------------------------------------------------------

@bp.route("/")
def root():
    """Send bare ``/`` to the default locale.

    Arabic, always — not negotiated from Accept-Language. The audience is
    Saudi and the content file leads in Arabic; an English browser locale is
    a weak signal next to that, and a redirect that varies by header is a
    cache key most CDNs get wrong.
    """
    return redirect(url_for("site.home", lang=C.DEFAULT_LOCALE), code=302)


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------

@bp.route("/<locale:lang>/")
def home():
    t = C.content(g.locale)
    return render_template(
        "home.html",
        page="home",
        packages=C.home_packages(g.locale),
        posts=t["posts"][:3],
    )


@bp.route("/<locale:lang>/about-us")
def about():
    return render_template("about.html", page="about")


@bp.route("/<locale:lang>/services")
def services():
    return render_template("services.html", page="services")


@bp.route("/<locale:lang>/services/<slug>")
def service(slug: str):
    record = C.service(g.locale, slug)
    if record is None:
        abort(404)
    others = [s for s in C.content(g.locale)["services"] if s["slug"] != slug]
    package = C.package(g.locale, slug if slug in C.PACKAGE_SLUGS else "gloss")
    return render_template(
        "service.html", page="services", service=record, others=others,
        package=package,
    )


@bp.route("/<locale:lang>/packages")
def packages():
    t = C.content(g.locale)
    return render_template("packages.html", page="packages", packages=t["packages"])


@bp.route("/<locale:lang>/branches")
def branches():
    return render_template("branches.html", page="branches")


# --------------------------------------------------------------------------
# Warranty
# --------------------------------------------------------------------------

@bp.route("/<locale:lang>/warranty", methods=["GET", "POST"])
def warranty():
    """The warranty page, and the lookup it hosts.

    A POST so the query never lands in a URL, a log line or a referrer
    header — a plate number is not something to leak into an access log.
    """
    t = C.content(g.locale)
    result = None
    state = None
    query = ""

    if request.method == "POST":
        query = (request.form.get("q") or "").strip()
        if not query:
            state = "empty"
        else:
            database = current_app.extensions["kmq_db"]
            if not database.enabled:
                state = "unavailable"
            else:
                try:
                    found = database.find_warranty(query)
                except Unavailable:
                    state = "unavailable"
                else:
                    if found is None:
                        state = "none"
                    else:
                        state = found.status
                        result = found

    return render_template(
        "warranty.html", page="warranty", result=result, state=state,
        query=query, blocks=t["warranty_blocks"],
    )


# --------------------------------------------------------------------------
# Journal
# --------------------------------------------------------------------------

@bp.route("/<locale:lang>/blog")
def blog():
    """Listing, with category filter, search and pagination in the URL.

    All three are query parameters rather than client state, so the filtered
    view is shareable, crawlable, and works before app.js loads.
    """
    t = C.content(g.locale)
    posts = t["posts"]

    category = (request.args.get("cat") or "").strip()
    if category and category not in C.CATEGORY_SLUGS:
        category = ""

    query = (request.args.get("q") or "").strip()

    matched = [
        p for p in posts
        if (not category or p["category"] == category)
        and (not query or query.lower() in (p["title"] + " " + p["excerpt"]).lower())
    ]

    pages = max(1, -(-len(matched) // PER_PAGE))
    try:
        page_no = int(request.args.get("page", 1))
    except ValueError:
        page_no = 1
    page_no = min(max(page_no, 1), pages)
    visible = matched[(page_no - 1) * PER_PAGE: page_no * PER_PAGE]

    counts = {c["slug"]: sum(1 for p in posts if p["category"] == c["slug"])
              for c in t["categories"]}

    return render_template(
        "blog.html", page="blog",
        posts=visible, featured=posts[0], matched=len(matched),
        category=category, query=query, page_no=page_no, pages=pages,
        counts=counts, popular=posts[:4],
    )


@bp.route("/<locale:lang>/blog/<slug>")
def article(slug: str):
    record = C.post(g.locale, slug)
    if record is None:
        abort(404)
    t = C.content(g.locale)
    related = [p for p in t["posts"]
               if p["category"] == record["category"] and p["slug"] != slug][:3]
    return render_template("article.html", page="blog", post=record, related=related)


# --------------------------------------------------------------------------
# Contact
# --------------------------------------------------------------------------

@bp.route("/<locale:lang>/contact-us", methods=["GET", "POST"])
def contact():
    form = None
    sent = False

    if request.method == "POST":
        # Honeypot. A real visitor never fills a field they cannot see.
        # Answer 200 with the success page so a bot learns nothing.
        if (request.form.get("company") or "").strip():
            return render_template("contact.html", page="contact", form=None, sent=True)

        form = validate_lead(request.form.to_dict(), g.locale)

        if form.ok:
            database = current_app.extensions["kmq_db"]
            ip_hash = client_hash(current_app)

            if not database.enabled:
                form.errors["__all__"] = "unavailable"
            elif database.recent_lead_count(ip_hash) >= 3:
                form.errors["__all__"] = "throttled"
            else:
                try:
                    database.insert_lead(lead_payload(
                        form, ip_hash=ip_hash,
                        user_agent=request.headers.get("User-Agent", ""),
                    ))
                except Unavailable:
                    form.errors["__all__"] = "unavailable"
                else:
                    sent = True
                    form = None

    return render_template("contact.html", page="contact", form=form, sent=sent)


# --------------------------------------------------------------------------
# Errors
# --------------------------------------------------------------------------

def register_errors(app) -> None:
    @app.errorhandler(404)
    def _not_found(_err):
        return render_template("error.html", page=None, code=404), 404

    @app.errorhandler(500)
    def _server_error(_err):
        return render_template("error.html", page=None, code=500), 500
