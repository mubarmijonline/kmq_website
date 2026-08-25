#!/usr/bin/env python3
"""Pair the before and after screenshots into sheets you can actually look at.

scripts/audit.py writes 78 PNGs per run. Two runs is 156 files, which is not a
comparison — it is a directory. This puts each section's before and after into
one labelled image, so the change is a scroll rather than a lookup.

    python3 scripts/contact_sheet.py                    # both locales
    python3 scripts/contact_sheet.py --width desktop    # one width

Output lands in docs/audit/sheets/.

Pillow rather than ImageMagick, which is what the rest of the image tooling
uses: a full-page mobile capture at 2x is over 19,000px tall, and libpng
refuses to open it at all — "Image height exceeds user limit in IHDR". Pillow
reads it without complaint.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent

#: The before run lives in a worktree of the pre-redesign commit, because the
#: harness is newer than the code it measures — both halves have to come from
#: the same script or the pair is not a comparison.
DEFAULT_BEFORE = Path("/tmp/kmq-before/docs/audit/before-fair/shots")
DEFAULT_AFTER = ROOT / "docs" / "audit" / "after" / "shots"

SECTIONS = ["hero", "trust", "services", "packages", "warranty",
            "why", "branches", "journal", "faq", "cta", "footer", "full"]

INK = (5, 7, 15)
ACCENT = (143, 176, 255)
LABEL_H = 30
GAP = 14

#: A full page is far taller than it is wide, so those two go side by side;
#: everything else stacks, which keeps like next to like at the same scale.
SIDE_BY_SIDE = {"full"}

#: Pillow refuses very large images by default as a decompression-bomb guard.
#: These are our own screenshots, so the guard is only in the way.
Image.MAX_IMAGE_PIXELS = None


def banner(text: str, width: int) -> Image.Image:
    strip = Image.new("RGB", (width, LABEL_H), INK)
    draw = ImageDraw.Draw(strip)
    draw.text((10, LABEL_H // 2), text, fill=ACCENT, anchor="lm")
    return strip


def titled(path: Path, text: str, cap_h: int | None) -> Image.Image:
    """One screenshot with a caption above it, optionally scaled to a height."""
    img = Image.open(path).convert("RGB")
    if cap_h and img.height > cap_h:
        img = img.resize((max(1, round(img.width * cap_h / img.height)), cap_h),
                         Image.LANCZOS)
    out = Image.new("RGB", (img.width, img.height + LABEL_H), INK)
    out.paste(banner(text, img.width), (0, 0))
    out.paste(img, (0, LABEL_H))
    return out


def compose(before: Path | None, after: Path, side_by_side: bool,
            cap_h: int | None) -> Image.Image:
    panes = []
    if before and before.exists():
        panes.append(titled(before, "BEFORE", cap_h))
    panes.append(titled(after, "AFTER", cap_h))

    if side_by_side:
        w = sum(p.width for p in panes) + GAP * (len(panes) - 1)
        h = max(p.height for p in panes)
        sheet = Image.new("RGB", (w, h), INK)
        x = 0
        for p in panes:
            sheet.paste(p, (x, 0))
            x += p.width + GAP
    else:
        w = max(p.width for p in panes)
        h = sum(p.height for p in panes) + GAP * (len(panes) - 1)
        sheet = Image.new("RGB", (w, h), INK)
        y = 0
        for p in panes:
            sheet.paste(p, ((w - p.width) // 2, y))
            y += p.height + GAP
    return sheet


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--before", type=Path, default=DEFAULT_BEFORE)
    ap.add_argument("--after", type=Path, default=DEFAULT_AFTER)
    ap.add_argument("--width", default=None, help="mobile | tablet | desktop")
    args = ap.parse_args()

    if not args.after.exists():
        sys.exit(f"no after shots at {args.after}; run scripts/audit.py after")

    out_dir = ROOT / "docs" / "audit" / "sheets"
    out_dir.mkdir(parents=True, exist_ok=True)
    sizes = [args.width] if args.width else ["mobile", "desktop"]

    for lang in ("ar", "en"):
        for size in sizes:
            print(f"{lang} {size}:")
            for name in SECTIONS:
                after = args.after / f"{lang}-{size}-{name}.png"
                if not after.exists():
                    continue
                before = args.before / f"{lang}-{size}-{name}.png"
                # Full pages are capped so the sheet stays openable; sections
                # keep their real pixels, because that is the point of them.
                sheet = compose(before, after,
                                name in SIDE_BY_SIDE,
                                2600 if name in SIDE_BY_SIDE else None)
                target = out_dir / f"{lang}-{size}-{name}.jpg"
                sheet.save(target, quality=86, optimize=True)
                print(f"  {target.relative_to(ROOT)}  "
                      f"{sheet.width}x{sheet.height}  "
                      f"{target.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
