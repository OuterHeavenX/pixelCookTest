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
          'relights': True,   # a keeper's spell: the lantern takes as a side effect
          'mp': 6,
          'power': 0,
          'kind': 'guardAll',
          'target': 'allies',
          'fx': 'holy'},
 'holy': {'name': 'Radiance',
          'relights': True,
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
          'desc': 'Hurls fire at one foe.'},
 'lamp_oil': {'name': 'Lamp Oil',
              'icon': 'i_ether',
              'price': 30,
              'kind': 'light',
              'power': 0,
              'desc': 'Relights the lantern at once.'}}

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
             'cold': True,   # of the barrow or the mere: shrouded while the lantern is out
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
          'cold': True,   # of the barrow or the mere: shrouded while the lantern is out
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
           'ai': [{'w': 14, 'act': 'snuff'}, {'w': 40, 'act': 'attack'},
                  {'w': 35, 'act': 'spell', 'spell': 'ice'},
                  {'w': 25, 'act': 'drain'}]},
 'rimewolf': {'name': 'Rimewolf',
             'cold': True,   # of the barrow or the mere: shrouded while the lantern is out
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
             'cold': True,   # of the barrow or the mere: shrouded while the lantern is out
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
               'cold': True,   # of the barrow or the mere: shrouded while the lantern is out
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
                'ai': [{'w': 18, 'act': 'snuff'}, {'w': 35, 'act': 'attack'},
                       {'w': 40, 'act': 'spell', 'spell': 'ice'},
                       {'w': 25, 'act': 'drain'}]},
 # Under the mere. A drowned keeper still walking his round, the cold that got
 # into a lamp, and the thing the ward was cut to hold - which does not fight
 # you here, because it is not down there any more.
 'drownkeep': {'name': 'Drowned Keeper',
              'cold': True,   # of the barrow or the mere: shrouded while the lantern is out
               'height': 30,
               'sprite': 'e_skeleton_ice',
               'hp': 148,
               'atk': 30,
               'def': 20,
               'mag': 14,
               'spd': 14,
               'exp': 62,
               'gil': 58,
               'weak': 'fire',
               'ai': [{'w': 15, 'act': 'snuff'}, {'w': 55, 'act': 'attack'},
                      {'w': 25, 'act': 'spell', 'spell': 'ice'},
                      {'w': 20, 'act': 'defend'}]},
 'coldwisp': {'name': 'Cold Lamp',
             'cold': True,   # of the barrow or the mere: shrouded while the lantern is out
              'height': 24,
              'sprite': 'e_wisp_ice',
              'hp': 116,
              'atk': 22,
              'def': 12,
              'mag': 34,
              'spd': 22,
              'exp': 58,
              'gil': 44,
              'weak': 'fire',
              'ai': [{'w': 20, 'act': 'snuff'}, {'w': 30, 'act': 'attack'},
                     {'w': 45, 'act': 'spell', 'spell': 'ice'},
                     {'w': 25, 'act': 'drain'}]},
 'walker': {'name': 'The Walker',
            'cold': True,
            'height': 46,
            'sprite': 'e_walker',
            'hp': 1500,
            'atk': 48,
            'def': 26,
            'mag': 32,
            'spd': 15,
            'exp': 900,
            'gil': 700,
            'weak': 'fire',
            'ai': [{'w': 34, 'act': 'attack'}, {'w': 26, 'act': 'snuff'},
                   {'w': 22, 'act': 'spell', 'spell': 'ice'}, {'w': 18, 'act': 'smash'}]},
 'warden': {'name': 'Drowned Warden',
           'cold': True,   # of the barrow or the mere: shrouded while the lantern is out
            'height': 74,
            'sprite': 'e_warden',
            'boss': True,
            'hp': 940,
            'atk': 44,
            'def': 24,
            'mag': 34,
            'spd': 16,
            'exp': 620,
            'gil': 1200,
            'weak': 'fire',
            'ai': [{'w': 18, 'act': 'snuff'}, {'w': 45, 'act': 'attack'},
                   {'w': 25, 'act': 'spell', 'spell': 'ice'},
                   {'w': 18, 'act': 'smash'},
                   {'w': 12, 'act': 'drain'}]},
 'ogre': {'name': 'Ogre Chieftain',
         'cold': True,   # of the barrow or the mere: shrouded while the lantern is out
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
          'ai': [{'w': 14, 'act': 'snuff'}, {'w': 55, 'act': 'attack'},
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
    # Under the mere. Everything here has been down here a long time.
    'mere': [{'w': 24, 'group': ['drownkeep']},
             {'w': 18, 'group': ['coldwisp']},
             {'w': 16, 'group': ['mereling', 'mereling']},
             {'w': 14, 'group': ['drownkeep', 'mereling']},
             {'w': 12, 'group': ['coldwisp', 'coldwisp']},
             {'w': 10, 'group': ['drownkeep', 'drownkeep']},
             {'w': 8, 'group': ['lampwraith', 'coldwisp']},
             {'w': 6, 'group': ['drownkeep', 'lampwraith', 'mereling']}],
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
# Everyone you can talk to, keyed by map. Plain words, short sentences: a
# player should never have to guess what somebody meant. `stages` change what
# they say as the story moves on; `needs` is a list of flags that must be set
# before they are there at all.
NPCS = {
 'mere2': [{'x': 20, 'y': 6, 'sprite': 'sera', 'dir': 'left', 'name': 'Kestrel Vail', 'wander': False,
            'after_flag': 'wardenDown',
            'lines': ['Do not touch the letters. Whatever else you do down here, do not touch them.',
                      'Eleven years. Forty letters. I cut them, the water wears them down, and I cut them again.',
                      'You are Sera. You are grown up.',
                      'I know what I did to you. Say it to me after this, and I will listen to all of it.',
                      'The thing on the other side of these letters is cutting too. It has never stopped.',
                      'Kill it, and I can stop.'],
            'after': ['It is quiet. I forgot rooms could be quiet.',
                      'Take my hand, Sera. I have not let go of anything in eleven years. I am out of practice.']}],
 'hollow_inn': [{'x': 4, 'y': 4, 'sprite': 'merchant', 'dir': 'down', 'name': 'Keeper Ilse', 'wander': False,
                 'service': 'inn',
                 'lines': ['The beds are warm. The lake is not. Fifty gil for the night.'],
                 'stages': [{'when': ['wardenDown'],
                             'lines': ['Fifty gil for the night. The lake is warmer than my beds now. I never thought I would say that.']}]},
                {'x': 8, 'y': 4, 'sprite': 'villager', 'dir': 'down', 'name': 'Grocer Wen', 'wander': False,
                 'service': 'shop', 'shelf': 'hollow',
                 'lines': ['Lamp oil, potions, and whatever the carts bring from the south. Less every month.']}],
 'hollow_armourer': [{'x': 4, 'y': 4, 'sprite': 'villager', 'dir': 'down', 'name': 'Armourer Fenn', 'wander': False,
                      'service': 'shop', 'shelf': 'fenn',
                      'lines': ['Gear made for the cold. It is heavy, and it is worth it.',
                                'Everything on this shelf has been under the ice at least once. So have I.']}],
 'hollow_pip': [{'x': 5, 'y': 3, 'sprite': 'villager', 'dir': 'down', 'name': "Pip's Father", 'wander': False,
                 'lines': ['My boy fell through the ice last winter. Sera Vail went in after him. She did not even take her coat off.',
                           'I light the two lamps outside this door every evening. It is the least I owe her.'],
                 'stages': [{'when': ['wardenDown'],
                             'lines': ['Both my lamps went out on their own. At the same time. At noon.',
                                       'I lit them again. My hands were shaking, but I lit them again.']}]}],
 'hollow_marrow': [],
 'hollow_keepers': [],
 'hollow_watch': [],
 'hollow': [{'x': 21, 'y': 28, 'sprite': 'bram', 'dir': 'down', 'name': 'Bram', 'wander': False, 'recruit': 'bram',
             'lines': ['{name}. I heard what came out of that barrow, and I heard who went in.',
                       'I have not seen you in four hundred miles, and you still walk like a new recruit.',
                       'They light the lamps at noon here. At noon.',
                       'I am not letting you go underground alone twice. Move over.'],
             'after': ['Say the word and I go first. That is my job.',
                       'Have you talked to the lamp girl? She knows something.']},
            {'x': 20, 'y': 9, 'sprite': 'sera', 'dir': 'up', 'name': 'Sera', 'wander': False, 'recruit': 'sera',
             'lines': ['Careful. The lake took two dogs and a cart this week.',
                       'It has not frozen in summer since my grandmother was a little girl.',
                       'You are the one from Rivenbrook. You broke the ward under the barrow.',
                       'No, do not apologise. My family cut that ward. We should have told somebody what it was for.',
                       'I am coming with you. This is my mess as much as yours now.'],
             'after': ['I keep the lamps lit because my mother did, and her mother before her.',
                       'Nobody ever told us why. We just never let one go out.']},
            {'x': 20, 'y': 12, 'sprite': 'sera', 'dir': 'down', 'name': 'Kestrel Vail', 'wander': False,
             'needs': ['wardenDown'],
             'lines': ['The lamps on the road went out one at a time. From here, going south. That is not the wind.',
                       'Something is walking the road and putting them out as it goes.',
                       'Your friend Bram is out there on that road. Go and get him. Then go after it.'],
             'stages': [{'when': ['walkerDown'],
                         'lines': ['It is gone. Not dead. Things that old do not die. But it is nowhere, and nowhere is where it belongs.',
                                   'My daughter says you are the reason. I believe her.']}]},
            {'x': 12, 'y': 19, 'sprite': 'elder', 'dir': 'right', 'name': 'Old Marrow', 'wander': False,
             'lines': ['Lamps at noon, lad. Lamps at noon.',
                       'My father said the day we stop lighting them is the day it comes up.'],
             'stages': [{'when': ['wardenDown'],
                         'lines': ['It came up. My father was right, and I am too old to be happy about it.',
                                   'The lamps went out, the water steamed, and then Kestrel Vail walked up the stairs.']}]},
            {'x': 33, 'y': 22, 'sprite': 'child', 'dir': 'left', 'name': 'Pip', 'wander': True,
             'lines': ['I skated on the lake once. Only once.',
                       'Sera pulled me out and did not even shout at me.'],
             'stages': [{'when': ['wardenDown'],
                         'lines': ['The lake is not frozen any more. It is steaming. In winter.',
                                   'Sera said stay off it. I am staying off it. I am not stupid twice.']}]},
            {'x': 8, 'y': 22, 'sprite': 'guard', 'dir': 'down', 'name': 'Watchwoman', 'wander': False,
             'lines': ['We watch the water, not the road. The road never hurt anybody.'],
             'stages': [{'when': ['wardenDown'],
                         'lines': ['We watch the road now.',
                                   'The lamps on it are going out one at a time, heading south, at walking speed. Your big friend is out there.']}]}],
 'shore': [{'x': 44, 'y': 14, 'sprite': 'bram', 'dir': 'left', 'name': 'Bram', 'wander': False, 'recruit': 'bram',
            'needs': ['roadDark'],
            'lines': ['It walked right past me. Tall. It did not look at me once.',
                      'It put out the lamp in my hand and kept going south. I lit the lamp again. Then I waited for you.',
                      'It is heading for Rivenbrook, {name}. For the wall lamps. Let us go.'],
            'after': ['I go first. That is the job.']}],
 'town_forge': [{'x': 4, 'y': 4, 'service': 'shop', 'shelf': 'forge', 'sprite': 'villager', 'dir': 'down',
                 'name': 'Smith Orla', 'wander': False,
                 'lines': ['I can give you steel. Courage you bring yourself.',
                           "Pell's boy keeps bringing me monster teeth. They are river stones. I keep every one."],
                 'stages': [{'when': ['bossDown'],
                             'lines': ["Bring me the chieftain's armour plate and I will make you something out of it.",
                                       'Whatever broke open in that barrow, you will want better steel than this.']},
                            {'when': ['wardenDown'],
                             'lines': ['That ward held for four hundred years, and somebody cut it with a chisel.',
                                       'I would like to meet the smith who made that chisel.']}]}],
 'town_store': [{'x': 9, 'y': 4, 'service': 'shop', 'shelf': 'store', 'sprite': 'merchant', 'dir': 'left',
                 'name': 'Pedlar Voss', 'wander': False,
                 'lines': ['Buying? I keep my stock here now.',
                           'Too many bandits on the south road for an honest cart.'],
                 'stages': [{'when': ['bossDown'],
                             'lines': ['The south road is quieter since you went down there.',
                                       'Quieter is not the same as safe. The bandits left. Bandits know things.']},
                            {'when': ['wardenDown'],
                             'lines': ['Carts from the north say the lamps on the lake road are going out. One each night, in order.',
                                       'Like somebody walking it. Nobody has seen who.']}]}],
 'town_pell': [{'x': 5, 'y': 3, 'sprite': 'villager', 'dir': 'down', 'name': "Tam's Mother", 'wander': False,
                'lines': ['He is out at the fence again. He says he is guarding it.',
                          'Pell says the south row of the garden is cold. I say the whole south end of town is cold. Nobody listens to me either.'],
                'stages': [{'when': ['bossDown'],
                            'lines': ['He shivers in his sleep now. He never used to.',
                                      'Pell will not say it, so I will. Something came up out of that barrow, and it came here.']},
                           {'when': ['bossDown', 'miraTended'],
                            'lines': ['Your healer sat up with him all night and would not take a coin for it.',
                                      'He slept. First time since the barrow. Tell her that from me.']},
                           {'when': ['wardenDown'],
                            'lines': ['He is himself again. Loud and filthy. Thank goodness.',
                                      'The lamps on the wall went out last night and he saw them come back on. He will tell you about it. At length.']}]}],
 'town_halvard': [],
 'town': [{'x': 20, 'y': 17, 'sprite': 'elder', 'dir': 'down', 'name': 'Elder Halvard', 'wander': False,
           'lines': ['Rivenbrook has stood for a hundred years, {name}.',
                     'Something is moving in the Thornwilds. The scouts say a chieftain.',
                     'And the sign at the old shrine on the south road has been re-carved. Fresh marks, this week. Nobody here did it.',
                     'Take the south gate. And take care.'],
           'stages': [{'when': ['bossDown'],
                       'lines': ['You came back. Sit down, {name}. You look like you saw something down there.',
                                 'Somebody was looking after that seal for four hundred years. Somebody who was not us.',
                                 'And now nobody is.']},
                      {'when': ['bossDown', 'aldricWarned'],
                       'lines': ['Your runner reached us before you did. We lit every lamp on the wall.',
                                 'I do not know why that felt like the right thing to do. It did.',
                                 'Sit down, {name}. You look like you saw something down there.']},
                      {'when': ['wardenDown'],
                       'lines': ['Kestrel Vail. So that is who was cutting the letters.',
                                 'I danced with her once, at a harvest festival, forty years ago. Her hands were cold even then.',
                                 'The wall lamps went out last night, one after another, and then came back. I have stopped asking why.']},
                      {'when': ['walkerDown'],
                       'lines': ['Every lamp in town is lit tonight. Nobody had to be told.',
                                 'Sit down, {name}. Stay a while. You have earned a chair.']}]},
          {'x': 16, 'y': 21, 'sprite': 'villager', 'dir': 'right', 'name': 'Gardener Pell', 'wander': True,
           'lines': ['These beds were carrots last spring.',
                     'The south row will not grow anything this year. Not carrots, not weeds, nothing.',
                     'I put my hand in the soil down there and it is cold as well water. In spring.'],
           'stages': [{'when': ['bossDown'], 'x': 14, 'y': 23, 'wander': False,
                       'lines': ['The fence held. The frost did not go away.',
                                 'It has reached the third row now. My boy will not go near it. Good.']},
                      {'when': ['wardenDown'],
                       'lines': ['Green. Look at it. The south row came back the day you say the lake went quiet.',
                                 'I am not asking how. I am planting carrots.']}]},
          {'x': 24, 'y': 14, 'sprite': 'child', 'dir': 'left', 'name': 'Tam', 'wander': True,
           'lines': ['I saw a wolf as big as a cart!',
                     'Its breath did not steam in the cold. Mum says I made that part up. I did not.'],
           'stages': [{'when': ['bossDown'], 'x': 15, 'y': 23, 'wander': False,
                       'lines': ['Did you SEE it? Was it bigger than the mill?',
                                 'I am not allowed past the fence now. Ma says the ground is wrong.',
                                 'I am cold all the time and I am not even sick.']},
                      {'when': ['bossDown', 'miraTended'], 'x': 15, 'y': 23, 'wander': False,
                       'lines': ['The healer sat with me all night. She did not sing or anything. She just sat there.',
                                 'She said the cold was not in me. It was just visiting. It is looking for something and I am not it.']},
                      {'when': ['wardenDown'], 'x': 24, 'y': 14, 'wander': True,
                       'lines': ['The lamps on the wall went out last night. All at once. Then they came back on.',
                                 'Nobody touched them. I was watching. I am always watching.']}]},
          {'x': 19, 'y': 26, 'sprite': 'guard', 'dir': 'down', 'name': 'Gate Guard', 'wander': False,
           'lines': ['Past this gate is the Thornwilds. Fight or run, but never stand still.',
                     'Press {menu} any time to open your journal.'],
           'stages': [{'when': ['bossDown'],
                       'lines': ['We heard the barrow open from here. Like a door closing, a long way down.',
                                 'Then the frost came up the road to the gate. In spring. I have stopped saying "in spring".']},
                      {'when': ['wardenDown'],
                       'lines': ['The wall lamps went out last night on their own. North to south, one after another.',
                                 'Then they came back on. I have not slept, and I am not going to.']},
                      {'when': ['walkerDown'],
                       'lines': ['I saw it come up the road. I saw what you did at the gate.',
                                 'I will keep the wall lit every night for the rest of my life. That is a promise.']}]},
          {'x': 21, 'y': 26, 'sprite': 'guard', 'dir': 'down', 'name': 'Gate Guard', 'wander': False,
           'lines': ['The Amber Lantern has beds and a shelf of supplies.',
                     'Rest before you go. Only a fool walks the wilds tired.'],
           'stages': [{'when': ['bossDown'],
                       'lines': ['Nobody told us anything. We lit the wall lamps when the frost reached the gate.',
                                 'It seemed like the right thing to do. Nobody could say why.']},
                      {'when': ['bossDown', 'aldricWarned'],
                       'lines': ['Your runner came through at dusk. We had every lamp on the wall lit before dark.',
                                 "Halvard's orders. I would have done it anyway. My hands wanted to."]},
                      {'when': ['wardenDown'],
                       'lines': ['A pedlar from the north says the lamps on the lake road are going out. One each night.',
                                 'Like somebody walking. I keep the wall lit. It is the only thing I know how to do about it.']}]}],
 'inn': [{'x': 4, 'y': 4, 'sprite': 'merchant', 'dir': 'down', 'name': 'Innkeeper Bryn', 'wander': False,
          'service': 'inn',
          'lines': ['Welcome to the Amber Lantern.'],
          'after': ['The room is free tonight. You have earned the bed.',
                    'Do not tell the others, but I have been leaving a lamp lit in the south window.']},
         {'x': 6, 'y': 6, 'sprite': 'villager', 'dir': 'down', 'name': 'Quartermaster', 'wander': False,
          'service': 'shop', 'shelf': 'amber',
          'lines': ['Potions, ethers, and lamp oil. The forge and the store have the rest.']},
         {'x': 12, 'y': 9, 'sprite': 'child', 'dir': 'left', 'name': 'Nib', 'wander': True,
          'lines': ['If you press {cancel} you can run away from a fight! Grown-ups always forget.']}],
 'wild': []}
# What each counter sells, keyed by the shelf an NPC names.
SHOP_STOCK = {
    # The inn keeps what a traveller forgot to pack; the store sells the rest.
    'amber': ['potion', 'hipotion', 'ether', 'phoenix', 'lamp_oil'],
    'store': ['potion', 'hipotion', 'ether', 'bomb', 'lamp_oil'],
    'hollow': ['potion', 'hipotion', 'ether', 'phoenix', 'bomb', 'lamp_oil'],
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
 'l': ['t_lamp', 1, 'lamp'],
 # Under the mere. The same masonry as the barrow, four hundred years wetter.
 '&': ['t_drowned', 0],
 '@': ['t_drownwall', 1],
 '$': ['t_ward', 0, 'ward'],
 '(': ['t_lampsunk', 1, 'lamp'],
 'h': ['t_hatch', 1, 'hatch']}

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
 'U': 'ground',
 '(': 't_drowned',
 '$': 't_drowned',
 'h': 't_snow'}

# Doors that are shut until something is true. The gate, the pass and the
# keepers' hatch were each a hardwired flag test in two builds, in four
# places, which is three too many: a lock is a tile tag, a flag and two things
# to say about it, and that is all it has ever been.
LOCKS = {
    'gate': {'flag': 'barrowKey',
             'open': ['The iron gate is open. Stairs lead down into the dark.'],
             'shut': ['An iron gate, barred and locked.',
                      'The lock is old, but it is not going to give.']},
    'pass': {'flag': 'bossDown',
             'open': ['The west pass. Somebody has been keeping the road clear.'],
             'shut': ['A pass to the west, blocked with thorns and fallen rock.',
                      'Nobody has come through here in a long time.']},
    'hatch': {'flag': 'mereOpened',
              'open': ["The keepers' hatch is open. Cold air comes up out of it."],
              'shut': ['Planks and iron, set flat into the shore.',
                       'There is no handle on this side. It only opens for keepers.']},
}

SIGN_TEXT = {
 'shore': 'THE LAKE ROAD - Do not stop between the lamps.',
 'hollow_keepers': 'KEEPERS OF THE LAKE - Never let a lamp go out. (The rest has worn away.)',
 'town_halvard': "A letter, very old, kept under glass: 'To the Elder of Rivenbrook. Light the south wall every night. You will not be told why. - K. Vail.'",
 'hollow_watch': 'THE WATCH - Lamps lit at dusk, north end first. Count them. If the count is wrong, ring the bell.',
 'hollow': 'HOLLOWMERE - Keep the lamps lit. Stay off the ice.',
 'town': 'RIVENBROOK - The Amber Lantern: rooms and supplies. The forge and the store are up the street.',
 'wild': 'OLD SHRINE - The barrow below is sealed. It was sealed for a reason.',
 'barrow1': 'Carved over the door: THE CHIEFTAIN SLEEPS BELOW. LET HIM SLEEP.',
 'mere1': "Cut over the stairs, in the keepers' handwriting: WE GO DOWN SO IT DOES NOT COME UP."}

# What a sign says once the story has moved past it.
SIGN_AFTER = {
 'wild': 'OLD SHRINE - The barrow below is sealed. The letters are freshly cut. Somebody re-carved this recently.',
 'barrow1': 'Carved over the door: THE CHIEFTAIN SLEEPS BELOW. Under it, newer: HE IS AWAKE. RUN.'}

# --------------------------------------------------------------------- gear
# Three slots per character. `users` is None when anyone can wear it, and the
# stats are flat bonuses folded into the derived stats, so nothing downstream
# has to know equipment exists - a sword just makes atk bigger.
GEAR = {
    # weapons
    'bronze_sword': {'name': 'Bronze Sword', 'slot': 'weapon', 'icon': 'i_sword',
                     'price': 120, 'users': ['aldric'], 'stats': {'atk': 6},
                     'desc': 'A new soldier\'s sword. Simple and solid.'},
    'iron_sword': {'name': 'Iron Sword', 'slot': 'weapon', 'icon': 'i_sword',
                   'price': 480, 'users': ['aldric'], 'stats': {'atk': 15},
                   'desc': 'Heavier than bronze, and it hits harder.'},
    'flame_brand': {'name': 'Flame Brand', 'slot': 'weapon', 'icon': 'i_sword',
                    'price': 1400, 'users': ['aldric'], 'stats': {'atk': 26},
                    'element': 'fire', 'desc': 'The edge burns. Ice creatures hate it.'},
    'oak_staff': {'name': 'Oak Staff', 'slot': 'weapon', 'icon': 'i_staff',
                  'price': 100, 'users': ['lyra', 'mira'], 'stats': {'atk': 2, 'mag': 4},
                  'desc': 'Plain wood, carefully carved.'},
    'moon_rod': {'name': 'Moon Rod', 'slot': 'weapon', 'icon': 'i_staff',
                 'price': 520, 'users': ['lyra'], 'stats': {'atk': 3, 'mag': 12},
                 'desc': 'Cold to hold. Makes spells stronger.'},
    'sage_cane': {'name': 'Sage Cane', 'slot': 'weapon', 'icon': 'i_staff',
                  'price': 560, 'users': ['mira'], 'stats': {'atk': 3, 'mag': 9, 'mp': 10},
                  'desc': 'Carried by healers who travel far.'},

    'iron_halberd': {'name': 'Iron Halberd', 'slot': 'weapon', 'icon': 'i_sword',
                     'price': 620, 'users': ['bram'], 'stats': {'atk': 18, 'def': 2},
                     'desc': 'Long enough to keep trouble away from you.'},
    'warden_staff': {'name': 'Warden Staff', 'slot': 'weapon', 'icon': 'i_staff',
                     'price': 640, 'users': ['sera'], 'stats': {'atk': 4, 'mag': 11, 'def': 3},
                     'desc': 'Made in Hollowmere. The head is a seal, not a decoration.'},
    'rimeblade': {'name': 'Rimeblade', 'slot': 'weapon', 'icon': 'i_sword',
                  'price': 1150, 'users': ['aldric'], 'stats': {'atk': 22},
                  'element': 'ice', 'desc': 'Frost forms on the edge when you draw it.'},
    'frost_pike': {'name': 'Frost Pike', 'slot': 'weapon', 'icon': 'i_sword',
                   'price': 1500, 'users': ['bram'], 'stats': {'atk': 29, 'def': 3},
                   'element': 'ice', 'desc': 'Cold to carry. Colder to be hit with.'},
    'mere_wand': {'name': 'Mere Wand', 'slot': 'weapon', 'icon': 'i_staff',
                  'price': 900, 'users': ['lyra', 'sera'], 'stats': {'atk': 3, 'mag': 17},
                  'desc': 'Made of lake glass, still cold from the water.'},

    # armour
    'leather_vest': {'name': 'Leather Vest', 'slot': 'armour', 'icon': 'i_armor',
                     'price': 90, 'users': None, 'stats': {'def': 4},
                     'desc': 'Better than a shirt.'},
    'chain_mail': {'name': 'Chain Mail', 'slot': 'armour', 'icon': 'i_armor',
                   'price': 420, 'users': ['aldric'], 'stats': {'def': 12, 'spd': -1},
                   'desc': 'Stops a blade. Slows you down a little.'},
    'silk_robe': {'name': 'Silk Robe', 'slot': 'armour', 'icon': 'i_armor',
                  'price': 380, 'users': ['lyra', 'mira'], 'stats': {'def': 6, 'mag': 3},
                  'desc': 'Woven to help a spell flow.'},
    'lake_mail': {'name': 'Lake Mail', 'slot': 'armour', 'icon': 'i_armor',
                  'price': 780, 'users': ['aldric', 'bram'], 'stats': {'def': 16},
                  'desc': 'Scales cut from something that lived in the lake.'},
    'warden_coat': {'name': 'Warden Coat', 'slot': 'armour', 'icon': 'i_armor',
                    'price': 720, 'users': ['lyra', 'mira', 'sera'],
                    'stats': {'def': 11, 'mag': 4},
                    'desc': 'Lined and hooded. Older than anyone who has worn it.'},
    'furs': {'name': 'Thick Furs', 'slot': 'armour', 'icon': 'i_armor',
             'price': 300, 'users': None, 'stats': {'def': 8, 'spd': -1},
             'desc': 'Warm. That is all it needs to be.'},
    'knight_plate': {'name': 'Knight Plate', 'slot': 'armour', 'icon': 'i_armor',
                     'price': 1200, 'users': ['aldric'], 'stats': {'def': 21, 'spd': -2},
                     'desc': 'Like wearing a wall.'},

    # accessories
    'copper_ring': {'name': 'Copper Ring', 'slot': 'trinket', 'icon': 'i_ring',
                    'price': 150, 'users': None, 'stats': {'hp': 24},
                    'desc': 'Warm to wear.'},
    'sage_pendant': {'name': 'Sage Pendant', 'slot': 'trinket', 'icon': 'i_ring',
                     'price': 300, 'users': None, 'stats': {'mp': 14},
                     'desc': 'Gives you a little more magic.'},
    'swift_boots': {'name': 'Swift Boots', 'slot': 'trinket', 'icon': 'i_ring',
                    'price': 450, 'users': None, 'stats': {'spd': 5},
                    'desc': 'Your turn comes a little faster.'},
    'ice_charm': {'name': 'Rime Charm', 'slot': 'trinket', 'icon': 'i_ring',
                  'price': 560, 'users': None, 'stats': {'def': 5, 'mag': 5},
                  'desc': 'Cold to hold, but it keeps the cold out.'},
    'lantern_stone': {'name': 'Lantern Stone', 'slot': 'trinket', 'icon': 'i_ring',
                      'price': 820, 'users': None, 'stats': {'mp': 22, 'mag': 4},
                      'desc': 'Hollowmere keeps its lamps burning with these.'},
    'guard_charm': {'name': 'Guard Charm', 'slot': 'trinket', 'icon': 'i_ring',
                    'price': 700, 'users': None, 'stats': {'def': 7, 'hp': 30},
                    'desc': 'A charm from someone who wanted you home safe.'},
    # Not for sale anywhere. It is given, once, by one person, and it is worth
    # about as much as a shop trinket - the point of it is whose it was.
    # Off the cutting floor. Nobody sells these; there were only ever a few and
    # they were all made for the same job.
    'keeper_coat': {'name': "Keeper's Coat", 'slot': 'armour', 'icon': 'i_armor',
                    'price': 0, 'users': None, 'stats': {'def': 22, 'mag': 8, 'hp': 40},
                    'snuff_shield': 1,   # the first snuff of a fight fails against it
                    'desc': 'Waxed against the coldest water. Keeps a flame alive.'},
    'lamp_key': {'name': "Sera's Lamp Key", 'slot': 'trinket', 'icon': 'i_ring',
                 'price': 0, 'users': ['aldric'], 'stats': {'def': 4, 'mag': 4, 'hp': 20},
                 'relight_free': True,   # relighting costs its wearer no turn
                 'desc': "Her mother's key. It still opens the lamps on the bridge."},
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
    # Steel comes from the forge, not the inn.
    'forge': ['bronze_sword', 'iron_sword', 'oak_staff', 'moon_rod', 'sage_cane',
              'leather_vest', 'chain_mail', 'silk_robe',
              'copper_ring', 'sage_pendant', 'swift_boots'],
    # Fenn sells cold-country work, and things for the two people who walked
    # out of the mist to join you.
    'fenn': ['iron_halberd', 'warden_staff', 'mere_wand', 'rimeblade',
             'lake_mail', 'warden_coat', 'furs',
             'ice_charm', 'lantern_stone', 'swift_boots'],
}

# --------------------------------------------------------------------- ending
# The bosses. A map names one by id and everything that used to be hardwired
# to the chieftain lives here instead: what he says when he stands up, the
# flag his death sets, what that death reveals, which chapter it closes and
# where it puts you afterwards. Chapter two needed a second one, and wiring a
# second one into two builds by hand is exactly how the two builds drift.
BOSSES = {
    'chieftain': {
        'enemy': 'ogre',
        'banner': 'The Ogre Chieftain blocks your path!',
        'flag': 'bossDown',
        'sets': ['sealBroken'],
        'sprite': 'e_ogre',
        'name': 'Ogre Chieftain',
        'starts_dark': True,   # the fight opens with the lantern out; someone has to light it
        'challenge': [
            'The Ogre Chieftain climbs off the stone bed at the bottom of the barrow.',
            'There is no running from this one. Stand and fight?'],
        'victory': [
            'The chieftain falls, and the barrow goes very quiet.',
            'Under the stone bed, something answers. A line of light opens in the floor.',
            'There was a ward carved into that stone. It is cracked now.'],
        'ending': 'one',
        'returns': 'town',
    },
    'drowned': {
        'enemy': 'warden',
        'banner': 'The Drowned Warden rises from the ward!',
        'flag': 'wardenDown',
        'sets': ['mereOpen'],
        'sprite': 'e_warden',
        'name': 'Drowned Warden',
        'challenge': [
            'The water above the ward moves, and something stands up out of it.',
            'It has been cutting the other side of these letters for four hundred years.',
            'There is nowhere to run down here. Stand and fight?'],
        'victory': [
            'The Warden comes apart, and the cutting stops.',
            'For the first time in eleven years, the ward is quiet.',
            'Far above you, very faintly, the lamps of Hollowmere go out one by one.'],
        'ending': 'two',
        'returns': 'hollow',
    },
    # Chapter three's end: the thing that was under both wards, walking up the
    # road toward the biggest light it can see. It starts in the dark only if
    # you put the wall lamps out.
    'walker': {
        'enemy': 'walker',
        'banner': 'The Walker reaches the gate!',
        'flag': 'walkerDown',
        'sets': ['lampsQuiet'],
        'sprite': 'e_walker',
        'name': 'The Walker',
        'dark_if': 'wallDark',
        'challenge': [
            'It comes up the south road at a walking pace. It does not hurry. It never has.',
            'Every lamp it passes goes out. Then it stops in front of you.',
            'This is the gate. There is nowhere else to stand. Fight?'],
        'victory': [
            'The Walker stops. It does not fall. It simply is not there any more.',
            'The cold goes out of the air like a held breath let go.',
            'Behind you, one by one, the lamps on the wall come back on.'],
        'ending': 'three',
        'returns': 'town',
    },
}
# The closing sequences, one per chapter, played once. Each beat is a screen
# of text over a scene; `scene` names what the ending draws behind it.
ENDINGS = {
    # Beats may carry `when` and `absent`: flags that decide whether the beat is
    # shown, so a chapter can close on what this party actually did. Every line
    # is at most 48 characters and every beat at most 4 lines.
    'one': {
        'beats': [
            {'scene': 'barrow', 'lines': [
                'The Chieftain did not live in the barrow.',
                'He was its guard. Somebody put him on that',
                'stone bed and told him to sit, and he sat',
                'there for four hundred years.']},
            {'scene': 'rift', 'when': ['lyraRead'], 'lines': [
                'Lyra read the letters before the floor',
                'split. Forty of them, in groups of four.',
                'Half a sentence, she says. And a name at',
                'the end, like you sign a letter: VAIL.']},
            {'scene': 'rift', 'absent': ['lyraRead'], 'lines': [
                'Cold comes up through the crack in the ward.',
                'Not cellar cold. The cold of somewhere that',
                'has no seasons. The letters were a sentence,',
                'Lyra says. Nobody read it before it broke.']},
            {'scene': 'town', 'when': ['aldricWarned'], 'lines': [
                'You walk back into Rivenbrook at dawn.',
                'Every lamp on the wall is lit. Your runner',
                'did that. Halvard meets you at the well and',
                'does not ask what you saw.']},
            {'scene': 'town', 'absent': ['aldricWarned'], 'lines': [
                'You walk back into Rivenbrook at dawn.',
                'There is frost on the south end of town.',
                'In spring. Halvard meets you at the well and',
                'does not ask what you saw.']},
            {'scene': 'town', 'lines': [
                'The other half of that sentence is carved',
                'under the ice, four hundred miles north, in',
                'a town that lights its lamps at noon. The',
                'woman who kept it went down eleven years ago.']},
        ],
        'title': 'CHAPTER ONE',
        'subtitle': 'THE GUARD OF THE BARROW',
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
            'and who has been cutting the other half',
        ],
        'hook': 'Your journal is saved. Somebody up north is still cutting.',
    },
    'two': {
        'beats': [
            {'scene': 'mere', 'lines': [
                'The ward under the lake is one half of a',
                'sentence. The other half was carved under',
                'a barrow four hundred miles south, and you',
                'broke that one in the spring.']},
            {'scene': 'mere', 'lines': [
                "Kestrel Vail climbs the keepers' stairs",
                'for the first time in eleven years.',
                'She does not say much. She holds her',
                "daughter's hand the whole way up."]},
            {'scene': 'hollow', 'lines': [
                'You come up into Hollowmere at noon, and',
                'Hollowmere is dark. Every lamp is out.',
                '"They never burned to keep it out," Kestrel',
                'says. "They burned to keep it asleep."']},
            {'scene': 'hollow', 'lines': [
                'The lake is open water. In midwinter.',
                'Steaming. Whatever slept under those two',
                'halves of one sentence has had both halves',
                'taken from it in a single year.']},
            {'scene': 'road', 'lines': [
                'South, the lake road goes dark one lamp at',
                'a time. Not all at once. In order, from the',
                'water, at the speed of somebody walking.',
                'Bram is out there with a lit lamp.']},
        ],
        'title': 'CHAPTER TWO',
        'subtitle': 'THE COLD BELOW',
        'credits': [
            'RIVENBROOK',
            'A Tale of the Thornwilds',
            '',
            'Hollowmere, the lake road and the ward below',
            'Monsters modelled in Blender, tiles cooked in Python',
            'One set of rules, two engines, no drift',
            '',
            'Chapter Three: WHAT THE LAMPS WERE FOR',
            'and what walks when they go out',
        ],
        'hook': 'Something is walking the Mere Road south. Bram is on it.',
    },
    'three': {
        'beats': [
            {'scene': 'road', 'lines': [
                'This is what the lamps were for.',
                'It follows light. It always has. The keepers',
                'lit the lamps in a ring around the lake so',
                'it would walk in a circle forever.']},
            {'scene': 'rift', 'lines': [
                'Two wards held it asleep under the ring.',
                'One broke in spring, one in winter. It woke,',
                'and it walked toward the biggest light',
                'it could see. Your town.']},
            {'scene': 'town', 'when': ['wallLit'], 'lines': [
                'You kept the wall lit and met it at the',
                'gate. Every guard on the wall was there.',
                'Halvard was there. Tam was there, behind',
                'his mother, watching. He is always watching.']},
            {'scene': 'town', 'when': ['wallDark'], 'lines': [
                'You put the wall lamps out and met it in the',
                'dark, with one lantern between you. It could',
                'not see the town. It could only see you.',
                'That was the idea.']},
            {'scene': 'town', 'lines': [
                'Tonight every lamp in Rivenbrook is lit.',
                'Nobody had to be told. Sera is showing Tam',
                'how to trim a wick, and Bram is asleep in a',
                'chair by the gate with his boots on.']},
            {'scene': 'barrow', 'lines': [
                'Under the barrow, the crack in the floor',
                'has frozen shut. Somebody has cut a new',
                'letter into the ice. Sera says it is not',
                'one of theirs.']},
        ],
        'title': 'CHAPTER THREE',
        'subtitle': 'WHAT THE LAMPS WERE FOR',
        'credits': [
            'RIVENBROOK',
            'A Tale of the Thornwilds',
            '',
            'Written for one town and the people in it',
            'Rendered in Blender, cooked in Python',
            'Played in a browser and in Godot 4',
            '',
            'Thank you for keeping the lamps lit.',
        ],
        'hook': 'Every lamp in Rivenbrook is lit. Somebody wrote a new letter in the ice.',
    },
}
# The music, as note tables both engines render the same way. Frequencies in
# hertz, 0 for a rest, one entry per step; `lead` carries the tune, `bass` the
# root under it, and `harm` a quiet third voice that fills the middle. Written
# to be listened to for an hour: soft waves, slow harmony, no shrill notes.
def _hz(name):
    names = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
    if name in ('', '.'):
        return 0
    note, octave = name[:-1], int(name[-1])
    semis = names[note[0]] + (1 if len(note) > 1 and note[1] == '#' else -1 if len(note) > 1 else 0)
    return int(round(440.0 * 2 ** ((semis + (octave - 4) * 12 - 9) / 12.0)))


