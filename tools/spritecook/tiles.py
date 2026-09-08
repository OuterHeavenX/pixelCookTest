"""16x16 terrain and prop tiles.

Ground tiles are textured with a seeded RNG so every tile is unique but
reproducible; props are hand-authored pixel art so their silhouettes read
clearly at 1x.
"""

import random

from .imaging import Image, from_art
from .palette import TILE_PALETTE as PAL

TILE = 16


def _noise(seed, base, speckles):
    """A flat tile dusted with speckles: (colour, count) pairs."""
    rng = random.Random(seed)
    img = Image(TILE, TILE, base)
    for color, count in speckles:
        for _ in range(count):
            img.set(rng.randrange(TILE), rng.randrange(TILE), color)
    return img


def _tufts(img, seed, color, count, length=2):
    rng = random.Random(seed)
    for _ in range(count):
        x = rng.randrange(TILE)
        y = rng.randrange(TILE - length)
        for i in range(length):
            img.set(x, y + i, color)
        img.set(x + 1, y + length - 1, color)
    return img


def grass(seed=1):
    img = _noise(seed, PAL[","], [(PAL["."], 26), (PAL[":"], 22)])
    return _tufts(img, seed + 90, PAL[":"], 7)


def grass_flowers(seed=2):
    img = grass(seed)
    rng = random.Random(seed + 7)
    for color in (PAL["f"], PAL["F"], PAL["u"], PAL["f"], PAL["F"]):
        x, y = rng.randrange(1, TILE - 1), rng.randrange(1, TILE - 1)
        img.set(x, y, color)
        img.set(x, y + 1, PAL[";"])
    return img


def tall_grass(seed=3):
    img = _noise(seed, PAL[":"], [(PAL[","], 30), (PAL[";"], 24)])
    return _tufts(img, seed + 5, PAL["."], 16, length=4)


def dirt(seed=4):
    return _noise(seed, PAL["D"], [(PAL["d"], 24), (PAL["e"], 26)])


def path(seed=5):
    """Trodden road: dirt with a couple of embedded pebbles."""
    img = _noise(seed, PAL["D"], [(PAL["d"], 30), (PAL["e"], 18)])
    rng = random.Random(seed + 11)
    for _ in range(4):
        x, y = rng.randrange(1, TILE - 2), rng.randrange(1, TILE - 2)
        img.rect(x, y, 2, 1, PAL["k"])
        img.set(x, y + 1, PAL["L"])
    return img


def cobble(seed=6):
    """Town square paving: offset brick courses."""
    img = Image(TILE, TILE, PAL["L"])
    rng = random.Random(seed)
    for row in range(4):
        offset = 0 if row % 2 == 0 else 4
        for col in range(-1, 3):
            x = col * 8 + offset
            y = row * 4
            shade = PAL["k"] if rng.random() < 0.4 else PAL["K"]
            img.rect(x, y, 7, 3, shade)
            img.rect(x, y, 7, 1, PAL["k"] if shade is PAL["K"] else shade)
    return img


def sand(seed=7):
    return _noise(seed, PAL["S"], [(PAL["s"], 40), (PAL["D"], 10)])


def water(frame=0):
    """Two-frame animated water; ripples slide across the tile."""
    img = _noise(20 + frame, PAL["W"], [(PAL["v"], 18)])
    for i in range(3):
        y = (i * 5 + frame * 2 + 2) % TILE
        x = (i * 6 + frame * 3) % TILE
        for dx in range(4):
            img.set((x + dx) % TILE, y, PAL["w"])
        img.set((x + 4) % TILE, y + 1, PAL["w"])
    return img


def _art(rows):
    return from_art(rows, PAL)


