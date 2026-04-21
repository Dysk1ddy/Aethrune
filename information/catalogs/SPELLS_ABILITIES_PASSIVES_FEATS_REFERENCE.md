# Spells, Abilities, Passives, And Feats Reference

Last updated: 2026-04-21

This document is a mechanical reference for the level-1-to-8 progression draft. It is written for implementation work in this repo, not for player-facing rulebook text.

Important note:

- Spell and feature text below is paraphrased from official D&D Basic Rules material and BG3 reference pages.
- I am intentionally not reproducing long rules text verbatim.
- Where tabletop D&D and BG3 differ, I call that out in a `BG3 note`.
- The scope here is the content most useful for this game's level-8 roadmap: the BG3 feat list, the core class abilities and passives that matter through level 8, and a high-priority spell pool for implementation.
- Current repo adaptation: implemented combat spells now spend Magic Points (`MP`) instead of player-facing spell slots. The spell-slot tables below remain BG3/backbone references for future spell-list and upcasting work.

## Source Backbone

### Official D&D sources used

- D&D Beyond Basic Rules (2014) class rules
- D&D Beyond Basic Rules (2014) spell rules and spell entries

### BG3 sources used

- BG3 feat list
- BG3 spell system page
- BG3 class pages for spell progression and class-feature timing
- BG3 action pages for selected class actions and passives

## Core Spellcasting Rules

### Shared Concepts

- Cantrips are level-0 spells and normally do not consume spell slots in D&D/BG3. In the current repo combat MVP, implemented combat cantrips cost `1 MP`.
- Spell attacks use `d20 + proficiency bonus + spellcasting ability modifier`.
- Spell save DC is normally `8 + proficiency bonus + spellcasting ability modifier`.
- Concentration only supports one active concentration spell at a time.
- Taking damage can break concentration with a Constitution saving throw against DC 10 or half the damage taken, whichever is higher.
- Long rests normally restore spell slots in the reference rules; in the current repo they also refill MP.
- Warlock pact slots also refresh on short rest in BG3; in the current repo, warlocks refill all MP on short rest.
- Upcasting uses a higher-level spell slot to strengthen a spell if the spell supports scaling. MP-based upcasting is not implemented yet.

### BG3 Known And Prepared Spell Model

| Casting model | Classes | Rule |
| --- | --- | --- |
| Known spells | Bard, Ranger, Sorcerer, Warlock, Eldritch Knight, Arcane Trickster, Wizard | Learn spells on level-up. Most can replace one known spell on level-up. |
| Prepared spells | Cleric, Druid, Paladin, Wizard | Prepare a subset of available spells outside combat. |
| Prepared count | Cleric, Druid, Paladin, Wizard | `spellcasting ability modifier + class level`, minimum 1. |
| Always prepared | Domain, oath, subclass, race, or feature-granted spells | Do not count against prepared capacity. |

### BG3 Effective Spellcaster Level

BG3 uses a universal spell-slot table for classes with the `Spellcasting` feature.

| Caster type | BG3 rule |
| --- | --- |
| Full caster | `ESL = class level` |
| Half caster | `ESL = ceil(class level / 2)` |
| One-third caster | `ESL = ceil(class level / 3)` |
| Multiclass spellcasting | Sum the fractional spellcaster levels from Spellcasting classes, then round the total down |

### BG3 Universal Spellcasting Slot Table

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

### BG3 Pact Magic

| Warlock level | Pact slots | Slot level | Refresh |
| --- | ---: | ---: | --- |
| 1 | 1 | 1 | Short or long rest |
| 2 | 2 | 1 | Short or long rest |
| 3 | 2 | 2 | Short or long rest |
| 4 | 2 | 2 | Short or long rest |
| 5 | 2 | 3 | Short or long rest |
| 6 | 2 | 3 | Short or long rest |
| 7 | 2 | 4 | Short or long rest |
| 8 | 2 | 4 | Short or long rest |

Key behavior:

- Warlocks do not use the normal Spellcasting slot table for their class slots.
- Warlock spells are cast at the current pact-slot level.
- This means lower-level warlock spells are automatically upcast when possible.

## Class Resource Scaling To Level 8

This section condenses the class-resource information most useful for implementation. Unless noted otherwise, values below are the BG3 model. Where D&D tabletop differs, that is called out in the notes.

### Martial And Hybrid Resource Tables

| Class / resource | L1 | L2 | L3 | L4 | L5 | L6 | L7 | L8 | Rest refresh | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| Barbarian Rage Charges | 2 | 2 | 3 | 3 | 3 | 4 | 4 | 4 | Long rest | BG3 rage adds +2 damage through level 8 and forbids spellcasting/concentration while raging. |
| Bardic Inspiration Charges | 3 | 3 | 3 | 3 | 4 | 4 | 4 | 5 | Long rest until level 5, then short rest | Bardic Inspiration die is `d6` until level 4, `d8` at levels 5-9. |
| Cleric Channel Divinity Charges | 0 | 1 | 1 | 1 | 1 | 2 | 2 | 2 | Short or long rest | Domain actions also spend these charges. |
| Druid Wild Shape Charges | 0 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | Short rest | Base BG3 druid uses 2 charges per short rest; Circle of the Moon upgrades action economy and forms. |
| Fighter Second Wind | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | Short rest | Heals `1d10 + fighter level`. |
| Fighter Action Surge | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | Short rest | Grants one additional action. |
| Monk Ki Points | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | Short rest | BG3 monks start with ki at level 1, unlike 2014 tabletop monks. |
| Paladin Lay on Hands Charges | 3 | 3 | 3 | 4 | 4 | 4 | 4 | 4 | Long rest | BG3 differs from tabletop pool math. Each charge heals `2 x paladin level`. Cure disease/poison costs 2 charges. |
| Paladin Channel Oath Charges | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | Short or long rest | Oath actions use this pool. |
| Rogue Sneak Attack Dice | 1d6 | 1d6 | 2d6 | 2d6 | 3d6 | 3d6 | 4d6 | 4d6 | Per turn / per round timing | BG3 allows direct-use actions and post-hit reactions; it effectively refreshes once per round. |
| Sorcery Points | 0 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | Long rest | Used for Metamagic and spell-slot conversion. |
| Warlock Invocations Known | 0 | 2 | 2 | 2 | 3 | 3 | 4 | 4 | Permanent choices | BG3 invocations are normally fixed unless the character is respecced. |

### Prepared Spell Capacity

| Class | Prepared spell rule in BG3 | Notes |
| --- | --- | --- |
| Cleric | `cleric level + WIS modifier`, minimum 1 | Domain spells are always prepared and should not consume capacity. |
| Druid | `druid level + WIS modifier`, minimum 1 | Circle spells or feature spells should not consume capacity. |
| Paladin | `paladin level + CHA modifier`, minimum 1 | Oath spells are always prepared and should not consume capacity. |
| Wizard | `wizard level + INT modifier`, minimum 1 | Wizard also learns extra spells through scribing, then prepares a subset. |

### Known Spell Progression Notes

