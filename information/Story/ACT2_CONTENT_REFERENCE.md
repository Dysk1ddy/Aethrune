# Aethrune Act 2 Content Reference

This file collects the approved design target for Act 2. Unlike `information/Story/ACT1_CONTENT_REFERENCE.md`, this is currently a planning and scaffolding document rather than a summary of already playable scenes, so it should be treated as the source of truth for future implementation work unless later story revisions replace it.

The tone and structure now target the original Aethrune frame: Iron Hollow politics, the Vein of Glass, the Resonant Vaults, and the Quiet Choir's attempt to control what the old systems remember.

## Act 2 Scope

- Opening arc: Act 1 aftermath -> Ashlamp claims council -> expedition sponsorship choice -> first lead
- Early branching route: dead-testimony circuit, Greywake Survey Camp, and `Stonehollow Dig`
- Early side-delve candidate: `Glasswater Intake` can slot between the first and second cleared early leads as a medium optional dungeon about water control, courier traffic, claims fraud, and the first practical signs of whisper contamination
- Early route rule: any two leads let the player trigger the midpoint, but delaying the third now causes a permanent consequence before that lead can be recovered later
- First new recruitable companion: `Nim Ardentglass` enters through `Stonehollow Dig`, but recruiting him late changes his trust and the quality of the recovered survey truth
- Midpoint convergence: sponsor tension -> sabotage night -> protect a priority and accept what slips through elsewhere
- Late branching route: `Broken Prospect` and `South Adit` are both required before the deeper cave, but can be taken in either order and materially wound each other when delayed
- Second new recruitable companion: `Irielle Ashwake` can be freed and recruited during `South Adit`, with stronger or weaker entry depending on how late the rescue comes
- Finale: `Resonant Vault Outer Galleries` -> `Blackglass Causeway` -> `Meridian Forge`
- Final boss: `Sister Caldra Voss`, a Quiet Choir cult agent using an obelisk shard to turn the Forge into a listening lens
- Total potential Act 2 combats should comfortably exceed 12 before counting random encounters
- Act 2 now tracks three structural pressures in the scaffold:
  - `Town Stability`: how intact Iron Hollow stays as a political and human community
  - `Route Control`: how much of the expedition map your side genuinely owns
  - `Whisper Pressure`: how much of the mine's wrong resonance is escaping containment

## Story Spine

- Varyn Sable's ledgers do more than point to the Resonant Vaults. They reveal that the Ashen Brand were functioning as a buffer force, keeping prospectors, merchants, town leaders, and rival diggers away from older Meridian routes until somebody better prepared could claim them.
- The act's public conflict is a frontier claims war. Its private conflict is stranger: the Quiet Choir has found an obelisk shard below the Vaults and realized the Meridian Forge can be used not just to repair, but to listen.
- In this version of Act 2, Caldra Voss is not trying to merely seize a treasure site. She is trying to tune the Vaults into a resonant instrument capable of hearing something farther down and farther away than any ordinary ruin should answer.
- The act should therefore feel layered:
  - first as a political fight over who gets to name the future of Iron Hollow
  - then as an expedition race where incomplete information is more dangerous than monsters
  - then as a ruin-crawl where old Meridian custody rules and the Quiet Choir are competing to define what the Vaults mean
  - and only near the end as obvious cosmic wrongness

## Act 1 Carryover

Act 2 should not start from a blank emotional or strategic slate. Several Act 1 choices now push directly into the opening metrics and later scene texture.

