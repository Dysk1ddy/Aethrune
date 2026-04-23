# Aethrune Retcon Implementation Plan

This is the second-stage planning artifact for converting the current game into the Aethrune version before touching gameplay implementation.

It consolidates the new material under `information/Retcon story/` and the local SRD reference at `information/SRD_CC_v5.2.1.txt`.

## Source Scan

Primary retcon inputs scanned:

- `information/Retcon story/World/aethrune_world_v1.md`
- `information/Retcon story/Lore/roads_that_remember_v1.md`
- `information/Retcon story/Lore/roads_that_remember_v2_world.md`
- `information/Retcon story/World/act1_map_system_remap_aethrune.md`
- `information/Retcon story/World/act2_map_system_remap_aethrune.md`
- `information/Retcon story/Races/races.md`
- `information/Retcon story/Classes/aethrune_srd_class_whitelist_v1.md`
- `information/Retcon story/Spells_and_abilities/aethrune_retcon_rename_list_srd_v1.md`
- `information/Retcon story/Spells_and_abilities/aethrune_abilities_passives_v1.md`
- `information/Retcon story/Items/aethrune_item_retcon_list_v1.md`
- `information/Retcon story/Items/aethrune_items_v1.md`
- `information/Retcon story/NPCs/aethrune_retcon_npcs_enemies_v1.md`
- `information/Retcon story/NPCs/NPCs_new.md`
- `information/Retcon story/NPCs/enemies_new.md`
- `information/Retcon story/NPCs/NPC_relationship_map.md`
- `information/Retcon story/Systems/aethrune_gameplay_variables_tuning_v1.md`
- `information/Retcon story/Systems/aethrune_quest_to_variable_matrix_v1.md`

Current repo exposure scan:

- setting/lore rename terms still appear across roughly 2,500 lines in runtime/docs/tests
- rules-facing D&D/SRD terms still appear across roughly 1,450 lines in runtime/docs/tests
- the Android port mirrors many of the same names and should be treated as a second implementation surface

## Canonical Direction

The retcon target is now clear:

- world name: Aethrune
- primary Act 1 region: Shatterbelt Frontier
- old civilization: Meridian Accord
- old buried-builder compact: Meridian Compact
- Act 1 route artery: Emberway
- major city opening: Greywake
- frontier hub town: Iron Hollow
- Act 2 region: Vein of Glass
- Act 2 deep ruin complex: Resonant Vaults
- Act 2 finale system: Meridian Forge
- Act 3 region: Meridian Depths

Core theme:

- roads, records, waterworks, signals, and buried infrastructure still shape reality after their creators are gone

Implementation rule:

- replace player-facing names, labels, menus, codex text, dialogue, quest text, and item descriptions first
- keep internal scene ids, quest ids, save keys, flags, method names, and tests stable until the public rewrite is passing

## SRD Decision

Use SRD 5.2.1 as a mechanics safety net, not as the public identity of the game.

Practical rule:

- lore/world/characters/factions should be original Aethrune
- mechanics may remain SRD-derived where useful
- if SRD-derived terms or rules remain visible, include the required CC BY 4.0 attribution
- player-facing rules vocabulary should move toward Aethrune terms where the retcon docs explicitly request it

There is one important planning tension:

- `aethrune_srd_class_whitelist_v1.md` says core D&D class names and mechanics can be kept with attribution
- `aethrune_retcon_rename_list_srd_v1.md` says the public-facing goal is no visible SRD/D&D terminology

Resolution for implementation:

- keep the underlying mechanics initially
- introduce Aethrune public labels in a controlled pass
- do not rewrite the entire combat math system during the setting rename pass

## Public Rename Map

### Act 1 Locations

