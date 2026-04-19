# Sword Coast Act 1 Content Reference

This file collects the current campaign-facing content that is most useful for debugging story flow, enemy setups, recruitment, and rewards.

The summary sections at the top reflect the expanded Act 1 route and should be treated as the current source of truth where they differ from older shorter-arc notes later in the file.

## Act 1 Scope

- Opening arc: background prologue -> Wayside Luck Shrine -> Greywake Triage Yard -> Greywake Road Breakout -> Neverwinter briefing -> High Road ambush -> Phandalin hub
- Branching middle route: `Old Owl Well` and `Wyvern Tor` can be tackled in either order, with a hidden optional strike into `Cinderfall Ruins`
- Convergence points: Stonehill war-room event, Ashfall Watch assault, Phandalin lantern vigil
- Late route: `Tresendar Manor` -> `Emberhall Cellars`
- Named minibosses: `Vaelith Marr`, `Brughor Skullcleaver`, and `Rukhar Cinderfang`
- Final boss: `Varyn Sable`
- Total potential Act 1 combats now comfortably exceeds 10 before counting random encounters
- New support hubs: Neverwinter's contract house, `Edermath Orchard`, `Miner's Exchange`, Stonehill war-room, and the post-Ashfall lantern vigil. Edermath Orchard now includes an optional old-cache stealth scene that becomes combat if the approach fails.
- Quest set currently defined in data: 13 Act 1 quests, including 5 inn quests across Neverwinter and Stonehill, 6 wider town or road quests, and 2 companion personal quests
- Reactivity layer now tracks `Town Fear`, `Ashen Strength`, and `Survivors Saved`, then resolves Act 1 as `clean_victory`, `costly_victory`, or `fractured_victory`

## Expanded Act 1 Route

1. Background-specific opening encounter or shortcut, then shared pre-Neverwinter Elira/Greywake sequence:
   Wayside Luck Shrine -> Greywake Triage Yard -> Greywake Road Breakout
2. Neverwinter setup, briefing, contract-house social hub, and optional Mira-assigned road companion
3. High Road ambush and Tolan recruitment point, with optional post-ambush side branches into `Liar's Circle`, `False Roadwarden Checkpoint`, and `False Tollstones`
4. Phandalin arrival, inn / shrine / shop / steward loops, orchard / exchange hubs, and a possible early `Cinderfall` reveal on a strong `Insight` read
   - Edermath Orchard can also reveal Daran's old adventurer's cache: a `Stealth` DC 12 route to recover `edermath_cache_compass`, or a watcher encounter on failure.
5. Old Owl Well route:
   dig-ring fight -> salt cart or supply trench branch -> Vaelith Marr miniboss
6. Wyvern Tor route:
   outer shelf fight -> drover hollow or shrine ledge branch -> Brughor Skullcleaver miniboss
7. Optional `Cinderfall Ruins` route if the hidden relay is uncovered:
   collapsed gate -> ash chapel or broken storehouse -> ember relay node
8. Stonehill war-room fixed event once both major side routes are cleared
9. Ashfall Watch route:
   gate fight -> prisoner yard / signal event -> lower barracks fight -> Rukhar miniboss
10. Lantern vigil fixed event back in Phandalin
11. Tresendar Manor route:
   cellar intake fight -> cistern event -> Cistern Eye roleplay boss / fight
   - Cistern Eye routes: kill it, trade a memory/truth/companion secret, bargain repeatedly, or deceive it.
   - Bargain and Deception routes can reveal Cinderfall relay context and Wave Echo / Forge foreshadowing before Emberhall.
   - The risky routes apply sanity-style combat pressure, `Whispered Through`, and companion trust costs.
12. Emberhall finale:
   antechamber fight -> chained clerk / ledger event -> Varyn boss fight

## Drafted Future Inserts

- `information/Story/HIGH_ROAD_LIARS_CIRCLE_PUZZLE_DRAFT.md`: optional post-ambush High Road wilderness branch built around four lying statues, with `Liar's Blessing` or `Liar's Curse` social-skill consequences.
- `information/Story/ACT1_PRE_NEVERWINTER_ELIRA_DRAFT.md`: implemented shared pre-Neverwinter opening insert that introduces Elira as the first companion candidate, gives her two early recruitment chances before the second major combat, and preserves the Phandalin shrine fallback.
- `information/Story/MIRA_NEVERWINTER_DIALOGUE_DRAFT.md`: implemented expanded Mira Thann question dialogue for the first Neverwinter briefing, conditional Greywake/Elira/Blackwake responses, and return-to-Neverwinter debriefs after Phandalin-side progress.
- `information/Story/COMPANION_CAMP_BANTER_DRAFT.md`: implemented companion-to-companion camp banter registry, Act 1 and Act 2 branching dialogue, gameplay and relationship consequences, and Act 3 secret-architect guardrails for keeping the second villain hidden until the planned midpoint reveal.

