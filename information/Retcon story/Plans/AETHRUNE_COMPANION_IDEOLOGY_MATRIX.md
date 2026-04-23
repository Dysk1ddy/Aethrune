# Aethrune Companion Ideology Matrix

This document turns the companion cast into a storybuilding system instead of a
set of isolated personalities. It should be used alongside:

- `AETHRUNE_TRUTH_AND_BELIEF_MATRIX.md`
- `aethrune_gameplay_variables_tuning_v1.md`
- `aethrune_quest_to_variable_matrix_v1.md`
- `NPC_relationship_map.md`
- `dnd_game/data/story/companions.py`

## Purpose

Companion trust needs to carry ideology, injury, and pressure.

They should represent competing answers to the question:

Who should decide what survives when systems, memory, and human need collide?

This matrix defines:

- each companion's ideological lane
- what kind of player choices build or break trust
- what personal-quest direction each companion can grow into
- where party conflict should come from
- how companions should react to endgame philosophies

## Public Name Rule

Use public-facing names in planning docs.

Runtime ids can remain save-safe for now:

| Public name | Current runtime id / internal name |
| --- | --- |
| Elira Lanternward | `elira_dawnmantle` / `Elira Dawnmantle` |
| Tolan Ironshield | `tolan_ironshield` |
| Bryn Underbough | `bryn_underbough` |
| Kaelis Starling | `kaelis_starling` |
| Rhogar Valeguard | `rhogar_valeguard` |
| Nim Ardentglass | `nim_ardentglass` |
| Irielle Ashwake | `irielle_ashwake` |

## Companion Core Matrix

| Companion | Primary lane | Secondary pull | Core wound | What they want from Aethrune | What they fear most |
| --- | --- | --- | --- | --- | --- |
| Elira Lanternward | Lantern Faith | Remembered | the road teaches people to treat losses as acceptable paperwork | a world where witness, mercy, and the dead still count | a restored order that functions by making sacrifice feel normal |
| Bryn Underbough | Free Path | practical survivor ethics | authority usually protects itself first | routes no one faction can own completely | becoming trapped under a structure that calls obedience safety |
| Tolan Ironshield | civic duty under strain | Council pragmatism | too many promises failed after people trusted the line would hold | dependable protection that ordinary people can build life around | abstraction outranking the living people immediately at risk |
| Kaelis Starling | pattern-reading truth | cautious civic trust | he once trusted the wrong map and paid for it in lives | honest routes, honest signals, and leaders who listen to evidence | institutions forcing false certainty onto unstable ground |
| Rhogar Valeguard | oath-bound order | humane reform | if vows mean nothing, people become prey for whoever is louder | a defendable order worthy of loyalty | a world where honor is a costume for power |
| Nim Ardentglass | Meridian Doctrine tempered by conscience | humane scholarship | curiosity can save people or kill them depending on discipline | understanding deep systems without surrendering ethics to them | panic, ignorance, and smashing the unknown before it can be read |
| Irielle Ashwake | anti-Choir survival | guarded Free Path | revelation was used to steal her selfhood | a future where systems cannot tune human beings into obedience | any route that starts calling surrender "clarity" |

## Approval Drivers

Use these as the default approval logic for scene writing.

### Elira Lanternward

Wins trust when the player:
- rescues witnesses, captives, or civilians
- preserves names, testimony, and mourning spaces
- chooses costly mercy without becoming passive
- refuses to let proof matter more than people

Loses trust when the player:
- preserves order by abandoning the vulnerable
- treats harshness as sophistication
- uses dangerous systems without moral guardrails
- repeatedly picks force-first outcomes when humane ones were possible

### Bryn Underbough

Wins trust when the player:
- breaks fake authority
- keeps exits open
- distrusts monopolies on truth or movement
- accepts messy but living outcomes over polished control

Loses trust when the player:
- centralizes power casually
- uses public crackdowns as the default answer
- accepts official certainty too easily
- turns every problem into compliance

### Tolan Ironshield

Wins trust when the player:
- follows through visibly
- protects civilians before symbolic victories
- stands firm under pressure
- shows that leadership means carrying weight, not shifting it

Loses trust when the player:
- chases theory while people bleed
- makes promises and walks away from the cost
- performs cleverness instead of duty
- treats steadiness like small thinking

### Kaelis Starling

Wins trust when the player:
- reads evidence carefully
- notices pattern over rhetoric
- protects route honesty
- avoids repeating a known bad method just because it is official

Loses trust when the player:
- trusts maps over judgment
- ignores anomalies because they are inconvenient
- rewards false certainty
- chooses noise or spectacle over clean observation

### Rhogar Valeguard

Wins trust when the player:
- acts openly in defense of others
- uses structure to protect rather than dominate
- names commitments and keeps them
- reforms broken authority instead of abandoning the idea of duty

Loses trust when the player:
- treats honor as naive
- accepts corruption as practical necessity
- manipulates trust without believing in it
- hides behind half-decisions while others pay the cost

### Nim Ardentglass

Wins trust when the player:
- studies before destroying
- asks what a structure was for before deciding what to do with it
- pursues knowledge with restraint
- protects people without abandoning understanding

Loses trust when the player:
- rejects knowledge as dangerous in itself
- smashes useful evidence reflexively
- collapses every anomaly into "burn it"
- treats curiosity as moral weakness

### Irielle Ashwake

Wins trust when the player:
- resists cadence capture
- values selfhood over revelation
- contains dangerous signal rather than mastering it for prestige
- believes survivors who say the system is not neutral

