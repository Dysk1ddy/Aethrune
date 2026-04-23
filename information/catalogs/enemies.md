# Enemy Reference

This file documents every enemy archetype currently defined in the project, including fixed story enemies, optional background-prologue enemies, and post-combat random-encounter enemies.

The final section also includes a design appendix with proposed future enemies written to match the same reference style. Those appendix entries are concept-ready additions, not live archetypes wired into factories or encounter tables yet.

## Scope And Scan Notes

- Scanned sources:
  - `dnd_game/data/story/factories.py`
  - `dnd_game/gameplay/story_intro.py`
  - `dnd_game/gameplay/story_act1_expanded.py`
  - `dnd_game/gameplay/story_act2_scaffold.py`
  - `dnd_game/gameplay/random_encounters.py`
  - `dnd_game/gameplay/combat_flow.py`
  - `dnd_game/gameplay/combat_resolution.py`
  - `dnd_game/data/items/catalog.py`
  - `information/Story/ACT1_CONTENT_REFERENCE.md`
  - `information/Story/ACT2_CONTENT_REFERENCE.md`
- `android_port/` mirrors the same enemy factory roster and encounter structure; it does not add unique enemy archetypes.
- The `Design Expansion: 25 New Enemy Concepts` appendix at the end of this file is proposal content added for future implementation. Its archetypes are not part of the current scanned runtime roster.
- Gold below is the enemy's built-in `gold_value`, which is awarded on victory.
- Item drops below are probabilistic loot-table entries. If an enemy says "no item loot table", the code currently grants XP/gold only unless the scene also hands out a separate scripted reward.
- "Forced" means combat is part of the scene once you commit to it. "Potential" means it only appears in certain backgrounds, branch choices, party sizes, or failed random-encounter resolutions.

## Roster Summary

| Archetype | Display Name | Act | Typical Use |
| --- | --- | --- | --- |
| `goblin` | Scrapling Raider | Act 1 | road raiders, scavengers, prologue threats |
| `wolf` | Ashfang Hound | Act 1 | road beast, prologue threat, random encounters |
| `bandit` | Ashen Brand Cutter | Act 1 | human raider baseline |
| `bandit_archer` | Ashen Brand Marksman | Act 1 | ranged Ashen Brand support |
| `ash_brand_enforcer` | Ashen Brand Enforcer | Act 1 | anti-momentum bruiser that punishes buffed heroes |
| `ember_channeler` | Ember Channeler | Act 1 | support caster that paints focus-fire targets |
| `carrion_stalker` | Carrion Stalker | Act 1 | stealth predator used in Cinderfall and relay ambushes |
| `skeletal_sentry` | Skeletal Sentry | Act 1 | Old Owl Well and manor undead guards |
| `worg` | Ashfang Beast | Act 1 | Wyvern Tor and Ashfall support beast |
| `orc_raider` | Red Mesa Raider | Act 1 | Wyvern Tor and Ashfall muscle |
| `orc_bloodchief` | Mesa Warlord | Act 1 | Wyvern Tor miniboss base |
| `ogre_brute` | Hollow Giant | Act 1 | Wyvern Tor heavy support |
| `gravecaller` | Gravecaller | Act 1 | Old Owl Well miniboss base |
| `nothic` | Cistern Eye | Act 1 | Tresendar cistern horror |
| `rukhar` | Rukhar Cinderfang | Act 1 | Ashfall Watch miniboss |
| `varyn` | Varyn Sable | Act 1 | Emberhall final boss |
| `expedition_reaver` | Rival Expedition Reaver | Act 2 | expedition-rival muscle |
| `cult_lookout` | Quiet Choir Agent | Act 2 | ranged cult support |
| `choir_adept` | Quiet Choir Adept | Act 2 | cult caster / leader |
| `grimlock_tunneler` | Tunnel Scavenger | Act 2 | ambusher in tunnels and routes |
| `stirge_swarm` | Bloodmote Swarm | Act 2 | swarm nuisance in cramped spaces |
| `ochre_slime` | Corrosive Mass | Act 2 | chokepoint ooze |
| `animated_armor` | Meridian Sentinel | Act 2 | construct guardian |
| `spectral_foreman` | Spectral Foreman | Act 2 | undead command unit |
| `starblighted_miner` | Starblighted Miner | Act 2 | corrupted worker / whisper victim |
| `caldra_voss` | Sister Caldra Voss | Act 2 | final cult boss |

## Act 1 Enemies

### Scrapling Raider

- Archetype: `goblin`
- Base sheet: level 1, 6 HP, AC 13, Scimitar `1d4+1`, XP 50, Gold 4
- Tags and traits: `enemy`, `cowardly`, feature `nimble`
- Runtime behavior:
  - No dedicated active AI branch beyond basic attacks
  - `nimble` exists as flavor / feature data, but no special runtime hook is currently implemented
- Item drops:
  - `potion_healing` 35%
  - `scroll_revivify` 1%
  - `bread_round` 45%
  - `dagger_common` 20%
  - `leather_armor_common` 15%
- Encounter locations:
  - Forced or potential: `Camp at First Light` (Outlander prologue)
  - Forced or potential: `Wayside Pursuit` (Hermit prologue)
  - Forced: `Roadside Ambush` on the High Road
  - Potential: `Abandoned Cottage` -> `Cottage Squatters` or `Cellar Door Rush`
  - Potential: `Ruined Wayhouse` -> `Wayhouse Scavengers`, `Wayhouse Holdouts`, or `Trapdoor Drop`
- Named variants seen in content:
  - `Scrapling Cutthroat`
  - `Scrapling Scavenger`

### Ashfang Hound

- Archetype: `wolf`
- Base sheet: level 1, 11 HP, AC 13, Bite `1d6+1`, XP 50, Gold 6
- Tags and traits: `enemy`, `beast`, feature `pack_tactics`
- Runtime behavior:
  - Gains practical advantage when another enemy is still conscious
  - On hit, target makes STR save DC 11 or becomes `prone` for 1 round
- Item drops:
  - `dried_fish` 40%
  - `travel_biscuits` 25%
- Encounter locations:
  - Forced or potential: `Hospice Gate` (Acolyte prologue)
  - Forced or potential: `Camp at First Light` (Outlander prologue)
  - Forced: `Roadside Ambush`
  - Potential: `Lone Wolf at the Kill` -> `Hound on the Trail` or `Cornered Hound`
  - Potential: `Frightened Draft Horse` -> `Brush Stalker`

### Ashen Brand Cutter

- Archetype: `bandit`
- Base sheet: level 1, 11 HP, AC 12, Scimitar `1d6`, XP 50, Gold 8
- Tags and traits: `enemy`, `humanoid`, `parley`
- Runtime behavior:
  - On high hit roll (`18+`), target makes STR save DC 11 or becomes `grappled` for 1 round
- Item drops:
  - `potion_healing` 40%
  - `scroll_revivify` 2%
  - `frontier_ale` 50%
  - `shortsword_common` 20%
  - `leather_armor_common` 25%
  - `antitoxin_vial` 15%
- Encounter locations:
  - Forced or potential: `South Barracks Breakout` (Soldier prologue) as `Ashen Brand Runner`
  - Forced or potential: `Blacklake Warehouse` (Criminal prologue) as `Ashen Brand Collector`
  - Forced or potential: `Market Corner` (Charlatan prologue) as `Ashen Brand Fixer`
  - Forced: `Old Owl Well Dig Ring` as `Ashen Brand Fixer`
  - Forced: `Ashfall Gate`
  - Forced: `Ashfall Lower Barracks`
  - Forced or potential: `Miniboss: Rukhar Cinderfang` support enemy
  - Forced: `Tresendar Cellars` as `Ashen Brand Collector`
  - Forced: `Emberhall Antechamber` as `Ashen Brand Fixer` / `Ashen Brand Guard`
  - Potential random fights:
    - `Chest Scavengers`
    - `Road Toll Collectors`
    - `Toll Line Standoff`
    - `Snare-Line Ambushers`
    - `Smuggler Camp`
    - `Smuggler Panic`
    - `Returning Scavengers`
    - `Returning Campers`
    - `Milestone Scavengers`

### Ashen Brand Marksman

