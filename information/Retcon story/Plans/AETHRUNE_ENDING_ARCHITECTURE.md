# Aethrune Ending Architecture

This document defines the late-game resolution lanes for Aethrune.

It assumes the current story scaffold:

- Act 2 ends at the `Meridian Forge`
- Caldra Voss is the visible Act 2 final antagonist
- the Forge is a lens that focuses deeper system logic
- Act 3 reveals `Malzurath, Keeper of the Ninth Ledger`
- the `Abyss` represents unresolved failure and incomplete reality

Primary support docs:

- `AETHRUNE_TRUTH_AND_BELIEF_MATRIX.md`
- `AETHRUNE_COMPANION_IDEOLOGY_MATRIX.md`
- `AETHRUNE_STORYBUILDING_PHASES_DRAFT.md`
- `aethrune_gameplay_variables_tuning_v1.md`
- `aethrune_quest_to_variable_matrix_v1.md`
- `dnd_game/gameplay/story_act3_scaffold.py`

## Final Conflict Statement

The end of Aethrune centers on deciding what the world should do with systems
that can:

- record choice
- predict behavior
- authorize passage
- rewrite practical reality
- and continue operating after the moral framework that built them is gone

The final question is:

Should reality be stabilized through stronger system rule, through constrained
stewardship, through distributed human refusal, or through costly containment of
what can no longer be safely resolved?

## Endgame Truths To Preserve

These should be stable across all ending routes:

- Malzurath embodies the logic of recorded outcome taken too far.
- The Meridian Forge is a lens and shaping instrument that channels deeper
  powers.
- The Abyss is what remains when systems fail to finish reality cleanly.
- No ending should feel cost-free.
- The best endings should land as coherent moral resolutions with clear
  tradeoffs, never as perfect victories.

## Core Endgame Variables

Use these as the main ending architecture inputs.

| Variable | Narrative meaning |
| --- | --- |
| `system_alignment` | whether the player trusts ordered structures over human irregularity |
| `player_predictability` | how easy the player became to model and counter |
| `unrecorded_choice_tokens` | how much human contradiction the system could not fully classify |
| `map_integrity` | whether living routes still belong to people rather than monopolies |
| `counter_cadence_known` | whether the party learned to resist system pressure by method rather than force |
| `act2_whisper_pressure` / `ninth_ledger_pressure` | how much contaminated pressure escaped containment |
| companion approval / final state | who still believes in the player's philosophy when it finally matters |

## Ending Family Overview

There should be five main endings and two failure endings.

### Main endings

1. Restoration Under Control
2. Humane Constraint
3. Distributed Autonomy
4. Refusal Of Total System Rule
5. Containment At Meaningful Cost

### Failure endings

6. Recorded Submission
7. Open Seam

## Main Ending Matrix

| Ending | Core philosophy | Typical requirements | What the player does | World outcome |
| --- | --- | --- | --- | --- |
| Restoration Under Control | the system should govern more cleanly and more completely | high `system_alignment`, medium/high `map_integrity`, player willing to use the lens as rule-instrument | stabilizes and reasserts route, record, and system authority through the Ledger/Forged lens | roads become safer and more legible, but freedom narrows and lived truth is subordinated to managed order |
| Humane Constraint | the system may remain under chosen moral limits and witness | `counter_cadence_known`, medium/high `map_integrity`, medium/high trust with humane companions, lens understood but not worshiped | binds or edits the Ledger's authority with counter-cadence, preserved witness, and chosen limits | the world gains stability without total submission, though permanent tension remains between care and control |
| Distributed Autonomy | no single authority should own truth, routes, or systems | low `system_alignment`, medium/high `unrecorded_choice_tokens`, at least moderate `map_integrity` | breaks monopoly over route and record authority, disperses knowledge, weakens centralized alignment tools | the world becomes messier but more human; movement, testimony, and local power diversify |
| Refusal Of Total System Rule | some systems are too dangerous to preserve intact even when useful | low `system_alignment`, lens blinded/broken path, willingness to lose structural advantage | cripples the ruling capacity of the Ledger/Forged route logic rather than inherit it | the world loses clean coordination but also escapes total accounting; survival becomes harder, domination less absolute |
| Containment At Meaningful Cost | unresolved failure must be limited even if no one wins cleanly | high pressure conditions, `counter_cadence_known` helpful, player accepts sacrifice | seals or quarantines the most dangerous route between Ledger logic, Forge lens, and Abyss rupture | catastrophe is delayed or contained, but access, knowledge, or whole corridors of the world may be lost |