## Companion Reference

| Companion | Race / Class | Summary | Recruitment point | Relationship bonuses |
| --- | --- | --- | --- | --- |
| Kaelis Starling | Half-Elf Ranger | scout and ambush reader | optional contract companion in Neverwinter before the road | Great: `+1 Perception`, `+1 initiative`; Exceptional: `+1 attack` |
| Rhogar Valeguard | Dragonborn Paladin | oathsworn caravan guardian | optional contract companion in Neverwinter before the road | Great: `+1 damage`; Exceptional: `+1 AC` |
| Tolan Ironshield | Dwarf Fighter | shield-wall caravan veteran | joins after Roadside Ambush or later from the inn | Great: `+1 AC`; Exceptional: `+1 CON saves` |
| Bryn Underbough | Halfling Rogue | trail scout and rumor-reader | recruited at Stonehill Inn on Persuasion success | Great: `+1 Stealth`, `+1 initiative`; Exceptional: `+1 Perception` |
| Elira Dawnmantle | Human Cleric | shrine healer and faith anchor | first met at Wayside Luck Shrine, recruitable there or at Greywake before the second shared combat; if missed, recruited at Phandalin's shrine | Great: `+1 healing`; Exceptional: `+1 WIS saves` |

### Scene support hooks

- Kaelis: `road_ambush`, gives hero bonus and player Invisible
- Kaelis: `wyvern_tor`, gives hero bonus and party Emboldened
- Tolan: `ashfall_watch`, gives hero bonus and player Blessed
- Rhogar: `ashfall_watch`, gives hero bonus and player Blessed
- Bryn: `old_owl_well`, gives hero bonus and player Invisible
- Bryn: `emberhall_cellars`, gives hero bonus and player Invisible
- Elira: `camp_rest`, gives player Blessed before rest

### Great-threshold combat abilities

- Kaelis at disposition `6+`: `Shadow Volley`, which grants the conscious party `Invisible 1` at combat start
- Tolan at disposition `6+`: `Hold the Line`, which grants the conscious party `Guarded 2` at combat start

### Personal quest hooks and conflict beats

- Bryn at disposition `3+`: unlocks `Loose Ends`, which resolves once her old cache ledger is found through trench notes or the smuggler encounter chain
- Elira at disposition `3+`: unlocks `Faith Under Ash`, which resolves in Ashfall's lower barracks when you decide the fate of a captured zealot
- Bryn and Rhogar at disposition `6+` after `Cinderfall` sabotage: can trigger a trust-splitting conflict over whether the route list is buried or publicly exposed

### Relationship thresholds

- `0-2`: Neutral
- `3-5`: Good
- `6-8`: Great
- `9+`: Exceptional
- `-3` to `-5`: Bad
- `-6` or worse: companion leaves the company

## Enemy Archetypes

