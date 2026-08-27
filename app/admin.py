"""The admin: everything the public site renders, editable by staff.

Mounted at ``/admin``, outside the ``<locale>`` prefix. That is on purpose —
this is one interface for the team, not a bilingual public page, so it is in
English throughout and edits both languages side by side.

The guard is a ``before_request`` hook rather than a decorator per view. A
decorator is opt-in, and the failure mode of forgetting one is an unprotected
page; here every endpoint in the blueprint is refused by default and the two
that are reachable signed out are named in :data:`ANONYMOUS`.
"""

from __future__ import annotations

import logging

from flask import (Blueprint, abort, current_app, flash, redirect,
                   render_template, request, session, url_for)

from . import audit, auth
from . import content as C
from . import editors, leads, store
from .text import normalise_saudi_phone

log = logging.getLogger(__name__)

bp = Blueprint("admin", __name__, url_prefix="/admin")

#: Reachable without a session. Everything else in the blueprint redirects to
#: the sign-in page, POSTs included.
ANONYMOUS = {"admin.login"}

#: Endpoints an editor may not reach. Anything absent needs ``editor``.
OWNER_ONLY = {"admin.settings", "admin.users", "admin.audit_trail"}

#: Reachable while an account still owes a password change. Everything else
#: waits until it has been changed.
PENDING_PASSWORD = {"admin.password", "admin.logout", "admin.login"}

#: What the sign-in page says. Deliberately the same wording for a wrong
#: address and a wrong password: telling someone which half they got right is
#: an account-enumeration oracle.
DENIALS = {
    "bad_credentials": "That email and password do not match an account.",
    "disabled": "That email and password do not match an account.",
    "throttled": "Too many failed attempts from this connection. "
                 "Wait fifteen minutes and try again.",
    "wrong_password": "Your current password is not correct.",
    "no_account": "That account no longer exists.",
}


def _db():
    return current_app.extensions["kmq_db"]


def _client_hash() -> str:
    from . import client_hash

    return client_hash(current_app)


def _record(action: str, entity: str, **fields) -> None:
    """Write one audit row outside a content transaction.

    Sign-ins and sign-outs change no content, so they neither need nor want
    :func:`store.writing` and its version bump.
    """
    try:
        with _db().cursor() as conn:
            audit.record(conn, actor=auth.current_user(), action=action,
                         entity=entity, **fields)
            conn.commit()
    except Exception:
        log.exception("Could not write an audit row for %s %s.", action, entity)


def _safe_next(target: str | None) -> str:
    """Only ever redirect back into the admin.

    ``next`` arrives in a query string and is therefore attacker-controlled;
    anything that is not a path under /admin is discarded rather than
    sanitised.
    """
    if not target or not target.startswith("/admin"):
        return url_for("admin.dashboard")
    if target.startswith("//") or "\\" in target:
        return url_for("admin.dashboard")
    return target


# --------------------------------------------------------------------------
# The guard
# --------------------------------------------------------------------------

@bp.before_request
def _guard():
    endpoint = request.endpoint or ""

    # The admin is the one part of the site that genuinely needs Postgres:
    # there is nothing to edit and nobody to authenticate without it. Say so
    # in 503 rather than raising, because the public pages are still fine.
    if not _db().enabled:
        return render_template("admin/unavailable.html"), 503

    if request.method == "POST":
        auth.check_csrf()

    if endpoint in ANONYMOUS:
        return None

    refusal = auth.require("owner" if endpoint in OWNER_ONLY else "editor")
    if refusal is not None:
        return refusal

    user = auth.current_user()
    if user and user["must_change_password"] and endpoint not in PENDING_PASSWORD:
        return redirect(url_for("admin.password"))
    return None


@bp.context_processor
def _inject():
    user = auth.current_user()
    return {
        "admin_user": user,
        # The sidebar badge. Counted per request rather than cached: an
        # enquiry that arrived a second ago is exactly the one staff are
        # waiting for, and the count is one indexed scan of unhandled rows.
        "waiting_leads": leads.waiting_count(_db()) if user else 0,
        "csrf_token": auth.csrf_token,
        "is_owner": auth.outranks(auth.current_user(), "owner"),
        "admin_nav": NAV,
        "here": _here,
        "locales": C.LOCALES,
        "editors": editors,
    }


