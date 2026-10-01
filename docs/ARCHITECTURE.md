# WP003: Technical architecture survey and implementation roadmap

## Scope and evidence

This engineering map describes `wchatgpt2026/pokemon-red-speedrun` at accepted
`master` commit `e195871fbadd5e3c1af14bc939ebadf22c0a1e23`. WP003 adds only this
document. It proposes technical sequencing, not gameplay design decisions.
Read [DESIGN_CHARTER.md](DESIGN_CHARTER.md) for design scope and
[DEVELOPMENT.md](DEVELOPMENT.md) for the build/validation workflow.

Evidence is repository source inspection plus a successful `make -j4` in Ubuntu
WSL with RGBDS **1.0.4**, producing Red, Blue, and Blue debug ROMs and linker
maps. The measurements below describe the accepted source, including the WP002
text marker. No emulator experiments were performed for this survey. Source
comments about bugs identify candidates for testing, not authorization to fix
them. Generated ROMs, symbols, maps, and the build log remain untracked.

## 1. Build, storage, and ROM organization

### Entry points and variants

`Makefile` assembles nine object groups: `audio.asm`, `home.asm`, `main.asm`,
`maps.asm`, `ram.asm`, `text.asm`, `gfx/pics.asm`, `gfx/sprites.asm`, and
`gfx/tilesets.asm`. `includes.asm` is preincluded for constants/macros.
`home.asm` includes the header, interrupt vectors, initialization, resident
helpers, and overworld/text entry paths. `main.asm` groups banked engines and
their data. `maps.asm` groups map headers, objects, blocks, and scripts;
`text.asm` groups banked dialogue. `ram.asm` includes the RAM layouts.

Object suffixes select `-D _RED`, `-D _BLUE`, or `-D _BLUE -D _DEBUG`.
Conditional assembly inside data and graphics selects version differences;
there is no runtime Red/Blue selection switch. `red_vc`/`blue_vc` add separate
VC definitions and patches. `.rgbds-version` and CI select 1.0.4;
`rgbdscheck.asm` permits a broader minimum, which is not the project default.

`layout.link` assigns named sections to banks. ROM0 is resident at
`$0000-$3fff`; a selected 16 KB ROMX bank occupies `$4000-$7fff`.
`home/bankswitch.asm`, `macros/farcall.asm`, `home/predef.asm`, and
`data/predef_pointers.asm` provide cross-bank calls. A plain `dw` pointer carries
no bank; moving a table or routine requires auditing its callers and bank
context, including literal bank numbers (for example in `home/pokemon.asm`).

| Banks (hex) | Useful grouping from `layout.link` and assembly includes |
| --- | --- |
| `00` | Home, vectors, header, resident helpers |
| `01`, `03` | Mixed menus/events, overworld, item handling; Mew data in `01` |
| `02`, `08`, `1f` | Three audio engine/data groups |
| `04-05`, `09-0c`, `14-16`, `1a` | Battle helper sections sharing banks with sprites, pictures, maps, or tilesets |
| `0e` | `Battle Engine 7`: moves, base stats, trainer AI/parties, evolution/learnsets, battle helpers |
| `0f` | `Battle Core`: `engine/battle/core.asm` and `effects.asm` |
| `06-07`, `11-18`, `1d` | Map sections sharing space with other engines/data |
| `19-1b` | Tileset graphics/block definitions, with a battle section in `1a` |
| `10`, `1c`, `1e` | Mixed movie, menu, save, and other engine sections; inspect `main.asm` for exact inclusions |
| `20-2a`, `2b`, `2c` | Dialogue, Pokédex text, move names respectively |

### Measured headroom and constraints

All three generated ROM files are 1,048,576 bytes after linker/fixer padding.
The Red map reports 44 used ROMX banks with **161,697 bytes free within those
banks**, plus **156 bytes free in ROM0**. That aggregate is not one contiguous
engine allocation. The linker map covers allocated banks through `2c`;
ROM-file padding beyond them is not evidence that new sections or bank switches
are already configured there.

| Region/bank | Red free bytes | Blue free bytes | Blue debug free bytes | Implication |
| --- | ---: | ---: | ---: | --- |
| ROM0 | 156 | 156 | 136 | Avoid adding substantial resident code |
| `01` | 951 | 951 | 633 | Menus/debug/new-game work competes here |
| `02` | 12 | 12 | 12 | Audio growth would require relocation |
| `03` | 950 | 950 | 950 | Item/overworld changes have limited local room |
| `0e` | 1,050 | 1,050 | 1,050 | AI, trainer formats, species/evolution data compete |
| `0f` | 1,080 | 1,080 | 1,080 | Mechanics work cannot assume unlimited inline growth |
| `19` | 32 | 32 | 32 | Tileset expansion is constrained |
| `1a` | 1 | 17 | 17 | Graphics and PP helper share a nearly full bank |
| `1b` | 0 | 0 | 0 | Tileset bank is full |
| `2c` | 14,833 | 14,833 | 14,833 | Significant local room, subject to bank-aware relocation |
| WRAM0 | 30 | 30 | 30 | Persistent boss/practice state needs a RAM plan |
| HRAM | 0 | 0 | 0 | No new HRAM allocation without restructuring |

Other tight Red banks include `1f` (6 bytes), `1e` (64), `09` (72), `13` (94),
and `0c` (112). Relocation can be needed well before total ROM capacity runs out.
SRAM has 7,646 unallocated bytes across its four declared banks, but its existing
save and sprite-buffer layouts are contractual; unused bytes are not a ready
save-format extension.

The Makefile always emits `<rom>.map` and `<rom>.sym`; `DEBUG=1` additionally
passes assembler `-E` to export more symbols. This flag is distinct from the
`blue_debug` target and `_DEBUG` behavior. Use `.map` section ranges, `EMPTY`
and `TOTAL EMPTY` lines to measure per-bank room; use `.sym` bank:address
entries for emulator breakpoints/watchpoints and relocation audits. Recheck all
three variants after format changes, graphics changes, or bank moves. Preserve
artifacts outside Git when comparing revisions.

