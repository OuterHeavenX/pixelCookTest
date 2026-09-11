#!/usr/bin/env python3
"""godotcook - stage the cooked assets for the Godot project.

The Godot build reads exactly the same atlas, maps and rules as the browser
build; this copies them under godot/assets/ along with the UI typeface.

    python3 tools/godotcook.py
"""

import json
import os
import re
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GODOT_ASSETS = os.path.join(ROOT, "godot", "assets")

GLYPH_RE = re.compile(r"^\s*(?:'(.)'|\"(.)\")\s*:\s*\[(.*?)\],\s*$")
ROW_RE = re.compile(r"'([01]{5})'")


def parse_font(path):
    """Read the glyph table out of src/font.js without needing a JS runtime."""
    font = {}
    for line in open(path, encoding="utf-8"):
        m = GLYPH_RE.match(line)
        if not m:
            continue
        ch = m.group(1) if m.group(1) is not None else m.group(2)
        rows = ROW_RE.findall(m.group(3))
        if len(rows) != 7:
            raise ValueError("glyph %r has %d rows, expected 7" % (ch, len(rows)))
        font[ch] = rows
    if not font:
        raise ValueError("no glyphs parsed from %s" % path)
    return font


def build():
    os.makedirs(GODOT_ASSETS, exist_ok=True)
    copied = []
    for name in ("atlas.png", "atlas.json", "maps.json", "gamedata.json"):
        src = os.path.join(ROOT, "assets", name)
        shutil.copyfile(src, os.path.join(GODOT_ASSETS, name))
        copied.append(name)

    # The Blender pictures, where a map has them: the base picture, its
    # overlay of roofs and treetops, and the water frames. The field draws
    # them in place of the tiles exactly as the browser build does.
    pre_src = os.path.join(ROOT, "art", "prerender")
    pre_dst = os.path.join(GODOT_ASSETS, "prerender")
    if os.path.isdir(pre_dst):
        for name in os.listdir(pre_dst):
            if name.endswith(".png"):
                os.remove(os.path.join(pre_dst, name))
    pictures = 0
    if os.path.isdir(pre_src):
        os.makedirs(pre_dst, exist_ok=True)
        for name in sorted(os.listdir(pre_src)):
            if name.endswith(".png"):
                shutil.copyfile(os.path.join(pre_src, name), os.path.join(pre_dst, name))
                pictures += 1
    if pictures:
        copied.append("prerender/ (%d pictures)" % pictures)

    # The UI typeface, the same files the browser build embeds, so both
    # runtimes set their menus in the same face.
    fonts_src = os.path.join(ROOT, "assets", "fonts")
    fonts_dst = os.path.join(GODOT_ASSETS, "fonts")
    os.makedirs(fonts_dst, exist_ok=True)
    faces = 0
    for name in sorted(os.listdir(fonts_src)):
        if name.endswith((".woff2", ".txt")):
            shutil.copyfile(os.path.join(fonts_src, name), os.path.join(fonts_dst, name))
            faces += name.endswith(".woff2")
    copied.append("fonts/ (%d faces)" % faces)

    font = parse_font(os.path.join(ROOT, "src", "font.js"))
    return copied, len(font)


if __name__ == "__main__":
    copied, glyphs = build()
    print("godot : godot/assets/{%s} (%d glyphs)" % (", ".join(copied), glyphs))
