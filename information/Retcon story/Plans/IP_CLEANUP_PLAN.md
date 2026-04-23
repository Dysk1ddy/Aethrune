# IP Cleanup Plan

This document is a practical cleanup plan for turning this repo into a public-facing original game instead of a project visibly tied to Dungeons & Dragons and the Forgotten Realms.

It is not legal advice. It is a repo-specific engineering and content plan based on the current code and docs layout.

## Working assumption

Target outcome:

- keep the game's original strengths
- remove Wizards-specific story and setting material
- decide intentionally whether to keep an SRD-based rules chassis or fully originalize the rules vocabulary

Recommended default:

- originalize the world, story, locations, gods, factions, and public branding
- keep the code architecture and encounter/state systems
- only keep rules terms that survive a deliberate SRD 5.1 whitelist pass

## Repo status at a glance

The repo currently mixes three different kinds of content:

1. Clear Wizards-facing setting and branding references
2. Original story/gameplay material that can survive the transition
3. D&D-style mechanics and terminology that need a rules-lane decision

That split shows up clearly in the codebase:

- Public branding and docs openly describe the project as D&D / Forgotten Realms:
  - `README.md`
  - `dnd_game/__init__.py`
  - `android_port/README.md`
  - `android_port/dnd_game/__init__.py`
- Runtime story content is still rooted in Neverwinter, Phandalin, Wave Echo, Conyberry, Agatha, and related material:
  - `dnd_game/gameplay/base.py`
  - `dnd_game/gameplay/story_intro.py`
  - `dnd_game/data/quests/act1.py`
  - `dnd_game/data/quests/act2.py`
  - `dnd_game/data/story/dialogue_inputs.py`
  - `dnd_game/data/story/companions.py`
  - `dnd_game/data/story/factories.py`
- The lore codex and several reference docs explicitly say they are adapted from official D&D material:
  - `dnd_game/data/story/lore.py`
  - `information/catalogs/SPELLS_ABILITIES_PASSIVES_FEATS_REFERENCE.md`
  - `information/systems/GAME_SYSTEMS_REFERENCE.md`
  - `information/systems/LEVELING_SYSTEM_DRAFT.md`
  - `information/Story/ACT1_CONTENT_REFERENCE.md`
  - `information/Story/ACT2_CONTENT_REFERENCE.md`
- The Android port mirrors much of the desktop content and will need the same cleanup:
  - `android_port/dnd_game/...`

## Bucket A: Rewrite Now

These are the places I would treat as red-zone content. Rewrite them even if you decide to keep an SRD-compatible rules layer.

### A1. Public branding and repo identity

Rewrite first:

- `README.md`
- `dnd_game/__init__.py`
- `android_port/README.md`
- `android_port/dnd_game/__init__.py`

Why:

- these are the most visible places where the project presents itself as D&D / Forgotten Realms work
- they shape first impressions for players, collaborators, and storefront reviewers

Immediate goal:

- stop calling the game D&D-inspired in public-facing copy
- stop describing the package as a D&D adventure package
- stop using `Sword Coast` as public sub-branding

### A2. Setting, map, and story proper nouns

Rewrite all explicit setting anchors:

- Neverwinter
- Phandalin
- Forgotten Realms
- Sword Coast
- High Road
- Triboar Trail
- Conyberry
- Agatha
- Wave Echo Cave
- Forge of Spells
- Old Owl Well
- Wyvern Tor
- Tresendar Manor
- Phandelver / Phandelver routes
- Mount Hotenow
- Lord Neverember
- Helm's Hold

Main file clusters:

- `dnd_game/gameplay/base.py`
- `dnd_game/gameplay/story_intro.py`
- `dnd_game/gameplay/story_act1_expanded.py`
- `dnd_game/gameplay/story_act2_scaffold.py`
- `dnd_game/gameplay/act2/conyberry.py`
- `dnd_game/gameplay/act2/wood_survey.py`
- `dnd_game/data/quests/act1.py`
- `dnd_game/data/quests/act2.py`
- `dnd_game/data/story/dialogue_inputs.py`
- `dnd_game/data/story/companions.py`
- `dnd_game/data/story/factories.py`
- `information/Story/*`
- `information/catalogs/NPCS.md`
- `information/catalogs/ITEM_CATALOG.md`

Practical note:

- scene ids, flags, and quest ids use many of these names internally
- even if you postpone deep runtime renames, you should at least rename public labels and player-facing text first

### A3. Gods, factions, and official-lore appendices

Rewrite or remove:

- Tymora and Tymoran references
- Zhentarim
- Forgotten Realms deity appendices
- Forgotten Realms faction summaries
- official appendices summaries grounded in D&D books

Main file clusters:

- `dnd_game/data/story/lore.py`
- `dnd_game/gameplay/story_intro.py`
- `dnd_game/gameplay/story_town_services.py`
- `dnd_game/gameplay/random_encounters.py`
- `dnd_game/data/story/companions.py`
- `dnd_game/data/story/factories.py`
- `information/Story/*`
- `information/systems/ACT1_RANDOM_ENCOUNTERS.md`

Recommendation:

- give Elira a new faith tradition in the new setting rather than trying to keep a renamed Tymora analogue that still behaves the same way

### A4. Explicitly adapted or paraphrased rules/lore text

These files are especially important because they do not just reference D&D. They explicitly say they are adapted from official material.

Rewrite or quarantine:

- `dnd_game/data/story/lore.py`
- `information/catalogs/SPELLS_ABILITIES_PASSIVES_FEATS_REFERENCE.md`
- `information/systems/GAME_SYSTEMS_REFERENCE.md`
- `information/systems/LEVELING_SYSTEM_DRAFT.md`
- `information/systems/OPENAI_STORY_WRITER.md`
- `information/Story/ACT1_CONTENT_REFERENCE.md`
- `information/Story/ACT2_CONTENT_REFERENCE.md`
- `information/Story/STORY_CONTENT_SUMMARY.md`

Why:

- these files create the clearest paper trail that the project is built as an adaptation
- they are the least defensible to leave unchanged in a public release

### A5. Item and monster references that lean on named official material

Rewrite obvious named or inspiration-forward references such as:

- `Holy Avenger`
- `Periapt of Wound Closure`
- item descriptions referencing `Forgotten Realms wonders`
- monster reference docs that frame designs as direct official-D&D-inspired archetype pulls

Main file clusters:

- `dnd_game/data/items/catalog.py`
- `information/catalogs/ITEM_CATALOG.md`
- `information/catalogs/enemies.md`
- `information/catalogs/ACT2_ENEMY_EXPANSION_DRAFT.md`

## Bucket B: Keep

These are the parts I would preserve. They look like your own game rather than borrowed setting material.

### B1. Core original narrative spine

Likely keep:

- Ashen Brand
- Quiet Choir
- Varyn Sable
- Caldra Voss
- Blackwake Crossing
- Greywake
- Cinderfall Ruins
- Ashfall Watch
- Emberhall Cellars
- Stonehollow Dig
- Broken Prospect
- Black Lake Causeway
- the claims-war pressure structure
- the route-control / town-stability / witness-pressure themes
- the political frontier + cosmic-horror escalation

These are not automatically safe in every sentence, because some are currently described through Forgotten Realms context. But the underlying concepts look original and worth preserving.

### B2. Systems and engine work

Keep:

- map framework
- party management
- relationship and companion support systems
- save/load structure
- inventory and equipment systems
- the MP implementation as a technical system
- combat turn structure as code
- quest/state/flag architecture
- story writer tooling
- test harness structure

Main code clusters:

- `dnd_game/gameplay/*.py`
- `dnd_game/data/quests/*.py`
- `dnd_game/models.py`
- `dnd_game/ai/*.py`
- `tests/*.py`

Important distinction:

- the code structure is keepable
- the names surfaced through that code are not always keepable

### B3. Original characters with setting-dependent bios

These are strong candidates to keep after reskinning their affiliations:

- Mira Thann
- Oren Vale
- Sabra Kestrel
- Vessa Marr
- Garren Flint
- Tessa Harrow
- Elira Dawnmantle
- Kaelis Starling
- Rhogar Valeguard
- Tolan Ironshield
- Bryn Underbough

Recommended treatment:

- keep the characters
- rewrite their city, religion, faction, route, and cultural attachments
- do not assume their current race/class labels are final if you choose a more aggressive rules originalization pass

## Bucket C: SRD Whitelist Decision

This is the yellow zone. Do not leave it in limbo.

You need to choose one of two paths:

1. keep a deliberately SRD-based rules layer with attribution
2. originalize the rules vocabulary as well as the setting

### C1. Files affected by that decision

- `dnd_game/models.py`
- `dnd_game/data/story/character_options/classes.py`
- `dnd_game/data/story/character_options/races.py`
- `dnd_game/data/story/character_options/backgrounds.py`
- `dnd_game/gameplay/creation.py`
- `dnd_game/gameplay/combat_flow.py`
- `dnd_game/gameplay/combat_resolution.py`
- `dnd_game/gameplay/status_effects.py`
- `dnd_game/gameplay/progression.py`
- `information/systems/GAME_SYSTEMS_REFERENCE.md`
- `information/systems/MP_SYSTEM_DRAFT.md`
- `information/systems/LEVELING_SYSTEM_DRAFT.md`
- `tests/test_core.py`
- `tests/test_act2_smoke.py`

### C2. If you keep an SRD-based rules chassis

Do this:

- build an explicit allowlist of every class, race, spell, feature, condition, weapon, armor term, and item rule term you intend to keep
- verify each kept term against SRD 5.1 instead of memory
- add the required CC BY 4.0 attribution for SRD-derived material
- stop mixing clearly non-setting original content with text that claims direct adaptation from official books

Rules vocabulary that belongs in the whitelist review:

- class names
- race or ancestry names
- spell names
- class feature names
- condition names
- `Armor Class`, `saving throw`, `death saves`, `initiative`, `proficiency`
- item names and enchantment names

### C3. If you fully originalize the rules layer

Do this:

- keep the math where it serves the game
- rename the surface vocabulary
- simplify the places where exact D&D language is doing the most brand signaling

