# Magic Points System Draft

Last updated: 2026-04-21

This document tracks the Magic Points, or MP, system for the Python DnD game. The MVP is now implemented in the main runtime, and the remaining notes below are both implementation reference and tuning guidance.

MP is now the player-facing combat spell resource. Existing spell-slot code remains as a compatibility shim during migration, but the combat menu asks one simple question: does the caster have enough MP to cast this spell?

## Current MVP Status

- `dnd_game/gameplay/magic_points.py` defines MP formulas, current spell costs, spend helpers, restore helpers, and spell-slot-restore-to-MP conversion.
- Character factories, level reconciliation, and old-save integrity paths synchronize MP.
- Combat menus show costs such as `Cast Fire Bolt (1 MP)` and hide spells that cannot currently be afforded.
- Spell resolution spends MP before the spell roll or saving throw; Divine Smite spends MP only after a weapon hit.
- Combatant summaries and party sheets show MP for casters.
- Long rests fully refill MP, short rests restore half MP for most casters, and warlocks refill all MP on short rest.
- Former spell-slot-refresh consumables currently restore `4 MP` per restore unit.

## Problem

- Before this MVP, cantrips such as `Fire Bolt`, `Sacred Flame`, `Produce Flame`, `Vicious Mockery`, and `Eldritch Blast` were repeatable every turn.
- Leveled spells already had slot plumbing in `dnd_game/gameplay/spell_slots.py`, but the player experience was split between free cantrips and limited spells.
- Repeated spell turns can crowd out weapon attacks, class resources, items, Dodge, Help, and tactical movement.
- The game needs spellcasting attrition that is easy to read in a text combat menu.

## Design Goals

- Every combat spell should have a consequence.
- Spellcasters should still feel good at their job, not punished for choosing a caster class.
- Cantrips should remain cheap baseline magic, but not literally free in combat.
- Martial classes should keep a clear reliability advantage when casters run low.
- Warlocks should keep a short-rest identity.
- The system should fit the existing `resources` and `max_resources` dictionaries on `Character`.
- The first implementation should be small enough to land without redesigning prepared spells, spell learning, or enemy archetypes.

## Non-Goals

- Exact tabletop spell-slot parity.
- Full BG3 spell preparation and spellbook behavior.
- Per-spell cooldowns for every spell.
- A separate stamina system for weapons and martial attacks.

## Core Rule

Every combat spell costs MP.

- Cantrips cost MP in combat.
- Leveled spells cost more MP based on spell rank and effect strength.
- If a caster does not have enough MP, the spell should be unavailable or clearly marked as unavailable.
- MP is spent after target confirmation, before the spell roll or saving throw.
- Reaction or rider spells spend MP at the moment their trigger is accepted.
- Divine Smite spends MP only after the weapon attack hits.
- Out-of-combat utility cantrips cost `0 MP` unless they replace a meaningful skill check, bypass a resource gate, or solve a scene problem that should carry cost.

## Terminology

Use `rank` for spell power tier in this adaptation.

| Term | Meaning |
| --- | --- |
| Cantrip | Rank 0 spell. Cheap combat magic. |
| Rank 1 spell | Current first-level spell equivalent. |
| Rank 2 spell | Current second-level spell equivalent. |
| Rank 3 spell | Current third-level spell equivalent. |
| Rank 4 spell | Current fourth-level spell equivalent for the level-8 roadmap. |
| MP | Magic Points available now. Stored as `resources["mp"]`. |
| Max MP | Character maximum. Stored as `max_resources["mp"]`. |

## MP Capacity

MP capacity should be derived from class, character level, and spellcasting ability modifier.

Current formulas:

```python
spell_mod = max(0, actor.ability_mod(actor.spellcasting_ability))

full_caster_mp = 6 + (4 * actor.level) + spell_mod
if actor.level < 2:
    half_caster_mp = 3 + spell_mod if has_feature_caster_access(actor) else 0
else:
    half_caster_mp = 4 + (2 * actor.level) + spell_mod
pact_caster_mp = 4 + (3 * actor.level) + spell_mod
feature_caster_mp = 3 + spell_mod
```

Class mapping:

| Caster type | Classes | Recovery identity |
| --- | --- | --- |
| Full caster | Bard, Cleric, Druid, Sorcerer, Wizard | Larger pool, partial short-rest recovery. |
| Half caster | Paladin, Ranger | Smaller pool, partial short-rest recovery from level 2 onward. Level-1 feature casting, such as Paladin Divine Smite, uses the feature-caster pool. |
| Pact caster | Warlock | Medium-low pool, strong short-rest recovery. |
| Feature caster | Magic Initiate, racial magic, story boons | Tiny pool unless a class also grants MP. |
| Non-caster | Barbarian, Fighter, Monk, Rogue | No MP by default. |