| Act 1 carryover | Typical source | Act 2 consequence |
| --- | --- | --- |
| `act1_victory_tier`, `act2_starting_pressure` | Act 1 ending state after Varyn falls | changes how strained Iron Hollow feels at the start of the expedition and how much immediate pressure the claims war opens under |
| `steward_vow_made`, `phandalin_council_seen` | choosing to speak for the town and help shape its defenses | raises starting `Town Stability`; the town enters the claims war with more nerve |
| `elira_helped` and whether Elira joined | shrine aid and recruitment | lowers starting `Whisper Pressure`; Agatha and Black Lake scenes become more grounded in mercy instead of panic |
| `miners_exchange_dispute_resolved`, `miners_exchange_ledgers_checked` | Act 1 Miner's Exchange path | raises starting `Route Control`; Halia is easier to justify as a sponsor, but the player also sees her more clearly |
| `act2_edermath_cache_routework` | recovering Daran Edermath's old adventurer's cache at the orchard | raises starting `Route Control`; Act 2 status text can cite the quiet orchard-to-highland control line |
| `early_companion_recruited` | Kaelis or Rhogar in Greywake | Kaelis improves route logic; Rhogar improves civic steadiness |
| `neverwinter_contract_house_political_callback` | spending contract-house intel in Blackwake or Mira's Greywake follow-up report | raises starting `Route Control`; Oren, Sabra, Vessa, and Garren create city-side witness pressure against copied road authority |
| `bryn_ledger_sold` vs `bryn_ledger_burned` | `Loose Ends` personal quest | selling the ledger pushes more pressure and distrust into the expedition opening; burning it makes the town start cleaner but poorer |
| `elira_mercy_blessing` vs `elira_hard_verdict` | `Faith Under Ash` personal quest | shapes whether frontier justice enters Act 2 as hopeful mercy or hard deterrence |
| Recruiting Bryn, Tolan, or Elira | Act 1 town companion work | each companion now supplies Act 2 sidetrack decisions that change later story pressure instead of only flavor text |

## Consequence Systems

- `Town Stability`
  - Represents whether Iron Hollow still acts like a community under stress or a marketplace under siege.
  - Low values mean panic, fractured aftermath, and a weaker Act 3 handoff.
  - High values mean survivor trust, better morale, and a stronger social base for later acts.
- `Route Control`
  - Represents how much clean survey truth, logistics, and trustworthy access your side actually possesses.
  - Low values mean rivals and cultists keep rewriting the map faster than you can.
  - High values mean you reach the cave on terms closer to your own.
- `Whisper Pressure`
  - Represents how much the mine's altered resonance has escaped into the act.
  - Low values mean the party is containing the Choir's influence.
  - High values mean the act ends with more obvious contamination feeding Act 3.
- `Sponsor Choice`
  - `Halia / Exchange`: faster routework, more leverage, more greed, higher risk of feeding the wrong parts of the race
  - `Linene / Lionshield`: steadier logistics, cleaner discipline, more defensible claims posture
  - `Elira + Daran / Wardens`: slower but morally firmer expedition, lower whisper seepage, stronger human consequences
- `Delayed Lead Rule`
  - Once the player advances to sabotage night with one early lead unresolved, that lead is marked as delayed.
  - The content remains recoverable later, but the damage of delaying it is already done and should never be fully undone.
- `Late Route Order`
  - `Broken Prospect` first means the route race improves while the prisoners suffer for the delay.
  - `South Adit` first means more captives live while rival claimants and cult sentries harden the route race elsewhere.

## Core Premise

- Varyn Sable's ledgers confirm that the Ashen Brand were not acting alone; they were keeping treasure hunters, miners, and local authorities away from older Meridian routes tied to the Resonant Vaults.
- Several factions now want what lies beneath the Vein of Glass:
  - honest miners and traders who want the region reopened
  - practical opportunists who want rights, salvage, and leverage
  - the Quiet Choir, a hidden cult cell studying a buried obelisk shard through the Vaults' lingering resonance
- The act should feel like a frontier recovery story giving way to an expedition race, then to a magical ruin crawl, and only near the end to unmistakable cosmic wrongness.

## Expanded Act 2 Route

1. Act 1 aftermath in Iron Hollow and a claims council at the Delvers' Exchange
2. Sponsor choice: decide whether speed, discipline, or caution defines the expedition's first tone
3. First lead selection and opening expedition prep
4. Optional side-delve: `Glasswater Intake` can open after the first cleared early lead as a medium dungeon that reshapes metrics and later route reads without replacing a core lead
5. Early lead A: dead-testimony circuit
6. Early lead B: Greywake Survey Camp
7. Early lead C: `Stonehollow Dig`
8. Once any two early leads are cleared, the player can trigger `Sabotage Night`
9. If the third lead is delayed, it remains playable later but its damage is already written into the campaign state
10. Midpoint convergence:
   the player chooses what to protect first in Iron Hollow and accepts a matching loss elsewhere
