#!/usr/bin/env python3
"""Model a piece of a map, rather than standing its tiles up.

town.py textures geometry with the game's own 16x16 tiles, so Blender only
ever contributes the light: the picture can never be more detailed than the
tiles it is wearing, and a lit tilemap mostly looks like a tilemap. This
builds the same region out of real things - flagstones with grout, shingled
roofs laid course by course, windows with frames and shutters, trees with
trunks and a canopy, a well with a roof and a bucket - with procedural
materials on all of it, and then takes the render down to game resolution
and through the palette, the way the monsters and backdrops go.

Same maps.json, same legend, same camera and light as town.py, so the two
can be judged on the geometry alone.

    pip install bpy==4.5.13
    python3 tools/blender/hdtown.py                       # flat and reference
    python3 tools/blender/hdtown.py --style reference --colours 40
"""

import argparse
import json
import math
import os
import random
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import town  # noqa: E402
from town import PPT, put, hex_rgb, find_houses, HOUSE_ROOF, HOUSE_WALL  # noqa: E402

WALL_H = 26.0
ROOF_PITCH = 26.0
EAVE = 3.0


# ------------------------------------------------------------------ materials

def _nodes(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.2
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    # World position, so a texture runs across tile boundaries without a seam
    # instead of restarting on every slab.
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    return m, nt, bsdf, geo.outputs["Position"]


def _scaled(nt, pos, scale):
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale, scale, scale)
    nt.links.new(pos, mp.inputs["Vector"])
    return mp.outputs["Vector"]


def _ramp(nt, a, b):
    r = nt.nodes.new("ShaderNodeValToRGB")
    r.color_ramp.elements[0].color = hex_rgb(a)
    r.color_ramp.elements[1].color = hex_rgb(b)
    return r


def _bump(nt, bsdf, fac, strength, distance=0.4):
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = strength
    bp.inputs["Distance"].default_value = distance
    nt.links.new(fac, bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], bsdf.inputs["Normal"])


_CACHE = {}

# ------------------------------------------------------------------ fast put
# town.put() builds every primitive through an operator, and each operator
# call re-evaluates the whole scene, so a few thousand grass blades and roof
# shingles go quadratic and a test render sits in the build phase for ten
# minutes. Here each primitive kind is made once, and every later put() is a
# mesh copy linked straight into the collection: no operator, no re-evaluation.
_TEMPLATES = {}


def _template(kind):
    me = _TEMPLATES.get(kind)
    if me is not None and me.name in bpy.data.meshes:
        return me
    o = town.put(kind, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, None)
    me = o.data
    me.materials.clear()
    me.use_fake_user = True
    bpy.data.objects.remove(o)
    _TEMPLATES[kind] = me
    return me


def put(kind, x, y, z, sx, sy, sz, material, rot=None):
    me = _template(kind).copy()
    me.materials.append(material)
    o = bpy.data.objects.new("hd_" + kind, me)
    o.location = (x, y, z)
    o.scale = (sx, sy, sz)
    if rot:
        o.rotation_euler = tuple(math.radians(a) for a in rot)
    bpy.context.collection.objects.link(o)
    return o



def material(kind, **kw):
    key = (kind, tuple(sorted(kw.items())))
    if key in _CACHE and _CACHE[key].name in bpy.data.materials:
        return _CACHE[key]
    m = MATERIALS[kind](**kw)
    _CACHE[key] = m
    return m


