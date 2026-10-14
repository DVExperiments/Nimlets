"""Build the web version of Nimlets with pygbag (v2.2).

    python tools/build_web.py             # build into dist/web
    python tools/build_web.py --serve     # build, then play it at http://localhost:8000

The web version is the same game running in a browser, so it plays on phones and
tablets too. Only the files the game needs are packed (main.py, game/, config/);
tests, tools and saves stay out. pygbag downloads its browser runtime while
building, so this needs an internet connection. GitHub builds and publishes it
for you: see .github/workflows/build-web.yml.

In the browser, saves live in the browser's own storage (see game/save.py).
"""
import argparse
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
STAGE = os.path.join(ROOT, "build", "nimlets")      # pygbag names the app after this folder
OUT = os.path.join(ROOT, "dist", "web")
PACKED = ("main.py", "game", "config")


def stage():
    """Copy just what the game needs into a clean folder for pygbag."""
    shutil.rmtree(STAGE, ignore_errors=True)
    os.makedirs(STAGE)
    for name in PACKED:
        src = os.path.join(ROOT, name)
        dst = os.path.join(STAGE, name)
        if os.path.isdir(src):
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copy2(src, dst)
    import make_icon                                # the egg icon doubles as the page's favicon
    make_icon.main(os.path.join(ROOT, "assets"))
    shutil.copy2(os.path.join(ROOT, "assets", "icon.png"), os.path.join(STAGE, "favicon.png"))
    return sorted(os.listdir(STAGE))


def build(serve=False):
    from game.version import VERSION
    print(f"Staged for the web: {', '.join(stage())}")
    cmd = [sys.executable, "-m", "pygbag", "--title", f"Nimlets v{VERSION}", "--app_name", "nimlets",
           "--icon", os.path.join(STAGE, "favicon.png")]
    if not serve:
        cmd.append("--build")
    cmd.append(STAGE)
    r = subprocess.run(cmd, cwd=ROOT)
    built = os.path.join(STAGE, "build", "web")
    if r.returncode != 0 or not os.path.exists(os.path.join(built, "index.html")):
        sys.exit("The web build didn't finish (pygbag needs an internet connection to fetch its runtime).")
    shutil.rmtree(OUT, ignore_errors=True)
    shutil.copytree(built, OUT)
    print(f"Done: {OUT} (open index.html through a web server, or use --serve)")
    return OUT


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Build the web version of Nimlets")
    ap.add_argument("--serve", action="store_true", help="build and play it locally at http://localhost:8000")
    build(ap.parse_args().serve)
