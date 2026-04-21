# Leveling System Draft

Last updated: 2026-04-21

This document is a hybrid progression draft for the text-based Python DnD game. It takes its backbone from official Dungeons & Dragons 5e progression and uses Baldur's Gate 3 as the model for feat cadence, subclass timing, and class choice density.

This is intentionally written as an implementation-facing design note, not just lore. The goal is to make later coding work straightforward.

## Design Goals

- Extend progression from level 4 to level 8.
- Use the official D&D XP curve so levels feel earned.
- Keep party XP shared across the whole roster.
- Level all party members together when the shared threshold is reached.
- Let new companions auto-scale to the current party level on recruitment.
- Replace flat "+1 style" upgrades with real choice points: subclasses, feats, spells, passives, resources, and class actions.
- Use BG3-style feat selection at levels 4 and 8.
- Keep the system deep, but still implementable in a text game.

## Reference Backbone

### Official D&D used for the backbone

- Character advancement XP thresholds.
- Core class progression through level 8.
- Core spell lists through spell level 4.
- Core feature timing such as Extra Attack, subclass unlocks, Channel Divinity, Wild Shape, Metamagic, Invocations, and Arcane Tradition features.

### BG3 used for the game feel

- Feat menu and feat names.
- Subclass timing and subclass roster.
- Choice density on level-up.
- "Everyone gets a real build decision" philosophy.
- Shared-party feel where companions can stay relevant without falling behind.

## Core Party Rules

### Shared XP

- Keep one `party_xp` value for the whole save.
- When `party_xp` reaches a threshold, the player and all recruited companions gain the new level.
- This matches the current game's direction and keeps narrative party members from lagging behind.

### Simultaneous Level-Up

- When a threshold is hit, resolve level-up for the player, all active companions, and all camp companions.

Recommended order:

1. Raise everyone's level number.
2. Apply hit point gain.
3. Unlock new class resources and passive features.
4. Resolve subclass choice if the class reaches its subclass level and has no subclass yet.
5. Resolve new spells or class options.
6. Resolve feat choice if the level grants one.
7. Refill newly unlocked resources.

### New Companion Auto-Scaling

When a new companion joins:

1. Set `target_level = player.level`.
2. If the companion is below that level, auto-run every missed level-up.
3. Apply all missed HP gains, MP capacity, spell-slot compatibility data, class features, subclass features, feats, and passives.
4. Use a companion build template for automatic choices. Template fields should include preferred subclass, fighting style, cantrips, spell picks by level, feats, and invocations or metamagic.
5. After catch-up, fully restore HP and resources so the companion joins ready to use.

Recommended rule:

- Player-controlled protagonist gets manual choices.
- Story companions auto-pick from templates by default.
- Optional future camp feature: "review companion build" to let the player adjust them later.

## XP Thresholds: Level 1 to 8

These totals follow official D&D character advancement.

| Level | Total XP | XP Needed From Previous Level | Proficiency Bonus |
| --- | ---: | ---: | ---: |
| 1 | 0 | 0 | +2 |
| 2 | 300 | 300 | +2 |
| 3 | 900 | 600 | +2 |
| 4 | 2,700 | 1,800 | +2 |
| 5 | 6,500 | 3,800 | +3 |
| 6 | 14,000 | 7,500 | +3 |
| 7 | 23,000 | 9,000 | +3 |
| 8 | 34,000 | 11,000 | +3 |

Recommended code update:

```python
LEVEL_XP_THRESHOLDS = {
    1: 0,
    2: 300,
    3: 900,
    4: 2700,
    5: 6500,
    6: 14000,
    7: 23000,
    8: 34000,
}
```

## Level-Up Choice Rules

### Global Rules

- Levels 4 and 8 always offer a feat choice.
- The feat menu should include `Ability Improvement` as a standard option.
- Ability scores still cap at 20 unless a later system explicitly overrides that.
- Full casters should feel stronger at levels 3, 5, and 7 because those unlock new spell levels.
- Martial classes should feel stronger at level 5 because of Extra Attack.
- Subclasses should define build identity, not just grant a flat stat bump.

### Optional BG3 Parity Rules Worth Keeping

- Fighter gets an extra feat at level 6.
- Rogue gets an extra feat at level 10, which is outside the current cap.

## Subclass Unlock Timing

Use BG3 timing for subclass selection:

| Class | Subclass Choice Level |
| --- | ---: |
| Barbarian | 3 |
| Bard | 3 |
| Cleric | 1 |
| Druid | 2 |
| Fighter | 3 |
| Monk | 3 |
| Paladin | 3 |
| Ranger | 3 |
| Rogue | 3 |
| Sorcerer | 1 |
| Warlock | 1 |
| Wizard | 2 |

## Spellcasting Progression Templates

Current repo note: the live combat implementation now uses Magic Points (`MP`) for spell affordability and spending. The BG3 spell-slot material in this section remains useful for future spell-list, upcasting, and compatibility planning, but player-facing combat should check MP first.

Use BG3's spellcasting concept instead of a bespoke per-class slot table. This makes future class data cleaner and lines up with the way BG3 handles full casters, half casters, one-third casters, prepared casters, and warlocks.

### BG3 Spellcasting Concepts

