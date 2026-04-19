# Companion Camp Banter Branching Draft

This draft expands camp from only player-to-companion talks into optional companion-to-companion scenes. The goal is to let the party process route pressure, personal quests, Varyn's visible system, and the later hidden-villain trail without revealing the secret architect before the planned Act 3 midpoint.

## Design Goals

- Make camp feel like a party, not a row of isolated loyalty menus.
- Use companion pairings to restate the campaign's main question: who gets sorted, named, recorded, and saved.
- Let Act 1 choices immediately echo through Elira, Tolan, Bryn, Kaelis, and Rhogar.
- Give Nim and Irielle strong Act 2 camp voices around maps, resonance, dangerous knowledge, and the Quiet Choir.
- Foreshadow Malzurath only through indirect language until the Act 3 midpoint reveal. Before that point, companions may mention ledgers, ninth columns, listening maps, route memory, and choices that feel counted, but not his name or full role.

## Current Runtime Fit

The current camp menu supports one-on-one companion talks through each companion profile's `camp_topics`. Companion banter can be added as a separate registry instead of overloading those talks.

Suggested menu text:

- `Listen around the campfire`
- Opens the highest-priority available banter scene, or a short list if multiple are available.
- Banters should be one-shot by default, with rare recurring "state check" variants for major act transitions.

Suggested data shape:

```python
{
    "id": "camp_banter_elira_tolan_greywake",
    "title": "The Wounded Line",
    "participants": ["elira", "tolan"],
    "requires_companions": ["elira", "tolan"],
    "requires_flags": ["greywake_triage_yard_seen"],
    "requires_any_flags": ["greywake_wounded_stabilized", "greywake_wounded_line_guarded", "greywake_manifest_preserved"],
    "blocked_flags": ["camp_banter_elira_tolan_greywake_seen"],
    "stage": "act1",
    "priority": 40,
    "lines": [...],
    "set_flags": ["camp_banter_elira_tolan_greywake_seen"],
}
```

Optional branch helpers:

- `requires_relationship`: minimum disposition for one or more participants.
- `requires_metric`: Act 2 pressure thresholds such as high `Whisper Pressure` or low `Town Stability`.
- `variant_flags`: pick replacement lines when a prior choice happened.
- `outcomes`: small relationship changes only when the banter contains a real disagreement.

## Secret-Villain Guardrail

Before the middle of Act 3, no companion should say `Malzurath`, `Quiet Architect`, or `Keeper of the Ninth Ledger` unless the player has already learned those terms through the main plot.

Allowed pre-reveal language:

- "someone is counting"
- "the ledger has a ninth column"
- "the road remembers who reaches it"
- "a map that listens"
- "a schedule, not a report"
- "choices filed before anyone makes them"

Direct language allowed only after a flag such as `act3_malzurath_revealed`:

- Malzurath as the architect behind the ledger logic
- Varyn as a willing visible instrument rather than the root cause
- The ledger as a reality-binding system rather than only criminal accounting
- Secret Act 4 implications that the party may have been recorded as a completed route

## Act 1 Early Banters

### `camp_banter_elira_tolan_greywake`

Participants: Elira, Tolan  
Gate: Elira and Tolan recruited, `greywake_triage_yard_seen`  
Branch flags: `greywake_wounded_stabilized`, `greywake_wounded_line_guarded`, `greywake_manifest_preserved`, `greywake_manifest_destroyed`, and `elira_initial_trust_reason`

Purpose: Turn Greywake into the first systemic camp conversation. Tolan reads the triage yard as battlefield sorting. Elira frames mercy as action, not feeling.

Base lines:

- Tolan: "That yard was not panic. Panic leaves a mess. That was a clerk with a knife."
- Elira: "A clerk, a captain, or someone who taught both of them to think the same way."
- Tolan: "You triaged like a shield wall. Worst bleeding first, then breathing, then anyone still shouting."
- Elira: "And you talk about mercy like a barricade."
- Tolan: "Aye. Sometimes it is."

