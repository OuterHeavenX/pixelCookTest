"""24x32 overworld characters and their walk cycles.

Every human comes out of one parametric humanoid so the whole cast shares a
silhouette language, but each role varies build, posture, headwear and a
carried prop so the townsfolk are not one person in five palettes.

Rendering rules that do the heavy lifting:
  * three tones per material - light, base, shadow - lit from the top left
  * outlines are a darkened version of the material, not flat black, so the
    sprite reads as coloured rather than inked
  * frame 0 is a legs-together idle, 1 and 2 are opposite strides
"""

from .imaging import Image
from .palette import rgb

W, H = 24, 32
FEET = H - 1
INK = rgb("1d1626")


# --- colour helpers ---------------------------------------------------------

def darken(c, amount):
    return (max(0, int(c[0] * (1 - amount))), max(0, int(c[1] * (1 - amount))),
            max(0, int(c[2] * (1 - amount))), c[3])


def lighten(c, amount):
    return (min(255, int(c[0] + (255 - c[0]) * amount)),
            min(255, int(c[1] + (255 - c[1]) * amount)),
            min(255, int(c[2] + (255 - c[2]) * amount)), c[3])


def outline_of(c):
    """Coloured outline: a very dark version of the material itself."""
    return darken(c, 0.62)


def shaded(img, x, y, w, h, color, light=0.22, shade=0.24, edges="tlbr"):
    """A filled block lit from the top left, with a coloured outline."""
    img.rect(x, y, w, h, color)
    if "t" in edges and h > 1:
        img.rect(x, y, w, 1, lighten(color, light))
    if "l" in edges and w > 1:
        img.rect(x, y, 1, h, lighten(color, light * 0.7))
    if "b" in edges and h > 1:
        img.rect(x, y + h - 1, w, 1, darken(color, shade))
    if "r" in edges and w > 1:
        img.rect(x + w - 1, y, 1, h, darken(color, shade))


def ink_box(img, x, y, w, h, color, round_corners=0):
    """Shaded block wrapped in a coloured outline.

    `round_corners` chamfers that many pixels off each corner of the fill,
    which is the difference between a sprite reading as a person and reading
    as a stack of boxes.
    """
    edge = outline_of(color)
    img.rect(x - 1, y, w + 2, h, edge)
    img.rect(x, y - 1, w, h + 2, edge)
    shaded(img, x, y, w, h, color)
    for i in range(round_corners):
        run = round_corners - i
        img.rect(x, y + i, run, 1, edge)
        img.rect(x + w - run, y + i, run, 1, edge)
        img.rect(x, y + h - 1 - i, run, 1, edge)
        img.rect(x + w - run, y + h - 1 - i, run, 1, edge)


# --- style ------------------------------------------------------------------

def style(skin, skin_sh, hair, hair_dk, cloth, cloth_dk, trim,
          boot=None, cape=None, helm=False, hood=False, skirt=False,
          hat=False, weapon=None, weapon_dk=None, robe_trim=False,
          build=0, stoop=0, small=0, beard=None, prop=None, apron=None,
          hair_style="short"):
    """`build` widens the torso, `stoop` lowers the head, `small` shrinks the
    whole figure, and `prop` is what the character carries."""
    return dict(skin=skin, skin_sh=skin_sh, hair=hair, hair_dk=hair_dk,
                cloth=cloth, cloth_dk=cloth_dk, trim=trim,
                boot=boot or cloth_dk, cape=cape, helm=helm, hood=hood,
                skirt=skirt, hat=hat, weapon=weapon, weapon_dk=weapon_dk,
                robe_trim=robe_trim, build=build, stoop=stoop, small=small,
                beard=beard, prop=prop, apron=apron, hair_style=hair_style)


# --- body parts -------------------------------------------------------------

def _torso_box(st):
    half = 4 + st["build"]
    return 12 - half, half * 2


def _legs(img, st, frame, top):
    """frame: 0 legs together, 1 left forward, 2 right forward."""
    lift = (0, 0) if frame == 0 else ((2, 0) if frame == 1 else (0, 2))
    inner = 1 if st["build"] < 0 else 0
    for side, (x, dy) in enumerate(((10 - 2 + inner, lift[0]), (12 + inner, lift[1]))):
        leg_h = FEET - 2 - top - dy
        if leg_h > 0:
            ink_box(img, x, top + dy, 3, leg_h, st["cloth_dk"])
        ink_box(img, x, FEET - 2 - dy, 3, 3, st["boot"])


