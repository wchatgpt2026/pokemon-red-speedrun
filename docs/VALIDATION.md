# WP004: Validation and capacity foundation

This package adds engineering tools and Blue-debug-only starting states. It
does not implement gameplay changes or WP005. Design authority remains
[DESIGN_CHARTER.md](DESIGN_CHARTER.md); architecture is in
[ARCHITECTURE.md](ARCHITECTURE.md). Use RGBDS **1.0.4**, GNU Make, the existing
C build tools, and Python 3 (standard library only for validation).

## Contributor workflow

From the repository root in the supported Unix-like environment:

```sh
rgbasm --version
rgblink --version
rgbfix --version
rgbgfx --version
make -j4                         # Red, Blue, Blue debug
make validate                    # artifact checks + corruption/regression tests
make capacity                    # all banks, holes, baseline deltas
python3 tools/validation.py --json > /tmp/wp-capacity.json
make fixture-battle              # builds Blue debug; prints entry instructions
make fixture-map                 # same ROM, different menu choice
git diff --check
# After committing:
sh .github/checkdiff.sh
git status --short --branch
```

Use `make red`, `make blue`, and `make blue_debug` for individual builds.
`make validation-tests` runs the tooling tests after building all variants.
The fixture targets do **not** launch an emulator or claim a gameplay pass.
An emulator is needed for the observations below. `DEBUG=1` exports additional
symbols; it is not the `_DEBUG` build selector and is not required here.

The normal build emits `.gbc`, `.map`, and `.sym` together. Missing or malformed
artifacts fail validation; they are never treated as zero usage. If a sidecar
was deleted while its ROM remained current, use `make clean && make -j4`.
Make does not track changes in command-line flags: clean before changing them.
Keep ROMs, maps, symbols, emulator saves/states, and logs out of commits.

There are three distinct checks:

- Pristine `baseline-pokered`: upstream `make compare`, unchanged by WP004.
- Modified hack: build assertions/linking plus `make validate capacity`.
- Gameplay: debug fixture observations and normal-build play tests. Structural
  success does not establish mechanics correctness or a playable full route.

## Capacity source, interpretation, and policy

`tools/validation.py` reads RGBDS 1.0.4 linker maps, checking every section and
empty range against bank boundaries and `TOTAL EMPTY`, then reconciling the
region summary. Zero-length sections and symbol aliases are supported. The
hardware windows are explicit; no project section sizes are hand-maintained.
RGBDS `-d` combines WRAM into the `$c000-$dfff` WRAM0 window. RGBDS omits VRAM
from its summary, so VRAM is checked by its bank ranges instead.

The human report shows **free bytes, largest contiguous hole, and signed delta
from the reviewed WP004 baseline** for each allocated ROM bank and RAM region.
Bank numbers are hexadecimal. The JSON report includes used/free bytes, largest
hole, bank identity, and ROM SHA-256. Output has no timestamps or machine paths.

Free totals include ROM0 and all 44 currently allocated ROMX banks, through
`2c`. Each ROM is padded to 1,048,576 bytes; padding beyond allocated banks is
excluded. Total free space is not same-bank capacity. Near pointers, banked
calls, alignment, and fragmentation constrain where code/data can go. In
particular, Red/Blue ROM0's 156 free bytes comprise holes of 66 and 90 bytes;
Blue debug has 66 and 70. A 100-byte resident section cannot simply use that
156-byte total. SRAM figures mean unallocated linker addresses, not permission
to change saved layouts, checksums, or buffer lifetimes.

Guardrails deliberately avoid freezing byte counts:

- RGBDS continues to reject actual overflow and existing table/format assertion
  failures. The script also rejects contradictory/incomplete map output,
  inconsistent ROM size/header/checksums, missing essential symbols, unequal
  variant RAM allocations, and debug fixture symbols in standard ROMs (or
  missing fixture entry symbols in Blue debug).
- Bank topology changes fail pending explicit review of layout and baseline.
  The header's four SRAM banks must all be represented. This is a project
  contract, not a claim that cartridge expansion is impossible.
- Any reduction from baseline in ROM0, WRAM0, HRAM, the WP003 watchlist
  `01 02 03 0e 0f 19 1a 1b 1e 1f`, or a ROMX bank with at most 128 baseline
  free bytes emits a warning. The last advisory rule also covers `09 0c 13`.
  It means "already less than a small block of code," not a hard budget.
