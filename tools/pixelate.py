#!/usr/bin/env python3
"""Quantise a Blender render into the game's pixel-art palette.

Cycles hands back a smooth 24-bit image; the game wants a small palette with
hard edges between colours, the way a 16-bit background was actually drawn.
Median cut picks the palette from the image itself, so the sunset keeps its
own colours instead of being forced into a generic ramp, and the mapping is
nearest-neighbour with no dithering so bands stay crisp.

    python3 tools/pixelate.py                       # every art/blender render
    python3 tools/pixelate.py --colors 24 art/blender/backdrop_dusk.png
"""

import argparse
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from spritecook.imaging import Image            # noqa: E402
from spritecook.imported import read_png        # noqa: E402

# Rec. 601 luma weights: quantising in a luma-weighted space keeps the sky
# ramp from collapsing while the near-black ridges are still told apart.
LUMA = (0.299, 0.587, 0.114)


def _histogram(img):
    counts = {}
    for c in img.px:
        if c[3] == 0:
            continue
        key = c[:3]
        counts[key] = counts.get(key, 0) + 1
    return counts


def _median_cut(counts, want):
    """Split colour space on the widest axis until we have `want` boxes."""
    boxes = [list(counts.items())]
    while len(boxes) < want:
        # Split the box that spans the most colour, weighted by how much of
        # the image it covers - that is where banding would show first.
        target, best = None, -1.0
        for box in boxes:
            if len(box) < 2:
                continue
            spread = max(
                (max(c[i] for c, _ in box) - min(c[i] for c, _ in box)) * LUMA[i]
                for i in range(3)
            )
            weight = spread * (sum(n for _, n in box) ** 0.5)
            if weight > best:
                target, best = box, weight
        if target is None:
            break
        axis = max(range(3), key=lambda i:
                   (max(c[i] for c, _ in target) - min(c[i] for c, _ in target)) * LUMA[i])
        target.sort(key=lambda item: item[0][axis])
        # Cut at the median *pixel*, not the median colour, so both halves
        # carry a similar share of the image.
        half = sum(n for _, n in target) / 2.0
        run, cut = 0, 1
        for i, (_, n) in enumerate(target):
            run += n
            if run >= half:
                cut = min(max(i, 1), len(target) - 1)
                break
        boxes.remove(target)
        boxes.append(target[:cut])
        boxes.append(target[cut:])
    return boxes


def build_palette(img, want):
    boxes = _median_cut(_histogram(img), want)
    palette = []
    for box in boxes:
        total = sum(n for _, n in box)
        if not total:
            continue
        palette.append(tuple(
            int(round(sum(c[i] * n for c, n in box) / total)) for i in range(3)
        ))
    return sorted(set(palette))


def quantise(img, palette):
    out = Image(img.width, img.height)
    cache = {}
    for y in range(img.height):
        for x in range(img.width):
            c = img.get(x, y)
            if c[3] == 0:
                continue
            key = c[:3]
            hit = cache.get(key)
            if hit is None:
                hit = min(palette, key=lambda p: sum(
                    LUMA[i] * (p[i] - key[i]) ** 2 for i in range(3)))
                cache[key] = hit
            out.set(x, y, hit + (c[3],))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sources", nargs="*", help="PNGs to quantise")
    ap.add_argument("--colors", type=int, default=28)
    ap.add_argument("--out", default=os.path.join(ROOT, "art", "backdrops"))
    args = ap.parse_args()

    sources = args.sources or sorted(glob.glob(os.path.join(ROOT, "art", "blender", "*.png")))
    if not sources:
        raise SystemExit("nothing to quantise")
    os.makedirs(args.out, exist_ok=True)
    for src in sources:
        img = read_png(src)
        palette = build_palette(img, args.colors)
        flat = quantise(img, palette)
        dest = os.path.join(args.out, os.path.basename(src))
        with open(dest, "wb") as fh:
            fh.write(flat.to_png())
        print("%-34s -> %s  (%d colours)" % (os.path.basename(src), dest, len(palette)))


if __name__ == "__main__":
    main()