| Archetype | Display name | Level | HP | AC | Weapon | XP | Gold | Notes |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | --- |
| `goblin_skirmisher` | Goblin Skirmisher | 1 | 6 | 13 | Scimitar `1d4+1` | 50 | 4 | feature tag `nimble`, but no dedicated runtime hook yet |
| `wolf` | Ash Wolf | 1 | 11 | 13 | Bite `1d6+1` | 50 | 6 | Pack Tactics style behavior and prone rider |
| `worg` | Worg | 1 | 18 | 13 | Rending Bite `2d4+1` | 75 | 8 | stronger pack hunter with prone rider |
| `bandit` | Ashen Brand Bandit | 1 | 11 | 12 | Scimitar `1d6` | 50 | 8 | parley-capable basic humanoid |
| `bandit_archer` | Ashen Brand Lookout | 1 | 9 | 12 | Shortbow `1d6` | 50 | 9 | has once-per-fight control shots |
| `ash_brand_enforcer` | Ashen Brand Enforcer | 2 | 18 | 13 | Hooked Falchion `1d8+1` | 100 | 14 | punishes buffed or marked heroes and can strip `Blessed` |
| `ember_channeler` | Ember Channeler | 2 | 15 | 12 | Ember Brand `1d6+1` | 100 | 12 | support caster that applies `Marked` for team focus fire |
| `carrion_stalker` | Carrion Stalker | 2 | 17 | 14 | Serrated Talons `1d6+2` | 100 | 0 | stealth predator that opens Invisible and applies `Bleeding` |
| `skeletal_sentry` | Skeletal Sentry | 1 | 13 | 12 | Rusty Spear `1d6` | 50 | 2 | undead site defender used around Old Owl Well and the manor |
| `orc_raider` | Orc Raider | 1 | 16 | 14 | Battleaxe `1d8+1` | 75 | 10 | hill raider used at Wyvern Tor and sometimes Ashfall |
| `orc_bloodchief` | Orc Bloodchief | 2 | 33 | 15 | Great Axe `1d12+1` | 150 | 30 | named Wyvern Tor miniboss template with self-buff war cry |
| `ogre_brute` | Ogre Brute | 2 | 38 | 11 | Maul Club `2d8` | 125 | 18 | heavy hitter used in hill and boss-support fights |
| `gravecaller` | Gravecaller | 2 | 26 | 13 | Gravehook Dagger `1d6` | 125 | 24 | caster-style undead handler with fear and ash-blind control |
| `nothic` | Nothic | 2 | 29 | 14 | Hooked Claws `2d4` | 150 | 22 | manor horror with Weird Insight style control |
| `rukhar` | Rukhar Cinderfang | 2 | 27 | 16 | Longsword `1d8` | 125 | 35 | leader miniboss with poison and control |
| `varyn` | Varyn Sable | 2 | 38 | 14 | Blackened Rapier `1d8` | 200 | 60 | leader boss with charm, hex, petrify, poison, and rally |

## Enemy Behavior Details

### Wolf

- Gains practical Pack Tactics style advantage if any other enemy is conscious
- On hit, target makes STR save DC `11` or becomes Prone `1`

### Worg

- Uses the same pack-advantage and prone-rush behavior as the wolf template, but with sturdier HP and higher damage

### Bandit

- On high hit roll (`18+`) against a conscious target, target makes STR save DC `11` or becomes Grappled `1`

### Bandit Archer

- `snare_shot`: once, DEX save DC `12` or Restrained `2`
- `ash_shot`: once, DEX save DC `12` or Blinded `1`

### Ashen Brand Enforcer

- `punishing_strike`: once, lunges at a buffed or marked hero, adds an extra `1d6` slashing damage on hit, and strips `Blessed`
- Prefers targets carrying momentum buffs such as `Blessed`, `Emboldened`, or `Invisible`

### Ember Channeler

- `ember_mark`: once, WIS save DC `12` or target gains `Marked 2` and `Reeling 1`
- Teamwide synergy: enemies now prioritize `Marked` heroes when possible, so the mark acts like a visible focus-fire signal

### Carrion Stalker

- Opens combat with `Invisible 1`
- `shadow_hide`: once, can vanish again mid-fight
- On hit, applies `Bleeding 2`

### Gravecaller

- `grave_fear`: once, WIS save DC `12` or Frightened `2`
- `ash_veil`: once, CON save DC `12` or Blinded `1`

### Orc Bloodchief

- `war_cry`: once, gains `6` temp HP and Emboldened `2`

### Nothic

- `weird_insight`: once, WIS save DC `12` or Reeling `2`
- `rotting_gaze`: once, CON save DC `12` or Poisoned `2`
- On a high claw roll (`18+`), target makes WIS save DC `12` or becomes Frightened `1`

### Rukhar Cinderfang

- War Shout: once, CON save DC `12` or Deafened `2`
- Martial Advantage: adds `2d6` weapon damage while another enemy is still conscious
- Poisoned strike:
  - CON save DC `12` or take `1d4` poison and become Poisoned `2`
  - second CON save DC `12` or become Paralyzed `1`

### Varyn Sable

- Silver Tongue: once, WIS save DC `12` or Charmed `1`
- Binding Hex: once, WIS save DC `12` or Incapacitated `1`
- Ashen Gaze: once, CON save DC `12` or Petrified `1`
- Rally: once at half HP or below, gains `6` temp HP and Emboldened `2`
- Poisoned strike:
  - CON save DC `12` or take `1d4` poison and become Poisoned `2`
  - second CON save DC `12` or gain Exhaustion `2`

## Main Quests

