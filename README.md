# Nimlets

**Version 2.6.0 "Front Door"** - see [CHANGELOG.md](CHANGELOG.md) for the full history. Releases are packaged as `nimlets_vX.Y.Z.zip` and published as GitHub Releases; the version is also shown in the window title and at the bottom of Settings.

A small, charming virtual-pet game in Python + pygame-ce. Hatch an egg, care for one little creature in short sessions, and watch it grow into one of 28 forms across two family trees (including 4 secret ones) depending on how you raise it. When it is grown, it leaves an egg behind and the next generation begins.

Everything — creatures, room, icons, sound effects and even the pixel font — is generated in code. No image, audio or font files, no internet, no server.

## Running it (Windows)

1. Install **Python 3.11 or newer** from python.org (tick "Add Python to PATH").
2. Double-click **`run_game.bat`**. The first launch installs pygame-ce automatically.

Or from a terminal in this folder:

```
pip install -r requirements.txt   # installs pygame-ce
python main.py
```

**Testing mode:** double-click `run_test_mode.bat` (600× speed, with its own separate `test_save.json`) or run `python main.py --speed 600 --test-save`. At 600×, the egg hatches in a fraction of a second and the baby stage lasts six seconds; a full lifecycle takes around 30 real minutes. Press **T** in-game to cycle 1× / 10× / 60× / 600× / 3600×.

Other options: `--reset` (fresh game; the old save is backed up), `--mute`, `--save PATH`.

**Where your saves live.** Saves, preferences, backups and exported reports are kept in your own **Nimlets folder**, not the game folder, so they survive updates and reinstalls:
- Windows: `%APPDATA%\Nimlets`
- macOS: `~/Library/Application Support/Nimlets`
- Linux: `~/.local/share/Nimlets`

**Settings → Open folder** takes you there. The first time v2.0 or later runs, it *copies* any saves from the old `saves` folder inside the game folder (the originals are left where they were). Set `NIMLETS_DATA_DIR` to use a different folder, for example a portable copy on a USB stick.

## Licence

Nimlets is **free to play, all rights reserved**. Anyone can download it from this page and play it for free, but it may not be copied, re-uploaded, modified or sold without permission. See [LICENSE](LICENSE). To ask for permission, open an issue.

## Building the standalone game (Nimlets.exe)

Players don't need Python: they just run **Nimlets.exe**. There are two ways to build it, and both use the same script, `tools/build_exe.py`, which runs the tests, draws the icon, builds a single-file game with PyInstaller, test-runs the result, and zips it with a short read-me for players.

- **On your PC:** double-click **`build_exe.bat`**. It installs pygame-ce and PyInstaller if needed, builds, and opens the `dist` folder with `Nimlets.exe` and `Nimlets-vX.Y.Z-windows.zip`.
- **On GitHub:** publish a **Release** and GitHub builds the .exe on its own Windows machines and attaches the zip to that release, usually within ten minutes. You can also build on demand from the **Actions** tab (*Build Windows .exe* → *Run workflow*) and download it from the run's *Artifacts*. The recipe is `.github/workflows/build-windows.yml`.

If any test fails, no build is made. Always change the code and rebuild; never edit a build. Windows may show "Windows protected your PC" the first time someone runs the .exe, because it isn't signed with a paid certificate; *More info → Run anyway* starts it.

## Playing in a browser (and on phones)

**Play it at https://dvexperiments.github.io/Nimlets/**, on a computer, tablet or phone. No app store and no download.