If `greywake_wounded_stabilized` or `greywake_wounded_line_guarded`:

- Elira: "They will remember who stood between them and the road."
- Tolan: "Good. Let the enemy learn that witnesses can have armor too."

If `greywake_manifest_preserved`:

- Tolan: "That manifest was no casualty list. It was the fight before the fight."
- Elira: "Names sorted into outcomes. Tymora hates a loaded die."

If `greywake_manifest_destroyed`:

- Tolan: "Paper burns. People who lived can still point."
- Elira: "Then we keep them alive long enough to be believed."

If `elira_initial_trust_reason == spiritual_kinship`:

- Elira: "Faith did not make the work lighter. It only made looking away impossible."
- Tolan: "That is a better prayer than most hymns."

### `camp_banter_elira_rhogar_faith_action`

Participants: Elira, Rhogar  
Gate: Elira and Rhogar recruited, any of `wayside_luck_shrine_seen`, `greywake_triage_yard_seen`, `road_ambush_cleared`

Purpose: Connect Elira's "faith becomes action" first-read moment to Rhogar's oath identity.

Base lines:

- Rhogar: "You tied the shrine bell as if it could hear you."
- Elira: "No. I tied it because we could."
- Rhogar: "A promise, then."
- Elira: "A small one. Small promises are harder to excuse."
- Rhogar: "An oath begins the same way. Not with thunder. With a hand placed where it cannot easily be withdrawn."

If the player skipped shrine help:

- Elira: "Some people need longer to find the wounded thing in front of them."
- Rhogar: "Then we stand where they must look."

If the player helped wounded:

- Rhogar: "They did not ask whether the road deserved saving. They saved who lay on it."
- Elira: "That is the only sermon I trust at first reading."

### `camp_banter_bryn_kaelis_road_angles`

Participants: Bryn, Kaelis  
Gate: Bryn and Kaelis recruited, `road_ambush_cleared` or `blackwake_completed`

Purpose: Let the two route-readers contrast instinct, maps, smuggling habits, and ambush logic.

Base lines:

- Bryn: "You count exits before you count faces."
- Kaelis: "Faces lie slower than exits close."
- Bryn: "That is horribly wise. I hate it."
- Kaelis: "You counted the cookfire smoke."
- Bryn: "Cookfires tell the truth. People put lies in their mouths, not their chimneys."

If Blackwake was resolved through witness exposure:

- Kaelis: "At Blackwake, the lie was in the uniforms."
- Bryn: "Uniforms are just costumes with better buttons."

If Blackwake was resolved through sabotage:

- Bryn: "Their checkpoint folded fast once the quiet bits stopped working."
- Kaelis: "Most systems look brave until one hinge is gone."

### `camp_banter_tolan_rhogar_line_and_oath`

Participants: Tolan, Rhogar  
Gate: Tolan and Rhogar recruited, `road_ambush_cleared` or `ashfall_watch_cleared`

Purpose: Establish their shared front-line ethics before late Act 1 choices test them.

Base lines:

- Tolan: "An oath is a fine thing until arrows start asking questions."
- Rhogar: "Then the oath answers by where you stand."
- Tolan: "Spoken like someone who has not had to move a wagon with two wheels and three cowards."
- Rhogar: "Spoken like someone whose discipline has become faith without admitting it."
- Tolan: "Careful. I am allergic to compliments."

If `ashfall_watch_prisoners_saved`:

- Rhogar: "The prisoners lived because the line bent."
- Tolan: "A line that never bends is just a wall waiting to crack."

If `act1_town_fear_high`:

- Tolan: "People are watching for who panics first."
- Rhogar: "Then we do not."

## Act 1 Phandalin and Mid-Route Banters

### `camp_banter_bryn_elira_quiet_mercy`

Participants: Bryn, Elira  
Gate: Bryn and Elira recruited, any of `stonehill_nera_treated`, `greywake_wounded_stabilized`, `greywake_wounded_line_guarded`, `songs_for_missing_nera_detail`