| Current public label | Aethrune public label | Internal id now |
| --- | --- | --- |
| Neverwinter | Greywake | keep |
| High Road / Triboar Trail | Emberway | keep |
| Phandalin | Iron Hollow | keep |
| Wayside Luck Shrine | Wayside Lantern Shrine | keep |
| Stonehill Inn | Ashlamp Inn | keep |
| Shrine of Tymora | Lantern Shrine | keep |
| Barthen's Provisions | Hadrik's Provisions | keep |
| Lionshield Trading Post | Ironbound Trading Post | keep |
| Edermath Orchard | Orchard Wall | keep |
| Miner's Exchange | Delvers' Exchange | keep |
| Old Owl Well | Blackglass Well | keep |
| Wyvern Tor | Red Mesa Hold | keep |
| Cinderfall Ruins | Cinderfall Ruins | keep |
| Ashfall Watch | Ashfall Watch | keep |
| Tresendar Manor | Duskmere Manor | keep |
| Emberhall Cellars | Emberhall Cellars | keep |
| Blackwake Crossing | Blackwake Crossing | keep |

### Act 2 Locations

| Current public label | Aethrune public label | Internal id now |
| --- | --- | --- |
| Phandalin claims council | Iron Hollow claims council | keep |
| Wave Echo Cave | Resonant Vaults | keep |
| Phandelver Pact | Meridian Compact | keep |
| Conyberry | Hushfen | keep |
| Agatha's Circuit | Pale Circuit | keep |
| Neverwinter Wood Survey Camp | Greywake Survey Camp | keep |
| Stonehollow Dig | Stonehollow Dig | keep |
| Glasswater Intake | Glasswater Intake | keep |
| Broken Prospect | Broken Prospect | keep |
| South Adit | South Adit | keep |
| Wave Echo Outer Galleries | Resonant Vault Outer Galleries | keep |
| Black Lake Causeway | Blackglass Causeway | keep |
| Forge of Spells | Meridian Forge | keep |

### NPCs

| Current public role/name | Aethrune direction |
| --- | --- |
| Elira Dawnmantle | Elira Lanternward in public text; keep companion id initially |
| Barthen | Hadrik |
| Halia Thornton | convert to Delvers' Exchange / Reclaimer-aligned claims figure; final public name still needs one pass |
| Linene Graywind | convert to Ironbound supply/trade figure; final public name still needs one pass |
| Daran Edermath | convert to Orchard Wall defensive veteran; final public name still needs one pass |
| Mara Stonehill | convert to Ashlamp Inn keeper; final public name still needs one pass |
| Agatha | Pale Witness |
| fake roadwardens | route forgers / fake route-authority agents |
| Town Council | Iron Hollow Council |
| Blackwake survivors | Emberway survivors where context is not specifically Blackwake Crossing |

NPCs that can mostly stay after context rewrite:

- Mira Thann
- Oren Vale
- Sabra Kestrel
- Vessa Marr
- Garren Flint
- Tessa Harrow
- Sella Quill
- Old Tam Veller
- Nera Doss
- Kaelis Starling
- Rhogar Valeguard
- Tolan Ironshield
- Bryn Underbough
- Nim Ardentglass
- Irielle Ashwake
- Varyn Sable
- Vaelith Marr
- Rukhar Cinderfang
- Caldra Voss

Open naming conflict:

- the retcon docs use both `Garren Flint` and `Garen Flint`; implementation should preserve `Garren Flint` unless you intentionally rename him, because current code/tests already use that spelling

### Enemies

| Current public enemy | Aethrune public enemy |
| --- | --- |
| Goblin Skirmisher | Scrapling Raider |
| Wolf / Worg | Ashfang Hound |
| Bandit | Ashen Brand Cutter or Road Agent |
| Bandit Archer | Ashen Brand Marksman |
| Animated Armor | Meridian Sentinel |
| Kobold | Cinderkin Scavenger |
| Orc Raider | Red Mesa Raider |
| Orc Bloodchief | Mesa Warlord |
| Ogre | Hollow Giant |
| Fen Wisp | Lantern Wisp |
| Nothic | Cistern Eye |
| Grimlock | Tunnel Scavenger |
| Stirge Swarm | Bloodmote Swarm |
| Ochre Slime | Corrosive Mass |
| Pact Foreman | Meridian Foreman |
| Cultist / Quiet Choir cultist | Quiet Choir Listener / Adept / Agent |

### Rules Presentation

