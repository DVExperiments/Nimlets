# Changelog

All notable changes to Nimlets (formerly "Tamagotchi Reimagined" / "Pocket Pal").
Versions follow `MAJOR.MINOR.PATCH`: MINOR for new features, PATCH for fixes.
Each release is packaged as `nimlets_vX.Y.Z.zip` and published as a GitHub Release.

## v2.2.3 "Web Ready" (fix)

**The web version stalled right after starting `main.py`**
- **The browser's console showed `main.py` starting, then nothing more.** The stall was between `main.py` and the game's own code.
- **`main.py` now follows pygbag's standard shape:** an `async def main()` with `asyncio.run(main())` as its last line, the form pygbag looks for. Before, a variation of it was tucked inside an `if` block.
- **If the game's code fails to load in the browser,** the error is shown on screen and in the console, using only pygame's built-in font so it works even if the game's own code can't load.
- **The desktop game and the .exe start exactly as before** (rebuilt and smoke-tested).

**Tests**
- 2 new tests (206 in total): `main.py` keeps pygbag's standard shape and does nothing when merely imported, and a failure loading the game's code is reported and drawn.

## v2.2.2 "Web Ready" (fix)

**The web version showed "Loading Nimlets..." and then went grey**
- **Sounds are made the first time they're played** in the browser, instead of all 34 at start-up. Generating them sample by sample in Python is slow in a browser, and the browser's sound settings made it about four times more work than on a computer. The desktop version still makes them up front.
- **The game keeps the loading screen's canvas** in the browser instead of opening a second window, which could blank the page.
- **Progress goes straight into the browser's developer console,** with timings for each start-up step and a few heartbeats once it's running. pygbag keeps Python's own output to itself, so before this the console couldn't show what was happening.
- **Any error at all during start-up** is now shown on screen and in the console.

**Tests**
- 3 new tests (204 in total), including the whole web start-up path with a stand-in browser console and storage.

## v2.2.1 "Web Ready" (fix)