Purpose: Reward stealthy compassion and connect Bryn's "help without being watched" read to Elira's shrine values.

Base lines:

- Elira: "You dislike being seen doing kind things."
- Bryn: "Wild accusation. Hurtful. Accurate, but hurtful."
- Elira: "Why?"
- Bryn: "Because if people see it, they start deciding what it means."
- Elira: "It can mean someone was helped."
- Bryn: "That is the dangerous version."

If `stonehill_nera_treated`:

- Elira: "Nera breathed easier after you left."
- Bryn: "Then let that be the whole song."

If `greywake_wounded_stabilized` or `greywake_wounded_line_guarded`:

- Bryn: "Greywake was different. Too many eyes to be sneaky."
- Elira: "And still you helped."
- Bryn: "Do not make it sound noble. I panicked in a useful direction."

### `camp_banter_bryn_rhogar_public_truth`

Participants: Bryn, Rhogar  
Gate: Bryn and Rhogar recruited, `cinderfall_ruins_cleared` or `bryn_loose_ends_resolved`  
Branch flags: `bryn_ledger_sold`, `bryn_ledger_burned`, and `act1_companion_conflict_side`

Purpose: Seed or pay off their conflict about public exposure versus protecting vulnerable people from political blowback.

Base lines:

- Rhogar: "A hidden truth can protect the guilty."
- Bryn: "A shouted truth can get the powerless killed."
- Rhogar: "Then choose the place and hour, but do not bury it forever."
- Bryn: "Forever is expensive. I usually rent silence by the week."

If `act1_companion_conflict_side == rhogar`:

- Rhogar: "The town deserved to know who sold its roads."
- Bryn: "Aye. I just hope the town knows where to aim its anger."

If `act1_companion_conflict_side == bryn`:

- Bryn: "Some names stayed quiet because quiet kept people breathing."
- Rhogar: "Then the burden remains with us until quiet is no longer mercy."

If `bryn_ledger_sold`:

- Rhogar: "Leverage bought with rot still smells of rot."
- Bryn: "And clean hands do not open every locked door."

If `bryn_ledger_burned`:

- Bryn: "Ash cannot blackmail anyone."
- Rhogar: "Nor testify."
- Bryn: "I know."

### `camp_banter_kaelis_tolan_timing`

Participants: Kaelis, Tolan  
Gate: Kaelis and Tolan recruited, `road_ambush_cleared`

Purpose: Pair scout timing with shield timing.

Base lines:

- Kaelis: "You step half a breath before the hit."
- Tolan: "You vanish half a breath before anyone knows there is a hit."
- Kaelis: "Both are timing."
- Tolan: "Both are rude to whoever planned the ambush."
- Kaelis: "Good."

If `road_ambush_scouted`:

- Tolan: "Clean work on the ridge."
- Kaelis: "Clean means the wounded list stayed short."

If `road_ambush_scouted` is false:

- Kaelis: "I read the trees late."
- Tolan: "Then read the next ones angry, not ashamed."

### `camp_banter_elira_kaelis_silence`

Participants: Elira, Kaelis  
Gate: Elira and Kaelis recruited, any of `old_owl_well_cleared`, `greywake_triage_yard_seen`, `agatha_truth_secured`

Purpose: Build a quiet friendship around grief, stillness, and what silence means before Act 2 weaponizes listening.

Base lines:

- Elira: "You listen like silence might confess."
- Kaelis: "Sometimes it does."
- Elira: "And when it does not?"
- Kaelis: "Then it is waiting."
- Elira: "I used to think silence was where faith rested. Now I think it is where fear hides its shoes."

If `old_owl_well_cleared`:

- Kaelis: "Old Owl Well was too quiet after the fight."
- Elira: "Some places do not become peaceful just because they stop screaming."

### `camp_banter_tolan_bryn_stonehill_order`