| Class | BG3 model through level 8 |
| --- | --- |
| Bard | Starts with 4 spells known at level 1 and generally gains 1 additional known spell each level through 8. |
| Sorcerer | Starts with 2 spells known at level 1 and reaches 9 known spells by level 8. |
| Warlock | Starts with 2 spells known at level 1 and gains 1 additional known spell per level through 8. |
| Ranger | Known-spell half-caster progression; learns slowly and benefits from careful curation. |
| Eldritch Knight / Arcane Trickster | One-third caster progression with restricted school access early on. |

## Common Combat Conditions Referenced In This File

| Condition / state | Gameplay meaning |
| --- | --- |
| Advantage | Roll two d20s and use the higher result. |
| Disadvantage | Roll two d20s and use the lower result. |
| Concentration | You can maintain only one concentration spell at a time; taking damage can break it. |
| Charmed | Usually cannot target the charmer with attacks or harmful abilities and is vulnerable to charm synergy effects. |
| Frightened | Often imposes disadvantage and prevents moving closer to the fear source. |
| Paralysed | The creature is incapacitated, fails STR/DEX saves, attack rolls against it have advantage, and nearby hits can crit. |
| Stunned | The creature is incapacitated, cannot move, automatically fails STR/DEX saves, and attacks against it have advantage. |
| Invisible | Attack rolls against the creature have disadvantage and its own attacks often gain advantage until invisibility breaks. |
| Surprised | Loses opening-tempo options at the start of combat. BG3 feat text often references immunity to Surprise rather than tabletop surprise rounds. |
| Difficult Terrain | Movement costs extra distance. |
| Opportunity Attack | A reaction strike when a hostile creature leaves melee reach unless prevented by a feature or spell. |

## BG3 Feats Detailed Reference

| Feat | Type | Action economy | Detailed mechanics | Notes |
| --- | --- | --- | --- | --- |
| Ability Improvement | Passive | Passive | Increase one ability score by 2, or two ability scores by 1, to a maximum of 20. | Core fallback feat. |
| Actor | Passive | Passive | +1 CHA. Gain Expertise in Deception and Performance. | If the character lacks proficiency, BG3 also grants proficiency first. |
| Alert | Passive | Passive | +5 Initiative and immunity to being Surprised. | Excellent universal feat. |
| Athlete | Passive | Passive | +1 STR or DEX, reduced movement cost to stand from Prone, and 50% more jump distance. | Mobility feat. |
| Charger | Activated feat | Action plus Bonus Action | Rush up to 30 ft without provoking from the target you collide with, then make a boosted melee strike or shove. Weapon version adds +5 damage. | Counts as a single weapon attack. |
| Crossbow Expert | Passive | Passive | Crossbow attacks do not suffer disadvantage in melee range. Improves Piercing Shot by lengthening Gaping Wounds. | Best on ranged weapon users. |
| Defensive Duellist | Reaction feat | Reaction | While wielding a proficient finesse weapon, add proficiency bonus to AC against a melee attack that would hit. | Requires DEX 13. |
| Dual Wielder | Passive | Passive | Allows two-weapon fighting with non-Light one-handed melee weapons and grants +1 AC while dual-wielding. | Does not grant the Two-Weapon Fighting style. |
| Dungeon Delver | Passive | Passive | Advantage on Perception checks to detect hidden objects, advantage on saves against traps, and resistance to trap damage. | Exploration-heavy feat. |
| Durable | Passive | Passive | +1 CON and recover to full hit points on short rest. | Strong survivability feat in a rest-driven game. |
| Elemental Adept | Passive | Passive | Choose Acid, Cold, Fire, Lightning, or Thunder. Spells of that type ignore resistance, and 1s on that damage are treated as 2s. | Great on focused blasters. |
| Great Weapon Master | Passive plus toggle | Passive, Bonus Action on proc, toggle on attack | Bonus-action melee attack after a crit or kill. Toggleable All In applies -5 to hit and +10 damage with two-handed or fully two-handed versatile weapons. | One of BG3's best melee DPR feats. |
| Heavily Armoured | Passive | Passive | +1 STR and Heavy Armour proficiency. | Requires Medium Armour proficiency. |
| Heavy Armour Master | Passive | Passive | +1 STR and reduce non-magical bludgeoning, piercing, and slashing damage by 3 while wearing heavy armour. | Requires Heavy Armour proficiency. |
| Lightly Armoured | Passive | Passive | +1 STR or DEX and Light Armour proficiency. | Helps robe users pivot into armour. |
| Lucky | Resource feat | Special resource use | Gain 3 Luck Points per long rest for advantage on attacks, checks, or saves, or to force an enemy reroll on an attack. | Strong universal utility feat. |
| Mage Slayer | Passive plus Reaction | Reaction against nearby caster | Advantage on saves against spells cast by creatures within melee range, Reaction attack against a close-range caster, and disadvantage on enemy concentration saves you trigger by hitting them. | Anti-mage melee feat. |
| Magic Initiate: Bard | Spell feat | Passive spell access | Learn 2 Bard cantrips and 1 Bard level-1 spell castable once per long rest with CHA. | Same structure as the other Magic Initiate feats. |
| Magic Initiate: Cleric | Spell feat | Passive spell access | Learn 2 Cleric cantrips and 1 Cleric level-1 spell castable once per long rest with WIS. |  |
| Magic Initiate: Druid | Spell feat | Passive spell access | Learn 2 Druid cantrips and 1 Druid level-1 spell castable once per long rest with WIS. |  |
| Magic Initiate: Sorcerer | Spell feat | Passive spell access | Learn 2 Sorcerer cantrips and 1 Sorcerer level-1 spell castable once per long rest with CHA. |  |
| Magic Initiate: Warlock | Spell feat | Passive spell access | Learn 2 Warlock cantrips and 1 Warlock level-1 spell castable once per long rest with CHA. |  |
| Magic Initiate: Wizard | Spell feat | Passive spell access | Learn 2 Wizard cantrips and 1 Wizard level-1 spell castable once per long rest with INT. |  |
| Martial Adept | Resource feat | Passive plus manoeuvre actions | Learn 2 Battle Master manoeuvres and gain 1 Superiority Die that refreshes on short or long rest. | Great on Fighters, Paladins, and Rangers. |
| Medium Armour Master | Passive | Passive | Medium armour no longer imposes Stealth disadvantage, and the DEX-to-AC cap rises from +2 to +3. | Requires Medium Armour proficiency. |
| Mobile | Passive | Passive | +10 ft movement, Dash ignores difficult terrain, and moving after a melee attack avoids that target's opportunity attack. | Premium skirmisher feat. |
| Moderately Armoured | Passive | Passive | +1 STR or DEX, Medium Armour proficiency, and Shield proficiency. | Requires Light Armour proficiency. |
| Performer | Passive | Passive | +1 CHA and Musical Instrument proficiency. | Flavor-heavy, lower combat impact. |
| Polearm Master | Passive plus Bonus Action | Bonus Action and Reaction | Bonus-action butt-end strike with glaive, halberd, pike, quarterstaff, or spear, plus opportunity attack when an enemy enters reach. | One of the strongest area-control feats. |
| Resilient | Passive | Passive | +1 to a chosen ability score and proficiency in that ability's saving throws. | Flexible defense feat. |
| Ritual Caster | Spell feat | Ritual casting outside combat | Learn 2 ritual spells. BG3 ritual options are Enhance Leap, Disguise Self, Find Familiar, Longstrider, Speak with Animals, and Speak with Dead. | Strong utility package. |
| Savage Attacker | Passive | Passive | Roll melee weapon damage dice twice and use the higher result. | Simple, reliable damage boost. |
| Sentinel | Passive plus Reaction | Reaction and opportunity attack rider | Reaction attack when a nearby enemy attacks an ally, stop movement when you land an opportunity attack, and gain advantage on opportunity attacks. | Premium tank/control feat. |
| Sharpshooter | Passive plus toggle | Passive and attack toggle | Ignore BG3 low-ground ranged penalty. Toggleable All In applies -5 to hit and +10 damage with proficient ranged weapons. | Core ranged DPR feat. |
| Shield Master | Passive plus Reaction | Reaction | +2 DEX saves while using a shield and a Reaction to reduce or negate DEX-save spell damage. | BG3 version differs from tabletop and is flatter. |
| Skilled | Passive | Passive | Gain proficiency in 3 skills of choice. | High utility feat. |
| Spell Sniper | Passive | Passive | Learn one attack cantrip and reduce spell critical threshold by 1. | BG3 version differs from tabletop and stacks. |
| Tavern Brawler | Passive | Passive | +1 STR or CON. Add STR twice to attack rolls and damage for unarmed attacks, improvised weapons, and thrown objects. | Extremely strong for monks and throw builds. |
| Tough | Passive | Passive | Gain +2 maximum HP per level. | Very clean durability feat. |
| War Caster | Passive plus Reaction | Reaction | Advantage on concentration saves and Reaction access to Shocking Grasp on a target leaving melee range. | Strong concentration feat for spellcasters. |
| Weapon Master | Passive | Passive | +1 STR or DEX and proficiency with 4 weapon types. | Flexible but lower impact than top-tier feats. |

