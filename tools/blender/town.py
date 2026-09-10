#!/usr/bin/env python3
"""Build a piece of a map as real geometry and render it three ways.

The maps are 51 kinds of 16x16 tile drawn flat. This reads the same maps.json
and the same legend the game reads, stands every tile up as geometry with a
height, and photographs it - so the question "what would this look like in
2.5D" can be answered by looking at it rather than by arguing about it.

Every colour comes from the cooked atlas: each tile's own material is the
average of the pixels the game already draws for it, and the sides are that
colour in shadow. Nothing here is hand-picked, so all 51 tiles are covered and
the palette cannot drift from the one on screen.

    pip install bpy==4.5.13
    python3 tools/blender/town.py --style flat
    python3 tools/blender/town.py --style quarter
    python3 tools/blender/town.py --style diorama

    flat      the angle the game is drawn from now, with real light and shadow
    quarter   tilted far enough to see the sides of things
    diorama   the same, lower and softer, with depth of field
"""

import argparse
import json
import math
import os
import sys

import bpy
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from spritecook.imported import read_png  # noqa: E402

PPT = 16          # pixels per tile, and Blender units per tile
SUPER = 4         # render at this multiple of the game's own resolution

# How tall each tile stands, in game pixels. A tile with no entry is ground.
HEIGHT = {
    "t_wall": 22, "t_palewall": 22, "t_cryptwall": 22, "t_drownwall": 22,
    "t_window": 22, "t_palewindow": 22,
    "t_roof": 25, "t_blueroof": 25, "t_rooftop": 29,
    "t_door": 20, "t_gate": 18, "t_hatch": 3,
    "t_mountain": 36,
    "t_tree": 30, "t_pinesnow": 30,
    "t_bush": 9, "t_rock": 9,
    "t_fence": 11, "t_sign": 14, "t_well": 13,
    "t_lamp": 17, "t_lantern": 17, "t_brazier": 15,
    "t_barrel": 11, "t_chest": 9, "t_shelf": 14, "t_counter": 11,
    "t_bedtop": 5, "t_bedbot": 5,
    "t_tallgrass": 5, "t_flowers": 2, "t_bones": 1, "t_lampsunk": 17,
    "t_water0": -2, "t_water1": -2, "t_ice": -1,
}

# Tiles whose art is a facade. They are drawn as blocks with that art on the
# sides and plain slate on top; every other block wears its art all round.
WALLS = {"t_wall", "t_palewall", "t_cryptwall", "t_drownwall", "t_window",
         "t_palewindow", "t_door"}

# What shape it is. Everything else is a block, which is right for masonry and
# wrong for a tree.
SHAPE = {
    "t_tree": "tree", "t_pinesnow": "pine",
    "t_bush": "dome", "t_rock": "dome",
    "t_well": "drum", "t_barrel": "drum", "t_brazier": "drum",
    "t_lamp": "post", "t_lantern": "post", "t_sign": "post", "t_lampsunk": "post",
    "t_fence": "rail",
    "t_roof": "roof", "t_blueroof": "roof", "t_rooftop": "ridge",
    "t_tallgrass": "tuft", "t_flowers": "tuft",
}


def hex_rgb(c):
    def to_linear(v):
        v /= 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return tuple(to_linear(x) for x in c[:3]) + (1.0,)


