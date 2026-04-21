# Sword Coast Story Content Summary

This file is a repo-wide story pass for the current text-based Python DnD game. It is based on the `information/` reference markdown files, the live game flow in `dnd_game/`, the current map system, companion and camp data, random encounter content, the Act 2 scaffold, and a quick scan of the Android and draft folders.

## What Is Live, Planned, Or Legacy

- Live fully playable campaign: Act 1, `Ashes on the Triboar Trail`.
- Live partially playable scaffold: Act 2, `Echoes Beneath the Sword Mountains`.
- Roadmap only: Act 3, `The Jewel and the Chasm`.
- Important implementation note: the live Act 1 route uses `MapSystemMixin`, so some older linear Act 1 scene code is effectively superseded by the room-based map version.
- The `android_port/` folder is a legacy mirror of an older, shorter Act 1 flow. It does not add unique new branches beyond the current desktop version.
- The `dnd_game/drafts/map_system/` folder is design support, not a separate playable story branch, but it helps explain the intended room-by-room structure of Act 1.

## Story Source Map

- Story and systems references:
  - `README.md`
  - `information/Story/ACT1_CONTENT_REFERENCE.md`
  - `information/Story/ACT2_CONTENT_REFERENCE.md`
  - `information/systems/GAME_SYSTEMS_REFERENCE.md`
- Live story code:
  - `dnd_game/gameplay/story_intro.py`
  - `dnd_game/gameplay/story_town_hub.py`
  - `dnd_game/gameplay/story_town_services.py`
  - `dnd_game/gameplay/story_act1_expanded.py`
  - `dnd_game/gameplay/story_act2_scaffold.py`
  - `dnd_game/gameplay/map_system.py`
  - `dnd_game/gameplay/camp.py`
  - `dnd_game/gameplay/random_encounters.py`
- Story data:
  - `dnd_game/data/story/character_options/*`
  - `dnd_game/data/story/background_openings.py`
  - `dnd_game/data/story/companions.py`
  - `dnd_game/data/quests/act1.py`
  - `dnd_game/data/quests/act2.py`

## Character Building And Identity

### Campaign framing

- Act 1: `Ashes on the Triboar Trail` - playable.
- Act 2: `Echoes Beneath the Sword Mountains` - scaffolded and fully outlined, but not fully playable.
- Act 3: `The Jewel and the Chasm` - roadmap only.

### Character creation flow

- Start style:
  - Preset character.
  - Custom character.
- Custom build flow:
  - Name.
  - Race.
  - Class.
  - Background.
  - Ability assignment by standard array or point buy.
  - Class skill picks.
  - Rogue-only Expertise picks.
  - Final confirmation before the run begins.
- Ongoing respec story beat:
  - Camp includes a `magic mirror` that can fully respec the player for `100 gp`, framed as seeing alternate versions of the life they might have led.

### Races

- `Human`: ambitious generalist from the wider Sword Coast and beyond.
- `Dwarf`: clan-hardened, stone-shaped, stubbornly durable.
- `Elf`: graceful wanderer with keen senses and long memory.
- `Halfling`: luck-heavy survivor who refuses intimidation.
- `Dragonborn`: proud draconic bloodline, direct and confrontational.
- `Gnome`: clever tinkerer and curious scholar.
- `Half-Elf`: adaptable bridge-between-worlds social build.
- `Half-Orc`: relentless bruiser with fierce presence.
- `Tiefling`: marked outsider who turns suspicion into poise.
- `Goliath`: endurance-first mountain-bred competitor.
- `Orc`: forceful, darkvision-bearing momentum build.

### Classes

- `Barbarian`: fury, momentum, and raw battlefield pressure.
- `Bard`: social control, performance, and quick magic.
- `Cleric`: faith anchor, healing, and radiant offense.
- `Druid`: wilderness caster with healing and flame.
- `Fighter`: disciplined martial front-liner.
- `Monk`: speed, balance, and precision.
- `Paladin`: armored holy champion with healing and radiant force.
- `Ranger`: pathfinder, ranged hunter, and scout.
- `Rogue`: precision, nerve, stealth, and timing.
- `Sorcerer`: instinctive magic and force-of-personality casting.
- `Warlock`: uncanny pact-flavored caster with social bite.
- `Wizard`: studied arcane controller and blaster.

### Backgrounds and prologue starts

- `Soldier`
  - Opening title: `South Barracks Muster`
  - Setup: a wounded courier arrives and an Ashen Brand runner tries to escape the barracks.
  - First choice set:
    - Hit the gate hard.
    - Read the panic and find the escape lane.
    - Lock the teamsters in line by force of command.
  - Story result: the player learns the threat is organized enough to rattle Neverwinter's quartermasters.

- `Acolyte`
  - Opening title: `Hall of Justice Hospice`
  - Setup: a poisoned teamster and shaken survivors limp into a temple hospice.
  - First choice set:
    - Stabilize the poisoned victim.
    - Lead a calming prayer.
    - Read the poison and beast spoor.
  - Story result: the player sees the human cost of the Ashen Brand before the problem becomes logistics.

