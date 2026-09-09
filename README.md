# Rivenbrook — a tale of the Thornwilds

A small pixel-art RPG, built twice from one set of cooked assets and one set of
rules: as a **single-file browser build** and as a **Godot 4 project**.

**Play in a browser** — open `index.html`. No server, no build step, no
dependencies.

    open index.html          # macOS
    xdg-open index.html      # Linux

**Open in Godot** — Godot 4.3 or newer (verified on 4.5), `Import` the `godot/`
folder, and press play. Same game, same art, same numbers.

## What's in it

- **The town of Rivenbrook** — a walkable map with houses, a plaza and well, a
  hedged garden, a pond, chests, and seven townsfolk who wander and talk.
- **The Amber Lantern** — an interior you can enter through the inn door, with an
  innkeeper who restores the party for 50 gil and a quartermaster who sells items.
- **The Thornwilds** — leave by the south gate into open country: roads, a river
  with bridges, woods, boulders, and random encounters in the grass.
- **Monsters sized against the party** — each one's data says how tall it should
  stand in game pixels, next to a hero drawn 32 tall, so a cave bat is a cave
  bat and only the chieftain is bigger than you.
- **ATB combat** in the Final Fantasy IV–VI mould: gauges fill in real time and
  freeze while a command window is open. Fight / Magic / Item / Guard / Run,
  target selection, criticals, elemental weaknesses, damage numbers, EXP, gil,
  level-ups, and spells learned on level.
- **A three-hero party** — Aldric the Knight, Lyra the Black Mage, Mira the White
  Mage — each with their own growth curve and spell list.
- **The Barrow** — two floors of dark stone under the shrine in the south-east:
  a gallery ringed with chambers, an iron gate that wants a key, and a stair
  down to the chieftain's floor. Its own monsters (Barrow Guards and Wights),
  its own encounter table, its own theme, and its own night sky over every
  fight. The three best pieces of gear are down there.
- **An ogre chieftain** on the bier at the bottom of the barrow.
- **An ending, and a cliffhanger.** The chieftain is not the barrow's tenant, he
  is its lock, and killing him breaks a ward that was there for a reason. The
  chapter closes with a staged sequence, a card, credits and a hook - and then
  hands you back a saved game in a Rivenbrook that reacts, a shrine sign
  someone has re-cut, and a rift in the barrow floor you have nothing to fight
  with yet.
- **A stylised menu** (items, magic, status, save), a title screen, a game over
  screen, `localStorage` saves, and a small chiptune soundtrack.

## Controls

| Key | Action |
| --- | --- |
| Arrows / WASD | Move, and move the cursor in menus |
| Z / Enter / Space | Confirm, talk, examine |
| X / Backspace | Cancel, and hold to dash on the field |
| C / Esc / Shift | Open the menu |
| M | Mute |

Touch controls appear automatically on touch devices. Movement is a floating
stick: it has no fixed home, so a thumb landing anywhere on the left of the
screen becomes its centre, and it fades out again on release rather than
sitting on top of the game. It reads all eight directions, with a small dead
zone so a resting thumb does not walk. A, B and the menu button stay put on
the right, and work at the same time as the stick.

## Equipment

Three slots each - weapon, armour, trinket. A piece's stats are folded straight
into the derived stats in `refreshStats`, so nothing downstream knows equipment
exists: a sword just makes `atk` bigger, and every damage formula, ATB rate and
HP bar picks it up for free. Swapping moves current HP and MP with the maximum,
so a +30 HP charm is felt now rather than banked for the next level.

`users` decides who can wear what, the quartermaster grew an **Armoury** tab
that quotes the stat change for whoever can actually use the piece, and an
elemental weapon carries its element into a physical swing - which is why the
Flame Brand is worth the walk if the thing in front of you hates fire. The
three best pieces are not for sale; they are in chests off the main path.

`datacook` refuses to build if a chest_loot entry names a tile with no chest
painted on it - loot nobody can reach is worse than no loot. `mapcook` goes
further and walks every map: from the spawn tile, every warp, chest, sign and
boss has to be reachable on foot once the locked gates are open, and the key
that opens a gate has to be reachable while they are still shut. A key behind
the door it unlocks makes a dungeon unwinnable, and playing the happy path
never finds that.