def m_stone(a=(182, 184, 192), b=(146, 150, 162), grout=(72, 74, 86), scale=0.042,
            rough=0.85):
    """Flagstones: a brick pattern with mortar, two stone shades varied by
    noise, and the mortar cut in as bump."""
    m, nt, bsdf, pos = _nodes("stone")
    v = _scaled(nt, pos, scale)
    brick = nt.nodes.new("ShaderNodeTexBrick")
    brick.inputs["Scale"].default_value = 1.0
    brick.inputs["Mortar Size"].default_value = 0.06
    brick.inputs["Bias"].default_value = 0.0
    brick.offset = 0.5
    nt.links.new(v, brick.inputs["Vector"])
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 2.4
    nt.links.new(v, noise.inputs["Vector"])
    ramp = _ramp(nt, a, b)
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], brick.inputs["Color1"])
    brick.inputs["Color2"].default_value = hex_rgb(tuple(int(c * 0.9) for c in a))
    brick.inputs["Mortar"].default_value = hex_rgb(grout)
    nt.links.new(brick.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rough
    _bump(nt, bsdf, brick.outputs["Fac"], 0.4, 0.6)
    return m


def m_grass(a=(110, 172, 82), b=(62, 120, 54), scale=0.045):
    m, nt, bsdf, pos = _nodes("grass")
    v = _scaled(nt, pos, scale)
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 3.0
    noise.inputs["Detail"].default_value = 2.0
    noise.inputs["Roughness"].default_value = 0.4
    nt.links.new(v, noise.inputs["Vector"])
    ramp = _ramp(nt, a, b)
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.92
    fine = nt.nodes.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = 6.0
    nt.links.new(v, fine.inputs["Vector"])
    _bump(nt, bsdf, fine.outputs["Fac"], 0.25, 0.3)
    return m


def m_dirt(a=(190, 148, 92), b=(146, 106, 60), scale=0.06):
    m, nt, bsdf, pos = _nodes("dirt")
    v = _scaled(nt, pos, scale)
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 2.0
    nt.links.new(v, noise.inputs["Vector"])
    ramp = _ramp(nt, a, b)
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.95
    pebbles = nt.nodes.new("ShaderNodeTexVoronoi")
    pebbles.inputs["Scale"].default_value = 5.0
    nt.links.new(v, pebbles.inputs["Vector"])
    _bump(nt, bsdf, pebbles.outputs["Distance"], 0.3, 0.4)
    return m


def m_wood(a=(150, 104, 58), b=(96, 62, 32), scale=0.5, rough=0.7, along="x"):
    """Planks: bands along one axis, wobbled by noise, with the grain as bump."""
    m, nt, bsdf, pos = _nodes("wood")
    v = _scaled(nt, pos, scale)
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = 'BANDS'
    wave.bands_direction = 'X' if along == "x" else 'Y'
    wave.inputs["Scale"].default_value = 0.9
    wave.inputs["Distortion"].default_value = 3.5
    wave.inputs["Detail"].default_value = 2.0
    nt.links.new(v, wave.inputs["Vector"])
    ramp = _ramp(nt, a, b)
    nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rough
    _bump(nt, bsdf, wave.outputs["Fac"], 0.2, 0.25)
    return m


def m_plaster(a=(226, 210, 178), b=(196, 178, 146), scale=0.1):
    m, nt, bsdf, pos = _nodes("plaster")
    v = _scaled(nt, pos, scale)
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 3.0
    noise.inputs["Detail"].default_value = 5.0
    nt.links.new(v, noise.inputs["Vector"])
    ramp = _ramp(nt, a, b)
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.9
    _bump(nt, bsdf, noise.outputs["Fac"], 0.15, 0.3)
    return m


def m_flat(rgb, rough=0.7, metallic=0.0, emit=0.0):
    m, nt, bsdf, pos = _nodes("flat")
    bsdf.inputs["Base Color"].default_value = hex_rgb(rgb)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metallic
    if emit > 0 and "Emission Strength" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = hex_rgb(rgb)
        bsdf.inputs["Emission Strength"].default_value = emit
    return m


def m_leaf(a=(92, 150, 70), b=(52, 104, 46), scale=0.3):
    m, nt, bsdf, pos = _nodes("leaf")
    v = _scaled(nt, pos, scale)
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 4.0
    noise.inputs["Detail"].default_value = 4.0
    nt.links.new(v, noise.inputs["Vector"])
    ramp = _ramp(nt, a, b)
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.75
    _bump(nt, bsdf, noise.outputs["Fac"], 0.5, 0.8)
    return m


def m_water(rgb=(64, 132, 178)):
    m, nt, bsdf, pos = _nodes("water")
    v = _scaled(nt, pos, 0.15)
    bsdf.inputs["Base Color"].default_value = hex_rgb(rgb)
    bsdf.inputs["Roughness"].default_value = 0.08
    ripple = nt.nodes.new("ShaderNodeTexNoise")
    ripple.inputs["Scale"].default_value = 3.0
    nt.links.new(v, ripple.inputs["Vector"])
    _bump(nt, bsdf, ripple.outputs["Fac"], 0.3, 0.2)
    return m


MATERIALS = {
    "stone": m_stone, "grass": m_grass, "dirt": m_dirt, "wood": m_wood,
    "plaster": m_plaster, "flat": m_flat, "leaf": m_leaf, "water": m_water,
}


# ------------------------------------------------------------------- things

def _rng(tx, ty, salt=0):
    return random.Random(tx * 7919 + ty * 104729 + salt)


def ground(name, tx, ty):
    x = tx * PPT + PPT / 2.0
    y = -ty * PPT - PPT / 2.0
    if name in ("t_water0", "t_water1"):
        put("cube", x, y, -2.5, PPT, PPT, 1.0, material("water"))
        return
    if name == "t_ice":
        put("cube", x, y, -1.5, PPT, PPT, 1.0, material("flat", rgb=(190, 214, 236), rough=0.15))
        return
    kind = {
        "t_cobble": material("stone"),
        "t_crypt": material("stone", a=(118, 112, 132), b=(84, 78, 98), grout=(48, 44, 58), scale=0.19),
        "t_drowned": material("stone", a=(80, 130, 148), b=(52, 92, 108), grout=(28, 48, 60), scale=0.19),
        "t_path": material("dirt"),
        "t_sand": material("dirt", a=(222, 206, 158), b=(196, 176, 126)),
        "t_snow": material("plaster", a=(226, 232, 242), b=(200, 210, 226)),
        "t_plank": material("wood", a=(170, 124, 72), b=(120, 84, 46), scale=0.35),
        "t_bridge": material("wood", a=(150, 104, 58), b=(96, 62, 32), scale=0.4),
        "t_rug": material("flat", rgb=(150, 52, 56), rough=0.95),
    }.get(name, material("grass"))
    put("cube", x, y, -0.5, PPT, PPT, 1.0, kind)
    if name in ("t_grass", "t_grass2", "t_grass3", "t_flowers", "t_tallgrass"):
        # A few blades, so grass has a surface and not just a colour.
        r = _rng(tx, ty)
        n = 7 if name == "t_tallgrass" else 0
        for _ in range(n):
            gx, gy = x + r.uniform(-6, 6), y + r.uniform(-6, 6)
            h = r.uniform(2.0, 4.5) if name != "t_tallgrass" else r.uniform(4, 7)
            blade = put("cone", gx, gy, h / 2.0, 1.6, 1.6, h,
                        material("leaf", a=(132, 190, 96), b=(96, 152, 72)),
                        rot=(r.uniform(-14, 14), r.uniform(-14, 14), 0))
            blade.visible_shadow = False   # a blade's shadow is a dark speck, not grass
        if name == "t_flowers":
            for _ in range(2):
                fx, fy = x + r.uniform(-5, 5), y + r.uniform(-5, 5)
                put("cyl", fx, fy, 1.6, 0.5, 0.5, 3.2, material("leaf"))
                rgb = r.choice(((232, 92, 110), (244, 214, 96), (240, 240, 232)))
                put("sphere", fx, fy, 3.5, 2.6, 2.6, 1.8, material("flat", rgb=rgb, rough=0.8))


_FENCE = set()   # every fence tile in the region, so rails can meet their neighbours


def fence(tx, ty):
    x = tx * PPT + PPT / 2.0
    y = -ty * PPT - PPT / 2.0
    wood = material("wood", a=(140, 96, 52), b=(90, 58, 30), scale=0.6, along="y")
    r = _rng(tx, ty, 3)
    put("cube", x, y, 5.5, 2.6, 2.6, 11, wood, rot=(r.uniform(-2, 2), r.uniform(-2, 2), 0))
    rail = material("wood", a=(150, 104, 58), b=(96, 62, 32), scale=0.6)
    rail_y = material("wood", a=(150, 104, 58), b=(96, 62, 32), scale=0.6, along="y")
    # A rail runs from this post to each neighbouring fence post. A post with no
    # neighbours gets a stub each way, so it still reads as fence.
    sides = [(dx, dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)) if (tx + dx, ty + dy) in _FENCE]
    if not sides:
        sides = [(1, 0), (-1, 0)]
    half = PPT / 2.0 + 0.4
    for dx, dy in sides:
        cx, cy = x + dx * half / 2.0, y - dy * half / 2.0
        if dx:
            for z in (9.0, 4.8):
                put("cube", cx, cy, z, half, 1.4, 1.6, rail)
        else:
            for z in (9.0, 4.8):
                put("cube", cx, cy, z, 1.4, half, 1.6, rail_y)


