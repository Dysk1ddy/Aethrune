# Roads That Remember

Roads That Remember is a Python text adventure built around a D&D-inspired party adventure set between Neverwinter and Phandalin in the Forgotten Realms.

## Current state

Act 1 is fully playable. The game now includes:

- Character creation with race, class, background, skill picks, rogue Expertise, and ability score assignment
- Expanded race options including Human, Dwarf, Elf, Halfling, Dragonborn, Half-Elf, Half-Orc, Gnome, Tiefling, Goliath, and Orc
- Expanded class options including Fighter, Rogue, Cleric, Wizard, Paladin, Ranger, Druid, Barbarian, Bard, Monk, Sorcerer, and Warlock
- Shared party XP, gold, inventory, level-ups, class progression, and companion relationship bonuses
- A significantly expanded Act 1 with background-specific prologues, post-ambush High Road side branches before Phandalin, a larger Phandalin hub, fixed town events, non-combat scenes, inns and NPC hubs, a live hybrid map system, branching grid dungeons, the hidden `Cinderfall Ruins` route, multiple minibosses, and a longer final dungeon push
- Recruitable companions with camp interactions, relationship growth, scene support bonuses, trust-gated interjections, personal quest hooks, party/camp management, and camp resurrection for fallen allies with a `Scroll of Revivify`
- Act 1 reactivity layers for `Town Fear`, `Ashen Strength`, and `Survivors Saved`, plus route sabotage, companion conflict scenes, and three end-of-act victory tiers that feed pressure into Act 2
- Post-combat random encounters with non-forced outcomes, optional fights, loot scenes, road events, ruins, shrines, smugglers, bandits, animals, abandoned locations, and small follow-up chains that can pay off later in the act

Act 2 is now playable as a scaffolded expedition campaign, and the project also includes:

- A live Act 2 route framework with the claims council, expedition hub, Act II pressure tracking, playable local maps for `Stonehollow Dig`, `Broken Prospect`, `South Adit`, `Wave Echo Outer Galleries`, `Black Lake Causeway`, and the `Forge of Spells`, plus an Act II completion handoff into Act 3 state
- A full Act 2 content reference built around Phandalin's claim war, Wave Echo Cave, branching expedition routes, companion side arcs, two new recruitable companions, a cult-agent boss, and Act 3 foreshadowing
- Act 2-exclusive item entries in the source item catalog so future quest rewards, loot tables, and merchants can reference them directly

## Combat and rules systems

- D&D-style checks, initiative, combat rounds, attack rolls, saving throws, damage, healing, conditions, and death saves
- A visible Magic Points (`MP`) spellcasting economy: combat spells show their MP cost, cantrips spend MP, unaffordable spells drop out of the combat menu, and failed direct casts explain the shortfall
- A real action / bonus action turn structure with support for features like Rage, Bardic Inspiration, Second Wind, Healing Word, Martial Arts, Flurry of Blows, Patient Defense, Step of the Wind, Cunning Action, off-hand attacks, and Action Surge
- Potion timing rule support:
  drinking a healing potion yourself is a bonus action
  giving a healing potion to someone else is an action
- Class and enemy abilities, status effects, resistances, parley, fleeing, chained-fight handling, companion combat openers, and simple enemy coordination around marked targets

## Inventory, equipment, and items

- A shared inventory with loot drops, merchants, selling, carrying capacity, consumables, scrolls, rarity tiers, and supply-based resting
- Rest and consumable support for the MP migration: long rests refill MP, short rests restore half MP for most casters and all MP for warlocks, and spell-refresh consumables now restore MP
- Full equipment management for every party member, not just the player character
- Equipment slots for `Head`, `Ring 1`, `Ring 2`, `Neck`, `Chest`, `Gloves`, `Boots`, `Main Hand`, `Off Hand`, and `Cape`
- Character sheets for every party member, separate from the quick `party` combat-status view
- A generated item reference in `information/catalogs/ITEM_CATALOG.md` covering the full catalog, rarity, rules text, weight, and acquisition sources

## Presentation and readability

- A live Act 1 hybrid map display:
  node-based overworld travel in Phandalin
  room-based dungeon maps in combat sites
  Rich-powered panels when `rich` is installed, with plain-text fallback if not
- Act 2 expedition status support:
  Act II pressure and route panels in the map UI
  journal and campaign snapshots for rescue, clue, and route state
  a compact camp digest so expedition fallout stays visible outside the hub
