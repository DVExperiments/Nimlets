"""Tiny chiptune sound effects generated at startup - no audio files needed."""
import array
import random

import pygame

C4, D4, E4, F4, G4, A4, B4 = 262, 294, 330, 349, 392, 440, 494
C5, D5, E5, F5, G5, A5, B5, C6, E6 = 523, 587, 659, 698, 784, 880, 988, 1047, 1319

SOUNDS = {
    "button": ([(A5, 0.035)], "square", 0.22),
    "select": ([(E5, 0.025)], "square", 0.15),
    "eat": ([(E4, 0.06), (0, 0.03), (G4, 0.06), (0, 0.03), (E4, 0.07)], "square", 0.3),
    "happy": ([(C5, 0.07), (E5, 0.07), (G5, 0.07), (C6, 0.12)], "square", 0.25),
    "call": ([(B5, 0.09), (0, 0.06), (B5, 0.09), (0, 0.06), (B5, 0.09)], "square", 0.25),
    "sick": ([(G4, 0.12), (F4, 0.12), (E4, 0.12), (D4, 0.22)], "tri", 0.4),
    "evolve": ([(C4, 0.06), (E4, 0.06), (G4, 0.06), (C5, 0.06), (E5, 0.06), (G5, 0.06),
                (C6, 0.06), (G5, 0.06), (C6, 0.06), (E6, 0.32)], "square", 0.25),
    "hatch": ([(G5, 0.05), (0, 0.05), (G5, 0.05), (0, 0.05), (C6, 0.2)], "square", 0.25),
    "success": ([(E5, 0.08), (G5, 0.08), (C6, 0.08), (E6, 0.2)], "square", 0.25),
    "fail": ([(G4, 0.12), (E4, 0.12), (C4, 0.26)], "tri", 0.4),
    "point": ([(G5, 0.05), (C6, 0.08)], "square", 0.22),
    "miss": ([(E4, 0.06), (C4, 0.1)], "tri", 0.35),
    "sleep": ([(C5, 0.2), (G4, 0.2), (E4, 0.36)], "tri", 0.35),
    "clean": ([(0, 0.25)], "noise", 0.12),
    "refuse": ([(A4, 0.07), (0, 0.04), (F4, 0.12)], "square", 0.22),
    "praise": ([(G5, 0.06), (C6, 0.1)], "tri", 0.4),
    "scold": ([(G4, 0.14), (E4, 0.2)], "square", 0.25),
    "heal": ([(C5, 0.06), (G5, 0.06), (C6, 0.16)], "tri", 0.4),
    "poop": ([(150, 0.08), (110, 0.1)], "square", 0.2),
    "chirp": ([(E6, 0.04), (0, 0.05), (E6, 0.05)], "square", 0.16),
    "trill": ([(C6, 0.03), (E6, 0.03), (C6, 0.03), (E6, 0.03), (C6, 0.03), (E6, 0.05)], "tri", 0.35),
    "tap": ([(0, 0.04)], "noise", 0.18),
    "chirp1": ([(E6, 0.05)], "square", 0.16),
    "coin": ([(B5, 0.05), (E6, 0.12)], "square", 0.2),
    "shop": ([(C6, 0.05), (E6, 0.05), (G5, 0.08)], "tri", 0.3),
    "rustle": ([(0, 0.18)], "noise", 0.1),
    "chime": ([(C6, 0.18), (G5, 0.18), (E5, 0.3)], "tri", 0.3),
    "clink": ([(C6 * 2, 0.03), (0, 0.03), (G5 * 2, 0.05)], "tri", 0.25),
    "puff": ([(0, 0.1)], "noise", 0.08),
    "bird": ([(E6, 0.04), (C6 * 2, 0.04), (E6, 0.06)], "tri", 0.25),
    "tune": ([(C5, 0.15), (E5, 0.15), (G5, 0.15), (E5, 0.15), (C6, 0.3)], "tri", 0.3),
    "coo": ([(G5, 0.12), (E5, 0.16)], "tri", 0.35),
    "page": ([(G5, 0.04), (C6, 0.06)], "tri", 0.3),
    "depart": ([(G5, 0.25), (E5, 0.25), (C5, 0.25), (G4, 0.25), (C5, 0.5)], "tri", 0.35),
}


class Audio:
    def __init__(self, enabled=True, lazy=False):
        """lazy=True (the web version) makes each sound the first time it's played, instead of all
        of them at start-up: generating samples in Python is slow in a browser."""
        self.enabled = enabled
        self.ok = False
        self.lazy = lazy
        self.sounds = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            init = pygame.mixer.get_init()
            if init and init[1] in (-16, 16, 32):
                self.rate, self.size, self.channels = init
                if not lazy:
                    for name, (notes, wave, vol) in SOUNDS.items():
                        self.sounds[name] = self._make(notes, wave, vol)
                self.ok = True
        except (pygame.error, ValueError, TypeError) as exc:
            print(f"[audio] sound disabled: {exc}")
            self.ok = False

    def _make(self, notes, wave, volume):
        is_float = self.size == 32
        buf = array.array("f" if is_float else "h")
        rnd = random.Random(1)
        for freq, dur in notes:
            n = int(self.rate * dur)
            attack = self.rate * 0.004
            release = self.rate * 0.02
            for i in range(n):
                if wave == "noise":
                    s = rnd.uniform(-1, 1) * (1 - i / n)
                elif freq <= 0:
                    s = 0.0
                else:
                    ph = (i * freq / self.rate) % 1.0
                    s = (1.0 if ph < 0.5 else -1.0) if wave == "square" else 4 * abs(ph - 0.5) - 1
                env = min(1.0, i / attack) * min(1.0, (n - i) / release)
                v = s * env * volume
                sample = v if is_float else int(v * 32767)
                for _ in range(self.channels):
                    buf.append(sample)
        return pygame.mixer.Sound(buffer=buf.tobytes())

    def play(self, name):
        if not (self.enabled and self.ok):
            return
        if name not in self.sounds and self.lazy and name in SOUNDS:
            try:
                self.sounds[name] = self._make(*SOUNDS[name])
            except (pygame.error, ValueError, TypeError):
                return
        if name in self.sounds:
            self.sounds[name].play()

    def toggle(self):
        self.enabled = not self.enabled
        return self.enabled