def lamp(tx, ty, lit=True):
    x = tx * PPT + PPT / 2.0
    y = -ty * PPT - PPT / 2.0
    iron = material("flat", rgb=(52, 52, 60), rough=0.55, metallic=0.4)
    glass = material("flat", rgb=(255, 196, 104), emit=2.0) if lit \
        else material("flat", rgb=(150, 160, 170), rough=0.2)
    put("cyl", x, y, 0.8, 4.0, 4.0, 1.6, iron)              # base
    put("cyl", x, y, 10.5, 2.4, 2.4, 19.0, iron)            # post
    put("cube", x, y - 1.6, 20.4, 1.2, 4.4, 1.2, iron)      # arm
    put("cube", x, y - 3.6, 21.8, 6.4, 6.4, 5.0, glass)      # the glowing pane
    put("cone", x, y - 3.6, 25.0, 4.4, 4.4, 1.4, iron)      # cap, smaller than the pane
    put("sphere", x, y - 3.6, 25.9, 1.2, 1.2, 1.2, iron)    # finial


def well(tx, ty):
    x = tx * PPT + PPT / 2.0
    y = -ty * PPT - PPT / 2.0
    stone = material("stone", a=(222, 214, 202), b=(190, 182, 170), grout=(96, 90, 86), scale=0.07)
    wood = material("wood", a=(140, 96, 52), b=(90, 58, 30), scale=0.6, along="y")
    put("cyl", x, y, 3.0, 14.6, 14.6, 6.0, stone)          # the wall of it
    put("cyl", x, y, 5.0, 10.6, 10.6, 1.6, material("water", rgb=(28, 70, 118)))
    put("cyl", x, y, 6.5, 15.8, 15.8, 1.2, stone)          # the rim
    put("cyl", x + 5.0, y - 3.0, 8.0, 3.0, 3.0, 3.0, wood)  # a bucket left on the rim


