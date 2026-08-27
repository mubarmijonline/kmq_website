"""The enquiry inbox: what the contact form wrote, as staff read it.

The public site's half of a lead is one INSERT in :mod:`app.db`, which is
deliberately narrow. This is the other half — the reading, the counting and
the one state a lead has — and it lives apart from ``db.py`` for the same
reason ``audit.py`` does: nothing here may run for a visitor.

A lead is *waiting* until somebody presses "Mark handled". That is what the
sidebar counts, so the number next to Leads means "enquiries nobody has dealt
with yet" rather than "enquiries nobody has looked at" — a count that would
clear itself the moment the page was opened and tell staff nothing.

``handled_at`` and ``handled_by`` are the columns the admin migration added
for exactly this; no new migration was needed.
"""

from __future__ import annotations

import logging
from typing import Any

from . import audit
from . import content as C

log = logging.getLogger(__name__)

#: The admin is in English, so codes are resolved against the English option
#: tables. A code that is no longer offered still has to render: it is what a
#: real visitor chose at the time, and dropping it would lose the enquiry.
_SERVICE_LABELS = dict(C.SERVICE_OPTIONS["en"])
_TIMING_LABELS = dict(C.TIMING_OPTIONS["en"])

#: How many enquiries one page of the inbox shows.
PAGE_SIZE = 50


def waiting_count(database) -> int:
    """Enquiries nobody has marked handled. Served by ``lead_unhandled_idx``.

    Called on every admin page to draw the sidebar badge, so it must never be
    the reason a page fails: a database that has gone away shows no badge
    rather than a 500.
    """
    try:
        with database.cursor() as conn:
            row = conn.execute(
                "SELECT count(*) AS n FROM lead WHERE handled_at IS NULL"
            ).fetchone()
        return int(row["n"])
    except Exception:
        log.exception("Could not count waiting enquiries.")
        return 0


def recent(database, *, limit: int = PAGE_SIZE, waiting_only: bool = False
           ) -> list[dict[str, Any]]:
    """The inbox, newest first, with the branch name and who handled it."""
    where = "WHERE lead.handled_at IS NULL" if waiting_only else ""
    with database.cursor() as conn:
        rows = conn.execute(
            f"""
            SELECT lead.id, lead.created_at, lead.full_name, lead.phone,
                   lead.service, lead.car_model, lead.branch_id, lead.timing,
                   lead.notes, lead.locale, lead.handled_at,
                   branch.name_en   AS branch_name,
                   admin_user.email AS handled_by_email
              FROM lead
              JOIN branch ON branch.id = lead.branch_id
              LEFT JOIN admin_user ON admin_user.id = lead.handled_by
              {where}
             ORDER BY lead.created_at DESC, lead.id DESC
             LIMIT %(limit)s
            """,
            {"limit": max(1, min(limit, 500))},
        ).fetchall()
    return [_labelled(row) for row in rows]


def get(database, lead_id: int) -> dict[str, Any] | None:
    with database.cursor() as conn:
        row = conn.execute(
            """
            SELECT lead.id, lead.created_at, lead.full_name, lead.phone,
                   lead.service, lead.car_model, lead.branch_id, lead.timing,
                   lead.notes, lead.locale, lead.handled_at,
                   branch.name_en   AS branch_name,
                   admin_user.email AS handled_by_email
              FROM lead
              JOIN branch ON branch.id = lead.branch_id
              LEFT JOIN admin_user ON admin_user.id = lead.handled_by
             WHERE lead.id = %(id)s
            """,
            {"id": lead_id},
        ).fetchone()
    return None if row is None else _labelled(row)


def set_handled(database, lead_id: int, *, handled: bool, actor) -> bool:
    """Mark one enquiry handled, or put it back in the queue.

    The audit row is written on the same connection as the update, the way
    every other admin change is, so "who cleared this" is answerable later.
    Returns False when the id is not a lead, which is a 404 rather than an
    error.
    """
    with database.cursor() as conn:
        row = conn.execute(
            """
            UPDATE lead
               SET handled_at = CASE WHEN %(handled)s THEN now() ELSE NULL END,
                   handled_by = CASE WHEN %(handled)s
                                     THEN %(actor)s::bigint ELSE NULL END
             WHERE id = %(id)s
            RETURNING id, full_name
            """,
            {"id": lead_id, "handled": handled,
             "actor": actor.get("id") if actor else None},
        ).fetchone()
        if row is None:
            return False
        audit.record(conn, actor=actor,
                     action="update", entity="lead", entity_id=str(lead_id),
                     before={"handled": not handled},
                     after={"handled": handled, "name": row["full_name"]})
        conn.commit()
    return True


def _labelled(row: dict[str, Any]) -> dict[str, Any]:
    """Codes as staff read them, and the phone as a link they can press."""
    out = dict(row)
    out["service_label"] = _SERVICE_LABELS.get(row["service"], row["service"])
    out["timing_label"] = _TIMING_LABELS.get(row["timing"], row["timing"])
    # The form stores E.164, which is what both tel: and wa.me want.
    out["wa_url"] = "https://wa.me/" + row["phone"].lstrip("+")
    out["waiting"] = row["handled_at"] is None
    return out
