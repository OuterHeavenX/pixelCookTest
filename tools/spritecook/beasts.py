"""Battle monsters and item icons.

Enemies face right (they stand on the left of the battlefield). Everything is
drawn at 1x here and blown up 2x by the renderer, so shapes stay chunky.
"""

import random

from .imaging import Image
from .palette import rgb
from . import chars
from .chars import style

INK = rgb("201826")


def _eye(img, x, y, white=rgb("f4f4ec"), pupil=INK, w=3, h=3):
    img.rect(x, y, w, h, white)
    img.rect(x + w - 2, y + 1, 1, h - 1, pupil)


def _shade(c, amount):
    return (max(0, int(c[0] * (1 - amount))), max(0, int(c[1] * (1 - amount))),
            max(0, int(c[2] * (1 - amount))), c[3])


def _tint(c, amount):
    return (min(255, int(c[0] + (255 - c[0]) * amount)),
            min(255, int(c[1] + (255 - c[1]) * amount)),
            min(255, int(c[2] + (255 - c[2]) * amount)), c[3])


def _speckle(img, seed, color, count, box):
    """Scatter texture pixels inside a box, only over opaque pixels."""
    rng = random.Random(seed)
    x0, y0, x1, y1 = box
    for _ in range(count):
        x, y = rng.randrange(x0, x1), rng.randrange(y0, y1)
        if img.get(x, y)[3]:
            img.set(x, y, color)


def slime():
    img = Image(24, 20)
    body, mid, dark = rgb("58c8e0"), rgb("2f96c0"), rgb("1c6690")
    img.ellipse(12, 14, 11, 7, mid)
    img.ellipse(12, 12, 9, 7, body)
    img.ellipse(12, 11, 8, 5, _tint(body, 0.16))
    # a settled, denser base and a wet highlight up top
    img.ellipse(12, 17, 10, 3, dark)
    img.ellipse(8, 8, 3, 2, rgb("dff8ff"))
    img.ellipse(9, 9, 1, 1, rgb("ffffff"))
    img.ellipse(16, 9, 1, 1, _tint(body, 0.5))
    for bx, by in ((6, 13), (17, 14), (11, 16)):
        img.ellipse(bx, by, 1, 1, _tint(body, 0.35))
    _eye(img, 8, 10, w=3, h=3)
    _eye(img, 14, 10, w=3, h=3)
    img.rect(11, 15, 3, 1, dark)
    img.outline(INK)
    return img


def wolf():
    img = Image(30, 22)
    fur, fur_lo, fur_hi = rgb("7a6a86"), rgb("4c4058"), rgb("a596b0")
    img.ellipse(15, 12, 10, 6, fur)
    img.ellipse(13, 10, 8, 4, fur_hi)
    img.rect(4, 8, 3, 8, fur_lo)  # tail
    img.rect(2, 5, 3, 6, fur_lo)
    img.ellipse(24, 9, 5, 4, fur)          # head
    img.rect(26, 8, 4, 3, fur_hi)          # snout
    img.rect(28, 9, 2, 2, rgb("2b2230"))
    img.rect(20, 3, 2, 4, fur)             # ears
    img.rect(24, 3, 2, 4, fur)
    img.rect(20, 3, 2, 2, fur_lo)
    img.rect(24, 3, 2, 2, fur_lo)
    for lx in (9, 13, 19, 23):
        img.rect(lx, 16, 3, 5, fur_lo)
        img.rect(lx, 16, 1, 5, _shade(fur_lo, 0.25))
        img.rect(lx, 20, 3, 1, rgb("2b2230"))
    # belly shadow and a ruff of fur along the spine
    img.ellipse(15, 15, 9, 2, _shade(fur_lo, 0.15))
    for sx in range(8, 24, 3):
        img.rect(sx, 6, 2, 2, fur_hi)
    _speckle(img, 7, _shade(fur, 0.18), 26, (5, 7, 27, 17))
    _speckle(img, 8, fur_hi, 16, (7, 6, 24, 13))
    img.rect(23, 8, 3, 2, rgb("f0d040"))   # eye
    img.rect(25, 9, 1, 1, INK)
    img.rect(27, 11, 1, 2, rgb("f4f4ec"))  # fang
    img.outline(INK)
    return img