- Archetype: `bandit_archer`
- Base sheet: level 1, 9 HP, AC 12, Shortbow `1d6`, XP 50, Gold 9
- Tags and traits: `enemy`, `humanoid`, `parley`
- Runtime behavior:
  - `snare_shot` once: DEX save DC 12 or `restrained` for 2 rounds
  - `ash_shot` once: DEX save DC 12 or `blinded` for 1 round
- Item drops:
  - `moonmint_drops` 35%
  - `shortbow_common` 25%
  - `nut_mix` 40%
- Encounter locations:
  - Forced or potential: `Archive Stair` (Sage prologue) as `Archive Cutout`
  - Forced or potential: `Counting-House Yard` (Guild Artisan prologue) as `Ashen Brand Teamster`
  - Potential: `Panicked Holdouts`
  - Potential: `Chest Scavengers` on parties of 3 or more
  - Forced or potential: `Miniboss: Vaelith Marr` as `Ashen Brand Marksman` on large parties
  - Forced: `Ashfall Gate`
  - Forced: `Tresendar Cellars` as `Archive Cutout`
  - Forced: `Emberhall Antechamber` as `Cellar Sniper`
  - Potential random fights:
    - `Panicked Holdouts`
    - `Road Toll Collectors` on parties of 3 or more
    - `Toll Line Standoff` on parties of 3 or more
    - `Snare-Line Ambushers`
    - `Smuggler Camp` on parties of 3 or more
    - `Smuggler Panic` on parties of 3 or more
    - `Returning Scavengers`
    - `Returning Campers` on parties of 3 or more
    - `Milestone Scavengers` on parties of 3 or more

### Ashen Brand Enforcer

- Archetype: `ash_brand_enforcer`
- Base sheet: level 2, 18 HP, AC 13, Hooked Falchion `1d8+1`, XP 100, Gold 14
- Tags and traits: `enemy`, `humanoid`, `parley`, feature `punishing_strike`
- Runtime behavior:
  - `punishing_strike` once: attacks a buffed or marked hero, then deals an extra `1d6` slashing damage on hit
  - On a successful punishing strike, strips `blessed` if the target has it
  - Normal targeting prefers marked heroes first, then heroes currently carrying momentum buffs such as `blessed`, `emboldened`, or `invisible`
- Item drops:
  - No item loot table currently defined in `LOOT_TABLES`
- Encounter locations:
  - Forced: `Ashfall Lower Barracks`
  - Forced or potential: `Miniboss: Rukhar Cinderfang` support enemy
  - Forced: `Cinderfall Relay` as `Ashen Brand Runner`
  - Forced: `Boss: Varyn Sable`
  - Potential: `Smuggler Revenge Squad`

### Ember Channeler

- Archetype: `ember_channeler`
- Base sheet: level 2, 15 HP, AC 12, Ember Brand `1d6+1`, XP 100, Gold 12
- Tags and traits: `enemy`, `humanoid`, feature `ember_mark`
- Runtime behavior:
  - `ember_mark` once: WIS save DC 12 or target gains `marked` for 2 rounds and `reeling` for 1 round
  - The mark acts as a team focus-fire flag; other updated enemies will prioritize that hero when possible
- Item drops:
  - No item loot table currently defined in `LOOT_TABLES`
- Encounter locations:
  - Potential: `Ashfall Lower Barracks`
  - Forced: `Cinderfall Relay` as `Ember Relay Keeper`
  - Forced: `Boss: Varyn Sable`
  - Potential: `Smuggler Revenge Squad` on parties of 3 or more

### Carrion Stalker

- Archetype: `carrion_stalker`
- Base sheet: level 2, 17 HP, AC 14, Serrated Talons `1d6+2`, XP 100, Gold 0
- Tags and traits: `enemy`, `monstrosity`, feature `shadow_hide`
- Runtime behavior:
  - Starts combat with `invisible` for 1 round
  - `shadow_hide` once: can vanish again mid-fight if still conscious
  - On hit, applies `bleeding` for 2 rounds
  - Targeting prefers marked heroes first, then weak or lightly defended heroes
- Item drops:
  - No item loot table currently defined in `LOOT_TABLES`
- Encounter locations:
  - Forced: `Cinderfall Gate`
  - Potential: `Cinderfall Relay`

### Skeletal Sentry

- Archetype: `skeletal_sentry`
- Base sheet: level 1, 13 HP, AC 12, Rusty Spear `1d6`, XP 50, Gold 2
- Tags and traits: `enemy`, `undead`, feature `undead_fortitude`
- Runtime behavior:
  - No separate active AI branch beyond basic attacks
  - Intended as site defender / attrition unit
- Item drops:
  - `blessed_salve` 18%
  - `mace_common` 14%
  - `soldiers_amulet_common` 6%
- Encounter locations:
  - Forced: `Old Owl Well Dig Ring`
  - Potential: `Miniboss: Vaelith Marr`
  - Forced: `Tresendar Cellars`
  - Potential: `The Cistern Eye`

### Ashfang Beast

- Archetype: `worg`
- Base sheet: level 1, 18 HP, AC 13, Rending Bite `2d4+1`, XP 75, Gold 8
- Tags and traits: `enemy`, `beast`, feature `pack_tactics`
- Runtime behavior:
  - Gains practical advantage when another enemy is still conscious
  - On hit, target makes STR save DC 11 or becomes `prone` for 1 round
- Item drops:
  - `smoked_ham` 45%
  - `travel_biscuits` 35%
  - `spiced_sausage` 25%
- Encounter locations:
  - Forced: `Wyvern Tor Shelf Fight`
  - Potential: `Ashfall Gate` on larger parties

### Red Mesa Raider

- Archetype: `orc_raider`
- Base sheet: level 1, 16 HP, AC 14, Battleaxe `1d8+1`, XP 75, Gold 10
- Tags and traits: `enemy`, `humanoid`, `parley`, feature `aggressive`
- Runtime behavior:
  - No dedicated active AI branch beyond basic attacks
  - Serves as the tougher melee line in Wyvern Tor / Ashfall
- Item drops:
  - `potion_healing` 30%
  - `battleaxe_common` 25%
  - `shield_common` 15%
  - `salt_pork` 45%
  - `travel_biscuits` 35%
- Encounter locations:
  - Forced: `Wyvern Tor Shelf Fight`
  - Potential: `Miniboss: Brughor Skullcleaver`
  - Potential: `Ashfall Lower Barracks`
  - Potential: `Miniboss: Rukhar Cinderfang`
  - Named variant: `Tor Lookout`

### Mesa Warlord

- Archetype: `orc_bloodchief`
- Base sheet: level 2, 33 HP, AC 15, Great Axe `1d12+1`, XP 150, Gold 30
- Tags and traits: `enemy`, `humanoid`, `leader`, `parley`, features `aggressive`, `war_cry`
- Runtime behavior:
  - `war_cry` once: gains 6 temp HP and `emboldened` for 2 rounds
- Item drops:
  - `greater_healing_draught` 60%
  - `battleaxe_uncommon` 30%
  - `scale_mail_uncommon` 18%
  - `potion_heroism` 25%
  - `spiced_sausage` 100%, quantity 2-3
- Encounter locations:
  - Forced miniboss: `Miniboss: Brughor Skullcleaver`
- Scripted scene reward near this fight:
  - `greater_healing_draught` from `Brughor's travel chest`

### Hollow Giant

- Archetype: `ogre_brute`
- Base sheet: level 2, 38 HP, AC 11, Maul Club `2d8`, XP 125, Gold 18
- Tags and traits: `enemy`, `giant`
- Runtime behavior:
  - On high hit roll (`18+`), target makes STR save DC 12 or becomes `prone`
- Item drops:
  - `camp_stew_jar` 50%
  - `bread_round` 100%, quantity 1-3
  - `warhammer_common` 18%
- Encounter locations:
  - Potential support in `Miniboss: Brughor Skullcleaver` as `Cragmaw-Ogre Thane`

### Gravecaller

- Archetype: `gravecaller`
- Base sheet: level 2, 26 HP, AC 13, Gravehook Dagger `1d6`, XP 125, Gold 24
- Tags and traits: `enemy`, `humanoid`, `leader`, `parley`, features `ritual_ash`, `grave_fear`
- Runtime behavior:
  - `grave_fear` once: WIS save DC 12 or `frightened` for 2 rounds
  - `ash_veil` once: CON save DC 12 or `blinded` for 1 round