def tile_colours():
    """The average colour of every tile, straight off the cooked atlas.

    Sampling the art the game actually draws means the geometry cannot end up
    in a different palette from the sprites standing on it, and it covers every
    tile without anybody choosing 51 colours by hand.
    """
    atlas = read_png(os.path.join(ROOT, "assets", "atlas.png"))
    frames = json.load(open(os.path.join(ROOT, "assets", "atlas.json")))["frames"]
    out = {}
    for name, (fx, fy, fw, fh) in frames.items():
        if not name.startswith("t_"):
            continue
        r = g = b = n = 0
        for y in range(fh):
            for x in range(fw):
                px = atlas.get(fx + x, fy + y)
                if px[3] < 128:
                    continue
                r += px[0]; g += px[1]; b += px[2]; n += 1
        out[name] = (r // n, g // n, b // n) if n else (128, 128, 128)
    return out


_ATLAS_IMAGE = None
_FRAMES = None


def atlas_image():
    """The cooked atlas, as one Blender image, loaded once.

    The geometry wears the game's own tiles. Colouring it with each tile's
    average instead - which is what the first pass did - shows the shape of a
    town and none of its art, and the whole question is what the art looks like
    with depth under it.
    """
    global _ATLAS_IMAGE, _FRAMES
    if _ATLAS_IMAGE is None:
        _ATLAS_IMAGE = bpy.data.images.load(os.path.join(ROOT, "assets", "atlas.png"))
        _ATLAS_IMAGE.colorspace_settings.name = 'sRGB'
        _FRAMES = json.load(open(os.path.join(ROOT, "assets", "atlas.json")))["frames"]
    return _ATLAS_IMAGE, _FRAMES


def mat(name, rgb, rough=0.72, shade=1.0):
    """A tile's own sixteen pixels, mapped onto every face of whatever it is
    built out of. `shade` darkens it for the sides, so a wall's face reads
    lighter than its return even before the sun gets to it.

    A cube's faces are each unit-square in UV, so one Mapping node aimed at
    this tile's patch of the atlas textures all six without touching a single
    UV by hand. Nearest-neighbour, because everything here is pixel art.
    """
    key = "%s_%.2f" % (name, shade)
    if key in bpy.data.materials:
        return bpy.data.materials[key]
    m = bpy.data.materials.new(key)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = rough
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.14
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    image, frames = atlas_image()
    base = name.split("_hi")[0].split("_lo")[0].split("_trunk")[0].split("_post")[0]
    base = base.split("_cap")[0].split("_lit")[0]
    base = base if base in frames else name
    if base in frames:
        fx, fy, fw, fh = frames[base]
        aw, ah = image.size
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = image
        tex.interpolation = 'Closest'
        tex.extension = 'EXTEND'
        # Straight UV, with every cube unwrapped face-by-face below. Box
        # projection cannot do this: it picks two of the three axes per face,
        # so an axis has to be the horizontal of one face and the vertical of
        # another, and no single mapping satisfies both. The whole town came
        # out purple, sampling somebody's robe from the far side of the atlas.
        mapping = nt.nodes.new("ShaderNodeMapping")
        mapping.inputs["Scale"].default_value = (fw / aw, fh / ah, 1.0)
        # Blender's V runs up the image and the atlas's runs down it.
        mapping.inputs["Location"].default_value = (fx / aw, 1.0 - (fy + fh) / ah, 0.0)
        coord = nt.nodes.new("ShaderNodeTexCoord")
        nt.links.new(coord.outputs["UV"], mapping.inputs["Vector"])
        nt.links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
        if shade >= 0.999:
            nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        else:
            mix = nt.nodes.new("ShaderNodeMixRGB")
            mix.blend_type = 'MULTIPLY'
            mix.inputs["Fac"].default_value = 1.0
            mix.inputs["Color2"].default_value = (shade, shade, shade, 1.0)
            nt.links.new(tex.outputs["Color"], mix.inputs["Color1"])
            nt.links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])
        return m

    lit = tuple(min(255, int(c * shade)) for c in rgb)
    bsdf.inputs["Base Color"].default_value = hex_rgb(lit)
    return m


def unit_uvs(obj):
    """Give every face of a box the whole 0-1 square.

    primitive_cube_add unwraps its six faces as a net inside one square, which
    is right for a texture of a cube and wrong for a texture that is one tile
    meant to appear on each face whole.
    """
    mesh = obj.data
    uv = mesh.uv_layers.active
    if uv is None:
        uv = mesh.uv_layers.new(name="tile")
    corners = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
    for poly in mesh.polygons:
        if poly.loop_total != 4:
            continue
        for i in range(4):
            uv.data[poly.loop_start + i].uv = corners[i]


