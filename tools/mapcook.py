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
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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
    g.set(46, 37, ">")          # the way into the barrow
    g.set(2, 22, "/")           # the west pass, shut until the barrow is done

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
        "encounters": "wild",
        "music": "field",
        "spawn": [28, 4],
        "warps": [
            {"x": 28, "y": 2, "to": "town", "tx": 20, "ty": 27, "dir": "up"},
            {"x": 46, "y": 37, "to": "barrow1", "tx": 20, "ty": 28, "dir": "up"},
            {"x": 2, "y": 22, "to": "shore", "tx": 3, "ty": 14, "dir": "left"},
        ],
    }


def barrow_upper():
    """The Barrow, upper halls: a corridor up from the entrance into a long
    gallery, with a chamber at each end and the vault sealed in the middle.
    The stair down is behind the gate, and the gate wants the key, which is in
    the chamber at the far end - so the floor has to be walked, not crossed."""
    g = Grid(40, 30, "#")

    def hall(x, y, w, h):
        g.rect(x, y, w, h, "_")

    hall(17, 24, 7, 5)                   # entrance chamber
    g.set(20, 29, "<")                   # back up to the shrine
    hall(17, 18, 7, 6)                   # corridor to the gallery
    hall(4, 14, 32, 4)                   # the long west-east gallery
    hall(4, 4, 8, 10)                    # west chamber
    hall(28, 4, 8, 10)                   # east chamber
    hall(12, 4, 16, 4)                   # north gallery joining the two

    # The vault. Sealed on every side; the only way in is the gate on its
    # south wall, and the only thing in it is the way down.
    hall(17, 9, 7, 4)
    g.rect(17, 13, 7, 1, "#")
    g.set(20, 13, "g")
    g.set(20, 10, ">")

    g.set(6, 6, "c")                     # the guard charm, west chamber
    g.set(33, 6, "c")                    # the gate key, east chamber
    g.set(30, 16, "c")                   # potions, off the gallery
    for bx, by in ((5, 13), (10, 4), (29, 4), (34, 13), (16, 14), (24, 14),
                   (18, 23), (22, 23)):
        g.set(bx, by, "i")               # braziers, so the halls are lit
    for jx, jy in ((7, 9), (31, 10), (13, 16), (26, 17), (19, 21), (8, 12)):
        g.set(jx, jy, "j")
    g.set(20, 23, "s")                   # the lintel inscription
    return {
        "id": "barrow1",
        "name": "The Barrow",
        "rows": g.out(),
        "encounter": 18,
        "encounters": "barrow",
        "battle_bg": "night",
        "music": "barrow",
        "ground": "t_crypt",
        "spawn": [20, 27],
        "warps": [
            {"x": 20, "y": 29, "to": "wild", "tx": 46, "ty": 37, "dir": "down"},
            {"x": 20, "y": 10, "to": "barrow2", "tx": 18, "ty": 25, "dir": "up"},
        ],
    }


def barrow_deep():
    """The deep barrow: one long descent to the chieftain's floor, with two
    dead ends that are worth the walk."""
    g = Grid(38, 28, "#")

    def hall(x, y, w, h):
        g.rect(x, y, w, h, "_")

    hall(15, 24, 7, 3)                   # arrival
    g.set(18, 27, "<")                   # back up
    hall(17, 12, 4, 12)                  # the spine
    hall(3, 18, 15, 3)                   # west arm
    hall(3, 4, 4, 15)                    # west arm turns north
    hall(3, 4, 8, 3)                     # to a dead end with the plate
    hall(20, 20, 14, 3)                  # east arm
    hall(30, 8, 4, 13)                   # east arm turns north
    hall(24, 8, 10, 3)                   # and back west
    hall(12, 4, 14, 9)                   # the chieftain's floor
    hall(24, 8, 4, 3)                    # joined to the east arm

    g.set(18, 6, "%")                    # the ward the chieftain sits on
    g.set(4, 6, "c")                     # knight plate
    g.set(32, 22, "c")                   # a purse
    g.set(19, 4, "c")                    # flame brand, behind the boss
    for bx, by in ((13, 5), (24, 5), (13, 11), (24, 11), (4, 17), (33, 19), (16, 23)):
        g.set(bx, by, "i")
    for jx, jy in ((19, 6), (15, 9), (22, 10), (5, 12), (31, 15), (26, 21), (8, 19)):
        g.set(jx, jy, "j")
    return {
        "id": "barrow2",
        "name": "The Barrow, Deep",
        "rows": g.out(),
        "encounter": 15,
        "encounters": "barrow",
        "battle_bg": "night",
        "music": "barrow",
        "ground": "t_crypt",
        "spawn": [18, 25],
        "warps": [
            {"x": 18, "y": 27, "to": "barrow1", "tx": 20, "ty": 11, "dir": "down"},
        ],
        "boss": {"x": 18, "y": 8},
    }