def tree(tx, ty, snow=False):
    x = tx * PPT + PPT / 2.0
    y = -ty * PPT - PPT / 2.0
    r = _rng(tx, ty, 1)
    bark = material("wood", a=(92, 68, 46), b=(52, 38, 26), scale=0.45, along="y", rough=0.95)
    put("cone", x, y, 7.0, 5.6, 5.6, 14.0, bark)           # a tapered trunk
    for i in range(3):                                     # branches
        a = r.uniform(0, 360)
        put("cyl", x + math.cos(math.radians(a)) * 3.0, y + math.sin(math.radians(a)) * 3.0,
            15.0, 1.4, 1.4, 8.0, bark, rot=(math.sin(math.radians(a)) * 35, -math.cos(math.radians(a)) * 35, 0))
    if snow:
        leaves = [material("leaf", a=(72, 110, 84), b=(40, 70, 52)),
                  material("plaster", a=(232, 238, 246), b=(206, 216, 230))]
        for i, (rad, z, sz) in enumerate(((9.5, 14, 10), (7.5, 21, 9), (5.0, 27, 8))):
            put("cone", x, y, z, rad * 2, rad * 2, sz, leaves[0])
            put("cone", x, y, z + sz * 0.32, rad * 1.9, rad * 1.9, sz * 0.4, leaves[1])
        return
    leaves = [material("leaf"), material("leaf", a=(112, 172, 82), b=(64, 120, 56)),
              material("leaf", a=(72, 126, 60), b=(40, 84, 40))]
    # A canopy as a cloud of lumps inside an ellipsoid. Enough of them that
    # the light finds edges everywhere, which is what a canopy is.
    for i in range(36):
        u, v, w = r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(-1, 1)
        if u * u + v * v + w * w > 1.0:
            continue
        cx, cy, cz = x + u * 13.0, y + v * 13.0, 23.0 + w * 7.5
        rad = r.uniform(5.5, 8.5)
        put("sphere", cx, cy, cz, rad, rad, rad * 0.9, r.choice(leaves))


