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
CRYPT_HI = rgb("6a6478")
CRYPT = rgb("4b465a")
CRYPT_LO = rgb("332f42")
CRYPT_DK = rgb("221f2e")
MOSS = rgb("46714a")
BONE = rgb("d8d2b8")
BONE_LO = rgb("9a9478")
EMBER = rgb("ff9a3c")
EMBER_LO = rgb("c04a20")
ICE_HI = rgb("dcefff")
ICE = rgb("a8ccec")
ICE_LO = rgb("6f9cc4")
SNOW = rgb("ccd8ea")
# Under the mere: the cold deep, four values of it. Colder and darker than
# the crypt, which is a purple-grey - this is blue-green and lightless.
DEEP_HI = rgb("58899c")
DEEP_MID = rgb("3d6a7d")
DEEP = rgb("2e5468")
DEEP_LO = rgb("1b3543")
DEEP_DK = rgb("0d1c26")
CAUSTIC = rgb("9fd8e8")

PALE_HI = rgb("cacee2")
PALE = rgb("a2a7bd")
PALE_LO = rgb("6f748c")
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
    "I": ICE,
    "i": ICE_HI,
    "J": ICE_LO,
    "N2": SNOW,
    "j": PALE_LO,
    "H": PALE,
    "h": PALE_HI,
    "u": PALE_LO,
    "C": CRYPT_HI,
    "c": CRYPT,
    "V": CRYPT_LO,
    "X": CRYPT_DK,
    "Z": MOSS,
    "O": BONE,
    "0": BONE_LO,
    "E": EMBER,
    "3": EMBER_LO,
    "1": GOLD,
    "2": GOLD_LO,
    "#": INK,
    "%": INK_SOFT,
    "4": DEEP_MID,
    "5": DEEP_HI,
    "6": DEEP,
    "7": DEEP_LO,
    "8": DEEP_DK,
    "9": CAUSTIC,
    "@": WHITE,
}
