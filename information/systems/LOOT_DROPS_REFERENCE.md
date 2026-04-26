# Loot Drops Reference

This file explains how item drops work in the game. It covers enemy loot after combat, direct rewards from random or scripted encounters, and the safest way to add new drops.

## Quick Summary

Loot is driven by enemy archetype, not enemy display name.

When a combat encounter is won, the game awards guaranteed XP and gold from each defeated enemy, then rolls item drops from that enemy's loot table. Item drops are optional chance rolls. Gold is not part of the item loot table.

## Main Files

| Purpose | File |
| --- | --- |
| Item definitions, `LootEntry`, `LOOT_TABLES`, and drop rolling | `dnd_game/data/items/catalog.py` |
| Inventory handling, adding items, and collecting combat loot | `dnd_game/gameplay/inventory_core.py` |
| Combat victory reward flow | `dnd_game/gameplay/combat_flow.py` |
| Enemy archetypes, XP values, and gold values | `dnd_game/data/story/factories.py` |
| Direct random encounter rewards | `dnd_game/gameplay/random_encounters.py` |

## Combat Loot Flow

1. A combat encounter ends in victory.
2. `resolve_encounter_victory()` sums `xp_value` and `gold_value` from every defeated enemy.
3. The party receives that XP and gold through `reward_party()`.
4. `collect_loot()` loops over each defeated enemy.
5. Each enemy is passed to `roll_loot_for_enemy()`.
6. `roll_loot_for_enemy()` looks up `LOOT_TABLES[enemy.archetype]`.
7. Every `LootEntry` in that table rolls independently.
8. Successful item rolls choose a quantity between `minimum` and `maximum`.
9. All drops from the encounter are combined into totals.
10. `add_inventory_item()` adds the items to shared inventory.

## How To Read `LootEntry`

```python
LootEntry("potion_healing", 0.35)
```

This means the enemy has a 35% chance to drop 1 healing potion.

```python
LootEntry("miners_ration_tin", 0.75, 1, 2)
```

This means the enemy has a 75% chance to drop either 1 or 2 miner's ration tins.

```python
LootEntry("spiced_sausage", 1.0, 2, 3)
```

This means the enemy always drops 2 to 3 spiced sausages.

## Important Behavior

- Drop rolls are independent. A single enemy can drop multiple items from the same table.
- Tables are not weighted choice lists. The game does not pick only one item.
- Each copy of an enemy rolls separately. Three `goblin` enemies roll the `goblin` table three times.
- Item IDs are resolved through `resolve_item_id()`, so legacy aliases can still map to current item IDs.
- If an enemy archetype has no entry in `LOOT_TABLES`, that enemy drops no items.
- The journal records successfully looted items that were added to shared inventory.

## XP And Gold

Enemy XP and gold come from the enemy template in `create_enemy()`.

Example fields:

```python
xp_value=175
gold_value=14
archetype="false_map_skirmisher"
```

The `archetype` controls item drops. `xp_value` and `gold_value` are guaranteed combat rewards on victory.

This means an enemy can:

- Award gold but no item loot.
- Drop item loot but have no gold.
- Award both gold and item loot.
- Award neither, if both values and the loot table are empty.

## Direct Encounter Rewards

Some non-combat or post-combat rewards do not use `LOOT_TABLES`.

Random encounter choices can call:

```python
grant_random_encounter_rewards(
    reason="the fern-hidden chest",
    gold=9,
    items={"potion_healing": 1, "bread_round": 1},
)
```

Those rewards are direct grants. They still use `add_inventory_item()`, but they do not roll enemy loot tables.

Scripted story rewards often call `add_inventory_item()` directly for the same reason.

## Act 2 Loot Shape

Act 2 loot leans into the act theme of controlled truth, corrupted records, resonance, delving, and dangerous knowledge.

Common Act 2 drops include:

- `resonance_tonic`
- `thoughtward_draught`
- `scroll_clarity`
- `scroll_lesser_restoration`
- `scroll_guardian_light`
- `delvers_amber`
- `miners_ration_tin`
- `mushroom_broth_flask`
- `fireward_elixir`

Uncommon and rare Act 2 equipment drops include:

- `choirward_amulet_uncommon`
- `choirward_amulet_rare`
- `sigil_anchor_ring_rare`
- `delver_lantern_hood_uncommon`
- `forgehand_gauntlets_uncommon`
- `forgehand_gauntlets_rare`
- `chain_mail_uncommon`
- `chain_mail_rare`
- `breastplate_rare`

## Adding A New Enemy Loot Table

1. Confirm the enemy's `archetype` in `dnd_game/data/story/factories.py`.
2. Add a matching key to `LOOT_TABLES` in `dnd_game/data/items/catalog.py`.
3. Use existing item IDs from `ITEMS`; add the item first if it does not exist.
4. Keep routine consumables in the 15% to 80% range.
5. Keep uncommon equipment in the 7% to 18% range for normal enemies.
6. Keep rare equipment very low on normal enemies, usually 3% to 12%.
7. Use `1.0` only for items that should always drop.
8. Add tests if the enemy is important to a new act, boss, or encounter suite.

## Balance Notes

Enemy loot should support the region's economy and survival pressure without replacing merchants or quest rewards.

Small enemies should usually drop supplies, common consumables, or low-chance gear. Elite enemies can carry uncommon gear and stronger consumables. Bosses can justify rare gear, scrolls, and stronger healing, but even boss tables usually keep the best equipment chance-based unless the story needs a guaranteed reward.

For Act 2 specifically, good loot tables should make players feel they are scavenging corrupted expedition gear, legal/ritual instruments, resonance tools, and protective countermeasures rather than generic wilderness loot.
