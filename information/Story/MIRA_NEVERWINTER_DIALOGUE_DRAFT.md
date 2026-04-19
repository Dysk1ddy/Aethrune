# Mira Neverwinter Branching Dialogue Draft

This draft expands Mira Thann's Neverwinter briefing from a short premise scene into a reactive debrief hub. It covers:

- the first formal briefing after Greywake
- exclusive responses to choices made before reaching Mira
- return dialogue if the player comes back to Neverwinter after Phandalin-side progress

Design goal:

- Mira should feel like an intelligence officer updating her model as the player changes the facts.
- The player should feel that Wayside, Greywake, Blackwake, Phandalin, and later Act 1 sites have immediate political weight in Neverwinter.
- Longer answers should give color and stakes without replacing player agency or overexplaining future villains.

## Suggested Runtime Shape

Current scene:

- `scene_neverwinter_briefing`

Recommended helper split:

- `mira_dialogue_stage()`
- `mira_initial_question_options()`
- `mira_return_question_options()`
- `handle_mira_question(selection_key)`

Suggested stages:

| Stage | Gate |
| --- | --- |
| `initial_briefing` | no `phandalin_arrived` |
| `blackwake_return` | `blackwake_completed` and `blackwake_return_destination == neverwinter` |
| `phandalin_return` | `phandalin_arrived` and no major route clear yet |
| `mid_act1_return` | `old_owl_well_cleared` or `wyvern_tor_cleared` |
| `post_ashfall_return` | `ashfall_watch_cleared` |
| `late_act1_return` | `tresendar_cleared` or `emberhall_revealed` |
| `post_act1_return` | `varyn_body_defeated_act1` or `act1_victory_tier` |

One-shot flags can stay specific:

- `mira_q_neverwinter_initial`
- `mira_q_phandalin_initial`
- `mira_q_brand_initial`
- `mira_q_greywake_initial`
- `mira_q_elira_initial`
- `mira_q_blackwake_return`
- `mira_q_phandalin_return`
- `mira_q_route_sites_return`
- `mira_q_ashfall_return`
- `mira_q_cellars_return`
- `mira_q_act1_after_report`

## Initial Briefing Opening

Base opening:

> Mira has borrowed a counting room above the river warehouses, though nothing in it is being counted honestly anymore. Three maps are pinned over one another: Neverwinter roads, Phandalin supply lanes, and a crude copy of the old frontier ruins. Mira looks at the evidence before she looks at you.

Base Mira line:

> "Caravans bound for Phandalin have vanished, miners are being shaken down, and a new gang calling itself the Ashen Brand is using the frontier's old ruins for cover. That was the simple version before you walked in."

### Immediate Greywake Payoff

These fire before the question menu if their conditions are true. Multiple can fire.

If Elira joined before Mira:

> "You found Dawnmantle before I could send anyone for her. Good. That means the road is already worse than my reports."

If `greywake_manifest_preserved`:

> "This is not a forged report. This is a schedule."
>
> "A forged report lies about what happened. This tells someone what should happen next. That difference is why I am no longer treating the Ashen Brand as a gang with lucky timing."

If `greywake_manifest_destroyed`:

> "Then we work from witnesses. Less clean, but sometimes harder to kill."
>
> "Paper burns. Angry people remember who tried to decide their deaths in advance."

If `greywake_wounded_line_guarded` or `greywake_wounded_stabilized`:

> "People will talk because they lived long enough to be angry."
>
> "That matters. A frightened witness gives rumor. An angry survivor gives sequence."

If `greywake_sorting_publicly_exposed`:

> "You made clerks say the quiet part aloud. Good. A system can survive secret rot longer than public embarrassment."

If `greywake_outcome_tags_matched_wounds`:

> "Dawnmantle's notes and those tags agree. That is medical proof, not tavern fear."

## Initial Question Menu

Recommended visible options:

1. `"How is Neverwinter holding together these days?"`
2. `"Tell me what matters most about Phandalin before I ride."`
3. `"How dangerous is this Ashen Brand, really?"`
4. Conditional: `"What do you make of Greywake?"` if `greywake_outcome_sorting_seen`
5. Conditional: `"You know Elira Dawnmantle?"` if `elira_first_contact`
6. Conditional: `"Who inside the city benefits from this?"` if `neverwinter_private_room_intel` or `false_manifest_circuit` active/complete
7. `"What do you need from me before I leave?"`

## Question: Neverwinter

Player:

> "How is Neverwinter holding together these days?"

Base Mira:

> "Neverwinter is bruised, not broken. That is the line Lord Neverember prefers, and to be fair, it is not entirely a lie."
>
> "The city rebuilds faster than fear can settle. New stone goes up over old ash. Traders come back because profit has a stronger stomach than memory. But roads are how a city proves it is more than walls. If the road to Phandalin fails, every merchant in Neverwinter learns that the frontier can still reach north and take what it wants."

If `greywake_manifest_preserved`:

> "And now I have a schedule pretending to be a manifest. That makes this a city problem, not a frontier inconvenience."

If `blackwake_completed` and `blackwake_resolution == evidence`:

> "Blackwake proves the rot can stand within sight of Neverwinter's smoke and still call itself road business. I can move on that. Quietly, first. Loudly, if they make me."

If `blackwake_completed` and `blackwake_resolution == rescue`:

> "The rescued teamsters are already changing the story. A city can ignore missing cargo longer than it can ignore people walking home with names, scars, and witnesses."

If `blackwake_completed` and `blackwake_resolution == sabotage`:

> "A burned cache is less useful in court, but useful on the road. Sometimes stopping the next attack matters more than proving the last one."

Follow-up option:

> "Why not send soldiers?"

Mira:

> "Because soldiers make a road look occupied, not understood. If I send a column south, the Brand scatters, Phandalin panics, and the person shaping the route learns exactly which pressure made us flinch."
>
> "I need capable hands that can move faster than permission and report back before the official version hardens around the wrong lie."

## Question: Phandalin

Player:

> "Tell me what matters most about Phandalin before I ride."

Base Mira:

> "Phandalin is a town built by people who know ruins do not stay ruins if someone is stubborn enough. That makes them brave, practical, and terribly vulnerable to anyone who can make tomorrow's bread look less certain than today's fear."
>
> "The miners matter. The provisioners matter. The shrine matters more than it admits, because the wounded go there before they go to law. If the Ashen Brand can make those people distrust one another, Phandalin becomes easier to hold without ever being conquered."

If `steward_vow_made` on a later return:

> "Tessa Harrow will remember a vow. Be careful with that. Frontier towns live on promises, but they also keep score."

If `phandalin_arrived` and `steward_seen`:

> "Now you have seen Tessa's room. That town is not waiting for rescue. It is arguing over how much of itself it can spend to survive."

If `stonehill_instigator_unmasked`:

> "The paid mouth at Stonehill tells me the Brand is attacking the room before the road. That is cheaper than killing a caravan and usually cleaner."

If `stonehill_barfight_resolved` but not `stonehill_instigator_unmasked`:

> "A brawl in the Stonehill sounds small until you remember that panic is logistics too. A town that cannot share a room cannot hold a gate."

Follow-up option:

> "Who should I trust there?"

Mira:

> "Trust slowly. Tessa Harrow will try to hold the town together even if it costs her sleep and friends. Barthen will know what is missing before the law knows what was stolen. Linene Graywind will notice which weapons arrive late. Elira, if she is there, will tell you who is hurt before she tells you who is guilty."
>
> "And listen at the Stonehill. Inns lie constantly, but they lie in public. That makes the useful ones easier to catch."

## Question: Ashen Brand

Player:

> "How dangerous is this Ashen Brand, really?"

Base Mira:

> "Dangerous enough to stop calling them raiders."
>
> "Raiders take what is loose. The Ashen Brand is deciding what becomes loose. They pressure miners, bend caravan routes, poison witnesses, and use old ruins like a clerk uses shelves. Someone taught them that fear moves goods as well as horses do."

If `wayside_false_road_marks_found`:

> "Those false road marks you found near the shrine matter. The Brand is not only ambushing wagons. It is borrowing the shape of authority long enough to make honest people obey the wrong command."

If `greywake_outcome_sorting_seen`:

> "Greywake makes the danger uglier. Someone is not merely predicting losses. They are preparing the road to accept those losses as normal."

If `old_owl_notes_found` or `varyn_filter_logic_seen`:

> "Old Owl Well adds a filter to the pattern. They are not only choosing targets. They are sorting which kinds of fear travel best."

If `wyvern_beast_stampede` or `varyn_detour_logic_seen`:

> "Wyvern Tor shows the other hand: force the road to detour, then punish the detour until the detour feels inevitable."

If `cinderfall_relay_destroyed`:

> "Cinderfall was a relay, not a camp. That means messages, timing, and fallback orders. You did not just burn a nest. You cut a nerve."

Follow-up option:

> "Who is commanding them?"