def put(kind, x, y, z, sx, sy, sz, material, rot=None):
    if kind == "cube":
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(x, y, z))
    elif kind == "cyl":
        bpy.ops.mesh.primitive_cylinder_add(vertices=14, radius=0.5, depth=1.0,
                                            location=(x, y, z))
    elif kind == "cone":
        bpy.ops.mesh.primitive_cone_add(vertices=14, radius1=0.5, radius2=0.0,
                                        depth=1.0, location=(x, y, z))
    else:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=14, ring_count=7, radius=0.5,
                                             location=(x, y, z))
    o = bpy.context.object
    o.scale = (sx, sy, sz)
    if rot:
        o.rotation_euler = tuple(math.radians(a) for a in rot)
    o.data.materials.append(material)
    if kind == "cube":
        for p in o.data.polygons:
            p.use_smooth = False
        unit_uvs(o)
    return o


FACADES = True   # set per render: False when the camera looks straight down


def build_tile(name, colours, tx, ty):
    """One tile of the map, standing up. tx/ty are in tiles; the scene is in
    game pixels, with +x east, +y north and z up."""
    rgb = colours.get(name, (120, 120, 120))
    h = HEIGHT.get(name, 0)
    shape = SHAPE.get(name, "block")
    x = tx * PPT + PPT / 2.0
    y = -ty * PPT - PPT / 2.0     # map y runs down the screen, Blender's runs up

    # One material, and the sun does the shading. Pre-darkening the sides with
    # a mix node turned every wall in the town black, and in a render that is
    # the light's job anyway: a face turned away from the sun is darker because
    # it is turned away, not because somebody multiplied it by 0.72.
    top = mat(name, rgb, shade=1.0)
    side = top

    if shape == "tree":
        # A canopy that spills past its own tile, in three lumps. The single
        # sphere read as a lollipop; the reference's willow is most of the
        # square it stands in.
        leaf = mat("t_bush", colours.get("t_bush", rgb), rough=0.75)
        put("cyl", x, y, 6, 3.6, 3.6, 12, mat(name + "_trunk", rgb, shade=0.55))
        put("sphere", x, y, 19, 20, 20, 15, leaf)
        put("sphere", x - 6, y + 3, 22, 13, 13, 12, leaf)
        put("sphere", x + 5, y - 4, 23, 12, 12, 11, leaf)
        put("sphere", x - 2, y + 1, 27, 10, 10, 8, leaf)
        return
    if shape == "pine":
        put("cyl", x, y, 4, 2.8, 2.8, 8, mat(name + "_trunk", rgb, shade=0.5))
        for i, (r, z, sz) in enumerate(((7.6, 12, 9), (6.0, 19, 8), (4.2, 25, 7)))    :
            put("cone", x, y, z, r * 2, r * 2, sz, mat(name + "_%d" % i, rgb,
                                                       shade=1.0 - i * 0.08))
        return
    if shape == "dome":
        put("sphere", x, y, h * 0.45, 12, 12, h * 1.1, top)
        return
    if shape == "drum":
        put("cyl", x, y, h / 2.0, 11, 11, h, side)
        put("cyl", x, y, h, 11.4, 11.4, 1.6, top)
        return
    if shape == "post":
        put("cyl", x, y, h * 0.36, 2.6, 2.6, h * 0.72, mat(name + "_post", rgb, shade=0.5))
        lit = mat(name + "_lit", rgb, shade=1.35)
        if "Emission Strength" in lit.node_tree.nodes[1].inputs:
            lit.node_tree.nodes[1].inputs["Emission Color"].default_value = hex_rgb((255, 214, 140))
            lit.node_tree.nodes[1].inputs["Emission Strength"].default_value = 1.1
        put("cube", x, y, h - 2.5, 6, 6, 6, lit)
        return
    if shape == "rail":
        put("cyl", x, y, h * 0.5, 2.4, 2.4, h, side)
        put("cube", x, y, h - 2.0, PPT, 2.2, 2.2, top)
        put("cube", x, y, h - 6.0, PPT, 2.0, 2.0, top)
        return
    if shape == "tuft":
        put("cone", x, y, h / 2.0, 9, 9, h, top)
        return
    if shape == "roof":
        # A pitched slab sitting on the walls, with nothing under it. Giving it
        # its own box to stand on put a storey of dark roof tile between the
        # eaves and the windows, and the house read as a black hole with a red
        # hat: the rows below a roof on these maps are the wall, and they are
        # already standing there.
        put("cube", x, y, h - 4.0, PPT, PPT * 1.44, 5.0, top, rot=(34, 0, 0))
        return
    if shape == "ridge":
        put("cube", x, y, h - 3.0, PPT, 7.0, 4.5, mat(name + "_cap", rgb, shade=1.08))
        return

    if h < 0:
        # Water: a thin slab sunk to its depth, the banks' sides showing above.
        put("cube", x, y, h - 0.5, PPT, PPT, 1.0, top)
        return
    if h == 0:
        put("cube", x, y, -0.5, PPT, PPT, 1.0, top)
        return
    # One block, the tile's own art on every face. It used to be two: a body
    # and a thin cap for the top, and the cap sat exactly on the body's top
    # face. Two coincident surfaces trap Cycles' rays between them, and every
    # wall in the town came out solid black - not the material, not the light,
    # not the roof above it, all of which got blamed first.
    o = put("cube", x, y, h / 2.0, PPT, PPT, h, top)
    if name in WALLS and FACADES:
        # A wall's art belongs on the face you look at, not on top of it: a
        # window drawn on the top of a block is a skylight. The top gets slate.
        o.data.materials.append(mat(name + "_top", (78, 82, 92), rough=0.9, shade=1.0))
        for poly in o.data.polygons:
            if poly.normal.z > 0.5:
                poly.material_index = 1


