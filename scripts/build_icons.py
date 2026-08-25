#!/usr/bin/env python3
"""Re-emit the client's icon kit as one Jinja macro.

The kit arrives as ``WEBSITE/<section>/<name>.svg`` — thirty-seven files, one
per glyph, each an Illustrator export: an XML declaration, a ``<defs><style>``
block that paints every shape with one class, and one or two wrapping ``<g>``
elements that carry nothing but that class.

This turns them into ``templates/partials/icons.html``:

* the wrapper elements go, since a fill rule is all they carried;
* the kit's #00B3FF becomes ``currentColor``, so a glyph takes the colour of
  whatever labels it rather than the kit's own blue — the site's accent is the
  logo's blue, which is not the same value;
* everything else — path data, viewBox, fill rules — is copied verbatim.

The two payment marks are the exception: they are third-party brand logos and
keep their own colours, which is why the packages page shows them on a light
plate rather than on the page's near-black.

Run it after the client sends a new kit:

    .venv/bin/python scripts/build_icons.py
"""

from __future__ import annotations

import hashlib
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KIT = ROOT / "WEBSITE"
TARGET = ROOT / "templates" / "partials" / "icons.html"

SVG_NS = "{http://www.w3.org/2000/svg}"

#: The kit's own blue. Every monochrome glyph is painted with it, and every
#: one of them becomes currentColor.
KIT_BLUE = "#00b3ff"

#: Delivered filename → the name templates ask for. Written out rather than
#: derived: the kit's names carry section prefixes, two spellings of
#: "service" and one typo ("maual unstallation"), and none of that belongs in
#: a template. Two files may share a name only if they are byte-identical —
#: the build fails otherwise, so a redraw is never silently dropped.
NAMES: dict[str, str] = {
    # ---- Home ----
    "1 Home/H Google rating.svg": "rating",
    "1 Home/H maual unstallation.svg": "hand-install",
    "1 Home/H response.svg": "response",
    "1 Home/H warranty.svg": "warranty",
    "1 Home/H whatsapp.svg": "whatsapp",
    # ---- Services ----
    "3 Service/Srv sparkle.svg": "sparkle",
    "3 Service/srv shield.svg": "car-shield",
    "3 Service/svr cool.svg": "cool",
    "3 Service/svr drop.svg": "drop",
    "3 Service/svr heat.svg": "heat",
    "3 Service/svr palette.svg": "palette",
    "3 Service/svr style.svg": "car-gloss",
    "3 Service/svr sun.svg": "sun",
    "3 Service/svr warranty.svg": "warranty",
    # ---- Packages: the instalment providers' own marks ----
    "4 Packages/Icons-02.svg": "pay-tabby",
    "4 Packages/Icons-03.svg": "pay-emkan",
    # ---- Warranty ----
    "5 Warranty/war Car Plate.svg": "plate",
    "5 Warranty/war Invoice Number.svg": "invoice",
    "5 Warranty/war Self Healing.svg": "self-healing",
    "5 Warranty/war UV.svg": "uv",
    "5 Warranty/war no bubbles.svg": "no-bubbles",
    # ---- Branches ----
    "6 Brunches/H whatsapp.svg": "whatsapp",
    "6 Brunches/location.svg": "location",
    # ---- Contact ----
    "Contact Us/H mobile.svg": "phone",
    "Contact Us/cont branch.svg": "branch",
    "Contact Us/cont form.svg": "form",
    "Contact Us/cont name.svg": "person",
    "Contact Us/cont service type.svg": "service-type",
    "Contact Us/cont whatsapp.svg": "whatsapp-solid",
    # ---- Header and footer ----
    "header - footer/H clock.svg": "clock",
    "header - footer/H facebook.svg": "facebook",
    "header - footer/H instagram.svg": "instagram",
    "header - footer/H mobile.svg": "phone",
    "header - footer/H snap.svg": "snapchat",
    "header - footer/H tiktok.svg": "tiktok",
    "header - footer/H whatsapp.svg": "whatsapp",
    "header - footer/location.svg": "location",
}

#: A tighter viewBox than the file ships with, for the icons that arrive with
#: the artwork adrift in a square canvas. Both payment marks sit in a 128
#: square as a band 35 units tall, so at chip height the mark itself would be
#: six pixels of ink. Measured once, and reproducible:
#:
#:     convert -background none -density 1280 "Icons-02.svg" -trim info:
#:
#: which reports the ink's box in pixels at 13.328 px per viewBox unit.
CROPS: dict[str, str] = {
    "pay-tabby": "29.6 52.8 70.0 22.4",
    "pay-emkan": "18.4 47.7 91.2 33.2",
}

#: Fills that are a brand's own backing plate rather than its mark. Tabby
#: ships as a black wordmark on a green pill; the packages page already gives
#: all three instalment marks one shared light chip, so the pill made Tabby
#: the only logo on the row wearing a second, differently coloured box. Drop
#: it and the wordmark sits on the chip like the other two. The crop above is
#: the wordmark's own ink box, measured the same way as the note explains.
PLATES: dict[str, tuple[str, ...]] = {
    "pay-tabby": ("#64c0a5",),
}

