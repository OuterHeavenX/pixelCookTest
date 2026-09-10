# The third runtime

Rivenbrook is built from one set of cooked assets and one set of rules. The
browser build reads them, the Godot build reads them, and this reads them: the
same `atlas.png`, `atlas.json`, `maps.json`, `gamedata.json` and the same 5x7
font, staged here by `tools/unrealcook.py` and read off disk at startup.

They are deliberately **not** imported as Unreal assets. An imported atlas is a
fourth copy that can drift from the other three, and the whole discipline of
this repository is that there is one cooked copy of everything.

## The shape of it

Both other runtimes draw everything in a single pass — `Main._draw()` in Godot,
`frame()` in the browser — so this is **one Slate widget with one `OnPaint`**,
not a level full of actors. No Paper2D, no tilemap assets, no Blueprints, no
`.umap`. The entire runtime is text in this repository, which is what lets it
be worked on from anywhere.

The whole graphics surface the game uses is fifteen primitives:

    Spr  SprStretched  SprFoot  ScaleFor  Rect
    Text  TextWidth  TextBig  WrapText
    Window  Button  Cursor  Bar  Shadow

Implement those on Slate and the rest of the port is a mechanical translation
of 4,300 lines of straight-line logic that already exists twice.

    unreal/
      Rivenbrook.uproject                 engine association lives here
      Content/Rivenbrook/                 staged by tools/unrealcook.py
      Plugins/Rivenbrook/
        Source/Rivenbrook/
          Public/RivenbrookArt.h          the atlas, the font, the primitives
          Public/SRivenbrookView.h        the one widget
          Public/RivenbrookModule.h       registers the tab
          Private/...

## Running it

    python tools/build.py                 recook everything, including here
    # open unreal/Rivenbrook.uproject, let it compile, then
    # Window -> Developer Tools -> Rivenbrook

A tab rather than Play-in-Editor, because a tab needs no level and no game
mode — nothing that has to be authored inside Unreal. When the runtime is
finished it gets a viewport path too.

## Where it is

**Stage 0 — the art layer.** Loads the atlas and the font, sizes the view to
the tab the same way the other two size to their window, and draws a standing
test of itself: a backdrop, the cast, the monsters, and text. If the assets are
missing it says so on screen instead of drawing nothing.

Still to come: the data layer (`gamedata.json` into structs), the field, the
battle, the menus, and a smoke test to match `godot/scripts/Smoke.gd`.

## The one thing to know

This was written without an Unreal Engine to compile against. Every previous
"it is obviously correct" moment in this project turned out to be wrong until
an engine actually ran it, so treat the first build as a fixing session rather
than as a build. The likely spots are marked in comments — the Slate UV region
type moved between engine versions, and `EngineAssociation` in the .uproject is
a guess at 5.5.