Menus are tapped, not walked to. The battle commands, the spell and item
lists, the combatants during targeting, and the field menu's column all
register themselves as screen rectangles while they draw, and a tap is matched
against them on the next frame - so hitting Magic means putting a thumb on
Magic, not steering a cursor to it. Keys and taps go through the same
functions, so neither can drift away from the other.

## The ending

`tools/datacook.py` holds the whole closing sequence as data - the beats and
their scenes, the card, the credits and the hook - so both runtimes play the
same chapter from one script and neither one restates a line of it. The world
after it is flag-driven: `bossDown` swaps in `after` dialogue for the townsfolk
and re-cut text for the signs, `sealBroken` turns the ward tile in the barrow
floor into a rift. The journal is written *before* the credits roll, so nothing
in the sequence can cost anyone their save.

## Two builds, one source of truth

The rules live in `tools/datacook.py` and are cooked to `assets/gamedata.json`:
spells, items, equipment, class growth, monsters, encounter tables, townsfolk,
the tile legend and the loot. The browser build inlines that file at build time; the
Godot project loads it at startup. Neither runtime restates a single number, so
balance is changed in exactly one place.

The same goes for the art and the maps — one atlas, one map file, both builds.

| | Browser build | Godot build |
| --- | --- | --- |
| Entry point | `index.html` (everything inlined) | `godot/project.godot` |
| Source | `src/game.js`, `src/font.js` | `godot/scripts/*.gd` |
| Rendering | one 2D canvas at 320x180 | one `Node2D._draw()` at 320x180 |
| Text | glyph sheet built from `FONT` | same glyphs, from `font.json` |
| Audio | WebAudio square-wave synth | generated `AudioStreamWAV` buffers |
| Saves | `localStorage` | `user://rivenbrook_save.json` |

## Where the art comes from

Every sprite in the game is generated by **spritecook**, the asset kitchen in
`tools/`. There is no binary art checked in that wasn't cooked from source, and
no runtime drawing of game art — `assets/atlas.png` is the only texture.

    python3 tools/spritecook.py                 # atlas.png + atlas.json
    python3 tools/spritecook.py --sheet out.png # zoomed contact sheet of every sprite
    python3 tools/mapcook.py                    # maps.json
    python3 tools/datacook.py                   # gamedata.json
    python3 tools/godotcook.py                  # stage assets under godot/
    python3 tools/build.py                      # run every cook, emit index.html

`spritecook` needs nothing but the Python standard library — the PNG encoder is
built on `zlib` in `tools/spritecook/imaging.py`.

The two battle backdrops are the one exception to "drawn a pixel at a time":
they are modelled and rendered in **Blender**, because receding mountain
ranges are about silhouette and overlap, which a real camera solves and hand
plotting does not. Every material is a flat emission shader, so the render
comes back as graphic colour rather than photographic shading, and
`tools/pixelate.py` then median-cuts it down to 28 colours with hard edges.
The finished PNGs land on the same atlas as everything else, so the game just
draws a sprite named `bg_dusk` or `bg_night`.

    pip install bpy==4.5.13                     # Blender as a Python module
    python3 tools/blender/backdrop.py           # art/blender/backdrop_*.png
    python3 tools/pixelate.py                   # art/backdrops/backdrop_*.png
    python3 tools/build.py                      # onto the atlas, into the game

Both intermediate renders are checked in, so a clone without Blender still
builds.

Six of the monsters are modelled and rendered there too. A slime is a sphere
catching a light, a bat's wings fold over each other, an ogre is mass - those
are things a renderer knows and a rectangle does not. The models are built from
primitives (`ball`, `limb`, `cone`), lit by a key, a fill and a rim plus an
ambient sky, and shot through an orthographic camera so a 24-pixel monster gets
no perspective distortion across its own body.

    python3 tools/blender/enemies.py            # art/enemies/raw/e_*.png at 8x
    python3 tools/spritedown.py                 # art/enemies/e_*.png, sprite size

`spritedown` crops each render to what it actually drew, fits it to the sprite
box, hard-thresholds the alpha so the silhouette stays crisp, lifts contrast
and saturation - a soft render averaged to 24 pixels is otherwise a wash of
identical mid-tones - median-cuts it to 14 colours, and puts the ink outline
back on. The outline is not decoration: it is what lets a monster read against
grass, flagstones and a night sky alike.