#: Shapes worth carrying over. Nothing in the kit uses any other element.
SHAPES = ("path", "rect", "circle", "ellipse", "polygon", "polyline")

#: Which attributes each shape keeps, in this order.
KEEP = {
    "path": ("d",),
    "rect": ("x", "y", "width", "height", "rx", "ry"),
    "circle": ("cx", "cy", "r"),
    "ellipse": ("cx", "cy", "rx", "ry"),
    "polygon": ("points",),
    "polyline": ("points",),
}

HEADER = """\
{# The client's icon kit. GENERATED by scripts/build_icons.py — edit the SVGs
   in WEBSITE/ and run it again rather than editing this file.

   Every monochrome glyph is filled with `currentColor`, so it takes the
   colour of whatever labels it; the kit paints them #00B3FF, which is the
   logo's blue and not this site's accent. The two payment marks keep their
   own colours, being someone else's brand.

   `kit` is the whole set. `brand_icon` is the older name for the same thing,
   kept because the header, the footer and the floating button call it. #}

{% macro kit(name, size=64, extra='') -%}
"""

FOOTER = """\
  {%- endif %}
{%- endmacro %}


{% macro brand_icon(name, size=20) -%}{{ kit(name, size) }}{%- endmacro %}
"""


def _declarations(css: str) -> dict[str, dict[str, str]]:
    """``.cls-1 { fill: #00b3ff; }`` → ``{"cls-1": {"fill": "#00b3ff"}}``."""
    out: dict[str, dict[str, str]] = {}
    for selector, body in re.findall(r"\.([\w-]+)\s*\{([^}]*)\}", css):
        props = {}
        for declaration in body.split(";"):
            if ":" in declaration:
                prop, _, value = declaration.partition(":")
                props[prop.strip()] = value.strip()
        out[selector] = props
    return out


def _paint(props: dict[str, str]) -> str:
    """The fill attributes one shape needs, given its class's declarations.

    A shape painted in the kit's blue gets nothing: it inherits currentColor
    from the ``<svg>``. A translucent tint of that blue keeps its alpha and
    inherits the hue, so the two tones still move together. Any other colour
    is somebody else's brand and is copied as it is.
    """
    fill = props.get("fill", KIT_BLUE).lower()
    bits = []

    alpha = re.match(r"rgba\(\s*0\s*,\s*179\s*,\s*255\s*,\s*([\d.]+)\s*\)", fill)
    if alpha:
        bits.append(f'fill-opacity="{alpha.group(1)}"')
    elif fill != KIT_BLUE:
        bits.append(f'fill="{fill}"')

    if props.get("fill-rule"):
        bits.append(f'fill-rule="{props["fill-rule"]}"')
    return "".join(f" {bit}" for bit in bits)


def convert(path: Path, name: str) -> tuple[str, str]:
    """One delivered SVG → its viewBox and its shapes, as markup."""
    tree = ET.parse(path)
    root = tree.getroot()

    css = "".join(
        (node.text or "") for node in root.iter(f"{SVG_NS}style")
    )
    classes = _declarations(css)

    shapes = []
    for node in root.iter():
        tag = node.tag.removeprefix(SVG_NS)
        if tag not in SHAPES:
            continue
        props = classes.get(node.get("class", ""), {})
        if props.get("fill", "").lower() in PLATES.get(name, ()):
            continue
        attrs = "".join(
            f' {attr}="{node.get(attr)}"'
            for attr in KEEP[tag] if node.get(attr) is not None
        )
        shapes.append(f"<{tag}{attrs}{_paint(props)}/>")

    if not shapes:
        raise SystemExit(f"{path}: no shapes found")
    return CROPS.get(name, root.get("viewBox", "")), "".join(shapes)


def build() -> dict[str, str]:
    """Write the partial. Returns name → viewBox, for the summary line."""
    seen: dict[str, str] = {}      # name → digest of the file it came from
    icons: dict[str, tuple[str, str]] = {}

    for relative, name in NAMES.items():
        source = KIT / relative
        if not source.exists():
            raise SystemExit(f"missing from the kit: {relative}")

        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if name in seen:
            if seen[name] != digest:
                raise SystemExit(
                    f"two different drawings both named {name!r}; the second "
                    f"is {relative}. Give one of them its own name."
                )
            continue
        seen[name] = digest
        icons[name] = convert(source, name)

    lines = [HEADER]
    for index, name in enumerate(sorted(icons)):
        view_box, shapes = icons[name]
        keyword = "if" if index == 0 else "elif"
        lines.append(
            f'  {{%- {keyword} name == "{name}" %}}\n'
            f'  <svg class="kmq-glyph {{{{ extra }}}}" width="{{{{ size }}}}"'
            f' height="{{{{ size }}}}" viewBox="{view_box}"\n'
            f'       fill="currentColor" aria-hidden="true" focusable="false">'
            f"{shapes}</svg>\n"
        )
    lines.append(FOOTER)

    TARGET.write_text("".join(lines), encoding="utf-8")
    return {name: icons[name][0] for name in sorted(icons)}


if __name__ == "__main__":
    written = build()
    print(f"{TARGET.relative_to(ROOT)}: {len(written)} icons")
    print("  " + ", ".join(written))
    sys.exit(0)