# Tiles that together make a house. On these maps a house is a rectangle of
# roof rows over wall rows, and the two are NOT two depths - the roof is the
# building's top and the wall rows are its FRONT FACE, drawn below it on the
# screen because that is how a flat map shows a facade. Stand each row up as
# its own block and you get a stepped grey ziggurat; read them as one building
# and you get a house.
HOUSE_ROOF = {"t_roof", "t_blueroof", "t_rooftop"}
HOUSE_WALL = {"t_wall", "t_palewall", "t_window", "t_palewindow", "t_door"}
WALL_H = 26.0        # eaves height, game pixels
ROOF_PITCH = 24.0    # degrees
EAVE = 2.0           # how far the roof reaches past the walls


def find_houses(m, legend, rx, ry, rw, rh):
    """Connected rectangles of house tiles inside the region, each as
    (x0, y0, x1, y1, rows) with rows the list of [tile names] per map row."""
    rows = m["rows"]
    seen = set()
    houses = []
    for ty in range(ry, min(ry + rh, m["h"])):
        for tx in range(rx, min(rx + rw, m["w"])):
            spec = legend.get(rows[ty][tx])
            if spec is None or (tx, ty) in seen:
                continue
            if spec[0] not in HOUSE_ROOF and spec[0] not in HOUSE_WALL:
                continue
            # Flood the component, then take its bounding box: the maps only
            # ever draw houses as rectangles.
            stack, comp = [(tx, ty)], []
            while stack:
                cx, cy = stack.pop()
                if (cx, cy) in seen or not (0 <= cx < m["w"] and 0 <= cy < m["h"]):
                    continue
                sp = legend.get(rows[cy][cx])
                if sp is None or (sp[0] not in HOUSE_ROOF and sp[0] not in HOUSE_WALL):
                    continue
                seen.add((cx, cy))
                comp.append((cx, cy))
                stack += [(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)]
            x0 = min(c[0] for c in comp); x1 = max(c[0] for c in comp)
            y0 = min(c[1] for c in comp); y1 = max(c[1] for c in comp)
            names = [[legend[rows[y][x]][0] if rows[y][x] in legend else None
                      for x in range(x0, x1 + 1)] for y in range(y0, y1 + 1)]
            houses.append((x0, y0, x1, y1, names))
    return houses, seen


