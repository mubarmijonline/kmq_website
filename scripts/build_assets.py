#!/usr/bin/env python3
"""Build static/build/ from design/. Run at deploy time."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import BUILD_DIR, DESIGN_DIR  # noqa: E402
from app.assets import build  # noqa: E402

if __name__ == "__main__":
    manifest = build(DESIGN_DIR, BUILD_DIR)
    for kind, name in manifest.items():
        print(f"{kind}: {name}")