def _here(endpoint: str, args: dict) -> bool:
    """Whether the sidebar entry is the page being shown."""
    if request.endpoint != endpoint:
        return False
    return all(request.view_args.get(key) == value for key, value in args.items())


#: The sections, in the order the sidebar lists them. Sections whose views
#: arrive in a later milestone are absent rather than dead links.
NAV = (
    ("admin.dashboard", "Dashboard", "editor", {}),
    ("admin.copy", "Copy", "editor", {}),
    ("admin.collection", "Services", "editor", {"kind": "services"}),
    ("admin.collection", "Packages", "editor", {"kind": "packages"}),
    ("admin.branches", "Branches", "editor", {}),
    ("admin.collection", "Journal", "editor", {"kind": "posts"}),
    ("admin.collection", "Warranty page", "editor", {"kind": "warranty_blocks"}),
    ("admin.leads_inbox", "Leads", "editor", {}),
    ("admin.lists", "All lists", "editor", {}),
    ("admin.audit_trail", "Audit", "owner", {}),
)


# --------------------------------------------------------------------------
# Sessions
# --------------------------------------------------------------------------

@bp.route("/login", methods=["GET", "POST"])
def login():
    if auth.current_user() is not None and request.method == "GET":
        return redirect(url_for("admin.dashboard"))

    error = None
    email = ""
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        try:
            user = auth.authenticate(_db(), email=email, password=password,
                                     ip_hash=_client_hash())
        except auth.Denied as denied:
            error = DENIALS.get(denied.reason, DENIALS["bad_credentials"])
            log.info("Sign-in refused for %r: %s", email, denied.reason)
        except Exception:
            log.exception("Sign-in failed against the database.")
            error = "The database could not be reached. Try again shortly."
        else:
            auth.sign_in(user)
            _record("login", "session", entity_id=str(user["id"]))
            if user["must_change_password"]:
                return redirect(url_for("admin.password"))
            return redirect(_safe_next(request.args.get("next")))

    return render_template("admin/login.html", error=error, email=email)


@bp.route("/logout", methods=["POST"])
def logout():
    user = auth.current_user()
    if user is not None:
        _record("logout", "session", entity_id=str(user["id"]))
    auth.sign_out()
    session.clear()
    flash("Signed out.", "ok")
    return redirect(url_for("admin.login"))


@bp.route("/password", methods=["GET", "POST"])
def password():
    user = auth.current_user()
    error = None

    if request.method == "POST":
        current = request.form.get("current_password", "")
        first = request.form.get("new_password", "")
        second = request.form.get("confirm_password", "")

        if len(first) < 12:
            error = "Choose a password of at least twelve characters."
        elif first != second:
            error = "The two new passwords do not match."
        elif first == current:
            error = "The new password must differ from the current one."
        else:
            try:
                auth.change_own_password(_db(), user_id=int(user["id"]),
                                         current=current, replacement=first)
            except auth.Denied as denied:
                error = DENIALS.get(denied.reason, DENIALS["wrong_password"])
            except Exception:
                log.exception("Password change failed.")
                error = "The database could not be reached. Try again shortly."
            else:
                # The hash changed but the epoch did not, so this session
                # survives its own password change; every other one would too,
                # which is why a reset — where the point is to evict them —
                # bumps the epoch and this does not.
                _record("password", "account", entity_id=str(user["id"]))
                flash("Password changed.", "ok")
                return redirect(url_for("admin.dashboard"))

    return render_template("admin/password.html", error=error,
                           forced=bool(user and user["must_change_password"]))


# --------------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------------

@bp.route("/")
def dashboard():
    try:
        waiting = leads.recent(_db(), limit=5, waiting_only=True)
    except Exception:
        log.exception("Could not read the enquiries.")
        waiting = []
    return render_template("admin/dashboard.html", recent=_recent_activity(),
                           waiting=waiting)


def _recent_activity(limit: int = 10):
    try:
        return audit.recent(_db(), limit=limit)
    except Exception:
        log.exception("Could not read the audit trail.")
        return []




# --------------------------------------------------------------------------
# Copy
# --------------------------------------------------------------------------

