"""Sizing the browser canvas so the game stays sharp on phones (v2.5).

pygbag draws the game into a canvas exactly as big as ``set_mode`` asked for, then
stretches that canvas with CSS to fill the browser window. Before v2.5 the canvas
was always 960 x 760, so on a phone it was stretched by an awkward fraction (and
squashed into a landscape box even when the phone was upright): soft, blurry pixels.

Now the canvas matches the window's shape and its real pixels: CSS size x the
screen's pixel density (``devicePixelRatio``), divided by a whole number ``k`` when
that would be too many pixels to draw smoothly. With ``k`` = 2 each canvas pixel
covers exactly 2 x 2 screen pixels, and the canvas is set to ``image-rendering:
pixelated`` so the browser enlarges it without blurring. The layout then picks the
biggest whole-number room that fits, so pixels stay square and crisp either way.

Who sizes what (v2.5.1). Three things can change the canvas, and before v2.5.1 they
fought: the game sets its *drawing* size with ``set_mode``; pygbag sets its *on-screen*
size with CSS; and SDL, for a window made RESIZABLE, quietly resets the drawing size
to the on-screen size on every browser resize event. A phone fires several of those
while it turns, so SDL could shrink the drawing area after the game had chosen it,
and a tall frame drawn into a shorter canvas lost its top. So in the browser the
window is never RESIZABLE (``FLAGS``): the game alone owns the drawing size, pygbag
alone owns the on-screen size, and the game checks the real canvas, not just its
own idea of it.

Where it sits on the page (v2.5.2). pygbag also *places* the canvas: it centres it in
a box on the page. After a phone turned back upright that box could still have the
landscape height, so the tall canvas was centred on a short box, with its top above
the screen and an empty gap below. So the game now tells pygbag it manages the canvas
itself (pygbag's ``user_canvas_managed`` switch) and places it directly: pinned to the
screen (``position: fixed``), as big as fits without changing its shape, and centred,
worked out from the window's size every time it changes.

Everything that touches the browser is wrapped: if anything goes wrong, the game
keeps its current canvas (as before) instead of risking a blank page.
"""
FLAGS = 0                   # never pygame.RESIZABLE in the browser (see above)
BUDGET = 1_200_000          # canvas pixels; the web version ran smoothly at 960 x 760 (about 0.73M)
MIN_SIDE = 320


def canvas_size(css_w, css_h, dpr=1.0, budget=BUDGET):
    """(width, height, k): the canvas for a window of css_w x css_h CSS pixels.

    k is the smallest whole number that keeps the canvas within ``budget`` pixels,
    so each canvas pixel covers k x k of the screen's own pixels."""
    dpr = dpr if dpr and dpr > 0 else 1.0
    dev_w, dev_h = max(1.0, css_w * dpr), max(1.0, css_h * dpr)
    k = 1
    while k < 8 and (dev_w / k) * (dev_h / k) > budget:
        k += 1
    w, h = int(round(dev_w / k)), int(round(dev_h / k))
    if min(w, h) < MIN_SIDE and k > 1:              # never so coarse that the device can't fit
        k -= 1
        w, h = int(round(dev_w / k)), int(round(dev_h / k))
    return max(w, 1), max(h, 1), k


def _window():
    try:
        import platform
        return platform.window
    except Exception:
        return None


def browser_window():
    """(css width, css height, devicePixelRatio) of the browser window, or None."""
    win = _window()
    if win is None:
        return None
    try:
        w, h = float(win.innerWidth), float(win.innerHeight)
        dpr = float(getattr(win, "devicePixelRatio", 1) or 1)
    except Exception:
        return None
    if w < 50 or h < 50:
        return None
    return w, h, dpr


def wanted_size():
    """The canvas size the browser window wants right now, or None if unknown."""
    bw = browser_window()
    if bw is None:
        return None
    w, h, _ = canvas_size(*bw)
    return w, h


def canvas_buffer():
    """The real canvas's drawing size in the page, or None if it can't be read."""
    win = _window()
    try:
        return int(win.canvas.width), int(win.canvas.height)
    except Exception:
        return None


def settle():
    """Keep the page itself still: no scrolling, so the canvas can't be pushed off the top."""
    win = _window()
    if win is None:
        return
    try:
        win.document.documentElement.style.overflow = "hidden"
        win.document.body.style.overflow = "hidden"
    except Exception:
        pass
    try:
        win.scrollTo(0, 0)
    except Exception:
        pass


def fit_rect(win_w, win_h, canvas_w, canvas_h):
    """(left, top, width, height) in CSS pixels: the canvas as big as fits, same shape, centred."""
    ar = canvas_w / max(1, canvas_h)
    w = min(win_w, win_h * ar)
    h = w / ar
    return (win_w - w) / 2, (win_h - h) / 2, w, h


def take_over():
    """Tell pygbag the game places and sizes the canvas itself, so it stops doing it."""
    win = _window()
    if win is None:
        return
    for owner in ("python", None):
        try:
            cfg = getattr(win, owner).config if owner else win.config
            cfg.user_canvas_managed = 1
        except Exception:
            pass


def place(canvas_size):
    """Pin the canvas to the screen, centred and as big as fits. Returns what it applied
    (window size, canvas size), so callers can skip it when nothing has changed."""
    win = _window()
    bw = browser_window()
    if win is None or bw is None or not canvas_size:
        return None
    win_w, win_h, _ = bw
    left, top, w, h = fit_rect(win_w, win_h, *canvas_size)
    try:
        st = win.canvas.style
        st.position = "fixed"
        st.margin = "0px"
        st.right = st.bottom = "auto"
        st.left, st.top = f"{left:.2f}px", f"{top:.2f}px"
        st.width, st.height = f"{w:.2f}px", f"{h:.2f}px"
        st.imageRendering = "pixelated"
    except Exception:
        return None
    return (win_w, win_h, tuple(canvas_size))


def after_resize(canvas_size=None):
    """After the canvas changes: take it over from pygbag and place it."""
    take_over()
    return place(canvas_size)
