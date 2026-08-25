"""Bundles ``design/`` into ``static/build/``.

Three stylesheets and one script become one of each, fingerprinted by content
so they can be served immutable. In development the bundle rebuilds whenever a
source file's mtime moves; in production it is built once, at deploy time.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
from pathlib import Path

#: Concatenation order matters: tokens define the custom properties that base
#: and components consume.
CSS_SOURCES = ("tokens.css", "base.css", "components.css")
JS_SOURCES = ("app.js",)

#: The admin is a separate bundle: a visitor should never download the staff
#: interface, and staff should not wait for the public site's 56 KB of
#: components to edit a string. It shares tokens.css, which is where the two
#: interfaces genuinely agree.
ADMIN_CSS_SOURCES = ("tokens.css", "admin.css")

MANIFEST = "manifest.json"


def _squeeze_css(text: str) -> str:
    """Strip comments and collapse whitespace.

    Deliberately conservative — no selector merging, no colour rewriting. The
    stylesheet is ~30 KB and gzip does the real work; the goal here is to drop
    the commentary, which is more than half the file.
    """
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*([{}:;,>])\s*", r"\1", text)
    text = re.sub(r";}", "}", text)
    return text.strip()


def _squeeze_js(text: str) -> str:
    """Drop full-line comments and blank lines.

    Not a minifier. Rewriting JavaScript with regular expressions breaks on
    the first regex literal or template string that looks like a comment, and
    a 6 KB script does not justify pulling in a real one.
    """
    out = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue
        out.append(stripped)
    return "\n".join(out)


def _digest(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:10]


def _write(path: Path, payload: str) -> None:
    path.write_text(payload, encoding="utf-8")
    # nginx has gzip_static but not brotli on this host, so ship a .gz
    # alongside and let the edge handle Brotli.
    with gzip.open(path.with_suffix(path.suffix + ".gz"), "wt",
                   encoding="utf-8", compresslevel=9) as fh:
        fh.write(payload)


def build(design_dir: Path, build_dir: Path) -> dict[str, str]:
    """Build the bundle and return the manifest."""
    build_dir.mkdir(parents=True, exist_ok=True)

    css = _squeeze_css("\n".join(
        (design_dir / name).read_text(encoding="utf-8") for name in CSS_SOURCES
    ))
    js = _squeeze_js("\n".join(
        (design_dir / name).read_text(encoding="utf-8") for name in JS_SOURCES
    ))

    admin_css = _squeeze_css("\n".join(
        (design_dir / name).read_text(encoding="utf-8") for name in ADMIN_CSS_SOURCES
    ))

    manifest = {
        "css": f"kmq.{_digest(css)}.css",
        "js": f"kmq.{_digest(js)}.js",
        "admin_css": f"kmq-admin.{_digest(admin_css)}.css",
    }

    # Clear superseded fingerprints so the directory does not grow forever.
    keep = set(manifest.values()) | {MANIFEST}
    for stale in build_dir.iterdir():
        if stale.name.removesuffix(".gz") not in keep:
            stale.unlink()

    _write(build_dir / manifest["css"], css)
    _write(build_dir / manifest["js"], js)
    _write(build_dir / manifest["admin_css"], admin_css)
    (build_dir / MANIFEST).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def newest_mtime(design_dir: Path) -> float:
    return max(
        (design_dir / name).stat().st_mtime
        for name in CSS_SOURCES + JS_SOURCES + ADMIN_CSS_SOURCES
    )


def load_manifest(build_dir: Path) -> dict[str, str] | None:
    path = build_dir / MANIFEST
    if not path.exists():
        return None
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    # A manifest from an older build is missing whichever bundle was added
    # since. Treat it as absent so the caller rebuilds, rather than letting a
    # template fail on a KeyError at request time.
    if not all(key in manifest for key in ("css", "js", "admin_css")):
        return None
    return manifest