Reference values with a `+3` spellcasting modifier:

| Level | Full caster | Half caster | Pact caster |
| ---: | ---: | ---: | ---: |
| 1 | 13 | 0, or 6 with feature-caster access | 10 |
| 2 | 17 | 11 | 13 |
| 3 | 21 | 13 | 16 |
| 4 | 25 | 15 | 19 |
| 5 | 29 | 17 | 22 |
| 6 | 33 | 19 | 25 |
| 7 | 37 | 21 | 28 |
| 8 | 41 | 23 | 31 |

These values are intentionally flatter than a direct spell-slot conversion. Spell rank, action economy, class features, and spell effects should carry the power spikes.

## Spell Costs

Base cost table:

| Spell category | MP cost | Notes |
| --- | ---: | --- |
| Cantrip combat spell | 1 | Baseline spell attack, save cantrip, or combat debuff. |
| Rank 1 standard spell | 3 | Most single-target damage, healing, or simple control. |
| Rank 1 premium spell | 4 | Bonus-action healing, strong control, or high reliability. |
| Rank 1 auto-hit spell | 5 | Use for Magic Missile style reliability. |
| Rank 2 spell | 6 | Standard second-rank effects. |
| Rank 3 spell | 9 | Standard third-rank effects. |
| Rank 4 spell | 12 | Standard fourth-rank effects. |

Cost modifiers:

| Modifier | MP adjustment | Example use |
| --- | ---: | --- |
| Bonus-action spell | `+1` | Healing Word style action economy. |
| Auto-hit damage | `+1` or `+2` | Magic Missile. |
| Multi-target or area spell | `+1` to `+3` | Fireball-style damage or wide control. |
| Concentration spell | `+0` | Concentration is already a risk and opportunity cost. |
| No-save, no-roll control | `+2` | Hard control that cannot miss. |
| Ritual outside combat | `0` | Only when the scene allows time and safety. |

Initial costs for current player-facing spells:

| Spell or feature | Current user | MP cost | Notes |
| --- | --- | ---: | --- |
| Sacred Flame | Cleric | 1 | Cantrip, DEX save. |
| Produce Flame | Druid | 1 | Cantrip, ranged attack. |
| Vicious Mockery | Bard | 1 | Cantrip, WIS save plus light debuff. |
| Fire Bolt | Sorcerer, Wizard | 1 | Cantrip, ranged attack. |
| Eldritch Blast | Warlock | 1 | Cantrip, ranged attack. Future invocations may raise value but not base cost. |
| Cure Wounds | Bard, Cleric, Druid | 3 | Action heal. |
| Healing Word | Bard, Cleric, Druid | 4 | Bonus-action heal. |
| Magic Missile | Sorcerer, Wizard | 5 | Auto-hit damage. |
| Divine Smite | Paladin | 4 | Spend only after a hit. Current implementation rolls the base `2d8`; upcast tuning is future work. |
| Channel Divinity | Cleric | 0 | Uses `channel_divinity`, not MP. |
| Lay on Hands | Paladin | 0 | Uses `lay_on_hands`, not MP. |

## Upcasting

Upcasting spends the cost of the destination rank.

Examples:

- Cure Wounds as rank 1 costs `3 MP`.
- Cure Wounds upcast to rank 2 costs `6 MP`.
- Magic Missile as rank 1 costs `5 MP`.
- Magic Missile upcast to rank 2 should cost `7 MP` because it keeps auto-hit reliability.

Recommended rule:

- Use the destination rank's base cost.
- Reapply only the modifiers that still matter at that rank.
- Do not charge both base rank and destination rank.

## Turn Rules

Keep the current action economy shape.

- Action spells spend the action.
- Bonus-action spells spend the bonus action.
- A character can cast one ranked spell per turn.
- If a bonus-action ranked spell is cast, the action spell that same turn must be a cantrip.
- If an action ranked spell is cast, no bonus-action ranked spell can be cast that turn.
- Cantrips can be cast with available actions as long as the caster has MP.
- No passive MP regeneration happens during combat.

The MVP does not need spell cooldowns. MP is the primary consequence.

Optional anti-spam rule if cantrips still dominate after playtesting:

- Track the last combat spell id on each caster for the current encounter.
- If the same cantrip is cast on three consecutive turns by the same caster, the third and later consecutive casts cost `+1 MP`.
- Reset the streak when the caster casts a different spell, attacks with a weapon, uses an item, takes Dodge, helps an ally, or combat ends.

## Rest And Recovery

Long rest:

- Restore all MP for living party members.
- Reset any cantrip streak tracking.

Short rest:

- Full and half casters restore `ceil(max_mp * 0.50)`.
- Warlocks restore all MP.
- Feature casters restore `ceil(max_mp * 0.50)`, minimum `1 MP` when they have an MP pool.
- Recovery cannot exceed Max MP.
- Keep the existing limit of two short rests before the next long rest.