## 2. Pokémon base data and indexing

`data/pokemon/base_stats.asm` assembles the ordinary base records in Pokédex
order; individual files under `data/pokemon/base_stats/` contain five byte-sized
stats (HP, Attack, Defense, Speed, Special), two types, catch rate, base
experience, sprite metadata/pointers, four initial moves, growth rate, TM/HM
bitset, and padding. `constants/pokemon_data_constants.asm` defines offsets and
`BASE_DATA_SIZE` (28 bytes). There is one Special stat, not separate offensive
and defensive Special values.

`constants/pokemon_constants.asm` defines internal species IDs, including holes
and special picture IDs. These are **not Pokédex numbers**.
`constants/pokedex_constants.asm` and `data/pokemon/dex_order.asm` describe the
other ordering. `GetMonHeader` in `home/pokemon.asm` converts internal IDs using
`IndexToPokedex`, indexes `BaseStats`, and copies the record into `wMonHeader`.
`IndexToPokedex` itself is in `engine/menus/pokedex.asm`.
Mew is special-cased to `MewBaseStats` in `data/pokemon/mew.asm`, which includes
its base-stat file separately. Fossil/Ghost IDs have separate picture handling.
Do not reorder IDs as part of a rebalance.

`data/pokemon/evos_moves.asm` contains `EvosMovesPointerTable`, indexed by
internal ID, with evolution records followed by ordered level/move pairs;
both lists end with zero. Initial moves are in the base record, not this
level-up list. `engine/pokemon/evos_moves.asm` supplies `WriteMonMoves`,
learning and evolution consumers. `engine/pokemon/add_mon.asm` constructs
party mons and calls the move-generation path, so changing learnsets also
changes ordinary trainer and wild movesets.

Both `WriteMonMoves` and `LearnMoveFromLevelUp` skip evolution data by scanning
for the first zero byte, not by parsing each method's length. Existing evolution
payloads therefore use nonzero parameters (including minimum level 1 for
stone/trade records). A zero-valued parameter in a new method can silently
misalign the learnset even if the evolution dispatcher itself is updated.

`macros/data.asm` supplies `tmhm`; its bit order is the machine mapping in
`constants/item_constants.asm` and `data/moves/tmhm_moves.asm`.
`engine/items/tms.asm` and `ItemUseTMHM` in `engine/items/item_effects.asm`
consume compatibility. Changing which move a TM represents affects every
compatible species, shop, reward, and machine name using that machine ID.

`home/move_mon.asm` (`CalcStats`, `CalcStat`) combines base stats, level, DVs,
and stat experience. `engine/pokemon/experience.asm` and
`data/growth_rates.asm` implement experience/growth. Party and box layouts,
four move slots, six-mon capacity, 24-bit experience, and PP bit packing are
defined in `constants/pokemon_data_constants.asm` and `macros/ram.asm`.
Changing values within the existing records is straightforward; changing the
record shape, stat count, or species namespace is foundational work.
`engine/battle/experience.asm` (`GainExperience`) consumes enemy base experience
and level, divides among eligible participants, applies trainer/traded boosts,
and adds stat experience from enemy base stats. This connects rebalance data
to player growth beyond the per-species experience curve.

Non-obvious rebalance coupling: base Speed feeds critical-hit probability;
Special affects both special damage and defense; types select physical/special
damage by type category; catch rate/base experience affect routing/resources;
learnsets affect default enemy moves. Existing saved mons retain stored stats,
types, moves, and growth history until relevant recalculation/update paths run;
save compatibility must be tested rather than assumed.

## 3. Moves, battle data, and mechanics decision points

`data/moves/moves.asm` (`Moves`, `move`) stores six bytes per move:
animation/ID, effect, power, type, scaled accuracy, and PP. IDs/effect IDs are in
`constants/move_constants.asm` and `constants/move_effect_constants.asm`;
`constants/battle_constants.asm` defines battle structure/state conventions.
The `move` macro asserts base PP is at most 40. Current PP shares its byte with
PP Up count (`PP_MASK`/`PP_UP_MASK`), so increasing PP is not an unrestricted
byte edit. Move names and animations live under `data/moves/`.

`engine/battle/core.asm` orchestrates `MainInBattleLoop`, `SelectEnemyMove`,
`ExecutePlayerMove`, and `ExecuteEnemyMove`. Player/enemy execution paths are
partly duplicated. `hWhoseTurn` selects shared helpers and mirrored RAM fields.
`GetCurrentMove`/`ReloadMoveData` load move records into battle RAM.
`engine/battle/effects.asm` (`JumpMoveEffect`, `_JumpMoveEffect`) dispatches
through `data/moves/effects_pointers.asm` (`MoveEffectPointerTable`). Some
effects use banked `engine/battle/move_effects/*.asm` handlers; others are inline.

Dispatch timing also depends on `data/battle/residual_effects_1.asm`,
`residual_effects_2.asm`, `special_effects.asm`, `set_damage_effects.asm`, and
`always_happen_effects.asm`. Merely adding an effect pointer does not establish
when it executes, whether it tests accuracy, or whether it runs after a KO.

For ordinary damage, `CalculateDamage` performs integer operations corresponding
to `(floor(2 * level / 5) + 2) * power * attack / defense / 50`, then adds 2
with a neutral-damage cap of 999. `AdjustDamageForMoveType` adds half the damage
for STAB and applies matchup multipliers; `RandomizeDamage` samples 217-255 and
multiplies by that value/255. Intermediate truncation, high-stat scaling, and
special-effect branches make the routines authoritative over an algebraic
formula. `GetDamageVarsFor*Attack` compares type against `SPECIAL` (defined in
`constants/type_constants.asm`) to choose the stat pair; no per-move category
field exists.