## Core Class Abilities And Passives

These entries focus on the core actions, passives, and resources that matter for the level-1-to-8 system. Subclass-only features are called out where they define a build path, but this is not yet a full subclass encyclopedia.

### Barbarian

| Feature | Type | Cost / trigger | Recharge | Mechanical summary | BG3 note |
| --- | --- | --- | --- | --- | --- |
| Rage | Bonus action, resource | Bonus Action plus 1 Rage Charge | Long rest | Enter a battle frenzy for 10 turns. Gain resistance to bludgeoning, piercing, and slashing damage, advantage on STR checks and saving throws, and bonus melee damage. | BG3 rage also blocks spellcasting and concentration while active. |
| Reckless Attack | Attack rider | Declared on first melee attack of turn | None | Gain advantage on melee weapon attacks using STR this turn, but attacks against you gain advantage until your next turn. | Great for crit fishing. |
| Danger Sense | Passive | Passive | None | Advantage on DEX saves against visible effects while not blinded, deafened, or incapacitated. | Strong survival passive. |
| Extra Attack | Passive | When taking Attack action | None | Make 2 attacks instead of 1. | Core level-5 martial spike. |
| Fast Movement | Passive | Passive | None | Gain extra movement while not in heavy armour. | Use as a flat speed increase in text combat. |
| Feral Instinct | Passive | Passive | None | Improves initiative and makes it harder to be caught flat-footed at the start of combat. | In BG3, initiative bonuses are often easier to model than surprise clauses. |

### Bard

| Feature | Type | Cost / trigger | Recharge | Mechanical summary | BG3 note |
| --- | --- | --- | --- | --- | --- |
| Bardic Inspiration | Bonus action, resource | Bonus Action plus 1 Bardic Inspiration | Long rest before level 5, short rest from level 5 | At 60 ft, inspire an ally to add a bardic inspiration die to one attack roll, ability check, or saving throw. | Die starts at `1d6`, improves to `1d8` at bard level 5, and BG3 increases charge count as bard levels rise. |
| Jack of All Trades | Passive | Passive | None | Add half proficiency bonus to ability checks you are not proficient in. | Great for dialogue and exploration. |
| Song of Rest | Support feature | Out-of-combat support | Per rest cycle | Provides an extra short-rest style recovery window. | Easy to model as one bonus team recovery per day. |
| Expertise | Passive choice | Level-up choice | None | Double proficiency in selected skills. | Very important for social builds. |
| Font of Inspiration | Passive | Passive | None | Bardic Inspiration refreshes on short rest instead of long rest. | Big level-5 power spike. |
| Countercharm | Action or passive support | Action | Repeatable | Use performance magic to help nearby allies resist being charmed or frightened. | Best implemented as an ally buff that grants advantage against fear and charm effects in a short-radius aura. |

### Cleric

| Feature | Type | Cost / trigger | Recharge | Mechanical summary | BG3 note |
| --- | --- | --- | --- | --- | --- |
| Channel Divinity | Class resource | Usually Action | Short rest | Spend a Channel Divinity charge on domain powers or Turn Undead. | Resource should be tracked separately from spell slots. |
| Turn Undead | Action, resource | Action plus 1 Channel Divinity | Short rest | Undead in a nearby radius must make a WIS save or flee, losing the ability to meaningfully advance on the party. | Good template for crowd-control scenes. |
| Destroy Undead | Passive rider | Triggered through Turn Undead | None | Lower-CR undead destroyed instead of only turned. | Best implemented as a threshold kill rider on failed Turn Undead. |
| Divine Strike | Passive rider | Once per turn weapon hit | None | Add extra weapon damage, usually tied to the domain. | Domains may swap this for spell damage support. |
| Potent Spellcasting | Passive | Passive | None | Add spellcasting modifier to damage from cleric cantrips. | Domain-dependent alternative to Divine Strike. |

### Druid

| Feature | Type | Cost / trigger | Recharge | Mechanical summary | BG3 note |
| --- | --- | --- | --- | --- | --- |
| Wild Shape | Action, resource | Action plus 1 Wild Shape Charge | Short rest | Transform into a beast form with its own hit points, movement profile, attacks, and senses. The form ends when those hit points run out or the druid chooses to revert. | In BG3, basic forms unlock at level 2 and Moon druids get better combat forms. |
| Wild Shape Charges | Resource | Passive resource pool | Short rest | Tracks how many beast transformations remain. | Needs a dedicated resource, not spell slots. |
| Natural Recovery | Out-of-combat resource recovery | Out-of-combat action | Once per day or per rest depending on adaptation | Reference rules recover expended spell slots. Current MP MVP relies on normal short-rest MP recovery rather than extra MP. | Strong candidate for Circle of the Land support if druids need more pacing help later. |
| Combat Wild Shape | Bonus action variant | Bonus Action plus charge | Short rest | Faster, more battle-ready Wild Shape access. | Best reserved for Moon druid implementation. |
| Symbiotic Entity | Action, subclass resource rider | Action plus Wild Shape Charge | Short rest | Converts Wild Shape charges into temporary HP and fungal damage bonuses. | Strong Spores druid identity feature. |