- `Criminal`
  - Opening title: `Blacklake Docks`
  - Setup: a fence deal turns into an Ashen Brand pressure play around forged wagon seals.
  - First choice set:
    - Pose as the collector's buyer.
    - Slip above the warehouse floor and steal the satchel.
    - Lift the ledger instead of the silver.
  - Story result: the player learns the gang launders route access through false papers and stolen seals.

- `Sage`
  - Opening title: `House of Knowledge Archives`
  - Setup: someone is stealing exactly the ruin plans and cellar maps that matter.
  - First choice set:
    - Follow the physical evidence in the archive.
    - Decode the arcane shorthand.
    - Reconstruct which ruin map matters most.
  - Story result: the campaign is framed as a puzzle about old routes, ruins, and selective theft.

- `Outlander`
  - Opening title: `Neverwinter Wood Trail Camp`
  - Setup: the frontier goes quiet before dawn and a raid pattern becomes readable in tracks and silence.
  - First choice set:
    - Set the ground where the attack will land.
    - Climb and refuse surprise.
    - Ghost into the brush first.
  - Story result: the danger feels like a living frontier pattern rather than only a city rumor.

- `Charlatan`
  - Opening title: `Protector's Enclave Market`
  - Setup: an Ashen Brand fixer tries to turn your talent for lies into employment.
  - First choice set:
    - Sell a bigger lie.
    - Turn the exchange into public theater.
    - Read the fixer's real pressure point.
  - Story result: the Ashen Brand reads like a trade-and-forgery network, not only a raider gang.

- `Guild Artisan`
  - Opening title: `River District Counting-House`
  - Setup: the southbound supply chain is being quietly manipulated.
  - First choice set:
    - Audit the manifests.
    - Settle the room and get testimony.
    - Cut off the fleeing haulers.
  - Story result: the campaign is seen through shortages, false weights, and pressure on trade.

- `Hermit`
  - Opening title: `Wayside Shrine on the High Road`
  - Setup: a hunted courier collapses at a lonely shrine carrying omen-heavy warnings.
  - First choice set:
    - Stabilize the courier.
    - Read the spoor.
    - Read the omen in the warning.
  - Story result: the campaign opens with omen, sickness, and pursuit before politics catches up.

### Preset characters

- `Barbarian`: Brakka Stonewake, Goliath Outlander.
- `Bard`: Lark Voss, Half-Elf Charlatan.
- `Fighter`: Riven Ashguard, Half-Orc Soldier.
- `Rogue`: Mira Quickstep, Halfling Criminal.
- `Cleric`: Sister Elowen, Half-Elf Acolyte.
- `Wizard`: Theron Vale, Human Sage.
- `Paladin`: Ser Jorren Dawnsteel, Dragonborn Soldier.
- `Ranger`: Kael Thornwatch, Elf Outlander.
- `Druid`: Liora Fenbloom, Half-Elf Hermit.
- `Monk`: Shen Vale, Human Hermit.
- `Sorcerer`: Iria Flamevein, Tiefling Sage.
- `Warlock`: Cairn Blackwake, Tiefling Charlatan.

### Title-screen lore content

The title screen has a `Lore Codex` with much more worldbuilding than the core story path alone. It includes:

- World and location lore.
- Class lore.
- Race lore.
- Background lore.
- Ability and skill notes.
- Feature and condition notes.
- Appendix-style deity, faction, and planar notes.
- Campaign roadmap notes.
- Item and equipment manual entries.

This means the game's narrative identity is not only in scenes; part of it lives in optional codex reading.

## Companion Story Content

### Recruitable companions

#### Act 1 companions

- `Kaelis Starling`
  - Half-Elf Ranger.
  - Recruited in Neverwinter if Mira sends the scout.
  - Story role: quiet pattern-reader and woods guide.
  - Scene support: `road_ambush`, `wyvern_tor`.
  - Great-trust combat opener: `Shadow Volley`.

- `Rhogar Valeguard`
  - Dragonborn Paladin.
  - Recruited in Neverwinter if Mira sends the caravan guardian.
  - Story role: oath-driven protector.
  - Scene support: `ashfall_watch`.
  - Late Act 1 hook: can collide with Bryn over how publicly Cinderfall route names should be handled.

- `Tolan Ironshield`
  - Dwarf Fighter.
  - Recruited after the High Road ambush or later at Stonehill Inn.
  - Story role: veteran shield-wall survivor.
  - Scene support: `ashfall_watch`.
  - Great-trust combat opener: `Hold the Line`.

- `Bryn Underbough`
  - Halfling Rogue.
  - Recruited at Stonehill Inn, first through `Persuasion`, then through a later `Insight` retry if the first ask fails.
  - Story role: rumor-reader, anxious scout, ex-smuggler.
  - Scene support: `old_owl_well`, `emberhall_cellars`.
  - Personal hook: `Loose Ends`, an old cache and ledger decision that can surface through trench notes or the smuggler encounter chain.

- `Elira Dawnmantle`
  - Human Cleric.
  - Recruited at the shrine; automatically easier if you helped her first.
  - Story role: frontier priestess and moral center.
  - Scene support: `camp_rest`.
  - Personal hook: `Faith Under Ash`, a captured-cultist judgment scene inside `Ashfall Watch`.

#### Act 2 companions

- `Nim Ardentglass`
  - Rock Gnome Wizard.
  - Recruited during `Stonehollow Dig` or sent to camp first.
  - Story role: Pact cartographer and practical ruin scholar.
  - Scene support: `stonehollow_dig`, `wave_echo_outer_galleries`.

