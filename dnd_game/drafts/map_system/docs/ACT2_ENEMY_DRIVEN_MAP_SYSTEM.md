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
             /              |              \              \
 [PALE CIRCUIT]   [GREYWAKE CAMP]    [STONEHOLLOW]    [GLASSWATER]
             \              |              /                 |
                      [SABOTAGE NIGHT]
                                                        [SILTLOCK]
                    /                  \
             [BROKEN PROSPECT]     [SOUTH ADIT]
                    \                  /
              [RESONANT VAULT GALLERIES]
                            |
                     [BLACKGLASS]
                         /     \
             [RELAY HOUSE]     |
                         \     |
                   [MERIDIAN FORGE]
                            |
                      [ACT II END]
```

## Expansion Slots

A new branch fits cleanly in three places.

1. Beside `Broken Prospect` and `South Adit`
   The hub already pauses for a hard commitment here. A third late route can carry route control, captive fallout, or cult intel and still feed the same Outer Galleries convergence.

2. Beside `Glasswater Intake`
   This slot opens after one early lead and stays out of the two-of-three sabotage math if it remains optional. It suits sponsor politics, supply trouble, or a companion-specific detour.

3. Between `Blackglass Causeway` and the `Meridian Forge`
   This is the smallest surgical addition. It works best as a short threshold objective that changes the forge fight or clarifies one piece of Choir doctrine.

This pass drafts the third slot as `Blackglass Relay House`: a far-side signal room where wet cables, counterweights, and old bell timing feed support pulses into the Meridian Forge.

This pass also drafts the second slot as `Siltlock Counting House`: an early paper dungeon where water permits, ration ledgers, and green valve wax expose who paid to make Glasswater's corruption look like ordinary civic failure.

## Siltlock Counting House Draft

Siltlock Counting House sits on a muddy lane behind the Ashlamp Inn, close enough to the water carts that every clerk smells faintly of wet rope. A painted sign promises FAIR CERTIFICATION FOR FAIR CLAIMS. The lower edge of the sign has been scraped by wagon hubs so many times that only the words FAIR CLAIMS remain clean.

Travelers think Siltlock certifies small claims, ferry permissions, and charity rations. The clerks use it as a paper sluice. Bad water becomes a maintenance delay. Missing food becomes a corrected ration table. A forged permit crosses the public counter with a bell tap, then vanishes into the back till before a miner can ask why the seal is still warm.

Branch purpose:

- Give Act 2 an early optional route about paperwork, supplies, and sponsor pressure.
- Let the player attack Glasswater from the civic side before entering the waterworks.
- Give sabotage night a prep hook through ration tags, watch bells, and supply ledgers.
- Make sponsor choice visible in a physical room: coin chits, crate seals, erased council signatures, and clerks choosing which truth gets filed.
- Add a low-cave, high-town branch so Act 2 breathes between wilderness leads and mine delves.

Opening condition:

- Opens after any one early lead: `agatha_truth_secured`, `woodland_survey_cleared`, or `stonehollow_dig_cleared`.
- Stays optional through sabotage night so the player can use it as early prevention or late damage control.
- Closes after `caldra_defeated` because the evidence belongs in Act 2's town-pressure economy.
- Suggested reveal flag: `siltlock_counting_house_known`.

Why it fits beside Glasswater:

- Glasswater is the physical waterworks problem.
- Siltlock is the paper trail that made the waterworks problem invisible.
- Glasswater asks who changed the flow.
- Siltlock asks who signed the flow change and which sponsor looked away.
- The two sites can be cleared in either order, with different tone.

Timing variants:

- Before Glasswater: Siltlock gives `glasswater_permit_fraud_exposed` and `glasswater_valve_wax_matched`, lowering DCs in the Glasswater relay office, ledger vault, or valve rooms.
- After Glasswater: Siltlock turns waterworks evidence into public leverage and can improve a council or sponsor confrontation.
- Before sabotage night: Siltlock gives `sabotage_supply_watch_warned`, improving town stability or weakening one sabotage-night front.
- After sabotage night: Siltlock explains which ration cache failed, names the clerk who redirected the watch bell, and gives recovery evidence rather than prevention.
- After two late routes: Siltlock should feel late, useful, and slightly sickening: the town already bled, but the burned receipt corners still name who sold the bandage.

Room shape:

- `Public Counter`: entrance; public-facing claims desk with mud on one side and clean boot scuffs behind the rail.
- `Permit Stacks`: event room; forged water permits and ferry tags expose Glasswater's paper cover.
- `Ration Cellar`: combat room; stolen charity stores and quiet reserve crates point toward sabotage prep.
- `Back Till Cage`: treasure or social-pressure room; sponsor chits, clipped coin, and green wax wafers name who benefited.
- `Valve Wax Archive`: event room; preserved seal samples match Glasswater valve wax and can become hard evidence.
- `Sluice Bell Alcove`: event room; a warning bell can be armed, exposed, or traced after sabotage night.
- `Auditor's Stair`: boss or social boss room; the auditor tries to spend evidence like coin before the party can seize it.