11. Late route A: `Broken Prospect`
12. Late route B: `South Adit`
13. The order of 11 and 12 materially changes captives, route posture, and companion texture
14. `Resonant Vault Outer Galleries`
15. `Blackglass Causeway`, now framed as a shrine / barracks / causeway-priority decision instead of a straight bridge fight
16. `Meridian Forge`
17. Act end summary records not just victory, but what kind of victory it was

### Drafted Early Side-Dungeon

- `Glasswater Intake`
  - Best unlocked after the first cleared early lead and before `Sabotage Night`.
  - Functions as a medium optional dungeon that foreshadows the Resonant Vaults by way of waterworks, courier ledgers, claims fraud, and containment choices instead of full late-act spectacle.
  - Intended to carry 4 to 5 encounter beats, one real finale, and multiple metric-facing choices rather than reading like a throwaway side room chain.
  - Its final chamber can center on `Brother Merik Sorn`, a Quiet Choir field operator who treats water pressure, logistics discipline, and doctrine as the same system.
  - Full draft: `information/Story/ACT2_GLASSWATER_INTAKE_DRAFT.md`
- Additional branch-heavy location packets:
  - `information/Story/ACT2_LOCATION_BRANCH_PACKETS.md` collects deeper multi-stage branch webs for the dead-testimony circuit, Greywake Survey Camp, `Stonehollow Dig`, `Broken Prospect`, and Blackglass Causeway.
  - `information/Story/ACT2_CONYBERRY_AGATHA_DRAFT.md` is a legacy implementation draft for the dead-testimony circuit; keep only the warning-custody structure and replace old names during implementation.

## Choice Web

### Early lead consequences

- Delay the dead-testimony circuit
  - The player reaches sabotage night without the full warning.
  - `Whisper Pressure` rises and the southern adit stays less clearly mapped.
  - Recovering the circuit later still matters, but it becomes a damaged warning rather than a clean one.
- Delay Greywake Survey Camp
  - The saboteur line feeds directly into the midpoint riot.
  - `Town Stability` and `Route Control` both drop because the enemy reaches town through confusion and false routework.
  - Recovering the wood later stops future damage, but cannot erase the riot's cost.
- Delay `Stonehollow`
  - The survey truth reaches the party late and incomplete.
  - `Route Control` falls and `Whisper Pressure` rises because the deeper dig sat under resonance longer.
  - Nim can still be recruited, but his trust and the quality of his notes should reflect the delay.

### Midpoint priority consequences

- Save the claims hall first
  - Best for preserving policy, leadership, and civic structure.
  - Risks letting hidden knives escape in the smoke.
- Save the shrine lane and civilians first
  - Best for human cost and public trust.
  - Risks weakening the formal claims apparatus or sponsor confidence.
- Hunt the infiltrator cell first
  - Best for keeping the expedition map from being rewritten in secret.
  - Risks making the town feel abandoned in its most frightened hour.

### Late-route order consequences

- `Broken Prospect` first
  - Stronger route position, cleaner approach, firmer expedition leverage.
  - The player reaches `South Adit` later and sees more irreversible loss among the captives.
- `South Adit` first
  - More lives saved, stronger moral authority, better human memory of the expedition.
  - The route race hardens elsewhere and `Broken Prospect` becomes a meaner recovery scene.

## Hidden Truth Under The Resonant Vaults

- Old Meridian custody rules did not merely share a profitable site. They also functioned as a discipline of listening and restraint. The Vaults' echoing properties were useful, but dangerous enough that access, route knowledge, and sacred obligations were distributed so that no single claimant could weaponize the whole site alone.
- The Meridian Forge matters because it can amplify whatever intention is fed into it. In careful hands, that means repair and controlled wonder. Under the Quiet Choir, it becomes a listening lens aimed through the Vaults' natural resonance.
- Sister Caldra Voss should therefore read less like a greedy necromancer-in-a-dungeon and more like a field theologian of something cosmic and wrong. She believes revelation is not spoken to mortals directly because mortals are too loud. The Choir's work is to make the world quiet enough to hear what was always there.
- The horror of Act 2 is that she is partly right. The Vaults do answer. The problem is what answers back.
- This lets Act 3 escalate naturally:
  - if `Whisper Pressure` stayed low, Act 3 begins as containment after a near miss
  - if `Whisper Pressure` stayed medium, Act 3 begins with fragments already leaking into dreams, notes, and rituals
  - if `Whisper Pressure` stayed high, Act 3 begins with the party having carried part of the signal out themselves
  - if `act3_forge_route_state` is `mastered`, Act 3 begins with the Forge already broken across all three subroutes
  - if `act3_forge_route_state` is `broken` or `partial`, later scenes should remember exactly which Forge lines were actually cleared through `act3_forge_subroutes_cleared`
  - if `act3_forge_lens_state` is `mapped`, later dialogue can speak concretely about how Caldra held witness, ritual, and shard pressure together
  - if `act3_forge_lens_state` is `shattered_blind`, later scenes should work from rumor, damage patterns, and surviving echoes instead of a clean explanation

