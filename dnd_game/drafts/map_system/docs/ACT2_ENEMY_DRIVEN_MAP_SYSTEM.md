# Act 2 Enemy-Driven Map System Draft

## Purpose

This draft extends the Act 1 hybrid map idea into a more complex Act 2 structure and now feeds the current playable scaffold.

Act 1 is mostly a hub-and-branch adventure with short local maps. Act 2 should feel more like an expedition theater:

- the player returns to Iron Hollow as an operational hub
- early routes can be completed in different orders
- delaying a route leaves permanent consequences
- enemy factions change what each map means
- late routes are both required, but order changes stakes
- the final Resonant Vaults chain becomes a deeper, multi-objective dungeon sequence

The companion blueprint lives in:

- `dnd_game/drafts/map_system/data/act2_enemy_map.py`
- preview command: `python -m dnd_game.drafts.map_system.examples.act2_preview`

## Current implementation snapshot

The live code now covers most of this route shape:

- richer requirement support is wired into the draft/runtime layer and consumed by the playable Act 2 map state
- the Act 2 hub can render route availability and local site previews through the in-game `map` command
- `Stonehollow Dig`, `Broken Prospect`, `South Adit`, `Resonant Vault Outer Galleries`, `Blackglass Causeway`, and the `Meridian Forge` all exist as playable local maps
- Act II pressure, rescue, clue, and late-route consequences now surface through map status panels, journal snapshots, and the camp digest
- the Act II completion scene now records Forge-specific Act 3 handoff flags for route state, cleared subroutes, and resonance-lens state

## Enemy-First Design

Act 2 should be mapped around enemy pressure packages rather than around location names alone.

| Enemy package | Enemies | Map function |
| --- | --- | --- |
| `claim_war` | `expedition_reaver`, `cult_lookout`, `gutter_zealot` | turns the public claims war into route sabotage and false map control |
| `cave_predators` | `grimlock_tunneler`, `stirge_swarm`, `ochre_slime`, `acidmaw_burrower`, `carrion_lash_crawler`, `hookclaw_burrower` | makes the mine ecology hostile before the cult is fully visible |
| `pact_haunting` | `animated_armor`, `spectral_foreman`, `graveblade_wight`, `iron_prayer_horror` | shows the old Meridian Compact defending itself badly or under corrupted orders |
| `quiet_choir` | `cult_lookout`, `choir_adept`, `starblighted_miner`, `choir_executioner`, `obelisk_eye`, `caldra_voss` | turns Act 2 from claim dispute into cosmic listening-horror |
| `black_lake` | `animated_armor`, `starblighted_miner`, `blacklake_pincerling`, `spectral_foreman`, `obelisk_eye` | makes the final threshold a tactical and spiritual crossing |

## Route Shape

The Act 2 overworld is not a simple line. It has three early leads, a forced midpoint, two late branches that affect each other, and a final dungeon chain.

```text
                     [CLAIMS COUNCIL]
                            |
                     [IRON HOLLOW]
             /              |              \
 [PALE CIRCUIT]   [GREYWAKE CAMP]    [STONEHOLLOW]
             \              |              /
                      [SABOTAGE NIGHT]
                    /                  \
             [BROKEN PROSPECT]     [SOUTH ADIT]
                    \                  /
              [RESONANT VAULT GALLERIES]
                            |
                     [BLACKGLASS]
                            |
                   [MERIDIAN FORGE]
                            |
                      [ACT II END]
```

## Local Map Philosophy

Act 2 local maps should usually have five to seven rooms, not the four-room pattern used by many Act 1 sites.

Every local map should include at least two of these:

- one mandatory enemy room
- one optional objective room
- one rescue, clue, or pressure-control room
- one boss or convergence room
- one room that changes if the site was delayed

This keeps the text-based map readable while making Act 2 feel wider and more reactive.

## Draft Site Breakdown