def build_house(x0, y0, x1, y1, names, colours):
    """One building: a body over the whole footprint, the wall rows' art on its
    south face, and a pitched roof with an overhang across all of it."""
    w = (x1 - x0 + 1) * PPT
    d = (y1 - y0 + 1) * PPT
    cx = x0 * PPT + w / 2.0
    cy = -(y0 * PPT) - d / 2.0
    south = -(y1 + 1) * PPT             # the face the camera sees

    wall_rows = [r for r in names if any(n in HOUSE_WALL for n in r)]
    roof_name = next((n for r in names for n in r if n in HOUSE_ROOF), "t_roof")
    wall_name = next((n for r in wall_rows for n in r
                      if n in ("t_wall", "t_palewall")), "t_wall")
    body = mat(wall_name, colours.get(wall_name, (200, 180, 150)), rough=0.85)

    # The body, its top plain slate - the roof covers it, but the overhang
    # leaves a sliver visible at the eaves and it should not be brick.
    o = put("cube", cx, cy, WALL_H / 2.0, w, d, WALL_H, body)
    o.data.materials.append(mat("slate", (70, 74, 84), rough=0.9))
    for poly in o.data.polygons:
        if poly.normal.z > 0.5:
            poly.material_index = 1

    # The facade: the wall rows, stacked down the south face in order, each
    # tile as a thin slab wearing its own art. Windows land where the map puts
    # windows and the door where it puts the door.
    if wall_rows:
        band = WALL_H / len(wall_rows)
        for i, row in enumerate(wall_rows):
            z = WALL_H - band * (i + 0.5)
            for k, n in enumerate(row):
                if n is None:
                    continue
                face = mat(n, colours.get(n, (200, 180, 150)), rough=0.85)
                # Proud of the wall, not flush with it: flush put the slab's
                # face exactly on the body's face, which is the coincident-
                # surface trap that turned the walls black the first time.
                put("cube", x0 * PPT + k * PPT + PPT / 2.0, south - 0.45, z,
                    PPT, 0.9, band, face)

    # A pitched roof over the lot, ridge east-west, with eaves past the walls
    # so it throws the shadow line onto the facade that every house in the
    # reference has under its roof.
    half = d / 2.0 + EAVE
    pitch = math.radians(ROOF_PITCH)
    slab_len = half / math.cos(pitch)
    rise = half * math.tan(pitch)
    roof = mat(roof_name, colours.get(roof_name, (160, 66, 63)), rough=0.8)
    for sign in (-1, 1):
        put("cube", cx, cy + sign * half / 2.0, WALL_H + rise / 2.0,
            w + EAVE * 2, slab_len, 2.4, roof, rot=(sign * -ROOF_PITCH, 0, 0))
    put("cube", cx, cy, WALL_H + rise + 0.3, w + EAVE * 2 + 1, 3.0, 1.2,
        mat(roof_name + "_ridge", colours.get(roof_name, (160, 66, 63)), rough=0.8))


def build(map_id, rx, ry, rw, rh, houses_too=True):
    """Stand the map's tiles up as geometry wearing their own art."""
    global _ATLAS_IMAGE
    # A factory reset takes the loaded atlas with it, and a cached handle to a
    # deleted datablock is a crash on the second render rather than an error on
    # the first.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _ATLAS_IMAGE = None
    maps = json.load(open(os.path.join(ROOT, "assets", "maps.json")))
    data = json.load(open(os.path.join(ROOT, "assets", "gamedata.json")))
    legend, underlay = data["legend"], data["underlay"]
    m = maps[map_id]
    ground = m.get("ground", "t_grass")
    colours = tile_colours()

    PAD = 3
    rx, ry, rw, rh = rx - PAD, ry - PAD, rw + PAD * 2, rh + PAD * 2
    rx, ry = max(0, rx), max(0, ry)
    houses, taken = find_houses(m, legend, rx, ry, rw, rh) if houses_too else ([], set())
    for x0, y0, x1, y1, names in houses:
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                build_tile(ground, colours, tx, ty)     # the ground under it
        build_house(x0, y0, x1, y1, names, colours)

    for ty in range(ry, min(ry + rh, m["h"])):
        row = m["rows"][ty]
        for tx in range(rx, min(rx + rw, m["w"])):
            if (tx, ty) in taken:
                continue
            ch = row[tx]
            spec = legend.get(ch)
            if spec is None:
                continue
            name = spec[0]
            # Props sit on something. The same underlay table the game uses to
            # stop a barrel floating on a void puts a floor under it here.
            under = underlay.get(ch)
            if under:
                build_tile(ground if under == "ground" else under, colours, tx, ty)
            elif HEIGHT.get(name, 0) > 0:
                build_tile(ground, colours, tx, ty)
            build_tile(name, colours, tx, ty)
    return m, colours


