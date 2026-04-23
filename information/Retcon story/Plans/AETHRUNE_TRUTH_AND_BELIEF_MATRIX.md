# Aethrune Truth And Belief Matrix

This document is the first storybuilding deliverable after the current retcon
implementation phases. Its job is to lock the campaign's ideological spine
before more scene prose, quest branching, and companion writing are produced.

Primary inputs:

- `information/Retcon story/Lore/aethrune_religions_v1.md`
- `information/Retcon story/Lore/aethrune_v2_world.md`
- `information/Retcon story/World/aethrune_world_v1.md`
- `information/Retcon story/World/emberway_aethrune_v1.md`
- `information/Retcon story/World/greywake_aethrune_v2.md`
- `information/Retcon story/World/iron_hollow_aethrune_v5.md`
- `information/Retcon story/World/hushfen_aethrune_v1.md`
- `information/Retcon story/World/stonehollow_aethrune_v1.md`
- `information/Retcon story/World/resonant_vaults_aethrune_v2.md`
- `information/Retcon story/World/aethrune_abyss.md`
- `information/Retcon story/NPCs/NPC_relationship_map.md`
- `information/Retcon story/NPCs/NPCs_new.md`
- `information/Retcon story/NPCs/aethrune_enemy_categories_v1.md`
- `information/Retcon story/Systems/aethrune_gameplay_variables_tuning_v1.md`
- `information/Retcon story/Systems/aethrune_quest_to_variable_matrix_v1.md`

## Core Story Question

Who gets to define reality when roads, records, systems, and memory disagree?

This question should sit under every major act:

- Act 1 asks who controls passage and public fear.
- Act 2 asks who controls truth, interpretation, and access to buried systems.
- Act 3 asks whether the old system should be restored, rewritten, refused, or
  contained.

## Axis Definitions

Use these as the stable ideological axes across the campaign.

| Axis | Pole A | Pole B | Story Use |
| --- | --- | --- | --- |
| Control | centralized authority | distributed autonomy | defines who should hold roads, maps, and systems |
| Truth | verified record | lived or witnessed truth | defines who is believed when evidence conflicts |
| Memory | preserved names and testimony | redaction, pruning, or omission | defines what survives collapse |
| Repair | restore the system | refuse or break the system | defines endgame philosophy |
| Resolution | force clean answers | accept contradiction and uncertainty | defines the line between order and the Abyss |

## Faction And Doctrine Matrix

This table maps the major operating blocs and belief lanes.

