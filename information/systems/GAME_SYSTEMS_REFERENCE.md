# Aethrune Systems Reference

This file is a source-oriented reference for reading and debugging the current game implementation.

## Scope

- Current fully playable campaign scope: Act 1
- Current partially playable scaffold: Act 2 route framework and local-map expedition slices
- Current level cap: 4
- Party progression is shared across the whole company
- The game uses a compact SRD-derived d20 rules layer internally while public terminology is being moved toward Aethrune.

## Source Map

- `dnd_game/game.py`: main composed game class
- `dnd_game/gameplay/creation.py`: character creation flow
- `dnd_game/data/story/character_options/classes.py`: classes and level progression
- `dnd_game/data/story/character_options/races.py`: races
- `dnd_game/data/story/character_options/backgrounds.py`: backgrounds
- `dnd_game/gameplay/progression.py`: XP and level-up handling
- `dnd_game/gameplay/map_system.py`: live Act 1 and Act 2 map flow, route flags, reactivity state, and epilogue carryover
- `dnd_game/gameplay/magic_points.py`: MP formulas, spell costs, spend/restore helpers, and spell-slot-to-MP item conversion
- `dnd_game/gameplay/combat_flow.py`: combat turn options and enemy AI
- `dnd_game/gameplay/combat_resolution.py`: attack, spell, healing, damage, save, and death logic
- `dnd_game/gameplay/status_effects.py`: status definitions and condition ticking
- `dnd_game/gameplay/inventory_core.py`: resting, supply use, loot, item use
- `dnd_game/gameplay/random_encounters.py`: post-combat event pool, follow-up chains, and Act-specific encounter tables
- `dnd_game/data/story/factories.py`: hero and enemy factory data
- `dnd_game/data/quests/act1.py`: quest definitions
- `information/systems/QUEST_SYSTEM_REFERENCE.md`: detailed quest lifecycle, rewards, turn-in, and maintenance reference
- `information/catalogs/ITEM_CATALOG.md`: generated item and equipment catalog

## Campaign State Layers

### Act 1 route structure

- Overworld travel is node-based around the save-safe `phandalin_hub` id, now presented as Iron Hollow.
- Hostile sites use room-based dungeon progression from `dnd_game/drafts/map_system/data/act1_hybrid_map.py`
- The live mid-Act route can now include Blackglass Well, Red Mesa Hold, and an optional hidden Cinderfall Ruins strike before Ashfall Watch.
- The Emberway now has a post-ambush travel choice before Iron Hollow. Once both ambush waves are cleared, the scene reopens with the south road, a `BACKTRACK` option when history allows it, and any unlocked side branches: `Liar's Circle`, `False Roadwarden Checkpoint`, and `False Tollstones`.
- Returning from those Emberway side branches travels to `phandalin_hub` without recording the side branch as the new backtrack target. From Iron Hollow, backtracking skips resolved Emberway side detours and points back to the meaningful route node.

### Act 1 metrics and carryover

- `act1_town_fear`
  - default `2`
  - tracks how badly Iron Hollow is rattled
- `act1_ashen_strength`
  - default `3`
  - tracks how much outer-site pressure the Ashen Brand still retains
- `act1_survivors_saved`
  - default `0`
  - tracks rescue outcomes across the act
- `act1_victory_tier`
  - recorded as `clean_victory`, `costly_victory`, or `fractured_victory`
- `act2_starting_pressure`
  - derived from the ending tier plus a few late moral choices such as selling Bryn's ledger

### Quest-state rules

- Quest log statuses are `active`, `ready_to_turn_in`, and `completed`
- Readiness is driven from flags, not scene position alone
- Some Act 1 quests are auto-granted from companion trust thresholds rather than a town-giver menu

## Character Creation

### Ability assignment

- Standard array: `15, 14, 13, 12, 10, 8`
- Point buy budget: `27`
- Point buy costs:

| Score | Cost |
| --- | ---: |
| 8 | 0 |
| 9 | 1 |
| 10 | 2 |
| 11 | 3 |
| 12 | 4 |
| 13 | 5 |
| 14 | 7 |
| 15 | 9 |

### Shared character formulas

- Ability modifier: `(score - 10) // 2`
- Proficiency bonus: `2 + max(0, (level - 1) // 4)`
- Levels 1-4 all currently use proficiency bonus `+2`
- Starting HP: `hit die + CON modifier`, minimum `1`
- Unarmored AC:
  - default: `10 + DEX`
  - Barbarian: `10 + DEX + CON`
  - Monk: `10 + DEX + WIS`