| Quest id | Title | Giver | Location | Completion flag | Reward |
| --- | --- | --- | --- | --- | --- |
| `secure_miners_road` | Stop the Watchtower Raids | Tessa Harrow | Steward's Hall | `ashfall_watch_cleared` | `45 XP`, `25 gp` |
| `restore_barthen_supplies` | Keep the Shelves Full | Barthen | Barthen's Provisions | `ashfall_watch_cleared` | `30 XP`, `12 gp`, `bread_round x2`, `camp_stew_jar x1` |
| `reopen_lionshield_trade` | Reopen the Trade Lane | Linene Graywind | Lionshield Coster | `ashfall_watch_cleared` | `35 XP`, `18 gp`, `potion_healing x1`, `antitoxin_vial x1` |
| `marked_keg_investigation` | The Marked Keg | Mara Stonehill | Stonehill Inn | `marked_keg_resolved` | `70 XP`, `24 gp`, `innkeeper_credit_token x1` |
| `songs_for_the_missing` | Songs for the Missing | Sella Quill | Stonehill Inn | `songs_for_missing_jerek_detail`, `songs_for_missing_tam_detail`, `songs_for_missing_nera_detail` | `65 XP`, `18 gp`, `sella_ballad_token x1` |
| `quiet_table_sharp_knives` | Quiet Table, Sharp Knives | Nera Doss | Stonehill Inn | `quiet_table_knives_resolved` | `80 XP`, `28 gp`, `blackseal_taster_pin x1` |
| `find_dain_harl` | Bring Back Dain's Name | Jerek Harl | Stonehill Inn | `dain_harl_truth_found` | `85 XP`, `26 gp`, `harl_road_knot x1` |
| `false_manifest_circuit` | False Manifest Circuit | Sabra Kestrel | Oren Vale's Contract House | `false_manifest_oren_detail`, `false_manifest_vessa_detail`, `false_manifest_garren_detail` | `75 XP`, `24 gp`, `kestrel_ledger_clasp x1` |
| `silence_old_owl_well` | Silence Old Owl Well | Halia Thornton | Miner's Exchange | `old_owl_well_cleared` | `50 XP`, `24 gp`, `scroll_clarity x1` |
| `break_wyvern_tor_raiders` | Break the Wyvern Tor Raiders | Daran Edermath | Edermath Orchard | `wyvern_tor_cleared` | `50 XP`, `20 gp`, `greater_healing_draught x1` |
| `bryn_loose_ends` | Loose Ends | Bryn Underbough | personal / road chain | `bryn_loose_ends_resolved` | no listed item reward; resolves by ledger choice |
| `elira_faith_under_ash` | Faith Under Ash | Elira Dawnmantle | personal / Ashfall field scene | `elira_faith_under_ash_resolved` | no listed item reward; resolves by mercy or execution choice |

### Quest state logic

- Quests are stored as `active`, `ready_to_turn_in`, or `completed`
- `ready_to_turn_in` is computed from completion flags, not from scene position alone
- The journal view groups quests by readiness and appends accepted, ready, and completed notes over time
- Bryn and Elira's personal quests are auto-granted from trust thresholds instead of a town giver menu

## Act 1 Reactivity State

### Global metrics

- `act1_town_fear`
  - default `2`
  - lowered by public reassurance, rescues, and mercy choices
- `act1_ashen_strength`
  - default `3`
  - reduced by clearing enemy outer sites and can be driven to `0` by `Cinderfall` sabotage
- `act1_survivors_saved`
  - default `0`
  - raised through rescue branches such as Old Owl, Wyvern Tor, and Cinderfall

### Hidden route unlocks

- `Phandalin` arrival `Insight` success can reveal `Cinderfall Ruins`
- `Old Owl Well` supply trench notes can reveal `Cinderfall Ruins`
- `Wyvern Tor` rescued-drover follow-up can reveal `Cinderfall Ruins`

### Ashfall consequences

