"""Bake every sprite onto one atlas page."""

import json
import os

from .imaging import Packer
from . import backdrops, beasts, chars, imported, rendered, tiles, tints

# Wide enough for a full-width battle backdrop to sit on the page. The screen
# is not a fixed 320 any more, so neither is this: a sprite wider than the page
# used to be recorded at its real width and then quietly clipped to the page,
# which draws as half a backdrop and nothing anywhere complains.
ATLAS_WIDTH = 512


def cook_all():
    sprites = {}
    sprites.update(tiles.cook())
    sprites.update(chars.cook())
    sprites.update(beasts.cook())
    sprites.update(beasts.cook_icons())
    sprites.update(backdrops.cook())
    # Blender-rendered monsters win over their plotted versions.
    sprites.update(rendered.cook())
    # Externally generated art wins over the procedural sprite of the same
    # name, so the cast can be upgraded one character at a time.
    sprites.update(imported.cook())
    # Recolours run last, so they inherit whichever version of a monster won.
    sprites.update(tints.cook(sprites))
    return sprites


def build(out_dir):
    sprites = cook_all()
    widest = max(s.width for s in sprites.values())
    assert widest <= ATLAS_WIDTH, (
        "%dpx sprite will not fit a %dpx page" % (widest, ATLAS_WIDTH))
    packer = Packer(ATLAS_WIDTH, padding=1)
    # Tallest first keeps the shelves tight and the page small.
    for name in sorted(sprites, key=lambda n: (-sprites[n].height, n)):
        packer.add(name, sprites[name])
    page = packer.bake()

    os.makedirs(out_dir, exist_ok=True)
    png_path = os.path.join(out_dir, "atlas.png")
    json_path = os.path.join(out_dir, "atlas.json")
    with open(png_path, "wb") as fh:
        fh.write(page.to_png())
    meta = {
        "image": "atlas.png",
        "width": page.width,
        "height": page.height,
        "frames": {k: packer.frames[k] for k in sorted(packer.frames)},
    }
    with open(json_path, "w") as fh:
        json.dump(meta, fh, indent=1, sort_keys=True)
    return png_path, json_path, page, meta


def contact_sheet(out_path, scale=3):
    """A zoomed dump of every sprite, for eyeballing the art."""
    from .imaging import Image
    sprites = cook_all()
    names = sorted(sprites)
    cols = 10
    cell_w = max(s.width for s in sprites.values()) + 2
    cell_h = max(s.height for s in sprites.values()) + 2
    rows = (len(names) + cols - 1) // cols
    sheet = Image(cols * cell_w, rows * cell_h, (28, 24, 34, 255))
    for i, name in enumerate(names):
        cx = (i % cols) * cell_w + 1
        cy = (i // cols) * cell_h + 1
        sheet.blit(sprites[name], cx, cy)
    with open(out_path, "wb") as fh:
        fh.write(sheet.scaled(scale).to_png())
    return out_path