- In official D&D and BG3, cantrips do not consume spell slots and can usually be cast at will. In this repo's current combat MVP, implemented combat cantrips cost `1 MP`.
- Most spell slots refresh on a long rest.
- Warlock Pact Magic slots refresh on a short or long rest.
- Casting a spell with a higher slot upcasts it if the spell supports scaling.
- Spells cast with higher slots count as the level of the slot spent, even if they gain no other benefit.

### BG3 Known And Prepared Spell Rules

- Known-spell casters in BG3: Bard, Ranger, Sorcerer, Warlock, Eldritch Knight, Arcane Trickster, and Wizard.
- Wizards are still special because they also learn extra spells by scribing scrolls.
- Prepared casters in BG3: Cleric, Druid, Paladin, and Wizard.
- Prepared spell count in BG3 is `spellcasting ability modifier + class level`, minimum 1.
- Always-prepared spells from class features, domains, or oaths should not count against prepared capacity.

### BG3 Effective Spellcaster Level

BG3 uses one universal Spellcasting slot table based on effective spellcaster level, or `ESL`.

- Full casters use `ESL = class level`.
- Half casters use `ESL = ceil(class level / 2)`.
- One-third casters use `ESL = ceil(class level / 3)`.
- If multiclassing is ever added later, BG3 sums the fractional spellcaster levels from each Spellcasting class and rounds the total down.

### BG3 Universal Spellcasting Slot Table

This table is copied from BG3's general spellcasting rules and then trimmed to the current level-8 target.

| ESL | 1st | 2nd | 3rd | 4th |
| --- | ---: | ---: | ---: | ---: |
| 1 | 2 | 0 | 0 | 0 |
| 2 | 3 | 0 | 0 | 0 |
| 3 | 4 | 2 | 0 | 0 |
| 4 | 4 | 3 | 0 | 0 |
| 5 | 4 | 3 | 2 | 0 |
| 6 | 4 | 3 | 3 | 0 |
| 7 | 4 | 3 | 3 | 1 |
| 8 | 4 | 3 | 3 | 2 |

### Single-Class BG3 Slot Outcomes For This Project

| Class Type | Levels 1-8 ESL Mapping | Resulting Highest Spell Slot By Level 8 |
| --- | --- | --- |
| Full caster | 1, 2, 3, 4, 5, 6, 7, 8 | 4th |
| Half caster | 1, 1, 2, 2, 3, 3, 4, 4 | 2nd |
| One-third caster | 0, 0, 1, 2, 2, 2, 3, 3 | 2nd |

### BG3 Pact Magic Progression

Warlocks do not use the universal spellcasting slot table. They use Pact Magic.

- Pact slots are always the highest spell level the warlock can currently cast.
- Pact slots refresh on a short rest.
- Warlock spells are automatically upcast to the current pact slot level.

| Warlock Level | Pact Slots | Pact Slot Level |
| --- | ---: | ---: |
| 1 | 1 | 1 |
| 2 | 2 | 1 |
| 3 | 2 | 2 |
| 4 | 2 | 2 |
| 5 | 2 | 3 |
| 6 | 2 | 3 |
| 7 | 2 | 4 |
| 8 | 2 | 4 |

### Recommended Implementation Rule

For future spell-list and upcasting work, keep deriving slot-style compatibility data by slot level, for example:

```python
spell_slots = {1: 4, 2: 3, 3: 2, 4: 0}
```

Then derive those values from:

- `class_name`
- `level`
- `subclass`
- `is_warlock`

This is cleaner than adding `+1 spell slot` on every level-up, because it keeps the data in line with BG3 and avoids drift when companions auto-scale to party level. Runtime combat should still spend MP through `dnd_game/gameplay/magic_points.py`.

## BG3 Feat Catalog

All classes can choose one feat at levels 4 and 8. Fighter should also get a level 6 feat if we want closer BG3 parity.

The effects below are paraphrased for implementation notes.

