"""Render the battle backdrops in Blender.

Blender does the part that is genuinely hard to fake in 2D: silhouettes,
overlap and perspective across receding ridges. Every material is a flat
Emission, so the render comes back as graphic colour rather than photographic
shading, and the palette stays exactly what we choose. tools/pixelate.py then
quantises the result into the game's colours.

    python3 tools/blender/backdrop.py            # both moods
    python3 tools/blender/backdrop.py --mood dusk
"""

import argparse
import math
import os
import random
import sys

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Wide enough to cover the widest view the game will ever ask for. The screen
# is not a fixed 320 any more - a phone gets a 20:9 view - and a backdrop that
# stops at 320 would leave the ends of the world missing. The height stays
# where it was; a view taller than this extends the top row of sky, which is
# flat, so nothing shows.
WIDTH, HEIGHT = 512, 116

# The lens and the shift are both tied to the frame's aspect. Blender fits the
# sensor to the LONGER side, so widening the frame at a fixed focal length
# crops the top and bottom off instead of showing more of the sides: the lens
# has to open by the same factor the aspect changed. And shift_y is in sensor
# WIDTH units, so the shift that put the horizon 65% down the frame has to
# shrink by the same factor to keep it there.
_ASPECT = WIDTH / float(HEIGHT)
_LENS = 42.0 * (320.0 / 116.0) / _ASPECT
_SHIFT_Y = 0.0544 * (320.0 / 116.0) / _ASPECT

# Two moods: the ordinary encounter at dusk, and the boss shrine at night.
MOODS = {
    "dusk": {
        "sky_top": "1b2b4a", "sky_mid": "6a4a7a", "sky_low": "b5647c",
        "sky_glow": "e38a4a",
        "cloud_hi": "e8a06a", "cloud_lo": "8c5a78",
        "sun": "ffd9a0", "sun_y": 0.20,
        "ridges": ["2f3f63", "3c5f7c", "4a6f88", "5b7f94"],
        "trees": "1f3a3a", "trees_near": "27482f",
        "water": "3f6f96", "water_hi": "6fa8c8",
        "ground": ["3a6136", "45733e", "52894a", "5f9c54"],
        "castle": "26304f",
    },
    "night": {
        "sky_top": "140c22", "sky_mid": "34193e", "sky_low": "5c2a4e",
        "sky_glow": "8a3f5e",
        "cloud_hi": "6e3a5c", "cloud_lo": "2a1634",
        "sun": "d8c4e8", "sun_y": 0.16, "stars": 130,
        "ridges": ["1f1629", "2a1c34", "352440", "3f2c4c"],
        "trees": "120c1c", "trees_near": "1a1226",
        "water": "2b2040", "water_hi": "5a4372",
        "ground": ["31283f", "3a3049", "443a56", "4e4262"],
        "castle": "150e1f",
    },
}


# Two interiors, built the same way - flat emissive shapes, no lights - so
# they sit on the atlas beside the outdoor ones as the same kind of picture.
# A fight in the barrow happens in the barrow; the ridges and the sunset are
# four floors up.
MOODS["barrow"] = {
    "interior": True,
    "wall": "2c2740", "block_a": "3d3656", "block_b": "463f62", "mortar": "241f34",
    "arch": "0e0b16", "pillar": "352e4c", "pillar_hi": "4b4368",
    "floor": ["3a3450", "443d5c", "4e4768", "585174"], "flag": "2e2842",
    "brazier": "1d1a28", "flame": "ffb347", "flame_hi": "fff0b0", "glow": "4a3b52",
    "bones": "c9bfa8",
}
MOODS["mere"] = {
    "interior": True,
    "wall": "1a3440", "block_a": "244a58", "block_b": "2b5666", "mortar": "142830",
    "arch": "081218", "pillar": "1f404d", "pillar_hi": "2c5a6a",
    "floor": ["24485a", "2c5568", "356276", "3f6f84"], "flag": "1e3e4e",
    "water": "10283a", "water_hi": "2a5f7a",
    "brazier": "1a1c22", "flame": "ffd75a", "flame_hi": "fff6c8", "glow": "3a5a60",
}


