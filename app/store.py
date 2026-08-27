"""The editable-content store.

`content.py` holds the copy the site shipped with. This module holds whatever
an editor has since changed, and layers the two:

    template → content.py accessor → overlay (here) → database
                                                    ↘ shipped dicts

The shipped dicts are the fallback and stay authoritative when the database is
unreachable. That is not a nicety: `db.py` deliberately opens its pool with
``open=False`` so a Postgres outage never stops the site serving its pages, and
making content a hard database dependency would have thrown that away. With the
overlay, an outage means edits stop applying — not that the site stops.

Two shapes are stored:

* **copy strings** — the 142 scalar values in each locale dict, as
  ``(locale, key) → value``.
* **collections** — the 20 lists, as ``content_entry`` rows carrying the record
  dict as jsonb. ``kind`` is the key the list lives under in the locale dict.

Reads go through a short-lived cache keyed on a database-side version counter,
so an edit made in one gunicorn worker reaches the other without a restart.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from contextlib import contextmanager
from typing import Any

from . import content as C

log = logging.getLogger(__name__)

#: How long a worker may serve its overlay before re-checking the version
#: counter. The upper bound on how stale a just-saved edit can look.
CACHE_TTL_SECONDS = 5.0

#: Lists in the locale dicts whose rows carry a natural identifier. Anything
#: else is keyed by its ordinal, which is stable because these are fixed
#: editorial lists whose order is the content, not an accident.
NATURAL_KEYS = {
    "services": "slug",
    "packages": "slug",
    "posts": "slug",
    "categories": "slug",
    "branches": "id",
    "nav": "key",
    "social": "name",
    "film_spec": "k",
    "stack": "code",
}

#: Scalar lists — list[str] rather than list[dict]. Stored as {"value": ...}.
SCALAR_KINDS = ("war_rows", "not_covered", "conditions", "tags")

#: The one collection that is not a document. A branch carries an E.164 check
#: on two columns, an HTTPS check on a third, and a foreign key from every lead
#: and every warranty; those constraints are why the table exists. So the
#: branch list is read out of `branch` rather than out of content_entry, and
#: seeding fills the table's display columns instead of writing documents.
BRANCH_KIND = "branches"

#: How a branch row becomes the dict the templates already expect, per locale.
#: ``city_en`` is not a column: it is ``city`` upper-cased, which is what the
#: copy file spells out for all six branches.
_BRANCH_COLUMNS = {
    "ar": {"name": "name_ar", "city": "city_ar", "location": "location_ar",
           "short": "short_ar", "hours": "hours_ar"},
    "en": {"name": "name_en", "city": "city", "location": "location_en",
           "short": "short_en", "hours": "hours_en"},
}

#: Shared by both locales: a phone number is a phone number.
_BRANCH_SHARED = {"phone": "phone_e164", "whatsapp": "whatsapp_e164",
                  "map_url": "map_url"}

#: Settings that live in site_setting, with the environment variable that
#: overrides each. A deploy must be able to pin a value no admin can change.
SETTINGS = {
    "whatsapp_number": "KMQ_WHATSAPP",
    "show_prices": "KMQ_SHOW_PRICES",
}


def collection_kinds() -> tuple[str, ...]:
    """Every list key in the locale dicts that is stored as a document.

    Derived rather than enumerated, less :data:`BRANCH_KIND`, which lives in
    its own table.
    """
    return tuple(k for k, v in C.AR.items()
                 if isinstance(v, list) and k != BRANCH_KIND)


def copy_keys() -> tuple[str, ...]:
    """Every scalar string key in the locale dicts."""
    return tuple(k for k, v in C.AR.items() if isinstance(v, str))


def entry_slug(kind: str, index: int, row: Any) -> str:
    """The stable identifier for one record of ``kind``."""
    key = NATURAL_KEYS.get(kind)
    if key and isinstance(row, dict) and row.get(key):
        return str(row[key])
    return str(index)


# --------------------------------------------------------------------------
# The overlay
# --------------------------------------------------------------------------

class Overlay:
    """A cached snapshot of everything an editor has changed.

    Held per worker process. Rebuilt when the database's ``content_version``
    moves, checked at most once per ``CACHE_TTL_SECONDS``.
    """

    def __init__(self, database) -> None:
        self._db = database
        self._lock = threading.Lock()
        self._checked_at = 0.0
        self._version: int | None = None
        # locale -> {key: value}
        self._copy: dict[str, dict[str, str]] = {}
        # locale -> {kind: [row, ...]}
        self._lists: dict[str, dict[str, list[Any]]] = {}
        # locale -> the shipped dict with both of the above merged over it
        self._merged: dict[str, dict[str, Any]] = {}
        self._settings: dict[str, str] = {}

    # -- Public -----------------------------------------------------------

    def content(self, locale: str) -> dict[str, Any]:
        """The locale dict with every edit applied.

        Merged once per rebuild rather than once per call: this runs several
        times a request, and a request that changes nothing should cost a
        dictionary lookup.
        """
        self._refresh_if_stale()
        return self._merged.get(locale) or C.shipped(locale)

    def setting(self, name: str, default: Any = None) -> Any:
        self._refresh_if_stale()
        return self._settings.get(name, default)

    def invalidate(self) -> None:
        """Force the next read to rebuild. Called after a write in-process.

        The snapshot itself is left in place, so a rebuild that fails against
        an unreachable database keeps serving the last good copy instead of
        falling back to the shipped one mid-edit.
        """
        with self._lock:
            self._checked_at = 0.0
            self._version = None

    # -- Internals --------------------------------------------------------

    def _refresh_if_stale(self) -> None:
        now = time.monotonic()
        if now - self._checked_at < CACHE_TTL_SECONDS:
            return
        with self._lock:
            # Another thread may have refreshed while we waited for the lock.
            if time.monotonic() - self._checked_at < CACHE_TTL_SECONDS:
                return
            self._checked_at = time.monotonic()
            try:
                version = self._read_version()
            except Exception:
                # An unreachable database means the shipped copy stands. Log
                # once per TTL rather than per request, and carry on.
                log.warning("Content overlay could not read its version; "
                            "serving the copy shipped in the repository.")
                return
            if version == self._version:
                return
            try:
                self._rebuild()
            except Exception:
                log.exception("Content overlay rebuild failed; keeping the "
                              "previous snapshot.")
                return
            self._version = version

    def _read_version(self) -> int:
        if not self._db.enabled:
            raise RuntimeError("database disabled")
        with self._db.cursor() as conn:
            row = conn.execute("SELECT version FROM content_version").fetchone()
        return int(row["version"]) if row else 0

    def _rebuild(self) -> None:
        copy: dict[str, dict[str, str]] = {loc: {} for loc in C.LOCALES}
        raw: dict[str, dict[str, list[tuple[int, Any]]]] = {loc: {} for loc in C.LOCALES}
        settings: dict[str, str] = {}

        with self._db.cursor() as conn:
            for row in conn.execute(
                "SELECT locale, key, value FROM copy_string"
            ).fetchall():
                if row["locale"] in copy:
                    copy[row["locale"]][row["key"]] = row["value"]

            for row in conn.execute(
                """
                SELECT kind, locale, sort_order, data
                  FROM content_entry
                 WHERE is_published
                 ORDER BY kind, sort_order, slug
                """
            ).fetchall():
                if row["locale"] not in raw:
                    continue
                raw[row["locale"]].setdefault(row["kind"], []).append(
                    (row["sort_order"], row["data"])
                )

            for row in conn.execute("SELECT key, value FROM site_setting").fetchall():
                settings[row["key"]] = row["value"]

            branch_rows = conn.execute(
                """
                SELECT id, city, city_ar, sort_order, name_ar, name_en,
                       location_ar, location_en, short_ar, short_en,
                       phone_e164, whatsapp_e164, hours_ar, hours_en, map_url
                  FROM branch
                 WHERE is_published
                 ORDER BY sort_order, id
                """
            ).fetchall()

        lists: dict[str, dict[str, list[Any]]] = {}
        for locale, kinds in raw.items():
            out: dict[str, list[Any]] = {}
            for kind, rows in kinds.items():
                rows.sort(key=lambda pair: pair[0])
                if kind in SCALAR_KINDS:
                    out[kind] = [r[1].get("value", "") for r in rows]
                else:
                    out[kind] = [_revive(r[1]) for r in rows]
            lists[locale] = out

        for locale in C.LOCALES:
            branches = [_branch_dict(row, locale) for row in branch_rows]
            if branches:
                lists.setdefault(locale, {})[BRANCH_KIND] = branches

        merged: dict[str, dict[str, Any]] = {}
        for locale in C.LOCALES:
            snapshot = dict(C.shipped(locale))
            snapshot.update(copy.get(locale, {}))
            snapshot.update(lists.get(locale, {}))
            merged[locale] = snapshot

        self._copy = copy
        self._lists = lists
        self._merged = merged
        self._settings = settings


def _revive(data: dict[str, Any]) -> dict[str, Any]:
    """Turn a stored record back into what the templates expect.

    Only one value needs it: a pending price is the ``TBD`` sentinel in Python
    and templates test identity against it, but jsonb has no way to carry a
    Python singleton. It is stored as null and restored here.
    """
    row = dict(data)
    for key in ("price", "phone", "hours", "map_url"):
        if key in row and row[key] is None:
            row[key] = C.TBD
    return row


def _branch_dict(row: dict[str, Any], locale: str) -> dict[str, Any]:
    """One branch row as the dict the templates already read.

    The shipped branch of the same id is the base, so a column nobody has
    filled shows the copy the site was deployed with rather than a blank —
    the same fallback a copy string gets. A column that is null where the
    shipped copy has nothing either resolves to ``TBD``, which is what prints
    "to be confirmed".
    """
    base = dict(_shipped_branch(locale, row["id"]))
    base["id"] = row["id"]
    base["city_en"] = (row["city"] or "").upper() or base.get("city_en", "")

    for key, column in _BRANCH_COLUMNS[locale].items():
        if row.get(column):
            base[key] = row[column]
    for key, column in _BRANCH_SHARED.items():
        base[key] = row[column] if row.get(column) else C.TBD

    base.setdefault("whatsapp", C.TBD)
    return base


def _shipped_branch(locale: str, bid: str) -> dict[str, Any]:
    for row in C.shipped(locale)[BRANCH_KIND]:
        if row["id"] == bid:
            return row
    # A branch the copy file never had. Everything the templates read is
    # present, and anything the columns do not supply prints as pending.
    return {"id": bid, "name": "", "city": "", "location": "", "short": "",
            "city_en": "", "phone": C.TBD, "hours": C.TBD, "map_url": C.TBD}


def _flatten(row: Any) -> Any:
    """The inverse of :func:`_revive`, for writing."""
    if not isinstance(row, dict):
        return row
    out = {}
    for key, value in row.items():
        out[key] = None if value is C.TBD else value
    return out


# --------------------------------------------------------------------------
# Seeding
# --------------------------------------------------------------------------

def seed(database, *, force: bool = False) -> dict[str, int]:
    """Fill the store from the shipped dicts.

    Idempotent. Existing rows are left alone unless ``force``, so re-running
    this after an editor has made changes does not undo them.
    """
    counts = {"copy": 0, "entries": 0, "settings": 0, "branches": 0}
    conflict = "DO UPDATE SET value = EXCLUDED.value" if force else "DO NOTHING"
    entry_conflict = (
        "DO UPDATE SET data = EXCLUDED.data, sort_order = EXCLUDED.sort_order"
        if force else "DO NOTHING"
    )

    with database.cursor() as conn:
        for locale in C.LOCALES:
            base = C.shipped(locale)

            for key in copy_keys():
                result = conn.execute(
                    f"""
                    INSERT INTO copy_string (locale, key, value)
                    VALUES (%(locale)s, %(key)s, %(value)s)
                    ON CONFLICT (locale, key) {conflict}
                    """,
                    {"locale": locale, "key": key, "value": base[key]},
                )
                counts["copy"] += result.rowcount or 0

            for kind in collection_kinds():
                for index, row in enumerate(base[kind]):
                    if kind in SCALAR_KINDS:
                        payload: dict[str, Any] = {"value": row}
                    else:
                        payload = _flatten(row)
                    result = conn.execute(
                        f"""
                        INSERT INTO content_entry
                               (kind, slug, locale, sort_order, data)
                        VALUES (%(kind)s, %(slug)s, %(locale)s, %(sort)s,
                                %(data)s::jsonb)
                        ON CONFLICT (kind, slug, locale) {entry_conflict}
                        """,
                        {
                            "kind": kind,
                            "slug": entry_slug(kind, index, row),
                            "locale": locale,
                            "sort": index,
                            "data": json.dumps(payload, ensure_ascii=False),
                        },
                    )
                    counts["entries"] += result.rowcount or 0

        counts["branches"] = _seed_branches(conn, force=force)

        # Branches were documents until migration 003 moved them into their own
        # table. Anything left in content_entry under that kind is ignored by
        # the overlay; clearing it keeps the store from carrying two answers.
        conn.execute("DELETE FROM content_entry WHERE kind = %s", (BRANCH_KIND,))

        conn.commit()

    return counts


def _seed_branches(conn, *, force: bool) -> int:
    """Fill the branch table's display columns from the shipped copy.

    Only writes columns that are still null, and only touches a row that has
    one — so a second run reports nothing written, and an edited branch keeps
    its edit. ``force`` overwrites them, like the rest of the seed. Rows are
    never created here: a branch is a place with a foreign key pointing at it
    from every lead, and inventing one from a copy file is not the seeder's
    call.
    """
    written = 0
    shipped = {
        locale: {row["id"]: row for row in C.shipped(locale)[BRANCH_KIND]}
        for locale in C.LOCALES
    }

    for row in conn.execute("SELECT id FROM branch").fetchall():
        ar = shipped["ar"].get(row["id"])
        en = shipped["en"].get(row["id"])
        if ar is None or en is None:
            continue

        # The copy file leaves hours pending for every branch, so _text gives
        # None and the column is left out entirely rather than seeded with a
        # blank that would read as "known to be empty".
        values = {
            "city_ar": _text(ar["city"]),
            "short_ar": _text(ar["short"]),
            "short_en": _text(en["short"]),
            "hours_ar": _text(ar["hours"]),
            "hours_en": _text(en["hours"]),
        }
        columns = [name for name, value in values.items() if value is not None]
        if not columns:
            continue

        params = {name: values[name] for name in columns} | {"id": row["id"]}
        assignment = ", ".join(f"{name} = %({name})s" for name in columns)
        unfilled = " OR ".join(f"{name} IS NULL" for name in columns)
        clause = "" if force else f" AND ({unfilled})"

        result = conn.execute(
            f"UPDATE branch SET {assignment} WHERE id = %(id)s{clause}", params
        )
        written += result.rowcount or 0
    return written


def _text(value: Any) -> str | None:
    """A storable string, or ``None`` for the pending sentinel and blanks."""
    if value is C.TBD or value is None:
        return None
    value = str(value).strip()
    return value or None


def bump_version(conn) -> None:
    """Move the counter every worker watches. Call inside a write transaction."""
    conn.execute(
        "UPDATE content_version SET version = version + 1, bumped_at = now()"
    )


# --------------------------------------------------------------------------
# Writing
# --------------------------------------------------------------------------
# Every mutating admin action runs inside :func:`writing`. It bumps
# content_version in the same transaction as the edit, so the two can never
# disagree: an edit that commits is always an edit the other worker will see,
# and an edit that rolls back never moves the counter.

@contextmanager
def writing(database):
    """A transaction that publishes whatever it changed.

    Usage::

        with store.writing(db) as conn:
            before = store.set_copy(conn, locale="ar", key="hero_sub", ...)
            audit.record(conn, actor, "update", "copy", ...)

    The audit row is written on the same connection deliberately — an edit the
    audit log has no record of is worse than no edit at all.
    """
    with database.cursor() as conn:
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        bump_version(conn)
        conn.commit()


def set_copy(conn, *, locale: str, key: str, value: str,
             actor_id: int | None) -> str | None:
    """Store one flat string. Returns the value it replaced, or ``None``."""
    row = conn.execute(
        "SELECT value FROM copy_string WHERE locale = %s AND key = %s",
        (locale, key),
    ).fetchone()
    conn.execute(
        """
        INSERT INTO copy_string (locale, key, value, updated_at, updated_by)
        VALUES (%(locale)s, %(key)s, %(value)s, now(), %(actor)s)
        ON CONFLICT (locale, key) DO UPDATE
           SET value = EXCLUDED.value,
               updated_at = now(),
               updated_by = EXCLUDED.updated_by
        """,
        {"locale": locale, "key": key, "value": value, "actor": actor_id},
    )
    return row["value"] if row else None


def revert_copy(conn, *, locale: str, key: str) -> str | None:
    """Delete a stored string so the shipped copy stands again.

    This is the only rollback the design has, and it is why seeding writes
    every key rather than only the edited ones: with a full seed, reverting is
    a re-seed of one row; without it, it is a deletion.
    """
    row = conn.execute(
        "DELETE FROM copy_string WHERE locale = %s AND key = %s RETURNING value",
        (locale, key),
    ).fetchone()
    return row["value"] if row else None


def set_entry(conn, *, kind: str, slug: str, locale: str, data: dict[str, Any],
              sort_order: int | None = None, is_published: bool | None = None,
              actor_id: int | None) -> dict[str, Any] | None:
    """Store one collection record. Returns the row it replaced.

    ``sort_order`` and ``is_published`` are left as they were when omitted, so
    saving an editor's form does not silently reorder or unpublish a record the
    form never showed.
    """
    before = conn.execute(
        """
        SELECT sort_order, is_published, data
          FROM content_entry
         WHERE kind = %s AND slug = %s AND locale = %s
        """,
        (kind, slug, locale),
    ).fetchone()

    if sort_order is None:
        sort_order = before["sort_order"] if before else _next_sort(conn, kind, locale)
    if is_published is None:
        is_published = before["is_published"] if before else True

    conn.execute(
        """
        INSERT INTO content_entry (kind, slug, locale, sort_order,
                                   is_published, data, updated_at, updated_by)
        VALUES (%(kind)s, %(slug)s, %(locale)s, %(sort)s, %(published)s,
                %(data)s::jsonb, now(), %(actor)s)
        ON CONFLICT (kind, slug, locale) DO UPDATE
           SET sort_order = EXCLUDED.sort_order,
               is_published = EXCLUDED.is_published,
               data = EXCLUDED.data,
               updated_at = now(),
               updated_by = EXCLUDED.updated_by
        """,
        {
            "kind": kind, "slug": slug, "locale": locale, "sort": sort_order,
            "published": is_published,
            "data": json.dumps(_flatten(data), ensure_ascii=False),
            "actor": actor_id,
        },
    )
    return dict(before) if before else None


def set_published(conn, *, kind: str, slug: str, published: bool,
                  actor_id: int | None) -> None:
    """Publish or unpublish a record in *both* locales.

    Publication is a property of the record, not of one of its translations:
    an Arabic service that is live while its English twin is hidden would give
    the language switcher a page to switch to that does not exist.
    """
    conn.execute(
        """
        UPDATE content_entry
           SET is_published = %(published)s, updated_at = now(),
               updated_by = %(actor)s
         WHERE kind = %(kind)s AND slug = %(slug)s
        """,
        {"kind": kind, "slug": slug, "published": published, "actor": actor_id},
    )


def reorder(conn, *, kind: str, slugs: list[str], actor_id: int | None) -> None:
    """Give ``slugs`` positions 0..n-1, in both locales."""
    for position, slug in enumerate(slugs):
        conn.execute(
            """
            UPDATE content_entry
               SET sort_order = %(sort)s, updated_at = now(),
                   updated_by = %(actor)s
             WHERE kind = %(kind)s AND slug = %(slug)s
            """,
            {"kind": kind, "slug": slug, "sort": position, "actor": actor_id},
        )


def set_setting(conn, *, key: str, value: str, actor_id: int | None) -> str | None:
    """Store one site setting. Returns the value it replaced."""
    row = conn.execute(
        "SELECT value FROM site_setting WHERE key = %s", (key,)
    ).fetchone()
    if value == "":
        conn.execute("DELETE FROM site_setting WHERE key = %s", (key,))
    else:
        conn.execute(
            """
            INSERT INTO site_setting (key, value, updated_at, updated_by)
            VALUES (%(key)s, %(value)s, now(), %(actor)s)
            ON CONFLICT (key) DO UPDATE
               SET value = EXCLUDED.value, updated_at = now(),
                   updated_by = EXCLUDED.updated_by
            """,
            {"key": key, "value": value, "actor": actor_id},
        )
    return row["value"] if row else None


def _next_sort(conn, kind: str, locale: str) -> int:
    row = conn.execute(
        """
        SELECT coalesce(max(sort_order) + 1, 0) AS next
          FROM content_entry WHERE kind = %s AND locale = %s
        """,
        (kind, locale),
    ).fetchone()
    return int(row["next"]) if row else 0


# --------------------------------------------------------------------------
# Reading for the editors
# --------------------------------------------------------------------------
# The overlay above serves the public site and therefore hides unpublished
# records. The admin has to see them, so it reads through these instead.

def entries(database, kind: str) -> list[dict[str, Any]]:
    """Every record of ``kind``, both locales, ordered, unpublished included.

    Shaped as one row per slug carrying both translations, because that is how
    the editors present them — Arabic and English side by side, one save.
    """
    with database.cursor() as conn:
        rows = conn.execute(
            """
            SELECT slug, locale, sort_order, is_published, data, updated_at
              FROM content_entry
             WHERE kind = %s
             ORDER BY sort_order, slug
            """,
            (kind,),
        ).fetchall()

    merged: dict[str, dict[str, Any]] = {}
    for row in rows:
        record = merged.setdefault(row["slug"], {
            "slug": row["slug"],
            "sort_order": row["sort_order"],
            "is_published": row["is_published"],
            "updated_at": row["updated_at"],
            "data": {},
        })
        record["data"][row["locale"]] = _revive(row["data"])
        # An unpublished translation unpublishes the record; see set_published.
        record["is_published"] = record["is_published"] and row["is_published"]
    return sorted(merged.values(), key=lambda r: (r["sort_order"], r["slug"]))


def entry(database, kind: str, slug: str) -> dict[str, Any] | None:
    """One record of ``kind`` by slug, both locales, or ``None``."""
    for row in entries(database, kind):
        if row["slug"] == slug:
            return row
    return None


def copy_rows(database, keys: tuple[str, ...] | list[str]) -> dict[str, dict[str, str]]:
    """``{key: {locale: value}}`` for ``keys``, stored values over shipped.

    Falls back key by key rather than wholesale: a string nobody has edited
    shows the editor exactly what the visitor is seeing.
    """
    values: dict[str, dict[str, str]] = {
        key: {loc: C.shipped(loc).get(key, "") for loc in C.LOCALES}
        for key in keys
    }
    if not keys:
        return values
    with database.cursor() as conn:
        rows = conn.execute(
            "SELECT locale, key, value FROM copy_string WHERE key = ANY(%s)",
            (list(keys),),
        ).fetchall()
    for row in rows:
        if row["key"] in values and row["locale"] in C.LOCALES:
            values[row["key"]][row["locale"]] = row["value"]
    return values


def settings(database) -> dict[str, str]:
    """Stored settings, ignoring the environment. For the settings editor."""
    with database.cursor() as conn:
        rows = conn.execute("SELECT key, value FROM site_setting").fetchall()
    return {row["key"]: row["value"] for row in rows}


def pinned_by_environment(name: str) -> bool:
    """Whether a deploy has pinned ``name``, making the admin's copy inert.

    The editor shows this rather than silently accepting an edit that the
    environment will keep overriding.
    """
    variable = SETTINGS.get(name)
    return bool(variable) and os.environ.get(variable) is not None


# --------------------------------------------------------------------------
# Branches
# --------------------------------------------------------------------------
# The typed half of the store. Everything above stores documents; a branch
# stores columns, because the E.164 checks, the HTTPS check and the foreign
# keys from lead and warranty are worth more than uniformity.

#: Columns the branch editor writes. `id` and `created_at` are not among them:
#: an id is referenced by leads and warranties and never changes.
BRANCH_FIELDS = ("city", "city_ar", "name_ar", "name_en", "location_ar",
                 "location_en", "short_ar", "short_en", "phone_e164",
                 "whatsapp_e164", "hours_ar", "hours_en", "map_url",
                 "sort_order", "is_published")


def branches(database) -> list[dict[str, Any]]:
    """Every branch, unpublished included, in display order."""
    with database.cursor() as conn:
        return conn.execute(
            f"""
            SELECT id, created_at, updated_at, {", ".join(BRANCH_FIELDS)}
              FROM branch
             ORDER BY sort_order, id
            """
        ).fetchall()


def branch(database, bid: str) -> dict[str, Any] | None:
    with database.cursor() as conn:
        return conn.execute(
            f"""
            SELECT id, created_at, updated_at, {", ".join(BRANCH_FIELDS)}
              FROM branch WHERE id = %s
            """,
            (bid,),
        ).fetchone()


def set_branch(conn, *, bid: str, values: dict[str, Any],
               actor_id: int | None) -> dict[str, Any] | None:
    """Update one branch. Returns the row as it was, or ``None`` if unknown.

    Only the keys present in ``values`` are written, so a form that shows six
    fields cannot blank the other nine. The database still has the final word
    on the phone numbers and the map link — the checks live there because the
    back office writes this table too.
    """
    before = conn.execute(
        f"SELECT id, {', '.join(BRANCH_FIELDS)} FROM branch WHERE id = %s",
        (bid,),
    ).fetchone()
    if before is None:
        return None

    columns = [name for name in values if name in BRANCH_FIELDS]
    if not columns:
        return dict(before)

    params = {name: values[name] for name in columns} | {"id": bid, "actor": actor_id}
    assignment = ", ".join(f"{name} = %({name})s" for name in columns)
    conn.execute(
        f"""
        UPDATE branch
           SET {assignment}, updated_at = now(), updated_by = %(actor)s
         WHERE id = %(id)s
        """,
        params,
    )
    return dict(before)