| Feat | BG3-style effect summary | Notes / prerequisite |
| --- | --- | --- |
| Ability Improvement | Increase one ability by 2, or two abilities by 1, up to 20. | Core fallback option. |
| Actor | +1 CHA, gain Expertise in Deception and Performance. | If not proficient, also gain proficiency first. |
| Alert | +5 Initiative and cannot be Surprised. | Great universal passive. |
| Athlete | +1 STR or DEX, stand from Prone with much less movement, jump farther. | Mobility feat. |
| Charger | Gain charge attacks that let you rush in for a boosted melee hit or shove without provoking during the rush. | Strong gap-closing action. |
| Crossbow Expert | No melee-range penalty on crossbow attacks; Piercing Shot inflicts a longer wound effect. | Best for ranged weapon builds. |
| Defensive Duellist | Use Reaction to add proficiency bonus to AC against a melee hit while wielding a finesse weapon. | Requires DEX 13. |
| Dual Wielder | Dual-wield non-Light one-handed melee weapons and gain +1 AC while dual-wielding. | Does not grant the Two-Weapon Fighting style by itself. |
| Dungeon Delver | Advantage on Perception against hidden objects and on saves versus traps; gain trap damage resistance. | Exploration feat. |
| Durable | +1 CON and recover to full HP on short rest. | Very strong sustain in a text game. |
| Elemental Adept | Pick one damage type; your spells ignore resistance to it and 1s on that damage roll are treated as 2s. | Acid, Cold, Fire, Lightning, or Thunder in BG3. |
| Great Weapon Master | Bonus attack after a crit or kill; optional -5 attack / +10 damage toggle with two-handed or fully two-handed versatile weapons. | Premium heavy-weapon feat. |
| Heavily Armoured | +1 STR and gain Heavy Armour proficiency. | Requires Medium Armour proficiency. |
| Heavy Armour Master | +1 STR and reduce incoming non-magical physical damage by 3 while in heavy armour. | Requires Heavy Armour proficiency. |
| Lightly Armoured | +1 STR or DEX and gain Light Armour proficiency. | Good for robe users who want armor access. |
| Lucky | Gain 3 Luck Points per long rest to improve attacks, checks, saves, or force an enemy reroll. | Strong universal feat. |
| Mage Slayer | Advantage on saves against nearby enemy spells, Reaction attack against close-range casters, and better concentration breaking on hit. | Anti-caster melee feat. |
| Magic Initiate: Bard | Learn 2 Bard cantrips and 1 Bard level-1 spell castable once per long rest, using CHA. | Separate BG3 feat entry. |
| Magic Initiate: Cleric | Learn 2 Cleric cantrips and 1 Cleric level-1 spell castable once per long rest, using WIS. | Separate BG3 feat entry. |
| Magic Initiate: Druid | Learn 2 Druid cantrips and 1 Druid level-1 spell castable once per long rest, using WIS. | Separate BG3 feat entry. |
| Magic Initiate: Sorcerer | Learn 2 Sorcerer cantrips and 1 Sorcerer level-1 spell castable once per long rest, using CHA. | Separate BG3 feat entry. |
| Magic Initiate: Warlock | Learn 2 Warlock cantrips and 1 Warlock level-1 spell castable once per long rest, using CHA. | Separate BG3 feat entry. |
| Magic Initiate: Wizard | Learn 2 Wizard cantrips and 1 Wizard level-1 spell castable once per long rest, using INT. | Separate BG3 feat entry. |
| Martial Adept | Learn 2 Battle Master maneuvers and gain 1 Superiority Die that refreshes on short or long rest. | Great on Fighters and martial hybrids. |
| Medium Armour Master | Medium armour no longer hurts Stealth, and medium armour can use up to +3 DEX to AC. | Requires Medium Armour proficiency. |
| Mobile | +10 ft movement, Dash ignores difficult terrain, and melee attacks let you move away from that target without provoking. | Great for skirmishers. |
| Moderately Armoured | +1 STR or DEX and gain Medium Armour and Shield proficiency. | Requires Light Armour proficiency. |
| Performer | +1 CHA and gain Musical Instrument proficiency. | Flavorful, weaker combat feat. |
| Polearm Master | Bonus-action butt-end strike with spear, quarterstaff, pike, halberd, or glaive; opportunity attack when enemies enter reach. | Strong area control feat. |
| Resilient | +1 to one ability and gain proficiency in that ability's saving throws. | Flexible defensive feat. |
| Ritual Caster | Learn 2 ritual spells. BG3 ritual pool: Enhance Leap, Disguise Self, Find Familiar, Longstrider, Speak with Animals, Speak with Dead. | Strong utility feat. |
| Savage Attacker | Roll melee weapon damage dice twice and keep the higher result. | Straightforward damage boost. |
| Sentinel | Reaction attack when a nearby enemy hits an ally, stop movement on successful opportunity attack, and gain advantage on opportunity attacks. | Premium control feat. |
| Sharpshooter | Ignore low-ground penalty on ranged attacks and optionally take -5 attack for +10 damage. | Best ranged DPR feat. |
| Shield Master | +2 DEX saves while using a shield and Reaction to greatly reduce spell damage from DEX-save effects. | Defensive tank feat. |
| Skilled | Gain proficiency in 3 skills of choice. | Strong out-of-combat utility. |
| Spell Sniper | Learn 1 attack cantrip and lower the spell critical threshold by 1. | BG3 version differs from tabletop. |
| Tavern Brawler | +1 STR or CON; add STR twice to attack and damage with unarmed attacks, improvised weapons, and thrown objects. | Excellent for thrown builds and monks. |
| Tough | Gain +2 maximum HP per level. | Simple durability feat. |
| War Caster | Advantage on concentration saves and can cast Shocking Grasp as an opportunity attack. | BG3-specific OA behavior. |
| Weapon Master | +1 STR or DEX and gain proficiency with 4 weapon types. | Flexible but usually lower impact. |

## Class Progression Draft: Level 1 to 8

The tables below are the recommended gameplay-facing progression model.

### Barbarian

BG3 subclass roster: Berserker, Wildheart, Wild Magic, Giant

| Level | Gains | Player Choices |
| --- | --- | --- |
| 1 | Rage, Unarmoured Defence | None |
| 2 | Reckless Attack, Danger Sense | None |
| 3 | Subclass, Rage charge +1 | Choose subclass |
| 4 | Feat | Choose feat / Ability Improvement |
| 5 | Extra Attack, Fast Movement | None |
| 6 | Subclass feature, Rage charge +1 | Automatic subclass package |
| 7 | Feral Instinct | None |
| 8 | Feat | Choose feat / Ability Improvement |

