"""Application factory."""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import date
from pathlib import Path
from urllib.parse import quote

from flask import Flask, g, request
from werkzeug.routing import BaseConverter

from . import assets
from . import content as C

ROOT = Path(__file__).resolve().parent.parent
DESIGN_DIR = ROOT / "design"
BUILD_DIR = ROOT / "static" / "build"


class LocaleConverter(BaseConverter):
    """Matches only ``ar`` and ``en``.

    A converter rather than a string argument so that ``/fr/packages`` is a
    404 instead of quietly rendering Arabic under a French URL — which would
    let a crawler index the same page under unlimited paths.
    """

    regex = "ar|en"


def _env_flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def create_app(config: dict | None = None) -> Flask:
    app = Flask(
        __name__,
        static_folder=str(ROOT / "static"),
        template_folder=str(ROOT / "templates"),
    )

    app.url_map.converters["locale"] = LocaleConverter

    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY") or os.urandom(32),
        DATABASE_URL=os.environ.get("DATABASE_URL"),
        # Salt for the IP hash used to throttle. Not a secret in the
        # cryptographic sense, but a per-deployment value so hashes are not
        # comparable across sites.
        IP_HASH_SALT=os.environ.get("IP_HASH_SALT", "kmq-dev-salt"),
        # The business's WhatsApp number. Unset by default and deliberately
        # so: the design file shipped 966500000000, which is not KMQ's.
        # With it unset, every WhatsApp CTA falls back to the contact page
        # rather than opening a chat with a stranger.
        WHATSAPP_NUMBER=os.environ.get("KMQ_WHATSAPP", "").strip(),
        SHOW_PRICES=_env_flag("KMQ_SHOW_PRICES", True),
        SHOW_BEFORE_AFTER=_env_flag("KMQ_SHOW_BEFORE_AFTER", True),
        ENV_NAME=os.environ.get("KMQ_ENV", "dev"),
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_HTTPONLY=True,
        JSON_AS_ASCII=False,
    )
    if config:
        app.config.update(config)

    is_prod = app.config["ENV_NAME"] == "prod"
    app.config["SESSION_COOKIE_SECURE"] = is_prod
    app.config["PREFERRED_URL_SCHEME"] = "https" if is_prod else "http"

    logging.basicConfig(
        level=logging.INFO if is_prod else logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    _wire_assets(app, rebuild=not is_prod)
    _wire_database(app)
    _wire_locale(app)
    _wire_context(app)

    from .routes import bp, register_errors

    app.register_blueprint(bp)
    register_errors(app)

    return app


# --------------------------------------------------------------------------
# Assets
# --------------------------------------------------------------------------

def _wire_assets(app: Flask, *, rebuild: bool) -> None:
    manifest = assets.load_manifest(BUILD_DIR)
    if manifest is None:
        manifest = assets.build(DESIGN_DIR, BUILD_DIR)
    app.extensions["kmq_assets"] = {
        "manifest": manifest,
        "mtime": assets.newest_mtime(DESIGN_DIR),
    }

    if not rebuild:
        return

    @app.before_request
    def _rebuild_if_stale() -> None:
        state = app.extensions["kmq_assets"]
        current = assets.newest_mtime(DESIGN_DIR)
        if current > state["mtime"]:
            state["manifest"] = assets.build(DESIGN_DIR, BUILD_DIR)
            state["mtime"] = current


# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------

def _wire_database(app: Flask) -> None:
    from .db import Database

    database = Database(app.config["DATABASE_URL"])
    app.extensions["kmq_db"] = database

    @app.teardown_appcontext
    def _noop(_exc):  # pooled connections are returned by the context manager
        return None


# --------------------------------------------------------------------------
# Locale
# --------------------------------------------------------------------------

def _wire_locale(app: Flask) -> None:
    @app.url_value_preprocessor
    def _pull_locale(_endpoint, values):
        """Take ``lang`` off the view arguments and onto ``g``.

        Keeps every view signature free of a parameter that is really request
        state, and means a template can ask for ``g.locale`` without the view
        having passed it down.
        """
        if values is None:
            return
        g.locale = values.pop("lang", C.DEFAULT_LOCALE)

    @app.url_defaults
    def _push_locale(endpoint, values):
        """Put it back, so ``url_for('site.packages')`` needs no language."""
        if "lang" in values or not app.url_map.is_endpoint_expecting(endpoint, "lang"):
            return
        values["lang"] = getattr(g, "locale", C.DEFAULT_LOCALE)


# --------------------------------------------------------------------------
# Template context
# --------------------------------------------------------------------------

def _wire_context(app: Flask) -> None:
    @app.context_processor
    def _inject():
        locale = getattr(g, "locale", C.DEFAULT_LOCALE)
        return {
            "t": C.content(locale),
            "locale": locale,
            "TBD": C.TBD,
            "asset": _asset_url,
            "wa": _whatsapp_url,
            "wa_configured": bool(app.config["WHATSAPP_NUMBER"]),
            "show_prices": app.config["SHOW_PRICES"],
            "show_before_after": app.config["SHOW_BEFORE_AFTER"],
            "current_year": date.today().year,
            "icons": C.ICONS,
            # The lead form is described once, in content.py, and rendered by
            # one loop. Everything that loop needs is resolved here so the
            # template never calls into Python.
            "lead_fields": C.LEAD_FIELDS,
            "lead_labels": C.LEAD_LABELS[locale],
            "lead_hints": C.LEAD_HINTS.get(locale, {}),
            "lead_options": {
                "service": C.service_options(locale),
                "branch": C.branch_options(locale),
                "timing": C.timing_options(locale),
            },
            "errors_for_locale": C.LEAD_ERRORS[locale],
        }

    def _asset_url(kind: str) -> str:
        manifest = app.extensions["kmq_assets"]["manifest"]
        from flask import url_for

        return url_for("static", filename=f"build/{manifest[kind]}")

    def _whatsapp_url(text: str | None = None) -> str | None:
        """A wa.me link, or ``None`` when no number is configured.

        Templates treat ``None`` as "link to the contact page instead". That
        is the honest fallback: better to route someone to a form we own than
        to a phone number we invented.
        """
        number = app.config["WHATSAPP_NUMBER"]
        if not number:
            return None
        digits = "".join(ch for ch in number if ch.isdigit())
        if not digits:
            return None
        message = text or C.content(getattr(g, "locale", C.DEFAULT_LOCALE))["wa_default"]
        return f"https://wa.me/{digits}?text={quote(message)}"


def client_hash(app: Flask) -> str:
    """A salted hash of the caller's address.

    Stored instead of the address itself: enough to rate-limit a single
    client, not enough to identify one after the fact.
    """
    forwarded = request.headers.get("X-Forwarded-For", "")
    addr = forwarded.split(",")[0].strip() if forwarded else (request.remote_addr or "")
    salt = app.config["IP_HASH_SALT"]
    return hashlib.sha256(f"{salt}:{addr}".encode("utf-8")).hexdigest()