The goblin, the bandit and the skeleton stay hand-plotted. The pattern is
consistent - a render wins where the character *is* its volume and loses on
thin figures whose legibility comes from hard black edges around small
features, which is exactly what averaging a render down destroys.
`tools/spritecook/rendered.py` holds that list, so switching one over is a
one-line change.

| Piece | What it does |
| --- | --- |
| `tools/spritecook/imaging.py` | RGBA raster, PNG encoder, shelf packer |
| `tools/spritecook/palette.py` | the shared colour vocabulary |
| `tools/spritecook/tiles.py` | terrain, buildings, props, furniture |
| `tools/spritecook/chars.py` | one parametric humanoid → party, townsfolk, walk cycles |
| `tools/spritecook/beasts.py` | monsters and item icons |
| `tools/spritecook/backdrops.py` | carries the rendered backdrops onto the atlas |
| `tools/blender/backdrop.py` | builds and renders the battle backdrops in Blender |
| `tools/pixelate.py` | quantises a render into a small palette with crisp edges |
| `tools/blender/enemies.py` | models and renders six of the monsters |
| `tools/spritedown.py` | takes a render down to sprite size, outline and all |
| `tools/spritecook/rendered.py` | carries the rendered monsters onto the atlas |
| `tools/mapcook.py` | the five maps, painted with drawing ops and walked for reachability |
| `tools/datacook.py` | the rules: spells, items, growth, monsters, loot |
| `tools/godotcook.py` | stages the cooked assets and the font under `godot/` |
| `tools/build.py` | runs every cook, inlines the atlas into `index.html` |
| `tools/gdlint.py` | cross-reference check for the Godot scripts |
| `tools/godotsmoke.py` | boots the Godot build in the engine and plays it |

## Layout

    index.html          the built browser game (everything inlined)
    src/game.js         browser source: field, battle, menus, audio
    src/font.js         5x7 bitmap font
    src/index.html      page shell the build fills in
    godot/              the Godot 4 project
      project.godot     autoloads, 320x180 viewport, nearest-neighbour filtering
      scenes/Main.tscn  a single Node2D; everything else is built in code
      scripts/          Art, Dat, Gs, Snd, Inp autoloads + the five game modes
      scripts/Smoke.gd  the smoke test that drives the game (see godotsmoke.py)
      assets/           staged copies of the cooked atlas, maps, rules, font
    assets/             cooked atlas.png, atlas.json, maps.json, gamedata.json
    art/blender/        raw Blender renders of the battle backdrops
    art/backdrops/      the same renders quantised to the game palette
    art/enemies/raw/    Blender renders of the monsters, at 8x sprite size
    art/enemies/        the same renders taken down to sprite size
    art/godot/          screenshots of the Godot build, taken by the smoke test
    tools/              spritecook, mapcook, datacook, godotcook, build, gdlint
    tools/blender/      the Blender scene for the battle backdrops

Edit anything under `src/`, `godot/scripts/` or `tools/`, then re-run
`python3 tools/build.py`.

## How each build was checked

The browser build was driven end to end in Chromium — title, town, inn, shop,
dialogue, warps, random and boss encounters, magic, items, revival, running,
victory, defeat, save and load — plus a 2,600-input randomized soak across every
battle phase.

The Godot project is run, by the engine, on every check:

    python3 tools/godotsmoke.py          # godot on PATH, or $GODOT, or --godot

It imports the project, boots the real `Main.tscn`, and plays it - New Game,
the field, the equip screen, the shop and its armoury, an encounter through
the command window to a resolved attack, and a save/load round trip - pressing
real keys and asserting on the game's own state at each step. It screenshots
every mode into `art/godot/`, so the two builds can be compared frame by frame.
Rendering needs an OpenGL context, so on a headless machine it wraps the run in
`xvfb-run` with Mesa's software rasteriser: slow, but it draws what a GPU would.

This was worth doing. The project had passed `tools/gdlint.py` and a GDScript
grammar parse for its whole life, and the engine still refused to load half of
it: `var x := max(a, b)` infers Variant, which Godot 4 treats as a fatal parse
error, and eighteen declarations across five scripts did exactly that. gdlint
now knows about that class of mistake, and is self-tested against it, but the
lesson is the obvious one - a linter is not an engine.

`tools/gdlint.py` still runs first and is still worth having: it resolves every
`Object.member` reference against the script that owns it, flags same-block
redeclarations, catches Variant-inferring declarations, and checks that every
sprite the scripts ask for exists in the atlas. It is a second of work against
a minute of engine boot.

