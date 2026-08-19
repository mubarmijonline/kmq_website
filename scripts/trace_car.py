#!/usr/bin/env python3
"""Measure a hero cutout and emit the numbers design/components.css needs.

The protection stack filters five copies of the same PNG and relies on the
file's own alpha to confine each coating to the silhouette. Every percentage in
the .kmq-coat rules is of the .kmq-stack__car box, so swapping the photo means
re-measuring, not rescaling. Run this on the new file, then trace the
greenhouse off the grid overlay it writes.

    python3 scripts/trace_car.py static/img/car-suv.png
"""
import sys
from PIL import Image, ImageDraw

OVERLAY = "/tmp/car-grid.png"


def main(path):
    im = Image.open(path)
    print(f"file        {path}")
    print(f"mode        {im.mode}")
    im = im.convert("RGBA")
    w, h = im.size
    print(f"canvas      {w} x {h}")

    alpha = im.getchannel("A")
    lo, hi = alpha.getextrema()
    opaque = lo == 255 and hi == 255
    print(f"alpha range {lo}-{hi}" + ("  << NO TRANSPARENCY" if opaque else ""))

    bbox = im.getbbox()
    print(f"alpha bbox  {bbox}")
    if bbox:
        bw, bh = bbox[2] - bbox[0], bbox[3] - bbox[1]
        print(f"subject     {bw} x {bh}  ({100*bw/w:.1f}% x {100*bh/h:.1f}% of canvas)")
    print(f"aspect      {w} / {h}   = {w/h:.4f}")

    if opaque:
        print("\nThe coatings need real alpha: with an opaque canvas every")
        print("filtered copy becomes a full rectangle instead of a car.")

    # Percentage grid, labelled, so the greenhouse can be traced by eye.
    grid = im.copy()
    flat = Image.new("RGBA", grid.size, (255, 255, 255, 255))
    flat.alpha_composite(grid)
    draw = ImageDraw.Draw(flat)
    for pct in range(0, 101, 5):
        x, y = w * pct / 100, h * pct / 100
        heavy = pct % 25 == 0
        ink = (255, 0, 0, 255) if heavy else (0, 160, 255, 160)
        draw.line([(x, 0), (x, h)], fill=ink, width=2 if heavy else 1)
        draw.line([(0, y), (w, y)], fill=ink, width=2 if heavy else 1)
        if pct % 10 == 0:
            draw.text((x + 3, 3), str(pct), fill=(255, 0, 0, 255))
            draw.text((3, y + 3), str(pct), fill=(255, 0, 0, 255))
    flat.convert("RGB").save(OVERLAY)
    print(f"\ngrid overlay -> {OVERLAY}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "static/img/car-suv.png")