def _notes(text):
    return [_hz(n) for n in text.split()]


THEMES = {
    # Rivenbrook by day: a gentle waltz-like turn, major, unhurried.
    'town': {'bpm': 300,
             'lead': _notes('C5 . E5 . G5 . E5 . D5 . F5 . A5 . F5 . C5 . E5 . G5 E5 C5 . B4 . D5 . B4 . A4 .'),
             'bass': _notes('C3 . . G3 . . C3 . D3 . . A3 . . D3 . C3 . . G3 . . C3 . G2 . . D3 . . A2 .'),
             'harm': _notes('E4 . . . . . . . F4 . . . . . . . E4 . . . . . . . D4 . . . . . . .')},
    # Walking: a steady step, a little wistful, in a minor key.
    'field': {'bpm': 330,
              'lead': _notes('A4 . C5 . E5 . D5 C5 A4 . . . G4 . A4 . F4 . A4 . C5 . B4 A4 G4 . . . E4 . . .'),
              'bass': _notes('A2 . . . E3 . . . A2 . . . G2 . . . F2 . . . C3 . . . G2 . . . E2 . . .'),
              'harm': _notes('C4 . . . . . . . E4 . . . . . . . A3 . . . . . . . B3 . . . . . . .')},
    # Fighting: quick, driving, but rounded so it does not tire the ear.
    'battle': {'bpm': 440,
               'lead': _notes('E5 . E5 D5 E5 . G5 . D5 . D5 C5 D5 . F5 . E5 . E5 D5 E5 G5 A5 G5 E5 D5 C5 B4 A4 B4 C5 D5'),
               'bass': _notes('E3 E3 . E3 E3 . E3 . D3 D3 . D3 D3 . D3 . E3 E3 . E3 E3 . E3 . A2 A2 A2 A2 D3 D3 E3 E3'),
               'harm': _notes('G4 . . . . . . . F4 . . . . . . . G4 . . . . . . . E4 . . . . . . .')},
    # A boss: the battle theme's shape, lower and slower, with a pedal note.
    'boss': {'bpm': 400,
             'lead': _notes('E4 . E4 F4 E4 . D4 . C4 . C4 D4 C4 . B3 . E4 . F4 . G4 . A4 . G4 F4 E4 D4 C4 . B3 .'),
             'bass': _notes('A2 A2 . A2 A2 . A2 . A2 A2 . A2 A2 . A2 . A2 A2 . A2 A2 . A2 . E2 E2 E2 E2 E2 E2 E2 E2'),
             'harm': _notes('C4 . . . . . . . . . . . . . . . C4 . . . . . . . B3 . . . . . . .')},
    # The inn: slow, warm, three notes rocking.
    'inn': {'bpm': 220,
            'lead': _notes('E5 . G5 . A5 . G5 . E5 . D5 . C5 . D5 .'),
            'bass': _notes('C3 . . . F3 . . . G3 . . . C3 . . .'),
            'harm': _notes('G4 . . . A4 . . . B4 . . . G4 . . .')},
    # Hollowmere: cold and slow, a tune that keeps not quite resolving.
    'hollow': {'bpm': 220,
               'lead': _notes('C5 . D5 . B4 . A4 . C5 . E5 . D5 . C5 . A#4 . C5 . A4 . G4 . A4 . C5 . A#4 . . .'),
               'bass': _notes('C3 . . . . . . . D#3 . . . . . . . A#2 . . . . . . . C3 . . . G2 . . .'),
               'harm': _notes('G4 . . . . . . . G4 . . . . . . . F4 . . . . . . . E4 . . . . . . .')},
    # The barrow and the halls under the lake: low, slow, and sparse.
    'barrow': {'bpm': 190,
               'lead': _notes('G4 . . . A#4 . . . A4 . . . F4 . . . G4 . . . C5 . A#4 . A4 . G4 . E4 . . .'),
               'bass': _notes('G2 . . . G2 . . . A#2 . . . A#2 . . . A2 . . . A2 . . . F2 . . . F2 . F2 .'),
               'harm': _notes('. . . . D4 . . . . . . . C4 . . . . . . . D#4 . . . . . . . C4 . . .')},
    # The endings: slow, open, resolving at last.
    'ending': {'bpm': 170,
               'lead': _notes('C5 . . . E5 . . . G5 . . . E5 . . . F5 . . . E5 . . . D5 . . . C5 . . .'),
               'bass': _notes('C3 . . . . . . . G2 . . . . . . . F2 . . . . . . . C3 . . . . . . .'),
               'harm': _notes('G4 . . . . . . . B4 . . . . . . . A4 . . . . . . . E4 . . . . . . .')},
}