def _head(img, st, top, face=True, back=False):
    ink_box(img, 7, top, 10, 11, st["skin"], round_corners=2)
    img.rect(7, top + 9, 10, 2, st["skin_sh"])
    if back:
        return
    if face:
        eye = rgb("f8f8f2")
        for ex in (9, 13):
            img.rect(ex, top + 5, 3, 3, eye)
            img.rect(ex + 1, top + 6, 2, 2, INK)
            img.rect(ex, top + 4, 3, 1, darken(st["skin"], 0.35))
        img.rect(11, top + 8, 2, 1, st["skin_sh"])
        img.rect(10, top + 10, 4, 1, rgb("9c5346"))


def _hair(img, st, top, back=False):
    if st["hood"] or st["helm"] or st["hat"]:
        return
    h = st["hair"]
    style_name = st["hair_style"]
    depth = 11 if back else 5
    shaded(img, 7, top, 10, depth, h)
    edge = outline_of(h)
    for i in range(2):
        run = 2 - i
        img.rect(7, top + i, run, 1, edge)
        img.rect(17 - run, top + i, run, 1, edge)
    if back:
        for i in range(2):
            run = 2 - i
            img.rect(7, top + depth - 1 - i, run, 1, edge)
            img.rect(17 - run, top + depth - 1 - i, run, 1, edge)
    img.rect(8, top - 1, 8, 1, edge)
    img.rect(9, top, 6, 1, lighten(h, 0.32))
    if style_name == "long":
        shaded(img, 5, top + 2, 2, 12, h)
        shaded(img, 17, top + 2, 2, 12, h)
        img.rect(4, top + 2, 1, 12, outline_of(h))
        img.rect(19, top + 2, 1, 12, outline_of(h))
    elif style_name == "bald":
        img.rect(7, top, 10, depth, st["skin"])
        img.rect(7, top, 10, 2, lighten(st["skin"], 0.18))
        shaded(img, 5, top + 4, 2, 5, h)
        shaded(img, 17, top + 4, 2, 5, h)
    else:
        shaded(img, 6, top + 1, 1, 5, h)
        shaded(img, 17, top + 1, 1, 5, h)
    if back:
        img.rect(11, top + 1, 2, 9, darken(h, 0.3))
        img.rect(11, top + 1, 1, 9, lighten(h, 0.12))
        img.rect(6, top + 5, 1, 3, st["skin_sh"])   # ear hints
        img.rect(17, top + 5, 1, 3, st["skin_sh"])
        img.rect(10, top + 11, 4, 1, st["skin_sh"])  # neck
    if st["beard"] and not back:
        b = st["beard"]
        shaded(img, 8, top + 9, 8, 5, b)
        img.rect(7, top + 9, 1, 4, outline_of(b))
        img.rect(16, top + 9, 1, 4, outline_of(b))
        img.rect(10, top + 10, 4, 1, rgb("7a4038"))


def _headwear(img, st, top):
    if st["helm"]:
        m = st["trim"]
        ink_box(img, 6, top - 2, 12, 5, m)
        img.rect(7, top - 1, 10, 1, lighten(m, 0.5))
        img.rect(6, top + 3, 12, 1, darken(m, 0.35))
        # cheek guards, leaving the face open between them
        for gx in (6, 16):
            ink_box(img, gx, top + 3, 2, 6, m)
        img.rect(11, top - 6, 2, 5, rgb("d0454f"))
        img.rect(11, top - 6, 1, 5, rgb("f07078"))
    elif st["hood"]:
        c = st["cloth"]
        ink_box(img, 6, top - 2, 12, 8, c)
        img.rect(6, top + 6, 3, 8, c)
        img.rect(15, top + 6, 3, 8, c)
        img.rect(5, top + 6, 1, 8, outline_of(c))
        img.rect(18, top + 6, 1, 8, outline_of(c))
        img.rect(7, top - 1, 10, 1, lighten(c, 0.3))
        img.rect(6, top + 5, 12, 1, darken(c, 0.3))
    elif st["hat"]:
        c = st["cloth"]
        ink_box(img, 3, top + 1, 18, 2, c)
        ink_box(img, 8, top - 5, 8, 6, c)
        img.rect(8, top - 5, 8, 1, lighten(c, 0.35))
        img.rect(3, top + 1, 18, 1, lighten(c, 0.25))
        img.rect(8, top - 1, 8, 2, st["trim"])


