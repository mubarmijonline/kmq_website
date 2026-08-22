#!/usr/bin/env python3
"""Measure a hero cutout and emit the numbers design/components.css needs.

The protection stack filters five copies of the same PNG and relies on the
file's own alpha to confine each coating to the silhouette. Every percentage in
the .kmq-coat rules is of the .kmq-stack__car box, so swapping the photo means
re-measuring, not rescaling. Run this on the new file, then trace the
greenhouse off the grid overlay it writes.

The thermal tint is the one coating the silhouette cannot place on its own: it
belongs on the glass, not the whole car. This also writes that mask —
``<stem>-glass.png``, an alpha cut of the greenhouse that design/components.css
loads with mask-image. It is found rather than drawn: inside REGION below, the
glass, pillars and roof are the only things darker than LEVEL, so thresholding
lands on the real window edges instead of a polygon's guess at them. REGION is
a loose fence, not the outline — it only has to keep the far mirror, the mirror
shadow on the door and the cowl shut line out of the threshold's reach.

    python3 scripts/trace_car.py static/img/car-suv.png
"""
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

OVERLAY = "/tmp/car-grid.png"

#: Loose greenhouse fence, in percent of the canvas. Traced on car-suv.png at
#: 1150x718: roofline, down the far A-pillar, back along the scuttle and the
#: belt line, with a notch at 15-26% stepping over the door mirror. It runs a
#: point or two wide of the glass everywhere — the threshold trims it back.
REGION = [
    (6.5, 0), (70, 0), (73, 6), (76, 13), (78.6, 21.0), (78.0, 24.6),
    (73, 26.4), (67, 27.6), (58, 29.0), (50, 30.0), (42, 30.4), (35, 30.2),
    (31.5, 29.2), (28.5, 27.6), (26.2, 25.6), (25.2, 21.6), (20.8, 21.0),
    (16.6, 24.4), (15.6, 27.6), (12, 27.8), (8, 27.0), (6.5, 21.5),
]

LEVEL = 62     #: luminance below this is glass; silver body sits far above it
SOLID = 180    #: alpha below this is the cutout's feathered edge, not the car
CLOSE = 9      #: closes the reflection streaks; the mirror hole is far wider
OPEN = 5       #: drops specks the threshold picked out of the interior
FEATHER = 1.2  #: the mask's own edge, so the tint does not land on a stair


def glass_mask(im):
    """Alpha cut of the greenhouse: dark pixels inside REGION, cleaned up."""
    w, h = im.size
    body = im.getchannel("A").point(lambda v: 255 if v > SOLID else 0)
    dark = im.convert("L").point(lambda v: 255 if v < LEVEL else 0)

    fence = Image.new("L", im.size, 0)
    ImageDraw.Draw(fence).polygon(
        [(x * w / 100, y * h / 100) for x, y in REGION], fill=255
    )

    m = ImageChops.multiply(ImageChops.multiply(dark, body), fence)
    # Close, then open: fill the windscreen's bright streaks without swallowing
    # the door mirror, then drop what is left of the seats and headrests.
    m = m.filter(ImageFilter.MaxFilter(CLOSE)).filter(ImageFilter.MinFilter(CLOSE))
    m = m.filter(ImageFilter.MinFilter(OPEN)).filter(ImageFilter.MaxFilter(OPEN))
    # The close bleeds a few pixels past the fence; put it back inside.
    m = ImageChops.multiply(m, fence).filter(ImageFilter.GaussianBlur(FEATHER))
    return m


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

    src = Path(path)
    mask = glass_mask(im)
    out = src.with_name(src.stem + "-glass.png")
    # Grey-and-alpha, not RGBA: mask-image reads the alpha channel, so the
    # colour plane is a constant and costs nothing to keep flat.
    Image.merge("LA", (Image.new("L", im.size, 255), mask)).save(out, optimize=True)
    covered = sum(1 for v in mask.getdata() if v > 127)
    print(f"glass mask   -> {out}  ({100*covered/(w*h):.1f}% of canvas)")

    # Proof sheet: the tint as the visitor meets it, over the hero's ground.
    tint = Image.new("RGBA", im.size, (0, 0, 0, 255))
    tint.putalpha(mask.point(lambda v: int(v * 0.84)))
    proof = Image.new("RGBA", im.size, (13, 13, 13, 255))
    proof.alpha_composite(im)
    proof.alpha_composite(tint)
    proof.convert("RGB").save("/tmp/car-tint.png")
    print("tint proof   -> /tmp/car-tint.png")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "static/img/car-suv.png")
