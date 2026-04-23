# Aethrune

Aethrune is a Python text adventure set in a dark frontier world shaped by roads, records, buried infrastructure, and systems that still function after their creators are gone.

The project is currently in an Aethrune retcon pass. The implementation still preserves existing save-sensitive scene IDs and quest IDs internally, but the public story direction is now original: Greywake, the Emberway, Iron Hollow, the Shatterbelt Frontier, the Vein of Glass, the Meridian Accord, the Quiet Choir, and the Ashen Brand.

## Current State

Act 1 is fully playable and Act 2 is playable as a scaffolded expedition campaign. The current build includes:

- Character creation, companions, party XP, inventory, equipment, leveling, relationship bonuses, and camp management.
- A route-driven Act 1 with background prologues, roadside branches, a frontier hub, branching expedition sites, hidden-route discovery, fortress assault, and a final descent.
- A scaffolded Act 2 with a claims council, expedition hub, pressure tracking, local maps, route-order consequences, companion recruitment, and Act 3 handoff flags.
- Turn-based combat with checks, initiative, attacks, defenses, conditions, healing, death-state handling, class features, channel-like abilities, consumables, parley, fleeing, and chained encounters.
- A live map system for overworld travel and dungeon rooms, with Rich-powered panels when `rich` is installed and plain-text fallback when it is not.
- Optional audio, typed narration, pacing controls, dice animation, manual saves, journal, party, inventory, equipment, sheet, camp, and settings commands.

## Aethrune Retcon Direction

The retcon keeps the existing engine and much of the original narrative spine while replacing legacy setting wrappers with Aethrune.

Key canon:

- Aethrune is a fractured land where control of movement, records, and infrastructure is power.
- The Meridian Accord was an old civilization that governed roads, waterworks, archives, signals, and outcomes.
- The Shatterbelt Frontier is the Act 1 surface region.
- The Emberway is the main route artery.
- Greywake is the major city opening.
- Iron Hollow is the frontier hub.
- The Vein of Glass and Resonant Vaults carry Act 2 into deeper Accord infrastructure.
- The Ashen Brand controls routes through force, false authority, and supply pressure.
- The Quiet Choir controls truth through records, signals, and listening systems.

Current public terminology:

- Classes currently display with their existing class names until the full class redesign pass.
- Ability labels are `Strength`, `Agility`, `Endurance`, `Intelligence`, `Wisdom`, and `Charisma`.
- Race labels preserve internal mechanics keys while displaying retcon names such as `Forged (Dragonborn)`, `Unrecorded (Gnome)`, `Astral Elf (Half-Elf)`, `Fire-Blooded (Tiefling)`, and `Riverfolk (Goliath)`.
- Preset quick-start characters now display as Aethrune-facing pairings such as `Riverfolk Barbarian`, `Astral Elf Bard`, `Orc Fighter`, `Dwarf Cleric`, `Unrecorded Wizard`, `Forged Paladin`, and `Fire-Blooded Sorcerer`.

Planning lives under:

- `information/Retcon story/Plans/`
- `information/Retcon story/World/`
- `information/Retcon story/NPCs/`
- `information/Retcon story/Systems/`
- `information/Retcon story/Spells_and_abilities/`
- `information/Retcon story/Items/`
- `information/Retcon story/Races/`

## Running The Game

Easiest option on Windows:

```powershell
.\Play Aethrune.bat
```

Terminal option:

```powershell
pip install pygame rich
python main.py
```

`rich` is optional for gameplay logic but recommended for readable map and panel output.

## AI-Assisted Writing

The repo includes an optional OpenAI-backed drafting tool for scene prose, dialogue, and lore revision. It is for authoring support only; runtime story logic stays deterministic in Python and data files.

Example:

```powershell
pip install openai
python tools/story_writer.py --brief "Rewrite this route-control exchange so it reads as Greywake and Emberway logistics without changing route logic." --scene-key blackwake_crossing --context dnd_game/gameplay/story_intro.py
```

Full setup and examples live in `information/systems/OPENAI_STORY_WRITER.md`.

The desktop wrapper can be launched with:

```powershell
python story_writer_studio.py
```

or by double-clicking `Launch Story Writer Studio.bat` on Windows.

## Map Flow

The current implementation preserves the existing route structure while the public names are being retconned.

Act 1 route target:

- Greywake opening
- Emberway road sequence
- Iron Hollow hub
- Blackglass Well and Red Mesa Hold branch sites
- Cinderfall Ruins optional relay strike
- Ashfall Watch assault
- Duskmere Manor descent
- Emberhall Cellars finale

Act 2 route target:

- Iron Hollow claims council
- Hushfen and the Pale Circuit
- Greywake Survey Camp
- Stonehollow Dig
- Glasswater Intake
- Broken Prospect and South Adit
- Resonant Vault Outer Galleries
- Blackglass Causeway
- Meridian Forge

## Testing

Core regression coverage:

```powershell
python -m pytest tests/test_core.py
```

Fast Act 2 content-smoke pass:

```powershell
python -m pytest -m smoke
```

During the retcon, some tests may continue to reference internal legacy IDs until the public text pass, display-name mappings, and save-safe migrations are complete.

## Useful In-Game Commands

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

## Files Worth Knowing

- `main.py`: entry point.
- `dnd_game/`: main game code. The package name is retained for compatibility during the retcon.
- `information/Retcon story/Plans/AETHRUNE_RETCON_IMPLEMENTATION_PLAN.md`: active implementation plan.
- `information/Retcon story/Plans/IP_CLEANUP_PLAN.md`: IP cleanup audit and strategy.
- `information/Retcon story/World/`: Aethrune world and map-remap references.
- `information/Retcon story/Systems/`: variable and quest-matrix retcon references.
- `information/catalogs/ITEM_CATALOG.md`: generated item catalog pending Aethrune item-language cleanup.
- `saves/`: JSON save files.
- `tests/test_core.py`: core regression coverage.

## License And SRD Notice

The world, story, factions, characters, and setting direction are original to Aethrune.

Some mechanics may remain derived from SRD 5.2.1 during the retcon. If SRD-derived rules remain in a released build, include the required attribution:

This work includes material from the System Reference Document 5.2.1 ("SRD 5.2.1") by Wizards of the Coast LLC, available at https://www.dndbeyond.com/srd. The SRD 5.2.1 is licensed under the Creative Commons Attribution 4.0 International License.
