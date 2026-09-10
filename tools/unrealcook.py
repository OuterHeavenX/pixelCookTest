#!/usr/bin/env python3
"""unrealcook - stage the cooked assets for the Unreal project.

The third runtime reads exactly the same atlas, maps, rules and font as the
other two. This copies them under unreal/Content/Rivenbrook/, which the plugin
loads off disk at startup rather than importing as Unreal assets - the whole
point of the pipeline is that there is one cooked copy of everything and every
runtime reads it, so turning the atlas into a .uasset would be a fourth copy
that can drift.

    python3 tools/unrealcook.py
"""

import json
import os
import shutil

import godotcook

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNREAL_DATA = os.path.join(ROOT, "unreal", "Content", "Rivenbrook")


def build():
    os.makedirs(UNREAL_DATA, exist_ok=True)
    copied = []
    for name in ("atlas.png", "atlas.json", "maps.json", "gamedata.json"):
        shutil.copyfile(os.path.join(ROOT, "assets", name),
                        os.path.join(UNREAL_DATA, name))
        copied.append(name)

    # The same glyph table the Godot build gets, parsed out of src/font.js by
    # the same reader - one font, three runtimes.
    font = godotcook.parse_font(os.path.join(ROOT, "src", "font.js"))
    with open(os.path.join(UNREAL_DATA, "font.json"), "w") as fh:
        json.dump(font, fh, indent=0, sort_keys=True)
    copied.append("font.json")
    return copied, len(font)


if __name__ == "__main__":
    copied, glyphs = build()
    print("unreal: unreal/Content/Rivenbrook/{%s} (%d glyphs)"
          % (", ".join(copied), glyphs))