| Group | Truth model | What it wants | What it fears | Preferred methods | Natural allies | Natural opposition |
| --- | --- | --- | --- | --- | --- | --- |
| Iron Hollow Council | practical civic truth | a town that continues to function | panic, fragmentation, loss of compliance | logistics, public legitimacy, compromise under strain | Lantern Faith, selective Free Operator help | Ashen Brand, Quiet Choir, hardline Reclaimers when safety is ignored |
| Lantern Faith | human truth carried by witness and care | endurance, memory, mercy, human continuity | dehumanized order, forgotten dead, sacrifice without mourning | healing, naming, mediation, public courage | Council, Remembered, merciful companions | Quiet Choir, Ashen Creed, ruthless optimization |
| Ashen Brand / Ashen Creed | truth belongs to whoever can hold the road | route monopoly, fear, leverage, obedience | uncontrolled movement, public solidarity, honest witnesses | fake authority, ambush, visible punishment, territorial domination | opportunists, frightened local elites | Council, Free Path, Lantern Faith |
| Quiet Choir | truth is pattern, tuned not debated | interpretive supremacy over signal, record, and system response | emotional truth, independent witnesses, unclassifiable choices | silence discipline, record manipulation, cadence control, patient infiltration | system listeners, compromised officials, some Reclaimer splinters | Lantern Faith, Free Path, Irielle, high-token player paths |
| Meridian Reclaimers / Meridian Doctrine | truth is engineered and recoverable | restoration through understanding and controlled excavation | ignorance, superstition, reckless destruction, anomaly spread | study, reconstruction, mapping, secured access | Greywake methods, Nim-style scholarship, some Council pragmatists | Choir control logic, anti-system refusal, labor backlash when cost is too high |
| Free Operators / Free Path | truth is situational and earned, not certified | autonomy, mobility, flexible survival | monopoly, fixed hierarchy, ideological capture | side channels, informal networks, self-authored codes | Bryn lanes, Hadrik, Sella, selective Council cooperation | Ashen Brand, rigid Greywake bureaucracy, Quiet Choir |
| Remembered | truth survives through preserved names and stories | continuity of identity beyond collapse | erasure, anonymized sacrifice, history as tool | witness, oral history, memorial record, survivor testimony | Lantern Faith, Old Tam, public grief quests | Choir redaction, ruthless control choices |
| Veilbound | truth hides in what remains unseen or unmeasured | protected contact with anomaly and threshold phenomena | total exposure, false certainty, shallow interpretation | observation, withdrawal, indirect ritual, guarded research | fringe scholars, anomaly investigators | dogmatic institutions of any type |
| Fractured Signal | broken truth is more honest than imposed order | sabotage of false systems and forced meaning | stable control, coherent doctrine, closed interpretation | disruption, contradiction, anti-order rituals, systemic destabilization | rogue Choir remnants, nihilistic cells | Council, Lantern Faith, Reclaimers, anyone trying to stabilize the world |

## Variable Interpretation Guide

These are the narrative meanings that should stay stable when scene writers use
the variable system.

### `system_alignment`

- Raise it when the player chooses discipline, clean hierarchy, infrastructure
  restoration, and certainty even at moral cost.
- Lower it when the player chooses human judgment, decentralization, refusal of
  total control, or deliberate system-breaking.

Narrative read:
- high = "the player thinks ordered structures should decide more"
- low = "the player trusts people over systems"

### `player_predictability`

- Raise it when the player solves problems through one repeated philosophy or
  obvious optimal pattern.
- Lower it when the player preserves contradictions, surprises the system, or
  makes costly humane choices.

Narrative read:
- high = legible to adaptive systems
- low = harder for the world to model cleanly

### `unrecorded_choice_tokens`

- Gain them when the player protects lives over optimization, keeps conflicting
  loyalties, or makes choices that do not collapse neatly into doctrine.
- Lose or fail to gain them when the player keeps resolving every problem into
  one clean control philosophy.

Narrative read:
- high = the player still contains human irregularity the system cannot finish
- low = the player is becoming easy to classify

### `map_integrity`

- Raise it when routes remain honest, open, and survivable without total
  monopoly.
- Lower it when roads are militarized, surveys are falsified, or access is
  centralized through fear and control.

Narrative read:
- high = living routes still belong to people
- low = routes are becoming captured systems

## Companion Belief Matrix

Use public-facing names in story docs. Runtime ids can remain save-safe until a
 later implementation pass. For example, Elira may still be stored internally as
 `Elira Dawnmantle`, but storybuilding should treat her as `Elira Lanternward`.

