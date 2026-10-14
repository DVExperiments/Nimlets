"""Build the standalone game (Nimlets.exe on Windows) with PyInstaller.

    python tools/build_exe.py              # tests, icon, build, smoke test, zip
    python tools/build_exe.py --skip-tests

Used by build_exe.bat on your PC and by .github/workflows/build-windows.yml on
GitHub. Output goes to dist/:
    dist/Nimlets.exe                       the game, one file, no Python needed
    dist/Nimlets-vX.Y.Z-windows.zip        the .exe plus a short read-me, for releases

The build always comes from the code in this folder - never edit a build.
Saves are not touched: the game keeps them in the player's own Nimlets folder.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

PLATFORM = {"win32": "windows", "darwin": "macos"}.get(sys.platform, "linux")
EXE_NAME = "Nimlets.exe" if sys.platform == "win32" else "Nimlets"

PLAYER_README = """Nimlets {version}
==============

Double-click Nimlets.exe to play. No installation and no Python needed.

The first time, Windows may say "Windows protected your PC". That's because
Nimlets is a small independent game without a paid code-signing certificate.
Click "More info", then "Run anyway".

Your pet is saved in your own Nimlets folder, not next to the game:
    %APPDATA%\\Nimlets
(In the game: Settings, Open folder.) Updating to a new version keeps your pet:
just replace Nimlets.exe with the new one.

Keys: 1-8 actions, A / B / C buttons, O settings, M sound, P pause, F9 Observation Mode.

Nimlets is free to play, all rights reserved: please don't re-upload, modify
or sell it. Share the official GitHub page instead. See LICENSE.txt.
"""


def step(msg):
    print(f"\n==> {msg}", flush=True)


def headless_env(extra=None):
    env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
    env.update(extra or {})
    return env


def run_tests():
    step("Running the tests")
    r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=ROOT,
                       env=headless_env())
    if r.returncode != 0:
        sys.exit("Tests failed, so no build was made. Fix the failures and try again.")


def make_icon():
    step("Drawing the icon")
    import make_icon as mk
    mk.main(os.path.join(ROOT, "assets"))
    return os.path.join(ROOT, "assets", "icon.ico")


def build(icon):
    step("Building with PyInstaller (this takes a minute or two)")
    try:
        import PyInstaller.__main__ as pyi
    except ImportError:
        sys.exit("PyInstaller isn't installed. Run:  python -m pip install pyinstaller")
    dist = os.path.join(ROOT, "dist")
    work = os.path.join(ROOT, "build")
    args = ["--noconfirm", "--clean", "--onefile", "--windowed", "--name", "Nimlets",
            "--distpath", dist, "--workpath", work, "--specpath", work,
            "--add-data", f"{os.path.join(ROOT, 'config')}{os.pathsep}config",
            os.path.join(ROOT, "main.py")]
    if sys.platform == "win32":
        args[:0] = ["--icon", icon]
    pyi.run(args)
    exe = os.path.join(dist, EXE_NAME)
    if not os.path.exists(exe):
        sys.exit(f"The build finished but {exe} is missing.")
    return exe


def smoke_test(exe):
    step("Smoke-testing the built game")
    with tempfile.TemporaryDirectory() as data:
        r = subprocess.run([exe, "--smoke-test", "180", "--mute"], env=headless_env({"NIMLETS_DATA_DIR": data}),
                           timeout=300)
        saved = os.path.exists(os.path.join(data, "savegame.json"))
    if r.returncode != 0 or not saved:
        sys.exit(f"The built game didn't run cleanly (exit {r.returncode}, saved: {saved}).")
    print("The built game started, ran 180 frames, saved to its data folder and quit cleanly.")


def package(exe):
    from game.version import VERSION
    step("Zipping the release")
    out = os.path.join(ROOT, "dist", f"Nimlets-v{VERSION}-{PLATFORM}.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(exe, os.path.basename(exe))
        z.writestr("README.txt", PLAYER_README.format(version=f"v{VERSION}"))
        z.write(os.path.join(ROOT, "LICENSE"), "LICENSE.txt")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the standalone Nimlets game")
    ap.add_argument("--skip-tests", action="store_true", help="build without running the tests first")
    ap.add_argument("--no-smoke", action="store_true", help="don't run the built game afterwards")
    args = ap.parse_args(argv)
    if not args.skip_tests:
        run_tests()
    exe = build(make_icon())
    if not args.no_smoke:
        smoke_test(exe)
    out = package(exe)
    size = os.path.getsize(exe) / 1e6
    step(f"Done: {exe} ({size:.1f} MB)\n    and {out}")
    shutil.rmtree(os.path.join(ROOT, "build"), ignore_errors=True)
    return out


if __name__ == "__main__":
    main()