- Item drops:
  - `scroll_clarity` 45%
  - `scroll_lesser_restoration` 30%
  - `amber_amulet_uncommon` 18%
  - `blessed_salve` 35%
  - `black_tea` 60%
- Encounter locations:
  - Forced miniboss: `Miniboss: Vaelith Marr`
- Named variant:
  - `Vaelith Marr`
- Scripted scene reward near this fight:
  - `scroll_lesser_restoration` from `Vaelith's ritual satchel`

### Cistern Eye

- Archetype: `nothic`
- Base sheet: level 2, 29 HP, AC 14, Hooked Claws `2d4`, XP 150, Gold 22
- Tags and traits: `enemy`, `aberration`, features `weird_insight`, `rotting_gaze`
- Runtime behavior:
  - `weird_insight` once: WIS save DC 12 or `reeling` for 2 rounds
  - `rotting_gaze` once: CON save DC 12 or `poisoned` for 2 rounds
  - On high hit roll (`18+`), target makes WIS save DC 12 or becomes `frightened` for 1 round
- Item drops:
  - `watcher_ring_uncommon` 18%
  - `amber_amulet_uncommon` 18%
  - `scroll_arcane_refresh` 25%
  - `red_wine` 80%
- Encounter locations:
  - Forced boss-style encounter: `The Cistern Eye`
- Named variant:
  - `Cistern Eye`
- Scripted scene reward near this fight:
  - `scroll_arcane_refresh` from `a sealed coffer in the cistern alcove`

### Rukhar Cinderfang

- Archetype: `rukhar`
- Base sheet: level 2, 27 HP, AC 16, Longsword `1d8`, shielded, XP 125, Gold 35
- Tags and traits: `enemy`, `humanoid`, `leader`, `parley`, features `martial_advantage`, `cinder_poison`
- Runtime behavior:
  - `war_shout` once: CON save DC 12 or `deafened` for 2 rounds
  - Martial advantage: adds `2d6` damage on weapon hits while another enemy remains conscious
  - Poisoned strike:
    - CON save DC 12 or take `1d4` poison and become `poisoned` for 2 rounds
    - second CON save DC 12 or become `paralyzed` for 1 round
- Item drops:
  - `greater_healing_draught` 80%
  - `scroll_revivify` 5%
  - `warhammer_uncommon` 35%
  - `chain_shirt_uncommon` 25%
  - `fireward_elixir` 25%
  - `scroll_guardian_light` 35%
  - `smoked_ham` 100%, quantity 2-3
- Encounter locations:
  - Forced miniboss: `Miniboss: Rukhar Cinderfang`

### Varyn Sable

- Archetype: `varyn`
- Base sheet: level 2, 38 HP, AC 14, Blackened Rapier `1d8`, to-hit bonus weapon, XP 200, Gold 60
- Tags and traits: `enemy`, `humanoid`, `leader`, `parley`, features `ashen_poison`, `rally`
- Runtime behavior:
  - `silver_tongue` once: WIS save DC 12 or `charmed` for 1 round
  - `binding_hex` once: WIS save DC 12 or `incapacitated` for 1 round
  - `ashen_gaze` once: CON save DC 12 or `petrified` for 1 round
  - `rally` once at half HP or lower: gains 6 temp HP and `emboldened` for 2 rounds
  - Poisoned strike:
    - CON save DC 12 or take `1d4` poison and become `poisoned` for 2 rounds
    - second CON save DC 12 or gain `exhaustion` 2
- Item drops:
  - `superior_healing_elixir` 80%
  - `scroll_revivify` 5%
  - `rapier_rare` 35%
  - `studded_leather_rare` 25%
  - `dust_of_disappearance` 20%
  - `scroll_arcane_refresh` 35%
  - `camp_stew_jar` 100%, quantity 2-4
- Encounter locations:
  - Forced final boss: `Boss: Varyn Sable`

## Act 2 Enemies

### Rival Expedition Reaver

- Archetype: `expedition_reaver`
- Base sheet: level 2, 18 HP, AC 13, Survey Hatchet `1d6+2`, XP 75, Gold 10
- Tags and traits: `enemy`, `humanoid`, `parley`
- Runtime behavior:
  - No dedicated active AI branch beyond basic attacks
- Item drops:
  - No item loot table currently defined in `LOOT_TABLES`
- Encounter locations:
  - Potential: `Woodland Saboteurs`
  - Potential: `Midpoint: Sabotage Night`

### Quiet Choir Agent

- Archetype: `cult_lookout`
- Base sheet: level 2, 16 HP, AC 13, Marked Shortbow `1d6+2`, XP 75, Gold 9
- Tags and traits: `enemy`, `humanoid`, `parley`, features `blind_dust`, `marked_shot`
- Runtime behavior:
  - `blind_dust` once: DEX save DC 12 or `blinded` 1 and `reeling` 1
  - `marked_shot` once: self-buffs with `emboldened`, attacks, and can apply `reeling` 1 on hit
- Item drops:
  - No item loot table currently defined in `LOOT_TABLES`
- Encounter locations:
  - Forced or potential: `Woodland Saboteurs`
  - Forced: `Midpoint: Sabotage Night`
  - Potential: `Broken Prospect`
  - Potential: `South Adit Wardens`
  - Potential: `Boss: Sister Caldra Voss`

### Quiet Choir Adept

- Archetype: `choir_adept`
- Base sheet: level 3, 24 HP, AC 13, Ritual Knife `1d6+1`, XP 125, Gold 22
- Tags and traits: `enemy`, `humanoid`, `leader`, `parley`, features `hush_prayer`, `discordant_word`
- Runtime behavior:
  - `hush_prayer` once: applies `blessed` to self and conscious allies for 2 rounds
  - `discordant_word` once: WIS save DC 13 or takes `2d6` psychic damage, plus `frightened` 1 and `reeling` 2
- Item drops:
  - No item loot table currently defined in `LOOT_TABLES`
- Encounter locations:
  - Forced: `Midpoint: Sabotage Night`
  - Forced: `South Adit Wardens`
  - Forced: `Boss: Sister Caldra Voss`

### Tunnel Scavenger

- Archetype: `grimlock_tunneler`
- Base sheet: level 2, 20 HP, AC 14, Hooked Blade `1d6+2`, XP 100, Gold 6
- Tags and traits: `enemy`, `monstrosity`, feature `blind_sense`
- Runtime behavior:
  - Prefers targets already suffering `reeling`
  - On hit against a `reeling` target, or on high hit roll, target can be dragged into `grappled` for 2 rounds after STR save DC 12 fails
- Item drops:
  - No item loot table currently defined in `LOOT_TABLES`
- Encounter locations:
  - Potential: `Woodland Saboteurs`
  - Forced: `Stonehollow Breakout`
  - Potential: `Midpoint: Sabotage Night`
  - Forced: `Outer Gallery Pressure`

### Bloodmote Swarm

- Archetype: `stirge_swarm`
- Base sheet: level 2, 17 HP, AC 14, Proboscis `1d6`, XP 75, Gold 0
- Tags and traits: `enemy`, `beast`, feature `swarm`
- Runtime behavior:
  - On hit, latches onto target and applies `grappled` for 2 rounds
  - If still attached on its next turn, deals extra `1d4` piercing damage and refreshes the grapple
- Item drops:
  - No item loot table currently defined in `LOOT_TABLES`
- Encounter locations:
  - Potential: `Stonehollow Breakout`
  - Potential: `Outer Gallery Pressure`

### Corrosive Mass

- Archetype: `ochre_slime`
- Base sheet: level 2, 28 HP, AC 8, Pseudopod `2d6`, XP 100, Gold 0
- Tags and traits: `enemy`, `ooze`, feature `ooze`
- Runtime behavior:
  - On hit, deals an extra `1d4` acid damage and applies `acid` for 2 rounds
  - AI prefers targets already suffering acid pressure
- Item drops:
  - No item loot table currently defined in `LOOT_TABLES`
- Encounter locations:
  - Forced: `Stonehollow Breakout`
  - Forced: `Outer Gallery Pressure`

