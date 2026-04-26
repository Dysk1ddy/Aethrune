# Quest System Reference

This file documents the current quest implementation for reading, balancing, debugging, and adding new quests.

## Scope

- Current quest count: 20
- Quest data lives in `dnd_game/data/quests/`
- Quest runtime behavior lives in `dnd_game/gameplay/quests.py`
- Quest state is saved on `GameState.quests`
- Rewards are paid only when a ready quest is turned in to its original giver
- Quest rewards can now include XP, gold, items, story unlock flags, merchant attitude changes, and Act 2 campaign metric shifts

## Source Map

| File | Role |
| --- | --- |
| `dnd_game/data/quests/schema.py` | Dataclasses for `QuestDefinition`, `QuestReward`, and `QuestLogEntry`. |
| `dnd_game/data/quests/act1.py` | Act 1 quest definitions. |
| `dnd_game/data/quests/act2.py` | Act 2 quest definitions. |
| `dnd_game/data/quests/__init__.py` | Combines Act 1 and Act 2 quest maps into `QUESTS` and `QUEST_ORDER`. |
| `dnd_game/gameplay/quests.py` | Runtime quest log, status refresh, quest grant, reward summary, and turn-in behavior. |
| `dnd_game/models.py` | `GameState.quests` stores active save data. |
| `dnd_game/gameplay/story_intro.py` | Neverwinter briefing scenes, Oren Vale's contract house hub, `False Manifest Circuit`, and the upstairs private-room reward scene. |
| `dnd_game/gameplay/story_town_hub.py` | Steward Tessa Harrow flow, Stonehill inn NPC scenes, inn quest grant and turn-in flow, the upstairs quiet-room intel scene, and the Stonehill barfight resolution scene. |
| `dnd_game/gameplay/story_town_services.py` | Barthen, Elira shrine, and Linene service scenes. |
| `dnd_game/gameplay/story_act1_expanded.py` | Halia and Daran Act 1 quest scenes. |
| `dnd_game/gameplay/map_system.py` | Map-driven completion flags, Blackwake turn-in, Ashfall/Emberhall route consequence hooks, and companion personal quest resolution. |
| `dnd_game/gameplay/story_act2_scaffold.py` | Act 2 quest grants, original-giver report flow, Act 2 metric rewards, and turn-in dialogue. |
| `dnd_game/data/items/catalog.py` | Item catalog entries used by quest rewards. |
| `information/catalogs/ITEM_CATALOG.md` | Generated catalog reference for quest reward items. |
| `tests/test_core.py` | Regression tests for quest turn-ins, rewards, catalog validity, and Act 2 carryover benefits. |

## Data Model

### QuestDefinition

`QuestDefinition` is the static source of truth for a quest. It is not saved directly into save files; saves store lightweight `QuestLogEntry` records keyed by quest id, then runtime code looks up the definition from `QUESTS`.

| Field | Meaning |
| --- | --- |
| `quest_id` | Stable id used in saves, flags, tests, and code. Do not rename after release unless migration code is added. |
| `title` | Player-facing quest title. |
| `giver` | Exact original quest giver name. Turn-in enforcement compares against this string. |
| `location` | Player-facing source or turn-in location. |
| `summary` | Longer quest-log style context. |
| `objective` | Current actionable goal shown when the quest is granted. |
| `turn_in` | Player-facing instruction for where the reward is claimed. |
| `completion_flags` | Tuple of state flags that must all be truthy before the quest becomes ready. |
| `reward` | `QuestReward` payload applied only at turn-in. |
| `accepted_text` | Note and grant text when the quest is accepted. |
| `ready_text` | Note and announcement text when completion flags mark the quest ready. |
| `turn_in_text` | Text shown and stored when the quest is completed. |

Important behavior: `completion_flags` uses `all(...)`. An empty tuple is immediately complete after grant, so use an empty tuple only for intentionally instant turn-in quests.

### QuestReward

`QuestReward` describes every reward paid by `turn_in_quest()`.

| Field | Meaning |
| --- | --- |
| `xp` | Shared party XP. Paid through `reward_party()`, which can trigger level-ups. |
| `gold` | Shared party gold. Paid through `reward_party()`. |
| `items` | `{item_id: quantity}` added through `add_inventory_item()`. Every id must exist in `ITEMS`. |
| `flags` | `{flag_name: value}` written directly to `state.flags`. Used for durable story unlocks. |
| `merchant_attitudes` | `{merchant_id: delta}` applied through `adjust_merchant_attitude()`. |
| `act2_metrics` | `{metric_key: delta}` applied through `act2_shift_metric()` when available. |