- Warnings do not fail CI. Every bank's signed delta remains visible, including
  unconstrained banks. A reviewed relocation or growth is allowed. Attach
  before/after reports and explain critical losses in the work package.

`tools/capacity-baseline.json` records all banks for all variants. It is a
reviewed measurement, never automatically rewritten by Make or CI. For an
intentional new baseline, first capture `--json` to a separate temporary file,
review the deltas and allocation changes, then explicitly replace the baseline
and update this documentation. Do not redirect onto the file being read.
ROM hashes in the baseline are evidence of this revision, not permanent
byte-identity requirements for future gameplay work.

### Measured post-WP004 headroom

All numbers below are free bytes, measured with RGBDS 1.0.4. The full per-bank
record is in the baseline JSON and reproduced by `make capacity`.

| Region / bank | Red | Blue | Blue debug |
| --- | ---: | ---: | ---: |
| ROM0 | 156 | 156 | 136 |
| ROMX `01` | 951 | 951 | 596 |
| ROMX `02` | 12 | 12 | 12 |
| ROMX `03` | 950 | 950 | 950 |
| ROMX `09` | 72 | 72 | 72 |
| ROMX `0c` | 112 | 112 | 112 |
| ROMX `0e` | 1,050 | 1,050 | 1,050 |
| ROMX `0f` | 1,080 | 1,080 | 1,080 |
| ROMX `13` | 94 | 94 | 94 |
| ROMX `19` | 32 | 32 | 32 |
| ROMX `1a` | 1 | 17 | 17 |
| ROMX `1b` | 0 | 0 | 0 |
| ROMX `1e` | 64 | 64 | 64 |
| ROMX `1f` | 6 | 6 | 6 |
| ROMX `2c` | 14,833 | 14,833 | 14,833 |
| All allocated ROM (including ROM0) | 161,853 | 161,868 | 161,477 |
| WRAM0 | 30 | 30 | 30 |
| HRAM | 0 | 0 | 0 |
| SRAM `00` | 1,960 | 1,960 | 1,960 |
| SRAM `01` | 2,780 | 2,780 | 2,780 |
| SRAM `02` | 1,453 | 1,453 | 1,453 |
| SRAM `03` | 1,453 | 1,453 | 1,453 |
| All declared SRAM | 7,646 | 7,646 | 7,646 |

WP004 consumes 37 additional bytes in Blue debug bank `01` versus WP003 (633
to 596). Red and Blue usage, all RAM allocations, and all other debug banks
remain unchanged. No HRAM headroom exists; Red bank `1a` has only one byte.

## Fixture entry and isolation

Open **`pokeblue_debug.gbc`**, with its matching `.sym`, in a separate emulator
test directory. Start from a reset/power-on, not an old emulator save state.
Wait for the title screen showing the Pokémon logo; press the Game Boy
**Select** button. Choose **FIGHT** or **MAP**, then A. B returns to the title.
Use the Game Boy controls mapped in your SameBoy preferences.

`engine/debug/validation_fixtures.asm` is included only under `_DEBUG` and has
an assembly assertion enforcing that condition. FIGHT replaces the menu's
legacy `TestBattle` entry; MAP replaces its seven-badge DEBUG preset. The old
unreferenced `TestBattle` code remains for standard ROM byte identity but is
not the WP004 fixture. In particular its uninitialized bag and special move
selection mode are not used. No new RAM or production battle hooks were added.

Use separate test SRAM/save files. Selecting a fixture reconstructs RAM; it
does not erase cartridge SRAM. Choosing SAVE in MAP writes the ordinary save
format and can overwrite the test save. Never move fixture saves into a race
ROM. Standard builds cannot enter these fixtures; their ROM bytes are unchanged.

## Battle fixture

FIGHT clears the player/main/party/box region and sprite data through
`PrepareOakSpeech`, runs `InitPlayerData2`, installs a fixed party, and enters
the ordinary `InitOpponent` trainer path. Link mode, prior battle type/state,
debug mode, and options initialization are explicitly reset. Bag and PC item
lists are empty and terminated; money is 3,000, badges are zero, progression
flags are cleared, and toggleable objects use new-game defaults. The fixture
does not use `BIT_TEST_BATTLE` or turn on debug battle rules.

