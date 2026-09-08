"""16x24 overworld characters and their 3-frame walk cycles.

Every human in the game comes out of one parametric humanoid so the party,
the townsfolk and the guards share a silhouette. A "style" dict supplies the
colours and a few shape flags (helm, hood, cape, skirt, staff, sword).
"""

from .imaging import Image
from .palette import rgb

INK = rgb("201826")

W, H = 16, 24


def _ink_rect(img, x, y, w, h, fill, ink=INK):
    """Filled rect with a 1px outline hugging all four sides."""
    img.rect(x - 1, y, w + 2, h, ink)
    img.rect(x, y - 1, w, h + 2, ink)
    img.rect(x, y, w, h, fill)


def _darken(c, amount):
    return (int(c[0] * (1 - amount)), int(c[1] * (1 - amount)),
            int(c[2] * (1 - amount)), c[3])


def _lighten(c, amount):
    return (min(255, int(c[0] + (255 - c[0]) * amount)),
            min(255, int(c[1] + (255 - c[1]) * amount)),
            min(255, int(c[2] + (255 - c[2]) * amount)), c[3])


def style(skin, skin_sh, hair, hair_dk, cloth, cloth_dk, trim,
          boot=None, cape=None, helm=False, hood=False, skirt=False,
          hat=False, weapon=None, weapon_dk=None, robe_trim=False):
    return dict(skin=skin, skin_sh=skin_sh, hair=hair, hair_dk=hair_dk,
                cloth=cloth, cloth_dk=cloth_dk, trim=trim,
                boot=boot or cloth_dk, cape=cape, helm=helm, hood=hood,
                skirt=skirt, hat=hat, weapon=weapon, weapon_dk=weapon_dk,
                robe_trim=robe_trim)


def _legs(img, st, frame, back=False):
    """frame: 0 idle, 1 left forward, 2 right forward."""
    lift_l, lift_r = 0, 0
    if frame == 1:
        lift_l, lift_r = 1, 0
    elif frame == 2:
        lift_l, lift_r = 0, 1
    for x, lift in ((5, lift_l), (9, lift_r)):
        img.rect(x, 19, 2, 3 - lift, st["cloth_dk"])
        img.rect(x, 22 - lift, 2, 2, st["boot"])
        img.rect(x - 1, 19, 1, 5 - lift, INK)
        img.rect(x + 2, 19, 1, 5 - lift, INK)
        img.rect(x, 24 - lift, 2, 1, INK)


def _head_base(img, st):
    _ink_rect(img, 4, 3, 8, 10, st["skin"])
    img.rect(4, 12, 8, 1, st["skin_sh"])


def _hair_down(img, st):
    img.rect(4, 3, 8, 4, st["hair"])
    img.rect(4, 3, 8, 1, st["hair_dk"])
    img.rect(4, 7, 1, 3, st["hair"])
    img.rect(11, 7, 1, 3, st["hair"])
    img.rect(4, 7, 1, 3, st["hair_dk"])


def _helm(img, st):
    img.rect(3, 2, 10, 5, st["trim"])
    img.rect(4, 6, 8, 1, rgb("9a9aa6"))
    img.rect(3, 2, 10, 1, INK)
    img.rect(4, 3, 8, 1, rgb("e8ecf4"))
    img.rect(7, 0, 2, 3, rgb("e05a5a"))  # plume
    img.rect(3, 7, 1, 4, st["trim"])
    img.rect(12, 7, 1, 4, st["trim"])


def _hood(img, st):
    """Cowl that frames the face instead of hiding it."""
    img.rect(3, 1, 10, 6, st["cloth"])
    img.rect(3, 1, 10, 1, st["cloth_dk"])
    img.rect(3, 7, 2, 6, st["cloth"])
    img.rect(11, 7, 2, 6, st["cloth"])
    img.rect(4, 6, 8, 1, st["cloth_dk"])
    img.rect(2, 1, 1, 12, INK)
    img.rect(13, 1, 1, 12, INK)
    img.rect(3, 0, 10, 1, INK)


def _hat(img, st):
    img.rect(2, 4, 12, 1, st["cloth_dk"])
    img.rect(1, 5, 14, 1, INK)
    img.rect(4, 1, 8, 3, st["cloth"])
    img.rect(5, 0, 6, 1, st["cloth_dk"])
    img.rect(4, 0, 1, 4, INK)
    img.rect(11, 0, 1, 4, INK)
    img.rect(4, 3, 8, 1, st["trim"])