Reward serialization helpers exist on the dataclass, but static definitions are currently loaded from Python source. Save files do not duplicate the reward payload.

### QuestLogEntry

`QuestLogEntry` is the save-facing state for a quest.

| Field | Meaning |
| --- | --- |
| `quest_id` | Link back to `QUESTS[quest_id]`. |
| `status` | One of `active`, `ready_to_turn_in`, or `completed`. |
| `notes` | Player-facing quest notes accumulated from accepted, ready, and turn-in text. |

## Registry And Ordering

`dnd_game/data/quests/__init__.py` builds the live registry like this:

```python
QUESTS = dict(ACT_1_QUESTS)
QUESTS.update(ACT_2_QUESTS)
QUEST_ORDER = tuple(QUESTS)
```

This means:

- Act 1 quests are inserted first.
- Act 2 quests are appended after Act 1.
- Duplicate ids in Act 2 would overwrite Act 1 definitions, so quest ids must be globally unique.
- `QUEST_ORDER` controls deterministic iteration for status refreshes and quest status lists.

## Lifecycle

The quest lifecycle has four practical states:

| State | Where it lives | Meaning |
| --- | --- | --- |
| Not in log | Missing from `state.quests` | The player has not accepted or unlocked it. |
| `active` | `QuestLogEntry.status` | The quest is accepted but its completion flags are not all true. |
| `ready_to_turn_in` | `QuestLogEntry.status` | The completion flags are true and the player must report to the original giver. |
| `completed` | `QuestLogEntry.status` | Rewards have been paid and the quest no longer refreshes. |

### Grant

Use `grant_quest(quest_id, note="")`.

Grant flow:

1. If the quest already exists, only the optional note is appended.
2. If the quest is new, a `QuestLogEntry(status="active")` is added.
3. The quest's `accepted_text` and optional note are appended to the quest notes.
4. `Quest accepted: ...` is added to the journal.
5. The rich quest panel is rendered when rich UI is available; otherwise plain text is shown.
6. `refresh_quest_statuses(announce=False)` runs immediately, so a quest whose completion flags are already true can become `ready_to_turn_in` right away.

Common grant locations:

- Town NPC dialogue scenes grant town quests.
- Companion trust checks grant personal quests.
- Act 2 route scenes grant route-specific quests.
- The Blackwake branch can grant `trace_blackwake_cell` during the Neverwinter departure fork.

### Refresh

Use `refresh_quest_statuses(announce=True)`.

Refresh behavior:

1. Iterate through `QUEST_ORDER`.
2. Skip missing quests.
3. Skip completed quests.
4. Read the static definition.
5. Check `quest_objective_met(quest_id)`.
6. If all completion flags are true, change `active` to `ready_to_turn_in`.
7. Append the quest's `ready_text` to quest notes.
8. Add `Quest updated: ... is ready to turn in.` to the journal.
9. If `announce=True`, also print the update and ready text.
10. If the flags are no longer true and the quest was ready, move it back to `active`.

Refresh runs from multiple surfaces, including state integrity checks, journal display, map completion paths, and turn-in attempts. Completion flags are still the source of truth until the quest is completed.

### Turn-In

Use `turn_in_quest(quest_id, *, giver="Exact Giver Name")`.

Turn-in behavior:

1. Refresh quest statuses with `announce=False`.
2. Refuse if the quest is missing.
3. Refuse if the quest is not `ready_to_turn_in`.
4. Look up the quest definition.
5. Refuse if the provided `giver` does not exactly match `definition.giver`.
6. Mark the quest `completed`.
7. Append `turn_in_text` to quest notes.
8. Add `Quest completed: ...` to the journal.
9. Show the turn-in text.
10. Pay XP and gold through `reward_party()`.
11. Add item rewards through `add_inventory_item()`.
12. Apply story flags, merchant attitude rewards, and Act 2 metric rewards.

The original-giver rule is intentional. Completing an objective only moves the quest to `ready_to_turn_in`; rewards are withheld until the player returns to the quest giver. Backtracking and hub reports are therefore part of the reward loop.

Wrong-giver behavior:

```text
<Quest Title> has to be turned in to <Original Giver>.
```

No rewards are paid on a wrong-giver attempt.

## Reward Application Details

### XP And Gold