# The three ways of looking at it. `pitch` is degrees from horizontal: 90 is
# straight down, which is the angle the game is drawn from today.
# `sun_xy` is where on the ground the light is heading: (0.55, 0.72) is a sun
# over the viewer's left shoulder lighting the faces the camera sees, and
# (0.62, -0.42) is one from the upper left of the screen, raking across roofs
# and ground and leaving the facades in shade with the fill to pick them up -
# which is how the reference town is lit. `haze` is a thin scattering volume
# over the whole scene, so the sun throws visible shafts wherever a roof or a
# canopy interrupts it. `soft` is the sun's angular size: bigger is softer
# shadow edges. `grade` pulls the finished frame toward the reference's cool,
# misty palette before it is quantised.
STYLES = {
    "flat":      {"pitch": 90.0, "yaw": 0.0,  "sun": 58.0, "sun_xy": (0.55, 0.72),
                  "fill": 0.30, "dof": 0.0, "haze": 0.0, "soft": 2.5, "grade": False,
                  "note": "the angle it is drawn from now, with real light"},
    "quarter":   {"pitch": 58.0, "yaw": 0.0,  "sun": 46.0, "sun_xy": (0.55, 0.72),
                  "fill": 0.28, "dof": 0.0, "haze": 0.0, "soft": 2.5, "grade": False,
                  "note": "tilted far enough to see the sides of things"},
    "diorama":   {"pitch": 46.0, "yaw": 12.0, "sun": 38.0, "sun_xy": (0.55, 0.72),
                  "fill": 0.24, "dof": 0.9, "haze": 0.0, "soft": 2.5, "grade": False,
                  "note": "lower, softer, with the ends of the world out of focus"},
    "reference": {"pitch": 57.0, "yaw": 0.0,  "sun": 38.0, "sun_xy": (0.62, -0.42),
                  "fill": 0.78, "dof": 0.0, "haze": 0.0022, "soft": 6.0, "grade": True,
                  "note": "a strict three-quarter view lit from the upper left, "
                          "with haze for the sun to make shafts in"},
}


def light(style):
    world = bpy.data.worlds.new("sky")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    # A cool grey-green sky rather than a blue one: it is what fills every
    # shadow in the frame, and the reference's shadows are sage, not navy.
    bg.inputs["Color"].default_value = hex_rgb((168, 186, 178))
    bg.inputs["Strength"].default_value = style["fill"]

    sun_data = bpy.data.lights.new("sun", type="SUN")
    sun_data.energy = 5.2 if style["haze"] > 0 else 4.6
    sun_data.color = hex_rgb((255, 240, 208))[:3]
    sun_data.angle = math.radians(style["soft"])
    sun = bpy.data.objects.new("sun", sun_data)
    bpy.context.collection.objects.link(sun)
    # Over the viewer's left shoulder, not from behind the houses. The first
    # pass had it coming from the far side of the map, which is correct for a
    # sunset and useless for a town: every face the camera could see was the
    # one in shadow, and the houses came out as black holes under red roofs.
    a = math.radians(style["sun"])
    sx, sy = style["sun_xy"]
    d = Vector((math.cos(a) * sx, math.cos(a) * sy, -math.sin(a)))
    sun.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def haze(rx, ry, rw, rh, density):
    """A thin scattering volume over the whole scene.

    On its own the sun just lights things. Through a little fog it becomes
    visible where it passes between a roof and the ground, and that is the
    reference's whole atmosphere: the light is something you can see, not
    just something that falls on the tiles.
    """
    if density <= 0.0:
        return
    cx = rx * PPT + rw * PPT / 2.0
    cy = -(ry * PPT + rh * PPT / 2.0)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, 22.0))
    o = bpy.context.object
    o.scale = (rw * PPT * 1.6, rh * PPT * 1.6, 48.0)
    m = bpy.data.materials.new("haze")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Density"].default_value = density
    vol.inputs["Anisotropy"].default_value = 0.25
    vol.inputs["Color"].default_value = hex_rgb((214, 226, 220))
    nt.links.new(vol.outputs["Volume"], out.inputs["Volume"])
    o.data.materials.append(m)
    o.display_type = 'WIRE'
    o.visible_shadow = False