## New Companion Reference

| Companion | Race / Class | Summary | Recruitment point | Relationship bonuses |
| --- | --- | --- | --- | --- |
| Nim Ardentglass | Unrecorded Wizard | Pact cartographer and practical ruin scholar | joins after a rescue or breakthrough around `Stonehollow Dig` or the first early-route convergence | Great: `+1 Arcana`, `+1 Investigation`; Exceptional: `+1 spell attack` |
| Irielle Ashwake | Fire-Blooded Warlock | escaped cult augur trying to stay ahead of the whispers that marked her | freed during `South Adit` around the late-act 70 percent mark | Great: `+1 spell damage`, `+1 Insight`; Exceptional: `+1 WIS saves` |

### Scene support hooks

- Nim: `stonehollow_dig`, gives hero bonus and player Blessed
- Nim: `wave_echo_outer_galleries`, gives hero bonus and enemy Reeling; public text should call this the Resonant Vaults.
- Nim: `forge_of_spells`, reads support traffic aloud at the threshold so the Meridian Forge feels like routework as well as spectacle.
- Irielle: `south_adit`, gives hero bonus and player Invisible
- Irielle: `forge_of_spells`, gives hero bonus and enemy Frightened, and now speaks into the resonance-lens / counter-cadence reads directly.

## Companion Arc Hooks

Act 2 should deepen the whole party by revealing personal history through optional side tracks, not mandatory main-path bottlenecks. Each arc now needs a decision with a real campaign-facing consequence, not just a disposition increase.

| Companion | Optional quest id | Primary location | Theme | Decision | Persistent payoff |
| --- | --- | --- | --- | --- | --- |
| Kaelis Starling | `ashes_in_the_boughs` | Greywake Wood | old scout loyalties, guilt, and the cost of reading danger too well | preserve a hidden trail or burn it | better route speed vs stronger town security |
| Rhogar Valeguard | `oath_beneath_stone` | sealed miners' chapel | oath, mercy, and whether duty means guarding relics or people first | anchor his oath in the town or the threshold | stronger civic stability vs lower whisper seepage |
| Tolan Ironshield | `last_wagon_standing` | Broken Prospect road | caravan memory, survivor anger, and whether pragmatism is moral enough | salvage tainted structure or destroy profitable wrongness | better route control vs cleaner spiritual state |
| Bryn Underbough | `false_ledgers` | Miner's Exchange / sponsor stores | smuggling instincts, bad old contacts, and choosing who gets trusted with the truth | quietly falsify bad ledgers or expose the scheme in public | better covert route leverage vs stronger civic trust |
| Elira Dawnmantle | `lantern_of_tymora` | dead-testimony chapel ruins | faith under pressure, grief, and whether hope is luck or discipline | carry the warding lantern into the field or leave it in town | lower whisper pressure vs higher town stability |
| Nim Ardentglass | `missing_theorem` | South Adit archive room | mentor legacy, academic pride, and whether knowledge is worth carrying out intact | preserve the dangerous theorem or burn its corrupted pages | stronger forge options vs safer Act 3 contamination profile |
| Irielle Ashwake | `starved_signal` | Blackglass shrine | resisting the cult's hold and deciding whether dangerous knowledge should be destroyed or studied | teach the counter-cadence or bury it | stronger forge opening vs cleaner containment into Act 3 |

## Act 2 Exclusive Item Spotlight

These items have been added to the catalog source so future encounter, quest, and loot placement can reference them directly.