# The lantern: the one rule every fight shares. The party carries one lamp,
# lit or dark. Wild things do not care. Anything of the cold - the barrow's
# dead, the mere's keepers, the two wardens - is shrouded while it is dark:
# it takes less damage and its blows go through armour. Some of them act to
# snuff it; any hero can spend a turn to light it, lamp oil lights it at once,
# and a keeper's spell lights it in passing.
LANTERN = {
    'shroud': 0.6,        # damage a cold enemy takes while the lantern is out
    'pierce': True,       # a cold enemy's blows ignore defence while it is out
}

# Which picture a map wears, by flag: the last variant whose flags are all set
# wins, and a map with none listed wears its plain picture. The town frosts
# from the south end once the seal is broken.
PICTURE_VARIANTS = {
    'town': [{'when': ['sealBroken'], 'variant': 'cold'},
             {'when': ['wildDark'], 'absent': ['walkerDown'], 'variant': 'night'}],
    'shore': [{'when': ['roadDark'], 'variant': 'night'}],
    'wild': [{'when': ['roadDark'], 'absent': ['walkerDown'], 'variant': 'night'}],
}
# Beats that fire the first time the party walks onto a map, once each. `needs`
# is every flag that must already be set, `absent` every flag that must not be,
# and `leaves` is who walks out of the party at the end of it.
MAP_BEATS = {
    # Chapter one's three choices, one per hero. None of them changes where you
    # go; each changes what the town and the ending know.
    'barrow1': [
        {'flag': 'aldricGate',
         'party': ['aldric'],
         'lines': ["The sign at the mouth of the barrow has been re-carved. This week. The cuts are still pale.",
                   "Somebody knows this place is open, and did not tell Rivenbrook.",
                   "Aldric looks back up the road. Halvard said take care. He did not say send word."],
         'choice': {
             'options': ['Send a runner back with word', 'Go down now'],
             'sets': ['aldricWarned', 'aldricHurried'],
             'replies': [
                 ["Aldric writes three lines for the boy at the gate and adds a fourth: light the wall.",
                  "He does not know why he adds it. His hands wanted to."],
                 ["Every hour spent up here is an hour that chisel down there goes unanswered.",
                  "You go down."]]}},
    ],
    'barrow2': [
        {'flag': 'lyraLetters',
         'party': ['lyra'],
         'speaker': 'Lyra',
         'lines': ["Wait. Before anyone touches it. Those are letters, not a pattern.",
                   "Forty of them, in groups of four. It is a sentence, {name}. Half of one.",
                   "Give me one minute with it. Then do what you came to do."],
         'choice': {
             'options': ['Let her read', 'We are not here to read'],
             'sets': ['lyraRead', 'lyraHurried'],
             'replies': [
                 ["She reads with her fingers, lips moving, and stops at the last four.",
                  "\"There is a name,\" she says. \"VAIL. Whoever carved this signed it.\"",
                  "She looks like someone who has just read the first half of a letter addressed to her."],
                 ["\"Fine.\" She steps back. \"But once it is broken, nobody will ever know what it said.\"",
                  "She is right. You do it anyway."]]}},
    ],
    'town': [
        {'flag': 'miraTam',
         'needs': ['bossDown'],
         'party': ['mira'],
         'speaker': 'Mira',
         'lines': ["Pell's boy. Tam. He has been shivering since the night the barrow opened, and he is not sick.",
                   "I can sit with him tonight. It costs us the night, and I do not think I can help him.",
                   "I think I should be there anyway. You decide where we sleep, {name}."],
         'choice': {
             'options': ['Stay the night', 'We leave at dawn'],
             'sets': ['miraTended', 'miraHurried'],
             'replies': [
                 ["She sits with him until the frost melts off the inside of the window.",
                  "\"It is not in him,\" she says in the morning. \"It was visiting. It is looking for something, and he is not it.\""],
                 ["\"Then I will sit with him until dawn,\" she says, \"and leave when you do.\"",
                  "She does. You do not ask what she saw."]]}},
        # Chapter three: it is coming for the wall lamps. Aldric decides.
        {'flag': 'gateStand',
         'needs': ['wildDark'],
         'absent': ['walkerDown'],
         'party': ['aldric'],
         'lines': ["Every lamp on the wall is lit. You can see them from a mile down the road.",
                   "So can it. It follows light. That is what it does.",
                   "Aldric looks up at the wall, then down the dark road. There is time for one order."],
         'choice': {
             'options': ['Keep the lamps lit. We stand at the gate.', 'Put the lamps out. Let it pass in the dark.'],
             'sets': ['wallLit', 'wallDark'],
             'replies': [
                 ["\"Keep them lit,\" Aldric says. \"Every one. If it wants light, it comes to us.\"",
                  "The guards spread out along the wall. Nobody argues."],
                 ["\"Put them out,\" Aldric says. \"All of them. It cannot want what it cannot see.\"",
                  "The wall goes dark, lamp by lamp. It is very quiet. Then you light your own lantern, and wait."]]}},
    ],
    'shore': [
        {'flag': 'bramHoldsRoad',
         'needs': ['bossDown'],
         'party': ['bram', 'sera'],
         'speaker': 'Bram',
         'leaves': 'bram',
         'lines': ["Hold on. Look at the lamps. Every one of them is lit, all the way back.",
                   "Somebody walks this road at dusk to light them. Every night. Alone.",
                   "If the road goes dark, Hollowmere goes dark, and then it is just you down there.",
                   "So I am staying up here to keep them lit. No, do not argue.",
                   "{name}. I have followed you into one hole in the ground already.",
                   "Let me be useful somewhere you can still find me."]},
        # Sera, in four parts, spread over the walk between Hollowmere and the
        # water. The first two come from having her with you and coming back
        # this way, the third asks you a question, and the fourth is the answer
        # she would not give in the first.
        {'flag': 'seraDusk',
         'needs': ['bramHoldsRoad'],
         'party': ['sera'],
         'speaker': 'Sera',
         'lines': ["He is going to light every one of them, you know. All the way to the bridge.",
                   "My mother did that. Not the whole road. Ours, and the two on either side, because the Marrows are old.",
                   "I thought it was a chore. Then she disappeared that winter, and I went out at dusk anyway.",
                   "That is when I understood. It was not a chore. It was a promise.",
                   "Ask me what I promised. No. Ask me later, when we know what is under the water."]},
        {'flag': 'seraWater',
         'needs': ['seraLamp'],
         'party': ['sera'],
         'speaker': 'Sera',
         'lines': ["Stop a moment. Listen to the ice.",
                   "It makes that sound when it is about to break. My grandmother said it was the lake clearing its throat.",
                   "We are going down there soon, and one of us is going to say something stupid.",
                   "So it might as well be tonight. Sit with me until the lamps catch."],
         'choice': {
             'options': ['Sit with her', 'There is no time'],
             'sets': ['seraClose', 'seraKept'],
             'replies': [
                 ["She does not say anything else for a long time. Neither do you.",
                  "The lamps catch, one after another, all the way down to the bridge.",
                  "\"There,\" she says. \"Now I have kept it twice.\""],
                 ["\"No,\" she agrees. \"There is not.\"",
                  "She stands up, walks on ahead of you, and lights the next one anyway.",
                  "She does not sound angry. Somehow that is worse."]]}},
        # Chapter three: the road is dark.
        {'flag': 'roadWalked',
         'needs': ['roadDark'],
         'lines': ["Every lamp on the lake road is out.",
                   "The snow gives off a little light of its own. That is all there is.",
                   "Somewhere ahead of you, Bram is on this road with a lit lamp."]},
    ],
    'hollow': [
        {'flag': 'seraLamp',
         'needs': ['seraDusk'],
         'party': ['sera'],
         'speaker': 'Sera',
         'gives': 'lamp_key',
         'lines': ["Hold out your hand. No, the other one. You keep that one free. I have been watching.",
                   "It is a lamp key. Every keeper gets one at twelve and loses it by thirty.",
                   "That one was my mother's. It still opens the lamps on the bridge, so do not drop it in the lake.",
                   "{name}. That is the first time I have said your name without the town in front of it."]},
        {'flag': 'seraKeptTwice',
         'needs': ['seraClose'],
         'party': ['sera'],
         'speaker': 'Sera',
         'lines': ["You asked me what I promised. Out on the road, before I told you to ask later.",
                   "Never to let one go out. That is all it is. Nobody ever said why.",
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
        # And then she takes you down. This is the beat the whole chapter has
        # been walking toward, and it is also the lock on the keepers' hatch:
        # nothing else in the game sets mereOpened.
        {'flag': 'mereOpened',
         'needs': ['seraWater'],
         'party': ['sera'],
         'speaker': 'Sera',
         'lines': ["Come down to the shore. Past the lamps. Right down to the ice.",
                   "There is a hatch under the snow with a keeper's lock on it. Nobody who was not a keeper has ever opened it.",
                   "My mother went through it eleven years ago to re-cut the ward.",
                   "The town buried an empty box that winter and told me the cold took her. I was twelve. I believed them for about four years.",
                   "You have her key. I gave it to you, and I knew exactly what I was doing.",
                   "Open it."]},
        # Chapter three opens here.
        {'flag': 'roadDark',
         'needs': ['wardenDown'],
         'speaker': 'Kestrel Vail',
         'lines': ["Listen to me. The lamps on the road went out one at a time, from here going south.",
                   "That is not the wind. Something is walking the road and putting them out as it goes.",
                   "It is the thing that was under the wards. It is awake, and it is following the light.",
                   "Your friend Bram is out on that road. Go and get him. Then go after it."]},
    ],
    'hollow_keepers': [
        # Sera's house. Her mother's house.
        {'flag': 'seraHome',
         'party': ['sera'],
         'speaker': 'Sera',
         'lines': ["This is my house. It was my mother's, and her mother's before that.",
                   "Four lamps, one in each corner. A keeper's house is never dark. Not for one minute, not ever.",
                   "That chest by the wall has been locked since I was twelve. Go on. You have the key.",
                   "I could never make myself open it."]},
    ],
    'wild': [
        # Chapter three: the wilds at night, and the wall lamps in the distance.
        {'flag': 'wildDark',
         'needs': ['roadDark'],
         'lines': ["The Thornwilds are dark. Nothing moves.",
                   "Far to the north, over the trees, you can see the lamps on the wall of Rivenbrook. They are lit.",
                   "That is where it is going."]},
    ],
    'mere1': [
        {'flag': 'mereLamps',
         'speaker': 'Sera',
         'lines': ["Lamps. The whole length of the hall. Every one of them lit.",
                   "Nobody has been down here in eleven years, {name}.",
                   "So somebody has been lighting these."]},
    ],
    'mere2': [
        {'flag': 'cuttingFloor',
         'lines': ["The room at the bottom of the keepers' stairs is not a tomb.",
                   "It is a workshop. Stone chips on the floor. A whetstone worn down in the middle.",
                   "A tally scratched into the wall in groups of four. The groups go on and on."]},
    ],
}
# Keyed "<map>:<x>,<y>".
CHEST_LOOT = {'town:4,5': {'item': 'potion', 'n': 2},
 'town:35,24': {'item': 'ether', 'n': 1},
 'inn:11,2': {'gil': 120},
 'town_pell:6,2': {'item': 'potion', 'n': 2},
 'town_halvard:6,2': {'item': 'ether', 'n': 2},
 'hollow_inn:10,2': {'gil': 260},
 'hollow_marrow:5,2': {'item': 'lamp_oil', 'n': 3},
 'hollow_keepers:3,2': {'item': 'lamp_oil', 'n': 4},
 'hollow_keepers:6,2': {'gil': 400},
 'hollow_pip:5,2': {'item': 'potion', 'n': 3},
 'hollow_watch:6,2': {'item': 'phoenix', 'n': 1},
 'wild:43,39': {'item': 'hipotion', 'n': 2},
 'wild:6,12': {'gear': 'copper_ring'},
 'wild:51,5': {'item': 'potion', 'n': 3},
 'wild:13,36': {'gil': 220},
  # Under the mere.
 'mere1:6,6': {'gear': 'lantern_stone'},
 'mere1:34,6': {'item': 'hipotion', 'n': 3},
 'mere2:7,5': {'gear': 'keeper_coat'},
 'mere2:28,5': {'gil': 900},
 # The barrow. The gate key is a flag rather than a bag item: it opens one
 # door and then it has done its job.
 'barrow1:6,6': {'gear': 'guard_charm'},
 'barrow1:30,16': {'item': 'hipotion', 'n': 2},
 'barrow1:33,6': {'flag': 'barrowKey',
                  'text': 'A heavy iron key, green with age.'},
 'barrow2:4,6': {'gear': 'knight_plate'},
 'barrow2:32,22': {'gil': 600},
 'barrow2:19,4': {'gear': 'flame_brand'}}


# The ending draws its lines from x=20 in a 320-wide screen, in a 6-pixel
# monospaced font: 50 characters reach the right edge exactly and 48 leaves a
# margin. Chapter one shipped with lines of 66 and the ends of seven of them
# have been off the side of the screen ever since - silently, because nothing
# anywhere measures this.
ENDING_LINE_MAX = 48

# And the box below them starts at y=116 in a 180-tall screen, on a 14-pixel
# line pitch: four lines reach y=178 and a fifth is off the bottom.
ENDING_BEAT_LINES = 4


def _check_endings():
    bad = []
    for name, end in ENDINGS.items():
        for beat in end["beats"]:
            if len(beat["lines"]) > ENDING_BEAT_LINES:
                bad.append("ending %s: a beat has %d lines, %r"
                           % (name, len(beat["lines"]), beat["lines"][0]))
            for line in beat["lines"]:
                if len(line) > ENDING_LINE_MAX:
                    bad.append("ending %s: %d chars, %r" % (name, len(line), line))
    if bad:
        raise SystemExit("ending line too long for the screen:\n  "
                         + "\n  ".join(bad))


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
    _check_endings()
    payload = {
        "spells": SPELLS,
        "items": ITEMS,
        "classes": CLASSES,
        "enemies": ENEMIES,
        "encounters": ENCOUNTERS,
        "npcs": NPCS,
        "picture_variants": PICTURE_VARIANTS,
        "lantern": LANTERN,
        "themes": THEMES,
        "shop_stock": SHOP_STOCK,
        "legend": LEGEND,
        "locks": LOCKS,
        "underlay": UNDERLAY,
        "sign_text": SIGN_TEXT,
        "sign_after": SIGN_AFTER,
        "chest_loot": CHEST_LOOT,
        "bosses": BOSSES,
        "endings": ENDINGS,
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