### Meridian Sentinel

- Archetype: `animated_armor`
- Base sheet: level 2, 26 HP, AC 16, Gauntlet Slam `1d6+2`, XP 100, Gold 12
- Tags and traits: `enemy`, `construct`, feature `construct`
- Runtime behavior:
  - `lockstep_bash` once: attacks with a shove-style opener; failed STR save DC 13 causes `prone`
  - On high hit rolls, can also force `prone`
  - AI prefers low-AC targets
- Item drops:
  - No item loot table currently defined in `LOOT_TABLES`
- Encounter locations:
  - Forced: `Broken Prospect`
  - Forced: `Blackglass Causeway`

### Spectral Foreman

- Archetype: `spectral_foreman`
- Base sheet: level 3, 31 HP, AC 14, Phantom Pick `1d8+2`, XP 150, Gold 18
- Tags and traits: `enemy`, `undead`, `leader`, features `dead_shift`, `hammer_order`
- Runtime behavior:
  - `hammer_order` once: buffs an ally with `emboldened` 2 and self with `blessed` 1
  - `dead_shift` once: CON save DC 13 or target takes `2d6` necrotic, plus `exhaustion` 1 and `reeling` 1
- Item drops:
  - No item loot table currently defined in `LOOT_TABLES`
- Encounter locations:
  - Potential: `Stonehollow Breakout` when delayed
  - Forced: `Broken Prospect`
  - Potential: `Blackglass Causeway`

### Starblighted Miner

- Archetype: `starblighted_miner`
- Base sheet: level 3, 29 HP, AC 13, Rusted Pick `1d8+1`, XP 125, Gold 14
- Tags and traits: `enemy`, `humanoid`, feature `whisper_glare`
- Runtime behavior:
  - `whisper_glare` once: WIS save DC 13 or target gains `frightened` 1 and `reeling` 2
  - On high hit rolls, threat profile lines up with the Act 2 reference's reeling pressure theme
- Item drops:
  - No item loot table currently defined in `LOOT_TABLES`
- Encounter locations:
  - Forced: `South Adit Wardens`
  - Potential: `Outer Gallery Pressure`
  - Forced: `Blackglass Causeway`
  - Potential: `Boss: Sister Caldra Voss`

### Sister Caldra Voss

- Archetype: `caldra_voss`
- Base sheet: level 4, 42 HP, AC 15, Shard Dagger `1d8+2`, XP 250, Gold 70
- Tags and traits: `enemy`, `humanoid`, `leader`, `parley`, features `obelisk_whisper`, `shard_veil`, `quiet_choir_rally`, `echo_step`
- Runtime behavior:
  - `obelisk_whisper` once: WIS save DC 14 or `2d8` psychic damage, `frightened` 2, and `reeling` 2
  - `shard_veil` once below roughly two-thirds HP: gains 8 temp HP, `invisible` 1, `blessed` 1
  - `quiet_choir_rally` once: gives self and allies 6 temp HP and `emboldened` 2
  - `echo_step` once: clears movement-impairing statuses, becomes `invisible` 1 and `emboldened` 1
- Item drops:
  - No item loot table currently defined in `LOOT_TABLES`
- Encounter locations:
  - Forced final boss: `Boss: Sister Caldra Voss`

## Act 2 Thematic Expansion: Control Of Truth

These fifteen enemies are designed specifically around Act 2's core themes: control of truth, dangerous knowledge, false authority, expedition sabotage, corrupted custody, and listening-horror rising out of Resonant Vaults.

They are intentionally stronger than the existing Act 1 filler pool. Early Act 2 should already feel like fighting disciplined saboteurs, ritual specialists, warped cave predators, and old Meridian Compact defenses that have outlived their judgment.

### Expansion Summary

| Archetype | Name | Level | HP / AC | Core Attack | Role |
| --- | --- | --- | --- | --- | --- |
| `false_map_skirmisher` | False-Map Skirmisher | 4 | 38 / 15 | Route Knife `1d8+3` | mobile sabotage attacker |
| `claimbinder_notary` | Claimbinder Notary | 4 | 40 / 15 | Seal Mace `1d6+3` | control debuffer |
| `echo_sapper` | Echo Sapper | 4 | 42 / 14 | Breach Hammer `1d10+2` | line-breaker |
| `pact_archive_warden` | Meridian Archive Warden | 4 | 44 / 16 | Archive Spear `1d8+3` | defensive sentinel |
| `blackglass_listener` | Blackglass Listener | 4 | 41 / 15 | Thought Spike `1d8+2` psychic | anti-caster scout |
| `choir_cartographer` | Choir Cartographer | 5 | 48 / 15 | Survey Blade `1d8+3` | route-control leader |
| `resonance_leech` | Resonance Leech | 5 | 50 / 14 | Siphon Tendril `2d6+2` | sustain drain monster |
| `survey_chain_revenant` | Survey-Chain Revenant | 5 | 52 / 16 | Chain Pick `1d10+3` | undead lock-down bruiser |
| `censer_horror` | Iron Censer Horror | 5 | 55 / 16 | Smothering Swing `2d6+2` | construct area denial |
| `memory_taker_adept` | Memory-Taker Adept | 5 | 46 / 15 | Quietus Dagger `1d8+3` | psychic assassin |
| `obelisk_chorister` | Obelisk Chorister | 6 | 58 / 16 | Choir Staff `1d8+4` | elite cult caster |
| `blacklake_adjudicator` | Blackglass Adjudicator | 6 | 60 / 17 | Judgement Pike `1d10+4` | elite Meridian guardian |
| `forge_echo_stalker` | Forge-Echo Stalker | 6 | 62 / 16 | Echo Claws `2d6+4` | ambush predator |
| `covenant_breaker_wight` | Covenant Breaker Wight | 6 | 64 / 17 | Oathsplitter `1d10+4` | commander-killer undead |
| `hollowed_survey_titan` | Hollowed Survey Titan | 6 | 72 / 15 | Survey Maul `2d8+4` | late-route brute |

### False-Map Skirmisher

- Archetype: `false_map_skirmisher`
- Base sheet: level 4, 38 HP, AC 15, Route Knife `1d8+3`, XP 175, Gold 14
- Tags and traits: `enemy`, `humanoid`, `skirmisher`, `parley`
- Runtime behavior:
  - `route_splice` once: shifts position, gains `emboldened` 1, and grants the first ally attacking the same target this round `+2` to hit
  - `mislead_step` once: DEX save DC 13 or target suffers `reeling` 1
- Encounter locations:
  - Potential: `Woodland Saboteurs`
  - Potential: `Midpoint: Sabotage Night`
  - Potential: delayed-route recovery scenes

### Claimbinder Notary

- Archetype: `claimbinder_notary`
- Base sheet: level 4, 40 HP, AC 15, Seal Mace `1d6+3`, XP 180, Gold 22
- Tags and traits: `enemy`, `humanoid`, `leader`, `parley`
- Runtime behavior:
  - `seizure_order` once: WIS save DC 14 or target loses `emboldened`/`blessed` style boons and suffers `reeling` 2
  - `filed_objection` once: marks one target; allies deal +2 damage against that target until the notary is hit
- Encounter locations:
  - Potential: claims-war command scenes
  - Potential: sponsor conflict encounters
  - Potential: rival expedition leadership fights

### Echo Sapper

- Archetype: `echo_sapper`
- Base sheet: level 4, 42 HP, AC 14, Breach Hammer `1d10+2`, XP 190, Gold 16
- Tags and traits: `enemy`, `humanoid`, `siege`
- Runtime behavior:
  - `survey_charge` once: DEX save DC 14 or targets take `2d6` force and fall `prone`
  - `dust_blind` once: targets already `prone` or `reeling` also risk `blinded` 1
- Encounter locations:
  - Potential: `Stonehollow Dig`
  - Potential: `Broken Prospect`
  - Potential: collapse or breach scenes

### Meridian Archive Warden

- Archetype: `pact_archive_warden`
- Base sheet: level 4, 44 HP, AC 16, Archive Spear `1d8+3`, XP 200, Gold 18
- Tags and traits: `enemy`, `construct`, `sentinel`
- Runtime behavior:
  - `access_denied` once: STR save DC 14 or target is shoved back and `slowed` for 1 round
  - `custody_protocol` passive: gains +2 AC against the first attack each round from a target it already struck
