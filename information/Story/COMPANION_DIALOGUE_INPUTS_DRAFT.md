# Companion Dialogue Inputs Draft

This draft covers companion interjections during ordinary dialogue, route decisions, NPC briefings, quest turn-ins, and act transitions.

It is separate from `COMPANION_CAMP_BANTER_DRAFT.md`. Camp banter is for companion-to-companion scenes at rest. Dialogue inputs are smaller, reactive insertions inside the main story flow.

## Goals

- Make the active party feel present in conversations, not only combat.
- Let past choices change who speaks, what they notice, and how much they trust the player's framing.
- Give party composition a visible texture without requiring any one companion for main progression.
- Use companion input to clarify stakes before a choice, echo consequences after a choice, and occasionally create companion tension.
- Keep Act 3 secret-architect guardrails intact. Before the midpoint reveal, no companion should name Malzurath or explain the Ninth Ledger as an intelligent force.

## Input Types

| Type | Timing | Purpose |
| --- | --- | --- |
| `pre_choice_read` | Before a choice menu | A companion frames the risk from their specialty. |
| `answer_support` | After the player asks an NPC a question | A companion adds context, presses the NPC, or translates the answer. |
| `choice_counsel` | Before a major moral or strategic decision | One or two companions argue for different priorities. |
| `post_choice_echo` | After the player commits | A companion responds to the choice and may adjust disposition. |
| `proof_callout` | When evidence, ledgers, testimony, or maps appear | A specialist identifies why this detail matters. |
| `relationship_echo` | When trust is Good, Great, Bad, or Exceptional | The same moment lands warmer, sharper, or more personal. |
| `party_cross_input` | When two specific companions are present | Short exchange that shows agreement, tension, or shared expertise. |

## Companion Voice Contracts

| Companion | Speaks when the topic is... | Avoid |
| --- | --- | --- |
| Kaelis Starling | tracks, ambushes, patterns, silence, route lies, scout guilt | long speeches or moral certainty |
| Rhogar Valeguard | oaths, law, public duty, protection, courage under scrutiny | sneaky approval unless framed as duty |
| Tolan Ironshield | lines, witnesses, triage discipline, practical survival, veteran memory | abstract theology or delicate wording |
| Bryn Underbough | exits, lies, hidden kindness, smuggler logic, anxious room reads | clean heroics without nervous deflection |
| Elira Dawnmantle | wounds, mercy, faith as action, testimony, the cost of delay | soft sentiment without practical consequence |
| Nim Ardentglass | maps, mechanisms, Pact logic, dangerous notes, scholar fear | grand prophecy or confident mysticism |
| Irielle Ashwake | whispers, coercive certainty, cult rhythms, survival after control | naming Malzurath before the reveal unless explicitly allowed |

## Branch Factors

Dialogue input should consider these factors in roughly this order:

1. Active party membership: only companions in the active party should speak in live scene dialogue.
2. Scene and dialogue topic: the input must answer the immediate conversation, not just advertise the companion.
3. Required flags: evidence, route order, quest state, prior choice, or reveal state.
4. Blocked flags: do not repeat one-shot lines.
5. Personal stakes: companion quest state outranks generic expertise.
6. Relationship tier: Bad or Terrible trust should create colder lines or silence; Great and Exceptional can unlock more vulnerable lines.
7. Party composition: if two companions have a strong conflict or synergy, use a two-line exchange instead of two unrelated one-liners.
8. Campaign pressure: Act 1 metrics, Act 2 pressures, Act 3 map integrity, and unrecorded choice tokens can alter tone.
9. Player identity: class, background, or prior dialogue posture can unlock a variant, but should not override companion-specific stakes.

## Runtime Shape

Suggested registry shape:

```python
{
    "id": "dialogue_input_elira_mira_trust_lie",
    "act": 1,
    "scene_keys": ["neverwinter_briefing"],
    "trigger": "answer_support",
    "topic_keys": ["mira_elira_question"],
    "requires_companions": ["elira_dawnmantle"],
    "requires_any_flags": ["elira_pre_neverwinter_recruited", "elira_greywake_recruited", "elira_phandalin_recruited"],
    "blocked_flags": ["dialogue_input_elira_mira_trust_lie_seen"],
    "relationship_min": {"elira_dawnmantle": -2},
    "priority": 80,
    "lines": [
        ("Elira Dawnmantle", "Trust me with breath, blood, and bad odds. Do not trust me to bless a lie because it would make the room easier to stand in.")
    ],
    "set_flags": ["dialogue_input_elira_mira_trust_lie_seen"],
}
```

Optional fields:

- `requires_flag_values`: for values such as `blackwake_resolution == "rescue"`.
- `blocked_flag_values`: to avoid contradictions.
- `requires_metric_min` / `requires_metric_max`: for Act 2 pressures and Act 3 map integrity.
- `speaker_priority`: tiebreaker if several companions could speak.
- `replacement_lines`: keyed by relationship tier, route order, or player pattern profile.
- `outcomes`: small disposition deltas only when the line responds to a real decision.

## Selection Rules

- Default to one companion input per dialogue beat.
- Allow two inputs only for explicit counsel scenes or strongly paired companions.
- Never let an input answer a question the NPC has not answered yet unless it is a deliberate interruption.
- Do not use a companion line to expose information the scene has not earned.
- If the player repeats an NPC topic, use either no companion input or a shortened relationship echo.
- When the player has no active companions, do not fake voices through narration. Use environment, NPC witnesses, or journal memory instead.
- If a companion is recruited but not active, reserve their reaction for camp, a hub follow-up, or a quest turn-in.

## Dialogue Topic Tags

These tags can be attached to NPC questions or choice options to help select companion inputs:

| Topic tag | Best speakers |
| --- | --- |
| `wounded_people` | Elira, Tolan, Rhogar |
| `witness_testimony` | Elira, Tolan, Bryn |
| `false_authority` | Bryn, Rhogar, Kaelis |
| `route_pattern` | Kaelis, Nim, Bryn |
| `dangerous_knowledge` | Nim, Irielle, Elira |
| `mercy_or_execution` | Elira, Rhogar, Tolan |
| `public_truth` | Rhogar, Tolan, Bryn |
| `hidden_truth` | Bryn, Kaelis, Irielle |
| `forge_or_resonance` | Nim, Irielle, Elira |
| `ledger_or_record` | Nim, Bryn, Tolan, Elira |
| `oath_or_law` | Rhogar, Tolan, Elira |
| `lie_or_performance` | Bryn, Kaelis, Nim |

