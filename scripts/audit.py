#!/usr/bin/env python3
"""Measure the site the same way twice, so before and after are comparable.

Three things, one command:

  * Lighthouse mobile for both locales -> Performance, LCP, CLS, TBT.
  * Screenshots of every homepage section, both locales, three widths.
  * A 4x-CPU-throttled recording of the hero -> long tasks, layout shifts.

Everything lands in ``docs/audit/<label>/``. Run it once before touching
anything and once at the end; the two directories diff by eye.

    python3 scripts/audit.py before
    python3 scripts/audit.py after
    python3 scripts/audit.py after --only shots     # skip the slow parts

Lighthouse comes from ``npx``, which caches it outside the project — no
package.json is created and nothing is added to requirements.txt. It drives
the Chromium that Playwright already downloaded rather than a second browser.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_ROOT = ROOT / "docs" / "audit"

LOCALES = ("ar", "en")

#: Widths the acceptance criteria name. 360 is the floor the layout must hold.
WIDTHS = {"mobile": 360, "tablet": 768, "desktop": 1440}

#: Homepage sections, in document order. Keyed by a stable selector rather
#: than nth-child so a section moving does not silently rename a screenshot.
SECTIONS = [
    ("header", ".kmq-header"),
    ("hero", "[data-kmq-stack], [data-kmq-hero]"),
    ("trust", ".kmq-strip"),
    ("services", "[data-kmq-section='services']"),
    ("packages", "[data-kmq-section='packages']"),
    ("warranty", "[data-kmq-section='warranty']"),
    ("why", ".kmq-grid--hairline"),
    ("branches", "[data-kmq-section='branches']"),
    ("journal", "[data-kmq-section='blog']"),
    ("faq", ".kmq-faq"),
    ("cta", ".kmq-close"),
    ("footer", ".kmq-footer"),
]

#: Collected in the page before Playwright asks for it, because both entry
#: types only fire once and a late addEventListener misses them.
OBSERVER = """
window.__kmq = { long: [], shifts: [], lcp: 0 };
new PerformanceObserver((l) => {
  for (const e of l.getEntries()) window.__kmq.long.push(Math.round(e.duration));
}).observe({ type: 'longtask', buffered: true });
new PerformanceObserver((l) => {
  for (const e of l.getEntries()) {
    if (!e.hadRecentInput) window.__kmq.shifts.push(e.value);
  }
}).observe({ type: 'layout-shift', buffered: true });
new PerformanceObserver((l) => {
  const e = l.getEntries().pop();
  if (e) window.__kmq.lcp = Math.round(e.startTime);
}).observe({ type: 'largest-contentful-paint', buffered: true });
"""


def chromium() -> str:
    """The browser Playwright installed, so Lighthouse does not fetch its own."""
    cache = Path.home() / ".cache" / "ms-playwright"
    found = sorted(cache.glob("chromium-*/chrome-linux*/chrome"))
    if not found:
        sys.exit("no Playwright chromium found; run `playwright install chromium`")
    return str(found[-1])


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Server:
    """The site on a loopback port, torn down even when a check raises."""

    def __init__(self) -> None:
        self.port = free_port()
        self.base = f"http://127.0.0.1:{self.port}"
        self.proc: subprocess.Popen | None = None

    def __enter__(self) -> "Server":
        env = dict(os.environ, KMQ_ENV="dev", SECRET_KEY="audit", PYTHONPATH=str(ROOT))
        env.pop("DATABASE_URL", None)  # 24 of 26 pages never touch it
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "gunicorn", "--workers", "2", "--threads", "4",
             "--bind", f"127.0.0.1:{self.port}", "--log-level", "warning", "wsgi:app"],
            cwd=ROOT, env=env,
        )
        for _ in range(100):
            time.sleep(0.2)
            try:
                with socket.create_connection(("127.0.0.1", self.port), 0.3):
                    return self
            except OSError:
                if self.proc.poll() is not None:
                    sys.exit(f"server exited with {self.proc.returncode}")
        sys.exit("server never came up")

    def __exit__(self, *exc: object) -> None:
        if self.proc:
            self.proc.terminate()
            self.proc.wait(timeout=10)


# --------------------------------------------------------------------------
# Lighthouse
# --------------------------------------------------------------------------

def lighthouse(base: str, out: Path) -> dict:
    """Mobile run per locale. Returns the four numbers Section 7 asks for."""
    if not shutil.which("npx"):
        print("  npx missing — skipping Lighthouse")
        return {}

    scores = {}
    for lang in LOCALES:
        report = out / f"lighthouse-{lang}.json"
        cmd = [
            "npx", "--yes", "lighthouse", f"{base}/{lang}/",
            "--quiet", "--output=json", f"--output-path={report}",
            "--only-categories=performance", "--form-factor=mobile",
            "--screenEmulation.mobile", "--throttling-method=simulate",
            "--chrome-flags=--headless=new --no-sandbox --disable-dev-shm-usage",
        ]
        print(f"  lighthouse /{lang}/ ...", flush=True)
        # Lighthouse 12 takes the browser from CHROME_PATH; --chrome-path is
        # accepted on the command line and then ignored.
        env = dict(os.environ, CHROME_PATH=chromium())
        run = subprocess.run(cmd, capture_output=True, text=True, timeout=600, env=env)
        if not report.exists():
            print(f"    failed: {run.stderr.strip().splitlines()[0][:300] if run.stderr.strip() else run.stdout.strip()[:300]}")
            continue

        data = json.loads(report.read_text())
        audits = data["audits"]
        scores[lang] = {
            "performance": round(data["categories"]["performance"]["score"] * 100),
            "lcp_ms": round(audits["largest-contentful-paint"]["numericValue"]),
            "cls": round(audits["cumulative-layout-shift"]["numericValue"], 4),
            "tbt_ms": round(audits["total-blocking-time"]["numericValue"]),
        }
        print(f"    {scores[lang]}")
    return scores


# --------------------------------------------------------------------------
# Screenshots
# --------------------------------------------------------------------------

def screenshots(base: str, out: Path) -> None:
    from playwright.sync_api import sync_playwright

    shots = out / "shots"
    shots.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        for lang in LOCALES:
            for name, width in WIDTHS.items():
                ctx = browser.new_context(
                    viewport={"width": width, "height": 900},
                    device_scale_factor=2 if width == 360 else 1,
                )
                page = ctx.new_page()
                page.goto(f"{base}/{lang}/", wait_until="networkidle")
                page.wait_for_timeout(1200)  # let the hero settle on state 1

                page.screenshot(path=shots / f"{lang}-{name}-full.png", full_page=True)

                # A page wider than its viewport is the RTL failure that shows
                # up as a scrollbar and nothing else; record it as a number.
                overflow = page.evaluate(
                    "document.documentElement.scrollWidth - window.innerWidth"
                )
                if overflow > 0:
                    print(f"    !! {lang} @{width}px overflows by {overflow}px")

                for label, selector in SECTIONS:
                    el = page.query_selector(selector)
                    if el is None:
                        continue
                    el.scroll_into_view_if_needed()
                    page.wait_for_timeout(250)
                    el.screenshot(path=shots / f"{lang}-{name}-{label}.png")
                ctx.close()
        browser.close()
    print(f"  shots -> {shots}")


# --------------------------------------------------------------------------
# Throttled hero recording
# --------------------------------------------------------------------------

def hero_trace(base: str, out: Path) -> dict:
    """Long tasks and layout shifts while the hero runs, CPU at 4x throttle."""
    from playwright.sync_api import sync_playwright

    result = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        for lang in LOCALES:
            ctx = browser.new_context(viewport={"width": 390, "height": 844})
            page = ctx.new_page()
            page.add_init_script(OBSERVER)

            cdp = ctx.new_cdp_session(page)
            cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})

            page.goto(f"{base}/{lang}/", wait_until="load")
            # Twelve seconds is three full cycles of the rebuilt hero, and
            # enough of the old one's track to catch its worst frames.
            for _ in range(12):
                page.mouse.wheel(0, 90)
                page.wait_for_timeout(1000)

            m = page.evaluate("window.__kmq")
            long_tasks = [d for d in m["long"] if d > 50]
            result[lang] = {
                "lcp_ms": m["lcp"],
                "cls": round(sum(m["shifts"]), 4),
                "long_tasks_over_50ms": len(long_tasks),
                "worst_task_ms": max(long_tasks, default=0),
            }
            print(f"    {lang}: {result[lang]}")
            ctx.close()
        browser.close()
    return result


# --------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("label", help="before | after | any directory name")
    ap.add_argument("--only", choices=("lighthouse", "shots", "trace"),
                    help="run a single check instead of all three")
    args = ap.parse_args()

    out = OUT_ROOT / args.label
    out.mkdir(parents=True, exist_ok=True)
    summary: dict[str, object] = {"label": args.label}

    with Server() as srv:
        print(f"serving {srv.base}")
        if args.only in (None, "lighthouse"):
            print("lighthouse:")
            summary["lighthouse"] = lighthouse(srv.base, out)
        if args.only in (None, "shots"):
            print("screenshots:")
            screenshots(srv.base, out)
        if args.only in (None, "trace"):
            print("hero trace (4x CPU throttle):")
            summary["hero"] = hero_trace(srv.base, out)

    if args.only in (None, "lighthouse", "trace"):
        path = out / "summary.json"
        merged = json.loads(path.read_text()) if path.exists() else {}
        merged.update(summary)
        path.write_text(json.dumps(merged, indent=2) + "\n")
        print(f"\n{path}")
        print(json.dumps(merged, indent=2))


if __name__ == "__main__":
    main()
