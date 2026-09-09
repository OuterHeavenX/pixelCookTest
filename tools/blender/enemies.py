#!/usr/bin/env python3
"""Model and render the monsters in Blender.

The hand-plotted monsters were built out of rectangles and ellipses, which is
fine for a slime and thin for anything with a skeleton under it. Blender gives
them actual volume: a light that wraps around a shoulder, a snout that occludes
a cheek, a ribcage that reads as a cage rather than as five stripes.

Materials are plain diffuse - no specular, no roughness games - so the render
comes back as shape and shadow rather than as photography. Each monster is
rendered at eight times its sprite size with a transparent background;
tools/spritedown.py then area-averages it down, quantises it and puts the
outline back on, which is what makes it read on any backdrop.

    pip install bpy==4.5.13
    python3 tools/blender/enemies.py                 # all of them
    python3 tools/blender/enemies.py --only slime wolf
"""

import argparse
import json
import math
import os
import sys

import bpy
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "art", "enemies", "raw")

# Render at this multiple of the sprite size, then average down. Eight is
# enough that a diagonal edge lands on a believable intermediate colour.
SUPER = 8


def hex_rgb(h):
    h = h.lstrip("#")
    def to_linear(c):
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return tuple(to_linear(int(h[i:i + 2], 16)) for i in (0, 2, 4)) + (1.0,)