## A note on tooling

The task asked for assets via *Spritecook*. That connector is installed on the
account but was **not enabled for the session** this was built in, so none of
its tools were reachable. Rather than hand-wave the art, `tools/spritecook.py`
is a working asset generator built for this project that fills the same role:
one command cooks every sprite in the game from source, with no dependencies
beyond the Python standard library.

### Wiring up SpriteCook

There are two ways to reach it, and either one is enough:

1. **The account connector.** SpriteCook is already installed on the account;
   it just has to be enabled for the individual chat, in that chat's connector
   settings. Nothing else is needed - the authorization already exists.
2. **A project MCP server.** If you want SpriteCook in an editor that has no
   connector (Cursor, VS Code, a local Claude Code), point it at
   `https://mcp.spritecook.ai/mcp/claude` and set **no** `Authorization`
   header, so the client can run OAuth (dynamic client registration, S256
   PKCE) instead of needing an API key.

   Two traps are worth writing down. Pinning a bearer token in `headers`
   disables the OAuth fallback, turning a missing token into a hard 401
   instead of a sign-in prompt. And the route matters: `api.spritecook.ai/mcp/`
   answers, but its protected-resource metadata declares
   `https://mcp.spritecook.ai/mcp/openai`, so a client that validates RFC 9728
   metadata rejects the mismatch. The `/mcp/claude` route's metadata is
   self-consistent.

### Bringing SpriteCook art into the game

`art/spritecook/` holds the generated source PNGs and a `MANIFEST.json` saying
which game sprite names each file supplies and how tall it should end up.
`tools/spritecook/imported.py` crops each file to its silhouette, area-averages
it down to that height with a hard alpha threshold so the edges stay crisp, and
packs it into the same atlas as the procedural art. **A name imported this way
overrides the procedural sprite of that name**, which is what lets the cast be
upgraded one character at a time.

Two things were settled by measurement rather than taste:

- **Characters land at 24x32, two tiles tall.** SpriteCook returns roughly
  38x64 of usable character inside a 66x66 image. Scaled to 24x32 the helm,
  plume, cape and face all survive; at 18x24 the face disappears entirely, and
  at native size the character is four tiles tall against 16px terrain.
- **Nothing assumes a fixed sprite size any more.** Both runtimes anchor
  sprites on the feet (`sprFoot` / `Art.spr_foot`) and pick a zoom with
  `scaleFor` / `Art.scale_for`, so a 24x32 generated character and a 16x24
  procedural townsperson stand correctly side by side on the same tile.

**The party of three is generated art; everyone else is procedural.** Aldric
has a real four-direction walk cycle (left mirrors right); Lyra and Mira only
ever appear in battle and in menu portraits, so their front-facing idle stands
in for every field direction. All three share front-facing battle poses, since
SpriteCook animates attack and hurt from the front idle - mixing a side-view
stance with a front-view swing would have the character spin to face the camera
mid-attack.

Two details in the importer matter more than they look. Every frame in a group
is cropped to **one shared bounding box**, because cropping each frame to its
own silhouette makes the sprite jitter as the crop shifts underneath it. And
field and battle poses are **separate groups**, so Aldric's extended sword does
not widen the box that his walk cycle is scaled against.

Costs, for planning: a base character is 12 credits and each animation 16-20,
plus a 12-credit prep step for every viewing angle beyond the front. Aldric's
full set came to about 180 and each battle-only mage about 60. A complete cast
replacement - eight characters and seven monsters - would run well past 1,300,
so the party is where the credits go.

Once either route is live the art can be regenerated through SpriteCook. The
swap is deliberately cheap: both runtimes look sprites up by name from
`atlas.json` and neither hardcodes a pixel coordinate, so replacing the art
means replacing the atlas and its frame table, not touching game code. The
names the game asks for are:

| Sprite | Names |
| --- | --- |
| Walk cycles | `<char>_<down\|up\|left\|right><0..2>` for each of the 8 characters |
| Battle poses | `<hero>_ready`, `<hero>_attack`, `<hero>_hurt` |
| Monsters | `e_slime`, `e_goblin`, `e_wolf`, `e_bat`, `e_wisp`, `e_bandit`, `e_ogre` |

`tools/spritecook.py` stays either way: it cooks the tiles, props, furniture,
icons and font, which are not character art.
