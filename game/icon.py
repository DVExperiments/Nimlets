"""The Nimlets app icon (v2.0), drawn in code like everything else.

A spotted egg on a purple tile with a light underwater pattern borrowed from
the Tide shell: wave crests, bubbles, sparkles and a deeper wave along the
bottom. Small sizes drop the fine detail so the egg still reads at 16 px.

    icon_surface(size)   -> a pygame Surface (used for the window icon)
    tools/make_icon.py   -> writes assets/icon.png and a multi-size assets/icon.ico
"""
import math

import pygame

BASE = (143, 123, 196)
LIP = (111, 90, 168)
BAND = (124, 104, 184)
BAND2 = (113, 92, 174)
CREST = (178, 162, 226)
BUBBLE = (196, 184, 238)
BUBBLE_EDGE = (226, 218, 250)
SPARKLE = (246, 231, 168)
EGG_GENOME = {"hue": 262, "sat": 0.55, "marking": "cheeks", "marking_hue": 330, "mutation": None}


def _egg_sprite():
    from . import config
    from .sprites import SpriteRenderer
    img = SpriteRenderer(config.load_species()).egg(EGG_GENOME)
    return img.subsurface(img.get_bounding_rect()).copy()


def _wave(surf, col, y, amp, k, filled=True, width=2):
    w, h = surf.get_size()
    pts = [(x, y - amp * math.sin(x / (w / 5.5) * math.pi)) for x in range(0, w + 4, max(2, w // 64))]
    if filled:
        pygame.draw.polygon(surf, col, pts + [(w, h), (0, h)])
    else:
        pygame.draw.lines(surf, col, False, pts, width)


def _sparkle(surf, x, y, s):
    pts = [(x, y - s), (x + s * 0.3, y - s * 0.3), (x + s, y), (x + s * 0.3, y + s * 0.3), (x, y + s),
           (x - s * 0.3, y + s * 0.3), (x - s, y), (x - s * 0.3, y - s * 0.3)]
    pygame.draw.polygon(surf, SPARKLE, pts)


def icon_surface(size=256):
    """The icon at any size. Drawn at 256 and scaled down, with less detail when small."""
    big = 256
    k = big / 256.0
    tile = pygame.Surface((big, big), pygame.SRCALPHA)
    radius = 56
    pygame.draw.rect(tile, LIP, (0, 0, big, big), border_radius=radius)
    pygame.draw.rect(tile, BASE, (0, 0, big, big - 14), border_radius=radius)
    deco = pygame.Surface((big, big), pygame.SRCALPHA)
    _wave(deco, BAND, 200, 7, k)
    _wave(deco, BAND2, 222, 6, k)
    if size >= 32:                                   # finer detail only where it can be seen
        _wave(deco, CREST, 40, 6, k, filled=False, width=5)
        _wave(deco, CREST, 62, 6, k, filled=False, width=3)
        for x, y, r in ((40, 120, 10), (30, 160, 6), (216, 112, 8), (226, 150, 12), (204, 182, 5), (52, 186, 5)):
            pygame.draw.circle(deco, BUBBLE, (x, y), r)
            pygame.draw.circle(deco, BUBBLE_EDGE, (x, y), r, max(2, r // 4))
        for x, y, s in ((44, 86, 9), (212, 80, 11), (128, 234, 7)):
            _sparkle(deco, x, y, s)
    mask = pygame.Surface((big, big), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, big, big - 14), border_radius=radius)
    deco.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    tile.blit(deco, (0, 0))
    egg = _egg_sprite()
    scale = 7 if size >= 32 else 8                    # a touch bigger when tiny
    egg = pygame.transform.scale(egg, (egg.get_width() * scale, egg.get_height() * scale))
    shadow = pygame.Surface((egg.get_width(), 14), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (60, 44, 110, 110), shadow.get_rect())
    tile.blit(shadow, shadow.get_rect(center=(128, 120 + egg.get_height() // 2)))
    tile.blit(egg, egg.get_rect(center=(128, 116)))
    if size == big:
        return tile
    return pygame.transform.smoothscale(tile, (size, size))
