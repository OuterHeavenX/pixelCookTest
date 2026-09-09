#!/usr/bin/env python3
"""gdlint - a cross-reference check for the Godot project.

Godot only reports a bad member name when the line actually runs, which makes
typos easy to ship. This resolves every `Object.member` reference in the
project against the script that owns it, and checks that every sprite the
scripts ask for exists in the cooked atlas.

    python3 tools/gdlint.py
"""

import re
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GODOT = os.path.join(ROOT, "godot")
SCRIPTS = os.path.join(GODOT, "scripts")

# Receiver name -> the script that defines it.
OWNERS = {
    "Art": "Art.gd", "Dat": "Dat.gd", "Gs": "Gs.gd", "Snd": "Snd.gd", "Inp": "Inp.gd",
    "main": "Main.gd", "field": "FieldMode.gd", "battle": "BattleMode.gd",
    "menu": "MenuMode.gd", "shop": "ShopMode.gd", "title": "TitleMode.gd",
}

FUNC_RE = re.compile(r"^\s*(?:static\s+)?func\s+([A-Za-z_]\w*)\s*\(", re.M)
MEMBER_RE = re.compile(r"^\s*(?:@export\s+)?(?:var|const)\s+([A-Za-z_]\w*)", re.M)
REF_RE = re.compile(r"\b(" + "|".join(OWNERS) + r")\.([A-Za-z_]\w*)")
SPRITE_RE = re.compile(r"\"((?:t_|i_|e_)[a-z0-9_]+)\"")
CLASS_RE = re.compile(r"^class_name\s+(\w+)", re.M)


def scripts():
    return {f: open(os.path.join(SCRIPTS, f), encoding="utf-8").read()
            for f in sorted(os.listdir(SCRIPTS)) if f.endswith(".gd")}


def surface(src):
    """Everything a script exposes: its methods plus its script-level members."""
    names = set(FUNC_RE.findall(src))
    for m in MEMBER_RE.finditer(src):
        # Script-level declarations only; locals are indented.
        if m.group(0)[0] not in " \t":
            names.add(m.group(1))
    return names


def check_references(srcs, problems):
    surfaces = {name: surface(srcs[path]) for name, path in OWNERS.items()
                if path in srcs}
    for path, src in srcs.items():
        for i, line in enumerate(src.split("\n"), 1):
            if line.lstrip().startswith("#"):
                continue
            for recv, member in REF_RE.findall(line):
                if recv not in surfaces:
                    continue
                # Skip our own declarations of that name.
                if member in surfaces[recv]:
                    continue
                problems.append("%s:%d  %s.%s is not defined in %s"
                                % (path, i, recv, member, OWNERS[recv]))


def check_sprites(srcs, problems):
    meta_path = os.path.join(GODOT, "assets", "atlas.json")
    frames = set(json.load(open(meta_path))["frames"])
    for path, src in srcs.items():
        for i, line in enumerate(src.split("\n"), 1):
            for name in SPRITE_RE.findall(line):
                if name in frames:
                    continue
                # Names built by format strings are checked separately.
                if name.endswith("_") or "%" in line.split(name)[0][-3:]:
                    continue
                problems.append("%s:%d  sprite %s is not in the atlas" % (path, i, name))


def check_generated_sprites(problems):
    """Names the scripts build at runtime: walk cycles, battle poses, tiles."""
    frames = set(json.load(open(os.path.join(GODOT, "assets", "atlas.json")))["frames"])
    data = json.load(open(os.path.join(GODOT, "assets", "gamedata.json")))
    wanted = set()
    sprites = {c["sprite"] for c in data["classes"].values()}
    for npc_list in data["npcs"].values():
        for npc in npc_list:
            sprites.add(npc["sprite"])
    for s in sprites:
        for facing in ("down", "up", "left", "right"):
            for frame in range(3):
                wanted.add("%s_%s%d" % (s, facing, frame))
    for c in data["classes"].values():
        for pose in ("ready", "attack", "hurt"):
            wanted.add("%s_%s" % (c["sprite"], pose))
    for e in data["enemies"].values():
        wanted.add(e["sprite"])
    for entry in data["legend"].values():
        wanted.add(entry[0])
    for under in data["underlay"].values():
        if under != "ground":
            wanted.add(under)
    for it in data["items"].values():
        wanted.add(it["icon"])
    wanted |= {"t_water0", "t_water1", "t_grass", "t_grass2", "t_grass3", "t_plank"}
    for name in sorted(wanted - frames):
        problems.append("atlas is missing %s, which the data asks for" % name)


def check_data_keys(srcs, problems):
    data = json.load(open(os.path.join(GODOT, "assets", "gamedata.json")))
    known = set(data) | {"maps", "roll_encounter", "_read_json"}
    dat_surface = surface(srcs["Dat.gd"])
    for name in sorted(known - dat_surface - {"maps"}):
        if name not in dat_surface:
            problems.append("Dat.gd never exposes gamedata key '%s'" % name)


BLOCK_OPENERS = ("if ", "elif ", "else:", "for ", "while ", "match ", "func ")
VAR_DECL_RE = re.compile(r"^(\t*)var\s+([A-Za-z_]\w*)")