- `Irielle Ashwake`
  - Tiefling Warlock.
  - Freed in `South Adit`; can join immediately or regroup at camp first.
  - Story role: escaped Quiet Choir augur.
  - Scene support: `south_adit`, `forge_of_spells`.

### Camp conversation structure

- Every companion has:
  - a summary blurb,
  - three camp conversation prompts,
  - positive and negative trust changes from those talks,
  - relationship-based special dialogue at `Great` and `Exceptional`,
  - possible departure if trust falls to `Terrible`.
- Relationship labels:
  - `Neutral` at `0-2`
  - `Good` at `3-5`
  - `Great` at `6-8`
  - `Exceptional` at `9+`
  - `Bad` at `-3` to `-5`
  - `Terrible` at `-6` or lower, which makes the companion leave

### Camp talk topics by companion

- `Tolan Ironshield`
  - Worst road he ever guarded.
  - What his clan expects now.
  - A dismissive "relic from an older war" jab.

- `Bryn Underbough`
  - Why she left smuggling.
  - What still scares her on the road.
  - A dismissive "you worry too much" jab.

- `Elira Dawnmantle`
  - What faith means under grief.
  - Why Tymora matters on the frontier.
  - A cruel "prayer won't save anyone" jab.

- `Kaelis Starling`
  - What the wood taught him.
  - The mistake he still carries.
  - A distrustful "you hide too much" jab.

- `Rhogar Valeguard`
  - The oath that drives him.
  - Whether honor cost too much.
  - A "honor is naive" jab.

- `Nim Ardentglass`
  - Why maps matter.
  - Who taught him to read ruins.
  - A dismissive jab about fear in scholar's clothing.

- `Irielle Ashwake`
  - What the Quiet Choir promised first.
  - What freedom looks like now.
  - A distrustful accusation that she might betray the party.

### Act 2 companion sidetracks

- `Bryn`: poison bad ledgers quietly, or expose the claims scam in public.
- `Elira`: carry the warding lantern into the field, or leave it in town.
- `Kaelis`: preserve a hidden ranger trail, or burn it so nobody uses it cleanly.
- `Rhogar`: bind his oath to the town above, or to the sacred threshold below.
- `Tolan`: salvage useful brace-iron, or bury tainted ore and abandon profit.
- `Nim`: preserve dangerous theorem notes, or burn the corrupted pages.
- `Irielle`: teach the counter-cadence, or bury it and refuse to carry the Choir's song farther.

## Act 1: Current Playable Story

### High-level route

1. Background-specific prologue in or near Neverwinter.
2. Mira Thann's private briefing.
3. High Road ambush, Tolan pivot, and a cleared-road travel menu with optional post-ambush High Road side branches before Phandalin.
4. Phandalin hub, side conversations, and possible early discovery of the hidden `Cinderfall` route.
5. `Old Owl Well` and `Wyvern Tor` in either order.
6. Optional `Cinderfall Ruins` relay strike before the main assault.
7. Stonehill war-room council.
8. `Ashfall Watch`.
9. Lantern vigil in Phandalin.
10. `Tresendar Manor`.
11. `Emberhall Cellars`.
12. Act 1 completion, ending tier resolution, and Wave Echo foreshadowing.

### Neverwinter briefing

Mira Thann gives the core premise:

- Caravans to Phandalin are vanishing.
- Miners are being shaken down.
- The `Ashen Brand` is using old frontier ruins for cover.

The player can ask:

- `How is Neverwinter holding together these days?`
- `Tell me what matters most about Phandalin before I ride.`
- `How dangerous is this Ashen Brand, really?`

Before leaving, the player can make one final preparation:

- `Investigation`: review caravan ledgers.
- `Religion`: seek a road prayer and blessing.
- `Persuasion`: loosen tongues among teamsters and dockhands.
- Or skip the detour.

The player also chooses an early companion:

- `Kaelis Starling`
- `Rhogar Valeguard`

### High Road ambush

Setup:

- Goblin raiders and a chained ash wolf are attacking a wagon.
- Tolan Ironshield is trying to hold them off.

Approach choices:

- `Athletics`: charge in.
- `Stealth`: flank through the brush.
- `Intimidation`: break their nerve with a warning shout.

Resolution choices after victory:

- Recruit `Tolan` immediately.
- Send him to recover at `Stonehill Inn` and recruit him later.

Post-ambush side branches:

- The second ambush wave now loops back into the cleared High Road scene instead of auto-entering Phandalin.
- Side-branch options are plain action labels; only `BACKTRACK` remains explicitly tagged because it is navigation.
- Returning from a side branch preserves the main High Road as the next useful backtrack point and prevents Phandalin from backtracking into resolved detours.
- `Liar's Circle`: logic puzzle; correct answer grants `Liar's Blessing` and `200 XP`, wrong answer applies `Liar's Curse`.
- `False Roadwarden Checkpoint`: non-combat social encounter with fake roadwardens demanding papers. Can resolve through `Deception`, `Insight`, `Persuasion`, `Intimidation`, or contract-house proof from Oren/Sabra/Garren.
- `False Tollstones`: false toll operation at a broken milemarker; `Liar's Blessing` can bypass the normal checks.

