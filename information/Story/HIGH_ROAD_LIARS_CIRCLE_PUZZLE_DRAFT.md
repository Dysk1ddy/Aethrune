# High Road Puzzle Draft: The Liars' Circle

This draft describes the now-implemented optional wilderness puzzle branch after the High Road ambush and before Phandalin arrival.

## Implementation Status

- Implemented scene id: `high_road_liars_circle`
- The branch unlocks after both High Road ambush waves are cleared.
- The cleared High Road scene now reopens as a travel menu before Phandalin, offering the south road, `BACKTRACK` when available, and unlocked side branches.
- The Liar's Circle inspection and answer options use plain action/quoted labels instead of redundant skill tags.
- Returning from the branch travels to `phandalin_hub` without recording the side branch as the next backtrack node, so later Phandalin backtracking points back to the meaningful High Road route.

## Placement

- Act: Act 1
- Region: High Road wilderness
- Intended insertion point: after `road_ambush` resolves, before the party reaches `phandalin_hub`
- Branch type: optional roadside detour
- Tone: eerie, fey-adjacent logic puzzle with a social-skill reward
- Combat: none by default
- Retry policy: one answer only

Suggested scene id:

```text
high_road_liars_circle
```

Suggested flags:

```text
liars_circle_seen
liars_circle_solved
liars_circle_failed
liars_circle_locked
liars_blessing_active
liars_curse_active
```

## Branch Entry

After the ambush, the party finds a side path cutting away from the churned road. It should feel optional, but tempting. In the current implementation, the branch is offered from the cleared High Road travel menu after the second wave is beaten.

Suggested choice:

```text
The High Road bends south under leaning pines. Past the ambush site, a deer trail slips west through the brush, marked by four old standing stones half-hidden under moss.

1. Follow the High Road to Phandalin.
2. Backtrack to the previous route node, if history allows it.
3. Follow the overgrown statue trail into the wilderness.
4. Investigate the broken roadwarden milemarker, if available.
5. Challenge the false roadwarden checkpoint, if available.
```

If the player ignores the branch, continue to Phandalin normally. The branch remains available from the cleared High Road menu until resolved or locked.

## Scene Setup

Read when entering the circle:

```text
The deer trail ends in a ring of pale stones. Four statues stand inside it, each weathered but distinct: a Knight with a cracked shield, a Priest with folded hands, a Thief with one finger raised to silent lips, and a King with a crown worn nearly smooth by rain.

No birds call from the trees around the clearing. Even the road sounds far away.

At the center of the circle, a flat black plaque waits beneath a skin of moss.
```

Plaque text:

```text
Exactly one of us speaks the truth.
The others always lie.
```

## Inspection Flow

The player should be able to inspect all four statues before answering. The scene should not force an answer until the player chooses to name the truthful statue.

Suggested options:

```text
1. Inspect the Knight.
2. Inspect the Priest.
3. Inspect the Thief.
4. Inspect the King.
5. Name the statue that tells the truth.
6. Leave the circle.
```

Leaving before answering should be allowed. If the puzzle has not been answered, the player can step away without reward or penalty.

## Statue Lines

Each statue speaks once per inspection, but repeated inspections can replay the line.

Knight:

```text
The Knight's stone visor tilts down. "If the Priest is lying, then the King is telling the truth."
```

Priest:

```text
The Priest's folded hands grind softly together. "Exactly one of the Knight or the King is telling the truth."
```

Thief:

```text
The Thief smiles with a mouth that was never carved open. "Exactly one of the Priest or I is telling the truth."
```

King:

```text
The King's rain-worn crown turns toward you. "The Priest is lying if and only if I am telling the truth."
```

## Answer Prompt

When the player chooses to answer:

```text
The four statues wait without breathing. Which one speaks the truth?

1. Knight
2. Priest
3. Thief
4. King
5. Say nothing yet.
```

Correct answer:

```text
Thief
```

## Solution Proof

Let the truth values of the statues' statements be:

```text
K = Knight is telling the truth
P = Priest is telling the truth
T = Thief is telling the truth
G = King is telling the truth
```

The plaque says exactly one of `K`, `P`, `T`, and `G` is true.

The statements translate as:

```text
Knight: If P is false, then G is true.
        K = P or G

Priest: Exactly one of K or G is true.
        P = K xor G

Thief: Exactly one of P or T is true.
        T = P xor T

King: P is false if and only if G is true.
      G = (not P) iff G
```

The Thief's self-referential statement forces `P` to be false. If `P` were true, the Thief's statement would contradict itself. With `P` false, the Knight and King statements collapse into the same truth value.

If the King were true, then the Knight would also be true, giving at least two truth-tellers. That violates the plaque.

So the King is false, the Knight is false, and the Priest is false. The only remaining truth-teller is the Thief.

Final truth table:

| Statue | Truth value |
| --- | --- |
| Knight | False |
| Priest | False |
| Thief | True |
| King | False |

## Success Outcome

When the player names the Thief:

```text
The Thief's stone smile deepens.

"A clean lie is only half the art," it says. "The better half is knowing when truth will be mistaken for one."

The circle exhales. Moss slides from the plaque in a soft black sheet, and for one heartbeat every shadow points toward you like an audience waiting for the next line.
```