### Fighter

| Feature | Type | Cost / trigger | Recharge | Mechanical summary | BG3 note |
| --- | --- | --- | --- | --- | --- |
| Fighting Style | Passive choice | Level-up choice | None | Pick a combat specialization such as Archery, Defence, Dueling, Great Weapon Fighting, Protection, or Two-Weapon Fighting. | Should be a level-up pick, not a static bonus baked into the class. |
| Second Wind | Bonus action, resource | Bonus Action plus 1 Second Wind | Short rest | Self-heal for `1d10 + fighter level`. | Great early sustain tool. |
| Action Surge | Free action spike, resource | Extra action burst | Short rest | Gain an additional action on your turn. | One of the defining fighter power moments. |
| Extra Attack | Passive | When taking Attack action | None | Make 2 attacks instead of 1. | Main level-5 power spike. |
| Battle Master manoeuvres | Resource actions | Maneuver cost plus Superiority Die | Short rest | Tactical weapon riders such as precision, push, trip, disarm, or riposte. | Great fit for a text game because each maneuver can be a named tactical option. |
| Champion Improved Critical | Passive | Passive | None | Weapon attacks crit on 19-20. | Easy low-complexity subclass feature. |
| Eldritch Knight spellcasting | Mixed feature | Uses spell slots | Long rest | Limited arcane casting on a fighter chassis. | Use the one-third caster slot progression. |

### Monk

| Feature | Type | Cost / trigger | Recharge | Mechanical summary | BG3 note |
| --- | --- | --- | --- | --- | --- |
| Martial Arts | Passive | Passive | None | Unarmed strikes and monk weapons use monk scaling and unlock bonus unarmed follow-ups. | Core monk identity. |
| Ki Points | Resource | Passive resource pool | Short rest | Fuels monk techniques. | Set total equal to monk level from level 2 onward. |
| Flurry of Blows | Bonus action, resource | Bonus Action plus 1 Ki | Short rest | Make extra unarmed strikes after attacking. | One of the monk's main damage tools. |
| Patient Defence | Bonus action, resource | Bonus Action plus 1 Ki | Short rest | Take a high-defense stance, usually Dodge-based. | Excellent survival option. |
| Step of the Wind | Bonus action, resource | Bonus Action plus 1 Ki | Short rest | Boost mobility, usually Dash or Disengage plus jump support. | Strong reposition tool. |
| Deflect Missiles | Reaction-style defense | Triggered when hit by ranged attack | None | Reduce ranged damage and sometimes throw the missile back. | Good candidate for a defensive reaction. |
| Slow Fall | Reaction-style passive | Triggered by falling | None | Reduce fall damage. | Mostly exploration utility unless vertical combat appears. |
| Stunning Strike | Attack rider, resource | On hit plus 1 Ki | Short rest | Add normal strike damage and force a CON save to avoid being Stunned. | BG3 exposes this as a dedicated attack action. |
| Ki-Empowered Strikes | Passive | Passive | None | Unarmed strikes count as magical. | Important against resistant enemies. |
| Evasion | Passive | Triggered by DEX save | None | Greatly reduce or negate damage from DEX-save effects. | Strong defensive spike. |
| Stillness of Mind | Active cleanse | Usually Action | Repeatable | End mental disruption such as fear or charm. | Can be simplified as a self-cleanse. |

### Paladin

| Feature | Type | Cost / trigger | Recharge | Mechanical summary | BG3 note |
| --- | --- | --- | --- | --- | --- |
| Lay on Hands | Action, healing resource | Action plus Lay on Hands charges | Long rest | Heal a target by spending charges, or spend 2 charges to cure disease or poison. | BG3 differs from tabletop pool math: charge count scales by class table and each charge heals `2 x paladin level`. |
| Divine Sense | Utility action | Action | Limited use | Detect certain supernatural presences. | Can be simplified into dialogue, scouting, or encounter intel. |
| Fighting Style | Passive choice | Level-up choice | None | Choose a martial specialization such as Defence, Dueling, Great Weapon Fighting, or Protection. | Same framework as fighter and ranger. |
| Divine Smite | Hit rider using MP in current repo | Trigger on melee weapon hit | Uses `4 MP` in current repo | Spend the resource after a hit to deal bonus radiant damage. Current implementation uses base `2d8`; reference rules gain `+1d8` for each slot level above 1 and another `+1d8` against fiends or undead. | Good candidate for future MP upcast tuning and crit spikes. |
| Divine Health | Passive | Passive | None | Immunity or strong resistance to disease. | Easy narrative passive. |
| Channel Oath | Resource actions | Usually Action plus 1 Channel Oath charge | Short rest | Oath-specific active powers. | Track separately from spell slots. |
| Aura of Protection | Passive aura | Passive | None | You and nearby allies gain a bonus to saving throws equal to the paladin's CHA modifier. | One of the strongest team passives in this level band; easiest text-game implementation is a 10-ft-style party aura. |

### Ranger

| Feature | Type | Cost / trigger | Recharge | Mechanical summary | BG3 note |
| --- | --- | --- | --- | --- | --- |
| Favoured Enemy | Passive choice | Character creation or level-up choice | None | Choose a prey specialty that grants utility, proficiencies, or combat perks. | BG3 implements this as a pick package, not just a lore tag. |
| Natural Explorer | Passive choice | Character creation or level-up choice | None | Choose terrain or wilderness training that grants resistances or utility tools. | BG3 also makes this a pick package. |
| Fighting Style | Passive choice | Level-up choice | None | Usually Archery, Defence, Dueling, or Two-Weapon Fighting. | Important early choice. |
| Ranger spellcasting | Spell feature | Uses MP in current repo once implemented | Long rest / MP recovery rules | Half-caster spell progression for tracking, scouting, and burst damage support. | Use BG3 half-caster ESL mapping for future spell-list work, then map combat costs to MP. |
| Beast Companion | Summon feature | Action or summon action | Persistent companion | Gain a controllable beast ally. | Strong subclass-defining feature for Beast Master. |
| Dread Ambusher | Passive combat opener | First round of combat | None | Initiative and opener burst package. | Great Gloom Stalker identity. |
| Hunter's Prey | Passive rider | Conditional on attacks | None | Gains specialized damage or anti-escape tools. | Hunter subclass identity anchor. |
| Swarmkeeper Swarm | Passive plus active rider | Triggered by attacks | None | Swarm adds movement, damage, or battlefield control effects. | Strong text-game flavor hook. |
| Extra Attack | Passive | When taking Attack action | None | Make 2 attacks instead of 1. | Core level-5 martial spike. |

### Rogue

