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
        put("cyl", x, y, 5, 3.4, 3.4, 10, mat(name + "_trunk", rgb, shade=0.55))
        put("sphere", x, y, 19, 14, 14, 15, top)
        put("sphere", x - 3, y + 2, 25, 8, 8, 8, mat(name + "_hi", rgb, shade=1.16))
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
        put("cube", x, y, h - 2.5, 6, 6, 6, mat(name + "_lit", rgb, shade=1.35))
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

    if h <= 0:
        # Ground, and water a little below it.
        put("cube", x, y, h / 2.0 - 0.5, PPT, PPT, 1.0 + abs(h), top)
        return
    # One block, the tile's own art on every face. It used to be two: a body
    # and a thin cap for the top, and the cap sat exactly on the body's top
    # face. Two coincident surfaces trap Cycles' rays between them, and every
    # wall in the town came out solid black - not the material, not the light,
    # not the roof above it, all of which got blamed first.
    put("cube", x, y, h / 2.0, PPT, PPT, h, top)


def build(map_id, rx, ry, rw, rh):
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

    for ty in range(ry, min(ry + rh, m["h"])):
        row = m["rows"][ty]
        for tx in range(rx, min(rx + rw, m["w"])):
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
STYLES = {
    "flat":    {"pitch": 90.0, "yaw": 0.0,  "sun": 58.0, "fill": 0.30, "dof": 0.0,
                "note": "the angle it is drawn from now, with real light"},
    "quarter": {"pitch": 58.0, "yaw": 0.0,  "sun": 46.0, "fill": 0.28, "dof": 0.0,
                "note": "tilted far enough to see the sides of things"},
    "diorama": {"pitch": 46.0, "yaw": 12.0, "sun": 38.0, "fill": 0.24, "dof": 0.9,
                "note": "lower, softer, with the ends of the world out of focus"},
}


def light(style):
    world = bpy.data.worlds.new("sky")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = hex_rgb((150, 170, 220))
    bg.inputs["Strength"].default_value = style["fill"]

    sun_data = bpy.data.lights.new("sun", type="SUN")
    sun_data.energy = 4.6
    sun_data.color = hex_rgb((255, 244, 214))[:3]
    sun_data.angle = math.radians(2.5)      # a hard-ish shadow, not a blur
    sun = bpy.data.objects.new("sun", sun_data)
    bpy.context.collection.objects.link(sun)
    # Over the viewer's left shoulder, not from behind the houses. The first
    # pass had it coming from the far side of the map, which is correct for a
    # sunset and useless for a town: every face the camera could see was the
    # one in shadow, and the houses came out as black holes under red roofs.
    a = math.radians(style["sun"])
    d = Vector((math.cos(a) * 0.55, math.cos(a) * 0.72, -math.sin(a)))
    sun.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def render(map_id, rx, ry, rw, rh, style_name, out_path, samples):
    style = STYLES[style_name]
    build(map_id, rx, ry, rw, rh)
    light(style)
    scene = bpy.context.scene

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", default="town")
    ap.add_argument("--x", type=int, default=16)
    ap.add_argument("--y", type=int, default=12)
    ap.add_argument("--w", type=int, default=18)
    ap.add_argument("--h", type=int, default=14)
    ap.add_argument("--style", default="all",
                    help="flat, quarter, diorama, or all three")
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--out", default=os.path.join(ROOT, "art", "blender"))
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    names = list(STYLES) if args.style == "all" else [args.style]
    for name in names:
        path = os.path.join(args.out, "town_%s.png" % name)
        render(args.map, args.x, args.y, args.w, args.h, name, path, args.samples)
        print("%-8s -> %s  (%s)" % (name, path, STYLES[name]["note"]))


if __name__ == "__main__":
    main()