| Topic | Actual implementation and coupling |
| --- | --- |
| Type effectiveness | `data/types/type_matchups.asm` (`TypeEffects`); core `AdjustDamageForMoveType` handles STAB/type multiplication. `AIGetTypeEffectiveness` is a separate consumer and contains a documented `$10` versus decimal 10 initialization issue. Changes need both damage and AI checks. |
| Critical hits | Core `CriticalHitTest`, `data/battle/critical_hit_moves.asm` (`HighCriticalMoves`). Starts from base Speed/2, modifies threshold for high-critical moves and `GETTING_PUMPED`, then compares a rotated random byte. |
| Damage | Core `GetDamageVarsForPlayerAttack`/`GetDamageVarsForEnemyAttack`, `CalculateDamage`, `AdjustDamageForMoveType`, `RandomizeDamage`. Type category selects Attack/Defense versus Special; criticals use unmodified stats and double level. Screens, burn, Explosion, fixed damage, Counter, and integer-width/truncation paths need individual tests. |
| Stat stages | `StatModifierUpEffect`/`StatModifierDownEffect` in `effects.asm`; core `CalculateModifiedStats`/`CalculateModifiedStat`; `data/battle/stat_modifiers.asm`. Stages use an encoded neutral value of 7, bounds 1-13. Badge and burn/paralysis adjustments interact with recalculation. |
| Status | Core `CheckPlayerStatusConditions`, `CheckEnemyStatusConditions`, `HandlePoisonBurnLeechSeed`; `effects.asm` sleep/poison/burn/freeze handlers and banked paralysis/Haze/heal handlers. Persistent `MON_STATUS` differs from volatile battle flags/counters. Also inspect overworld poison (`engine/events/poison.asm`) and healing/status displays. |
| Substitute | Banked `SubstituteEffect_` in `engine/battle/move_effects/substitute.asm`; core `ApplyDamageTo*Pokemon`, `AttackSubstitute`, `MoveHitTest`; `effects.asm` `CheckTargetSubstitute` and individual status handlers. A shared target check is not applied uniformly to every effect. |
| Hyper Beam | `HyperBeamEffect`/`ClearHyperBeam` in `effects.asm`, core recharge checks and post-hit effect sequencing. `NEEDS_TO_RECHARGE` is set only when dispatch reaches that effect. KO returns before ordinary final effects; Substitute breaking zeroes the attacker's effect. Thus recharge depends on these paths, not just the move definition. |
| Trapping | `TrappingEffect` in `effects.asm`, core multi-turn status checks, `CheckNumAttacksLeft`, and `MoveHitTest`. Uses `USING_TRAPPING_MOVE`, attack counters, and saved damage; target action suppression is in turn flow. Trapping setup clears target Hyper Beam recharge even before hit testing; switching/status interrupts need testing. |
| Focus Energy | `engine/battle/move_effects/focus_energy.asm` sets `GETTING_PUMPED`; core `CriticalHitTest` shifts right where its comment identifies the intended left shift. The observed algorithm reduces ordinary critical chance to about one quarter. Dire Hit uses the same flag. |
| 1/256 miss | Core `MoveHitTest`/`CalcHitChance`: scaled accuracy caps at 255, then random byte `>=` threshold misses. It is not solved by entering 100 in move data. Swift and X Accuracy take bypass paths; non-damaging effects can run their own hit tests. |

Explicit source hazards worth regression fixtures: Substitute's HP affordability
check can allow exactly affordable use to leave zero HP; `AttackSubstitute`
does not replace `wDamage` with absorbed HP on break; the Swift fix left the
draining-move Substitute comparison checking a clobbered value in `MoveHitTest`.
These findings identify implementation sites, not a complete bug catalogue.
Test every adopted mechanics change for both sides, substitute/no substitute,
KO/no KO, multi-hit, status, switching, and link-battle exclusions as applicable.

## 4. Trainers and boss team representation

`constants/trainer_constants.asm` defines classes; names, portraits, reward
money, encounter types, party data, and AI tables are under `data/trainers/`.
`TrainerDataPointers` in `parties.asm` indexes class; `wTrainerNo` selects a
one-based entry within that class by scanning zero-terminated teams.
`ReadTrainer` in `engine/battle/read_trainer_party.asm` supports:

- A common level followed by species bytes and zero.
- `$ff` followed by level/species pairs and zero, allowing per-mon levels.

`AddPartyMon` generates stats/default moves; the engine party limit is six.
Core `LoadEnemyMonData` supplies fixed trainer DVs (`ATKDEFDV_TRAINER`,
`SPDSPCDV_TRAINER`); wild enemies instead get random DVs. There is no per-team
DV/stat-experience customization payload in the trainer records.
No general four-moves-per-mon payload exists in either trainer format.
`data/trainers/special_moves.asm` has `LoneMoves` selected by script-set
`wLoneAttackNo`, and `TeamMoves` keyed by class. Despite that name, the reader
assigns the class move to the fifth mon's third move slot, not the whole team.
Lone overrides use a zero-based party index and third slot. Champion Rival
has hardcoded first-mon and sixth-mon overrides based on `wRivalStarter`.

Gym Leaders have individual classes; Rocket grunts share `ROCKET`; Giovanni
has his own class; Rival phases use `RIVAL1`, `RIVAL2`, `RIVAL3`, with separate
party entries for starter choices; Elite Four members have individual classes.
`scripts/*Gym.asm`, `scripts/Route22.asm`, `scripts/SilphCo7F.asm`, and
`scripts/ChampionsRoom.asm` select encounters. Map objects can store trainer
class/number directly, while scripted bosses set battle variables explicitly.

Species/level edits and six-member teams fit existing formats. Many fully
custom boss movesets need a reader/format extension or a separate override
table. Prototype explicit moves and PP initialization, class+trainer identity,
and how entries are skipped before content work. The old skip loop treats
every zero byte as a terminator: embedding `NO_MOVE` in a new payload without
changing skipping logic is unsafe. Preserve old format compatibility or migrate
all consumers deliberately. Reward money is class base money multiplied by
the last loaded mon's level in `ReadTrainer`; reordering teams can change payout.