The same game also runs in a web browser, built with [pygbag](https://pypi.org/project/pygbag/). GitHub builds it and publishes it on **GitHub Pages** every time the main branch changes.

- **The home page (v2.6).** The address opens a small home page: the name, one Nimlet growing up from egg to adult, a **Play now** button, how to keep it like an app, and the collection of forms to find. It loads straight away; the game's own download only starts when you press Play. A returning player's button names their pet ("Visit Pichan"). The page lives in `site/` and its pictures are drawn at build time by the game's own sprite code.
- **The game is at `/play/`.** Old links to the site still work, one tap further. Saves belong to the whole site, so moving the game there kept every pet.
- **Keep it like an app (v2.6).** Nimlets can be added to a home screen (or installed from Chrome and Edge on a computer) and then opens full screen with its own icon, straight into the game. Chrome and Edge get an **Install Nimlets** button on the home page. The first time you tap or press a key in the game, it asks the browser to keep its storage, so the pet isn't cleared to save space.
- **On iPhone and iPad, add it to the Home Screen before hatching your egg** and always play from the icon. The Home Screen app has its own storage, separate from Safari, so a pet started in Safari stays in Safari. Safari may also clear a website's saved data after about a week away; the Home Screen app keeps it. The home page explains this.
- **One-time setup:** in the repo's *Settings → Pages → Build and deployment*, set *Source* to **GitHub Actions**. The workflow is `.github/workflows/build-web.yml`; the address appears on the run's summary in the *Actions* tab.
- **On your own computer:** `python tools/build_web.py --serve` builds everything and serves it at http://localhost:8000. pygbag downloads its browser runtime while building, so this needs an internet connection. `python tools/build_web.py --site-only --serve` builds just the home page, with a stand-in for the game, and works offline.
- **In the browser your pet is saved in the browser itself.** Clearing the site's data clears your pet, and a browser save is separate from the one on your computer. Reports and logs can't be exported from the browser version yet.
- **It works on phones and computers** (tested in Chrome on a PC and on a phone).
- **Touch (v2.4):** with a finger, the pet only sees you while you're touching. Tap the pet, the room and its things as you would click them. Tabs press in and act when you lift (slide off to cancel). Drag on the lower wall to draw, drag the bed to move it, and drag anywhere else in the room to make a gesture; lifting your finger ends it.
- **Phone layouts (v2.5):** hold the phone upright and the room spans the screen, with the eight tabs in a 4 × 2 grid beneath it and the buttons in thumb reach. Turn it on its side and the room sits in the middle with four tabs either side. It switches by itself when you turn the phone (or choose in Settings → Screen).
- **Sharp on phones (v2.5):** the game draws at the phone's real pixel size (or exactly half of it, when that would be too many pixels to draw smoothly), so the pixel art stays crisp instead of being stretched.
- **If it ever shows a problem,** the web version puts the error on screen, and the browser's developer console (Ctrl+Shift+J in Chrome) shows `[nimlets]` progress lines.

## How to play

The first time you play, a short **welcome tour** (five pages) introduces the egg, the hearts, the buttons, how your pet notices you, and how time works. Game time holds still while it's open, so the egg can't hatch mid-tour. For your first days, a few **one-time hints** appear in the message line the first time something important happens: its first call for attention, its first mess, its first bedtime, its first drawing on the wall, and the first time it grows up. Players who already had a save don't see either. **Settings → Welcome tour** shows the tour again any time.

The game looks like a little handheld device. The room is its screen, the eight action **tabs** run down both sides of it, the **hearts** sit in a strip above it, messages appear on the small green screen below it, and along the bottom are the **A / B / C** buttons with Settings and Sound on the left and Speed and Pause on the right.

| Button | Key | What it does |
|---|---|---|
| Feed | 1 | Rice Ball, Fish, Berries (meals) or Cake (snack, more happiness, more weight). The food goes into the bowl and your pet trots over to eat it. **Shop** at the bottom of the list. |
| Play | 2 | Three mini-games, each under a minute. Winning earns coins. **Shop** at the bottom of the list. |
| Clean | 3 | Flush away mess. When the room is already tidy, wipe the **wall** instead: a **Sponge** for bits, or **Wipe it all**. |
| Medicine | 4 | Cure illness (sometimes needs two doses) |
| Train | 5 | **Praise** good behaviour, **Scold** mischief |
| Lights | 6 | Turn the lights off when it sleeps |
| Status | 7 | Hearts, discipline, weight, age, learned favourites |
| Records | 8 | A quick view on the screen: Collection, family tree, care records, the **Diary**, **Bond** (Shared Memories and the Observation Lab), new generation. **Expand** (or **E**) opens the full Records book. |

**A / B / C** (click them, or press the A, B and C keys): **A** moves along the tabs, **B** chooses the highlighted one, and **C** goes back (closes a menu or panel, or dismisses a message). In menus A moves down and B chooses; in mini-games A, B and C are left, action and right. Clicking a tab or pressing its number works as before.

Other controls: **drag the bed** to move it (your pet will notice, eventually). **F9** opens Observation Mode. **Click and drag on the lower part of the wall** to draw (your marks are coral; your pet may answer). To clean the wall, press **Clean** while the room is tidy, pick **Sponge** and drag over the marks; right-click, **Esc** or **Clean** puts the sponge away. **Click the pet** to pet it. **Click the ball** to kick it. **Click a gift** to keep it. **M** toggles sound, **P** pauses time, **T** changes speed, **S** or **F5** saves, and **O** opens Settings. **Esc** closes menus. In menus, use arrows and Enter or the number keys. In mini-games, use ←/→ (or A/D) and Space.

**Hearts:** the strip above the screen shows **Hunger, Happy and Health**, 6 hearts each. You can change the number of slots with `heart_slots` in `config/settings.json`.

### Coins and the shop

Win a mini-game to earn **coins**: 3, plus a bonus for extra points. Games your pet starts itself pay a coin or two when they go well. Spend coins via the **Shop** button at the bottom of the Feed or Play list. It opens a shop window with special **Treats** and **Toys**. Everything is used the moment you buy it: treats go into the bowl, and toys appear in the room for your pet to play with.

Each pet has hidden tastes. These depend on its personality and family line (water pets tend to like Kelp Crisps), plus some pure individuality; Fire Pepper is love-it-or-hate-it. How much it enjoys something on a given day also depends on novelty, boredom (the same toy every day gets old) and mood. So it learns what it likes, and two pets react to the same gift very differently. After a couple of tries the shop shows "loves this" or "not keen", and the Diary notes new favourites.

### An interactive room

Click things in the room:
- **Plant:** it shakes. Sometimes a trinket stuck underneath tumbles out, and a pet with a secret stash may rush over to guard it.
- **Window:** a bird visits by day; a shooting star crosses it at night.
- **Lamp:** it swings.
- **Clock:** it chimes.
- **Picture:** it goes crooked, and tidy pets may straighten it.
- **Bowl:** it clinks, and hungry pets come running.
- **Bed cushion:** it puffs up. Drag the bed to move it.

Your pet reacts in its own way each time.

### The Diary and "While you were away"

Interesting things your pet does are written to a **Diary** (Records → Diary, newest first; scroll with the mouse wheel). Anything that happened while you weren't watching shows up in a **"While you were away"** summary. This appears when you reopen the game, switch back to its window after two minutes or more, or return after two minutes without touching anything. While the game is closed, a small "offline life" simulation runs as part of the normal capped catch-up. Its entries are real: if the diary says it added to its drawing or moved its bed, you'll find the drawing or the bed there.

### Settings (gear icon, or O)

- **Theme colour.** Choose "Pet colour" (the device matches your pet and changes each generation), Peach, Lemon, Mint, Sky, Lavender or Rose. Use ←/→ to cycle.
- **Appearance.** Light or Dark (**D**), and **Pixel text** or **Smooth text**. Pixel text is the game's own pixel font; switch to smooth text if you find it easier to read.
- **Shell.** Click the left or right half to cycle through *Match my pet* and the shells you've unlocked (see *Shells* below). Sound has its own button on the device, or press **M**.
- **Screen.** *Auto* (the default) picks the layout that gives the biggest crisp room for the window's shape: the classic handheld on a computer, the upright layout on a phone held upright, and the wide layout on a phone on its side. *Portrait* always uses the upright layout (centred on a wide window). *Landscape* uses whichever of the classic and wide layouts fits better.
- **Wandering** (on by default): lets a pet that's used to going outside take long walks around the whole device. See "The Frontier" below.
- **Open folder** opens your Nimlets folder, with saves, backups and exported reports. **Welcome tour** replays the first-time tour.
- **Reset.**
  - *New egg (keep records)* starts over but keeps your collection, family history and gifts.
  - *Erase everything* wipes the pet and all records.

  Both ask for confirmation first, and the old save is always backed up as `savegame.json.reset-backup`.

Theme choices live in `preferences.json` in your Nimlets folder, so they survive resets.

**Tips**
- The red **!** light beside the name and a flashing tab mean it needs something. Answer within about 15 game-minutes to avoid a hidden care mistake.
- Sometimes it calls for attention when it needs nothing. That's mischief, so **Scold** it. Praise it right after it does something good, like winning a game or eating food it dislikes.
- Praise it for a habit (dancing, sitting) and it will do that more often.
- Mistakes, discipline, weight, happiness, and personality all shape what it evolves into.

### The Records book

The Records button shows a **quick view** right on the screen. Press **Expand** (or **E**) for the full **Records book**: an open storybook over the whole window, with six coloured tabs.

- **Collection** shows every form, with silhouettes for ones you haven't met. The facing page tracks progress on each family line and the secrets, your longest-lived pet and your rare finds.
- **Family** lists every generation, with its sprite, evolution path, lifespan and how its life ended. The facing page covers the current pet: personality, family line, markings, colouring, what earlier generations left in the room, and *Begin a new generation*.
- **Care** has this life's care records and favourites, totals across every generation, coins, and the gifts your pets gave you.
- **Diary** shows the signals you share and the moments worth remembering, plus the full diary grouped by day with important moments starred. Scroll with the mouse wheel or Up and Down.
- **Bond** holds your Shared Memories as a timeline. The facing page shows how your pet sees you, its language, its rituals, and buttons for the Observation Lab and *Export report*.
- **Shells** shows every shell, with the locked ones' hints. Preview one, *Wear this shell*, or tick *Match my pet*.

Turn pages with the tabs, Left and Right, or **A**. **Esc**, **C** or the close button go back to the quick view.

### Shells

The device's shell is decorated, and new designs are unlocked by your family's history:

| Shell | Unlocked by |
|---|---|
| Classic | Always available; takes the theme colour |
| Tide (bubbles, kelp, fish) | Hatching your first Dewdrop (water line) |
| Meadow (leaves, flowers, sprouts) | Hatching your first Pipling (land line) |
| Starlight (stars, moon, a ringed planet) | Raising a Celestine or Aurora |
| Glitch (scanlines and stray pixels) | Raising a Glitchling |
| Spore (mushrooms and spores) | Raising a Mycelia |
| Patchwork (a family quilt) | Reaching generation 3 |
| Heirloom (cream, gold and pearls) | Reaching generation 5 |
| Family Tree (branches climbing a wooden shell) | Reaching generation 10 |
| Golden, Void, Chimera, Pastel, Static | Hatching a Golden, Void, Chimera, Pastel or Glitch egg |

New unlocks are announced and written in the Diary. By default the shell is **Match my pet**: it follows your pet's secret form if it has one, otherwise its rare egg, otherwise its family line, using the first of those you've unlocked. Eggs wear Classic so the line stays a surprise. Pick a specific shell on the Records book's **Shells** page, or in Settings. Unlocks come from the collection records, so older saves get the shells they've already earned, and *Erase everything* locks them again.

## The Living Pet System

On top of the care loop sits a small hidden "mind" (`game/living.py`). It never shows a stat. Everything comes through as behaviour.

**It notices you.** It only uses this game's own window: cursor position inside the screen, window focus, mouse entering or leaving, and clicks. There's no camera, microphone, keylogging, or looking at other apps.

- Its eyes follow your cursor some of the time. Fast movement catches its eye, and hovering over it makes it look up at you.
- A shy or observant pet sometimes looks away, as if it wasn't watching.
- When you come back, after switching windows or after 45 seconds without input, it decides how to greet you. It might run over and wave, peek out from behind the plant, glance and carry on, or barely notice through a yawn.
- Clicking the room makes it turn toward the sound. Clicking repeatedly makes it curious, or annoyed if it's stubborn.
- Wiggling the cursor around makes it tilt its head.

**Watched or alone.** It behaves differently depending on whether you're there. When you leave, it carries on with its own agenda: dozing, playing with its ball, gazing out of the window, or doing something silly when it thinks nobody is looking. When you return it doesn't reset to idle. You may catch it mid-activity; it stops, looks at you, and carries on. If you catch it doing something silly, it looks embarrassed.

**It remembers.**
- **Routines.** If you usually visit around a certain hour, after a few days it starts waiting at the front of the room around then.
- **Neglect.** Care mistakes make it wary for a while; this fades over game time.
- **Affection.** Petting and praise make it approach your cursor more readily.
- **Associations.** After several doses of medicine it gets nervous when you hover over Medicine. If it's hungry it gets excited when you hover over Feed.
- **Favourite places.** It keeps favourite spots and usually sleeps in its bed.

**It has its own agenda.**
- It inspects the food bowl, pushes its ball around, rests on its cushion, ponders, and hums when content.
- It gets distracted halfway across the room, or changes its mind and turns around.
- Some of these chances are tied to time without input, so a pet left alone for long gets bored and makes its own fun.

**Hidden emotions.** Excited, affectionate, grumpy, curious, lonely and mischievous rise and fade within about a minute. Shy, sleepy, content and playful come from its current state. Together they shape what it chooses to do and how its face looks, so a hungry pet can still be thrilled to see you.

**Quirks.** Each pet gets three hidden quirks, appearing at the baby, child and teen stages. They are chosen from Observer, Troublemaker, Clingy, Independent, Sleepyhead, Show-off, Shy and Explorer, are never displayed, and you discover them by watching.
- A Show-off performs tricks when you hover nearby. Praise it straight after and it counts as good behaviour.
- A Troublemaker pretends to sleep and hides its ball behind the plant.

**Rare moments.**
- Peekaboo behind the plant.
- Little gifts after several days of good care: a flower, leaf, drawing or pebble, counted in Records.
- Dream bubbles about recent food, games or praise, and occasionally something strange.
- Zoomies, failed attempts to balance on the food bowl, finding something on the floor, and long window-gazing on rainy days.

A cooldown of several minutes keeps these rare.

## Artificial life: is it deciding, or following instructions?

The newest layer turns Nimlets into a small experiment in artificial life. None of it is AI in the modern sense. It's a handful of hidden numbers, counters and hand-written rules, and that's deliberate. The aim is for its behaviour to be just interesting enough that you sometimes wonder whether it's choosing. None of it adds care work for you.

**Autonomy.**
- **Avoidance:** a pet that doesn't trust your cursor backs away or hides. If you leave the cursor resting quietly near it, it slowly becomes braver.
- **Refusing suggestions:** kick its ball and it may look at the ball, look at you, shake its head, and walk off.
- **Guarding its spot:** it gets annoyed if you click near its favourite place while it's resting there.
- **Rearranging its room:** it drags its bed somewhere it prefers.
- **Bedtime ritual:** it develops a little routine before sleeping.
- **Solitude:** sometimes it just sits alone.

**Creations.** It makes things without being asked:
- a drawing on the wall, added to over days in its own style
- a collection of found trinkets
- a nest around its bed
- invented games, such as bouncing the ball off the wall or trying to get it into the food bowl

These belong to the **room**, not the pet, so they survive evolution and generations.

**Cleaning the wall (v1.6).** The drawing can get busy over time, so you can wipe it (Clean, when the room is tidy). What your pet makes of that depends on *whose* marks you wipe and *how fresh* they were:
- Wiping something it drew **within the last game-hour** reads as "please don't". Do that a few times and it decides you don't want it drawing on the wall. It then rarely draws while you're watching... and sometimes draws while you're away instead.
- Wiping marks from **earlier today** is a milder version of the same lesson.
- Wiping **old** marks, or your own coral ones, is just tidying, and teaches it nothing.
- Stubborn pets shrug it off more; a sleeping pet only half notices.
- Leaving its drawings up for a few hours, or drawing on the wall yourself, slowly persuades it that drawing is welcome again.
- Wiping away the last of an *ancestor's* drawing is noted in the Diary, and a pet that once studied that drawing may be sad to see it go. A new pet may study the drawing its predecessor left and add to it, or play an old invented game "picked up from the room". It's a tiny culture.

**Beliefs.** Each pet keeps learned associations:
- the cursor near Feed means food is coming
- being touched is nice, or overwhelming
- the bed is safe
- the ball is fun
- clicked things move
- the room has edges, and those edges aren't always solid
- its drawings on the wall are welcome, or not (see *Cleaning the wall*)

When it's unsure, it tests things. It may tap its bowl, look at you, and wait, and whether you feed it changes what it believes. The first time a belief becomes firm, the Diary notes it.

**A shared language.** It has a few signals: chirps, a trill, a hop-and-look, a wiggle, tapping the bowl, nudging the ball toward you, and drawing a mark on the floor. When it wants food, play or attention it tries one, glancing at the thing it means. If you respond in the right way soon after, that signal is reinforced; ignored signals fade. Over days you settle on shared signals, listed at the top of the Diary as "Signals you share". Different pets prefer different signals, some vocal and some gestural.

**Anomalies.**
- **Rare eggs:** Golden, Void, Chimera (mixed body parts from different forms), Glitch and Pastel.
- **Hidden behavioural mutations:** Nocturnal, Mimic, Wanderer, Collector, Dreamer, Shapeshifter, Echo, Inventor and Trickster. These are never shown at hatching. They *emerge* one to four days into a pet's life and are announced in the Diary as "Something new...". They can be inherited, so they surface again in later generations.

**The Frontier.** Slowly, over many days, a curious pet discovers that its world has edges:
1. **Discovery:** it touches the walls and presses its face against the screen, leaving fingerprints on the glass.
2. **Experimentation:** it climbs the walls and knocks on the inside of the screen.
3. **Breakthrough** (teen or older): it climbs *out* of the room. It walks along the screen bezel, pokes your hearts (they wobble), stares at the clock, and sits on the Settings button before diving back in.
4. **First contact:** on later trips it watches your cursor from outside the room. Click it or press a care button and it hurries home.
5. **Wandering:** a pet that's used to going outside may take a long walk around the whole device: over the hearts, past the clock, onto the A, B and C buttons, along the message screen, down the side of the tabs and up onto the Feed tab, before hopping home with a little souvenir such as "a crumb from the message screen". It never leaves the game window. Switch it off in Settings → Wandering.

Test speeds also speed up these rare behaviours, up to 8×, so you can watch the progression.

## Reciprocal intelligence: you learn each other (v1.3)

Neither you nor your pet starts out understanding the other. The pet doesn't just wait for input: it starts interactions itself, watches what you do, and adapts. You learn its signals and it learns your habits. Nothing here adds a meter or a chore, and if you don't respond it simply goes back to its own life.

- **Gestures.** Move the cursor inside the room: a swipe left or right, a side-to-side sweep, a little circle, a flick up or down, or a quick wiggle. Pause briefly at the end of a gesture. Sometimes your pet performs one of these, looks at you and waits. Copy it and see what happens. Draw one near it and it may try to copy *you*. It copies imperfectly at first: a circle may come back as a sway. Repeating your gesture helps it get better.
- **Games it invents.** It will occasionally start a game with you and lead it. It never explains the rules; you work them out.
  - *Follow My Lead:* it performs a short movement for you to copy.
  - *Pass the Ball:* it pushes the ball toward your cursor; touch the ball or click it to send it back.
  - *Echo:* it chirps a rhythm; click the same rhythm in the room.
  - *Follow the Path:* it visits two or three objects, then you point at the same ones in order by hovering or clicking.

  Patterns grow longer as you play together, at a pace set by experience and personality. Once you've played *Follow the Path*, hover over two objects in a row and it may follow *your* route.
- **Its own language.** Every pet has a private set of signals made from sounds and gestures, such as "a soft coo + a look at the ball" or "tapping the bowl". It keeps a model of how you respond to each one and chooses accordingly. It sometimes experiments, and sometimes even tests its assumptions, such as asking for food when it isn't hungry and then only sniffing it. Signals that work become conventions; ones you often misread are dropped. Signals can change meaning over time. Older pets with a couple of conventions can combine them: an attention call followed by a gesture that names what they want.
- **Misunderstandings get repaired.** If you answer with the wrong thing, it shakes its head and tries again. First it repeats the signal, then it adds a gesture or goes to the object it means, then it tries a different signal. After that it gives up and gets on with its day.
- **Negotiation.** Now and then it would rather do something else: rest instead of play, a different game than the one you picked, the window instead of the ball, or no snack because it's full. Insist with the ball and it settles down, then plays with it later on its own terms. It never refuses food when it's hungry, or medicine.
- **Boundaries.** If you chase it with the cursor after it backs away, it learns to keep its distance. If you hold back, it gets comfortable and starts coming to you.
- **Rituals.** Greet it with the same cursor gesture a few times and it will learn it, and eventually greet *you* first. Rituals can also form around mealtimes, bedtime and play, and they fade if you stop.
- **Drawing together.** Draw on the lower wall. It may come over, study your mark, and add its own, sometimes an imperfect copy of yours. It learns which of its styles you respond to. Shared drawings outlive the pet, and later generations may copy fragments of them.
- **Its model of you.** It notices whether you tend to copy it, answer its sounds or gestures, play ball, draw, leave it alone, give it space, or visit briefly. It adapts: more imitation games for imitators, shorter patterns for quick visitors, and more independence for people who leave it be.
- **Records → Bond.** *Shared Memories* keeps the milestones of your relationship. The **Observation Lab** button shows what's underneath for curious players: the signal tables with expected success, its language level, how it sees you, rituals, game interests, how well it reads your gestures, and its last decision with the reason. **Export report** saves a Markdown file to your Nimlets folder. Swap save files with a friend and compare how long it takes to learn someone else's pet.

## The Observer: a creature that studies you (v1.4)

99% of the time Nimlets is still a cute virtual pet. Underneath, the creature now builds a model of the one thing in its world that behaves unlike everything else: your cursor. Unusual behaviour is meant to *emerge* from simple, inspectable systems. It is never staged, and nothing claims the creature is conscious.

**It studies you.** It learns which parts of the screen your cursor visits, the order you move between them, and what you usually do next. When it's confident, it acts early, for example heading to its bowl while your cursor is still on its way to Feed. It scores its own predictions, loses confidence when wrong, and adapts as your habits change. Sometimes it simply stops and watches the cursor: motionless, from the front of the screen, or peeking from behind the plant.

**Its model of you develops in stages:** Encounter, Association, Prediction, Experimentation, Representation, Communication, Collaboration. These are milestones reached through experience. Some pets never reach them all.

**It notices its world is strange.** Speed the game up and it may look at the clock, then at the speed control. After a few pauses it glances at the pause button when time resumes. (Pausing really freezes it.) A pet that has already climbed out of its room may visit those controls and press them, and finds that nothing happens for *it*. A very adventurous one walks to the edge of the window and presses against it.

**It remembers.** Episodic memories strengthen with importance and repetition, and fade otherwise. Occasionally it recalls something you stopped doing, such as the movement that answers a greeting gesture you haven't used for days. It keeps a spatial memory of the room: drag its bed while it isn't looking and it will later search the old spot, look puzzled, and find it. Then it either drags the bed back to where it likes it or, over time, gets used to the new layout.

**It invents its own rituals.** Whatever it happened to do just before something good (eating, sleeping, play, your return, being understood) gets a little credit. Consistent coincidences become rituals it performs on purpose, much like superstitions. In testing, one pet started looking at you and then visiting the window before asking for something. No two pets end up the same, and many never form one.

**It experiments and uses tools.** It pushes its ball at the wall, the bowl, the plant or a trinket, watches what happens, and remembers. Reliable results become skills: the ball rebounds, lands in the bowl, or vanishes behind the plant. When a trinket rolls under the plant out of reach, it may work out how to knock it free with the ball and then pick it up. No script tells it to; across five test seeds, all five pets managed it. It also keeps a private stash behind the plant, and stops whatever private thing it's doing when your cursor comes near.

**It draws you.** Once its model of you is advanced enough, an arrow shape appears on the wall. Later the arrow may appear beside the thing it most associates with you, such as the bowl. New generations sometimes work fragments of ancestors' drawings into their own.

**Mirrors and memory.** Switch on the mirror in Settings → Experiments. Over many sessions the pet goes from greeting "the other creature" to testing the reflection and, eventually, examining the markings on its own body. The picture on the wall shows its first form, and it sometimes stands under it, looks up, then looks at itself. As a rare *prototype*, a curious adult may build a little figure from its trinkets and teach it to spin or jump. The figure has its own small learning table.

**Rare events.** These come in three levels (subtle, uncanny, existential), gated by real prerequisites and cooldowns. They never happen while the pet needs care. Some pets will never have some of them.

**Observation Mode (F9).** A developer view that's separate from the care screen:
- current intentions and plans
- the model of you, with predictions, accuracy and confidence
- memories, rituals and beliefs
- signal success rates and object experiments
- spatial memory, rare events and what's eligible right now
- a **reasoning trace** explaining each decision, for example *"Cursor context z:room:pet → Past cases: 21 → Expected you to feed (87%) → Moved early"*

**E** exports the whole thing as JSON and Markdown, for comparing creatures and generations.

**Privacy and control.**
- The cursor is only read inside this game's window, and only while it has focus. Nothing else is observed: no other applications, keyboard input outside the game, files, camera or microphone.
- Nothing ever leaves the game window: wandering stays inside the device, and can be switched off in Settings.
- **Settings → Experiments → "Unusual: off"** turns off everything in this section plus the Frontier escapes, leaving a normal, cute pet.

### What's implemented, prototyped or deferred

| Spec area | Status |
|---|---|
| Cursor recognition, zones, transitions, prediction, anticipation, adaptation | Implemented and tested |
| Deliberate observation (watching, from behind furniture, curiosity at stillness, studying repetition) | Implemented |
| Creature tests the player; experiment budget | Implemented (v1.3 signals plus v1.4 primitives and budget) |
| Personal rituals from action-sequence reinforcement | Implemented and tested |
| Episodic memory and recalling forgotten interactions | Implemented and tested |
| Symbolic representation of the cursor in drawings | Implemented and tested |
| Time-speed and pause awareness; real pause | Implemented and tested |
| Boundary discovery including interface controls and the window edge | Implemented |
| Environmental change detection and spatial memory | Implemented and tested |
| Tool use and multi-step skills (ball frees a trinket) | Implemented and tested |
| Hidden collections, private activities, arrangements | Implemented |
| Persistent creations and cultural transmission | Implemented (v1.2–1.4) |
| Mirror experiment | Implemented and tested (optional) |
| Recognising its past (memory frame) | Implemented |
| Caretaker experiment | **Prototype** |
| Rare-event registry with levels, prerequisites and cooldowns | Implemented and tested |
| Observation Mode, reasoning trace, exportable log | Implemented |
| Seeded accelerated dev simulation | Implemented (`tools/devsim.py`) |
| "Pull" and "pick up any object" as general primitives | **Deferred**: only trinkets can be picked up, and only the ball is pushed |
| Using one *movable* object to reposition the *bed* or other large objects | **Deferred** |

### Developer simulation

```
python tools/devsim.py --minutes 20 --seed 7                    # a player with consistent habits
python tools/devsim.py --minutes 20 --seed 7 --player random    # an unpredictable player
python tools/devsim.py --minutes 10 --player absent --speed 600 # stress test at test speed
```

On Windows, `run_devsim.bat` runs the same. Each run reports:
- prediction accuracy for the first and second half
- anticipations, rituals, skills and rare events
- episode count and cost per frame
- the most recent reasoning trace

Seeds make unusual behaviour reproducible for diagnosis. Example from development (seed 3, 25 minutes, habitual player):
- predictions settled around 80% accurate
- it drew the cursor
- it formed a ritual of its own before signalling: looking at you, then going to the window

## Design notes

- **Forgiving by design.** The creature can get sick and miserable, but it never dies of neglect: health has a floor and illness is always curable. Life ends gently. Elders depart peacefully, or an adult can "set off on a journey" from the Records screen. Either way it leaves an egg.
- **Offline time is capped and gentle.** On launch, up to 8 hours (configurable) of absence are simulated at reduced decay. A whole absence adds **at most one** care mistake.
- **Personality is hidden.** The five traits (playfulness, sociability, curiosity, independence, stubbornness) drift with experience. You only see them through behaviour and one vague "Seems: bouncy & curious" line.
- **Animation runs in real time; needs run in game time.** At high test speeds the pet still moves at a natural pace.

### Evolution trees

Each egg follows one of two family trees, the original **Pipling line** or the water-and-garden **Dewdrop line**. Children usually inherit their parent's line.

```
Egg ─► Pipling ─┬► Bobbit (≤1 mistake) ─┐
                └► Grumpkin ────────────┤
                                        ├► Sprouty (discipline ≥50) ─┐
                                        ├► Zippit  (playful)         ├► Luminelle · Mochimaru · Frolicat
                                        └► Scruff  (otherwise/neglect)┘   Hootle · Grumblin · Thornback
                                                                         SECRET: Celestine · Glitchling
Egg ─► Dewdrop ─┬► Puddle (≤1 mistake) ─┐
                └► Mudlet ──────────────┤
                                        ├► Ripplet (discipline ≥50) ─┐
                                        ├► Splashy (playful)         ├► Lumifin · Coralie · Bubbleroo
                                        └► Murkle  (otherwise)       ┘   Tidepup · Bogsworth · Gloomfin
                                                                         SECRET: Aurora
Any line, rarely ─► SECRET: Mycelia (pets that love collecting)
Adult ─► Elder (same form, greyer, calmer) ─► departs, leaving an egg
```

Celestine needs near-perfect care: ≤2 lifetime mistakes, discipline ≥75, a strong bond, high average happiness, plus luck. Glitchling comes from a rare "glitch" gene mutation, or a 2% fluke. Heavy feeding as a teen leads to Mochimaru. Rough upbringings lead to Grumblin. All rules are in `game/evolution.py`.

### Generations

A new egg inherits a hue close to its parent's, usually the same markings, 60% of the parent's final personality, and a chance of keeping a rare colour mutation (Shiny, Pastel, Midnight, Glitched). The Records screen tracks discovered forms (silhouettes for unknown ones, "?" for secrets), every generation's evolution path and lifespan, the longest-lived creature, rare finds, and lifetime care totals.

## Project structure

```
main.py               launcher
run_game.bat          Windows launcher (installs pygame on first run)
run_test_mode.bat     600x speed with a separate test save
config/settings.json  timings, decay rates, bedtimes, speeds, offline cap, hemisphere
config/species.json   every creature form: body shape, features, palette, tendencies
game/app.py           main loop, input, evolution/generation flow, drawing
game/creature.py      creature data model + serialisation
game/care.py          needs simulation and all care actions
game/personality.py   hidden traits
game/memory.py        foods, games, favourite food/game, habits, favourite spot, bond
game/behaviour.py     interruptible step plans + state-to-pose animation mapping
game/evolution.py     branching evolution rules
game/genetics.py      genomes, inheritance, mutations, names
game/living.py        the Living Pet System + artificial-life layer (the pet's "mind")
game/learning.py      beliefs (learned associations about the world)
game/language.py      each pet's private, evolving language
game/reciprocity.py   reciprocal intelligence: gestures, imitation, games, requests, rituals, collaboration
game/version.py       version number (also in VERSION and CHANGELOG.md)
game/shop.py          coins, shop items, per-pet tastes, preferences, toy play
game/observer.py      the Observer: cursor model, predictions, watching, time/pause awareness, stages
game/episodes.py      episodic memory with strength, decay and recall
game/rituals.py       rituals the pet invents from reinforced action sequences
game/world_model.py   spatial memory, change detection, restore/adapt
game/skills.py        object experiments, learned skills, tool use, stashes, arrangements
game/existential.py   mirror, memory frame, caretaker prototype
game/uncanny.py       rare-event registry: levels, prerequisites, cooldowns
game/observation.py   reasoning trace and exportable observation logs
tools/devsim.py       seeded accelerated simulation with a synthetic player
game/world.py         persistent room shared across generations (drawing, nest, inventions)
game/wall.py          cleaning the wall, and what the pet learns from it
game/shells.py        decorated device shells: unlock rules, "Match my pet", drawing
game/book.py          the Records book: the in-depth storybook version of Records
game/pixelfont.py     the game's own pixel font, drawn in code
game/journal.py       the behaviour diary
game/escape.py        trips across the interface, including long wanders around the device
game/icon.py          the app icon (an egg on an underwater tile), drawn in code
game/welcome.py       the first-time welcome tour and the one-time hints
game/minigames.py     Higher or Lower, Which Way?, Timing Star
game/sprites.py       procedural pixel-art creature/egg generator
game/room.py          room, window sky/weather, seasons, mess, lighting, particles
game/ui.py            layout, buttons, menus, status/records panels
game/pointer.py       mouse or finger: where the pointer is, and whether it is there at all (v2.4)
game/webscreen.py     sizing the browser canvas to the phone's real pixels, so it stays sharp (v2.5)
game/audio.py         chiptune sound effects synthesised at startup
game/records.py       collection, lineage, totals
game/save.py          atomic JSON save, .bak fallback on corruption
tests/test_systems.py core gameplay tests
tests/test_living.py  living-pet, settings and reset tests
tests/test_alife.py   artificial-life, diary, bowl, frontier, trip and wander tests
tests/test_reciprocity.py  reciprocal intelligence tests
tests/test_observer.py     observer update tests (one group per spec requirement)
tests/test_shop_room.py    28 forms (all reachable), coins, shop, preferences, room objects
tests/test_wall.py         wall cleaning: timestamps, sponge, wipe-all, learning from wipes
tests/test_handheld.py     handheld layout at many sizes, shells and unlocks, A/B/C, Settings picker
tests/test_book.py         Records book: Expand, navigation, every page, shells, diary scroll, buttons
tests/test_font_shells.py  pixel font, the 14 shells and their unlocks, every screen in both text styles
tools/export_sprites.py  renders assets/sprite_sheet.png (preview of all forms)
tools/make_icon.py    writes assets/icon.png and the multi-size assets/icon.ico for the .exe
tools/build_exe.py    builds the standalone game: tests, icon, PyInstaller, smoke test, release zip
tools/build_web.py    builds the web version: the home page from site/, and the game with pygbag in play/
site/index.html       the web home page (filled in and illustrated by build_web.py)
site/manifest.webmanifest  lets the web version be added to a home screen or installed as an app
build_exe.bat         one-click build on Windows (installs what it needs, then runs build_exe.py)
.github/workflows/build-windows.yml   builds the .exe on GitHub for every Release
.github/workflows/build-web.yml       builds the web version and publishes it on GitHub Pages
tests/test_build_ready.py  the Nimlets data folder, copying old saves, the test save, the icon
tests/test_welcome.py      the welcome tour, holding time, skipping, replaying, and the one-time hints
tests/test_touch.py        the pointer: a finger only there while touching, tabs on release, finger gestures
tests/test_phone.py        portrait and wide layouts, the Screen setting, canvas sizing, following the phone round
tests/test_web.py          the async loop, saving to browser storage, web mode, and what the web build packs
tests/test_site.py         the web home page, the game in play/, the app manifest, icons and the collection
saves/example_save.json  example save (a young adult Luminelle); other saves are git-ignored
assets/               sprite sheet preview, project cover images
dv-project.json       metadata for the DV Experiments dashboard
```

Saves go to `savegame.json` in your Nimlets folder (preferences go to `preferences.json`), written atomically, with a `.bak` copy of the previous save. Autosave runs every 60 seconds, after each evolution, and on quit. To try the example, copy `saves/example_save.json` from the game folder to `savegame.json` in your Nimlets folder.

### Save structure (abridged)

```json
{
  "version": 1, "saved_at": 1760160000.0, "world_time": 1760160000.0,
  "paused": false, "speed_idx": 0, "sound": true, "started": "2026-10-11",
  "creature": {
    "name": "Pichan", "generation": 1, "species": "luminelle", "stage": "adult",
    "age": 312000.0, "stage_age": 4000.0,
    "hunger": 81.2, "happiness": 64.0, "energy": 77.0, "hygiene": 90.0, "health": 100.0,
    "weight": 29, "discipline": 80, "care_mistakes": 1, "sick": false, "poops": 0,
    "asleep": false, "lights_on": true, "attention": null,
    "genome": {"hue": 204.1, "sat": 0.58, "marking": "spots", "mutation": null, "tendencies": {"...": 0.5}},
    "personality": {"playfulness": 0.61, "sociability": 0.55, "curiosity": 0.4, "independence": 0.38, "stubbornness": 0.33},
    "memory": {"food_likes": {"fish": 0.62}, "food_counts": {"fish": 3}, "attachment": 54.0,
               "habits": {"dance": 0.8}, "spots": [0, 1, 6, 9, 2, 0, 0, 0], "lessons": 2},
    "forms": ["pipling", "bobbit", "sprouty", "luminelle"], "stats": {"meals": 12, "games": 5}
  },
  "records": {"discovered": ["pipling", "bobbit", "sprouty", "luminelle"], "lineage": [],
              "longest": null, "rare": [], "totals": {"meals": 0}}
}
```

## Configuration

Edit `config/settings.json`:

- **`stage_hours`**: how long each life stage lasts (egg 3 min, baby 1 h, child 1 day, teen 2 days, adult 6 days, elder 3 days by default).
- **`base_time_scale`**: permanently speed up or slow down the whole game.
- **`decay_per_hour`**, **`poop_interval_hours`**, **`bedtimes`**, **`attention_timeout_minutes`**: care tuning.
- **`offline_cap_hours`**: how much absence is simulated.
- **`hemisphere`**: `"north"` or `"south"`, which flips the seasonal decorations.
- **`allow_test_speeds`**, **`test_speeds`**: the T-key speed options.

New creature forms can be added in `config/species.json` by combining existing body and feature options. You then add a rule for them in `game/evolution.py`.

## Testing

```
python -m unittest discover -s tests -v
```

The 249 tests cover:

- needs decay and the hearts display
- feeding and refusal
- care mistakes from ignored calls
- clean, medicine, scold and praise logic
- sleep and lights
- the health floor
- gentle offline simulation
- every evolution branch, including all four secrets and target validity across 300 random creatures
- a full accelerated lifecycle across **three generations** (egg → baby → child → teen → adult → elder → new egg) with an automatic carer
- save/load round-trip and corrupt-save fallback
- inheritance staying close to the parent
- all three mini-games completing, plus timing hit detection
- every species rendering a unique sprite
- the Living Pet System: quirk assignment and unlocking, upgrading old saves, interrupted activities resuming, depth movement, sleeping in bed, a 400-second autonomous run that stays on screen and varied, cursor gaze, return greetings, catching secret activities, click annoyance, loneliness, routine recognition, wariness fading, medicine nervousness, gifts
- theme preferences, and both reset types (records kept or erased, backup written, theme preserved)
- the artificial-life layer: world and diary persistence and merging, beliefs forming once, signals becoming shared and fading, responses reinforcing signals, bowl experiments, fear turning into trust, every egg anomaly rendering, chimeras looking different, mutations emerging later and staying hidden in inheritance, nocturnal schedules, wall drawings, collections, bed dragging, inventions, a new generation studying the old drawing, the ball landing in the bowl, frontier progression to an escape, a full trip across the hearts, clock and Settings, recalling a trip, a wander around the whole device that never leaves the window, food going into the bowl and being eaten, the offline diary and away summary, `--reset` ignoring the backup, and 6-slot hearts
- reciprocal intelligence:
  - the gesture classifier and stroke detection
  - conventions forming, changing meaning and being lost to ambiguity
  - combinatorial signals limited by capacity, exploration versus exploitation, and memory decay
  - requests that succeed, are misunderstood and repaired, or give up after the cap
  - testing assumptions, and the pet starting requests on its own
  - Follow My Lead success and ignored invitations, imperfect imitation improving, catch rallies, Echo, Follow the Path and following your route, and the pet inventing games
  - rituals forming, being started by the pet and fading
  - negotiation (rest, insisting on the ball, declining a snack) and respecting space versus chasing
  - collaborative drawing and style learning
  - the Observation Lab, report export, wall drawing in the real app, the Bond tab, the version in the title, and older saves gaining a bond
- the observer update, numbered as in the spec:
  1. predictions improve with experience, including a seeded devsim run
  2. failed predictions change confidence and behaviour
  3. heading detection and anticipation
  4. rituals form from consistent history and not from inconsistent actions
  5. the world model handles unseen moves, searches, restores and adapts
  6. rare events respect prerequisites
  7. cooldowns prevent repetition
  8. all new memories survive save and load
  9. a new generation starts with a fresh model of you while the room keeps its artifacts
  10. care still works, and no rare events happen while the pet needs care
  11. a 600× stress run stays bounded
  12. the cursor is not read when the window isn't focused

- v1.5 additions:
  - all 28 forms exist and every one is reachable
  - family lines are inherited, and old saves keep the original tree
  - winning earns coins, and pet-led games pay a little
  - the Shop entry appears in both lists
  - bought items are used at once, toys get used up, and items can't be bought without coins or while asleep or sick (except the Golden Apple)
  - pets' tastes differ, preferences are learned, and boredom builds up
  - coins persist
  - room objects respond to clicks, shaking the plant frees a trinket, and tidy pets straighten the picture

- v1.6 wall cleaning: drawings carry a timestamp, the sponge only wipes where you drag, *Wipe it all* asks first, Clean still flushes mess before offering the wall, fresh wipes teach a lesson and old ones don't, stubborn and sleeping pets learn less, secret drawing, the belief recovering, ancestors' drawings being noted, and old saves without timestamps

- v1.7 handheld: the layout fits without overlaps at seven window sizes, the tabs run down both sides in order, every shell draws light and dark at every size, unlocks come from the family history, *Match my pet* follows the line and secret forms (eggs stay Classic), a locked choice falls back, hatching announces a new shell, A/B/C work as buttons and keys and do nothing when covered, the Settings picker cycles and persists, every shell renders in the running game, passing hovers aren't scored as wrong guesses, and room headings only count the near side's tabs

- v1.8 Records book: Expand (button and E key) opens the matching section and Esc, C and close return to it, pages turn with keys, A and tabs, every section draws for an egg and a lived-in save at three window sizes, the diary scrolls within bounds, locked shells can be previewed but not worn, Wear and Match my pet change the shell, and Export, the Observation Lab and new generation work from the book

- v1.9 pixel font and shells: every glyph is well formed, rendered sizes match measured sizes at every scale, unknown characters are stood in for, pixels stay crisp, the generation and rare-egg shells unlock from the records, Match my pet prefers a secret form, then a rare egg, then the family line, falling back to what's unlocked, all 14 shells draw light and dark, every screen (menus, panels, shop, Records, the book, dialogs and mini-games) draws in both text styles at three window sizes, and Settings switches the text style

- v2.0 build-ready: the Nimlets data folder on Windows, macOS and Linux (and the override), old saves copied once without ever overwriting a newer save, the game saving to the data folder with a separate test save, a wander touring the device without leaving the window, and the icon drawing at every size with a valid multi-size .ico

- v2.1 welcome: a new player gets the tour and time holds still without touching their own pause, pages turn with keys, A/B/C and buttons, skipping, existing players never see it unless they ask, every page draws in both text styles at three sizes, each hint shows once, hints never interrupt another message, and what triggers each hint

- v2.2 web-ready: saves and preferences going to browser storage instead of files (with the backup fallback), the game in web mode (no folder buttons, friendly messages for exports, reopening the page restores the pet), the async loop, saving when the window loses focus, the web build packing only the game, and every preference surviving a restart
- v2.4 touch: a finger exists only while touching (plus a short afterglow), no phantom cursor or false trust after a tap, tabs acting on release and cancelling when you slide off, mouse clicks still immediate, a finger drag ending its gesture on lift, and no heading read from a finger
- v2.5 phone layouts: upright phones get the portrait layout and phones on their side the wide one, with everything on the device and nothing overlapping at many phone sizes; desktop windows keep the classic device; the Screen setting (including Portrait on a wide window); escape trips staying on the device; long messages wrapping onto two lines instead of shrinking; the browser canvas matching the phone's real pixels within a pixel budget; the game following the phone round and back (never as a resizable window, ignoring sizes reported mid-turn, and putting right a canvas changed by something else, and the canvas pinned fully on screen at every step, v2.5.2); a failed resize keeping the old canvas; and every screen drawing at phone sizes
- v2.6 home page: the home page on top and the game in play/, every file the page uses existing, nothing loaded from other sites, the collection showing every form with secrets kept secret, icons and pictures at the right sizes, an installable manifest that opens the game, the game page gaining the app extras once and inside its head, the home page reading the same save key the game writes, a missing placeholder stopping the build, and a home-page-only build that needs no pygbag

The whole suite is also run at simulated times of day (night, morning, noon, evening), so no test depends on the real clock.

  Also covered: deliberate watching, time awareness, real pause, episode recall and fading, the cursor drawing reaching the representation stage, tool use emerging across seeds, private stashes pausing near the cursor, mirror stages, the caretaker figure learning, the memory frame, older saves upgrading, Observation Mode pages, the "Unusual: off" switch, and log export

**Headless smoke test of the real game loop:**

```
python main.py --smoke-test 300 --screenshot shot.png --save saves/smoke.json
```

**Manual checklist (about 15 minutes in test mode):**

1. Run `run_test_mode.bat`.
2. Watch it hatch.
3. Feed each food and notice which it loves.
4. Play all three games.
5. Let mess pile up, then clean.
6. Let it get sick, then give medicine.
7. Scold a fake call (the "!" appears while all needs are fine).
8. Turn the lights off at night.
9. Check Status and Records.
10. Press T up to 3600× to reach adulthood.
11. Start a new generation from Records > Family.
12. Close and reopen the game to confirm everything restores.
13. Living pet: move the cursor around the screen and hover the pet. Switch to another window for a minute and come back. Click the ball. Leave it alone for a couple of minutes and watch.
14. Settings: try every theme colour in Light and Dark mode, then use both reset options.

## Feature checklist

| Area | Status |
|---|---|
| Python 3.11+, pygame-ce only, offline, JSON saves, modular code | ✅ |
| Egg → Baby → Child → Teen → Adult → Elder, configurable timings | ✅ |
| Feed / Play / Clean / Medicine / Praise & Scold / Lights / Status / Records | ✅ All functional, no dead buttons |
| Hunger, happiness (hearts), energy, hygiene, health, weight, age, discipline, attention, care mistakes | ✅ |
| Procedural pixel-art creatures, distinct per form, expressive faces | ✅ 28 forms + egg, about 15 expressions and poses |
| Animations: walk, bounce, jump, spin, dance, sit, sleep, eat, react, call, sulk, evolve, hatch, depart | ✅ |
| Autonomous utility-weighted FSM, influenced by needs, personality, species, habits | ✅ |
| Hidden personality (5 traits) that drifts with experience | ✅ |
| Memory: favourite food and game, bond, discipline lessons, habits, favourite resting spot | ✅ |
| Branching evolution with 4 secret forms and an evolution flash animation | ✅ |
| Generations: colour, markings, personality tendencies, rare mutations, lineage | ✅ |
| Records: collection with silhouettes, family history, longest-lived, rare finds, care totals | ✅ |
| Room: day/night lighting, window sky with sun/moon/stars, weather, seasonal decor, mess, lamp | ✅ |
| 3 mini-games with personality-based reactions | ✅ |
| Illness, medicine, recovery animation, weight effects | ✅ |
| Real-time ageing, autosave, manual save, capped gentle offline progress, pause, test speeds | ✅ |
| Resizable window, integer pixel-perfect scaling, mouse and keyboard | ✅ |
| Handheld device UI: side tabs, hearts strip, message screen, A/B/C buttons | ✅ |
| 14 decorated shells unlocked by family history, generations and rare eggs; Match my pet | ✅ |
| The game's own pixel font, drawn in code, with a smooth-text option | ✅ |
| Records book: quick view plus an expandable six-section storybook | ✅ |
| Programmatic chiptune SFX (20 sounds), mute toggle | ✅ |
| Settings: theme colour (7), light/dark, sound, two reset options with confirmation and backup | ✅ |
| Living pet: cursor gaze, hover, look-away, focus-return greetings, inactivity, room clicks | ✅ |
| Living pet: routines, wariness, affection, associations, favourite spots, sleeps in bed | ✅ |
| Living pet: bowl/ball/window/bed objects, distraction, changing its mind, secret activities | ✅ |
| Living pet: 10 hidden emotions, 8 hidden quirks, rare surprises, gifts, dreams | ✅ |
| Food served in the bowl; darker UI text; 6-slot Hunger/Happy/Health hearts | ✅ |
| Behaviour diary, "While you were away" summary, offline life | ✅ |
| Autonomy: avoidance/bravery, refusals, territory, rearranging, rituals | ✅ |
| Creations and culture across generations (drawing, collection, nest, inventions) | ✅ |
| Beliefs + experiments; emergent shared signals | ✅ |
| Anomalous eggs (5) and hidden behavioural mutations (9) | ✅ |
| Frontier: screen pressing, climbing, escapes across the UI | ✅ |
| Wandering around the whole device (replaces desktop roaming) | ✅ |
| Saves in a per-user Nimlets folder, with a one-time copy of old saves | ✅ |
| App icon drawn in code, with a multi-size .ico | ✅ |
| First-time welcome tour and one-time hints for new players | ✅ |
| Web version (browser, incl. phones) built with pygbag and published on GitHub Pages | ✅ Touch (v2.4), portrait and wide phone layouts, sharp canvas (v2.5) |
| Web home page with Play now, add to home screen / install as an app, kept storage | ✅ (v2.6) |
| Reciprocal intelligence: gestures, two-way imitation, 4 pet-led games, private language (4 levels), experiments on the player, repair, negotiation, boundaries, rituals, drawing together, player model | ✅ |
| Shared Memories + Observation Lab + report export | ✅ |
| Versioned releases + CHANGELOG | ✅ |
| Observer update: prediction, watching, rituals, episodic memory, cursor drawings, time/pause awareness, spatial memory, tool use, stashes, mirror, memory frame, rare-event registry, Observation Mode, dev sim | ✅ (caretaker = prototype) |
| 28 forms across two family trees, 4 secrets | ✅ |
| Coins for winning games; shop of 12 one-time treats/toys; per-pet tastes, learned preferences and reactions | ✅ |
| Interactive room objects (plant, window, lamp, clock, picture, bowl, bed, pumpkin, mirror) | ✅ |
| Wall cleaning (sponge or wipe-all) that the pet learns from, by freshness | ✅ |
| Automated tests | ✅ 249 passing |

## Known limitations (honest notes)

- **The web version can't be built in my own build environment** (pygbag fetches its browser runtime from the internet while building). Everything up to that point is tested, GitHub's machines do the full build, and it has been confirmed working in Chrome on a PC and a phone.
- **The sharp phone canvas (v2.5) is tested with a stand-in browser, not a real phone.** If resizing the canvas ever fails in a real browser, the game logs it in the console and carries on at its old size (stretched and softer, as before v2.5), rather than risking a blank page.
- **The home page was checked in headless Chrome** (a phone-sized view, light and dark, a new and a returning player), where Chrome also offered to install it. Adding it to a real iPhone or Android home screen hasn't been tried yet, and neither has the game itself running from `/play/`; pygbag's page uses relative paths, as it already did one folder down at `/Nimlets/`, so it should behave the same.

- **The handheld UI was checked in headless screenshots,** at sizes from 640×520 up to 1920×1080 and on every shell, light and dark, but not yet on a real Windows display.
- **Pixel text only comes in whole sizes,** so it stays crisp. Where space is tight, some small labels (secondary hints, the smallest window size) drop to the smaller size rather than being cut off. *Smooth text* in Settings is there for anyone who prefers it.
- **The Observer was retuned for the new layout.** The tabs sit right beside the room, so the cursor crosses the room more often. Passing hovers are no longer scored as wrong guesses, and a tab only counts as the cursor's destination from the nearer half of the room. Simulated prediction accuracy is about 64% (it was about 72% with the old layout).

- **Not run on Windows here.** It was developed and tested on Linux, headless (dummy video and audio drivers), with Python 3.12 (classic pygame 2.6.1 up to v1.3, pygame-ce 2.5.8 from v1.4). The code only uses cross-platform pygame-ce and standard-library features, but I could not see or hear it running on real Windows hardware.
- **Sound** generation and playback were verified with SDL's dummy audio driver, not real speakers. If no audio device is available, the game prints a note and continues silently.
- **Clock drift at test speeds.** At test speeds the in-game clock (day/night, bedtime) runs ahead of the real clock and stays ahead when you return to 1×. Use a separate test save (as `run_test_mode.bat` does) to keep your real pet on real time.
- **Names are random** per generation. There is no rename screen.
- **The .exe build was smoke-tested here as a Linux build** (the same PyInstaller script). The Windows .exe itself is built on your PC or on GitHub, and the build test-runs it before zipping, but I haven't seen it run on a real Windows desktop.
- **Weather is purely decorative**, by design. It does affect how often the pet watches the window.
- **Window focus, enter and leave events** (the "you came back" greeting) are handled with standard pygame-ce 2 events. I tested them by calling the handlers directly, because a headless test environment doesn't generate real focus changes. Returning after 45 seconds of inactivity, with the window still focused, triggers the same greeting.
- **The Observer's thresholds were tuned with a synthetic player.** That includes zones, heading detection, prediction thresholds and cooldowns. Real players are less regular, so expect fewer confident predictions at first. That's fine, since the pet should be wrong sometimes. The thresholds are named constants in `game/observer.py`.
- **Rarity by design.** In a 25-minute simulated session you'll typically see predictions, watching, a cursor drawing and maybe one ritual. Tool use, mirror understanding and the caretaker figure need many sessions, and some pets never get there.
- **Gesture recognition was tuned on synthetic cursor paths**, plus a 20-minute simulated player run through the real game loop, not on a real mouse. Real hand movements are messier, so the thresholds may need adjusting after you try it. They're the constants in `classify()` in `game/reciprocity.py`. Pausing briefly at the end of a gesture helps.
- **Relationships take time.** In the 20-minute simulated session, a greeting ritual, a game of catch and a shared drawing formed, and one signal convention emerged. A rich private language takes several play sessions. That's intended.
- **Frontier pacing.** Escapes need a teen-or-older pet and a lot of prior curiosity, so at normal speed they take several days of play. Use a test speed to watch the whole progression.
- **No explicit routine indicator.** The routine-waiting behaviour needs several days of visits around the same hour before it shows up. That's intended, but it means you won't see it in a short session.