def hollowmere():
    """Hollowmere: a lake town on the far side of the Thornwilds, built in pale
    stone with the mere frozen along its north edge. Every doorway has a
    lantern over it and every lantern is lit, which is the first thing anyone
    notices and the last thing anyone here will explain."""
    g = Grid(44, 34, "n")

    def house(x, y, w, h, door_x):
        g.rect(x, y, w, 2, "Q")          # roof
        g.rect(x, y + 2, w, h - 2, "P")  # wall
        # Lit windows: the town's whole character is that nothing here is dark.
        for wx in range(1, w - 1, 3):
            if wx != door_x:
                g.set(x + wx, y + 2, "V")
        g.set(x + door_x, y + h - 1, "D")
        g.set(x + door_x - 1, y + h - 1, "L")

    g.border(1, "M")
    g.rect(0, 0, 44, 8, "I")             # the mere, frozen over
    g.rect(0, 0, 44, 1, "M")
    for x in range(2, 42):               # a shore of trodden snow
        g.set(x, 8, "n")

    # The lantern row along the shore: this is the town's whole job.
    for x in range(4, 40, 5):
        g.set(x, 9, "L")

    house(3, 12, 8, 5, 4)                # west terrace
    house(13, 12, 7, 5, 3)
    house(24, 12, 9, 5, 4)               # the inn
    house(36, 12, 6, 5, 2)
    house(5, 24, 9, 5, 4)                # south terrace
    house(18, 25, 8, 5, 3)               # the armoury
    house(31, 24, 8, 5, 4)

    for x in range(2, 42):               # the long street
        g.set(x, 20, "=")
        g.set(x, 21, "=")
    for y in range(17, 33):              # a cross street to the south gate
        g.set(21, y, "=")
        g.set(22, y, "=")
    g.set(21, 33, "/")                   # the pass back to the Thornwilds
    g.set(22, 33, "/")

    for lx, ly in ((10, 19), (20, 19), (32, 19), (10, 22), (32, 22), (26, 30)):
        g.set(lx, ly, "L")
    for px, py in ((2, 11), (43 - 2, 11), (3, 31), (40, 30), (16, 31), (28, 32),
                   (2, 18), (41, 18), (8, 32)):
        g.set(px, py, "p")
    g.set(24, 22, "s")                   # the sign on the street
    g.set(38, 9, "c")                    # a chest at the end of the lantern row
    g.set(6, 31, "c")
    return {
        "id": "hollow",
        "name": "Hollowmere",
        "rows": g.out(),
        "encounter": 0,
        "music": "hollow",
        "ground": "t_snow",
        "spawn": [21, 31],
        "warps": [
            {"x": 21, "y": 33, "to": "shore", "tx": 45, "ty": 14, "dir": "right"},
            {"x": 22, "y": 33, "to": "shore", "tx": 45, "ty": 14, "dir": "right"},
        ],
    }


def mere_road():
    """The road along the mere: the cold country between the west pass and
    Hollowmere. Open on the lake side, pines on the other, and nothing living
    out here that is glad to see you."""
    g = Grid(48, 26, "n")
    g.border(1, "M")
    g.rect(1, 1, 46, 7, "I")             # the mere along the north
    g.rect(0, 0, 48, 1, "M")
    for x in range(1, 47):
        g.set(x, 8, "n")

    for x in range(2, 46):               # the road itself
        g.set(x, 14, "-")
        g.set(x, 15, "-")
    # Pines and boulders, not grass: the first pass scattered summer tallgrass
    # across a snowfield and it read as a lawn with weather on it.
    g.scatter("p", 40, 71, on=("n",))
    g.scatter("r", 22, 72, on=("n",))

    for lx in range(5, 45, 9):           # the lantern posts, still burning
        g.set(lx, 12, "L")
    g.set(24, 17, "s")
    g.set(9, 20, "c")
    g.set(40, 10, "c")
    g.set(1, 14, "/")                    # east, back to the Thornwilds pass
    g.set(46, 14, "/")                   # west, on to Hollowmere
    return {
        "id": "shore",
        "name": "The Mere Road",
        "rows": g.out(),
        "encounter": 16,
        "encounters": "shore",
        "battle_bg": "night",
        "music": "hollow",
        "ground": "t_snow",
        "spawn": [3, 14],
        "warps": [
            {"x": 1, "y": 14, "to": "wild", "tx": 3, "ty": 22, "dir": "right"},
            {"x": 46, "y": 14, "to": "hollow", "tx": 21, "ty": 32, "dir": "up"},
        ],
    }