Pathing:

- `Public Counter` opens three routes: `Permit Stacks`, `Ration Cellar`, and `Back Till Cage`.
- `Permit Stacks` leads toward `Valve Wax Archive` and can also reach `Back Till Cage`.
- `Ration Cellar` leads toward `Sluice Bell Alcove` and can also reach `Back Till Cage`.
- `Back Till Cage` links the paper and supply halves of the branch.
- `Valve Wax Archive` and `Sluice Bell Alcove` both feed `Auditor's Stair`.
- `Auditor's Stair` clears the branch.

Room-by-room gameplay:

- `Public Counter`
  The party enters during business hours or just after a hurried closing. The counter bell rings below the floorboards instead of out front. Skills can read the clerk script, spot the hot seal press, or make a junior clerk panic. Clear flags: `siltlock_counter_seen`, `siltlock_counting_house_known`.

- `Permit Stacks`
  Damp water permits, ferry claims, and corrected survey slips sit in stacks tied with blue cord. The newest ink was dried over lamp soot. Investigation can connect false permits to Glasswater. Insight can identify which corrections were rehearsed. Persuasion can make a clerk admit which book never reaches the council table. Clear flags: `siltlock_permit_chain_read`, `glasswater_permit_fraud_exposed`.

- `Ration Cellar`
  The charity cellar holds flour, pickled turnip crocks, watch lantern oil, and reserve crate marks. Combat can use cramped shelves, spilling lamp oil, and a bell cord that keeps trying to summon help. Suggested enemies: `cult_lookout`, `expedition_reaver`, `claimbinder_notary`, `gutter_zealot`. Clear flag: `siltlock_ration_tags_recovered`.

- `Back Till Cage`
  A locked cage behind the public counter holds clipped coin, sponsor chits, and green wax wafers wrapped in cheesecloth. This room should react to `act2_sponsor`. Halia's pressure appears as ledger leverage. Lionshield pressure appears as guarded supply seals. Council pressure appears as erased signatures and minutes with a missing vote. Clear flags: `siltlock_bribe_float_found`, `act2_sponsor_pressure_named`.

- `Valve Wax Archive`
  Thin drawers preserve valve seals for audits that never happen. Several wafers carry the same green grit that stains Glasswater's relay-office ledgers. Arcana can read resonance contamination. Investigation can match the archive to Glasswater. Sleight of Hand can preserve a clean sample before the room's burner box destroys it. Clear flags: `siltlock_valve_wax_sampled`, `glasswater_valve_wax_matched`.

- `Sluice Bell Alcove`
  A small warning bell hangs behind the cellar, wired to a watch post and looped back into Siltlock through a gnawed mortar hole. Before sabotage night, the party can arm the bell and warn the watch. After sabotage night, the party can prove the bell was turned inward so Siltlock heard the danger and the street did not. Clear flags: `siltlock_sluice_bell_armed`, `sabotage_supply_watch_warned`.

- `Auditor's Stair`
  The auditor waits above the counter on a stair polished by worried hands. Burned receipt corners fill little trash cups on each landing. This can play as a boss fight, a coercion scene, or a social trap. The auditor's moves: burn a page, blame a sponsor, release the ration-cellar crew, offer a permit book, or ring the cellar bell. Clear flags: `siltlock_counting_house_cleared`, `siltlock_auditor_broken`.

Flag plan:

- `siltlock_counting_house_known`: the branch is known from hub evidence.
- `siltlock_counter_seen`: entry room cleared.
- `siltlock_permit_chain_read`: permit fraud is legible.
- `glasswater_permit_fraud_exposed`: Glasswater's civic cover is exposed.
- `siltlock_ration_tags_recovered`: stolen charity supplies are recovered or documented.
- `siltlock_bribe_float_found`: back-room money trail is found.
- `act2_sponsor_pressure_named`: the chosen sponsor gets tied to the branch's pressure economy.
- `siltlock_valve_wax_sampled`: physical wax evidence is preserved.
- `glasswater_valve_wax_matched`: Siltlock wax matches Glasswater valve tampering.
- `siltlock_sluice_bell_armed`: the warning bell is made useful.
- `sabotage_supply_watch_warned`: sabotage night gets a prevention or recovery hook.
- `siltlock_auditor_broken`: the branch boss loses control of the books.
- `siltlock_counting_house_cleared`: branch completion flag.

