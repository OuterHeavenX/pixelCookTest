"""Fold the Blender-rendered monsters onto the atlas.

tools/blender/enemies.py models and renders them; tools/spritedown.py takes
each render down to sprite size, quantises it and puts the ink outline back on.
This step only carries the finished PNGs onto the same page as everything else,
so the game draws a rendered monster exactly like a plotted one.

Not every monster is better rendered, and the ones that are not stay plotted.
The pattern is consistent: a render wins wherever the character IS its volume -
a sphere catching a light, a wing folding over itself, an ogre's mass - and
loses on thin figures whose legibility comes from hard black edges around small
features. The goblin, the bandit and the skeleton are all that second kind at
24x32, and averaging a soft render down to that size takes exactly the edges
away. The goblin and bandit also share the parametric humanoid the player party
is built from, so plotted keeps them matching the heroes across from them.

This list is the record of that decision rather than an accident. Adding a name
to it is all it takes to switch one over.
"""

import json
import os

from .imported import read_png

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIR = os.path.join(ROOT, "art", "enemies")

# The monsters the render wins on: anything with volume to catch a light.
USE = (
    "e_slime",      # the light wrapping a sphere is the whole character
    "e_bat",        # membrane wings occlude each other
    "e_wolf",       # a body with a near side and a far side
    "e_wisp",       # concentric shells of glow
    "e_wight",      # a hood that is a hollow
    "e_ogre",       # mass, which is what an ogre is for
    "e_warden",     # a coat heavy with water, and one lamp in it
)


def cook():
    out = {}
    for name in USE:
        path = os.path.join(DIR, name + ".png")
        if not os.path.exists(path):
            continue
        out[name] = read_png(path)
    return out