def render(map_id, rx, ry, rw, rh, style_name, out_path, samples, builder=None):
    """Photograph a region. `builder` puts the scene together; by default that
    is build() above, which stands the map's own tiles up. hdtown.py passes a
    builder that models the town instead. Camera, light and haze are the same
    either way, so two builders can be judged on the geometry alone."""
    style = STYLES[style_name]
    global FACADES
    FACADES = style["pitch"] < 89.0
    (builder or build)(map_id, rx, ry, rw, rh, FACADES)
    light(style)
    haze(rx, ry, rw, rh, style["haze"])
    scene = bpy.context.scene
    if style["haze"] > 0.0:
        scene.cycles.volume_bounces = 1
        scene.cycles.volume_max_steps = 256

    # Orthographic, because the game is: a tile has to be the same size at the
    # near edge of the screen and the far one, or the tilemap under it stops
    # lining up with what is drawn.
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = rw * PPT
    cam = bpy.data.objects.new("cam", cam_data)
    bpy.context.collection.objects.link(cam)
    scene.camera = cam

    centre = Vector((rx * PPT + rw * PPT / 2.0, -(ry * PPT + rh * PPT / 2.0), 6.0))
    # Aimed by construction rather than by to_track_quat, which has no opinion
    # about which way up an image is when the camera looks straight down - and
    # answered that by rotating the whole map a half turn.
    #
    # A camera at rest looks down -Z with +X to the right and +Y up the image,
    # which is exactly the game's own view. Tilting is one rotation about X:
    # 90 degrees of pitch is straight down, less leans the camera back until
    # the sides of things come into view.
    tilt = math.radians(90.0 - style["pitch"])
    turn = math.radians(style["yaw"])
    cam.rotation_euler = (tilt, 0.0, turn)
    look = Vector((-math.sin(turn) * math.sin(tilt),
                   math.cos(turn) * math.sin(tilt),
                   -math.cos(tilt)))
    cam.location = centre - look * 400.0
    if style["dof"] > 0.0:
        cam_data.dof.use_dof = True
        cam_data.dof.focus_distance = 400.0
        cam_data.dof.aperture_fstop = 0.7 / style["dof"]

    # A tilted camera sees a taller slice than a flat one does: the far rows
    # are foreshortened, and everything standing up needs room above them.
    lean = math.radians(style["pitch"])
    height_tiles = rh if style["pitch"] >= 89.0 else rh * math.sin(lean) + 3.4
    scene.render.resolution_x = int(rw * PPT * SUPER)
    scene.render.resolution_y = int(height_tiles * PPT * SUPER)
    scene.render.resolution_percentage = 100
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False
    scene.render.filter_size = 1.1
    scene.render.film_transparent = False
    scene.view_settings.view_transform = 'Standard'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.filepath = out_path
    bpy.ops.render.render(write_still=True)
    return out_path