Class features:

| Feature | MP adaptation |
| --- | --- |
| Arcane Recovery | No extra MP in the MVP; the half-Max short-rest recovery already represents spellcasting focus returning. Revisit only if wizards feel too constrained. |
| Natural Recovery | No extra MP in the MVP; the half-Max short-rest recovery already represents spellcasting focus returning. Revisit only if druids feel too constrained. |
| Song of Rest | If implemented later, restore `proficiency_bonus` MP to each ally who recovers any MP from that short rest. |
| Sorcery Points | Keep separate at first. Later, allow conversion between Sorcery Points and MP. |
| Warlock Pact Magic | Model through pact-caster MP and full short-rest MP recovery. |

Consumables:

- Items that previously restored spell slots now restore MP instead.
- `spell_slot_restore: 1` currently maps to `4 MP` through `spell_slot_restore_units_to_mp`.
- Rare arcane refresh items can restore `8 to 12 MP`.
- Scrolls should normally not spend the reader's MP unless the scroll is designed as a focus amplifier instead of a consumable spell.

## Combat Menu And HUD

Player-facing text should make MP cost visible.

Examples:

- `Cast Fire Bolt (1 MP)`
- `Cast Magic Missile (5 MP)`
- `Cast Healing Word (4 MP, Bonus Action)`
- `Attack with Divine Smite (4 MP on hit)`

Current display:

- Combatant lines include the MP segment, for example `AC 13, MP 9/13`
- Journal party status: include MP after AC for spellcasters.
- Compact HUD: only show party-wide resource detail if it does not crowd the current layout.
- Spell unavailable message: `Elira needs 4 MP to cast Healing Word, but has 2 MP.`

Do not hide all caster options without explanation. If the menu renderer supports disabled options later, show unaffordable spells dimmed with their MP shortfall. Until then, hiding unaffordable spells is acceptable, but the status line should show low MP clearly.

## Enemy Spellcasting

Enemies should use the same cost language unless they are explicitly supernatural bosses.

- Basic caster enemies get MP from the same class or archetype formula.
- Enemy AI should check MP before choosing a spell.
- If an enemy caster lacks MP, it should use a weapon, Dodge, flee, or use a non-MP feature.
- Bosses can receive bonus MP through `max_resources["mp"]` if the encounter needs sustained magic.
- Scripted boss clocks can remain outside MP if they are environmental mechanics rather than normal spellcasting.

Recommended boss rule:

- If the spell is listed in the enemy's normal turn options, it costs MP.
- If the spell is a scene clock, ritual pulse, lair action, or phase transition, it does not cost MP but should have its own timing rule.

## Data Model

Use existing character resource dictionaries:

```python
actor.max_resources["mp"] = calculated_max_mp
actor.resources["mp"] = min(actor.resources.get("mp", calculated_max_mp), calculated_max_mp)
```

Current helper module:

- `dnd_game/gameplay/magic_points.py`

Current helper functions:

```python
def max_magic_points(actor) -> int:
    ...

def synchronize_magic_points(actor, *, refill: bool) -> int:
    ...

def has_magic_points(actor, cost: int) -> bool:
    ...

def spend_magic_points(actor, cost: int) -> bool:
    ...

def restore_magic_points(actor, amount: int) -> int:
    ...

def restore_all_magic_points(actor) -> int:
    ...

def restore_half_magic_points(actor) -> int:
    ...
```

Spell costs should live in data rather than inside every cast function.

Suggested shape:

```python
SPELL_MP_COSTS = {
    "sacred_flame": 1,
    "produce_flame": 1,
    "vicious_mockery": 1,
    "fire_bolt": 1,
    "eldritch_blast": 1,
    "cure_wounds": 3,
    "healing_word": 4,
    "magic_missile": 5,
    "divine_smite": 4,
}
```

## Source Touchpoints

| File | MVP status |
| --- | --- |
| `dnd_game/models.py` | No schema change required if MP uses `resources` and `max_resources`. |
| `dnd_game/gameplay/spell_slots.py` | Keep as compatibility during transition or replace with `magic_points.py`. |
| `dnd_game/gameplay/progression.py` | Synchronizes Max MP during level resource scaling. |
| `dnd_game/data/story/factories.py` | Initializes MP when characters and enemies are built. |
| `dnd_game/gameplay/combat_flow.py` | Shows spell options only when MP and action economy allow them; labels costs. |
| `dnd_game/gameplay/combat_resolution.py` | Spends MP in each implemented combat spell before resolution, with Divine Smite spending on hit. |
| `dnd_game/gameplay/inventory_core.py` | Restores MP on rests and converts spell-slot restoration consumables to MP restoration. |
| `dnd_game/gameplay/journal.py` | Shows MP in party status and character sheets. |
| `dnd_game/gameplay/io.py` | No compact HUD MP pass yet. |
| `tests/test_core.py` | Covers cost labels, MP creation, save reconciliation, recovery, consumables, and insufficient-MP casts. |