What the checkpoint adds:

- makes Neverwinter contract-house intel matter before Blackwake,
- sets Blackwake route leads when exposed,
- gives the player a social answer to copied roadwarden authority instead of another fight.

### Phandalin arrival

First impression choices:

- `Insight`: read the town's mood.
- `Persuasion`: announce that Neverwinter sent help.
- `Investigation`: read the tracks, barricades, and weak points.
- There are also class/race identity response options in some dialogue scenes.

A strong `Insight` read can also reveal the hidden `Cinderfall Ruins` route before either outer branch is complete.

### Phandalin hub conversations and side-story hubs

#### Steward Tessa Harrow

Conversation options:

- Ask where the Ashen Brand is hurting the town most.
- Ask about the old ruins around town.
- Make a vow to break their grip on Phandalin.
- Turn in the Ashfall quest later.

What this hub adds:

- The main civic pressure of the town.
- The `Stop the Watchtower Raids` quest.
- Repeated emphasis that old ruins and buried cellar routes are part of the problem.

#### Stonehill Inn

Conversation options with Bryn:

- Buy her a drink and ask questions.
- Ask what the roads are saying about the Ashen Brand.
- Recruit Bryn with `Persuasion`.
- If that fails, try a deeper `Insight` read later.
- If Tolan was deferred, bring him back into the party here.

What this hub adds:

- Bryn's scout perspective on Ashfall Watch.
- The strongest inn-based rumor confirmation that Ashfall is the gang's field spine.

#### Shrine of Tymora

Conversation options with Elira:

- `Medicine`: help stabilize a poisoned miner.
- `Religion`: pray with her.
- Ask what she has learned about the raiders.
- Recruit Elira, easier if you already helped.

What this hub adds:

- Poison-and-discipline framing for the gang.
- Elira's mercy-based view of the frontier.

#### Barthen's Provisions

Conversation options:

- Ask what the town runs short on first.
- Shop.
- Turn in Barthen's road-supply quest.

What this hub adds:

- The clearest "everyday people are paying for this" angle.

#### Lionshield Coster / Linene Graywind

Conversation options:

- Ask how badly trade is being strangled.
- Shop and barter.
- Turn in Linene's trade-lane quest.

What this hub adds:

- The clearest trade-and-fear framing.

#### Edermath Orchard / Daran Edermath

Conversation options:

- `Nature`: inspect ash blight and sabotage in the orchard.
- Ask about `Wyvern Tor`.
- `Athletics`: run a frontier warm-up drill with Daran.
- `Stealth`: recover Daran's old adventurer's cache quietly; failure triggers an `Edermath Orchard Watchers` encounter.
- Turn in the Wyvern Tor quest.

What this hub adds:

- Daran's old-soldier voice.
- The main lead into `Wyvern Tor`.
- A unique Act 1 reward, `edermath_cache_compass`, plus `act2_edermath_cache_routework` for later route-control pressure.
- Different cache dialogue if `Wyvern Tor` has already been cleared before the cache is recovered.

#### Miner's Exchange / Halia Thornton

Conversation options:

- Ask which crews are missing and where.
- `Investigation`: inspect the ledgers.
- `Persuasion`: resolve a bitter claim dispute.
- Turn in the Old Owl Well quest.

What this hub adds:

- The main lead into `Old Owl Well`.
- Strong hints that the gang's violence is tied to logistics and salvage, not just open raiding.
- One of the cleanest non-combat reveal lanes for the hidden `Cinderfall` reserve route.

### Fixed Act 1 convergence beats

#### Stonehill war-room council

Triggers after both `Old Owl Well` and `Wyvern Tor` are cleared.

Choices:

- `Investigation`: read the exact route pressure point at Ashfall Watch.
- `Persuasion`: stiffen the town's nerves before the assault.
- `Insight`: figure out what Rukhar values and protects.

Story function:

- Reframes the campaign from scattered local threats into one coordinated assault target.

#### Lantern vigil

Triggers after `Ashfall Watch` is cleared.

Choices:

- `Medicine`: stabilize a rescued witness and get a clean tunnel account.
- `Religion`: hold the vigil together.
- `Investigation`: decode the soot-marked ledgers.

Story function:

- Reveals that the Ashen Brand is still moving people and goods through `Tresendar Manor` and deeper into `Emberhall`.

### Act 1 branch sites and dungeon structure

The current live version is room-based, not just scene-based. Major sites now have named rooms, movement choices, and reconvergence.

#### Old Owl Well

Route structure:

- `Dig Ring`
- branch to `Salt Cart Hollow`
- branch to `Supply Trench`
- reconverge at `Buried Dark Lip` for `Vaelith Marr`

Room story beats:

- `Dig Ring`
  - Approach options:
    - Stealth through the trench.
    - Arcana read on the ritual sigils.
    - Deception as hired salvage.
  - The stealth opening now branches again into sabotage, sentry removal, or deeper infiltration.
- `Salt Cart Hollow`
  - Rescue options:
    - `Medicine`
    - `Persuasion`
    - brute-force cart break
- `Supply Trench`
  - Note-handling options:
    - `Investigation`
    - `Arcana`
    - quick salvage and destroy the rest
    - if Bryn is trusted and active, let her read the soot ledgers herself
