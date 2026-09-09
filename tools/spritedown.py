#!/usr/bin/env python3
"""Turn a Blender render into a game sprite.

Area-average it down to the sprite's size, hard-threshold the alpha so the
silhouette stays crisp instead of fading into a halo, quantise the colours so
it reads as pixel art rather than as a small photograph, and put the ink
outline back on - every hand-drawn sprite in this game has one, and it is what
lets a monster read against grass, flagstones or a night sky.

    python3 tools/spritedown.py                  # everything in art/enemies/raw
    python3 tools/spritedown.py --colors 12
"""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from pixelate import build_palette, quantise          # noqa: E402
from spritecook.imaging import Image                  # noqa: E402
from spritecook.imported import downscale, read_png   # noqa: E402
from spritecook.palette import INK                    # noqa: E402

RAW = os.path.join(ROOT, "art", "enemies", "raw")
OUT = os.path.join(ROOT, "art", "enemies")


def crop_alpha(img):
    """Cut the render down to what it actually drew."""
    xs, ys = [], []
    for y in range(img.height):
        for x in range(img.width):
            if img.get(x, y)[3]:
                xs.append(x)
                ys.append(y)
    if not xs:
        return img
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    out = Image(x1 - x0 + 1, y1 - y0 + 1)
    for y in range(out.height):
        for x in range(out.width):
            out.set(x, y, img.get(x0 + x, y0 + y))
    return out


def fit_into(img, w, h):
    """Scale the crop to the largest size that fits, then stand it on the
    bottom edge of a w x h frame.

    Fitting the camera to the model in Blender was not enough: a bounding box
    is bigger than the silhouette inside it, and monsters came out rattling
    around in frames they should have filled. Measuring the pixels that were
    actually drawn is exact."""
    scale = min(w / float(img.width), h / float(img.height))
    tw = max(1, min(w, int(round(img.width * scale))))
    th = max(1, min(h, int(round(img.height * scale))))
    small = downscale(img, tw, th)
    out = Image(w, h)
    out.blit(small, (w - tw) // 2, h - th)
    return out


def punch(img, contrast=1.30, saturation=1.28):
    """Lift contrast and saturation before quantising.

    A soft render averaged down to 24 pixels arrives as a wash of near
    identical mid-tones, and a median cut over those gives a sprite you cannot
    read. The hand-drawn monsters get their legibility from hard steps between
    colours; this puts the steps back before the palette is chosen."""
    out = Image(img.width, img.height)
    for y in range(img.height):
        for x in range(img.width):
            p = img.get(x, y)
            if not p[3]:
                continue
            lum = 0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2]
            vals = []
            for i in range(3):
                v = lum + (p[i] - lum) * saturation          # saturation
                v = 128 + (v - 128) * contrast               # contrast
                vals.append(max(0, min(255, int(round(v)))))
            out.set(x, y, (vals[0], vals[1], vals[2], p[3]))
    return out


def cook_one(path, size, colors):
    raw = read_png(path)
    w, h = size
    # Leave a pixel of room all round for the outline to live in.
    small = fit_into(crop_alpha(raw), w - 2, h - 2)
    small = punch(small)
    palette = build_palette(small, colors)
    flat = quantise(small, palette)
    out = Image(w, h)
    out.blit(flat, 1, 1)
    out.outline(INK)
    return out, len(palette)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--colors", type=int, default=14)
    ap.add_argument("--only", nargs="*", default=None)
    args = ap.parse_args()

    manifest = os.path.join(RAW, "MANIFEST.json")
    if not os.path.exists(manifest):
        raise SystemExit("no renders yet - run tools/blender/enemies.py first")
    sizes = json.load(open(manifest))
    names = args.only or sorted(sizes)
    names = [n if n.startswith("e_") else "e_" + n for n in names]
    os.makedirs(OUT, exist_ok=True)
    for name in names:
        if name not in sizes:
            raise SystemExit("no render for %s" % name)
        path = os.path.join(RAW, name + ".png")
        img, used = cook_one(path, sizes[name], args.colors)
        dest = os.path.join(OUT, name + ".png")
        with open(dest, "wb") as fh:
            fh.write(img.to_png())
        print("%-12s -> %s  (%dx%d, %d colours)"
              % (name, dest, img.width, img.height, used))


if __name__ == "__main__":
    main()