def bush(tx, ty):
    x = tx * PPT + PPT / 2.0
    y = -ty * PPT - PPT / 2.0
    r = _rng(tx, ty, 2)
    leaves = [material("leaf"), material("leaf", a=(112, 172, 82), b=(64, 120, 56))]
    for i in range(9):
        u, v = r.uniform(-1, 1), r.uniform(-1, 1)
        rad = r.uniform(3.2, 4.8)
        put("sphere", x + u * 4.5, y + v * 4.5, 3.6 + r.uniform(0, 2), rad, rad, rad * 0.8, r.choice(leaves))


def rock(tx, ty):
    x = tx * PPT + PPT / 2.0
    y = -ty * PPT - PPT / 2.0
    r = _rng(tx, ty, 4)
    stone = material("stone", a=(150, 152, 160), b=(104, 108, 120), grout=(90, 92, 100), scale=0.6)
    for i in range(3):
        put("sphere", x + r.uniform(-3, 3), y + r.uniform(-3, 3), r.uniform(2, 3.5),
            r.uniform(5, 7), r.uniform(5, 7), r.uniform(3.5, 5), stone,
            rot=(r.uniform(0, 40), r.uniform(0, 40), r.uniform(0, 90)))


def barrel(tx, ty):
    x = tx * PPT + PPT / 2.0
    y = -ty * PPT - PPT / 2.0
    put("cyl", x, y, 5.0, 10.0, 10.0, 10.0, material("wood", a=(150, 104, 58), b=(96, 62, 32), scale=0.5, along="y"))
    iron = material("flat", rgb=(50, 50, 56), rough=0.5, metallic=0.6)
    for z in (2.5, 7.5):
        put("cyl", x, y, z, 10.6, 10.6, 1.0, iron)


def chest(tx, ty):
    x = tx * PPT + PPT / 2.0
    y = -ty * PPT - PPT / 2.0
    wood = material("wood", a=(160, 112, 62), b=(104, 68, 34), scale=0.5)
    put("cube", x, y, 3.0, 11.0, 8.0, 6.0, wood)
    put("cube", x, y, 6.8, 11.4, 8.4, 2.0, wood)
    put("cube", x, y, 5.0, 2.0, 8.8, 7.0, material("flat", rgb=(222, 186, 80), rough=0.35, metallic=0.8))


def sign(tx, ty):
    x = tx * PPT + PPT / 2.0
    y = -ty * PPT - PPT / 2.0
    wood = material("wood", a=(150, 104, 58), b=(96, 62, 32), scale=0.6)
    put("cube", x, y, 5.0, 1.8, 1.8, 10.0, wood)
    put("cube", x, y - 0.6, 10.0, 12.0, 1.4, 6.0, wood)