Participants: Tolan, Bryn  
Gate: Tolan and Bryn recruited, `stonehill_war_room_seen` or `marked_keg_resolved`

Purpose: Give Stonehill's social pressure a camp echo.

Base lines:

- Tolan: "A room full of frightened folk can turn faster than a bad wheel."
- Bryn: "Bad wheels squeak first. Frightened folk smile."
- Tolan: "You watch smiles?"
- Bryn: "I watch who stops smiling when coin gets mentioned."

If `stonehill_marked_keg_named`:

- Tolan: "Public answer steadied them."
- Bryn: "Public answers also make public enemies."

If `marked_keg_resolved` without `stonehill_marked_keg_named`:

- Bryn: "Quiet fix, fewer broken cups."
- Tolan: "And fewer lessons learned."

## Act 1 Late Banters

### `camp_banter_elira_rhogar_faith_under_ash`

Participants: Elira, Rhogar  
Gate: Elira and Rhogar recruited, `elira_faith_under_ash_resolved`

Purpose: Reflect Elira's personal quest and Rhogar's moral vocabulary.

If mercy route:

- Rhogar: "Mercy is not softness. Not when given where anger has a claim."
- Elira: "I am not sure it was mercy. It may have been fear of becoming certain."
- Rhogar: "Certainty has killed more prisoners than rage."
- Elira: "Then I will call doubt a guardrail and keep walking."

If hard-verdict route:

- Elira: "I keep hearing the bell from the shrine."
- Rhogar: "Because judgment leaves an echo."
- Elira: "I thought a hard choice would feel cleaner."
- Rhogar: "Clean is not the same as just."

### `camp_banter_tolan_rhogar_ashfall`

Participants: Tolan, Rhogar  
Gate: Tolan and Rhogar recruited, `ashfall_watch_cleared`

Purpose: Pay off front-line ethics after Ashfall.

Base lines:

- Tolan: "Ashfall was built like a threat pretending to be a fort."
- Rhogar: "Then it fell like a fort pretending to be an oath."
- Tolan: "That sounded clever. I am deciding whether to resent it."
- Rhogar: "Take your time."

If `ashfall_prisoners_freed`:

- Tolan: "The prisoner line held."
- Rhogar: "Because we treated it as the gate."

If `ashfall_watch_cleared` without `ashfall_prisoners_freed`:

- Rhogar: "We broke their command and still lost people."
- Tolan: "A victory can be true and still make you sick."

### `camp_banter_bryn_kaelis_tresendar_eye`

Participants: Bryn, Kaelis  
Gate: Bryn and Kaelis recruited, `tresendar_nothic_route`

Purpose: Let the Cistern Eye's strange truth pressure unsettle the two most practical companions.

Base lines:

- Bryn: "I prefer secrets with pockets."
- Kaelis: "That thing had teeth where a secret should keep its door."
- Bryn: "Thank you for making my complaint worse."
- Kaelis: "You are welcome."

If `tresendar_nothic_route == bargain` or `tresendar_nothic_route == trade`:

- Kaelis: "It learned something from us."
- Bryn: "Everything does. The question is whether it paid."

If `tresendar_nothic_route == kill`:

- Bryn: "Dead horrors tell fewer stories."
- Kaelis: "Fewer is not none."

### `camp_banter_elira_tolan_after_varyn`

Participants: Elira, Tolan  
Gate: Elira and Tolan recruited, `varyn_body_defeated_act1`

Purpose: Put the Act 1 victory tier into companion mouths.

If `act1_victory_tier == clean_victory`:

- Tolan: "Town is bruised, not broken."
- Elira: "And the bell can still be repaired."
- Tolan: "You really mean to go back for that shrine."
- Elira: "Yes. Promises get smaller if you leave them untended."

If `act1_victory_tier == costly_victory`:

- Tolan: "We won with our teeth clenched."
- Elira: "Then we unclench them carefully. People mistake relief for healing."