## Act 1 Inputs

### Wayside Luck Shrine

Status: Elira is an NPC here unless already recruited through a future skip or debug state. Use this scene to establish how future companion inputs should treat her.

Gate: `wayside_luck_shrine`

If the player chooses Medicine:

- Elira: "Pressure first. Prayer after. If Tymora wants a miracle, she can start by keeping your hands steady."

If the player chooses Religion:

- Elira: "Good. Give them words they can breathe through. I will handle the blood."

If the player chooses Investigation:

- Elira: "If the road marks tell you who did this, read fast. The dying cannot testify twice."

If the player skips direct help:

- Elira: "Take the draught. Luck dislikes waste, even when people are in a hurry to call it caution."

Future echo if `elira_initial_trust_reason == warm_trust`:

- Elira: "I learned your hands before I learned your promises."

Future echo if `elira_initial_trust_reason == reserved_kindness`:

- Elira: "Kindness is not the same as trust. It is only the door trust may use later."

### Greywake Triage Yard

Gate: `greywake_triage_yard_seen`

If Elira is present and `greywake_manifest_preserved`:

- Elira: "A manifest should follow the wounded. This one walked in ahead of them and chose where they would fall."

If Elira is present and `greywake_wounded_stabilized`:

- Elira: "They are breathing. That means the paper has not won yet."

If Elira is not recruited but `elira_first_contact`:

- Elira: "I kept the shrine breathing. Now someone has taught the road to decide who survives before it sees them."

If the player asks whether this connects to Phandalin:

- Elira: "If this reaches Phandalin, it will not look like a manifest. It will look like an empty shelf, a missing miner, a mother waiting too long."

### Greywake Road Breakout

Gate: `greywake_attack_imminent`

Before protect-wounded choice, if Elira is active:

- Elira: "The proof matters. The people carrying it matter first."

Before seize-manifest choice, if Kaelis somehow active through debug or future route:

- Kaelis: "Runner's eyes. Left gate. He already knows where the fire is waiting."

Before intimidate choice, if Rhogar active:

- Rhogar: "Make their fear public. Cowards rely on silence as much as blades."

Post-combat if `greywake_wounded_line_guarded` and Tolan later joins:

- Tolan: "I heard about Greywake. Wounded line held under arrows. That is not mercy. That is discipline with a pulse."

### Neverwinter Briefing With Mira

Gate: `neverwinter_briefing`

Existing implemented Elira branch:

- Elira: "Harmless is what people call you when they have never watched you choose who gets the last clean bandage. I prefer useful."
- Elira: "The wounded are people first. If their pain becomes proof, it is because someone tried to bury them with it."
- Elira: "Trust me with breath, blood, and bad odds. Do not trust me to bless a lie because it would make the room easier to stand in."

If Kaelis is chosen as road companion:

- Kaelis: "If the Brand knows the road, we do not beat them by marching louder. We beat them by arriving from the angle they stopped watching."

If Rhogar is chosen as road companion:

- Rhogar: "A writ is not a shield. But held openly at the right moment, it can make the guilty reveal who taught them to fear law."

If Elira is already present and the player chooses Kaelis:

- Elira: "A scout sees the wound before it opens. I can work with that."
- Kaelis: "And a field priest knows which screams are bait. I can work with that."

If Elira is already present and the player chooses Rhogar:

- Rhogar: "Then we carry road mercy and road law together."
- Elira: "Only if the law remembers it has hands."

If `greywake_manifest_destroyed`:

- Tolan, if active by future return: "Paper burns. A frightened witness forgets. An angry witness remembers."
- Elira: "Then keep them angry without letting them bleed for it."

If `blackwake_completed` on return:

- Kaelis with `blackwake_resolution == "evidence"`: "Blackwake had tracks under the ledgers. Someone moved people and paperwork along the same path."
- Elira with `blackwake_resolution == "rescue"`: "The saved teamsters will talk differently than rescued cargo. Good."
- Bryn with `blackwake_resolution == "sabotage"`: "Systems hate losing quiet hinges. They will get louder now."

### Oren Vale's Contract House

Gate: `neverwinter_contract_house_seen` or related inn branch

When Sabra explains the false manifest circuit:

- Bryn, if active on a later return: "Three liars correcting the same paper is not sloppiness. That is a room where everyone thinks they own the door."
- Nim, Act 2+ return: "A bad manifest records a lie. A coordinated manifest records a method."

When Vessa's card table becomes a read-the-room scene:

- Kaelis: "The table is not about cards. Watch who is relieved when the wrong person wins."
- Bryn: "Cards lie beautifully. People are worse at it."

When Garren exposes copied roadwarden cadence:

- Rhogar: "That is the ugliest theft here. They did not steal a badge. They stole obedience."
- Tolan: "Aye. Teach a road to obey the wrong shout and you do not need many swords."

If the player mishandles the room and `ash_in_the_ale` triggers:

- Elira: "Poison in an inn is not subtle. It is someone admitting they ran out of honest masks."

### Neverwinter Preparation Branches

Gate: preparation choice before leaving Neverwinter

Investigation ledgers:

- Kaelis: "Look for the route nobody wanted to admit existed."
- Nim, Act 2+ return: "The correction marks matter more than the totals. People hide intent in revisions."

Religion road-prayer:

- Elira: "A prayer before the road is not asking to be spared. It is agreeing to notice who is not."
- Rhogar: "Let the vow be simple: if we arrive, we arrive responsible."

Persuasion with teamsters and dockhands:

- Bryn: "Ask who got paid too early. Honest trouble pays late."
- Tolan: "Ask who changed shifts. Fear moves guards before it moves goods."

### High Road Ambush And Tolan Recruitment

Gate: `road_ambush_cleared`

Before the approach:

- Kaelis: "Too quiet near the ditch. They want the wagon loud and the brush forgotten."
- Rhogar: "Then we give the wagon courage and the brush judgment."
- Elira: "If the wounded start moving, do not chase glory past them."

When Tolan is first seen holding the road:

- Tolan: "Less admiring. More fighting."