## Failure Ending Matrix

| Ending | Trigger feel | World outcome |
| --- | --- | --- |
| Recorded Submission | high `player_predictability`, low `unrecorded_choice_tokens`, high pressure, weak companion resistance | the player or world is successfully entered into Malzurath's accounting logic; movement and choice continue, but only as managed outcomes |
| Open Seam | low `map_integrity`, high `ninth_ledger_pressure`, no adequate cadence or humane resistance | the system fails to resolve cleanly and containment collapses; reality frays into repeating, partial, and unfinished zones |

These are consequence endings earned by cumulative ideological and systemic
failure. A single lost fight should never trigger them.

## Detailed Ending Notes

### 1. Restoration Under Control

Promise:
- cleaner roads
- stable routing
- reduced overt chaos

Cost:
- stronger certification regimes
- narrower tolerated autonomy
- truth becomes more official and less human

Best faction beneficiaries:
- hardline Council elements
- Reclaimers who favor governance through understanding
- remnants willing to accept system order as necessary

Most likely companion responses:
- Rhogar can support if framed as duty
- Tolan may support if civilian safety is real
- Nim may support if ethics remain visible
- Elira, Bryn, and Irielle should all be wary or opposed

### 2. Humane Constraint

Promise:
- stability without pure domination
- routes remain usable
- witness and mercy remain load-bearing

Cost:
- the world stays contested
- maintenance becomes permanent work
- the temptation to slip into control never disappears

Best faction beneficiaries:
- Lantern Faith
- moderate Council
- humane Reclaimers
- Remembered

Most likely companion responses:
- strongest consensus ending
- Elira, Tolan, Kaelis, Nim can all support
- Rhogar strongly supports if the constraint feels like sworn stewardship
- Bryn accepts if it does not become soft monopoly
- Irielle supports if the cadence is used to limit control, not mask it

### 3. Distributed Autonomy

Promise:
- no single power owns the future
- routes become plural, local, and negotiable
- living truth outranks centralized certification

Cost:
- less uniform safety
- more local conflict
- slower reconstruction

Best faction beneficiaries:
- Free Operators
- local councils that can survive without monopolies
- survivors who distrust large systems

Most likely companion responses:
- Bryn strongly supports
- Irielle supports
- Elira can support if people are not abandoned
- Kaelis may support if map honesty survives
- Rhogar is mixed
- Nim is mixed if too much knowledge is scattered without stewardship

### 4. Refusal Of Total System Rule

Promise:
- nobody inherits the old totalizing machine
- the world keeps moral space that cannot be fully counted

Cost:
- broken systems remain broken
- infrastructure recovery is delayed or permanently reduced
- some places become unreachable or unsafe

Best faction beneficiaries:
- radical Free Path lanes
- anti-system survivors
- some Remembered and Irielle routes

Most likely companion responses:
- Bryn and Irielle support strongly
- Elira may support if it prevents dehumanization
- Nim opposes if it destroys too much understanding
- Rhogar may see it as abdication unless framed as moral refusal

### 5. Containment At Meaningful Cost

Promise:
- the worst breach does not become the whole world
- catastrophe is held back

Cost:
- lost routes
- sealed knowledge
- chosen sacrifice
- a future built around a wound that never fully heals

