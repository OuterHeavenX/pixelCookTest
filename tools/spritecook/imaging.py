"""Tiny dependency-free imaging core for spritecook.

Provides an RGBA raster buffer, a PNG encoder built on zlib, and a shelf
packer used to lay every cooked sprite out on one atlas page.
"""

import struct
import zlib

TRANSPARENT = (0, 0, 0, 0)


class Image:
    """A mutable RGBA raster."""

    def __init__(self, width, height, fill=TRANSPARENT):
        self.width = width
        self.height = height
        self.px = [fill] * (width * height)

    def get(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.px[y * self.width + x]
        return TRANSPARENT

    def set(self, x, y, color):
        if color is None:
            return
        if 0 <= x < self.width and 0 <= y < self.height:
            self.px[y * self.width + x] = color

    def blend(self, x, y, color):
        """Source-over composite of one pixel."""
        if color is None or color[3] == 0:
            return
        if color[3] == 255:
            self.set(x, y, color)
            return
        dst = self.get(x, y)
        sa = color[3] / 255.0
        da = dst[3] / 255.0
        out_a = sa + da * (1 - sa)
        if out_a <= 0:
            self.set(x, y, TRANSPARENT)
            return
        out = tuple(
            int(round((color[i] * sa + dst[i] * da * (1 - sa)) / out_a)) for i in range(3)
        )
        self.set(x, y, (out[0], out[1], out[2], int(round(out_a * 255))))

    def rect(self, x, y, w, h, color):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.set(xx, yy, color)

    def ellipse(self, cx, cy, rx, ry, color):
        for y in range(int(cy - ry), int(cy + ry) + 1):
            for x in range(int(cx - rx), int(cx + rx) + 1):
                dx = (x - cx + 0.5) / max(rx, 0.001)
                dy = (y - cy + 0.5) / max(ry, 0.001)
                if dx * dx + dy * dy <= 1.0:
                    self.set(x, y, color)

    def outline(self, color):
        """Trace a 1px silhouette outline around every opaque pixel."""
        edges = []
        for y in range(self.height):
            for x in range(self.width):
                if self.get(x, y)[3]:
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    if self.get(x + dx, y + dy)[3] == 255:
                        edges.append((x, y))
                        break
        for x, y in edges:
            self.set(x, y, color)
        return self

    def scaled(self, factor):
        out = Image(self.width * factor, self.height * factor)
        for y in range(out.height):
            for x in range(out.width):
                out.set(x, y, self.get(x // factor, y // factor))
        return out

    def blit(self, src, dx, dy):
        for y in range(src.height):
            for x in range(src.width):
                c = src.get(x, y)
                if c[3]:
                    self.set(dx + x, dy + y, c)

    def flipped_x(self):
        out = Image(self.width, self.height)
        for y in range(self.height):
            for x in range(self.width):
                out.set(self.width - 1 - x, y, self.get(x, y))
        return out

    def to_png(self):
        raw = bytearray()
        for y in range(self.height):
            raw.append(0)  # filter type 0 (None)
            row = self.px[y * self.width:(y + 1) * self.width]
            for r, g, b, a in row:
                raw += bytes((r, g, b, a))
        return _png_bytes(self.width, self.height, bytes(raw))


def _chunk(tag, data):
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def _png_bytes(width, height, raw):
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(raw, 9))
        + _chunk(b"IEND", b"")
    )


def from_art(rows, palette):
    """Build an Image from character-grid art.

    `rows` is a list of equal-length strings; each character is looked up in
    `palette`. A character mapping to None (or absent) stays transparent.
    """
    h = len(rows)
    w = max(len(r) for r in rows) if h else 0
    img = Image(w, h)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            color = palette.get(ch)
            if color is not None:
                img.set(x, y, color)
    return img


class Packer:
    """Shelf packer: keeps the atlas tidy and deterministic."""

    def __init__(self, width, padding=1):
        self.width = width
        self.padding = padding
        self.x = padding
        self.y = padding
        self.shelf_height = 0
        self.frames = {}
        self.entries = []

    def add(self, name, img):
        if name in self.frames:
            raise ValueError("duplicate sprite name: %s" % name)
        if self.x + img.width + self.padding > self.width:
            self.x = self.padding
            self.y += self.shelf_height + self.padding
            self.shelf_height = 0
        self.frames[name] = [self.x, self.y, img.width, img.height]
        self.entries.append((self.x, self.y, img))
        self.x += img.width + self.padding
        self.shelf_height = max(self.shelf_height, img.height)
        return self.frames[name]

    def bake(self):
        height = self.y + self.shelf_height + self.padding
        # Power-of-two-ish height keeps the texture friendly; not required, but neat.
        page = Image(self.width, height)
        for x, y, img in self.entries:
            page.blit(img, x, y)
        return page
