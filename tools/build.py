#!/usr/bin/env python3
"""Bundle the cooked assets and the game source into one playable index.html.

    python3 tools/build.py

Runs every cook step first (sprites, maps, rules, Godot staging), then inlines
atlas.png as a data URI so the finished index.html opens straight off the
filesystem with no server.
"""

import base64
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sh(*args):
    subprocess.run([sys.executable] + list(args), check=True, cwd=ROOT)


def main():
    sh(os.path.join("tools", "spritecook.py"))
    sh(os.path.join("tools", "mapcook.py"))
    sh(os.path.join("tools", "datacook.py"))
    sh(os.path.join("tools", "godotcook.py"))

    png = open(os.path.join(ROOT, "assets", "atlas.png"), "rb").read()
    meta = json.load(open(os.path.join(ROOT, "assets", "atlas.json")))
    maps = json.load(open(os.path.join(ROOT, "assets", "maps.json")))
    gamedata = json.load(open(os.path.join(ROOT, "assets", "gamedata.json")))
    font = open(os.path.join(ROOT, "src", "font.js"), encoding="utf-8").read()
    game = open(os.path.join(ROOT, "src", "game.js"), encoding="utf-8").read()
    html = open(os.path.join(ROOT, "src", "index.html"), encoding="utf-8").read()

    data_uri = "data:image/png;base64," + base64.b64encode(png).decode("ascii")

    # Pre-rendered maps, if any. tools/blender/town.py --full writes one per
    # map under art/prerender/, lit and shadowed in Blender at exactly the
    # map's own size, and the field draws it under the sprites instead of the
    # tiles. A map without one is drawn from tiles as before.
    # <map>_over.png, when it exists, is the same picture's overhangs - roofs,
    # treetops - on a clear film, drawn after the sprites so a sprite behind a
    # house is behind it.
    # <map>_water<k>.png are the water surfaces alone, one per frame of the
    # loop, drawn over the base picture in turn so the water moves.
    pre_dir = os.path.join(ROOT, "art", "prerender")
    prerender, overlay, water = {}, {}, {}
    if os.path.isdir(pre_dir):
        for name in sorted(os.listdir(pre_dir)):
            if not name.endswith(".png"):
                continue
            stem = name[:-4]
            uri = "data:image/png;base64," + base64.b64encode(
                open(os.path.join(pre_dir, name), "rb").read()).decode("ascii")
            frame = re.match(r"^(.*)_water(\d+)$", stem)
            if frame and frame.group(1) in maps:
                water.setdefault(frame.group(1), []).append((int(frame.group(2)), uri))
            elif stem.endswith("_over") and stem[:-5] in maps:
                overlay[stem[:-5]] = uri
            elif stem in maps:
                prerender[stem] = uri
    water = {k: [u for _, u in sorted(v)] for k, v in water.items()}

    assets = "\n".join([
        "/* Cooked by tools/spritecook.py and tools/mapcook.py - do not edit by hand. */",
        "const ATLAS_PNG = %s;" % json.dumps(data_uri),
        "const PRERENDER_PNG = %s;" % json.dumps(prerender),
        "const PRERENDER_OVER = %s;" % json.dumps(overlay),
        "const PRERENDER_WATER = %s;" % json.dumps(water),
        "const ATLAS_META = %s;" % json.dumps(meta, separators=(",", ":")),
        "const MAPS = %s;" % json.dumps(maps, separators=(",", ":")),
        "const GAMEDATA = %s;" % json.dumps(gamedata, separators=(",", ":")),
    ])

    out = html.replace("/*__ASSETS__*/", assets)
    out = out.replace("/*__FONT__*/", font)
    out = out.replace("/*__GAME__*/", game)

    path = os.path.join(ROOT, "index.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(out)
    print("built : %s (%.1f KB, %d sprites, %d maps%s)"
          % (path, len(out.encode("utf-8")) / 1024, len(meta["frames"]), len(maps),
             ", %d pre-rendered" % len(prerender) if prerender else ""))


if __name__ == "__main__":
    main()