- `Buried Dark Lip`
  - Boss talk options against `Vaelith Marr`:
    - `Religion`
    - `Intimidation`
    - immediate rush
  - Boss setup now reacts to the earlier sabotage, sentry, or infiltration outcome

Story function:

- Reveals the grave-salvage wing of the Ashen Brand network.
- Connects Old Owl, Ashfall, and manor-hill logistics into one chain.

#### Wyvern Tor

Route structure:

- `Goat Path`
- branch to `Drover Hollow`
- branch to `Shrine Ledge`
- reconverge at `Broken High Shelf` for `Brughor Skullcleaver`

Room story beats:

- `Goat Path`
  - Approach options:
    - `Survival`
    - `Stealth`
    - `Nature`
- `Drover Hollow`
  - Drover scene options:
    - `Medicine`
    - `Insight`
    - cut them loose and arm them
  - The follow-up ask can now send a warning, stage a hidden signal, or loose the remaining beasts
- `Shrine Ledge`
  - Ledge options:
    - restore shrine by `Religion`
    - loose the tethered beasts
    - strip the tack and empty the ledge
    - if Rhogar is trusted and active, let him reset the cairn oath directly
- `Broken High Shelf`
  - Boss talk options against `Brughor`:
    - `Intimidation`
    - `Athletics`
    - immediate strike
  - Boss setup now reacts to hidden spotter support, a camp stampede, and Rhogar's omen

Story function:

- Handles the raider-and-worg pressure on the high ground.
- Confirms the hill raiders are coordinated with Ashfall instead of acting alone.

#### Cinderfall Ruins

Route structure:

- `Collapsed Gate`
- branch to `Ash Chapel`
- branch to `Broken Storehouse`
- reconverge at `Ember Relay Node`

Room story beats:

- `Collapsed Gate`
  - Breach options:
    - `Stealth`
    - `Investigation`
    - `Athletics`
- `Ash Chapel`
  - Survivor-and-shrine side branch that can increase the rescue count
- `Broken Storehouse`
  - Supply and route-slate branch that exposes how Ashfall is being fed off the main road
- `Ember Relay Node`
  - Relay strike that can cut Ashfall reinforcements and deny Rukhar his reserve edge

Story function:

- Acts as the dynamic third route in mid-Act 1.
- Foreshadows Emberhall's deeper logistics.
- Gives the player a concrete way to shape the later Ashfall difficulty.

#### Ashfall Watch

Route structure:

- `Gate Breach`
- branch to `Prisoner Yard`
- branch to `Signal Basin`
- `Lower Barracks`
- `Rukhar's Command Post`

Room story beats:

- `Gate Breach`
  - Assault opening:
    - `Stealth`
    - `Deception`
    - `Athletics`
  - Immediate follow-up choice:
    - snuff the basin,
    - free prisoners,
    - read Rukhar's board.
- `Prisoner Yard`
  - Choices:
    - break cages and arm prisoners,
    - read Rukhar's orders,
    - do a quick lock-cut evacuation and move on.
- `Signal Basin`
  - Choices:
    - `Stealth` to smother the signal,
    - wind-reading sabotage,
    - brute-force destruction.
- `Lower Barracks`
  - Hard reconvergence fight after one stabilizing branch.
- `Rukhar's Command Post`
  - Boss talk options:
    - `Intimidation`
    - `Persuasion`
    - immediate strike

Story function:

- Breaks the Ashen Brand's field base.
- Reveals the soot-black Tresendar key and prisoner transfer chain toward Emberhall.

#### Tresendar Manor

Route structure:

- `Hidden Stair`
- `Cellar Intake`
- `Cistern Walk`
- optional `Cage Store`
- `Cistern Eye`

Room story beats:

- `Hidden Stair`
  - Entry options:
    - `Investigation`
    - `Stealth`
    - `Athletics`
- `Cellar Intake`
  - Mandatory intake fight.
- `Cistern Walk`
  - Pre-horror choices:
    - `Insight`
    - `Arcana`
    - bait-and-charge
- `Cage Store`
  - Choices:
    - decode ledgers,
    - quietly open the coffer,
    - drag the whole coffer out
- `Cistern Eye`
  - Nothic roleplay boss before the fight.
  - The Cistern Eye reads the player's background, then offers four routes:
    - kill it immediately for the safe path,
    - trade a memory, self-truth, or active Bryn/Rhogar secret,
    - bargain repeatedly for escalating lore,
    - deceive it for full lore with no sanity cost on success.
  - Repeated bargains reveal Emberhall first, then Cinderfall's relay role, then Wave Echo / Forge of Spells foreshadowing.
  - Bargain costs escalate through combat debuffs, `Whispered Through`, and active companion distrust.
  - Bryn betrayal exposes `bryn_secret_exposed`; Rhogar betrayal sets `rhogar_cistern_conflict_pending`.

Story function:

- Shows that the manor is the intake route, not the final command center.
- Confirms Varyn has withdrawn deeper into Emberhall.
- Can reveal Cinderfall and Wave Echo context early if the player accepts risk or wins the Deception route.
- Turns the Manor into a late-Act companion-trust and player-background pressure scene instead of only a monster room.

#### Emberhall Cellars

Route structure:

- `Antechamber`
- `Ledger Chain Room`
- optional `Ash Archive`
- optional `Black Reserve`
- `Varyn's Sanctum`

Room story beats:

- `Antechamber`
  - Approach options:
    - `Stealth`
    - `Athletics`
    - `Persuasion`
- `Ledger Chain Room`
  - Choices:
    - save the chained clerk,
    - read the ledgers,
    - smash the poison table
- `Ash Archive`
  - Choices:
    - map reserve exits,
    - find a hidden reserve,
    - sweep fast and move on
- `Black Reserve`
  - Optional reserve fight.
- `Varyn's Sanctum`
  - Final talk options:
    - `Persuasion`
    - `Intimidation`
    - immediate strike

Story function:

- Ends Act 1.
- Confirms that Varyn and the Ashen Brand were only the surface of a deeper Wave Echo problem.

### Act 1 ending and foreshadowing

When `Varyn Sable` falls:

- Act 1 now records one of three ending tiers:
  - `clean_victory`
  - `costly_victory`
  - `fractured_victory`
- That ending state is shaped by `Town Fear`, `Ashen Strength`, `Survivors Saved`, and strained late-act moral choices around Bryn, Elira, and Rhogar.
- Phandalin can leave the act relieved, exhausted, or still visibly cracked by what it took to win.
- Varyn's ledgers point toward older powers beneath the Sword Mountains.
- `Wave Echo Cave` becomes the obvious next narrative destination, and the game records `act2_starting_pressure` for the next act.

## Act 1 Post-Combat Random Encounter Story Pool

These are optional side vignettes that can trigger after fights. They are not pure combat filler; they are small story moments with loot, checks, or small follow-up fights.

| Encounter | Setup |
| --- | --- |
| Locked Chest Under the Ferns | A traveler's chest is hidden beneath a fallen marker stone. |
| Abandoned Cottage | A soot-stained roadside cottage has a suspiciously newer cellar door. |
| Bandit Toll Line | A fake toll rope and sign block the road while voices wait out of sight. |
| Wounded Messenger | A messenger in torn livery is bleeding out behind a milepost. |
| Messenger Returns | A previously saved courier can come back later with a reward and more road intel. |
| Hunter's Snare | A taut roadside snare is waiting for a careless ankle. |
| Lone Wolf at the Kill | A wolf guards a carcass and a glinting torn purse. |
| Smuggler Cookfire | A hidden cookfire and tarp suggest smugglers camping just off-road. |
| Smuggler Revenge Squad | If the smugglers are disrupted, they can later come back with Ashen Brand backing. |
| Shrine of Tymora | A weathered lucky-road shrine still stands under an oak. |
| Half-Sunk Satchel | A satchel is trapped in runoff water in a muddy ditch. |
| Ruined Wayhouse | A roofless wayhouse hides fresh scrape marks around its cellar trapdoor. |
| Scavenger Cart | A broken cart lies in the ditch with one useful-looking axle pin still jammed in place. |
| Loose Flagstones | Raised roadside flagstones look like they are hiding a cache. |
| Frightened Draft Horse | A panicked draft horse is tangled in broken trace lines. |
| Rain Barrel Cache | A weighted rain barrel sounds like it hides more than water. |
| Watchfire Embers | A just-abandoned watchfire still holds warm bedroll hollows. |
| Broken Milestone | A shattered milestone shows fresh pry marks from recent scavengers. |

General pattern:

- Most of these offer three choices.
- The options are usually a careful skill route, a bolder forceful route, and a leave-it or escalate-it route.
- Outcomes can be loot, clue-like flavor, damage, or a short side fight.
- A few now chain forward into later road scenes or companion-quest payoffs:
  - `Wounded Messenger` -> `Messenger Returns`
  - `Smuggler Cookfire` -> `Smuggler Revenge Squad`
  - `Abandoned Cottage` can expose an `Emberhall` clue once Bryn's cache trail is live

## Act 2 Scaffold Story Content

Important status note:

- Act 2 is strongly documented and partially scaffolded in code, but it is not as fully live as the current Act 1 map route.
- The repo treats this as the intended next campaign arc, so it still matters for story summarization.

### Core Act 2 premise

Act 2 shifts the game from frontier cleanup into a layered expedition story:

- public conflict: who controls `Wave Echo Cave` and the claims around it,
- private conflict: the `Quiet Choir` is using the Forge and an obelisk shard as a listening instrument,
- emotional pressure: Phandalin is no longer just surviving bandits; it is deciding what kind of town it becomes while deeper horror pushes upward.

`Sister Caldra Voss` is framed as a cult theologian more than a greedy treasure hunter. Her story role is to prove that the mine is dangerous not only because it is valuable, but because it can answer the wrong kind of prayer.

### Campaign pressures

The Act 2 scaffold repeatedly tracks three pressures:

- `Town Stability`
  - how well Phandalin holds together politically and emotionally,
- `Route Control`
  - how secure the expedition roads, cuts, and approach lines are,
- `Whisper Pressure`
  - how much Quiet Choir influence, dread, and resonance contamination is spreading.

Act 1 carryover choices push these values:

- saving townsfolk and handling civic scenes feeds `Town Stability`,
- road and outpost wins feed `Route Control`,
- recovering Daran's old cache adds a quieter orchard-to-highland route-control hook,
- shrine and spiritual choices can lower `Whisper Pressure`,
- which companions were recruited also unlocks side arcs that shift later pressure.

