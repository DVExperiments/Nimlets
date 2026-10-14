"""Nimlets - launch with:  python main.py   (see README for options)

This file is also the web version's entry point (built with pygbag), so it follows
pygbag's standard shape: an `async def main()` and `asyncio.run(main())` at the end.
"""
import asyncio
import os
import sys

WEB = sys.platform == "emscripten"
RUN = WEB or __name__ == "__main__"          # run when started, not when imported


def log(msg, error=False):
    """Print, and in the browser also write to the page's developer console."""
    print(msg)
    if WEB:
        try:
            import platform
            (platform.window.console.error if error else platform.window.console.log)(msg)
        except Exception:
            pass


def show_error(text):
    """Last resort: draw an error with pygame's built-in font, so it's never just a grey page."""
    try:
        import pygame
        pygame.init()
        screen = pygame.display.get_surface() or pygame.display.set_mode((960, 760))
        screen.fill((43, 34, 64))
        font = pygame.font.Font(None, 22)
        y = 16
        for line in ["Sorry - Nimlets couldn't start.", "Please send a screenshot of this to the developer.", ""] \
                + text.splitlines():
            screen.blit(font.render(line[:120], True, (255, 220, 200)), (16, y))
            y += 22
        pygame.display.flip()
    except Exception as exc:
        log(f"[nimlets] could not show the error: {exc}", error=True)


if not WEB:
    # the folder this file is in (pygbag may run main.py without __file__, so only rely on it here)
    sys.path.insert(0, os.path.dirname(os.path.abspath(globals().get("__file__", "main.py"))))

if sys.platform == "win32":
    try:  # crisp pixels on high-DPI Windows displays
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


async def main():
    if not RUN:
        return
    if not WEB:
        from game.app import main as desktop_main
        desktop_main(sys.argv[1:])
        return
    log("[nimlets] main.py running in the browser")
    try:
        from game.app import main_async
    except BaseException:
        import traceback
        text = traceback.format_exc()
        log("[nimlets] the game's code didn't load:\n" + text, error=True)
        show_error(text)
        while True:                           # keep the message on screen
            await asyncio.sleep(1)
    log("[nimlets] game code loaded")
    await main_async([])


asyncio.run(main())
