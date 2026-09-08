#!/usr/bin/env python3
"""Bundle the cooked assets and the game source into one playable index.html.

    python3 tools/build.py

Runs spritecook and mapcook first, then inlines atlas.png as a data URI so the
finished index.html opens straight off the filesystem with no server.
"""

import base64
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sh(*args):
    subprocess.run([sys.executable] + list(args), check=True, cwd=ROOT)


def main():
    sh(os.path.join("tools", "spritecook.py"))
    sh(os.path.join("tools", "mapcook.py"))

    png = open(os.path.join(ROOT, "assets", "atlas.png"), "rb").read()
    meta = json.load(open(os.path.join(ROOT, "assets", "atlas.json")))
    maps = json.load(open(os.path.join(ROOT, "assets", "maps.json")))
    font = open(os.path.join(ROOT, "src", "font.js"), encoding="utf-8").read()
    game = open(os.path.join(ROOT, "src", "game.js"), encoding="utf-8").read()
    html = open(os.path.join(ROOT, "src", "index.html"), encoding="utf-8").read()

    data_uri = "data:image/png;base64," + base64.b64encode(png).decode("ascii")
    assets = "\n".join([
        "/* Cooked by tools/spritecook.py and tools/mapcook.py - do not edit by hand. */",
        "const ATLAS_PNG = %s;" % json.dumps(data_uri),
        "const ATLAS_META = %s;" % json.dumps(meta, separators=(",", ":")),
        "const MAPS = %s;" % json.dumps(maps, separators=(",", ":")),
    ])

    out = html.replace("/*__ASSETS__*/", assets)
    out = out.replace("/*__FONT__*/", font)
    out = out.replace("/*__GAME__*/", game)

    path = os.path.join(ROOT, "index.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(out)
    print("built : %s (%.1f KB, %d sprites, %d maps)"
          % (path, len(out.encode("utf-8")) / 1024, len(meta["frames"]), len(maps)))


if __name__ == "__main__":
    main()