Payoff hooks:

- Glasswater Intake:
  `glasswater_permit_fraud_exposed` can reduce the Relay Office or Ledger Vault DC by 1. `glasswater_valve_wax_matched` can reduce Valve Hall or Pump Gallery DC by 1. If both are present, Brother Merik should lose one line of plausible deniability before combat or parley.

- Sabotage Night:
  `sabotage_supply_watch_warned` can protect a supply front, add a town-stability point, reduce the first enemy wave, or reveal the strike cell earlier. If the branch is cleared late, the same flag can become evidence for recovery rather than prevention.

- Sponsor pressure:
  `act2_sponsor_pressure_named` can create a sponsor-specific hub line. Halia wants the ledger intact. Lionshield wants the ration marks buried. The council wants the signatures described carefully. The player can use the same evidence as leverage or public proof.

- Act 3 handoff:
  If Siltlock is cleared and Glasswater is cleared, Act 3 can inherit a civic-infrastructure thread: permits, water, and emergency supplies have already been used as weapons once.

Outcome variants:

- Clean audit:
  The party clears Permit Stacks, Back Till Cage, and either evidence wing before Auditor's Stair. The auditor loses room to bargain. Rewards should lean clue-heavy.

- Supply-first raid:
  The party clears Ration Cellar and Sluice Bell Alcove first. Sabotage night gets the strongest prevention hook, but Glasswater evidence may stay softer.

- Paper-first audit:
  The party clears Permit Stacks and Valve Wax Archive first. Glasswater gets the strongest mechanical payoff, while sabotage-night benefit depends on whether the bell is handled.

- Late cleanup:
  If sabotage night already happened, the branch turns quieter. The clerks are burning tabs, the ration cellar smells of spilled flour and lamp oil, and the bell alcove proves why a watch warning arrived too late.

## Blackglass Relay House Draft

Blackglass Relay House sits above the far landing, built into stone that sweats black water onto iron cable. The room still smells of lamp oil and river rot. Choir crews use its counterweights to keep Caldra's Forge support line timed.

Branch purpose:

- Give the player one optional pressure-control route after the causeway and before Caldra.
- Let Blackglass choices matter for a second beat before the Forge.
- Add a compact route for stealing timing notes, grounding a support signal, or turning an old relay bell against the Choir.

Room shape:

- `Relay Gate`: entrance; wet cables climb from Blackglass into a forge-wall signal duct.
- `Cable Sump`: combat lane; lake pressure and Choir guards protect the moving cable line.
- `Keeper Ledger`: treasure and clue room; timing slates name which bells still answer Caldra.
- `Null-Bell Walk`: event room; the party can tune the relay pulse into dead weight.
- `Counterweight Crown`: boss room; clearing it grants `blackglass_relay_house_cleared` and `forge_signal_grounded`.

Pathing:

- `Relay Gate` can lead to either `Cable Sump` or `Keeper Ledger`.
- `Cable Sump` and `Keeper Ledger` connect to each other, then feed `Null-Bell Walk`.
- `Null-Bell Walk` leads to `Counterweight Crown`.

Forge payoff:

- `forge_signal_grounded` can reduce Forge support enemies or lower one threshold DC.
- `forge_reserve_timing_known` can improve the first read at the Forge threshold.
- `blackglass_relay_bell_tuned` can give a one-scene defensive boon against Choir resonance.

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
| `Siltlock Counting House` | claim clerks, bribed guards, Choir paper handlers | optional early paper dungeon; exposes Glasswater permits and can warn sabotage-night supply watches |
| `Iron Hollow Sabotage Night` | Choir lookout plus adept strike cell | three-front town crisis where the player cannot protect everything first |
| `Broken Prospect Threshold` | Meridian Compact armor, spectral foreman, rival scouts | haunted route-control dungeon; stronger if taken after South Adit |
| `South Adit Prison Line` | starblighted miners and Choir wardens | captive survival map; Irielle hook; stronger if taken after Broken Prospect |
| `Resonant Vault Outer Galleries` | cave predator ecology | bigger five-column map with side runs, slime lanes, false echoes, and a final haul gate |
| `Blackglass Causeway` | constructs, starblight, lake predators | three objective choices: shrine, barracks, or anchors |
| `Blackglass Relay House` | Choir signal crews, Blackglass machinery | optional threshold branch; grounding the relay can weaken Forge support |
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