| Feature | Type | Cost / trigger | Recharge | Mechanical summary | BG3 note |
| --- | --- | --- | --- | --- | --- |
| Sneak Attack | Damage rider | Once per turn on valid finesse or ranged hit | None | Add bonus precision damage when you attack with advantage or an ally meaningfully engages the target and you do not have disadvantage. | Track melee and ranged variants separately if needed. |
| Expertise | Passive choice | Level-up choice | None | Double proficiency in chosen skills. | Huge skill-identity feature. |
| Cunning Action | Bonus action toolkit | Bonus Action | Repeatable | Dash, Disengage, or Hide as a bonus action. | Big action-economy spike at level 2. |
| Assassin features | Passive opener | First turn or surprised target | None | Strong alpha-strike pattern. | Great low-complexity subclass if added. |
| Fast Hands | Passive action gain | Bonus Action economy | None | Gain more off-hand or item-tempo options. | Thief identity hook. |
| Uncanny Dodge | Reaction defense | Reaction on hit | Repeatable | Halve damage from one attacker that hits you. | One of the rogue's best defensive tools. |
| Evasion | Passive | Triggered by DEX save | None | Greatly reduce or negate damage from DEX-save effects. | Level-7 defense spike. |

### Sorcerer

| Feature | Type | Cost / trigger | Recharge | Mechanical summary | BG3 note |
| --- | --- | --- | --- | --- | --- |
| Sorcerous Origin | Subclass chassis | Level 1 choice | None | Defines bloodline or innate magic theme. | Should be chosen at level 1. |
| Font of Magic | Resource system | Passive resource pool | Long rest | Gain Sorcery Points used for metamagic and flexible casting. | Sorcery point count typically tracks sorcerer level. |
| Sorcery Points | Resource | Passive resource pool | Long rest | Reference rules convert into spell slots or spend on metamagic. | Important to track separately from MP and compatibility slots. |
| Metamagic | Spell modifier choices | Spend Sorcery Points when casting | Long rest via points | Modify spells with options such as Twinned, Quickened, Distant, Heightened, or Extended. | One of the biggest build-customization systems in the game. |
| Draconic Resilience | Passive | Passive | None | Improved durability and AC support. | Strong baseline for Draconic Bloodline. |
| Wild Magic Surge | Triggered wild effect | On spellcast under surge rules | Variable | Random magical side effects occur after certain casts. | Needs a surge table if implemented. |
| Storm Flight | Triggered movement | After casting certain spells | Repeatable | Short reposition or flight effect after spellcasting. | Useful Storm Sorcery mobility hook. |

### Warlock

| Feature | Type | Cost / trigger | Recharge | Mechanical summary | BG3 note |
| --- | --- | --- | --- | --- | --- |
| Pact Magic | Spell feature | Uses pact slots in BG3; MP in current repo | Short or long rest | Warlock slots are few, always at the highest available level, and always upcast warlock spells. Current repo models the short-rest identity by refilling all warlock MP on short rest. | Separate from normal Spellcasting slots; map future warlock spell costs into MP. |
| Eldritch Invocations | Passive or activated picks | Level-up choices | Varies | Choose passive boons or new castable powers such as Agonising Blast, Repelling Blast, Devil's Sight, Armour of Shadows, or Book of Ancient Secrets. | Very important customization system. |
| Agonising Blast | Passive invocation | Passive | None | Add CHA modifier to each Eldritch Blast beam's damage. | Signature damage upgrade. |
| Repelling Blast | Passive invocation | Trigger on Eldritch Blast hit | None | Push target on Eldritch Blast hit. | Great battlefield-control tool. |
| Devil's Sight | Passive invocation | Passive | None | See through magical and non-magical darkness. | Strong Darkness combo tool. |
| Pact Boon | Build-defining feature | Level 3 choice | None | Choose Pact of the Blade, Chain, or Tome, gaining a weapon-focused, familiar-focused, or spellbook-focused pact package. | Needs a major level-up choice screen. |
| Deepened Pact | Passive boon upgrade | Level 5 | None | Blade gains Extra Attack, Chain empowers familiar, Tome grants long-rest spells. | Strong level-5 identity spike. |

### Wizard

| Feature | Type | Cost / trigger | Recharge | Mechanical summary | BG3 note |
| --- | --- | --- | --- | --- | --- |
| Arcane Recovery | Out-of-combat recovery | Special action | Once per day / compatibility slot hook | Reference rules recover expended spell slots after combat. Current MP MVP does not grant extra MP beyond normal short-rest recovery. | Revisit only if wizard pacing feels too constrained. |
| Spell Scribing | Spellbook system | Spend scroll and gold if used | Permanent | Learn extra wizard spells from scrolls. | Very BG3-feeling system and worth preserving. |
| Arcane Tradition | Subclass chassis | Level 2 choice | None | Choose a wizard school such as Abjuration, Divination, Evocation, or Bladesinging. | Major build-defining choice. |
| Arcane Ward | Passive shield | Triggered by abjuration magic | Refreshed by abjuration casting | Generate and refresh a protective ward. | Strong Abjuration identity feature. |
| Portent | Resource / foreknowledge | Special roll replacement | Long rest | Replace d20 rolls using foreseen dice. | Big Divination identity feature. |
| Sculpt Spells | Passive | Triggered by evocation AoE | None | Allies can be protected from your own evocation blasts. | Great Evocation quality-of-life feature. |
| Bladesong | Bonus action, resource stance | Bonus Action | Limited uses | Enter a boosted melee-mage stance with bonuses to AC, speed, Acrobatics, and concentration support while not using heavy gear. | High-complexity but stylish subclass feature. |

## Choice Package References

These are the high-value sub-choices that repeatedly appear inside level-up flows and should be represented as data, not hard-coded text.

### Fighting Styles

| Fighting Style | Gameplay effect | Best users | Notes |
| --- | --- | --- | --- |
| Archery | `+2` to ranged weapon attack rolls. | Fighter, Ranger | Best pure ranged style. |
| Defence | `+1 AC` while wearing armour. | Fighter, Paladin, Ranger | Low-complexity, always useful. |
| Dueling | `+2` damage with a one-handed melee weapon when the other hand is empty. | Fighter, Paladin, Ranger | Strong sword-and-board or duelist style. |
| Great Weapon Fighting | Reroll 1s and 2s on damage dice for two-handed or versatile-two-handed melee weapons. | Fighter, Paladin | Best with large damage dice. |
| Protection | While using a shield, impose disadvantage on an attack made against a nearby ally. | Fighter, Paladin | Best on defensive frontliners. |
| Two-Weapon Fighting | Add ability modifier to off-hand melee damage. | Fighter, Ranger | Very important for dual-wield builds. |

### Metamagic

| Metamagic | Sorcery Point cost | Gameplay effect | Notes |
| --- | ---: | --- | --- |
| Distant Spell | 1 | Increase spell range and often convert touch spells into short-ranged spells. | Strong utility and safety pick. |
| Extended Spell | 1 | Double a spell's duration up to a limit. | Great on long buffs or control spells. |
| Heightened Spell | 3 | Impose disadvantage on the target's first saving throw against the spell. | Expensive, high-impact control tool. |
| Quickened Spell | 3 | Cast a spell that normally costs an action as a bonus action. | One of the strongest tempo tools in BG3. |
| Twinned Spell | Variable by spell level | Duplicate a single-target spell onto a second target when legal. | Very strong but restricted by spell targeting. |

