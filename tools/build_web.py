"""Build the web version of Nimlets: a home page with the game behind it (v2.6).

    python tools/build_web.py                    # build everything into dist/web
    python tools/build_web.py --serve            # build, then try it at http://localhost:8000
    python tools/build_web.py --site-only        # just the home page, with a stand-in game (no pygbag)

What ends up in dist/web (and on GitHub Pages):

    index.html             the home page, from site/index.html
    manifest.webmanifest   lets phones and computers add Nimlets as an app
    img/                   icons and pixel art, drawn here by the game's own code
    play/                  the game itself, built with pygbag

The game is the same game running in a browser, so it plays on phones and
tablets too. Only the files the game needs are packed (main.py, game/, config/);
tests, tools and saves stay out. pygbag downloads its browser runtime while
building, so a full build needs an internet connection. GitHub builds and
publishes it for you: see .github/workflows/build-web.yml.

In the browser, saves live in the browser's own storage (see game/save.py). That
storage belongs to the whole site, not to one page, so moving the game into
play/ kept everyone's pet.
"""
import argparse
import functools
import http.server
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
STAGE = os.path.join(ROOT, "build", "nimlets")      # pygbag names the app after this folder
OUT = os.path.join(ROOT, "dist", "web")
SITE = os.path.join(ROOT, "site")                   # the home page's own files
PACKED = ("main.py", "game", "config")
GAME_DIR = "play"                                   # the game's folder on the site

HERO_HUE = 205                                      # the pet on the home page (blue reads well on peach)
GROWTH = ("egg", "pipling", "bobbit", "sprouty", "luminelle")
ICON_SIZES = (180, 192, 512)                        # 180 for iPhones, 192 and 512 for everyone else

# Added to the game's page, so adding the game itself to a home screen works too,
# and so the browser is asked to keep the pet's storage (on the first tap or key,
# never on page load: Firefox shows a question for it).
HEAD_MARK = "<!-- nimlets:app -->"
GAME_HEAD = HEAD_MARK + """
<link rel="manifest" href="../manifest.webmanifest">
<link rel="apple-touch-icon" href="../img/icon-180.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Nimlets">
<script>
(function () {
  var asked = false;
  function ask() {
    if (asked) return;
    asked = true;
    try {
      var s = navigator.storage;
      if (!s || !s.persist || !s.persisted) return;
      s.persisted().then(function (kept) { return kept || s.persist(); })
        .then(function (kept) { console.log("[nimlets] storage kept: " + kept); })
        .catch(function () {});
    } catch (e) {}
  }
  ["pointerdown", "keydown", "touchstart"].forEach(function (t) {
    window.addEventListener(t, ask, {once: true, capture: true, passive: true});
  });
})();
</script>
"""

STAND_IN = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Nimlets (stand-in)</title></head>
<body style="font-family: system-ui, sans-serif; padding: 2rem">
<p>This is a stand-in for the game, made by <code>build_web.py --site-only</code>.
A full build puts the real game here.</p><p><a href="../">Back to the home page</a></p>
</body></html>
"""


# ---------------------------------------------------------------- the game (pygbag)

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


def build_game():
    """Run pygbag; returns the folder holding the built game."""
    from game.version import VERSION
    print(f"Staged for the web: {', '.join(stage())}")
    cmd = [sys.executable, "-m", "pygbag", "--title", f"Nimlets v{VERSION}", "--app_name", "nimlets",
           "--icon", os.path.join(STAGE, "favicon.png"), "--build", STAGE]
    r = subprocess.run(cmd, cwd=ROOT)
    built = os.path.join(STAGE, "build", "web")
    if r.returncode != 0 or not os.path.exists(os.path.join(built, "index.html")):
        sys.exit("The web build didn't finish (pygbag needs an internet connection to fetch its runtime).")
    return built


def add_app_head(html):
    """Put GAME_HEAD into the game's page, once, just before </head>."""
    if HEAD_MARK in html:
        return html
    at = html.lower().find("</head>")
    if at < 0:                                      # no head: put it first, browsers still read it
        return GAME_HEAD + html
    return html[:at] + GAME_HEAD + html[at:]


# ---------------------------------------------------------------- the home page

def _pygame():
    import pygame
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((1, 1))
    return pygame


def wordmark_svg(text="Nimlets"):
    """The name in the game's own pixel font, as an SVG that takes the page's text colour."""
    from game.pixelfont import GLYPHS, ROWS, normalise
    rects, x = [], 0
    for ch in normalise(text):
        g = GLYPHS[ch]
        for ry, row in enumerate(g):
            rx = 0
            while rx < len(row):                    # one rectangle per run of lit pixels
                if row[rx]:
                    start = rx
                    while rx < len(row) and row[rx]:
                        rx += 1
                    rects.append(f'<rect x="{x + start}" y="{ry}" width="{rx - start}" height="1"/>')
                else:
                    rx += 1
        x += len(g[0]) + 1
    w = max(1, x - 1)
    return (f'<svg class="wordmark-art" viewBox="0 0 {w} {ROWS}" width="{w * 8}" height="{ROWS * 8}" '
            f'aria-hidden="true" focusable="false" shape-rendering="crispEdges">'
            f'<g class="shade" transform="translate(0.5 0.5)">{"".join(rects)}</g>'
            f'<g class="face">{"".join(rects)}</g></svg>')