def _torso(img, st, frame, top, side_view=False):
    x, w = _torso_box(st)
    if side_view:
        x, w = x + 1, w - 2
    h = max(6, (FEET - 7) - top)
    ink_box(img, x, top, w, h, st["cloth"], round_corners=1)
    img.rect(x, top + h - 2, w, 2, st["trim"])
    if st["apron"]:
        a = st["apron"]
        shaded(img, x + 2, top + 4, w - 4, h - 5, a)
        img.rect(x + 3, top + 3, w - 6, 1, a)
        img.rect(x + 2, top + 4, w - 4, 1, lighten(a, 0.3))
        img.rect(x + 2, top + h - 2, w - 4, 1, darken(a, 0.3))
    if st["robe_trim"]:
        img.rect(x + 2, top, 1, 2, st["trim"])
        img.rect(x + w - 3, top, 1, 2, st["trim"])
        img.rect(x + w // 2 - 1, top + 1, 2, 1, st["trim"])
    if st["skirt"]:
        ink_box(img, x - 1, top + h - 3, w + 2, 4, st["cloth"])
        img.rect(x - 1, top + h, w + 2, 1, darken(st["cloth"], 0.3))

    swing = 0 if frame == 0 else (1 if frame == 1 else -1)
    arm_w = 3
    for ax, s in ((x - arm_w - 1, swing), (x + w + 1, -swing)):
        ink_box(img, ax, top + 1 + s, arm_w, h - 3, st["cloth_dk"])
        ink_box(img, ax, top + h - 2 + s, arm_w, 2, st["skin"])


def _prop(img, st, top, side_view=False):
    """What the character carries - the cheapest way to tell roles apart."""
    p = st["prop"]
    if not p:
        return
    x, w = _torso_box(st)
    if p == "staff":
        sx = x + w + 3
        wood = st["weapon_dk"] or rgb("8a6a3a")
        img.rect(sx, top - 5, 2, FEET - top + 4, wood)
        img.rect(sx, top - 5, 1, FEET - top + 4, lighten(wood, 0.25))
        img.rect(sx - 1, top - 8, 4, 3, rgb("8fd8f0"))
        img.rect(sx, top - 9, 2, 1, rgb("d8f4ff"))
    elif p == "spear":
        sx = x + w + 3
        img.rect(sx, top - 6, 2, FEET - top + 5, rgb("7a5a34"))
        img.rect(sx, top - 6, 1, FEET - top + 5, rgb("9c7440"))
        img.rect(sx, top - 10, 2, 4, rgb("c8ccd8"))
        img.rect(sx, top - 12, 2, 2, rgb("e4e8f4"))
    elif p == "sword":
        h = max(6, (FEET - 7) - top)
        # Clear of the head's x-range, and no taller than the torso, so the
        # blade never crosses the face.
        sx = x + w + 1
        hand_y = top + h - 3
        blade = min(7, h - 1)
        img.rect(sx, hand_y - blade, 2, blade, rgb("c8ccd8"))
        img.rect(sx, hand_y - blade, 1, blade, rgb("e8ecf4"))
        img.rect(sx, hand_y - blade - 1, 2, 1, rgb("aeb4c4"))
        img.rect(sx - 1, hand_y, 4, 1, rgb("8a6a3a"))      # crossguard
        img.rect(sx, hand_y + 1, 2, 2, rgb("6b4423"))      # grip
    elif p == "basket":
        bx = x - 5
        ink_box(img, bx, top + 6, 5, 5, rgb("b98b4f"))
        img.rect(bx, top + 6, 5, 1, rgb("d8b070"))
        img.rect(bx + 1, top + 5, 3, 1, rgb("6fbf5a"))
    elif p == "pouch":
        img.rect(x + w - 2, top + 9, 4, 4, rgb("8a5a34"))
        img.rect(x + w - 2, top + 9, 4, 1, rgb("b07a48"))
        img.rect(x + w, top + 10, 1, 2, rgb("f0c04a"))


def _cape(img, st, top):
    c = st["cape"]
    x, w = _torso_box(st)
    shaded(img, x - 2, top - 1, w + 4, 12, c)
    img.rect(x - 3, top - 1, 1, 12, outline_of(c))
    img.rect(x + w + 2, top - 1, 1, 12, outline_of(c))
    img.rect(x - 2, top + 11, w + 4, 1, outline_of(c))
    img.rect(x - 1, top, 2, 10, lighten(c, 0.22))


# --- assembly ---------------------------------------------------------------

def _layout(st):
    head_top = 3 + st["stoop"]
    torso_top = head_top + 12
    legs_top = FEET - 7          # always seven pixels of leg and boot
    return head_top, torso_top, legs_top


def char_down(st, frame):
    img = Image(W, H)
    head_top, torso_top, legs_top = _layout(st)
    if st["cape"]:
        _cape(img, st, torso_top)
    _legs(img, st, frame, legs_top)
    _torso(img, st, frame, torso_top)
    _head(img, st, head_top)
    _hair(img, st, head_top)
    _headwear(img, st, head_top)
    _prop(img, st, torso_top)
    return img


def char_up(st, frame):
    img = Image(W, H)
    head_top, torso_top, legs_top = _layout(st)
    _legs(img, st, frame, legs_top)
    _torso(img, st, frame, torso_top)
    _head(img, st, head_top, face=False, back=True)
    _hair(img, st, head_top, back=True)
    _headwear(img, st, head_top)
    if st["cape"]:
        _cape(img, st, torso_top)
    _prop(img, st, torso_top)
    return img


def char_side(st, frame):
    """Faces right; the loader mirrors it for the left-facing set."""
    img = Image(W, H)
    head_top, torso_top, legs_top = _layout(st)
    if st["cape"]:
        c = st["cape"]
        shaded(img, 5, torso_top - 1, 5, 12, c)
        img.rect(4, torso_top - 1, 1, 12, outline_of(c))

    x, w = _torso_box(st)
    body_h = max(6, (FEET - 7) - torso_top)
    ink_box(img, x, torso_top, w, body_h, st["cloth"], round_corners=1)
    img.rect(x, torso_top + body_h - 2, w, 2, st["trim"])
    if st["skirt"]:
        ink_box(img, x - 1, torso_top + body_h - 3, w + 2, 4, st["cloth"])

    swing = 0 if frame == 0 else (2 if frame == 1 else -2)
    arm_x = x + w - 4
    ink_box(img, arm_x, torso_top + 1 + swing, 3, body_h - 4, st["cloth_dk"])
    ink_box(img, arm_x, torso_top + body_h - 3 + swing, 3, 2, st["skin"])

    step = 0 if frame == 0 else (2 if frame == 1 else -2)
    leg_h = max(1, FEET - 2 - legs_top)
    for lx, s in ((x + 1, step), (x + w - 4, -step)):
        ink_box(img, lx, legs_top, 3, leg_h, st["cloth_dk"])
        ink_box(img, lx + (1 if s > 0 else 0), FEET - 2, 3, 3, st["boot"])

    ink_box(img, 7, head_top, 10, 11, st["skin"], round_corners=2)
    img.rect(7, head_top + 9, 10, 2, st["skin_sh"])
    eye = rgb("f8f8f2")
    img.rect(13, head_top + 5, 3, 3, eye)
    img.rect(14, head_top + 6, 2, 2, INK)
    img.rect(16, head_top + 5, 1, 4, st["skin_sh"])
    img.rect(14, head_top + 10, 3, 1, rgb("9c5346"))
    if not (st["hood"] or st["helm"] or st["hat"]):
        h = st["hair"]
        shaded(img, 7, head_top, 9, 5, h)
        shaded(img, 6, head_top + 1, 2, 8, h)
        img.rect(6, head_top - 1, 11, 1, outline_of(h))
        if st["hair_style"] == "long":
            shaded(img, 5, head_top + 2, 3, 13, h)
        if st["beard"]:
            shaded(img, 10, head_top + 9, 7, 5, st["beard"])
    _headwear(img, st, head_top)
    _prop(img, st, torso_top, side_view=True)
    return img


def battle_pose(st, kind):
    if kind == "attack":
        img = char_side(st, 1)
        return img
    if kind == "hurt":
        src = char_side(st, 0)
        out = Image(W, H)
        for y in range(H):
            for x in range(W):
                c = src.get(x, y)
                if c[3]:
                    out.set(x, max(0, y - 1), c)
        return out
    return char_side(st, 0)


# --- cast -------------------------------------------------------------------

PARTY_STYLES = {
    "aldric": style(
        skin=rgb("f0c090"), skin_sh=rgb("cf9a68"),
        hair=rgb("e8c25a"), hair_dk=rgb("b08a2c"),
        cloth=rgb("4a78d0"), cloth_dk=rgb("2f4f9c"), trim=rgb("d8d8e4"),
        boot=rgb("6b4a2a"), cape=rgb("c04a58"), helm=True,
        weapon="sword", weapon_dk=rgb("8a6a3a"), prop="sword", build=1),
    "lyra": style(
        skin=rgb("f4cba4"), skin_sh=rgb("d3a37c"),
        hair=rgb("7a4bd0"), hair_dk=rgb("4e2c90"),
        cloth=rgb("6a3fb5"), cloth_dk=rgb("42256f"), trim=rgb("f0c04a"),
        boot=rgb("3a2452"), hat=True, skirt=True, hair_style="long",
        weapon="staff", weapon_dk=rgb("8a6a3a"), prop="staff"),
    "mira": style(
        skin=rgb("f6d3b0"), skin_sh=rgb("d4ac88"),
        hair=rgb("c85a3c"), hair_dk=rgb("8f3a25"),
        cloth=rgb("f0ece0"), cloth_dk=rgb("c8c0ae"), trim=rgb("c04a58"),
        boot=rgb("8a6a3a"), hood=True, skirt=True, robe_trim=True,
        weapon="staff", weapon_dk=rgb("a08050"), prop="staff"),
}

NPC_STYLES = {
    # A farmhand: plain tunic, carries a harvest basket.
    "villager": style(
        skin=rgb("efc49a"), skin_sh=rgb("cb9e74"),
        hair=rgb("6b4a2a"), hair_dk=rgb("47301b"),
        cloth=rgb("5aa050"), cloth_dk=rgb("3f7d3c"), trim=rgb("c8a06a"),
        boot=rgb("5a3c20"), prop="basket"),
    # Stooped, bald on top, long beard and a walking staff.
    "elder": style(
        skin=rgb("e8c0a0"), skin_sh=rgb("c49a7c"),
        hair=rgb("e0e0e0"), hair_dk=rgb("a8a8b0"),
        cloth=rgb("8a6ab0"), cloth_dk=rgb("5f478a"), trim=rgb("f0c04a"),
        boot=rgb("4a3a2a"), skirt=True, prop="staff", weapon_dk=rgb("6b4423"),
        beard=rgb("ececf0"), hair_style="bald", stoop=2, build=-1),
    # Broad, aproned, coin pouch on the belt.
    "merchant": style(
        skin=rgb("d8a878"), skin_sh=rgb("b4855a"),
        hair=rgb("2e2a30"), hair_dk=rgb("1a171d"),
        cloth=rgb("d08a3c"), cloth_dk=rgb("a05f22"), trim=rgb("f0c04a"),
        boot=rgb("5a3c20"), build=1, prop="pouch", apron=rgb("c8b48a"),
        beard=rgb("3a3238")),
    # Helmed, spear, broadest build in town.
    "guard": style(
        skin=rgb("e8b98c"), skin_sh=rgb("c4956a"),
        hair=rgb("4a3a2a"), hair_dk=rgb("2e241a"),
        cloth=rgb("8d8d98"), cloth_dk=rgb("5f5f6b"), trim=rgb("b8b8c0"),
        boot=rgb("3d3d47"), helm=True, build=1, prop="spear"),
    # Small, slight, no prop.
    "child": style(
        skin=rgb("f4cfa8"), skin_sh=rgb("d0a880"),
        hair=rgb("d8a03c"), hair_dk=rgb("a8741f"),
        cloth=rgb("e07a9c"), cloth_dk=rgb("b5527a"), trim=rgb("f4f4ec"),
        boot=rgb("6b4423"), skirt=True, small=3, build=-1),
}


def _shrink(img, rows):
    """Squash a sprite toward its feet so children read as younger.

    Sampling is nearest-neighbour over the full source height, so the whole
    figure survives the squash instead of losing its head or its legs.
    """
    out = Image(W, H)
    span = H - rows
    for y in range(span):
        src_y = min(H - 1, int(y * H / float(span)))
        for x in range(W):
            c = img.get(x, src_y)
            if c[3]:
                out.set(x, y + rows, c)
    return out


def cook():
    out = {}
    all_styles = {}
    all_styles.update(PARTY_STYLES)
    all_styles.update(NPC_STYLES)
    for name, st in all_styles.items():
        for frame in range(3):
            down = char_down(st, frame)
            up = char_up(st, frame)
            side = char_side(st, frame)
            if st["small"]:
                down, up, side = (_shrink(i, st["small"]) for i in (down, up, side))
            out["%s_down%d" % (name, frame)] = down
            out["%s_up%d" % (name, frame)] = up
            out["%s_right%d" % (name, frame)] = side
            out["%s_left%d" % (name, frame)] = side.flipped_x()
    for name, st in PARTY_STYLES.items():
        out["%s_ready" % name] = battle_pose(st, "ready").flipped_x()
        out["%s_attack" % name] = battle_pose(st, "attack").flipped_x()
        out["%s_hurt" % name] = battle_pose(st, "hurt").flipped_x()
    return out