@bp.route("/copy")
def copy():
    """The flat strings, listed by the page that uses them."""
    edited = _diverged_keys()
    groups = [
        {
            "label": label,
            "slug": editors.group_slug(label),
            "count": len(keys),
            "edited": sum(1 for key in keys if key in edited),
        }
        for label, keys in editors.COPY_GROUPS
    ]
    return render_template("admin/copy_index.html", groups=groups)


@bp.route("/copy/<slug>", methods=["GET", "POST"])
def copy_group(slug: str):
    group = editors.copy_group(slug)
    if group is None:
        abort(404)
    label, keys = group
    user = auth.current_user()

    if request.method == "POST":
        changed = _save_copy(keys, user)
        if changed:
            flash(f"Saved {changed} string{'s' if changed != 1 else ''}. "
                  f"The site shows it within five seconds.", "ok")
        else:
            flash("Nothing changed.", "ok")
        return redirect(url_for("admin.copy_group", slug=slug))

    return render_template(
        "admin/copy_group.html", label=label, keys=keys,
        values=store.copy_rows(_db(), keys),
        shipped={key: {loc: C.shipped(loc).get(key, "") for loc in C.LOCALES}
                 for key in keys},
        locked=editors.LOCKED_KEYS,
    )


def _save_copy(keys, user) -> int:
    """Write the strings that actually changed, and audit each one."""
    current = store.copy_rows(_db(), keys)
    changed = 0
    with store.writing(_db()) as conn:
        for key in keys:
            if key in editors.LOCKED_KEYS:
                continue
            for locale in C.LOCALES:
                submitted = request.form.get(f"{key}__{locale}")
                if submitted is None:
                    continue
                submitted = submitted.replace("\r\n", "\n").strip()
                was = current[key][locale]
                if submitted == was:
                    continue
                shipped = C.shipped(locale).get(key, "")
                if submitted == shipped:
                    # Back to what the repository ships: delete the row rather
                    # than store a copy of it. That is the revert.
                    store.revert_copy(conn, locale=locale, key=key)
                else:
                    store.set_copy(conn, locale=locale, key=key,
                                   value=submitted, actor_id=user["id"])
                audit.record(conn, actor=user, action="update", entity="copy",
                             entity_id=f"{locale}:{key}", before=was,
                             after=submitted)
                changed += 1
    return changed


def _diverged_keys() -> set[str]:
    """Keys whose stored value differs from what the repository ships.

    Seeding writes a row for every key, so "has a row" would mean "all of
    them". What an editor wants to see is which strings have been changed.
    """
    try:
        with _db().cursor() as conn:
            rows = conn.execute(
                "SELECT locale, key, value FROM copy_string"
            ).fetchall()
    except Exception:
        log.exception("Could not read the copy store.")
        return set()
    return {row["key"] for row in rows
            if row["value"] != C.shipped(row["locale"]).get(row["key"], "")}


# --------------------------------------------------------------------------
# Collections
# --------------------------------------------------------------------------

@bp.route("/lists")
def lists():
    """Every list the site renders, grouped the way the sidebar groups them."""
    sections = [
        (label, editors.specs_in(slug))
        for slug, label in editors.SECTIONS
    ]
    return render_template("admin/lists.html", sections=sections)


@bp.route("/lists/<kind>")
def collection(kind: str):
    spec = editors.spec(kind)
    if spec is None:
        abort(404)
    try:
        records = store.entries(_db(), kind)
    except Exception:
        log.exception("Could not read the %s collection.", kind)
        flash("That list could not be read.", "bad")
        records = []
    return render_template("admin/collection.html", spec=spec, records=records)


@bp.route("/lists/<kind>/new", methods=["GET", "POST"])
@bp.route("/lists/<kind>/<slug>", methods=["GET", "POST"])
def record(kind: str, slug: str | None = None):
    spec = editors.spec(kind)
    if spec is None:
        abort(404)

    existing = store.entry(_db(), kind, slug) if slug else None
    if slug and existing is None:
        abort(404)
    if slug is None and not spec.open_ended:
        # Fixed lists — the nav, the four stack layers — are as long as the
        # site is; adding a row here would not create the thing it names.
        abort(404)

    errors: list[str] = []
    values = _record_values(spec, existing)

    if request.method == "POST":
        new_slug = slug or _new_slug(spec, request.form.get("slug", ""))
        if not new_slug:
            errors.append("An identifier is required, in lower case with "
                          "hyphens: my-new-article.")
        records, problems = editors.parse_record(spec, request.form,
                                                 slug=new_slug or "")
        errors += problems
        values = {locale: records[locale] for locale in C.LOCALES}

        if not errors:
            _save_record(spec, new_slug, records, existing)
            flash("Saved. The site shows it within five seconds.", "ok")
            return redirect(url_for("admin.collection", kind=kind))

    return render_template("admin/record.html", spec=spec, record=existing,
                           slug=slug, values=values, errors=errors)