- Destroying the `Cinderfall` ember relay removes one lower-barracks reinforcement and prevents `Rukhar` from opening with his `4` temp HP reserve edge
- Jerek Harl's `Bring Back Dain's Name` now resolves in the Ashfall prisoner-yard line, with a command-post paperwork fallback if the player reaches `Rukhar` first
- Decoding Nera's upstairs quiet-room packet adds a special Ashfall command option that spends stolen countersign intel against `Rukhar`
- Elira's `Faith Under Ash` resolution also feeds into Ashfall's boss setup:
  - mercy grants a later `Blessed` opener
  - hard judgment increases pressure and hardens the finale tone

### Ending tiers

- `clean_victory`: low fear, low Ashen strength, enough survivors saved, and no major strained companion fallout
- `costly_victory`: the middle state when Phandalin wins but carries visible damage or tension
- `fractured_victory`: high fear, high remaining enemy pressure, or a strained late-game moral path with too few rescues
- The game records `act2_starting_pressure` from these outcomes so Act 2 can open under different levels of strain

## Early Story Recruitment And Encounter Notes

### Pre-Neverwinter Elira and Greywake sequence

- Background prologues now converge at `Wayside Luck Shrine` before Mira Thann's briefing.
- Elira Dawnmantle is introduced as the first companion candidate.
- First Elira recruitment chance:
  - Wayside Luck Shrine after helping with poison, prayer, road marks, or triage flow.
  - Helping Elira makes recruitment automatic or much easier.
- Second Elira recruitment chance:
  - Greywake Triage Yard before the Greywake Road Breakout.
  - Stabilizing the wounded line lowers the recruitment DC.
- Greywake Triage Yard is the systemic escalation:
  - the intake board and manifest sort travelers into `treat`, `hold`, and `lost` before the wagons arrive
  - Elira frames the second recruitment chance as leaving triage to stop the hand moving those outcome marks
  - successful Insight, Medicine, or Persuasion routes create a concrete evidence kind for Mira: marked manifest, matched triage tags, or yard witnesses
- Greywake Road Breakout is the shared second major combat:
  - Ashen Brand cutters try to steal or burn an outcome-marked manifest.
  - Preserving the manifest can set `system_profile_seeded` and `varyn_route_pattern_seen`.
  - If Elira is recruited, she can bless the player before the fight.
  - If Elira is not recruited, she protects the wounded line and later appears at Phandalin's Shrine of Tymora.

### Neverwinter briefing

- The player can choose:
  - Kaelis Starling
  - Rhogar Valeguard
- Elira may already be in the party before this choice; Mira's road companion can still be assigned afterward if party space allows.
- If the player carries Greywake proof into the briefing, Mira reacts directly: the evidence proves the Ashen Brand is coordinating outcomes, not merely causing damage.
  - Early Elira recruitment prompts Mira to note that the road is already worse than her reports.
  - A preserved manifest is treated as a schedule, not a forged report.
  - A burned manifest shifts the plan to witness testimony.
  - Protected wounded become angry, living witnesses.
- Oren Vale's contract house now acts as the city-side inn and social pressure valve before departure:
  - Oren Vale keeps the room, the witnesses, and the upstairs private arrangements
  - Sabra Kestrel grants `False Manifest Circuit`
  - Vessa Marr runs the card table and smoke-side rumor line
  - Garren Flint exposes how copied roadwarden cadence keeps getting obeyed
- `False Manifest Circuit` is a Neverwinter inn quest built from Oren, Vessa, and Garren's separate details, then turned back in to Sabra
- Completing Sabra's quest unlocks an upstairs private-room scene that turns contract-house politics into Blackwake and High Road intelligence
- Oren/Sabra/Garren proof can also collapse the `False Roadwarden Checkpoint` before Blackwake, making the contract-house thread pay off on the road itself
- That private-room intel can be spent at Blackwake to corner Sereth Vane directly, then echoed through Mira's Neverwinter report if Oren, Sabra, Vessa, and Garren become public witnesses
- `Ash In The Ale` can break out in the room if the player mishandles Vessa's table or pushes Garren too hard

### Roadside Ambush

- Small parties receive encounter scaling help:
  - solo players get weakened enemies, temp HP, Blessed, and initiative help
  - duo parties get lighter scaling support
- The player chooses an opening approach:
  - Athletics rush
  - Stealth flank
  - Intimidation warning
- On victory:
  - clue: the goblins carry Ashen Brand markings
  - clue: the raiders answer to a hobgoblin sergeant tied to Ashfall Watch
  - extra reward: `25 XP`, `15 gp`
  - Tolan can be recruited immediately or left waiting at the inn
- Post-ambush side branches:
  - `Liar's Circle`: a four-statue logic puzzle that grants `Liar's Blessing` or applies `Liar's Curse`
  - `False Roadwarden Checkpoint`: a non-combat social stop with Deception, Insight, Persuasion, Intimidation, or Oren/Sabra/Garren proof
  - `False Tollstones`: a broken milemarker operation that changes if the player has `Liar's Blessing`