Core import tokens:

- `rage`
- `rage_charges`
- `unarmoured_defence_barbarian`
- `reckless_attack`
- `danger_sense`
- `extra_attack`
- `fast_movement`
- `feral_instinct`

### Bard

BG3 subclass roster: College of Glamour, College of Lore, College of Swords, College of Valour

| Level | Gains | Player Choices |
| --- | --- | --- |
| 1 | Spellcasting, Bardic Inspiration | Choose cantrips and level-1 spells |
| 2 | Jack of All Trades, Song of Rest | Choose one new spell if using known-spell progression |
| 3 | Subclass, Expertise, level-2 spells | Choose subclass and new spell |
| 4 | Feat | Choose feat / Ability Improvement |
| 5 | Font of Inspiration, Bardic Inspiration improves, level-3 spells | Choose new spell |
| 6 | Countercharm, subclass feature | Choose subclass package if needed |
| 7 | Level-4 spells | Choose new spell |
| 8 | Feat | Choose feat / Ability Improvement |

Core import tokens:

- `bard_spellcasting`
- `bardic_inspiration`
- `jack_of_all_trades`
- `song_of_rest`
- `expertise_bard`
- `font_of_inspiration`
- `countercharm`

### Cleric

BG3 subclass roster: Death, Knowledge, Life, Light, Nature, Tempest, Trickery, War

| Level | Gains | Player Choices |
| --- | --- | --- |
| 1 | Spellcasting, Divine Domain, domain feature | Choose domain, cantrips, prepared spells |
| 2 | Channel Divinity | Prepare spells |
| 3 | Level-2 spells | Prepare spells |
| 4 | Feat | Choose feat / Ability Improvement |
| 5 | Destroy Undead, level-3 spells | Prepare spells |
| 6 | Channel Divinity improvement, domain feature | Prepare spells |
| 7 | Level-4 spells | Prepare spells |
| 8 | Feat, Divine Strike or Potent Spellcasting depending domain | Choose feat / Ability Improvement |

Core import tokens:

- `cleric_spellcasting`
- `divine_domain`
- `channel_divinity`
- `destroy_undead`
- `divine_strike`
- `potent_spellcasting`

### Druid

BG3 subclass roster: Circle of the Land, Circle of the Moon, Circle of the Spores, Circle of the Stars

| Level | Gains | Player Choices |
| --- | --- | --- |
| 1 | Spellcasting | Choose cantrips and prepared spells |
| 2 | Wild Shape, subclass | Choose subclass and prepared spells |
| 3 | Level-2 spells | Prepare spells |
| 4 | Feat, Wild Shape improvement | Choose feat / Ability Improvement |
| 5 | Level-3 spells | Prepare spells |
| 6 | Subclass feature | Automatic subclass package |
| 7 | Level-4 spells | Prepare spells |
| 8 | Feat, Wild Shape improvement | Choose feat / Ability Improvement |

Core import tokens:

- `druid_spellcasting`
- `wild_shape`
- `wild_shape_charges`
- `circle_of_the_land`
- `circle_of_the_moon`
- `circle_of_the_spores`
- `circle_of_the_stars`

### Fighter

BG3 subclass roster: Arcane Archer, Battle Master, Champion, Eldritch Knight

| Level | Gains | Player Choices |
| --- | --- | --- |
| 1 | Second Wind, Fighting Style | Choose Fighting Style |
| 2 | Action Surge | None |
| 3 | Subclass | Choose subclass |
| 4 | Feat | Choose feat / Ability Improvement |
| 5 | Extra Attack | None |
| 6 | Feat | Choose feat / Ability Improvement |
| 7 | Subclass feature | Automatic subclass package |
| 8 | Feat | Choose feat / Ability Improvement |

Core import tokens:

- `second_wind`
- `fighting_style`
- `action_surge`
- `extra_attack`
- `battle_master_superiority_dice`
- `eldritch_knight_spellcasting`
- `champion_improved_critical`
- `arcane_archer_arcane_shots`

### Monk

BG3 subclass roster: Way of the Drunken Master, Way of the Four Elements, Way of the Open Hand, Way of Shadow

| Level | Gains | Player Choices |
| --- | --- | --- |
| 1 | Martial Arts, Unarmoured Defence, Flurry of Blows | None |
| 2 | Ki, Patient Defence, Step of the Wind, Unarmoured Movement | None |
| 3 | Deflect Missiles, subclass | Choose subclass |
| 4 | Feat, Slow Fall | Choose feat / Ability Improvement |
| 5 | Extra Attack, Stunning Strike, martial arts damage increase | None |
| 6 | Ki-Empowered Strikes, subclass feature | Automatic subclass package |
| 7 | Evasion, Stillness of Mind | None |
| 8 | Feat | Choose feat / Ability Improvement |

Core import tokens:

- `martial_arts`
- `unarmoured_defence_monk`
- `ki_points`
- `flurry_of_blows`
- `patient_defence`
- `step_of_the_wind`
- `deflect_missiles`
- `slow_fall`
- `extra_attack`
- `stunning_strike`
- `ki_empowered_strikes`
- `evasion`
- `stillness_of_mind`

### Paladin

BG3 subclass roster: Oath of Devotion, Oath of the Ancients, Oath of the Crown, Oath of Vengeance. Oathbreaker should be treated as a special unlock rather than a normal pick.