## 5. Trainer AI

`engine/battle/trainer_ai.asm` has two distinct decisions:

1. `AIEnemyTrainerChooseMoves` starts four scores at 10 in `wBuffer`, penalizes
   disabled moves, applies class layers from
   `data/trainers/move_choices.asm` (`TrainerClassMoveChoiceModifications`),
   and returns only minimum-score moves. Core `SelectEnemyMove` samples slots
   with `BattleRandom`, rejecting absent/disabled entries.
2. `TrainerAI` uses `data/trainers/ai_pointers.asm` (`TrainerAIPointers`),
   class-specific routines, `Random`, and per-active-mon `wAICount` to decide
   item use or switching. Carry signals that an AI action consumed the turn.
   It excludes wild and link battles.

Layer 1 discourages non-damaging status when the player is already statused.
Layer 2 encourages ranges of effect IDs when `wAILayer2Encouragement == 1`.
Layer 3 encourages type advantages even on non-damaging moves, and penalizes
some bad damaging choices using a coarse alternative-move scan. Layer 4 is a
no-op. This is not damage prediction, multi-turn planning, or a knowledge model.
Enemy ordinary move selection does not enforce player-like PP depletion;
audit `SelectEnemyMove` and `DecrementPP` before designing PP/resource tactics.

Class routines specify fixed item types and probabilities: e.g. Brock heals
status, Misty can use X Defend, Lance can Hyper Potion. They are not inventories
encoded per trainer. `AIUse*`, `AIRecoverHP`, `AICureStatus`, and
`AISwitchIfEnoughMons` share party synchronization and battle effects.
`CooltrainerFAI` explicitly has a commented-out early return, so its nominal
probability gate is ineffective. The separate type evaluator issue noted above
and encouraging status moves on type alone are visible limitations.

Stronger, learnable AI likely needs per-boss policy identity, legal-action
filtering, deliberate tie rules, bounded item budgets, and a tested switching
policy. Decide observable inputs and randomness policy before implementing it.
Do not infer that deterministic move choice makes a battle deterministic: speed
ties, status, accuracy, damage, and item decisions still consume RNG. Keep
policy evaluation from overwriting the chosen move state (`ReadMove` currently
writes `wEnemyMove*`), preserve turn-consumption conventions, and avoid exhausting
bank `0e` or permanent RAM. Prototype one boss and an ordinary trainer together.

## 6. Wild encounters

`data/wild/grass_water.asm` (`WildDataPointers`) indexes map ID and includes
`data/wild/maps/*.asm`. Each map has a grass rate, ten level/species pairs when
nonzero, then a water rate and ten pairs when nonzero. `LoadWildData` in
`engine/overworld/wild_mons.asm` copies these into `wGrassMons`/`wWaterMons`.
`macros/asserts.asm` validates encounter-list sizes.

`TryDoWildEncounter` in `engine/battle/wild_encounters.asm` checks movement,
warps/doors, tiles, rates, Repel, and slot selection.
`data/wild/probabilities.asm` provides unequal slot weights. Levels are fixed
per slot, so a level range comes from multiple entries rather than min/max
sampling. Rate is compared against a byte, not interpreted as a percentage.
Repel rejects levels below the first party mon's level. Indoor/forest checks
and asymmetric shoreline tile tests mean tables alone do not determine where
encounters are possible.

`ItemUseOldRod` in `engine/items/item_effects.asm` hardcodes its encounter;
`ItemUseGoodRod` uses `data/wild/good_rod.asm`. `ReadSuperRodData` consumes
`data/wild/super_rod.asm`, mapping areas to shared counted fishing groups.
Fishing has separate bite/selection flow. Static species/level objects use
the trainer-shaped object payload and scripts; inspect `scripts/PowerPlant.asm`,
`scripts/SeafoamIslandsB4F.asm`, `scripts/VictoryRoad2F.asm`,
`scripts/CeruleanCaveB1F.asm`, and Snorlax scripts. Tower Ghost behavior also
has dedicated core and script checks; gifts/trades/prizes are separate sources.

Version-specific tables use `IF DEF(_RED)`/`_BLUE` inside map files. Shared
pointer targets (e.g. sea routes), fishing groups, and version branches must
be audited before redistribution. Aggressive redistribution within existing
slots/maps is low engine complexity. New encounter methods, different slot
counts, or making previously inert terrain encounter-capable require engine
or map work and Pokédex-location validation (`FindWildLocationsOfMon`).

## 7. Maps, events, objects, and expansion

The practical map bundle is:

- `constants/map_constants.asm`: ID and width/height **in blocks**, with
  ordered city/route/indoor groups.
- `data/maps/headers/<Map>.asm`: `map_header`, optional `connection`,
  `end_map_header`; tileset, dimensions, blocks, text/script pointers, objects.
- `maps/<Map>.blk`: block-ID grid. `gfx/tilesets.asm`,
  `gfx/tilesets/*`, and `data/tilesets/tileset_headers.asm` associate tile graphics,
  4x4-tile block definitions, and collision data. Objects use finer coordinates
  (two movement positions per block dimension).
- `data/maps/objects/<Map>.asm`: border block, warps, background signs,
  NPC/trainer/item objects, and warp arrival displacement data.
- `scripts/<Map>.asm`: map script state machine, trainer headers, text pointer
  table, dialogue wrappers, event checks, movements, and block replacements.
- `text/<Map>.asm`: banked text reached through script `text_far` wrappers.