| Current public term | Aethrune public term |
| --- | --- |
| spellcasting | channeling |
| spell slot | charge band |
| cantrip | minor channel / minor cast |
| upcast / upcasting | overchannel |
| pact magic | bound channel |
| magic item | relic |
| potion | draught |
| scroll | script |
| gold / gp | marks |
| Armor Class | Guard |
| saving throw | resist check |
| attack roll | strike check |
| advantage | edge |
| disadvantage | strain |

Deferred class public labels from the retcon docs:

| Current class | Aethrune label |
| --- | --- |
| Barbarian | Vanguard |
| Bard | Resonant |
| Cleric | Channeler |
| Druid | Wildbinder |
| Fighter | Blade |
| Monk | Disciple |
| Paladin | Oathbearer |
| Ranger | Pathwarden |
| Rogue | Veilrunner |
| Sorcerer | Fluxborn |
| Warlock | Bound |
| Wizard | Scribe |

Current runtime decision, revised after Phase 6 feedback: keep displayed class names as the current class names until the classes are reworked completely.

Spell/channel public labels from the retcon docs:

| Current spell | Aethrune channel |
| --- | --- |
| Magic Missile | Arc Pulse |
| Fire Bolt | Ember Lance |
| Ray of Frost | Frost Shard |
| Shocking Grasp | Volt Grasp |
| Cure Wounds | Field Mend |
| Healing Word | Pulse Restore |
| Guiding Bolt | Guiding Strike |
| Eldritch Blast | Void Surge |
| Shield | Ward Shell |
| Mage Armor | Phase Weave |
| Detect Magic | System Sense |
| Identify | Pattern Read |
| Inflict Wounds | Corrupt Strike |

## Implementation Phases

### Phase 0. Planning freeze

Do before changing runtime:

- use this document as the implementation source of truth
- resolve the few open NPC name mappings noted above
- decide whether tests should assert old internals or new public strings during the transition

### Phase 1. Public repo surface

Files:

- `README.md`
- `dnd_game/__init__.py`
- `android_port/README.md`
- `android_port/dnd_game/__init__.py`
- `information/systems/OPENAI_STORY_WRITER.md`

Goal:

- stop presenting the project as D&D / Forgotten Realms
- present it as Roads That Remember set in Aethrune
- mention SRD only as licensed mechanics attribution if still needed

Do not:

- alter game flow
- rename save keys
- rename internal package directories in this phase

### Phase 2. Lore and title-screen codex

Files:

- `dnd_game/data/story/lore.py`
- `android_port/dnd_game/data/story/lore.py`
- `dnd_game/gameplay/base.py`
- `android_port/dnd_game/gameplay/base.py`

Goal:

- replace Forgotten Realms and official-lore codex with Aethrune world, factions, regions, peoples, and systems
- change menu/codex labels from D&D setting context to Aethrune context
- keep rules-help pages only if rewritten or attributed

Status:

- implemented for desktop and Android lore codex files
- implemented for title-screen lore/menu copy in desktop and Android `base.py`
- implemented for public act-title metadata in shared character options
- focused lore/title tests updated to assert Aethrune-facing strings

Implementation notes:

- `dnd_game/data/story/lore.py` now presents Aethrune, the Shatterbelt Frontier, Greywake, the Emberway, Iron Hollow, the Vein of Glass, the Resonant Vaults, the Meridian Forge, Aethrune peoples, Aethrune public class labels, factions, Lantern Faith, and SRD-derived mechanics notes
- internal class/race/background keys are preserved so character creation and save compatibility are not forced into a rules-presentation migration yet
- lore menu labels now honor an optional `label` field, allowing entries such as `Barbarian` to display publicly as `Vanguard`
- item manual copy now uses Aethrune-facing terms such as Guard, draughts, scripts, relics, channeling, strike checks, and resist checks
- broader runtime scene labels, scene objectives, character introductions, Act 1 dialogue, and Act 2 dialogue still contain old public names and are intentionally deferred to Phases 3 and 4

### Phase 3. Act 1 surface rewrite

Files:

- `dnd_game/gameplay/story_intro.py`
- `dnd_game/gameplay/story_town_hub.py`
- `dnd_game/gameplay/story_town_services.py`
- `dnd_game/gameplay/story_act1_expanded.py`
- `dnd_game/gameplay/map_system.py`
- `dnd_game/gameplay/random_encounters.py`
- `dnd_game/data/quests/act1.py`
- `dnd_game/data/story/background_openings.py`
- `dnd_game/data/story/companions.py`
- `dnd_game/data/story/dialogue_inputs.py`
- `dnd_game/data/story/factories.py`
- `dnd_game/data/story/interaction_actions.py`
- `dnd_game/drafts/map_system/data/act1_hybrid_map.py`

Goal:

- rewrite displayed Act 1 path as Greywake -> Emberway -> Iron Hollow -> Blackglass Well / Red Mesa Hold -> Cinderfall -> Ashfall -> Duskmere -> Emberhall
- remove Tymora, Neverwinter, Phandalin, Stonehill, Barthen, Lionshield, Edermath, Miner's Exchange, Old Owl Well, Wyvern Tor, and Tresendar from player-facing strings
- preserve room graphs, scene ids, route unlocks, quest ids, and flags

#### Phase 3A Status

Implemented first Act 1 surface slice:

- rewritten opening/background prologue copy to Greywake, the Emberway, Iron Hollow, Lantern Hall, and Elira Lanternward public presentation
- rewritten Greywake briefing, departure fork, Emberway ambush, side-branch return copy, early encounter titles, and route prompts in `story_intro.py`
- rewritten Act 1 hybrid route-map public node labels and travel-edge labels in `act1_hybrid_map.py`
- added public character-name display aliases so legacy internal companion/NPC names can remain stable while dialogue and HUD output show Aethrune-facing names
- updated early Act 1 overworld backtrack copy to Greywake, Emberway, and Iron Hollow
- updated focused tests for the Phase 3A public strings while preserving internal ids such as `neverwinter_briefing`, `high_road_ambush`, and `phandalin_hub`

Validation:

- `python -m py_compile dnd_game\gameplay\base.py dnd_game\gameplay\io.py dnd_game\gameplay\story_intro.py dnd_game\gameplay\map_system.py dnd_game\data\story\background_openings.py dnd_game\drafts\map_system\data\act1_hybrid_map.py`
- `python -m pytest tests\test_core.py -k "background_prologue or class_identity_option_appears_in_briefing or neverwinter_briefing_routes_response_menu or road_ambush_approach_can_backtrack or road_ambush_flow_recruits_tolan or freshly_cleared_high_road_offers_side_branches or cleared_high_road_can_branch_to_false_checkpoint or road_ambush_scales_for_solo_party or road_ambush_scales_for_two_member_party or blackwake_entrance_offers_overworld_backtrack_to_greywake or act1_overworld_backtrack_can_return_to_greywake or act1_overworld_backtrack_from_iron_hollow or cleared_emberway_scene_can_backtrack_to_greywake or travel_to_act1_node_updates_state or open_act1_map_menu"`: 15 passed
- `python -m pytest tests\test_core.py`: 464 passed

Focused string scan result:

- Phase 3A files are clear of old public setting names except for intentional compatibility alias keys in `base.py`: `Barthen`, `Daran Edermath`, and `Mara Stonehill`
- remaining Act 1 old-name exposure is concentrated in Phase 3B/3C surfaces: town hub, town services, Act 1 expanded branch content, Act 1 quest text, camp banter, broader map-system scenes, and their older test expectations

#### Phase 3B Status

Implemented Iron Hollow town/service slice:

- rewritten town arrival, Blackwake arrival callbacks, steward options, hub menu labels, inn/service options, and town reward reasons in `story_town_hub.py`
- rewritten shrine, provisioner, and trading-post service copy in `story_town_services.py`
- rewritten Act 1 quest public definitions for Greywake, Iron Hollow, Hadrik's Provisions, Ironbound Trading Post, Ashlamp Inn, Delvers' Exchange, Blackglass Well, Orchard Wall, Red Mesa Hold, and Elira Lanternward while preserving quest ids
- updated public-facing town arrival identity interactions and companion interjections in `interaction_actions.py` and `dialogue_inputs.py`
- added a public intro for Mara Ashlamp and kept old internal companion/NPC keys where save compatibility still depends on them
- updated turn-in giver checks touched by renamed quest definitions so gameplay remains consistent while scene ids and quest ids remain stable
- updated related tests to assert the new public labels