def _solid_chars():
    """The legend lives in datacook; collision comes from there, not a second
    copy here that could drift."""
    import datacook
    return {ch for ch, spec in datacook.LEGEND.items() if len(spec) > 1 and spec[1]}


def _reachable(m, solid):
    """Flood fill from the spawn over everything you can stand on."""
    rows = m["rows"]
    w, h = len(rows[0]), len(rows)
    start = tuple(m["spawn"])
    seen = {start}
    stack = [start]
    while stack:
        x, y = stack.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < w and 0 <= ny < h) or (nx, ny) in seen:
                continue
            if rows[ny][nx] in solid:
                continue
            seen.add((nx, ny))
            stack.append((nx, ny))
    return seen


def validate(maps):
    """A map you cannot walk is worse than no map, and the mistake is silent:
    the game boots, the room is just never seen.

    Everything has to be reachable once the locked gates are open, and the key
    that opens a gate has to be reachable while they are still shut - a key
    behind the door it unlocks makes the dungeon unwinnable, and no amount of
    playing the happy path finds that."""
    import datacook
    problems = []
    solid = _solid_chars()
    unlocked = solid - {ch for ch, spec in datacook.LEGEND.items()
                        if len(spec) > 2 and spec[2] == "gate"}
    for m in sorted(maps):
        mp = maps[m]
        rows = mp["rows"]
        if rows[mp["spawn"][1]][mp["spawn"][0]] in solid:
            problems.append("%s: spawn %s is inside a wall" % (m, mp["spawn"]))
            continue
        # Gates count as open here: a lock is a delay, not a wall.
        seen = _reachable(mp, unlocked)
        locked = _reachable(mp, solid)

        def standable(where, x, y, what, note=""):
            if (x, y) in where:
                return True
            # Props are solid; you use them from the tile next to them.
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if (x + dx, y + dy) in where:
                    return True
            problems.append("%s: %s at %d,%d cannot be reached%s"
                            % (m, what, x, y, note))
            return False

        for w in mp.get("warps", []):
            if (w["x"], w["y"]) not in seen:
                problems.append("%s: the warp to %s at %d,%d cannot be reached"
                                % (m, w["to"], w["x"], w["y"]))
        if mp.get("boss"):
            standable(seen, mp["boss"]["x"], mp["boss"]["y"], "the boss")
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch == "c":
                    standable(seen, x, y, "a chest")
                    loot = datacook.CHEST_LOOT.get("%s:%d,%d" % (m, x, y), {})
                    if loot.get("flag"):
                        standable(locked, x, y, "the %s key" % loot["flag"],
                                  " with the gates still locked")
                elif ch == "s":
                    standable(seen, x, y, "a sign")
    return problems


def build():
    maps = {m["id"]: m for m in (town(), inn(), wilds(), barrow_upper(),
                                 barrow_deep(), hollowmere(), mere_road())}
    for m in maps.values():
        widths = {len(r) for r in m["rows"]}
        assert len(widths) == 1, "%s has ragged rows: %s" % (m["id"], widths)
        m["w"] = widths.pop()
        m["h"] = len(m["rows"])
    problems = validate(maps)
    if problems:
        raise SystemExit("unwalkable map:\n  " + "\n  ".join(problems))

    path = os.path.join(ROOT, "assets", "maps.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(maps, fh, indent=1, sort_keys=True)
    for m in maps.values():
        print("map %-6s %2dx%-2d  %s" % (m["id"], m["w"], m["h"], m["name"]))
    return path


if __name__ == "__main__":
    print("maps  :", build())