def _torso(img, st, frame, arms_offset=0):
    _ink_rect(img, 5, 14, 6, 5, st["cloth"])
    img.rect(5, 18, 6, 1, st["trim"])
    if st["robe_trim"]:
        img.rect(6, 14, 1, 1, st["trim"])
        img.rect(9, 14, 1, 1, st["trim"])
        img.rect(7, 15, 2, 1, st["trim"])
    if st["skirt"]:
        img.rect(4, 18, 8, 2, st["cloth"])
        img.rect(3, 19, 1, 1, INK)
        img.rect(12, 19, 1, 1, INK)
        img.rect(4, 20, 8, 1, st["cloth_dk"])
    swing = 0 if frame == 0 else (1 if frame == 1 else -1)
    for x, s in ((3, swing), (11, -swing)):
        img.rect(x, 14 + s, 2, 4, st["cloth_dk"])
        img.rect(x, 18 + s, 2, 1, st["skin"])
        img.rect(x - 1, 14 + s, 1, 5, INK)
        img.rect(x + 2, 14 + s, 1, 5, INK)
        img.rect(x, 13 + s, 2, 1, INK)
        img.rect(x, 19 + s, 2, 1, INK)


def _cape(img, st):
    """Cloak seen from behind: tapered, with a shaded hem."""
    img.rect(3, 13, 10, 6, st["cape"])
    img.rect(4, 19, 8, 2, st["cape"])
    img.rect(4, 20, 8, 1, _darken(st["cape"], 0.6))
    img.rect(3, 13, 10, 1, _darken(st["cape"], 0.45))
    img.rect(5, 14, 2, 5, _lighten(st["cape"], 0.25))
    img.rect(2, 13, 1, 6, INK)
    img.rect(13, 13, 1, 6, INK)
    img.rect(3, 19, 1, 2, INK)
    img.rect(12, 19, 1, 2, INK)
    img.rect(4, 21, 8, 1, INK)


def face_down(img, st):
    eye = rgb("f6f6f0")
    for x in (5, 9):
        img.rect(x, 8, 2, 2, eye)
        img.rect(x + 1, 8, 1, 2, INK)
    img.rect(4, 10, 1, 1, st["skin_sh"])
    img.rect(11, 10, 1, 1, st["skin_sh"])
    img.rect(7, 11, 2, 1, rgb("a8604c"))


def face_side(img, st):
    img.rect(8, 8, 2, 2, rgb("f6f6f0"))
    img.rect(9, 8, 1, 2, INK)
    img.rect(11, 8, 1, 3, st["skin_sh"])
    img.rect(10, 11, 2, 1, rgb("a8604c"))


def char_down(st, frame):
    img = Image(W, H)
    if st["cape"]:
        _cape(img, st)
    _torso(img, st, frame)
    _legs(img, st, frame)
    _head_base(img, st)
    if st["hood"]:
        _hood(img, st)
    else:
        _hair_down(img, st)
        if st["helm"]:
            _helm(img, st)
        if st["hat"]:
            _hat(img, st)
    face_down(img, st)
    _weapon_down(img, st)
    return img


def char_up(st, frame):
    img = Image(W, H)
    _torso(img, st, frame)
    _legs(img, st, frame)
    _head_base(img, st)
    if st["hood"]:
        _hood(img, st)
    else:
        img.rect(4, 3, 8, 9, st["hair"])
        img.rect(4, 3, 8, 2, st["hair_dk"])
        img.rect(4, 11, 8, 1, st["hair_dk"])
        if st["helm"]:
            _helm(img, st)
            img.rect(4, 7, 8, 5, st["hair"])
        if st["hat"]:
            _hat(img, st)
    if st["cape"]:
        _cape(img, st)
    _weapon_up(img, st)
    return img


