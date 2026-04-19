# Act 1 Pre-Neverwinter And Elira First Companion Draft

This draft adds one or two shared Act 1 locations between the background prologue and Mira Thann's Neverwinter briefing.

Primary goal:

- Let the player meet Elira Dawnmantle as the first companion candidate before the second major combat.
- Give Elira two early recruitment chances before that second combat.
- If both early chances fail or the player declines, Elira still appears later at Phandalin's Shrine of Tymora and can be recruited there anyway.

Interpretation note:

- The current live flow starts with a background-specific prologue and then moves to `neverwinter_briefing`.
- This draft inserts a shared road-and-shrine sequence before the party fully reaches Mira's briefing in Neverwinter.
- If implementation later decides the phrase "before reaching Neverwinter" should instead mean "before reaching Phandalin after leaving Neverwinter," the same locations can be flipped south of the city with minimal story changes.

## Desired Opening Flow

Current:

1. Background-specific prologue.
2. Neverwinter briefing.
3. Optional Neverwinter prep and companion choice.
4. Road content.
5. Phandalin.

Drafted:

1. Background-specific prologue.
2. `Wayside Luck Shrine` - first Elira contact and first recruitment chance.
3. `Greywake Triage Yard` - second Elira contact and second recruitment chance.
4. Second major combat: `Greywake Road Breakout`.
5. Neverwinter briefing with Mira Thann.
6. Existing road south and Phandalin content.
7. If Elira is still not recruited, she appears at Phandalin's Shrine of Tymora.

## Location 1: Wayside Luck Shrine

Scene id target:

- `wayside_luck_shrine`

Story position:

- Immediately after the background prologue.
- Before the player reaches the Neverwinter briefing.
- Before the second combat.

Scene function:

- Introduce Elira as the first companion candidate.
- Establish the campaign's mercy theme before the logistics/politics of Neverwinter.
- Give the player a non-combat way to affect the next road fight.
- Set up the Ashen Brand as a threat to ordinary travelers, not only caravans and guards.

Core image:

- A roadside Tymoran shrine under a rain-dark oak.
- A cracked luck bell tied with green thread.
- Two injured drovers, one poisoned pilgrim, and Elira working alone with a field kit that is almost empty.
- The road to Neverwinter is close enough to hear city bells, but the wounded have not made it there.

Opening text target:

> The first bells of Neverwinter are still only a rumor when you find the shrine: a lucky-road marker under a black oak, its ribbons stiff with rain. A young priestess has turned the altar into a triage board. She looks up once, sees whether your hands are steady, and goes back to keeping a dying drover in the world.

Elira intro:

> "If you are here to pray, kneel. If you are here to help, wash your hands first."

### Elira First Read

Elira's first line adapts to the player's background or class before the shrine choice:

| Player hook | Elira read |
| --- | --- |
| `Acolyte`, `Cleric`, or `Paladin` | Tests whether faith becomes action instead of only words. |
| `Soldier` or `Fighter` | Clocks battlefield triage competence and expects fast, steady choices. |
| `Criminal`, `Rogue`, or `Charlatan` | Notices whether the player helps when no one important is watching. |
| `Sage` or `Wizard` | Warns that knowing the poison is not the same as saving the victim. |

Memorable object:

- A cracked luck bell tied with green road-ribbons hangs over the altar.
- If Elira is recruited here, she ties the cracked bell once before leaving: not as a prayer, but as a promise that someone will come back to repair it.
- The green road-ribbon recurs later at Phandalin's Shrine of Tymora.

### Choices

The player chooses one primary aid route:

| Choice | Skill | Success | Failure |
| --- | --- | --- | --- |
| Stabilize the poisoned drover. | `Medicine` DC 8 | Set `elira_helped`, add clue about ash-bitter poison, +1 Elira trust if recruited later. | The drover lives because Elira catches the mistake, but no trust bonus. |
| Lead the road prayer so Elira can keep working. | `Religion` DC 8 | Set `elira_helped`, gain `Blessed` for the next combat or `blessed_salve`. | The prayer steadies bystanders, but the fear remains noisy. |
| Inspect harness marks and false authority signs. | `Investigation` DC 8 | Set `elira_helped`, add clue tying the wounded to false roadwarden pressure. | The player sees the violence, but not the pattern. |

Trust distinction:

- Helped the wounded: `warm_trust`.
- Prayed with/for the shrine: `spiritual_kinship`.
- Found the road marks: `wary_respect`.
- Skipped direct help: `reserved_kindness` - Elira remains kind, but less immediately open.

Suggested rewards:

- `10 XP` for meaningful aid.
- `blessed_salve` or `potion_healing` if the player helps or if solo/small party needs support.
- Hidden flags include `elira_first_contact = True`, `wayside_luck_bell_seen = True`, and route/trust markers for Elira's initial read.

### First Recruitment Chance

Trigger:

- After the aid choice.

Prompt:

> Elira wipes her hands clean and looks toward the city road, then back to the wounded who will not reach it without someone standing between them and the next knife.

Options:

1. `[PERSUASION] "Come with me. The next wound will be on the road, not at this shrine."`
2. `"Stay with them. I will carry your warning to Neverwinter."`
3. `"I am not asking for faith. I am asking for steady hands."` if the player succeeded at the aid check.

Recruitment logic:

- If `elira_helped == True`, recruitment can either skip the check or use a very low DC.
- Otherwise use `Persuasion` DC 8.
- On success:
  - recruit Elira immediately.
  - set `elira_pre_neverwinter_recruited = True`.
  - set `elira_first_companion = True`.
  - set `wayside_luck_bell_promised = True`.
- On decline or failure:
  - set `elira_wayside_recruit_attempted = True`.
  - Elira says she will move the wounded toward the city and asks the player to keep the road alive.

Failure line target:

> "Not yet. I will not leave people bleeding because the road might need me more loudly. Earn the road's trust, and ask again before you ride south."

## Location 2: Greywake Triage Yard

Scene id target:

- `greywake_triage_yard`

Story position:

- After `wayside_luck_shrine`.
- Before the second major combat.
- Just outside one of Neverwinter's outer relief yards, where caravans are being sorted before city entry.

Scene function:

- Give the second Elira recruitment chance.
- Show the first clear hint that the enemy is not only hurting people, but pre-sorting outcomes before victims arrive.
- Introduce the second combat before the formal briefing.
- Let Elira matter whether or not she has joined yet.
- Give Mira concrete evidence to react to in the Neverwinter briefing.

Core image:

- A muddy relief yard outside the city wall.
- Wagons waiting under quarantine ropes.
- An intake board sorting wagons into `TREAT`, `HOLD`, and `LOST` before anyone crosses the gate.
- A city clerk refusing entry because the papers list injuries and outcomes before they happened.
- Elira arrives with shrine wounded if she was not recruited.

Opening text target:

> Greywake Yard is where Neverwinter pretends the road can be made orderly before it enters the city. Today the ropes sag, the clerks are pale, and one intake board has already sorted wagons into treat, hold, and lost before anyone has crossed the gate. One manifest lists three wounded travelers by name before the wagons carrying them arrive.

### Choices

The player chooses how to stabilize the yard:

| Choice | Skill | Success | Failure |
| --- | --- | --- | --- |
| Challenge the outcome-marked manifest. | `Insight` DC 9 | Set `greywake_outcome_manifest_read`, `greywake_mira_evidence_kind = marked_manifest`, `system_profile_seeded`, and `varyn_route_pattern_seen`; learn the paperwork sorts losses before they happen. | The clerk panics and the yard stays volatile, but the outcome board remains suspicious. |
| Match prewritten triage tags against the wounded with Elira. | `Medicine` DC 9 | Set `greywake_wounded_stabilized`, `greywake_outcome_tags_matched_wounds`, and `greywake_mira_evidence_kind = matched_triage_tags`; lower second-combat pressure. | Elira prevents deaths, but the line never fully becomes calm. |
| Make the clerks read the outcome marks aloud. | `Persuasion` DC 9 | Set `greywake_yard_steadied`, `greywake_sorting_publicly_exposed`, and `greywake_mira_evidence_kind = yard_witnesses`; gain hero initiative bonus for the combat. | The crowd obeys for a moment, then the attack interrupts. |

### Second Recruitment Chance

Trigger:

- Before the second combat begins.
- Only if Elira has not joined yet.

Prompt:

> Elira sees the yard beginning to break and closes her field kit with one hand. "This is not a ledger mistake. If I stay, I treat what someone already decided. If I walk with you, maybe we reach the hand moving the marks."

Options:

1. `[PERSUASION] "Then walk with me now. We stop the wound before it reaches the shrine."`
2. `"Stay. If the road brings me back alive, I will find you again."`
3. `[ELIRA HELPED] "You already know my hands. Trust them with the road."`

Recruitment logic:

- If `elira_helped == True`, automatic success or Persuasion DC 6.
- If `greywake_wounded_stabilized == True`, Persuasion DC 6.
- Otherwise Persuasion DC 8.
- On success:
  - recruit Elira.
  - set `elira_greywake_recruited = True`.
  - set `elira_first_companion = True`.
