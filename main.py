"""Nimlets - launch with:  python main.py   (see README for options)"""
import os
import sys

if sys.platform == "emscripten":                      # the web version (built with pygbag)
    print("[nimlets] main.py running in the browser")
else:
    # the folder this file is in (pygbag may run main.py without __file__, so don't rely on it there)
    sys.path.insert(0, os.path.dirname(os.path.abspath(globals().get("__file__", "main.py"))))

if sys.platform == "win32":
    try:  # crisp pixels on high-DPI Windows displays
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

if sys.platform == "emscripten":
    import asyncio
    from game.app import main_async
    asyncio.run(main_async([]))
elif __name__ == "__main__":
    from game.app import main
    main(sys.argv[1:])