def mat(name, color, emit=0.0):
    """Diffuse, with an optional emissive lift for things that glow."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    if emit >= 1.0:
        sh = nt.nodes.new("ShaderNodeEmission")
        sh.inputs["Color"].default_value = hex_rgb(color)
        sh.inputs["Strength"].default_value = emit
        nt.links.new(sh.outputs["Emission"], out.inputs["Surface"])
        return m
    diff = nt.nodes.new("ShaderNodeBsdfDiffuse")
    diff.inputs["Color"].default_value = hex_rgb(color)
    if emit <= 0.0:
        nt.links.new(diff.outputs["BSDF"], out.inputs["Surface"])
        return m
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = hex_rgb(color)
    em.inputs["Strength"].default_value = emit
    add = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(diff.outputs["BSDF"], add.inputs[0])
    nt.links.new(em.outputs["Emission"], add.inputs[1])
    nt.links.new(add.outputs["Shader"], out.inputs["Surface"])
    return m


def _finish(obj, material, rot=None, smooth=True):
    obj.data.materials.append(material)
    if rot:
        obj.rotation_euler = tuple(math.radians(a) for a in rot)
    if smooth:
        for p in obj.data.polygons:
            p.use_smooth = True
    return obj


def ball(loc, scale, material, rot=None, segments=20):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=segments // 2,
                                         radius=1.0, location=loc)
    o = bpy.context.object
    o.scale = scale if isinstance(scale, (tuple, list)) else (scale,) * 3
    return _finish(o, material, rot)


def box(loc, scale, material, rot=None):
    bpy.ops.mesh.primitive_cube_add(size=2.0, location=loc)
    o = bpy.context.object
    o.scale = scale if isinstance(scale, (tuple, list)) else (scale,) * 3
    return _finish(o, material, rot, smooth=False)


def tube(loc, radius, height, material, rot=None, verts=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius,
                                        depth=height, location=loc)
    o = bpy.context.object
    return _finish(o, material, rot)


def cone(loc, radius, height, material, rot=None, verts=16, tip=0.0):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=radius, radius2=tip,
                                    depth=height, location=loc)
    o = bpy.context.object
    return _finish(o, material, rot)


def limb(a, b, radius, material, verts=12):
    """A capsule from a to b: the workhorse for arms, legs and tails."""
    a, b = Vector(a), Vector(b)
    d = b - a
    length = d.length
    mid = (a + b) / 2
    tube(tuple(mid), radius, length, material, verts=verts)
    o = bpy.context.object
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = d.to_track_quat('Z', 'Y')
    ball(tuple(a), radius, material, segments=12)
    ball(tuple(b), radius, material, segments=12)
    return o


def surface(center, radii, direction, out=1.0):
    """A point on an ellipsoid's surface, in the given direction.

    Eyes and horns have to sit ON the body, not inside it - the first pass
    placed them by eye and every one of them ended up buried."""
    d = Vector(direction).normalized()
    c, r = Vector(center), Vector(radii)
    return tuple(c + Vector((d.x * r.x, d.y * r.y, d.z * r.z)) * out)


def facing(yaw_deg, spread_deg=0.0, rise=0.0):
    """A direction out of the monster's face that the camera can actually see.

    Every monster is built facing +X with its left and right along +/-Y. The
    camera azimuth `yaw` is 0 when it sits at -Y - a profile, the monster
    facing screen-right - and 90 when it sits at +X, looking the monster in
    the face. So a feature on the face has to be aimed between +X, where the
    face points, and the camera: at yaw 0 a pure +X eye lands exactly on the
    silhouette edge and disappears."""
    a = math.radians(yaw_deg)
    cam = Vector((math.sin(a), -math.cos(a), 0.0))
    d = (Vector((1.0, 0.0, 0.0)) * 0.55 + cam * 0.75).normalized()
    b = math.radians(spread_deg)
    return (d.x * math.cos(b) - d.y * math.sin(b),
            d.x * math.sin(b) + d.y * math.cos(b), rise)


def eyes(center, radii, yaw_deg, spread_deg, size, material, rise=0.0, out=0.94):
    """A pair of eyes on a head, placed either side of the facing direction."""
    made = []
    for sign in (-1, 1):
        p = surface(center, radii, facing(yaw_deg, spread_deg * sign, rise), out)
        made.append(ball(p, size, material, segments=12))
    return made


# ------------------------------------------------------------------ monsters
# Each builds its model around the origin, standing on z=0, facing +X - which
# is the direction the party is in. `size` is the sprite it has to fit, `span`
# how many Blender units the camera should see across, and `yaw` how far round
# the camera sits: 0 is dead front, 90 is full profile.

def m_slime(P):
    body = mat("slime", "5ec8e8", emit=0.12)
    dark = mat("slime_lo", "2f7fa8")
    ball((0, 0, 0.62), (1.05, 0.95, 0.7), body)
    ball((0, 0, 0.20), (1.12, 1.0, 0.30), dark)          # the pooled base
    ball((0.15, -0.2, 1.0), (0.42, 0.30, 0.34), P["hi"])  # the shine on top
    eyes((0, 0, 0.62), (1.05, 0.95, 0.7), 76, 26, 0.26, P["white"], rise=0.16)
    eyes((0, 0, 0.62), (1.05, 0.95, 0.7), 76, 26, 0.17, P["ink"], rise=0.16, out=1.10)
    eyes((0, 0, 0.62), (1.05, 0.95, 0.7), 76, 30, 0.06, P["white"], rise=0.30, out=1.18)
    ball(surface((0, 0, 0.62), (1.05, 0.95, 0.7), facing(76, 0, -0.35), 1.02),
         (0.20, 0.06, 0.05), P["ink"])                     # a small flat mouth
    return dict(yaw=76, pitch=8)


def m_bat(P):
    fur = mat("bat_fur", "6a4a86")
    wing = mat("bat_wing", "8f5aa8")
    ball((0, 0, 0.96), (0.40, 0.34, 0.58), fur)           # a longer body
    ball((0.16, 0, 1.42), (0.34, 0.32, 0.32), fur)        # head
    for sy in (-1, 1):
        cone((0.02, 0.22 * sy, 1.82), 0.14, 0.52, fur)    # tall ears
        # The membrane: one swept panel per finger, each a little lower and
        # a little further back, so the wing reads as spread rather than as
        # a row of blocks.
        # Rounded panels, not boxes: the scalloped lower edge is most of what
        # makes a wing read as a wing.
        for i, (dy, dz, w) in enumerate(((0.44, 0.30, 0.44),
                                         (0.84, 0.42, 0.38),
                                         (1.16, 0.40, 0.27))):
            ball((-0.04 - i * 0.05, dy * sy, 1.02 + dz), (0.035, 0.23, w), wing)
            limb((0.05, 0.15 * sy, 1.20), (-0.05 - i * 0.06, (dy + 0.20) * sy,
                 1.02 + dz + w * 0.75), 0.045, fur)       # finger bones
    eyes((0.16, 0, 1.42), (0.34, 0.32, 0.32), 84, 26, 0.10, P["ember"], rise=0.12)
    ball(surface((0.16, 0, 1.42), (0.34, 0.32, 0.32), facing(84, 0, -0.55), 1.0),
         (0.10, 0.11, 0.05), P["white"])                   # a small fanged mouth
    return dict(yaw=84, pitch=6)


def m_wolf(P):
    fur = mat("wolf", "6f6a7a")
    fur_lo = mat("wolf_lo", "45414f")
    ruff = mat("wolf_ruff", "8b8698")
    ball((0, 0, 0.95), (0.85, 0.48, 0.46), fur)           # barrel
    ball((-0.55, 0, 0.98), (0.42, 0.44, 0.44), ruff)      # shoulder ruff
    ball((0.78, 0, 1.15), (0.36, 0.30, 0.30), fur)        # head
    cone((1.18, 0, 1.05), 0.19, 0.52, fur, rot=(0, 90, 0))  # snout
    for sy in (-1, 1):
        cone((0.72, 0.17 * sy, 1.48), 0.12, 0.34, fur)    # ears
        limb((0.45, 0.28 * sy, 0.75), (0.52, 0.30 * sy, 0.0), 0.12, fur_lo)
        limb((-0.55, 0.28 * sy, 0.75), (-0.62, 0.30 * sy, 0.0), 0.13, fur_lo)
        ball((1.02, 0.15 * sy, 1.22), (0.09, 0.09, 0.10), P["ember"])
    limb((-0.85, 0, 1.05), (-1.45, 0.10, 1.45), 0.11, fur)  # tail
    box((1.30, 0, 0.97), (0.12, 0.10, 0.05), P["white"], rot=(0, 0, 0))  # fang
    return dict(yaw=10, pitch=8)


def m_wisp(P):
    # Concentric shells only read if each one is smaller AND brighter than the
    # one outside it - the first pass had an opaque halo hiding everything.
    core = mat("wisp_core", "fbffd0", emit=9.0)
    glow = mat("wisp_glow", "a8f0d0", emit=3.4)
    halo = mat("wisp_halo", "4fae94", emit=1.1)
    dark = mat("wisp_eye", "10321f")
    ball((0, 0, 1.2), (0.62, 0.78, 0.78), halo)
    # A ragged rim, so it is a wisp and not a billiard ball.
    for i in range(9):
        a = i * (2 * math.pi / 9)
        ball((0.05, math.sin(a) * 0.80, 1.2 + math.cos(a) * 0.80),
             (0.10, 0.17, 0.17), halo, segments=10)
    ball((0.34, 0, 1.2), (0.38, 0.52, 0.52), glow)
    ball((0.62, 0, 1.2), (0.20, 0.26, 0.26), core)
    # Two dark slots in the core read as eyes at any size.
    for sy in (-1, 1):
        ball((0.80, 0.115 * sy, 1.27), (0.10, 0.045, 0.075), dark, segments=10)
    for i in range(4):                                     # motes coming off it
        a = i * (2 * math.pi / 4) + 0.6
        ball((0.2, math.sin(a) * 1.02, 1.2 + math.cos(a) * 1.02), 0.075, glow,
             segments=8)
    return dict(yaw=80, pitch=4)


def m_ogre(P):
    skin = mat("ogre", "7fa84f")
    skin_lo = mat("ogre_lo", "4f6f33")
    cloth = mat("ogre_cloth", "8a5a34")
    limb((-0.2, 0.42, 0.0), (-0.1, 0.42, 1.15), 0.30, skin_lo)   # legs
    limb((-0.2, -0.42, 0.0), (-0.1, -0.42, 1.15), 0.30, skin_lo)
    ball((0, 0, 1.75), (0.78, 0.95, 0.72), skin)                 # chest
    ball((0, 0, 1.28), (0.72, 0.86, 0.42), cloth)                # loincloth
    ball((0.18, 0, 2.02), (0.42, 0.55, 0.30), skin)              # pectorals
    ball((0, 0, 2.72), (0.56, 0.60, 0.56), skin)                 # head
    for sy in (-1, 1):
        # Arms hang outside the silhouette; the first pass crossed one over
        # the face and the ogre lost his head.
        limb((-0.1, 1.05 * sy, 2.25), (0.05, 1.35 * sy, 1.05), 0.26, skin)
        cone((-0.15, 0.62 * sy, 2.72), 0.14, 0.36, skin_lo, rot=(90 * sy, 0, 0))
        cone((-0.05, 0.30 * sy, 3.20), 0.11, 0.44, P["bone"], rot=(0, 16 * sy, 0))
        box(surface((0, 0, 2.72), (0.56, 0.60, 0.56), facing(78, 13 * sy, -0.42), 0.98),
            (0.06, 0.05, 0.09), P["white"])                       # tusks
    eyes((0, 0, 2.72), (0.56, 0.60, 0.56), 78, 22, 0.12, P["gold"], rise=0.18)
    ball(surface((0, 0, 2.72), (0.56, 0.60, 0.56), facing(78, 0, -0.5), 0.94),
         (0.13, 0.20, 0.06), mat("ogre_mouth", "3a1f1f"))
    # The club is carried behind the shoulder, out of the face.
    limb((-0.35, -1.45, 1.15), (-0.75, -1.70, 3.05), 0.16, cloth)
    ball((-0.85, -1.75, 3.30), (0.34, 0.34, 0.42), mat("club", "9c7440"))
    return dict(yaw=78, pitch=6)


def _humanoid(P, skin, cloth, boot, hair=None):
    """The shared body under the goblin and the bandit, seen in profile."""
    limb((-0.05, 0.18, 0.0), (0.0, 0.18, 0.88), 0.15, boot)      # longer legs
    limb((-0.05, -0.18, 0.0), (0.0, -0.18, 0.88), 0.15, boot)
    ball((0, 0, 1.26), (0.34, 0.42, 0.46), cloth)                # torso
    ball((0, 0, 0.94), (0.32, 0.38, 0.20), boot)                 # belt
    ball((0.02, 0, 1.68), (0.13, 0.16, 0.10), skin)              # neck
    ball((0.04, 0, 1.86), (0.28, 0.30, 0.30), skin)              # head, smaller
    if hair:
        ball((-0.05, 0, 1.98), (0.28, 0.31, 0.20), hair)
    return dict(skin=skin, cloth=cloth, boot=boot)


def m_goblin(P):
    skin = mat("gob", "8ab84f")
    skin_lo = mat("gob_lo", "5f8534")
    cloth = mat("gob_cloth", "9c6b3c")
    boot = mat("gob_boot", "4a3423")
    _humanoid(P, skin, cloth, boot, hair=mat("gob_hair", "33251a"))
    for sy in (-1, 1):                                            # swept-back ears
        cone((-0.26, 0.26 * sy, 1.98), 0.08, 0.50, skin_lo,
             rot=(0, -70, 40 * sy))
    ball(surface((0.04, 0, 1.86), (0.28, 0.30, 0.30), facing(62, 14, 0.12), 0.96),
         (0.10, 0.10, 0.11), P["gold"])                           # eye
    ball(surface((0.04, 0, 1.86), (0.28, 0.30, 0.30), facing(62, 14, 0.12), 1.08),
         (0.062, 0.062, 0.068), P["ink"])
    cone(surface((0.04, 0, 1.86), (0.28, 0.30, 0.30), facing(62, 0, -0.1), 0.98),
         0.085, 0.20, skin_lo, rot=(0, 90, 0))                    # nose
    limb((0.05, -0.36, 1.46), (0.34, -0.46, 1.02), 0.11, skin)    # sword arm, near side
    limb((0.34, -0.46, 1.02), (0.34, -0.48, 1.92), 0.055, P["steel"])
    box((0.34, -0.48, 1.06), (0.09, 0.13, 0.05), boot)            # crossguard
    return dict(yaw=62, pitch=6)


def m_bandit(P):
    skin = mat("ban", "d8a878")
    cloth = mat("ban_cloth", "7a6f92")
    boot = mat("ban_boot", "3a3348")
    sash = mat("ban_sash", "c04a58")
    _humanoid(P, skin, cloth, boot, hair=mat("ban_hair", "241f2a"))
    ball((0, 0, 1.48), (0.30, 0.40, 0.12), sash)                  # sash
    ball((0.05, 0, 1.72), (0.26, 0.29, 0.14), sash)               # face scarf
    ball(surface((0.04, 0, 1.86), (0.28, 0.30, 0.30), facing(62, 12, 0.30), 0.96),
         (0.08, 0.08, 0.09), P["white"])                          # eye over the scarf
    ball(surface((0.04, 0, 1.86), (0.28, 0.30, 0.30), facing(62, 12, 0.30), 1.06),
         (0.04, 0.04, 0.045), P["ink"])
    limb((0.05, -0.34, 1.44), (0.40, -0.42, 1.14), 0.11, skin)
    limb((0.40, -0.42, 1.14), (0.86, -0.44, 1.46), 0.05, P["steel"])  # dagger
    limb((-0.10, 0.34, 1.44), (-0.30, 0.40, 0.98), 0.11, cloth)
    return dict(yaw=62, pitch=6)


def m_skeleton(P):
    bone = mat("bone", "d2cba8")
    bone_lo = mat("bone_lo", "958e70")
    ball((0, 0, 2.10), (0.32, 0.30, 0.34), bone)                  # skull
    ball(surface((0, 0, 2.10), (0.32, 0.30, 0.34), facing(74, 0, -0.85), 0.95),
         (0.13, 0.16, 0.08), bone_lo)                             # jaw
    eyes((0, 0, 2.10), (0.32, 0.30, 0.34), 74, 26, 0.10, P["ink"], rise=0.16)
    eyes((0, 0, 2.10), (0.32, 0.30, 0.34), 74, 26, 0.05, P["ember"], rise=0.16, out=1.1)
    # A striped barrel, not a hole with bars over it. The first version put a
    # dark ball inside a wide-spaced cage and at 22 pixels the chest read as a
    # black rectangle; tight alternating rings keep the stripes and the mass.
    gap = mat("skel_gap", "3a3446")
    ball((0, 0, 1.82), (0.18, 0.30, 0.09), bone)                  # collarbone
    limb((0, 0, 1.82), (0, 0, 1.02), 0.075, bone_lo)              # spine
    for i in range(6):                                            # ribs
        z = 1.70 - i * 0.125
        r = 0.30 - i * 0.018
        bpy.ops.mesh.primitive_torus_add(location=(0, 0, z), major_radius=r,
                                         minor_radius=0.068,
                                         major_segments=16, minor_segments=6,
                                         rotation=(0, math.radians(90), 0))
        _finish(bpy.context.object, bone if i % 2 == 0 else gap)
    ball((0, 0, 0.98), (0.22, 0.28, 0.14), bone_lo)               # hips
    for sy in (-1, 1):
        limb((0, 0.24 * sy, 0.92), (0.02, 0.20 * sy, 0.0), 0.085, bone_lo)
        limb((0, 0.32 * sy, 1.74), (0.20, 0.40 * sy, 1.02), 0.075, bone_lo)
    # A duller, thinner blade: pure steel at 22 pixels came out as a white slab
    # brighter than the skeleton holding it.
    limb((0.22, 0.42, 1.02), (0.24, 0.44, 2.00), 0.035, mat("skel_blade", "8b90a4"))
    box((0.23, 0.43, 1.08), (0.07, 0.13, 0.045), mat("skel_grip", "6b4423"))
    return dict(yaw=74, pitch=6)


def m_wight(P):
    robe = mat("wight", "43395e")
    robe_lo = mat("wight_lo", "241d38")
    void = mat("wight_void", "0e0a18")
    glow = mat("wight_eye", "7fe8d8", emit=5.0)
    cone((0, 0, 0.95), 0.86, 1.9, robe)                           # the robe
    ball((0, 0, 0.10), (0.92, 0.92, 0.16), robe_lo)               # pooled hem
    ball((0, 0, 2.02), (0.52, 0.56, 0.56), robe)                  # hood
    ball(surface((0, 0, 2.02), (0.52, 0.56, 0.56), facing(78, 0, -0.1), 0.50),
         (0.34, 0.34, 0.40), void)                                # the dark in it
    eyes((0, 0, 2.02), (0.52, 0.56, 0.56), 78, 21, 0.10, glow, rise=0.02, out=0.98)
    for sy in (-1, 1):                                            # sleeves
        limb((0.05, 0.42 * sy, 1.72), (0.30, 0.60 * sy, 1.05), 0.17, robe)
    limb((0.30, 0.60, 1.05), (0.52, 0.66, 0.86), 0.09, P["bone"])  # a bone hand
    for i in range(4):                                            # cold coming off it
        ball((0.1 + i * 0.05, (i - 1.5) * 0.42, 2.9 + (i % 2) * 0.3),
             0.055, glow, segments=8)
    return dict(yaw=78, pitch=6)


MONSTERS = {
    "e_slime": (m_slime, (24, 20)),
    "e_bat": (m_bat, (28, 20)),
    "e_wolf": (m_wolf, (30, 22)),
    "e_wisp": (m_wisp, (24, 24)),
    "e_ogre": (m_ogre, (32, 40)),
    "e_goblin": (m_goblin, (24, 32)),
    "e_bandit": (m_bandit, (24, 32)),
    "e_skeleton": (m_skeleton, (22, 30)),
    "e_wight": (m_wight, (26, 32)),
}


def _shared_palette():
    """Colours several monsters reach for, made once per scene."""
    return {
        "white": mat("p_white", "f4f4ec"),
        "ink": mat("p_ink", "1a1622"),
        "gold": mat("p_gold", "f2d15a"),
        "ember": mat("p_ember", "ff6a4a", emit=1.4),
        "bone": mat("p_bone", "e8e0c8"),
        "steel": mat("p_steel", "c8ccd8"),
        "hi": mat("p_hi", "ffffff", emit=0.5),
    }


def setup_lights():
    """Three lights and an ambient sky. A key from the front left so the lit
    side faces the camera, a cool fill opposite it so the shadow side never
    goes to black, and a rim from behind to lift the silhouette.

    The ambient matters more than it looks: with lights alone the shadow side
    of every monster crushed to near-black, and quantising that gave a sprite
    that was half silhouette."""
    world = bpy.data.worlds.new("ambient")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = hex_rgb("8fa8d8")
    bg.inputs["Strength"].default_value = 0.55

    for name, loc, energy, color, size in (
            ("key", (-3.5, -6.0, 6.5), 3200.0, "fff4e0", 7.0),
            ("fill", (5.5, -4.0, 2.0), 1100.0, "a8c8ff", 9.0),
            ("rim", (1.0, 6.5, 5.0), 1700.0, "ffd2a0", 6.0)):
        data = bpy.data.lights.new(name, 'AREA')
        data.energy = energy
        data.size = size
        data.color = hex_rgb(color)[:3]
        obj = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(obj)
        obj.location = loc
        obj.rotation_euler = (Vector((0, 0, 1.2)) - Vector(loc)).to_track_quat(
            '-Z', 'Y').to_euler()


def render(name, samples):
    build, (w, h) = MONSTERS[name]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    spec = build(_shared_palette())
    setup_lights()

    # Orthographic, or a 24-pixel monster gets perspective distortion across
    # its own body and stops reading as a flat game sprite.
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = 'ORTHO'
    cam = bpy.data.objects.new("cam", cam_data)
    bpy.context.collection.objects.link(cam)
    scene.camera = cam
    yaw = math.radians(spec["yaw"])
    pitch = math.radians(spec["pitch"])
    view = Vector((math.sin(yaw) * math.cos(pitch),
                   -math.cos(yaw) * math.cos(pitch),
                   math.sin(pitch)))
    cam.location = view * 12.0
    cam.rotation_euler = (-view).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.view_layer.update()

    # Frame the monster by measuring it rather than by guessing a span: every
    # sprite should fill its own box, and hand-tuned numbers had half of them
    # rattling around inside theirs.
    right = cam.matrix_world.to_quaternion() @ Vector((1, 0, 0))
    up = cam.matrix_world.to_quaternion() @ Vector((0, 1, 0))
    xs, ys, centre = [], [], Vector((0, 0, 0))
    for obj in scene.objects:
        if obj.type != 'MESH':
            continue
        for corner in obj.bound_box:
            p = obj.matrix_world @ Vector(corner)
            xs.append(p.dot(right))
            ys.append(p.dot(up))
    if not xs:
        raise SystemExit("%s built no geometry" % name)
    pad = 1.06
    span = max((max(xs) - min(xs)) * pad, (max(ys) - min(ys)) * pad * w / float(h))
    cam_data.ortho_scale = span
    # Re-aim so the measured box is centred in frame.
    centre = right * ((max(xs) + min(xs)) / 2) + up * ((max(ys) + min(ys)) / 2)
    cam.location = view * 12.0 + centre

    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False
    scene.render.resolution_x = w * SUPER
    scene.render.resolution_y = h * SUPER
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.view_settings.view_transform = 'Standard'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    path = os.path.join(OUT, name + ".png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path, (w, h)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--samples", type=int, default=48)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    names = args.only or sorted(MONSTERS)
    names = ["e_" + n if not n.startswith("e_") else n for n in names]
    sizes = {}
    manifest_path = os.path.join(OUT, "MANIFEST.json")
    if os.path.exists(manifest_path):
        sizes = json.load(open(manifest_path))
    for name in names:
        if name not in MONSTERS:
            raise SystemExit("no such monster: %s" % name)
        path, size = render(name, args.samples)
        sizes[name] = list(size)
        print("rendered %-12s -> %s  (%dx%d target)" % (name, path, size[0], size[1]))
    with open(manifest_path, "w") as fh:
        json.dump(sizes, fh, indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