`maps.asm` places these into named map sections; script sections need not be
next to the header/block section. `MapHeaderPointers` and `MapHeaderBanks` in
`data/maps/` select the header; `home/overworld.asm` (`LoadMapData`,
`LoadMapHeader`, `SwitchToMapRomBank`) loads connections/objects/scripts and
handles bank context. `data/maps/songs.asm`, `sprite_sets.asm`,
`town_map_entries.asm`, and `data/wild/grass_water.asm` have parallel ID-based
coverage. Toggleable visibility uses `data/maps/toggleable_objects.asm`,
`constants/toggle_constants.asm`, and `engine/overworld/toggleable_objects.asm`.
Header block/object/script/text-table pointers are near pointers interpreted
in the map bank. Separate named sections do not remove that same-bank contract;
banked dialogue itself is reached through explicit far-text commands.

`macros/scripts/maps.asm` defines `warp_event`, `bg_event`, `object_event`,
`trainer`, connections, and headers. Warp IDs are authored one-based and stored
zero-based; `LAST_MAP` (`$ff`, authored `-1`) returns to `wLastMap`.
Objects encode trainer/item flags in their text byte. Ordinary trainer objects
link class/party number to script trainer headers, sight range, battle dialogue,
and defeat flags (`home/trainers*.asm`,
`engine/overworld/trainer_sight.asm`). Visible item objects feed
`engine/events/pick_up_item.asm`; hidden items/events use
`data/events/hidden_events.asm`, `hidden_item_coords.asm`,
`engine/events/hidden_items.asm`, and hidden-event dispatch, not object lists.

### Practical modification paths

| Task | Required work and validation |
| --- | --- |
| Modify a route | Edit blocks and objects; if dimensions change, update constants, warp displacements, both ends of connections, coordinate-trigger scripts, and any scripted block replacement. Check collision, trainer sight, visibility, encounters, and reentry after save/load. |
| Expand a dungeon | Prefer a prototype of one new floor before a large layout. Growing a floor also shifts coordinate events/warps and consumes the buffered map area. More floors require the new-map procedure plus inter-floor warps, puzzle state, escape/blackout behavior, and town-map grouping. |
| Create a map | Allocate an ID deliberately; add dimensions, header, blocks, objects, script/text pointers, section includes, and entries in parallel map tables. Supply tileset/collision, songs, sprites, town-map association, and wild/toggle data or explicit empty coverage. |
| Connect it to Kanto | Add reciprocal connection strips/offsets for a seamless boundary or paired destination warp numbers for doors/stairs. Check spawn coordinates from both directions, `wLastMap`, Fly/Dig/Escape Rope/blackout rules, and all relevant story states. |

Limits are concrete: `MAX_WARP_EVENTS=32`, `MAX_BG_EVENTS=16`, and
`MAX_OBJECT_EVENTS=16` in `constants/map_data_constants.asm`. Map macros assert
counts and object/sign text-ID partitioning. The `trainer` macro also requires
defeat event-bit alignment with trainer/object order; flags cannot be reassigned
arbitrarily. `wOverworldMap` is a 1,300-byte buffer (`ram/wram.asm`) with a
three-block connection border; larger geometry must be checked against actual
load/copy routines, not just the `.blk` file size. `NUM_MAPS` currently ends at
`$f8`; IDs are bytes and `$ff` is reserved. Spare/unused IDs require full table
audits, and inserting IDs shifts many tables and saved map references.
Tilesets are shared, so editing a block or collision list can affect many maps.
Tileset banks are exceptionally tight (section 1); ordinary map banks also share
space with engines. A new map is not just an extra file.

## 8. Progression and flags

`ram/wram.asm` has `wObtainedBadges`, redundant `wBeatGymFlags`,
`wEventFlags`, `wStatusFlags1-7`, visibility state, and map-specific script-state
bytes. `constants/event_constants.asm` defines event bit IDs;
`macros/scripts/events.asm` and `engine/flag_action.asm` provide operations.
Story state is distributed across these fields and script branches rather than
a central progression graph. Saved main data includes progression state.

Concrete gate/reward anchors:

- `scripts/PewterGym.asm` sets Brock defeat/reward flags and both badge arrays;
  other Gym scripts follow related patterns. `scripts/PewterCity.asm` uses
  Brock's defeat event for the eastward escort/gate.
- `scripts/OaksLab.asm`, `scripts/ViridianCity.asm`/`ViridianMart.asm`, and
  `scripts/BillsHouse.asm` cover opening/Pokédex/parcel/Bill dependencies.
- `scripts/Route5Gate.asm`, `Route6Gate.asm`, `Route7Gate.asm`, and
  `Route8Gate.asm` check/set `BIT_GAVE_SAFFRON_GUARDS_DRINK`;
  `engine/events/saffron_guards.asm` removes a drink from
  `data/items/guard_drink_items.asm`.
  `scripts/SilphCo11F.asm` and toggleable objects implement liberation/visibility
  changes affecting Saffron access. Snorlax uses flute/event conditions;
  Mansion switches/Secret Key and Safari rewards are further independent gates.
- `scripts/ViridianCity.asm` opens the Gym when badge bits equal all seven
  non-Earth badges and sets `EVENT_VIRIDIAN_GYM_OPEN`.
- `scripts/Route22Gate.asm` checks Boulder Badge; `scripts/Route23.asm` checks
  the remaining individual badges and stores passed-check flags. Victory Road
  puzzles and HM traversal add geometry/event prerequisites. League room scripts
  (`LoreleisRoom` through `ChampionsRoom`/`HallOfFame`) run sequential battles
  and doors/state transitions.

Field-move gating is in `engine/menus/start_sub_menus.asm`: Cut requires
Cascade, Fly Thunder, Surf Soul, Strength Rainbow, Flash Boulder. Acquisition
is independent: SS Anne captain, Route 16 house, Safari secret house, Warden,
and Route 2 gate scripts supply HMs. Terrain and map-specific permissions add
further restrictions.