| Initial field | Player | Enemy |
| --- | --- | --- |
| Pokémon | Rhydon, only party member | Youngster #2's only Pokémon: Spearow |
| Level | 20 | 14 |
| HP / status | 72/72, healthy | 37/37, healthy |
| Attack / Defense / Speed / Special | 60 / 56 / 24 / 26 | 24 / 15 / 26 / 15 |
| DV bytes | `88 88` (HP DV 0) | `98 88` (ordinary trainer DVs, HP DV 8) |
| Stat experience | all zero | all zero |
| Moves (PP) | Horn Attack (25), Stomp (20), Tail Whip (30), Fury Attack (20) | Peck (35), Growl (40), Leer (30), empty slot |

Rhydon's fixed record is a test input, not a replacement species definition:
10,000 experience, full PP without PP Ups, OT ID `1234` matching the player,
and nickname RHYDON. It therefore needs neither an obedience override nor a
badge boost. Enemy data is the existing unmodified Youngster party and ordinary
learnset. If later packages change that trainer, learnset, or species, explicitly
review this contract rather than assuming the fixture still matches the table.

Normal battle initialization supplies neutral stat stages (7), cleared
volatile status, enemy party/PP, active battle copies, and turn bookkeeping.
`WP004BattleReady` is **before** that initialization: inspect enemy/active
battle state at `DisplayBattleMenu` instead. Scratch memory outside the cleared
regions, graphics/audio state, hardware timers, and RNG are not globally reset
on each repeat; the standard battle entry/exit paths manage their own lifetimes.
Only enter from a fresh boot/title, not by jumping into the routine from arbitrary
gameplay. Victory or defeat returns to a freshly installed starting party/bag;
reset the emulator to leave the loop. Victory/repeat was exercised; defeat is
still a manual test case.

**This is a controlled initial state, not deterministic battle execution.**
RNG, `rDIV`, VBlank, critical hits, damage rolls, accuracy, and enemy decisions
remain ordinary game behavior. Record ROM hash, emulator/version/model, moves,
observations, and any saved-state origin. For frame-identical comparisons use
the same emulator and compatible save state/input trace; no cross-build or
seed-only guarantee is provided. No battle damage expectations are asserted.

### SameBoy battle observation

1. Build `make fixture-battle`, load the new debug ROM, reset, and select FIGHT
   as above. Confirm Youngster sends out level-14 Spearow and your level-20
   Rhydon starts at 72/72 HP.
2. Open FIGHT and check all four moves/PP. Open ITEM and confirm the bag is
   empty. Cancel back normally. Select Horn Attack; observe a normal turn.
3. Complete the fight, advance victory text, and confirm the next fight starts
   with full HP and PP. Separately test a defeat/restart when investigating loss
   handling; do not infer that result from the victory smoke test.
4. For exact memory inspection on Windows, run
   `sameboy_debugger.exe pokeblue_debug.gbc` with the matching `.sym` alongside.
   Break with Ctrl+C and enter:

```text
breakpoint DisplayBattleMenu
continue
examine/2 wBattleMonHP
examine/2 wEnemyMonHP
examine/4 wBattleMonMoves
examine/4 wEnemyMonMoves
examine/4 wBattleMonPP
examine/4 wEnemyMonPP
examine/8 wPlayerMonStatMods
examine/8 wEnemyMonStatMods
```

