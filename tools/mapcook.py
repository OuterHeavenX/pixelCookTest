#!/usr/bin/env python3
"""mapcook - author the game's maps as validated tile grids.

Maps are painted with explicit drawing ops (no randomness in the layout that
matters) and written to assets/maps.json. Legend characters are resolved to
atlas sprites and collision flags by the game at load time.

    python3 tools/mapcook.py
"""

import json
import os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Grid:
    def __init__(self, w, h, fill="."):
        self.w = w
        self.h = h
        self.rows = [[fill] * w for _ in range(h)]

    def set(self, x, y, ch):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.rows[y][x] = ch

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.rows[y][x]
        return None

    def rect(self, x, y, w, h, ch):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.set(xx, yy, ch)

    def border(self, thickness, ch):
        self.rect(0, 0, self.w, thickness, ch)
        self.rect(0, self.h - thickness, self.w, thickness, ch)
        self.rect(0, 0, thickness, self.h, ch)
        self.rect(self.w - thickness, 0, thickness, self.h, ch)

    def hline(self, x0, x1, y, ch):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            self.set(x, y, ch)

    def vline(self, x, y0, y1, ch):
        for y in range(min(y0, y1), max(y0, y1) + 1):
            self.set(x, y, ch)

    def stamp(self, x, y, art):
        for dy, row in enumerate(art):
            for dx, ch in enumerate(row):
                if ch != " ":
                    self.set(x + dx, y + dy, ch)

    def scatter(self, ch, count, seed, on=(".", ","), pad=1):
        rng = random.Random(seed)
        placed = 0
        guard = 0
        while placed < count and guard < count * 60:
            guard += 1
            x = rng.randrange(pad, self.w - pad)
            y = rng.randrange(pad, self.h - pad)
            if self.get(x, y) in on:
                self.set(x, y, ch)
                placed += 1
        return self

    def out(self):
        return ["".join(r) for r in self.rows]


# A house: rooftop ridge, tiled roof, wall with windows, and a door.
HOUSE = [
    "^^^^^",
    "RRRRR",
    "WGWGW",
    "WWDWW",
]
HOUSE_WIDE = [
    "^^^^^^^",
    "RRRRRRR",
    "WGWWWGW",
    "WWWDWWW",
]


def town():
    g = Grid(40, 30, ".")
    g.scatter(",", 90, 1)
    g.scatter("*", 26, 2)
    g.scatter("b", 12, 3)
    g.scatter("T", 10, 4)

    # Ring the valley: mountains at the back, woods around the rest.
    g.rect(0, 0, 40, 3, "M")
    g.rect(0, 3, 2, 27, "T")
    g.rect(38, 3, 2, 27, "T")
    g.rect(0, 28, 40, 2, "T")
    g.rect(2, 3, 36, 1, "T")

    # Central plaza with the town well.
    g.rect(15, 12, 11, 7, "=")
    g.stamp(19, 14, ["o"])

    # Main road: gate in the south, north spur to the chapel steps.
    g.vline(20, 19, 27, "-")
    g.vline(20, 4, 12, "-")
    g.hline(6, 15, 15, "-")
    g.hline(25, 34, 15, "-")

    # Town gate: clear the approach, then carve the road through the wood.
    g.rect(17, 24, 7, 3, ".")
    g.rect(19, 27, 3, 3, "-")
    g.set(18, 27, "f")
    g.set(22, 27, "f")
    g.set(18, 26, "l")
    g.set(22, 26, "l")

    # Houses.
    g.stamp(5, 7, HOUSE)          # villager cottage
    g.stamp(12, 6, HOUSE)         # armoury
    g.stamp(27, 7, HOUSE_WIDE)    # the inn
    g.stamp(6, 19, HOUSE)         # workshop
    g.stamp(29, 19, HOUSE)        # elder's house
    g.set(32, 11, "s")            # inn sign
    g.set(9, 11, "s")

    # Kitchen garden, hedged.
    g.rect(11, 20, 7, 5, "*")
    for x in range(10, 19):
        g.set(x, 19, "f")
        g.set(x, 25, "f")
    for y in range(19, 26):
        g.set(10, y, "f")
        g.set(18, y, "f")
    g.set(14, 25, "*")  # gap so the garden is reachable

    # Duck pond in the north-east corner of the valley.
    g.rect(31, 4, 6, 4, "~")
    g.rect(30, 5, 1, 2, "x")
    g.rect(37, 5, 1, 2, "x")
    g.set(33, 8, "B")
    g.set(34, 8, "B")

    # Street lamps and a couple of chests worth poking at.
    for pos in ((17, 12), (24, 12), (17, 18), (24, 18)):
        g.set(pos[0], pos[1], "l")
    g.set(35, 24, "c")
    g.set(4, 5, "c")

    return {
        "id": "town",
        "name": "Rivenbrook",
        "ground": "t_grass",
        "rows": g.out(),
        "encounter": 0,
        "music": "town",
        "spawn": [20, 20],
        "warps": [
            {"x": 19, "y": 29, "to": "wild", "tx": 28, "ty": 3, "dir": "down"},
            {"x": 20, "y": 29, "to": "wild", "tx": 28, "ty": 3, "dir": "down"},
            {"x": 21, "y": 29, "to": "wild", "tx": 28, "ty": 3, "dir": "down"},
            {"x": 30, "y": 10, "to": "inn", "tx": 9, "ty": 12, "dir": "up"},
        ],
    }


