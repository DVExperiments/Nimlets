"""Desktop companion (optional, Windows): the pet visits your desktop.

Started as a separate process by escape.launch_roam(). It opens a tiny
borderless, always-on-top window whose magenta background is made fully
transparent with the Win32 colour-key API, so only the pet is visible. It
walks along the top of your taskbar, looks around, and then walks back to
the game window and exits, writing a small result file (an imaginary
souvenir).

It does not read the screen, other windows, files or input outside its own
little window. Click the pet to send it home early. It also gives up on its
own after the configured duration.
"""
import json
import os
import random
import sys
import time

KEY = (255, 0, 255)
SOUVENIRS = ("a stray pixel", "a crumb of taskbar", "a scrap of wallpaper", "a tiny lost window",
             "a cursor sparkle", "a speck of desktop dust")


def _work_area():
    if sys.platform != "win32":
        return (0, 0, 1920, 1040)
    import ctypes
    from ctypes import wintypes
    rect = wintypes.RECT()
    ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)  # SPI_GETWORKAREA
    return (rect.left, rect.top, rect.right, rect.bottom)


class _Win32Window:
    def __init__(self, hwnd):
        import ctypes
        self.u = ctypes.windll.user32
        self.hwnd = hwnd
        GWL_EXSTYLE = -20
        WS_EX_LAYERED, WS_EX_TOOLWINDOW, WS_EX_TOPMOST = 0x80000, 0x80, 0x8
        style = self.u.GetWindowLongW(hwnd, GWL_EXSTYLE)
        self.u.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_TOPMOST)
        colorref = KEY[0] | (KEY[1] << 8) | (KEY[2] << 16)
        self.u.SetLayeredWindowAttributes(hwnd, colorref, 0, 0x1)  # LWA_COLORKEY

    def move(self, x, y):
        HWND_TOPMOST, SWP_NOSIZE, SWP_NOACTIVATE = -1, 0x1, 0x10
        self.u.SetWindowPos(self.hwnd, HWND_TOPMOST, int(x), int(y), 0, 0, SWP_NOSIZE | SWP_NOACTIVATE)


def run(cfg_path, max_frames=None):
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, root)
    import pygame
    from game.config import load_species
    from game.sprites import SpriteRenderer

    rng = random.Random()
    k = 3
    size = 32 * k
    left, top, right, bottom = cfg["rect"]
    wl, wt, wr, wb = _work_area()
    # start at the game window's right edge, feet on its top bar
    x, feet = float(right - size // 2), float(top + 60)
    os.environ["SDL_VIDEO_WINDOW_POS"] = f"{int(x - size / 2)},{int(feet - size)}"
    pygame.init()
    screen = pygame.display.set_mode((size, size), pygame.NOFRAME)
    pygame.display.set_caption(f"{cfg.get('name', 'Pet')} is exploring")
    win = None
    if sys.platform == "win32":
        try:
            win = _Win32Window(pygame.display.get_wm_info()["window"])
        except Exception as exc:
            print(f"[roam] transparency unavailable: {exc}")
    renderer = SpriteRenderer(load_species())
    clock = pygame.time.Clock()
    start = time.time()
    duration = float(cfg.get("duration", 60))
    phase, vy, target, wait, facing = "fall", 0.0, None, 0.0, 1
    ground = float(wb)
    frames = 0
    t = 0.0
    while True:
        dt = min(clock.tick(30) / 1000.0, 0.1)
        t += dt
        frames += 1
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                phase = "home"
            elif ev.type == pygame.MOUSEBUTTONDOWN and phase not in ("home", "climb"):
                phase = "home"          # clicked: hurry home
        elapsed = time.time() - start
        if elapsed > duration and phase in ("wander", "pause"):
            phase = "home"
        state = "idle"
        if phase == "fall":
            vy += 900 * dt
            feet += vy * dt
            x += 40 * dt
            state = "jump"
            if feet >= ground:
                feet, phase = ground, "wander"
        elif phase == "wander":
            if target is None:
                target = rng.uniform(wl + size, wr - size)
            d = target - x
            facing = 1 if d > 0 else -1
            x += facing * min(abs(d), 45 * dt)
            state = "walk"
            if abs(d) < 2:
                target, phase, wait = None, "pause", rng.uniform(2, 5)
        elif phase == "pause":
            wait -= dt
            state = rng.choice(["look", "idle"]) if int(t) % 3 else "look"
            if wait <= 0:
                phase = "wander"
        elif phase == "home":
            d = (right - size // 2) - x
            facing = 1 if d > 0 else -1
            x += facing * min(abs(d), 90 * dt)
            state = "walk"
            if abs(d) < 3:
                phase = "climb"
        elif phase == "climb":
            goal = top + 60
            feet -= 160 * dt
            state = "jump"
            if feet <= goal:
                break
        if max_frames and frames >= max_frames:
            break
        tick = int(t * 6) % 2
        pose = {"eyes": "open", "mouth": "smile", "squash": 0, "feet": "both", "arms": "down"}
        if state == "walk":
            pose["feet"] = "left" if tick else "right"
        elif state == "jump":
            pose.update(eyes="happy", mouth="big", arms="up", squash=-1)
        elif state == "look":
            pose["gaze"] = "ul" if int(t) % 2 else "ur"
        if (t % 3.4) < 0.14:
            pose["eyes"] = "closed"
        img = renderer.creature(cfg["species"], cfg["genome"], cfg.get("elder", False), pose)
        if facing > 0:
            img = pygame.transform.flip(img, True, False)
        screen.fill(KEY)
        screen.blit(pygame.transform.scale(img, (size, size)), (0, 0))
        pygame.display.flip()
        if win:
            win.move(x - size / 2, feet - size + k)
    seconds = round(time.time() - start, 1)
    result = {"souvenir": rng.choice(SOUVENIRS), "seconds": seconds}
    try:
        with open(cfg["result"], "w", encoding="utf-8") as f:
            json.dump(result, f)
    except OSError:
        pass
    pygame.quit()
    return result