- Skill-tagged dialogue only when a real check is involved, with redundant tags suppressed for action text and `BACKTRACK` labels kept explicit for navigation
- Consistent blank-line spacing after non-conversation action choices
- Failed checks now avoid repetitive canned failure text
- Animated dice rolls for checks, attacks, saves, healing, damage, initiative, and other shared dice events
- D20 animations show the live roll against the target number such as `vs DC` or `vs AC`
- Pressing `Enter` during a dice animation fast-forwards it to the final result while still keeping the final one-second pause
- Choice pacing, combat transition pacing, typed NPC dialogue, typed scene/setup narration, staggered loot reveals, and first-meeting descriptions for named NPCs, companions, and unique enemies
- A settings menu available from the title screen and by typing `settings` during prompts, with separate audio and presentation toggles

## Running the game

Easiest option on Windows:

1. Double-click `Play Roads That Remember.bat`

That launcher automatically opens the game from the correct folder, so you do not need to use `cd` or type `python main.py`.

If you prefer the terminal way:

```bash
pip install pygame rich
python main.py
```

`rich` is optional for gameplay logic, but strongly recommended now because the Act 1 map system uses it for the overworld and dungeon panels.

## Act 1 map flow

Act 1 now uses a hybrid navigation structure:

- Phandalin uses node-based travel. The hub renders the current overworld route when you arrive, and you can reopen it any time with `map`.
- After the High Road ambush is fully cleared, the road scene now reopens as a travel choice before Phandalin. You can press south, backtrack to the prior route node, or take unlocked side branches such as `Liar's Circle`, `False Roadwarden Checkpoint`, and `False Tollstones`.
- Returning from a High Road side branch preserves the High Road as the meaningful backtrack point and avoids sending Phandalin backtracking into resolved side detours.
- Combat sites use room-based dungeon traversal. Each site keeps its own mini-map, current room, and cleared room history.
- Branching routes usually reconverge on a miniboss or boss room. Some paths are optional support rooms; others gate later rooms directly.
- Dungeon movement is now direction-driven. Available room choices are labeled as `[MOVE LEFT]`, `[MOVE RIGHT]`, `[MOVE UP]`, or `[MOVE DOWN]`.
- Maps no longer redraw on every prompt. They appear when you enter the hub or arrive in a dungeon room, and after that you can reopen them with `map`.
- The `map` command opens a selector:
  `1. Overworld`
  `2. Dungeon` if you are currently inside a dungeon
  `3. Back`

Current Act 1 dungeon structure:

- `Old Owl Well`: opening dig-ring fight, then choose between the salt cart rescue or the supply trench notes before Vaelith Marr, with some approaches opening a second layer of tactical follow-up
- `Wyvern Tor`: opening shelf fight, then choose between the drover hollow or shrine ledge before Brughor, with rescued allies and companion input able to shift the boss setup
- `Cinderfall Ruins`: optional hidden pre-Ashfall relay strike with a chapel/storehouse branch that can cut Ashfall reinforcements and reserves
- `Ashfall Watch`: gate breach into a fast support choice, then lower barracks, then Rukhar
- `Tresendar Manor`: entry route, intake fight, clue branch, optional store room, then the cistern eye
- `Emberhall Cellars`: antechamber, control/ledger branch, optional reserve room, then Varyn and an Act 1 ending state that can land as clean, costly, or fractured

## Feedback guide

The best feedback right now is concrete playtest feedback rather than broad taste feedback. The most useful notes are:

- where the overworld layout still feels visually off or too wide
- where a dungeon branch felt confusing, too linear, or too easy to miss
- where a direction label matched the map cleanly
- where a direction label felt wrong for the room you actually entered
- where using `map` was enough to stay oriented, or where you still wanted the map shown automatically again
- any room or branch that felt unrewarding compared to its risk
- any point where the map state, quest state, and story text seemed out of sync

Useful format:

- `Location / room`
- `Command or choice used`
- `What I expected`
- `What happened`
- `What I want instead`

## Map playtest checklist

If you want a quick focused pass on the new map system, this route will cover most of it:

1. Reach `Phandalin` and note whether the overworld panel makes the unlocked routes easy to read on first display.
2. Type `map`, choose `Overworld`, and confirm the panel is still readable when reopened manually.
3. Clear `Old Owl Well` and check whether the branch choices clearly signal direction.
4. Clear `Wyvern Tor` and take the opposite style of branch from what you chose at Old Owl.
5. If `Cinderfall Ruins` unlocks, clear it before `Ashfall Watch` and check whether the hidden-route branch feels readable and worth discovering.
6. Enter `Ashfall Watch` and verify the side branches, reconvergence, and `map -> Dungeon` flow still feel readable.
7. Enter `Tresendar Manor` and test returning through a previously visited room.
8. Finish `Emberhall Cellars` and note whether the final route feels readable under pressure and whether the ending state felt earned.