def grade(img):
    """Pull a frame toward the reference's palette: cool, misty, low in
    saturation, with the shadows lifted rather than black and the warm accents
    left warm. Applied at game resolution, before anything is quantised, so
    the palette that gets chosen is already the one we want.
    """
    from spritecook.imaging import Image
    out = Image(img.width, img.height)
    tint = (0.62, 0.72, 0.68)          # sage, as a multiplier on the grey
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = img.get(x, y)
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            # Desaturate less for warm pixels than cool ones, so the shutters
            # and the lamps keep their colour while the stone goes to sage.
            warm = max(0.0, min(1.0, (r - b) / 96.0))
            keep = 0.40 + 0.24 * warm
            r2 = lum + (r - lum) * keep
            g2 = lum + (g - lum) * keep
            b2 = lum + (b - lum) * keep
            # Mist: lift the darks toward a grey-green and cap the brights.
            k = 1.0 - lum / 255.0
            r2 = r2 * (1 - 0.16 * k) + 255 * tint[0] * 0.16 * k
            g2 = g2 * (1 - 0.16 * k) + 255 * tint[1] * 0.16 * k
            b2 = b2 * (1 - 0.16 * k) + 255 * tint[2] * 0.16 * k
            r2 = 0.97 * r2 + 3
            g2 = 0.97 * g2 + 5
            b2 = 0.97 * b2 + 4
            out.set(x, y, (int(max(0, min(255, r2))), int(max(0, min(255, g2))),
                           int(max(0, min(255, b2))), a))
    return out


def finish(raw_path, style, colours=0):
    """The render at game resolution, graded if the style asks for it, and
    quantised to `colours` when that is set, saved beside the raw frame. This
    is what a human compares; the raw frame is four times too big to judge as
    pixel art, and a full-colour render next to palette sprites is a
    photograph next to a drawing until it has been through the palette step
    the monsters and backdrops go through."""
    from spritecook.imported import downscale
    img = read_png(raw_path)
    small = downscale(img, img.width // SUPER, img.height // SUPER)
    if style["grade"]:
        small = grade(small)
    if colours > 0:
        from pixelate import build_palette, quantise
        small = quantise(small, build_palette(small, colours))
    out = raw_path.replace(".png", "_game.png")
    with open(out, "wb") as fh:
        fh.write(small.to_png())
    return out, small


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", default="town")
    ap.add_argument("--x", type=int, default=16)
    ap.add_argument("--y", type=int, default=12)
    ap.add_argument("--w", type=int, default=18)
    ap.add_argument("--h", type=int, default=14)
    ap.add_argument("--style", default="all",
                    help="flat, quarter, diorama, reference, or all")
    ap.add_argument("--full", action="store_true",
                    help="the whole map, written to art/prerender/<map>.png at game "
                         "resolution for the game to draw under its sprites")
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--out", default=os.path.join(ROOT, "art", "blender"))
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    if args.full:
        # The camera has to keep every tile where the tilemap already has it
        # for the game to draw sprites over the picture, so this is the flat
        # style only: straight down, one game pixel per pixel, no grade.
        maps = json.load(open(os.path.join(ROOT, "assets", "maps.json")))
        m = maps[args.map]
        style = "flat" if args.style == "all" else args.style
        raw = os.path.join(args.out, "full_%s.png" % args.map)
        render(args.map, 0, 0, m["w"], m["h"], style, raw, args.samples)
        game, small = finish(raw, STYLES[style])
        dest = os.path.join(ROOT, "art", "prerender", "%s.png" % args.map)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as fh:
            fh.write(small.to_png())
        assert (small.width, small.height) == (m["w"] * PPT, m["h"] * PPT), \
            "prerender is %dx%d, map is %dx%d" % (small.width, small.height,
                                                   m["w"] * PPT, m["h"] * PPT)
        print("full     -> %s  %dx%d" % (os.path.relpath(dest, ROOT), small.width, small.height))
        return
    names = list(STYLES) if args.style == "all" else [args.style]
    for name in names:
        path = os.path.join(args.out, "town_%s.png" % name)
        render(args.map, args.x, args.y, args.w, args.h, name, path, args.samples)
        game, small = finish(path, STYLES[name])
        print("%-9s -> %s  %dx%d  (%s)"
              % (name, os.path.relpath(game, ROOT), small.width, small.height,
                 STYLES[name]["note"]))


if __name__ == "__main__":
    main()
