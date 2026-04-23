# Progression Cleanup Reference

Last updated: 2026-04-23

This file replaces the older level-1-to-8 draft that leaned on external progression summaries. Keep this as a compact implementation note for Aethrune.

## Live State

- Current runtime level cap: 4.
- Source of truth: `dnd_game/gameplay/constants.py`.
- Progression flow: `dnd_game/gameplay/progression.py`.
- Class level additions: `dnd_game/data/story/character_options/classes.py`.
- Party XP is shared across the roster.
- New companions should be synchronized to the party level when recruited.

Current thresholds:

| Level | Total XP |
| --- | ---: |
| 1 | 0 |
| 2 | 300 |
| 3 | 900 |
| 4 | 2700 |

## Design Goals

- Keep progression readable in a text adventure.
- Make level-ups meaningful without importing unused tabletop or video-game build catalogs.
- Preserve the existing shared-party XP model.
- Let companion auto-scaling use small templates instead of full manual build screens.
- Prefer Aethrune-facing labels for resources, abilities, and feature descriptions.

## Keep

- Existing level-up loop and threshold checks.
- Current HP, MP/channel reserve, feature, and resource synchronization helpers.
- The Act II level-4 test snapshot tooling.
- Class identities as internal mechanical keys until the public class redesign pass is ready.

## Remove From Future Drafts

- Long official progression tables that are not implemented.
- External subclass, spell, or feat comparison text.
- Rulebook-style spell lists.
- Source-lore explanations that do not affect this game's code.

## Next Progression Pass

1. Decide whether the next cap is 5 or 8.
2. Add only the features and resource changes needed for that cap.
3. Give each companion a small auto-build template for missed levels.
4. Add tests for threshold crossing, companion catch-up, resource refill, and public feature labels.
