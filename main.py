"""Nimlets - launch with:  python main.py   (see README for options)"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if sys.platform == "win32":
    try:  # crisp pixels on high-DPI Windows displays
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

if __name__ == "__main__":
    from game.app import main
    main(sys.argv[1:])