- Encounter locations:
  - Potential: `Broken Prospect`
  - Potential: archive thresholds
  - Potential: sealed Meridian record rooms

### Blackglass Listener

- Archetype: `blackglass_listener`
- Base sheet: level 4, 41 HP, AC 15, Thought Spike `1d8+2` psychic, XP 190, Gold 10
- Tags and traits: `enemy`, `aberration`, `scout`
- Runtime behavior:
  - `overhear_intent` once: WIS save DC 14 or target becomes `frightened` 1 and cannot gain advantage-like bonuses until its next turn
  - `feedback_pulse` once: deals `2d6` psychic to a target that used a spell or support action last round
- Encounter locations:
  - Potential: `Hushfen and the Pale Circuit`
  - Potential: `Blackglass Causeway`
  - Potential: high-whisper route events

### Choir Cartographer

- Archetype: `choir_cartographer`
- Base sheet: level 5, 48 HP, AC 15, Survey Blade `1d8+3`, XP 225, Gold 28
- Tags and traits: `enemy`, `humanoid`, `leader`, `parley`
- Runtime behavior:
  - `map_the_weakness` once: one target takes +2 damage from all allies for 2 rounds
  - `stolen_route` once: swaps places with a conscious ally and gains `blessed` 1
- Encounter locations:
  - Potential: `Midpoint: Sabotage Night`
  - Potential: late early-route convergence
  - Potential: `Resonant Vault Outer Galleries`

### Resonance Leech

- Archetype: `resonance_leech`
- Base sheet: level 5, 50 HP, AC 14, Siphon Tendril `2d6+2`, XP 230, Gold 0
- Tags and traits: `enemy`, `aberration`
- Runtime behavior:
  - `drain_cadence` once: CON save DC 14 or target takes `2d6` psychic, loses one active positive status, and the leech gains 8 temp HP
  - `echo_feast` passive: deals +`1d6` damage to `frightened`, `reeling`, or `silenced` targets
- Encounter locations:
  - Potential: `South Adit`
  - Potential: `Resonant Vault Outer Galleries`
  - Potential: `Blackglass Causeway`

### Survey-Chain Revenant

- Archetype: `survey_chain_revenant`
- Base sheet: level 5, 52 HP, AC 16, Chain Pick `1d10+3`, XP 240, Gold 20
- Tags and traits: `enemy`, `undead`, `bruiser`
- Runtime behavior:
  - `drag_to_marker` once: STR save DC 15 or target is `grappled` and pulled into melee range
  - `unfinished_shift` passive: while grappling a target, the revenant reduces incoming weapon damage by 2
- Encounter locations:
  - Potential: delayed rescue routes
  - Potential: `South Adit`
  - Potential: burial-ledger or rail-line scenes

### Iron Censer Horror

- Archetype: `censer_horror`
- Base sheet: level 5, 55 HP, AC 16, Smothering Swing `2d6+2`, XP 250, Gold 18
- Tags and traits: `enemy`, `construct`, `horror`
- Runtime behavior:
  - `hush_smoke` once: CON save DC 14 or targets in a small area suffer `blinded` 1 and deal -2 damage with verbal or morale-style abilities
  - `cinder_liturgy` passive: enemies starting adjacent while `frightened` take `1d4` fire
- Encounter locations:
  - Potential: cult chapel rooms
  - Potential: Meridian Forge-approach chambers
  - Potential: sanctum profanation fights

### Memory-Taker Adept

- Archetype: `memory_taker_adept`
- Base sheet: level 5, 46 HP, AC 15, Quietus Dagger `1d8+3`, XP 220, Gold 24
- Tags and traits: `enemy`, `humanoid`, `assassin`, `parley`
- Runtime behavior:
  - `erase_witness` once: WIS save DC 14 or target loses reaction-style defensive options and suffers `reeling` 2
  - `borrowed_instinct` once: after hitting a target with a positive status, the adept gains `emboldened` 2
- Encounter locations:
  - Potential: Quiet Choir kill teams
  - Potential: sponsor assassination scenes
  - Potential: `Blackglass Causeway`

### Obelisk Chorister

- Archetype: `obelisk_chorister`
- Base sheet: level 6, 58 HP, AC 16, Choir Staff `1d8+4`, XP 300, Gold 34
- Tags and traits: `enemy`, `humanoid`, `leader`, `parley`
- Runtime behavior:
  - `shard_hymn` once: WIS save DC 15 or target takes `3d6` psychic, `frightened` 2, and `reeling` 2
  - `choral_screen` once: self and allies gain 6 temp HP; cult allies also clear `frightened`
- Encounter locations:
  - Potential: Meridian Forge antechambers
  - Potential: elite cult escort fights
  - Potential: high-whisper late-route encounters

### Blackglass Adjudicator

- Archetype: `blacklake_adjudicator`
- Base sheet: level 6, 60 HP, AC 17, Judgement Pike `1d10+4`, XP 310, Gold 26
- Tags and traits: `enemy`, `construct`, `leader`, `sentinel`
- Runtime behavior:
  - `sentence_of_entry` once: WIS save DC 15 or target becomes `slowed` and cannot move closer to the threshold next turn
  - `mirror_verdict` passive: the first ranged hit it suffers each round reflects `1d6` force back to the attacker
- Encounter locations:
  - Potential: `Blackglass Causeway`
  - Potential: ritual bridgeheads
  - Potential: pre-Meridian Forge threshold rooms

### Forge-Echo Stalker

- Archetype: `forge_echo_stalker`
- Base sheet: level 6, 62 HP, AC 16, Echo Claws `2d6+4`, XP 325, Gold 0
- Tags and traits: `enemy`, `aberration`, `ambusher`
- Runtime behavior:
  - `answering_screech` once: against a `reeling` target, deals an extra `2d6` thunder and can knock `prone` on CON save DC 15 failure
  - `heatshadow_prowl` once: gains `invisible` 1 and bonus movement through forge-lit terrain
- Encounter locations:
  - Potential: `Resonant Vault Outer Galleries`
  - Potential: forge side halls
  - Potential: whisper-surged boss support fights

### Covenant Breaker Wight

- Archetype: `covenant_breaker_wight`
- Base sheet: level 6, 64 HP, AC 17, Oathsplitter `1d10+4`, XP 340, Gold 32
- Tags and traits: `enemy`, `undead`, `leader`
- Runtime behavior:
  - `break_the_line` once: STR or WIS save DC 15 or target suffers `prone` plus `frightened` 1
  - `life_levy` passive: the wight regains 6 HP the first time each round it damages a `blessed` or `emboldened` target
- Encounter locations:
  - Potential: `South Adit`
  - Potential: late `Broken Prospect`
  - Potential: Forge guard retinues

### Hollowed Survey Titan

- Archetype: `hollowed_survey_titan`
- Base sheet: level 6, 72 HP, AC 15, Survey Maul `2d8+4`, XP 375, Gold 30
- Tags and traits: `enemy`, `construct`, `brute`
- Runtime behavior:
  - `bearing_collapse` once: DEX save DC 15 or targets in a short line take `3d6` bludgeoning and become `prone`
  - `loadbearing_frame` passive: while above half HP, forced movement against the titan automatically fails
- Encounter locations:
  - Potential: `Broken Prospect`
  - Potential: `Resonant Vault Outer Galleries`
  - Potential: Forge boss-support variant

## Encounter Cross-Reference

### Background Prologue Combat Pool

- `South Barracks Breakout`: bandit
- `Hospice Gate`: wolf
- `Blacklake Warehouse`: bandit
- `Archive Stair`: bandit_archer
- `Camp at First Light`: goblin + wolf
- `Market Corner`: bandit
- `Counting-House Yard`: bandit_archer
- `Wayside Pursuit`: goblin

### Main Story Forced Fights