### Common Warlock Invocations

| Invocation | Gameplay effect | Notes |
| --- | --- | --- |
| Agonising Blast | Add CHA modifier to each Eldritch Blast beam's damage. | Staple damage invocation. |
| Repelling Blast | Push targets struck by Eldritch Blast. | Great positioning and hazard combo tool. |
| Devil's Sight | See normally in darkness, including magical darkness. | Enables Darkness combos. |
| Armour of Shadows | Cast Mage Armor at will without spending a spell slot in reference rules. | If implemented under MP, decide whether this stays free as invocation utility. |
| Beguiling Influence | Gain proficiency in Deception and Persuasion. | Strong social invocation. |
| Book of Ancient Secrets | Gain ritual utility tied to Pact of the Tome. | Good long-form exploration support. |

### Signature Wild Shape Forms Worth Supporting Early

| Form | Role | Key gameplay value |
| --- | --- | --- |
| Cat | Scout / traversal | Small body, stealth utility, infiltration. |
| Wolf | Control skirmisher | Mobility plus knockdown or pack-style pressure. |
| Bear | Tank | High hit points and frontline durability. |
| Spider | Control | Web or poison pressure and climb fantasy. |
| Dire Raven | Scout / mobility | Flight and reposition utility. |
| Sabre-Toothed Tiger | Striker | Strong Moon druid combat form at the top of this project's current cap. |

## High-Priority Spell Reference

This section covers the spells most likely to matter for the first implementation pass. The `Mechanical summary` column follows official D&D spell behavior, while `BG3 note` highlights important game-specific differences or implementation cues.

### Cantrips

| Spell | Classes | Cast | Range | Conc. | Roll / save | Damage / healing | Mechanical summary | BG3 note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Guidance | Cleric, Druid | 1 action | Touch | Yes, up to 1 minute | None | None | Target adds `1d4` to one ability check before the spell ends. | Strong dialogue and exploration buff. |
| Vicious Mockery | Bard | 1 action | 60 ft | No | WIS save | `1d4` psychic at level 1 | On a failed save, target takes psychic damage and has disadvantage on its next attack roll before the end of its next turn. Damage scales by cantrip tier. | Excellent control cantrip for support bards. |
| Sacred Flame | Cleric | 1 action | 60 ft | No | DEX save | `1d8` radiant at level 1 | Radiant damage cantrip that ignores cover benefits. Damage scales by cantrip tier. | Reliable ranged cleric cantrip. |
| Fire Bolt | Sorcerer, Wizard, Eldritch Knight | 1 action | 120 ft | No | Spell attack | `1d10` fire at level 1 | Ranged attack cantrip that can ignite unattended flammable objects. Damage scales by cantrip tier. | Bread-and-butter ranged arcane cantrip. |
| Ray of Frost | Sorcerer, Wizard, Eldritch Knight, Arcane Trickster | 1 action | 60 ft | No | Spell attack | `1d8` cold at level 1 | On hit, deals cold damage and reduces target speed by 10 ft until the start of your next turn. Damage scales by cantrip tier. | Great soft control cantrip. |
| Shocking Grasp | Sorcerer, Wizard | 1 action | Touch | No | Spell attack | `1d8` lightning at level 1 | On hit, target cannot take reactions until its next turn. You have advantage if the target wears metal armour. Damage scales by cantrip tier. | Great disengage tool. |
| Eldritch Blast | Warlock | 1 action | 120 ft in D&D, 60 ft in BG3 | No | Spell attack | `1d10` force per beam | Signature warlock attack cantrip. Gains additional beams as the character levels. | At the level-8 cap, plan around the BG3 level-5 beam increase. |
| Mage Hand | Bard, Sorcerer, Warlock, Wizard, Arcane Trickster | 1 action | 30 ft | No | None | None | Summon a spectral hand for remote interaction and utility. | Treat as a utility spell rather than combat damage. |

### Level 1 Spells

| Spell | Classes | Cast | Range | Conc. | Roll / save | Damage / healing | Mechanical summary | BG3 note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Bless | Cleric, Paladin | 1 action | 30 ft | Yes, up to 1 minute | None | None | Up to 3 creatures add `1d4` to attack rolls and saving throws. Upcast adds 1 extra target per slot level above 1. | Excellent low-level party buff. |
| Cure Wounds | Bard, Cleric, Druid, Paladin, Ranger | 1 action | Touch | No | None | `1d8 + spellcasting modifier` healing | Direct single-target healing. Upcast adds `+1d8` healing per slot level above 1. | Stronger raw heal than Healing Word, but costs the main action. |
| Healing Word | Bard, Cleric, Druid | 1 bonus action | 60 ft | No | None | `1d4 + spellcasting modifier` healing | Fast ranged pick-up heal. Upcast adds `+1d4` healing per slot level above 1. | Best emergency revive tool at low levels. |
| Guiding Bolt | Cleric | 1 action | 120 ft | No | Spell attack | `4d6` radiant | On hit, the next attack roll against the target before the end of your next turn has advantage. Upcast adds `+1d6` per slot level above 1. | Huge early burst and setup spell. |
| Shield of Faith | Cleric, Paladin | 1 bonus action | 60 ft | Yes, up to 10 minutes | None | None | Grants `+2 AC` to a creature for the duration. | Great defensive concentration option. |
| Faerie Fire | Bard, Druid | 1 action | 60 ft | Yes, up to 1 minute | DEX save | None | Affected creatures and objects glow; attacks against affected creatures have advantage and invisibility is suppressed. | Excellent anti-stealth and setup spell. |
| Hunter's Mark | Ranger | 1 bonus action | 90 ft | Yes, up to 1 hour | None | `+1d6` weapon damage per hit | Mark a target. Your weapon hits deal extra damage, and you can move the mark when the target dies. | Core ranger damage rider. |
| Magic Missile | Sorcerer, Wizard, Eldritch Knight | 1 action | 120 ft | No | No attack roll, no save | `3 x (1d4 + 1)` force | Fires 3 darts that automatically hit. Upcast adds 1 extra dart per slot level above 1. | Reliable finisher and concentration breaker. |
| Shield | Sorcerer, Wizard, Eldritch Knight | 1 reaction | Self | No | Triggered when hit or targeted by Magic Missile | None | Gain `+5 AC` until the start of your next turn, including against the triggering attack, and negate Magic Missile. | One of the best defensive reactions in the game. |
| Thunderwave | Bard, Druid, Wizard | 1 action | Self, 15-ft cube | No | CON save | `2d8` thunder | Creatures in the area take thunder damage and are pushed 10 ft on a failed save, or half damage without the push on a success. Upcast adds `+1d8` per slot level above 1. | Good close-range emergency blast. |

### Level 2 Spells