| Level | Gains | Player Choices |
| --- | --- | --- |
| 1 | Lay on Hands, Divine Sense, subclass oath in BG3 character creation style | Choose oath if using BG3 start flow |
| 2 | Fighting Style, Spellcasting, Divine Smite | Choose Fighting Style and spells |
| 3 | Divine Health, Sacred Oath feature, Channel Oath | Choose oath if not chosen at level 1 |
| 4 | Feat | Choose feat / Ability Improvement |
| 5 | Extra Attack, level-2 spells | Choose spells |
| 6 | Aura of Protection | None |
| 7 | Oath feature | Automatic subclass package |
| 8 | Feat | Choose feat / Ability Improvement |

Core import tokens:

- `lay_on_hands`
- `divine_sense`
- `paladin_spellcasting`
- `divine_smite`
- `fighting_style`
- `divine_health`
- `channel_oath`
- `extra_attack`
- `aura_of_protection`

### Ranger

BG3 subclass roster: Beast Master, Gloom Stalker, Hunter, Swarmkeeper

| Level | Gains | Player Choices |
| --- | --- | --- |
| 1 | Favoured Enemy, Natural Explorer | Choose one Favoured Enemy and one Natural Explorer |
| 2 | Fighting Style, Spellcasting | Choose Fighting Style and first spells |
| 3 | Subclass, improved spell progression | Choose subclass and new spell |
| 4 | Feat | Choose feat / Ability Improvement |
| 5 | Extra Attack, level-2 spells | Choose new spell |
| 6 | Additional Favoured Enemy and Natural Explorer | Choose second Favoured Enemy and second Natural Explorer |
| 7 | Subclass feature | Automatic subclass package |
| 8 | Feat, Land's Stride style mobility bonus if desired | Choose feat / Ability Improvement |

Core import tokens:

- `favoured_enemy`
- `natural_explorer`
- `ranger_spellcasting`
- `fighting_style`
- `extra_attack`
- `beast_companion`
- `gloom_stalker_dread_ambusher`
- `hunters_prey`
- `swarmkeeper_swarm`

### Rogue

BG3 subclass roster: Arcane Trickster, Assassin, Swashbuckler, Thief

| Level | Gains | Player Choices |
| --- | --- | --- |
| 1 | Sneak Attack, Expertise | Choose Expertise skills |
| 2 | Cunning Action | None |
| 3 | Subclass, Sneak Attack improves to 2d6 | Choose subclass |
| 4 | Feat | Choose feat / Ability Improvement |
| 5 | Uncanny Dodge, Sneak Attack 3d6 | None |
| 6 | Expertise again | Choose more Expertise skills |
| 7 | Evasion, Sneak Attack 4d6 | None |
| 8 | Feat | Choose feat / Ability Improvement |

Core import tokens:

- `sneak_attack`
- `expertise_rogue`
- `cunning_action`
- `uncanny_dodge`
- `evasion`
- `arcane_trickster_spellcasting`
- `assassinate`
- `fast_hands`
- `swashbuckler_dirty_tricks`

### Sorcerer

BG3 subclass roster: Draconic Bloodline, Shadow Magic, Storm Sorcery, Wild Magic

| Level | Gains | Player Choices |
| --- | --- | --- |
| 1 | Spellcasting, Sorcerous Origin | Choose origin, cantrips, spells |
| 2 | Font of Magic, Sorcery Points | Choose new spell if using known-spell progression |
| 3 | Metamagic, level-2 spells | Choose 2 Metamagic options and new spell |
| 4 | Feat | Choose feat / Ability Improvement |
| 5 | Level-3 spells | Choose new spell |
| 6 | Origin feature | Automatic subclass package |
| 7 | Level-4 spells | Choose new spell |
| 8 | Feat | Choose feat / Ability Improvement |

Core import tokens:

- `sorcerer_spellcasting`
- `sorcerous_origin`
- `font_of_magic`
- `sorcery_points`
- `metamagic`
- `draconic_resilience`
- `wild_magic_surge`
- `storm_flight`
- `shadow_eyes`

### Warlock

BG3 subclass roster: The Archfey, The Fiend, The Great Old One, The Hexblade

| Level | Gains | Player Choices |
| --- | --- | --- |
| 1 | Pact Magic, Patron feature | Choose patron, cantrips, spells |
| 2 | Eldritch Invocations | Choose 2 invocations |
| 3 | Pact Boon, level-2 pact slots | Choose Pact of the Blade, Chain, or Tome plus a new spell |
| 4 | Feat | Choose feat / Ability Improvement |
| 5 | Invocation, level-3 pact slots | Choose 1 invocation and 1 spell |
| 6 | Patron feature | Automatic subclass package |
| 7 | Invocation, level-4 pact slots | Choose 1 invocation and 1 spell |
| 8 | Feat | Choose feat / Ability Improvement |

Core import tokens:

- `warlock_spellcasting`
- `pact_magic`
- `eldritch_invocations`
- `pact_boon`
- `fiend_dark_ones_blessing`
- `great_old_one_mortal_reminder`
- `archfey_fey_presence`
- `hexblade_hex_warrior`

### Wizard

