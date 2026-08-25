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
    ("hero", "[data-kmq-stack], [data-kmq-cycle]"),
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


#: Production is gunicorn behind nginx with gzip_static on, so HTML, CSS and
#: JS reach the browser compressed. Measuring against bare gunicorn reports the
#: stylesheet at 54 KB when a visitor downloads about 11 KB, which makes every
#: transfer-size-driven number — LCP most of all — pessimistic by a factor
#: nobody can reason about. This is the smallest thing that closes the gap.
GZIP_APP = '''
import gzip as _gzip
from wsgi import app as _app

_TYPES = ("text/html", "text/css", "application/javascript", "image/svg+xml")


def app(environ, start_response):
    accepts = "gzip" in environ.get("HTTP_ACCEPT_ENCODING", "")
    captured = {}

    def capture(status, headers, exc_info=None):
        captured["status"] = status
        captured["headers"] = headers
        return lambda _: None

    body = b"".join(_app(environ, capture))
    headers = captured["headers"]
    ctype = next((v for k, v in headers if k.lower() == "content-type"), "")

    if accepts and any(t in ctype for t in _TYPES) and len(body) > 512:
        body = _gzip.compress(body, 6)
        headers = [(k, v) for k, v in headers
                   if k.lower() not in ("content-length", "content-encoding")]
        headers += [("Content-Encoding", "gzip"), ("Content-Length", str(len(body)))]
    else:
        headers = [(k, v) for k, v in headers if k.lower() != "content-length"]
        headers.append(("Content-Length", str(len(body))))

    start_response(captured["status"], headers)
    return [body]
'''


class Server:
    """The site on a loopback port, torn down even when a check raises."""

    def __init__(self) -> None:
        self.port = free_port()
        self.base = f"http://127.0.0.1:{self.port}"
        self.proc: subprocess.Popen | None = None

    def __enter__(self) -> "Server":
        (ROOT / "_audit_wsgi.py").write_text(GZIP_APP)
        env = dict(os.environ, KMQ_ENV="dev", SECRET_KEY="audit", PYTHONPATH=str(ROOT))
        env.pop("DATABASE_URL", None)  # 24 of 26 pages never touch it
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "gunicorn", "--workers", "2", "--threads", "4",
             "--bind", f"127.0.0.1:{self.port}", "--log-level", "warning",
             "_audit_wsgi:app"],
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
        (ROOT / "_audit_wsgi.py").unlink(missing_ok=True)


# --------------------------------------------------------------------------
# Lighthouse
# --------------------------------------------------------------------------

#: Lighthouse runs on a shared machine, and one run is not a measurement.
#: A single noisy run here reported every main-thread category inflated four
#: times over — script parsing included, which the change under test does not
#: touch — while the very next locale in the same batch improved. Three runs
#: and a median is the cheapest thing that stops that reading as a regression.
LH_RUNS = 3