Validation:

- `python -m py_compile dnd_game\gameplay\story_town_hub.py dnd_game\gameplay\story_town_services.py dnd_game\data\quests\act1.py dnd_game\data\story\interaction_actions.py dnd_game\data\story\dialogue_inputs.py dnd_game\gameplay\story_act1_expanded.py dnd_game\gameplay\map_system.py dnd_game\gameplay\base.py`
- `python -m pytest tests\test_core.py`: 464 passed

Focused string scan result:

- Phase 3B town/service files are clear of old public setting and town-service names
- remaining old-name exposure is now concentrated in Phase 3C/4 surfaces: Act 1 expanded branch scenes, broader map-system branch scenes, camp banter, Act 2 council/scaffold surfaces, and tests that intentionally still cover those later surfaces

#### Phase 3C Status

Implemented Act 1 expanded branch/map/camp slice:

- rewritten Act 1 expanded branch public copy in `story_act1_expanded.py` for Iron Hollow, Blackglass Well, Red Mesa Hold, Duskmere Manor, Resonant Vaults, Meridian Forge, Hadrik, Halia Vey, Linene Ironward, Daran Orchard, and Mara Ashlamp
- rewritten matching branch and encounter copy in `map_system.py`, including Red Mesa Hold, Blackglass Well, Duskmere, Resonant Vaults, Meridian Forge, and Iron Hollow backtrack language while preserving internal node ids and save flags
- rewritten camp banter public text in `camp_banter.py`, including the Lantern faith wording and renamed town/manor references
- pre-aligned the touched Act 2 route-map blueprint labels in `act2_enemy_map.py` where the Phase 3C map runtime exposed old names, including Iron Hollow, Ashlamp Claims Council, Greywake Wood labels, Resonant Vaults, and Meridian Forge
- updated related test expectations and direct public-string test inputs while preserving legacy internal ids such as `phandalin_hub`, `tresendar_manor`, `wyvern_tor_cleared`, and merchant ids

Validation:

- `python -m py_compile dnd_game\drafts\map_system\data\act2_enemy_map.py dnd_game\gameplay\story_act1_expanded.py dnd_game\gameplay\map_system.py dnd_game\data\story\camp_banter.py`
- `python -m pytest tests\test_core.py`: 464 passed

Focused string scan result:

- Phase 3C target files are clear of old public setting and town-service names
- remaining old-name exposure is now concentrated in Phase 4+ surfaces: Act 2 council/scaffold modules, Act 2 quest data, older random-encounter/endgame support text, item/enemy/rules presentation, Android mirror files, and documentation/history folders

### Phase 4. Act 2 surface rewrite

Files:

- `dnd_game/gameplay/act2/conyberry.py`
- `dnd_game/gameplay/act2/council.py`
- `dnd_game/gameplay/act2/wood_survey.py`
- `dnd_game/gameplay/story_act2_scaffold.py`
- `dnd_game/data/quests/act2.py`
- `dnd_game/drafts/map_system/data/act2_enemy_map.py`
- `dnd_game/drafts/map_system/docs/ACT2_ENEMY_DRIVEN_MAP_SYSTEM.md`

Goal:

- rewrite Act 2 as Iron Hollow claims council -> Hushfen/Pale Circuit, Greywake Survey Camp, Stonehollow Dig, Glasswater Intake -> Broken Prospect / South Adit -> Resonant Vaults -> Blackglass Causeway -> Meridian Forge
- remove Conyberry, Agatha, Neverwinter Wood, Wave Echo, Forge of Spells, and Phandelver from public text
- keep expedition hub logic, pressure variables, local-map dungeons, midpoint rules, delay consequences, and Act 3 handoff flags

#### Phase 4 Status

Implemented the Phase 4 Act 2 surface rewrite and the linked runtime cleanup it exposed:

- rewritten public-facing Act 2 council, Hushfen/Pale Circuit, Greywake Survey Camp, scaffold summary, quest, and route-map text in `council.py`, `conyberry.py`, `wood_survey.py`, `story_act2_scaffold.py`, `act2.py`, `act2_enemy_map.py`, and `ACT2_ENEMY_DRIVEN_MAP_SYSTEM.md`
- extended the pass into `dnd_game/gameplay/map_system.py` where the playable late-route/runtime scenes still surfaced Black Lake, Conyberry, Pact, and related old public Act 2 language
- normalized public Elira references in the touched Act 2 runtime surfaces to `Elira Lanternward` while preserving internal companion ids/lookups as `Elira Dawnmantle`
- updated `tests/test_core.py` for the new public canon and repaired the accidental mojibake block/box-drawing assertions introduced during earlier bulk rewrites

Validation:

- `python -m py_compile dnd_game\gameplay\act2\council.py dnd_game\gameplay\act2\conyberry.py dnd_game\gameplay\act2\wood_survey.py dnd_game\gameplay\story_act2_scaffold.py dnd_game\data\quests\act2.py dnd_game\drafts\map_system\data\act2_enemy_map.py dnd_game\gameplay\map_system.py tests\test_core.py`
- `python -m pytest tests\test_core.py`: 464 passed

Focused string scan result:

- the Phase 4 playable/runtime surfaces are now clear of old public Act 2 place/system names; remaining matches in the touched files are internal ids, legacy helper names, or companion-id lookups intentionally left stable
- remaining old-name exposure is now mostly Phase 5+ territory: item/enemy presentation, broader rules text, random-encounter/support text outside the Phase 4 target list, draft README/example support docs, Android mirror files, and documentation/history cleanup

### Phase 5. Items and enemies

Files:

- `dnd_game/data/items/catalog.py`
- `information/catalogs/ITEM_CATALOG.md`
- `information/catalogs/enemies.md`
- `information/catalogs/ACT2_ENEMY_EXPANSION_DRAFT.md`
- enemy factories in `dnd_game/data/story/factories.py`
- combat display strings where enemy names surface

Goal:

- rename item types toward draughts, scripts, relics, gear, marks
- replace D&D/setting references in descriptions
- consolidate or at least reframe repetitive trinkets into route tokens, signal relics, memory pieces, and faction marks
- replace public enemy names with the Aethrune taxonomy while preserving stat/archetype behavior

#### Phase 5 Status

Implemented the Phase 5 item/enemy presentation pass and the linked item UI cleanup it exposed:

- rewritten `dnd_game/data/items/catalog.py` item names, descriptions, sources, unique rewards, enchantment notes, trinket framing, and player-facing render helpers toward draughts, scripts, relics, gear, marks, Guard, strike, channeling, and resist checks
- regenerated `information/catalogs/ITEM_CATALOG.md` from the updated catalog source so the reference doc now matches runtime item presentation
- rewritten enemy display names in `dnd_game/data/story/factories.py` for Scrapling Raider, Ashfang Hound / Beast, Ashen Brand Cutter / Marksman, Red Mesa Raider, Mesa Warlord, Hollow Giant, Cistern Eye, Tunnel Scavenger, Bloodmote Swarm, Corrosive Mass, Meridian Sentinel, Meridian Archive Warden, Blackglass Adjudicator, Cinderkin Scavenger, Quiet Choir Listener / Agent, and Lantern Wisp while preserving template keys, archetypes, and encounter behavior
- updated linked player-facing item surfaces in `dnd_game/gameplay/base.py`, `dnd_game/gameplay/inventory_core.py`, `dnd_game/gameplay/inventory_management.py`, and `dnd_game/gameplay/camp.py` so identify, inventory, trade, recovery, and equipment-preview text follow the new Phase 5 vocabulary
- rewritten `information/catalogs/enemies.md` and `information/catalogs/ACT2_ENEMY_EXPANSION_DRAFT.md` to match the Aethrune enemy taxonomy and the already-retconned Act 2 place/system names
- updated `tests/test_core.py` for the new public item/enemy names and item-surface terminology

Validation:

- `python -m py_compile dnd_game\data\items\catalog.py dnd_game\data\story\factories.py dnd_game\gameplay\base.py dnd_game\gameplay\inventory_core.py dnd_game\gameplay\inventory_management.py dnd_game\gameplay\camp.py tests\test_core.py`
- `python -m pytest tests\test_core.py`: 464 passed

Focused string scan result:

- the Phase 5 target files are now clear of old D&D-linked item names, old enemy display names, and the major old location/faction references tied to the item/enemy presentation surface
- remaining old-name exposure is now mostly Phase 6+ territory: broader rules/global economy wording outside the item UI slice, older story/support docs, untouched companion/reference notes, Android mirror files, and documentation/history cleanup

### Phase 6. Rules presentation

Files:

- `dnd_game/data/story/character_options/classes.py`
- `dnd_game/data/story/character_options/races.py`
- `dnd_game/gameplay/creation.py`
- `dnd_game/gameplay/combat_flow.py`
- `dnd_game/gameplay/combat_resolution.py`
- `dnd_game/gameplay/magic_points.py`
- `dnd_game/gameplay/spell_slots.py`
- `dnd_game/gameplay/journal.py`
- `dnd_game/models.py`
- `tests/test_core.py`

Goal:

- introduce Aethrune labels for classes, peoples, channels, item terms, and visible mechanics
- keep internal IDs and old mechanics until public labels are stable
- use SRD attribution if any SRD names/rules remain visible or directly derived

Recommended approach:

- add display-name mapping functions instead of immediately renaming internal keys
- keep save compatibility
- update tests to assert player-facing Aethrune labels only after display mappings are in place

#### Phase 6 Status

Implemented the Phase 6 rules-presentation pass while preserving internal save and mechanics keys:

- added `dnd_game/data/story/public_terms.py` as the central public-label layer for ability/skill labels, channels, features, resources, marks, Guard, edge/strain, resist checks, and rules-text cleanup
- updated character creation, preset/custom summaries, class/race lore, progression text, party views, character sheets, combat menus, combat resolution output, dice labels, channel reserve displays, charge-band summaries, developer/help surfaces, rest costs, camp/town rest options, and random-encounter currency text to use Aethrune-facing vocabulary
- added model-level public identity helpers so runtime output can centralize displayed race/class identity without changing stored `race` / `class_name` values
- kept internal spell, resource, class, race, feature, currency, and advantage keys stable for save compatibility; public combat options now map back to legacy internal action keys
- updated `tests/test_core.py` to assert the new player-facing language and fixed one control-flow regression where the `Veilstrike` message escaped its Rogue-only branch

Validation:

- `python -m py_compile dnd_game\data\story\public_terms.py dnd_game\data\story\character_options\classes.py dnd_game\data\story\character_options\races.py dnd_game\gameplay\creation.py dnd_game\gameplay\creation_point_buy.py dnd_game\gameplay\combat_flow.py dnd_game\gameplay\combat_resolution.py dnd_game\gameplay\magic_points.py dnd_game\gameplay\spell_slots.py dnd_game\gameplay\journal.py dnd_game\models.py dnd_game\gameplay\base.py dnd_game\gameplay\io.py dnd_game\gameplay\progression.py dnd_game\gameplay\quests.py dnd_game\gameplay\inventory_core.py dnd_game\dice.py dnd_game\data\items\catalog.py`
- `python -m py_compile dnd_game\gameplay\camp.py dnd_game\gameplay\random_encounters.py dnd_game\gameplay\act2\council.py dnd_game\gameplay\story_town_hub.py dnd_game\gameplay\story_intro.py dnd_game\gameplay\map_system.py`
- `python -m pytest tests\test_core.py`: 464 passed

Focused string scan result:

- runtime/test matches for old rules terms are now limited to internal compatibility names, mapping tables, helper names, old action keys that are translated before display, or draft-only notes
- broader `information/` docs and the Android mirror still contain old SRD/D&D terminology and should be handled in later documentation/mirror cleanup rather than mixed into the desktop runtime pass

Phase 6 correction:

- class display names were restored to the current class names pending a full class redesign
- race display names were restored to bracketed retcon names while preserving internal mechanics keys, e.g. `Forged (Dragonborn)`, `Unrecorded (Gnome)`, `Elven Variant (Half-Elf)`, `Fire-Blooded (Tiefling)`, and `Riverfolk (Goliath)`
- preset race assignments were cleaned up so the quick-start roster no longer exposes `Half-Orc`; the Fighter preset now uses the `Orc` mechanics key and displays as `Orc Fighter`
- ability labels were restored to Strength, Intelligence, Wisdom, and Charisma while keeping Agility and Endurance

### Phase 7. Variables and deeper Aethrune systems

Files:

- `dnd_game/models.py`
- `dnd_game/gameplay/base.py`
- `dnd_game/gameplay/quests.py`
- Act 1 and Act 2 scene files

Minimum set from the retcon docs:

- companion approval / recruited / final state
- `rep_iron_hollow_council`
- `rep_ashen_brand`
- `rep_quiet_choir`
- `rep_meridian_reclaimers`
- `rep_free_operators`
- `town_fear`
- `ashen_strength`
- `survivors_saved`
- `act2_town_stability`
- `act2_route_control`
- `act2_whisper_pressure`
- `player_predictability`
- `system_alignment`
- `unrecorded_choice_tokens`
- `counter_cadence_known`

Important:

- this should come after the surface retcon unless a scene already needs these variables
- do not overload every choice with every variable

### Phase 8. Android mirror

Files:

- `android_port/dnd_game/...`
- `android_port/README.md`

Goal:

- mirror the stable desktop public-text rewrite
- avoid hand-editing divergent Android lore unless the port is intentionally split

## Non-Goals For First Implementation

Do not do these during the first implementation pass:

- rename `dnd_game/` package directory
- rename scene ids such as `phandalin_hub`, `neverwinter_briefing`, or `conyberry_agatha`
- rename quest ids such as `seek_agathas_truth` or `restore_barthen_supplies`
- rename save-state keys without migration code
- rewrite combat math
- rebuild all tests at once
- fully redesign every item in the catalog before core story text is clean

## Validation Plan

After each implementation phase:

1. Run targeted string scans for old public names.
2. Allow old names only in internal ids, migration comments, or this planning/history folder.
3. Run focused tests for touched systems.
4. Run the core regression suite once the phase is complete.

Suggested scans:

```powershell
rg -n -i "Neverwinter|Phandalin|High Road|Stonehill Inn|Shrine of Tymora|Barthen|Lionshield|Edermath|Miner's Exchange|Old Owl Well|Wyvern Tor|Tresendar Manor|Conyberry|Agatha|Wave Echo|Forge of Spells|Phandelver|Tymora" README.md dnd_game tests android_port
```

```powershell
rg -n -i "Magic Missile|Fire Bolt|Cure Wounds|Healing Word|Eldritch Blast|Spell Slots|Cantrip|Spellcasting|Pact Magic|Armor Class|Saving Throw|Advantage|Disadvantage|gp" README.md dnd_game tests android_port
```

Expected transition behavior:

- the first scan should shrink sharply after Phases 1-4
- the second scan should shrink after Phase 6
- tests may keep old internal ids during the transition but should not require old public labels after their phase is migrated

## Open Decisions Before Runtime Work

Resolve these before Phase 3 or while starting it:

- choose final public replacements for Halia Thornton, Linene Graywind, Daran Edermath, and Mara Stonehill
- decide whether Elira should be fully renamed in displayed companion names now or only in lore/codex first
- choose final inn label between `Ashlamp Inn`, `Lantern Rest`, and any later inn name
- choose final currency label between `marks`, `iron`, `coin`, and `script`; current strongest candidate is `marks`
- choose whether class labels are replaced in the first playable retcon release or saved for the rules-presentation phase
- decide how much of `information/Story/*` should be rewritten versus archived as old design history

## Recommended Next Move

Start implementation with Phase 1 and Phase 2 only:

- they clean the public face of the project
- they do not risk save compatibility
- they establish Aethrune as the canon before the heavy Act 1 and Act 2 text passes

After that, tackle Act 1 public-text rewrite as the first runtime pass.