TREE = [
    "     yyyy       ",
    "   yyTTTTyy     ",
    "  yTTTTTTtty    ",
    " yTTTTTTTTtty   ",
    " yTTtTTTTTtty   ",
    "yTTTTTTtTTTtty  ",
    "yTTTTTTTTTTttyy ",
    "yTTtTTTTTTtttyy ",
    " yTTTTTTtTttyy  ",
    " yyTTTTTTtty    ",
    "  yyTTTTtyy     ",
    "    ybbBy       ",
    "     bBB        ",
    "     bBB        ",
    "    bbBBB       ",
    "   ;;;;;;;      ",
]

BUSH = [
    "                ",
    "                ",
    "     yyyy       ",
    "   yyTTTTy      ",
    "  yTTTtTTTy     ",
    " yTTTTTTtTTy    ",
    " yTTtTTTTTTy    ",
    " yTTTTTtTTty    ",
    "  yTTTTTTtyy    ",
    "   yyTTTtyy     ",
    "     yyyy       ",
    "                ",
    "                ",
    "                ",
    "                ",
    "                ",
]

ROCK = [
    "                ",
    "                ",
    "      kkk       ",
    "    kkKKKkk     ",
    "   kKKKKKKKk    ",
    "  kKKKKKKKKKk   ",
    "  kKKKKKKKKLk   ",
    " kKKKKKKKLLLLk  ",
    " kKKKKKKLLLLLk  ",
    " kKKKKLLLLLLLk  ",
    "  LLLLLLLLLLL   ",
    "   LLLLLLLLl    ",
    "     lllll      ",
    "                ",
    "                ",
    "                ",
]

MOUNTAIN = [
    "       m        ",
    "      mmm       ",
    "     mmMmm      ",
    "    mmMMMmm     ",
    "   mmMMMMMmm    ",
    "   mMMMMMMxm    ",
    "  mMMMMMMxxxm   ",
    "  mMMMMMxxxxm   ",
    " mMMMMMxxxxxxm  ",
    " mMMMMxxxxxxxm  ",
    "mMMMxxxxxxxxxxm ",
    "mMMxxxxxxxxxxxm ",
    "mMxxxxxxxxxxxxm ",
    "mxxxxxxxxxxxxxm ",
    "xxxxxxxxxxxxxxx ",
    "xxxxxxxxxxxxxxx ",
]

WALL = [
    "pppppppppppppppp",
    "pPPPPPPPPPPPPPPo",
    "pPPPPPPPPPPPPPPo",
    "pPPoooooooooPPPo",
    "pPPPPPPPPPPPPPPo",
    "pPPPPPPPPPPPPPPo",
    "pPPPPPPPPPPPPPPo",
    "pPPPPPPPPPPPPPPo",
    "poooooooooooPPPo",
    "pPPPPPPPPPPPPPPo",
    "pPPPPPPPPPPPPPPo",
    "pPPPPPPPPPPPPPPo",
    "pPPPPPPPPPPPPPPo",
    "pPPPoooooooooPPo",
    "pPPPPPPPPPPPPPPo",
    "oooooooooooooooo",
]

ROOF = [
    "qqqqqqqqqqqqqqqq",
    "rrrrrrrrrrrrrrrr",
    "RRRRRRRRRRRRRRRR",
    "RRRqRRRRRRRqRRRR",
    "qqqqqqqqqqqqqqqq",
    "rrrrrrrrrrrrrrrr",
    "RRRRRRRRRRRRRRRR",
    "RRRRRRqRRRRRRRRq",
    "qqqqqqqqqqqqqqqq",
    "rrrrrrrrrrrrrrrr",
    "RRRRRRRRRRRRRRRR",
    "RRqRRRRRRRRqRRRR",
    "qqqqqqqqqqqqqqqq",
    "rrrrrrrrrrrrrrrr",
    "RRRRRRRRRRRRRRRR",
    "qqqqqqqqqqqqqqqq",
]