- Weapon attack bonus: attack ability modifier + proficiency + weapon bonus + bonuses from features, gear, and relationships
- Weapon damage bonus: attack ability modifier + weapon bonus + bonuses from features, gear, and relationships
- Spell attack bonus: proficiency + spellcasting ability modifier + spell attack bonuses
- Spell save DC: `8 + proficiency + spellcasting ability modifier`

### Magic Points

Combat spellcasting now uses Magic Points (`MP`) as the player-facing resource. Spell-slot resources still synchronize as compatibility data, but combat menus, party sheets, combatant summaries, rest recovery, and spell-refresh consumables all speak in MP.

- MP is stored as `resources["mp"]` with the maximum in `max_resources["mp"]`
- Full casters: `6 + 4 * level + max(0, spellcasting modifier)`
- Pact casters: `4 + 3 * level + max(0, spellcasting modifier)`
- Half casters from level 2 onward: `4 + 2 * level + max(0, spellcasting modifier)`
- Feature casters, including level-1 Paladins with `divine_smite`, use `3 + max(0, spellcasting modifier)`
- Characters without spellcasting or feature-caster access have no MP row
- Creation, level reconciliation, and old-save integrity checks call `synchronize_magic_points`
- Combat options only show spells the actor can currently afford; direct cast attempts with too little MP print the required cost and current MP

## Classes

| Class | HD | Saves | Level 1 features | Starting resources | Spell stat |
| --- | ---: | --- | --- | --- | --- |
| Barbarian | d12 | STR, CON | Rage, Unarmored Defense | rage 2 | none |
| Bard | d8 | DEX, CHA | Bard Spellcasting, Bardic Inspiration | MP by formula, bardic_inspiration 3 | CHA |
| Cleric | d8 | WIS, CHA | Cleric Spellcasting | MP by formula | WIS |
| Druid | d8 | INT, WIS | Druid Spellcasting | MP by formula | WIS |
| Fighter | d10 | STR, CON | Second Wind | second_wind 1 | none |
| Monk | d8 | STR, DEX | Martial Arts, Unarmored Defense | none | none |
| Paladin | d10 | WIS, CHA | Lay on Hands, Divine Smite | lay_on_hands 5, MP from Divine Smite access | CHA |
| Ranger | d10 | STR, DEX | Natural Explorer | none | none |
| Rogue | d8 | DEX, INT | Sneak Attack, Expertise | none | none |
| Sorcerer | d6 | CON, CHA | Sorcerer Spellcasting | MP by formula | CHA |
| Warlock | d8 | WIS, CHA | Warlock Spellcasting | MP by pact formula | CHA |
| Wizard | d6 | INT, WIS | Wizard Spellcasting, Arcane Recovery | MP by formula | INT |

## Leveling

### Shared XP thresholds

| Level | XP |
| --- | ---: |
| 1 | 0 |
| 2 | 300 |
| 3 | 900 |
| 4 | 2700 |

### Level-up rules

- XP is stored once on `GameState`, not per character
- Every party member and companion levels together when the shared XP threshold is reached
- HP gain on level-up: `max(1, hit_die // 2 + 1 + CON modifier)`
- The player picks one new class skill at each level-up if one remains available
- Companions auto-pick the first available class skill
- Spellcasting characters resynchronize MP on level-up and save reconciliation; spell-slot values still synchronize as hidden compatibility data
- Paladin Lay on Hands pool becomes `level * 5`
- Monk ki scales to current level once ki has been unlocked

### Class progression by level

#### Barbarian

- Level 2: Reckless Pressure, `+1 damage`, `+1 initiative`
- Level 3: Primal Tenacity, `+1 AC while unarmored`
- Level 4: Ferocious Presence, `+1 Intimidation`, `+1 CON saves`

#### Bard

- Level 2: Cutting Wit, `+1 spell damage`
- Level 3: Silver Tongue, `+1 Persuasion`, `+1 Deception`
- Level 4: Stage Courage, `+1 initiative`, `+1 WIS saves`

#### Cleric

- Level 2: Channel Divinity, `channel_divinity 1`
- Level 3: Disciple of Life, `+2 healing`
- Level 4: Radiant Potency, `+1 spell damage`

#### Druid

- Level 2: Natural Recovery, short rests restore spellcasting stamina under the MP recovery rules
- Level 3: Wildfire Adept, `+1 spell damage`, `+1 healing`
- Level 4: Land's Embrace, `+1 AC`, `+1 WIS saves`

#### Fighter

- Level 2: Action Surge, `action_surge 1`
- Level 3: Improved Critical, criticals on `19-20`
- Level 4: Martial Mastery, `+1 attack`, `+1 damage`