def bat():
    img = Image(28, 20)
    wing, wing_lo, body = rgb("6b3f7a"), rgb("452650"), rgb("3a2a44")
    for flip in (-1, 1):
        base = 13 + flip * 3
        for i in range(6):
            x = base + flip * i * 2
            img.rect(x, 4 + i, 2, 9 - i, wing if i % 2 == 0 else wing_lo)
        # finger bones across the membrane
        for i in range(0, 6, 2):
            img.rect(base + flip * i * 2, 4 + i, 1, 9 - i, _tint(wing, 0.25))
        img.rect(base + flip * 10, 9, 2, 3, wing_lo)
    img.ellipse(14, 11, 4, 5, body)
    img.rect(11, 3, 2, 5, body)
    img.rect(16, 3, 2, 5, body)
    _eye(img, 11, 9, white=rgb("f05a5a"), pupil=INK, w=2, h=2)
    _eye(img, 15, 9, white=rgb("f05a5a"), pupil=INK, w=2, h=2)
    img.rect(12, 13, 4, 1, rgb("f4f4ec"))
    img.outline(INK)
    return img


def wisp():
    img = Image(24, 24)
    core, glow, halo = rgb("f0f4a0"), rgb("9fe8c0"), rgb("4fa890")
    img.ellipse(12, 12, 10, 10, _shade(halo, 0.35))
    img.ellipse(12, 12, 8, 8, halo)
    img.ellipse(12, 12, 6, 6, glow)
    img.ellipse(12, 11, 4, 4, _tint(glow, 0.3))
    img.ellipse(12, 11, 3, 3, core)
    img.ellipse(11, 10, 1, 1, rgb("ffffff"))
    # wisps of light trailing off the halo
    for wx, wy in ((3, 9), (20, 14), (7, 21), (18, 4)):
        img.ellipse(wx, wy, 1, 1, _tint(glow, 0.4))
    for x, y in ((4, 5), (19, 7), (6, 19), (18, 18), (12, 2), (12, 21)):
        img.rect(x, y, 1, 1, core)
    _eye(img, 9, 10, white=rgb("1c3a34"), pupil=rgb("1c3a34"), w=2, h=3)
    _eye(img, 13, 10, white=rgb("1c3a34"), pupil=rgb("1c3a34"), w=2, h=3)
    return img


def ogre():
    """The wilderness boss: a slab of a humanoid, 32x40."""
    img = Image(32, 40)
    skin, skin_lo, skin_hi = rgb("7fa84f"), rgb("537233"), rgb("a6cb6c")
    cloth, cloth_lo = rgb("8a5a34"), rgb("5c3a20")
    img.rect(6, 16, 20, 14, skin)          # torso
    img.rect(6, 16, 20, 3, skin_hi)
    img.rect(7, 26, 18, 5, cloth)          # loincloth
    img.rect(7, 30, 18, 2, cloth_lo)
    img.ellipse(15, 10, 9, 8, skin)        # head
    img.ellipse(15, 8, 8, 5, skin_hi)
    img.rect(4, 8, 3, 4, skin_lo)          # ears
    img.rect(25, 8, 3, 4, skin_lo)
    img.rect(8, 3, 3, 5, rgb("e8e0c8"))    # horns
    img.rect(21, 3, 3, 5, rgb("e8e0c8"))
    _eye(img, 10, 9, white=rgb("f2d15a"), w=4, h=4)
    _eye(img, 18, 9, white=rgb("f2d15a"), w=4, h=4)
    img.rect(11, 15, 10, 2, rgb("3a2020"))  # mouth
    img.rect(12, 14, 2, 2, rgb("f4f4ec"))   # tusks
    img.rect(18, 14, 2, 2, rgb("f4f4ec"))
    img.rect(1, 18, 6, 12, skin)            # arms
    img.rect(25, 18, 6, 12, skin)
    img.rect(1, 18, 6, 2, skin_hi)
    img.rect(25, 18, 6, 2, skin_hi)
    # bulk: pectoral and belly shading, plus a lit top edge on the arms
    img.ellipse(11, 21, 4, 3, _tint(skin, 0.16))
    img.ellipse(20, 21, 4, 3, _tint(skin, 0.16))
    img.ellipse(15, 28, 8, 3, _shade(skin, 0.16))
    img.rect(1, 18, 6, 1, _tint(skin_hi, 0.25))
    img.rect(25, 18, 6, 1, _tint(skin_hi, 0.25))
    _speckle(img, 21, _shade(skin, 0.14), 30, (7, 17, 25, 31))
    img.rect(7, 18, 1, 12, skin_lo)         # arm seams
    img.rect(24, 18, 1, 12, skin_lo)
    img.rect(15, 20, 2, 6, skin_lo)         # sternum
    img.rect(9, 23, 14, 1, skin_lo)
    img.rect(8, 31, 7, 8, skin_lo)          # legs
    img.rect(17, 31, 7, 8, skin_lo)
    img.rect(24, 4, 5, 16, rgb("7a5a34"))   # club
    img.rect(23, 2, 7, 6, rgb("9c7440"))
    for kx, ky in ((24, 3), (28, 6), (25, 7)):
        img.rect(kx, ky, 2, 2, rgb("5c3a20"))
    img.outline(INK)
    return img