Badges also affect `ApplyBadgeStatBoosts`, obedience (`CheckForDisobedience`),
and displays in `engine/battle/core.asm`/menus. Partially flexible Gym order
therefore requires an explicit dependency audit of Gym reward/defeat flags,
field permissions, physical obstacles, story visibility, Viridian/League gates,
obedience/stat boosts, and save/reentry states. Dynamic team scaling, if desired
later, additionally needs trainer identity/selection extensions; the existing
reader does not scale by badge count. Prototype reachable and irreversible
states before committing new map layouts or trainer difficulty curves.

## 9. Items, machines, shops, and money

`constants/item_constants.asm` defines item and machine IDs.
`data/items/names.asm`, `prices.asm`, `tm_prices.asm`, `key_items.asm`,
`use_party.asm`, and `use_overworld.asm` supply names, prices, classifications,
and menu eligibility. `home/item.asm`/`home/item_price.asm` dispatch lookup;
`engine/items/item_effects.asm` (`UseItem_`, `ItemUsePtrTable`) dispatches effects.
Names/IDs/effect pointers/eligibility must stay aligned for a new item.

`data/items/marts.asm` contains `script_mart` inventory text scripts;
`engine/events/pokemart.asm` handles buy/sell menus and transactions.
Vending prices are in `data/items/vending_prices.asm`; gifts, floor pickups,
Gym TMs, Game Corner prizes (`data/events/prizes.asm`), and fossil/trade rewards
are additional economy sources. Shop changes alone do not redistribute them.

`data/moves/tmhm_moves.asm` maps 50 TMs and five HMs to moves;
`data/moves/hm_moves.asm` supplies the HM move list and machine-use constraints.
`ItemUseTMHM` checks compatibility and installs moves; TMs are consumed,
HMs are reusable. Machine compatibility lives in each base record (section 2).
Item IDs/machine indexing and special name/price handling should be audited
before adding machine slots.

Effect anchors in `item_effects.asm` include:

- `ItemUseEvoStone`: selects a party mon and calls evolution with item/forced
  evolution state; current stones already share one handler.
- `ItemUseMedicine`: healing, cures, revival, vitamins/Rare Candy branches and
  party/battle state synchronization.
- `ItemUseXStat`, `ItemUseXAccuracy`, `ItemUseGuardSpec`, `ItemUseDireHit`:
  battle flags/stat effects; trainer item AI has its own use paths.
- `ItemUsePPRestore`, `ItemUsePPUp`, `GetMaxPP`, `RestoreBonusPP`, `AddBonusPP`:
  Ether/Max Ether and Elixir/Max Elixir selection/all-move restoration, including
  packed PP Up bits and maximum PP calculation.
- Key items: some active handlers (flute, Card Key, bicycle, rods), others
  checked by scripts (tickets/keys/parcel). Toss restrictions use `IsKeyItem_`.

`wPlayerMoney` is three-byte BCD, not binary. `home/money.asm`,
`engine/math/bcd.asm`, `engine/items/subtract_paid_money.asm`, reward code,
and mart code handle arithmetic/display. `ResetStatusAndHalveMoneyOnBlackout`
in `engine/events/black_out.asm` halves it and resets travel/battle state;
core `HandlePlayerBlackOut` leads into loss handling. Coins have separate
storage and prize handling. Resource-routing work is mostly inventories,
prices, reward scripts, and encounter/catch data until it changes consumption,
loss rules, or inventory/storage formats.

## 10. Evolutions and single-player trade evolution options

`constants/pokemon_data_constants.asm` defines `EVOLVE_LEVEL`, `EVOLVE_ITEM`,
and `EVOLVE_TRADE`. `data/pokemon/evos_moves.asm` encodes:

| Method | Record after method byte | Consumer condition |
| --- | --- | --- |
| Level | required level, target internal species | Battle evolution eligibility and level check |
| Item | item ID, minimum level, target internal species | Item/forced evolution path and matching `wCurItem` |
| Trade | minimum level, target internal species | `wLinkState == LINK_STATE_TRADING` |

`EvolutionAfterBattle`/`TryEvolvingMon` in `engine/pokemon/evos_moves.asm`
walk eligibility flags and records, launch `EvolveMon` in
`engine/movie/evolution.asm`, then update species, stats, names, dex state,
and learning. Trading has its own entry/state through `engine/movie/trade*.asm`.
Extending record shapes requires updating both method-aware traversal and the
zero-scanning learnset readers (section 2). The stone party menu in
`engine/menus/party_menu.asm` copies records into `wEvoDataBuffer`, sized for
`NUM_EVOS_IN_BUFFER=3` four-byte records plus terminator; adding more branches
requires auditing this menu buffer too.

Replacing an existing trade record with a level record or an existing stone
item record fits current methods and is primarily data work, plus routing,
learnset, cancellation, and save tests. A new item that uses `EVOLVE_ITEM`
can reuse the engine method, but needs item ID/name/price/classification/effect
dispatch and acquisition data. A genuinely new trigger/method needs constants,
dispatch, record-skipping, eligibility/call-site changes, and tests.
An NPC service would need scripts and a safe evolution entry path; writing a
target species byte alone would bypass necessary updates.

The source explicitly documents a wild-encounter/stone evolution bug caused by
`wCurItem` aliasing species state. Test this boundary before extending item
evolution. No replacement method is chosen by WP003.

## 11. Text, menus, and speedrun ergonomics

`home/text.asm` (`PlaceString` and text command interpretation),
`home/print_text.asm` (`PrintLetterDelay`), `home/text_script.asm`,
`home/textbox.asm`, and `macros/scripts/text.asm` form the text path.
`wOptions`, `wLetterPrintingDelayFlags`, and `BIT_NO_TEXT_DELAY` control delay;
`DisplayOptionMenu`/`InitOptions` in `engine/menus/main_menu.asm` expose speed,
animation, and battle-style options. Text speed does not remove explicit
`DelayFrames`, input waits, sound waits, animations, or script movements.