| Item id | Name | Category | Design role | Intended source style |
| --- | --- | --- | --- | --- |
| `miners_ration_tin` | Miner's Ration Tin | supply | denser expedition food than Act 1 road provisions | survey packs, dwarf camps, and mine lockers |
| `mushroom_broth_flask` | Mushroom Broth Flask | supply | warm underground comfort item for camp flavor | ruined kitchens, watchfires, and miner stores |
| `delvers_amber` | Delver's Amber | consumable | temp HP and anti-fear support for cave descents | Stonehollow and expedition caches |
| `resonance_tonic` | Resonance Tonic | consumable | anti-reeling / MP support for ruin casters | Agatha lead rewards and arcane vaults |
| `forge_blessing_elixir` | Forge-Blessing Elixir | consumable | late-act courage draught with blessed synergy | forge reliquaries and elite cult loot |
| `thoughtward_draught` | Thoughtward Draught | consumable | anti-charm / anti-fear counterplay for whisper magic | ward caches and prisoner escape kits |
| `scroll_echo_step` | Scroll of Echo Step | scroll | stealth / escape tool that rewards smart disengage play | scout tubes and hidden script lockers |
| `scroll_counter_cadence` | Counter-Cadence Script | scroll | one-shot anti-whisper cleanse with a small courage swing | South Adit caches and prisoner counter-cult kits |
| `scroll_quell_the_deep` | Scroll of Quell the Deep | scroll | healing plus mental-condition cleanse | shrines, chapels, and anti-cult aid |
| `scroll_forge_shelter` | Scroll of Forge Shelter | scroll | protective forge buff before key combats | annex vaults and late quest rewards |
| `delver_lantern_hood_*` | Delver Lantern Hood | equipment | perception / investigation head slot for expedition play | survey caches and side chambers |
| `echostep_boots_*` | Echostep Boots | equipment | balance and initiative gear for cave movement | stealth-oriented act rewards |
| `forgehand_gauntlets_*` | Forgehand Gauntlets | equipment | strength-bracing gloves for frontliners | smithies and Resonant Vault tool caches |
| `sigil_anchor_ring_*` | Sigil Anchor Ring | equipment | anti-whisper ring for Arcana users and mind-defense builds | cult reliquaries and deep vaults |
| `choirward_amulet_*` | Choirward Amulet | equipment | wisdom-heavy warding neck slot item | shrine caches and rescued prisoners |

## Enemy Archetypes

These enemies should carry the act's thematic load: cave pressure, expedition rivalry, haunted labor, and a cult operating behind more mundane greed.

| Archetype | Display name | Level | HP | AC | Weapon | XP | Gold | Notes |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | --- |
| `expedition_reaver` | Rival Expedition Reaver | 2 | 18 | 13 | Hatchet `1d6+2` | 75 | 10 | practical treasure-hunter willing to parley, lie, or bolt |
| `cult_lookout` | Quiet Choir Lookout | 2 | 16 | 13 | Shortbow `1d6+2` | 75 | 9 | uses blind-dust, marked shots, and retreat angles |
| `choir_adept` | Quiet Choir Adept | 3 | 24 | 13 | Ritual Knife `1d6+1` | 125 | 22 | whisper caster with charm / fear pressure |
| `grimlock_tunneler` | Grimlock Tunneler | 2 | 20 | 14 | Hooked Blade `1d6+2` | 100 | 6 | tunnel ambusher that punishes disoriented targets |
| `stirge_swarm` | Stirge Swarm | 2 | 17 | 14 | Proboscis `1d6` | 75 | 0 | fast nuisance fight for cramped approaches |
| `ochre_slime` | Ochre Slime | 2 | 28 | 8 | Pseudopod `2d6` | 100 | 0 | slow acid body used in chokepoints and side chambers |
| `animated_armor` | Pact Sentinel Armor | 2 | 26 | 16 | Gauntlet Slam `1d6+2` | 100 | 12 | old mine guardian animated by lingering forge magic |
| `spectral_foreman` | Spectral Foreman | 3 | 31 | 14 | Phantom Pick `1d8+2` | 150 | 18 | dead shift boss used in haunted labor scenes |
| `starblighted_miner` | Starblighted Miner | 3 | 29 | 13 | Rusted Pick `1d8+1` | 125 | 14 | miner twisted by shard exposure and whisper-static |
| `caldra_voss` | Sister Caldra Voss | 4 | 42 | 15 | Shard Dagger `1d8+2` | 250 | 70 | final cult agent boss with charm, reeling, petrify hints, and rally tools |