If the player recruits Tolan immediately:

- Tolan: "Fine. But if this becomes a parade, I am leaving before the speeches."

If the player sends Tolan to Stonehill:

- Tolan: "Aye. I will get the blood out of my beard and meet you where the next bad idea is waiting."

If Kaelis and Tolan are both present:

- Kaelis: "You held the line long enough for the road to answer."
- Tolan: "The road answered with a scout. I have had worse mornings."

### Liar's Circle

Gate: `high_road_liars_circle`

Before solving:

- Bryn, if present on a later route: "Four statues and a truth problem. This is either a curse or someone's idea of flirting."
- Elira: "A blessing from a liar is still a bargain. Be careful what part of you signs."
- Kaelis: "The circle wants impatience. Do not give it any."
- Nim, Act 2+ return: "Truth tables. Terrible sculpture, decent logic."

If `liars_blessing_active`:

- Bryn: "Well. Your tongue just got expensive."
- Rhogar: "Use it carefully. A false blessing still leaves a true mark."

If `liars_curse_active`:

- Tolan: "Next time a statue laughs at us, I am arguing with a hammer."
- Elira: "Curses that cling to speech can be starved. Say fewer clever things for a while."

### False Roadwarden Checkpoint

Gate: `high_road_false_checkpoint`

If the player uses Deception:

- Bryn: "Good lie. Do not polish it. Polished lies squeak."

If the player uses Insight:

- Kaelis: "The badge is calm. His boots are not. He expected obedience, not questions."

If the player uses Persuasion:

- Rhogar: "Make them answer as officers. A thief wearing law hates being asked for duty."

If the player uses Intimidation:

- Tolan: "If the badge is fake, hit the confidence first. The rest usually falls out of its pockets."

If Oren/Sabra/Garren proof is available:

- Elira: "Good. Let the lie meet a witness before it meets another victim."

### False Tollstones

Gate: `false_tollstones`

If `liars_blessing_active`:

- Bryn: "This is exactly the sort of terrible gift that wants to be useful. I hate how tempting that is."

If `liars_curse_active`:

- Kaelis: "Speak less. Point more. The stones are listening for confidence."

If Rhogar is present:

- Rhogar: "A toll without protection is theft with a table."

If Tolan is present:

- Tolan: "Break the table. Then we can discuss philosophy."

### Blackwake Crossing

Gate: `blackwake_completed` or Blackwake route scene

Choice counsel before final resolution:

- Evidence route, Kaelis: "If we leave with ledgers, Neverwinter has to move. If we leave only with smoke, the road learns less."
- Rescue route, Elira: "The ledgers can wait if the living cannot."
- Sabotage route, Bryn: "Break the quiet machinery now and the next convoy might not need rescuing."
- Public challenge, Rhogar: "Make them answer in daylight. False authority hates witnesses."
- Defensive hold, Tolan: "People first, proof second, arson third. Unless arson is how people stay first."

Post-resolution:

- `blackwake_resolution == "evidence"`:
  - Nim, later: "Useful records make cowards invent explanations. That is where they start contradicting each other."
  - Bryn: "Good. Now the city has handles on the story. Watch who refuses to grab them."
- `blackwake_resolution == "rescue"`:
  - Elira: "A breathing witness is not cleaner than a ledger. Better. Clean is overrated."
  - Tolan: "They lived. That gives the road teeth."
- `blackwake_resolution == "sabotage"`:
  - Kaelis: "Their next route just got more expensive."
  - Rhogar: "Sabotage becomes honorable when it breaks a machine built from fear."

### Phandalin Arrival

Gate: `phandalin_arrived`

If the player reads the town mood:

- Bryn: "This town is not quiet. It is deciding who gets blamed when it finally gets loud."
- Elira: "Fear makes triage out of whole streets if you let it."

If the player announces Neverwinter's help:

- Rhogar: "Say it like a promise, not a banner."
- Tolan: "And be ready when they ask what a promise weighs."

If the player reads tracks and barricades:

- Kaelis: "The barricades point inward as much as out. That means fear has already crossed the gate."
- Nim, later: "Improvised defenses have grammar. These say nobody agrees where the danger starts."

If `hidden_route_unlocked` from arrival Insight:

- Bryn: "You saw that too? Good. Bad. Both."
- Kaelis: "A route people avoid is still a route. Sometimes more so."

### Steward's Hall

Gate: `steward_seen`

When Tessa asks where to spend scarce defense:

- Rhogar: "A town survives when people know what they are defending, not only what they fear."
- Tolan: "Put strength where panic will look first."
- Bryn: "And leave one quiet exit. Not for running. For moving the people too scared to ask."

If the player makes `steward_vow_made`:

- Elira: "Do not make vows to comfort a room. Make them because your feet already know where they will stand."
- Rhogar, Great or higher: "That was not theater. Good. I can stand behind it."

If the player refuses public certainty:

- Kaelis: "Useful truth beats loud certainty. The town may not thank you until later."

### Stonehill Inn

Gate: `stonehill_inn_seen`

When recruiting Bryn:

- Kaelis: "She has counted every exit and still stayed in the room. That is not nothing."
- Tolan: "Fast hands, fast eyes, mouth like a thrown cup. Could be useful."
- Elira: "She jokes when frightened. Give her a reason not to run."

If Bryn initially refuses:

- Bryn: "I like living. Very inconvenient habit. Makes recruitment conversations complicated."
- Rhogar: "Fear is not failure."
- Bryn: "That is annoyingly generous and I reject how much I needed it."

For `marked_keg_resolved`:

- Elira: "Poison in a common room turns every cup into suspicion. Ending that matters."
- Bryn: "You caught the keg before it taught the room to hate its own thirst."

For `stonehill_instigator_unmasked`:

- Kaelis: "Paid mouths always look toward the door before the lie lands."
- Tolan: "Good catch. A room can survive anger. It cannot survive a hidden conductor for long."

For `songs_for_missing_*`:

- Elira: "Names keep the missing human when fear tries to make them weather."
- Tolan: "A song is not a grave marker, but it keeps cowards from calling the dead supplies."

### Shrine Of Tymora In Phandalin

Gate: `visit_shrine`

If Elira was not recruited and fallback is pending:

- Elira: "The road kept its appointment after all. Good. I was beginning to take that personally."