| Spell | Classes | Cast | Range | Conc. | Roll / save | Damage / healing | Mechanical summary | BG3 note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Aid | Cleric, Paladin | 1 action | 30 ft | No | None | `+5` max HP and current HP to 3 targets | Increases both current and maximum hit points for 8 hours. Upcast adds `+5` HP per slot level above 2. | Great pre-fight buff and recovery spell. |
| Hold Person | Bard, Cleric, Sorcerer, Warlock, Wizard | 1 action | 60 ft | Yes, up to 1 minute | WIS save | None | Paralyse a humanoid on a failed save. The target repeats the save at the end of each turn. Upcast adds one additional humanoid target per slot level above 2. | One of the best single-target control spells. |
| Invisibility | Bard, Sorcerer, Warlock, Wizard, Arcane Trickster | 1 action | Touch | Yes, up to 1 hour | None | None | Makes a creature invisible until it attacks, casts a spell, or the spell ends. Upcast adds extra targets. | Key scouting and ambush spell. |
| Lesser Restoration | Bard, Cleric, Druid, Paladin, Ranger | 1 action | Touch | No | None | None | End one disease or one of these conditions on the target: blinded, deafened, paralysed, or poisoned. | Important status-cleanse spell. |
| Misty Step | Sorcerer, Warlock, Wizard | 1 bonus action | Self | No | None | None | Teleport up to 30 ft to an unoccupied space you can see. | Top-tier reposition spell. |
| Moonbeam | Druid | 1 action | 120 ft | Yes, up to 1 minute | CON save | `2d10` radiant | Summon a 5-ft-radius beam. Creatures take damage when entering it for the first time on a turn or starting their turn there. You can move the beam with an action. Upcast adds `+1d10` per slot level above 2. | Strong repeated damage zone. |
| Pass without Trace | Druid, Ranger | 1 action | Self, 30-ft aura | Yes, up to 1 hour | None | None | Chosen creatures in the aura gain `+10` to Stealth checks and leave no tracks. | Huge stealth and exploration tool. |
| Shatter | Bard, Sorcerer, Warlock, Wizard | 1 action | 60 ft | No | CON save | `3d8` thunder | Damaging burst in a 10-ft-radius sphere. Inorganic creatures have disadvantage on the save. Upcast adds `+1d8` per slot level above 2. | Great early AoE on non-fire builds. |
| Spiritual Weapon | Cleric | 1 bonus action | 60 ft | No | Melee spell attack | `1d8 + spellcasting modifier` force | Summon a floating weapon for 1 minute. It attacks when cast and can move and attack again with a bonus action on later turns. Upcast adds `+1d8` every 2 slot levels above 2. | Very efficient because it does not require concentration. |
| Spike Growth | Druid, Ranger | 1 action | 150 ft | Yes, up to 10 minutes | No initial save | `2d4` piercing per 5 ft moved | Creates hidden spiked ground in a 20-ft radius. The area becomes difficult terrain and moving through it deals repeated damage. | Excellent battlefield-control spell for a text game. |

### Level 3 Spells

| Spell | Classes | Cast | Range | Conc. | Roll / save | Damage / healing | Mechanical summary | BG3 note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Counterspell | Sorcerer, Warlock, Wizard | 1 reaction | 60 ft | No | Ability check for higher-level spells | None | Interrupt a creature casting a spell. Automatically stops spells of the same level or lower than the slot used; otherwise requires an ability check. | Essential anti-caster tool. |
| Fireball | Sorcerer, Wizard | 1 action | 150 ft | No | DEX save | `8d6` fire | Explodes in a 20-ft-radius sphere. Failed save takes full damage; successful save takes half. Upcast adds `+1d6` per slot level above 3. | The classic AoE benchmark. |
| Haste | Sorcerer, Wizard | 1 action | 30 ft | Yes, up to 1 minute | None | None | Doubles movement, grants `+2 AC`, advantage on DEX saves, and an extra action each turn. When it ends, the target becomes lethargic for a turn. | BG3's extra action is stronger than tabletop, so this spell may need careful balancing. |
| Hypnotic Pattern | Bard, Sorcerer, Warlock, Wizard | 1 action | 120 ft | Yes, up to 1 minute | WIS save | None | Creatures that fail become charmed, incapacitated, and reduced to speed 0 until shaken awake or damaged. | One of the best crowd-control spells in the game. |
| Mass Healing Word | Bard, Cleric | 1 bonus action | 60 ft | No | None | `1d4 + spellcasting modifier` healing to up to 6 creatures | Wide-area emergency recovery. Upcast adds `+1d4` per slot level above 3. | Great post-AoE stabilization tool. |
| Revivify | Cleric, Paladin | 1 action | Touch | No | None | Restores life to a creature dead for up to 1 minute | Returns a dead creature to life with 1 HP. | Critical campaign safety net. |
| Spirit Guardians | Cleric | 1 action | Self, 15-ft radius | Yes, up to 10 minutes | WIS save | `3d8` radiant or necrotic | Hostile creatures inside the aura are slowed and take damage when entering it or starting their turn there. Upcast adds `+1d8` per slot level above 3. | Signature cleric battlefield spell. |
| Call Lightning | Druid | 1 action | 120 ft | Yes, up to 10 minutes | DEX save | `3d10` lightning | Create a storm cloud and call lightning into a chosen point below it. You can repeat the bolt with later actions. Upcast adds `+1d10` per slot level above 3. | Great sustained AoE spell for druids. |

### Level 4 Spells

| Spell | Classes | Cast | Range | Conc. | Roll / save | Damage / healing | Mechanical summary | BG3 note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Banishment | Cleric, Sorcerer, Warlock, Wizard | 1 action | 60 ft | Yes, up to 1 minute | CHA save | None | Remove a target from the battlefield. Native extraplanar creatures can be permanently banished if concentration lasts the full duration. | Excellent boss-control tool. |
| Blight | Druid, Sorcerer, Warlock, Wizard | 1 action | 30 ft | No | CON save | `8d8` necrotic | Heavy single-target necrotic damage. Plant creatures take the damage especially badly. | Strong anti-bruiser nuke. |
| Dimension Door | Bard, Sorcerer, Warlock, Wizard | 1 action | 500 ft | No | None | None | Teleport yourself and optionally one willing creature to a destination in range. | Fantastic rescue and reposition spell. |
| Greater Invisibility | Bard, Sorcerer, Wizard | 1 action | Touch | Yes, up to 1 minute | None | None | The target stays invisible even after attacking or casting spells. | Great on rogues, archers, and blasters. |
| Polymorph | Bard, Druid, Sorcerer, Wizard | 1 action | 60 ft | Yes, up to 1 hour | WIS save | Beast-form hit-point buffer | Transform a creature into a beast form with the beast's statistics and hit points. The form ends when those hit points run out. | Can be used offensively or defensively. |
| Wall of Fire | Druid, Sorcerer, Wizard | 1 action | 120 ft | Yes, up to 1 minute | DEX save | `5d8` fire on major triggers | Create a damaging wall or ring of fire that punishes entering, ending turns on the hot side, or being caught when it appears. | Strong zone-control spell. |

