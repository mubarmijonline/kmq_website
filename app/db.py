"""PostgreSQL access.

Two operations, both narrow: write a lead, read a warranty. Everything else
on this site is static content.

The connection pool is optional at import time and every call degrades to a
sentinel rather than raising. A marketing site whose entire job is to start a
WhatsApp conversation must not return 500 because Postgres is restarting — the
warranty widget says "try again", the lead form says "message us instead", and
the other 24 pages never touch the database at all.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Any

from .text import normalise_lookup

log = logging.getLogger(__name__)

try:  # psycopg 3
    from psycopg_pool import ConnectionPool
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - exercised only on an incomplete install
    ConnectionPool = None  # type: ignore[assignment]
    dict_row = None  # type: ignore[assignment]


class Unavailable(Exception):
    """The database could not be reached."""


@dataclass(frozen=True)
class Warranty:
    warranty_number: str
    service_type: str
    activation_date: date
    expiry_date: date
    status: str


class Database:
    def __init__(self, dsn: str | None, *, min_size: int = 0, max_size: int = 4) -> None:
        self._pool: Any = None
        if not dsn:
            log.warning("No DATABASE_URL: lead capture and warranty lookup are disabled.")
            return
        if ConnectionPool is None:
            log.error("psycopg_pool is not installed: database features are disabled.")
            return
        # open=False so a database that is down at boot does not stop the
        # site from serving its 24 static pages.
        self._pool = ConnectionPool(
            dsn, min_size=min_size, max_size=max_size,
            kwargs={"row_factory": dict_row}, open=False,
        )
        try:
            self._pool.open(wait=False)
        except Exception:  # pragma: no cover
            log.exception("Could not open the connection pool.")

    @property
    def enabled(self) -> bool:
        return self._pool is not None

    def cursor(self):
        """A pooled connection. Raises :class:`Unavailable` when there is none.

        Public because the admin and the content store need it too; the two
        original callers below keep using it under its old name.
        """
        if self._pool is None:
            raise Unavailable("no pool")
        return self._pool.connection()

    #: Retained so the original call sites read unchanged.
    _cursor = cursor

    # -- Warranty ---------------------------------------------------------

    def find_warranty(self, query: str) -> Warranty | None:
        """Look a warranty up by plate or invoice number.

        Both columns store the normalised form, and the query is normalised
        the same way, so the two always meet. Returns only the four fields the
        page displays — the row also carries a branch, a technician name and
        an install date, and none of that belongs in an unauthenticated
        response.
        """
        key = normalise_lookup(query)
        if not key:
            return None
        try:
            with self._cursor() as conn:
                row = conn.execute(
                    """
                    SELECT warranty_number, service_type, activation_date,
                           expiry_date, status
                      FROM warranty
                     WHERE plate_number = %(key)s
                        OR invoice_number = %(key)s
                     LIMIT 1
                    """,
                    {"key": key},
                ).fetchone()
        except Unavailable:
            raise
        except Exception as exc:  # pragma: no cover
            log.exception("Warranty lookup failed.")
            raise Unavailable(str(exc)) from exc

        if row is None:
            return None
        return Warranty(**row)

    # -- Leads ------------------------------------------------------------

    def insert_lead(self, payload: dict[str, Any]) -> int:
        try:
            with self._cursor() as conn:
                row = conn.execute(
                    """
                    INSERT INTO lead (full_name, phone, service, car_model,
                                      branch_id, timing, notes, locale,
                                      ip_hash, user_agent)
                    VALUES (%(full_name)s, %(phone)s, %(service)s, %(car_model)s,
                            %(branch_id)s, %(timing)s, %(notes)s, %(locale)s,
                            %(ip_hash)s, %(user_agent)s)
                    RETURNING id
                    """,
                    payload,
                ).fetchone()
                conn.commit()
        except Unavailable:
            raise
        except Exception as exc:
            log.exception("Lead insert failed.")
            raise Unavailable(str(exc)) from exc
        return int(row["id"])

    def recent_lead_count(self, ip_hash: str, *, seconds: int = 60) -> int:
        """Leads from this client in the last ``seconds``. Used to throttle."""
        try:
            with self._cursor() as conn:
                row = conn.execute(
                    """
                    SELECT count(*) AS n
                      FROM lead
                     WHERE ip_hash = %(ip_hash)s
                       AND created_at > now() - make_interval(secs => %(secs)s)
                    """,
                    {"ip_hash": ip_hash, "secs": seconds},
                ).fetchone()
        except Exception:
            # Failing open here is deliberate: a throttle that cannot read
            # must not become a wall that blocks every genuine enquiry.
            log.exception("Throttle check failed; allowing the submission.")
            return 0
        return int(row["n"])

    def close(self) -> None:
        if self._pool is not None:
            self._pool.close()