def collection_order():
    """Every form, land line first, then water, then any line; secrets last in each."""
    from game.config import load_species
    db = load_species()
    rank = {"land": 0, "water": 1}
    return sorted(db, key=lambda sid: (rank.get(db[sid].get("line"), 2), bool(db[sid].get("secret"))))


def site_images(img_dir):
    """Draw the home page's pictures with the game's own sprite code. Returns the collection's tiles."""
    pygame = _pygame()
    from game.config import load_species
    from game.icon import icon_surface
    from game.pixelfont import PixelFont
    from game.sprites import SpriteRenderer
    os.makedirs(img_dir, exist_ok=True)
    db = load_species()
    r = SpriteRenderer(db)
    genome = {"hue": HERO_HUE, "sat": 0.6, "marking": "none", "marking_hue": (HERO_HUE + 180) % 360}
    face = {"eyes": "open", "mouth": "smile"}

    for size in ICON_SIZES:
        pygame.image.save(icon_surface(size), os.path.join(img_dir, f"icon-{size}.png"))
    for sid in GROWTH:
        img = r.egg(genome, 0) if sid == "egg" else r.creature(sid, genome, False, face)
        pygame.image.save(img, os.path.join(img_dir, f"grow-{sid}.png"))

    q = pygame.Surface((32, 32), pygame.SRCALPHA)   # the "?" tile for a secret form
    mark = PixelFont(16, bold=True).render("?", color=(70, 66, 92))
    q.blit(mark, mark.get_rect(center=(16, 17)))
    pygame.image.save(q, os.path.join(img_dir, "secret.png"))

    tiles = []
    for sid in collection_order():
        sp = db[sid]
        if sp.get("secret"):
            tiles.append(("secret.png", "A secret form", "secret"))
        elif sid in GROWTH:
            pygame.image.save(r.creature(sid, genome, False, face), os.path.join(img_dir, f"form-{sid}.png"))
            tiles.append((f"form-{sid}.png", sp.get("name", sid.title()), "found"))
        else:
            pygame.image.save(r.silhouette(sid), os.path.join(img_dir, f"form-{sid}.png"))
            tiles.append((f"form-{sid}.png", "A form still to find", "unknown"))
    return tiles


def render_page(template, values):
    """Fill {{NAME}} placeholders; every placeholder must be filled."""
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    if "{{" in template:
        left = template[template.index("{{"):template.index("{{") + 40]
        raise ValueError(f"site/index.html has a placeholder nothing fills: {left!r}")
    return template


def build_site(out):
    """The home page, its manifest and its pictures, into out (which is emptied first)."""
    from html import escape
    from game.version import CODENAME, VERSION
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(SITE, out)
    tiles = site_images(os.path.join(out, "img"))
    found = sum(1 for t in tiles if t[2] == "found")
    secrets = sum(1 for t in tiles if t[2] == "secret")
    items = "\n".join(f'      <li class="{kind}"><img src="img/{src}" alt="{escape(alt)}" width="32" height="32"></li>'
                      for src, alt, kind in tiles)
    path = os.path.join(out, "index.html")
    with open(path, encoding="utf-8") as f:
        page = f.read()
    page = render_page(page, {"VERSION": VERSION, "CODENAME": escape(CODENAME), "WORDMARK": wordmark_svg(),
                              "COLLECTION": items, "FORMS": str(len(tiles)), "FOUND": str(found),
                              "SECRETS": str(secrets)})
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)
    return out


def assemble(game_build, out=OUT):
    """The home page at the top, the game in play/ with its home-screen extras."""
    build_site(out)
    play = os.path.join(out, GAME_DIR)
    if game_build:
        shutil.copytree(game_build, play)
    else:
        os.makedirs(play)
        with open(os.path.join(play, "index.html"), "w", encoding="utf-8") as f:
            f.write(STAND_IN)
    page = os.path.join(play, "index.html")
    with open(page, encoding="utf-8") as f:
        html = f.read()
    with open(page, "w", encoding="utf-8") as f:
        f.write(add_app_head(html))
    return out


class _Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = dict(http.server.SimpleHTTPRequestHandler.extensions_map,
                          **{".webmanifest": "application/manifest+json", ".apk": "application/octet-stream"})


def serve(folder, port=8000):
    handler = functools.partial(_Handler, directory=folder)
    print(f"Serving {folder} at http://localhost:{port}/ (Ctrl+C to stop)")
    with http.server.ThreadingHTTPServer(("", port), handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


def build(serve_it=False, site_only=False):
    out = assemble(None if site_only else build_game())
    print(f"Done: {out}  (home page at index.html, the game in {GAME_DIR}/)")
    if serve_it:
        serve(out)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Build the web version of Nimlets")
    ap.add_argument("--serve", action="store_true", help="build, then try it at http://localhost:8000")
    ap.add_argument("--site-only", action="store_true", help="only the home page, with a stand-in for the game")
    a = ap.parse_args()
    build(a.serve, a.site_only)