def slab(name, x, y, z, sx, sy, sz, material):
    """An axis-aligned box: the interiors are made of nothing else."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(x, y, z))
    o = bpy.context.object
    o.name = name
    o.scale = (sx, sy, sz)
    o.data.materials.append(material)
    return o


def build_interior(mood_name):
    """A stone hall seen from the party's side of it: a wall of blocks at the
    back with a dark way through, pillars either side, a floor of flagstone
    bands that lighten toward the camera, and fire or lamplight because the
    lantern is the whole point of a fight down here."""
    m = MOODS[mood_name]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    world = bpy.data.worlds.new("dark")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = hex_rgb(m["wall"])
    bg.inputs["Strength"].default_value = 1.0

    # --- the back wall: mortar first, then the blocks over it -----------------
    wall_y = 40.0
    slab("mortar", 0, wall_y + 0.2, 8, 80, 0.2, 18, emission("mortar", m["mortar"]))
    block_a = emission("block_a", m["block_a"])
    block_b = emission("block_b", m["block_b"])
    rng = random.Random(3)
    z = 0.0
    row = 0
    while z < 16.0:
        h = 1.15
        x = -40.0 + (1.6 if row % 2 else 0.0)
        while x < 40.0:
            w = rng.uniform(2.4, 3.6)
            slab("block%d_%d" % (row, int(x * 10)), x + w / 2.0, wall_y, z + h / 2.0,
                 w - 0.25, 0.2, h - 0.2, block_a if rng.random() < 0.6 else block_b)
            x += w
        z += h
        row += 1
    # The way down, or through: a dark arch at the centre of the wall.
    slab("arch", 0, wall_y - 0.3, 3.4, 7.0, 0.3, 6.8, emission("arch", m["arch"]))
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=3.5, depth=0.3,
                                        location=(0, wall_y - 0.3, 6.8))
    top = bpy.context.object
    top.rotation_euler = (math.pi / 2, 0, 0)
    top.data.materials.append(emission("arch_top", m["arch"]))

    # --- pillars, with a lit edge -------------------------------------------
    pillar = emission("pillar", m["pillar"])
    pillar_hi = emission("pillar_hi", m["pillar_hi"])
    for px in (-16.0, 16.0):
        slab("pillar%d" % px, px, 30.0, 7.0, 3.0, 3.0, 14.0, pillar)
        slab("pillar_hi%d" % px, px + (0.9 if px < 0 else -0.9), 28.4, 7.0, 0.7, 0.2, 14.0, pillar_hi)
        slab("cap%d" % px, px, 30.0, 14.2, 3.8, 3.8, 0.6, pillar_hi)
        slab("foot%d" % px, px, 30.0, 0.3, 3.8, 3.8, 0.6, pillar_hi)

    # --- the floor: bands that lighten toward the camera, cut into flags -----
    bands_y = [26, 12, -2, -20]
    bands_d = [14, 14, 14, 18]
    flag = emission("flag", m["flag"])
    for i, color in enumerate(m["floor"]):
        y0, depth = bands_y[i], bands_d[i]
        slab("floor%d" % i, 0, y0 + depth / 2.0, -0.05 + i * 0.01, 120, depth, 0.1,
             emission("floor%d" % i, color))
        # Flag lines: across, then along, thinner and closer the further away.
        for k in range(3):
            y = y0 + depth * (k + 0.5) / 3.0
            slab("line%d_%d" % (i, k), 0, y, 0.02 + i * 0.01, 120, 0.18 + 0.04 * i, 0.06, flag)
        step = 6.0 + i * 1.5
        x = -60.0 + (step / 2.0 if i % 2 else 0.0)
        while x < 60.0:
            slab("col%d_%d" % (i, int(x)), x, y0 + depth / 2.0, 0.02 + i * 0.01, 0.16 + 0.04 * i, depth, 0.06, flag)
            x += step

    if m.get("water"):
        # The drowned hall: a pool across the back of the room, lamplight on it.
        slab("pool", 0, 24.0, 0.06, 120, 10.0, 0.1, emission("water", m["water"]))
        hi = emission("water_hi", m["water_hi"])
        for i, (wy, ww) in enumerate(((21.5, 26), (24.0, 18), (26.5, 34), (28.5, 12))):
            slab("ripple%d" % i, rng.uniform(-14, 14), wy, 0.12, ww, 0.35, 0.05, hi)

    # --- fire: braziers in the barrow, keepers' lamps in the mere -----------
    brazier = emission("brazier", m["brazier"])
    flame = emission("flame", m["flame"], 2.0)
    flame_hi = emission("flame_hi", m["flame_hi"], 2.6)
    glow = emission("glow", m["glow"])
    for fx in (-9.0, 9.0):
        y = 34.0
        if m.get("water"):
            slab("post%d" % fx, fx, y, 3.0, 0.9, 0.9, 6.0, brazier)
            slab("lamp%d" % fx, fx, y - 0.6, 6.6, 1.8, 1.0, 2.0, flame)
            slab("lamp_hi%d" % fx, fx, y - 1.2, 6.9, 0.8, 0.4, 0.8, flame_hi)
            slab("lamp_cap%d" % fx, fx, y, 7.9, 2.4, 2.4, 0.5, brazier)
        else:
            slab("stand%d" % fx, fx, y, 1.6, 0.8, 0.8, 3.2, brazier)
            slab("bowl%d" % fx, fx, y, 3.4, 3.0, 3.0, 1.0, brazier)
            slab("fire%d" % fx, fx, y - 0.4, 4.6, 2.0, 1.2, 1.6, flame)
            slab("fire_hi%d" % fx, fx + 0.3, y - 0.8, 5.4, 0.9, 0.6, 1.2, flame_hi)
            slab("fire_tip%d" % fx, fx - 0.4, y - 0.6, 5.9, 0.6, 0.4, 0.9, flame)
        # Painted light: a warm disc on the wall behind and a pool on the floor
        # below, because nothing here casts any. Only a step warmer than the
        # stone, or it reads as a box nailed to the wall.
        bpy.ops.mesh.primitive_circle_add(vertices=20, radius=4.2, fill_type='NGON',
                                          location=(fx, wall_y - 0.15, 6.2))
        wg = bpy.context.object
        wg.rotation_euler = (math.pi / 2, 0, 0)
        wg.scale = (1.0, 0.8, 1.0)
        wg.data.materials.append(glow)
        bpy.ops.mesh.primitive_circle_add(vertices=20, radius=4.0, fill_type='NGON',
                                          location=(fx, y - 3.0, 0.16))
        fg = bpy.context.object
        fg.scale = (1.0, 0.55, 1.0)
        fg.data.materials.append(glow)

    if m.get("bones"):
        bones = emission("bones", m["bones"])
        for i, (bx, by, bl) in enumerate(((-22, 18, 2.2), (-19.5, 17.2, 1.4), (24, 9, 2.6), (26, 10.4, 1.2))):
            slab("bone%d" % i, bx, by, 0.2, bl, 0.35, 0.3, bones)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=6, radius=0.7, location=(-24.5, 18.6, 0.6))
        bpy.context.object.data.materials.append(bones)

    return scene


def hex_rgb(h):
    h = h.lstrip("#")
    # Blender works in linear light; these are sRGB values from the palette.
    def to_linear(c):
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return tuple(to_linear(int(h[i:i + 2], 16)) for i in (0, 2, 4)) + (1.0,)


def emission(name, hex_color, strength=1.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = hex_rgb(hex_color)
    emit.inputs["Strength"].default_value = strength
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat


def add_mesh(name, verts, faces, material):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(material)
    bpy.context.collection.objects.link(obj)
    return obj


def ridge(name, depth, base_z, height, roughness, seed, material, span=900.0,
          steps=120):
    """A mountain range: a jagged skyline extruded down into a solid slab."""
    rng = random.Random(seed)
    # Two octaves of value noise give peaks with foothills rather than a comb.
    coarse = [rng.uniform(0.35, 1.0) for _ in range(9)]
    fine = [rng.uniform(0.0, 1.0) for _ in range(31)]

    def sample(t):
        def lerp_list(vals):
            p = t * (len(vals) - 1)
            i = int(p)
            f = p - i
            a = vals[min(i, len(vals) - 1)]
            b = vals[min(i + 1, len(vals) - 1)]
            f = f * f * (3 - 2 * f)          # smoothstep between control points
            return a + (b - a) * f
        return lerp_list(coarse) * 0.75 + lerp_list(fine) * 0.25 * roughness

    verts, faces = [], []
    for i in range(steps + 1):
        t = i / steps
        x = (t - 0.5) * span
        z = base_z + sample(t) * height
        verts.append((x, depth, z))
        verts.append((x, depth, base_z - 400.0))
    for i in range(steps):
        a = i * 2
        faces.append((a, a + 2, a + 3, a + 1))
    add_mesh(name, verts, faces, material)

    def height_at(x):
        """Skyline height at a world x, so a building can sit ON the ridge."""
        return base_z + sample(min(max(x / span + 0.5, 0.0), 1.0)) * height
    return height_at


def pine(x, y, z, height, radius, material, name):
    """A conifer as two stacked cones - enough silhouette at this scale."""
    bpy.ops.mesh.primitive_cone_add(vertices=7, radius1=radius, depth=height,
                                    location=(x, y, z + height / 2))
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    return obj


def cloud(x, z, width, thickness, depth, material, seed, name):
    """A cloud bank: overlapping squashed discs, so the edge stays lumpy."""
    rng = random.Random(seed)
    for i in range(5):
        t = (i / 4.0 - 0.5) * 2.0
        bpy.ops.mesh.primitive_circle_add(
            vertices=14, radius=1.0, fill_type='NGON',
            location=(x + t * width * 0.42, depth,
                      z + rng.uniform(-0.18, 0.18) * thickness))
        o = bpy.context.object
        o.name = "%s_%d" % (name, i)
        o.rotation_euler = (math.pi / 2, 0, 0)
        lobe = 1.0 - abs(t) * 0.45
        o.scale = (width * 0.34 * lobe, 1, thickness * 0.5 * lobe)
        o.data.materials.append(material)


def castle(x, y, z, scale, material):
    """Keep, curtain wall and spired towers, read as one silhouette."""
    parts = []
    def block(bx, bz, w, d, h):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x + bx * scale, y,
                                                          z + (bz + h / 2) * scale))
        o = bpy.context.object
        o.scale = (w * scale / 2, d * scale / 2, h * scale / 2)
        o.data.materials.append(material)
        parts.append(o)
    def spire(bx, bz, r, h):
        bpy.ops.mesh.primitive_cone_add(vertices=6, radius1=r * scale, depth=h * scale,
                                        location=(x + bx * scale, y,
                                                  z + (bz + h / 2) * scale))
        o = bpy.context.object
        o.data.materials.append(material)
        parts.append(o)
    block(0, 0, 14, 6, 10)            # curtain wall
    block(0, 8, 8, 6, 12)             # keep
    for tx in (-6, 6):
        block(tx, 0, 3.6, 5, 18)
        spire(tx, 18, 2.6, 7)
    block(-1.6, 20, 4.5, 5, 8)
    spire(-1.6, 27, 3.4, 9)
    return parts


def build(mood_name):
    m = MOODS[mood_name]
    if m.get("interior"):
        return build_interior(mood_name)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    # --- sky: a vertical gradient painted into the world shader -------------
    world = bpy.data.worlds.new("sky")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    tex = nt.nodes.new("ShaderNodeTexCoord")
    mapr = nt.nodes.new("ShaderNodeMapRange")
    # The ridges hide everything below about 4.5 degrees, so the ramp is
    # mapped over the strip of sky that actually survives them: any lower and
    # the sunset colours are painted behind the mountains where nobody sees.
    mapr.inputs["From Min"].default_value = 0.055
    mapr.inputs["From Max"].default_value = 0.205
    # Four stops: the sun's warm glow sits in the last few degrees above the
    # ridges, then rose, then purple, then the deep blue overhead.
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = hex_rgb(m["sky_glow"])
    ramp.color_ramp.elements[1].position = 1.0
    ramp.color_ramp.elements[1].color = hex_rgb(m["sky_top"])
    for pos, key in ((0.17, "sky_low"), (0.48, "sky_mid")):
        ramp.color_ramp.elements.new(pos).color = hex_rgb(m[key])
    nt.links.new(tex.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], mapr.inputs["Value"])
    nt.links.new(mapr.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

    # --- stars, for the night sky only ---------------------------------------
    if m.get("stars"):
        star_mat = emission("star", "e8e0ff", 1.6)
        rng = random.Random(77)
        for i in range(m["stars"]):
            bpy.ops.mesh.primitive_plane_add(
                # The frame is about 600 units wide at this depth, so the
                # scatter has to be that wide or the stars bunch up in the middle.
                size=rng.uniform(0.7, 1.5),
                location=(rng.uniform(-310, 310), 700,
                          rng.uniform(58, 165)))
            st = bpy.context.object
            st.name = "star%d" % i
            st.rotation_euler = (math.pi / 2, 0, 0)
            st.data.materials.append(star_mat)

    # --- sun sitting on the far ridges --------------------------------------
    sun_mat = emission("sun", m["sun"], 2.2)
    bpy.ops.mesh.primitive_circle_add(vertices=28, radius=10.0, fill_type='NGON',
                                      location=(-58, 430, 26))
    sun = bpy.context.object
    sun.rotation_euler = (math.pi / 2, 0, 0)
    sun.data.materials.append(sun_mat)

    # --- cloud banks, behind the ridges but in front of the sky --------------
    cloud_hi = emission("cloud_hi", m["cloud_hi"])
    cloud_lo = emission("cloud_lo", m["cloud_lo"])
    for i, (cx, cz, cw, ct, mat) in enumerate((
            (-120, 78, 190, 13, cloud_lo),
            (150, 96, 210, 15, cloud_lo),
            (-40, 52, 150, 9, cloud_hi),
            (190, 60, 130, 8, cloud_hi),
            (40, 118, 240, 17, cloud_lo),
            (-210, 116, 160, 12, cloud_hi))):
        cloud(cx, cz, cw, ct, 620, mat, 40 + i, "cloud%d" % i)

    # --- receding ridges: furthest and palest first --------------------------
    depths = [340, 235, 165, 118]
    heights = [40, 27, 17, 10]
    bases = [-1.0, -1.5, -2.0, -2.5]
    skyline = []
    for i, color in enumerate(m["ridges"]):
        skyline.append(ridge("ridge%d" % i, depths[i], bases[i], heights[i],
                             0.7 + i * 0.3, 11 + i * 7,
                             emission("ridge%d" % i, color),
                             span=900 - i * 150, steps=170))

    # A keep on the right-hand ridge, the way the reference frames it. Planted
    # at the skyline height so it stands on the range instead of floating.
    castle(68, depths[1] - 3, skyline[1](68) - 1.0, 0.58,
           emission("castle", m["castle"]))

    # --- lake -----------------------------------------------------------------
    water = emission("water", m["water"])
    bpy.ops.mesh.primitive_plane_add(size=1, location=(14, 84, 0.02))
    lake = bpy.context.object
    lake.scale = (60, 18, 1)
    lake.data.materials.append(water)
    hi = emission("water_hi", m["water_hi"])
    for i, (ly, lw) in enumerate(((77, 46), (81, 36), (86, 24), (91, 13))):
        bpy.ops.mesh.primitive_plane_add(size=1, location=(8 + i * 5, ly, 0.04))
        band = bpy.context.object
        band.scale = (lw, 0.55 + i * 0.25, 1)
        band.data.materials.append(hi)

    # --- treeline -------------------------------------------------------------
    far_trees = emission("trees", m["trees"])
    near_trees = emission("trees_near", m["trees_near"])
    rng = random.Random(5)
    for i in range(190):
        x = rng.uniform(-170, 170)
        y = rng.uniform(100, 122)
        pine(x, y, 0, rng.uniform(4.0, 6.2), rng.uniform(0.9, 1.5), far_trees,
             "pine_far%d" % i)
    for i in range(80):
        x = rng.uniform(-140, 140)
        y = rng.uniform(76, 96)
        if -14 < x < 54:
            continue                       # keep the lake mouth clear
        pine(x, y, 0, rng.uniform(3.6, 5.4), rng.uniform(0.8, 1.4), near_trees,
             "pine_near%d" % i)

    # --- ground: bands that get lighter toward the camera --------------------
    bands_y = [66, 44, 24, -14]
    bands_d = [40, 22, 20, 38]
    for i, color in enumerate(m["ground"]):
        y0, depth = bands_y[i], bands_d[i]
        bpy.ops.mesh.primitive_plane_add(size=1, location=(0, y0 + depth / 2, i * 0.01))
        g = bpy.context.object
        g.scale = (400, depth, 1)
        g.data.materials.append(emission("ground%d" % i, color))

    # Tufts and shadowed dips, so the meadow is not one flat slab of green.
    # They are close in value to the band they sit on - the party sprites
    # still have to read against this.
    shades = [emission("tuft%d" % i, c) for i, c in enumerate(m["ground"])]
    rng = random.Random(19)
    for i in range(220):
        y = rng.uniform(-12, 64)
        band = 0
        for b, (by, bd) in enumerate(zip(bands_y, bands_d)):
            if by <= y < by + bd:
                band = b
        near = (y + 12) / 76.0            # 0 at the treeline, 1 at the camera
        bpy.ops.mesh.primitive_circle_add(
            vertices=8, radius=1.0, fill_type='NGON',
            location=(rng.uniform(-90, 90), y, 0.05 + i * 1e-4))
        t = bpy.context.object
        t.name = "tuft%d" % i
        t.scale = (rng.uniform(0.9, 2.8) * (0.4 + near), rng.uniform(0.3, 0.8), 1)
        # One step darker or lighter than the band underneath.
        step = -1 if i % 3 else 1
        t.data.materials.append(shades[min(max(band + step, 0), len(shades) - 1)])

    return scene


def render(mood_name, out_path, samples=8):
    scene = build(mood_name)
    m = MOODS[mood_name]

    cam_data = bpy.data.cameras.new("cam")
    cam_data.lens = _LENS
    # shift_y is in sensor-WIDTH units; one unit moves the image 2.76 frame
    # heights here, so this drops the horizon to 65% down the frame.
    cam_data.shift_y = _SHIFT_Y
    cam = bpy.data.objects.new("cam", cam_data)
    bpy.context.collection.objects.link(cam)
    scene.camera = cam
    cam.location = (0, -16, 2.6)
    cam.rotation_euler = (math.pi / 2, 0, 0)

    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.filter_size = 0.30   # nearly no AA, so edges stay crisp
    scene.render.film_transparent = False
    scene.view_settings.view_transform = 'Standard'   # no filmic tone curve
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.filepath = out_path
    bpy.ops.render.render(write_still=True)
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mood", choices=sorted(MOODS) + ["all"], default="all")
    ap.add_argument("--out", default=os.path.join(ROOT, "art", "blender"))
    ap.add_argument("--samples", type=int, default=8)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    moods = sorted(MOODS) if args.mood == "all" else [args.mood]
    for mood in moods:
        path = os.path.join(args.out, "backdrop_%s.png" % mood)
        render(mood, path, args.samples)
        print("rendered %s -> %s" % (mood, path))


if __name__ == "__main__":
    main()
