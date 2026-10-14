"""The pointer (v2.4): one place that knows whether you're using a mouse or a finger.

A mouse is always somewhere: it can rest, hover and drift towards a button, and the
pet can watch all of that. A finger is only *there* while it touches the glass. When
it lifts, the browser (and SDL) still report the last tap position as "the mouse",
so before v2.4 the pet saw a phantom cursor parked wherever you last tapped: resting
on Feed forever, building trust it hadn't earned, keeping the last tapped tab lit.

The rule here is simple: in touch mode the pointer exists while a finger is down,
plus a short afterglow at the spot it lifted from (so the pet's eyes can linger
there), and then it's gone. Mouse mode behaves exactly as before.

The mode follows the last input, per event, so a touchscreen laptop can switch
freely. Touch is recognised from SDL's FINGER* events and from mouse events SDL
synthesises from touches (they carry ``touch=True`` in pygame-ce).
"""
import pygame

AFTERGLOW = 0.8          # seconds the pet can still "see" where a finger lifted
NOWHERE = (-10000, -10000)


class Pointer:
    def __init__(self):
        self.mode = "mouse"
        self.down = False            # a finger is touching (touch mode only)
        self.pos = None              # last known finger position, window pixels
        self.since_lift = 99.0
        self.lifted = False          # a finger lifted since the last frame
        self.focused = True

    # ------------------------------------------------------------------ events
    @property
    def touch(self):
        return self.mode == "touch"

    def on_event(self, ev, size=None):
        """Watch every event. Returns True if it was a touch-originated event."""
        et = ev.type
        if et in (pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION):
            w, h = size or (1, 1)
            pos = (int(ev.x * w), int(ev.y * h))
            self.mode = "touch"
            if et == pygame.FINGERDOWN:
                self._press(pos)
            elif et == pygame.FINGERUP:
                self._lift(pos)
            elif self.down:
                self.pos = pos
            return True
        if et in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
            if getattr(ev, "touch", False):
                self.mode = "touch"
                if et == pygame.MOUSEBUTTONDOWN:
                    self._press(ev.pos)
                elif et == pygame.MOUSEBUTTONUP:
                    self._lift(ev.pos)
                elif self.down:
                    self.pos = ev.pos
                return True
            if et == pygame.MOUSEMOTION or self.mode == "touch":
                self.mode = "mouse"      # a real mouse moved (or clicked): back to mouse mode
                self.down = False
        return False

    def _press(self, pos):
        self.down = True
        self.pos = pos
        self.since_lift = 99.0

    def _lift(self, pos):
        if self.down:
            self.lifted = True
        self.down = False
        self.pos = pos
        self.since_lift = 0.0

    def tick(self, dt):
        """Once per frame, after events and updates."""
        self.lifted = False
        if not self.down:
            self.since_lift += dt

    # ------------------------------------------------------------------ queries
    def present(self, afterglow=False):
        """Where the pointer is, in window pixels, or None if there isn't one.

        Mouse: wherever the mouse is, while it's over a focused window.
        Touch: where the finger is while it's down; with ``afterglow``, also for a
        moment after it lifts."""
        if self.mode == "mouse":
            return pygame.mouse.get_pos() if pygame.mouse.get_focused() else None
        if self.down or (afterglow and self.since_lift < AFTERGLOW):
            return self.pos
        return None

    def hover_pos(self):
        """For hover highlights: the mouse, or a finger that's down. Never a lifted finger."""
        p = self.present()
        return p if p is not None else NOWHERE

    def pressed(self):
        if self.mode == "mouse":
            return bool(pygame.mouse.get_pressed()[0])
        return self.down


POINTER = Pointer()


def hover_pos():
    return POINTER.hover_pos()