XP and gold are paid through `reward_party(xp=..., gold=..., reason=definition.title)`.

Effects:

- Adds shared XP to `state.xp`.
- Adds shared gold to `state.gold`.
- Prints a reward line.
- Prints XP progress.
- Adds a journal reward entry.
- Calls `resolve_level_ups()`.

Because quest XP can trigger level-up choices, tests that turn in high-value quests may need deterministic input for level-up prompts if the party crosses a threshold.

### Items

Items are added through `add_inventory_item(item_id, quantity, source=definition.giver)`.

Effects:

- Looks up the item in `ITEMS`.
- Adds items to shared inventory.
- Prints an add line for successfully added items.
- Adds a quest reward journal line listing successfully received items.

Maintenance rule: every quest reward item id must exist in `dnd_game/data/items/catalog.py`. After adding catalog items, regenerate `information/catalogs/ITEM_CATALOG.md`.

### Story Unlock Flags

`reward.flags` writes durable benefits into `state.flags`.

Current naming convention:

- Use `quest_reward_...` for flags granted by quest reward turn-ins.
- Keep names descriptive, for example `quest_reward_lionshield_logistics`.
- These flags are a clean hook for later story branches, discounts, route shortcuts, social leverage, and Act 3 handoff state.

The reward UI labels strip prefixes such as `quest_reward_`, `act2_`, and `act3_` when printing a short unlock line.

### Merchant Attitudes

`reward.merchant_attitudes` applies attitude deltas through `adjust_merchant_attitude()`.

Current merchant ids:

- `barthen_provisions`
- `linene_graywind`

Merchant attitude affects trade through `buy_price_multiplier()` and `sell_price_multiplier()`. Higher attitude means better prices.

### Act 2 Metrics

`reward.act2_metrics` applies deltas to Act 2 campaign metrics:

- `act2_town_stability`
- `act2_route_control`
- `act2_whisper_pressure`

When `act2_shift_metric()` exists, rewards use that helper so metric bounds, labels, and narration stay consistent. If the helper is not available, the quest system falls back to directly adding the delta to the flag.

Positive `act2_town_stability` and `act2_route_control` are beneficial. Negative `act2_whisper_pressure` is beneficial.

## Current Quest Catalog