def inn():
    """The Amber Lantern: counter on the left, beds on the right, a rug
    between them so the room reads as a room and not a box."""
    g = Grid(19, 13, "F")
    g.border(1, "W")
    g.rect(1, 1, 17, 1, "W")     # back wall reads two tiles thick
    g.set(9, 12, "D")

    g.rect(2, 3, 5, 1, "K")      # bar counter
    g.set(2, 4, "K")
    g.set(1, 2, "H")             # shelves behind the bar
    g.set(2, 2, "H")
    g.set(3, 2, "H")
    g.set(7, 4, "A")             # barrels
    g.set(2, 6, "A")

    for by in (4, 8):            # two beds against the east wall
        g.set(16, by, "1")
        g.set(16, by + 1, "2")
        g.set(14, by, "1")
        g.set(14, by + 1, "2")
    g.set(17, 2, "H")

    g.rect(8, 6, 4, 4, "U")      # rug
    g.set(1, 11, "l")
    g.set(17, 11, "l")
    g.set(11, 2, "c")
    return {
        "id": "inn",
        "name": "The Amber Lantern",
        "rows": g.out(),
        "encounter": 0,
        "music": "inn",
        "ground": "t_plank",
        "spawn": [9, 10],
        "warps": [
            {"x": 9, "y": 12, "to": "town", "tx": 30, "ty": 11, "dir": "down"},
        ],
    }


def wilds():
    g = Grid(56, 44, ".")
    g.scatter(",", 260, 11)
    g.scatter('"', 200, 12)

    g.rect(0, 0, 56, 2, "M")
    g.rect(0, 42, 56, 2, "M")
    g.rect(0, 0, 2, 44, "M")
    g.rect(54, 0, 2, 44, "M")

    # The river snakes north to south before the roads are cut, so every
    # crossing can be turned into a bridge instead of a dead end.
    for y in range(2, 42):
        cx = 23 if (y // 7) % 2 == 0 else 17
        g.rect(cx, y, 3, 1, "~")

    def road(cells):
        for x, y in cells:
            g.set(x, y, "B" if g.get(x, y) == "~" else "-")

    def hroad(x0, x1, y):
        road([(x, y) for x in range(min(x0, x1), max(x0, x1) + 1)])

    def vroad(x, y0, y1):
        road([(x, y) for y in range(min(y0, y1), max(y0, y1) + 1)])

    vroad(28, 2, 12)     # north road up to the town gate
    hroad(12, 28, 12)
    vroad(12, 12, 30)
    hroad(12, 46, 30)
    vroad(46, 18, 30)

    # Woods, boulders and open meadows.
    for (cx, cy, r, ch) in ((7, 6, 4, "T"), (46, 8, 5, "T"), (8, 36, 4, "T"),
                            (36, 40, 3, "T"), (40, 20, 3, "T"), (30, 26, 3, "b")):
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r and g.get(x, y) in (".", ",", '"'):
                    g.set(x, y, ch)
    g.scatter("T", 60, 13)
    g.scatter("r", 34, 14)
    g.scatter("b", 40, 15)
    g.scatter("*", 30, 16)

    # Ruined shrine in the south-east: the boss waits on the flagstones.
    g.rect(42, 33, 9, 7, "=")
    g.set(43, 33, "l")
    g.set(49, 33, "l")
    g.set(43, 39, "c")
    g.set(50, 36, "s")

    # Three caches worth leaving the road for. The best gear is found, not
    # bought, so each one sits in a corner the main path does not pass.
    g.set(6, 12, "c")       # north-west, behind the pines
    g.set(51, 5, "c")       # north-east, past the far treeline
    g.set(13, 36, "c")      # south-west, deep in the thorns
    vroad(46, 30, 33)

    return {
        "id": "wild",
        "name": "Thornwilds",
        "ground": "t_grass",
        "rows": g.out(),
        "encounter": 22,
        "music": "field",
        "spawn": [28, 4],
        "warps": [
            {"x": 28, "y": 2, "to": "town", "tx": 20, "ty": 27, "dir": "up"},
        ],
        "boss": {"x": 46, "y": 36},
    }


def build():
    maps = {m["id"]: m for m in (town(), inn(), wilds())}
    for m in maps.values():
        widths = {len(r) for r in m["rows"]}
        assert len(widths) == 1, "%s has ragged rows: %s" % (m["id"], widths)
        m["w"] = widths.pop()
        m["h"] = len(m["rows"])
    path = os.path.join(ROOT, "assets", "maps.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(maps, fh, indent=1, sort_keys=True)
    for m in maps.values():
        print("map %-6s %2dx%-2d  %s" % (m["id"], m["w"], m["h"], m["name"]))
    return path


if __name__ == "__main__":
    print("maps  :", build())