- `Roadside Ambush`: goblin + wolf
- `Old Owl Well Dig Ring`: skeletal_sentry + bandit, plus extra skeletal_sentry on larger parties
- `Miniboss: Vaelith Marr`: gravecaller, plus optional skeletal_sentry / bandit_archer support
- `Wyvern Tor Shelf Fight`: orc_raider + worg, plus extra orc_raider on larger parties
- `Miniboss: Brughor Skullcleaver`: orc_bloodchief, plus optional ogre_brute / orc_raider support
- `Ashfall Gate`: bandit + bandit_archer, plus optional worg
- `Ashfall Lower Barracks`: bandit + bandit_archer, plus optional bandit / orc_raider
- `Miniboss: Rukhar Cinderfang`: rukhar, plus optional bandit / orc_raider support
- `Tresendar Cellars`: bandit + bandit_archer, plus optional skeletal_sentry
- `The Cistern Eye`: nothic, plus optional skeletal_sentry
- `Emberhall Antechamber`: bandit + bandit_archer, plus optional bandit
- `Boss: Varyn Sable`: varyn, plus bandit and bandit_archer support

### Random Encounter Combat Pool

- Ashen Brand cutter / marksman:
  - `Chest Scavengers`
  - `Panicked Holdouts`
  - `Road Toll Collectors`
  - `Toll Line Standoff`
  - `Snare-Line Ambushers`
  - `Smuggler Camp`
  - `Smuggler Panic`
  - `Returning Scavengers`
  - `Returning Campers`
  - `Milestone Scavengers`
- Scrapling:
  - `Cottage Squatters`
  - `Cellar Door Rush`
  - `Wayhouse Scavengers`
  - `Wayhouse Holdouts`
  - `Trapdoor Drop`
- Ashfang Hound:
  - `Hound on the Trail`
  - `Cornered Hound`
  - `Brush Stalker`

### Act 2 Forced Or Conditional Fights

- `Woodland Saboteurs`: expedition_reaver + cult_lookout, with conditional extra cult_lookout or grimlock_tunneler
- `Stonehollow Breakout`: ochre_slime + grimlock_tunneler, with conditional spectral_foreman or stirge_swarm
- `Midpoint: Sabotage Night`: cult_lookout + choir_adept, with conditional expedition_reaver or grimlock_tunneler
- `Broken Prospect`: animated_armor + spectral_foreman, with conditional cult_lookout
- `South Adit Wardens`: starblighted_miner + choir_adept, with conditional cult_lookout support
- `Outer Gallery Pressure`: grimlock_tunneler + ochre_slime, with conditional starblighted_miner or stirge_swarm
- `Blackglass Causeway`: animated_armor + starblighted_miner, with conditional spectral_foreman
- `Boss: Sister Caldra Voss`: caldra_voss + choir_adept, with conditional cult_lookout and/or starblighted_miner

## Important Implementation Notes

- The combat engine keys special behavior off `archetype`, so renamed enemies like `Ashen Brand Fixer`, `Scrapling Cutthroat`, or `Cistern Eye` still use the same base enemy logic.
- Only Act 1 archetypes currently have item loot tables in `dnd_game/data/items/catalog.py`.
- Act 2 enemies still award their built-in gold values, but they do not currently roll item drops.
- Several major scenes also grant scripted environmental rewards that are not part of enemy drop tables:
  - Vaelith area: `scroll_lesser_restoration`
  - Brughor area: `greater_healing_draught`
  - Tresendar cistern area: `scroll_arcane_refresh`
  - Emberhall clerk event: `antitoxin_vial`

## Design Expansion: 25 New Enemy Concepts

These entries are designed to slot cleanly into the game's current status vocabulary and encounter style while drawing from frontier scavengers, Quiet Choir cells, engineered sentries, ruin predators, drowned revenants, and other Aethrune-aligned threat shapes.

They are ordered from easy to hard so you can lift early-game skirmishers, mid-tier specialists, or boss-grade threats as needed.

### Expansion Summary

| Archetype | Display Name | Difficulty | Role |
| --- | --- | --- | --- |
| `cinder_kobold` | Cinderkin Scavenger | Easy | pack skirmisher |
| `briar_twig` | Briar Twig Ambusher | Easy | hidden opener |
| `mireweb_spider` | Mireweb Spider | Easy | restraining hunter |
| `gutter_zealot` | Quiet Choir Listener | Easy | fanatic support |
| `rust_shell_scuttler` | Rust-Shell Scuttler | Easy | corrosion nuisance |
| `lantern_fen_wisp` | Lantern Wisp | Easy | evasive lure |
| `ashstone_percher` | Ashstone Percher | Easy | ruin ambusher |
| `acidmaw_burrower` | Acidmaw Burrower | Easy | tunnel bruiser |
| `bugbear_reaver` | Bugbear Tunnel Reaver | Standard | ambush striker |
| `ettervine_webherd` | Ettervine Webherd | Standard | drag-and-pin controller |
| `carrion_lash_crawler` | Carrion Lash Crawler | Standard | paralysis predator |
| `cache_mimic` | Cache Mimic | Standard | trap monster |
| `stonegaze_skulker` | Stonegaze Skulker | Standard | gaze disabler |
| `cliff_harpy` | Shrieking Cliff Harpy | Standard | charm disruptor |
| `whispermaw_blob` | Whispermaw Blob | Standard | chaos brawler |
| `blackglass_pincerling` | Blackglass Pincerling | Standard | grapple-lock hunter |
| `graveblade_wight` | Graveblade Wight | Standard | undead captain |
| `cinderflame_skull` | Cinderflame Skull | Hard | mobile fire caster |
| `obelisk_eye` | Eye of the Obelisk | Hard | ray sentinel |
| `iron_prayer_horror` | Iron Prayer Horror | Hard | anti-control tank |
| `hookclaw_burrower` | Hookclaw Burrower | Hard | cave dragger |
| `thunderroot_mound` | Thunderroot Mound | Hard | engulfing plant brute |
| `oathbroken_revenant` | Oathbroken Revenant | Hard | stalking duelist |
| `choir_executioner` | Choir Executioner | Hard | elite cult finisher |
| `duskmire_matriarch` | Duskmire Matriarch | Hard | apex spider boss |

### Easy Expansion Enemies

#### Cinderkin Scavenger

- Description: A soot-stained tunnel raider that fights in pairs, pelts foes with ash pots, and bolts the moment the line breaks.
- Archetype: `cinder_kobold`
- Suggested base sheet: level 1, 7 HP, AC 13, Hook Knife `1d4+2`, XP 50, Gold 5
- Tags and traits: `enemy`, `humanoid`, `cowardly`, features `pack_tactics`, `cinder_pot`
- Suggested runtime behavior:
  - Gains practical advantage while at least one ally remains conscious
  - `cinder_pot` once: DEX save DC 11 or `blinded` 1 and `reeling` 1
- Suggested encounter use:
  - Early mine tunnels, kiln ruins, or ash-waste scavenger packs

#### Briar Twig Ambusher

- Description: A rootbound shrub-creature that passes for dead brush until a traveler steps close enough for the thorns to lash out.
- Archetype: `briar_twig`
- Suggested base sheet: level 1, 8 HP, AC 13, Thorn Claws `1d4+1`, XP 50, Gold 2
- Tags and traits: `enemy`, `plant`, features `false_appearance`, `thorn_burst`
- Suggested runtime behavior:
  - If combat begins while it is unnoticed, it favors opening on backline or lightly armored targets
  - On first hit, target makes STR save DC 11 or gains `reeling` 2
- Suggested encounter use:
  - Hedgerow ambusher, cursed grove filler, or graveyard underbrush hazard

#### Mireweb Spider

- Description: A long-legged swamp spider that pins prey in slick webbing and lets venom finish the work.
- Archetype: `mireweb_spider`
- Suggested base sheet: level 1, 12 HP, AC 14, Venom Fang `1d6+1`, XP 75, Gold 0
- Tags and traits: `enemy`, `beast`, features `spider_climb`, `web_walker`, `venom_web`
- Suggested runtime behavior:
  - `venom_web` once: DEX save DC 11 or `restrained` 2
  - Bite adds `1d4` poison; CON save DC 11 or `poisoned` 1
- Suggested encounter use:
  - Marsh bridges, cave mouths, canopy fights, or spider brood support

#### Quiet Choir Listener