## Migration From Spell Slots

Migration path:

1. Done: add MP helpers while leaving `spell_slots.py` intact.
2. Done: initialize `mp` and `max_resources["mp"]` for all spellcasting characters.
3. Done: change combat spell functions to spend MP instead of spell slots.
4. Done: change spell-restoring items to restore MP.
5. In progress: keep old `spell_slots_*` values in saves harmlessly ignored for one release.
6. Future cleanup: after old saves are stable, remove or deprecate remaining compatibility-only spell-slot summaries.

For existing saves:

- If a caster has no `max_resources["mp"]`, calculate Max MP on load.
- For the first migration, refill MP to max. This avoids punishing old saves with an invented partial state.
- Leave `spell_slots_1`, `spell_slots_2`, and related keys untouched unless a dedicated save cleanup pass is added.

## Implementation Checklist

1. Done: create `dnd_game/gameplay/magic_points.py`.
2. Done: add spell cost constants for currently implemented spells.
3. Done: add MP synchronization to character creation and level reconciliation.
4. Done: update combat menus to show MP costs.
5. Done: update spell cast functions to spend MP.
6. Done: update Divine Smite to spend MP only after a hit.
7. Done for MVP: update short rest, long rest, Natural Recovery text, and consumables.
8. Done: update party status and combatant summaries.
9. Done: add tests for MP summary, insufficient MP, rest recovery, warlock recovery, consumables, and old-save reconciliation.
10. Still recommended: playtest at least one martial, one full caster, one healer, and one warlock through two consecutive encounters before tuning numbers.

## Test Cases

Minimum regression coverage:

- A wizard casting Fire Bolt loses `1 MP`.
- A cleric casting Sacred Flame loses `1 MP`.
- A bard casting Healing Word loses `4 MP` and spends the bonus action.
- A wizard with `4 MP` cannot cast Magic Missile if it costs `5 MP`.
- Magic Missile spends MP before damage resolution.
- Divine Smite spends MP only after the weapon hit lands.
- Long rest restores MP to Max MP.
- Short rest restores partial MP for full casters.
- Short rest restores all MP for warlocks.
- A non-caster has no MP row unless a feature grants one.
- Loading an old save without MP adds MP to spellcasters without crashing.

## Balance Examples

Level 1 wizard with `INT +3`:

- Max MP: `13`
- Fire Bolt: `1 MP`
- Magic Missile: `5 MP`
- The wizard can throw cantrips for a while, but every magical attack still drains the day.

Level 4 cleric with `WIS +3`:

- Max MP: `25`
- Sacred Flame: `1 MP`
- Cure Wounds: `3 MP`
- Healing Word: `4 MP`
- The cleric can heal actively, but bonus-action healing has a visible cost.

Level 4 warlock with `CHA +3`:

- Max MP: `19`
- Eldritch Blast: `1 MP`
- Short rest restores all MP.
- The warlock remains the most comfortable repeat caster across multiple encounters, but still has an in-combat meter.

Level 4 paladin with `CHA +2`:

- Max MP: `14`
- Divine Smite: `4 MP on hit`
- The paladin can spike damage several times, but cannot smite every hit forever.

## Tuning Notes

If casters feel too constrained:

- Increase full caster formula from `4 * level` to `5 * level`.
- Let full casters restore all MP on short rest only in low-rest campaign stretches.
- Reduce cantrip cost to `1 MP` only after the first cantrip each encounter.

If cantrip spam still dominates:

- Add the optional consecutive-cantrip surcharge.
- Reduce post-rest incidental MP restoration.
- Increase cantrip cost to `2 MP` only for enhanced cantrips with added riders.

If healing becomes too strong:

- Keep Cure Wounds at `3 MP`.
- Keep Healing Word at `4 MP`.
- Make multi-target healing cost rank base plus `+2`.
- Avoid free post-combat MP restoration.

If warlocks become too efficient:

- Lower pact caster formula to `3 + (2 * level) + spell_mod`.
- Restore only `ceil(max_mp * 0.75)` on short rest.
- Keep Eldritch Blast at `1 MP`; tune recovery before increasing its cost.

## Recommendation

Ship the MVP with:

- Cantrips at `1 MP`.
- Current leveled spell costs from the initial cost table.
- Full, half, and pact MP formulas above.
- No cooldowns.
- No passive in-combat MP regeneration.
- Short-rest recovery as listed.
- Clear menu labels showing MP costs.

This gives every spell a visible price while preserving the simple, readable combat loop the project already has.