Loses trust when the player:
- embraces the Forge-lens as clean authority
- talks like the Choir when describing truth
- treats the player's own clarity as more important than others' freedom
- chooses control-first routes that look too much like submission

## Direction States

These are the preferred personal-quest outcome lanes.

| Companion | State A | State B | State C |
| --- | --- | --- | --- |
| Elira Lanternward | hopeful witness | burdened healer | hardened mercy |
| Bryn Underbough | loyal freehand | opportunist survivor | escaped self |
| Tolan Ironshield | mentor | hardened wall | fatalist veteran |
| Kaelis Starling | balanced scout | decisive hunter | paranoid cartographer |
| Rhogar Valeguard | reformer | enforcer | broken oath |
| Nim Ardentglass | disciplined scholar | consumed interpreter | balanced reader |
| Irielle Ashwake | free survivor | contained listener | unstable vessel |

### Meaning Of These States

- `State A` should mean the companion grows toward their best self without
  becoming simple or saintly.
- `State B` should mean the companion survives by hardening or narrowing.
- `State C` should mean the companion becomes dangerous, diminished, or harder
  to save.

## Personal Quest Design Questions

Each companion needs one question that no other companion can fully answer for
them.

| Companion | Personal question | Best route | Hard route | Damage route |
| --- | --- | --- | --- | --- |
| Elira | what does mercy mean when mercy carries risk for everyone else? | mercy with witness | harsh safety | spiritual withdrawal |
| Bryn | what is freedom worth if no structure ever deserves trust? | chosen loyalty without surrender | leverage-first freedom | total detachment |
| Tolan | when does duty protect life and when does it become habit wearing armor? | duty with tenderness | duty without tenderness | exhausted surrender |
| Kaelis | when should evidence outrank official certainty? | evidence with trust | evidence without trust | obsession |
| Rhogar | can order remain moral when the world rewards domination? | reform | enforcement | oath collapse |
| Nim | how much knowledge is worth carrying if it changes the carrier? | study with limits | study with appetite | refusal of moral responsibility |
| Irielle | how do you live after a system taught you your own mind was not yours? | sever and reclaim | contain and endure | absorb and echo |

## Key Party Conflict Pairs

Use these for banter, camp scenes, branch arguments, and approval cross-talk.

| Pair | Central argument |
| --- | --- |
| Elira vs Nim | does understanding justify risk, or must knowledge answer to mercy first? |
| Elira vs Rhogar | when does duty protect life, and when does duty start excusing harm? |
| Bryn vs Rhogar | is structure a shield or the first step toward capture? |
| Bryn vs Tolan | is stability worth the cost of living under rules written by others? |
| Kaelis vs Rhogar | should evidence override hierarchy when the hierarchy is wrong? |
| Nim vs Irielle | can dangerous systems be understood safely, or is that belief itself the trap? |
| Elira vs Irielle | how much of the wounded self can be healed by care, and how much needs destruction of what caused the wound? |
| Bryn vs Nim | is buried knowledge leverage, responsibility, or bait? |

## Approval And Loyalty Threshold Use

Recommended narrative use of the variable bands:

| Approval band | Story meaning | Scene behavior |
| --- | --- | --- |
| `8 to 10` | Bound | companion risks themselves for the player and argues for their philosophy in Act 3 |
| `5 to 7` | Loyal | companion backs the player unless pushed into a direct belief-line violation |
| `2 to 4` | Friendly | companion supports but still challenges openly |
| `-1 to 1` | Neutral | companion defaults to role function, not deep trust |
| `-2 to -4` | Strained | companion starts withholding emotional trust and may oppose route choices |
| `-5 to -7` | Fractured | companion can refuse support or trigger confrontation scenes |
| `-8 to -10` | Broken | departure, betrayal, shutdown, or permanent ideological split |

### Act 3 Loyalty Lock Rule

A companion should require both:

- approval at `5+`
- no direct violation of their break line during the key Act 2 / early Act 3 turns

to stay fully reliable in the late game.

## Endgame Preference Matrix

This is the fast guide for how companions read the main ending lanes.

| Companion | Restoration with strict control | Restoration with humane constraint | Distributed autonomy | Refusal of total system rule | Containment at cost |
| --- | --- | --- | --- | --- | --- |
| Elira | opposes | supports cautiously | supports if people are protected | supports if memory and witness survive | supports if it saves lives without erasing the dead |
| Bryn | opposes hard | wary but possible | supports | supports strongly | supports if it does not become another lockdown |
| Tolan | wary support if civilians are safer | supports strongly | mixed | mixed | supports if the cost is honest and necessary |
| Kaelis | distrusts | supports if evidence remains honest | supports if routes stay usable | supports if false maps are broken | supports if the truth of the cost is not hidden |
| Rhogar | can support | strongly supports | mixed | opposes if it feels like abdication | supports if framed as duty and protection |
| Nim | supports if ethical | strongly supports | mixed | opposes if it destroys too much knowledge | supports if it preserves understanding without domination |
| Irielle | opposes hard | cautious support | supports | strongly supports | supports if it prevents future capture |

## Writing Rules

When writing companion scenes:

- do not flatten them into "merciful one," "skeptic one," or "smart one"
- always connect their belief stance to a wound, habit, or survival lesson
- make approval changes about philosophy under pressure, not abstract morality
- let companions agree on goals while violently disagreeing on methods
- keep at least one disagreement alive even in high-trust party states

## Recommended Next Uses

This doc should feed:

- companion personal quest packet drafts
- approval event matrices
- Act 2 conflict banter
- Act 3 loyalty locks and fracture scenes
- ending reaction writing
