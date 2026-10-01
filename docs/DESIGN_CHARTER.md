# Project Design Charter

## Authority and decision status

This charter is the design authority for future work packages in
`wchatgpt2026/pokemon-red-speedrun`, a fork of `pret/pokered`.
WP001 establishes design intent only; it changes no game behavior.
The pristine baseline is commit `d2704a63c26f9ba046ade877445216b3de0519a4`,
tagged `baseline-pokered`, with `make compare` previously verified successfully.

- **Locked principles** are constraints for subsequent design and implementation.
- **Current direction** is the preferred approach, subject to evidence from testing.
- **Open questions** require later evaluation; inclusion here does not settle them.

## 1. Core objective and audience

**Locked principles.** Build an expanded, difficult Pokémon Red ROM hack for
experienced Pokémon players and serious speedrunners. Preserve the full Kanto
journey and eight-badge → Elite Four backbone. The game must remain full-length
or become longer than vanilla Red; it is not a compressed speedrun minigame.
Expansion is encouraged when it improves gameplay.

Speedrunning is a first-class concern, alongside a satisfying standalone
challenge. The result must feel unmistakably like Gen I Pokémon, retaining Red's
identity and overall structure while substantially increasing strategic depth,
routing complexity, difficulty, and eventually world and content scope.

A strong blind player should be able to progress and eventually finish without
external documentation. Experts should gain substantial advantages from studying
teams, mechanics, routes, item locations, damage ranges, and AI rules.

## 2. Difficulty quality

**Locked principles.** Difficulty should primarily test route planning, team
construction, battle execution, resource management, optional-versus-mandatory
content decisions, and risk/reward choices. Stronger trainer teams, better AI,
and meaningful encounter design should support those tests.

Avoid difficulty primarily driven by large level inflation, mandatory grinding,
hidden boss cheats, arbitrary surprise immunities, or repeated low-probability
RNG fishing.

> If the optimal solution to a difficult section is simply grinding random
> encounters for a long time, the design probably needs improvement.

## 3. Speedrun routing

**Locked principles.** The main optimization problem is speed under meaningful
constraints. Support aggressive risky routes, safer slower routes, and optional
detours with real time/value tradeoffs. Experience, resources, encounters,
captures, starters, and team composition must all offer meaningful routing choices.

A top route should not simply consist of one obvious Pokémon sweeping the entire
game. Encourage multiple plausible strategies even if one ultimately becomes
fastest; equal completion times are not required.

## 4. World and progression

**Locked principles.** Keep Kanto as the main setting, eight badges as the
progression backbone, and the Elite Four as the main-game endpoint. Do not
compress the world. Initial expansion should focus on Kanto rather than a second
complete region. Significant new areas must create a routing choice, test the
player, or materially improve progression; new content must not be filler.

Gym order should be partially flexible rather than completely linear or
completely open.

**Current direction.** Constrain early progression relatively closely, permit
meaningful midgame order flexibility, and reconverge late progression before
Giovanni and the Elite Four. Potential expansion includes existing dungeons,
new Kanto sub-areas, route branches, more meaningful Team Rocket content,
additional mandatory bosses, and optional high-value challenge areas.

**Open questions.** Exact gates, gym dependencies, added bosses, and expansion
locations require routing and progression tests before becoming commitments.

## 5. Trainers and bosses

**Locked principles.** Use four encounter tiers:

1. Standard trainers.
2. Elite trainers, officers, and gatekeepers.
3. Major bosses.
4. Endgame bosses and superbosses.

Regular trainers should be stronger and more coherent than vanilla without
making every route exhausting. Major bosses should have deliberately constructed
teams, better movesets, stronger AI, meaningful coverage, and limited purposeful
item use. Team size and complexity should increase over the journey; early
bosses do not all need six Pokémon.

Gym Leaders must retain recognizable themes, but strict monotype purity is not
required. Boss identity may also emphasize speed control, status, setup, bulk,
offensive pressure, or resource attrition. Bosses must not rely on invisible stat
multipliers or arbitrary hidden advantages unless explicitly communicated as a
game mechanic.

**Open questions.** Specific teams, coverage, item allowances, and challenge
density need battle and route testing.

## 6. AI

**Locked principles.** Substantially improve major trainer AI over vanilla while
keeping its behavior understandable and sufficiently deterministic for serious
speedrunning.

> The AI should make sensible decisions, and skilled runners should be able to
> learn the rules governing those decisions.

Avoid completely random "smart" behavior that unnecessarily destabilizes
optimized routes. Exact decision rules remain open for implementation and testing.

## 7. Roster and encounters

**Locked principles.** Initial scope is Gen I only: all 151 species, with no
later-generation Pokémon. Aim to make essentially all 151 obtainable in one
save, remove version-exclusive limitations, and enable trade evolutions in
single-player.