## Enemy Behavior Details

### Quiet Choir Lookout

- `blind_dust`: once, DEX save DC `13` or Blinded `1`
- `marked_shot`: once, next ranged hit deals `+1d6` damage

### Quiet Choir Adept

- `hush_prayer`: once, WIS save DC `13` or Charmed `1`
- `discordant_word`: once, WIS save DC `13` or Frightened `2`

### Grimlock Tunneler

- On hit against a target already Reeling, deals `+1d4` damage
- On a high hit roll (`18+`), target makes CON save DC `13` or becomes Reeling `1`

### Stirge Swarm

- On hit, target makes STR save DC `12` or becomes Grappled `1`
- If the target stays Grappled into the swarm's next turn, it deals `1d4` extra damage

### Ochre Slime

- On hit, target takes `1d4` acid and gains Acid `2`
- Splitting on slashing damage is good flavor if later runtime support appears, but is not required for first implementation

### Pact Sentinel Armor

- Critical hits against it should feel ineffective even before dedicated adamantine-style runtime support exists
- `lockstep_bash`: once, STR save DC `13` or target becomes Prone `1`

### Spectral Foreman

- `dead_shift`: once, WIS save DC `13` or Frightened `2`
- `hammer_order`: once, CON save DC `13` or Deafened `2`

### Starblighted Miner

- `whisper_glare`: once, WIS save DC `13` or Charmed `1`
- On a high hit roll (`18+`), target makes WIS save DC `13` or becomes Reeling `2`

### Sister Caldra Voss

- `obelisk_whisper`: once, WIS save DC `14` or Charmed `1` and Reeling `2`
- `shard_veil`: once, CON save DC `14` or Petrified `1`
- `quiet_choir_rally`: once at half HP or below, gains `8` temp HP and Emboldened `2`
- `echo_step`: once, becomes Invisible `1` before the next exchange

## Main Quests

| Quest id | Title | Giver | Location | Trigger | Reward |
| --- | --- | --- | --- | --- | --- |
| `recover_pact_waymap` | Recover the Pact Waymap | Halia Thornton | Miner's Exchange | offered during the first claims council if the player presses the mine-history angle | `60 XP`, `28 gp`, `resonance_tonic x1` |
| `seek_agathas_truth` | Ask the Banshee What Was Buried | Elira Dawnmantle | shrine / Conyberry route | offered after the player follows chapel or spiritual clues | `55 XP`, `scroll_quell_the_deep x1` |
| `rescue_stonehollow_scholars` | Bring Back the Survey Team | Linene Graywind | Stonehollow Dig | offered if the player asks about missing hired specialists | `60 XP`, `22 gp`, `miners_ration_tin x2` |
| `cut_woodland_saboteurs` | Break the Woodland Saboteurs | Daran Edermath | orchard / woodland route | offered if the player pushes the road-and-ranger angle | `60 XP`, `25 gp`, `delvers_amber x1` |
| `hold_the_claims_meet` | Hold the Claims Meeting Together | Linene Graywind | Iron Hollow | triggers automatically once any two early leads are cleared | `50 XP`, `18 gp`, sponsor reputation flag |
| `free_wave_echo_captives` | Free the South Adit Prisoners | Elira Dawnmantle | South Adit | offered when the resonance cells are discovered | `70 XP`, `30 gp`, `scroll_echo_step x1` |
| `sever_quiet_choir` | Sever the Quiet Choir | town council | Resonant Vaults | becomes active once Caldra and the cult cell are positively identified | `100 XP`, `40 gp`, `forge_blessing_elixir x1` |

### Quest state logic

- Quests should still use `active`, `ready_to_turn_in`, and `completed`
- Several Act 2 quests are conversation-triggered rather than purely location-triggered
- Companion arcs should journal separately from main quests so they do not crowd out the main expedition beats

## Random Encounter Pool: Act 2 Exclusive

These encounters are designed to be suspenseful, fast, and thematically aligned with expedition play, old mines, and creeping whisper-lore. They may lead to combat, but should just as often resolve through one or two meaningful choices.

Implementation note for later: add an act-scope field such as `act_exclusive` or `act_tags` so the existing road pool becomes `act1`, the entries below become `act2`, and the eventual cosmic pool can cleanly become `act3`.

