"""Who changed what, when, and what it used to say.

One row per mutating admin action, written on the same connection as the
change itself so that an edit and its audit row commit or fail together. The
actor's address is denormalised into the row: accounts are disabled rather
than deleted, but a rename should not rewrite history.

Values are stored as jsonb, which is what lets a copy string, a package price
and a warranty status all be recorded by the same two columns. Anything that
is not JSON-serialisable — the ``TBD`` sentinel, a date — is coerced by
:func:`_jsonable` rather than left to fail at commit time, because an audit
row that raises would take the edit down with it.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from typing import Any

from . import content as C

log = logging.getLogger(__name__)

#: Actions worth naming. Not a constraint — the column is free text so a new
#: kind of change does not need a migration — but these are what the filter in
#: the audit view offers.
ACTIONS = ("create", "update", "delete", "publish", "unpublish", "reorder",
           "login", "logout", "password", "role", "disable", "enable")


def record(conn, *, actor: dict[str, Any] | None, action: str, entity: str,
           entity_id: str | None = None, before: Any = None,
           after: Any = None) -> None:
    """Write one audit row on an open transaction.

    ``actor`` is the signed-in user dict, or ``None`` for the CLI — which is
    recorded as ``cli`` rather than as a null, since "nobody did this" is never
    true.
    """
    conn.execute(
        """
        INSERT INTO audit_log (actor_id, actor_email, action, entity,
                               entity_id, before_value, after_value)
        VALUES (%(actor_id)s, %(actor_email)s, %(action)s, %(entity)s,
                %(entity_id)s, %(before)s::jsonb, %(after)s::jsonb)
        """,
        {
            "actor_id": actor.get("id") if actor else None,
            "actor_email": (actor.get("email") if actor else None) or "cli",
            "action": action,
            "entity": entity,
            "entity_id": None if entity_id is None else str(entity_id),
            "before": _dump(before),
            "after": _dump(after),
        },
    )


def recent(database, *, limit: int = 20, entity: str | None = None,
           action: str | None = None, actor_id: int | None = None
           ) -> list[dict[str, Any]]:
    """The audit trail, newest first, optionally filtered."""
    clauses = []
    params: dict[str, Any] = {"limit": max(1, min(limit, 500))}
    if entity:
        clauses.append("entity = %(entity)s")
        params["entity"] = entity
    if action:
        clauses.append("action = %(action)s")
        params["action"] = action
    if actor_id:
        clauses.append("actor_id = %(actor_id)s")
        params["actor_id"] = actor_id
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    with database.cursor() as conn:
        return conn.execute(
            f"""
            SELECT id, at, actor_id, actor_email, action, entity, entity_id,
                   before_value, after_value
              FROM audit_log
              {where}
             ORDER BY at DESC, id DESC
             LIMIT %(limit)s
            """,
            params,
        ).fetchall()


def entities(database) -> list[str]:
    """Distinct entity names, for the filter. Cheap: the index covers it."""
    with database.cursor() as conn:
        rows = conn.execute(
            "SELECT DISTINCT entity FROM audit_log ORDER BY entity"
        ).fetchall()
    return [row["entity"] for row in rows]


def _dump(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return json.dumps(_jsonable(value), ensure_ascii=False)
    except (TypeError, ValueError):
        log.exception("Unserialisable audit value; storing its repr.")
        return json.dumps({"repr": repr(value)}, ensure_ascii=False)


def _jsonable(value: Any) -> Any:
    if value is C.TBD:
        return None
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
