#!/usr/bin/env python3
"""Run the Godot build and check that it actually works.

gdlint and a syntax pass can only prove the scripts are well formed. They
cannot catch a warning the engine treats as a fatal parse error, a method that
does not exist on a real object, or a scene that fails to boot. This starts the
engine, plays the game through every mode, and screenshots each one.

    python3 tools/godotsmoke.py                  # find godot on PATH or $GODOT
    python3 tools/godotsmoke.py --godot ./godot4
    python3 tools/godotsmoke.py --shots art/godot

Rendering needs a display and an OpenGL context. On a headless machine this
wraps the run in xvfb-run with Mesa's software rasteriser, which is slow but
draws exactly what a real GPU would.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT = os.path.join(ROOT, "godot")

# Engine noise that says nothing about the game: no sound card and no GPU in a
# container, and Godot's exit-time accounting of its own reference cycles.
IGNORED = (
    re.compile(r"ALSA|libpulse|audio driver|Condition \"status < 0\"|init_output_device"),
    re.compile(r"V-Sync"),
    re.compile(r"ObjectDB instances leaked"),
    re.compile(r"at: (cleanup|set_use_vsync|initialize) "),
)


def find_godot(explicit):
    for cand in (explicit, os.environ.get("GODOT"), "godot", "godot4"):
        if not cand:
            continue
        path = shutil.which(cand) or (cand if os.path.isfile(cand) else None)
        if path:
            return os.path.abspath(path)
    return None


def run(argv, env, timeout):
    p = subprocess.run(argv, cwd=ROOT, env=env, timeout=timeout,
                       capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def engine_errors(output):
    out = []
    for line in output.splitlines():
        if not re.search(r"SCRIPT ERROR|Parse Error|Compile Error|^ERROR:|^WARNING:", line):
            continue
        if any(rx.search(line) for rx in IGNORED):
            continue
        out.append(line.strip())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--godot")
    ap.add_argument("--shots", default=os.path.join(ROOT, "art", "godot"))
    ap.add_argument("--timeout", type=int, default=600)
    args = ap.parse_args()

    godot = find_godot(args.godot)
    if not godot:
        print("godot not found: put it on PATH, set $GODOT, or pass --godot")
        return 2

    env = dict(os.environ)
    env.update(LIBGL_ALWAYS_SOFTWARE="1", GALLIUM_DRIVER="llvmpipe")
    os.makedirs(args.shots, exist_ok=True)
    env["SMOKE_OUT"] = os.path.abspath(args.shots)

    # An import pass first: class_name types are only visible to the engine
    # once the project has been scanned, and a fresh clone has never been.
    code, out = run([godot, "--headless", "--editor", "--path", PROJECT, "--quit"],
                    env, args.timeout)
    errs = engine_errors(out)
    if errs:
        print("import failed:")
        for e in errs[:25]:
            print("  " + e)
        return 1
    print("import : clean")

    argv = [godot, "--path", PROJECT, "res://scenes/Smoke.tscn",
            "--rendering-driver", "opengl3"]
    if not os.environ.get("DISPLAY") and shutil.which("xvfb-run"):
        argv = ["xvfb-run", "-a", "-s", "-screen 0 1280x720x24"] + argv
    code, out = run(argv, env, args.timeout)

    for line in out.splitlines():
        if line.startswith(("  ok ", "  FAIL", "SMOKE", "  - ")) or line in (
                "title", "field", "equipment", "menu", "shop", "battle", "save"):
            print(line)
    errs = engine_errors(out)
    if errs:
        print("engine errors:")
        for e in errs[:25]:
            print("  " + e)
    if code != 0 or errs:
        return 1
    print("shots  : %s" % args.shots)
    return 0


if __name__ == "__main__":
    sys.exit(main())