| Encounter id | Title | Usual resolution | Notes |
| --- | --- | --- | --- |
| `silent_mule_train` | Silent Mule Train | investigation / animal handling / optional combat | abandoned ore mules dragging cut harness bells through the dark |
| `lantern_in_the_wash` | Lantern in the Wash | investigation / loot | washed-out lantern, map tube, and one unsettling sign of cult traffic |
| `hushed_pilgrims` | Hushed Pilgrims | social / protection | frightened travelers from Conyberry share warnings and rumors |
| `buried_wheel_rut` | Buried Wheel Rut | survival / investigation | half-buried wagon track that can reveal the cult's supply line |
| `collapsed_watchfire` | Collapsed Watchfire | rescue / optional combat | a ruined camp with one living survivor and something still nearby |
| `chalked_warning_stone` | Chalked Warning Stone | lore / skill check | an old dwarven marker that can grant context, caution, or a hidden stash |
| `missing_voice_at_camp` | Missing Voice at Camp | companion scene / insight | a party member or follower wanders toward a whispering seam in the stone |
| `rope_across_the_dark` | Rope Across the Dark | trap / stealth / combat | a narrow-path ambush line set by lookout pairs |
| `blackwater_crossing` | Blackwater Crossing | skill challenge / optional combat | a ford watched by nervous cult outriders |
| `prospectors_last_joke` | Prospector's Last Joke | investigation / hazard | a fake treasure marker leading to ooze, collapse, or a real hidden tube |
| `choir_under_hill` | Choir Under the Hill | scout / dread scene | chanting heard through stone can be ignored, trailed, or exploited |
| `broken_sending_tube` | Broken Sending Tube | lore / loot | a Pact-age message cylinder with partial directions and names |
| `stone_taster` | Stone-Taster | non-combat creature / optional combat | a blind cave lizard can reveal a seam or panic into a fight |
| `shardfall_gleam` | Shardfall Gleam | omen / skill check | a tiny crystal splinter offers loot and an early Act 3 shiver |
| `dust_in_the_bedroll` | Dust in the Bedroll | camp sabotage / discovery | cult dust, broken sleep, and a chance to catch an infiltrator before dawn |

## Story Flags Worth Watching

- `act2_started`
- `act2_town_stability`
- `act2_route_control`
- `act2_whisper_pressure`
- `act2_sponsor`
- `phandelver_claims_council_seen`
- `act2_neglected_lead`
- `act2_midpoint_priority`
- `agatha_truth_secured`
- `agatha_truth_clear`
- `woodland_survey_cleared`
- `stonehollow_dig_cleared`
- `nim_recruited`
- `claims_meet_held`
- `phandalin_sabotage_resolved`
- `broken_prospect_cleared`
- `south_adit_cleared`
- `act2_first_late_route`
- `act2_captive_outcome`
- `irielle_recruited`
- `wave_echo_reached`
- `quiet_choir_identified`
- `act2_companion_arc_started`
- `act2_companion_arc_resolved`
- `black_lake_shrine_purified`
- `black_lake_barracks_raided`
- `caldra_defeated`
- `act3_phandalin_state`
- `act3_claims_balance`
- `act3_whisper_state`
- `act3_forge_route_state`
- `act3_forge_subroutes_cleared`
- `act3_forge_lens_state`

## Debugging Pointers

- The early expedition route should allow any two of three leads to unlock the midpoint, but the third lead should remain recoverable later in a degraded state
- Delaying an early lead must apply its consequence exactly once when sabotage night begins, not every time the hub is revisited
- Nim's recruitment should be reachable from more than one valid success path, but `has_companion()` style checks should still prevent duplicates
- Companion side tracks should deepen the act without blocking the main route; they should alter one of the campaign pressures, a later scene, or an Act 3 setup flag
- `Broken Prospect` and `South Adit` should both become available after the midpoint and should not force a single canonical order anymore
- The route chosen first must change the second route's tone and stakes even if the player ultimately clears both
- Random encounters need act-tag filtering once exclusivity is implemented, or the Act 2 mood will get diluted by generic frontier road scenes
- Caldra Voss and Irielle Ashwake both point toward Act 3 lore; keep those reveal flags separate from the basic Act 2 completion path so the player can miss some foreshadowing without breaking progression