BG3 subclass roster: Abjuration, Bladesinging, Conjuration, Divination, Enchantment, Evocation, Illusion, Necromancy, Transmutation

| Level | Gains | Player Choices |
| --- | --- | --- |
| 1 | Spellcasting, Arcane Recovery, Spell Scribing | Choose cantrips and spellbook |
| 2 | Arcane Tradition | Choose school |
| 3 | Level-2 spells | Learn new spells |
| 4 | Feat | Choose feat / Ability Improvement |
| 5 | Level-3 spells | Learn new spells |
| 6 | Arcane Tradition feature | Automatic subclass package |
| 7 | Level-4 spells | Learn new spells |
| 8 | Feat | Choose feat / Ability Improvement |

Core import tokens:

- `wizard_spellcasting`
- `arcane_recovery`
- `spell_scribing`
- `arcane_tradition`
- `abjuration_ward`
- `divination_portent`
- `evocation_sculpt_spells`
- `bladesong`

## Ability and Passive Import Checklist

These are the first-pass abilities, actions, reactions, resources, and passives worth importing into data files later.

### Martial and General

- `extra_attack`
- `fighting_style_archery`
- `fighting_style_defence`
- `fighting_style_duelling`
- `fighting_style_great_weapon_fighting`
- `fighting_style_protection`
- `fighting_style_two_weapon_fighting`
- `feat_choice`
- `ability_improvement`

### Barbarian

- `rage`
- `reckless_attack`
- `danger_sense`
- `fast_movement`
- `feral_instinct`

### Bard

- `bardic_inspiration`
- `jack_of_all_trades`
- `song_of_rest`
- `expertise_bard`
- `font_of_inspiration`
- `countercharm`

### Cleric

- `channel_divinity`
- `turn_undead`
- `destroy_undead`
- `divine_strike`
- `potent_spellcasting`

### Druid

- `wild_shape`
- `wild_shape_bear`
- `wild_shape_cat`
- `wild_shape_wolf`
- `wild_shape_spider`
- `wild_shape_dire_raven`
- `combat_wild_shape`
- `symbiotic_entity`

### Fighter

- `second_wind`
- `action_surge`
- `superiority_die`
- `battle_manoeuvre`
- `improved_critical`
- `weapon_bond`
- `war_magic`

### Monk

- `ki_points`
- `flurry_of_blows`
- `patient_defence`
- `step_of_the_wind`
- `deflect_missiles`
- `slow_fall`
- `stunning_strike`
- `ki_empowered_strikes`
- `stillness_of_mind`

### Paladin

- `lay_on_hands`
- `divine_sense`
- `divine_smite`
- `channel_oath`
- `aura_of_protection`
- `oath_feature`

### Ranger

- `favoured_enemy_choice`
- `natural_explorer_choice`
- `hunters_mark_support`
- `beast_companion`
- `dread_ambusher`
- `hunters_prey`
- `swarmkeeper_swarm`

### Rogue

- `sneak_attack_melee`
- `sneak_attack_ranged`
- `cunning_action_dash`
- `cunning_action_disengage`
- `cunning_action_hide`
- `uncanny_dodge`
- `evasion`
- `fast_hands`
- `assassinate`

### Sorcerer

- `sorcery_points`
- `metamagic_quickened`
- `metamagic_twinned`
- `metamagic_heightened`
- `metamagic_distant`
- `metamagic_extended`
- `wild_magic_surge`
- `draconic_resilience`

### Warlock

- `eldritch_invocation`
- `agonizing_blast`
- `repelling_blast`
- `devils_sight`
- `book_of_ancient_secrets`
- `pact_of_the_blade`
- `pact_of_the_chain`
- `pact_of_the_tome`

### Wizard

- `arcane_recovery`
- `spell_scribing`
- `abjuration_ward`
- `portent`
- `sculpt_spells`
- `bladesong`

## Spell Reference Pools

This is the recommended first implementation pool for levels 1 to 8. It is not the entire tabletop catalog. It is the shortlist most useful for a text game that still wants class identity.

### Bard Spell Pool

- Cantrips: `Vicious Mockery`, `Minor Illusion`, `Mage Hand`, `Light`, `Prestidigitation`, `Message`
- 1st level: `Bane`, `Charm Person`, `Cure Wounds`, `Faerie Fire`, `Feather Fall`, `Healing Word`, `Heroism`, `Sleep`, `Thunderwave`
- 2nd level: `Blindness/Deafness`, `Detect Thoughts`, `Enhance Ability`, `Heat Metal`, `Hold Person`, `Invisibility`, `Knock`, `Lesser Restoration`, `Shatter`, `Silence`, `Suggestion`
- 3rd level: `Bestow Curse`, `Dispel Magic`, `Fear`, `Glyph of Warding`, `Hypnotic Pattern`, `Major Image`, `Speak with Dead`
- 4th level: `Confusion`, `Dimension Door`, `Freedom of Movement`, `Greater Invisibility`, `Polymorph`

### Cleric Spell Pool