If Elira is already active and returns to shrine:

- Elira: "A shrine can survive my absence. That is the point of building a place around more than one pair of hands."

If the player helps the poisoned miner:

- Elira: "Good hands. Keep them honest when the next choice is less clean."

If the player prays:

- Rhogar: "A prayer with work behind it has weight."
- Elira: "That is the only kind I trust."

### Barthen's Provisions

Gate: `barthen_seen`

When Barthen explains shortages:

- Tolan: "Shelves empty before bellies do. That is when decent towns start making ugly choices."
- Bryn: "The Brand does not need to starve everyone. Just enough people to make suspicion affordable."
- Elira: "Hunger is a wound that learns to speak in arguments."

If `restore_barthen_supplies` ready:

- Rhogar: "Then make the return public. Let people see the road can still bring back what fear took."

### Lionshield Coster

Gate: `lionshield_seen`

When Linene explains trade pressure:

- Kaelis: "They are not only stealing weapons. They are deciding who feels safe enough to hold one."
- Rhogar: "A town denied tools is a town asked to kneel politely."
- Bryn: "And if the crates arrive late enough, everyone blames the shop instead of the hand on the road."

If trade lane is reopened:

- Tolan: "Good. A town with a supply line argues louder, but it also stands longer."

### Edermath Orchard

Gate: `edermath_orchard_seen`

When Daran discusses Wyvern Tor:

- Kaelis: "High ground, raider pride, and too many clean sightlines. They want us visible before we want them dead."
- Tolan: "Then we make the approach ugly for both sides."

If recovering old cache:

- Bryn: "Old adventurer caches are just apology letters with supplies."
- Rhogar: "Respect the dead hand that stored it."
- Bryn: "I can be respectful and still check for traps."

If `act2_edermath_cache_routework`:

- Nim, later: "Daran's compass is old routework, not nostalgia. Whoever kept it knew the map would matter again."

### Miner's Exchange

Gate: `miners_exchange_seen`

When Halia discusses missing crews:

- Tolan: "Mine crews disappear twice. First from the road, then from the ledgers if nobody kicks the table."
- Bryn: "Halia kicks tables for profit. Still useful. Just keep your fingers out from under it."

If the player inspects ledgers:

- Nim, later: "Someone made absence balance. That is mathematically offensive and politically worse."
- Kaelis: "The missing crews cluster around routes people were taught to avoid."

If the player resolves a claim dispute:

- Rhogar: "A fair hearing is not soft. It tells frightened people the room still has rules."

### Old Owl Well

Gate: `old_owl_well`

Entry read:

- Bryn: "This place feels watched in the way a snare feels patient."
- Nim, later: "Old wells are archives with bad manners."
- Elira: "The dead here are not the only ones being used."

If `varyn_filter_logic_seen`:

- Kaelis: "They were not guarding treasure. They were filtering who got curious enough to reach it."
- Bryn: "That is worse, right? Please say that is worse."

If the player protects workers or prisoners:

- Elira: "Good. Nobody should become a footnote because the map wanted privacy."

### Wyvern Tor

Gate: `wyvern_tor`

Entry read:

- Kaelis: "High ground. Fresh tracks. Worgs lower than the orcs. They expect fear to run downhill."
- Rhogar: "Then we climb."
- Tolan: "And keep our footing. Heroics roll badly on loose stone."

If `varyn_detour_logic_seen`:

- Kaelis: "This was a detour trap. Make the safe road look deadly, then punish the road people choose instead."
- Bryn: "A map that herds you is just a cage with scenery."

If rescued drovers point toward Cinderfall:

- Elira: "They kept the drover alive just long enough to make terror useful. That is not mercy. That is accounting."

### Cinderfall Ruins

Gate: `hidden_route_unlocked` or `cinderfall_ruins_cleared`

Entry read:

- Bryn: "We should not be here. Which, historically, is where the useful things hide."
- Kaelis: "Too many paths converge here. A ruin should not have traffic discipline."
- Nim, later: "This is relay thinking. Not a camp. Not a shrine. A machine pretending to be wreckage."

If `cinderfall_relay_destroyed`:

- Tolan: "That was a nerve, not a nest. Good thing to cut."
- Rhogar: "A hidden command line is still a battlefield. We held it."

If Bryn and Rhogar are both present after relay destruction:

- Bryn: "Public truth gets people hurt."
- Rhogar: "Hidden truth lets the guilty choose the next victim."
- Player choice can set `act1_companion_conflict_side`.

### Stonehill War Room

Gate: both major outer routes cleared

Opening:

- Tolan: "This is where towns either become a line or a crowd."
- Elira: "Let them speak fear before anyone tries to weaponize it."
- Bryn: "And watch who enjoys being the loudest."

If `act1_town_fear` is high:

- Rhogar: "Do not shame them for fear. Give fear a duty."
- Kaelis: "A frightened room still has patterns. Find the person pulling them crooked."

If `act1_survivors_saved` is high:

- Elira: "Survivors change the room. They make fear answer to names."

### Ashfall Watch

Gate: `ashfall_watch`

Entry:

- Rhogar: "We end the field command here."
- Tolan: "No breaks. No chasing. Watch the gates."
- Kaelis: "They built escape into the watch rotations. Someone expects failure to travel."

Prisoner yard:

- Elira: "Open cages first if you can. A prisoner left for later may not have later."
- Bryn: "Keys, hinges, guard habits. In that order, unless someone starts screaming."

Signal event:

- Nim, later: "Signal logic. One wrong bell becomes three wrong decisions."
- Kaelis: "Cut the message before the blade. Messages move faster."

Faith Under Ash choice:

- Elira, mercy route: "Mercy here is not innocence. It is refusing to let their cruelty choose what our hands become."
- Elira, hard verdict route: "Then do not call it peace. Call it judgment, and carry the weight honestly."
- Rhogar: "An oath can permit a hard sentence. It cannot permit hiding from its name."
- Tolan: "If they live, guard them. If they die, do not pretend that makes the next choice lighter."

### Lantern Vigil

Gate: post-Ashfall return

If `elira_mercy_blessing`:

- Elira: "Hope is not softer because it survived blood. It is sharper."

If `elira_hard_verdict`:

- Elira: "I will still pray. Not because I am certain. Because I am not."