## Additional Spell Details For The Wider Draft Pools

These are the next most important spells from the leveling draft's class pools. They are here so the reference file covers more of the actual implementation candidates, not just the first combat shortlist.

### Additional Level 1 Spells

| Spell | Classes | Cast | Range | Conc. | Roll / save | Damage / healing | Mechanical summary | BG3 note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Bane | Bard, Cleric, Warlock | 1 action | 30 ft | Yes, up to 1 minute | CHA save | None | Up to 3 creatures that fail the save subtract `1d4` from attack rolls and saving throws for the duration. Upcast adds 1 extra target per slot level above 1. | Excellent offensive debuff and inverse of Bless. |
| Command | Cleric, Paladin | 1 action | 60 ft | No | WIS save | None | Speak a one-word command such as Approach, Drop, Flee, Grovel, or Halt; the creature follows it on its next turn if it fails the save. Upcast can target additional creatures. | Great control spell for social and combat scenes. |
| Feather Fall | Bard, Sorcerer, Wizard | 1 reaction | 60 ft | No | Triggered by falling | None | Up to 5 falling creatures slow their descent and ignore most fall damage for 1 minute. | Mostly traversal and emergency utility. |
| Goodberry | Druid, Ranger | 1 action | Self | No | None | `10` berries healing `1` each | Create magical berries that each restore 1 HP and provide a day's nourishment. | Strong attrition-management spell if the game leans into travel. |
| Sleep | Bard, Sorcerer, Wizard, Arcane Trickster | 1 action | 90 ft | No | HP pool, no save | `5d8` total HP affected at 1st level | Creatures in a 20-ft-radius area fall asleep starting from the lowest current HP until the rolled pool is spent. Upcast adds `2d8` affected HP per slot level above 1. | Very strong at low levels, falls off later. |

### Additional Level 2 Spells

| Spell | Classes | Cast | Range | Conc. | Roll / save | Damage / healing | Mechanical summary | BG3 note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Detect Thoughts | Bard, Wizard | 1 action | Self | Yes, up to 1 minute | WIS save for deeper probe | None | Read surface thoughts, then optionally probe deeper into a creature's mind. | Very useful for dialogue-heavy content. |
| Heat Metal | Bard, Druid | 1 action | 60 ft | Yes, up to 1 minute | CON save for item handling pressure | `2d8` fire per trigger | Cause a metal object to glow red-hot, damaging the bearer and imposing weapon-drop or armour pressure. Reapply damage with a bonus action on later turns. Upcast adds `+1d8` per slot level above 2. | Excellent anti-armour or anti-weapon control spell. |
| Mirror Image | Sorcerer, Warlock, Wizard, Arcane Trickster | 1 action | Self | No | No save | None | Create 3 illusory duplicates that can cause attacks to miss you instead. | Strong non-concentration defense spell. |
| Silence | Bard, Cleric, Ranger | 1 action | 120 ft | Yes, up to 10 minutes | None | None | Create a 20-ft-radius sphere where sound cannot pass and many verbal spells cannot be cast. | High-value anti-caster zone. |
| Web | Sorcerer, Wizard, Eldritch Knight | 1 action | 60 ft | Yes, up to 1 hour | DEX save and repeated checks | None initial, fire-sensitive terrain | Fill an area with sticky webbing that restrains creatures and creates difficult terrain. The webs can burn. | Great battlefield-control spell. |

### Additional Level 3 Spells

| Spell | Classes | Cast | Range | Conc. | Roll / save | Damage / healing | Mechanical summary | BG3 note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Dispel Magic | Bard, Cleric, Druid, Sorcerer, Wizard | 1 action | 120 ft | No | Ability check for stronger effects | None | End one spell effect on a creature, object, or magical effect. Stronger effects may require a casting-ability check. | Important utility and anti-magic answer. |
| Fear | Bard, Sorcerer, Warlock, Wizard | 1 action | Self, 30-ft cone | Yes, up to 1 minute | WIS save | None | Targets that fail drop what they hold and become frightened, often forcing retreat behavior. | Great cone control spell. |
| Fly | Sorcerer, Warlock, Wizard | 1 action | Touch | Yes, up to 10 minutes | None | None | Grant a creature a flying speed for the duration. Upcast can target extra creatures. | Huge mobility and encounter-breaking potential. |
| Glyph of Warding | Bard, Cleric, Wizard | 1 action | Touch | No | DEX or appropriate save | `5d8` or status package | Inscribe a magical trap that explodes or inflicts a special control effect when triggered. Upcast adds `+1d8` per slot level above 3. | Better for ambush, prep, or encounter scripting than reactive combat. |
| Lightning Bolt | Sorcerer, Wizard | 1 action | Self, 100-ft line | No | DEX save | `8d6` lightning | Blast creatures in a long line. Failed save takes full damage; success takes half. Upcast adds `+1d6` per slot level above 3. | Linear alternative to Fireball. |

### Additional Level 4 Spells

| Spell | Classes | Cast | Range | Conc. | Roll / save | Damage / healing | Mechanical summary | BG3 note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Confusion | Bard, Wizard | 1 action | 90 ft | Yes, up to 1 minute | WIS save | None | Affected creatures behave erratically and may waste turns or lose reliable targeting. | High-chaos multi-target control. |
| Freedom of Movement | Bard, Cleric, Druid | 1 action | Touch | No | None | None | Target ignores many movement restraints, difficult terrain penalties, and magical slowing effects for 1 hour. | Great pre-boss or anti-control buff. |
| Ice Storm | Druid, Sorcerer, Wizard | 1 action | 300 ft | No | DEX save | `2d8` bludgeoning + `4d6` cold | Large-radius storm dealing mixed damage and leaving difficult terrain. | Good non-fire AoE that also shapes terrain. |

## Expansion Candidates

Useful next-wave spells if the system grows after the first implementation pass:

- Bane
- Command
- Detect Thoughts
- Goodberry
- Heat Metal
- Mirror Image
- Silence
- Fear
- Glyph of Warding
- Ice Storm
- Freedom of Movement
- Confusion

## Sources

- Official D&D Basic Rules classes: https://www.dndbeyond.com/sources/dnd/basic-rules-2014/classes
- Official D&D Basic Rules spells: https://www.dndbeyond.com/sources/dnd/basic-rules-2014/spells
- BG3 feat list: https://bg3.wiki/wiki/Feats
- BG3 spell system overview: https://bg3.wiki/wiki/Spells
- BG3 Warlock class page for Pact Magic progression: https://bg3.wiki/wiki/Warlock
- BG3 Bard class page for spell-slot and inspiration timing: https://bg3.wiki/wiki/Bard
- BG3 Wizard class page for prepared-spell and spellbook behavior: https://bg3.wiki/wiki/Wizard
- BG3 Wild Shape action page: https://bg3.wiki/wiki/Wild_Shape
- BG3 Stunning Strike action page: https://bg3.wiki/wiki/Stunning_Strike_%28Unarmed%29