ROOF_TOP = [
    "       qq       ",
    "      qrrq      ",
    "     qrRRrq     ",
    "    qrRRRRrq    ",
    "   qrRRRRRRrq   ",
    "  qrRRRRRRRRrq  ",
    " qrRRRRRRRRRRrq ",
    "qrRRRRRRRRRRRRrq",
    "qRRRRRRRRRRRRRRq",
    "qqqqqqqqqqqqqqqq",
    "rrrrrrrrrrrrrrrr",
    "RRRRRRRRRRRRRRRR",
    "RRqRRRRRRRRqRRRR",
    "qqqqqqqqqqqqqqqq",
    "rrrrrrrrrrrrrrrr",
    "qqqqqqqqqqqqqqqq",
]

DOOR = [
    "pppppppppppppppp",
    "pPoooooooooooooo",
    "pPoNNNNNNNNNNNoo",
    "pPoNnnnnnnnnnNoo",
    "pPoNnNNNNNNNnNoo",
    "pPoNnNnnnnnNnNoo",
    "pPoNnNnNNNnNnNoo",
    "pPoNnNnN1NnNnNoo",
    "pPoNnNnN1NnNnNoo",
    "pPoNnNnnnnnNnNoo",
    "pPoNnNNNNNNNnNoo",
    "pPoNnnnnnnnnnNoo",
    "pPoNNNNNNNNNNNoo",
    "pPoNNNNNNNNNNNoo",
    "pPoNNNNNNNNNNNoo",
    "oooooooooooooooo",
]

WINDOW = [
    "pppppppppppppppp",
    "pPPPPPPPPPPPPPPo",
    "pPPNNNNNNNNNNPPo",
    "pPPNggggGggggNPo",
    "pPPNgggggGgggNPo",
    "pPPNggGgggggGNPo",
    "pPPNNNNNNNNNNNPo",
    "pPPNgggggggGggNo",
    "pPPNggGggggggGNo",
    "pPPNgggGgggggGNo",
    "pPPNNNNNNNNNNNPo",
    "pPPPPPPPPPPPPPPo",
    "pPPoooooooooPPPo",
    "pPPPPPPPPPPPPPPo",
    "pPPPPPPPPPPPPPPo",
    "oooooooooooooooo",
]

FENCE = [
    "                ",
    "                ",
    "   n         n  ",
    "   n         n  ",
    "  nNn       nNn ",
    " nnnnnnnnnnnnnn ",
    " NNNNNNNNNNNNNN ",
    "  nNn       nNn ",
    "  nNn       nNn ",
    " nnnnnnnnnnnnnn ",
    " NNNNNNNNNNNNNN ",
    "  nNn       nNn ",
    "  nNn       nNn ",
    "  nNn       nNn ",
    "  ;;;       ;;; ",
    "                ",
]

SIGN = [
    "                ",
    "                ",
    "  nnnnnnnnnnnn  ",
    "  nNNNNNNNNNNn  ",
    "  nN########Nn  ",
    "  nNN######NNn  ",
    "  nN########Nn  ",
    "  nNN####NNNNn  ",
    "  nNNNNNNNNNNn  ",
    "  nnnnnnnnnnnn  ",
    "      nNn       ",
    "      nNn       ",
    "      nNn       ",
    "      nNn       ",
    "     ;;;;;      ",
    "                ",
]

WELL = [
    "                ",
    "   nnnnnnnnnn   ",
    "  nNNNNNNNNNNn  ",
    "  n          n  ",
    "  n   LLLL   n  ",
    " kkkkkkkkkkkkk  ",
    " kKKKKKKKKKKKk  ",
    " kKvvvvvvvvKKk  ",
    " kKvWWWWWWvKKk  ",
    " kKvWwwwwWvKKk  ",
    " kKvWWWWWWvKKk  ",
    " kKvvvvvvvvKKk  ",
    " kKKKKKKKKKKKk  ",
    " LLLLLLLLLLLLL  ",
    "  lllllllllll   ",
    "                ",
]

