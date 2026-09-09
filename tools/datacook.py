#!/usr/bin/env python3
"""datacook - the single source of truth for the game's rules and content.

Spells, items, classes, monsters, encounter tables, townsfolk, the tile
legend and the loot are authored here and written to assets/gamedata.json.
Both runtimes read that file: the browser build inlines it into index.html,
and the Godot project loads it at startup, so balance is changed in one place.

    python3 tools/datacook.py
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INN_COST = 50

# Magic. `kind` drives resolution; `power` is the raw scaling term.
SPELLS = {'fire': {'name': 'Fire',
          'mp': 4,
          'power': 22,
          'kind': 'attack',
          'element': 'fire',
          'target': 'enemy',
          'fx': 'fire'},
 'ice': {'name': 'Blizzard',
         'mp': 4,
         'power': 20,
         'kind': 'attack',
         'element': 'ice',
         'target': 'enemy',
         'fx': 'ice'},
 'bolt': {'name': 'Thunder',
          'mp': 6,
          'power': 28,
          'kind': 'attack',
          'element': 'bolt',
          'target': 'enemy',
          'fx': 'bolt'},
 'flare': {'name': 'Flare',
           'mp': 18,
           'power': 62,
           'kind': 'attack',
           'element': None,
           'target': 'enemy',
           'fx': 'flare'},
 'quake': {'name': 'Quake',
           'mp': 14,
           'power': 30,
           'kind': 'attack',
           'element': 'earth',
           'target': 'enemies',
           'fx': 'quake'},
 'cure': {'name': 'Cure', 'mp': 4, 'power': 46, 'kind': 'heal', 'target': 'ally', 'fx': 'heal'},
 'cura': {'name': 'Cura',
          'mp': 10,
          'power': 110,
          'kind': 'heal',
          'target': 'ally',
          'fx': 'heal'},
 'vigil': {'name': 'Vigil',
           'mp': 8,
           'power': 40,
           'kind': 'healAll',
           'target': 'allies',
           'fx': 'heal'},
 'life': {'name': 'Raise',
          'mp': 16,
          'power': 0.5,
          'kind': 'revive',
          'target': 'ally',
          'fx': 'holy'},
 'holy': {'name': 'Radiance',
          'mp': 20,
          'power': 58,
          'kind': 'attack',
          'element': 'holy',
          'target': 'enemy',
          'fx': 'holy'}}

# Consumables. `price` is what the quartermaster charges.
ITEMS = {'potion': {'name': 'Potion',
            'icon': 'i_potion',
            'price': 40,
            'kind': 'heal',
            'power': 70,
            'desc': 'Restores 70 HP.'},
 'hipotion': {'name': 'Hi-Potion',
              'icon': 'i_potion',
              'price': 150,
              'kind': 'heal',
              'power': 250,
              'desc': 'Restores 250 HP.'},
 'ether': {'name': 'Ether',
           'icon': 'i_ether',
           'price': 200,
           'kind': 'mp',
           'power': 40,
           'desc': 'Restores 40 MP.'},
 'phoenix': {'name': 'Phoenix Down',
             'icon': 'i_phoenix',
             'price': 260,
             'kind': 'revive',
             'power': 0.4,
             'desc': 'Revives a fallen ally.'},
 'bomb': {'name': 'Fire Bomb',
          'icon': 'i_phoenix',
          'price': 120,
          'kind': 'damage',
          'power': 90,
          'desc': 'Hurls fire at one foe.'}}

# Party growth is flat per level and deliberately readable:
# stat(level) = base + grow * (level - 1).
CLASSES = {'aldric': {'name': 'Aldric',
            'title': 'Knight',
            'sprite': 'aldric',
            'base': {'hp': 130, 'mp': 0, 'atk': 16, 'def': 12, 'mag': 4, 'spd': 9},
            'grow': {'hp': 22, 'mp': 0, 'atk': 3.1, 'def': 2.4, 'mag': 0.5, 'spd': 0.8},
            'spells': [],
            'skill': None},
 'lyra': {'name': 'Lyra',
          'title': 'Black Mage',
          'sprite': 'lyra',
          'base': {'hp': 74, 'mp': 34, 'atk': 8, 'def': 6, 'mag': 17, 'spd': 11},
          'grow': {'hp': 12, 'mp': 7, 'atk': 1.1, 'def': 1.2, 'mag': 3.4, 'spd': 1.1},
          'spells': [{'id': 'fire', 'lv': 1},
                     {'id': 'ice', 'lv': 1},
                     {'id': 'bolt', 'lv': 3},
                     {'id': 'quake', 'lv': 6},
                     {'id': 'flare', 'lv': 9}]},
 'mira': {'name': 'Mira',
          'title': 'White Mage',
          'sprite': 'mira',
          'base': {'hp': 88, 'mp': 30, 'atk': 9, 'def': 8, 'mag': 15, 'spd': 10},
          'grow': {'hp': 15, 'mp': 6, 'atk': 1.3, 'def': 1.6, 'mag': 3, 'spd': 1},
          'spells': [{'id': 'cure', 'lv': 1},
                     {'id': 'cura', 'lv': 4},
                     {'id': 'vigil', 'lv': 6},
                     {'id': 'life', 'lv': 5},
                     {'id': 'holy', 'lv': 8}]}}

# Monsters. `ai` entries are weighted; `weak` names a doubled-down element.
# `height` is how tall the thing should stand on screen, in game pixels. That
# used to be a bare `scale` multiplier, which nobody could sanity-check: x2 on
# a 20-pixel bat and x2 on a 40-pixel ogre are not the same decision, and the
# result was a cave bat taller than the knight fighting it. A hero is drawn 36
# pixels tall, so these numbers can be read against that and argued with.
ENEMIES = {'slime': {'name': 'Bog Slime',
          'height': 22,   # a blob you could step over
           'sprite': 'e_slime',
           'hp': 34,
           'atk': 10,
           'def': 6,
           'mag': 4,
           'spd': 5,
           'exp': 8,
           'gil': 7,
           'weak': 'bolt',
           'ai': [{'w': 100, 'act': 'attack'}]},
 'bat': {'name': 'Cave Bat',
        'height': 20,   # a cave bat, not a roc
         'sprite': 'e_bat',
         'hp': 26,
         'atk': 12,
         'def': 4,
         'mag': 5,
         'spd': 15,
         'exp': 9,
         'gil': 9,
         'weak': 'fire',
         'ai': [{'w': 80, 'act': 'attack'}, {'w': 20, 'act': 'drain'}]},
 'goblin': {'name': 'Goblin',
           'height': 30,   # a head shorter than a knight
            'sprite': 'e_goblin',
            'hp': 52,
            'atk': 15,
            'def': 9,
            'mag': 4,
            'spd': 9,
            'exp': 14,
            'gil': 16,
            'ai': [{'w': 85, 'act': 'attack'}, {'w': 15, 'act': 'rally'}]},
 'wolf': {'name': 'Direwolf',
         'height': 24,   # tall at the shoulder, long in the body
          'sprite': 'e_wolf',
          'hp': 68,
          'atk': 19,
          'def': 10,
          'mag': 4,
          'spd': 14,
          'exp': 20,
          'gil': 18,
          'weak': 'fire',
          'ai': [{'w': 70, 'act': 'attack'}, {'w': 30, 'act': 'pounce'}]},
 'wisp': {'name': 'Marsh Wisp',
         'height': 24,   # a drifting light
          'sprite': 'e_wisp',
          'hp': 58,
          'atk': 11,
          'def': 8,
          'mag': 18,
          'spd': 12,
          'exp': 22,
          'gil': 24,
          'weak': 'holy',
          'ai': [{'w': 45, 'act': 'attack'}, {'w': 55, 'act': 'spell', 'spell': 'fire'}]},
 'bandit': {'name': 'Road Bandit',
           'height': 32,   # a man
            'sprite': 'e_bandit',
            'hp': 92,
            'atk': 22,
            'def': 12,
            'mag': 6,
            'spd': 12,
            'exp': 30,
            'gil': 45,
            'ai': [{'w': 70, 'act': 'attack'}, {'w': 30, 'act': 'steal'}]},
 'skeleton': {'name': 'Barrow Guard',
              'height': 30,   # was a man
              'sprite': 'e_skeleton',
              'hp': 78,
              'atk': 22,
              'def': 16,
              'mag': 4,
              'spd': 10,
              'exp': 26,
              'gil': 22,
              'weak': 'quake',
              'ai': [{'w': 75, 'act': 'attack'}, {'w': 25, 'act': 'rally'}]},
 'wight': {'name': 'Barrow Wight',
           'height': 34,   # was a man, and stands taller for it
           'sprite': 'e_wight',
           'hp': 96,
           'atk': 20,
           'def': 13,
           'mag': 19,
           'spd': 13,
           'exp': 34,
           'gil': 30,
           'weak': 'fire',
           'ai': [{'w': 40, 'act': 'attack'},
                  {'w': 35, 'act': 'spell', 'spell': 'ice'},
                  {'w': 25, 'act': 'drain'}]},
 'ogre': {'name': 'Ogre Chieftain',
         'height': 76,   # the boss, and the only thing here bigger than you
          'sprite': 'e_ogre',
          'boss': True,
          'hp': 520,
          'atk': 30,
          'def': 16,
          'mag': 12,
          'spd': 10,
          'exp': 260,
          'gil': 500,
          'weak': 'ice',
          'ai': [{'w': 55, 'act': 'attack'},
                 {'w': 25, 'act': 'smash'},
                 {'w': 20, 'act': 'spell', 'spell': 'quake'}]}}

# Weighted encounter table for the Thornwilds.
# Encounter tables, keyed by region. A map names the table it draws from, so
# the barrow can be a harder place without touching the wilds.
ENCOUNTERS = {
    'wild': [{'w': 26, 'group': ['slime']},
             {'w': 20, 'group': ['bat', 'bat']},
             {'w': 18, 'group': ['goblin']},
             {'w': 14, 'group': ['slime', 'slime', 'bat']},
             {'w': 12, 'group': ['wolf']},
             {'w': 10, 'group': ['goblin', 'goblin']},
             {'w': 8, 'group': ['wisp']},
             {'w': 7, 'group': ['wolf', 'goblin']},
             {'w': 5, 'group': ['bandit']},
             {'w': 4, 'group': ['wisp', 'bat', 'bat']}],
    'barrow': [{'w': 24, 'group': ['skeleton']},
               {'w': 18, 'group': ['bat', 'bat', 'bat']},
               {'w': 16, 'group': ['skeleton', 'skeleton']},
               {'w': 12, 'group': ['wight']},
               {'w': 10, 'group': ['skeleton', 'wolf']},
               {'w': 8, 'group': ['wisp', 'wisp']},
               {'w': 7, 'group': ['wight', 'skeleton']},
               {'w': 5, 'group': ['bandit', 'skeleton']}],
}

# Townsfolk, keyed by map id. {name}/{menu}/{cancel} are filled in at runtime.
NPCS = {'town': [{'x': 20,
           'y': 17,
           'sprite': 'elder',
           'dir': 'down',
           'name': 'Elder Halvard',
           'wander': False,
           'lines': ['Rivenbrook has stood a hundred years, {name}.',
                     'But something stirs in the Thornwilds. A chieftain, the scouts say.',
                     'Take the south gate. And take care.']},
          {'x': 16,
           'y': 21,
           'sprite': 'villager',
           'dir': 'right',
           'name': 'Gardener Pell',
           'wander': True,
           'lines': ['These beds were carrots last spring.',
                     'Now? Weeds and worry. Nothing grows with monsters at the fence.']},
          {'x': 24,
           'y': 14,
           'sprite': 'child',
           'dir': 'left',
           'name': 'Tam',
           'wander': True,
           'lines': ['I saw a wolf as big as a cart!', 'Mum says I made it up. I did not.']},
          {'x': 19,
           'y': 26,
           'sprite': 'guard',
           'dir': 'down',
           'name': 'Gate Guard',
           'wander': False,
           'lines': ['Beyond the gate is the Thornwilds. Fight or flee, but never dawdle.',
                     'Press {menu} any time to open your journal.']},
          {'x': 21,
           'y': 26,
           'sprite': 'guard',
           'dir': 'down',
           'name': 'Gate Guard',
           'wander': False,
           'lines': ['The Amber Lantern keeps a bed and a stocked shelf.',
                     'Rest before you go. Only a fool walks the wilds tired.']},
          {'x': 9,
           'y': 12,
           'sprite': 'villager',
           'dir': 'down',
           'name': 'Smith Orla',
           'wander': True,
           'lines': ['Steel I can give you. Courage you bring yourself.',
                     "Lyra's fire and Mira's mercy - that's a party worth its salt."]},
          {'x': 33,
           'y': 16,
           'sprite': 'merchant',
           'dir': 'left',
           'name': 'Pedlar Voss',
           'wander': True,
           'lines': ['Buying? The inn keeps my stock these days.',
                     'Too many bandits on the south road for an honest cart.']}],
 'inn': [{'x': 4,
          'y': 4,
          'sprite': 'merchant',
          'dir': 'down',
          'name': 'Innkeeper Bryn',
          'wander': False,
          'service': 'inn',
          'lines': ['Welcome to the Amber Lantern.']},
         {'x': 6,
          'y': 6,
          'sprite': 'villager',
          'dir': 'down',
          'name': 'Quartermaster',
          'wander': False,
          'service': 'shop',
          'lines': ['Potions, ethers, and a bomb or two.']},
         {'x': 12,
          'y': 9,
          'sprite': 'child',
          'dir': 'left',
          'name': 'Nib',
          'wander': True,
          'lines': ['If you press {cancel} you can run! Grown-ups always forget.']}],
 'wild': []}

SHOP_STOCK = ['potion', 'hipotion', 'ether', 'phoenix', 'bomb']

# Tile legend: map character -> [sprite, solid, tag].
LEGEND = {'1': ['t_bedtop', 1, 'bed'],
 '#': ['t_cryptwall', 1],
 '_': ['t_crypt', 0],
 '<': ['t_stairup', 0, 'stair'],
 '>': ['t_stairdown', 0, 'stair'],
 'g': ['t_gate', 1, 'gate'],
 'i': ['t_brazier', 1],
 'j': ['t_bones', 0],
 '2': ['t_bedbot', 1, 'bed'],
 '.': ['t_grass', 0],
 'F': ['t_plank', 0],
 ',': ['t_grass2', 0],
 '*': ['t_flowers', 0],
 '"': ['t_tallgrass', 0],
 '-': ['t_path', 0],
 '=': ['t_cobble', 0],
 'x': ['t_sand', 0],
 'B': ['t_bridge', 0],
 'D': ['t_door', 0, 'door'],
 '~': ['t_water0', 1, 'water'],
 'T': ['t_tree', 1],
 'b': ['t_bush', 1],
 'r': ['t_rock', 1],
 'K': ['t_counter', 1],
 'A': ['t_barrel', 1],
 'H': ['t_shelf', 1],
 'U': ['t_rug', 0],
 'M': ['t_mountain', 1],
 'W': ['t_wall', 1],
 'R': ['t_roof', 1],
 '^': ['t_rooftop', 1],
 'G': ['t_window', 1],
 'f': ['t_fence', 1],
 's': ['t_sign', 1, 'sign'],
 'o': ['t_well', 1, 'well'],
 'c': ['t_chest', 1, 'chest'],
 'l': ['t_lamp', 1, 'lamp']}

# What sits under a prop so it never floats on a void.
# 'ground' resolves to each map's own ground tile.
UNDERLAY = {'1': 'ground',
 'i': 't_crypt',
 'j': 't_crypt',
 'g': 't_crypt',
 '2': 'ground',
 'T': 'ground',
 'b': 'ground',
 'r': 'ground',
 'f': 'ground',
 's': 'ground',
 'c': 'ground',
 'A': 'ground',
 'l': 't_cobble',
 'o': 't_cobble',
 'B': 't_water0',
 'U': 'ground'}

SIGN_TEXT = {'town': 'RIVENBROOK - The Amber Lantern, rooms and remedies.',
 'wild': 'THORNWILDS SHRINE - The barrow below is sealed. It was sealed for a reason.',
 'barrow1': 'Carved into the lintel: THE CHIEFTAIN SLEEPS BELOW. LET HIM.'}

# --------------------------------------------------------------------- gear
# Three slots per character. `users` is None when anyone can wear it, and the
# stats are flat bonuses folded into the derived stats, so nothing downstream
# has to know equipment exists - a sword just makes atk bigger.
GEAR = {
    # weapons
    'bronze_sword': {'name': 'Bronze Sword', 'slot': 'weapon', 'icon': 'i_sword',
                     'price': 120, 'users': ['aldric'], 'stats': {'atk': 6},
                     'desc': 'A recruit\'s blade. Honest, blunt.'},
    'iron_sword': {'name': 'Iron Sword', 'slot': 'weapon', 'icon': 'i_sword',
                   'price': 480, 'users': ['aldric'], 'stats': {'atk': 15},
                   'desc': 'Heavier, and it tells.'},
    'flame_brand': {'name': 'Flame Brand', 'slot': 'weapon', 'icon': 'i_sword',
                    'price': 1400, 'users': ['aldric'], 'stats': {'atk': 26},
                    'element': 'fire', 'desc': 'Its edge burns. Ice hates it.'},
    'oak_staff': {'name': 'Oak Staff', 'slot': 'weapon', 'icon': 'i_staff',
                  'price': 100, 'users': ['lyra', 'mira'], 'stats': {'atk': 2, 'mag': 4},
                  'desc': 'Plain wood, patiently carved.'},
    'moon_rod': {'name': 'Moon Rod', 'slot': 'weapon', 'icon': 'i_staff',
                 'price': 520, 'users': ['lyra'], 'stats': {'atk': 3, 'mag': 12},
                 'desc': 'Cold to hold. Sharpens a spell.'},
    'sage_cane': {'name': 'Sage Cane', 'slot': 'weapon', 'icon': 'i_staff',
                  'price': 560, 'users': ['mira'], 'stats': {'atk': 3, 'mag': 9, 'mp': 10},
                  'desc': 'Carried by healers who walk far.'},

    # armour
    'leather_vest': {'name': 'Leather Vest', 'slot': 'armour', 'icon': 'i_armor',
                     'price': 90, 'users': None, 'stats': {'def': 4},
                     'desc': 'Better than a shirt.'},
    'chain_mail': {'name': 'Chain Mail', 'slot': 'armour', 'icon': 'i_armor',
                   'price': 420, 'users': ['aldric'], 'stats': {'def': 12, 'spd': -1},
                   'desc': 'Turns a blade. Slows a step.'},
    'silk_robe': {'name': 'Silk Robe', 'slot': 'armour', 'icon': 'i_armor',
                  'price': 380, 'users': ['lyra', 'mira'], 'stats': {'def': 6, 'mag': 3},
                  'desc': 'Woven to carry a spell cleanly.'},
    'knight_plate': {'name': 'Knight Plate', 'slot': 'armour', 'icon': 'i_armor',
                     'price': 1200, 'users': ['aldric'], 'stats': {'def': 21, 'spd': -2},
                     'desc': 'A wall you can walk in.'},

    # accessories
    'copper_ring': {'name': 'Copper Ring', 'slot': 'trinket', 'icon': 'i_ring',
                    'price': 150, 'users': None, 'stats': {'hp': 24},
                    'desc': 'Warm against the skin.'},
    'sage_pendant': {'name': 'Sage Pendant', 'slot': 'trinket', 'icon': 'i_ring',
                     'price': 300, 'users': None, 'stats': {'mp': 14},
                     'desc': 'Holds a little more of the well.'},
    'swift_boots': {'name': 'Swift Boots', 'slot': 'trinket', 'icon': 'i_ring',
                    'price': 450, 'users': None, 'stats': {'spd': 5},
                    'desc': 'The gauge fills that bit faster.'},
    'guard_charm': {'name': 'Guard Charm', 'slot': 'trinket', 'icon': 'i_ring',
                    'price': 700, 'users': None, 'stats': {'def': 7, 'hp': 30},
                    'desc': 'Someone wanted you to come home.'},
}

# The three slots, in the order the equip screen lists them.
GEAR_SLOTS = [
    {'id': 'weapon', 'label': 'Weapon'},
    {'id': 'armour', 'label': 'Armour'},
    {'id': 'trinket', 'label': 'Trinket'},
]

# What each character walks out of the prologue wearing.
STARTING_GEAR = {
    'aldric': {'weapon': 'bronze_sword', 'armour': 'leather_vest', 'trinket': None},
    'lyra': {'weapon': 'oak_staff', 'armour': None, 'trinket': None},
    'mira': {'weapon': 'oak_staff', 'armour': None, 'trinket': None},
}

# The armoury's shelf. The best pieces are not for sale - those are found.
GEAR_STOCK = ['bronze_sword', 'iron_sword', 'oak_staff', 'moon_rod', 'sage_cane',
              'leather_vest', 'chain_mail', 'silk_robe',
              'copper_ring', 'sage_pendant', 'swift_boots']

# Keyed "<map>:<x>,<y>".
CHEST_LOOT = {'town:4,5': {'item': 'potion', 'n': 2},
 'town:35,24': {'item': 'ether', 'n': 1},
 'inn:11,2': {'gil': 120},
 'wild:43,39': {'item': 'hipotion', 'n': 2},
 'wild:6,12': {'gear': 'copper_ring'},
 'wild:51,5': {'item': 'potion', 'n': 3},
 'wild:13,36': {'gil': 220},
 # The barrow. The gate key is a flag rather than a bag item: it opens one
 # door and then it has done its job.
 'barrow1:6,6': {'gear': 'guard_charm'},
 'barrow1:30,16': {'item': 'hipotion', 'n': 2},
 'barrow1:33,6': {'flag': 'barrowKey',
                  'text': 'A heavy iron key, green with age.'},
 'barrow2:4,6': {'gear': 'knight_plate'},
 'barrow2:32,22': {'gil': 600},
 'barrow2:18,4': {'gear': 'flame_brand'}}


def _check_chests():
    """Every chest_loot key must name a tile that actually holds a chest.

    Loot keyed to a spot with no chest on it is invisible: the item exists in
    the data and nobody can ever open it. mapcook runs before this step, so
    the painted maps are on disk to check against.
    """
    path = os.path.join(ROOT, "assets", "maps.json")
    if not os.path.exists(path):
        return []
    with open(path) as fh:
        maps = json.load(fh)
    problems = []
    for key in sorted(CHEST_LOOT):
        map_id, _, xy = key.partition(":")
        x, y = (int(n) for n in xy.split(","))
        rows = maps.get(map_id, {}).get("rows")
        if not rows or y >= len(rows) or x >= len(rows[y]) or rows[y][x] != "c":
            problems.append(key)
    if problems:
        raise SystemExit("chest loot with no chest on the map: %s" % ", ".join(problems))
    return sorted(CHEST_LOOT)


def build():
    _check_chests()
    payload = {
        "spells": SPELLS,
        "items": ITEMS,
        "classes": CLASSES,
        "enemies": ENEMIES,
        "encounters": ENCOUNTERS,
        "npcs": NPCS,
        "shop_stock": SHOP_STOCK,
        "legend": LEGEND,
        "underlay": UNDERLAY,
        "sign_text": SIGN_TEXT,
        "chest_loot": CHEST_LOOT,
        "gear": GEAR,
        "gear_slots": GEAR_SLOTS,
        "gear_stock": GEAR_STOCK,
        "starting_gear": STARTING_GEAR,
        "inn_cost": INN_COST,
    }
    path = os.path.join(ROOT, "assets", "gamedata.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(payload, fh, indent=1, sort_keys=True)
    return path, payload


if __name__ == "__main__":
    path, payload = build()
    print("data  : %s (%d spells, %d items, %d gear, %d monsters, %d tiles)"
          % (path, len(payload["spells"]), len(payload["items"]),
             len(payload["gear"]), len(payload["enemies"]), len(payload["legend"])))
