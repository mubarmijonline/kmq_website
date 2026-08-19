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
import threading
import time
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

#: Settings that live in site_setting, with the environment variable that
#: overrides each. A deploy must be able to pin a value no admin can change.
SETTINGS = {
    "whatsapp_number": "KMQ_WHATSAPP",
    "show_prices": "KMQ_SHOW_PRICES",
}


def collection_kinds() -> tuple[str, ...]:
    """Every list key in the locale dicts, derived rather than enumerated."""
    return tuple(k for k, v in C.AR.items() if isinstance(v, list))


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
        self._settings: dict[str, str] = {}

    # -- Public -----------------------------------------------------------

    def content(self, locale: str) -> dict[str, Any]:
        """The locale dict with every edit applied."""
        base = C.content(locale)
        self._refresh_if_stale()

        copy = self._copy.get(locale)
        lists = self._lists.get(locale)
        if not copy and not lists:
            return base

        merged = dict(base)
        if copy:
            merged.update(copy)
        if lists:
            merged.update(lists)
        return merged

    def setting(self, name: str, default: Any = None) -> Any:
        self._refresh_if_stale()
        return self._settings.get(name, default)

    def invalidate(self) -> None:
        """Force the next read to rebuild. Called after a write in-process."""
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

        self._copy = copy
        self._lists = lists
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
    counts = {"copy": 0, "entries": 0, "settings": 0}
    conflict = "DO UPDATE SET value = EXCLUDED.value" if force else "DO NOTHING"
    entry_conflict = (
        "DO UPDATE SET data = EXCLUDED.data, sort_order = EXCLUDED.sort_order"
        if force else "DO NOTHING"
    )

    with database.cursor() as conn:
        for locale in C.LOCALES:
            base = C.content(locale)

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

        conn.commit()

    return counts


def bump_version(conn) -> None:
    """Move the counter every worker watches. Call inside a write transaction."""
    conn.execute(
        "UPDATE content_version SET version = version + 1, bumped_at = now()"
    )
