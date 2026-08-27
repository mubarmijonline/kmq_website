#!/usr/bin/env python3
"""Measure the admin's contrast the way a person sees it: rendered.

The admin went unreadable once already — it drew its colours from tokens.css,
the site's palette flipped from dark to light underneath it, and half the
sheet followed while the hard-coded half did not. Nothing in the admin's own
file had changed, so nothing in review looked wrong. Only the rendered page
was wrong.

This signs in, walks every admin page, and measures every visible text node
against what is actually painted behind it. It reuses the measurement
scripts/audit.py already runs over the public site, so the two agree about
what a failure is.

    KMQ_TEST_DATABASE_URL=postgresql:///kmq_admin_test \\
        .venv/bin/python scripts/check_admin_contrast.py

Point it at a development database — it signs in, which writes a session and
an audit row. Never production. It exits non-zero on the first failure, so it
can gate a deploy; add --shots to also write PNGs next to the report.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from audit import CONTRAST, free_port  # noqa: E402

OUT = ROOT / "docs" / "audit" / "admin-contrast"

#: The account this makes, uses and deletes. The suffix is the same one the
#: test suite reserves, so a leftover row is cleaned by the same query.
EMAIL = "contrast-check@kmq.test"

#: Every page the admin serves, less the ones that need a record that may not
#: exist. Widths: the rail's own breakpoint is 900px, so both sides of it.
PAGES = (
    ("/admin/", "dashboard"),
    ("/admin/leads", "leads"),
    ("/admin/leads?show=all", "leads-all"),
    ("/admin/copy", "copy"),
    ("/admin/copy/branches", "copy-group"),
    ("/admin/lists", "lists"),
    ("/admin/lists/packages", "collection"),
    ("/admin/lists/packages/gloss", "record"),
    ("/admin/settings", "settings"),
    ("/admin/branches", "branches"),
    ("/admin/branches/al-rimal", "branch"),
    ("/admin/audit", "audit"),
)

WIDTHS = ((1440, 950), (820, 1000))


class Server:
    """The admin on a loopback port, in this process, with a database.

    scripts/audit.py has one of these but deliberately runs it without
    DATABASE_URL — 24 of the 26 public pages never touch one. The admin is
    the other case: without a database there is nobody to sign in.
    """

    def __init__(self, dsn: str) -> None:
        self.port = free_port()
        self.base = f"http://127.0.0.1:{self.port}"
        self._dsn = dsn
        self._server = None
        self._thread = None

    def __enter__(self) -> "Server":
        import threading

        from werkzeug.serving import make_server

        from app import BUILD_DIR, DESIGN_DIR, create_app
        from app.assets import build

        # Build before booting. The dev rebuild hook compares against the
        # mtime it captured at start-up, so a sheet edited before the server
        # started is never stale by its reckoning — and this check would then
        # measure the bundle from the last build rather than the CSS under
        # test, which is the one mistake it cannot be allowed to make.
        os.umask(0o002)
        build(DESIGN_DIR, BUILD_DIR)

        app = create_app({"ENV_NAME": "dev", "SECRET_KEY": "contrast-check",
                          "DATABASE_URL": self._dsn})
        self._server = make_server("127.0.0.1", self.port, app, threaded=True)
        self._thread = threading.Thread(target=self._server.serve_forever,
                                        daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        if self._server is not None:
            self._server.shutdown()
        if self._thread is not None:
            self._thread.join(timeout=10)


def make_account(dsn: str) -> str:
    """An owner account with a known password, created for this run only."""
    from app import auth, create_app

    password = secrets.token_urlsafe(18)
    app = create_app({"ENV_NAME": "test", "SECRET_KEY": "contrast-check",
                      "DATABASE_URL": dsn})
    database = app.extensions["kmq_db"]
    drop_account(dsn)
    auth.create_user(database, email=EMAIL, display_name="Contrast Check",
                     password=password, role="owner")
    # create_user leaves the account owing a password change, which would put
    # every page behind the password form and measure that twelve times.
    auth.set_password(database, email=EMAIL, password=password,
                      must_change=False, revoke_sessions=False)
    return password


def drop_account(dsn: str) -> None:
    from app import create_app

    app = create_app({"ENV_NAME": "test", "SECRET_KEY": "contrast-check",
                      "DATABASE_URL": dsn})
    with app.extensions["kmq_db"].cursor() as conn:
        conn.execute("DELETE FROM audit_log WHERE actor_email = %s", (EMAIL,))
        conn.execute("DELETE FROM admin_user WHERE email = %s", (EMAIL,))
        conn.commit()


def sign_in(page, base: str, password: str) -> None:
    page.goto(f"{base}/admin/login", wait_until="networkidle")
    page.fill("#email", EMAIL)
    page.fill("#password", password)
    page.click("button[type=submit]")
    page.wait_for_load_state("networkidle")
    if "/admin/login" in page.url:
        sys.exit("could not sign in: the check cannot measure what it cannot reach")


def run(dsn: str, shots: bool) -> int:
    from playwright.sync_api import sync_playwright

    password = make_account(dsn)
    failures: list[dict] = []
    on_gradient: list[dict] = []
    measured = 0

    OUT.mkdir(parents=True, exist_ok=True)

    with Server(dsn) as srv, sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        for width, height in WIDTHS:
            ctx = browser.new_context(viewport={"width": width, "height": height})
            page = ctx.new_page()

            def measure(path: str, name: str) -> None:
                nonlocal measured
                page.goto(f"{srv.base}{path}", wait_until="networkidle")
                found = page.evaluate(CONTRAST)
                measured += 1
                # The page that answered, not the one asked for: /admin/login
                # redirects to the dashboard once there is a session, and a
                # failure filed under the wrong page is a failure nobody finds.
                where = page.url.replace(srv.base, "")
                for item in found["bad"]:
                    failures.append({**item, "page": where, "width": width})
                for item in found["onGradient"]:
                    on_gradient.append({**item, "page": where, "width": width})
                if shots:
                    page.screenshot(path=OUT / f"{name}-{width}.png", full_page=True)

            # Signed out first: the sign-in page is the only one a session
            # hides, and it is the one page every member of staff sees.
            measure("/admin/login", "login")
            sign_in(page, srv.base, password)
            for path, name in PAGES:
                measure(path, name)

            # Focus: tab through the busiest page and confirm every stop paints
            # something. outline:none with nothing in its place is the bug.
            page.goto(f"{srv.base}/admin/lists/packages/gloss", wait_until="networkidle")
            for _ in range(30):
                page.keyboard.press("Tab")
                seen = page.evaluate("""() => {
                    const el = document.activeElement;
                    if (!el || el === document.body) return null;
                    const cs = getComputedStyle(el);
                    const ring = cs.outlineStyle !== 'none'
                        && parseFloat(cs.outlineWidth) > 0;
                    return { ok: ring || cs.boxShadow !== 'none',
                             tag: el.tagName.toLowerCase() };
                }""")
                if seen and not seen["ok"]:
                    failures.append({"focus": seen["tag"], "page": "record",
                                     "width": width})
            ctx.close()
        browser.close()

    drop_account(dsn)

    report = {"pages_measured": measured, "failures": failures,
              "on_gradient": on_gradient}
    (OUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")

    print(f"{measured} page renders measured, {len(failures)} failures")
    for item in failures[:40]:
        if "focus" in item:
            print(f"  focus  {item['page']} @{item['width']}  <{item['focus']}>")
        else:
            print(f"  {item['ratio']:>5} (needs {item['need']})  {item['page']}"
                  f" @{item['width']}  .{item['cls']}  {item['text']!r}")
    if on_gradient:
        print(f"  {len(on_gradient)} nodes over a gradient, measured by hand")
    print(f"report: {OUT / 'report.json'}")
    return 1 if failures else 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shots", action="store_true",
                        help="also write a PNG of every page")
    args = parser.parse_args()

    dsn = os.environ.get("KMQ_TEST_DATABASE_URL")
    if not dsn:
        sys.exit("KMQ_TEST_DATABASE_URL is unset. Point it at a development "
                 "database — this signs in and writes to it.")
    raise SystemExit(run(dsn, args.shots))


if __name__ == "__main__":
    main()
