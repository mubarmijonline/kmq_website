#!/usr/bin/env python3
"""Build static/build/ from design/. Run at deploy time."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import BUILD_DIR, DESIGN_DIR  # noqa: E402
from app.assets import build  # noqa: E402

if __name__ == "__main__":
    # The deploy account and the interactive accounts are all in `developers`
    # and static/build/ is setgid, so either can write there — but only if the
    # files are group-writable. At the shell's default umask they land 0644,
    # and then whichever account did not build them cannot overwrite them.
    # The case that turns into an outage: if manifest.json goes missing,
    # _wire_assets builds inside create_app, in the worker, as the service
    # account, and a PermissionError there is gunicorn failing to boot rather
    # than a failed build.
    os.umask(0o002)
    manifest = build(DESIGN_DIR, BUILD_DIR)
    for kind, name in manifest.items():
        print(f"{kind}: {name}")
