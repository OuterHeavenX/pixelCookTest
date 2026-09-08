"""Shared colour vocabulary for every cooked asset.

One palette keeps the town, the wilderness, the party and the monsters
looking like they come from the same cartridge.
"""


def rgb(hex_str, alpha=255):
    hex_str = hex_str.lstrip("#")
    return (
        int(hex_str[0:2], 16),
        int(hex_str[2:4], 16),
        int(hex_str[4:6], 16),
        alpha,
    )


# Ground / nature
GRASS_HI = rgb("7bc86c")
GRASS = rgb("5aa050")
GRASS_LO = rgb("3f7d3c")
GRASS_DK = rgb("2f5f30")
DIRT_HI = rgb("c8a06a")
DIRT = rgb("a67c44")
DIRT_LO = rgb("7d5a33")
SAND_HI = rgb("e8d9a0")
SAND_LO = rgb("c4ae74")
STONE_HI = rgb("b8b8c0")
STONE = rgb("8d8d98")
STONE_LO = rgb("5f5f6b")
STONE_DK = rgb("3d3d47")
WATER_HI = rgb("6fd2e8")
WATER = rgb("3c9ad4")
WATER_LO = rgb("2360a8")
MTN_HI = rgb("9a8f88")
MTN = rgb("6f665f")
MTN_LO = rgb("4a423d")

# Flora
LEAF_HI = rgb("6fbf5a")
LEAF = rgb("47913f")
LEAF_LO = rgb("2f6630")
BARK_HI = rgb("8a6034")
BARK_LO = rgb("5a3c20")
FLOWER_R = rgb("e0576b")
FLOWER_Y = rgb("f2d15a")
FLOWER_W = rgb("f0eee6")

# Buildings
ROOF_HI = rgb("d1655c")
ROOF = rgb("a8443f")
ROOF_LO = rgb("73282a")
PLASTER_HI = rgb("efe0c2")
PLASTER = rgb("d6c19c")
PLASTER_LO = rgb("a68a68")
WOOD_HI = rgb("9c6b3c")
WOOD_LO = rgb("6b4423")
GLASS = rgb("8fd0e8")
GLASS_LO = rgb("4d8fb5")
GOLD = rgb("f0c04a")
GOLD_LO = rgb("a87a20")

# Ink
INK = rgb("241b26")
INK_SOFT = rgb("3a2f42")
WHITE = rgb("f4f4ec")
SHADOW = (0, 0, 0, 70)

TILE_PALETTE = {
    " ": None,
    ".": GRASS_HI,
    ",": GRASS,
    ":": GRASS_LO,
    ";": GRASS_DK,
    "d": DIRT_HI,
    "D": DIRT,
    "e": DIRT_LO,
    "s": SAND_HI,
    "S": SAND_LO,
    "k": STONE_HI,
    "K": STONE,
    "L": STONE_LO,
    "l": STONE_DK,
    "w": WATER_HI,
    "W": WATER,
    "v": WATER_LO,
    "T": LEAF_HI,
    "t": LEAF,
    "y": LEAF_LO,
    "b": BARK_HI,
    "B": BARK_LO,
    "r": ROOF_HI,
    "R": ROOF,
    "q": ROOF_LO,
    "p": PLASTER_HI,
    "P": PLASTER,
    "o": PLASTER_LO,
    "n": WOOD_HI,
    "N": WOOD_LO,
    "f": FLOWER_R,
    "F": FLOWER_Y,
    "u": FLOWER_W,
    "g": GLASS,
    "G": GLASS_LO,
    "m": MTN_HI,
    "M": MTN,
    "x": MTN_LO,
    "1": GOLD,
    "2": GOLD_LO,
    "#": INK,
    "%": INK_SOFT,
    "@": WHITE,
}
