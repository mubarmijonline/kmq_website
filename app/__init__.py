"""Application factory."""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import quote

from flask import Flask, g, request
from werkzeug.routing import BaseConverter

from . import assets
from . import content as C
from . import text

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
        # The client's Google Analytics 4 property. Only the published site
        # reports to it: a dev process and the test suite would otherwise
        # count themselves as visitors in the client's own numbers, which is
        # worse than no analytics at all. Set KMQ_GA_ID empty to switch it off
        # in production too.
        GA_MEASUREMENT_ID=os.environ.get("KMQ_GA_ID", "G-Z12Q4Y5EQZ").strip(),
        ENV_NAME=os.environ.get("KMQ_ENV", "dev"),
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_HTTPONLY=True,
        JSON_AS_ASCII=False,
    )
    if config:
        app.config.update(config)

    is_prod = app.config["ENV_NAME"] == "prod"
    if is_prod and not os.environ.get("SECRET_KEY"):
        # The os.urandom fallback above is fine for one dev process and wrong
        # for two gunicorn workers: each would sign cookies with a different
        # key, so an admin session would survive one request in two. Refusing
        # to boot is the only honest response.
        raise RuntimeError(
            "SECRET_KEY must be set when KMQ_ENV=prod: without it each worker "
            "signs sessions with a different key and admins are logged out at "
            "random."
        )
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

    from . import cli
    from .admin import bp as admin_bp
    from .routes import bp, register_errors

    app.register_blueprint(bp)
    app.register_blueprint(admin_bp)
    register_errors(app)
    cli.register(app)

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
    from . import store
    from .db import Database

    database = Database(app.config["DATABASE_URL"])
    app.extensions["kmq_db"] = database

    # The content overlay: stored edits layered over the copy in content.py.
    # Installed only when there is a pool to read from, so a site running
    # without DATABASE_URL keeps the shipped copy and pays nothing for it.
    overlay = store.Overlay(database)
    app.extensions["kmq_overlay"] = overlay
    # content.py holds one module-level overlay, which is right for the single
    # application a worker process builds and matters in tests, where an app
    # built without a database must not keep reading through the previous
    # app's pool.
    C.use_overlay(overlay if database.enabled else None)

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
            "wa_at": _whatsapp_url_at,
            "wa_configured": bool(app.config["WHATSAPP_NUMBER"]),
            "ga_id": (app.config["GA_MEASUREMENT_ID"]
                      if app.config["ENV_NAME"] == "prod" else ""),
            "show_prices": app.config["SHOW_PRICES"],
            "current_year": date.today().year,
            "icons": C.ICONS,
            # Stamped on every image URL so a replaced photograph is a
            # new URL rather than a cache hit on the old one.
            "img_v": app.extensions.setdefault("kmq_img_v", _image_version()),
            # Article bodies are plain text; this is the whole of the markup
            # they are allowed to imply. See app/text.py:blocks.
            "blocks": text.blocks,
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

    def _image_version() -> str:
        """A short stamp that changes whenever any file under static/img does.

        Photographs keep their names when their content changes — a replaced
        shot is still ppf-matte-800.avif — so nothing about the URL tells a
        cache that it is looking at a different picture. Templates hang this on
        image URLs so a replacement is a new URL and lands immediately, instead
        of waiting out whatever max-age the last visit was given.

        Cheap enough to do at boot and never again: the newest mtime in the
        tree, hashed short. In dev the before_request hook below recomputes it
        alongside the asset bundle.
        """
        newest = 0.0
        img_dir = ROOT / "static" / "img"
        if img_dir.exists():
            for path in img_dir.rglob("*"):
                if path.is_file():
                    newest = max(newest, path.stat().st_mtime)
        return hashlib.sha256(str(newest).encode()).hexdigest()[:8]

    def _asset_url(kind: str) -> str:
        manifest = app.extensions["kmq_assets"]["manifest"]
        from flask import url_for

        return url_for("static", filename=f"build/{manifest[kind]}")

    def _whatsapp_url_at(number: Any, message: str | None = None) -> str | None:
        """A wa.me link to one branch's own number, or ``None``.

        Falsy covers both an unset number and the ``TBD`` sentinel, which is
        what an unconfirmed branch phone is; callers fall back to
        :func:`_whatsapp_url` and then to the contact page.
        """
        if not number:
            return None
        digits = "".join(ch for ch in str(number) if ch.isdigit())
        if not digits:
            return None
        text = message or C.content(getattr(g, "locale", C.DEFAULT_LOCALE))["wa_default"]
        return f"https://wa.me/{digits}?text={quote(text)}"

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
