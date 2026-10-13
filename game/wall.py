"""Cleaning the wall, and what the pet makes of it.

The wall drawing is shared by you and every pet that has lived in the room.
You can wipe it with a sponge (Clean, when the room itself is already tidy).

What the pet learns depends on *whose* marks you wipe and *how fresh* they
were, measured in game time:

    fresh   (< FRESH_HOURS)   it just made that. Wiping it reads as "don't".
    recent  (< RECENT_HOURS)  a milder version of the same lesson.
    old     (older)           tidying up. No lesson about drawing.

Your own coral marks and older generations' drawings teach it nothing about
drawing, though a pet that once studied an ancestor's drawing may be sad to
see the last of it go.

The lesson lives in the "wall_ok" belief (-1..1). Living.pick() reads it:
a pet that believes drawing is unwelcome draws far less while you're
watching - and a little *more* while you're away. Drawings that survive,
and you drawing on the wall yourself, slowly nudge the belief back up.
"""

from .behaviour import act

FRESH_HOURS = 1.0
RECENT_HOURS = 24.0
SURVIVE_HOURS = 6.0       # its drawing has stayed up this long: it's welcome
FULL_LESSON = 12          # pixels of fresh drawing that count as a full lesson
SECRET_BELIEF = -0.35     # below this it starts drawing in secret


def classify(removed, generation, now):
    """Sort wiped pixels by whose they were and how old."""
    out = {"fresh": 0, "recent": 0, "old": 0, "yours": 0, "ancestors": {}}
    for p in removed:
        gen = p[3]
        if gen == 0:
            out["yours"] += 1
        elif gen != generation:
            out["ancestors"][gen] = out["ancestors"].get(gen, 0) + 1
        else:
            t = p[4] if len(p) > 4 else 0.0      # pre-1.6 saves: no timestamp, so treat as old
            hours = (now - t) / 3600.0 if t else 1e9
            out["fresh" if hours < FRESH_HOURS else "recent" if hours < RECENT_HOURS else "old"] += 1
    return out


def draw_factor(belief, watched):
    """How keen the pet is to draw right now, given what it has learned."""
    if belief >= 0:
        return 1.0 + 0.5 * belief
    if watched:
        return max(0.08, 1.0 + 1.2 * belief)          # it won't draw in front of you
    return 1.0 + min(0.8, -belief)                    # ...but it might while you're away


def survived(world, generation, now):
    """Pixels of this pet's drawing that have been left up for a while."""
    cutoff = now - SURVIVE_HOURS * 3600
    return sum(1 for p in world.mural if p[3] == generation and len(p) > 4 and 0 < p[4] <= cutoff)


def on_wiped(mind, removed, all_at_once=False):
    """React to a wipe. Returns a message for the status line, or None."""
    c, beh, w = mind.c, mind.beh, mind.world
    if not removed:
        return None
    now = mind.offline_wt or mind.world_time
    k = classify(removed, c.generation if c else -1, now)
    msg = None
    for gen in k["ancestors"]:                       # culture lost
        if not any(p[3] == gen for p in w.mural):
            artist = w.mural_artists.get(str(gen), "a pet from long ago")
            mind._log("wall", f"The last of {artist}'s old drawing was wiped from the wall.", "drawing", True)
    if c is None or c.stage == "egg" or beh is None:
        return None
    asleep = c.asleep or beh.tag == "outside"
    sees = 0.5 if asleep else 1.0
    tough = 1.25 - c.personality["stubbornness"] * 0.6     # stubborn pets shrug it off
    own = k["fresh"] + k["recent"]
    if k["fresh"]:
        amount = min(1.0, k["fresh"] / FULL_LESSON)
        mind.learn("wall_ok", -1.0, 0.28 * amount * sees * tough)
        mind.episodes.add("wiped", "wall_wiped", "watched you wipe away a drawing it had just made",
                          importance=0.6)
    elif k["recent"]:
        amount = min(1.0, k["recent"] / FULL_LESSON)
        mind.learn("wall_ok", -0.5, 0.12 * amount * sees * tough)
    mind.trace(["You wiped the wall",
                f"{k['fresh']} fresh / {k['recent']} recent / {k['old']} old marks of its own",
                "Drawing seems unwelcome" if own else "Just tidying"], "wall")
    if asleep:
        if own and mind.first("wiped_asleep"):
            mind.log("wall", "slept through you wiping its drawing off the wall.", "drawing")
        return None
    face = -1 if beh.x > 74 else 1
    if k["fresh"]:
        if c.personality["stubbornness"] > 0.6 or mind.emo["grumpy"] > 0.4:
            mind.emo["grumpy"] = min(1.0, mind.emo["grumpy"] + 0.35)
            beh.interject([act("refuse", 1.4, face=face, tag="reaction")])
            msg = f"{c.name} huffs. It was still working on that!"
        else:
            mind.emo["affectionate"] = max(0.0, mind.emo["affectionate"] - 0.1)
            beh.interject([act("look", 0.8, face=face, gaze="u", tag="reaction"),
                           act("sad", 2.0, tag="reaction")])
            msg = f"{c.name} watches its drawing disappear and droops a little."
        if mind.first("wiped_fresh"):
            mind.log("wall", "watched you wipe away the drawing it had only just made.", "drawing", True)
    elif k["recent"]:
        beh.interject([act("look", 1.2, face=face, gaze="u", tag="reaction")])
        msg = f"{c.name} watches you wipe the wall."
    elif k["old"] or k["ancestors"]:
        lost_studied = any(not any(p[3] == g for p in w.mural) for g in k["ancestors"]) \
            and "studied_mural" in c.firsts
        if lost_studied:
            beh.interject([act("look", 1.0, face=face, gaze="u", tag="reaction"), act("sad", 1.6, tag="reaction")])
            msg = f"{c.name} gazes at the bare patch where the old drawing used to be."
        elif not beh.reaction:
            beh.interject([act("notice", 0.6, face=face)])
    if all_at_once and not msg:
        msg = "A fresh, clean wall."
    return msg