Examples of low-pain originalization targets:

- `Armor Class` -> `Guard` or `Defense`
- `saving throw` -> `resist check` or `defense roll`
- `death saves` -> `bleed-out checks` or `last-chance checks`
- class labels -> role labels
- spell names -> original spell names
- `race` -> `ancestry`, `origin`, or `lineage`

### C4. My recommendation on the rules lane

For this repo, I would lean toward:

- original world and story
- mostly original rules-facing presentation
- optional quiet internal reuse of your current math where it helps implementation

Reason:

- it reduces legal and branding ambiguity
- it makes marketing easier
- it lets your strongest original material stop reading like a module remix

If you want the least rewrite work instead, the fallback is:

- original world and story
- SRD whitelist for mechanics
- strict removal of non-SRD or branded setting references

## First Files To Tackle

If I were doing this in order, I would start here:

1. `README.md`
   - remove D&D / Forgotten Realms positioning
2. `dnd_game/__init__.py`
   - stop branding the package as D&D
3. `android_port/README.md`
   - remove Sword Coast branding
4. `dnd_game/data/story/lore.py`
   - this is the biggest explicit adaptation liability
5. `dnd_game/gameplay/base.py`
   - central labels, scene names, codex blurbs, title-screen copy
6. `dnd_game/gameplay/story_intro.py`
   - heavy concentration of Neverwinter / Phandalin / Tymora / road-lore material
7. `dnd_game/data/quests/act1.py`
   - quest text and objective names
8. `dnd_game/data/quests/act2.py`
   - Act 2 still leans hard on Conyberry / Agatha / Wave Echo
9. `information/Story/ACT1_CONTENT_REFERENCE.md`
   - strong project-planning dependence on official place names
10. `information/Story/ACT2_CONTENT_REFERENCE.md`
   - strong project-planning dependence on official place names

After that:

- pick the rules lane
- then update `classes.py`, `races.py`, `combat_flow.py`, `combat_resolution.py`, and the system docs in one coordinated pass

## Suggested Rewrite Strategy

### Phase 1. Create a new world bible

Before mass renaming, define:

- new region name
- new hub town name
- new major city name
- new road names
- new religion/god structure
- new mine/ruin mythology
- new names for Act 1 and Act 2 anchor sites

If you skip this step, you will end up doing inconsistent string swaps.

### Phase 2. Build a rename map

Create a plain table with:

- old name
- new name
- scope
- notes

Suggested scopes:

- public-only rename
- player-facing runtime rename
- internal id rename later
- delete instead of rename

### Phase 3. Clean the public surface first

Do this before deep internal refactors:

- README
- package docstrings
- title-screen copy
- lore menu labels
- public reference docs

This gives you a much cleaner outward-facing repo quickly.

### Phase 4. Rewrite the story wrapper around your original spine

Focus on:

- city-to-frontier opening
- hub town politics
- shrine/god content
- mine-claims war framing
- cave/forge mythology

Keep:

- the pressure systems
- the companion structure
- the route logic
- the cult and conspiracy beats that are already yours

### Phase 5. Resolve the rules lane

Either:

- finish the SRD whitelist and attribution pass

Or:

- replace the D&D-facing vocabulary with original terms and rewrite the docs/tests to match

### Phase 6. Mirror the changes into the Android port

Important:

- the Android copy is not a separate legal cleanup
- it is a second copy of the same exposure

Treat desktop and Android as one cleanup effort.

## Fast Search Commands

Use these to keep the audit moving:

```powershell
rg -n -i "Neverwinter|Phandalin|Forgotten Realms|Sword Coast|Wave Echo|Forge of Spells|Old Owl Well|Wyvern Tor|Tresendar|Conyberry|Agatha|Phandelver"
```

```powershell
rg -n -i "Tymora|Zhentarim|Lord Neverember|Helm's Hold|Mount Hotenow|Waterdeep|Baldur's Gate|Faerun"
```

```powershell
rg -n -i "Magic Missile|Eldritch Blast|Cure Wounds|Healing Word|Fire Bolt|Sacred Flame|Produce Flame|Vicious Mockery|Divine Smite|Lay on Hands|Channel Divinity|Bardic Inspiration|Action Surge|Second Wind|Rage|Flurry of Blows|Cunning Action|Patient Defense|Step of the Wind"
```

```powershell
rg -n -i "official D&D|Forgotten Realms|Basic Rules|Free Rules|D&D Beyond|in this adaptation|inspired by"
```

## Bottom Line

The strongest path for this repo is not a total scorched-earth rewrite.

What you have is better than that:

- a reusable engine
- a strong original intrigue-and-pressure spine
- several original locations and factions worth keeping

The part to replace is the D&D wrapper around it:

- setting
- gods
- public branding
- adapted lore/reference text
- any rules terminology you are not prepared to defend through an SRD whitelist

## Good Next Pass

If you want a practical implementation order, the next pass should be:

1. define the new world bible and rename map
2. rewrite the public-facing repo surface
3. rewrite the Act 1 and Act 2 setting anchors
4. decide the rules lane and build the whitelist or rename pass
5. mirror the same cleanup into `android_port`

