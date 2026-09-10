"""A light grade for the cast, so they stand in the world instead of on it.

The Blender pictures are graded toward the reference: cool, misty, low in
saturation. The sprites were painted for the old tile art and read a step
more saturated than the ground they walk on. This pulls them a quarter of the
way toward the pictures' palette - less than the pictures themselves get,
because a character has to stay legible against them - and leaves the dark
outlines alone so nothing goes soft.
"""

from .imaging import Image

# Which sprite families are people and monsters. Tiles, item icons and the
# battle backdrops keep their colour.
CAST_PREFIXES = ("aldric", "bram", "lyra", "mira", "sera", "child", "elder",
                 "guard", "merchant", "villager", "e_")

TINT = (0.62, 0.72, 0.68)          # the pictures' sage, as a multiplier on grey
KEEP = 0.76                        # saturation kept: 1.0 is untouched
MIST = 0.06                        # how far mid-tones lean toward the tint


def is_cast(name):
    return name.startswith(CAST_PREFIXES)


def grade_sprite(img):
    out = Image(img.width, img.height)
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = img.get(x, y)
            if a == 0:
                out.set(x, y, (r, g, b, a))
                continue
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            # Outlines and deep shadow stay as drawn: they are the sprite's
            # shape, and softening them is what makes a graded sprite mushy.
            if lum < 40:
                out.set(x, y, (r, g, b, a))
                continue
            warm = max(0.0, min(1.0, (r - b) / 96.0))
            keep = KEEP + 0.12 * warm       # skin and hair keep a little more
            r2 = lum + (r - lum) * keep
            g2 = lum + (g - lum) * keep
            b2 = lum + (b - lum) * keep
            k = MIST * (1.0 - abs(lum - 128.0) / 128.0)   # mid-tones only
            r2 = r2 * (1 - k) + 255 * TINT[0] * k
            g2 = g2 * (1 - k) + 255 * TINT[1] * k
            b2 = b2 * (1 - k) + 255 * TINT[2] * k
            out.set(x, y, (int(max(0, min(255, r2))), int(max(0, min(255, g2))),
                           int(max(0, min(255, b2))), a))
    return out


def grade_cast(sprites):
    return {name: (grade_sprite(img) if is_cast(name) else img)
            for name, img in sprites.items()}