- Cantrips: `Guidance`, `Light`, `Resistance`, `Sacred Flame`, `Spare the Dying`, `Thaumaturgy`
- 1st level: `Bless`, `Command`, `Cure Wounds`, `Guiding Bolt`, `Healing Word`, `Inflict Wounds`, `Sanctuary`, `Shield of Faith`
- 2nd level: `Aid`, `Blindness/Deafness`, `Hold Person`, `Lesser Restoration`, `Prayer of Healing`, `Protection from Poison`, `Silence`, `Spiritual Weapon`, `Warding Bond`
- 3rd level: `Animate Dead`, `Beacon of Hope`, `Daylight`, `Dispel Magic`, `Glyph of Warding`, `Mass Healing Word`, `Remove Curse`, `Revivify`, `Spirit Guardians`
- 4th level: `Banishment`, `Death Ward`, `Freedom of Movement`, `Guardian of Faith`, `Locate Creature`

### Druid Spell Pool

- Cantrips: `Druidcraft`, `Guidance`, `Poison Spray`, `Produce Flame`, `Resistance`, `Shillelagh`
- 1st level: `Cure Wounds`, `Entangle`, `Faerie Fire`, `Fog Cloud`, `Goodberry`, `Healing Word`, `Longstrider`, `Speak with Animals`, `Thunderwave`
- 2nd level: `Barkskin`, `Flame Blade`, `Flaming Sphere`, `Heat Metal`, `Moonbeam`, `Pass without Trace`, `Spike Growth`
- 3rd level: `Call Lightning`, `Daylight`, `Dispel Magic`, `Plant Growth`, `Protection from Energy`, `Sleet Storm`, `Speak with Plants`, `Wind Wall`
- 4th level: `Blight`, `Conjure Woodland Beings`, `Freedom of Movement`, `Ice Storm`, `Polymorph`, `Stoneskin`, `Wall of Fire`

### Paladin Spell Pool

- 1st level: `Bless`, `Command`, `Cure Wounds`, `Divine Favor`, `Heroism`, `Shield of Faith`
- 2nd level: `Aid`, `Branding Smite`, `Lesser Restoration`, `Magic Weapon`, `Protection from Poison`, `Zone of Truth`

### Ranger Spell Pool

- 1st level: `Cure Wounds`, `Fog Cloud`, `Goodberry`, `Hunter's Mark`, `Longstrider`, `Speak with Animals`
- 2nd level: `Barkskin`, `Darkvision`, `Lesser Restoration`, `Pass without Trace`, `Silence`, `Spike Growth`

### Sorcerer Spell Pool

- Cantrips: `Fire Bolt`, `Ray of Frost`, `Shocking Grasp`, `Mage Hand`, `Minor Illusion`, `Poison Spray`, `Prestidigitation`
- 1st level: `Burning Hands`, `Chromatic Orb` if added later, `Feather Fall`, `Mage Armor`, `Magic Missile`, `Shield`, `Sleep`, `Thunderwave`
- 2nd level: `Blur`, `Darkness`, `Hold Person`, `Invisibility`, `Mirror Image`, `Misty Step`, `Scorching Ray`, `Shatter`, `Web`
- 3rd level: `Blink`, `Counterspell`, `Fireball`, `Fly`, `Haste`, `Hypnotic Pattern`, `Lightning Bolt`, `Slow`
- 4th level: `Banishment`, `Blight`, `Dimension Door`, `Greater Invisibility`, `Ice Storm`, `Polymorph`, `Wall of Fire`

### Warlock Spell Pool

- Cantrips: `Eldritch Blast`, `Chill Touch`, `Mage Hand`, `Minor Illusion`, `Poison Spray`, `Prestidigitation`
- 1st level: `Charm Person`, `Hellish Rebuke`, `Protection from Evil and Good`
- 2nd level: `Darkness`, `Hold Person`, `Invisibility`, `Mirror Image`, `Misty Step`, `Shatter`, `Suggestion`
- 3rd level: `Counterspell`, `Fear`, `Fly`, `Hypnotic Pattern`, `Major Image`, `Vampiric Touch`
- 4th level: `Banishment`, `Blight`, `Dimension Door`

### Wizard Spell Pool

- Cantrips: `Fire Bolt`, `Ray of Frost`, `Shocking Grasp`, `Mage Hand`, `Minor Illusion`, `Prestidigitation`, `Light`
- 1st level: `Burning Hands`, `Detect Magic`, `Disguise Self`, `Feather Fall`, `Find Familiar`, `Grease`, `Mage Armor`, `Magic Missile`, `Shield`, `Sleep`, `Thunderwave`
- 2nd level: `Blur`, `Darkvision`, `Detect Thoughts`, `Flaming Sphere`, `Hold Person`, `Invisibility`, `Knock`, `Levitate`, `Mirror Image`, `Misty Step`, `Scorching Ray`, `Web`
- 3rd level: `Animate Dead`, `Blink`, `Counterspell`, `Dispel Magic`, `Fear`, `Fireball`, `Fly`, `Glyph of Warding`, `Haste`, `Hypnotic Pattern`, `Lightning Bolt`, `Slow`
- 4th level: `Arcane Eye`, `Banishment`, `Confusion`, `Dimension Door`, `Fire Shield`, `Greater Invisibility`, `Ice Storm`, `Polymorph`, `Stoneskin`, `Wall of Fire`

### Eldritch Knight Borrowed Spell Pool

