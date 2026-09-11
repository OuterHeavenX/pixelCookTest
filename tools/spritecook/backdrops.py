"""Battle backdrops, rendered in Blender and quantised to the game palette.

tools/blender/backdrop.py builds the scene and renders it; tools/pixelate.py
flattens the render into a small palette. This step only carries the finished
PNGs onto the atlas, so the game draws a backdrop exactly like any other
sprite and neither runtime needs a second image loader.
"""

import os

from .imported import read_png

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIR = os.path.join(ROOT, "art", "backdrops")

# mood -> sprite name the battle renderer asks for.
MOODS = {"dusk": "bg_dusk", "night": "bg_night", "barrow": "bg_barrow", "mere": "bg_mere"}


def cook():
    out = {}
    for mood, name in MOODS.items():
        path = os.path.join(DIR, "backdrop_%s.png" % mood)
        if not os.path.exists(path):
            continue
        out[name] = read_png(path)
    return out