#### Monk

- Level 2: Ki, Flurry of Blows, Patient Defense, Step of the Wind, Unarmored Focus, `ki 2`, `+1 AC`, `+1 initiative`
- Level 3: Open Hand Timing, `+1 damage`
- Level 4: Centered Spirit, `+1 WIS saves`, `+1 Insight`

#### Paladin

- Level 2: Divine Health, `+1 CON saves`, `+1 WIS saves`
- Level 3: Aura of Resolve, `+1 AC`
- Level 4: Radiant Strikes, `+1 damage`

#### Ranger

- Level 2: Hunter's Quarry, `+1 damage`
- Level 3: Skirmisher's Eye, `+2 initiative`, `+1 Perception`
- Level 4: Fieldcraft, `+1 Nature`, `+1 Survival`

#### Rogue

- Level 2: Cunning Action, `+2 Stealth`, `+2 initiative`
- Level 3: Deadly Sneak Attack, Sneak Attack becomes `2d6`
- Level 4: Evasion, `+2 DEX saves`

#### Sorcerer

- Level 2: Arcane Overflow, `+1 spell damage`
- Level 3: Warped Grace, `+1 initiative`, `+1 CHA saves`
- Level 4: Focused Will, `+1 spell attack`

#### Warlock

- Level 2: Patron's Sting, `+1 spell damage`
- Level 3: Unnerving Presence, `+1 Intimidation`, `+1 WIS saves`
- Level 4: Eldritch Precision, `+1 spell attack`

#### Wizard

- Level 2: Sculpted Cantrips, `+1 spell damage`
- Level 3: Spellguard, `+1 INT saves`, `+1 initiative`
- Level 4: Arcane Focus, `+1 spell attack`

## Races

| Public race (mechanics key) | Ability bonuses | Skill grants | Feature tags |
| --- | --- | --- | --- |
| Human | STR+1, DEX+1, CON+1, INT+1, WIS+1, CHA+1 | none | none |
| Dwarf | CON+2 | none | darkvision, dwarven_resilience |
| Elf | DEX+2 | Perception | darkvision, keen_senses, fey_ancestry |
| Halfling | DEX+2 | none | lucky, brave |
| Forged (`Dragonborn`) | STR+2, CHA+1 | none | draconic_presence |
| Unrecorded (`Gnome`) | INT+2 | Investigation | gnome_cunning |
| Astral Elf (`Half-Elf`) | CHA+2, DEX+1, WIS+1 | Insight, Persuasion | fey_ancestry |
| Orc-Blooded (`Half-Orc`) | STR+2, CON+1 | Intimidation | relentless_endurance, menacing |
| Fire-Blooded (`Tiefling`) | INT+1, CHA+2 | none | darkvision, hellish_resistance |
| Riverfolk (`Goliath`) | STR+2, CON+1 | Athletics | stone_endurance |
| Orc | STR+2, CON+1 | Intimidation | darkvision, adrenaline_rush |

### Racial feature hooks

Implemented directly in mechanics:

- `lucky`: rerolls natural 1s on d20 rolls
- `dwarven_resilience`: poison save advantage and poison resistance
- `hellish_resistance`: fire resistance
- `unarmored_defense_barbarian` and `unarmored_defense_monk`: AC formulas

Present as tags and lore, but not given dedicated runtime logic yet:

- `darkvision`
- `keen_senses`
- `fey_ancestry`
- `brave`
- `draconic_presence`
- `gnome_cunning`
- `relentless_endurance`
- `menacing`
- `stone_endurance`
- `adrenaline_rush`

## Backgrounds

| Background | Skill proficiencies | Extra proficiencies | Passive bonuses |
| --- | --- | --- | --- |
| Soldier | Athletics, Intimidation | Land Vehicles, Gaming Set | Athletics +1, Intimidation +1 |
| Acolyte | Insight, Religion | Calligrapher's Supplies, Celestial | Medicine +1, Religion +1 |
| Criminal | Deception, Stealth | Thieves' Tools, Disguise Kit | Stealth +1, Sleight of Hand +1 |
| Sage | Arcana, History | Calligrapher's Supplies, Draconic | Arcana +1, History +1 |
| Outlander | Athletics, Survival | Herbalism Kit, One Musical Instrument | Nature +1, Survival +1 |
| Charlatan | Deception, Sleight of Hand | Forgery Kit, Disguise Kit | Deception +1, Performance +1 |
| Guild Artisan | Insight, Persuasion | Artisan's Tools, Merchant's Scales | History +1, Persuasion +1 |
| Hermit | Medicine, Religion | Herbalism Kit, Sylvan | Insight +1, Medicine +1 |