### Opening structure

Act 2 opens with:

1. aftermath in `Phandalin`,
2. a `Stonehill Claims Council`,
3. a sponsor decision,
4. three early leads, of which any two can push the act to its midpoint.

At the `Stonehill Claims Council`, the player is not just hearing exposition. The scene is a political conversation about who gets to shape the expedition and how much of Phandalin's future gets traded away to make it happen.

### Sponsor choice

The player can align most strongly with one of three sponsor lanes:

- `Halia Thornton / Miner's Exchange`
  - stronger route and ambition,
  - but more dangerous whisper-side compromise,
- `Linene Graywind / Lionshield`
  - steadier practical support,
  - more balanced town and route gains,
- `Elira Dawnmantle and Daran Edermath / Warden lane`
  - more conscience-driven expedition posture,
  - helps town resilience and restrains whisper corruption.

This is a story choice, not just a stat pick. It defines who frames the mine: profit, preparedness, or moral stewardship.

### Early-route branch set

The player can pursue three early leads. Clearing any two unlocks the midpoint, but delaying the third permanently changes its tone.

#### Conyberry and Agatha's Circuit

Story function:

- reconnects the expedition to old Pact routes and older warnings,
- gives `Elira`-aligned spiritual context,
- determines whether the town reaches the midpoint with a clean warning or a damaged one.

Main conversation and choice texture:

- the player seeks `Agatha's` truth,
- the scene leans into grief, memory, and whether warnings can still be trusted after history has already failed once,
- key approaches use:
  - `Persuasion`,
  - `Religion`,
  - `Arcana`.

If delayed:

- the warning still exists,
- but it arrives late and fractured,
- making the midpoint feel more panicked and less prepared.

#### Neverwinter Wood Survey Camp

Story function:

- focuses on witnesses, sabotage traces, and how expedition truth can be erased before it reaches town,
- carries more grounded frontier-investigation energy than the ghostly `Conyberry` route.

Key approaches:

- `Stealth`,
- `Intimidation`,
- `Survival`.

If delayed:

- saboteurs have more time to clean up,
- evidence gets worse,
- the scene becomes less about prevention and more about salvage.

#### Stonehollow Dig

Story function:

- excavation rescue scene,
- survey-truth branch,
- recruitment entrance for `Nim Ardentglass`.

Key approaches:

- `Investigation`,
- `Athletics`,
- `Arcana`.

Its emotional core is not just "clear the dig." It is about whether knowledge comes back out of the earth in usable form, and whether scholars and delvers still matter as people instead of expendable assets.

If delayed:

- the cleanest survey notes are lost or degraded,
- the route picture is worse,
- `Nim` still can appear, but the rescue has a more damaged emotional register.

### Midpoint convergence: Sabotage Night

Once two early leads are cleared, the player can trigger `Sabotage Night`.

This is the act's first major convergence scene:

- town factions collide,
- earlier missing information starts to hurt,
- the player must choose what to protect first.

Priority options:

- hold the `Claims Hall`
  - `Persuasion`,
- save `Shrine Lane`
  - `Medicine`,
- hunt the infiltrator cell
  - `Perception`.

This is one of the strongest story-pressure moments in the repo because it forces a real "you cannot save everything at once" beat.

### Late-route branch set

Both late routes are required before the deep mine push, but their order matters.

#### Broken Prospect

Story function:

- secures the cleaner tactical approach,
- prioritizes route control over immediate prisoner rescue,
- is especially meaningful for `Tolan`'s survival-memory arc.

Key approaches:

- `History`,
- `Stealth`,
- `Religion`.

If taken first:

- the expedition line improves,
- but the `South Adit` captives suffer for the delay.

#### South Adit

Story function:

- prison-rescue route,
- direct confrontation with the Quiet Choir's human cost,
- recruitment entrance for `Irielle Ashwake`.

Key approaches:

- `Sleight of Hand`,
- `Intimidation`,
- `Medicine`.

If taken first:

- more captives live,
- but the rival route and claim pressure harden elsewhere.

This is one of the clearest moral forks in the campaign: save people first, or stabilize the path first.

### Final Wave Echo sequence

After both late routes, the act closes with three linked scenes.

#### Wave Echo Outer Galleries

Story function:

- the company finally commits to a real mine advance,
- the story tone shifts from frontier skirmish to deep-ruin pressure,
- the player proves the expedition can actually hold a line underground.

Key approaches:

- `Investigation`,
- `Survival`,
- `Athletics`.

#### Black Lake Causeway

This scene reframes the approach to the Forge around three priorities:

- reclaim the shrine
  - `Religion`,
- raid the barracks
  - `Stealth`,
- sabotage the causeway directly
  - `Athletics`.

It is effectively a last "what kind of victory do you want?" scene before the boss.

#### Forge of Spells

Story function:

- final confrontation with `Sister Caldra Voss`,
- reveal that the Forge has been turned into a listening lens,
- explicit handoff toward Act 3-scale cosmic danger.

Key confrontation routes:

- `Arcana`,
- `Persuasion`,
- immediate assault.

