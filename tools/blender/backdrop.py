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
WIDTH, HEIGHT = 320, 116

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
    cam_data.lens = 42
    # shift_y is in sensor-WIDTH units; one unit moves the image 2.76 frame
    # heights here, so this drops the horizon to 65% down the frame.
    cam_data.shift_y = 0.0544
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