Redistribute encounters aggressively where useful, give different Pokémon
distinct strategic roles, and improve selected weak or unusable species where
justified. Preserve meaningful asymmetry; do not try to make every Pokémon equal.
All starters should support plausible serious routes while retaining distinct
identities. Legendaries remain optional and powerful, with enough acquisition
time and difficulty to make them genuine routing decisions.

**Open questions.** Encounter tables, individual buffs, legendary access, and the
trade-evolution mechanism require testing. Trade evolution should ideally involve
a routing or resource decision.

## 8. Gen I mechanics policy

**Locked principles.** Preserve Gen I identity by default. Generally retain the
combined Special stat, Gen I type system, Speed-influenced critical hits, stat
experience, recognizable battle behavior, and the original battle-system
character. Do not modernize mechanics wholesale. Keep interesting quirks unless
they damage strategic depth or competitive consistency.

Major progression-breaking glitches must not be intended parts of the primary
speedrun route. This includes arbitrary code execution, item duplication,
Trainer-Fly/Mew-style bypasses, save corruption, and equivalent sequence
destruction.

**Current direction.** Likely fix or redesign the 1/256 accuracy failure, Focus
Energy malfunction, obviously broken trainer AI, progression-breaking glitches,
and degenerate trapping behavior if it trivializes encounters.

**Open questions.** Evaluate individually the badge-boost glitch, sleep, freeze,
critical-hit/stat-boost interactions, Hyper Beam behavior, Substitute quirks,
Dig/Fly edge cases, and other notable Gen I quirks. Neither blanket preservation
nor automatic removal is the policy; specific outcomes remain unsettled.

## 9. Items, TMs, and economy

**Locked principles.** Resource planning must matter. Strong resources should
save time while creating opportunity cost. Use meaningful TM scarcity and
strategic placement, money pressure, healing decisions, X-item routing,
evolution-resource decisions, and PP management.

X-items should remain powerful speedrun tools without becoming effectively
unlimited immediately. Portable healing should matter without creating attrition
misery. Pokémon Centers remain freely usable. Key-item friction without a
meaningful strategic purpose may be streamlined.

**Current direction.** TMs generally remain single-use unless future testing
strongly supports a change.

**Open questions.** Prices, supplies, placements, evolution costs, and resource
availability need economy and route testing.

## 10. RNG

**Locked principles.** Meaningful randomness remains part of Pokémon: retain
damage ranges, critical hits, encounter variance, accuracy, status, and other
meaningful RNG. Avoid designing optimal play around repeated absurdly
low-probability events.

RNG manipulation may remain possible and reward expert knowledge, but extreme
RNG abuse must not be the only competitive strategy. Test both ordinary play and
expert routing for reasonable consistency.

## 11. Speedrun ergonomics and practice

**Locked principles.** Preserve game length while reducing meaningless dead time.
Practice tools must not affect ranked competitive builds.

> A serious runner should be able to practice major segments efficiently without
> replaying hours of prior content.

**Current direction.** Future goals include fast text, reduced unnecessary
dialogue delay, faster menus and transitions where appropriate, low reset
friction, no mandatory beginner tutorials, and practice-friendly architecture.
The hack may eventually have a standard/race build and a separate practice build.
Possible practice tools include boss warps, state presets, level/item presets,
encounter tools, and RNG diagnostics.

**Open questions.** Build separation, practice tooling, and exact timing changes
are future work, not features implemented or promised by WP001.

## 12. Failure and recovery

**Locked principles.** Normal play retains Pokémon-style saving and progression.
Wipes should punish failure through lost time and battle consequences without
excessive repetitive backtracking. Avoid long mandatory sequences before difficult
bosses. Do not impose ironman rules in the standard game.

**Open questions.** Blackout money loss may be retained, reduced, or removed
depending on economy testing.

## 13. Initial scope boundaries

**Locked principles.** Near-term scope is the Pokémon Red/Gen I engine, Kanto,
151 Pokémon, eight-badge progression, and an Elite Four main-game endpoint,
with significant future gameplay redesign and Kanto expansion.

Initially exclude a second complete region, later-generation Pokémon, wholesale
conversion to later-generation battle mechanics, enormous custom item systems,
and a major story rewrite before core gameplay is proven.

WP001 is documentation-only. It authorizes no source, map, trainer, encounter,
mechanic, graphic, build-behavior, ROM-data, or generated-ROM changes. Subsequent
implementation belongs to separately scoped work packages.

## 14. Decision Rule for Future Changes

Judge proposed mechanics and content primarily by whether they improve strategic
depth, difficulty quality, speedrun routing, competitive consistency, and Gen I
identity. Explain tradeoffs across these criteria rather than optimizing one at
the expense of the others without justification.

Proposals must respect locked principles and initial scope. For current directions
and open questions, document the intended benefit, then test blind progression,
resource costs, route alternatives, and battle reliability as relevant. Record
the resulting decision and evidence before treating an unresolved choice as
settled. A deliberate revision of a locked principle must explicitly update this
charter; it must not occur implicitly through implementation.