| Character | Primary lane | Secondary pull | Approves of | Rejects | Break line |
| --- | --- | --- | --- | --- | --- |
| Elira Lanternward | Lantern Faith | Remembered | rescue, naming the dead, mercy under pressure, choosing people before proof | contempt, dehumanized control, sacrifice justified as efficiency | repeated choices that preserve order while abandoning witnesses or survivors |
| Bryn Underbough | Free Path | practical survivor ethics | breaking fake authority, flexible solutions, anti-monopoly choices, keeping exits open | rigid authority, trust-me-because-I-say-so institutions, public crackdowns | a player who keeps trading freedom for structure |
| Tolan Ironshield | civic duty grounded in survival | Council pragmatism | holding the line, protecting civilians, honest follow-through, earned steadiness | vanity, reckless theorizing, promises without action | repeated choices that privilege abstraction over the living people in front of him |
| Kaelis Starling | truth through pattern-reading | cautious civic responsibility | careful observation, honest route-reading, disciplined anti-Brand action, subtlety over noise | sloppy certainty, false maps, repeating mistakes because authority said so | a player who ignores evidence and treats maps as more real than judgment |
| Rhogar Valeguard | oath-bound order | humane reform rather than cruelty | open defense, responsibility, visible courage, structure used to protect others | cynicism, opportunism, tolerated corruption, evasive half-commitments | a player who treats honor as disposable rhetoric |
| Nim Ardentglass | Meridian Doctrine | humane scholarship | study before destruction, honest excavation, pattern interpretation, curiosity with restraint | anti-knowledge posturing, smashing what could be learned from, panic-driven refusal | a player who always chooses suppression over understanding |
| Irielle Ashwake | anti-Choir survival | guarded Free Path | containment, resisting pattern capture, protecting selfhood, skepticism toward forced revelation | surrender to system voices, cadence obedience, "the system knows best" logic | any route where the player embraces Choir-style certainty or control |

## Key NPC Anchor Matrix

These NPCs should carry the ideological weight of the setting in public scenes.

Note:
- preserve runtime spelling as `Garren Flint` if code/tests already depend on it

| Character | Primary lane | Scene function |
| --- | --- | --- |
| Tessa Harrow | Council civic pragmatism | makes survival procedural and reveals the cost of keeping a town functional |
| Garren Flint | defensive order | speaks for hard public safety and suspicion of outsider disruption |
| Nera Doss | labor survival ethics | forces system ambitions to answer the question "who pays the bodily cost?" |
| Hadrik | Free Operator leaning Council | shows compromise between profit, logistics, and town loyalty |
| Sella Quill | Free Path opportunism | turns information into leverage without pretending it is neutral |
| Old Tam Veller | Remembered | preserves identity, survivor memory, and the long emotional history of collapse |
| Varyn Sable | Ashen Creed strategist | gives the control-through-passage philosophy its most polished voice |
| Rukhar Cinderfang | Ashen Creed force | embodies route ownership as open domination rather than administrative finesse |
| Vaelith Marr | hybrid curiosity without ethics | bridges human ambition and dangerous system contact |
| Caldra Voss | Quiet Choir | gives calm, articulate form to control-through-pattern |
| Pale Witness | system-bound truth | reveals dangerous facts without offering a human moral frame |

## Location Truth Map

This matrix shows what each major region should prove or challenge.

| Location | Primary pressure | Truth mode | Dominant question | Doctrine under pressure | Counter-doctrine |
| --- | --- | --- | --- | --- | --- |
| Emberway | movement control | visible route truth | who controls passage? | Ashen Brand / Council conflict | Free Path, Lantern witness routes |
| Iron Hollow | human continuity under strain | lived civic truth | what keeps people going when collapse is ordinary? | Council and Lantern Faith | Ashen Creed, hardline Reclaimer sacrifice |
| Greywake | certification and mapping | procedural truth | who is allowed to declare what is real? | Reclaimer and survey logic | Free Path skepticism, Hushfen-style contradiction |
| Hushfen | contradiction, echo, incomplete record | uncontrolled memory truth | what remains when truth is not organized? | Choir interest, Greywake failure | Remembered, anomaly humility |
| Stonehollow Dig | excavation consequence | buried structural truth | what happens when knowledge is physically opened? | Meridian Doctrine | labor caution, anti-system warning |
| Glasswater Intake | managed flow and allocation | infrastructural truth | who owns the systems that distribute survival? | Reclaimers and civic planners | Free Path sabotage, Choir appropriation |
| Broken Prospect | failed ambition | broken expedition truth | what does a failed claim reveal about greed and misreading? | Reclaimer overreach | survivor pragmatism |
| South Adit | captivity, extraction, pressure | coerced truth | what is revealed when people are trapped inside a system? | Ashen or Choir control lanes depending final use | Lantern mercy, Irielle anti-control routes |
| Resonant Vaults | adaptive system intelligence | predictive truth | what does a system learn from you, and what does it do with that knowledge? | Quiet Choir and Meridian logic | low-predictability, high-token player path |
| Blackglass Causeway | crossing through submerged risk | transit truth under distortion | what does it mean to keep a route alive across unstable ground? | route authority and survival logistics | collapse, mistrust, fear |
| Meridian Forge | restoration or rewrite power | authored truth | who gets to decide what the world should resolve into? | every major doctrine converges here | none; this is the collision point |
| Meridian Depths | core systemic inheritance | foundational truth | was the old system ever savable, or only survivable? | final endgame philosophies | player-defined answer |
| Abyss | unresolved failure | truth without resolution | what is left when reality is no longer being finished? | Choir interpretation and existential terror | any doctrine that requires clean certainty |