CHEST = [
    "                ",
    "                ",
    "    2222222     ",
    "   211111112    ",
    "  21NNNNNNN12   ",
    "  1NnnnnnnnN1   ",
    "  1NnnnnnnnN1   ",
    "  2111111112    ",
    "  1NNN212NNN1   ",
    "  1Nnn212nnN1   ",
    "  1Nnn111nnN1   ",
    "  1Nnnnnnnn N   ",
    "  1NNNNNNNNN1   ",
    "  22222222222   ",
    "   ;;;;;;;;;    ",
    "                ",
]

BRIDGE = [
    "vvvvvvvvvvvvvvvv",
    "NNNNNNNNNNNNNNNN",
    "nnnnnnnnnnnnnnnn",
    "nnnnnnnnnnnnnnnn",
    "NNNNNNNNNNNNNNNN",
    "nnnnnnnnnnnnnnnn",
    "nnnnnnnnnnnnnnnn",
    "NNNNNNNNNNNNNNNN",
    "nnnnnnnnnnnnnnnn",
    "nnnnnnnnnnnnnnnn",
    "NNNNNNNNNNNNNNNN",
    "nnnnnnnnnnnnnnnn",
    "nnnnnnnnnnnnnnnn",
    "NNNNNNNNNNNNNNNN",
    "nnnnnnnnnnnnnnnn",
    "vvvvvvvvvvvvvvvv",
]

FLOOR = [
    "kkkkkkkkkkkkkkkk",
    "kKKKKKKkKKKKKKKk",
    "kKKKKKKkKKKKKKKk",
    "kKKKKKKkKKKKKKKk",
    "kKKKKKKkKKKKKKKk",
    "kKKKKKKkKKKKKKKk",
    "kKKKKKKkKKKKKKKk",
    "kkkkkkkkkkkkkkkk",
    "kKKKKKKkKKKKKKKk",
    "kKKKKKKkKKKKKKKk",
    "kKKKKKKkKKKKKKKk",
    "kKKKKKKkKKKKKKKk",
    "kKKKKKKkKKKKKKKk",
    "kKKKKKKkKKKKKKKk",
    "kKKKKKKkKKKKKKKk",
    "kkkkkkkkkkkkkkkk",
]

LAMP = [
    "                ",
    "      111       ",
    "     11@11      ",
    "     1@@@1      ",
    "     11@11      ",
    "      212       ",
    "      2N2       ",
    "      nNn       ",
    "      nNn       ",
    "      nNn       ",
    "      nNn       ",
    "      nNn       ",
    "     LLLLL      ",
    "    LLlllLL     ",
    "     lllll      ",
    "                ",
]


# --- interior furnishings -------------------------------------------------

def plank(seed=30):
    """Wooden floorboards: warmer than stone for indoor rooms."""
    img = _noise(seed, PAL["n"], [(PAL["N"], 14)])
    rng = random.Random(seed)
    for y in (0, 5, 10, 15):
        img.rect(0, y, TILE, 1, PAL["N"])
    for y0, x in ((0, 6), (5, 12), (10, 3), (11, 13)):
        img.rect(x, y0 + 1, 1, 4, PAL["N"])
    for _ in range(10):
        img.set(rng.randrange(TILE), rng.randrange(TILE), PAL["b"])
    return img


def rug(seed=31):
    """Seamless weave: several rug tiles laid together read as one carpet."""
    img = Image(TILE, TILE, PAL["R"])
    for y in range(TILE):
        for x in range(TILE):
            if (x + y) % 8 == 0 or (x - y) % 8 == 0:
                img.set(x, y, PAL["r"])
    for cx, cy in ((3, 3), (11, 11)):
        img.rect(cx, cy, 2, 2, PAL["1"])
        img.set(cx, cy, PAL["2"])
    for y in range(0, TILE, 4):
        img.set((y * 3) % TILE, y, PAL["q"])
    return img