### Stonehill Inn

- Bryn can be recruited with Persuasion DC `12`
- If Tolan was sent to recover instead of recruited on the road, he can be picked up here
- New regulars now anchor the inn scene:
  - Mara Stonehill, who runs the common room and grants `The Marked Keg`
  - Jerek Harl, whose grief and anger now anchor `Bring Back Dain's Name`
  - Sella Quill, a singer who grants `Songs for the Missing`
  - Old Tam Veller, a ruin-minded prospector who still remembers honest route details
  - Nera Doss, a courier whose split lip leads into `Quiet Table, Sharp Knives`
- The Stonehill inn now supports:
  - an inn sabotage investigation around a chalk-marked keg
  - Jerek's missing-brother route quest, which ties Stonehill grief directly to Ashfall Watch
  - a memory-ballad quest built from Jerek, Tam, and Nera's true details
  - a quiet-table whisper scheme that can roll into a skill-resolved barfight
  - an upstairs quiet-room reward scene that decodes stolen courier intel for later Ashfall and Emberhall use
  - a memorial follow-up where Sella's song changes once Dain Harl's fate is brought home
  - `Liar's Blessing` options in the keg, quiet-table, and quiet-room scenes
- Stonehill's inn rewards now echo into Act 2:
  - `Harl Road-Knot` opens a special route-reading option at Stonehollow Dig
  - the quiet-room courier intel opens a special order-seizure option at Black Lake and is named during the claims council

### Shrine

- If Elira was not recruited at Wayside or Greywake, she appears at Phandalin's Shrine of Tymora.
- Early failed recruitment attempts do not lock her out.
- If `elira_phandalin_fallback_pending` is set, asking her to join in Phandalin recruits her without another skill gate.
- If the player has no early Elira fallback and has not helped her, the normal recruitment check remains Persuasion DC `8`.

## Post-Combat Random Encounter Chains

- `Wounded Messenger`
  - a successful rescue sets up `Messenger Returns`, where the same courier can come back later with coin, healing supplies, and more road intel
- `Smuggler Cookfire`
  - if the camp is disrupted, it can unlock `Smuggler Revenge Squad`
  - if Bryn's personal quest is active, the cookfire can also expose her old cache
- `Abandoned Cottage`
  - once Bryn's cache trail is live, the cellar holdout can point toward `Emberhall`

## Story Flags Worth Watching

These flags show up repeatedly in Act 1 flow and are useful when debugging saves or scene transitions.

- `background_prologue_pending`
- `act1_started`
- `wayside_luck_shrine_seen`
- `elira_first_contact`
- `elira_wayside_recruit_attempted`
- `elira_pre_neverwinter_recruited`
- `greywake_triage_yard_seen`
- `elira_greywake_recruit_attempted`
- `elira_greywake_recruited`
- `greywake_breakout_resolved`
- `greywake_manifest_preserved`
- `elira_phandalin_fallback_pending`
- `elira_phandalin_recruited`
- `early_companion_recruited`
- `road_approach_chosen`
- `tolan_waiting_at_inn`
- `inn_recruit_bryn_attempted`
- `shrine_recruit_attempted`
- `elira_helped`
- `hidden_route_unlocked`
- `cinderfall_relay_destroyed`
- `bryn_cache_found`
- `edermath_old_cache_recovered`
- `act2_edermath_cache_routework`
- `high_road_false_checkpoint_exposed`
- `neverwinter_contract_house_checkpoint_pressure`
- `bryn_ledger_burned`
- `bryn_ledger_sold`
- `elira_mercy_blessing`
- `elira_hard_verdict`
- `act1_companion_conflict_side`
- `act1_town_fear`
- `act1_ashen_strength`
- `act1_survivors_saved`
- `act1_victory_tier`
- `act2_starting_pressure`
- `ashfall_watch_cleared`

## Debugging Pointers

- Enemy special behavior is keyed by `archetype`, so a renamed enemy still uses the base archetype logic
- Companion scene support only activates when the companion is in the active party and has disposition `6+`
- Great-threshold companion combat openers are separate from scene-support bonuses, so a companion can matter both in the room setup and again when initiative starts
- Quest completion is mostly flag-driven, so a missing `completion_flag` is often more important than a missing journal entry
- The same companion can be offered from multiple story branches, but `has_companion()` prevents duplicate recruitment