def mountain(tx, ty):
    """A cliff block: grey rock, not brickwork, with a few boulders on top."""
    x = tx * PPT + PPT / 2.0
    y = -ty * PPT - PPT / 2.0
    r = _rng(tx, ty, 6)
    rock_m = material("dirt", a=(132, 130, 140), b=(84, 84, 96), scale=0.05)
    put("cube", x, y, 11.0, PPT, PPT, 22.0 + r.uniform(-2, 3), rock_m)
    for i in range(2):
        put("sphere", x + r.uniform(-4, 4), y + r.uniform(-4, 4), 22.0 + r.uniform(1, 3),
            r.uniform(6, 9), r.uniform(6, 9), r.uniform(4, 6), rock_m,
            rot=(r.uniform(0, 30), r.uniform(0, 30), r.uniform(0, 90)))


def wall_block(tx, ty, name):
    x = tx * PPT + PPT / 2.0
    y = -ty * PPT - PPT / 2.0
    if name in ("t_cryptwall", "t_drownwall"):
        stone = material("stone", a=(96, 90, 112), b=(66, 62, 80), grout=(36, 32, 46), scale=0.05) \
            if name == "t_cryptwall" else \
            material("stone", a=(44, 80, 96), b=(26, 52, 66), grout=(12, 26, 36), scale=0.05)
    else:
        stone = material("stone", a=(160, 162, 170), b=(120, 124, 136), grout=(66, 68, 80), scale=0.05)
    put("cube", x, y, 11.0, PPT, PPT, 22.0, stone)