def counter():
    img = Image(TILE, TILE)
    img.rect(0, 2, TILE, 14, PAL["N"])
    img.rect(0, 2, TILE, 2, PAL["n"])
    img.rect(0, 1, TILE, 1, PAL["b"])
    img.rect(0, 0, TILE, 1, PAL["#"])
    for x in (3, 8, 13):
        img.rect(x, 5, 1, 11, PAL["B"])
    img.rect(0, 15, TILE, 1, PAL["#"])
    return img


def barrel():
    img = Image(TILE, TILE)
    img.rect(3, 2, 10, 13, PAL["N"])
    img.rect(4, 2, 8, 13, PAL["n"])
    img.rect(3, 3, 10, 2, PAL["2"])
    img.rect(3, 8, 10, 2, PAL["2"])
    img.rect(3, 13, 10, 2, PAL["2"])
    img.rect(4, 1, 8, 2, PAL["b"])
    img.rect(5, 1, 6, 1, PAL["B"])
    img.outline(PAL["#"])
    return img


def shelf():
    img = Image(TILE, TILE)
    img.rect(0, 0, TILE, 16, PAL["N"])
    img.rect(1, 1, 14, 6, PAL["#"])
    img.rect(1, 9, 14, 6, PAL["#"])
    for i, color in enumerate((PAL["w"], PAL["f"], PAL["F"], PAL["g"])):
        img.rect(2 + i * 3, 3, 2, 4, color)
        img.rect(2 + i * 3, 2, 1, 1, color)
    for i, color in enumerate((PAL["F"], PAL["g"], PAL["w"])):
        img.rect(3 + i * 4, 11, 2, 4, color)
    img.rect(0, 7, TILE, 2, PAL["n"])
    img.rect(0, 15, TILE, 1, PAL["b"])
    return img


def bed(top):
    img = Image(TILE, TILE)
    img.rect(1, 0 if top else 0, 14, 16, PAL["n"])
    img.rect(2, 0, 12, 16, PAL["N"])
    if top:
        img.rect(1, 0, 14, 3, PAL["b"])       # headboard
        img.rect(2, 3, 12, 6, PAL["@"])       # pillow
        img.rect(3, 4, 10, 4, PAL["p"])
        img.rect(2, 9, 12, 7, PAL["r"])
        img.rect(2, 9, 12, 1, PAL["q"])
    else:
        img.rect(2, 0, 12, 12, PAL["r"])
        img.rect(2, 3, 12, 1, PAL["q"])
        img.rect(2, 8, 12, 1, PAL["q"])
        img.rect(1, 12, 14, 4, PAL["b"])      # footboard
        img.rect(2, 13, 12, 2, PAL["N"])
    img.rect(0, 0, 1, 16, PAL["#"])
    img.rect(15, 0, 1, 16, PAL["#"])
    return img


def cook():
    """Return {name: Image} for every terrain and prop tile."""
    out = {
        "t_grass": grass(1),
        "t_grass2": grass(11),
        "t_grass3": grass(23),
        "t_flowers": grass_flowers(2),
        "t_tallgrass": tall_grass(3),
        "t_path": path(5),
        "t_cobble": cobble(6),
        "t_sand": sand(7),
        "t_water0": water(0),
        "t_water1": water(1),
        "t_tree": _art(TREE),
        "t_bush": _art(BUSH),
        "t_rock": _art(ROCK),
        "t_mountain": _art(MOUNTAIN),
        "t_wall": _art(WALL),
        "t_roof": _art(ROOF),
        "t_rooftop": _art(ROOF_TOP),
        "t_door": _art(DOOR),
        "t_window": _art(WINDOW),
        "t_fence": _art(FENCE),
        "t_sign": _art(SIGN),
        "t_well": _art(WELL),
        "t_chest": _art(CHEST),
        "t_bridge": _art(BRIDGE),
        "t_lamp": _art(LAMP),
        "t_plank": plank(),
        "t_rug": rug(),
        "t_counter": counter(),
        "t_barrel": barrel(),
        "t_shelf": shelf(),
        "t_bedtop": bed(True),
        "t_bedbot": bed(False),
    }
    return out
