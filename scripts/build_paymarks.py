#!/usr/bin/env python3
"""Re-cut the Tamara wordmark as a background-free image.

The client's kit ships Tamara as ``WEBSITE/4 Packages/tamara.png``: black
letters on the brand's rainbow pill, 108x35, and opaque wherever the pill is.
The other two instalment marks (Tabby, Emkan) are line art on transparency, so
the pill made Tamara the odd one out — three marks on one row, one of them
wearing its own coloured box.

This lifts the letters off the pill, on two measurements. Darkness does most
of the work, since the letters are black and the pill is light. That alone
would keep the pill's purple corner, which is nearly as dark as the letters'
antialiasing, so neutrality decides the rest: the mark is black and every part
of the pill is a colour. The source's own alpha, eroded so the pill's rim is
not traced, masks whatever survives both.

The mark is re-cut at 4x and trimmed to its ink, because the packages page now
sizes it to the full width of its chip rather than to a fixed 24px height.

    .venv/bin/python scripts/build_paymarks.py
"""

from __future__ import annotations

from pathlib import Path

try:
    from PIL import Image, ImageChops, ImageFilter
except ModuleNotFoundError:  # pragma: no cover - a build-time tool, not runtime
    raise SystemExit(
        "this needs Pillow, which the site itself does not:\n"
        "    .venv/bin/pip install Pillow"
    )

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "WEBSITE" / "4 Packages" / "tamara.png"
#: Not ``tamara.png``: nginx serves everything under /static/ immutable for a
#: year and only the CSS and JS bundles are fingerprinted, so an image that
#: changes has to change its name or the old cut stays in caches. The name is
#: also the truer one now that the pill is gone.
TARGET = ROOT / "static" / "img" / "pay" / "tamara-mark.png"

#: Resample the source this much before separating ink from pill, so the
#: threshold has subpixel detail to work with and the edges come out smooth
#: rather than stepped. 108px of source becomes 432px, which is still ample
#: for a chip a couple of hundred device pixels wide.
SCALE = 4

#: Luminance below LO is solid ink, above HI is pill, and the ramp between
#: them carries the antialiasing. Measured off the source: the letters sit at
#: 0-30 and the pill runs 81 (its purple corner) to 230.
LO, HI = 40, 110

#: Luminance alone cannot tell the letters from that purple corner, so chroma
#: does the rest: the mark is neutral black (chroma 0 through 26) and every
#: part of the pill is a colour (median 36). Ink survives below CLO, nothing
#: survives above CHI, and the ramp keeps the letters' coloured antialiasing.
CLO, CHI = 24, 40

#: The mark's own black, kept rather than recoloured -- it is someone else's
#: brand, and the chip it sits on is light.
INK = (5, 5, 0)

#: Shrink the pill's silhouette by this many pixels before using it as a
#: stencil, so its own antialiased rim is not mistaken for ink. Odd, because
#: MinFilter wants an odd window. Two source pixels at 4x.
ERODE = 9


def main() -> int:
    src = Image.open(SOURCE).convert("RGBA")
    big = src.resize((src.width * SCALE, src.height * SCALE), Image.LANCZOS)

    rgb, alpha = big.convert("RGB"), big.getchannel("A")
    bands = rgb.split()

    darkness = rgb.convert("L").point(
        lambda v: 255 if v <= LO else 0 if v >= HI else
        round(255 * (HI - v) / (HI - LO)))
    chroma = ImageChops.difference(
        ImageChops.lighter(ImageChops.lighter(*bands[:2]), bands[2]),
        ImageChops.darker(ImageChops.darker(*bands[:2]), bands[2]))
    neutral = chroma.point(lambda v: 255 if v <= CLO else 0 if v >= CHI else
                           round(255 * (CHI - v) / (CHI - CLO)))

    ink = Image.new("RGBA", big.size, INK + (0,))
    mask = ImageChops.multiply(darkness, neutral)
    # Outside the pill the source is transparent white, which reads as ink
    # once luminance is all we look at, and the pill's own antialiased rim
    # reads as a grey halo. Its alpha rules both out -- eroded by ERODE, so
    # the rim is cut away rather than traced.
    inside = alpha.point(lambda v: 255 if v >= 250 else 0)
    inside = inside.filter(ImageFilter.MinFilter(ERODE))
    mask = Image.composite(mask, Image.new("L", big.size, 0), inside)
    ink.putalpha(mask)

    out = ink.crop(ink.getbbox())
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    out.save(TARGET, optimize=True)
    print(f"{TARGET.relative_to(ROOT)}  {out.width}x{out.height}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