**The web version showed a grey screen after "Ready to start"**
- **A likely cause is fixed.** `main.py` worked out its own folder from `__file__`, which a browser may not provide, so the game could crash on its very first line. It no longer relies on that in the browser.
- **The web version now shows "Loading Nimlets..." straight away.**
- **If anything goes wrong while starting, the error appears on screen** (and in the browser's console) instead of a blank page, so it can be reported with a screenshot.
- **Progress messages in the browser console** (`[nimlets] ...`) show how far startup got.

**Tests**
- 2 new tests (201 in total): `main.py` starting without `__file__`, and a startup crash being shown on screen.

## v2.2.0 "Web Ready"

The first step towards phones: the same game now runs in a web browser.

**The web version**
- **Built with pygbag:** `tools/build_web.py` packs only `main.py`, `game/` and `config/`, with the egg icon as the page's icon. `--serve` plays it locally.
- **Published on GitHub Pages:** `.github/workflows/build-web.yml` runs the tests, builds, and publishes whenever the main branch changes, giving a link that works on phones.
- **An async main loop** hands control back to the browser after every frame. The desktop loop is unchanged.
- **Saves in the browser:** saves and preferences go to the browser's own storage, still with a backup copy. On a computer they're files exactly as before.
- **Saving whenever the window loses focus,** since a browser tab or phone app can be closed without warning. This helps on desktop too.
- **Friendly messages instead of files in the browser:** Settings hides Open folder there, and report and log exports explain they're not available yet.

**Fixes**
- **Some preferences were forgotten on every restart:** your chosen shell, Pixel/Smooth text, and the welcome tour's flags. Only an older, fixed list of preferences was kept when loading. All of them are kept now, and a test restarts the game to make sure.

**Tests**
- 6 new tests (199 in total), still passing at any simulated time of day.

## v2.1.0 "Welcome"

**A welcome for new players**
- **A five-page storybook tour the first time someone plays:**
  - your egg and the 28 forms it might become;
  - looking after it (the hearts, the attention light and the tabs);
  - the A/B/C buttons;
  - how your Nimlet notices you and has a mind of its own (without spoiling what it does);
  - how life carries on gently in real time.
- **Each page has a picture drawn from the game's own pieces.** On small windows the picture shrinks before the text does.
- **Game time holds still during the tour,** so the egg can't hatch mid-tour, and the player's own pause setting isn't touched.
- **Turning pages:** Next, Back and Skip, or Enter/Right, Left and Esc, or B and C.
- **Settings → Welcome tour** replays it.
- **Existing players never see it automatically.**

**One-time hints**
- For a new player's first days, a short hint appears the first time something important happens: its first call for attention, its first mess, its first bedtime, its first drawing on the wall, and the first time it grows up.
- Each appears once, waits until no other message is showing, and is remembered in preferences.

**Licence**
- **Nimlets is now explicitly "free to play, all rights reserved"** (`LICENSE`). Anyone can download and play it free, but it may not be copied, re-uploaded, modified or sold without permission.
- **The release zip includes it** as `LICENSE.txt`.

**Tests**
- 8 new tests (193 in total).
- The wander test assumed daytime and failed after the pet's bedtime; it's pinned to the afternoon now.
- The whole suite was checked at five simulated times of day.

## v2.0.0 "Build Ready"

Getting ready for the standalone Windows .exe.

**Saves in your own Nimlets folder**
- **A per-user folder.** Saves, preferences, backups and exported reports now live in `%APPDATA%\Nimlets` on Windows (Application Support on macOS, `~/.local/share` on Linux), not in the game folder. They survive updates, reinstalls and the packaged .exe.
- **A one-time copy of old saves.** The first run copies any saves from the old `saves` folder. The originals are left in place, and it never overwrites a newer save.
- **Settings → Open folder** opens the folder in your file browser.
- **Test mode** uses its own `test_save.json` there (`--test-save`).
- **`NIMLETS_DATA_DIR`** overrides the folder, for example for a portable copy.

**Wandering replaces desktop roaming**
- **The separate desktop companion window is gone,** along with the Windows-only code that ran it.
- **Instead, a pet used to going outside may take a long wander around the whole device:** the hearts, the clock, the A, B and C buttons, the message screen, the sides of the tabs and the top of the Feed tab, coming home with a little souvenir.
- **It never leaves the game window.**
- **Settings → Wandering** (on by default) switches it off.

**An app icon**
- **A spotted egg on a purple tile,** with an underwater pattern from the Tide shell. It's drawn in code and simplified at small sizes so it still reads at 16 px.
- **The game window uses it.**
- **`tools/make_icon.py`** writes `assets/icon.png` and a multi-size `assets/icon.ico` for the .exe.

**Building the standalone game**
- **`tools/build_exe.py`** runs the tests, draws the icon, builds a single-file `Nimlets.exe` with PyInstaller, test-runs the built game (it must start, save to its data folder and quit cleanly), and zips it with a short read-me for players.
- **`build_exe.bat`** does all of that with a double-click on Windows.
- **`.github/workflows/build-windows.yml`** builds it on GitHub's Windows machines for every published Release and attaches the zip, or on demand from the Actions tab.
- **The packaged game finds its own files inside the .exe,** and copies saves from a `saves` folder next to it on first run.

**Tests**
- 5 new tests (185 in total).
- The offline-diary test no longer depends on the real time of day. It used to fail now and then overnight, which would have blocked automatic builds.

## v1.9.0 "Pixel Perfect"

**The game's own pixel font**
- **An original pixel font,** drawn in code like the creatures, room and sounds, so there's still no font file. Most letters are 4 pixels wide, capitals 7 tall, with proper descenders.
- **Crisp at every size:** text is drawn at whole-number scales only.
- **Every character works:** curly quotes, dashes and the like are stood in for, and unknown characters show as "?" instead of failing.
- **On by default.** Settings → Appearance has a *Pixel text / Smooth text* switch.
- **Layouts adjusted for it:**
  - the hearts strip keeps the hearts big and shrinks its labels when space is tight;
  - Settings buttons and colour swatches size themselves to their text;
  - the confirmation dialog wraps its explanation instead of cutting it off;
  - shop cards, the book's gift labels and shell names each use one shared size, so they never mismatch;
  - the diary has a proper time column;
  - the message screen picks a smaller size before squashing a long message.

**Eight new shells (14 in total)**
- **Generation milestones:** Patchwork (generation 3), Heirloom (5) and Family Tree (10).
- **Rare eggs:** Golden, Void, Chimera, Pastel, and Static for the rare Glitch egg.
- **Unlocks come from the records,** so older saves get the shells they've already earned.
- **Match my pet** now tries the secret-form shell, then the rare-egg shell, then the family line, and wears the first one you've unlocked.
- **The Records book's Shells page** shows all 14 in four columns.

**Fixes**
- A rare-colour pet whose rare shell wasn't unlocked yet fell back to Classic instead of its family line's shell.

**Tests**
- 10 new tests (180 in total), including one that draws every screen in both text styles at three window sizes.

## v1.8.0 "Storybook"

**The Records book**
- **The quick Records panel works as before,** and now has an **Expand** button (or press **E**). It opens the full Records book: an open storybook over the whole window, with six coloured section tabs.
- **Collection:** every form at a comfortable size, with silhouettes and hidden secrets. The facing page has progress bars for the Pipling line, the Dewdrop line and the secrets, a hint, the longest life and rare finds.
- **Family:** every generation with its sprite, evolution path, lifespan and how its life ended. The current pet has its personality, family line, markings, colouring, what the family left in the room, and *Begin a new generation*.
- **Care:** this life's records and favourites, totals across generations, coins, and the gifts your pets gave you.
- **Diary:** the signals you share and a box of moments worth remembering. The full diary is grouped by day, newest first, with important moments starred, and scrolls.
- **Bond:** Shared Memories as a timeline. The facing page shows how your pet sees you, drawn as simple bars, plus its language and rituals, with buttons for the Observation Lab and *Export report*.
- **Shells:** every shell drawn small with your live screen inside, and locked ones showing a padlock and their hint. Preview any shell, *Wear this shell*, or tick *Match my pet*.
- **Navigation:** turn pages with the tabs, Left/Right or A. Esc, C or the close button return to the quick view on the matching section.

**Other**
- **The quick view's tabs** now shrink to leave room for Expand and the close button. At smaller window sizes the tabs had been crowding the close button.
- 6 new tests (170 in total).

## v1.7.0 "Handheld"

**A new look: the handheld device**
- **The window is now a little handheld device.** The room is its screen, with the eight actions as coloured tabs down both sides (Feed, Play, Clean and Meds on the left; Train, Light, Status and Book on the right).
- **A hearts strip** above the screen, with Hunger, Happy and Health in three equal sections.
- **A green message screen** below the screen.
- **A name plate** with an attention light, and the day and clock beside it.
- **A / B / C buttons** along the bottom, flanked by Settings and Sound on the left and Speed and Pause on the right:
  - A moves along the tabs, B chooses and C goes back. The highlighted tab is outlined.
  - In menus A moves and B chooses; C closes menus, panels and dialogs; in mini-games they are left, action and right.
  - The A, B and C keys do the same.
- The layout scales from 640×520 to large windows and keeps its proportions in very wide or tall ones.

**Decorated shells**
- **Six shells, all drawn in code:** Classic, Tide, Meadow, Starlight, Glitch and Spore.
- **Unlocked by your family history:** the first egg of each line and each secret form. Unlocks come from the collection records, so older saves get the shells they've already earned.
- **Unlocks are announced** in the message line and the Diary.
- **"Match my pet" is the default.** It follows the pet's line or secret form; eggs wear Classic so the line stays a surprise.
- **Choose a shell** in Settings → Shell.
- **Classic follows the theme colour,** and dark mode dims every shell.

**Changes**
- **Settings:** the Sound row is replaced by the Shell picker. The device has a sound button, and M still toggles sound.
- **No Save button on the device.** S, F5 and autosave are unchanged.
- **Escape trips** now stand on the hearts strip, beside the clock and on the Settings button.
- **The Observer was adjusted for the new layout:**
  - a "you're about to pet me" guess is withdrawn, not scored as wrong, when the cursor just passes over;
  - a tab only counts as the cursor's destination once the cursor is in the nearer half of the room.

**Tests**
- 12 new tests (164 in total).

## v1.6.0 "Clean Slate"

**Cleaning the wall**
- **Clean** still flushes mess first. When the room is already tidy and there's something on the wall, it offers **Sponge** or **Wipe it all**.
- **Sponge:** drag over the wall to wipe just the bits you choose, with little bubbles. Right-click, Esc, Clean or clicking elsewhere puts it away.
- **Wipe it all** asks for confirmation first, and mentions any ancestors' drawings that would be lost.
- The first time you clean the room while the wall has drawings, a hint mentions that Clean can also wipe the wall.

**What the pet learns**
- Every mark on the wall now remembers when it was drawn (game time).
- A new belief, *its drawings are welcome*, is shaped by what you wipe:
  - wiping something it drew within the last game-hour is a strong "don't";
  - wiping marks from the same day is a milder one;
  - wiping old marks or your own coral marks teaches nothing.
- Stubborn pets are less put off, and a sleeping pet only half notices.
- A pet that believes drawing is unwelcome rarely draws while you're watching, and draws a little more while you're away ("drew on the wall while you weren't looking"), including in offline life.
- Drawings left up for six game-hours or more, and you drawing on the wall yourself, slowly rebuild the belief.
- It reacts when it sees a fresh drawing wiped: it droops, or huffs if it's stubborn or grumpy. Watching it happen is kept as an episodic memory.
- Wiping away the last of an older generation's drawing is noted in the Diary, and a pet that once studied it may look sad.

**Other**
- New module `game/wall.py`, 17 new tests (152 in total).
- Saves from earlier versions load unchanged; existing drawings without a timestamp count as old.

## v1.5.1 "Menagerie" (housekeeping)

- **One name everywhere.** The game is now called Nimlets throughout the code, launchers and docs (previously also "Tamagotchi Reimagined" and "Pocket Pal").
- **Flatter repository.** The game now sits at the repository root instead of inside `Nimlets_v1.5.0/Nimlets v1.5.0/`. Release zips are no longer committed; they are attached to GitHub Releases.
- **`.gitignore` added.** Personal and test saves, `__pycache__` folders, build output and zips are no longer tracked. `saves/example_save.json` is still included.
- **Docs fixed.** The README feature checklist and test list now say 28 forms and 4 secrets (they still said 13 forms and 2 secrets).
- No gameplay changes. Saves from v1.5.0 load unchanged.

## v1.5.0 "Menagerie"

**28 forms (was 14)**
- A second family tree, the water-and-garden **Dewdrop line**, joins the original. Each egg hatches into one line or the other (about 45% water), and the line is usually inherited.
- **New baby:** Dewdrop.
- **New children:** Puddle and Mudlet.
- **New teens:** Ripplet, Splashy and Murkle.
- **New adults:** Lumifin, Coralie, Bubbleroo, Tidepup, Bogsworth and Gloomfin.
- **Two new secrets:**
  - **Aurora:** near-perfect care on the water line.
  - **Mycelia:** a mushroom-capped form that appears in pets that love collecting, on either line.
- **New sprite features:** dorsal fins, antlers, lop ears, mushroom caps, a spiral horn, a flower, fan tails and whip tails.
- The collection grid now fits all 28 forms at any window size.

**Coins and the shop**
- **Earning coins.** Winning a mini-game earns 3 coins plus a bonus for extra points. Games your pet starts itself pay a coin or two when they go well.
- **The Shop.** A Shop button sits at the bottom of the Feed and Play lists. It opens a shop window with **Treats** (Starfruit, Honey Cake, Kelp Crisps, Fire Pepper, Moon Pudding, Golden Apple) and **Toys** (Bubble Wand, Feather Teaser, Music Box, Puzzle Cube, Plush Buddy, Yarn Ball). Everything is used straight away: treats go into the bowl, and toys appear in the room and get played with.
- **Hidden tastes.** Every pet has a hidden taste for each item, shaped by personality, family line (water pets like Kelp Crisps) and individuality. Fire Pepper is deliberately divisive.
- **Varied reactions.** How much it enjoys an item *this time* also depends on novelty, boredom (the same toy every day gets old) and mood. Reactions range from adoring to refusing, and effects scale with them.
- **Learned preferences.** After a couple of tries the shop shows "loves this" or "not keen". The diary records first tries and new favourites. Different pets play differently, for example dancing to the Music Box versus dozing to it.
- **Records.** Records shows coins held, earned and spent.

**Interactive room.** Click things and they react, and so does your pet, in character:
- **Plant:** shakes and drops a leaf. It can shake loose a trinket stuck underneath, and a pet with a secret stash may rush over to guard it.
- **Window:** a bird lands on the sill by day; a shooting star crosses it at night.
- **Lamp:** swings and flickers.
- **Clock:** chimes.
- **Picture:** gets knocked crooked; a tidy pet may straighten it later.
- **Bowl:** clinks, and a hungry pet comes running.
- **Bed:** the cushion puffs up (dragging it still moves it).
- **Pumpkin and mirror:** they react too.

**Tests and fixes**
- 14 new tests (135 in total), including one that every one of the 28 forms is reachable through evolution.
- Several older tests were made robust to the extra random draw for the family line.

## v1.4.0 "The Observer"

Artificial life, emergent behaviour and apparent awareness, layered under the same simple care game. Every unusual behaviour can be switched off in Settings (Experiments → "Unusual: off").

**Phase 1: The Observer (fully implemented)**
- **Cursor model.** The pet learns which interface zones your cursor visits (buttons, toggles, bowl, ball, wall, the pet itself), the transitions between zones, and which of your actions follow a zone, a pair of zones, or the cursor heading toward a button.
- **Prediction.** It predicts your next action and scores itself: hits, misses, recent accuracy and per-action confidence. Confident predictions make it act early, for example trotting to the bowl as your cursor heads for Feed. Wrong predictions lower its confidence (and sometimes puzzle it), and its tables decay daily so it follows your changing habits.
- **Deliberate observation.** It sometimes stops to watch the cursor: motionless, turned toward it, from the front of the screen, or from behind the plant if shy. It gets curious when the cursor stops, and studies repetitive movements.
- **Seven-stage model of you.** Encounter, Association, Prediction, Experimentation, Representation, Communication, Collaboration. These are learning milestones, not ages.
- **Experiments on you.** New signal primitives: coming up to the screen, and pointing at things. Test requests now have a daily budget.

**Phase 2: The Uncanny Creature (fully implemented)**
- **Its own rituals.** Rituals form from action-sequence reinforcement before eating, sleeping, playing, greeting you, or asking for something. They are unique to each pet and fade if unused.
- **Episodic memory.** Strength grows with importance and repetition and decays otherwise. The pet can recall forgotten interactions, for example making the movement that answers a gesture you haven't used for days.
- **Symbolic drawings of the cursor.** An arrow on the wall, and later the cursor beside the thing it associates with you.
- **Time and pause awareness.** It looks at the clock when the world speeds up, then at the speed control, and later glances at the pause button. Pause now truly freezes the pet.
- **Spatial memory.** Drag its bed with the mouse. If it didn't see, it searches the old spot. It may drag the bed back, or gradually get used to the new layout.
- **Boundary trips.** New trips visit the speed and pause controls (it presses them; nothing happens for it) and the edge of the application window.

**Phase 3: The Independent Mind (fully implemented)**
- **Tool use discovered by experiment.** Ball actions are pushed at the wall, the bowl, a trinket or the plant, followed by waiting or chasing. Action → outcome counts turn into skills (rebound, ball in bowl, ball behind plant, knocking a trinket). Goal-directed experimentation lets it free trinkets stuck under the plant with its ball, then pick them up.
- **Loose trinkets** can roll under the plant.
- **Hidden stash** behind the plant. Private activities pause when the cursor comes close and resume when it leaves.
- **Personal arrangements** of its collection.
- **Culture.** Skills discovered by one pet are recorded in the room and bias later generations' experiments.

**Phase 4: Existential Experiments**
- **The mirror** (Settings, optional): a live reflection and five developmental stages, from greeting the "other creature" to examining its own markings. *Implemented.*
- **Memory frame**: the wall picture shows its first form, and it sometimes looks at it, then at itself. *Implemented.*
- **Building on ancestors' drawings.** *Implemented*, as a level-3 rare event.
- **Caretaker experiment**: a curious adult may build a little figure from its trinkets and teach it movements. The figure has its own learning table. *PROTOTYPE*: rare and simple.

**Rare events.** A registry of 18 events across three levels (subtle, uncanny, existential), with prerequisites from real history, level and per-event cooldowns, no events while the pet needs care, and a full history.

**Observation Mode (F9, or Settings).** A developer view with five pages:
- **Now:** intentions, plan, request, game and prediction.
- **Model of you:** stage, accuracy, zones, associations and confidence.
- **Memory:** memories, rituals and beliefs.
- **Learning:** signal success and object experiments.
- **World:** spatial memory, rare events, eligibility and the mirror.

There is also a **reasoning trace** explaining *why* each behaviour happened. **Export log (E)** writes JSON and Markdown.

**Developer tools**
- `tools/devsim.py` (also `run_devsim.bat`): a seeded, accelerated headless simulation with a synthetic player (habitual, random or absent). It reports prediction accuracy, rituals, skills, rare events and cost per frame.
- `--seed N` for reproducible runs.

**Changes**
- Now uses **pygame-ce**. The launchers swap out classic pygame if found; the code is still compatible with classic pygame.
- 32 new tests, 121 in total.
- Older saves upgrade automatically.

**Fixed**
- The offline-diary test was nondeterministic; it is now seeded.

## v1.3.0 "Reciprocity"

The Reciprocal Intelligence System: you and your pet learn each other.

- **Gesture recognition.** Cursor strokes inside the room are recognised: left, right, side-to-side, circle, up, down and wiggle.
- **Imitation, both ways.** The pet performs gestures and waits to see if you copy them. You draw gestures and it tries to copy you. It copies imperfectly at first (a circle may become a sway) and improves when you repeat or confirm.
- **Games the pet invents and leads.** Follow My Lead, Pass the Ball (catch), Echo (chirp rhythms) and Follow the Path. Their length and complexity grow from experience and personality, not from unlocks. You can also lead a path for it to follow.
- **A private language per creature.**
  - Each pet has its own repertoire of signals combining sounds and gestures.
  - It keeps a model of how *you* respond to each one and picks signals by expected success, ambiguity and exploration.
  - It moves through four language levels: Instinctive, Associative, Conventional and Combinatorial.
  - Signals can change meaning over time.
- **The pet experiments on you.** It tests whether its signals still work, for example asking for food when it isn't hungry and then just sniffing the food.
- **Miscommunication and repair.** If you answer with the wrong action, it shakes its head and repairs: it repeats the signal, adds a gesture, approaches the object, tries another signal, and then gives up gracefully. This is capped and never punishes you.
- **Negotiation.** It occasionally prefers something else: rest instead of play, a different game, the window instead of the ball, or declining a snack when it's full. It may play with the ball later "on its own terms". None of this blocks essential care.
- **Boundaries.** Chasing a pet that has backed away teaches it that retreating is needed. Giving it space makes it comfortable enough to approach you.
- **Mutual rituals.** A cursor gesture you keep using at greetings, meals, bedtime or play becomes a shared ritual the pet can start first. Rituals fade with disuse.
- **Creative collaboration.** Click and drag on the lower wall to draw in coral. The pet answers with marks of its own, sometimes copying yours imperfectly. It learns which styles you respond to. New generations can copy fragments of old shared drawings.
- **A model of you.** The pet tracks how you tend to respond: copying gestures, answering sounds or gestures, the ball, drawing, leaving it alone, giving it space, quick visits. This shapes how it interacts with you.
- **Variation.** Imperfect memory (daily decay), attention limits, misperception, exploration, game interests that drift as it grows, and capacity that rises with life stage and curiosity.
- **New Bond tab in Records.**
  - *Shared Memories* records milestones such as first imitation, first learned signal, a signal you recognised, rituals, longest games, the first shared drawing and repaired misunderstandings.
  - The optional *Observation Lab* shows its signal tables, language level, model of you, rituals and its last decision with the reason.
  - *Export report* writes a Markdown file so you can compare relationships, for example after swapping save files.
- **Housekeeping.**
  - Version numbering: `VERSION`, `game/version.py` and this changelog.
  - The version is shown in the window title and in Settings.
  - ZIP files are versioned.
- **Changed.** The v1.2 signal system was replaced by the new language. Older saves get a fresh language on load.

## v1.2.0 "Artificial life"

- Food is served in the bowl. UI text is darker. There are 6-slot Hunger, Happy and Health hearts.
- Added a behaviour Diary, a "While you were away" summary and simulated offline life.
- **Autonomy.** Avoidance and bravery, refusals, territory, rearranging its room, bedtime rituals.
- **Creations and culture.** A wall drawing, collections, a nest and invented games, all persisting across generations.
- **Learning.** Beliefs and experiments, plus the first emergent signal system.
- **Anomalies.** Five rare egg types (Golden, Void, Chimera, Glitch, Pastel) and nine hidden behavioural mutations that emerge later.
- **The Frontier.** Pressing against the screen, climbing the walls, escaping across the UI, and optional desktop roaming on Windows.
- Fixed: `--reset` reloaded the `.bak` backup.
- Fixed: settings and top bar overflowed at the minimum window size.

## v1.1.0 "Living pet"

- **Settings.** Seven theme colours, light and dark mode, sound, and two reset options with backups.
- **Living Pet System.**
  - Awareness: cursor gaze, window focus and return greetings, inactivity, clicks.
  - Hidden emotions, quirks, routines and associations.
  - An interruptible plan system.
  - Room objects: bed, bowl, ball and plant.
  - Rare moments: peekaboo, gifts, dreams, zoomies.

## v1.0.0 "First hatch"

- Core virtual pet: egg to elder, 13 forms including 2 secrets, care actions, illness, discipline, personality, memory, three mini-games, generations and genetics, records, day and night, seasons, chiptune sound effects, JSON saves with capped offline progress, and test speeds.