Best faction beneficiaries:
- no faction wins cleanly
- survivors benefit, ideologues do not

Most likely companion responses:
- Tolan and Elira can support if the cost is borne honestly
- Irielle supports if it stops further capture
- Kaelis supports if the truth of the sacrifice is not hidden
- Nim supports if some understanding is preserved
- Bryn accepts reluctantly if containment does not become permanent authoritarian lock

## Companion Break Conditions In The Endgame

Use these as late-game hard lines.

| Companion | Most likely break trigger |
| --- | --- |
| Elira Lanternward | preserving system order by knowingly discarding witnesses, captives, or the dead |
| Bryn Underbough | handing permanent truth or route monopoly to one authority without meaningful limit |
| Tolan Ironshield | treating ordinary people as acceptable collateral for elegant systemic solutions |
| Kaelis Starling | accepting false certainty when evidence proves the route or map is lying |
| Rhogar Valeguard | using honor and civic language as cover for naked domination |
| Nim Ardentglass | destroying or refusing critical knowledge out of fear alone, or inheriting it without ethics |
| Irielle Ashwake | embracing Choir-style submission, lens rule, or self-erasing pattern logic |

## Faction End-State Grid

| Ending | Council | Lantern Faith | Ashen Brand remnant | Quiet Choir remnant | Reclaimers | Free Operators |
| --- | --- | --- | --- | --- | --- | --- |
| Restoration Under Control | strengthened | tolerated but constrained | crushed or absorbed | partially repurposed or suppressed | empowered | narrowed |
| Humane Constraint | stabilized and accountable | strengthened | weakened | broken but not forgotten | disciplined and limited | tolerated and necessary |
| Distributed Autonomy | decentralized | locally strengthened | fragmented | scattered underground | divided | strengthened |
| Refusal Of Total System Rule | weakened structurally | morally important but materially strained | weakened but chaos pockets remain | denied clean victory | frustrated | strengthened but burdened |
| Containment At Meaningful Cost | exhausted | deepened by sacrifice | disrupted | disrupted | partially cut off from deeper ambitions | route-dependent and unstable |

## Secret Act 4 Or Post-Ending Continuation Hook

Any continuation path should function as a post-resolution route for endings
that leave:

- living map integrity
- meaningful unrecorded choice
- and unresolved but non-catastrophic leftover system depth

Recommended unlock conditions:

- `malzurath_revealed = true`
- `counter_cadence_known = true`
- `map_integrity >= 3`
- `unrecorded_choice_tokens >= 2`
- not in `Recorded Submission`
- not in `Open Seam`

Recommended continuation premise:
- the world remains unfinished after the great accounting fails to close cleanly
- the surviving question concerns how unrecorded routes, uncounted people, and
  witness spaces live onward

## Scene Architecture For Final Choices

The final choice set should have three layers:

### Layer 1. Recognition

The player understands what the Forge, Ledger, and Abyss actually mean.

### Layer 2. Commitment

The player chooses a philosophy:
- govern
- constrain
- distribute
- refuse
- contain

### Layer 3. Cost

The player chooses what to lose:
- central stability
- free access
- knowledge
- speed of recovery
- trusted relationships
- or part of the world itself

## Writing Rules For Ending Scenes

- every ending must name what becomes easier and what becomes harder
- every ending must show who pays the hidden cost
- avoid triumph that sounds total
- companions should interpret the ending through ideology and lived belief,
  with affection acting as a modifier
- the Abyss should remain the image of unresolved failure and incomplete
  reality, not simple destruction
- Malzurath should feel like the final form of counted certainty, grounded in
  the campaign's route-and-record logic

## Recommended Immediate Next Uses

This doc should feed:

- Act 3 route packets
- companion endgame reaction sheets
- faction epilogue planning
- Secret Act 4 gate logic if retained
- Meridian Forge and Meridian Depths location bible work
