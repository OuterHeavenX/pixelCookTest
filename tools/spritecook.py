#!/usr/bin/env python3
"""spritecook CLI - cook the game's pixel art.

    python3 tools/spritecook.py              # write assets/atlas.png + atlas.json
    python3 tools/spritecook.py --sheet FILE # also dump a 3x contact sheet
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spritecook.cook import build, contact_sheet  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser(description="Cook the game's pixel-art atlas.")
    ap.add_argument("--out", default=os.path.join(ROOT, "assets"))
    ap.add_argument("--sheet", default=None, help="write a zoomed contact sheet here")
    args = ap.parse_args()

    png, meta_path, page, meta = build(args.out)
    print("atlas : %s (%dx%d)" % (png, page.width, page.height))
    print("frames: %s (%d sprites)" % (meta_path, len(meta["frames"])))
    if args.sheet:
        print("sheet : %s" % contact_sheet(args.sheet))


if __name__ == "__main__":
    main()