Menu handling spans `home/window.asm`, `home/list_menu.asm`, `home/start_menu.asm`,
`home/pokemon.asm`, and `engine/menus/`; fades, tile transfers, input polling,
sprite reloads, and cursor state accompany transitions. Altering polling or
frame waits can affect input behavior and RNG timing (section 12).

Startup/title/intro are in `home/init.asm`, `engine/movie/splash.asm`,
`title*.asm`, `intro.asm`; new-game flow runs through `MainMenu` and
`engine/movie/oak_speech/*`. Opening scripted scenes are in
`scripts/PalletTown.asm`/`OaksLab.asm`; the old man catching demonstration also
uses battle-core special handling. Other sequences include Bill, SS Anne,
fossil restoration, evolution, trade, Hall of Fame, and credits. These sequences
often initialize flags or synchronize maps as well as show text.

`engine/joypad.asm` detects A+B+Start+Select and runs `TrySoftReset`;
`home/init.asm` contains reset initialization. Do not equate soft reset with
loading an arbitrary practice state. `engine/menus/save.asm` (`SaveGameData`,
`SaveMainData`, `LoadMainData`, box/party save paths, `CalcCheckSum`) and
`ram/sram.asm` define checksummed SRAM blocks. Changing persistent RAM layouts
can require save migration or explicit incompatibility.

Future practice hooks can build on existing debug new-game/battle entry points,
but must initialize coherent party, moves/PP, inventory, badges/events,
visibility, map script states, coordinates, options, and travel/blackout data.
Practice state selection, intro shortcuts, and reset/save semantics should be
prototyped early and isolated by an explicit build definition. Existing debug
mode is not a complete project practice build.

## 12. RNG and consistency

`ram/hram.asm` stores `hRandomAdd` and `hRandomSub`.
`home/random.asm` (`Random`) calls `Random_` in `engine/math/random.asm`, which
mixes reads of the hardware divider `rDIV` into the two bytes using ADC/SBC;
`Random` returns `hRandomAdd`. `home/vblank.asm` calls `Random` every VBlank.
Timing and incoming arithmetic carry state matter; this is not a seed-only
PRNG whose outputs are independent of execution timing.

Core `BattleRandom` normally jumps to `Random`, but link battles use
`wLinkBattleRandomNumberList`/index for synchronized values. Battle consumers
include move selection, speed ties, hit/critical tests, damage randomization,
status checks, multi-turn durations, DVs, and escape tests. Trainer item AI
calls `Random` directly. `TryDoWildEncounter` reads `hRandomAdd` for occurrence
and `hRandomSub` for slot selection instead of requesting fresh values there.
Fishing, catch logic, encounter initialization, and party generation are other
consumers (`item_effects.asm`, core, `add_mon.asm`).

Changing text/menu timing, adding AI calls, changing branch/call counts, or
skipping scenes can change battle/encounter outcomes even without editing RNG.
For reproducible tests record build hash, emulator/version, start state, input
frames, and RNG bytes/divider observations. Deterministic practice initialization
and manipulation stability require experiments under defined timing; no seed
API or reproducibility guarantee is established by this inspection.

## 13. Debugging and validation support

The Makefile has `blue_debug`; `_DEBUG` enables `DebugMenu` in
`engine/debug/debug_menu.asm` with FIGHT and DEBUG entries, `TestBattle`,
`StartNewGameDebug`, and `PrepareNewGameDebug`/`SetDebugNewGameParty` in
`engine/debug/debug_party.asm`. Debug initialization provides powerful party,
badges, and travel access. Source comments warn that `TestBattle` does not
initialize bag data correctly, so it is not automatically a trustworthy
resource/economy fixture. Core/overworld debug flag checks add shortcuts;
audit all `_DEBUG` and `BIT_DEBUG_MODE` references before reusing them.

Assembly assertions validate table widths/counts (`macros/asserts.asm`),
move PP, species tables, map object/warp/sign limits and text IDs, trainer
flag alignment, map-ID namespace, and toolchain version. The linker rejects
placement/bank overflow. These are structural checks, not gameplay regression
tests. `tools/scan_includes` maintains dependencies; graphics compression tools
also participate in builds.

`.github/workflows/` builds on Linux and macOS with RGBDS 1.0.4. Upstream `pret`
uses `make compare`; this fork's CI builds normal targets and runs
`.github/checkdiff.sh`. The latter checks tracked cleanliness, not correctness.
Its triggers are master pushes and pull requests, so merely pushing this
package branch does not establish CI success. Vanilla `roms.sha1` is already
inapplicable to the intentional WP002 marker; do not change reference hashes
to accommodate the hack.

Practical future validation: build all variants, inspect bank/RAM usage, load
fresh ROMs, use symbols to break at the relevant entry/effect routine, watch
mirrored battle/party state, and test save/reload and map reentry. For mechanics,
use controlled cases for exact HP/stages/status/move/turn interactions on both
sides. For progression, walk alternative gate orders and test leaving/reentering,
blackout, and loading during script states. For new maps, inspect boundaries,
collision, arrival points, shared tileset changes, and hidden events.

Gaps: no project-specific automated mechanics/progression suite, no dedicated
data-schema linter beyond assembler checks, no measured regression budget for
bank/RAM growth, and no established deterministic emulator harness. A future
tooling package should prototype reproducible battle fixtures, state snapshots,
table audits, and a per-bank report before widespread engine/content edits.

## Engineering risk assessment

Risk here means implementation complexity and coupling, not design desirability.