def _record_values(spec, existing):
    """What the form shows: the stored record, or empty fields for a new one."""
    if existing is None:
        return {locale: ({} if not spec.scalar else "") for locale in C.LOCALES}
    out = {}
    for locale in C.LOCALES:
        data = existing["data"].get(locale, {})
        out[locale] = data.get("value", "") if spec.scalar else data
    return out


def _new_slug(spec, submitted: str) -> str:
    """The identifier for a record being created.

    Positional lists get the next free ordinal; everything else gets the slug
    the editor typed, reduced to what a URL can carry.
    """
    if spec.id_field is None or spec.scalar:
        rows = store.entries(_db(), spec.kind)
        ordinals = [int(r["slug"]) for r in rows if r["slug"].isdigit()]
        return str(max(ordinals) + 1 if ordinals else 0)

    cleaned = "".join(ch if ch.isalnum() else "-" for ch in submitted.strip().lower())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-")


def _save_record(spec, slug: str, records, existing) -> None:
    user = auth.current_user()
    with store.writing(_db()) as conn:
        for locale in C.LOCALES:
            payload = ({"value": records[locale]} if spec.scalar
                       else records[locale])
            store.set_entry(conn, kind=spec.kind, slug=slug, locale=locale,
                            data=payload, actor_id=user["id"])
        audit.record(conn, actor=user,
                     action="update" if existing else "create",
                     entity=spec.kind, entity_id=slug,
                     before=(existing or {}).get("data"),
                     after=records)


@bp.route("/lists/<kind>/<slug>/publish", methods=["POST"])
def publish(kind: str, slug: str):
    spec = editors.spec(kind)
    if spec is None:
        abort(404)
    published = request.form.get("published") == "1"
    user = auth.current_user()

    with store.writing(_db()) as conn:
        store.set_published(conn, kind=kind, slug=slug, published=published,
                            actor_id=user["id"])
        audit.record(conn, actor=user,
                     action="publish" if published else "unpublish",
                     entity=kind, entity_id=slug)

    flash("Published." if published else
          "Unpublished. It is gone from the site in both languages.", "ok")
    return redirect(url_for("admin.collection", kind=kind))


@bp.route("/lists/<kind>/order", methods=["POST"])
def reorder(kind: str):
    spec = editors.spec(kind)
    if spec is None:
        abort(404)

    slugs = [row["slug"] for row in store.entries(_db(), kind)]
    slug = request.form.get("slug", "")
    step = -1 if request.form.get("direction") == "up" else 1
    if slug in slugs:
        position = slugs.index(slug)
        target = position + step
        if 0 <= target < len(slugs):
            slugs[position], slugs[target] = slugs[target], slugs[position]
            user = auth.current_user()
            with store.writing(_db()) as conn:
                store.reorder(conn, kind=kind, slugs=slugs, actor_id=user["id"])
                audit.record(conn, actor=user, action="reorder", entity=kind,
                             entity_id=slug, after=slugs)

    return redirect(url_for("admin.collection", kind=kind))


# --------------------------------------------------------------------------
# Leads
# --------------------------------------------------------------------------

@bp.route("/leads")
def leads_inbox():
    """The enquiry inbox. Waiting first by default, since that is the job."""
    waiting_only = request.args.get("show", "waiting") != "all"
    try:
        rows = leads.recent(_db(), waiting_only=waiting_only)
    except Exception:
        log.exception("Could not read the enquiries.")
        flash("The enquiries could not be read.", "bad")
        rows = []
    return render_template("admin/leads.html", rows=rows,
                           waiting_only=waiting_only)