def median(values: list[float]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def lighthouse(base: str, out: Path) -> dict:
    """Mobile runs per locale, median of LH_RUNS. Section 7's four numbers."""
    if not shutil.which("npx"):
        print("  npx missing — skipping Lighthouse")
        return {}

    # Lighthouse 12 takes the browser from CHROME_PATH; --chrome-path is
    # accepted on the command line and then ignored.
    env = dict(os.environ, CHROME_PATH=chromium())
    scores = {}

    for lang in LOCALES:
        runs = []
        for n in range(LH_RUNS):
            report = out / f"lighthouse-{lang}-{n}.json"
            cmd = [
                "npx", "--yes", "lighthouse", f"{base}/{lang}/",
                "--quiet", "--output=json", f"--output-path={report}",
                "--only-categories=performance", "--form-factor=mobile",
                "--screenEmulation.mobile", "--throttling-method=simulate",
                "--chrome-flags=--headless=new --no-sandbox --disable-dev-shm-usage",
            ]
            print(f"  lighthouse /{lang}/ {n + 1}/{LH_RUNS} ...", flush=True)
            run = subprocess.run(cmd, capture_output=True, text=True,
                                 timeout=600, env=env)
            if not report.exists():
                err = run.stderr.strip() or run.stdout.strip()
                print(f"    failed: {err.splitlines()[0][:300] if err else '?'}")
                continue

            data = json.loads(report.read_text())
            audits = data["audits"]
            runs.append({
                "performance": round(data["categories"]["performance"]["score"] * 100),
                "lcp_ms": round(audits["largest-contentful-paint"]["numericValue"]),
                "cls": round(audits["cumulative-layout-shift"]["numericValue"], 4),
                "tbt_ms": round(audits["total-blocking-time"]["numericValue"]),
            })
            print(f"    {runs[-1]}")

        if not runs:
            continue
        scores[lang] = {k: round(median([r[k] for r in runs]), 4)
                        for k in runs[0]}
        scores[lang]["runs"] = len(runs)
        print(f"    median: {scores[lang]}")
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

                # Walk the page before the full-page shot. Playwright captures
                # full_page by resizing rather than scrolling, which never
                # trips loading="lazy" — the branch and journal cards came out
                # as empty wells, which looks exactly like a broken build.
                page.evaluate("""() => new Promise(done => {
                    let y = 0;
                    const step = () => {
                        y += window.innerHeight * 0.8;
                        window.scrollTo(0, y);
                        if (y < document.body.scrollHeight) setTimeout(step, 120);
                        else { window.scrollTo(0, 0); setTimeout(done, 400); }
                    };
                    step();
                })""")
                page.wait_for_load_state("networkidle")

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
# Contrast and focus
# --------------------------------------------------------------------------

#: Walks the rendered page rather than the palette. Tokens can be correct and
#: still land the wrong pair on an element, and the only way to know is to ask
#: the browser what it actually painted. Backgrounds are resolved by walking
#: up until something is not transparent, which is what the eye does too.
CONTRAST = r"""
() => {
  const lum = (c) => {
    const [r, g, b] = c.map(v => {
      v /= 255;
      return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };
  const parse = (s) => {
    const m = s.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1].split(/[\s,\/]+/).filter(Boolean).map(Number);
    return { rgb: p.slice(0, 3), a: p.length > 3 ? p[3] : 1 };
  };
  // Returns the painted ground, or null when a gradient is in the way.
  // Walking past a gradient to the colour underneath reports a ratio against
  // something the eye never sees — that produced a 1.06 for white-on-brand,
  // which is neither the real number nor a real pass. Gradients come back as
  // null and are listed separately for a by-hand check; --grad-brand's own
  // worst point is measured in tokens.css.
  //
  // Known false positive: .kmq-pkg--featured paints a brand gradient on its
  // border box and an opaque --ink-800 layer on its padding box. This stops
  // at the first gradient it meets, so the card's text is reported here even
  // though it sits on the opaque layer. Checked by hand — text-mid 8.78,
  // text-low 4.75, brand-300 8.04 on --ink-800, all passing.
  const ground = (el) => {
    for (let n = el; n && n !== document.documentElement; n = n.parentElement) {
      const cs = getComputedStyle(n);
      if (cs.backgroundImage && cs.backgroundImage.includes('gradient')) return null;
      const c = parse(cs.backgroundColor);
      if (c && c.a > 0.5) return c.rgb;
    }
    const c = parse(getComputedStyle(document.body).backgroundColor);
    return c ? c.rgb : [0, 0, 0];
  };
  const bad = [], onGradient = [];
  for (const el of document.querySelectorAll('body *')) {
    if (!el.childNodes.length) continue;
    const text = [...el.childNodes]
      .filter(n => n.nodeType === 3).map(n => n.textContent.trim()).join('');
    if (!text) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none') continue;
    if (parseFloat(cs.opacity) < 0.5) continue;
    // Gradient-clipped headings paint transparent by design; the gradient's
    // own stops are checked in tokens.css, not here.
    if (cs.webkitTextFillColor === 'rgba(0, 0, 0, 0)') continue;
    const fg = parse(cs.color);
    if (!fg || fg.a < 0.5) continue;
    const bg = ground(el);
    if (bg === null) {
      onGradient.push({ text: text.slice(0, 40), color: cs.color,
                        cls: (el.className || '').toString().slice(0, 40) });
      continue;
    }
    // Flatten any partial alpha on the text colour over its own ground.
    const flat = fg.rgb.map((v, i) => v * fg.a + bg[i] * (1 - fg.a));
    const l1 = lum(flat), l2 = lum(bg);
    const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
    const size = parseFloat(cs.fontSize);
    const weight = parseInt(cs.fontWeight, 10) || 400;
    const large = size >= 24 || (size >= 18.66 && weight >= 700);
    const need = large ? 3 : 4.5;
    if (ratio < need) {
      bad.push({ text: text.slice(0, 40), ratio: Math.round(ratio * 100) / 100,
                 need, size, tag: el.tagName.toLowerCase(),
                 cls: (el.className || '').toString().slice(0, 40) });
    }
  }
  return { bad, onGradient };
}
"""


def contrast(base: str, out: Path) -> dict:
    """Every visible text node, measured against what is painted behind it."""
    from playwright.sync_api import sync_playwright

    # No trailing slashes: app/routes.py declares "/<locale:lang>/packages"
    # and friends, and Flask 404s the slashed form rather than redirecting.
    # With them, this audited the error page five times over.
    pages = ["", "packages", "services", "branches", "contact-us", "warranty",
             "about-us", "blog", "services/ppf-gloss"]
    result = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        for lang in LOCALES:
            failures, rings = [], 0
            ctx = browser.new_context(viewport={"width": 1440, "height": 950})
            page = ctx.new_page()
            gradients = []
            for path in pages:
                page.goto(f"{base}/{lang}/{path}", wait_until="networkidle")
                found = page.evaluate(CONTRAST)
                for item in found["bad"]:
                    item["page"] = f"/{lang}/{path}"
                    failures.append(item)
                gradients.extend(found["onGradient"])

            # Focus: tab through the homepage and confirm every stop paints
            # something visible. outline:none with no replacement is the bug.
            page.goto(f"{base}/{lang}/", wait_until="networkidle")
            for _ in range(40):
                page.keyboard.press("Tab")
                seen = page.evaluate("""() => {
                    const el = document.activeElement;
                    if (!el || el === document.body) return null;
                    const cs = getComputedStyle(el);
                    const outline = cs.outlineStyle !== 'none'
                        && parseFloat(cs.outlineWidth) > 0;
                    return { ok: outline || cs.boxShadow !== 'none',
                             tag: el.tagName.toLowerCase() };
                }""")
                if seen and not seen["ok"]:
                    failures.append({"focus": seen["tag"], "page": f"/{lang}/"})
                elif seen:
                    rings += 1
            ctx.close()
            colours = sorted({g["color"] for g in gradients})
            result[lang] = {"contrast_failures": failures,
                            "focus_stops_ok": rings,
                            "on_gradient_labels": len(gradients),
                            "on_gradient_colours": colours}
            print(f"    {lang}: {len(failures)} contrast failures, "
                  f"{rings} focus stops with a visible ring, "
                  f"{len(gradients)} labels on a gradient ({', '.join(colours)})")
            for f in failures[:8]:
                print(f"      {f}")
        browser.close()

    (out / "contrast.json").write_text(json.dumps(result, indent=2) + "\n")
    return {lang: {"contrast_failures": len(v["contrast_failures"]),
                   "focus_stops_ok": v["focus_stops_ok"],
                   "on_gradient_colours": v["on_gradient_colours"]}
            for lang, v in result.items()}


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
    ap.add_argument("--only", choices=("lighthouse", "shots", "trace", "a11y"),
                    help="run a single check instead of all of them")
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
        if args.only in (None, "a11y"):
            print("contrast and focus:")
            summary["a11y"] = contrast(srv.base, out)
        if args.only in (None, "trace"):
            print("hero trace (4x CPU throttle):")
            summary["hero"] = hero_trace(srv.base, out)

    if args.only in (None, "lighthouse", "trace", "a11y"):
        path = out / "summary.json"
        merged = json.loads(path.read_text()) if path.exists() else {}
        merged.update(summary)
        path.write_text(json.dumps(merged, indent=2) + "\n")
        print(f"\n{path}")
        print(json.dumps(merged, indent=2))


if __name__ == "__main__":
    main()