If `act1_victory_tier == fractured_victory`:

- Elira: "The road is open, but people look at it like a wound."
- Tolan: "A wound can close wrong."
- Elira: "Then we do not pretend the scar is the cure."

## Act 2 Banters

### `camp_banter_nim_kaelis_maps_lie`

Participants: Nim, Kaelis  
Gate: Nim and Kaelis recruited, `stonehollow_dig_seen` or `neverwinter_wood_survey_seen`

Purpose: Contrast academic map truth with field-trail truth.

Base lines:

- Nim: "A map lies when it is old, proud, copied badly, or paid for by a fool."
- Kaelis: "A trail lies when someone wants you alive until the wrong bend."
- Nim: "So both our professions are mainly polite suspicion."
- Kaelis: "Mine is not polite."

If Stonehollow was delayed:

- Nim: "Stonehollow sat under bad math too long."
- Kaelis: "Then we stop trusting any line that wants to be finished for us."

If Route Control is high:

- Nim: "For once, the ink and the ground agree."
- Kaelis: "Do not say that too loudly."

### `camp_banter_nim_bryn_false_ledgers`

Participants: Nim, Bryn  
Gate: Nim and Bryn recruited, any of `miners_exchange_ledgers_checked`, `false_ledgers_unlocked`, `bryn_loose_ends_resolved`

Purpose: Make ledgers a bridge between Bryn's smuggling past, Nim's scholarship, and the campaign's counting motif.

Base lines:

- Nim: "Bad ledgers have personalities."
- Bryn: "Good ledgers do too. Smug ones."
- Nim: "This one leaves room in the margins for a number it refuses to name."
- Bryn: "That is not accounting. That is bait."

If `bryn_ledger_burned`:

- Nim: "You burned your old ledger."
- Bryn: "I retired a weapon before it learned new hands."

If `bryn_ledger_sold`:

- Nim: "You sold your old ledger."
- Bryn: "I rented the damage to someone useful."
- Nim: "That is a sentence with excellent balance and terrible implications."

Pre-reveal foreshadowing, before `act3_malzurath_revealed`:

- Nim: "There is a missing column in too many records."
- Bryn: "A column for what?"
- Nim: "For what the record wants next."

### `camp_banter_irielle_elira_after_adit`

Participants: Irielle, Elira  
Gate: Irielle and Elira recruited, `south_adit_captives_rescued` or `south_adit_seen`

Purpose: Let the healer and former Choir captive define compassion under whisper pressure.

Base lines:

- Irielle: "Do your prayers ever answer in someone else's voice?"
- Elira: "No."
- Irielle: "Good."
- Elira: "Not because silence is proof of safety. Because a prayer should leave you more yourself, not less."
- Irielle: "The Choir called that loneliness."
- Elira: "The Choir lied."

If South Adit was cleared early:

- Irielle: "You came before the voices learned everyone's names."
- Elira: "Then we were lucky."
- Irielle: "No. Luck is when the door opens. Someone still has to walk through."

If South Adit was delayed:

- Irielle: "You came late."
- Elira: "Yes."
- Irielle: "Say it again."
- Elira: "We came late."
- Irielle: "Good. Now it cannot grow teeth in the dark."

### `camp_banter_irielle_nim_dangerous_theorem`

Participants: Irielle, Nim  
Gate: Irielle and Nim recruited, `forge_lens_understood` or `missing_theorem_unlocked`

Purpose: Put knowledge-preservation pressure directly between the scholar and the survivor.

Base lines:

- Nim: "A dangerous theorem is not evil. It is a blade without a handle."
- Irielle: "The Choir says the same thing before handing someone the sharp end."
- Nim: "That is a fair objection and a devastating image."
- Irielle: "Do not admire it."
- Nim: "Too late, but I will behave."

If theorem preserved:

- Irielle: "You kept the pages."
- Nim: "I kept responsibility for them."
- Irielle: "Pages do not care who feels responsible."

If theorem burned:

- Nim: "I can still feel where the missing proof should sit."
- Irielle: "Good. Let it ache. An ache is better than an altar."

### `camp_banter_irielle_rhogar_chosen_certainty`

Participants: Irielle, Rhogar  
Gate: Irielle and Rhogar recruited, `south_adit_seen`

Purpose: Let Irielle challenge certainty while Rhogar distinguishes chosen oath from imposed doctrine.

Base lines:

- Irielle: "You sound certain when you speak."
- Rhogar: "I try to sound accountable."
- Irielle: "The Choir was certain."
- Rhogar: "The Choir demanded surrender. An oath demands return."
- Irielle: "Return to what?"
- Rhogar: "The person who must answer for what the oath has done."

If Whisper Pressure is high:

- Irielle: "Certainty is louder when the whispers are near."
- Rhogar: "Then I will speak less and stand better."

### `camp_banter_nim_tolan_shield_map`

Participants: Nim, Tolan  
Gate: Nim and Tolan recruited, `broken_prospect_seen` or `wave_echo_outer_galleries_seen`

Purpose: Connect Tolan's practical defense to Nim's route logic.

Base lines:

- Nim: "A shield is a map with one instruction."
- Tolan: "Stand here?"
- Nim: "More precisely, make here matter."
- Tolan: "I have heard worse from officers."
- Nim: "That is either praise or an indictment of officers."
- Tolan: "Both, lad."

If Broken Prospect first:

- Tolan: "We saved the route and paid in faces."
- Nim: "A map that costs people is not finished."

If South Adit first:

- Nim: "We saved the captives and let the route harden."
- Tolan: "Then the route gets a shield next."

## Act 3 and Secret-Architect Banters

### `camp_banter_bryn_elira_route_displacement`

Participants: Bryn, Elira  
Gate: Bryn and Elira recruited, `act3_route_displacement_seen`

Purpose: Show that Varyn's Act 1 road control was only the first visible expression of a larger system.

Before `act3_malzurath_revealed`:

- Bryn: "I hate a door that remembers where you meant to go."
- Elira: "Roads should not have intentions."
- Bryn: "Exactly. Roads should be dirt with aspirations."
- Elira: "And yet this one feels disappointed when we choose."
- Bryn: "Do not say that near the map."

After `act3_malzurath_revealed`:

- Elira: "Varyn sorted roads. Malzurath sorts meaning."
- Bryn: "I miss when our villains had normal hobbies."
- Elira: "He made cruelty look like administration."
- Bryn: "Then we make mercy look like sabotage."

### `camp_banter_nim_irielle_ninth_ledger`

Participants: Nim, Irielle  
Gate: Nim and Irielle recruited, any of `act3_ninth_column_seen`, `act3_malzurath_revealed`

Purpose: The core hidden-villain camp reveal conversation.

Before `act3_malzurath_revealed`:

- Nim: "The ninth column is not a sum. It is an appetite."
- Irielle: "Do not give it a body before we know where it keeps its mouth."
- Nim: "That may be the most academically useful threat I have ever received."
- Irielle: "It was advice."

After `act3_malzurath_revealed`:

- Nim: "Malzurath did not forge a ledger to describe reality. He forged one to make reality behave."
- Irielle: "The Choir listened for him without knowing whose ear they were feeding."
- Nim: "Varyn's routes, Caldra's resonance, the copied claims, the missing column..."
- Irielle: "All practice for being filed."

### `camp_banter_tolan_rhogar_recorded_routes`

Participants: Tolan, Rhogar  
Gate: Tolan and Rhogar recruited, `act3_malzurath_revealed`

Purpose: Front-liners confront an enemy who treats moral action as input data.

Base lines:

- Tolan: "I can fight a tyrant. I can fight a dragon. I dislike fighting bookkeeping."
- Rhogar: "Then we fight the hand that holds the pen."
- Tolan: "And if the page already has us?"
- Rhogar: "A record is not an oath."
- Tolan: "Good. Because I did not sign."

