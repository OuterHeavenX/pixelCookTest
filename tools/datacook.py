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
 'ward': {'name': 'Ward',
          'mp': 6,
          'power': 0,
          'kind': 'guardAll',
          'target': 'allies',
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
 'bram': {'name': 'Bram',
          'title': 'Shieldman',
          'sprite': 'bram',
          'base': {'hp': 158, 'mp': 0, 'atk': 15, 'def': 16, 'mag': 3, 'spd': 7},
          'grow': {'hp': 27, 'mp': 0, 'atk': 2.8, 'def': 3.0, 'mag': 0.3, 'spd': 0.6},
          'spells': [],
          'skill': None},
 'sera': {'name': 'Sera',
          'title': 'Sealkeeper',
          'sprite': 'sera',
          'base': {'hp': 96, 'mp': 26, 'atk': 11, 'def': 11, 'mag': 14, 'spd': 12},
          'grow': {'hp': 16, 'mp': 6, 'atk': 1.4, 'def': 2.0, 'mag': 2.8, 'spd': 1.2},
          'spells': [{'id': 'ward', 'lv': 1},
                     {'id': 'cure', 'lv': 1},
                     {'id': 'holy', 'lv': 4},
                     {'id': 'vigil', 'lv': 7}]},
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
 'rimewolf': {'name': 'Rimewolf',
              'height': 26,   # leaner than a direwolf, and it does not tire
              'sprite': 'e_wolf_ice',
              'hp': 104,
              'atk': 27,
              'def': 14,
              'mag': 6,
              'spd': 18,
              'exp': 38,
              'gil': 30,
              'weak': 'fire',
              'ai': [{'w': 60, 'act': 'attack'}, {'w': 40, 'act': 'pounce'}]},
 'mereling': {'name': 'Mereling',
              'height': 26,   # whatever the lake has been growing
              'sprite': 'e_slime_ice',
              'hp': 120,
              'atk': 21,
              'def': 19,
              'mag': 16,
              'spd': 9,
              'exp': 40,
              'gil': 34,
              'weak': 'bolt',
              'ai': [{'w': 55, 'act': 'attack'},
                     {'w': 45, 'act': 'spell', 'spell': 'ice'}]},
 'lampwraith': {'name': 'Lamp Wraith',
                'height': 30,   # what a lantern keeps out
                'sprite': 'e_wight_ice',
                'hp': 132,
                'atk': 24,
                'def': 15,
                'mag': 24,
                'spd': 15,
                'exp': 52,
                'gil': 46,
                'weak': 'holy',
                'ai': [{'w': 35, 'act': 'attack'},
                       {'w': 40, 'act': 'spell', 'spell': 'ice'},
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
    # The road along the mere. Everything here is colder and hits harder.
    'shore': [{'w': 24, 'group': ['rimewolf']},
              {'w': 18, 'group': ['mereling']},
              {'w': 16, 'group': ['rimewolf', 'rimewolf']},
              {'w': 12, 'group': ['bat', 'bat', 'rimewolf']},
              {'w': 10, 'group': ['lampwraith']},
              {'w': 8, 'group': ['mereling', 'mereling']},
              {'w': 7, 'group': ['lampwraith', 'rimewolf']},
              {'w': 5, 'group': ['wight', 'mereling']}],
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
NPCS = { 'hollow': [{'x': 21,
             'y': 28,
             'sprite': 'bram',
             'dir': 'down',
             'name': 'Bram',
             'wander': False,
             'recruit': 'bram',
             'lines': ['{name}. I heard what came out of that barrow, and I heard who went in.',
                       'Four hundred miles I have not seen you, and you still walk like a recruit.',
                       'They are lighting the lamps at noon here. Noon.',
                       'I am not letting you go down there alone twice. Move over.'],
             'after': ['Say the word and I will go first. That is the job.',
                       'Have you talked to the lamp girl? She knows something.']},
            {'x': 20,
             'y': 9,
             'sprite': 'sera',
             'dir': 'up',
             'name': 'Sera',
             'wander': False,
             'recruit': 'sera',
             'lines': ['Careful. The mere took two dogs and a cart this week.',
                       'It has not frozen in summer since my grandmother was small.',
                       'You are the one from Rivenbrook. You broke the ward.',
                       'No - do not apologise. My family cut that ward. We should have told somebody what it was for.',
                       'I am coming with you. It is my mess as much as yours now.'],
             'after': ['I keep the lamps because my mother did, and hers.',
                       'Nobody ever said why. We just never let one go out.']},
            {'x': 27,
             'y': 16,
             'sprite': 'merchant',
             'dir': 'down',
             'name': 'Keeper Ilse',
             'wander': False,
             'service': 'inn',
             'lines': ['Beds are warm. The mere is not. Fifty gil.']},
            {'x': 21,
             'y': 24,
             'sprite': 'villager',
             'dir': 'up',
             'name': 'Armourer Fenn',
             'wander': False,
             'service': 'shop',
             'shelf': 'hollow',
             'lines': ['Cold-country work. It weighs more and it is worth it.']},
            {'x': 12,
             'y': 19,
             'sprite': 'elder',
             'dir': 'right',
             'name': 'Old Marrow',
             'wander': False,
             'lines': ['Lamps at noon, lad. Lamps at noon.',
                       'My father said the day we stop is the day it comes up.']},
            {'x': 33,
             'y': 22,
             'sprite': 'child',
             'dir': 'left',
             'name': 'Pip',
             'wander': True,
             'lines': ['I skated on the mere once. Once.',
                       'Sera pulled me out and did not even shout.']},
            {'x': 8,
             'y': 22,
             'sprite': 'guard',
             'dir': 'down',
             'name': 'Watchwoman',
             'wander': False,
             'lines': ['We watch the water, not the road. The road never hurt anybody.']}],
 'town': [{'x': 20,
           'y': 17,
           'sprite': 'elder',
           'dir': 'down',
                      'after': ['You came back. Sit down, {name}. You look like the barrow looked at you.',
                      'The scouts found the shrine sign re-cut. Fresh chisel marks, this week.',
                      'Somebody is still tending that seal. It is not us.'],
           'name': 'Elder Halvard',
           'wander': False,
           'lines': ['Rivenbrook has stood a hundred years, {name}.',
                     'But something stirs in the Thornwilds. A chieftain, the scouts say.',
                     'Take the south gate. And take care.']},
          {'x': 16,
           'y': 21,
           'sprite': 'villager',
           'dir': 'right',
                      'after': ['Carrots this spring, maybe. The fence held.',
                      'Ground has gone cold at the south end, mind. Nothing takes root there.'],
           'name': 'Gardener Pell',
           'wander': True,
           'lines': ['These beds were carrots last spring.',
                     'Now? Weeds and worry. Nothing grows with monsters at the fence.']},
          {'x': 24,
           'y': 14,
           'sprite': 'child',
           'dir': 'left',
                      'after': ['Did you SEE it? Was it big? Was it bigger than the mill?',
                      'Ma says stay off the south road. Ma says a lot of things.'],
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
                      "after": ["Bring me the chieftain's plate and I will make you something out of it.",
                      "Whatever cracked in that barrow, you will want better steel than this."],
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
                    'after': ['Room is on the house tonight. You have earned the bed.',
                     'Do not tell the others, but I have been leaving a lamp lit facing south.'],
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
          'shelf': 'amber',
          'lines': ['Potions, ethers, and a bomb or two.']},
         {'x': 12,
          'y': 9,
          'sprite': 'child',
          'dir': 'left',
          'name': 'Nib',
          'wander': True,
          'lines': ['If you press {cancel} you can run! Grown-ups always forget.']}],
 'wild': []}

# What each counter sells, keyed by the shelf an NPC names.
SHOP_STOCK = {
    'amber': ['potion', 'hipotion', 'ether', 'phoenix', 'bomb'],
    'hollow': ['potion', 'hipotion', 'ether', 'phoenix', 'bomb'],
}

# Tile legend: map character -> [sprite, solid, tag].
LEGEND = {'1': ['t_bedtop', 1, 'bed'],
 '#': ['t_cryptwall', 1],
 '_': ['t_crypt', 0],
 '<': ['t_stairup', 0, 'stair'],
 '>': ['t_stairdown', 0, 'stair'],
 'g': ['t_gate', 1, 'gate'],
 'i': ['t_brazier', 1],
 '%': ['t_seal', 0, 'seal'],
 'I': ['t_ice', 1, 'water'],
 'n': ['t_snow', 0],
 'P': ['t_palewall', 1],
 'V': ['t_palewindow', 1],
 'Q': ['t_blueroof', 1],
 'L': ['t_lantern', 1, 'lamp'],
 'p': ['t_pinesnow', 1],
 '/': ['t_path', 0, 'pass'],
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
 '%': 't_crypt',
 'L': 't_snow',
 'p': 't_snow',
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

SIGN_TEXT = {'shore': 'THE MERE ROAD - Do not stop between the lamps.',
 'hollow': 'HOLLOWMERE - Keep the lanterns lit. Keep off the ice.',
 'town': 'RIVENBROOK - The Amber Lantern, rooms and remedies.',
 'wild': 'THORNWILDS SHRINE - The barrow below is sealed. It was sealed for a reason.',
 'barrow1': 'Carved into the lintel: THE CHIEFTAIN SLEEPS BELOW. LET HIM.'}

# Signs that read differently once the ward is broken.
SIGN_AFTER = {
 'wild': 'THORNWILDS SHRINE - The barrow below is sealed. The letters are fresh cut. Someone re-carved this recently.',
 'barrow1': 'Carved into the lintel: THE CHIEFTAIN SLEEPS BELOW. Under it, newer: HE IS AWAKE. RUN.'}

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

    'iron_halberd': {'name': 'Iron Halberd', 'slot': 'weapon', 'icon': 'i_sword',
                     'price': 620, 'users': ['bram'], 'stats': {'atk': 18, 'def': 2},
                     'desc': 'Long enough to keep trouble at arm\'s length.'},
    'warden_staff': {'name': 'Warden Staff', 'slot': 'weapon', 'icon': 'i_staff',
                     'price': 640, 'users': ['sera'], 'stats': {'atk': 4, 'mag': 11, 'def': 3},
                     'desc': 'Hollowmere work. The head is a seal, not an ornament.'},
    'rimeblade': {'name': 'Rimeblade', 'slot': 'weapon', 'icon': 'i_sword',
                  'price': 1150, 'users': ['aldric'], 'stats': {'atk': 22},
                  'element': 'ice', 'desc': 'The edge frosts over as you draw it.'},
    'frost_pike': {'name': 'Frost Pike', 'slot': 'weapon', 'icon': 'i_sword',
                   'price': 1500, 'users': ['bram'], 'stats': {'atk': 29, 'def': 3},
                   'element': 'ice', 'desc': 'Cold to carry. Colder to be hit by.'},
    'mere_wand': {'name': 'Mere Wand', 'slot': 'weapon', 'icon': 'i_staff',
                  'price': 900, 'users': ['lyra', 'sera'], 'stats': {'atk': 3, 'mag': 17},
                  'desc': 'Lake-glass, still cold from the water.'},

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
    'lake_mail': {'name': 'Lake Mail', 'slot': 'armour', 'icon': 'i_armor',
                  'price': 780, 'users': ['aldric', 'bram'], 'stats': {'def': 16},
                  'desc': 'Scales cut from something that lived in the mere.'},
    'warden_coat': {'name': 'Warden Coat', 'slot': 'armour', 'icon': 'i_armor',
                    'price': 720, 'users': ['lyra', 'mira', 'sera'],
                    'stats': {'def': 11, 'mag': 4},
                    'desc': 'Lined, hooded, and older than anyone wearing it.'},
    'furs': {'name': 'Thick Furs', 'slot': 'armour', 'icon': 'i_armor',
             'price': 300, 'users': None, 'stats': {'def': 8, 'spd': -1},
             'desc': 'Warm. That is the entire argument.'},
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
    'ice_charm': {'name': 'Rime Charm', 'slot': 'trinket', 'icon': 'i_ring',
                  'price': 560, 'users': None, 'stats': {'def': 5, 'mag': 5},
                  'desc': 'Cold to hold, and it keeps the cold out.'},
    'lantern_stone': {'name': 'Lantern Stone', 'slot': 'trinket', 'icon': 'i_ring',
                      'price': 820, 'users': None, 'stats': {'mp': 22, 'mag': 4},
                      'desc': 'Hollowmere keeps its lamps lit with these.'},
    'guard_charm': {'name': 'Guard Charm', 'slot': 'trinket', 'icon': 'i_ring',
                    'price': 700, 'users': None, 'stats': {'def': 7, 'hp': 30},
                    'desc': 'Someone wanted you to come home.'},
    # Not for sale anywhere. It is given, once, by one person, and it is worth
    # about as much as a shop trinket - the point of it is whose it was.
    'lamp_key': {'name': "Sera's Lamp Key", 'slot': 'trinket', 'icon': 'i_ring',
                 'price': 0, 'users': ['aldric'], 'stats': {'def': 4, 'mag': 4, 'hp': 20},
                 'desc': "Her mother's. It still turns the ones on the bridge."},
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
    # Chapter two. They arrive carrying what they own, not what you bought.
    'bram': {'weapon': 'iron_halberd', 'armour': 'chain_mail', 'trinket': None},
    'sera': {'weapon': 'warden_staff', 'armour': 'silk_robe', 'trinket': 'copper_ring'},
}

# The armoury's shelf. The best pieces are not for sale - those are found.
GEAR_STOCK = {
    'amber': ['bronze_sword', 'iron_sword', 'oak_staff', 'moon_rod', 'sage_cane',
              'leather_vest', 'chain_mail', 'silk_robe',
              'copper_ring', 'sage_pendant', 'swift_boots'],
    # Hollowmere sells cold-country work, and things for the two people who
    # walked out of the mist to join you.
    'hollow': ['iron_halberd', 'warden_staff', 'mere_wand', 'rimeblade',
               'lake_mail', 'warden_coat', 'furs',
               'ice_charm', 'lantern_stone', 'swift_boots'],
}

# --------------------------------------------------------------------- ending
# What the chieftain's death actually reveals. The shrine sign has said "the
# barrow below is sealed, it was sealed for a reason" since the first map was
# painted; this is the bill for ignoring it. The chieftain was not guarding a
# tomb, he was the lock on one, and the party has just broken it.
BOSS_VICTORY = [
    'The chieftain falls, and the barrow goes very quiet.',
    'Beneath the bier, something answers. A seam of light opens in the floor.',
    'The stone had a ward carved into it. It is cracked now.',
]

# The closing sequence, played once. Each beat is a screen of text over a
# scene; `scene` names what the ending draws behind it.
ENDING = {
    'beats': [
        {'scene': 'barrow', 'lines': [
            'The Ogre Chieftain was not the barrow\'s tenant.',
            'He was its warden. Something older set him on that bier',
            'and told him to sit, and he sat for four hundred years.']},
        {'scene': 'rift', 'lines': [
            'Cold comes up through the crack in the ward.',
            'Not the cold of a cellar. The cold of somewhere with no season.',
            'Far below, in the dark, something turns over and settles.']},
        {'scene': 'town', 'lines': [
            'You walk back into Rivenbrook at dawn.',
            'The lanterns are still lit. The gate is still standing.',
            'Elder Halvard meets you at the well and does not ask what you saw.']},
        {'scene': 'town', 'lines': [
            'For tonight, the Thornwilds are quiet, and that is enough.',
            'The seal will hold a while yet.',
            'A while.']},
    ],
    'title': 'CHAPTER ONE',
    'subtitle': 'THE WARDEN OF THE BARROW',
    'credits': [
        'RIVENBROOK',
        'A Tale of the Thornwilds',
        '',
        'Every sprite cooked by spritecook',
        'Backdrops and monsters modelled in Blender',
        'Maps painted by mapcook, rules by datacook',
        'Played in a browser and in Godot 4',
        '',
        'Chapter Two: THE COLD BELOW',
        'coming up out of the floor',
    ],
    'hook': 'Your journal is saved. The rift is still open.',
}

# Beats that fire the first time the party walks onto a map, once each. `needs`
# is every flag that must already be set, `absent` every flag that must not be,
# and `leaves` is who walks out of the party at the end of it.
MAP_BEATS = {
    'shore': [
        {'flag': 'bramHoldsRoad',
         'needs': ['bossDown'],
         'party': ['bram', 'sera'],
         'speaker': 'Bram',
         'leaves': 'bram',
         'lines': ["Hold on. Look at the lamps - every one of them lit, all the way back.",
                   "Somebody walks this road at dusk to do that. Every night. Alone.",
                   "If the road goes dark, Hollowmere goes dark, and then it is just you down there.",
                   "So I am staying up here and keeping them lit. No, do not.",
                   "{name}. I have followed you into one hole in the ground already.",
                   "Let me be useful where you can still find me."]},

        # Sera, in four movements, spread over the walk between Hollowmere and
        # the water. Nothing here is automatic: the first two are earned by
        # having her with you and coming back this way, the third asks you
        # outright, and the fourth is only the answer to a question she
        # refused to answer in the first.
        {'flag': 'seraDusk',
         'needs': ['bramHoldsRoad'],
         'party': ['sera'],
         'speaker': 'Sera',
         'lines': ["He is going to light every one of them, you know. All the way to the bridge.",
                   "My mother did that. Not the whole road - ours, and the two either side, because the Marrows are old.",
                   "I thought it was a chore. Then she went in the winter, and I went out at dusk anyway.",
                   "That was when I understood it was not a chore. It was a promise.",
                   "Ask me what I promised. No - ask me later. When we know what is under the water."]},

        {'flag': 'seraWater',
         'needs': ['seraLamp'],
         'party': ['sera'],
         'speaker': 'Sera',
         'lines': ["Stop a moment. The ice is talking.",
                   "It does that when it is thinking about breaking. Grandmother said it was the mere clearing its throat.",
                   "We are going down there soon, and one of us is going to say something stupid.",
                   "So it may as well be tonight. Sit with me until the lamps take."],
         'choice': {
             'options': ['Sit with her', 'There is no time'],
             'sets': ['seraClose', 'seraKept'],
             'replies': [
                 ["She does not say anything else for a long while. Neither do you.",
                  "The lamps take, one after another, all the way down to the bridge.",
                  "\"There,\" she says. \"Now I have kept it twice.\""],
                 ["\"No,\" she agrees. \"There is not.\"",
                  "She stands, walks on ahead of you, and lights the next one anyway.",
                  "She does not sound angry. Somehow that is worse."]]}},
    ],
    'hollow': [
        {'flag': 'seraLamp',
         'needs': ['seraDusk'],
         'party': ['sera'],
         'speaker': 'Sera',
         'gives': 'lamp_key',
         'lines': ["Hold out your hand. No - the other one. You keep that one free. I have been watching.",
                   "It is a lamp key. Every keeper gets one at twelve and loses it by thirty.",
                   "That one was hers. It still turns the ones on the bridge, so do not drop it in the mere.",
                   "{name}. That is the first time I have said your name without the town in front of it."]},

        {'flag': 'seraKeptTwice',
         'needs': ['seraClose'],
         'party': ['sera'],
         'speaker': 'Sera',
         'lines': ["You asked me what I promised. Out on the road, before I told you to ask later.",
                   "Not to let one go out. That is all it is. Nobody ever said why.",
                   "I have added you to it. You do not get a say in that.",
                   "Now stop looking at me like that and go and buy a coat."]},

        {'flag': 'seraKeptQuiet',
         'needs': ['seraKept'],
         'absent': ['seraClose'],
         'party': ['sera'],
         'speaker': 'Sera',
         'lines': ["You never asked me again. Out on the road. What I promised.",
                   "Good. Keep it that way until this is finished.",
                   "Then ask me, and I will still be here, and I will tell you."]},
    ],
}

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
 'barrow2:19,4': {'gear': 'flame_brand'}}


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
        "sign_after": SIGN_AFTER,
        "chest_loot": CHEST_LOOT,
        "boss_victory": BOSS_VICTORY,
        "ending": ENDING,
        "map_beats": MAP_BEATS,
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