If `act1_town_fear` low:

- Rhogar: "The town stands differently tonight."
- Bryn: "Less like a kicked dog. More like a dog considering where to bite."

If `act1_survivors_saved` high:

- Tolan: "Listen. More voices than bells. That is a victory no ledger should get to summarize."

### Tresendar Manor

Gate: `tresendar_manor`

Entry:

- Elira: "There is suffering here. Old, but not asleep."
- Bryn: "Cellars have opinions. I hate when they are informed."
- Nim, later: "The stonework has been reused too many times. Every owner left instructions by accident."

Cistern Eye bargain:

- Irielle, later or debug: "Do not give it anything you need to stay yourself."
- Bryn: "Secrets are not coins. Spend one and people start asking what else you carry."
- Rhogar: "A truth taken under hunger is not honest trade."

If the player trades a companion secret:

- Affected companion should receive a significant negative disposition echo.
- Elira: "Do not call that strategy before you have called it betrayal."
- Tolan: "A line breaks fastest when the person beside you sells your footing."

If `deep_ledger_hint_count` increases:

- Nim, later: "It said book, route, and swallowing in the same breath. That is either madness or a map with teeth."

### Emberhall Cellars And Varyn

Gate: `emberhall_cellars`

Chained clerk:

- Elira: "Poisoned witnesses are still witnesses. Keep them breathing before the story narrows."
- Kaelis: "Ask what route they were told not to see."
- Bryn: "Clerks know where lies get filed when nobody wants to keep them at home."

Ledger event:

- Nim, later: "The exits are written like arguments. One of them is missing its premise."
- Tolan: "If a ledger can tell soldiers where to stand, it can tell them where to die."

Before Varyn fight:

- Rhogar: "You do not own a road because you can predict who bleeds on it."
- Kaelis: "He wants the obvious attack. Do not give him only one answer."
- Bryn: "If this is a trap, make it expensive."

After Varyn route displacement:

- Nim, if present in future replay: "That was not escape magic. It behaved like a route correction."
- Irielle, post-Act 2 knowledge: "Something let him leave the choice, not the room."
- Elira: "Do not let the impossible exit steal the truth that Phandalin survived."

### Act 1 Completion

Gate: `act1_complete`

Clean victory:

- Rhogar: "Let the town have the word victory. We can carry the footnotes."
- Bryn: "A clean win. Suspicious. I will take it."

Costly victory:

- Tolan: "Open road, bruised town. Still counts. Counting is not the same as healing."
- Elira: "Then we start healing before someone mistakes survival for being done."

Fractured victory:

- Kaelis: "We opened the road. The fear found side paths."
- Elira: "Then the next work is not glory. It is repair."

If `varyn_route_displaced`:

- Nim, later: "Keep every note about the impossible exit. It may be the first honest map of what comes next."

## Act 2 Inputs

### Claims Council

Gate: `act2_claims_council`

Opening:

- Halia angle, Bryn: "If Halia says leverage, ask who pays interest."
- Linene angle, Tolan: "Discipline keeps people fed when politics starts wearing good boots."
- Wardens angle, Elira: "Caution is not delay if it keeps the living from becoming proof too late."
- Daran angle, Kaelis: "Old scouts do not keep caches because they enjoy nostalgia."

Sponsor choice:

- `act2_sponsor == "exchange"`:
  - Bryn: "Fast and sharp. Useful. Also exactly how some knives describe themselves."
  - Rhogar: "If we choose speed, we must guard what speed tempts us to ignore."
- `act2_sponsor == "lionshield"`:
  - Tolan: "A supply line with discipline beats three heroic guesses."
  - Nim: "Reliable logistics are just maps with soup attached."
- `act2_sponsor == "wardens"`:
  - Elira: "Slower mercy is still movement."
  - Kaelis: "Slow can work if nobody mistakes it for blind."

If `act2_starting_pressure` is high:

- Irielle, if recruited later in flashback echo: "The town was already listening to fear before the cave started speaking."

### Expedition Hub

Gate: `act2_expedition_hub`

When choosing an early lead:

- Conyberry:
  - Elira: "If Agatha knows what grief remembers, we should ask before grief is all we have left."
  - Irielle, later: "Old dead sometimes tell cleaner truths than living cultists."
- Neverwinter Wood:
  - Kaelis: "Survey camps fail quietly first. That is when you still have time."
  - Bryn: "Woods hide bodies and bad decisions with equal enthusiasm."
- Stonehollow Dig:
  - Nim, before recruited as NPC: "A collapse is a sentence. I would very much like to know who wrote the verb."
  - Tolan: "Dig sites punish rushing. They also punish hesitation. Miserable places."

If one early lead is about to be delayed:

- Kaelis: "Leaving a route unread does not freeze it. Someone else keeps moving."
- Elira: "Delay spends lives whether or not we sign the receipt."
- Nim: "Incomplete maps do not stay incomplete. They become confidently wrong."

### Conyberry And Agatha's Circuit

Gate: `conyberry_agatha_circuit`

Entry:

- Elira: "Speak gently. The dead are not props just because they cannot leave."
- Irielle: "Do not mistake silence for consent. Some places are only quiet because they are holding their breath."

If `agatha_truth_clear`:

- Nim: "A clear warning from a spirit is rare. Terrifyingly efficient, but rare."
- Elira: "Then we honor it by acting before it becomes an elegy."

If Conyberry was delayed:

- Elira: "A late warning can still save someone. It just arrives carrying more names."

Lantern of Tymora choice:

- Carry lantern into field:
  - Elira: "Then hope walks where the wound is deepest."
- Leave lantern in town:
  - Elira: "Then the town keeps a light while we walk into dark. That is not lesser work."
- Rhogar: "A guarded light and a carried light are both vows. Choose which vow answers more need."

### Neverwinter Wood Survey Camp

Gate: `neverwinter_wood_survey`

Entry:

- Kaelis: "Wrong bird calls. Cut trail marks. Someone taught the woods to stutter."
- Bryn: "I hate a campsite that looks abandoned politely."

If saboteur signs are found:

- Kaelis: "These are route edits. Not tracks. Edits."
- Nim: "Someone corrected the map in the field, which is rude, dangerous, and technically impressive."

Kaelis personal choice:

- Preserve hidden trail:
  - Kaelis: "A hidden path can save people if the right hands keep it quiet."
  - Rhogar: "Then swear who those hands are."
- Burn hidden trail:
  - Kaelis: "No one uses it cleanly if no one uses it at all."
  - Bryn: "Burning an exit feels awful. Sometimes awful is the point."

### Stonehollow Dig

Gate: `stonehollow_dig`

Entry before Nim joins:

- Nim: "The braces failed in sequence. Stone is stubborn, not theatrical. Someone helped."

If Nim is rescued late:

- Nim: "I am grateful. Also furious. Give me a moment to arrange those alphabetically."

If Nim is recruited early:

- Nim: "Excellent. Terrifying. I have always wanted to be useful somewhere I might be crushed."

If `stonehollow_dig_cleared` cleanly:

- Nim: "We recovered survey truth before it turned into folklore. That matters more than it sounds."

Missing Theorem choice:

- Preserve theorem:
  - Nim: "Dangerous knowledge is still knowledge. That is not a defense. It is the problem."
  - Irielle: "Carry it only if you can hear when it starts carrying you."
- Burn corrupted pages:
  - Nim: "There. I hate that I agree with myself."
  - Elira: "Some pages are wounds. Closing them is not ignorance."

### Sabotage Night

Gate: `phandalin_sabotage_resolved`

Before priority choice:

- Save claims hall:
  - Rhogar: "If the hall breaks, every promise made inside it becomes easier to steal."
  - Bryn: "Just remember people can die while rooms stay official."
- Save shrine lane and civilians:
  - Elira: "The living are not a distraction from the town. They are the town."
  - Tolan: "Civilians first makes the next argument messier. Messy is fine if they are alive."
- Hunt infiltrator cell:
  - Kaelis: "Cut the hand changing the map or we spend tomorrow rescuing people from routes that no longer exist."
  - Nim: "I dislike agreeing with the terrifyingly quiet scout, but yes."

Set pattern tags:

- Claims hall: `pattern_preserves_institutions`
- Shrine lane: `pattern_preserves_people`
- Infiltrator cell: `pattern_hunts_systems`

Post-choice tension:

- If civilians suffer: Elira colder in the next hub.
- If claims hall suffers: Rhogar and Linene-aligned companions press the cost.
- If infiltrator escapes: Kaelis and Nim warn about Act 3 route prediction.

### Broken Prospect

Gate: `broken_prospect`

If chosen before South Adit:

- Tolan: "This is the route-first choice. Fine. Then make it count enough to answer for the people waiting elsewhere."
- Kaelis: "Cleaner route now. Worse rescue later. No point pretending otherwise."

If chosen after South Adit:

- Bryn: "The road got meaner while we were saving people. Very rude. Very predictable."
- Nim: "Delayed structures do not simply decay. They learn from neglect."

Tolan personal choice:

- Salvage tainted brace-iron:
  - Tolan: "Useful wrongness is still wrong. But I have seen bridges held by worse."
- Destroy profitable wrongness:
  - Tolan: "Good. Let nobody get rich enough to call this necessary."

### South Adit

Gate: `south_adit`

If chosen before Broken Prospect:

- Elira: "Captives first. We can argue routes with living mouths later."
- Rhogar: "A rescue that costs advantage may still buy honor."

If chosen after Broken Prospect:

- Irielle, when found: "Late is not the same as false. But it does have a sound."
- Elira: "Then let the next sound be keys."

Irielle recruitment:

- Irielle: "I can walk with you. I cannot promise quiet inside my own head."
- Elira: "Then we do not ask quiet of you. We ask truth."
- Nim: "Truth with footnotes. Very important distinction."

Starved Signal choice:

- Teach counter-cadence:
  - Irielle: "A weapon, yes. Also a door. Promise me you know the difference when it opens."
  - Nim: "I can notate it without understanding it, which is usually the start of disaster."
- Bury counter-cadence:
  - Irielle: "Good. Some songs survive only because frightened people keep humming proof."
  - Kaelis: "Buried tools have a way of being dug up by worse hands."

### Wave Echo Outer Galleries

Gate: `wave_echo_outer_galleries`

Entry:

- Nim: "This place is not echoing. It is answering with a delay."
- Irielle: "No. It is deciding which answer you want to hear."
- Tolan: "I miss ordinary caves. Ordinary caves only try to drop rocks on you."

If route state is strong:

- Kaelis: "We own enough of the approach that their ambush has to improvise."

If route state is weak:

- Bryn: "Every tunnel feels like it knows our name. I would like that to stop."

### Black Lake Causeway

Gate: `black_lake_causeway`

Priority choice counsel:

- Purify shrine:
  - Elira: "If the shrine stays wrong, every frightened person who touches it carries the wrongness forward."
  - Irielle: "A corrupted prayer is still a hook."
- Raid barracks:
  - Tolan: "Break the fighters before they decide the causeway owns the tempo."
  - Rhogar: "A clean strike here protects every slower mercy after."
- Secure causeway route:
  - Kaelis: "If the crossing remains theirs, every other victory has to pass through their hands."
  - Nim: "Causeways are decisions made in stone. This one has been edited."

If Irielle's counter-cadence is known:

- Irielle: "I can make the song miss a beat. After that, move before it remembers us."

### Forge Of Spells

Gate: `forge_of_spells`

Entry:

- Nim: "The Forge is not only making magic stronger. It is making intention louder."
- Irielle: "Caldra wanted quiet so something else could hear itself through us."
- Elira: "Then keep naming people. Names are heavy. They keep souls from becoming instruments."

Before Caldra:

- Rhogar: "Revelation without mercy is only conquest wearing a holy mouth."
- Tolan: "She wants us listening upward. Watch the floor."
- Bryn: "If a ritual needs everyone quiet, I vote we become very irritating."

Lens mapped:

- Nim: "Witness, ritual, shard. Three legs. Break one and the table lies."
- Irielle: "Break two and it screams."

Lens blinded:

- Nim: "We are working from damage patterns, which is scholar-speak for please duck."

Act 2 completion:

- Low Whisper Pressure:
  - Irielle: "It did not leave cleanly. But it did leave less of itself."
- High Whisper Pressure:
  - Elira: "We won with something still clinging to the edges. Do not call that paranoia. Call it follow-up care."
