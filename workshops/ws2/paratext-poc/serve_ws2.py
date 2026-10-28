#!/usr/bin/env python3
"""Run `paratext review` with our patched front end (ui/static/) instead of the
packaged one. app.js is an ES module, so it can't be extended from outside;
ui/static/ is a copy of paratext's review/static with our changes (see
ui/README.md for the diff and what each change is for).

    uv run python serve_ws2.py --no-open        # same flags as `paratext review`
"""

import sys
from pathlib import Path

import paratext.review.server as server
from paratext.cli import main

server.STATIC_DIR = Path(__file__).resolve().parent / "ui" / "static"

if __name__ == "__main__":
    sys.exit(main(["review", *sys.argv[1:]]))