| Quest id | Title | Giver | Completion flags | Reward highlights |
| --- | --- | --- | --- | --- |
| `trace_blackwake_cell` | Embers Before the Road | Mira Thann | `blackwake_completed` | 90 XP, 35 gp, `miras_blackwake_seal`, `scroll_ember_ward`, Blackwake watch backing flag. |
| `secure_miners_road` | Stop the Watchtower Raids | Steward Tessa Harrow | `ashfall_watch_cleared` | 100 XP, 50 gp, `roadwarden_cloak`, supplies, miners-road-open flag. |
| `restore_barthen_supplies` | Keep the Shelves Full | Barthen | `ashfall_watch_cleared` | 75 XP, 35 gp, `barthen_resupply_token`, food, Barthen attitude boost, resupply-credit flag. |
| `reopen_lionshield_trade` | Reopen the Trade Lane | Linene Graywind | `ashfall_watch_cleared` | 85 XP, 45 gp, `lionshield_quartermaster_badge`, potions, Linene attitude boost, logistics flag. |
| `marked_keg_investigation` | The Marked Keg | Mara Stonehill | `marked_keg_resolved` | 70 XP, 24 gp, `innkeeper_credit_token`, Stonehill common-room-welcome flag. |
| `songs_for_the_missing` | Songs for the Missing | Sella Quill | `songs_for_missing_jerek_detail`, `songs_for_missing_tam_detail`, `songs_for_missing_nera_detail` | 65 XP, 18 gp, `sella_ballad_token`, names-carried flag. |
| `quiet_table_sharp_knives` | Quiet Table, Sharp Knives | Nera Doss | `quiet_table_knives_resolved` | 80 XP, 28 gp, `blackseal_taster_pin`, quiet-room-access flag. |
| `find_dain_harl` | Bring Back Dain's Name | Jerek Harl | `dain_harl_truth_found` | 85 XP, 26 gp, `harl_road_knot`, Jerek road-knot flag. |
| `false_manifest_circuit` | False Manifest Circuit | Sabra Kestrel | `false_manifest_oren_detail`, `false_manifest_vessa_detail`, `false_manifest_garren_detail` | 75 XP, 24 gp, `kestrel_ledger_clasp`, Neverwinter private-room access flag. |
| `silence_old_owl_well` | Silence Old Owl Well | Halia Thornton | `old_owl_well_cleared` | 100 XP, 45 gp, `gravequiet_amulet`, scroll and salve, gravequiet contacts flag. |
| `break_wyvern_tor_raiders` | Break the Wyvern Tor Raiders | Daran Edermath | `wyvern_tor_cleared` | 100 XP, 40 gp, `edermath_scout_buckle`, healing draught, scout-network flag. |
| `bryn_loose_ends` | Loose Ends | Bryn Underbough | `bryn_loose_ends_resolved` | 80 XP, 25 gp, `bryns_cache_keyring`, `dust_of_disappearance`, underworld-favor flag. |
| `elira_faith_under_ash` | Faith Under Ash | Elira Dawnmantle | `elira_faith_under_ash_resolved` | 80 XP, 20 gp, `dawnmantle_mercy_charm`, `blessed_salve`, mercy-blessing flag. |
| `recover_pact_waymap` | Recover the Pact Waymap | Halia Thornton | `agatha_truth_secured`, `wave_echo_reached` | 140 XP, 75 gp, `pact_waymap_case`, resonance tonics, route-control boost. |
| `seek_agathas_truth` | Ask the Banshee What Was Buried | Elira Dawnmantle | `agatha_truth_secured` | 130 XP, 40 gp, `agathas_truth_lantern`, `scroll_quell_the_deep`, whisper-pressure reduction. |
| `rescue_stonehollow_scholars` | Bring Back the Survey Team | Linene Graywind | `stonehollow_dig_cleared` | 140 XP, 70 gp, `stonehollow_survey_lantern`, rations, Linene attitude boost, town and route boosts. |
| `cut_woodland_saboteurs` | Break the Woodland Saboteurs | Daran Edermath | `woodland_survey_cleared` | 140 XP, 65 gp, `woodland_wayfinder_boots`, `delvers_amber`, route-control boost. |
| `hold_the_claims_meet` | Hold the Claims Meeting Together | Linene Graywind | `claims_meet_held`, `phandalin_sabotage_resolved` | 120 XP, 75 gp, `claims_accord_brooch`, Linene attitude boost, major town-stability boost. |
| `free_wave_echo_captives` | Free the South Adit Prisoners | Elira Dawnmantle | `south_adit_cleared` | 160 XP, 80 gp, `freed_captive_prayer_beads`, scrolls, town boost and whisper reduction. |
| `sever_quiet_choir` | Sever the Quiet Choir | Town Council | `caldra_defeated` | 250 XP, 150 gp, `forgeheart_cinder`, forge consumables, town and route boosts, major whisper reduction. |

## Act 1 Reward Carryover Into Act 2

Act 1 reward and callback flags influence Act 2 starting metrics in `act2_initialize_metrics()`.

| Reward or callback flag | Act 2 effect |
| --- | --- |
| `quest_reward_blackwake_watch_backing` | +1 town stability, +1 route control. |
| `quest_reward_miners_road_open` | +1 town stability, +1 route control. |
| `quest_reward_barthen_resupply_credit` | +1 town stability. |
| `quest_reward_lionshield_logistics` | +1 route control. |
| `quest_reward_gravequiet_contacts` | -1 whisper pressure. |
| `quest_reward_edermath_scout_network` | +1 route control. |
| `act2_edermath_cache_routework` | +1 route control from Daran's old adventurer's cache; Act 2 status text can mention the quiet orchard-to-highland control line. |
| `quest_reward_bryn_underworld_favor` | +1 route control. |
| `quest_reward_elira_mercy_blessing` | +1 town stability, -1 whisper pressure. |
| `neverwinter_contract_house_political_callback` | +1 route control, Act 2 witness-pressure status text, and claims-council dialogue from Oren, Sabra, Vessa, and Garren. |

These are the main current examples of quest rewards and connected report callbacks unlocking beneficial options further down the story.

## Turn-In Integration Points

Current turn-in scenes call `turn_in_quest()` with an explicit original giver.