| Site | Enemy basis | Complexity upgrade |
| --- | --- | --- |
| `The Pale Circuit` | Quiet Choir defilement, undead omen pressure | social boss room; truth quality depends on whether side branches are resolved |
| `Greywake Survey Saboteur Camp` | rival reavers plus Choir lookouts | ranged roost, spoiled stores, proof cache, and fallback trail |
| `Stonehollow Dig Site` | slimes, grimlocks, collapse predators | rescue and route-truth branches; Nim hook; delayed version can add foreman or hookclaw pressure |
| `Iron Hollow Sabotage Night` | Choir lookout plus adept strike cell | three-front town crisis where the player cannot protect everything first |
| `Broken Prospect Threshold` | Meridian Compact armor, spectral foreman, rival scouts | haunted route-control dungeon; stronger if taken after South Adit |
| `South Adit Prison Line` | starblighted miners and Choir wardens | captive survival map; Irielle hook; stronger if taken after Broken Prospect |
| `Resonant Vault Outer Galleries` | cave predator ecology | bigger five-column map with side runs, slime lanes, false echoes, and a final haul gate |
| `Blackglass Causeway` | constructs, starblight, lake predators | three objective choices: shrine, barracks, or anchors |
| `Meridian Forge Resonance Lens` | Caldra, adepts, obelisk pressure | final boss map where side objectives modify the boss fight |

## Feasible Implementation Steps

1. Data-only draft
   - Add the Act 2 blueprint and design doc without wiring it into the playable game.
   - Use existing `HybridMapBlueprint`, `TravelNode`, `DungeonMap`, and `DungeonRoom` models.
   - This is the safest first step and is now represented by `act2_enemy_map.py`.

2. Add Act 2 map preview
   - Add a standalone preview script like the Act 1 preview.
   - Use a mid-to-late Act 2 state so the map demonstrates more complexity than the opening routes.

3. Generalize map-state naming
   - Rename Act 1-specific methods in `gameplay/map_system.py` behind neutral helpers.
   - Keep `current_scene` as the authority, but allow the active blueprint to be selected by `current_act`.

4. Add richer requirement support
   - Act 2 needs requirements that Act 1 did not need:
     - "any two of these three flags"
     - metric thresholds like `Whisper Pressure >= 4`
     - route-order conditions like `act2_first_late_route == "broken_prospect"`
   - Draft support now exists through `FlagCountRequirement`, `NumericFlagRequirement`, `FlagValueRequirement`, and `DraftMapState.flag_values`.
   - This keeps the map from needing awkward fake flags such as `act2_midpoint_unlocked`.

5. Wire the Act 2 hub to the blueprint
   - Keep the existing Act 2 scene flow intact.
   - Let the map render available routes next to the current hub options.
   - Feed real Act 2 flags and metric values into `DraftMapState` so the blueprint can unlock sabotage night from any two early leads directly.
  - Read-only route rendering now exists through the in-game `map` command; local site maps render against live Act 2 state when the current scene is inside a converted site.

6. Convert one site at a time
  - Start with `Stonehollow Dig`, because it has clear enemies, a companion hook, and a simple rescue outcome.
  - `Stonehollow Dig` is now the first playable Act 2 local map. It uses `act2_map_state`, room navigation, room-specific encounters/events, Nim recruitment, and the original route-control/whisper consequences.
  - Then convert `South Adit`, because it tests order consequences and companion recruitment.
  - `Broken Prospect`, `South Adit`, `Resonant Vault Outer Galleries`, `Blackglass Causeway`, and `Meridian Forge` are now also playable local maps, with the later sites carrying order-sensitive fallout into the finale.

7. Add enemy-pressure overlays
   - Instead of only showing room symbols, expose the enemy package:
     - `claim_war`
     - `cave_predators`
     - `pact_haunting`
     - `quiet_choir`
     - `black_lake`
  - Later, this can influence random encounters and room text.
  - The live game now also surfaces pressure through the Act II status panel and room text, even though the overlay model is still lighter than the full draft vision.

8. Save and test
  - Add Act 2 map state into saves beside the existing map payload.
  - Test travel availability, delayed lead consequences, late-route order, and final route unlocking.
  - Keep the preview script as a fast visual smoke test.
  - The live scaffold now also stores Forge-specific Act 3 handoff flags: `act3_forge_route_state`, `act3_forge_subroutes_cleared`, and `act3_forge_lens_state`.

## Integration Guardrails

- Do not rewrite the Act 2 scaffold all at once.
- Keep the existing scene methods as the story authority.
- Let the map system display, gate, and navigate. Let the scenes keep handling combat, companion recruitment, rewards, and pressure changes.
- Add richer requirement logic before trying to represent all Act 2 consequences in the map data.
- Treat enemy packages as a layer on top of room roles, not as a replacement for authored scene text.

## Best Next Decision

The next practical build step should be either:

1. make the Act 2 blueprint render from the in-game `map` command while staying read-only, or
2. add requirement support for "any two of three flags" and metric thresholds, then wire `Stonehollow Dig` as the first playable Act 2 local map.
