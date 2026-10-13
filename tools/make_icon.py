"""Write the app icon files from game/icon.py (no image editor, no extra libraries).

    python tools/make_icon.py

Creates assets/icon.png (256 x 256) and assets/icon.ico, a Windows icon holding
16, 24, 32, 48, 64, 128 and 256 pixel versions (stored as PNG, which Windows
supports). The .exe build uses icon.ico; the game draws its own window icon.
"""
import os
import struct
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

from game.icon import icon_surface  # noqa: E402

SIZES = (16, 24, 32, 48, 64, 128, 256)


def png_bytes(surf):
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        pygame.image.save(surf, path)
        with open(path, "rb") as f:
            return f.read()
    finally:
        os.remove(path)


def write_ico(path, images):
    """images: list of (size, png bytes). ICO header, one directory entry per image, then the data."""
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries, blobs = b"", b""
    for size, data in images:
        dim = 0 if size >= 256 else size                  # 0 means 256 in the ICO format
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset)
        blobs += data
        offset += len(data)
    with open(path, "wb") as f:
        f.write(header + entries + blobs)


def main(out_dir=None):
    out_dir = out_dir or os.path.join(ROOT, "assets")
    pygame.init()
    pygame.display.set_mode((1, 1))
    os.makedirs(out_dir, exist_ok=True)
    pygame.image.save(icon_surface(256), os.path.join(out_dir, "icon.png"))
    write_ico(os.path.join(out_dir, "icon.ico"), [(s, png_bytes(icon_surface(s))) for s in SIZES])
    print(f"wrote {os.path.join(out_dir, 'icon.png')} and icon.ico ({', '.join(map(str, SIZES))} px)")
    return out_dir


if __name__ == "__main__":
    main()