def check_redeclarations(srcs, problems):
    """A second `var x` in the same block is a hard parse error in Godot, and
    the whole project fails to load - worth catching without the engine."""
    for path, src in srcs.items():
        lines = src.split("\n")
        stack = [[0, set()]]
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(line) - len(line.lstrip("\t"))
            if stripped.startswith("func "):
                stack = [[0, set()]]
                continue
            while len(stack) > 1 and indent <= stack[-1][0]:
                stack.pop()
            m = VAR_DECL_RE.match(line)
            if m:
                name = m.group(2)
                if name in stack[-1][1]:
                    problems.append("%s:%d  `var %s` is already declared in this block"
                                    % (path, i, name))
                stack[-1][1].add(name)
            if stripped.endswith(":") and stripped.startswith(BLOCK_OPENERS):
                stack.append([indent, set()])


# Godot's global maths helpers are Variant utility functions: they return
# Variant, so `var x := max(a, b)` fails the project's inferred-declaration
# warning and the engine refuses to load the script. Every one of these has a
# typed sibling (maxf/maxi, absf/absi, ...) that returns a real number.
VARIANT_UTILS = {
    "max": "maxf/maxi", "min": "minf/mini", "clamp": "clampf/clampi",
    "abs": "absf/absi", "round": "roundf/roundi", "floor": "floorf/floori",
    "ceil": "ceilf/ceili", "sign": "signf/signi", "snapped": "snappedf/snappedi",
    "lerp": "lerpf", "wrap": "wrapf/wrapi", "posmod": "posmod on ints",
}
INFER_RE = re.compile(r"^\s*var\s+(\w+)\s*:=\s*(\w+)\(")


def check_inferred_variants(srcs, problems):
    """`var x := max(...)` is a fatal parse error in Godot 4, not a warning.

    It cost a boot failure once: gdlint was clean, the syntax checker was
    clean, and the engine refused to load half the project. Cheap to catch
    here, so it never reaches the engine again.
    """
    for path, src in srcs.items():
        for i, line in enumerate(src.split("\n"), 1):
            m = INFER_RE.match(line)
            if m and m.group(2) in VARIANT_UTILS:
                problems.append(
                    "%s:%d  `var %s := %s(...)` infers Variant; use %s or annotate the type"
                    % (path, i, m.group(1), m.group(2), VARIANT_UTILS[m.group(2)]))


# World flags live in three places at once: the cooked data names them, the
# browser build reads them off `G.flags`, and the Godot build reads them off
# `Gs.flags`. Nothing connects the three, so the Godot build spelled the
# boss flag `boss_down` while the data that gated a whole chapter-two scene
# said `bossDown`, and the scene simply never fired. Neither build errored.
GD_FLAG_RE = re.compile(r"flags(?:\[|\.get\()\s*\"([A-Za-z_]\w*)\"")
JS_FLAG_RE = re.compile(r"G\.flags(?:\.([A-Za-z_]\w*)|\[[\'\"]([A-Za-z_]\w*))")


def flag_names(srcs):
    gd = set()
    for src in srcs.values():
        gd |= set(GD_FLAG_RE.findall(src))
    js = set()
    path = os.path.join(ROOT, "src", "game.js")
    if os.path.exists(path):
        for a, b in JS_FLAG_RE.findall(open(path, encoding="utf-8").read()):
            js.add(a or b)
    return gd, js


def check_flags(srcs, problems):
    """The two builds must know the same world flags by the same names."""
    gd, js = flag_names(srcs)
    if not js:
        return
    data = json.load(open(os.path.join(GODOT, "assets", "gamedata.json")))
    # Flags the data names are the data's vocabulary, not the engine's, and
    # either build may read one without owning it. Only the flags the code
    # itself invents have to match on both sides.
    from_data = set()
    for beats in data.get("map_beats", {}).values():
        for beat in beats:
            from_data.add(beat["flag"])
            from_data |= {f for f in beat.get("choice", {}).get("sets", []) if f}
    for loot in data.get("chest_loot", {}).values():
        if "flag" in loot:
            from_data.add(loot["flag"])
    gd -= from_data
    js -= from_data
    for name in sorted(js - gd):
        problems.append("flag '%s' is set in the browser build but never in Godot"
                        % name)
    for name in sorted(gd - js):
        problems.append("flag '%s' is set in the Godot build but never in the browser"
                        % name)
    # And every flag the data gates a scene behind has to be one somebody sets.
    produced = set(gd) | from_data
    for beats in data.get("map_beats", {}).values():
        for beat in beats:
            produced.add(beat["flag"])
            # A beat that asks a question sets whichever flag the answer names.
            produced |= {f for f in beat.get("choice", {}).get("sets", []) if f}
    for loot in data.get("chest_loot", {}).values():
        if "flag" in loot:
            produced.add(loot["flag"])
    for beats in data.get("map_beats", {}).values():
        for beat in beats:
            for name in beat.get("needs", []) + beat.get("absent", []):
                if name not in produced:
                    problems.append(
                        "map beat '%s' waits on flag '%s', which nothing sets"
                        % (beat["flag"], name))


def main():
    srcs = scripts()
    problems = []
    check_references(srcs, problems)
    check_redeclarations(srcs, problems)
    check_inferred_variants(srcs, problems)
    check_sprites(srcs, problems)
    check_generated_sprites(problems)
    check_data_keys(srcs, problems)
    check_flags(srcs, problems)

    declared = set()
    for src in srcs.values():
        declared |= set(CLASS_RE.findall(src))
    for used in ("FieldMode", "BattleMode", "MenuMode", "ShopMode", "TitleMode"):
        if used not in declared:
            problems.append("class_name %s is never declared" % used)

    if problems:
        print("gdlint: %d problem(s)" % len(problems))
        for p in problems:
            print("  " + p)
        return 1
    print("gdlint: %d scripts clean (references, redeclarations, inferred types,"
          " sprites, data keys, flags)"
          % len(srcs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