Reward:

```text
Liar's Blessing
+2 Deception
+1 Persuasion
Permanent until death
Applies to the player only
200 XP
```

Suggested reward message:

```text
Liar's Blessing settles behind your tongue. Deception +2 and Persuasion +1 until death.
```

Suggested journal line:

```text
At a roadside circle of lying statues, you named the Thief as the only truth-teller and earned Liar's Blessing.
```

Suggested flags:

```text
liars_circle_seen = True
liars_circle_solved = True
liars_blessing_active = True
```

## Failure Outcome

When the player names any statue except the Thief:

```text
The named statue cracks from brow to base.

For a moment, all four voices speak together.

"A poor lie. A poorer truth."

The circle locks into silence. The plaque sinks into the earth, taking the answer with it, and the path behind you looks suddenly shorter than it should.
```

Penalty:

```text
Liar's Curse
-1 Deception
-1 Persuasion
Lasts until the next long rest
Applies to the player only
Puzzle locks permanently
```

Suggested curse message:

```text
Liar's Curse catches in your throat. Deception -1 and Persuasion -1 until your next long rest.
```

Suggested journal line:

```text
At a roadside circle of lying statues, you named the wrong truth-teller. The circle locked, and Liar's Curse followed you back to the road.
```

Suggested flags:

```text
liars_circle_seen = True
liars_circle_failed = True
liars_circle_locked = True
liars_curse_active = True
```

## Companion Flavor

Use these as optional one-line interjections if the relevant companion is present.

Tolan Ironshield:

```text
"I dislike puzzles that wait in ambush formation," Tolan mutters. "But at least these ones are polite enough to stand still."
```

Kaelis Starling:

```text
Kaelis studies the brush around the stones. "No tracks inside the circle. Animals know better than we do, apparently."
```

Rhogar Valeguard:

```text
Rhogar's claws flex once around his weapon haft. "Truth should not need a trap to defend it."
```

Bryn Underbough:

```text
Bryn squints at the Thief. "I hate when a statue has better timing than half the living criminals I used to know."
```

Elira Dawnmantle:

```text
Elira touches the edge of the plaque without quite pressing down. "A blessing from a liar is still a bargain. Be careful what part of you signs."
```

## Implementation Notes

The current condition system can track persistent named conditions, but conditions do not currently modify skill bonuses. Deception and Persuasion are calculated through `Character.skill_bonus()`, which reads:

```text
equipment_bonuses
gear_bonuses
relationship_bonuses
```

Recommended implementation:

- Add a small story-bonus helper instead of overloading combat statuses.
- Store the blessing and curse on player-specific state, probably in `player.bond_flags` or a new explicit story modifier map.
- Have `Character.skill_bonus()` read those story modifiers.
- For the first implementation, using `player.equipment_bonuses` is workable, but the name is semantically loose.

Recommended first-pass hooks:

```text
player.equipment_bonuses["Deception"] += 2
player.equipment_bonuses["Persuasion"] += 1
state.flags["liars_blessing_active"] = True
```

For the curse:

```text
player.equipment_bonuses["Deception"] -= 1
player.equipment_bonuses["Persuasion"] -= 1
state.flags["liars_curse_active"] = True
```

Then clear the curse during long-rest recovery:

```text
if state.flags.get("liars_curse_active"):
    player.equipment_bonuses["Deception"] += 1
    player.equipment_bonuses["Persuasion"] += 1
    state.flags["liars_curse_active"] = False
```

For the blessing's "until death" rule, remove the bonus when the player dies, not merely when the player is downed at 0 HP. If resurrection is possible after true death, the blessing should remain gone.

Suggested helper names:

```text
apply_liars_blessing()
apply_liars_curse()
clear_liars_curse()
clear_liars_blessing_on_death()
```

## Balance Notes

- The reward is strong but narrow. It makes social builds better without raising combat math.
- The curse is meaningful but temporary, which keeps the one-answer lock from feeling cruel.
- Because the branch appears before Phandalin, the blessing can immediately matter in town scenes, Bryn recruitment, and later Blackwake/Act 1 social checks.
- The current implementation awards `200 XP` for solving the puzzle. If that proves too generous in playtests, tune the XP first and keep the social buff as the branch's identity reward.

## Test Checklist

Add tests when implementing:

- The branch appears after the High Road ambush when the player chooses the wilderness detour.
- The cleared High Road scene offers the side branch before auto-entering Phandalin.
- The side-branch option is not prefixed with a redundant `[PUZZLE]` tag.
- Inspecting each statue prints the correct line.
- Choosing Thief sets `liars_circle_solved` and applies Deception +2 / Persuasion +1 to the player.
- Choosing Knight, Priest, or King sets `liars_circle_failed`, locks the puzzle, and applies Deception -1 / Persuasion -1.
- A long rest clears the curse and restores the lost skill bonuses.
- A long rest does not clear the blessing.
- Player death removes the blessing.
- Leaving before answering applies no blessing, no curse, and no lock.
- The puzzle cannot be solved after it locks.
- Returning from the branch preserves the High Road as the next meaningful backtrack target instead of preserving `liars_circle`.