| Quest | Turn-in integration |
| --- | --- |
| `trace_blackwake_cell` | Blackwake backtrack/report path in `map_system.py`, giver `Mira Thann`. |
| `secure_miners_road` | Steward's Hall in `story_town_hub.py`, giver `Steward Tessa Harrow`. |
| `restore_barthen_supplies` | Barthen's Provisions in `story_town_services.py`, giver `Barthen`. |
| `reopen_lionshield_trade` | Lionshield Coster in `story_town_services.py`, giver `Linene Graywind`. |
| `find_dain_harl` | Stonehill Inn in `story_town_hub.py`, giver `Jerek Harl`. |
| `false_manifest_circuit` | Oren Vale's contract house in `story_intro.py`, giver `Sabra Kestrel`. |
| `silence_old_owl_well` | Miner's Exchange in `story_act1_expanded.py`, giver `Halia Thornton`. |
| `break_wyvern_tor_raiders` | Edermath Orchard in `story_act1_expanded.py`, giver `Daran Edermath`. |
| `bryn_loose_ends` | Bryn's personal quest resolution in `map_system.py`, giver `Bryn Underbough`. |
| `elira_faith_under_ash` | Elira's personal quest resolution in `map_system.py`, giver `Elira Dawnmantle`. |
| Act 2 route quests | `run_act2_council_turnins()` lists each ready quest by original giver and turns in only the selected report. |

Act 2 uses the expedition hub as the practical report surface, but the UI is still framed as reporting to the original giver. It no longer bulk-completes all ready quests at once.

## Adding A New Quest

Use this checklist.

1. Add the definition to `dnd_game/data/quests/act1.py` or `dnd_game/data/quests/act2.py`.
2. Pick a stable `quest_id` in snake case.
3. Set the exact `giver` string that turn-in code will pass.
4. Add one or more `completion_flags`.
5. Make sure scene code sets those flags when the objective is actually complete.
6. Fill in `accepted_text`, `ready_text`, and `turn_in_text`.
7. Add a meaningful `QuestReward`.
8. If rewarding a new item, add it to `dnd_game/data/items/catalog.py`.
9. Regenerate `information/catalogs/ITEM_CATALOG.md`.
10. Add a grant path with `grant_quest()`.
11. Add a turn-in path with `turn_in_quest(quest_id, giver="...")`.
12. Add or update tests in `tests/test_core.py`.

Recommended reward design:

- Give enough XP/gold that the turn-in feels materially different from incidental combat loot.
- Prefer at least one distinctive item for story quests.
- Use `flags` for downstream story leverage.
- Use `merchant_attitudes` when the giver is tied to a trade surface.
- Use `act2_metrics` for Act 2 campaign consequence quests.
- Keep item rewards useful but not mandatory for progression.

## Testing Expectations

Minimum coverage for quest changes:

- The quest becomes `ready_to_turn_in` only after its completion flags are true.
- Wrong-giver turn-in returns false and pays no rewards.
- Correct-giver turn-in marks the quest completed.
- XP, gold, and item rewards appear as expected.
- Reward flags are set only after turn-in.
- Merchant attitude rewards apply once.
- Act 2 metric rewards shift the correct metric.
- Every item id in every `QuestReward.items` exists in `ITEMS`.

Current relevant tests include:

- `test_turning_in_quest_grants_rewards`
- `test_quest_rewards_require_original_giver`
- `test_act2_turnins_are_selected_by_original_giver`
- `test_quest_reward_items_are_cataloged`
- `test_act1_reward_unlocks_improve_act2_starting_position`

## Common Gotchas

- `giver` matching is exact. If the definition says `Linene Graywind`, the call must pass `giver="Linene Graywind"`.
- A ready quest is not completed until `turn_in_quest()` succeeds.
- Empty `completion_flags` means immediately ready after grant.
- Completed quests do not reopen if flags later change.
- Item reward ids are looked up at runtime. A typo can break quest panels or turn-ins.
- Reward flags should be durable and descriptive because later story code will read them from saves.
- Avoid paying merchant attitude manually in a scene if the quest reward already does it.
- Avoid bulk turn-ins unless the UI still requires the player to choose the original giver report.

## Maintenance Commands

Run the core suite after quest changes:

```bash
python -m pytest tests/test_core.py
```

Regenerate the item catalog after adding or changing reward items:

```bash
python -c "from pathlib import Path; from dnd_game.data.items.catalog import write_item_catalog; write_item_catalog(Path('information/catalogs/ITEM_CATALOG.md'))"
```

If the root-level generated catalog is still being kept during the docs migration, regenerate it too:

```bash
python -c "from pathlib import Path; from dnd_game.data.items.catalog import write_item_catalog; write_item_catalog(Path('ITEM_CATALOG.md'))"
```