def house(x0, y0, x1, y1, names):
    w = (x1 - x0 + 1) * PPT
    d = (y1 - y0 + 1) * PPT
    cx = x0 * PPT + w / 2.0
    cy = -(y0 * PPT) - d / 2.0
    south = -(y1 + 1) * PPT

    wall_rows = [r for r in names if any(n in HOUSE_WALL for n in r)]
    roof_name = next((n for r in names for n in r if n in HOUSE_ROOF), "t_roof")
    pale = any(n == "t_palewall" for r in wall_rows for n in r)
    plaster = material("plaster") if not pale else \
        material("plaster", a=(202, 206, 224), b=(170, 176, 198))
    wood = material("wood", a=(120, 78, 44), b=(78, 48, 26), scale=0.5, along="y")
    dark = material("flat", rgb=(38, 36, 44), rough=0.9)
    glass = material("flat", rgb=(150, 200, 230), rough=0.08)

    o = put("cube", cx, cy, WALL_H / 2.0, w, d, WALL_H, plaster)
    o.data.materials.append(material("flat", rgb=(70, 74, 84), rough=0.9))
    for poly in o.data.polygons:
        if poly.normal.z > 0.5:
            poly.material_index = 1
    # Timber frame lines on the plaster.
    for k in range(x1 - x0 + 2):
        put("cube", x0 * PPT + k * PPT, south - 0.3, WALL_H / 2.0, 1.4, 0.6, WALL_H, wood)
    put("cube", cx, south - 0.3, WALL_H - 0.7, w + 1.0, 0.6, 1.4, wood)
    put("cube", cx, south - 0.3, 0.7, w + 1.0, 0.6, 1.4, wood)

    if wall_rows:
        band = WALL_H / len(wall_rows)
        for i, row in enumerate(wall_rows):
            zc = WALL_H - band * (i + 0.5)
            for k, n in enumerate(row):
                fx = x0 * PPT + k * PPT + PPT / 2.0
                if n in ("t_window", "t_palewindow"):
                    put("cube", fx, south - 0.4, zc, 8.0, 0.8, 7.0, dark)          # recess
                    put("cube", fx, south - 0.6, zc, 6.4, 0.4, 5.4, glass)         # pane
                    put("cube", fx, south - 0.9, zc, 0.6, 0.6, 5.4, wood)          # mullion
                    put("cube", fx, south - 0.9, zc, 6.4, 0.6, 0.6, wood)
                    put("cube", fx, south - 1.0, zc - 3.9, 9.4, 1.6, 0.9, wood)    # sill
                    for sx in (-1, 1):                                              # shutters
                        put("cube", fx + sx * 6.0, south - 0.8, zc, 3.0, 0.8, 7.4,
                            material("wood", a=(196, 132, 60), b=(140, 86, 36), scale=0.7, along="y"))
                elif n == "t_door":
                    put("cube", fx, south - 0.5, band * 0.42, 8.6, 1.0, band * 0.84,
                        material("wood", a=(118, 76, 40), b=(72, 44, 22), scale=0.9, along="y"))
                    put("cube", fx, south - 0.9, band * 0.86, 10.4, 1.2, 1.4, wood)   # lintel
                    put("sphere", fx + 2.8, south - 1.2, band * 0.42, 0.7, 0.7, 0.7,
                        material("flat", rgb=(200, 170, 80), rough=0.3, metallic=0.9))

    # The roof: two slabs, then shingles laid on them course by course, each
    # course overlapping the one below and staggered by half a shingle. This
    # is the single loudest "modelled, not tiled" tell in the reference.
    half = d / 2.0 + EAVE
    pitch = math.radians(ROOF_PITCH)
    slab_len = half / math.cos(pitch)
    rise = half * math.tan(pitch)
    shade = material("flat", rgb=(70, 34, 34), rough=0.9)
    tile_a = material("flat", rgb=(176, 72, 64), rough=0.85)
    tile_b = material("flat", rgb=(132, 50, 48), rough=0.85)
    tile_c = material("flat", rgb=(202, 96, 82), rough=0.85)
    r = random.Random(int(cx * 3 + cy * 7))
    for sign_ in (-1, 1):
        put("cube", cx, cy + sign_ * half / 2.0, WALL_H + rise / 2.0,
            w + EAVE * 2, slab_len, 1.6, shade, rot=(sign_ * -ROOF_PITCH, 0, 0))
        # Shingles: walk up the slope from eave to ridge.
        course = 0
        v = 1.6
        while v < slab_len - 1.0:
            offset = (course % 2) * 4.8
            u = -(w + EAVE * 2) / 2.0 + 4.8 + offset
            while u < (w + EAVE * 2) / 2.0 - 1.0:
                # local (u along the eave, v up the slope) -> world
                yy = cy - sign_ * (half - v * math.cos(pitch))
                zz = WALL_H + v * math.sin(pitch) + 1.0
                put("cube", cx + u, yy, zz, 9.2, 5.6, 1.0, r.choice((tile_a, tile_b, tile_c)),
                    rot=(sign_ * -ROOF_PITCH, 0, 0))
                u += 9.6
            v += 5.2
            course += 1
    put("cube", cx, cy, WALL_H + rise + 1.2, w + EAVE * 2 + 1, 3.2, 1.4, shade)
    # A chimney on the north slope.
    put("cube", cx + w / 2.0 - 6.0, cy + 3.0, WALL_H + rise * 0.5 + 6.0, 4.0, 4.0, 12.0,
        material("stone", a=(120, 116, 124), b=(88, 84, 94), grout=(56, 52, 62), scale=0.08))


# ------------------------------------------------------------------ the map

PROPS = {
    "t_fence": fence, "t_lamp": lamp, "t_lantern": lamp, "t_lampsunk": lamp,
    "t_well": well, "t_tree": tree, "t_bush": bush, "t_rock": rock,
    "t_barrel": barrel, "t_chest": chest, "t_sign": sign,
}