def char_side(st, frame):
    """Faces right; the loader mirrors it for the left-facing set."""
    img = Image(W, H)
    if st["cape"]:
        img.rect(3, 13, 4, 8, st["cape"])
        img.rect(2, 13, 1, 8, INK)
        img.rect(3, 12, 4, 1, INK)
        img.rect(3, 21, 4, 1, INK)
    _ink_rect(img, 5, 14, 5, 5, st["cloth"])
    img.rect(5, 18, 5, 1, st["trim"])
    if st["skirt"]:
        img.rect(4, 18, 7, 2, st["cloth"])
        img.rect(4, 20, 7, 1, st["cloth_dk"])
    swing = 0 if frame == 0 else (2 if frame == 1 else -2)
    img.rect(8, 14 + swing, 3, 4, st["cloth_dk"])
    img.rect(8, 18 + swing, 3, 1, st["skin"])
    img.rect(8, 13 + swing, 3, 1, INK)
    img.rect(11, 14 + swing, 1, 5, INK)
    img.rect(8, 19 + swing, 3, 1, INK)
    # legs, striding
    step = 0 if frame == 0 else (2 if frame == 1 else -2)
    for x, s in ((5, step), (8, -step)):
        img.rect(x, 19, 3, 3, st["cloth_dk"])
        img.rect(x + (1 if s > 0 else 0), 22, 3, 2, st["boot"])
        img.rect(x - 1, 19, 1, 5, INK)
        img.rect(x + 3, 19, 1, 5, INK)
        img.rect(x, 24, 3, 1, INK)
    _ink_rect(img, 4, 3, 8, 10, st["skin"])
    img.rect(4, 12, 8, 1, st["skin_sh"])
    if st["hood"]:
        _hood(img, st)
    else:
        img.rect(4, 3, 8, 4, st["hair"])
        img.rect(4, 3, 8, 1, st["hair_dk"])
        img.rect(4, 7, 2, 5, st["hair"])
        img.rect(4, 7, 1, 5, st["hair_dk"])
        if st["helm"]:
            _helm(img, st)
        if st["hat"]:
            _hat(img, st)
    face_side(img, st)
    _weapon_side(img, st)
    return img


def _weapon_down(img, st):
    if not st["weapon"]:
        return
    if st["weapon"] == "sword":
        img.rect(12, 14, 1, 6, st["weapon_dk"])
        img.rect(13, 14, 1, 6, INK)
    elif st["weapon"] == "staff":
        img.rect(2, 11, 1, 10, st["weapon_dk"])
        img.rect(1, 9, 3, 2, rgb("8fd8f0"))
        img.rect(2, 8, 1, 1, rgb("d8f4ff"))


def _weapon_up(img, st):
    _weapon_down(img, st)


def _weapon_side(img, st):
    if not st["weapon"]:
        return
    if st["weapon"] == "sword":
        img.rect(11, 12, 1, 8, rgb("c8ccd8"))
        img.rect(12, 12, 1, 8, INK)
        img.rect(10, 18, 3, 1, st["weapon_dk"])
    elif st["weapon"] == "staff":
        img.rect(11, 10, 1, 11, st["weapon_dk"])
        img.rect(10, 8, 3, 2, rgb("8fd8f0"))
        img.rect(11, 7, 1, 1, rgb("d8f4ff"))


def battle_pose(st, kind):
    """Larger-read side poses used in battle: ready / attack / hurt."""
    img = char_side(st, 0)
    if kind == "attack":
        img = Image(W, H)
        _ink_rect(img, 5, 14, 5, 5, st["cloth"])
        img.rect(5, 18, 5, 1, st["trim"])
        img.rect(9, 11, 3, 4, st["cloth_dk"])
        img.rect(9, 14, 3, 1, st["skin"])
        img.rect(8, 11, 1, 5, INK)
        img.rect(12, 11, 1, 5, INK)
        for x in (5, 8):
            img.rect(x, 19, 3, 3, st["cloth_dk"])
            img.rect(x, 22, 3, 2, st["boot"])
            img.rect(x - 1, 19, 1, 5, INK)
            img.rect(x + 3, 19, 1, 5, INK)
        _ink_rect(img, 4, 3, 8, 10, st["skin"])
        img.rect(4, 12, 8, 1, st["skin_sh"])
        if st["hood"]:
            _hood(img, st)
        else:
            img.rect(4, 3, 8, 4, st["hair"])
            img.rect(4, 3, 8, 1, st["hair_dk"])
            img.rect(4, 7, 2, 5, st["hair"])
            if st["helm"]:
                _helm(img, st)
            if st["hat"]:
                _hat(img, st)
        face_side(img, st)
        if st["weapon"] == "sword":
            img.rect(12, 2, 1, 12, rgb("e4e8f4"))
            img.rect(13, 2, 1, 12, INK)
            img.rect(11, 13, 4, 1, st["weapon_dk"])
        elif st["weapon"] == "staff":
            img.rect(12, 4, 1, 11, st["weapon_dk"])
            img.rect(11, 2, 3, 2, rgb("bfe8ff"))
            img.rect(12, 1, 1, 1, rgb("ffffff"))
    elif kind == "hurt":
        out = Image(W, H)
        for y in range(H):
            for x in range(W):
                c = img.get(x, y)
                if c[3]:
                    out.set(x, y - 1 if y > 0 else 0, c)
        img = out
    return img