| Future area | Approximate risk | Why / prerequisite |
| --- | --- | --- |
| Trainer species/levels | Low, data-driven | Existing formats, six-mon limit; party index references, generated moves, payout coupling |
| Full custom boss movesets | Moderate engine work | New representation/reader and safe skipping/PP initialization; prototype first |
| Wild redistribution | Low within existing tables | Shared/version/fishing/static sources and terrain/Repel assumptions; new methods increase risk |
| Pokémon stat/type rebalance | Low edit risk, moderate interaction risk | Crits, Special, category split, growth/catch/EXP, stored save data |
| TM/shop/reward redistribution | Low to moderate | Many acquisition sites; compatibility bits and machine identity shared globally |
| Trade evolution replacement | Low for existing methods; moderate for new item/service | Existing data format versus new dispatch/call path; evolution aliasing bug |
| AI overhaul | High/foundational | Turn contract, scratch state, policy identity, RNG, switching/items, bank `0e`/RAM constraints |
| Partially flexible Gym order | High/foundational | Distributed gates/flags, HM access, badge effects, geometry and persistent state |
| New map using existing tileset | Moderate | Parallel ID tables, pointers/banks, warp/link correctness, buffer/ID limits |
| Expanded dungeon | Moderate to high | Geometry buffers, puzzle flags, reentry/escape, more maps and bank pressure |
| New tilesets | High space/graphics risk | Nearly full/full banks, shared block/collision usage |
| New boss systems/scaling/phases | High/foundational | Team/AI identity, battle transition/state/save assumptions; requirements not chosen |
| Mechanics bug fixes | Moderate to high | Shared helpers plus mirrored paths, ordering and multiple move interactions |
| Practice build | Moderate to high | Complete state initialization, save/reset isolation and timing/RNG validity |
| ROM expansion/bank restructuring | High/foundational if needed | Near pointers, literal banks, predefs/far calls, assets and RAM/save layout; aggregate room alone is insufficient |

## Recommended implementation sequence

1. **Establish reproducible validation and storage budgets.** Capture per-bank
   and RAM baselines, agree emulator/test-start conventions, and prototype one
   controlled battle fixture and one map/progression fixture. Decide save
   compatibility and supported variants. Use existing debug features only after
   checking initialization. This supports every later package.
2. **Prototype representation and placement foundations.** Prove full trainer
   movesets/PP and per-boss identity while retaining an ordinary trainer path.
   Establish where policy/state can live with only 30 WRAM bytes free. If those
   prototypes exceed `0e`/ROM0 budgets, perform a focused relocation audit and
   move bank-safe units before committing large tables. Do not expand the ROM
   solely because a locally assigned bank is full.
3. **Settle and test mechanics decisions.** Specify intended behavior for crits,
   Focus Energy, Substitute, Hyper Beam, trapping, accuracy, stages/status,
   and X-items. Implement adopted changes in separately reviewable slices with
   regression fixtures. Damage semantics should stabilize before AI prediction
   or large team balance work. Recheck `0f` and helper-bank space after each slice.
4. **Prototype AI and practice state entry.** Demonstrate one boss policy, item
   budget, switching, legal actions, tie rules, and ordinary-trainer behavior.
   Practice setup can proceed alongside fixtures, but timing-sensitive hooks
   need tests after mechanics/AI settle. Recheck `01`, `0e`, ROM0, RAM, and saves.
5. **Prototype progression and map feasibility before content investment.**
   Audit the gate graph and show representative alternate Gym orders, HM
   traversal, Viridian/League access, save/load and blackout. Independently prove
   one additional dungeon floor/map, ID registration, reciprocal transitions,
   buffer capacity, and tileset choice. These prototypes constrain routing and
   boss-selection/scaling needs. Recheck affected map and graphics banks.
6. **Integrate content against stable contracts.** Species stats/learnsets,
   encounter distribution, trainer teams, single-player evolution choices,
   TMs, shops, rewards, and economy are mostly data work and can wait. Coordinate
   them as one resource/progression dependency set; trainer defaults depend on
   learnsets, economy depends on encounter/catch rates and party levels, and HM
   availability depends on both rewards and permissions. Validate incremental
   regional batches before filling all Kanto.
7. **Finish ergonomics and whole-run regression.** Once state transitions are
   stable, refine dialogue/menu/scene delays and practice workflows, then rerun
   input/RNG timing tests and complete-route/save tests. Check all variants and
   final bank/RAM headroom; retain measured capacity for further iteration.

Foundations may overlap, but mechanics precede predictive AI, team formats
precede custom teams, progression/map prototypes precede route/dungeon content,
and save/state policy precedes persistent boss/practice systems. Bank pressure
is a checkpoint throughout, not a final cleanup task.

## Open questions and experiments still needed

- The survey traces representative routines, not every special-case script.
  A full gate graph and all visibility/script-state dependencies still need a
  systematic audit, especially alternate-order Saffron, SS Anne, Safari,
  Viridian, and League paths. No alternate Gym order is validated here.
- Runtime mechanics claims are source-derived. Exact interactions at HP equality,
  integer overflow, KO/substitute breaks, status interrupts, Counter, switching,
  and badge recalculation need emulator fixtures before any chosen correction.
- The intended boss system and allowed AI knowledge are undecided. Whether it
  needs per-fight state, phases, scaling, or new classes must be established by
  prototypes rather than assumed in a large team migration.
- Maximum safe map dimensions require actual buffer/copy-path experiments with
  connection borders. The 1,300-byte allocation is evidence of a limit, not a
  validated universal width/height formula. Reusing unused IDs also needs audits
  of grouping/range comparisons and persistence.
- Bank relocation feasibility is not proven by free totals. Near-pointer tables,
  same-bank graphics assumptions, literal bank IDs, and predef conventions must
  be checked for each proposed move. No new bank layout is selected.
- RAM overlay lifetimes and saved main-data boundaries need a dedicated audit
  before reserving boss/practice state. Existing SRAM room does not prove
  compatibility with old saves or box checksums.
- Evolution replacements need cancellation, PP/learnset, stone aliasing,
  trade/link exclusion, and save tests. A new method must update all parsers.
- Speedrun manipulation consistency is unmeasured. Text timing, hardware divider,
  VBlank, carry state, and emulator timing prevent a seed-only conclusion.
- Existing debug tooling is useful but incomplete; no automated emulator or
  practice-build architecture has been selected. WP003 builds passed, but did
  not playtest debug mode or any later design proposal.