## Combat Flow

### Turn structure

- Each turn starts with `1` action and `1` bonus action
- Some abilities add or trade on top of that:
  - Fighter Action Surge grants one extra action
  - Monk Flurry of Blows, Patient Defense, and Step of the Wind use bonus action and ki
  - Rogue Cunning Action uses bonus action
  - Off-hand attack requires the Attack action first
- Dodge is a full action
- Trying to flee usually costs an action and uses Stealth vs DC `13`
- Free flee can be created by Step of the Wind or Cunning Action dash/disengage

### Initiative

- Initiative = d20 + DEX modifier + initiative bonuses + encounter hero/enemy bonus
- Tie sorting prefers higher DEX and then heroes over enemies

### Companion combat support

- Scene support bonuses are separate from combat-start openers
- At disposition `6+`, Kaelis can fire `Shadow Volley` to give the conscious party `Invisible 1` at encounter start
- At disposition `6+`, Tolan can call `Hold the Line` to give the conscious party `Guarded 2` at encounter start

### Enemy coordination hooks

- `Marked` is now a shared focus-fire status
- `Ember Channeler` can apply `Marked 2`, and enemies with updated AI will prefer marked heroes when possible
- `Ashen Brand Enforcer` can spend `punishing_strike` to punish buffed or marked heroes and strip `Blessed`
- `Carrion Stalker` opens under `Invisible` pressure and applies `Bleeding` on hits

### Criticals

- Normal critical threshold: `20`
- Fighter with Improved Critical: `19-20`
- Criticals double the dice count in the rolled expression

### Sneak Attack

- Rogue Sneak Attack is active if another conscious hero is present and the target is conscious
- It currently triggers on weapon attacks when the computed attack advantage state is not negative
- Damage:
  - Levels 1-2: `1d6`
  - Levels 3-4: `2d6`

### Off-hand rules

- Requires light melee weapons in both hands
- No ranged weapons
- No two-handed weapons
- Off-hand damage does not include positive ability modifier

## Implemented Spells And Active Combat Abilities

| Spell or ability | Users | Cost | Effect |
| --- | --- | --- | --- |
| Sacred Flame | Cleric | action, 1 MP | DEX save vs WIS DC, `1d8` radiant, applies Reeling 1 |
| Cure Wounds | Bard, Cleric, Druid, Paladin | action, 3 MP | `1d8 + casting mod + healing bonuses` |
| Healing Word | Bard, Cleric, Druid | bonus action, 4 MP | `1d4 + casting mod + healing bonuses` |
| Fire Bolt | Sorcerer, Wizard | action, 1 MP | spell attack, `1d10` fire, applies Burning 2 |
| Produce Flame | Druid | action, 1 MP | spell attack, `1d8` fire, applies Burning 2 |
| Magic Missile | Sorcerer, Wizard | action, 5 MP | auto-hit style implementation, `3d4+3` force |
| Vicious Mockery | Bard | action, 1 MP | WIS save vs CHA DC, `1d6` psychic, applies Reeling 2 |
| Eldritch Blast | Warlock | action, 1 MP | spell attack, `1d10` force, applies Reeling 1 |
| Rage | Barbarian | bonus action, 1 rage | gains temp HP `4 + level`, applies Emboldened 3 |
| Bardic Inspiration | Bard | bonus action, 1 inspiration | applies Blessed 2 to ally |
| Second Wind | Fighter | bonus action, 1 use | heal `1d10 + level` |
| Action Surge | Fighter | special, 1 use | adds 1 action |
| Martial Arts | Monk | bonus action after attack | attack for `1d4 + normal monk damage bonus`, applies Reeling 1 |
| Flurry of Blows | Monk | bonus action, 1 ki | two Martial Arts strikes |
| Patient Defense | Monk | bonus action, 1 ki | applies dodge state until next turn |
| Step of the Wind | Monk | bonus action, 1 ki | grants clean escape setup, may apply Emboldened 1 |
| Lay on Hands | Paladin | action | heal up to 5 HP per use from remaining pool |
| Divine Smite | Paladin | attack rider, 4 MP on hit | adds `2d8` radiant on a weapon hit |
| Channel Divinity | Cleric level 2+ | action, 1 use | `2d8` radiant, applies Stunned 1 |
| Cunning Action | Rogue level 2+ | bonus action | hide for Invisible 2 on success, or create flee opening |
| Help a Downed Ally | any hero | action | Medicine check DC `10`; on success target returns at 1 HP, on failure target stabilizes |

### Spell timing rule

