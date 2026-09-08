"""Fold externally generated art (SpriteCook) into the cooked atlas.

Source PNGs live in art/spritecook/ alongside a MANIFEST.json that says which
game sprite names each file supplies and how tall it should end up. Sprites are
cropped to their silhouette and area-averaged down, then packed into the same
atlas as the procedural art, so the game never learns where a sprite came from.

A name imported here overrides the procedural sprite of the same name, which is
what lets the party be upgraded a character at a time.
"""

import json
import os
import struct
import zlib

from .imaging import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ART_DIR = os.path.join(ROOT, "art", "spritecook")

_FILTERS = {0: "none", 1: "sub", 2: "up", 3: "average", 4: "paeth"}


def read_png(path):
    """Minimal PNG reader: 8-bit greyscale, RGB, palette or RGBA."""
    raw = open(path, "rb").read()
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("%s is not a PNG" % path)
    pos = 8
    idat = b""
    plte = trns = None
    width = height = depth = color = 0
    while pos < len(raw):
        length = struct.unpack(">I", raw[pos:pos + 4])[0]
        tag = raw[pos + 4:pos + 8]
        data = raw[pos + 8:pos + 8 + length]
        pos += 12 + length
        if tag == b"IHDR":
            width, height, depth, color = struct.unpack(">IIBB", data[:10])
            if depth != 8:
                raise ValueError("%s: only 8-bit PNGs are supported" % path)
        elif tag == b"IDAT":
            idat += data
        elif tag == b"PLTE":
            plte = data
        elif tag == b"tRNS":
            trns = data
        elif tag == b"IEND":
            break

    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color]
    stride = width * channels
    buf = zlib.decompress(idat)
    rows = bytearray()
    prev = bytearray(stride)
    i = 0
    for _ in range(height):
        ftype = buf[i]
        i += 1
        line = bytearray(buf[i:i + stride])
        i += stride
        for x in range(stride):
            a = line[x - channels] if x >= channels else 0
            b = prev[x]
            c = prev[x - channels] if x >= channels else 0
            if ftype == 1:
                line[x] = (line[x] + a) & 255
            elif ftype == 2:
                line[x] = (line[x] + b) & 255
            elif ftype == 3:
                line[x] = (line[x] + (a + b) // 2) & 255
            elif ftype == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pred = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[x] = (line[x] + pred) & 255
            elif ftype != 0:
                raise ValueError("%s: unknown PNG filter %d" % (path, ftype))
        rows += line
        prev = line

    img = Image(width, height)
    for y in range(height):
        for x in range(width):
            o = y * stride + x * channels
            if color == 6:
                img.set(x, y, (rows[o], rows[o + 1], rows[o + 2], rows[o + 3]))
            elif color == 2:
                img.set(x, y, (rows[o], rows[o + 1], rows[o + 2], 255))
            elif color == 0:
                v = rows[o]
                img.set(x, y, (v, v, v, 255))
            elif color == 4:
                v = rows[o]
                img.set(x, y, (v, v, v, rows[o + 1]))
            else:
                idx = rows[o]
                r, g, b = plte[idx * 3:idx * 3 + 3]
                alpha = trns[idx] if trns and idx < len(trns) else 255
                img.set(x, y, (r, g, b, alpha))
    return img


def crop_to_silhouette(img, alpha_min=8):
    xs, ys = [], []
    for y in range(img.height):
        for x in range(img.width):
            if img.get(x, y)[3] >= alpha_min:
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


def downscale(img, target_w, target_h, alpha_cut=110):
    """Area-average, then hard-threshold alpha so the silhouette stays crisp
    instead of fading into a halo at the edges."""
    out = Image(target_w, target_h)
    for ty in range(target_h):
        sy0 = int(ty * img.height / target_h)
        sy1 = max(sy0 + 1, int((ty + 1) * img.height / target_h))
        for tx in range(target_w):
            sx0 = int(tx * img.width / target_w)
            sx1 = max(sx0 + 1, int((tx + 1) * img.width / target_w))
            r = g = b = 0.0
            alpha_sum = 0.0
            weight = 0.0
            count = 0
            for sy in range(sy0, min(sy1, img.height)):
                for sx in range(sx0, min(sx1, img.width)):
                    p = img.get(sx, sy)
                    w = p[3] / 255.0
                    r += p[0] * w
                    g += p[1] * w
                    b += p[2] * w
                    alpha_sum += p[3]
                    weight += w
                    count += 1
            if count and weight > 0 and alpha_sum / count >= alpha_cut:
                out.set(tx, ty, (int(r / weight), int(g / weight), int(b / weight), 255))
    return out


def fit_height(img, target_h):
    """Scale to a target height, keeping the aspect ratio on an even width."""
    scale = target_h / float(img.height)
    target_w = max(1, int(round(img.width * scale)))
    if target_w % 2:
        target_w += 1
    return downscale(img, target_w, target_h)


def cook():
    """Return {game sprite name: Image} for everything in the manifest."""
    manifest_path = os.path.join(ART_DIR, "MANIFEST.json")
    if not os.path.exists(manifest_path):
        return {}
    manifest = json.load(open(manifest_path))
    out = {}
    for key, entry in sorted(manifest.get("assets", {}).items()):
        targets = entry.get("targets")
        if not targets:
            continue  # source art held for reference, not wired to the game yet
        path = os.path.join(ART_DIR, entry.get("file", key + ".png"))
        if not os.path.exists(path):
            raise ValueError("manifest references missing file: %s" % path)
        art = crop_to_silhouette(read_png(path))
        height = int(entry.get("height", 32))
        scaled = fit_height(art, height)
        for name in targets:
            out[name] = scaled
    return out
