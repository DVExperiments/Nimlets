"""Export every creature form (several poses) to assets/sprite_sheet.png.

The game never needs this file - all art is generated at runtime from
config/species.json - but it is handy for previewing designs after editing
species definitions.   Usage:  python tools/export_sprites.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
from game.config import load_species  # noqa: E402
from game.sprites import SpriteRenderer  # noqa: E402

POSES = [
    {"eyes": "open", "mouth": "smile"},
    {"eyes": "happy", "mouth": "big", "arms": "up", "squash": -1},
    {"eyes": "love", "mouth": "smile", "blush": True},
    {"eyes": "sad", "mouth": "frown", "squash": 1},
    {"eyes": "angry", "mouth": "frown"},
    {"eyes": "sick", "mouth": "frown"},
    {"eyes": "closed", "mouth": "flat", "feet": "tuck", "squash": 1},
]


def main(scale=4):
    pygame.init()
    pygame.display.set_mode((8, 8))
    db = load_species()
    r = SpriteRenderer(db)
    genome = {"hue": 205, "sat": 0.6, "marking": "none", "marking_hue": 20}
    cell = 34 * scale
    sheet = pygame.Surface((cell * (len(POSES) + 1), cell * (len(db) + 1)), pygame.SRCALPHA)
    for row, sid in enumerate(db):
        for col, pose in enumerate(POSES):
            img = r.creature(sid, genome, False, pose)
            sheet.blit(pygame.transform.scale(img, (32 * scale, 32 * scale)), (col * cell, row * cell))
        sil = r.silhouette(sid)
        sheet.blit(pygame.transform.scale(sil, (32 * scale, 32 * scale)), (len(POSES) * cell, row * cell))
    for crack in range(3):
        egg = r.egg(genome, crack)
        sheet.blit(pygame.transform.scale(egg, (32 * scale, 32 * scale)), (crack * cell, len(db) * cell))
    out = os.path.join(ROOT, "assets", "sprite_sheet.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    pygame.image.save(sheet, out)
    print("wrote", out)


if __name__ == "__main__":
    main()