This scene matters narratively because winning does not fully solve the problem. It proves the mine is part of something older and that Caldra was listening for a deeper answer, and it now records which Forge subroutes were actually broken before the final confrontation.

### Act 2 epilogue states

The scaffold now records four final state families for the next act:

- town outcome:
  - `united`,
  - `holding`,
  - `fractured`,
- claims outcome:
  - `secured`,
  - `contested`,
  - `chaotic`,
- whisper outcome:
  - `contained`,
  - `lingering`,
  - `carried_out`,
- forge outcome:
  - route state:
    - `mastered`,
    - `broken`,
    - `partial`,
    - `direct`,
  - lens state:
    - `mapped`,
    - `shattered_blind`,
  - cleared subroutes:
    - stored as `act3_forge_subroutes_cleared` so later scenes can name which Forge lines the party actually broke.

This means Act 2 is designed less like a single fixed finale and more like a state-setting bridge into a darker Act 3, with sponsor fallout and later dialogue able to remember how thoroughly the Forge was actually unraveled.

## Act 2 Random Encounter Story Pool

There are two important Act 2 random-story layers in the repo.

### Documented Act 2-exclusive pool

`information/Story/ACT2_CONTENT_REFERENCE.md` proposes a suspense-heavy pool built around expedition dread, cult traces, and mine folklore:

- `Silent Mule Train`
- `Lantern in the Wash`
- `Hushed Pilgrims`
- `Buried Wheel Rut`
- `Collapsed Watchfire`
- `Chalked Warning Stone`
- `Missing Voice at Camp`
- `Rope Across the Dark`
- `Blackwater Crossing`
- `Prospector's Last Joke`
- `Choir Under the Hill`
- `Broken Sending Tube`
- `Stone-Taster`
- `Shardfall Gleam`
- `Dust in the Bedroll`

These are framed as fast scenes that can resolve through protection, lore, investigation, or dread rather than always becoming combat.

### Implemented Act 2 scaffold pool in code

`dnd_game/gameplay/random_encounters.py` already includes a separate Act 2 post-combat pool with live scene text and three-option choices:

- `Echoing Supply Cache`
- `Whispering Lantern`
- `Collapsed Ore Sled`
- `Silent Prayer Wall`
- `Flooded Tool Chest`
- `Surveyor Ghostlight`
- `Stolen Claim Markers`
- `Blackwater Drifter`
- `Chain-Drag Tunnel`
- `Mushroom Bloom Hall`
- `Shattered Foreman Bell`
- `Hidden Prisoner Note`
- `Obsidian Shard Outcrop`
- `Broken Lift Cradle`
- `Hushed Campfire`

General pattern:

- choice 1 is usually a skill-based careful read of the scene,
- choice 2 is a quicker salvage play,
- choice 3 is to leave it alone and keep the route moving.

These scenes quietly carry a lot of story texture:

- old `Pact` labor history,
- Quiet Choir contamination,
- prisoner rumors,
- mine superstitions,
- moral pressure around what to touch and what to leave buried.

## Legacy, Duplicate, And Draft Story Material Elsewhere In The Repo

### Information markdown references

These files are useful canonical summaries or design targets:

- `README.md`
  - big-picture game premise and feature promises,
- `information/Story/ACT1_CONTENT_REFERENCE.md`
  - approved Act 1 story map and quest flow,
- `information/Story/ACT2_CONTENT_REFERENCE.md`
  - Act 2 design target and branching plan,
- `information/systems/GAME_SYSTEMS_REFERENCE.md`
  - companion, camp, travel, and systems context that affects how story is delivered.

### Android port

`android_port/` mostly mirrors the earlier desktop story stack:

- same `Act 1` style opening structure,
- same broad chapter plan,
- not a separate campaign with new lore.

It is best treated as a duplicate implementation surface, not as extra canon.

### Draft map-system documents

The map draft docs under `dnd_game/drafts/map_system/` are useful because they explain intended room flow, unlock logic, and Act 1 route sequencing.

They are not separate branches of the story. They are design notes for the current playable Act 1 map structure.

### Title-screen lore codex

The game also carries a built-in lore reference surfaced from the title/menu layer:

- world primer,
- major faction context,
- class and race summaries,
- background summaries,
- companion summaries,
- story-so-far framing.

That content is more encyclopedia than scene-writing, but it is still part of the repo's narrative surface.

## Bottom Line

If you strip away combat and systems language, the repo currently tells three overlapping kinds of story:

1. `Playable Act 1`
   - a frontier rescue-and-stabilization campaign built around Phandalin, recruitable companions, layered town conversations, and a room-based approach to the Ashen Brand and `Varyn Sable`.
2. `Structured character identity`
   - race, class, background, and preset choices that all carry tone, opening flavor, and lore framing rather than being purely mechanical.
3. `Act 2 scaffold and future arc`
   - a claims-war expedition into `Wave Echo Cave`, with sponsor politics, rescue-versus-route choices, companion side arcs, `Sister Caldra Voss`, and early cosmic-horror escalation.

So the game already has a substantial amount of story material even where the campaign is not fully finished:

- origin fantasy,
- town NPC conversation trees,
- recruitable companion banter,
- camp talks,
- branching quest priorities,
- end-of-act foreshadowing,
- and a clearly planned sequel act with its own moral and political shape.