## Testing

Core regression coverage:

```bash
python -m pytest tests/test_core.py
```

That suite now includes coverage for:

- Act 1 map-state initialization
- High Road post-ambush branch routing, side-branch cleanup, and backtrack history behavior
- branching room progression in the live map system
- hidden-route unlocks, `Cinderfall Ruins`, and Ashfall sabotage behavior
- companion quest / conflict hooks, encounter-chain unlocks, and Act 1 ending-tier carryover
- new Act 1 enemy coordination and companion combat opener behavior
- existing Act 1 scene flow compatibility
- Act 2 local-map progression, route-order consequences, companion recruitment, pressure/digest UI, forge finale routing, and Act 3 handoff flags
- MP creation, old-save reconciliation, combat menu costs, spell spending, insufficient-MP handling, short-rest recovery, warlock recovery, long-rest refill, and MP-restoring consumables

## Reference docs

For reading, balancing, and debugging, the project now has a few source-facing markdown references:

- `information/systems/GAME_SYSTEMS_REFERENCE.md`: classes, races, backgrounds, leveling, combat formulas, spells, abilities, statuses, rest rules, and inventory systems
- `information/systems/MP_SYSTEM_DRAFT.md`: implemented MP economy notes, formulas, costs, rest recovery, migration status, and tuning guidance
- `information/systems/QUEST_SYSTEM_REFERENCE.md`: quest data model, lifecycle, turn-in rules, rewards, story unlocks, and maintenance checklist
- `information/Story/ACT1_CONTENT_REFERENCE.md`: Act 1 route flow, major NPC hubs, expanded quest chain, enemy archetypes, rewards, recruitment points, and useful story flags
- `information/Story/ACT2_CONTENT_REFERENCE.md`: Act 2 route flow, new recruitable companions, companion side arcs, Wave Echo / cult structure, quests, enemies, and the planned Act 2 random encounter pool
- `information/catalogs/ITEM_CATALOG.md`: full generated item, equipment, consumable, and scroll catalog

## Useful in-game commands

During prompts you can also type:

- `save`
- `settings`
- `map`
- `party`
- `journal`
- `inventory` / `backpack` / `bag`
- `equipment` / `gear`
- `sheet` / `sheets`
- `camp`
- `help`

## Settings

You can open `Settings` from the main menu or type `settings` at most prompts.

The settings menu currently includes:

- Toggle sound effects
- Toggle music
- Toggle dice animations
- Toggle typed narration and dialogue
- Toggle pacing pauses
- Toggle staggered option reveals
- Settings persist between sessions, so your audio and presentation preferences carry over after closing the game

## Files worth knowing

- `main.py`: entry point
- `dnd_game/`: main game code
- `information/systems/GAME_SYSTEMS_REFERENCE.md`: mechanics and progression reference
- `information/systems/MP_SYSTEM_DRAFT.md`: Magic Points implementation and balance reference
- `information/systems/QUEST_SYSTEM_REFERENCE.md`: quest system and reward reference
- `information/Story/ACT1_CONTENT_REFERENCE.md`: Act 1 content and debugging reference
- `information/Story/ACT2_CONTENT_REFERENCE.md`: Act 2 design target and future implementation reference
- `information/catalogs/ITEM_CATALOG.md`: generated full item catalog
- `saves/`: JSON save files
- `tests/test_core.py`: core regression coverage

## Lore and rules references

The setting and mechanics are shaped by official D&D / Forgotten Realms references, especially:

- Forgotten Realms material around Neverwinter and Phandalin
- D&D 2014 Basic Rules sections for character creation, ability checks, proficiency, combat, spellcasting, conditions, healing, and equipment

## Scope

Act 1 is implemented and now runs as a much longer frontier campaign: Neverwinter and the High Road lead into Phandalin, then out through Old Owl Well and Wyvern Tor in either order, with an optional hidden swing through Cinderfall Ruins before Ashfall Watch, then down through Tresendar Manor and Emberhall for the finale.

Act 2 now runs as a playable scaffolded Phandelver / Wave Echo expedition arc with branching early leads, midpoint sponsor pressure in Phandalin, deeper companion development, route-order consequences, multi-room Wave Echo maps, a cult agent manipulating an obelisk shard, and explicit state handoff from both Act 1 and Act 2 into a weirder cosmic Act 3. Act 3 itself is still roadmap-only.