- Description: A street preacher turned knife-handed fanatic, eager to bleed for a promise no sane person would trust.
- Archetype: `gutter_zealot`
- Suggested base sheet: level 1, 10 HP, AC 12, Ritual Sickle `1d6+1`, XP 50, Gold 7
- Tags and traits: `enemy`, `humanoid`, `parley`, features `dark_devotion`, `blood_prayer`
- Suggested runtime behavior:
  - `blood_prayer` once below half HP: gains `blessed` 2 and 4 temp HP
  - Leans into charm- and fear-resistant fanatic behavior in encounter scripting
- Suggested encounter use:
  - Cult safehouses, alley sanctums, or low-tier support for stronger choir leaders

#### Rust-Shell Scuttler

- Description: A copper-streaked beetle horror that chews armor straps, blade grips, and anything else that tastes like decay.
- Archetype: `rust_shell_scuttler`
- Suggested base sheet: level 1, 14 HP, AC 13, Corrosive Mandibles `1d6+1`, XP 75, Gold 4
- Tags and traits: `enemy`, `monstrosity`, features `corrode`, `skitter`
- Suggested runtime behavior:
  - On hit, target gains `acid` 2
  - Against targets already suffering `acid`, the scuttler deals an extra `1d4` acid damage
- Suggested encounter use:
  - Armories, ruined barracks, old battlefields, or alchemical refuse pits

#### Lantern Wisp

- Description: A swamp light that floats just ahead of travelers until the path beneath them turns to black water and roots.
- Archetype: `lantern_fen_wisp`
- Suggested base sheet: level 2, 16 HP, AC 16, Shock Touch `1d8`, XP 75, Gold 0
- Tags and traits: `enemy`, `undead`, features `lure_glow`, `vanish`
- Suggested runtime behavior:
  - `lure_glow` once: WIS save DC 12 or `charmed` 1 and `reeling` 1
  - `vanish` once: gains `invisible` 1 after striking or after dropping below half HP
- Suggested encounter use:
  - Night-road hazard, marsh guide gone wrong, or slippery support nuisance

#### Ashstone Percher

- Description: A squat ruin-statue that clings to arches and rafters until it drops on intruders in a spray of chips and dust.
- Archetype: `ashstone_percher`
- Suggested base sheet: level 2, 20 HP, AC 15, Stone Claws `1d6+2`, XP 100, Gold 8
- Tags and traits: `enemy`, `elemental`, features `false_appearance`, `flyby`
- Suggested runtime behavior:
  - If it begins combat unseen, its first hit deals an extra `1d4` slashing damage
  - On high hit roll, target makes STR save DC 12 or becomes `prone`
- Suggested encounter use:
  - Cathedral eaves, broken bridges, gatehouses, or watchtower rafters

#### Acidmaw Burrower

- Description: A tunnel predator that bursts from loose earth, clamps onto prey, and drenches clustered targets in acid spit.
- Archetype: `acidmaw_burrower`
- Suggested base sheet: level 2, 24 HP, AC 14, Serrated Bite `1d8+2`, XP 100, Gold 6
- Tags and traits: `enemy`, `monstrosity`, features `burrower`, `acid_spray`
- Suggested runtime behavior:
  - Bite: failed STR save DC 12 causes `grappled` 1
  - `acid_spray` once: DEX save DC 12 or take `2d6` acid damage and gain `acid` 2
- Suggested encounter use:
  - Mine collapses, sinkholes, roadside burrows, or cave approach fights

### Standard Expansion Enemies

#### Bugbear Tunnel Reaver

- Description: A shaft-haunting brute that waits in the dark for the first clean opening, then crushes it with a single brutal swing.
- Archetype: `bugbear_reaver`
- Suggested base sheet: level 2, 25 HP, AC 14, Spiked Maul `1d8+2`, XP 125, Gold 12
- Tags and traits: `enemy`, `humanoid`, features `surprise_attack`, `abduct`
- Suggested runtime behavior:
  - First hit in combat deals an extra `2d6` if it began from ambush or struck an unwounded target
  - On hit, a Medium target makes STR save DC 12 or becomes `grappled` 1 as the reaver advances
- Suggested encounter use:
  - Raider lieutenant, mine ambusher, or opening bruiser in a goblinoid fight

#### Ettervine Webherd

- Description: A man-sized web hunter wrapped in root-web cords that treats prey like livestock to be reeled into the nest.
- Archetype: `ettervine_webherd`
- Suggested base sheet: level 3, 28 HP, AC 14, Hooked Fangs `1d6+2`, XP 125, Gold 10
- Tags and traits: `enemy`, `monstrosity`, features `spider_climb`, `web_walker`, `reel_strand`
- Suggested runtime behavior:
  - `reel_strand` once: DEX save DC 13 or `restrained` 2; if already `restrained`, dragged into `grappled` 1
  - Bite: CON save DC 12 or `poisoned` 2
- Suggested encounter use:
  - Web caverns, overgrown mines, or spider-queen support encounters

#### Carrion Lash Crawler

- Description: A ceiling-hugging scavenger whose twitching feeder tendrils numb prey long before the bite lands.
- Archetype: `carrion_lash_crawler`
- Suggested base sheet: level 3, 30 HP, AC 14, Maw Bite `1d6+2`, XP 125, Gold 0
- Tags and traits: `enemy`, `monstrosity`, features `ceiling_hunter`, `carrion_tentacles`
- Suggested runtime behavior:
  - `carrion_tentacles` once: CON save DC 13 or `poisoned` 2; if the target fails again at the end of its next turn, `paralyzed` 1
  - Prefers attacking targets already suffering `poisoned` or `reeling`
- Suggested encounter use:
  - Charnel tunnels, refuse pits, prison drains, or necromancer side rooms

#### Cache Mimic

- Description: A treasure chest, supply crate, or bedroll bundle that bites first, sticks fast, and punishes greed.
- Archetype: `cache_mimic`
- Suggested base sheet: level 3, 34 HP, AC 13, Crushing Bite `1d8+3`, XP 150, Gold 18
- Tags and traits: `enemy`, `monstrosity`, features `adhesive`, `false_appearance`, `greedy_lure`
- Suggested runtime behavior:
  - First creature to strike or loot it makes STR save DC 13 or becomes `grappled` 2
  - Bite against a `grappled` target deals an extra `1d8` acid damage
- Suggested encounter use:
  - Trap room solo threat, caravan ambush, or comic-relief fake reward that turns lethal

#### Stonegaze Skulker

- Description: A cave lizard with milky eyes and mineral-stained teeth that feeds on statues only after they stop screaming.
- Archetype: `stonegaze_skulker`
- Suggested base sheet: level 3, 36 HP, AC 15, Mineral Fangs `1d8+2`, XP 150, Gold 16
- Tags and traits: `enemy`, `monstrosity`, features `petrifying_gaze`, `stone_hide`
- Suggested runtime behavior:
  - `petrifying_gaze` once: CON save DC 13 or `restrained` 1; repeat next turn or become `petrified` 1
  - Bite deals an extra `1d4` poison damage against `restrained` targets
- Suggested encounter use:
  - Statue gardens, crystal caves, cursed quarries, or sanctum guardians

#### Shrieking Cliff Harpy

- Description: A ragged-wing predator that weaponizes hunger and grief through a song too beautiful to trust.
- Archetype: `cliff_harpy`
- Suggested base sheet: level 3, 32 HP, AC 13, Talons `2d4+1`, XP 150, Gold 14
- Tags and traits: `enemy`, `monstrosity`, features `luring_song`, `swoop`
- Suggested runtime behavior:
  - `luring_song` once: WIS save DC 13 or `charmed` 1 and `reeling` 1
  - `swoop` once: dives an isolated target; failed STR save DC 12 causes `prone`
- Suggested encounter use:
  - Sea cliffs, broken watchtowers, canyon bridges, or windy ruin approaches

#### Whispermaw Blob

- Description: A rolling knot of mouths and half-formed faces that warps sound, footing, and nerve all at once.
- Archetype: `whispermaw_blob`
- Suggested base sheet: level 3, 42 HP, AC 9, Gnashing Jaws `2d6`, XP 150, Gold 0
- Tags and traits: `enemy`, `aberration`, features `gibbering`, `warped_ground`, `blinding_spittle`
- Suggested runtime behavior:
  - Nearby creatures that start a turn close to it make WIS save DC 13 or gain `reeling` 1
  - `blinding_spittle` once: DEX save DC 13 or `blinded` 1
  - On high hit rolls, it can also force `prone`