- `counter_cadence_known`:
  - Irielle: "Keep the cadence ugly. Pretty songs are easier to obey."

## Act 3 Inputs

Act 3 is roadmap and scaffold content. These inputs should be treated as planning targets until the full route exists.

### Early Act 3: Varyn's Living Map

Gate: `act3_started` and not `malzurath_revealed`

Allowed language: route, map, signal, pressure, completed account, false roads, prediction.

Forbidden language: Malzurath, Keeper of the Ninth Ledger, secret architect.

If `player_pattern_profile == "mercy_first"`:

- Varyn: "You move toward the hurt first. Admirable. Measurable."
- Elira: "If he can measure mercy, make him learn it still changes shape."

If `player_pattern_profile == "institution_first"`:

- Varyn: "You preserve rooms, seals, and witnesses. You mistake structure for freedom."
- Rhogar: "Structure can guard freedom when the speaker remembers humility."

If `player_pattern_profile == "route_first"`:

- Varyn: "You hunt the system. That makes you useful to it."
- Kaelis: "Only if we keep using the routes he expects us to hate."

If `player_pattern_profile == "secrecy_first"`:

- Varyn: "You bury truths and call it mercy."
- Bryn: "Sometimes buried truth is a seed. Sometimes it is a body. Learn the difference."

If `player_pattern_profile == "force_first"`:

- Varyn: "You prefer clean breaks. The world records those easily."
- Tolan: "Then we make one messy enough to matter."

If `player_pattern_profile == "chaos_first"`:

- Irielle: "He thinks disorder is just an unfiled pattern. Do not become predictable by trying to be random."

### The Ninth Ledger Opens

Gate: `scene_act3_ninth_ledger_opens`

Existing reveal rule:

- Irielle names Malzurath first if present.
- Else Nim names Malzurath if present.
- Else narration names Malzurath.

Add companion resistance echoes after reveal:

- Elira: "No ledger gets to call mercy an error just because it could not profit from it."
- Bryn: "I have spent my whole life leaving routes off maps. Finally useful."
- Rhogar: "A vow binds the speaker. It does not give the page ownership of the future."
- Tolan: "Survival is not proof the dead were meant to die."
- Kaelis: "A map that knows every trail still has to guess why someone walks."
- Nim: "If a record makes reality obey, then contradiction is not a mistake. It is a tool."
- Irielle: "It hates songs that do not resolve. Good. Stay ugly."

If `act3_reveal_route_grammar_broken`:

- Nim: "You did not break ink. You broke obedience disguised as syntax."

If `act3_reveal_false_author_named`:

- Kaelis: "Varyn flinched before the page did. Remember that. He was being tracked too."

If contradiction route chosen:

- Elira: "A contradiction can be honest when the world is cruel enough to demand one clean answer."

### Post-Reveal Ledger Pressure

Gate: `malzurath_revealed`

When a recorded outcome appears:

- Irielle: "Do not answer the first version. It writes that one for you."
- Nim: "The Ledger predicts the efficient choice. Inefficiency may be a moral instrument. I hate this field."
- Bryn: "So we win by being inconvenient? Excellent. My time has come."

When spending an unrecorded choice token:

- Elira: "Spend it on a person, not pride."
- Rhogar: "Spend it where a future was stolen."
- Tolan: "Spend it where standing still would make us accomplices."
- Kaelis: "Spend it where the map is too confident."
- Nim: "Spend it where the equation closes too neatly."
- Irielle: "Spend it before the page teaches you to want the cost."

### Late Act 3: Varyn And Malzurath

If Varyn becomes a bitter temporary ally:

- Bryn: "I hate this. I hate that he is useful more."
- Rhogar: "Useful is not forgiven."
- Varyn: "I did not ask forgiveness."
- Elira: "Good. You are not ready to receive it."

If Varyn is unmade:

- Nim: "He became a route so completely the Ledger treated him as infrastructure."
- Tolan: "That is not a fate. That is a warning with a corpse missing."

If Varyn becomes a witness:

- Kaelis: "Let him testify. Then watch who tries to edit the testimony."
- Irielle: "Witness is dangerous to a thing that survives by making records sound complete."

### Act 3 Finale

Gate: `act3_finale_resolved`

High companion testimony:

- Elira: "We are not free because the page failed. We are free because people kept answering each other."
- Rhogar: "The future is not ownerless. It belongs to those who will live it."

Low companion testimony:

- Bryn: "We made it. I am not sure how much of us the road got to keep."
- Kaelis: "Then count what came back. Start there."

High `ninth_ledger_pressure`:

- Irielle: "It is weaker, not gone. There is a difference, and it will try to live in that difference."

Low `ninth_ledger_pressure`:

- Nim: "The account has holes. Beautiful, irresponsible holes."

## Secret Act 4 Inputs

Secret Act 4 should only appear after `secret_act4_unlocked`. These inputs should be dense and personal, not broad exposition.

### Unwritten Threshold

Gate: `act4_unwritten_road_entered`

If asking a companion to anchor the first mile:

- Elira: "Then let the first mile remember a life no page gets to spend."
- Rhogar: "Then I anchor it with a vow that names no owner."
- Bryn: "Then I anchor it with an exit nobody sold."
- Kaelis: "Then I anchor it with a trail walked for its own sake."
- Tolan: "Then I anchor it with the line we held because people were behind it."
- Nim: "Then I anchor it with an unfinished map. Which is, apparently, philosophy now."
- Irielle: "Then I anchor it with a silence that belongs to me."

### Witness Crossroads

Gate: `act4_witness_crossroads`

Each companion can testify if Great+, personal arc resolved, or directly relevant to Act 3 counterplay:

- Elira: "Mercy is not an accounting error. It is the moment the account admits it is not the world."
- Rhogar: "Duty that owns the future is tyranny. Duty that serves the living is a hand extended."
- Bryn: "A hidden road can be cowardice. It can also be shelter. Context matters, you overdressed notebook."
- Kaelis: "Prediction is not understanding. A snare knows where prey steps. It does not know why the deer runs."
- Tolan: "Do not tell me who was meant to die. I have buried too many people who were meant to come home."
- Nim: "A complete map of choice is not a map. It is a cage with excellent labeling."
- Irielle: "I was taught to sing until I disappeared inside someone else's answer. I decline."

### Blank Archive