- If a bonus-action spell is cast, the turn blocks non-cantrip action spells
- If a leveled action spell is cast, the turn blocks bonus-action spellcasting
- Cantrip-style attacks like Fire Bolt, Sacred Flame, Produce Flame, Vicious Mockery, and Eldritch Blast remain available as actions

## Status Effects

| Status | Main effect |
| --- | --- |
| Surprised | loses turn once |
| Blinded | attack disadvantage, helps attackers hit, hurts some checks |
| Charmed | cannot make hostile actions |
| Deafened | hurts hearing-based Perception checks |
| Exhaustion | skill disadvantage at 1+, attack penalty at 2+, save disadvantage at 3+ |
| Frightened | general d20 disadvantage pressure |
| Grappled | blocks movement, attack disadvantage |
| Incapacitated | cannot act |
| Invisible | grants attack advantage until broken by hostile action |
| Paralyzed | cannot act, auto-fails STR/DEX saves |
| Petrified | cannot act, auto-fails STR/DEX saves, halves incoming damage |
| Poisoned | general d20 disadvantage pressure |
| Burning | takes `1d6` fire at end of turn |
| Acid-Burned | takes `1d4` acid at end of turn, `-1 AC` |
| Reeling | `-2 attack` |
| Prone | `-2 AC`, melee attackers gain advantage, ranged attackers take disadvantage |
| Restrained | `-2 AC`, attack disadvantage, blocks movement, DEX save disadvantage |
| Emboldened | `+2 attack`, `+1 saves` |
| Blessed | `+1 attack`, `+2 saves` |
| Guarded | `+1 AC` |
| Marked | enemy focus-fire hook; attacks against the target gain extra pressure in some archetypes |
| Bleeding | takes `1d4` bleeding damage at end of turn |
| Cursed | `-1 attack`, `-1 saves`, not marked combat-only |
| Resist Fire / Cold / Lightning / Poison | grants matching damage resistance |
| Stunned | cannot act |
| Unconscious | represented when current HP is 0 and not dead |

## Enemy-Independent Damage And Survival Rules

- Resistances halve incoming matching damage
- Temporary HP absorbs damage before current HP
- Effective armor class now accounts for both AC penalties and AC bonuses such as `Guarded`
- Fire resistance can come from Fire-Blooded ancestry or item/status resistance
- Poison resistance can come from Dwarf ancestry or item/status resistance
- Dropping a hero to 0 HP starts death-save state
- Hitting a hero already at 0 HP causes a death-save failure instead of normal HP loss
- Enemies die immediately at 0 HP
- After combat, living heroes at 0 HP recover to 1 HP automatically

### Death saves

- DC `10`
- Natural `1`: two failures
- Natural `20`: stand up at `1` HP
- `3` successes: stabilize at `0`
- `3` failures: die

## Items, Resting, And Inventory

### Shared inventory

- Inventory is party-shared
- Carrying capacity is computed from the party
- Weight and supply points are tracked
- Equipment can be assigned to any company member

### Resting

- Short rests per long rest: `2`
- Short rest:
  - heals each living party member for half maximum HP, rounded up
  - restores short-rest resources like Second Wind, Action Surge, Channel Divinity, and ki
  - restores half maximum MP, rounded up, for non-warlock MP users
  - restores all MP for Warlocks
  - Arcane Recovery and Natural Recovery still restore one hidden compatibility spell slot while combat casting uses MP
- Long rest:
  - costs `12` supply points
  - fully restores HP, MP, and other resources for living members
  - resets short rests to `2`
  - clears temporary combat conditions
  - reduces Exhaustion by `1`

### Consumable timing

- Drinking a healing potion yourself in combat is a bonus action
- Using an item on someone else in combat is an action
- Scroll of Revivify works at camp on dead companions only
- The current item implementation supports healing, temp HP, revive HP, MP restoration through former spell-slot-refresh items, poison cure, condition clearing, and condition application

### Item catalog

- The full generated item reference already lives in `information/catalogs/ITEM_CATALOG.md`
- Use that file for concrete weights, rarities, acquisition sources, weapon properties, armor entries, consumables, and scroll effects

## Notes For Debugging

- Many race and class feature tags are descriptive identifiers, while only a subset have hard-coded effects
- Enemy behavior is driven more by `archetype` checks than by generic feature tags
- Companion relationship bonuses stack into the same bonus channels used by gear and level progression
- A few Act 1 story systems now sit in `map_system.py` rather than classic linear scene files, including hidden-route unlocks, companion personal quests, and the ending-tier calculation
- Character creation stores a few legacy display names like `Healing Potion`, but active gameplay inventory uses normalized item ids like `potion_healing`