GOBLIN_STYLE = style(
    skin=rgb("8ab84f"), skin_sh=rgb("5f8534"),
    hair=rgb("3a2a1e"), hair_dk=rgb("241a12"),
    cloth=rgb("9c6b3c"), cloth_dk=rgb("6b4423"), trim=rgb("c8a06a"),
    boot=rgb("4a3423"), weapon="sword", weapon_dk=rgb("6b4423"),
    prop="sword", build=-1)

BANDIT_STYLE = style(
    skin=rgb("d8a878"), skin_sh=rgb("ab7d52"),
    hair=rgb("2a2430"), hair_dk=rgb("18141d"),
    cloth=rgb("7a6f92"), cloth_dk=rgb("4c4664"), trim=rgb("c04a58"),
    boot=rgb("3a3348"), weapon="sword", weapon_dk=rgb("8a6a3a"),
    prop="sword", apron=rgb("8f5a4a"))


def _goblin_ears(img):
    """One swept-back ear. He is drawn in profile, so the far ear is hidden."""
    green = rgb("8ab84f")
    for i in range(4):
        x = 6 - i
        y = 8 + i
        img.rect(x, y, 2, 2, green if i < 2 else _shade(green, 0.18))
        img.rect(x, y - 1, 2, 1, INK)
        img.rect(x, y + 2, 2, 1, INK)
    img.rect(5, 8, 2, 1, _tint(green, 0.35))
    return img


def cook():
    out = {
        "e_slime": slime(),
        "e_wolf": wolf(),
        "e_bat": bat(),
        "e_wisp": wisp(),
        "e_ogre": ogre(),
    }
    goblin = chars.char_side(GOBLIN_STYLE, 0)
    out["e_goblin"] = _goblin_ears(goblin)
    out["e_bandit"] = chars.char_side(BANDIT_STYLE, 0)
    return out


ICON_ART = {
    "i_potion": [
        "  ####  ",
        "  #@@#  ",
        " ##@@## ",
        " #7777# ",
        "#777777#",
        "#767777#",
        "#777777#",
        " ###### ",
    ],
    "i_ether": [
        "  ####  ",
        "  #@@#  ",
        " ##@@## ",
        " #bbbb# ",
        "#bbbbbb#",
        "#b6bbbb#",
        "#bbbbbb#",
        " ###### ",
    ],
    "i_phoenix": [
        "   ##   ",
        "  #11#  ",
        " #1771# ",
        "#177771#",
        "#177771#",
        " #1771# ",
        "  #11#  ",
        "   ##   ",
    ],
    "i_sword": [
        "     ###",
        "    ##8#",
        "   ##8##",
        "  ##8## ",
        " #282#  ",
        "##8#    ",
        "#9#     ",
        "##      ",
    ],
    "i_staff": [
        "   ###  ",
        "  #bb#  ",
        "  #b6#  ",
        "   ##9# ",
        "   #9#  ",
        "  #9#   ",
        " #9#    ",
        " ##     ",
    ],
    "i_shield": [
        "########",
        "#8888888",
        "#8111188",
        "#8177118",
        "#8811188",
        " #88888#",
        "  #888# ",
        "   ###  ",
    ],
    "i_gil": [
        "  ####  ",
        " #1111# ",
        "#112211#",
        "#121121#",
        "#121121#",
        "#112211#",
        " #1111# ",
        "  ####  ",
    ],
    "i_heart": [
        " ## ##  ",
        "#77#77# ",
        "#767777#",
        "#777777#",
        " #7777# ",
        "  #77#  ",
        "   ##   ",
        "        ",
    ],
}

ICON_PAL = {
    " ": None,
    "#": INK,
    "@": rgb("bfe8ff"),
    "7": rgb("e0576b"),
    "6": rgb("ffffff"),
    "b": rgb("5a8fe0"),
    "1": rgb("f0c04a"),
    "2": rgb("a87a20"),
    "8": rgb("c8ccd8"),
    "9": rgb("8a6a3a"),
}


def cook_icons():
    from .imaging import from_art
    return {name: from_art(rows, ICON_PAL) for name, rows in ICON_ART.items()}