Mira:

> "The field name I have is Rukhar Cinderfang, a hobgoblin with enough discipline to make cruelty useful. But Greywake, Blackwake, and the false manifests point above him."
>
> "Do not chase the grand name too early. Find the hand close enough to hurt people today. The larger hand will reach for what it loses."

If `varyn_route_pattern_seen`:

> "You have already seen the route pattern. Keep that in mind. Whoever commands this does not think in camps. They think in paths."

## Question: Greywake

Gate:

- `greywake_outcome_sorting_seen`

Player:

> "What do you make of Greywake?"

Base Mira:

> "Greywake is the moment the mask slipped."
>
> "A false manifest says somebody lied. An outcome manifest says somebody expected obedience from the future. Treat. Hold. Lost. Those are not clerical mistakes. Those are orders wearing ink."

If `greywake_manifest_preserved`:

> "With the manifest intact, I can push quietly at three offices before anyone knows which desk is shaking."

If `greywake_manifest_destroyed`:

> "With the manifest gone, I use witnesses. Messier, yes. But a witness can answer a question a page cannot: who looked relieved when the proof burned?"

If `greywake_wounded_line_guarded`:

> "Protecting the wounded line did more than save lives. It preserved memory under pressure."

If `greywake_yard_steadied`:

> "Steadying the yard gave me public witnesses. Public witnesses are dangerous to the guilty because they are harder to buy one at a time."

Follow-up option:

> "Does this connect to Phandalin?"

Mira:

> "Yes. Greywake was close to the city because the system is safest to test near the place that trusts paperwork most. Phandalin is where that system becomes hunger, missing tools, and frightened miners."

## Question: Elira Dawnmantle

Gate:

- `elira_first_contact`

Player:

> "You know Elira Dawnmantle?"

If Elira joined at Wayside or Greywake:

> "I know of her. Tymora's clergy tend to look harmless right up until they become the only reason a road still has witnesses."
>
> Elira: "Harmless is what people call you when they have never watched you choose who gets the last clean bandage. I prefer useful."
>
> "If Dawnmantle chose to walk with you, she saw the same thing I see: the wounded are not aftermath anymore. They are evidence someone keeps trying to erase."
>
> Elira: "The wounded are people first. If their pain becomes proof, it is because someone tried to bury them with it."

If `elira_initial_trust_reason == warm_trust`:

> "She trusts hands before speeches. You gave her hands."

If `elira_initial_trust_reason == spiritual_kinship`:

> "Faith that keeps people alive is useful. Faith that only decorates fear is not. Dawnmantle knows the difference."

If `elira_initial_trust_reason == wary_respect`:

> "Wary respect from a field healer is worth more than praise from a comfortable officer."

If `elira_initial_trust_reason == reserved_kindness`:

> "She is kind, but do not confuse that for easy trust. People who work triage learn the cost of every delay."

If Elira was not recruited and `elira_phandalin_fallback_pending`:

> "Then she will move with the wounded. If the road lets her reach Phandalin, find her at the shrine. If the road does not, remember that delay has a body count."

If Elira was recruited at Phandalin on a later return:

> "So she waited until the town itself became the patient. That sounds like Dawnmantle. Do not waste what it cost her to leave."

Follow-up option:

> "Can I trust her?"

Mira:

> Elira: "Trust me with breath, blood, and bad odds. Do not trust me to bless a lie because it would make the room easier to stand in."
>
> "With a life, yes. With an easy lie, no. That is usually the better arrangement."

## Question: City-Side Beneficiaries

Gate:

- `neverwinter_private_room_intel`
- or `false_manifest_circuit` active/completed
- or `neverwinter_contract_house_political_callback`

Player:

> "Who inside the city benefits from this?"

Base Mira:

> "Benefit is the wrong first question. Start with who can make the wrong paper look normal."
>
> "A wagon master can lose a crate. A corrupt clerk can lose a road. The Ashen Brand needs blades, yes, but blades do not explain why honest teamsters keep obeying bad instructions."

If `false_manifest_circuit` completed:

> "Oren's room, Sabra's manifest, Vessa's buyer phrase, and Garren's roadwarden cadence give me four corners of the same table. Now I can press without guessing where the legs are."

If `neverwinter_contract_house_blackwake_reported`:

> "Your Blackwake report gave those witnesses teeth. Before that, they were useful rumors. Now they are pressure."

Follow-up option:

> "Are you asking me to expose Neverwinter officials?"

Mira:

> "I am asking you to bring back facts so clean that the officials expose themselves trying to explain them away."

