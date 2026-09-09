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
import time
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT = os.path.join(ROOT, "godot")

# Engine noise that says nothing about the game: no sound card and no GPU in a
# container, and Godot's exit-time accounting of its own reference cycles.
SECTIONS = ("title", "field", "equipment", "menu", "shop", "battle", "barrow",
            "ending", "aftermath", "chapter two", "save")

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


def run(argv, env, timeout, stream=False):
    """Run the engine, optionally echoing its output as it arrives.

    Buffering the whole run and printing at the end is fine until it hangs,
    and then there is nothing to look at: a run that stalls before its first
    screenshot gives you a silent process and no idea which line it stopped
    on. With stream on, every check prints the moment the engine prints it.
    """
    if not stream:
        try:
            p = subprocess.run(argv, cwd=ROOT, env=env, timeout=timeout,
                               capture_output=True, text=True)
        except subprocess.TimeoutExpired as e:
            # Report the timeout rather than dying on a traceback: a run that
            # overruns should still say what it managed to print.
            out = (e.stdout or b"").decode("utf-8", "replace") if e.stdout else ""
            return 1, out + "\nERROR: timed out after %ds\n" % timeout
        return p.returncode, (p.stdout or "") + (p.stderr or "")

    proc = subprocess.Popen(argv, cwd=ROOT, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            bufsize=1)
    lines = []
    deadline = time.time() + timeout
    try:
        for line in proc.stdout:
            lines.append(line)
            if line.startswith(("  ok ", "  FAIL", "SMOKE", "  - ")) or \
                    line.strip() in SECTIONS:
                print(line.rstrip(), flush=True)
            if time.time() > deadline:
                proc.kill()
                print("  TIMED OUT after %ds" % timeout, flush=True)
                break
    finally:
        proc.stdout.close()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    return proc.returncode or 0, "".join(lines)


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
    code, out = run(argv, env, args.timeout, stream=True)
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
