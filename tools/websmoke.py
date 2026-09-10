#!/usr/bin/env python3
"""Run the browser build and check that it actually works.

The Godot build has had a harness that plays it through every mode since the
day the engine first ran it. The browser build - the one you actually play -
had a pile of throwaway scripts in a temp directory, which is how a stray line
in the encounter path shipped: it made every step throw, and no test ever took
a step. This is the same harness for the same game in the other runtime.

    python3 tools/websmoke.py                    # headless, all of it
    python3 tools/websmoke.py --view 915x412 --dpr 3 --touch
    python3 tools/websmoke.py --shots art/web

It needs node and playwright. Playwright resolves its own browser; when the
installed playwright and the installed browsers are different builds - the
normal state of a machine that got them from different places - the harness
falls back to whatever chromium is actually under PLAYWRIGHT_BROWSERS_PATH.
"""

import argparse
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS = os.path.join(ROOT, "tools", "websmoke.js")
PAGE = os.path.join(ROOT, "index.html")


def node_path():
    """Where `require('playwright')` can find it.

    A global install is not on a script's own resolution path unless NODE_PATH
    says so, and playwright is normally global. A local node_modules wins when
    there is one, because that is the version the project pinned.
    """
    roots = []
    local = os.path.join(ROOT, "node_modules")
    if os.path.isdir(local):
        roots.append(local)
    if os.environ.get("NODE_PATH"):
        roots.append(os.environ["NODE_PATH"])
    try:
        out = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True,
                             timeout=30)
        if out.returncode == 0 and out.stdout.strip():
            roots.append(out.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return os.pathsep.join(roots)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--node", help="node binary; found on PATH by default")
    ap.add_argument("--page", default=PAGE, help="the built index.html to play")
    ap.add_argument("--shots", default=None, help="directory for screenshots")
    ap.add_argument("--view", default="960x540", help="window size, WxH")
    ap.add_argument("--dpr", default="1", help="device pixel ratio")
    ap.add_argument("--touch", action="store_true",
                    help="a touch device: the on-screen controls and the frameless layout")
    ap.add_argument("--timeout", type=int, default=600)
    args = ap.parse_args()

    node = args.node or shutil.which("node")
    if not node:
        print("node not found: put it on PATH or pass --node")
        return 2
    if not os.path.exists(args.page):
        print("no build to test at %s - run tools/build.py first" % args.page)
        return 2

    env = dict(os.environ)
    env["NODE_PATH"] = node_path()
    env["RIVEN_PAGE"] = os.path.abspath(args.page)
    env["RIVEN_VIEW"] = args.view
    env["RIVEN_DPR"] = args.dpr
    env["RIVEN_TOUCH"] = "1" if args.touch else "0"
    if args.shots:
        os.makedirs(args.shots, exist_ok=True)
        env["RIVEN_SHOTS"] = os.path.abspath(args.shots)

    print("page   : %s" % os.path.relpath(args.page, ROOT))
    print("window : %s at %sx%s" % (args.view, args.dpr, "touch" if args.touch else ""))
    try:
        proc = subprocess.run([node, HARNESS], cwd=ROOT, env=env, timeout=args.timeout)
    except subprocess.TimeoutExpired:
        print("ERROR: timed out after %ds" % args.timeout)
        return 1
    if proc.returncode == 0 and args.shots:
        print("shots  : %s" % args.shots)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