## Question: What Do You Need From Me?

Player:

> "What do you need from me before I leave?"

Base Mira:

> "Three things. Keep the writ visible when it protects civilians. Hide it when it would make you predictable. And do not mistake the loudest threat for the hand that profits from it."
>
> "When you reach Phandalin, listen before you promise. A town under pressure will ask for certainty it cannot afford. Give them useful truth instead."

If `greywake_manifest_preserved`:

> "Also: keep that schedule close. Anyone who recognizes it too quickly is more useful than they meant to be."

If `blackwake_completed`:

> "And if Blackwake follows you south, do not let people call it a side matter. It is the road showing you its teeth early."

If no early companion from Mira because Elira joined:

> "You already have Dawnmantle. I can still assign a scout or shield if you have room, but I will not pretend a roster matters more than the road's own choices."

## Return Hub: Blackwake Before Phandalin

Gate:

- `blackwake_completed`
- usually before `phandalin_arrived`

Opening:

> Mira listens without interrupting. That is worse than impatience. By the time you finish, she has moved two pins on the map and crossed out one tidy assumption.

If `blackwake_resolution == evidence`:

> "Copied seals, route marks, payment categories. Good. Ugly, but good."
>
> "Evidence lets me hurt the people who thought distance would protect them. Blackwake is close enough to Neverwinter that someone will have to explain why they never smelled the smoke."

If `blackwake_resolution == rescue`:

> "Survivors first was the right call if you wanted truth with a pulse."
>
> "The ledgers can be replaced. A teamster who saw the handoff can ruin three liars before breakfast."

If `blackwake_resolution == sabotage`:

> "You broke their rhythm. That buys lives even if it leaves me fewer names."
>
> "I can work with ashes, but ashes do not testify. Next time, if the choice allows it, bring me one living mouth from the other side."

If `blackwake_sereth_fate == escaped`:

> "Sereth Vane escaping means the road still has a clever coward in it. Clever cowards are dangerous because they learn."

If `neverwinter_private_room_intel`:

> "Oren and Sabra can make this hurt in the city. Vessa will charge us for honesty. Garren will pretend he is not relieved to finally be useful. I can use all of that."

Return choice:

> "Go south. Phandalin needs the next answer before Neverwinter finishes arguing over the first."

## Return Hub: After Reaching Phandalin

Gate:

- `phandalin_arrived`

Opening:

> Mira's room has changed while you were south. The old Neverwinter map is still there, but Phandalin now sits under three pins, two witness strings, and a charcoal note that says: town pressure is not collateral.

Player option:

> "Phandalin is worse than your reports."

If `steward_seen`:

> "Tessa Harrow usually sounds tired in writing. If she looked tired in person, assume the town is closer to breaking than she wants Neverwinter to know."

If `steward_vow_made`:

> "You made her a vow. Good. Now make it useful. Vows do not feed towns or open roads unless someone turns them into work."

If `blackwake_resolution == rescue`:

> "Rescued teamsters reaching Phandalin changes the town's posture. People fear less stupidly when they know survival has precedent."

If `blackwake_resolution == evidence`:

> "The Blackwake ledgers will make the merchants angrier than the bodies did. I do not admire that, but I can use it."

If `blackwake_resolution == sabotage`:

> "The sabotage bought time. Time is only mercy if you spend it before the enemy does."

Follow-up option:

> "What can Neverwinter actually send?"

Mira:

> "Not enough. A few writs, a little coin, pressure on the legal offices, and names whispered into the right ears. If I send soldiers now, Neverwinter gets to feel helpful while Phandalin becomes a symbol."
>
> "I would rather it remains a town."

## Return Hub: After Old Owl Well Or Wyvern Tor

Gate:

- `old_owl_well_cleared` or `wyvern_tor_cleared`

Player option:

> "The outer sites are not random."

If only `old_owl_well_cleared`:

> "Old Owl Well first. Then the Brand is willing to mix old dead things with new logistics. That is either desperation or doctrine. I dislike both."

If only `wyvern_tor_cleared`:

> "Wyvern Tor first. Hill pressure, beast panic, and forced detours. That is a road commander's language."

If both cleared:

> "Old Owl Well and Wyvern Tor are two jaws of the same trap. One teaches fear to linger. The other teaches traffic to move where the Brand wants it."

If `old_owl_notes_found`:

> "Those notes matter. They read people as categories, not enemies. That matches Greywake too closely for comfort."

If `wyvern_beast_stampede`:

> "A stampede is useful because nobody asks who ordered an animal to panic. Remember that."

If `hidden_route_unlocked` or `cinderfall_ruins_cleared`:

> "Cinderfall was the missing hinge. Routes do not bend by themselves. Something was relaying the pressure."

Follow-up option:

> "Should I keep clearing sites or go straight for the watch?"

Mira:

> "If Phandalin can breathe, cut the relay and the watch becomes less certain. If Phandalin is bleeding now, hit the watch before careful work becomes an elegant excuse."

## Return Hub: After Ashfall Watch

Gate:

- `ashfall_watch_cleared`

Player option:

> "Ashfall Watch is broken."

Mira:

> "Then the Brand has lost its field spine."
>
> "Do not celebrate too long. A broken spine can still leave teeth behind, and whoever built this operation will start deciding what to abandon."

If prisoners were protected or survivors saved flags are high:

> "Prisoners who walk home carry better maps than anything you can draw. Let them talk before fear edits them."

If `cinderfall_relay_destroyed`:

> "With Cinderfall cut and Ashfall broken, their timing should start to fray. Watch for the mistake they make when orders arrive late."

If `elira_faith_under_ash_resolved` or equivalent future flag:

> "Dawnmantle's mercy will complicate your report. Good. Clean reports usually mean someone left people out."

Follow-up option:

> "What changes now?"

Mira:

> "Now they stop pretending the road is the battlefield. They will pull inward, toward the places under Phandalin where fear has walls."

## Return Hub: After Tresendar Manor

Gate:

- `tresendar_cleared` or `emberhall_revealed`

Player option:

> "The manor is not just a ruin."

Mira:

> "No. It is a mouth."
>
> "Old stone gives criminals privacy. Older stone gives worse things patience. If the Brand used Tresendar as more than shelter, then Phandalin has been standing over part of the answer since the beginning."

If `tresendar_nothic_route == kill`:

> "You killed the thing in the dark. That is sometimes the only clean sentence a report gets."

If `tresendar_nothic_route == trade`:

> "You traded with it. I will not scold you until I know whether the price follows you home."

If `tresendar_nothic_route == deceive`:

> "You lied to a thing built to eat truths. Brave, foolish, or useful. I will decide after you survive the consequences."

If `tresendar_nothic_wave_echo_lore`:

> "Wave Echo again. That name keeps appearing where ordinary banditry should have run out of imagination."

Follow-up option:

> "Should Neverwinter intervene now?"

Mira:

> "Officially? No. Unofficially? You are already the intervention."

## Return Hub: After Emberhall And Varyn

Gate:

- `varyn_body_defeated_act1`
- or `act1_victory_tier`

Player option:

> "Varyn is beaten."

If `varyn_route_displaced`:

> "Beaten, yes. Finished, I am less sure."
>
> "Bodies are usually persuasive. Routes that fold wrong are not usually interested in persuasion."

If `act1_victory_tier == clean_victory`:

> "Phandalin will get to call this a victory without choking on the word. That is rare. Let them have it."

If `act1_victory_tier == costly_victory`:

> "The road is open, but nobody south of here will mistake open for healed. Costly victories still count. They also send invoices."

If `act1_victory_tier == fractured_victory`:

> "You won. I believe that. I also believe Phandalin will spend months learning what the word cost."

If `emberhall_impossible_exit_seen`:

> "Tell me again about the exit that should not have worked. Slowly. That may be the first honest sentence in this whole affair."

Follow-up option:

> "What does Neverwinter do with this?"

Mira:

> "Publicly, we praise brave locals, condemn organized banditry, and send repair money late enough to insult everyone."
>
> "Privately, I start tracking every route that behaved like it had a memory. The next enemy may not call itself the Ashen Brand. It may not need to."

## Implementation Notes

- Keep initial briefing questions available before departure, but let return stages use a separate set of flags so the same topics can be revisited after the player has new facts.
- Avoid locking the player into a long report. Each return hub should offer 2-4 high-signal questions plus a leave option.
- Let Mira's reactions be additive when the player earned multiple flags. Example: on a later return she can acknowledge Elira, Greywake proof, Blackwake evidence, and Phandalin witness pressure in sequence.
- Mira should not reveal Malzurath. Her language should stay in the realm of routes, schedules, pressure, memory, and systems until Act 3/4 planning wants a stronger leak.
- If a return to Neverwinter is not yet implemented as a map option, this draft can still be used by Blackwake's existing Neverwinter report branch and any future `Backtrack to Neverwinter` hub.