- Cantrips: `Fire Bolt`, `Ray of Frost`, `Shocking Grasp`, `True Strike`
- 1st level: `Magic Missile`, `Shield`, `Thunderwave`, `Burning Hands`
- 2nd level: `Blur`, `Mirror Image`, `Misty Step`, `Scorching Ray`

### Arcane Trickster Borrowed Spell Pool

- Cantrips: `Mage Hand`, `Minor Illusion`, `Ray of Frost`
- 1st level: `Disguise Self`, `Charm Person`, `Sleep`, `Mage Armor`
- 2nd level: `Invisibility`, `Mirror Image`, `Hold Person`, `Misty Step`

## Recommended Companion Build Templates

These are suggested default auto-picks so companions can scale instantly without asking the player ten questions in a row.

### Auto-pick priorities

- Martial frontline: durability feat first, then damage feat.
- Ranged martial: accuracy or ranged damage feat first.
- Full caster: casting stat feat first, then concentration or utility.
- Support companion: healing or control spells before niche utility.

### Suggested feat preferences by archetype

- Barbarian: `Great Weapon Master`, `Tough`, `Savage Attacker`, `Alert`
- Fighter: `Great Weapon Master`, `Sharpshooter`, `Polearm Master`, `Alert`
- Monk: `Tavern Brawler`, `Mobile`, `Alert`, `Tough`
- Paladin: `Great Weapon Master`, `War Caster`, `Tough`, `Alert`
- Ranger: `Sharpshooter`, `Alert`, `Mobile`, `Ability Improvement`
- Rogue: `Alert`, `Mobile`, `Lucky`, `Ability Improvement`
- Bard: `Ability Improvement`, `War Caster`, `Alert`, `Lucky`
- Cleric: `War Caster`, `Ability Improvement`, `Resilient`, `Alert`
- Druid: `War Caster`, `Ability Improvement`, `Alert`, `Resilient`
- Sorcerer: `Ability Improvement`, `War Caster`, `Alert`, `Spell Sniper`
- Warlock: `Ability Improvement`, `Spell Sniper`, `Alert`, `War Caster`
- Wizard: `Ability Improvement`, `War Caster`, `Alert`, `Lucky`

## Suggested Data Model Additions

Add or refactor these fields on `Character` later:

- `subclass: str`
- `feats: list[str]`
- `passives: list[str]`
- `actions: list[str]`
- `bonus_actions: list[str]`
- `reactions: list[str]`
- `spellbook: list[str]`
- `known_spells: list[str]`
- `prepared_spells: list[str]`
- `cantrips: list[str]`
- `fighting_style: str`
- `invocations: list[str]`
- `metamagic: list[str]`
- `pact_boon: str`
- `resource_progression: dict[str, int]`
- `build_template_id: str`
- `level_choice_log: list[dict[str, str]]`

## Suggested Implementation Order

### Phase 1

- Extend XP thresholds to 8.
- Add feat support.
- Add subclass field.
- Add a generic choice resolver for level-up.

### Phase 2

- Replace the current static level 2 to 4 feature table with per-class level 1 to 8 progression data.
- Add or maintain MP synchronization plus spell-slot compatibility templates.
- Add spell list data files.

### Phase 3

- Add companion build templates.
- Add recruit-time catch-up leveling.
- Add camp review and respec style interface later if desired.

## Concrete Notes For This Repo

- The current game already uses shared party XP, which is the right foundation.
- The biggest missing pieces are subclass state, feats, spell selection, and class-specific choice tracking.
- The current `CLASS_LEVEL_PROGRESSION` data should eventually become a deeper structure with fields such as `level`, `features`, `resource_changes`, `subclass_choice`, `feat_choice`, `spell_choice`, `prepared_spell_cap`, `known_spell_delta`, `cantrip_delta`, and `choice_templates`.

Recommended future shape:

```python
CLASS_LEVEL_PROGRESSION["Wizard"][5] = {
    "features": ["level_3_spells"],
    "spell_slot_progression": {"1": 4, "2": 3, "3": 2},
    "mp_progression": "full_caster",
    "spell_choice": {"learn": 2, "max_spell_level": 3},
}
```

## References

- Official D&D Basic Rules (2014) classes: https://www.dndbeyond.com/sources/dnd/basic-rules-2014/classes
- Official D&D Basic Rules spells: https://www.dndbeyond.com/sources/dnd/basic-rules-2014/spells
- Official D&D character advancement table: https://www.dndbeyond.com/sources/dnd/br-2024/creating-a-character
- BG3 feat list: https://bg3.wiki/wiki/Feats
- BG3 spell system overview: https://bg3.wiki/wiki/Spells
- BG3 Warlock class page for Pact Magic progression: https://bg3.wiki/wiki/Warlock
- BG3 class pages used for subclass rosters and class timing:
- https://bg3.wiki/wiki/Barbarian
- https://bg3.wiki/wiki/Bard
- https://bg3.wiki/wiki/Cleric
- https://bg3.wiki/wiki/Druid
- https://bg3.wiki/wiki/Fighter
- https://bg3.wiki/wiki/Monk
- https://bg3.wiki/wiki/Paladin
- https://bg3.wiki/wiki/Ranger
- https://bg3.wiki/wiki/Rogue
- https://bg3.wiki/wiki/Sorcerer
- https://bg3.wiki/wiki/Warlock
- https://bg3.wiki/wiki/Wizard
