"""Cold-country recolours of monsters that already exist.

A Rimewolf is a direwolf that has been out in it too long, and a Mereling is
what the lake has been growing. Rather than model them again, their sprites are
the existing ones pushed toward the cold: hue rotated to blue, saturation
pulled down, highlights lifted so they read as frost rather than as mud.

Doing this at cook time rather than with a runtime tint keeps the two builds
byte-identical - neither renderer has to know that some monsters are recolours.
"""

from .imaging import Image
from .imported import read_png  # noqa: F401  (kept for symmetry with rendered.py)

# Which finished sprite each cold variant is cut from.
ICE_VARIANTS = {
    "e_wolf_ice": "e_wolf",
    "e_slime_ice": "e_slime",
    "e_wight_ice": "e_wight",
}


def chill(img, strength=0.88, lift=0.30):
    """Push a sprite toward blue-white without flattening it to one colour."""
    out = Image(img.width, img.height)
    for y in range(img.height):
        for x in range(img.width):
            p = img.get(x, y)
            if not p[3]:
                continue
            lum = 0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2]
            # Toward a cold grey of the same brightness, then lifted and
            # tinted so the light side goes to ice rather than to white.
            r = p[0] + (lum * 0.86 - p[0]) * strength
            g = p[1] + (lum * 0.97 - p[1]) * strength
            b = p[2] + (lum * 1.26 + 38 - p[2]) * strength
            k = (lum / 255.0) * lift
            r += (210 - r) * k
            g += (235 - g) * k
            b += (255 - b) * k
            out.set(x, y, (max(0, min(255, int(r))), max(0, min(255, int(g))),
                           max(0, min(255, int(b))), p[3]))
    return out


def cook(sprites):
    """Called with everything cooked so far, so it can recolour the finished
    sprite whether that came from a plotter or from Blender."""
    out = {}
    for name, source in ICE_VARIANTS.items():
        if source in sprites:
            out[name] = chill(sprites[source])
    return out