def build_hd(map_id, rx, ry, rw, rh, facades):
    """The builder town.render() calls: the same region, modelled."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _CACHE.clear()
    _TEMPLATES.clear()
    maps = json.load(open(os.path.join(ROOT, "assets", "maps.json")))
    data = json.load(open(os.path.join(ROOT, "assets", "gamedata.json")))
    legend, underlay = data["legend"], data["underlay"]
    m = maps[map_id]
    ground_name = m.get("ground", "t_grass")

    PAD = 3
    rx, ry = max(0, rx - PAD), max(0, ry - PAD)
    rw, rh = rw + PAD * 2, rh + PAD * 2
    houses, taken = find_houses(m, legend, rx, ry, rw, rh)
    for x0, y0, x1, y1, names in houses:
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                ground(ground_name, tx, ty)
        house(x0, y0, x1, y1, names)

    _FENCE.clear()
    for ty in range(m["h"]):
        for tx in range(m["w"]):
            spec = legend.get(m["rows"][ty][tx])
            if spec and spec[0] == "t_fence":
                _FENCE.add((tx, ty))

    for ty in range(ry, min(ry + rh, m["h"])):
        row = m["rows"][ty]
        for tx in range(rx, min(rx + rw, m["w"])):
            if (tx, ty) in taken:
                continue
            spec = legend.get(row[tx])
            if spec is None:
                continue
            name = spec[0]
            under = underlay.get(row[tx])
            base = ground_name if under in (None, "ground") else under
            if name in PROPS:
                ground(base, tx, ty)
                if name == "t_tree" or name == "t_pinesnow":
                    tree(tx, ty, snow=(name == "t_pinesnow"))
                else:
                    PROPS[name](tx, ty)
            elif name == "t_pinesnow":
                ground(base, tx, ty)
                tree(tx, ty, snow=True)
            elif name == "t_mountain":
                mountain(tx, ty)
            elif name in ("t_wall", "t_palewall", "t_cryptwall", "t_drownwall",
                          "t_window", "t_palewindow", "t_door"):
                ground(base, tx, ty)
                wall_block(tx, ty, name)
            else:
                ground(name, tx, ty)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", default="town")
    ap.add_argument("--x", type=int, default=16)
    ap.add_argument("--y", type=int, default=12)
    ap.add_argument("--w", type=int, default=18)
    ap.add_argument("--h", type=int, default=14)
    ap.add_argument("--style", default="both", help="flat, reference, or both")
    ap.add_argument("--colours", type=int, default=40,
                    help="palette size for the game-resolution frame; 0 leaves it full colour")
    ap.add_argument("--samples", type=int, default=96)
    ap.add_argument("--full", action="store_true",
                    help="the whole map, modelled, written to art/prerender/<map>.png at "
                         "game size for the browser build to draw under its sprites")
    ap.add_argument("--out", default=os.path.join(ROOT, "art", "blender"))
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    if args.full:
        # Same contract as town.py --full: straight down, one game pixel per
        # pixel, every tile where the tilemap has it, no grade, so the game can
        # keep drawing sprites and collision from the map it already has.
        maps = json.load(open(os.path.join(ROOT, "assets", "maps.json")))
        m = maps[args.map]
        raw = os.path.join(args.out, "full_hd_%s.png" % args.map)
        town.render(args.map, 0, 0, m["w"], m["h"], "flat", raw, args.samples, builder=build_hd)
        game, small = town.finish(raw, town.STYLES["flat"], colours=args.colours)
        dest = os.path.join(ROOT, "art", "prerender", "%s.png" % args.map)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        assert (small.width, small.height) == (m["w"] * PPT, m["h"] * PPT), \
            "prerender is %dx%d, map is %dx%d" % (small.width, small.height,
                                                   m["w"] * PPT, m["h"] * PPT)
        with open(dest, "wb") as fh:
            fh.write(small.to_png())
        print("full     -> %s  %dx%d" % (os.path.relpath(dest, ROOT), small.width, small.height))
        return
    names = ["flat", "reference"] if args.style == "both" else [args.style]
    for name in names:
        raw = os.path.join(args.out, "hd_%s.png" % name)
        town.render(args.map, args.x, args.y, args.w, args.h, name, raw, args.samples,
                    builder=build_hd)
        game, small = town.finish(raw, town.STYLES[name], colours=args.colours)
        print("%-9s -> %s  %dx%d" % (name, os.path.relpath(game, ROOT), small.width, small.height))


if __name__ == "__main__":
    main()