- On failure or decline:
  - set `elira_greywake_recruit_attempted = True`.
  - set `elira_phandalin_fallback_pending = True`.
  - Elira remains with the wounded and later travels to Phandalin's shrine.

Failure/decline line target:

> "Then I will keep this line breathing and follow the wounded south. If Tymora is kind, you will find me in Phandalin before the next prayer turns into triage."

## Combat: Greywake Road Breakout

Scene id target:

- `greywake_road_breakout`

Story position:

- Second major combat after the background prologue.
- Happens before Mira's formal Neverwinter briefing.

Scene function:

- Pay off Elira's early recruitment.
- Show the Ashen Brand testing city-edge systems before the player receives the official job.
- Seed Varyn/Malzurath route-pattern telemetry without naming any secret villain.

Enemy concept:

- Ashen Brand cutters hit the triage yard to steal or destroy the impossible manifest.
- They are not trying to win a battle; they are trying to erase proof, preserve the pre-sorted outcome line, and test who responds.

Suggested enemy list:

- Small party:
  - `bandit`
  - `bandit_archer`
- Full party or harder route:
  - `bandit`
  - `bandit_archer`
  - `goblin_skirmisher` or `ash_brand_enforcer`

Opening options:

| Choice | Skill | Effect |
| --- | --- | --- |
| Guard the wounded line first. | `Medicine` or `Athletics` | Protects civilians, Elira approval, may reduce enemy pressure. |
| Seize the manifest runner. | `Investigation` or `Stealth` | Preserves predictive-paper clue and route telemetry. |
| Break the attackers' nerve loudly. | `Intimidation` | Faster combat opener, more public fear if failed. |

Elira involvement:

- If recruited:
  - She grants a pre-combat `Blessed` or small healing effect.
  - She reacts to protecting wounded vs chasing documents.
- If not recruited:
  - She appears as scene support, keeping the wounded alive but not joining combat.
  - On victory, she leaves for Phandalin if not recruited.

Victory outcomes:

- Set `greywake_breakout_resolved`.
- Set `system_profile_seeded` if the manifest clue is preserved or read.
- Set `varyn_route_pattern_seen` if the player identifies the attack as proof-erasure / route authority manipulation.
- Carry a concrete Greywake evidence kind into Mira's briefing:
  - `marked_manifest`
  - `matched_triage_tags`
  - `yard_witnesses`
  - `burned_manifest_corner` on flee / weaker proof.
- Add clue:
  - "The Greywake manifest pre-sorted travelers by expected wound, delay, and loss before their wagons arrived."
- Proceed to `neverwinter_briefing`.

Mira reaction target:

Mira should react to what actually happened at Greywake:

- If Elira joined early:
  - "You found Dawnmantle before I could send anyone for her. Good. That means the road is already worse than my reports."
- If the outcome-marked manifest was preserved:
  - "This is not a forged report. This is a schedule."
- If the manifest burned:
  - "Then we work from witnesses. Less clean, but sometimes harder to kill."
- If the wounded were protected:
  - "People will talk because they lived long enough to be angry."

Defeat/flee outcomes:

- The manifest is destroyed.
- Elira still survives, unless later design wants her fallback to be delayed rather than removed.
- The player reaches Neverwinter with weaker proof and higher road pressure.

## Phandalin Fallback: Shrine Of Tymora

Existing scene:

- `visit_shrine()` in `story_town_services.py`.

Drafted fallback behavior:

- If Elira was not recruited before Neverwinter or Greywake, she appears in Phandalin's shrine.
- She should be recruitable there even if both early attempts failed.
- The Phandalin version should preserve the current "help first, recruit easier" shape.

Suggested fallback states:

| Prior state | Phandalin shrine behavior |
| --- | --- |
| No early contact | Current shrine intro mostly unchanged. |
| Helped at Wayside, declined later | Elira recognizes the player warmly; recruitment can skip check. |
| Failed both recruitment asks but helped wounded | Elira says the road kept testing both of them; Persuasion DC 6 or automatic if `elira_helped`. |
| Ignored wounded / chased proof only | Elira is recruitable, but starts at lower trust or requires Persuasion DC 8. |
| Greywake manifest destroyed | Elira brings wounded testimony instead of paperwork proof. |

Important rule:

- Do not permanently lock Elira out because of early recruitment failure.
- Early failure should change tone/trust, not remove the companion.

## Elira As First Companion

Design target:

- Elira is the first companion candidate the player can meet.
- Kaelis and Rhogar can remain Neverwinter briefing choices, but Elira should be encountered before that formal choice.
- If Elira is recruited early, the briefing should acknowledge the player already has a healer on the road.