Gate: `act4_blank_archive`

Preserve blank archive:

- Nim: "A blank record can be sacred if what it preserves is possibility."
- Irielle: "Leave some silence unharvested."

Burn predictive records:

- Rhogar: "Burn ownership, not memory."
- Elira: "Let no one confuse ash with healing. After this, we still remember."

Search for the ninth page:

- Bryn: "Fine. But if a blank page starts flirting with destiny, I am stabbing the shelf."
- Kaelis: "Move slowly. The page wants urgency."

### Varyn's Last Route

Gate: `act4_varyn_last_route`

If Varyn is witness:

- Varyn: "I built roads to end uncertainty."
- Tolan: "You built roads to make other people pay for yours."

If Varyn is bitter ally:

- Bryn: "You are not on our side."
- Varyn: "No. I am against the thing that mistook me for a solved problem."
- Elira: "That may be enough for one road. No farther."

If Varyn is absent or unmade:

- Kaelis: "Even gone, he leaves tracks."
- Nim: "That is what systems do when people mistake themselves for architecture."

### Ninth Page

Gate: `act4_ninth_page`

Break Ledger authority:

- Rhogar: "No page commands a vow before it is spoken."
- Irielle: "No song owns the silence before breath."

Seal the Ledger:

- Elira: "Then let containment be a mercy with locks."
- Tolan: "And guards. Mercy with locks still needs guards."

Burn the Ledger:

- Nim: "If we burn it, we also burn explanations we may someday need."
- Bryn: "Some explanations are just traps with better handwriting."

Rewrite the ninth page:

- Kaelis: "Write a road that changes when kindness does."
- Elira: "Write nothing that can spend a person without meeting them."

## Party Composition Rules

### Single companion present

Use one precise line. Let that companion's specialty color the scene.

### Two companions present

Prefer a two-line exchange when they have a natural contrast:

- Elira + Tolan: mercy as discipline.
- Elira + Rhogar: faith and oath.
- Elira + Bryn: quiet kindness and visible mercy.
- Bryn + Kaelis: hidden routes, exits, ambush reads.
- Bryn + Rhogar: hidden truth versus public duty.
- Tolan + Rhogar: line discipline and oath.
- Nim + Irielle: dangerous knowledge and dangerous resonance.
- Nim + Bryn: ledgers, maps, and lies.
- Irielle + Elira: trauma, mercy, and refusing coercive certainty.
- Kaelis + Nim: route evidence versus map theory.

### Three or more companions present

Use a priority speaker, then optionally one short counterline. Do not let every companion speak.

Priority examples:

- Wounded or mercy choice: Elira, then Tolan or Rhogar.
- False authority: Rhogar, then Bryn or Kaelis.
- Route map or ambush: Kaelis, then Nim.
- Ledger or records: Nim, then Bryn or Tolan.
- Whisper or Choir: Irielle, then Nim or Elira.
- Public truth conflict: Rhogar, then Bryn.

### Bad trust variants

If a companion is Bad but still present, their input can become clipped or skeptical:

- Elira: "You know what mercy asks. Whether you answer is no longer my assumption."
- Rhogar: "I will hold the line. I am less certain you will name it honestly."
- Bryn: "I will point out the exit. Trusting what you do with it is extra."
- Kaelis: "Pattern is clear. Motive is not."
- Tolan: "Say the order. I will decide whether it deserves my feet."
- Nim: "I can explain the mechanism. I cannot make you respect the warning."
- Irielle: "I know the sound of being used. Be careful what note you ask me to sing."

### Exceptional trust variants

Exceptional trust should not make companions flatter the player. It should let them risk a more personal truth:

- Elira: "I can say the hard thing because I trust you not to mistake it for distance."
- Rhogar: "Your judgment has become a place I can stand without lowering my guard."
- Bryn: "I am scared. Obviously. But not of being unheard, which is new and upsetting."
- Kaelis: "I see three paths. I would trust your fourth."
- Tolan: "I have held lines with kin who knew me less."
- Nim: "Here is the part of the theory I would usually hide until after survival."
- Irielle: "The whisper is near. I can tell you before it becomes my voice."

## Outcome Rules

Only attach mechanical outcomes when the companion is responding to a meaningful player decision.

Recommended small outcomes:

- `+1 disposition`: player acted directly in line with the companion's core value at risk or cost.
- `-1 disposition`: player violated a value but not personally.
- `-2 disposition`: player used the companion, endangered their personal stakes, or betrayed a vulnerable group.
- Set a one-shot flag for the input.
- Add a clue only if the companion identifies new evidence, not if they merely react.
- Add journal text only for major consequences or Act 3/4 counterplay.

Avoid:

- Rewarding every agreeable line.
- Punishing every disagreement.
- Making companion input feel like the "correct answer" signpost.
- Letting one companion repeatedly override another in scenes where both have standing.

## Implementation Order

1. Add a lightweight dialogue input registry with hard gates, topic tags, and one-shot flags.
2. Wire only a few scene hooks first:
   - Neverwinter briefing.
   - Blackwake Crossing.
   - Phandalin hub arrival.
   - Stonehill Inn.
   - Ashfall Watch.
   - Emberhall Cellars.
3. Add party-composition pair exchanges for Elira/Tolan, Bryn/Rhogar, Kaelis/Bryn, Nim/Irielle.
4. Add Act 2 scaffold hooks after the Act 2 scene flow is stable.
5. Add Act 3 pre-reveal inputs only with forbidden-term tests.
6. Add post-reveal and Secret Act 4 inputs after the relevant flags exist.

## Test Targets

- Companion absent means no line.
- Companion inactive but recruited means no live scene line unless the scene is camp or a hub follow-up.
- A line with a one-shot flag does not repeat.
- Topic tag selects the expected companion when multiple companions are active.
- Bad and Exceptional variants override the neutral line only when thresholds match.
- Pre-reveal Act 3 lines do not contain `Malzurath`, `Keeper of the Ninth Ledger`, or `secret architect`.
- Post-reveal Act 3 lines may use explicit Ledger language only after `malzurath_revealed`.
- Blackwake evidence, rescue, and sabotage each select different companion echoes.
- Act 2 delayed lead state changes the companion warning text.
- Secret Act 4 testimony requires the unlock gate and valid companion anchor conditions.