PARTY_STYLES = {
    "aldric": style(
        skin=rgb("f0c090"), skin_sh=rgb("cf9a68"),
        hair=rgb("e8c25a"), hair_dk=rgb("b08a2c"),
        cloth=rgb("4a78d0"), cloth_dk=rgb("2f4f9c"), trim=rgb("d8d8e4"),
        boot=rgb("6b4a2a"), cape=rgb("c04a58"), helm=True,
        weapon="sword", weapon_dk=rgb("8a6a3a")),
    "lyra": style(
        skin=rgb("f4cba4"), skin_sh=rgb("d3a37c"),
        hair=rgb("7a4bd0"), hair_dk=rgb("4e2c90"),
        cloth=rgb("6a3fb5"), cloth_dk=rgb("42256f"), trim=rgb("f0c04a"),
        boot=rgb("3a2452"), hat=True, skirt=True,
        weapon="staff", weapon_dk=rgb("8a6a3a")),
    "mira": style(
        skin=rgb("f6d3b0"), skin_sh=rgb("d4ac88"),
        hair=rgb("c85a3c"), hair_dk=rgb("8f3a25"),
        cloth=rgb("f0ece0"), cloth_dk=rgb("c8c0ae"), trim=rgb("c04a58"),
        boot=rgb("8a6a3a"), hood=True, skirt=True, robe_trim=True,
        weapon="staff", weapon_dk=rgb("a08050")),
}

NPC_STYLES = {
    "villager": style(
        skin=rgb("efc49a"), skin_sh=rgb("cb9e74"),
        hair=rgb("6b4a2a"), hair_dk=rgb("47301b"),
        cloth=rgb("5aa050"), cloth_dk=rgb("3f7d3c"), trim=rgb("c8a06a"),
        boot=rgb("5a3c20")),
    "elder": style(
        skin=rgb("e8c0a0"), skin_sh=rgb("c49a7c"),
        hair=rgb("e0e0e0"), hair_dk=rgb("a8a8b0"),
        cloth=rgb("8a6ab0"), cloth_dk=rgb("5f478a"), trim=rgb("f0c04a"),
        boot=rgb("4a3a2a"), skirt=True, weapon="staff", weapon_dk=rgb("6b4423")),
    "merchant": style(
        skin=rgb("d8a878"), skin_sh=rgb("b4855a"),
        hair=rgb("2e2a30"), hair_dk=rgb("1a171d"),
        cloth=rgb("d08a3c"), cloth_dk=rgb("a05f22"), trim=rgb("f0c04a"),
        boot=rgb("5a3c20")),
    "guard": style(
        skin=rgb("e8b98c"), skin_sh=rgb("c4956a"),
        hair=rgb("4a3a2a"), hair_dk=rgb("2e241a"),
        cloth=rgb("8d8d98"), cloth_dk=rgb("5f5f6b"), trim=rgb("b8b8c0"),
        boot=rgb("3d3d47"), helm=True, weapon="sword", weapon_dk=rgb("6b4423")),
    "child": style(
        skin=rgb("f4cfa8"), skin_sh=rgb("d0a880"),
        hair=rgb("d8a03c"), hair_dk=rgb("a8741f"),
        cloth=rgb("e07a9c"), cloth_dk=rgb("b5527a"), trim=rgb("f4f4ec"),
        boot=rgb("6b4423"), skirt=True),
}


def _shrink_child(img):
    """Kids read younger when squashed two rows and kept bottom-aligned."""
    out = Image(W, H)
    for y in range(H):
        src_y = int(y * (H - 3) / H) + 3
        for x in range(W):
            c = img.get(x, src_y)
            if c[3]:
                out.set(x, y, c)
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
            if name == "child":
                down, up, side = (_shrink_child(i) for i in (down, up, side))
            out["%s_down%d" % (name, frame)] = down
            out["%s_up%d" % (name, frame)] = up
            out["%s_right%d" % (name, frame)] = side
            out["%s_left%d" % (name, frame)] = side.flipped_x()
    for name, st in PARTY_STYLES.items():
        out["%s_ready" % name] = battle_pose(st, "ready").flipped_x()
        out["%s_attack" % name] = battle_pose(st, "attack").flipped_x()
        out["%s_hurt" % name] = battle_pose(st, "hurt").flipped_x()
    return out