Recommended companion ordering:

1. Elira: first possible companion, met before second combat.
2. Kaelis or Rhogar: optional Mira briefing assignment if party space allows.
3. Tolan: road-combat survivor / later Stonehill pickup.
4. Bryn: Stonehill Inn.

Party-size consideration:

- If Elira joins before the briefing, the game should either:
  - still allow one Mira companion if under party cap, or
  - offer Kaelis/Rhogar as camp-bound contacts if the active party is already full later.

## Reactivity And Flags

New flags:

| Flag | Purpose |
| --- | --- |
| `wayside_luck_shrine_seen` | Shared pre-Neverwinter Elira scene visited. |
| `elira_first_contact` | Player met Elira before the briefing. |
| `elira_wayside_recruit_attempted` | First recruitment chance used. |
| `elira_pre_neverwinter_recruited` | Elira joined at the Wayside shrine. |
| `greywake_triage_yard_seen` | Second shared pre-Neverwinter location visited. |
| `greywake_wounded_stabilized` | Player helped the wounded line at Greywake. |
| `greywake_yard_steadied` | Player stabilized the crowd / civic line. |
| `elira_greywake_recruit_attempted` | Second recruitment chance used. |
| `elira_greywake_recruited` | Elira joined at Greywake. |
| `elira_first_companion` | Elira was the first companion recruited in the campaign. |
| `elira_phandalin_fallback_pending` | Elira should appear at Phandalin shrine if unrecruited. |
| `greywake_breakout_resolved` | Second combat resolved. |
| `greywake_manifest_preserved` | Player preserved the impossible manifest. |

Existing flags to reuse:

- `elira_helped`
- `shrine_recruit_attempted`
- `early_companion_recruited`
- `system_profile_seeded`
- `varyn_route_pattern_seen`

## Implementation Notes

Likely files:

- `dnd_game/gameplay/story_intro.py`
  - Add scenes:
    - `scene_wayside_luck_shrine`
    - `scene_greywake_triage_yard`
    - `scene_greywake_road_breakout`
  - Change `finish_background_prologue()` to route to `wayside_luck_shrine` instead of `neverwinter_briefing`.
  - Have `greywake_road_breakout` route to `neverwinter_briefing`.

- `dnd_game/gameplay/base.py`
  - Register the new scene handlers.
  - Add scene labels/objectives.

- `dnd_game/gameplay/story_town_services.py`
  - Update Phandalin shrine fallback text and recruitment logic.
  - Ensure failed early recruitment does not block recruitment in Phandalin.

- `information/Story/ACT1_CONTENT_REFERENCE.md`
  - Update opening route and companion reference once implemented.

- `tests/test_core.py`
  - Add focused tests for new scene ordering, Elira recruitment chances, fallback, and no-lockout behavior.

## Suggested Implementation Slices

### Slice 1: Draft-Only And Reference Updates

- Add this plan.
- Update Act 1 reference summary once approved.

### Slice 2: Scene Routing And Wayside Shrine

- Add `wayside_luck_shrine`.
- Route background prologues into it.
- Add first Elira recruitment chance.
- Test recruitment success, failure, and decline.

### Slice 3: Greywake Yard And Second Recruitment Chance

- Add `greywake_triage_yard`.
- Add second Elira recruitment chance.
- Test easier recruitment if `elira_helped` or `greywake_wounded_stabilized`.

### Slice 4: Greywake Road Breakout

- Add second major combat.
- Add manifest / route-pattern flags.
- Route to Neverwinter briefing afterward.
- Test with Elira recruited and unrecruited.

### Slice 5: Phandalin Fallback Polish

- Update `visit_shrine`.
- Ensure Elira can still be recruited after two failed early asks.
- Add tests for fallback states.

## Open Decisions

- Should the new locations happen before the player enters Neverwinter proper, or immediately after Mira's briefing but before the High Road?
  - Recommendation: before the briefing if the goal is to make Elira the first companion.
- Should Elira join automatically if the player succeeds at the first aid check?
  - Recommendation: no. Let the player ask, but make success automatic or nearly automatic after help.
- Should early Elira recruitment remove the Kaelis/Rhogar briefing choice?
  - Recommendation: no. Keep the choice, but respect active party limits.
- Should Greywake count as the campaign's second combat for all backgrounds?
  - Recommendation: yes. Some background prologues are combat-light, but Greywake can still be the first shared combat pressure beat.
- Should failing both early recruitment asks lower Elira trust?
  - Recommendation: only if the player behaved callously. Simple failed persuasion should not punish the relationship.