If Act 1 was clean victory:

- Rhogar: "He will count the people we saved as proof we can be steered."
- Tolan: "Then he has mistaken survivors for sheep."

If Act 1 was fractured victory:

- Tolan: "He will count every loss."
- Rhogar: "So will we. But not for the same reason."

### `camp_banter_full_party_before_secret_act4`

Participants: Any three companions, priority by presence  
Gate: `act3_malzurath_revealed`, late Act 3 transition, before Secret Act 4 entry

Purpose: Set up Secret Act 4 without explaining the whole plan in one exposition dump. This should feel like companions realizing the campaign has been treated as a route to completion.

Variant A, if Nim and Irielle are present:

- Nim: "The ledger does not end at the villain's defeat."
- Irielle: "It wants the shape of the ending."
- Elira: "Then we deny it certainty."
- Bryn: "I can steal certainty."
- Tolan: "Can you?"
- Bryn: "No, but it sounded braver than 'panic creatively.'"

Variant B, if Rhogar and Kaelis are present:

- Kaelis: "The path ahead is too clean."
- Rhogar: "A trap?"
- Kaelis: "A welcome mat."
- Tolan: "I hate those more."
- Rhogar: "Then we enter as guests who owe nothing."

Variant C, if Elira carries the shrine bell motif:

- Elira: "I keep thinking of the cracked bell."
- Bryn: "The shrine one?"
- Elira: "It rang wrong, but it rang. Maybe that matters now."
- Nim: "Imperfection as resistance."
- Irielle: "A song the ledger cannot complete."

## Implementation Slices

1. Add a companion banter registry and availability helper.
2. Add a camp menu option that chooses one available banter and marks it seen.
3. Implement Act 1 early banters for Elira, Tolan, Bryn, Kaelis, and Rhogar.
4. Add Act 1 late banters keyed to Ashfall, Tresendar, Varyn, and victory tier.
5. Add Act 2 banters for Nim and Irielle once those companions are implemented.
6. Add Act 3 reveal banters only after the `act3_malzurath_revealed` flag exists.

## Priority Banter Flags

| Banter id | Main gates | Seen flag |
| --- | --- | --- |
| `camp_banter_elira_tolan_greywake` | Elira, Tolan, `greywake_triage_yard_seen` | `camp_banter_elira_tolan_greywake_seen` |
| `camp_banter_elira_rhogar_faith_action` | Elira, Rhogar, shrine or Greywake seen | `camp_banter_elira_rhogar_faith_action_seen` |
| `camp_banter_bryn_kaelis_road_angles` | Bryn, Kaelis, High Road or Blackwake seen | `camp_banter_bryn_kaelis_road_angles_seen` |
| `camp_banter_bryn_elira_quiet_mercy` | Bryn, Elira, Stonehill or Greywake mercy flag | `camp_banter_bryn_elira_quiet_mercy_seen` |
| `camp_banter_bryn_rhogar_public_truth` | Bryn, Rhogar, Cinderfall or Bryn personal quest | `camp_banter_bryn_rhogar_public_truth_seen` |
| `camp_banter_elira_tolan_after_varyn` | Elira, Tolan, Varyn defeated | `camp_banter_elira_tolan_after_varyn_seen` |
| `camp_banter_nim_kaelis_maps_lie` | Nim, Kaelis, Stonehollow or survey camp | `camp_banter_nim_kaelis_maps_lie_seen` |
| `camp_banter_irielle_elira_after_adit` | Irielle, Elira, South Adit | `camp_banter_irielle_elira_after_adit_seen` |
| `camp_banter_nim_irielle_ninth_ledger` | Nim, Irielle, ninth-column or reveal flag | `camp_banter_nim_irielle_ninth_ledger_seen` |
| `camp_banter_full_party_before_secret_act4` | late Act 3 reveal transition | `camp_banter_full_party_before_secret_act4_seen` |