@bp.route("/leads/<int:lead_id>/handled", methods=["POST"])
def lead_handled(lead_id: int):
    handled = request.form.get("handled") == "1"
    try:
        found = leads.set_handled(_db(), lead_id, handled=handled,
                                  actor=auth.current_user())
    except Exception:
        log.exception("Could not update enquiry %s.", lead_id)
        flash("That enquiry could not be updated.", "bad")
        return redirect(url_for("admin.leads_inbox"))

    if not found:
        abort(404)
    flash("Marked handled." if handled else "Put back in the queue.", "ok")
    return redirect(_safe_next(request.form.get("next")))


# --------------------------------------------------------------------------
# Branches
# --------------------------------------------------------------------------

@bp.route("/branches")
def branches():
    try:
        rows = store.branches(_db())
    except Exception:
        log.exception("Could not read the branches.")
        flash("The branches could not be read.", "bad")
        rows = []
    return render_template("admin/branches.html", rows=rows)


@bp.route("/branches/<bid>", methods=["GET", "POST"])
def branch(bid: str):
    row = store.branch(_db(), bid)
    if row is None:
        abort(404)

    errors: list[str] = []
    values = dict(row)

    if request.method == "POST":
        values, errors = _branch_form()
        if not errors:
            user = auth.current_user()
            with store.writing(_db()) as conn:
                before = store.set_branch(conn, bid=bid, values=values,
                                          actor_id=user["id"])
                audit.record(conn, actor=user, action="update", entity="branch",
                             entity_id=bid, before=before, after=values)
            flash("Saved. The site shows it within five seconds.", "ok")
            return redirect(url_for("admin.branches"))
        values = {**row, **values}

    return render_template("admin/branch.html", row=row, values=values,
                           errors=errors)


#: The branch form, field by field. Phone numbers are normalised here so that
#: what the database stores is E.164 whatever the editor typed; the CHECK
#: constraint is still there behind it, because the back office writes this
#: table too.
_BRANCH_TEXT = ("city", "city_ar", "name_ar", "name_en", "location_ar",
                "location_en", "short_ar", "short_en", "hours_ar", "hours_en")


def _branch_form() -> tuple[dict, list[str]]:
    values: dict = {}
    errors: list[str] = []

    for name in _BRANCH_TEXT:
        raw = request.form.get(name, "").strip()
        values[name] = raw or None

    for name, label in (("phone_e164", "Phone"), ("whatsapp_e164", "WhatsApp")):
        raw = request.form.get(name, "").strip()
        if not raw:
            # Cleared means the client has not confirmed one, and the page
            # goes back to printing "to be confirmed".
            values[name] = None
            continue
        normalised = normalise_saudi_phone(raw)
        if normalised is None:
            errors.append(f"{label} must be a Saudi mobile number, "
                          f"e.g. 0512345678.")
            values[name] = raw
        else:
            values[name] = normalised

    map_url = request.form.get("map_url", "").strip()
    if map_url and not map_url.startswith("https://"):
        errors.append("The map link must start with https://.")
    values["map_url"] = map_url or None

    values["is_published"] = request.form.get("is_published") == "1"

    for required in ("city", "name_ar", "name_en", "location_ar", "location_en"):
        if not values.get(required):
            errors.append("City, name and location are required in both "
                          "languages.")
            break

    return values, errors


# --------------------------------------------------------------------------
# Audit
# --------------------------------------------------------------------------

@bp.route("/audit")
def audit_trail():
    """Owner-only. Who changed what, newest first.

    Read-only by design: an audit trail an admin can edit is not one.
    """
    entity = request.args.get("entity") or None
    action = request.args.get("action") or None
    try:
        rows = audit.recent(_db(), limit=200, entity=entity, action=action)
        known = audit.entities(_db())
    except Exception:
        log.exception("Could not read the audit trail.")
        flash("The audit trail could not be read.", "bad")
        rows, known = [], []

    return render_template("admin/audit.html", rows=rows, entities=known,
                           actions=audit.ACTIONS, entity=entity, action=action)


# --------------------------------------------------------------------------
# Errors
# --------------------------------------------------------------------------

@bp.app_errorhandler(403)
def _forbidden(_err):
    if request.path.startswith("/admin"):
        return render_template("admin/forbidden.html"), 403
    return render_template("error.html", code=403), 403