## Dialogue Tone Guide

Use these as writing constraints, not decoration.

### Council civic pragmatism

- short, practical, burdened sentences
- names labor, timing, stock, compliance, and consequence
- rarely speaks in cosmic terms
- default tone: "someone has to keep this working"

### Lantern Faith

- names people before systems
- uses care language, witness language, and endurance language
- never sounds naive; mercy is a disciplined act here
- default tone: "the living and the dead both deserve to count"

### Ashen Brand / Ashen Creed

- territorial, possessive, transactional language
- treats routes as assets and fear as proof
- speaks as if ownership justifies truth
- default tone: "if we can hold it, it is ours"

### Quiet Choir

- calm, exact, and disconcertingly unhurried
- prefers pattern, cadence, tuning, correction, signal, and inevitability
- treats feelings as noisy data unless strategically useful
- default tone: "truth becomes clearer when resistance stops"

### Meridian Reclaimers / Doctrine

- precise, analytical, quietly ambitious
- speaks in terms of function, structure, restoration, access, and interpretation
- should sound curious before sounding mystical
- default tone: "if it was built, it can be understood"

### Free Operators / Free Path

- plainspoken, skeptical, mobile
- distrusts grand claims, respects competence
- sounds like someone testing whether the other person is worth trusting
- default tone: "no system gets my loyalty for free"

### Remembered

- intimate, elegiac, witness-driven
- speaks through names, stories, and what should not be lost
- should feel emotionally precise, not melodramatic
- default tone: "if the name remains, the person still matters"

### Veilbound

- oblique, cautious, withheld
- implies more than it states directly
- never sounds fully comfortable with exposure
- default tone: "what is hidden may still be acting"

### Fractured Signal

- unstable but purposeful
- repeats, interrupts, or twists certainty against itself
- should feel like ideology breaking into sabotage
- default tone: "false order deserves to fail loudly"

## Branching Rules For Writers

Every major branch should put at least two of the following in conflict:

- mercy vs control
- witness vs certification
- restoration vs refusal
- truth vs stability
- order vs autonomy
- explanation vs containment

Do not write branches as simple good-versus-evil moral tests.

Preferred shape:
- one option protects structure
- one option protects people
- one option preserves uncertainty or future leverage

That pattern will keep the setting's philosophy alive in play.

## Recommended Story Use

Use this document to guide:

- companion approval logic
- NPC rewrite packets
- quest family design
- Act 2 and Act 3 scene planning
- ending architecture
- faction and location tone passes

## Next Deliverables To Derive From This Matrix

- `AETHRUNE_COMPANION_IDEOLOGY_MATRIX.md`
- `AETHRUNE_LOCATION_THEME_MAP.md`
- `AETHRUNE_ENDING_ARCHITECTURE.md`
- `AETHRUNE_DIALOGUE_TONE_GUIDE.md`