- Suggested encounter use:
  - Aberrant tunnels, ritual failures, sinkhole chambers, or polluted caverns

#### Blackglass Pincerling

- Description: A glossy shell-hunter that waits in black water until the first warm body steps close enough to clamp.
- Archetype: `blackglass_pincerling`
- Suggested base sheet: level 4, 40 HP, AC 15, Shock Pincer `1d8+3`, XP 175, Gold 18
- Tags and traits: `enemy`, `aberration`, features `pincer_hold`, `shock_spines`
- Suggested runtime behavior:
  - On hit, target makes STR save DC 13 or becomes `grappled` 2
  - `shock_spines` once against a `grappled` target: CON save DC 13 or `paralyzed` 1
- Suggested encounter use:
  - Flooded mines, lake causeways, sewer sluices, or underpier ambushes

#### Graveblade Wight

- Description: A mailed dead captain that remembers formation drills, hates the living, and never wastes a clean opening.
- Archetype: `graveblade_wight`
- Suggested base sheet: level 4, 45 HP, AC 15, Barrow Blade `1d8+3`, XP 200, Gold 26
- Tags and traits: `enemy`, `undead`, `leader`, features `life_drain`, `sunken_command`
- Suggested runtime behavior:
  - `life_drain` once: CON save DC 14 or take `2d6` necrotic damage and gain `exhaustion` 1
  - `sunken_command` once: self and one undead ally gain `emboldened` 2
- Suggested encounter use:
  - Tomb guard, undead lieutenant, or centerpiece for a disciplined grave encounter

### Hard Expansion Enemies

#### Cinderflame Skull

- Description: A blazing skull orbited by ash sparks and guttering runes, happiest when the room is already on fire.
- Archetype: `cinderflame_skull`
- Suggested base sheet: level 4, 38 HP, AC 15, Cinder Bolt `2d6+2`, XP 200, Gold 24
- Tags and traits: `enemy`, `undead`, features `fire_burst`, `rekindle`
- Suggested runtime behavior:
  - `fire_burst` once: DEX save DC 14 or take `3d6` fire damage and gain `burning` 2
  - First time reduced to 0 HP, reforms with 10 HP at the end of the next round unless the remains are doused, shattered, or ritually suppressed
- Suggested encounter use:
  - Mage crypts, ash sanctums, artillery support for cult casters, or relic vault traps

#### Eye of the Obelisk

- Description: A floating shard-eye that patrols forbidden chambers and punishes any attention with disciplined bursts of force and terror.
- Archetype: `obelisk_eye`
- Suggested base sheet: level 4, 44 HP, AC 15, Psionic Ray `2d6+2`, XP 225, Gold 30
- Tags and traits: `enemy`, `aberration`, `leader`, features `eye_rays`, `levitation`, `allseeing`
- Suggested runtime behavior:
  - Each round, chooses one ray pattern:
    - WIS save DC 14 or `frightened` 2
    - CON save DC 14 or `blinded` 1 and `reeling` 1
    - STR save DC 14 or `restrained` 1
  - Prefers different targets each round to spread pressure across the party
- Suggested encounter use:
  - Vault sentry, puzzle chamber boss, or aberrant sanctum guardian

#### Iron Prayer Horror

- Description: A sealed suit of plate animated by old vows and anti-magic scripture hammered into the inside of the steel.
- Archetype: `iron_prayer_horror`
- Suggested base sheet: level 5, 52 HP, AC 17, Oathblade `1d10+3`, XP 250, Gold 35
- Tags and traits: `enemy`, `construct`, features `spellward_plating`, `relentless_march`
- Suggested runtime behavior:
  - Ignores the first `charmed`, `frightened`, or `incapacitated` effect applied each encounter
  - `shield_bash` once: STR save DC 14 or `prone` 1 and `reeling` 1
- Suggested encounter use:
  - Reliquary guardian, elite construct wall, or miniboss escort for a caster leader

#### Hookclaw Burrower

- Description: A cave terror that hunts by echo and drags screaming prey into side tunnels too narrow for help.
- Archetype: `hookclaw_burrower`
- Suggested base sheet: level 5, 54 HP, AC 16, Twin Hooks `1d8+3`, XP 250, Gold 22
- Tags and traits: `enemy`, `monstrosity`, features `blind_sense`, `echo_locator`, `cave_drag`
- Suggested runtime behavior:
  - `echo_locator` lets it ignore `blinded` penalties and prefer noisy or `reeling` targets
  - On hit, target makes STR save DC 14 or becomes `grappled` 2; if already `grappled`, the target also becomes `prone`
  - `shriek_pulse` once: CON save DC 14 or `deafened` 2
- Suggested encounter use:
  - Deep mine terror, pursuit anchor, or single-creature tunnel boss

#### Thunderroot Mound

- Description: A walking hill of roots, corpses, and rain-soaked soil that surges with stolen stormlight.
- Archetype: `thunderroot_mound`
- Suggested base sheet: level 5, 62 HP, AC 14, Root Lash `2d8`, XP 300, Gold 0
- Tags and traits: `enemy`, `plant`, features `grasping_vines`, `engulf`, `lightning_feed`
- Suggested runtime behavior:
  - Root Lash: STR save DC 14 or `restrained` 2
  - Against a `restrained` target, `engulf` once: deals `2d6` bludgeoning damage and applies `grappled` 2
  - In a future implementation, lightning damage can convert into temp HP or `emboldened`
- Suggested encounter use:
  - Storm groves, drowned gardens, druidic curses, or apex wilderness fights

#### Oathbroken Revenant

- Description: A deathless hunter wrapped in ruined heraldry and held together by a single unfinished vendetta.
- Archetype: `oathbroken_revenant`
- Suggested base sheet: level 6, 58 HP, AC 16, Vengeance Sword `1d10+3`, XP 325, Gold 45
- Tags and traits: `enemy`, `undead`, `leader`, features `vengeance_mark`, `relentless_return`
- Suggested runtime behavior:
  - `vengeance_mark` once: WIS save DC 14 or gain `reeling` 2 and become the revenant's preferred target
  - First time reduced to 0 HP, it stands again with 12 HP on its next turn if its marked target still lives
  - Hits against the marked target add `1d6` necrotic damage
- Suggested encounter use:
  - Personal nemesis, roaming stalker, or act boss with narrative memory

#### Choir Executioner

- Description: A masked cult champion who speaks only in verdicts and kills under fields of ritual silence.
- Archetype: `choir_executioner`
- Suggested base sheet: level 6, 64 HP, AC 16, Silent Greatsword `2d6+3`, XP 350, Gold 60
- Tags and traits: `enemy`, `humanoid`, `leader`, `parley`, features `hush_command`, `finishing_stroke`, `dark_devotion`
- Suggested runtime behavior:
  - `hush_command` once: WIS save DC 15 or `incapacitated` 1
  - `finishing_stroke`: weapon hits against `frightened`, `restrained`, or `incapacitated` targets deal an extra `2d6`
  - Hard to disrupt with fear or charm due to fanatic conditioning
- Suggested encounter use:
  - Cult elite, execution chamber boss, or commander for zealot waves

#### Duskmire Matriarch

- Description: An ancient marsh widow big as a wagon, draped in cocoons and half-dissolved mail from hunters who failed.
- Archetype: `duskmire_matriarch`
- Suggested base sheet: level 6, 72 HP, AC 17, Queen Fangs `2d8+3`, XP 450, Gold 70
- Tags and traits: `enemy`, `monstrosity`, `leader`, features `shadow_web`, `brood_command`, `widow_venom`
- Suggested runtime behavior:
  - `shadow_web` once: DEX save DC 15 or `restrained` 2 and `blinded` 1
  - `brood_command` once: self and beast/monstrosity allies gain `emboldened` 2
  - `widow_venom`: CON save DC 15 or `poisoned` 2; on a second failed save before the poison ends, `paralyzed` 1
- Suggested encounter use:
  - Apex spider boss, swamp dungeon finale, or optional monster-hunt target
