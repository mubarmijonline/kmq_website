#!/usr/bin/env python3
"""Turn the client's source photographs into what the browser should download.

Three jobs share one pipeline, because they want the same thing — AVIF first,
WebP for the browsers that lack it, and the original format last — and differ
only in crop and width:

  hero      the four car states, alpha kept, aligned to a common baseline
  branches  the branch storefronts, 16:9
  services  the five service photographs, 16:9

    python3 scripts/build_images.py            # all three
    python3 scripts/build_images.py hero       # just one

Sources live outside static/ and are never served; the originals stay where
the client put them. Everything written here is derived and can be deleted and
rebuilt.

The hero states need one thing the other two do not. The four PNGs were cut
from different renders, so the car's alpha box moves by up to 63px between
them — enough that a straight crossfade reads as a jump rather than a change
of finish. Each is trimmed to its own alpha box and then re-canvased into one
shared frame, sitting on a common baseline, so only the paint changes.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_CARS = ROOT / "car_images"
SRC_BRANCHES = ROOT / "branches_images"
SRC_WEBSITE = ROOT / "WEBSITE"

#: ImageMagick 6 spells this `convert`; 7 renamed it `magick`. Both encode
#: AVIF and WebP here, so no extra dependency is needed for either.
IM = "magick" if shutil.which("magick") else "convert"

#: Widths actually used, per role. Anything wider is bandwidth nobody sees.
#: The hero box tops out at min(940px, 92vw), so 940 is the largest width any
#: layout asks for. A 1250 cut existed briefly and was removed: on a phone at
#: DPR 2.625 the browser multiplies a 379px box up to 995 and picks it, which
#: is a megapixel and a half of decode for a decorative photograph of a black
#: car on a dark ground. 940 is the cap, and the phone lands on 720.
HERO_WIDTHS = (480, 720, 940)
CARD_WIDTHS = (400, 600, 800, 1200)

#: Quality per format. AVIF holds up far lower than JPEG does; these were
#: picked by encoding the largest source at each step and stopping where the
#: file stopped shrinking faster than it degraded.
Q = {"avif": 50, "webp": 72, "jpg": 82, "png": 95}

#: Alpha below this percent is the cut-out's shadow halo, not the car.
ALPHA_FLOOR = 10

#: state key -> (source file, the service it illustrates)
#: Order is the order the hero cycles in, and it matches t.services, so the
#: labels come from copy that already exists in both languages.
CAR_STATES = [
    ("ppf-gloss",     "IMG_6642.PNG"),
    ("ppf-matte",     "IMG_6641.PNG"),
    ("nano-ceramic",  "IMG_6640.PNG"),
    ("window-tint",   "IMG_6639.PNG"),
]

#: The five branch photographs, in the order t.branches lists them. There are
#: five files for six branches; the sixth keeps the existing entrance shot,
#: which is the client's call and is recorded in app/content.py, not here.
BRANCH_PHOTOS = [
    ("al-hamra",             "WhatsApp Image 2026-08-24 at 20.58.31.jpeg"),
    ("al-rimal",             "WhatsApp Image 2026-08-24 at 20.58.31 (1).jpeg"),
    ("tuwaiq",               "WhatsApp Image 2026-08-24 at 20.58.31 (2).jpeg"),
    ("jeddah-madinah-road",  "WhatsApp Image 2026-08-24 at 20.58.31 (3).jpeg"),
    ("dammam-imam",          "WhatsApp Image 2026-08-24 at 20.58.31 (4).jpeg"),
]

#: Matched by what the photograph shows. Four come from the client's Service
#: folder; the tint has no photograph there, and the Home folder's tint shot
#: is the same job photographed the same way.
SERVICE_PHOTOS = [
    ("ppf-gloss",    "3 Service/svr gloss.jpg"),
    ("ppf-matte",    "3 Service/svr matte.jpg"),
    ("nano-ceramic", "3 Service/svr nano.jpg"),
    ("window-tint",  "1 Home/H4 - tint.jpg"),
    ("colour-change", "3 Service/SRV - color.png"),
]


def run(args: list[str]) -> None:
    out = subprocess.run(args, capture_output=True, text=True)
    if out.returncode:
        sys.exit(f"{' '.join(args[:3])} ...\n{out.stderr.strip()[:500]}")


def report(path: Path) -> None:
    print(f"    {path.relative_to(ROOT)}  {path.stat().st_size / 1024:.0f} KB")


def encode(src: Path, stem: Path, widths: tuple[int, ...], fallback: str,
           *, extra: list[str] | None = None) -> None:
    """One source -> avif + webp + fallback, at every width."""
    for w in widths:
        sizes = {}
        for fmt in ("avif", "webp", fallback):
            out = stem.with_name(f"{stem.name}-{w}.{fmt}")
            run([IM, str(src), *(extra or []),
                 "-resize", f"{w}x>", "-quality", str(Q[fmt]),
                 "-strip", str(out)])
            sizes[fmt] = out.stat().st_size / 1024
        # AVIF is what all but a sliver of traffic actually downloads, so it
        # leads the line; the fallback's weight is the worst case, not the
        # expected one.
        print(f"    {stem.name}-{w}  "
              + "  ".join(f"{f} {s:.0f}K" for f, s in sizes.items()))


# --------------------------------------------------------------------------

def hero() -> None:
    """The four states, trimmed to their own alpha and re-canvased as one."""
    out_dir = ROOT / "static" / "img" / "hero"
    out_dir.mkdir(parents=True, exist_ok=True)

    missing = [f for _, f in CAR_STATES if not (SRC_CARS / f).exists()]
    if missing:
        sys.exit(f"car_images/ is missing {missing}")

    # Measure every car first: the shared frame has to fit the widest and the
    # tallest of them, or one state gets clipped.
    #
    # Measured on the alpha channel, thresholded, rather than with -trim.
    # -trim compares whole pixels to the corner one, so the faint shadow halo
    # these renders carry — alpha in the single digits, invisible on any
    # ground — counts as content and inflates the box by several hundred
    # pixels. ALPHA_FLOOR is what the eye would call the edge of the car.
    boxes = {}
    for key, name in CAR_STATES:
        geom = subprocess.run(
            [IM, str(SRC_CARS / name), "-alpha", "extract",
             "-threshold", f"{ALPHA_FLOOR}%", "-format", "%@", "info:"],
            capture_output=True, text=True, check=True).stdout.strip()
        # "%@" is WxH+X+Y.
        size, off = geom.split("+", 1)
        w, h = (int(v) for v in size.split("x"))
        x, y = (int(v) for v in off.split("+"))
        boxes[key] = (w, h, x, y)

    # The four renders are the same car at the same angle, but not at the same
    # camera pitch: the alpha boxes are within 1% on width and vary 7% on
    # height, so the roofline sits at four different places. Baseline
    # alignment alone leaves that as a visible twitch mid-crossfade.
    #
    # Normalise on height rather than width. The eye tracks the roof and the
    # ground, not the bumper-to-bumper length, so matching the two horizontal
    # lines and letting length drift by a few percent is the trade that
    # actually looks still.
    target_h = round(sum(h for _, h, _, _ in boxes.values()) / len(boxes))
    scaled = {k: (round(w * target_h / h), target_h)
              for k, (w, h, _, _) in boxes.items()}

    frame_w = max(w for w, _ in scaled.values())
    frame_h = target_h
    # A little air so the drop shadow and the wheel arches are not flush with
    # the edge, and so a 1px rounding difference cannot clip a tyre.
    pad_x, pad_y = round(frame_w * 0.03), round(frame_h * 0.06)
    frame_w += pad_x * 2
    frame_h += pad_y * 2

    heights = [h for _, h, _, _ in boxes.values()]
    print(f"  shared frame {frame_w}x{frame_h} "
          f"(sources varied {min(heights)}-{max(heights)}px tall, "
          f"normalised to {target_h})")

    for key, name in CAR_STATES:
        src = SRC_CARS / name
        w, h, x, y = boxes[key]
        sw, sh = scaled[key]
        # -gravity south puts every car on the same baseline, which is what
        # the eye actually tracks: wheels planted, only the finish changing.
        aligned = out_dir / f"{key}-aligned.png"
        run([IM, str(src), "-crop", f"{w}x{h}+{x}+{y}", "+repage",
             "-resize", f"{sw}x{sh}!",
             "-background", "none", "-gravity", "south",
             "-extent", f"{frame_w}x{frame_h}", str(aligned)])

        print(f"  {key}")
        # PNG fallback, not JPEG: these are cut-outs and JPEG has no alpha.
        encode(aligned, out_dir / key, HERO_WIDTHS, "png")
        aligned.unlink()

    (out_dir / "frame.txt").write_text(f"{frame_w} {frame_h}\n")
    print(f"  aspect-ratio for the CSS box: {frame_w} / {frame_h}")


def cards(pairs: list[tuple[str, str]], src_root: Path, out_name: str) -> None:
    """16:9 crops for the card grids, so the rows stay even."""
    out_dir = ROOT / "static" / "img" / out_name
    out_dir.mkdir(parents=True, exist_ok=True)

    for key, name in pairs:
        src = src_root / name
        if not src.exists():
            sys.exit(f"missing source: {src}")
        print(f"  {key}")
        # Crop to 16:9 on the way in rather than relying on object-fit alone:
        # the sources are square, and cropping once here beats shipping the
        # pixels the card will never show.
        encode(src, out_dir / key, CARD_WIDTHS, "jpg",
               extra=["-resize", "1600x900^", "-gravity", "center",
                      "-extent", "1600x900"])


JOBS = {
    "hero": hero,
    "branches": lambda: cards(BRANCH_PHOTOS, SRC_BRANCHES, "branches"),
    "services": lambda: cards(SERVICE_PHOTOS, SRC_WEBSITE, "services"),
}

if __name__ == "__main__":
    wanted = sys.argv[1:] or list(JOBS)
    for job in wanted:
        if job not in JOBS:
            sys.exit(f"unknown job {job!r}; pick from {', '.join(JOBS)}")
        print(f"{job}:")
        JOBS[job]()