Remove the breakpoint with `delete` before continuing freely. If symbol lookup
is unavailable, use the bank:address printed for that symbol in the matching
`.sym`. See [SameBoy's debugger documentation](https://sameboy.github.io/debugger/)
for the console and command syntax. Compare memory at the first menu, before
taking a turn; later HP, PP, and stages naturally change.

## Map/progression fixture

MAP uses the ordinary Oak/new-game initializer with the debug flag only long
enough to skip naming/speech and select the existing Pallet fly warp. After the
short shrink/intro sequence, it clears `BIT_DEBUG_MODE` and enters Pallet Town
(`wCurMap=00`) at **x=5, y=6**, immediately outside the player's house.
It uses the same fixed Rhydon, zero badges/beat-Gym flags, walking state, and
player ID as FIGHT. No hold-B debug encounter/trainer/movement shortcut is enabled.

Exact initialized progression contract:

- `PrepareOakSpeech` clears player/main/party/box data, sprite data, map-script
  counters, event flags, and previously loaded progression. Names come from its
  existing debug-name constants. Options are default medium text/animations on/
  shift; the fixture does not inherit bicycle/warp/debug flags from a save.
- `InitPlayerData2` installs default object visibility, zero badges/coins, 3,000
  money, and empty bag/box lists. Oak's normal setup adds one Potion to the PC.
- Only `EVENT_FOLLOWED_OAK_INTO_LAB` and `EVENT_GOT_STARTER` are then set. The
  former bypasses the north-exit Oak escort trigger. All other event bits stay
  at cleared/new-game values until normal scripts change them. There is no
  Pokédex, no completed Gyms, no Fly destinations unlocked, and no parcel quest
  completion. Pokédex owned/seen bitsets stay empty despite the synthetic party.
- `wLastMap` and initial blackout map are Pallet; map pointer, coordinates,
  sub-block offsets, and tileset come from the existing special-warp data.
  Ordinary `SpecialEnterMap` initializes rendering/sprites and enables the
  game timer. Playtime, timers, and NPC movement advance normally.

This is deliberately a **minimal synthetic state**, not a coherent completed
opening story or a full practice save. Starter-choice values and unrelated
story/script state remain cleared/default. Do not use Oak's lab/rival/parcel
sequence as a validated route from this preset. WP004 establishes repeatable
location, flags, entry/reentry, and save/load; it proves no flexible Gym order.
Later packages should add an explicitly named preset with audited events,
object visibility, script counters, travel/blackout data, and party state for
their exact gate. Do not scatter direct coordinate writes through engine code.

### SameBoy map observation

1. Build `make fixture-map`, load/reset Blue debug, choose MAP, and advance any
   remaining introductory text with A. Confirm Pallet `(5,6)`, Rhydon, no badges,
   and empty bag. `breakpoint WP004MapReady` allows inspecting those coordinates,
   `wObtainedBadges`, and `wEventFlags` before map entry; then `delete`, `continue`.
2. Press Up once into the house. Wait until the warp finishes: Red's House 1F,
   map `$25`, `(2,7)`. Press Down once, wait, and confirm return to Pallet `(5,6)`.
3. Press Start, choose SAVE (fourth entry without the Pokédex), and confirm YES.
   Wait for the saved message and return to the map. Reset; press Start at the
   title, select CONTINUE, then A on the continue information screen. Do not
   choose MAP again: that would recreate the fixture instead of testing reload.
4. Confirm map/coordinates, zero badges, the two event bits, party HP/PP, and
   empty bag persist. Repeat house entry/exit after loading. Walk north to check
   the intended escort bypass only; do not infer other progression gates.

## Evidence, CI, and remaining limitations

Measured from accepted WP003 base `ba687f4cd58ed0349bce481143d9eaa04e0612b3`:

- Red, Blue, and Blue debug assembled/linked/fixed with all four RGBDS tools at
  1.0.4. `make validate capacity`, both fixture targets, and 11 tooling tests
  passed. Tests include missing/truncated maps, incorrect totals, omitted
  ranges, unknown records, duplicate banks, summary disagreement, ROM checksum
  corruption, fixture leakage, advisory budget reduction, and topology change.
- Red SHA-256 `976f0dd7b46f9d31c0b22340d760e021d5c755dcb7c51192b6777af13b0f5123`
  and Blue SHA-256 `f3f0f59708834cc8f06b21eab0b5726986db894a00dc6c803476b5a0af8e5a82`
  match freshly built accepted-source ROMs exactly. Standard behavior/data is
  unchanged, including the accepted WP002 marker. No vanilla hashes changed.
- A temporary PyBoy **2.6.1**, headless, sound disabled, default auto-detected
  model smoke test booted the ROM normally and used button input. Read-only
  execution hooks inspected fixture and battle-menu state. It observed the
  battle starting HP/DVs/moves, victory and repeat with reset party; MAP at
  `(5,6)`, house entry at `(2,7)`, return, ordinary SAVE, soft reset, and CONTINUE
  restoring the party and coordinates. This is limited runtime evidence, not
  a battle mechanics suite, audio test, or timing reproducibility claim.
- Linux and macOS fork CI now run `make validate capacity` after the existing
  build. Reports/warnings appear in job logs. Upstream `make compare` and
  `.github/checkdiff.sh` are preserved. No emulator/dependency/timing loop was
  added to CI. Existing master-push/PR triggers are unchanged: a package-branch
  push alone does not run these jobs.

Manual SameBoy visual/input/audio checks remain necessary; SameBoy itself was
not run in Codex. Full progression, defeat, other hardware models, arbitrary
saved-state entry, and long-term save compatibility are not established. The
normal ROM byte comparison is stronger than source inspection for WP004's
no-production-change claim, but it is not a substitute for testing later
intentional mechanics or progression changes.
