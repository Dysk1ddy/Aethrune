from __future__ import annotations

from typing import Any

from ..content import create_enemy, create_irielle_ashwake, create_nim_ardentglass
from ..drafts.map_system import ACT1_HYBRID_MAP, ACT2_ENEMY_DRIVEN_MAP
from ..drafts.map_system.runtime import (
    DraftMapState,
    DungeonMap,
    DungeonRoom,
    build_act2_pressure_panel,
    build_act2_pressure_panel_text,
    build_dungeon_panel,
    build_dungeon_panel_text,
    build_overworld_panel,
    build_overworld_panel_text,
    current_room_exits,
    requirement_met,
    room_direction,
    room_exit_directions,
    room_precise_direction,
)
from ..ui.rich_render import Group, RICH_AVAILABLE
from .encounter import Encounter


def _requirement_flag_names(*, requirement) -> set[str]:
    names = {
        *requirement.all_flags,
        *requirement.any_flags,
        *requirement.blocked_flags,
    }
    for flag_count in requirement.flag_count_requirements:
        names.update(flag_count.flags)
    for flag_value in requirement.flag_value_requirements:
        names.add(flag_value.flag_name)
    for numeric_flag in requirement.numeric_flag_requirements:
        names.add(numeric_flag.flag_name)
    return names


def _collect_blueprint_flag_names(blueprint) -> set[str]:
    flag_names: set[str] = set()
    for node in blueprint.nodes.values():
        flag_names.update(_requirement_flag_names(requirement=node.requirement))
    for edge in blueprint.edges:
        flag_names.update(_requirement_flag_names(requirement=edge.requirement))
    for beat in blueprint.story_beats:
        flag_names.update(_requirement_flag_names(requirement=beat.requirement))
        flag_names.update(beat.grants_flags)
    for dungeon in blueprint.dungeons.values():
        flag_names.update(dungeon.completion_flags)
        for room in dungeon.rooms.values():
            flag_names.update(_requirement_flag_names(requirement=room.requirement))
            flag_names.update(room.clear_grants_flags)
    return flag_names


ACT1_MAP_FLAG_NAMES = _collect_blueprint_flag_names(ACT1_HYBRID_MAP)
ACT2_MAP_FLAG_NAMES = _collect_blueprint_flag_names(ACT2_ENEMY_DRIVEN_MAP)
ACT1_SCENE_TO_NODE_ID = {node.scene_key: node_id for node_id, node in ACT1_HYBRID_MAP.nodes.items()}
ACT2_SCENE_TO_NODE_ID = {node.scene_key: node_id for node_id, node in ACT2_ENEMY_DRIVEN_MAP.nodes.items()}
ACT1_HIGH_ROAD_SIDE_BRANCH_NODE_IDS = {"liars_circle", "false_checkpoint", "false_tollstones"}
DUNGEON_DIRECTION_ORDER = {
    "NORTH": 0,
    "EAST": 2,
    "SOUTH": 4,
    "WEST": 6,
    "HERE": 8,
}


def _dungeon_direction_sort_key(direction: str) -> tuple[int, ...]:
    return tuple(DUNGEON_DIRECTION_ORDER.get(part, 99) for part in direction.split("-"))


def _room_target_sort_key(from_room: DungeonRoom, to_room: DungeonRoom, direction: str) -> tuple[int, tuple[int, ...]]:
    dx = to_room.x - from_room.x
    dy = to_room.y - from_room.y
    if dy < 0:
        primary = DUNGEON_DIRECTION_ORDER["NORTH"]
    elif dy > 0:
        primary = DUNGEON_DIRECTION_ORDER["SOUTH"]
    elif dx > 0:
        primary = DUNGEON_DIRECTION_ORDER["EAST"]
    elif dx < 0:
        primary = DUNGEON_DIRECTION_ORDER["WEST"]
    else:
        primary = DUNGEON_DIRECTION_ORDER["HERE"]
    return (primary, _dungeon_direction_sort_key(direction))


class MapSystemMixin:
    MAP_STATE_KEY = "map_state"
    ACT2_MAP_STATE_KEY = "act2_map_state"
    ACT1_METRIC_NAMES = {
        "act1_town_fear": "Town Fear",
        "act1_ashen_strength": "Ashen Strength",
        "act1_survivors_saved": "Survivors Saved",
    }
    ACT1_METRIC_LIMITS = {
        "act1_town_fear": 5,
        "act1_ashen_strength": 5,
    }
    ACT1_METRIC_LABELS = {
        "act1_town_fear": ("Steady", "Wary", "Rattled", "Afraid", "Panicked", "Breaking"),
        "act1_ashen_strength": ("Broken", "Shaken", "Pressed", "Active", "Entrenched", "Dominant"),
    }

    def act1_initialize_metrics(self) -> None:
        assert self.state is not None
        defaults = {
            "act1_town_fear": 2,
            "act1_ashen_strength": 3,
            "act1_survivors_saved": 0,
        }
        for metric_key, default_value in defaults.items():
            value = self.state.flags.get(metric_key)
            if isinstance(value, bool) or not isinstance(value, int | float):
                self.state.flags[metric_key] = default_value

    def act1_metric_value(self, metric_key: str) -> int:
        assert self.state is not None
        self.act1_initialize_metrics()
        value = self.state.flags.get(metric_key, 0)
        if isinstance(value, bool) or not isinstance(value, int | float):
            return 0
        return int(value)

    def act1_adjust_metric(self, metric_key: str, delta: int) -> int:
        assert self.state is not None
        current = self.act1_metric_value(metric_key)
        updated = current + delta
        limit = self.ACT1_METRIC_LIMITS.get(metric_key)
        if limit is None:
            updated = max(0, updated)
        else:
            updated = max(0, min(limit, updated))
        self.state.flags[metric_key] = updated
        return updated

    def can_visit_cinderfall_ruins(self) -> bool:
        assert self.state is not None
        return bool(self.state.flags.get("hidden_route_unlocked") or self.state.flags.get("cinderfall_ruins_cleared"))

    def unlock_act1_hidden_route(self, reveal_text: str) -> bool:
        assert self.state is not None
        if self.state.flags.get("hidden_route_unlocked"):
            return False
        self.state.flags["hidden_route_unlocked"] = True
        self.add_journal("A hidden route through Cinderfall Ruins can be used before the Ashfall assault.")
        self.say(reveal_text)
        self._clear_map_view_cache("overworld")
        return True

    def act1_relay_sabotaged(self) -> bool:
        assert self.state is not None
        return (
            bool(self.state.flags.get("cinderfall_relay_destroyed"))
            or bool(self.state.flags.get("blackwake_cache_sabotaged"))
            or self.act1_metric_value("act1_ashen_strength") <= 0
        )

    def active_companion_by_id(self, companion_id: str, *, minimum_disposition: int = -99):
        assert self.state is not None
        for companion in self.state.companions:
            if companion.dead or companion.companion_id != companion_id:
                continue
            if companion.disposition >= minimum_disposition:
                return companion
        return None

    def any_companion_by_id(self, companion_id: str, *, minimum_disposition: int = -99):
        assert self.state is not None
        seen_ids: set[int] = set()
        for companion in [*self.state.companions, *self.state.camp_companions]:
            if id(companion) in seen_ids or companion.dead or companion.companion_id != companion_id:
                continue
            seen_ids.add(id(companion))
            if companion.disposition >= minimum_disposition:
                return companion
        return None

    def maybe_offer_act1_personal_quests(self) -> None:
        assert self.state is not None
        if self.state.current_act >= 2:
            return
        bryn = self.any_companion_by_id("bryn_underbough", minimum_disposition=3)
        if bryn is not None and not self.has_quest("bryn_loose_ends") and not self.quest_is_completed("bryn_loose_ends"):
            self.grant_quest(
                "bryn_loose_ends",
                note="Bryn thinks one of her old smuggler caches is being folded into the Ashen Brand's back-road trade.",
            )
        elira = self.any_companion_by_id("elira_dawnmantle", minimum_disposition=3)
        if elira is not None and not self.has_quest("elira_faith_under_ash") and not self.quest_is_completed("elira_faith_under_ash"):
            self.grant_quest(
                "elira_faith_under_ash",
                note="Elira wants to know whether your mercy still holds once the Ashen Brand starts begging for it.",
            )

    def maybe_resolve_bryn_loose_ends(self) -> None:
        assert self.state is not None
        if not self.has_quest("bryn_loose_ends"):
            return
        if self.state.flags.get("bryn_loose_ends_resolved") or not self.state.flags.get("bryn_cache_found"):
            return
        bryn = self.any_companion_by_id("bryn_underbough")
        if bryn is None:
            return
        self.say(
            "Back in Iron Hollow, Bryn unwraps the smoke-stained ledger from the old cache. The names inside are part smugglers, part frightened teamsters, and part people who still live close enough to get hurt for what they once did."
        )
        choice = self.scenario_choice(
            "What do you tell Bryn to do with the ledger?",
            [
                self.action_option("Burn the ledger and bury the route with it."),
                self.action_option("Sell the names quietly and turn old dirt into useful coin."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Burn the ledger and bury the route with it.")
            self.state.flags["bryn_ledger_burned"] = True
            self.act1_adjust_metric("act1_town_fear", -1)
            self.adjust_companion_disposition(bryn, 1, "you chose mercy over profit in Bryn's old trade")
            self.say("Bryn watches the page curl to ash and exhales like she has finally stopped carrying one particular exit route in her head.")
        else:
            self.player_action("Sell the names quietly and turn old dirt into useful coin.")
            self.state.gold += 25
            self.state.flags["bryn_ledger_sold"] = True
            self.state.flags["act2_bonus_whisper_pressure"] = int(self.state.flags.get("act2_bonus_whisper_pressure", 0)) + 1
            self.adjust_companion_disposition(bryn, -1, "you turned Bryn's old ledger into coin")
            self.say("The ledger buys clean coin, but Bryn looks at the purse like it weighs more than the gold should.")
        self.reward_party(xp=20, reason="resolving Bryn's loose ends")
        self.state.flags["bryn_loose_ends_resolved"] = True
        self.refresh_quest_statuses(announce=False)
        self.turn_in_quest("bryn_loose_ends", giver="Bryn Underbough")

    def maybe_run_act1_companion_conflict(self) -> None:
        assert self.state is not None
        if self.state.flags.get("act1_companion_conflict_resolved"):
            return
        if not self.state.flags.get("cinderfall_relay_destroyed"):
            return
        bryn = self.any_companion_by_id("bryn_underbough", minimum_disposition=6)
        rhogar = self.any_companion_by_id("rhogar_valeguard", minimum_disposition=6)
        if bryn is None or rhogar is None:
            return
        self.say("Bryn and Rhogar collide the moment the Cinderfall maps hit the table. One sees vulnerable names; the other sees a duty to warn them before the Ashen Brand regroups around the same roads.")
        self.speaker("Bryn Underbough", "Burn the route list. Leave the town breathing and let the guilty keep their fear.")
        self.speaker("Rhogar Valeguard", "No. People cannot defend what they are not told to fear in time.")
        choice = self.scenario_choice(
            "Who do you back?",
            [
                self.action_option("Side with Bryn and keep the ugliest names off the public board."),
                self.action_option("Side with Rhogar and warn the town plainly, no matter who it shames."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Keep the ugliest names off the public board.")
            self.adjust_companion_disposition(bryn, 1, "you protected the vulnerable over public example")
            self.adjust_companion_disposition(rhogar, -1, "you kept the warning narrower than he wanted")
            self.state.flags["act1_companion_conflict_side"] = "bryn"
            self.say("Bryn softens. Rhogar does not argue further, but the silence he keeps is the kind that remembers.")
        else:
            self.player_action("Warn the town plainly, no matter who it shames.")
            self.adjust_companion_disposition(rhogar, 1, "you chose duty over comfort")
            self.adjust_companion_disposition(bryn, -1, "you chose exposure over discretion")
            self.state.flags["act1_companion_conflict_side"] = "rhogar"
            self.say("Rhogar nods once like a vow has been answered. Bryn folds in on herself for a moment before the humor comes back brittle.")
        self.state.flags["act1_companion_conflict_resolved"] = True

    def resolve_elira_faith_under_ash(self) -> None:
        assert self.state is not None
        if not self.has_quest("elira_faith_under_ash"):
            return
        if self.state.flags.get("elira_faith_under_ash_resolved"):
            return
        elira = self.any_companion_by_id("elira_dawnmantle")
        if elira is None:
            return
        self.say("In the wrecked barracks you find one gutter zealot alive under a collapsed bunk, too wounded to keep lying convincingly and too proud to beg well.")
        self.speaker("Elira Lanternward", "This is the moment that matters more than speeches ever do.")
        choice = self.scenario_choice(
            "What do you do with the captive cultist?",
            [
                self.action_option("Spare them, bind the wound, and send them out alive under warning."),
                self.action_option("Pass sentence here and make Ashfall fear what mercy costs."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Spare them, bind the wound, and send them out alive under warning.")
            self.state.flags["elira_mercy_blessing"] = True
            self.act1_adjust_metric("act1_town_fear", -1)
            self.adjust_companion_disposition(elira, 1, "you chose mercy under ash")
            self.say("Elira's expression steadies into something fierce and grateful. Word of mercy travels faster than terror when people are desperate enough to need proof it still exists.")
        else:
            self.player_action("Pass sentence here and make Ashfall fear what mercy costs.")
            self.state.flags["elira_hard_verdict"] = True
            self.adjust_companion_disposition(elira, -1, "you chose execution where Elira wanted mercy")
            self.say("The barracks go quiet around the verdict. It will travel through the fort faster than any order board.")
        self.reward_party(xp=20, reason="deciding Elira's question under fire")
        self.state.flags["elira_faith_under_ash_resolved"] = True
        self.refresh_quest_statuses(announce=False)
        self.turn_in_quest("elira_faith_under_ash", giver="Elira Lanternward")

    def act1_victory_tier(self) -> str:
        assert self.state is not None
        town_fear = self.act1_metric_value("act1_town_fear")
        ashen_strength = self.act1_metric_value("act1_ashen_strength")
        survivors_saved = self.act1_metric_value("act1_survivors_saved")
        strained = any(
            (
                self.state.flags.get("bryn_ledger_sold"),
                self.state.flags.get("elira_hard_verdict"),
                self.state.flags.get("act1_companion_conflict_side"),
            )
        )
        if town_fear <= 1 and ashen_strength <= 1 and survivors_saved >= 3 and not strained:
            return "clean_victory"
        if town_fear >= 4 or ashen_strength >= 3 or (strained and survivors_saved <= 1):
            return "fractured_victory"
        return "costly_victory"

    def act1_record_epilogue_flags(self) -> str:
        assert self.state is not None
        tier = self.act1_victory_tier()
        pressure = 0
        if tier == "costly_victory":
            pressure += 1
        elif tier == "fractured_victory":
            pressure += 2
        if self.act1_metric_value("act1_town_fear") > 3:
            pressure += 1
        pressure += int(self.state.flags.get("bryn_ledger_sold", False))
        self.state.flags["act1_victory_tier"] = tier
        self.state.flags["act2_starting_pressure"] = pressure
        return tier

    def ensure_state_integrity(self) -> None:
        super().ensure_state_integrity()
        if self.state is None:
            self._clear_map_view_cache()
            self._act1_map_cache_state_owner_id = None
            return
        normalize_act2_legacy_flags = getattr(self, "normalize_act2_legacy_flags", None)
        if callable(normalize_act2_legacy_flags):
            normalize_act2_legacy_flags()
        owner_id = id(self.state)
        if getattr(self, "_act1_map_cache_state_owner_id", None) != owner_id:
            self._act1_map_cache_state_owner_id = owner_id
            self._clear_map_view_cache()
        self._ensure_map_state_payload()
        self._sync_map_state_with_scene()

    def compact_hud_scene_key(self) -> tuple[int, str] | None:
        base = super().compact_hud_scene_key()
        if base is None or self.state is None:
            return base
        dungeon = self.current_act1_dungeon()
        if dungeon is None:
            return base
        room_id = str(self._map_state_payload().get("current_room_id") or "")
        return (base[0], f"{base[1]}::{room_id}")

    def hud_location_label(self) -> str:
        base = super().hud_location_label()
        dungeon = self.current_act1_dungeon()
        if dungeon is None:
            return base
        room = self.current_act1_room(dungeon)
        return f"{base} / {room.title}"

    def hud_objective_label(self) -> str:
        dungeon = self.current_act1_dungeon()
        if dungeon is None:
            return super().hud_objective_label()
        room = self.current_act1_room(dungeon)
        if not self.room_is_cleared(room.room_id):
            if room.role == "boss":
                return f"Break {room.title}."
            return f"Secure {room.title}."
        exits = current_room_exits(dungeon, self.act1_map_state())
        uncleared_exits = [candidate for candidate in exits if not self.room_is_cleared(candidate.room_id)]
        if uncleared_exits:
            if len(uncleared_exits) == 1:
                return f"Advance to {uncleared_exits[0].title}."
            return "Choose the next route."
        return "Find the open wing or withdraw."

    def _ensure_map_state_payload(self) -> None:
        assert self.state is not None
        raw = self.state.flags.get(self.MAP_STATE_KEY)
        if not isinstance(raw, dict):
            raw = {}
        payload = {
            "current_node_id": str(raw.get("current_node_id") or ACT1_HYBRID_MAP.start_node_id),
            "current_dungeon_id": raw.get("current_dungeon_id"),
            "current_room_id": raw.get("current_room_id"),
            "visited_nodes": self._string_list(raw.get("visited_nodes")),
            "cleared_rooms": self._string_list(raw.get("cleared_rooms")),
            "seen_story_beats": self._string_list(raw.get("seen_story_beats")),
            "node_history": self._string_history(raw.get("node_history")),
            "room_history": self._string_history(raw.get("room_history")),
        }
        self.state.flags[self.MAP_STATE_KEY] = payload

    def _map_state_payload(self) -> dict[str, Any]:
        assert self.state is not None
        self._ensure_map_state_payload()
        payload = self.state.flags[self.MAP_STATE_KEY]
        assert isinstance(payload, dict)
        return payload

    def _ensure_act2_map_state_payload(self) -> None:
        assert self.state is not None
        self._ensure_map_state_payload()
        raw = self.state.flags.get(self.ACT2_MAP_STATE_KEY)
        if not isinstance(raw, dict):
            raw = {}
        payload = {
            "current_node_id": str(raw.get("current_node_id") or ACT2_ENEMY_DRIVEN_MAP.start_node_id),
            "current_dungeon_id": raw.get("current_dungeon_id"),
            "current_room_id": raw.get("current_room_id"),
            "visited_nodes": self._string_list(raw.get("visited_nodes")),
            "cleared_rooms": self._string_list(raw.get("cleared_rooms")),
            "seen_story_beats": self._string_list(raw.get("seen_story_beats")),
            "node_history": self._string_history(raw.get("node_history")),
            "room_history": self._string_history(raw.get("room_history")),
        }
        self.state.flags[self.ACT2_MAP_STATE_KEY] = payload

    def _act2_map_state_payload(self) -> dict[str, Any]:
        assert self.state is not None
        self._ensure_act2_map_state_payload()
        payload = self.state.flags[self.ACT2_MAP_STATE_KEY]
        assert isinstance(payload, dict)
        return payload

    def _string_list(self, raw: Any) -> list[str]:
        if isinstance(raw, list):
            values = raw
        elif isinstance(raw, tuple):
            values = list(raw)
        else:
            values = []
        seen: set[str] = set()
        normalized: list[str] = []
        for value in values:
            if not isinstance(value, str):
                continue
            if value in seen:
                continue
            seen.add(value)
            normalized.append(value)
        return normalized

    def _string_history(self, raw: Any) -> list[str]:
        if isinstance(raw, list):
            values = raw
        elif isinstance(raw, tuple):
            values = list(raw)
        else:
            values = []
        return [value for value in values if isinstance(value, str)]

    def _map_view_cache(self) -> dict[str, Any]:
        cache = getattr(self, "_act1_map_view_cache", None)
        if not isinstance(cache, dict):
            cache = {"overworld": None, "dungeon": None}
            self._act1_map_view_cache = cache
        return cache

    def _map_state_signature(self, state: DraftMapState) -> tuple[Any, ...]:
        return (
            state.current_node_id,
            state.current_room_id,
            tuple(sorted(state.flags)),
            tuple(sorted(state.active_quests)),
            tuple(sorted(state.completed_quests)),
            tuple(sorted((key, repr(value)) for key, value in state.flag_values.items())),
            tuple(sorted(state.visited_nodes)),
            tuple(sorted(state.cleared_rooms)),
            tuple(sorted(state.seen_story_beats)),
        )

    def _clear_map_view_cache(self, *views: str) -> None:
        cache = self._map_view_cache()
        targets = views or ("overworld", "dungeon", "act2_overworld", "act2_dungeon")
        for view in targets:
            cache[view] = None

    def _sync_story_beats_from_flags(self) -> None:
        if self.state is None:
            return
        payload = self._map_state_payload()
        seen = set(payload["seen_story_beats"])
        if self.state.flags.get("phandalin_council_seen"):
            seen.add("stonehill_council")
        if self.state.flags.get("phandalin_after_watch_seen"):
            seen.add("lantern_vigil")
        payload["seen_story_beats"] = sorted(seen)

    def _remember_act1_nodes(self, payload: dict[str, Any], *node_ids: str) -> None:
        visited = payload["visited_nodes"]
        for node_id in node_ids:
            if node_id and node_id not in visited:
                visited.append(node_id)

    def _backfill_act1_visited_nodes(self, payload: dict[str, Any], current_node_id: str) -> None:
        assert self.state is not None
        opening_path = (
            "wayside_luck_shrine",
            "greywake_triage_yard",
            "greywake_road_breakout",
            "neverwinter_briefing",
        )
        if current_node_id == "wayside_luck_shrine":
            self._remember_act1_nodes(payload, "wayside_luck_shrine")
            return
        if current_node_id == "greywake_triage_yard":
            self._remember_act1_nodes(
                payload,
                "wayside_luck_shrine",
                "greywake_triage_yard",
            )
            return
        if current_node_id == "greywake_road_breakout":
            self._remember_act1_nodes(
                payload,
                "wayside_luck_shrine",
                "greywake_triage_yard",
                "greywake_road_breakout",
            )
            return
        if current_node_id == "neverwinter_briefing":
            self._remember_act1_nodes(payload, *opening_path)
            return
        if current_node_id == "high_road_ambush":
            self._remember_act1_nodes(payload, *opening_path, "high_road_ambush")
            return

        # Reaching any Iron Hollow-era node means the opening road, briefing, and ambush already happened.
        self._remember_act1_nodes(payload, *opening_path, "high_road_ambush", "phandalin_hub")

        later_than_branches = {"ashfall_watch", "tresendar_manor", "emberhall_cellars"}
        later_than_ashfall = {"tresendar_manor", "emberhall_cellars"}

        if current_node_id == "old_owl_well" or current_node_id in later_than_branches or bool(self.state.flags.get("old_owl_well_cleared")):
            self._remember_act1_nodes(payload, "old_owl_well")
        if current_node_id == "wyvern_tor" or current_node_id in later_than_branches or bool(self.state.flags.get("wyvern_tor_cleared")):
            self._remember_act1_nodes(payload, "wyvern_tor")
        if current_node_id == "cinderfall_ruins" or any(
            self.state.flags.get(flag_name)
            for flag_name in (
                "cinderfall_gate_opened",
                "cinderfall_chapel_secured",
                "cinderfall_storehouse_searched",
                "cinderfall_relay_destroyed",
                "cinderfall_ruins_cleared",
            )
        ):
            self._remember_act1_nodes(payload, "cinderfall_ruins")
        if (
            current_node_id == "ashfall_watch"
            or current_node_id in later_than_ashfall
            or bool(self.state.flags.get("ashfall_gate_breached"))
            or bool(self.state.flags.get("ashfall_watch_cleared"))
        ):
            self._remember_act1_nodes(payload, "ashfall_watch")
        if (
            current_node_id == "tresendar_manor"
            or current_node_id == "emberhall_cellars"
            or self.state.current_scene == "act1_complete"
            or bool(self.state.flags.get("tresendar_revealed"))
            or bool(self.state.flags.get("tresendar_cleared"))
            or bool(self.state.flags.get("emberhall_revealed"))
        ):
            self._remember_act1_nodes(payload, "tresendar_manor")
        if current_node_id == "emberhall_cellars" or self.state.current_scene == "act1_complete" or bool(self.state.flags.get("act1_complete")):
            self._remember_act1_nodes(payload, "emberhall_cellars")

    def _seed_act1_overworld_history(self, payload: dict[str, Any], current_node_id: str) -> None:
        if payload["node_history"]:
            return
        if current_node_id == "greywake_triage_yard":
            payload["node_history"] = ["wayside_luck_shrine"]
        elif current_node_id == "greywake_road_breakout":
            payload["node_history"] = ["wayside_luck_shrine", "greywake_triage_yard"]
        elif current_node_id == "high_road_ambush":
            payload["node_history"] = ["neverwinter_briefing"]
        elif current_node_id == "phandalin_hub":
            payload["node_history"] = ["neverwinter_briefing", "high_road_ambush"]

    def _sync_map_state_with_scene(self, *, force_node_id: str | None = None) -> None:
        assert self.state is not None
        payload = self._map_state_payload()
        node_id = force_node_id or ACT1_SCENE_TO_NODE_ID.get(self.state.current_scene)
        if node_id is None and self.state.current_scene == "act1_complete":
            node_id = "emberhall_cellars"
        if node_id is None:
            self._sync_story_beats_from_flags()
            return
        node = ACT1_HYBRID_MAP.nodes[node_id]
        payload["current_node_id"] = node_id
        payload["node_history"] = [history_node_id for history_node_id in payload["node_history"] if history_node_id in ACT1_HYBRID_MAP.nodes]
        self._backfill_act1_visited_nodes(payload, node_id)
        self._seed_act1_overworld_history(payload, node_id)
        if node.enters_dungeon_id is None or self.state.current_scene != node.scene_key:
            payload["current_dungeon_id"] = None
            payload["current_room_id"] = None
            payload["room_history"] = []
            self._compact_hud_last_scene_key = None
            self._sync_story_beats_from_flags()
            return
        dungeon = ACT1_HYBRID_MAP.dungeons[node.enters_dungeon_id]
        payload["current_dungeon_id"] = dungeon.dungeon_id
        if payload.get("current_room_id") not in dungeon.rooms:
            payload["current_room_id"] = dungeon.entrance_room_id
        payload["room_history"] = [room_id for room_id in payload["room_history"] if room_id in dungeon.rooms]
        self._compact_hud_last_scene_key = None
        self._sync_story_beats_from_flags()

    def _sync_act2_map_state_with_scene(self, *, force_node_id: str | None = None) -> None:
        assert self.state is not None
        payload = self._act2_map_state_payload()
        node_id = force_node_id or self._act2_current_node_id()
        node = ACT2_ENEMY_DRIVEN_MAP.nodes[node_id]
        payload["current_node_id"] = node_id
        payload["node_history"] = [history_node_id for history_node_id in payload["node_history"] if history_node_id in ACT2_ENEMY_DRIVEN_MAP.nodes]
        if node_id not in payload["visited_nodes"]:
            payload["visited_nodes"].append(node_id)
        if node.enters_dungeon_id is None or self.state.current_scene != node.scene_key:
            payload["current_dungeon_id"] = None
            payload["current_room_id"] = None
            payload["room_history"] = []
            return
        dungeon = ACT2_ENEMY_DRIVEN_MAP.dungeons[node.enters_dungeon_id]
        payload["current_dungeon_id"] = dungeon.dungeon_id
        if payload.get("current_room_id") not in dungeon.rooms:
            payload["current_room_id"] = dungeon.entrance_room_id
        payload["room_history"] = [room_id for room_id in payload["room_history"] if room_id in dungeon.rooms]

    def act1_map_state(self) -> DraftMapState:
        assert self.state is not None
        self._sync_map_state_with_scene()
        payload = self._map_state_payload()
        active_quests, completed_quests = self._map_quest_sets()
        flags = {
            flag_name
            for flag_name in ACT1_MAP_FLAG_NAMES
            if self.state.flags.get(flag_name)
        }
        return DraftMapState(
            current_node_id=str(payload["current_node_id"]),
            current_room_id=str(payload["current_room_id"]) if payload.get("current_room_id") else None,
            flags=flags,
            active_quests=active_quests,
            completed_quests=completed_quests,
            visited_nodes=set(payload["visited_nodes"]),
            cleared_rooms=set(payload["cleared_rooms"]),
            seen_story_beats=set(payload["seen_story_beats"]),
        )

    def _map_quest_sets(self) -> tuple[set[str], set[str]]:
        assert self.state is not None
        active_quests = {
            quest_id
            for quest_id, entry in self.state.quests.items()
            if getattr(entry, "status", "") in {"active", "ready_to_turn_in"}
        }
        completed_quests = {
            quest_id
            for quest_id, entry in self.state.quests.items()
            if getattr(entry, "status", "") == "completed"
        }
        return active_quests, completed_quests

    def _primitive_flag_values(self) -> dict[str, Any]:
        assert self.state is not None
        return {
            key: value
            for key, value in self.state.flags.items()
            if isinstance(value, str | int | float | bool)
        }

    def _act2_boolean_flags(self) -> set[str]:
        assert self.state is not None
        flags = {
            flag_name
            for flag_name in ACT2_MAP_FLAG_NAMES
            if self.state.flags.get(flag_name) is True
        }
        if self.state.current_act >= 2 or self.state.current_scene in ACT2_SCENE_TO_NODE_ID:
            flags.add("act2_started")
        return flags

    def _act2_cleared_room_ids(self) -> set[str]:
        assert self.state is not None
        cleared: set[str] = set()
        for dungeon in ACT2_ENEMY_DRIVEN_MAP.dungeons.values():
            for room in dungeon.rooms.values():
                if any(self.state.flags.get(flag_name) is True for flag_name in room.clear_grants_flags):
                    cleared.add(room.room_id)
        return cleared

    def _act2_seen_story_beats(self) -> set[str]:
        assert self.state is not None
        seen: set[str] = set()
        for beat in ACT2_ENEMY_DRIVEN_MAP.story_beats:
            if any(self.state.flags.get(flag_name) is True for flag_name in beat.grants_flags):
                seen.add(beat.beat_id)
        return seen

    def _act2_current_node_id(self) -> str:
        assert self.state is not None
        node_id = ACT2_SCENE_TO_NODE_ID.get(self.state.current_scene)
        if node_id is not None:
            return node_id
        if self.state.flags.get("act2_started") or self.state.current_act >= 2:
            return "act2_expedition_hub"
        return ACT2_ENEMY_DRIVEN_MAP.start_node_id

    def act2_map_state(self) -> DraftMapState:
        assert self.state is not None
        self._sync_act2_map_state_with_scene()
        payload = self._act2_map_state_payload()
        active_quests, completed_quests = self._map_quest_sets()
        current_node_id = str(payload["current_node_id"])
        node = ACT2_ENEMY_DRIVEN_MAP.nodes[current_node_id]
        current_room_id = str(payload["current_room_id"]) if payload.get("current_room_id") else None
        derived_cleared_rooms = self._act2_cleared_room_ids()

        state = DraftMapState(
            current_node_id=current_node_id,
            current_room_id=current_room_id,
            flags=self._act2_boolean_flags(),
            active_quests=active_quests,
            completed_quests=completed_quests,
            flag_values=self._primitive_flag_values(),
            visited_nodes=set(payload["visited_nodes"]),
            cleared_rooms=set(payload["cleared_rooms"]) | derived_cleared_rooms,
            seen_story_beats=set(payload["seen_story_beats"]) | self._act2_seen_story_beats(),
        )

        known_nodes = {
            node_id
            for node_id, candidate in ACT2_ENEMY_DRIVEN_MAP.nodes.items()
            if requirement_met(state, candidate.requirement)
        }
        known_nodes.add(ACT2_ENEMY_DRIVEN_MAP.start_node_id)
        known_nodes.add(current_node_id)
        state.visited_nodes.update(known_nodes)
        return state

    def current_act1_dungeon(self) -> DungeonMap | None:
        if self.state is None:
            return None
        payload = self._map_state_payload()
        dungeon_id = payload.get("current_dungeon_id")
        if not isinstance(dungeon_id, str):
            return None
        return ACT1_HYBRID_MAP.dungeons.get(dungeon_id)

    def current_act1_room(self, dungeon: DungeonMap) -> DungeonRoom:
        payload = self._map_state_payload()
        room_id = payload.get("current_room_id")
        if not isinstance(room_id, str) or room_id not in dungeon.rooms:
            room_id = dungeon.entrance_room_id
        return dungeon.rooms[room_id]

    def room_is_cleared(self, room_id: str) -> bool:
        return room_id in set(self._map_state_payload()["cleared_rooms"])

    def complete_map_room(self, dungeon: DungeonMap, room_id: str) -> None:
        assert self.state is not None
        payload = self._map_state_payload()
        if room_id not in payload["cleared_rooms"]:
            payload["cleared_rooms"].append(room_id)
        room = dungeon.rooms[room_id]
        for flag_name in room.clear_grants_flags:
            self.state.flags[flag_name] = True
        self._clear_map_view_cache("dungeon")
        self._compact_hud_last_scene_key = None

    def _queue_act1_dungeon_transition_feedback(self, movement_text: str = "") -> None:
        self._pending_act1_dungeon_map_refresh = True
        self._pending_act1_dungeon_movement_text = movement_text

    def _consume_act1_dungeon_transition_feedback(self, dungeon: DungeonMap) -> None:
        if not getattr(self, "_pending_act1_dungeon_map_refresh", False):
            return
        movement_text = str(getattr(self, "_pending_act1_dungeon_movement_text", ""))
        self._pending_act1_dungeon_map_refresh = False
        self._pending_act1_dungeon_movement_text = ""
        self.render_act1_dungeon_map(dungeon, force=True)
        if movement_text:
            self.say(movement_text)

    def set_current_map_room(self, room_id: str, *, announce: bool = False, movement_text: str = "") -> None:
        payload = self._map_state_payload()
        current_room_id = payload.get("current_room_id")
        if current_room_id == room_id:
            return
        if isinstance(current_room_id, str) and current_room_id:
            payload["room_history"].append(current_room_id)
        payload["current_room_id"] = room_id
        self._clear_map_view_cache("dungeon")
        self._compact_hud_last_scene_key = None
        self._queue_act1_dungeon_transition_feedback(
            movement_text or f"You move toward {room_id.replace('_', ' ')}." if announce else ""
        )

    def backtrack_map_room(self, dungeon: DungeonMap) -> bool:
        payload = self._map_state_payload()
        while payload["room_history"]:
            previous_room_id = payload["room_history"].pop()
            current_room_id = payload.get("current_room_id")
            if previous_room_id in dungeon.rooms and previous_room_id != current_room_id:
                current_room = dungeon.rooms[current_room_id] if isinstance(current_room_id, str) and current_room_id in dungeon.rooms else dungeon.rooms[dungeon.entrance_room_id]
                previous_room = dungeon.rooms[previous_room_id]
                direction = room_precise_direction(current_room, previous_room, dungeon).lower()
                payload["current_room_id"] = previous_room_id
                self._clear_map_view_cache("dungeon")
                self._compact_hud_last_scene_key = None
                self._queue_act1_dungeon_transition_feedback(f"You backtrack {direction} toward {previous_room.title}.")
                return True
        return False

    def peek_backtrack_room(self, dungeon: DungeonMap) -> DungeonRoom | None:
        payload = self._map_state_payload()
        for room_id in reversed(payload["room_history"]):
            if room_id in dungeon.rooms:
                return dungeon.rooms[room_id]
        return None

    def _show_act1_overworld_transition_feedback(self, text: str = "") -> None:
        self.render_act1_overworld_map(force=True)
        if text:
            self.say(text)

    def _refresh_map_scene_music(self) -> None:
        refresh_scene_music = getattr(self, "refresh_scene_music", None)
        if callable(refresh_scene_music):
            refresh_scene_music()

    def _act1_current_node_id_for_history(self, payload: dict[str, Any]) -> str:
        assert self.state is not None
        scene_node_id = ACT1_SCENE_TO_NODE_ID.get(self.state.current_scene)
        if scene_node_id is not None:
            return scene_node_id
        return str(payload.get("current_node_id") or "")

    def _record_act1_node_history(self, payload: dict[str, Any], from_node_id: str, to_node_id: str) -> None:
        if from_node_id and from_node_id in ACT1_HYBRID_MAP.nodes and from_node_id != to_node_id:
            payload["node_history"].append(from_node_id)

    def travel_to_act1_node(self, node_id: str, *, transition_text: str = "", record_history: bool = True) -> None:
        assert self.state is not None
        payload = self._map_state_payload()
        if record_history:
            self._record_act1_node_history(payload, self._act1_current_node_id_for_history(payload), node_id)
        node = ACT1_HYBRID_MAP.nodes[node_id]
        payload["current_node_id"] = node_id
        if node_id not in payload["visited_nodes"]:
            payload["visited_nodes"].append(node_id)
        if node.enters_dungeon_id is None:
            payload["current_dungeon_id"] = None
            payload["current_room_id"] = None
            payload["room_history"] = []
        else:
            dungeon = ACT1_HYBRID_MAP.dungeons[node.enters_dungeon_id]
            payload["current_dungeon_id"] = dungeon.dungeon_id
            payload["current_room_id"] = dungeon.entrance_room_id
            payload["room_history"] = []
        self.state.current_scene = node.scene_key
        self._clear_map_view_cache()
        self._compact_hud_last_scene_key = None
        self._refresh_map_scene_music()
        self._show_act1_overworld_transition_feedback(transition_text)

    def return_to_phandalin(self, text: str) -> None:
        self.travel_to_act1_node("phandalin_hub", transition_text=text)

    def return_to_blackwake_decision(self, text: str) -> None:
        self.travel_to_act1_node("road_decision_post_blackwake", transition_text=text)

    def _act1_overworld_backtrack_allowed(self, current_node_id: str, candidate_node_id: str) -> bool:
        if current_node_id == "phandalin_hub" and candidate_node_id in ACT1_HIGH_ROAD_SIDE_BRANCH_NODE_IDS:
            return False
        return candidate_node_id in ACT1_HYBRID_MAP.nodes and candidate_node_id != current_node_id

    def peek_act1_overworld_backtrack_node(self):
        payload = self._map_state_payload()
        current_node_id = str(payload.get("current_node_id") or "")
        for node_id in reversed(payload["node_history"]):
            if self._act1_overworld_backtrack_allowed(current_node_id, node_id):
                return ACT1_HYBRID_MAP.nodes[node_id]
        return None

    def _act1_overworld_backtrack_text(self, from_node_id: str, to_node_id: str) -> str:
        from_title = ACT1_HYBRID_MAP.nodes[from_node_id].title
        to_title = ACT1_HYBRID_MAP.nodes[to_node_id].title
        if to_node_id == "neverwinter_briefing":
            return (
                "You backtrack north toward Greywake, letting the familiar city road pull the party "
                "back to Mira's briefing room instead of pressing farther into the frontier."
            )
        if to_node_id == "high_road_ambush":
            return "You backtrack north along the Emberway, returning to the scarred wagon site between Iron Hollow and Greywake."
        if from_node_id == "road_decision_post_blackwake" and to_node_id == "blackwake_crossing":
            return "You double back toward Blackwake Crossing, following the wet wagon scars and smoke-stained reeds instead of committing to the south road."
        if from_node_id == "phandalin_hub":
            return f"You leave Iron Hollow by the same track you used before, letting the road back to {to_title} replace the town's noise behind you."
        return f"You backtrack from {from_title} toward {to_title}, choosing the familiar route over a new lead."

    def _narrate_act1_overworld_backtrack_context(self, from_node_id: str, to_node_id: str) -> None:
        if to_node_id == "neverwinter_briefing":
            self.say("Mira is waiting in the background of the city machine: messengers, wax seals, and hard questions ready for whatever you bring back.")
            return
        if to_node_id == "high_road_ambush":
            self.say("No fresh ambush waits there now, but the road still remembers the smoke, broken wheels, and the choice that first pointed you south.")
            return
        if to_node_id == "blackwake_crossing":
            self.say("Mira is not on this muddy bend, but her unanswered questions sit in the background as you retrace Blackwake's broken approach.")
            return
        if from_node_id == "phandalin_hub":
            self.say("Behind you, Iron Hollow keeps moving: Tessa's runners argue supplies, road watches trade signals, and familiar voices fade into background work.")

    def backtrack_act1_overworld_node(self) -> bool:
        assert self.state is not None
        candidate = self.peek_act1_overworld_backtrack_node()
        if candidate is None:
            return False
        payload = self._map_state_payload()
        current_node_id = str(payload.get("current_node_id") or "")
        while payload["node_history"]:
            node_id = payload["node_history"].pop()
            if node_id == candidate.node_id:
                break
        transition_text = self._act1_overworld_backtrack_text(current_node_id, candidate.node_id)
        self.travel_to_act1_node(candidate.node_id, transition_text=transition_text, record_history=False)
        self._narrate_act1_overworld_backtrack_context(current_node_id, candidate.node_id)
        return True

    def act1_hybrid_map_available(self) -> bool:
        if self.state is None:
            return False
        return self.state.current_scene in ACT1_SCENE_TO_NODE_ID or self.state.current_scene == "act1_complete"

    def act2_hybrid_map_available(self) -> bool:
        if self.state is None:
            return False
        return (
            self.state.current_scene in ACT2_SCENE_TO_NODE_ID
            or self.state.current_act >= 2
            or bool(self.state.flags.get("act2_started"))
        )

    def render_act1_overworld_map(self, *, force: bool = False) -> None:
        if not self.act1_hybrid_map_available():
            return
        state = self.act1_map_state()
        cache = self._map_view_cache()
        cache_key = self._map_state_signature(state)
        if not force and cache.get("overworld") == cache_key:
            return
        panel = build_overworld_panel(ACT1_HYBRID_MAP, state)
        if self.should_use_rich_ui() and RICH_AVAILABLE and self.emit_rich(panel, width=max(108, self.rich_console_width())):
            cache["overworld"] = cache_key
            self.output_fn("")
            return
        for line in build_overworld_panel_text(ACT1_HYBRID_MAP, state).splitlines():
            self.output_fn(line)
        cache["overworld"] = cache_key
        self.output_fn("")

    def render_act1_dungeon_map(self, dungeon: DungeonMap, *, force: bool = False) -> None:
        state = self.act1_map_state()
        cache = self._map_view_cache()
        cache_key = (dungeon.dungeon_id, self._map_state_signature(state))
        if not force and cache.get("dungeon") == cache_key:
            return
        if self.should_use_rich_ui() and RICH_AVAILABLE and self.emit_rich(
            build_dungeon_panel(dungeon, state),
            width=max(108, self.rich_console_width()),
        ):
            cache["dungeon"] = cache_key
            self.output_fn("")
            return
        for line in build_dungeon_panel_text(dungeon, state).splitlines():
            self.output_fn(line)
        cache["dungeon"] = cache_key
        self.output_fn("")

    def current_act2_dungeon(self) -> DungeonMap | None:
        if self.state is None or not self.act2_hybrid_map_available():
            return None
        self._sync_act2_map_state_with_scene()
        node = ACT2_ENEMY_DRIVEN_MAP.nodes[self._act2_current_node_id()]
        if node.enters_dungeon_id is None or self.state.current_scene != node.scene_key:
            return None
        return ACT2_ENEMY_DRIVEN_MAP.dungeons.get(node.enters_dungeon_id)

    def current_act2_room(self, dungeon: DungeonMap) -> DungeonRoom:
        payload = self._act2_map_state_payload()
        room_id = payload.get("current_room_id")
        if not isinstance(room_id, str) or room_id not in dungeon.rooms:
            room_id = dungeon.entrance_room_id
        return dungeon.rooms[room_id]

    def act2_room_is_cleared(self, room_id: str) -> bool:
        payload = self._act2_map_state_payload()
        if room_id in set(payload["cleared_rooms"]):
            return True
        return room_id in self._act2_cleared_room_ids()

    def complete_act2_map_room(self, dungeon: DungeonMap, room_id: str) -> None:
        assert self.state is not None
        payload = self._act2_map_state_payload()
        if room_id not in payload["cleared_rooms"]:
            payload["cleared_rooms"].append(room_id)
        room = dungeon.rooms[room_id]
        for flag_name in room.clear_grants_flags:
            self.state.flags[flag_name] = True
        self._clear_map_view_cache("act2_overworld", "act2_dungeon")
        self._compact_hud_last_scene_key = None

    def _queue_act2_dungeon_transition_feedback(self, movement_text: str = "") -> None:
        self._pending_act2_dungeon_map_refresh = True
        self._pending_act2_dungeon_movement_text = movement_text

    def _consume_act2_dungeon_transition_feedback(self, dungeon: DungeonMap) -> None:
        if not getattr(self, "_pending_act2_dungeon_map_refresh", False):
            return
        movement_text = str(getattr(self, "_pending_act2_dungeon_movement_text", ""))
        self._pending_act2_dungeon_map_refresh = False
        self._pending_act2_dungeon_movement_text = ""
        self.render_act2_dungeon_map(dungeon, force=True)
        if movement_text:
            self.say(movement_text)

    def _show_act2_overworld_transition_feedback(self, text: str = "") -> None:
        self.render_act2_overworld_map(force=True)
        if text:
            self.say(text)

    def _act2_current_node_id_for_history(self, payload: dict[str, Any]) -> str:
        assert self.state is not None
        scene_node_id = ACT2_SCENE_TO_NODE_ID.get(self.state.current_scene)
        if scene_node_id is not None:
            return scene_node_id
        return str(payload.get("current_node_id") or "")

    def _record_act2_node_history(self, payload: dict[str, Any], from_node_id: str, to_node_id: str) -> None:
        if from_node_id and from_node_id in ACT2_ENEMY_DRIVEN_MAP.nodes and from_node_id != to_node_id:
            payload["node_history"].append(from_node_id)

    def travel_to_act2_node(self, node_id: str, *, transition_text: str = "", record_history: bool = True) -> None:
        assert self.state is not None
        payload = self._act2_map_state_payload()
        if record_history:
            self._record_act2_node_history(payload, self._act2_current_node_id_for_history(payload), node_id)
        node = ACT2_ENEMY_DRIVEN_MAP.nodes[node_id]
        payload["current_node_id"] = node_id
        if node_id not in payload["visited_nodes"]:
            payload["visited_nodes"].append(node_id)
        if node.enters_dungeon_id is None:
            payload["current_dungeon_id"] = None
            payload["current_room_id"] = None
            payload["room_history"] = []
        else:
            dungeon = ACT2_ENEMY_DRIVEN_MAP.dungeons[node.enters_dungeon_id]
            payload["current_dungeon_id"] = dungeon.dungeon_id
            payload["current_room_id"] = dungeon.entrance_room_id
            payload["room_history"] = []
        self.state.current_scene = node.scene_key
        self._clear_map_view_cache("act2_overworld", "act2_dungeon")
        self._compact_hud_last_scene_key = None
        self._refresh_map_scene_music()
        self._show_act2_overworld_transition_feedback(transition_text)

    def set_current_act2_map_room(self, room_id: str, *, announce: bool = False, movement_text: str = "") -> None:
        payload = self._act2_map_state_payload()
        current_room_id = payload.get("current_room_id")
        if current_room_id == room_id:
            return
        if isinstance(current_room_id, str) and current_room_id:
            payload["room_history"].append(current_room_id)
        payload["current_room_id"] = room_id
        self._clear_map_view_cache("act2_dungeon")
        self._compact_hud_last_scene_key = None
        self._queue_act2_dungeon_transition_feedback(
            movement_text or f"You move toward {room_id.replace('_', ' ')}." if announce else ""
        )

    def peek_act2_backtrack_room(self, dungeon: DungeonMap) -> DungeonRoom | None:
        payload = self._act2_map_state_payload()
        for room_id in reversed(payload["room_history"]):
            if room_id in dungeon.rooms:
                return dungeon.rooms[room_id]
        return None

    def backtrack_act2_map_room(self, dungeon: DungeonMap) -> bool:
        payload = self._act2_map_state_payload()
        while payload["room_history"]:
            previous_room_id = payload["room_history"].pop()
            current_room_id = payload.get("current_room_id")
            if previous_room_id in dungeon.rooms and previous_room_id != current_room_id:
                current_room = dungeon.rooms[current_room_id] if isinstance(current_room_id, str) and current_room_id in dungeon.rooms else dungeon.rooms[dungeon.entrance_room_id]
                previous_room = dungeon.rooms[previous_room_id]
                direction = room_precise_direction(current_room, previous_room, dungeon).lower()
                payload["current_room_id"] = previous_room_id
                self._clear_map_view_cache("act2_dungeon")
                self._compact_hud_last_scene_key = None
                self._queue_act2_dungeon_transition_feedback(f"You backtrack {direction} toward {previous_room.title}.")
                return True
        return False

    def _act2_movement_option_label(self, room: DungeonRoom, candidate: DungeonRoom, direction: str | None = None) -> str:
        direction = direction or room_direction(room, candidate)
        verb = "Advance to" if not self.act2_room_is_cleared(candidate.room_id) else "Return to"
        return self.skill_tag(f"MOVE {direction}", self.action_option(f"{verb} {candidate.title}"))

    def _act2_backtrack_option_label(self, room: DungeonRoom, candidate: DungeonRoom, direction: str | None = None) -> str:
        direction = direction or room_precise_direction(room, candidate)
        return self.skill_tag(f"BACKTRACK {direction}", self.action_option(f"Backtrack to {candidate.title}"))

    def act2_room_navigation_options(self, dungeon: DungeonMap) -> list[tuple[str, str, str]]:
        room = self.current_act2_room(dungeon)
        options: list[tuple[str, str, str]] = []
        previous_room = self.peek_act2_backtrack_room(dungeon)
        backtrack_direction = room_precise_direction(room, previous_room, dungeon) if previous_room is not None else None
        exits = current_room_exits(dungeon, self.act2_map_state())
        move_exits = [candidate for candidate in exits if previous_room is None or candidate.room_id != previous_room.room_id]
        reserved_directions = {backtrack_direction} if backtrack_direction is not None else set()
        directions = room_exit_directions(room, move_exits, dungeon=dungeon, reserved_directions=reserved_directions)
        ordered_exits = sorted(
            move_exits,
            key=lambda candidate: (
                self.act2_room_is_cleared(candidate.room_id),
                _room_target_sort_key(room, candidate, directions[candidate.room_id]),
                candidate.title,
            ),
        )
        for candidate in ordered_exits:
            direction = directions[candidate.room_id]
            options.append((f"move:{direction}", candidate.room_id, self._act2_movement_option_label(room, candidate, direction)))
        if previous_room is not None and backtrack_direction is not None:
            options.append((f"backtrack:{backtrack_direction}", previous_room.room_id, self._act2_backtrack_option_label(room, previous_room, backtrack_direction)))
        options.append(("withdraw", "act2_expedition_hub", self.action_option("Withdraw to the expedition hub")))
        return options

    def return_to_act2_hub(self, text: str) -> None:
        self.travel_to_act2_node("act2_expedition_hub", transition_text=text)

    def _act2_overworld_backtrack_allowed(self, current_node_id: str, candidate_node_id: str) -> bool:
        return candidate_node_id in ACT2_ENEMY_DRIVEN_MAP.nodes and candidate_node_id != current_node_id

    def peek_act2_overworld_backtrack_node(self):
        payload = self._act2_map_state_payload()
        current_node_id = str(payload.get("current_node_id") or "")
        for node_id in reversed(payload["node_history"]):
            if self._act2_overworld_backtrack_allowed(current_node_id, node_id):
                return ACT2_ENEMY_DRIVEN_MAP.nodes[node_id]
        return None

    def _act2_overworld_backtrack_text(self, from_node_id: str, to_node_id: str) -> str:
        from_title = ACT2_ENEMY_DRIVEN_MAP.nodes[from_node_id].title
        to_title = ACT2_ENEMY_DRIVEN_MAP.nodes[to_node_id].title
        if from_node_id == "act2_expedition_hub":
            return f"You reopen the same expedition line from Iron Hollow, backtracking toward {to_title} before the council can turn the map into another argument."
        return f"You backtrack from {from_title} toward {to_title}, choosing the route you already know."

    def _narrate_act2_overworld_backtrack_context(self, from_node_id: str, to_node_id: str) -> None:
        if from_node_id == "act2_expedition_hub":
            self.say("At the expedition table behind you, Halia, Linene, Elira, and Daran keep the argument alive in low voices while the party retraces the marked route.")

    def backtrack_act2_overworld_node(self) -> bool:
        assert self.state is not None
        candidate = self.peek_act2_overworld_backtrack_node()
        if candidate is None:
            return False
        payload = self._act2_map_state_payload()
        current_node_id = str(payload.get("current_node_id") or "")
        while payload["node_history"]:
            node_id = payload["node_history"].pop()
            if node_id == candidate.node_id:
                break
        transition_text = self._act2_overworld_backtrack_text(current_node_id, candidate.node_id)
        self.travel_to_act2_node(candidate.node_id, transition_text=transition_text, record_history=False)
        self._narrate_act2_overworld_backtrack_context(current_node_id, candidate.node_id)
        return True

    def render_act2_overworld_map(self, *, force: bool = False) -> None:
        if not self.act2_hybrid_map_available():
            return
        state = self.act2_map_state()
        cache = self._map_view_cache()
        cache_key = self._map_state_signature(state)
        if not force and cache.get("act2_overworld") == cache_key:
            return
        panel = build_overworld_panel(ACT2_ENEMY_DRIVEN_MAP, state)
        if self.should_use_rich_ui() and RICH_AVAILABLE:
            rich_panel = Group(build_act2_pressure_panel(state.flag_values), panel) if Group is not None else panel
            if self.emit_rich(rich_panel, width=max(108, self.rich_console_width())):
                cache["act2_overworld"] = cache_key
                self.output_fn("")
                return
        for line in build_act2_pressure_panel_text(state.flag_values).splitlines():
            self.output_fn(line)
        for line in build_overworld_panel_text(ACT2_ENEMY_DRIVEN_MAP, state).splitlines():
            self.output_fn(line)
        cache["act2_overworld"] = cache_key
        self.output_fn("")

    def render_act2_dungeon_map(self, dungeon: DungeonMap, *, force: bool = False) -> None:
        state = self.act2_map_state()
        cache = self._map_view_cache()
        cache_key = (dungeon.dungeon_id, self._map_state_signature(state))
        if not force and cache.get("act2_dungeon") == cache_key:
            return
        dungeon_panel = build_dungeon_panel(dungeon, state)
        if self.should_use_rich_ui() and RICH_AVAILABLE:
            rich_panel = Group(build_act2_pressure_panel(state.flag_values), dungeon_panel) if Group is not None else dungeon_panel
            if self.emit_rich(
                rich_panel,
                width=max(108, self.rich_console_width()),
            ):
                cache["act2_dungeon"] = cache_key
                self.output_fn("")
                return
        for line in build_act2_pressure_panel_text(state.flag_values).splitlines():
            self.output_fn(line)
        for line in build_dungeon_panel_text(dungeon, state).splitlines():
            self.output_fn(line)
        cache["act2_dungeon"] = cache_key
        self.output_fn("")

    def _movement_option_label(self, room: DungeonRoom, candidate: DungeonRoom, direction: str | None = None) -> str:
        direction = direction or room_direction(room, candidate)
        verb = "Advance to" if not self.room_is_cleared(candidate.room_id) else "Return to"
        return self.skill_tag(f"MOVE {direction}", self.action_option(f"{verb} {candidate.title}"))

    def _backtrack_option_label(self, room: DungeonRoom, candidate: DungeonRoom, direction: str | None = None) -> str:
        direction = direction or room_precise_direction(room, candidate)
        return self.skill_tag(f"BACKTRACK {direction}", self.action_option(f"Backtrack to {candidate.title}"))

    def act1_room_navigation_options(self, dungeon: DungeonMap) -> list[tuple[str, str, str]]:
        room = self.current_act1_room(dungeon)
        options: list[tuple[str, str, str]] = []
        previous_room = self.peek_backtrack_room(dungeon)
        backtrack_direction = room_precise_direction(room, previous_room, dungeon) if previous_room is not None else None
        exits = current_room_exits(dungeon, self.act1_map_state())
        move_exits = [candidate for candidate in exits if previous_room is None or candidate.room_id != previous_room.room_id]
        reserved_directions = {backtrack_direction} if backtrack_direction is not None else set()
        directions = room_exit_directions(room, move_exits, dungeon=dungeon, reserved_directions=reserved_directions)
        ordered_exits = sorted(
            move_exits,
            key=lambda candidate: (
                self.room_is_cleared(candidate.room_id),
                _room_target_sort_key(room, candidate, directions[candidate.room_id]),
                candidate.title,
            ),
        )
        for candidate in ordered_exits:
            direction = directions[candidate.room_id]
            options.append((f"move:{direction}", candidate.room_id, self._movement_option_label(room, candidate, direction)))
        if previous_room is not None and backtrack_direction is not None:
            options.append((f"backtrack:{backtrack_direction}", previous_room.room_id, self._backtrack_option_label(room, previous_room, backtrack_direction)))
        overworld_backtrack_node = self.peek_act1_overworld_backtrack_node()
        if (
            previous_room is None
            and room.room_id == dungeon.entrance_room_id
            and overworld_backtrack_node is not None
            and overworld_backtrack_node.node_id != dungeon.exit_to_node_id
        ):
            options.append(("overworld_backtrack", overworld_backtrack_node.node_id, self.skill_tag("BACKTRACK", self.action_option(f"Backtrack to {overworld_backtrack_node.title}"))))
        if dungeon.exit_to_node_id == "road_decision_post_blackwake":
            options.append(("withdraw", "road_decision_post_blackwake", self.action_option("Withdraw to the Blackwake road decision")))
        else:
            options.append(("withdraw", "phandalin_hub", self.action_option("Withdraw to Iron Hollow")))
        return options

    def open_map_menu(self) -> None:
        if self.act1_hybrid_map_available():
            self.open_act1_map_menu()
            return
        if self.act2_hybrid_map_available():
            self.open_act2_map_menu()
            return
        self.say("There is no active hybrid map at this point in the adventure.")

    def open_act1_map_menu(self) -> None:
        if not self.act1_hybrid_map_available():
            self.say("There is no active map yet.")
            return
        dungeon = self.current_act1_dungeon()
        while True:
            choice = self.choose(
                "Map menu",
                [
                    "Travel Ledger",
                    "Overworld",
                    dungeon.title if dungeon is not None else "Dungeon (not available here)",
                    "Back",
                ],
                allow_meta=False,
                show_hud=False,
            )
            if choice == 1:
                self.render_compact_hud()
                continue
            if choice == 2:
                self.banner("Overworld Map")
                self.render_act1_overworld_map(force=True)
                continue
            if choice == 3:
                if dungeon is None:
                    self.say("There is no dungeon map to show from this location.")
                    continue
                self.banner(dungeon.title)
                self.render_act1_dungeon_map(dungeon, force=True)
                continue
            return

    def open_act2_map_menu(self) -> None:
        if not self.act2_hybrid_map_available():
            self.say("There is no active map yet.")
            return
        dungeon = self.current_act2_dungeon()
        site_label = "Current Site (not available here)"
        if dungeon is not None:
            playable_sites = {
                "stonehollow_dig",
                "siltlock_counting_house",
                "broken_prospect",
                "south_adit",
                "wave_echo_outer_galleries",
                "black_lake_causeway",
                "blackglass_relay_house",
                "forge_of_spells",
            }
            site_label = dungeon.title if dungeon.entry_node_id in playable_sites else f"{dungeon.title} (draft, read-only)"
        while True:
            choice = self.choose(
                "Map menu",
                [
                    "Travel Ledger",
                    "Act II Route Map",
                    site_label,
                    "Back",
                ],
                allow_meta=False,
                show_hud=False,
            )
            if choice == 1:
                self.render_compact_hud()
                continue
            if choice == 2:
                self.banner("Act II Route Map")
                self.render_act2_overworld_map(force=True)
                continue
            if choice == 3:
                if dungeon is None:
                    self.say("There is no Act II site map to show from this location.")
                    continue
                self.banner(dungeon.title)
                self.render_act2_dungeon_map(dungeon, force=True)
                continue
            return

    def handle_meta_command(self, raw: str) -> bool:
        lowered = raw.strip().lower()
        if lowered in {"map", "maps", "map menu"}:
            if self.state is None:
                self.say("There is no active map yet.")
            elif getattr(self, "_in_combat", False):
                self.say("Maps are unavailable during combat.")
            else:
                self.open_map_menu()
            return True
        return super().handle_meta_command(raw)

    def scene_phandalin_hub(self) -> None:
        assert self.state is not None
        self.act1_initialize_metrics()
        self._sync_map_state_with_scene(force_node_id="phandalin_hub")
        self.banner("Iron Hollow")
        if not self.state.flags.get("phandalin_arrived"):
            self.say(
                "Iron Hollow rises from rocky foothills in a scatter of rebuilt homes, old stone scars, orchard walls, wagon sheds, and lantern-lit mud lanes. "
                "There are no proper walls, no garrison worth the name, and too many decent people living one bad week away from disaster.",
                typed=True,
            )
            self.state.flags["phandalin_arrived"] = True
            self.add_journal("You reached Iron Hollow, a hard-bitten frontier town under growing Ashen Brand pressure.")
            if self.state.flags.get("blackwake_completed"):
                self.describe_blackwake_phandalin_arrival()
            choice = self.scenario_choice(
                "How do you enter town?",
                [
                    self.quoted_option("INSIGHT", "I want to read the mood of the town before I speak."),
                    self.quoted_option("PERSUASION", "Let them know Greywake sent help."),
                    self.skill_tag("INVESTIGATION", self.action_option("Survey the tracks, barricades, and weak points first.")),
                ]
                + [text for _, text in self.scene_identity_options("phandalin_arrival")],
                allow_meta=False,
            )
            identity_options = self.scene_identity_options("phandalin_arrival")
            if choice > 3:
                selection_key, _ = identity_options[choice - 4]
                if self.handle_scene_identity_action("phandalin_arrival", selection_key):
                    return self.scene_phandalin_hub()
            elif choice == 1:
                self.player_speaker("I want to read the mood of the town before I speak.")
                success = self.skill_check(self.state.player, "Insight", 12, context="to gauge the town's fear")
                if success:
                    self.say(
                        "You catch the way fear keeps pulling the crowd's attention toward manor-side ruins, the east road, and a handful of people everybody seems to quietly trust."
                    )
                    self.add_clue(
                        "Iron Hollow's fear points in three directions: the east road, the old manor hill, and the few locals still holding the place together."
                    )
                    self.add_clue(
                        "Old evacuation marks and nervous traffic patterns point toward Cinderfall Ruins, an abandoned relay east of Ashfall Watch."
                    )
                    self.unlock_act1_hidden_route(
                        "Reading Iron Hollow's fear exposes a third route: the abandoned Cinderfall Ruins, where Ashfall's reserve line still flickers behind the main road."
                    )
                    self.act1_adjust_metric("act1_town_fear", -1)
                    self.reward_party(xp=10, reason="reading Iron Hollow's mood on arrival")
                else:
                    self.say("The town's fear is real, but too tangled to untangle in one glance.")
            elif choice == 2:
                self.player_speaker("Let them know Greywake sent help.")
                success = self.skill_check(self.state.player, "Persuasion", 12, context="to steady the town's nerves")
                if success:
                    self.say("A few shoulders ease as your words sound more like a promise than a performance.")
                    self.act1_adjust_metric("act1_town_fear", -1)
                    self.reward_party(xp=10, gold=6, reason="reassuring Iron Hollow on arrival")
                else:
                    self.say("People listen, but frontier caution clings harder than hope.")
            else:
                self.player_action("Show me the tracks, barricades, and weak points first.")
                success = self.skill_check(self.state.player, "Investigation", 12, context="to assess the town's defenses")
                if success:
                    self.say("Fresh wagon ruts, anxious repairs, and redirected lanes give you a usable picture of how fear is reshaping the town.")
                    self.add_clue("Recent wagon ruts suggest the Ashen Brand watches both the east road and the manor-side lanes.")
                    self.reward_party(xp=10, reason="surveying Iron Hollow's defenses")
                else:
                    self.say("There are too many overlapping tracks and half-finished repairs for a quick clean read.")

        self.run_phandalin_council_event()
        self.run_after_watch_gathering()
        self._sync_story_beats_from_flags()
        self.maybe_offer_act1_personal_quests()
        self.maybe_resolve_bryn_loose_ends()
        self.maybe_run_act1_companion_conflict()

        while True:
            options: list[tuple[str, str]] = []
            if self.has_steward_interactions():
                options.append(("steward", self.action_option("Report to Steward Tessa Harrow")))
            options.append(("inn", self.action_option("Visit the Ashlamp Inn")))
            if self.has_shrine_interactions():
                options.append(("shrine", self.action_option("Stop by the Lantern shrine")))
            options.extend(
                [
                    ("barthen", self.skill_tag("TRADE", self.action_option("Browse Hadrik's Provisions"))),
                    ("linene", self.skill_tag("TRADE", self.action_option("Call on Linene Ironward at the Ironbound trading post"))),
                ]
            )
            if self.has_edermath_orchard_interactions():
                options.append(("orchard", self.action_option("Walk the old walls of Orchard Wall")))
            if self.has_miners_exchange_interactions():
                options.append(("exchange", self.action_option("Step into the Delvers' Exchange")))
            options.extend(
                [
                    ("camp", self.action_option("Return to camp")),
                    ("rest", self.action_option("Take a short rest")),
                ]
            )
            if not self.state.flags.get("old_owl_well_cleared"):
                label = self.action_option("Investigate Blackglass Well")
                if not self.can_visit_old_owl_well():
                    label = self.action_option("Investigate Blackglass Well (need a lead)")
                options.append(("old_owl", label))
            if not self.state.flags.get("wyvern_tor_cleared"):
                label = self.action_option("Hunt the raiders at Red Mesa Hold")
                if not self.can_visit_wyvern_tor():
                    label = self.action_option("Hunt the raiders at Red Mesa Hold (need a lead)")
                elif self.should_warn_for_wyvern_tor():
                    label = self.action_option(
                        f"Hunt the raiders at Red Mesa Hold (recommended level {self.wyvern_tor_recommended_level()})"
                    )
                options.append(("wyvern", label))
            if (
                not self.state.flags.get("ashfall_watch_cleared")
                and not self.state.flags.get("cinderfall_ruins_cleared")
                and self.can_visit_cinderfall_ruins()
            ):
                options.append(("cinderfall", self.action_option("Investigate Cinderfall Ruins")))
            if not self.state.flags.get("ashfall_watch_cleared"):
                label = self.action_option("Ride for Ashfall Watch")
                if not self.act1_side_paths_cleared():
                    label = self.action_option("Ride for Ashfall Watch (clear Blackglass Well and Red Mesa Hold first)")
                options.append(("ashfall", label))
            elif not self.state.flags.get("tresendar_cleared"):
                label = self.action_option("Descend beneath Duskmere Manor")
                if not self.state.flags.get("tresendar_revealed"):
                    label = self.action_option("Descend beneath Duskmere Manor (wait for a firmer lead)")
                options.append(("tresendar", label))
            else:
                options.append(("emberhall", self.action_option("Descend into Emberhall Cellars")))

            backtrack_node = self.peek_act1_overworld_backtrack_node()
            if backtrack_node is not None:
                options.append(("backtrack", self.skill_tag("BACKTRACK", self.action_option(f"Backtrack to {backtrack_node.title}"))))

            choice = self.scenario_choice("Where do you go next?", [text for _, text in options], echo_selection=True)
            selection_key, _ = options[choice - 1]
            if selection_key == "steward":
                self.visit_steward()
            elif selection_key == "inn":
                self.visit_stonehill_inn()
            elif selection_key == "shrine":
                self.visit_shrine()
            elif selection_key == "barthen":
                self.visit_barthen_provisions()
            elif selection_key == "linene":
                self.visit_trading_post()
            elif selection_key == "orchard":
                self.visit_edermath_orchard()
            elif selection_key == "exchange":
                self.visit_miners_exchange()
            elif selection_key == "camp":
                self.open_camp_menu()
            elif selection_key == "rest":
                self.short_rest()
            elif selection_key == "backtrack":
                if not self.backtrack_act1_overworld_node():
                    self.say("There is no familiar route to backtrack right now.")
                    continue
                return
            elif selection_key == "old_owl":
                if not self.can_visit_old_owl_well():
                    self.say("You need a firmer lead on the well before marching the party into empty scrub.")
                    continue
                self.travel_to_act1_node("old_owl_well")
                return
            elif selection_key == "wyvern":
                if not self.can_visit_wyvern_tor():
                    self.say("You still need somebody to point you toward the tor and the raiders haunting it.")
                    continue
                if not self.confirm_wyvern_tor_departure():
                    continue
                self.travel_to_act1_node("wyvern_tor")
                return
            elif selection_key == "cinderfall":
                if not self.can_visit_cinderfall_ruins():
                    self.say("You do not have a clean enough read on the hidden relay route yet.")
                    continue
                self.travel_to_act1_node("cinderfall_ruins")
                return
            elif selection_key == "ashfall":
                if not self.act1_side_paths_cleared():
                    self.say("Ashfall Watch is still too dangerous to take cleanly without dealing with the outer threats first.")
                    continue
                self.travel_to_act1_node("ashfall_watch")
                return
            elif selection_key == "tresendar":
                if not self.state.flags.get("tresendar_revealed"):
                    self.say("You need a firmer lead before committing to the buried manor routes.")
                    continue
                self.travel_to_act1_node("tresendar_manor")
                return
            else:
                self.travel_to_act1_node("emberhall_cellars")
                return

    def scene_old_owl_well(self) -> None:
        self.run_act1_dungeon("old_owl_well")

    def scene_blackwake_crossing(self) -> None:
        self.run_act1_dungeon("blackwake_crossing")

    def scene_road_decision_post_blackwake(self) -> None:
        assert self.state is not None
        self.banner("Road Decision After Blackwake")
        resolution = str(self.state.flags.get("blackwake_resolution", "unresolved"))
        self.say(
            "Blackwake Crossing falls behind you in wet ash, broken crate slats, and frightened testimony. "
            "The road has not become safer, exactly, but it has become more honest about what is hunting it.",
            typed=True,
        )
        options: list[tuple[str, str]] = [
            ("neverwinter", self.action_option("Return to Greywake with what you found.")),
            ("south", self.action_option("Press south toward the road to Iron Hollow.")),
            ("camp", self.action_option("Camp first, then decide.")),
        ]
        backtrack_node = self.peek_act1_overworld_backtrack_node()
        if backtrack_node is not None:
            options.append(("backtrack", self.skill_tag("BACKTRACK", self.action_option(f"Backtrack to {backtrack_node.title}"))))
        choice = self.scenario_choice("Where do you go now?", [text for _, text in options], allow_meta=False)
        selection_key, _ = options[choice - 1]
        if selection_key == "neverwinter":
            self.player_action("Return to Greywake with what you found.")
            self.state.flags["blackwake_return_destination"] = "neverwinter"
            self.speaker(
                "Mira Thann",
                "This is too close to the city to dismiss as frontier noise. Give me the names, the routes, and what you chose to leave standing.",
            )
            if not self.state.flags.get("blackwake_neverwinter_reported"):
                self.state.flags["blackwake_neverwinter_reported"] = True
                if resolution == "evidence":
                    self.reward_party(xp=20, gold=18, reason="bringing Blackwake proof back to Greywake")
                    self.say("Mira pays for the ledgers without pretending coin is the point.")
                elif resolution == "rescue":
                    self.add_inventory_item("potion_healing", 1, source="Mira's emergency stores")
                    self.say("Mira sends aid back toward the survivors before she finishes reading your account.")
                elif resolution == "sabotage":
                    self.add_inventory_item("antitoxin_vial", 1, source="a seized city-side medicine pouch")
                    self.say("Mira cannot prosecute ashes, but she can use the damage to tighten the next patrol net.")
                if self.state.flags.get("neverwinter_private_room_intel") and not self.state.flags.get("neverwinter_contract_house_blackwake_reported"):
                    self.state.flags["neverwinter_contract_house_blackwake_reported"] = True
                    self.state.flags["neverwinter_contract_house_political_callback"] = True
                    self.reward_party(xp=15, gold=10, reason="turning contract-house witnesses into Greywake pressure")
                    self.speaker(
                        "Sabra Kestrel",
                        "That is the same correction hand. Blackwake did not steal the manifests after the fact; someone in the city pre-taught the road where to bleed.",
                    )
                    self.speaker(
                        "Oren Vale",
                        "My room can swear to the booking. Vessa can swear to the buyer phrase. Garren can swear no honest roadwarden writes that cadence.",
                    )
                    self.speaker(
                        "Vessa Marr",
                        "I can swear to a great many things, provided everyone understands how expensive honesty becomes once officials start needing it.",
                    )
                    self.speaker(
                        "Garren Flint",
                        "Put my name under the roadwarden line. If a bad seal works because good officers got tired, then tired is done being an excuse.",
                    )
                    self.speaker(
                        "Mira Thann",
                        "Good. Then this stops being rumor and becomes pressure. I can make Greywake's quiet offices answer a thing they can no longer call frontier panic.",
                    )
                    self.add_journal(
                        "Oren, Sabra, Vessa, and Garren backed your Blackwake report, turning the contract-house intel into Greywake political pressure against the false-manifest circuit."
                    )
            self.turn_in_quest("trace_blackwake_cell", giver="Mira Thann")
            self.say("With the report made, the south road waits again. The Iron Hollow writ is still yours to carry.")
            self.travel_to_act1_node("high_road_ambush")
            return
        if selection_key == "south":
            self.player_action("Press south toward the road to Iron Hollow.")
            self.state.flags["blackwake_return_destination"] = "south_road"
            if resolution == "sabotage":
                self.say("Behind you, the ruined cache leaves the Ashen Brand's next road crew short on warning, arrows, and patience.")
            elif resolution == "evidence":
                self.say("The copied route marks ride in your pack, making every broken wagon ahead feel less random.")
            elif resolution == "rescue":
                self.say("The rescued survivors' names travel south with you, carried as proof that the road still has people worth saving.")
            self.travel_to_act1_node("high_road_ambush")
            return
        if selection_key == "camp":
            self.player_action("Camp first, then decide.")
            self.open_camp_menu()
            self.say("The fire burns low. Blackwake is behind you; Greywake and Iron Hollow both still have claims on the morning.")
            return
        if not self.backtrack_act1_overworld_node():
            self.say("There is no familiar Blackwake route to backtrack right now.")

    def scene_wyvern_tor(self) -> None:
        self.run_act1_dungeon("wyvern_tor")

    def scene_cinderfall_ruins(self) -> None:
        self.run_act1_dungeon("cinderfall_ruins")

    def scene_ashfall_watch(self) -> None:
        self.run_act1_dungeon("ashfall_watch")

    def scene_tresendar_manor(self) -> None:
        self.run_act1_dungeon("tresendar_manor")

    def scene_emberhall_cellars(self) -> None:
        self.run_act1_dungeon("emberhall_cellars")

    def scene_stonehollow_dig(self) -> None:
        if self.state is not None:
            self.state.current_scene = "stonehollow_dig"
        self.run_act2_dungeon("stonehollow_dig")

    def scene_glasswater_intake(self) -> None:
        if self.state is not None:
            self.state.current_scene = "glasswater_intake"
        self.run_act2_dungeon("glasswater_intake")

    def scene_siltlock_counting_house(self) -> None:
        if self.state is not None:
            self.state.current_scene = "siltlock_counting_house"
        self.run_act2_dungeon("siltlock_counting_house")

    def scene_broken_prospect(self) -> None:
        if self.state is not None:
            self.state.current_scene = "broken_prospect"
        self.run_act2_dungeon("broken_prospect")

    def scene_south_adit(self) -> None:
        if self.state is not None:
            self.state.current_scene = "south_adit"
        self.run_act2_dungeon("south_adit")

    def scene_wave_echo_outer_galleries(self) -> None:
        if self.state is not None:
            self.state.current_scene = "wave_echo_outer_galleries"
        self.run_act2_dungeon("wave_echo_outer_galleries")

    def scene_black_lake_causeway(self) -> None:
        if self.state is not None:
            self.state.current_scene = "black_lake_causeway"
        self.run_act2_dungeon("black_lake_causeway")

    def scene_blackglass_relay_house(self) -> None:
        if self.state is not None:
            self.state.current_scene = "blackglass_relay_house"
        self.run_act2_dungeon("blackglass_relay_house")

    def scene_forge_of_spells(self) -> None:
        if self.state is not None:
            self.state.current_scene = "forge_of_spells"
        self.run_act2_dungeon("forge_of_spells")

    def run_act1_dungeon(self, node_id: str) -> None:
        assert self.state is not None
        self.act1_initialize_metrics()
        self._sync_map_state_with_scene(force_node_id=node_id)
        node = ACT1_HYBRID_MAP.nodes[node_id]
        dungeon = ACT1_HYBRID_MAP.dungeons[str(node.enters_dungeon_id)]
        self.banner(node.title)
        self.render_act1_dungeon_map(dungeon, force=True)

        while self.state is not None and self.state.current_scene == node.scene_key:
            self._consume_act1_dungeon_transition_feedback(dungeon)
            room = self.current_act1_room(dungeon)
            if not self.room_is_cleared(room.room_id):
                self._run_act1_room(node_id, dungeon, room)
                if self.state.current_scene != node.scene_key:
                    return
                continue

            exits = current_room_exits(dungeon, self.act1_map_state())
            remaining_open_rooms = [
                candidate
                for candidate in dungeon.rooms.values()
                if candidate.room_id != room.room_id
                and not self.room_is_cleared(candidate.room_id)
                and requirement_met(self.act1_map_state(), candidate.requirement)
            ]
            if not exits and remaining_open_rooms:
                self.say(f"{room.title} is secure, but another wing is still open: {remaining_open_rooms[0].title}.")

            options = self.act1_room_navigation_options(dungeon)

            choice = self.scenario_choice(
                f"What do you do from {room.title}?",
                [text for _, _, text in options],
                allow_meta=False,
            )
            action, destination, _ = options[choice - 1]
            action_kind, _, action_direction = action.partition(":")
            if action_kind == "move":
                next_room = dungeon.rooms[destination]
                self.set_current_map_room(
                    destination,
                    announce=True,
                    movement_text=f"You move {(action_direction or room_direction(room, next_room, dungeon)).lower()} toward {next_room.title}.",
                )
                continue
            if action_kind == "backtrack":
                if not self.backtrack_map_room(dungeon):
                    self.say("There is nowhere useful to backtrack from here.")
                continue
            if action_kind == "overworld_backtrack":
                if not self.backtrack_act1_overworld_node():
                    self.say("There is no familiar overworld route to backtrack right now.")
                    continue
                return
            if dungeon.exit_to_node_id == "road_decision_post_blackwake":
                self.return_to_blackwake_decision(f"You pull back from {node.title} and regroup on the road beyond the river cut.")
                return
            self.return_to_phandalin(f"You withdraw from {node.title} and ride back to Iron Hollow to regroup.")
            return

    def _run_act1_room(self, node_id: str, dungeon: DungeonMap, room: DungeonRoom) -> None:
        handlers = {
            ("blackwake_crossing", "charred_tollhouse"): self._blackwake_charred_tollhouse,
            ("blackwake_crossing", "millers_ford_flooded_approach"): self._blackwake_flooded_approach,
            ("blackwake_crossing", "wagon_snarl"): self._blackwake_wagon_snarl,
            ("blackwake_crossing", "reedbank_camp"): self._blackwake_reedbank_camp,
            ("blackwake_crossing", "ford_ledger_post"): self._blackwake_ford_ledger_post,
            ("blackwake_crossing", "gallows_hanging_path"): self._blackwake_hanging_path,
            ("blackwake_crossing", "cage_clearing"): self._blackwake_cage_clearing,
            ("blackwake_crossing", "watcher_tree"): self._blackwake_watcher_tree,
            ("blackwake_crossing", "root_cellar_hollow"): self._blackwake_root_cellar_hollow,
            ("blackwake_crossing", "outer_cache"): self._blackwake_outer_cache,
            ("blackwake_crossing", "prison_pens"): self._blackwake_prison_pens,
            ("blackwake_crossing", "seal_workshop"): self._blackwake_seal_workshop,
            ("blackwake_crossing", "ash_office"): self._blackwake_ash_office,
            ("blackwake_crossing", "floodgate_chamber"): self._blackwake_floodgate_chamber,
            ("old_owl_well", "well_ring"): self._old_owl_well_ring,
            ("old_owl_well", "salt_cart"): self._old_owl_salt_cart,
            ("old_owl_well", "supply_trench"): self._old_owl_supply_trench,
            ("old_owl_well", "gravecaller_lip"): self._old_owl_gravecaller_lip,
            ("wyvern_tor", "goat_path"): self._wyvern_goat_path,
            ("wyvern_tor", "drover_hollow"): self._wyvern_drover_hollow,
            ("wyvern_tor", "shrine_ledge"): self._wyvern_shrine_ledge,
            ("wyvern_tor", "high_shelf"): self._wyvern_high_shelf,
            ("cinderfall_ruins", "collapsed_gate"): self._cinderfall_collapsed_gate,
            ("cinderfall_ruins", "ash_chapel"): self._cinderfall_ash_chapel,
            ("cinderfall_ruins", "broken_storehouse"): self._cinderfall_broken_storehouse,
            ("cinderfall_ruins", "ember_relay"): self._cinderfall_ember_relay,
            ("ashfall_watch", "breach_gate"): self._ashfall_breach_gate,
            ("ashfall_watch", "prisoner_yard"): self._ashfall_prisoner_yard,
            ("ashfall_watch", "signal_basin"): self._ashfall_signal_basin,
            ("ashfall_watch", "lower_barracks"): self._ashfall_lower_barracks,
            ("ashfall_watch", "rukhar_command"): self._ashfall_rukhar_command,
            ("tresendar_manor", "hidden_stair"): self._tresendar_hidden_stair,
            ("tresendar_manor", "cellar_intake"): self._tresendar_cellar_intake,
            ("tresendar_manor", "cistern_walk"): self._tresendar_cistern_walk,
            ("tresendar_manor", "cage_store"): self._tresendar_cage_store,
            ("tresendar_manor", "nothic_lair"): self._tresendar_nothic_lair,
            ("emberhall_cellars", "antechamber"): self._emberhall_antechamber,
            ("emberhall_cellars", "ledger_chain"): self._emberhall_ledger_chain,
            ("emberhall_cellars", "ash_archive"): self._emberhall_ash_archive,
            ("emberhall_cellars", "black_reserve"): self._emberhall_black_reserve,
            ("emberhall_cellars", "varyn_sanctum"): self._emberhall_varyn_sanctum,
        }
        handler = handlers[(node_id, room.room_id)]
        previous_context = getattr(self, "_post_combat_random_encounter_context", None)
        self._post_combat_random_encounter_context = {"act": 1, "room_role": room.role, "room_id": room.room_id}
        try:
            handler(dungeon, room)
        finally:
            if previous_context is None:
                delattr(self, "_post_combat_random_encounter_context")
            else:
                self._post_combat_random_encounter_context = previous_context

    def _blackwake_adjust_named_companion(self, name: str, delta: int, reason: str) -> None:
        companion = self.find_companion(name)
        if companion is not None:
            self.adjust_companion_disposition(companion, delta, reason)

    def _blackwake_mid_route_count(self) -> int:
        assert self.state is not None
        return sum(
            1
            for flag_name in ("blackwake_forged_papers_found", "blackwake_transfer_list_found")
            if self.state.flags.get(flag_name)
        )

    def _blackwake_charred_tollhouse(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say(
            "The tollhouse at the river cut is a blackened frame around stunned survivors, dead coals, and a torn inspection board. "
            "The attackers took ledgers, seals, and anyone who could explain the route marks.",
            typed=True,
        )
        enemies = [create_enemy("brand_saboteur"), create_enemy("bandit")]
        hero_bonus = self.apply_scene_companion_support("blackwake_crossing")
        avoid_fight = False
        choice = self.scenario_choice(
            "What do you do first at the burned tollhouse?",
            [
                self.skill_tag("INVESTIGATION", self.action_option("Reconstruct what was taken from the inspection room.")),
                self.skill_tag("MEDICINE", self.action_option("Stabilize a burned guard before their testimony fades.")),
                self.skill_tag("INTIMIDATION", self.action_option("Force a panicked mercenary to stop babbling and name facts.")),
                self.skill_tag("PERSUASION", self.action_option("Calm the survivors and organize clean testimony.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Reconstruct what was taken from the inspection room.")
            if self.skill_check(self.state.player, "Investigation", 12, context="to read the burned tollhouse before the trail goes cold"):
                self.state.flags["blackwake_millers_ford_lead"] = True
                self.add_clue("The tollhouse thieves wanted seals, route slates, and ledgers tied to Miller's Ford inspections.")
                enemies[0].current_hp = max(1, enemies[0].current_hp - 3)
                hero_bonus += 1
                self.say("The missing shelves point cleanly toward a forged checkpoint at Miller's Ford.")
            else:
                self.add_clue("The tollhouse evidence is damaged, but the thieves cared more about route authority than coin.")
                self.say("You cannot save the whole pattern, but the ashes still point toward organized papers, not random banditry.")
        elif choice == 2:
            self.player_action("Stabilize a burned guard before their testimony fades.")
            if self.skill_check(self.state.player, "Medicine", 12, context="to keep the burned guard coherent"):
                self.state.flags["blackwake_gallows_copse_lead"] = True
                self.state.flags["blackwake_survivors_saved"] = int(self.state.flags.get("blackwake_survivors_saved", 0) or 0) + 1
                self.add_clue("A rescued guard heard prisoners moved toward old hanging trees south of the river cut.")
                self._blackwake_adjust_named_companion("Rhogar Valeguard", 1, "you protected the burned guard before chasing proof")
                self.say("The guard lives long enough to name a prisoner route through Gallows Copse.")
            else:
                self.say("You keep the guard breathing, but only fragments survive: cages, dead trees, and soot-marked crate rope.")
        elif choice == 3:
            self.player_action("Force a panicked mercenary to stop babbling and name facts.")
            if self.skill_check(self.state.player, "Intimidation", 12, context="to turn panic into usable testimony"):
                self.state.flags["blackwake_millers_ford_lead"] = True
                self.apply_status(enemies[0], "frightened", 1, source="your hard-edged command")
                hero_bonus += 1
                self.say("The mercenary finally says the words that matter: false roadwardens, a ford ledger, and black ash on the permit wax.")
            else:
                self.apply_status(self.state.player, "reeling", 1, source="too many shouted accounts")
                self.say("The panic gives you direction, but not without wasting precious minutes.")
        else:
            self.player_action("Calm the survivors and organize clean testimony.")
            if self.skill_check(self.state.player, "Persuasion", 12, context="to steady the tollhouse survivors"):
                self.state.flags["blackwake_gallows_copse_lead"] = True
                self.state.flags["blackwake_survivors_saved"] = int(self.state.flags.get("blackwake_survivors_saved", 0) or 0) + 1
                self._blackwake_adjust_named_companion("Elira Dawnmantle", 1, "you made the frightened survivors people before evidence")
                avoid_fight = True
                self.say("The survivors spot the saboteur trying to blend into the crowd, and the whole yard turns on them before a real fight forms.")
            else:
                self.say("You settle enough voices to learn there were prisoners, but not enough to stop the saboteur from making a break for it.")

        if not avoid_fight:
            outcome = self.run_encounter(
                Encounter(
                    title="Charred Tollhouse Breakout",
                    description="A saboteur and hired blade try to erase the last witnesses before you can organize pursuit.",
                    enemies=enemies,
                    allow_flee=True,
                    allow_parley=True,
                    parley_dc=12,
                    hero_initiative_bonus=hero_bonus,
                    allow_post_combat_random_encounter=False,
                )
            )
            if outcome == "defeat":
                self.handle_defeat("The Blackwake trail burns out before it can be followed.")
                return
            if outcome == "fled":
                self.return_to_blackwake_decision("You pull away from the tollhouse before the smoke-trail can close cleanly.")
                return
        self.complete_map_room(dungeon, room.room_id)
        self.reward_party(xp=15, gold=6, reason="stabilizing the Blackwake tollhouse")
        self.say("Two routes remain readable through the damage: Miller's Ford for forged authority, and Gallows Copse for prisoners and fear.")

    def _blackwake_flooded_approach(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("Cold floodwater chews at the ford stones while wrecked carts pin draft horses against the current.")
        choice = self.scenario_choice(
            "How do you approach Miller's Ford?",
            [
                self.skill_tag("SURVIVAL", self.action_option("Cross safely and find the flank through the shallows.")),
                self.skill_tag("ANIMAL HANDLING", self.action_option("Calm the trapped horse teams before panic breaks them.")),
                self.skill_tag("STEALTH", self.action_option("Survey the false checkpoint before anyone notices you.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Cross safely and find the flank through the shallows.")
            if self.skill_check(self.state.player, "Survival", 12, context="to read the ford current and hidden shelf"):
                self.state.flags["blackwake_ford_flank"] = True
                self.say("The current shows you a dry shelf behind the checkpoint tents.")
        elif choice == 2:
            self.player_action("Calm the trapped horse teams before panic breaks them.")
            if self.skill_check(self.state.player, "Animal Handling", 12, context="to settle the trapped teams"):
                self.state.flags["blackwake_survivors_saved"] = int(self.state.flags.get("blackwake_survivors_saved", 0) or 0) + 1
                self.state.flags["blackwake_horse_teams_saved"] = True
                self._blackwake_adjust_named_companion("Rhogar Valeguard", 1, "you risked time to save the ford teams")
                self.say("The teams stop thrashing, which keeps the whole wreck from turning into a second disaster.")
        else:
            self.player_action("Survey the false checkpoint before anyone notices you.")
            if self.skill_check(self.state.player, "Stealth", 12, context="to watch Miller's Ford unseen"):
                self.state.flags["blackwake_ford_surveyed"] = True
                self._blackwake_adjust_named_companion("Kaelis Starling", 1, "you read the ford before triggering its alarm")
                self.say("You count the hired guards, the believers, and the tent where the seals are being copied.")
        self.complete_map_room(dungeon, room.room_id)

    def _blackwake_wagon_snarl(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("The wagon snarl is a knot of axles, splintered cargo ribs, and teamsters tied where the false wardens could use them as leverage.")
        choice = self.scenario_choice(
            "What do you prioritize in the wagon snarl?",
            [
                self.action_option("Cut civilians free before cargo or cover."),
                self.action_option("Secure the cargo before the smugglers can move it."),
                self.action_option("Overturn carts for cover and prepare an ambush."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Cut civilians free before cargo or cover.")
            self.state.flags["blackwake_survivors_saved"] = int(self.state.flags.get("blackwake_survivors_saved", 0) or 0) + 2
            self._blackwake_adjust_named_companion("Elira Dawnmantle", 1, "you put trapped teamsters ahead of cargo")
            self.say("The teamsters scatter, then return with enough courage to point out which tent the clerk was dragged into.")
        elif choice == 2:
            self.player_action("Secure the cargo before the smugglers can move it.")
            self.state.flags["blackwake_cargo_secured"] = True
            self.reward_party(gold=8, reason="recovering intact ford cargo")
            self.say("You save flour, lamp oil, and one locked strongbox whose wax matches the false permits.")
        else:
            self.player_action("Overturn carts for cover and prepare an ambush.")
            self.state.flags["blackwake_ford_ambush_prepared"] = True
            self.say("The carts become a fighting wall. Whoever holds the ledger post will have to come through your ground.")
        self.complete_map_room(dungeon, room.room_id)

    def _blackwake_reedbank_camp(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("The reedbank camp looks official from a distance: checkpoint tent, wax kit, blank permits, and a stolen roadwarden cloak drying over a spear.")
        choice = self.scenario_choice(
            "How do you work the forged checkpoint tent?",
            [
                self.skill_tag("STEALTH", self.action_option("Steal the seal kit and papers quietly.")),
                self.skill_tag("INTIMIDATION", self.action_option("Drag the lookout behind the reeds and make them talk.")),
                self.skill_tag("INVESTIGATION", self.action_option("Copy the names and route marks before disturbing anything.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Steal the seal kit and papers quietly.")
            if self.skill_check(self.state.player, "Stealth", 12, context="to lift the forged permit kit"):
                self.state.flags["blackwake_route_permits_found"] = True
                self.state.flags["blackwake_forged_papers_found"] = True
                self.add_clue("Forged route permits from Miller's Ford name Blackwake Store Cavern as the next handling point.")
                self._blackwake_adjust_named_companion("Bryn Underbough", 1, "you stole the paperwork before anyone could sanitize it")
        elif choice == 2:
            self.player_action("Drag the lookout behind the reeds and make them talk.")
            if self.skill_check(self.state.player, "Intimidation", 12, context="to break the lookout's false authority"):
                self.state.flags["blackwake_lookout_interrogated"] = True
                self.add_clue("A Reedbank lookout says someone in Greywake is paid to ignore missing toll seals.")
                self.say("The lookout gives up the cave name and keeps insisting the city side is not as clean as Mira hopes.")
        else:
            self.player_action("Copy the names and route marks before disturbing anything.")
            if self.skill_check(self.state.player, "Investigation", 12, context="to copy the forged route marks accurately"):
                self.state.flags["blackwake_route_names_copied"] = True
                self.state.flags["blackwake_forged_papers_found"] = True
                self.add_clue("Copied route marks tie Blackwake permits to a Greywake-facing paymaster mark.")
                self.say("The route marks are ugly in the useful way: repeatable, provable, and too neat to be local chaos.")
        self.complete_map_room(dungeon, room.room_id)

    def _blackwake_ford_ledger_post(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("At the ledger post, false roadwardens shout seizure orders while hired guards start wondering whether the papers are worth dying for.")
        enemies = [create_enemy("brand_saboteur"), create_enemy("bandit")]
        if self.act1_party_size() >= 3 and not self.state.flags.get("blackwake_ford_ambush_prepared"):
            enemies.append(create_enemy("bandit_archer"))
        hero_bonus = 1 if self.state.flags.get("blackwake_ford_flank") else 0
        avoid_fight = False
        choice = self.scenario_choice(
            "How do you break the ledger post?",
            [
                self.skill_tag("DECEPTION", self.action_option("Pose as higher authority and order the seizure halted.")),
                self.skill_tag("PERSUASION", self.action_option("Split the hired guards from the true loyalists.")),
                self.skill_tag("ATHLETICS", self.action_option("Rush the barricade before they settle behind it.")),
                self.skill_tag("INVESTIGATION", self.action_option("Use the seized ledgers to expose the fraud publicly.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Pose as higher authority and order the seizure halted.")
            if self.skill_check(self.state.player, "Deception", 13, context="to outrank the false roadwardens with their own lies"):
                avoid_fight = True
                self.state.flags["blackwake_forged_papers_found"] = True
                self._blackwake_adjust_named_companion("Bryn Underbough", 1, "you beat forged authority with a cleaner lie")
                self.say("The false wardens hesitate just long enough for the hired blades to decide they were never paid for this.")
        elif choice == 2:
            self.player_action("Split the hired guards from the true loyalists.")
            if self.skill_check(self.state.player, "Persuasion", 13, context="to separate fear from loyalty at the ledger post"):
                enemies = enemies[:1]
                hero_bonus += 1
                self.say("Most of the hired guards back away when the fraud becomes obvious enough to survive.")
        elif choice == 3:
            self.player_action("Rush the barricade before they settle behind it.")
            if self.skill_check(self.state.player, "Athletics", 12, context="to break the ford barricade"):
                self.apply_status(enemies[0], "prone", 1, source="your barricade rush")
                hero_bonus += 2
                self.say("The barricade folds inward and the saboteur loses the first clean breath of the fight.")
        else:
            self.player_action("Use the seized ledgers to expose the fraud publicly.")
            if self.skill_check(self.state.player, "Investigation", 12, context="to prove the checkpoint's authority is forged"):
                avoid_fight = True
                self.state.flags["blackwake_forged_papers_found"] = True
                self.add_clue("Miller's Ford ledgers prove the Ashen Brand was selecting cargo by route value, not raiding blindly.")
                self.say("The crowd hears enough names and dates that the checkpoint authority collapses in daylight.")

        if not avoid_fight:
            outcome = self.run_encounter(
                Encounter(
                    title="Miller's Ford Ledger Post",
                    description="False roadwardens try to keep their fraud alive with steel.",
                    enemies=enemies,
                    allow_flee=True,
                    allow_parley=True,
                    parley_dc=13,
                    hero_initiative_bonus=hero_bonus,
                    allow_post_combat_random_encounter=False,
                )
            )
            if outcome == "defeat":
                self.handle_defeat("The Miller's Ford fraud holds long enough to swallow the Blackwake trail.")
                return
            if outcome == "fled":
                self.return_to_blackwake_decision("You break away from Miller's Ford with only partial proof and too many riders behind you.")
                return
        self.state.flags["blackwake_forged_papers_found"] = True
        self.complete_map_room(dungeon, room.room_id)
        self.reward_party(xp=20, gold=8, reason="securing Miller's Ford")
        self.say("The seized papers name a riverside store cavern downstream: Blackwake's hidden cache.")

    def _blackwake_hanging_path(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("Gallows Copse begins with dead branches, staged warning charms, and cage marks dragged through old leaves.")
        choice = self.scenario_choice(
            "How do you approach the hanging path?",
            [
                self.skill_tag("RELIGION", self.action_option("Read whether the symbols are true rite or staged fear.")),
                self.skill_tag("PERCEPTION", self.action_option("Detect hidden sentries before they decide the route.")),
                self.skill_tag("STEALTH", self.action_option("Approach without triggering the copse alarm.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Read whether the symbols are true rite or staged fear.")
            if self.skill_check(self.state.player, "Religion", 12, context="to separate ritual from intimidation"):
                self.state.flags["blackwake_fear_symbols_staged"] = True
                self.say("The charms are theater: frightening, cheap, and checked often by living hands.")
        elif choice == 2:
            self.player_action("Detect hidden sentries before they decide the route.")
            if self.skill_check(self.state.player, "Perception", 12, context="to pick sentries out of the hanging branches"):
                self.state.flags["blackwake_copse_sentries_spotted"] = True
                self.say("You catch two sentry nests and the route they use to report prisoner movement.")
        else:
            self.player_action("Approach without triggering the copse alarm.")
            if self.skill_check(self.state.player, "Stealth", 12, context="to move through Gallows Copse unseen"):
                self.state.flags["blackwake_copse_alarm_prevented"] = True
                self._blackwake_adjust_named_companion("Kaelis Starling", 1, "you kept Gallows Copse quiet long enough to read it")
                self.say("The copse stays quiet, which makes every later choice less rushed.")
            else:
                self.state.flags["blackwake_copse_alarm_triggered"] = True
                self.say("A warning charm cracks underfoot. The alarm is not loud, but it is enough.")
        self.complete_map_room(dungeon, room.room_id)

    def _blackwake_cage_clearing(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("Cages hang low between dead trunks. The captives inside have learned to whisper only when the wind moves.")
        choice = self.scenario_choice(
            "What do you do with the captives?",
            [
                self.action_option("Free the captives now."),
                self.action_option("Question the captives before cutting cages loose."),
                self.action_option("Stay hidden and observe the next transfer pattern."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Free the captives now.")
            self.state.flags["blackwake_survivors_saved"] = int(self.state.flags.get("blackwake_survivors_saved", 0) or 0) + 2
            self.state.flags["blackwake_captive_support_ready"] = True
            self._blackwake_adjust_named_companion("Elira Dawnmantle", 1, "you chose living captives over cleaner intelligence")
            self.say("The freed captives can barely stand, but they can still tell you where the crates go.")
        elif choice == 2:
            self.player_action("Question the captives before cutting cages loose.")
            self.state.flags["blackwake_transfer_pattern_learned"] = True
            self.add_clue("Gallows captives confirm prisoners and seized goods are being funneled to Blackwake Store Cavern.")
            self.say("Their answers are thin with thirst, but the route is clear: cave, floodgate, southbound handoff.")
        else:
            self.player_action("Stay hidden and observe the next transfer pattern.")
            self.state.flags["blackwake_transfer_pattern_learned"] = True
            self.state.flags["blackwake_copse_alarm_prevented"] = True
            self._blackwake_adjust_named_companion("Elira Dawnmantle", -1, "you let prisoners wait in cages for cleaner timing")
            self.say("The wait earns you a transfer rhythm and costs the captives another measure of fear.")
        self.complete_map_room(dungeon, room.room_id)

    def _blackwake_watcher_tree(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("The watcher tree is more scaffold than tree now, full of rope, signal strips, and nailed charms meant to look older than they are.")
        choice = self.scenario_choice(
            "How do you use the watcher tree?",
            [
                self.skill_tag("ATHLETICS", self.action_option("Climb and scout the transfer route.")),
                self.action_option("Cut down the warning charms before they can be checked."),
                self.skill_tag("SURVIVAL", self.action_option("Leave the charms untouched and track who checks them.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Climb and scout the transfer route.")
            if self.skill_check(self.state.player, "Athletics", 12, context="to climb the watcher tree without dropping the alarm strips"):
                self.state.flags["blackwake_cavern_route_scouted"] = True
                self.say("From above, the riverbank route to the store cavern is plain enough to follow after dark.")
        elif choice == 2:
            self.player_action("Cut down the warning charms before they can be checked.")
            self.state.flags["blackwake_copse_alarm_prevented"] = True
            self.say("The charms come down in a dry rattle, leaving the next Brand patrol without its little theater of fear.")
        else:
            self.player_action("Leave the charms untouched and track who checks them.")
            if self.skill_check(self.state.player, "Survival", 12, context="to follow the charm-checker without being seen"):
                self.state.flags["blackwake_transfer_tail"] = True
                self.add_clue("A Gallows Copse charm-checker carries a soot-marked crate tag matching the Blackwake cache route.")
                self.say("The charm-checker leads you to a crate trail without ever knowing the warning system failed.")
        self.complete_map_room(dungeon, room.room_id)

    def _blackwake_root_cellar_hollow(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("Below the roots, transfer crates sit in shallow pits marked by soot, chalk cuts, and prisoner initials scratched under the lids.")
        choice = self.scenario_choice(
            "What do you inspect in the root cellar hollow?",
            [
                self.action_option("Inspect the transfer crates."),
                self.skill_tag("INVESTIGATION", self.action_option("Decode the route symbols.")),
                self.skill_tag("ATHLETICS", self.action_option("Force open the hidden cellar door.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Inspect the transfer crates.")
            self.state.flags["blackwake_soot_crate_route_found"] = True
            self.add_clue("Soot-marked crates show seized goods moving from Gallows Copse to Blackwake Store Cavern before redistribution.")
            self.say("The crates are numbered for storage, not ransom. This is logistics, not rage.")
        elif choice == 2:
            self.player_action("Decode the route symbols.")
            if self.skill_check(self.state.player, "Investigation", 12, context="to decode the Gallows Copse route marks"):
                self.state.flags["blackwake_transfer_list_found"] = True
                self.add_clue("A prisoner transfer list connects Blackwake to wider Ashen Brand staging farther south.")
                self.say("The marks point beyond the cavern: southbound pressure sites, later staging, and one hobgoblin supervision note.")
        else:
            self.player_action("Force open the hidden cellar door.")
            if self.skill_check(self.state.player, "Athletics", 12, context="to break the hidden root cellar door"):
                self.state.flags["blackwake_transfer_list_found"] = True
                self.reward_party(gold=6, reason="recovering coin from a hidden transfer box")
                self.say("The hidden compartment gives up a prisoner list and the petty coin skimmed off their guards.")
        self.state.flags["blackwake_transfer_list_found"] = True
        self.complete_map_room(dungeon, room.room_id)

    def _blackwake_outer_cache(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("Blackwake Store Cavern opens under an old quarry shelf, half flooded and half disguised as a rotten riverside store cut.")
        enemies = [create_enemy("brand_saboteur"), create_enemy("bandit_archer")]
        if self.act1_party_size() >= 3 and self._blackwake_mid_route_count() < 2:
            enemies.append(create_enemy("bandit"))
        hero_bonus = 0
        avoid_fight = False
        choice = self.scenario_choice(
            "How do you enter the outer cache?",
            [
                self.skill_tag("STEALTH", self.action_option("Slip through the loading shadow and bypass the front watch.")),
                self.skill_tag("DECEPTION", self.action_option("Enter as caravan inspectors using the forged papers.")),
                self.skill_tag("ATHLETICS", self.action_option("Break through the outer cache before they seal the passage.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Slip through the loading shadow and bypass the front watch.")
            if self.skill_check(self.state.player, "Stealth", 13, context="to infiltrate the Blackwake outer cache"):
                enemies[0].current_hp = max(1, enemies[0].current_hp - 4)
                self.apply_status(enemies[0], "surprised", 1, source="your cache infiltration")
                hero_bonus += 2
                self._blackwake_adjust_named_companion("Kaelis Starling", 1, "you entered Blackwake without feeding the alarm")
                self.say("You reach the loading cut before the first watchman realizes the shadow has moved.")
        elif choice == 2:
            self.player_action("Enter as caravan inspectors using the forged papers.")
            if self.state.flags.get("blackwake_forged_papers_found") and self.skill_check(
                self.state.player,
                "Deception",
                13,
                context="to pass as higher-route inspectors",
            ):
                avoid_fight = True
                self._blackwake_adjust_named_companion("Bryn Underbough", 1, "you made the stolen papers open the right door")
                self.say("The forged papers carry you past the first watch with the awful ease of a system built to trust itself.")
            else:
                self.state.flags["blackwake_cache_alarm_triggered"] = True
                self.say("The lie catches on one wrong route mark, and the cache watch reaches for weapons.")
        else:
            self.player_action("Break through the outer cache before they seal the passage.")
            if self.skill_check(self.state.player, "Athletics", 13, context="to force the loading gate before it bars shut"):
                self.apply_status(self.state.player, "emboldened", 2, source="breaking into Blackwake Store Cavern")
                hero_bonus += 1
                self.say("The loading gate loses the argument with your shoulder, and the watch line starts the fight scattered.")
        if not avoid_fight:
            outcome = self.run_encounter(
                Encounter(
                    title="Blackwake Outer Cache",
                    description="Cache guards try to keep the riverside entrance from becoming evidence.",
                    enemies=enemies,
                    allow_flee=True,
                    allow_parley=True,
                    parley_dc=13,
                    hero_initiative_bonus=hero_bonus,
                    allow_post_combat_random_encounter=False,
                )
            )
            if outcome == "defeat":
                self.handle_defeat("The Blackwake cache seals around its secrets.")
                return
            if outcome == "fled":
                self.return_to_blackwake_decision("You tear free of the cache entrance before the flood-cut can trap you inside.")
                return
        self.complete_map_room(dungeon, room.room_id)
        self.say("Past the outer cache, the cavern splits between prisoner pens and a seal workshop, both feeding Sereth Vane's office deeper in.")

    def _blackwake_prison_pens(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("The prison pens stink of river damp, old rope, and people held as inventory.")
        choice = self.scenario_choice(
            "What do you do with the prisoners?",
            [
                self.action_option("Free prisoners quietly."),
                self.action_option("Arm prisoners for an uprising."),
                self.action_option("Leave them until Sereth is handled to preserve stealth."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Free prisoners quietly.")
            self.state.flags["blackwake_prisoners_freed_early"] = True
            self.state.flags["blackwake_survivors_saved"] = int(self.state.flags.get("blackwake_survivors_saved", 0) or 0) + 2
            self._blackwake_adjust_named_companion("Elira Dawnmantle", 1, "you risked the cache route to free prisoners early")
            self.say("The prisoners move slowly, but every opened lock takes weight off the final chamber.")
        elif choice == 2:
            self.player_action("Arm prisoners for an uprising.")
            self.state.flags["blackwake_prisoner_uprising"] = True
            self.state.flags["blackwake_survivors_saved"] = int(self.state.flags.get("blackwake_survivors_saved", 0) or 0) + 1
            self.say("The prisoners take knives, pry bars, and one look that says chaos can be a kind of mercy.")
        else:
            self.player_action("Leave them until Sereth is handled to preserve stealth.")
            self.state.flags["blackwake_prisoners_delayed"] = True
            self._blackwake_adjust_named_companion("Elira Dawnmantle", -1, "you left prisoners behind for tactical patience")
            self.say("The stealth remains clean. The prisoners hear you leave them, which is less clean.")
        self.complete_map_room(dungeon, room.room_id)

    def _blackwake_seal_workshop(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("The seal workshop is all wax heat, copied stamps, route ledgers, and benches scarred by hurried knife work.")
        choice = self.scenario_choice(
            "What do you do with the forgery workshop?",
            [
                self.action_option("Seize the forgeries as evidence."),
                self.action_option("Destroy the workshop."),
                self.skill_tag("INVESTIGATION", self.action_option("Copy names and route marks before sabotage.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Seize the forgeries as evidence.")
            self.state.flags["blackwake_evidence_secured"] = True
            self.state.flags["blackwake_forged_papers_found"] = True
            self.add_clue("Blackwake's seal workshop proves the Ashen Brand is manipulating trade with forged authority.")
            self.say("The papers are heavy with names, seals, and the kind of proof officials can no longer politely misunderstand.")
        elif choice == 2:
            self.player_action("Destroy the workshop.")
            self.state.flags["blackwake_workshop_destroyed"] = True
            self.act1_adjust_metric("act1_ashen_strength", -1)
            self.say("Wax, stamp blanks, and route slates crack under deliberate ruin. The next false checkpoint will be harder to stock.")
        else:
            self.player_action("Copy names and route marks before sabotage.")
            if self.skill_check(self.state.player, "Investigation", 13, context="to copy the Blackwake route marks under pressure"):
                self.state.flags["blackwake_route_names_copied"] = True
                self.state.flags["blackwake_evidence_secured"] = True
                self.add_clue("Copied Blackwake marks name route payments, seized cargo categories, and a future Iron Hollow pressure chain.")
                self.say("You take the names before the workshop loses its shape.")
            self.state.flags["blackwake_workshop_destroyed"] = True
        self.complete_map_room(dungeon, room.room_id)

    def _blackwake_ash_office(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say(
            "Sereth's ash office is a command room pretending to be a storeroom: partial Iron Hollow pressure routes, caravan hijack summaries, and a note about hobgoblin supervision farther south."
        )
        choice = self.scenario_choice(
            "Which record do you focus on?",
            [
                self.action_option("Trace the Iron Hollow pressure sites."),
                self.action_option("Read the caravan hijack summaries."),
                self.action_option("Search for the southern supervisor note."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Trace the Iron Hollow pressure sites.")
            self.state.flags["blackwake_phandalin_pressure_clue"] = True
            self.add_clue("Blackwake notes point to Iron Hollow pressure sites and supply timing, not isolated roadside theft.")
        elif choice == 2:
            self.player_action("Read the caravan hijack summaries.")
            self.state.flags["blackwake_caravan_hijack_clue"] = True
            self.add_clue("Blackwake summaries show selective theft: food, medicine, tools, and route authority are taken before luxuries.")
        else:
            self.player_action("Search for the southern supervisor note.")
            self.state.flags["blackwake_hobgoblin_supervision_clue"] = True
            self.add_clue("A Blackwake order references hobgoblin supervision farther south, foreshadowing the Emberway and Ashfall chain.")
        self.complete_map_room(dungeon, room.room_id)

    def _blackwake_floodgate_chamber(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say(
            "The floodgate chamber breathes river-cold air through iron teeth. Prison ropes, seized ledgers, and packed crates all converge under Sereth Vane's calm little smile.",
            typed=True,
        )
        enemies = [create_enemy("sereth_vane")]
        if not self.state.flags.get("blackwake_prisoners_freed_early"):
            enemies.append(create_enemy("brand_saboteur"))
        if self.act1_party_size() >= 3 and self._blackwake_mid_route_count() < 2:
            enemies.append(create_enemy("bandit_archer"))
        hero_bonus = self.apply_scene_companion_support("blackwake_crossing")
        if self._blackwake_mid_route_count() >= 2:
            hero_bonus += 1
            self.say("Because both the ford and the copse are exposed, Sereth has fewer clean orders left to give.")

        talk_options: list[tuple[str, str]] = [
            ("persuasion", self.skill_tag("PERSUASION", self.action_option("Offer prisoners for Sereth's safe withdrawal."))),
            ("intimidation", self.skill_tag("INTIMIDATION", self.action_option("Threaten full exposure and a slaughtered supply line."))),
        ]
        if self.state.flags.get("blackwake_forged_papers_found") or self.state.flags.get("blackwake_transfer_list_found"):
            talk_options.append(("investigation", self.skill_tag("INVESTIGATION", self.action_option("Confront Sereth with specific ledger facts."))))
        if self.state.flags.get("blackwake_forged_papers_found"):
            talk_options.append(("deception", self.skill_tag("DECEPTION", self.action_option("Pretend to represent higher Ashen Brand authority."))))
        if self.state.flags.get("neverwinter_private_room_intel"):
            talk_options.append(
                (
                    "contract_house",
                    self.skill_tag(
                        "CONTRACT HOUSE INTEL",
                        self.action_option("Name the contract-house booking, Sabra's corrected manifest, and the false roadwarden cadence at once."),
                    ),
                )
            )
        talk_options.append(("strike", self.action_option("Strike immediately before Sereth can spoil the room.")))
        choice = self.scenario_choice("Sereth waits to see whether this becomes bargain, threat, or blood.", [text for _, text in talk_options], allow_meta=False)
        talk_key, talk_text = talk_options[choice - 1]
        self.player_choice_output(talk_text)
        if talk_key == "persuasion":
            if self.skill_check(self.state.player, "Persuasion", 14, context="to trade prisoners for Sereth's withdrawal"):
                self.state.flags["blackwake_partial_prisoner_surrender"] = True
                self.apply_status(enemies[0], "reeling", 1, source="your prisoner bargain")
                hero_bonus += 1
                self.say("Sereth gives up half the prisoners to buy room to survive the rest of the conversation.")
            else:
                self.state.flags["blackwake_evidence_burned_by_sereth"] = True
                self.say("Sereth smiles, tips a coalpan into the nearest ledger stack, and lets negotiation become smoke.")
        elif talk_key == "intimidation":
            if self.skill_check(self.state.player, "Intimidation", 14, context="to break Sereth's confidence"):
                self.apply_status(enemies[0], "frightened", 1, source="your threat of exposure")
                hero_bonus += 2
                self.say("For the first time, Sereth looks less like a fixer and more like someone standing beside a very expensive mistake.")
            else:
                self.state.flags["blackwake_floodgate_hazard"] = True
                self.say("Sereth answers the threat by kicking the floodgate release halfway open.")
        elif talk_key == "investigation":
            if self.skill_check(self.state.player, "Investigation", 13, context="to pin Sereth with the exact Blackwake ledger chain"):
                self.state.flags["blackwake_sereth_cornered_by_ledgers"] = True
                self.state.flags["blackwake_sereth_fate"] = "captured"
                self.apply_status(enemies[0], "reeling", 2, source="your ledger confrontation")
                hero_bonus += 2
                self.say("The facts land harder than a blade. Sereth's own people hear enough to stop trusting his escape math.")
            else:
                self.state.flags["blackwake_evidence_burned_by_sereth"] = True
                self.say("You have the right accusation, but not the right order. Sereth burns the page that would have made it clean.")
        elif talk_key == "deception":
            if self.skill_check(self.state.player, "Deception", 14, context="to impersonate higher Ashen Brand authority"):
                if len(enemies) > 1:
                    enemies.pop()
                hero_bonus += 1
                self._blackwake_adjust_named_companion("Bryn Underbough", 1, "you lied to the liars and made their chain of command bite itself")
                self.say("The lie hits the room like rank. One guard steps back before Sereth realizes the order never came from above.")
            else:
                self.state.flags["blackwake_enemy_ambush_advantage"] = True
                self.say("Sereth recognizes the missing countersign and the room moves on his timing.")
        elif talk_key == "contract_house":
            self.state.flags["blackwake_sereth_cornered_by_contract_house"] = True
            self.state.flags["blackwake_sereth_fate"] = "captured"
            self.apply_status(enemies[0], "reeling", 2, source="Oren and Sabra's contract-house paper trail")
            if len(enemies) > 1:
                self.apply_status(enemies[1], "surprised", 1, source="the false manifest line collapsing")
            hero_bonus += 2
            self.add_clue("Oren Vale's room booking, Sabra Kestrel's corrected manifest, and Garren Flint's roadwarden cadence all point to Sereth Vane's Blackwake command line.")
            self.say(
                "Sereth's smile survives Oren's booking line. It survives Sabra's manifest correction. It does not survive Garren's false cadence fitting both of them exactly."
            )
        else:
            self.player_action("Strike immediately before Sereth can spoil the room.")
            hero_bonus += 1

        if self.state.flags.get("blackwake_prisoner_uprising"):
            hero_bonus += 1
            self.say("The armed prisoners hit the chamber's edge at the same time you do.")
        if self.state.flags.get("blackwake_floodgate_hazard"):
            self.apply_status(self.state.player, "reeling", 1, source="the half-open floodgate")
        outcome = self.run_encounter(
            Encounter(
                title="Boss: Sereth Vane",
                description="Sereth Vane tries to turn papers, prisoners, and floodwater into one last exit.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=True,
                parley_dc=14 if self._blackwake_mid_route_count() >= 2 else 15,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("Sereth keeps Blackwake's cache alive and the frontier learns one more reason to fear the road.")
            return
        if outcome == "fled":
            self.state.flags["blackwake_sereth_fate"] = "escaped"
            self.state.flags["blackwake_completed"] = True
            self.refresh_quest_statuses()
            self.return_to_blackwake_decision("You escape the floodgate chamber with Blackwake broken but Sereth still somewhere ahead of you.")
            return
        if not self.state.flags.get("blackwake_sereth_fate"):
            self.state.flags["blackwake_sereth_fate"] = "dead"

        final_choice = self.scenario_choice(
            "The chamber is collapsing into smoke, shouting, and floodwater. What matters most now?",
            [
                self.action_option("Save the prisoners and survivors first."),
                self.action_option("Secure the ledgers and seal workshop."),
                self.action_option("Sabotage the entire cache and floodgate."),
            ],
            allow_meta=False,
        )
        if final_choice == 1:
            self.player_action("Save the prisoners and survivors first.")
            self.state.flags["blackwake_resolution"] = "rescue"
            self.state.flags["blackwake_survivors_saved"] = int(self.state.flags.get("blackwake_survivors_saved", 0) or 0) + 3
            self._blackwake_adjust_named_companion("Elira Dawnmantle", 2, "you chose people over proof at Blackwake")
            self._blackwake_adjust_named_companion("Rhogar Valeguard", 1, "you held the line for prisoners under pressure")
            self.add_inventory_item("potion_healing", 1, source="grateful Blackwake survivors")
            self.reward_party(xp=35, gold=8, reason="saving Blackwake prisoners")
            self.say("Records vanish into water and smoke, but people stumble out alive who would not have had another morning.")
        elif final_choice == 2:
            self.player_action("Secure the ledgers and seal workshop.")
            self.state.flags["blackwake_resolution"] = "evidence"
            self.state.flags["blackwake_evidence_secured"] = True
            self.state.flags["blackwake_ledgers_secured"] = True
            self._blackwake_adjust_named_companion("Bryn Underbough", 1, "you understood the value of proof before officials could deny it")
            self._blackwake_adjust_named_companion("Elira Dawnmantle", -1, "you chose ledgers while wounded people were still calling for help")
            self.reward_party(xp=35, gold=22, reason="securing Blackwake ledgers")
            self.add_clue("Blackwake ledgers prove organized route corruption from Greywake's edge toward Iron Hollow.")
            self.say("You leave with proof heavy enough to change official conversations, though not every voice in the chamber leaves with you.")
        else:
            self.player_action("Sabotage the entire cache and floodgate.")
            self.state.flags["blackwake_resolution"] = "sabotage"
            self.state.flags["blackwake_cache_sabotaged"] = True
            self.act1_adjust_metric("act1_ashen_strength", -1)
            self._blackwake_adjust_named_companion("Kaelis Starling", 1, "you broke the network's route before it could adapt")
            self._blackwake_adjust_named_companion("Bryn Underbough", -1, "you burned useful names with the cache")
            self.add_inventory_item("antitoxin_vial", 1, source="a waterproof cache satchel")
            self.reward_party(xp=35, gold=6, reason="sabotaging the Blackwake cache")
            self.say("The floodgate takes the cache apart in a roar. Evidence and loot go with it, but so does a working supply line.")
        self.complete_map_room(dungeon, room.room_id)
        self.refresh_quest_statuses()
        self.return_to_blackwake_decision("Blackwake Crossing is resolved. The choice now is whether its ashes go north to Mira or south toward Iron Hollow.")

    def run_act2_dungeon(self, node_id: str) -> None:
        assert self.state is not None
        self._sync_act2_map_state_with_scene(force_node_id=node_id)
        node = ACT2_ENEMY_DRIVEN_MAP.nodes[node_id]
        dungeon = ACT2_ENEMY_DRIVEN_MAP.dungeons[str(node.enters_dungeon_id)]
        self.banner(node.title)
        self.render_act2_dungeon_map(dungeon, force=True)

        while self.state is not None and self.state.current_scene == node.scene_key:
            self._consume_act2_dungeon_transition_feedback(dungeon)
            room = self.current_act2_room(dungeon)
            if not self.act2_room_is_cleared(room.room_id):
                self._run_act2_room(node_id, dungeon, room)
                if self.state.current_scene != node.scene_key:
                    return
                continue

            options = self.act2_room_navigation_options(dungeon)
            choice = self.scenario_choice(
                f"What do you do from {room.title}?",
                [text for _, _, text in options],
                allow_meta=False,
            )
            action, destination, _ = options[choice - 1]
            action_kind, _, action_direction = action.partition(":")
            if action_kind == "move":
                next_room = dungeon.rooms[destination]
                self.set_current_act2_map_room(
                    destination,
                    announce=True,
                    movement_text=f"You move {(action_direction or room_direction(room, next_room, dungeon)).lower()} toward {next_room.title}.",
                )
                continue
            if action_kind == "backtrack":
                if not self.backtrack_act2_map_room(dungeon):
                    self.say("There is nowhere useful to backtrack from here.")
                continue
            self.return_to_act2_hub(f"You withdraw from {node.title} and return to Iron Hollow's expedition table.")
            return

    def _run_act2_room(self, node_id: str, dungeon: DungeonMap, room: DungeonRoom) -> None:
        handlers = {
            ("stonehollow_dig", "survey_mouth"): self._stonehollow_survey_mouth,
            ("stonehollow_dig", "slime_cut"): self._stonehollow_slime_cut,
            ("stonehollow_dig", "warded_side_run"): self._stonehollow_warded_side_run,
            ("stonehollow_dig", "scholar_pocket"): self._stonehollow_scholar_pocket,
            ("stonehollow_dig", "collapse_lift"): self._stonehollow_collapse_lift,
            ("stonehollow_dig", "lower_breakout"): self._stonehollow_lower_breakout,
            ("glasswater_intake", "rock_weir"): self._glasswater_rock_weir,
            ("glasswater_intake", "intake_yard"): self._glasswater_intake_yard,
            ("glasswater_intake", "gatehouse_winch"): self._glasswater_gatehouse_winch,
            ("glasswater_intake", "valve_hall"): self._glasswater_valve_hall,
            ("glasswater_intake", "settling_cistern"): self._glasswater_settling_cistern,
            ("glasswater_intake", "lamp_chapel"): self._glasswater_lamp_chapel,
            ("glasswater_intake", "relay_office"): self._glasswater_relay_office,
            ("glasswater_intake", "ledger_vault"): self._glasswater_ledger_vault,
            ("glasswater_intake", "overflow_crawl"): self._glasswater_overflow_crawl,
            ("glasswater_intake", "filter_beds"): self._glasswater_filter_beds,
            ("glasswater_intake", "pump_gallery"): self._glasswater_pump_gallery,
            ("glasswater_intake", "headgate_chamber"): self._glasswater_headgate_chamber,
            ("siltlock_counting_house", "public_counter"): self._siltlock_public_counter,
            ("siltlock_counting_house", "permit_stacks"): self._siltlock_permit_stacks,
            ("siltlock_counting_house", "ration_cellar"): self._siltlock_ration_cellar,
            ("siltlock_counting_house", "back_till"): self._siltlock_back_till,
            ("siltlock_counting_house", "valve_wax_archive"): self._siltlock_valve_wax_archive,
            ("siltlock_counting_house", "sluice_bell_alcove"): self._siltlock_sluice_bell_alcove,
            ("siltlock_counting_house", "auditor_stair"): self._siltlock_auditor_stair,
            ("broken_prospect", "broken_shelf"): self._broken_prospect_broken_shelf,
            ("broken_prospect", "pact_markers"): self._broken_prospect_pact_markers,
            ("broken_prospect", "rival_survey_shelf"): self._broken_prospect_rival_survey_shelf,
            ("broken_prospect", "sentinel_span"): self._broken_prospect_sentinel_span,
            ("broken_prospect", "sealed_approach"): self._broken_prospect_sealed_approach,
            ("broken_prospect", "foreman_shift"): self._broken_prospect_foreman_shift,
            ("south_adit", "adit_mouth"): self._south_adit_adit_mouth,
            ("south_adit", "silent_cells"): self._south_adit_silent_cells,
            ("south_adit", "drainage_exit"): self._south_adit_drainage_exit,
            ("south_adit", "infirmary_cut"): self._south_adit_infirmary_cut,
            ("south_adit", "augur_cell"): self._south_adit_augur_cell,
            ("south_adit", "warden_nave"): self._south_adit_warden_nave,
            ("wave_echo_outer_galleries", "rail_junction"): self._wave_echo_rail_junction,
            ("wave_echo_outer_galleries", "slime_sluice"): self._wave_echo_slime_sluice,
            ("wave_echo_outer_galleries", "grimlock_side_run"): self._wave_echo_grimlock_side_run,
            ("wave_echo_outer_galleries", "collapsed_crane"): self._wave_echo_collapsed_crane,
            ("wave_echo_outer_galleries", "false_echo_loop"): self._wave_echo_false_echo_loop,
            ("wave_echo_outer_galleries", "deep_haul_gate"): self._wave_echo_deep_haul_gate,
            ("black_lake_causeway", "causeway_lip"): self._black_lake_causeway_lip,
            ("black_lake_causeway", "drowned_shrine"): self._black_lake_drowned_shrine,
            ("black_lake_causeway", "choir_barracks"): self._black_lake_choir_barracks,
            ("black_lake_causeway", "anchor_chains"): self._black_lake_anchor_chains,
            ("black_lake_causeway", "blackwater_edge"): self._black_lake_blackwater_edge,
            ("black_lake_causeway", "far_landing"): self._black_lake_far_landing,
            ("blackglass_relay_house", "relay_gate"): self._blackglass_relay_gate,
            ("blackglass_relay_house", "cable_sump"): self._blackglass_relay_cable_sump,
            ("blackglass_relay_house", "keeper_ledger"): self._blackglass_relay_keeper_ledger,
            ("blackglass_relay_house", "null_bell_walk"): self._blackglass_relay_null_bell_walk,
            ("blackglass_relay_house", "counterweight_crown"): self._blackglass_relay_counterweight_crown,
            ("forge_of_spells", "forge_threshold"): self._forge_threshold,
            ("forge_of_spells", "choir_pit"): self._forge_choir_pit,
            ("forge_of_spells", "pact_anvil"): self._forge_pact_anvil,
            ("forge_of_spells", "shard_channels"): self._forge_shard_channels,
            ("forge_of_spells", "resonance_lens"): self._forge_resonance_lens,
            ("forge_of_spells", "caldra_dais"): self._forge_caldra_dais,
        }
        handler = handlers[(node_id, room.room_id)]
        previous_context = getattr(self, "_post_combat_random_encounter_context", None)
        self._post_combat_random_encounter_context = {"act": 2, "room_role": room.role, "room_id": room.room_id}
        try:
            handler(dungeon, room)
        finally:
            if previous_context is None:
                delattr(self, "_post_combat_random_encounter_context")
            else:
                self._post_combat_random_encounter_context = previous_context

    def _stonehollow_delayed(self) -> bool:
        assert self.state is not None
        return self.state.flags.get("act2_neglected_lead") == "stonehollow_dig_cleared"

    def _stonehollow_survey_mouth(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        if not self.has_quest("rescue_stonehollow_scholars"):
            self.grant_quest("rescue_stonehollow_scholars")
        if not self.state.flags.get("stonehollow_seen"):
            self.say(
                "Stonehollow is a half-legitimate dig site turned excavation wound. Survey strings hang through damp air, "
                "collapsed supports choke the lower lane, and someone has been using the trapped scholars as unwilling map readers.",
                typed=True,
            )
            if self._stonehollow_delayed():
                self.say(
                    "Coming here late means the place has had longer to collapse inward on both bodies and evidence. The lower notes are not all going to be recoverable now."
                )
            self.state.flags["stonehollow_seen"] = True
        options: list[tuple[str, str]] = [
            (
                "investigation",
                self.skill_tag("INVESTIGATION", self.action_option("Read the support lines and mark the one section that can still hold.")),
            ),
            (
                "athletics",
                self.skill_tag("ATHLETICS", self.action_option("Brace the lowest beam before the entry throat folds inward.")),
            ),
            (
                "arcana",
                self.skill_tag("ARCANA", self.action_option("Listen for the old Meridian Compact warding under the fresh collapse noise.")),
            ),
        ]
        if self.state.flags.get("quest_reward_jerek_road_knot"):
            options.append(
                (
                    "road_knot",
                    self.skill_tag(
                        "HARL ROAD-KNOT",
                        self.action_option("Use Dain Harl's road-knot habit to tell which braces were tied by working hands instead of looters."),
                    ),
                )
            )
        choice = self.scenario_choice(
            "How do you take the first measure of the dig?",
            [text for _, text in options],
            allow_meta=False,
        )
        selection_key, _ = options[choice - 1]
        if selection_key == "investigation":
            self.player_action("Read the support lines and mark the one section that can still hold.")
            if self.skill_check(self.state.player, "Investigation", 13, context="to read the dig braces under pressure"):
                self.state.flags["stonehollow_supports_stabilized"] = True
                self.reward_party(xp=10, reason="stabilizing Stonehollow's entry braces")
                self.say("You mark the honest braces and the whole entry stops feeling like a mouth about to close.")
            else:
                self.say("The support pattern is bad in too many places at once. You get through, but not cleanly.")
        elif selection_key == "athletics":
            self.player_action("Brace the lowest beam before the entry throat folds inward.")
            if self.skill_check(self.state.player, "Athletics", 13, context="to brace the collapsing entry"):
                self.state.flags["stonehollow_entry_braced"] = True
                self.apply_status(self.state.player, "emboldened", 1, source="holding Stonehollow's entry open")
                self.say("The beam groans, but you force it into usefulness long enough for the party to pass.")
            else:
                self.apply_status(self.state.player, "reeling", 1, source="Stonehollow's unstable entry")
                self.say("You keep the beam from killing anyone, but it takes a brutal shoulder and a shower of stone.")
        elif selection_key == "arcana":
            self.player_action("Listen for the old Meridian Compact warding under the fresh collapse noise.")
            if self.skill_check(self.state.player, "Arcana", 13, context="to hear the warded side-run beneath the collapse noise"):
                self.state.flags["stonehollow_ward_path_hint"] = True
                self.say("Beneath the bad echoes, one old ward still answers in a steady pattern. There is a cleaner side-run somewhere below.")
            else:
                self.say("The echoes answer, but not in any pattern you can trust yet.")
        else:
            self.player_action("Use Dain Harl's road-knot habit to tell which braces were tied by working hands instead of looters.")
            self.state.flags["stonehollow_supports_stabilized"] = True
            self.reward_party(xp=10, reason="following Dain Harl's road-knot logic through Stonehollow")
            self.say("The knot pattern tells you which braces were tied by people trying to bring crews home rather than trap them. Stonehollow gives up one honest line immediately.")
        self.complete_act2_map_room(dungeon, room.room_id)

    def _stonehollow_slime_cut(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say(
            "The main cut narrows around spilled lantern oil, acid-eaten timber, and an ochre mass dragging itself through the dig like a slow argument against boots."
        )
        party_size = len(self.state.party_members())
        enemies = [create_enemy("ochre_slime")]
        if party_size >= 4:
            enemies.append(self.act2_pick_enemy(("stirge_swarm", "acidmaw_burrower", "carrion_lash_crawler")))
        hero_bonus = self.apply_scene_companion_support("stonehollow_dig")
        if self.state.flags.get("stonehollow_supports_stabilized"):
            hero_bonus += 1
            self.apply_status(enemies[0], "reeling", 1, source="your marked support collapse")
        choice = self.scenario_choice(
            "How do you cross the slime cut?",
            [
                self.skill_tag("INVESTIGATION", self.action_option("Drop the marked brace and pin the ooze under its own ceiling.")),
                self.skill_tag("ATHLETICS", self.action_option("Force the crossing before the acid eats the last plank.")),
                self.skill_tag("SURVIVAL", self.action_option("Use the dry stone ribs and keep everyone out of the wet center.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Drop the marked brace and pin the ooze under its own ceiling.")
            if self.skill_check(self.state.player, "Investigation", 13, context="to turn the support lines into a trap"):
                enemies[0].current_hp = max(1, enemies[0].current_hp - 5)
                self.apply_status(enemies[0], "prone", 1, source="the dropped brace")
                hero_bonus += 2
        elif choice == 2:
            self.player_action("Force the crossing before the acid eats the last plank.")
            if self.skill_check(self.state.player, "Athletics", 13, context="to force the slime cut crossing"):
                self.apply_status(self.state.player, "emboldened", 2, source="forcing the slime cut")
                hero_bonus += 1
        else:
            self.player_action("Use the dry stone ribs and keep everyone out of the wet center.")
            if self.skill_check(self.state.player, "Survival", 13, context="to read the safe stone through the slime cut"):
                hero_bonus += 2
                self.say("You find the narrow ribs that the ooze has not softened yet, and the party gets angles instead of panic.")
        outcome = self.run_encounter(
            Encounter(
                title="Stonehollow Slime Cut",
                description="An acid-slick chokepoint blocks the main survey route through the dig.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("Stonehollow seals over the party and the missing scholars stay lost below.")
            return
        if outcome == "fled":
            self.return_to_act2_hub("You retreat from the slime cut before the collapse can trap everyone together.")
            return
        self.complete_act2_map_room(dungeon, room.room_id)

    def _stonehollow_warded_side_run(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say(
            "The side-run is narrower and older than the main dig, lined with Meridian Compact scratches that have survived better than the new timber."
        )
        dc = 13 if self.state.flags.get("stonehollow_ward_path_hint") else 14
        choice = self.scenario_choice(
            "How do you work the warded side-run?",
            [
                self.skill_tag("ARCANA", self.action_option("Follow the living parts of the ward and ignore the dead echoes.")),
                self.skill_tag("HISTORY", self.action_option("Read the old survey discipline instead of the new dig marks.")),
                self.skill_tag("RELIGION", self.action_option("Treat the old oath marks as warnings, not decorations.")),
            ],
            allow_meta=False,
        )
        skill = "Arcana" if choice == 1 else "History" if choice == 2 else "Religion"
        if self.skill_check(self.state.player, skill, dc, context="to read Stonehollow's warded side-run"):
            self.state.flags["stonehollow_ward_path_read"] = True
            self.reward_party(xp=10, reason="reading Stonehollow's Meridian Compact warding")
            self.say("The side-run resolves into a real path, and the old warding shows where the scholars would have tried to hide.")
        else:
            self.say("The side-run gives you enough path to keep moving, but the deeper pattern stays stubbornly incomplete.")
        self.complete_act2_map_room(dungeon, room.room_id)

    def _stonehollow_scholar_pocket(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say(
            "A cramped pocket of salvage boards and chalk maps holds the last useful survey notes, a few shaking survivors, and one gnome who is trying to look less terrified than he is."
        )
        delayed = self._stonehollow_delayed()
        choice = self.scenario_choice(
            "What do you secure first?",
            [
                self.skill_tag("MEDICINE", self.action_option("Stabilize the injured scholars before the pocket has to move.")),
                self.skill_tag("INVESTIGATION", self.action_option("Gather the survey notes before another collapse eats the route truth.")),
                self.skill_tag("PERSUASION", self.action_option("Get the survivors moving as a group before panic chooses for them.")),
            ],
            allow_meta=False,
        )
        skill = "Medicine" if choice == 1 else "Investigation" if choice == 2 else "Persuasion"
        if self.skill_check(self.state.player, skill, 13, context="to secure Stonehollow's trapped survey pocket"):
            self.reward_party(xp=15, reason="saving Stonehollow's survey pocket")
            if choice == 2:
                self.state.flags["stonehollow_notes_preserved"] = True
            self.say("You turn the pocket from a trapped room into an evacuation point before the next tremor decides the matter.")
        else:
            self.say("You get the survivors moving, but the pocket sheds notes, tools, and certainty as it goes.")
        if not self.find_companion("Nim Ardentglass"):
            self.speaker(
                "Nim Ardentglass",
                "If you're the reason I'm not dying under my own survey notes, I should probably stop pretending I can solve Resonant Vaults by myself.",
            )
            recruit = self.scenario_choice(
                "Nim gathers his satchel and looks between you and the ruined lane.",
                [
                    self.quoted_option("RECRUIT", "Then walk with us and keep the maps honest."),
                    self.quoted_option("SAFE", "Get back to Iron Hollow and recover. We can talk there."),
                ],
                allow_meta=False,
            )
            self.recruit_companion(create_nim_ardentglass())
            nim = self.find_companion("Nim Ardentglass")
            if delayed and nim is not None:
                self.adjust_companion_disposition(
                    nim,
                    -1,
                    "you came for Stonehollow late, after some of the cleanest notes were already gone",
                )
            if recruit == 2 and nim is not None and nim in self.state.companions:
                self.move_companion_to_camp(nim)
                self.say("Nim agrees to return to camp and organize whatever survey truth can still be salvaged.")
        self.complete_act2_map_room(dungeon, room.room_id)

    def _stonehollow_collapse_lift(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("The lift shaft is half ladder, half hanging mistake, with something blind and hungry moving through the dark below.")
        party_size = len(self.state.party_members())
        enemies = [create_enemy("grimlock_tunneler")]
        if party_size >= 4:
            enemies.append(self.act2_pick_enemy(("acidmaw_burrower", "carrion_lash_crawler", "grimlock_tunneler")))
        hero_bonus = self.apply_scene_companion_support("stonehollow_dig")
        choice = self.scenario_choice(
            "How do you force the lower lane open?",
            [
                self.skill_tag("ATHLETICS", self.action_option("Drop fast, catch the chain, and make the shaft your angle.")),
                self.skill_tag("SURVIVAL", self.action_option("Move like the tunnelers do and reach their blind side first.")),
                self.skill_tag("STEALTH", self.action_option("Let the lift creak without you on it and strike from the side ladder.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Drop fast, catch the chain, and make the shaft your angle.")
            if self.skill_check(self.state.player, "Athletics", 13, context="to force the collapse lift"):
                hero_bonus += 2
                self.apply_status(self.state.player, "emboldened", 2, source="taking the shaft by force")
        elif choice == 2:
            self.player_action("Move like the tunnelers do and reach their blind side first.")
            if self.skill_check(self.state.player, "Survival", 13, context="to read the tunnelers' lower-lane path"):
                hero_bonus += 2
                self.apply_status(enemies[0], "surprised", 1, source="you reached the blind side first")
        else:
            self.player_action("Let the lift creak without you on it and strike from the side ladder.")
            if self.skill_check(self.state.player, "Stealth", 13, context="to misdirect the lift ambush"):
                enemies[0].current_hp = max(1, enemies[0].current_hp - 4)
                hero_bonus += 1
        outcome = self.run_encounter(
            Encounter(
                title="Stonehollow Collapse Lift",
                description="Tunnel predators try to keep the lower lane sealed around the trapped survey route.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("Stonehollow seals over the party and the missing scholars stay lost below.")
            return
        if outcome == "fled":
            self.return_to_act2_hub("You pull back from the collapse lift before the lower lane takes the whole company.")
            return
        self.complete_act2_map_room(dungeon, room.room_id)

    def _stonehollow_lower_breakout(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        delayed = self._stonehollow_delayed()
        party_size = len(self.state.party_members())
        enemies = [create_enemy("grimlock_tunneler")]
        if delayed:
            enemies.append(self.act2_pick_enemy(("spectral_foreman", "hookclaw_burrower")))
        elif not self.state.flags.get("stonehollow_scholars_found"):
            enemies.append(create_enemy("ochre_slime"))
        if party_size >= 4:
            enemies.append(self.act2_pick_enemy(("grimlock_tunneler", "acidmaw_burrower", "carrion_lash_crawler")))
        hero_bonus = self.apply_scene_companion_support("stonehollow_dig")
        if self.state.flags.get("stonehollow_lane_forced"):
            hero_bonus += 1
        if self.state.flags.get("stonehollow_ward_path_read"):
            hero_bonus += 1
        if self.state.flags.get("stonehollow_notes_preserved"):
            hero_bonus += 1
        choice = self.scenario_choice(
            "How do you turn the lower breakout into an exit instead of a grave?",
            [
                self.skill_tag("INVESTIGATION", self.action_option("Use the preserved route notes to call the safest extraction line.")),
                self.skill_tag("ATHLETICS", self.action_option("Hold the lower lane open while the scholars run.")),
                self.skill_tag("ARCANA", self.action_option("Wake the remaining ward just long enough to break the monsters' rhythm.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Use the preserved route notes to call the safest extraction line.")
            if self.skill_check(self.state.player, "Investigation", 14, context="to call the clean extraction line"):
                hero_bonus += 2
                if enemies:
                    enemies[0].current_hp = max(1, enemies[0].current_hp - 4)
        elif choice == 2:
            self.player_action("Hold the lower lane open while the scholars run.")
            if self.skill_check(self.state.player, "Athletics", 14, context="to hold Stonehollow's lower lane open"):
                hero_bonus += 2
                self.apply_status(self.state.player, "emboldened", 2, source="holding the lower lane")
        else:
            self.player_action("Wake the remaining ward just long enough to break the monsters' rhythm.")
            if self.skill_check(self.state.player, "Arcana", 14, context="to wake Stonehollow's remaining ward"):
                hero_bonus += 2
                for enemy in enemies:
                    self.apply_status(enemy, "reeling", 1, source="the old ward flaring")
        outcome = self.run_encounter(
            Encounter(
                title="Stonehollow Breakout",
                description="The trapped dig is full of things that want the scholars silenced before they can finish reading the cave.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("Stonehollow seals over the party and the missing scholars stay lost below.")
            return
        if outcome == "fled":
            self.return_to_act2_hub("You retreat from the lower breakout before Stonehollow can turn the rescue into a burial.")
            return
        self.complete_act2_map_room(dungeon, room.room_id)
        self.reward_party(xp=45, gold=10, reason="clearing Stonehollow Dig")
        stonehollow_reward = self.act2_stonehollow_milestone_item()
        self.act2_award_milestone_gear(
            "act2_stonehollow_milestone_gear",
            stonehollow_reward,
            source="Stonehollow's recovered survey locker",
        )
        if delayed:
            self.act2_shift_metric(
                "act2_route_control",
                1,
                "you salvage enough of Stonehollow's survey work to stop the route picture from staying crippled",
            )
        else:
            self.act2_shift_metric(
                "act2_route_control",
                2,
                "the Stonehollow survey line finally belongs to people who plan to bring it back out alive",
            )
            if self.state.flags.get("stonehollow_ward_path_read"):
                self.act2_shift_metric(
                    "act2_whisper_pressure",
                    -1,
                    "reading the Meridian Compact warding correctly keeps one more part of the cave from teaching through panic",
                )
        self.return_to_act2_hub("Stonehollow exhales stone dust behind you, and the rescued survey truth finally reaches the expedition table.")

    def _glasswater_delayed(self) -> bool:
        assert self.state is not None
        return bool(self.state.flags.get(self.ACT2_SABOTAGE_RESOLVED_FLAG)) and not self.state.flags.get("glasswater_intake_cleared")

    def _glasswater_active_companion(self, name: str):
        assert self.state is not None
        companion = self.find_companion(name)
        if companion is None or companion not in self.state.companions:
            return None
        return companion

    def _glasswater_award_baseline_rewards(self) -> None:
        assert self.state is not None
        if not self.state.flags.get("glasswater_reward_thoughtward"):
            if self.add_inventory_item("thoughtward_draught", source="the Glasswater foreman's reserve"):
                self.state.flags["glasswater_reward_thoughtward"] = True
        if not self.state.flags.get("glasswater_reward_clarity"):
            if self.add_inventory_item("scroll_clarity", source="the Glasswater headgate packet"):
                self.state.flags["glasswater_reward_clarity"] = True

    def _glasswater_rock_weir(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        delayed = self._glasswater_delayed()
        if not self.state.flags.get("glasswater_route_seen"):
            self.say(
                "The Glasswater run begins as practical dwarfwork cut into a wet slope: a rock apron, a spill channel, and old maintenance posts silvered by mist. "
                "Fresh boot marks cut across all of it like insults.",
                typed=True,
            )
            if self.state.flags.get("glasswater_permit_fraud_exposed"):
                self.say("Siltlock's permit chain gives the annex an uglier shape: the false maintenance delay was signed before the water turned foul.")
            if self.state.flags.get("glasswater_valve_wax_matched"):
                self.say("The green wax sample from Siltlock matches the grit packed around the first valve locks.")
            if delayed:
                self.say(
                    "You reached it after sabotage night. A few surfaces have already been wiped cleaner than the annex deserves, and one whole layer of panic has had time to dry into habit."
                )
            self.state.flags["glasswater_route_seen"] = True
        choice = self.scenario_choice(
            "How do you read the annex before the yard sees you?",
            [
                self.skill_tag("SURVIVAL", self.action_option("Trace the hauling and drainage rhythm before the water hides it.")),
                self.skill_tag("STEALTH", self.action_option("Get close enough to hear the yard cadence before anyone counts you.")),
                self.skill_tag("INVESTIGATION", self.action_option("Read the engineering scars instead of the footsteps.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Trace the hauling and drainage rhythm before the water hides it.")
            if self.skill_check(self.state.player, "Survival", 13, context="to read the Glasswater courier timing"):
                self.state.flags["glasswater_courier_timing_read"] = True
                self.reward_party(xp=10, reason="reading Glasswater's hauling rhythm")
                self.say("The annex traffic has a real cadence to it. You mark when the runners look at the water and when they stop trusting it.")
        elif choice == 2:
            self.player_action("Get close enough to hear the yard cadence before anyone counts you.")
            if self.skill_check(self.state.player, "Stealth", 13, context="to take the blind Glasswater approach"):
                self.state.flags["glasswater_blind_approach"] = True
                self.say("You find the angle where the yard trusts its own noise more than its eyes.")
        else:
            self.player_action("Read the engineering scars instead of the footsteps.")
            if self.skill_check(self.state.player, "Investigation", 13, context="to spot how Glasswater's runoff is being misdirected"):
                self.state.flags["glasswater_runoff_named"] = True
                self.add_clue("Glasswater's runoff is being vented on purpose. The fouling pattern is deliberate, measured, and tied to controlled traffic through the annex.")
                self.say("The damage is not random neglect. Somebody taught the annex to waste water exactly where it would spread the wrong story.")
        self.complete_act2_map_room(dungeon, room.room_id)

    def _glasswater_intake_yard(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        delayed = self._glasswater_delayed()
        self.say(
            "The yard is a working lie. Rope slings, valve keys, repair sledges, and stacked supply tins make it look like a maintenance annex held together by hard people. "
            "Then you notice which crates are guarded harder than the tools."
        )
        enemies = [create_enemy("false_map_skirmisher"), create_enemy("expedition_reaver")]
        if delayed:
            enemies.append(create_enemy("claimbinder_notary"))
        elif len(self.state.party_members()) >= 4:
            enemies.append(create_enemy("cult_lookout"))
        hero_bonus = self.apply_scene_companion_support("glasswater_intake")
        if self.state.flags.get("glasswater_blind_approach"):
            hero_bonus += 1
            self.apply_status(enemies[0], "surprised", 1, source="your rock-weir approach")
        if self.state.flags.get("glasswater_courier_timing_read"):
            hero_bonus += 1
            self.say("Because you already read the courier timing, the first shout lands half a beat later than the yard needed.")
        choice = self.scenario_choice(
            "How do you enter the Intake Yard?",
            [
                self.skill_tag("DECEPTION", self.action_option("Official route inspection. Open the line and stop wasting my time.")),
                self.skill_tag("STEALTH", self.action_option("Keep low, cut the nearest watcher, and let the yard realize too late what changed.")),
                self.skill_tag("ATHLETICS", self.action_option("Hit them hard before the report runs.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Official route inspection. Open the line and stop wasting my time.")
            if self.skill_check(self.state.player, "Deception", 14, context="to bluff your way through the Glasswater yard"):
                hero_bonus += 2
                self.state.flags["glasswater_headgate_count_heard"] = True
                self.say('A runner mutters that "the headgate only needs one more clean count" before they realize you do not belong there.')
        elif choice == 2:
            self.player_action("Keep low, cut the nearest watcher, and let the yard realize too late what changed.")
            if self.skill_check(self.state.player, "Stealth", 14, context="to break the Glasswater yard from the blind side"):
                hero_bonus += 2
                self.apply_status(enemies[0], "surprised", 1, source="the yard lost its first watcher")
        else:
            self.player_action("Hit them hard before the report runs.")
            if self.skill_check(self.state.player, "Athletics", 14, context="to smash through the Glasswater yard cleanly"):
                hero_bonus += 1
                self.apply_status(self.state.player, "emboldened", 2, source="taking the yard by force")
        outcome = self.run_encounter(
            Encounter(
                title="Glasswater Intake Yard",
                description="Maintenance lookouts and route fixers try to hold the annex long enough for the report to run.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=True,
                parley_dc=14,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The yard holds long enough for Glasswater's operators to clean the lie and keep the annex working against you.")
            return
        if outcome == "fled":
            self.return_to_act2_hub("You break off from the Glasswater yard before the annex can turn its own traffic against the party.")
            return
        self.complete_act2_map_room(dungeon, room.room_id)

    def _glasswater_gatehouse_winch(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("A narrow gear room hangs over the first drop channel. The winch brake is warm. Somebody has been making the intake choose between flood safety and hidden traffic.")
        if self._glasswater_active_companion("Tolan Ironshield") is not None:
            self.speaker(
                "Tolan Ironshield",
                "This room is the difference between a site and a trap. Decide which one we are walking into.",
            )
        if self._glasswater_active_companion("Kaelis Starling") is not None:
            self.speaker(
                "Kaelis Starling",
                "If we leave ourselves one honest exit, I will take it. If not, I would rather know that now.",
            )
        choice = self.scenario_choice(
            "What do you do with the gatehouse controls?",
            [
                self.skill_tag("ATHLETICS", self.action_option("Open the maintenance route and give the party a cleaner line through the upper works.")),
                self.skill_tag("INVESTIGATION", self.action_option("Jam the emergency release. If somebody downstream needs a panic flood, they do not get one.")),
                self.skill_tag("SLEIGHT OF HAND", self.action_option("Set the brake to fail on your timing and keep an exit plan in reserve.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Open the maintenance route and give the party a cleaner line through the upper works.")
            if self.skill_check(self.state.player, "Athletics", 13, context="to wrench the Glasswater maintenance route open"):
                self.state.flags["glasswater_maintenance_route_open"] = True
                self.say("The gate strains, then answers. The annex feels like it has one honest lane again.")
        elif choice == 2:
            self.player_action("Jam the emergency release. If somebody downstream needs a panic flood, they do not get one.")
            if self.skill_check(self.state.player, "Investigation", 13, context="to read and jam the Glasswater emergency release"):
                self.state.flags["glasswater_flood_release_jammed"] = True
                self.say("You lock the release just wrong enough that nobody below gets to lean on it cleanly.")
        else:
            self.player_action("Set the brake to fail on your timing and keep an exit plan in reserve.")
            if self.skill_check(self.state.player, "Sleight of Hand", 13, context="to leave the Glasswater brake on your timing"):
                self.state.flags["glasswater_exit_timed"] = True
                self.say("The brake looks intact until somebody needs it quickly. Then it will belong to your timing instead of theirs.")
        self.complete_act2_map_room(dungeon, room.room_id)

    def _glasswater_valve_hall(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        delayed = self._glasswater_delayed()
        self.say("Bronze wheels, pressure rods, and mineral-white spray turn the Valve Hall into a storm someone taught to obey numbers.")
        enemies = [create_enemy("pact_archive_warden")]
        if delayed or not self.state.flags.get("glasswater_maintenance_route_open"):
            enemies.append(create_enemy("animated_armor"))
        hero_bonus = self.apply_scene_companion_support("glasswater_intake")
        dc = 13 if self.state.flags.get("glasswater_valve_wax_matched") else 14
        if self.state.flags.get("glasswater_maintenance_route_open"):
            hero_bonus += 1
        if self.state.flags.get("glasswater_blind_approach"):
            hero_bonus += 1
        if self.state.flags.get("glasswater_valve_wax_matched"):
            hero_bonus += 1
            self.say("The Siltlock wax sample points to the valve wheel that was sealed for fraud instead of safety.")
        choice = self.scenario_choice(
            "How do you take control of the Valve Hall?",
            [
                self.skill_tag("INVESTIGATION", self.action_option("Read the pressure map and shut the dangerous line first.")),
                self.skill_tag("ATHLETICS", self.action_option("Force the wheels over before the sentinels can lock the room down.")),
                self.skill_tag("ARCANA", self.action_option("Break the wrong valve and make the hall punish its current masters.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Read the pressure map and shut the dangerous line first.")
            if self.skill_check(self.state.player, "Investigation", dc, context="to stabilize the Glasswater valves"):
                self.state.flags["glasswater_valves_stabilized"] = True
                hero_bonus += 2
                self.reward_party(xp=12, reason="stabilizing the Glasswater valve order")
        elif choice == 2:
            self.player_action("Force the wheels over before the sentinels can lock the room down.")
            if self.skill_check(self.state.player, "Athletics", dc, context="to muscle the Glasswater valve line into your control"):
                hero_bonus += 1
                self.apply_status(self.state.player, "emboldened", 2, source="forcing the valve line")
        else:
            self.player_action("Break the wrong valve and make the hall punish its current masters.")
            if self.skill_check(self.state.player, "Arcana", dc, context="to make the Glasswater valve pattern turn hostile"):
                hero_bonus += 1
                self.state.flags["glasswater_vent_line_broken"] = True
                self.apply_status(enemies[0], "reeling", 1, source="a burst of wrong pressure")
        outcome = self.run_encounter(
            Encounter(
                title="Glasswater Valve Hall",
                description="Old sentinels hold a pressure room the Quiet Choir taught to value obedience over safety.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The Valve Hall closes against the party and Glasswater keeps answering the wrong hands.")
            return
        if outcome == "fled":
            self.return_to_act2_hub("You withdraw from the Valve Hall before the annex can seal your whole line inside it.")
            return
        self.complete_act2_map_room(dungeon, room.room_id)

    def _glasswater_settling_cistern(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        delayed = self._glasswater_delayed()
        self.say("The cistern should be a quiet basin where silt drops out before clean flow continues. Instead the surface looks filmed over with thinking darkness.")
        if self._glasswater_active_companion("Elira Dawnmantle") is not None and not delayed:
            self.speaker(
                "Elira Lanternward",
                "If someone is still breathing in this room, that is the first clean task we have had since entering it.",
            )
        choice = self.scenario_choice(
            "What matters most in the cistern?",
            [
                self.skill_tag("MEDICINE", self.action_option("Cut the trapped worker free and keep them talking.")),
                self.skill_tag("INVESTIGATION", self.action_option("Read the runoff and learn what was mixed into it.")),
                self.skill_tag("ACROBATICS", self.action_option("Cross fast before the room decides you belong in it.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Cut the trapped worker free and keep them talking.")
            if self.skill_check(self.state.player, "Medicine", 14, context="to save whoever the cistern has not finished with yet"):
                if delayed:
                    self.state.flags["glasswater_worker_loss_seen"] = True
                    self.add_clue("Glasswater's delayed-state cost is human, not abstract. By the time you reached the cistern, one coerced worker had already died holding the wrong line together.")
                    self.say("You are too late to save them, but not too late to learn who kept the room running and who decided that counted as disposable labor.")
                else:
                    self.state.flags["glasswater_trapped_workers_saved"] = True
                    self.reward_party(xp=15, reason="saving a trapped Glasswater worker")
                    self.say("The worker coughs black grit, lives, and gives you the look of someone who had already been written off in neat hand.")
        elif choice == 2:
            self.player_action("Read the runoff and learn what was mixed into it.")
            if self.skill_check(self.state.player, "Investigation", 14, context="to read the Glasswater runoff"):
                self.state.flags["glasswater_runoff_sample"] = True
                self.add_clue("The Glasswater runoff carries altered grit and chant cadence in measured doses. Someone wanted fear and rumor to travel through an ordinary camp system.")
                self.say("The fouling is precise. Somebody measured exactly how much wrongness the line could carry before practical people would start calling it superstition.")
        else:
            self.player_action("Cross fast before the room decides you belong in it.")
            if self.skill_check(self.state.player, "Acrobatics", 13, context="to cross the settling cistern without letting it own the pace"):
                self.state.flags["glasswater_cistern_crossed_fast"] = True
                self.say("You keep your feet and your nerve, which is more than this room has been granting for a while.")
        self.complete_act2_map_room(dungeon, room.room_id)

    def _glasswater_lamp_chapel(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("The chapel is hardly larger than a pantry: six lamp niches, a worn basin, and a hammered plaque reminding crews that steady hands keep whole towns alive.")
        if self._glasswater_active_companion("Elira Dawnmantle") is not None:
            self.speaker(
                "Elira Lanternward",
                "This is a shrine for people who kept strangers alive without ever meeting them. I would rather not fail them in their own room.",
            )
        choice = self.scenario_choice(
            "How do you answer the chapel?",
            [
                self.skill_tag("RELIGION", self.action_option("Wake the old maintenance rite and force one clean line through the annex.")),
                self.skill_tag("INSIGHT", self.action_option("Read what kind of people wrote a prayer for valves and lamp oil.")),
                self.skill_tag("SURVIVAL", self.action_option("Take the basin water and move. Reverence can wait until the route is safe.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Wake the old maintenance rite and force one clean line through the annex.")
            if self.skill_check(self.state.player, "Religion", 14, context="to answer the Glasswater maintenance rite cleanly"):
                self.state.flags["glasswater_chapel_answered"] = True
                self.apply_status(self.state.player, "blessed", 1, source="the Glasswater lamp chapel")
                self.act2_shift_metric(
                    "act2_whisper_pressure",
                    -1,
                    "Glasswater's lamp chapel remembers that service and obedience were never meant to become the same thing",
                )
                self.say("One lamp catches cleanly. The whole annex does not become holy. It only remembers, for a moment, that service and obedience were not meant to be the same thing.")
        elif choice == 2:
            self.player_action("Read what kind of people wrote a prayer for valves and lamp oil.")
            if self.skill_check(self.state.player, "Insight", 13, context="to understand the people who built Glasswater's chapel"):
                self.state.flags["glasswater_maintenance_creed_read"] = True
                self.reward_party(xp=10, reason="reading Glasswater's maintenance creed")
                self.say("The old Meridian Compact crews did not pray to the machinery. They prayed to the duty of keeping strangers alive through work nobody would ever praise.")
        else:
            self.player_action("Take the basin water and move. Reverence can wait until the route is safe.")
            if self.skill_check(self.state.player, "Survival", 13, context="to take the chapel basin as a practical ward"):
                self.state.flags["glasswater_basin_taken"] = True
                self.say("The basin water is cold enough to feel like a warning, but it steadies your breathing instead of stealing it.")
        self.complete_act2_map_room(dungeon, room.room_id)

    def _glasswater_relay_office(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        delayed = self._glasswater_delayed()
        self.say("The Relay Office is too orderly for a ruin. Satchels hang by route mark, manifests are weighted against damp, and one wall is given over entirely to copied names.")
        dc = 13 if self.state.flags.get("glasswater_permit_fraud_exposed") else 14
        if self.state.flags.get("glasswater_permit_fraud_exposed"):
            self.say("Siltlock's forged permits name the manifest shelf that should have been missing from this office.")
        if self._glasswater_active_companion("Bryn Underbough") is not None:
            self.speaker(
                "Bryn Underbough",
                "Ignore the polished case. The packet that matters is always the one trying hardest not to look important.",
            )
        choice = self.scenario_choice(
            "What do you seize before the room scatters?",
            [
                self.skill_tag("STEALTH", self.action_option("Take the live satchel before the shelves teach you the wrong lesson.")),
                self.skill_tag("INVESTIGATION", self.action_option("Read the claim manifests and name who profits from the intake staying sick.")),
                self.skill_tag("INTIMIDATION", self.action_option("Pressure the clerk or fixer before fear turns them useless.")),
            ],
            allow_meta=False,
        )
        resolved_cleanly = False
        if choice == 1:
            self.player_action("Take the live satchel before the shelves teach you the wrong lesson.")
            if self.skill_check(self.state.player, "Stealth", dc, context="to steal the Glasswater live satchel without blowing the office"):
                resolved_cleanly = True
                self.state.flags["glasswater_relay_ledgers_taken"] = True
                self.state.flags["glasswater_relay_route_decoded"] = True
                self.add_clue("A Glasswater satchel tracks reserve schedules, copied manifests, and 'special transfers' that do not belong on a waterworks line.")
                self.say("You lift the live packet before the shelves can become theater. The room suddenly makes sense in the worst possible way.")
        elif choice == 2:
            self.player_action("Read the claim manifests and name who profits from the intake staying sick.")
            if self.skill_check(self.state.player, "Investigation", dc, context="to expose the false manifests in Glasswater's relay office"):
                resolved_cleanly = True
                self.state.flags["glasswater_claim_fraud_named"] = True
                self.add_clue("Glasswater manifests were falsified to protect a profitable lie: delays, fouled water, and missing repair allotments were all serving somebody's route politics.")
                self.say("The papers stop pretending to be maintenance records and turn into motive.")
        else:
            self.player_action("Pressure the clerk or fixer before fear turns them useless.")
            if self.skill_check(self.state.player, "Intimidation", dc, context="to break Glasswater's relay clerk before the room settles into silence"):
                resolved_cleanly = True
                self.state.flags["glasswater_courier_broken"] = True
                self.add_clue("A shaken Glasswater fixer admits that 'special transfers' moved through lower rooms on the same nights town water ran foul, tying the annex to a deeper prisoner-routing line.")
                self.say("The fixer cracks before the room can teach them a cleaner lie to die with.")
        if resolved_cleanly:
            self.complete_act2_map_room(dungeon, room.room_id)
            return

        enemies = [create_enemy("expedition_reaver"), create_enemy("cult_lookout")]
        if delayed:
            enemies.append(create_enemy("cult_lookout"))
        hero_bonus = 0
        if self.state.flags.get("glasswater_courier_timing_read"):
            hero_bonus += 1
        if self.state.flags.get("glasswater_headgate_count_heard"):
            hero_bonus += 1
        outcome = self.run_encounter(
            Encounter(
                title="Glasswater Relay Office",
                description="When the office stops pretending to be paperwork, hired route muscle and watchers try to erase the live packet with you in the room.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The relay office closes around the party and the annex keeps its cleaner paperwork intact.")
            return
        if outcome == "fled":
            self.return_to_act2_hub("You break away from the relay office before its panic can turn into a full purge of the records.")
            return
        self.complete_act2_map_room(dungeon, room.room_id)

    def _glasswater_ledger_vault(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("The vault door is small, ugly, and expensive in the way only practical secrets ever are.")
        dc = 13 if self.state.flags.get("glasswater_permit_fraud_exposed") or self.state.flags.get("glasswater_valve_wax_matched") else 14
        if self.state.flags.get("glasswater_permit_fraud_exposed"):
            self.say("The permit numbers from Siltlock give you three ledger rows before the vault can bury them in routine.")
        choice = self.scenario_choice(
            "Which truth do you take out first?",
            [
                self.skill_tag("INVESTIGATION", self.action_option("The proof that someone profited from the intake staying unstable.")),
                self.skill_tag("HISTORY", self.action_option("The route ledgers. You need the living pattern before the guilty names.")),
                self.skill_tag("SLEIGHT OF HAND", self.action_option("The prisoner-transfer notations before somebody notices the missing page.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("The proof that someone profited from the intake staying unstable.")
            if self.skill_check(self.state.player, "Investigation", dc, context="to isolate Glasswater's claims-fraud proof"):
                self.state.flags["glasswater_claim_fraud_named"] = True
                self.add_clue("Glasswater's hidden ledgers prove repair delays and false route reports were profitable, not accidental.")
        elif choice == 2:
            self.player_action("The route ledgers. You need the living pattern before the guilty names.")
            if self.skill_check(self.state.player, "History", dc, context="to reconstruct Glasswater's live route pattern"):
                self.state.flags["glasswater_relay_route_decoded"] = True
                self.add_clue("Glasswater's route ledgers mark which traffic was real, which was copied, and which loads only existed to cover stranger movement through the annex.")
        else:
            self.player_action("The prisoner-transfer notations before somebody notices the missing page.")
            if self.skill_check(self.state.player, "Sleight of Hand", dc, context="to lift the Glasswater transfer notations cleanly"):
                self.state.flags["glasswater_transfer_notes_found"] = True
                self.add_clue("Glasswater transfer slips reference lower-room 'special transfers' that do not fit supply work, foreshadowing the South Adit prisoner line.")
        if not self.state.flags.get("glasswater_reward_thoughtward"):
            if self.add_inventory_item("thoughtward_draught", source="a sealed foreman's coffer in the Glasswater vault"):
                self.state.flags["glasswater_reward_thoughtward"] = True
        self.complete_act2_map_room(dungeon, room.room_id)

    def _glasswater_overflow_crawl(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        delayed = self._glasswater_delayed()
        self.say("The crawl smells like old metal, wet lime, and the kind of panic people leave behind when they had to move through a space not built for standing.")
        enemies = [create_enemy("grimlock_tunneler")]
        if delayed:
            enemies.append(create_enemy("ochre_slime"))
        elif len(self.state.party_members()) >= 4:
            enemies.append(create_enemy("cult_lookout"))
        hero_bonus = 0
        if self.state.flags.get("glasswater_courier_timing_read"):
            hero_bonus += 1
        choice = self.scenario_choice(
            "How do you take the overflow crawl?",
            [
                self.skill_tag("STEALTH", self.action_option("Slide through the crawl quietly enough to own the angle first.")),
                self.skill_tag("SURVIVAL", self.action_option("Read the runoff and let it carry you to the flanking line.")),
                self.skill_tag("ATHLETICS", self.action_option("Force the bars and make speed your only courtesy.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Slide through the crawl quietly enough to own the angle first.")
            if self.skill_check(self.state.player, "Stealth", 14, context="to clear the Glasswater crawl from the blind side"):
                hero_bonus += 2
                self.apply_status(enemies[0], "surprised", 1, source="you reached the crawl's blind angle first")
        elif choice == 2:
            self.player_action("Read the runoff and let it carry you to the flanking line.")
            if self.skill_check(self.state.player, "Survival", 14, context="to turn Glasswater's overflow into a flank route"):
                hero_bonus += 1
                self.state.flags["glasswater_flank_route"] = True
        else:
            self.player_action("Force the bars and make speed your only courtesy.")
            if self.skill_check(self.state.player, "Athletics", 14, context="to clear the overflow bars before the annex reacts"):
                hero_bonus += 1
                self.apply_status(self.state.player, "emboldened", 2, source="forcing the overflow crawl")
        outcome = self.run_encounter(
            Encounter(
                title="Glasswater Overflow Crawl",
                description="The annex's side-run is miserable, useful, and already occupied by things that learned to hunt in it.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The overflow crawl chews the party up before the deep line can be flanked.")
            return
        if outcome == "fled":
            self.return_to_act2_hub("You pull out of the overflow crawl before the annex can turn the side-run into a coffin.")
            return
        self.complete_act2_map_room(dungeon, room.room_id)

    def _glasswater_filter_beds(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        delayed = self._glasswater_delayed()
        self.say("The filtration floor should slow water down until it clarifies. Instead it turns every step into an argument about what deserves to keep moving.")
        if delayed and not self.state.flags.get("glasswater_delayed_pressure_marked"):
            self.state.flags["glasswater_delayed_pressure_marked"] = True
            self.act2_shift_metric(
                "act2_whisper_pressure",
                1,
                "Glasswater's filter beds kept running foul after sabotage night and taught the annex a harsher kind of silence",
            )
        enemies = [create_enemy("choir_adept"), create_enemy("cult_lookout")]
        if delayed or not self.state.flags.get("glasswater_valves_stabilized"):
            enemies.append(create_enemy("ochre_slime"))
        elif len(self.state.party_members()) >= 4:
            enemies.append(create_enemy("starblighted_miner"))
        hero_bonus = self.apply_scene_companion_support("glasswater_intake")
        if self.state.flags.get("glasswater_valves_stabilized"):
            hero_bonus += 1
        if self.state.flags.get("glasswater_chapel_answered"):
            hero_bonus += 1
        if self.state.flags.get("glasswater_relay_route_decoded"):
            hero_bonus += 1
        if self.state.flags.get("glasswater_runoff_sample"):
            hero_bonus += 1
        if self.state.flags.get("glasswater_flank_route"):
            hero_bonus += 1
            self.apply_status(enemies[0], "surprised", 1, source="the overflow crawl gave you the safer angle")
        choice = self.scenario_choice(
            "How do you break the Filter Beds line?",
            [
                self.skill_tag("ATHLETICS", self.action_option("Push straight through while the room is still trying to decide where to hold you.")),
                self.skill_tag("ARCANA", self.action_option("Use the valvework you stabilized and make the beds turn against them.")),
                self.skill_tag("STEALTH", self.action_option("Follow the adepts' safe lane and then cut it out from under them.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Push straight through while the room is still trying to decide where to hold you.")
            if self.skill_check(self.state.player, "Athletics", 14, context="to force the Glasswater filter beds"):
                hero_bonus += 1
                self.apply_status(self.state.player, "emboldened", 1, source="forcing the filtration line")
        elif choice == 2:
            self.player_action("Use the valvework you stabilized and make the beds turn against them.")
            if self.skill_check(self.state.player, "Arcana", 14, context="to redirect the Glasswater filter flow"):
                hero_bonus += 2 if self.state.flags.get("glasswater_valves_stabilized") else 1
                self.state.flags["glasswater_filters_purged"] = True
                self.apply_status(enemies[0], "reeling", 1, source="the beds lose their tuned cadence")
        else:
            self.player_action("Follow the adepts' safe lane and then cut it out from under them.")
            if self.skill_check(self.state.player, "Stealth", 14, context="to steal the Glasswater safe lane"):
                hero_bonus += 2 if self.state.flags.get("glasswater_relay_route_decoded") else 1
                self.apply_status(enemies[1], "surprised", 1, source="you came up the lane they trusted")
        outcome = self.run_encounter(
            Encounter(
                title="Glasswater Filter Beds",
                description="Half-finished filtration lines, murky footing, and a Choir adept turn the room itself into a sorting system.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The filter beds sort the party into the wrong side of the annex and the headgate keeps turning.")
            return
        if outcome == "fled":
            self.return_to_act2_hub("You fall back from the filter beds before the murk can turn the whole line against you.")
            return
        self.complete_act2_map_room(dungeon, room.room_id)

    def _glasswater_pump_gallery(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        delayed = self._glasswater_delayed()
        self.say("The pump gallery is where the annex stops pretending to be neglected. The housings are warm, the rods are greased, and somebody has been keeping this machine alive on purpose.")
        if delayed:
            self.say("One set of chain marks has been freshly stripped. Whatever witness line the room once held, somebody started cleaning it before you arrived.")
        choice = self.scenario_choice(
            "What do you secure before the headgate chamber?",
            [
                self.skill_tag("MEDICINE", self.action_option("Free the trapped workers and force the room to remember witnesses exist.")),
                self.skill_tag("INVESTIGATION", self.action_option("Sabotage the support pressure before the operator can use it.")),
                self.skill_tag("INSIGHT", self.action_option("Listen at the chamber door and learn what kind of doctrine talks to pipes.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Free the trapped workers and force the room to remember witnesses exist.")
            if self.skill_check(self.state.player, "Medicine", 14, context="to triage Glasswater's last trapped workers"):
                self.state.flags["glasswater_workers_staged"] = True
                if not delayed:
                    self.state.flags["glasswater_trapped_workers_saved"] = True
                self.say("The survivors do not have to fight for you. It is enough that they remain alive to contradict the room.")
        elif choice == 2:
            self.player_action("Sabotage the support pressure before the operator can use it.")
            if self.skill_check(self.state.player, "Investigation", 14, context="to cut Glasswater's headgate support pressure"):
                self.state.flags["glasswater_support_pressure_cut"] = True
                self.reward_party(xp=12, reason="cutting Glasswater's support pressure")
                self.say("Two turns, one loose pin, and the headgate loses the clean support line it expected.")
        else:
            self.player_action("Listen at the chamber door and learn what kind of doctrine talks to pipes.")
            if self.skill_check(self.state.player, "Insight", 14, context="to overhear Merik's doctrine without giving away the approach"):
                self.state.flags["glasswater_doctrine_overheard"] = True
                self.say('Beyond the door, a patient voice says, "Noise is not life. Most of the time it is waste pretending to be freedom."')
        self.complete_act2_map_room(dungeon, room.room_id)

    def _glasswater_headgate_chamber(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        delayed = self._glasswater_delayed()
        self.say("The chamber yawns open around a great iron wheel above a black running channel. Brass rods hum in their brackets. Prayer-strips float in the runoff like things too tired to sink.")
        self.speaker("Brother Merik Sorn", "Hold the wheel where it is. The count is almost clean.")
        self.speaker("Brother Merik Sorn", "One more turn and the whole intake starts teaching the same lesson to everyone downstream.")
        self.speaker("Brother Merik Sorn", "You came all this way to defend confusion, then.")
        if self.state.flags.get("glasswater_chapel_answered"):
            self.speaker(
                "Brother Merik Sorn",
                "You woke a maintenance prayer in a room built for service. Admirable. Wrong. Service without obedience is only delay.",
            )
        if self.state.flags.get("glasswater_claim_fraud_named"):
            self.speaker(
                "Brother Merik Sorn",
                "So you found the paper lie before the water lie. Most people need the sickness first.",
            )
        elif self.state.flags.get("glasswater_permit_fraud_exposed"):
            self.speaker(
                "Brother Merik Sorn",
                "Siltlock kept such tidy forms. I wondered when someone would mistake neat filing for innocence.",
            )
        elif self.state.flags.get("glasswater_relay_ledgers_taken"):
            self.speaker(
                "Brother Merik Sorn",
                "The papers mattered less than the rhythm they protected, but people like you always need ink before they trust a wound.",
            )
        if delayed:
            self.speaker("Brother Merik Sorn", "You are late. We already sent the cleaner copies and the dirtier water.")

        merik = create_enemy("choir_adept", name="Brother Merik Sorn")
        enemies = [merik]
        if not self.state.flags.get("glasswater_support_pressure_cut"):
            enemies.append(create_enemy("pact_archive_warden"))
        if delayed:
            enemies.append(create_enemy("claimbinder_notary"))
        elif len(self.state.party_members()) >= 4:
            enemies.append(create_enemy("false_map_skirmisher"))

        hero_bonus = self.apply_scene_companion_support("glasswater_intake")
        if self.state.flags.get("glasswater_valves_stabilized"):
            hero_bonus += 1
        if self.state.flags.get("glasswater_chapel_answered"):
            hero_bonus += 1
        if self.state.flags.get("glasswater_relay_route_decoded"):
            hero_bonus += 1
        if self.state.flags.get("glasswater_flood_release_jammed"):
            hero_bonus += 1
        if self.state.flags.get("glasswater_exit_timed"):
            hero_bonus += 1
        if self.state.flags.get("glasswater_support_pressure_cut"):
            hero_bonus += 1
        if self.state.flags.get("glasswater_workers_staged"):
            hero_bonus += 1
        if self.state.flags.get("glasswater_doctrine_overheard"):
            hero_bonus += 1
        if self.state.flags.get("glasswater_headgate_count_heard"):
            hero_bonus += 1
        if self.state.flags.get("glasswater_permit_fraud_exposed"):
            hero_bonus += 1
            self.state.flags["glasswater_claim_fraud_named"] = True
        if self.state.flags.get("glasswater_valve_wax_matched"):
            hero_bonus += 1
            self.apply_status(merik, "reeling", 1, source="the Siltlock wax sample naming the false seal")
        if self.state.flags.get("glasswater_flank_route"):
            hero_bonus += 1
            self.apply_status(merik, "surprised", 1, source="you reached the chamber from the overflow flank")

        choice = self.scenario_choice(
            "How do you open the Headgate confrontation?",
            [
                self.quoted_option("GATE", "Open the gate and step away from it."),
                self.quoted_option("TOWN", "You poisoned a town to test whether fear would travel faster than truth."),
                self.quoted_option("BREAK", "Break the tuning line now. We end this before the whole valley starts listening."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_speaker("Open the gate and step away from it.")
            self.speaker("Brother Merik Sorn", "Step away? From the first honest work this annex has done in a century?")
            self.speaker("Brother Merik Sorn", "No. You do not open a line like this and then hand it back to people who still think mercy means disorder.")
            if self.skill_check(self.state.player, "Persuasion", 14, context="to shake Merik's certainty before the headgate fight"):
                hero_bonus += 1
                self.apply_status(merik, "reeling", 1, source="you force the civic truth of the room back into the argument")
        elif choice == 2:
            self.player_speaker("You poisoned a town to test whether fear would travel faster than truth.")
            self.speaker("Brother Merik Sorn", "Not poisoned. Tuned.")
            self.speaker("Brother Merik Sorn", "Fear only moves faster than truth when truth insists on arriving in pieces.")
            if self.skill_check(self.state.player, "Intimidation", 14, context="to pin Merik on the human cost before the fight breaks open"):
                hero_bonus += 1
                merik.current_hp = max(1, merik.current_hp - 4)
        else:
            self.player_speaker("Break the tuning line now. We end this before the whole valley starts listening.")
            self.speaker("Brother Merik Sorn", "Then you do understand what this is.")
            self.speaker("Brother Merik Sorn", "Good. Understanding usually arrives one room before disobedience.")
            if self.skill_check(self.state.player, "Arcana", 14, context="to break the first tuning line before Merik can stabilize it"):
                hero_bonus += 2
                self.state.flags["glasswater_support_pressure_cut"] = True
                self.apply_status(merik, "reeling", 1, source="the tuning line breaks under your first push")

        if self._glasswater_active_companion("Elira Dawnmantle") is not None:
            self.speaker("Elira Lanternward", "You do not get to call sickness discipline because you wrote it down neatly.")
        if self._glasswater_active_companion("Bryn Underbough") is not None:
            self.speaker("Bryn Underbough", "He talks like a clerk who found religion at the bottom of a lockbox.")
        if self._glasswater_active_companion("Tolan Ironshield") is not None:
            self.speaker("Tolan Ironshield", "Enough. It is a waterworks annex, not a chapel for frightened accountants.")
        if self._glasswater_active_companion("Kaelis Starling") is not None:
            self.speaker("Kaelis Starling", "He keeps saying line because he wants the room to do the threatening for him.")

        outcome = self.run_encounter(
            Encounter(
                title="Brother Merik Sorn",
                description="A Quiet Choir field operator tries to turn Glasswater's headgate into a lesson the whole valley will learn together.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("Merik holds the headgate and Glasswater keeps teaching the valley the wrong lesson together.")
            return
        if outcome == "fled":
            self.return_to_act2_hub("You tear free of the headgate chamber before Glasswater can close the whole annex around you.")
            return

        self.complete_act2_map_room(dungeon, room.room_id)
        self.say("Brother Merik Sorn sags against the wheel, still trying to look like the room is the thing that defeated him rather than the people in it.")
        choice = self.scenario_choice(
            "What do you do with the headgate now?",
            [
                self.quoted_option("PURGE", "Purge the headgate. Let water be water again."),
                self.quoted_option("LOCK", "Lock the annex down and drag every ledger into daylight."),
                self.quoted_option("REPURPOSE", "Strip the Choir's tuning and keep the headgate for the expedition."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_speaker("Purge the headgate. Let water be water again.")
            self.state.flags["glasswater_headgate_purged"] = True
            self.act2_shift_metric(
                "act2_whisper_pressure",
                -1,
                "the Glasswater headgate stops carrying the Choir's lesson downstream and becomes a water line again",
            )
            self.speaker("Brother Merik Sorn", "Back to waste, then. Back to a town teaching itself ten fears badly.")
            result_text = "Glasswater's headgate runs clean again behind you, and the annex finally sounds like a waterworks instead of a warning."
        elif choice == 2:
            self.player_speaker("Lock the annex down and drag every ledger into daylight.")
            self.state.flags["glasswater_headgate_locked"] = True
            self.act2_shift_metric(
                "act2_town_stability",
                1,
                "Glasswater's ledgers and headgate both survive long enough to be named in daylight instead of rumor",
            )
            self.speaker("Brother Merik Sorn", "Better. Locks admit that value exists.")
            result_text = "You seal Glasswater under watch and take its ledgers topside, turning the annex into evidence before anyone can clean it into rumor."
        else:
            self.player_speaker("Strip the Choir's tuning and keep the headgate for the expedition.")
            self.state.flags["glasswater_headgate_repurposed"] = True
            self.act2_shift_metric(
                "act2_route_control",
                1,
                "the expedition takes control of Glasswater's headgate and turns a stolen system back toward its own routework",
            )
            self.act2_shift_metric(
                "act2_whisper_pressure",
                1,
                "keeping the headgate means choosing to stand closer to a dangerous signal in exchange for leverage",
            )
            self.speaker("Brother Merik Sorn", "There. That is the first honest choice you have made since entering.")
            result_text = "You strip the Choir's tuning and leave Glasswater running under your side's hand, useful now, but not innocent."

        self.reward_party(xp=65, gold=16, reason="securing Glasswater Intake")
        self._glasswater_award_baseline_rewards()
        self.return_to_act2_hub(result_text)

    def _siltlock_delayed(self) -> bool:
        assert self.state is not None
        return bool(self.state.flags.get(self.ACT2_SABOTAGE_RESOLVED_FLAG)) and not self.state.flags.get("siltlock_counting_house_cleared")

    def _siltlock_public_counter(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        delayed = self._siltlock_delayed()
        if not self.state.flags.get("siltlock_counting_house_seen"):
            self.say(
                "Siltlock Counting House stands behind the Ashlamp Inn with mud on the visitor boards and clean boot scuffs behind the rail. "
                "A brass counter bell gives one polite tap, then rings again somewhere under the floor.",
                typed=True,
            )
            if delayed:
                self.say("You reached Siltlock after sabotage night. The public ledgers are still damp, and the waste bin smells of burned receipt corners.")
            elif self.state.flags.get("glasswater_intake_cleared"):
                self.say("Glasswater's seized ledgers make the clerks flinch before you say a word. They know which permit numbers you brought with you.")
            self.state.flags["siltlock_counting_house_seen"] = True
        choice = self.scenario_choice(
            "How do you open the Siltlock audit?",
            [
                self.skill_tag("INVESTIGATION", self.action_option("Read the counter traffic and mark which books are being closed too quickly.")),
                self.skill_tag("PERSUASION", self.action_option("Make the junior clerk explain why the cellar bell rings before the street bell.")),
                self.skill_tag("PERCEPTION", self.action_option("Watch hands and shoes instead of faces until the hidden routine shows itself.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Read the counter traffic and mark which books are being closed too quickly.")
            if self.skill_check(self.state.player, "Investigation", 13, context="to read Siltlock's public counter traffic"):
                self.state.flags["siltlock_clerk_script_read"] = True
                self.add_clue("Siltlock's public counter closes water permits and ration amendments in the same hand, then sends both books below the floor.")
                self.reward_party(xp=10, reason="reading Siltlock's public counter")
        elif choice == 2:
            self.player_action("Make the junior clerk explain why the cellar bell rings before the street bell.")
            if self.skill_check(self.state.player, "Persuasion", 13, context="to make a Siltlock clerk talk before the office locks down"):
                self.state.flags["siltlock_junior_clerk_spooked"] = True
                self.add_clue("A Siltlock junior clerk admits the bell under the counter warns the ration cellar before the town watch hears trouble.")
                self.reward_party(xp=10, reason="spooking the Siltlock junior clerk")
        else:
            self.player_action("Watch hands and shoes instead of faces until the hidden routine shows itself.")
            if self.skill_check(self.state.player, "Perception", 13, context="to spot Siltlock's hidden office routine"):
                self.state.flags["siltlock_bell_line_found"] = True
                self.say("A clerk taps the counter twice with one finger and every clean pair of boots turns toward the cellar door.")
                self.reward_party(xp=10, reason="spotting Siltlock's bell routine")
        self.complete_act2_map_room(dungeon, room.room_id)

    def _siltlock_permit_stacks(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say(
            "The permit stacks breathe wet paper and lamp soot. Blue cord binds water passes, ferry claims, and repair delays into bundles that look official until the ink catches the light."
        )
        dc = 13 if self.state.flags.get("siltlock_clerk_script_read") or self.state.flags.get("glasswater_intake_cleared") else 14
        choice = self.scenario_choice(
            "How do you break the permit chain?",
            [
                self.skill_tag("INVESTIGATION", self.action_option("Match the false water permits by seal pressure and clerk hand.")),
                self.skill_tag("INSIGHT", self.action_option("Read which corrections were rehearsed before the permits were signed.")),
                self.skill_tag("PERSUASION", self.action_option("Corner the stack clerk with dates the books cannot make agree.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Match the false water permits by seal pressure and clerk hand.")
            if self.skill_check(self.state.player, "Investigation", dc, context="to expose Siltlock's false water permits"):
                self.state.flags["siltlock_false_permit_hand_named"] = True
                self.add_clue("Siltlock's false water permits were signed before Glasswater reported trouble, giving the lie a civic costume before the sickness spread.")
                self.reward_party(xp=10, reason="exposing Siltlock's false permit hand")
        elif choice == 2:
            self.player_action("Read which corrections were rehearsed before the permits were signed.")
            if self.skill_check(self.state.player, "Insight", dc, context="to read the rehearsed corrections in Siltlock's stacks"):
                self.state.flags["siltlock_rehearsed_corrections_read"] = True
                self.add_clue("Several Siltlock corrections were rehearsed in the margin before the permits were issued, which means the water delay had a script.")
                self.reward_party(xp=10, reason="reading Siltlock's rehearsed corrections")
        else:
            self.player_action("Corner the stack clerk with dates the books cannot make agree.")
            if self.skill_check(self.state.player, "Persuasion", dc, context="to crack the Siltlock stack clerk with bad dates"):
                self.state.flags["siltlock_stack_clerk_cracked"] = True
                self.add_clue("A Siltlock clerk names the permit shelf tied to Glasswater's relay office and the auditor who ordered it copied twice.")
                self.reward_party(xp=10, reason="cracking Siltlock's stack clerk")
        self.complete_act2_map_room(dungeon, room.room_id)

    def _siltlock_ration_cellar(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        delayed = self._siltlock_delayed()
        self.say(
            "The ration cellar smells of flour, pickled turnip, lantern oil, and wet rope. Charity crates sit under a neat sign while quiet reserve marks hide on the sides facing the wall."
        )
        enemies = [create_enemy("cult_lookout"), create_enemy("expedition_reaver")]
        if delayed:
            enemies.append(create_enemy("claimbinder_notary"))
        elif len(self.state.party_members()) >= 4:
            enemies.append(self.act2_pick_enemy(("gutter_zealot", "false_map_skirmisher", "cult_lookout")))
        hero_bonus = self.apply_scene_companion_support("siltlock_counting_house")
        if self.state.flags.get("siltlock_bell_line_found"):
            hero_bonus += 1
            self.apply_status(enemies[0], "surprised", 1, source="you found the cellar warning line first")
        if self.state.flags.get("siltlock_junior_clerk_spooked"):
            hero_bonus += 1
        choice = self.scenario_choice(
            "How do you take the ration cellar?",
            [
                self.skill_tag("STEALTH", self.action_option("Cut the bell cord before the cellar crew can call the office down on you.")),
                self.skill_tag("INTIMIDATION", self.action_option("Name the stolen charity marks loudly enough that the guards lose their script.")),
                self.skill_tag("ATHLETICS", self.action_option("Topple the oil racks and make the cellar defend itself badly.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Cut the bell cord before the cellar crew can call the office down on you.")
            if self.skill_check(self.state.player, "Stealth", 14, context="to cut Siltlock's cellar alarm"):
                hero_bonus += 2
                self.state.flags["siltlock_cellar_alarm_cut"] = True
                self.apply_status(enemies[0], "surprised", 1, source="the cellar bell going slack")
        elif choice == 2:
            self.player_action("Name the stolen charity marks loudly enough that the guards lose their script.")
            if self.skill_check(self.state.player, "Intimidation", 14, context="to break Siltlock cellar morale with the ration marks"):
                hero_bonus += 1
                self.state.flags["siltlock_ration_mark_named"] = True
                self.apply_status(enemies[1], "frightened", 1, source="the charity marks being named aloud")
        else:
            self.player_action("Topple the oil racks and make the cellar defend itself badly.")
            if self.skill_check(self.state.player, "Athletics", 14, context="to turn Siltlock's cellar shelves against the defenders"):
                hero_bonus += 1
                enemies[0].current_hp = max(1, enemies[0].current_hp - 4)
        outcome = self.run_encounter(
            Encounter(
                title="Siltlock Ration Cellar",
                description="Bribed guards and Choir watchers defend stolen charity stores before the town can count them.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=True,
                parley_dc=14,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The ration cellar locks down, and Siltlock's supply books keep their clean cover.")
            return
        if outcome == "fled":
            self.return_to_act2_hub("You withdraw from Siltlock before the cellar crew can trap the whole party below the office.")
            return
        self.complete_act2_map_room(dungeon, room.room_id)
        self.add_clue("Siltlock's ration cellar was holding charity supplies, watch lantern oil, and reserve marks for the night Iron Hollow would be easiest to panic.")

    def _siltlock_back_till(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        sponsor = str(self.state.flags.get("act2_sponsor", "council"))
        self.say(
            "The back till cage holds clipped coin, sponsor chits, and green wax wafers wrapped in cheesecloth. The lock is expensive, ugly, and recently oiled."
        )
        if sponsor == "exchange":
            self.say("Exchange chits sit in the shallow drawer, arranged so a fast search would find them first.")
        elif sponsor == "lionshield":
            self.say("Lionshield crate seals hang from a nail beside the till, clean enough to look planted and useful enough to hurt.")
        else:
            self.say("Council signatures have been scraped thin on three receipts, leaving the paper soft where names should be.")
        choice = self.scenario_choice(
            "What do you take from the back till cage?",
            [
                self.skill_tag("INVESTIGATION", self.action_option("Sort planted sponsor chits from the payments that actually moved.")),
                self.skill_tag("SLEIGHT OF HAND", self.action_option("Lift the green wax wafers before the cage's burner slot eats them.")),
                self.skill_tag("INSIGHT", self.action_option("Read which accusation the room wants you to make too quickly.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Sort planted sponsor chits from the payments that actually moved.")
            if self.skill_check(self.state.player, "Investigation", 14, context="to sort Siltlock's sponsor chits"):
                self.state.flags["siltlock_sponsor_chits_sorted"] = True
                self.add_clue("Siltlock's sponsor chits were arranged for leverage. The useful payments are smaller, uglier, and tied to water permits.")
                self.reward_party(xp=10, reason="sorting Siltlock's sponsor chits")
        elif choice == 2:
            self.player_action("Lift the green wax wafers before the cage's burner slot eats them.")
            if self.skill_check(self.state.player, "Sleight of Hand", 14, context="to lift Siltlock's green wax wafers"):
                self.state.flags["siltlock_green_wax_wafers_taken"] = True
                self.add_clue("Siltlock kept green valve wax in the pay cage, wrapped like medicine and logged like a petty cash expense.")
                self.reward_party(xp=10, reason="preserving Siltlock's green wax")
        else:
            self.player_action("Read which accusation the room wants you to make too quickly.")
            if self.skill_check(self.state.player, "Insight", 14, context="to read Siltlock's planted accusation"):
                self.state.flags["siltlock_planted_accusation_seen"] = True
                self.add_clue("The back till was staged to make one sponsor look solely guilty while the working fraud stayed in permit numbers and wax seals.")
                self.reward_party(xp=10, reason="catching Siltlock's planted accusation")
        self.reward_party(gold=8, reason="seizing Siltlock's clipped coin")
        self.complete_act2_map_room(dungeon, room.room_id)

    def _siltlock_valve_wax_archive(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say(
            "Thin drawers line the archive wall, each one holding wax impressions for valves, water permits, and route locks. Several seals carry green grit that catches under a fingernail."
        )
        dc = 13 if self.state.flags.get("siltlock_green_wax_wafers_taken") or self.state.flags.get("siltlock_permit_chain_read") else 14
        choice = self.scenario_choice(
            "How do you preserve the valve-wax proof?",
            [
                self.skill_tag("ARCANA", self.action_option("Read the green grit for resonance before the wax goes soft.")),
                self.skill_tag("INVESTIGATION", self.action_option("Match the drawer marks to Glasswater's valve sequence.")),
                self.skill_tag("SLEIGHT OF HAND", self.action_option("Take a clean wax sample before the archive burner wakes up.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Read the green grit for resonance before the wax goes soft.")
            if self.skill_check(self.state.player, "Arcana", dc, context="to read Siltlock's valve wax resonance"):
                self.state.flags["siltlock_wax_resonance_read"] = True
                self.add_clue("The green grit in Siltlock's wax carries the same measured resonance used to make Glasswater's valves obey the wrong schedule.")
                self.reward_party(xp=12, reason="reading Siltlock's valve wax")
        elif choice == 2:
            self.player_action("Match the drawer marks to Glasswater's valve sequence.")
            if self.skill_check(self.state.player, "Investigation", dc, context="to match Siltlock wax to Glasswater's valve sequence"):
                self.state.flags["siltlock_wax_drawer_matched"] = True
                self.add_clue("Siltlock's wax archive names the Glasswater valve sequence that was approved on paper before the annex ever reported a fault.")
                self.reward_party(xp=12, reason="matching Siltlock wax to Glasswater")
        else:
            self.player_action("Take a clean wax sample before the archive burner wakes up.")
            if self.skill_check(self.state.player, "Sleight of Hand", dc, context="to preserve a clean Siltlock wax sample"):
                self.state.flags["siltlock_clean_wax_sample"] = True
                self.add_clue("A clean Siltlock wax sample survives the burner slot and can be matched against Glasswater's valve locks.")
                self.reward_party(xp=12, reason="preserving Siltlock's wax sample")
        self.complete_act2_map_room(dungeon, room.room_id)

    def _siltlock_sluice_bell_alcove(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        delayed = self._siltlock_delayed()
        self.say(
            "A waist-high bell hangs in a stone alcove behind the cellar. The pull cord runs toward the watch post, then loops back into Siltlock through a bitten hole in the mortar."
        )
        if delayed:
            self.say("The cord is frayed from recent use. The bell warned the counting house before the street heard anything.")
        dc = 13 if self.state.flags.get("siltlock_cellar_alarm_cut") or self.state.flags.get("siltlock_bell_line_found") else 14
        choice = self.scenario_choice(
            "How do you turn the sluice bell?",
            [
                self.skill_tag("INVESTIGATION", self.action_option("Trace the cord and prove where the town warning was stolen.")),
                self.skill_tag("SLEIGHT OF HAND", self.action_option("Rewire the bell so the next pull reaches the watch post first.")),
                self.skill_tag("ATHLETICS", self.action_option("Tear the return line out of the wall and make the bell honest by force.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Trace the cord and prove where the town warning was stolen.")
            if self.skill_check(self.state.player, "Investigation", dc, context="to trace Siltlock's stolen warning cord"):
                self.state.flags["siltlock_warning_theft_proven"] = True
                self.add_clue("Siltlock's sluice bell was routed to warn the office before the watch, which let supplies vanish while the street waited for help.")
                self.reward_party(xp=12, reason="tracing Siltlock's warning bell")
        elif choice == 2:
            self.player_action("Rewire the bell so the next pull reaches the watch post first.")
            if self.skill_check(self.state.player, "Sleight of Hand", dc, context="to rewire Siltlock's sluice bell"):
                self.state.flags["siltlock_watch_bell_rewired"] = True
                self.reward_party(xp=12, reason="rewiring Siltlock's warning bell")
        else:
            self.player_action("Tear the return line out of the wall and make the bell honest by force.")
            if self.skill_check(self.state.player, "Athletics", dc, context="to tear out Siltlock's return line"):
                self.state.flags["siltlock_return_line_torn_out"] = True
                self.apply_status(self.state.player, "emboldened", 1, source="ripping Siltlock's bell line open")
                self.reward_party(xp=12, reason="breaking Siltlock's stolen warning line")
        self.complete_act2_map_room(dungeon, room.room_id)

    def _siltlock_auditor_stair(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        delayed = self._siltlock_delayed()
        enemies = [create_enemy("claimbinder_notary", name="Auditor Pella Varr"), create_enemy("cult_lookout")]
        if not self.state.flags.get("siltlock_ration_tags_recovered"):
            enemies.append(create_enemy("expedition_reaver"))
        if delayed or len(self.state.party_members()) >= 4:
            enemies.append(self.act2_pick_enemy(("false_map_skirmisher", "gutter_zealot", "choir_cartographer")))
        hero_bonus = self.apply_scene_companion_support("siltlock_counting_house")
        parley_dc = 14
        self.say(
            "The auditor's stair climbs above the public counter in tight turns. Each landing holds a little trash cup full of burned receipt corners."
        )
        if self.state.flags.get("glasswater_permit_fraud_exposed"):
            hero_bonus += 1
            parley_dc -= 1
            self.apply_status(enemies[0], "reeling", 1, source="the false water permits already being in your hand")
        if self.state.flags.get("sabotage_supply_watch_warned"):
            hero_bonus += 1
            parley_dc -= 1
        if self.state.flags.get("act2_sponsor_pressure_named"):
            hero_bonus += 1
        if self.state.flags.get("glasswater_valve_wax_matched"):
            enemies[0].current_hp = max(1, enemies[0].current_hp - 4)
        self.speaker("Auditor Pella Varr", "Careful on the stairs. People drop things here. Receipts, accusations, friends.")
        self.speaker("Auditor Pella Varr", "Every town survives by filing some sins under maintenance.")
        choice = self.scenario_choice(
            "How do you break the auditor's control?",
            [
                self.skill_tag("PERSUASION", self.action_option("Offer public testimony and a narrow way out before Pella burns the last ledger.")),
                self.skill_tag("INTIMIDATION", self.action_option("Put the ration tags on the stair and make every guard see what they defended.")),
                self.skill_tag("INVESTIGATION", self.action_option("Read the burn cups and name which ledger corner still matters.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Offer public testimony and a narrow way out before Pella burns the last ledger.")
            if self.skill_check(self.state.player, "Persuasion", parley_dc, context="to break Pella Varr's control with public testimony"):
                hero_bonus += 2
                self.state.flags["siltlock_auditor_testimony_secured"] = True
                self.apply_status(enemies[0], "frightened", 1, source="public testimony becoming possible")
        elif choice == 2:
            self.player_action("Put the ration tags on the stair and make every guard see what they defended.")
            if self.skill_check(self.state.player, "Intimidation", parley_dc, context="to crack the Siltlock guards with the ration tags"):
                hero_bonus += 2
                self.state.flags["siltlock_guards_cracked"] = True
                if len(enemies) > 1:
                    self.apply_status(enemies[1], "frightened", 1, source="the charity tags landing on the stair")
        else:
            self.player_action("Read the burn cups and name which ledger corner still matters.")
            if self.skill_check(self.state.player, "Investigation", parley_dc, context="to recover the one burned ledger corner that matters"):
                hero_bonus += 2
                self.state.flags["siltlock_burned_corner_recovered"] = True
                enemies[0].current_hp = max(1, enemies[0].current_hp - 4)
        outcome = self.run_encounter(
            Encounter(
                title="Siltlock Auditor's Stair",
                description="Auditor Pella Varr tries to turn evidence, guards, and burned receipt corners into a last clean escape.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=True,
                parley_dc=max(12, parley_dc),
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("Siltlock's auditor burns the useful corners and leaves the town with ash where names should be.")
            return
        if outcome == "fled":
            self.return_to_act2_hub("You fall back from Siltlock before Pella's guards can pin the whole party on the stair.")
            return
        self.complete_act2_map_room(dungeon, room.room_id)
        self.reward_party(xp=45, gold=12, reason="breaking Siltlock Counting House")
        if self.state.flags.get("glasswater_permit_fraud_exposed"):
            self.add_journal("You broke Siltlock's permit chain and carried its water fraud back to the expedition table.")
        if self.state.flags.get("sabotage_supply_watch_warned"):
            self.add_journal("You exposed Siltlock's stolen warning bell and ration tags before they could hide inside civic procedure.")
        self.add_clue("Siltlock Counting House used permits, wax seals, and ration amendments to make sabotage look like routine town work.")
        self.return_to_act2_hub("Siltlock's ledgers leave in your hands, and the little cellar bell finally rings toward the street.")

    def _broken_prospect_delayed(self) -> bool:
        assert self.state is not None
        return self.state.flags.get("act2_first_late_route") == "south_adit"

    def _broken_prospect_broken_shelf(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        if not self.state.flags.get("act2_first_late_route"):
            self.act2_mark_late_route_choice("broken_prospect")
        if not self.has_quest("free_wave_echo_captives"):
            self.grant_quest("free_wave_echo_captives")
        if not self.has_quest("sever_quiet_choir"):
            self.grant_quest("sever_quiet_choir")
        if not self.state.flags.get("broken_prospect_seen"):
            self.say(
                "Broken Prospect is a jagged approach above Resonant Vaults: half collapsed survey cut, half old dwarfwork scar, "
                "and now one more place where history is trying to decide which footsteps matter.",
                typed=True,
            )
            if self._broken_prospect_delayed():
                self.say(
                    "Because you chose the prison line first, rival crews and cult sentries have had longer to root themselves into the prospect shelves."
                )
            self.state.flags["broken_prospect_seen"] = True
        choice = self.scenario_choice(
            "How do you make first contact with the cave approach?",
            [
                self.skill_tag("HISTORY", self.action_option("Call the old survey marks before the echoes lie about distance.")),
                self.skill_tag("STEALTH", self.action_option("Use the broken prospect ledge and slip past the first sentries.")),
                self.skill_tag("RELIGION", self.action_option("Steady the line before the dead memory of this place gets teeth.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Call the old survey marks before the echoes lie about distance.")
            if self.skill_check(self.state.player, "History", 14, context="to use the Meridian Compact survey marks correctly"):
                self.state.flags["prospect_shelf_marks_read"] = True
                self.reward_party(xp=10, reason="reading the Broken Prospect shelf marks")
                self.say("The old marks stop being decoration and become a usable way to judge distance.")
        elif choice == 2:
            self.player_action("Use the broken prospect ledge and slip past the first sentries.")
            if self.skill_check(self.state.player, "Stealth", 14, context="to slip into Broken Prospect cleanly"):
                self.state.flags["prospect_ledge_approach"] = True
                self.say("The ledge is ugly, but it gives you the first angle before the threshold realizes you have one.")
        else:
            self.player_action("Steady the line before the dead memory of this place gets teeth.")
            if self.skill_check(self.state.player, "Religion", 14, context="to keep the haunted threshold from owning the pace"):
                self.state.flags["prospect_threshold_steadied"] = True
                self.apply_status(self.state.player, "blessed", 2, source="meeting the cave with deliberate faith")
        self.complete_act2_map_room(dungeon, room.room_id)

    def _broken_prospect_pact_markers(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("The Meridian Compact markers cut across stone, timber, and old claim stakes, half survey language and half warning prayer.")
        dc = 13 if self.state.flags.get("prospect_shelf_marks_read") or self.state.flags.get("nim_countermeasure_notes") else 14
        choice = self.scenario_choice(
            "How do you make the markers useful?",
            [
                self.skill_tag("HISTORY", self.action_option("Read the dwarfwork survey order and call the true span.")),
                self.skill_tag("INVESTIGATION", self.action_option("Compare new claim scratches against the older route logic.")),
                self.skill_tag("ARCANA", self.action_option("Find the parts of the marking that still answer old Meridian Compact law.")),
            ],
            allow_meta=False,
        )
        skill = "History" if choice == 1 else "Investigation" if choice == 2 else "Arcana"
        if self.skill_check(self.state.player, skill, dc, context="to decode Broken Prospect's Meridian Compact markers"):
            self.state.flags["prospect_markers_decoded"] = True
            self.reward_party(xp=10, reason="decoding the Broken Prospect markers")
            self.say("The threshold resolves into spans, turns, and a warning about the foreman's dead shift below.")
        else:
            self.say("You get enough of the pattern to move, but the dead-shift warning stays more feeling than fact.")
        self.complete_act2_map_room(dungeon, room.room_id)

    def _broken_prospect_rival_survey_shelf(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("The delayed survey shelf is no longer empty. Rival claim stakes share space with Choir scratch marks and a lookout who knows exactly why this route mattered.")
        enemies = [create_enemy("cult_lookout")]
        if self.act2_metric_value("act2_route_control") <= 2:
            enemies.append(self.act2_pick_enemy(("expedition_reaver", "cult_lookout", "starblighted_miner")))
        else:
            enemies.append(self.act2_pick_enemy(("expedition_reaver", "cult_lookout")))
        if len(self.state.party_members()) >= 4:
            enemies.append(self.act2_pick_enemy(("grimlock_tunneler", "starblighted_miner", "cult_lookout")))
        hero_bonus = self.apply_scene_companion_support("broken_prospect")
        if self.state.flags.get("prospect_ledge_approach"):
            hero_bonus += 1
            self.apply_status(enemies[0], "surprised", 1, source="your ledge approach")
        choice = self.scenario_choice(
            "How do you break the rival shelf?",
            [
                self.skill_tag("STEALTH", self.action_option("Slip behind the claim stakes and cut off the lookout's escape.")),
                self.skill_tag("INTIMIDATION", self.action_option("Make it clear that this claim is not surviving contact with you.")),
                self.skill_tag("INVESTIGATION", self.action_option("Spot the false survey line and turn their prepared angle against them.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Slip behind the claim stakes and cut off the lookout's escape.")
            if self.skill_check(self.state.player, "Stealth", 14, context="to flank the rival survey shelf"):
                hero_bonus += 2
                self.apply_status(enemies[0], "surprised", 1, source="you reached the shelf from behind")
        elif choice == 2:
            self.player_action("Make it clear that this claim is not surviving contact with you.")
            if self.skill_check(self.state.player, "Intimidation", 14, context="to crack the rival survey crew's nerve"):
                hero_bonus += 1
                enemies[-1].current_hp = max(1, enemies[-1].current_hp - 3)
        else:
            self.player_action("Spot the false survey line and turn their prepared angle against them.")
            if self.skill_check(self.state.player, "Investigation", 14, context="to read the rival shelf's false survey line"):
                hero_bonus += 2
                self.state.flags["prospect_false_claim_exposed"] = True
        outcome = self.run_encounter(
            Encounter(
                title="Broken Prospect Rival Shelf",
                description="Delayed claimants and Choir scouts try to keep the cleaner Resonant Vaults approach from returning to your map.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=True,
                parley_dc=14,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The rival shelf throws the company back before the prospect route can be reclaimed.")
            return
        if outcome == "fled":
            self.return_to_act2_hub("You withdraw from the rival shelf before the claimants can pin the whole company there.")
            return
        self.complete_act2_map_room(dungeon, room.room_id)

    def _broken_prospect_sentinel_span(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("The sentinel span crosses old dwarfwork where a suit of armor still remembers a duty nobody living gave it.")
        enemies = [create_enemy("pact_archive_warden")]
        if self.act2_metric_value("act2_whisper_pressure") >= 4:
            enemies.append(self.act2_pick_enemy(("blacklake_adjudicator", "obelisk_eye")))
        elif len(self.state.party_members()) >= 4:
            enemies.append(self.act2_pick_enemy(("blackglass_listener", "grimlock_tunneler", "starblighted_miner")))
        hero_bonus = self.apply_scene_companion_support("broken_prospect")
        if self.state.flags.get("prospect_markers_decoded"):
            hero_bonus += 1
        choice = self.scenario_choice(
            "How do you cross the sentinel span?",
            [
                self.skill_tag("HISTORY", self.action_option("Call the old pass-mark and make the armor hesitate.")),
                self.skill_tag("ATHLETICS", self.action_option("Take the span fast and turn the narrow footing into your pressure.")),
                self.skill_tag("RELIGION", self.action_option("Treat the armor like a dead oath instead of a machine.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Call the old pass-mark and make the armor hesitate.")
            if self.skill_check(self.state.player, "History", 14, context="to call the Broken Prospect sentinel mark"):
                hero_bonus += 2
                self.apply_status(enemies[0], "reeling", 1, source="the old pass-mark")
        elif choice == 2:
            self.player_action("Take the span fast and turn the narrow footing into your pressure.")
            if self.skill_check(self.state.player, "Athletics", 14, context="to force the sentinel span"):
                hero_bonus += 1
                self.apply_status(self.state.player, "emboldened", 2, source="forcing the sentinel span")
        else:
            self.player_action("Treat the armor like a dead oath instead of a machine.")
            if self.skill_check(self.state.player, "Religion", 14, context="to answer the sentinel oath"):
                hero_bonus += 1
                self.state.flags["prospect_dead_oath_answered"] = True
        outcome = self.run_encounter(
            Encounter(
                title="Broken Prospect Sentinel Span",
                description="Old Meridian Compact armor tests the party before the cave approach can become a true route.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The sentinel span holds and the Resonant Vaults' threshold throws the company back.")
            return
        if outcome == "fled":
            self.return_to_act2_hub("You retreat from the sentinel span before the old armor can turn the ledge into a drop.")
            return
        self.complete_act2_map_room(dungeon, room.room_id)

    def _broken_prospect_sealed_approach(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("Behind the rival shelf, a sealed approach holds route nails, old tally slates, and a claim cache nobody had time to strip clean.")
        choice = self.scenario_choice(
            "What do you take from the sealed approach?",
            [
                self.skill_tag("INVESTIGATION", self.action_option("Recover the route cache and prove which survey marks were real.")),
                self.skill_tag("SLEIGHT OF HAND", self.action_option("Open the sealed coffer without breaking the old slates inside.")),
                self.skill_tag("HISTORY", self.action_option("Record the dead labor tally so the foreman's pattern makes sense.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Recover the route cache and prove which survey marks were real.")
            if self.skill_check(self.state.player, "Investigation", 14, context="to recover the Broken Prospect route cache"):
                self.state.flags["prospect_route_cache_read"] = True
                self.reward_party(xp=10, reason="recovering the Broken Prospect route cache")
                self.say("The cache turns the shelf from rumor into route control.")
        elif choice == 2:
            self.player_action("Open the sealed coffer without breaking the old slates inside.")
            if self.skill_check(self.state.player, "Sleight of Hand", 14, context="to open the Broken Prospect coffer"):
                self.add_inventory_item("scroll_arcane_refresh", source="the Broken Prospect sealed approach")
                self.say("The coffer opens without snapping the slate bundle inside.")
            else:
                self.say("The coffer fights you, but the route slates survive with only one ugly crack.")
        else:
            self.player_action("Record the dead labor tally so the foreman's pattern makes sense.")
            if self.skill_check(self.state.player, "History", 14, context="to read the dead labor tally"):
                self.state.flags["prospect_foreman_tally_read"] = True
                self.say("The tally gives the foreman's dead shift a pattern you can interrupt later.")
        self.complete_act2_map_room(dungeon, room.room_id)

    def _broken_prospect_foreman_shift(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        delayed = self._broken_prospect_delayed()
        enemies = [create_enemy("spectral_foreman")]
        if not self.state.flags.get("prospect_sentinel_span_cleared"):
            enemies.insert(0, create_enemy("pact_archive_warden"))
        if delayed or self.act2_metric_value("act2_route_control") <= 2:
            enemies.append(self.act2_pick_enemy(("blackglass_listener", "survey_chain_revenant", "obelisk_eye")))
        if len(self.state.party_members()) >= 4:
            enemies.append(self.act2_pick_enemy(("cult_lookout", "grimlock_tunneler", "survey_chain_revenant")))
        hero_bonus = 0
        if self.state.flags.get("nim_countermeasure_notes"):
            hero_bonus += 1
            self.say("Nim's preserved theorem notes let you predict which part of the prospect's echo is honest and which part is bait.")
        if self.state.flags.get("prospect_markers_decoded"):
            hero_bonus += 1
        if self.state.flags.get("prospect_route_cache_read") or self.state.flags.get("prospect_cache_secured"):
            hero_bonus += 1
        if self.state.flags.get("prospect_foreman_tally_read"):
            hero_bonus += 1
        if self.state.flags.get("prospect_threshold_steadied"):
            hero_bonus += 1
        choice = self.scenario_choice(
            "How do you break the dead foreman's shift?",
            [
                self.skill_tag("HISTORY", self.action_option("Call the old survey marks before the echoes lie about distance.")),
                self.skill_tag("STEALTH", self.action_option("Use the broken prospect ledge and hit the foreman from the blind side.")),
                self.skill_tag("RELIGION", self.action_option("Steady the line before the dead memory of this place gets teeth.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Call the old survey marks before the echoes lie about distance.")
            if self.skill_check(self.state.player, "History", 14, context="to use the Meridian Compact survey marks correctly"):
                hero_bonus += 2
        elif choice == 2:
            self.player_action("Use the broken prospect ledge and hit the foreman from the blind side.")
            if self.skill_check(self.state.player, "Stealth", 14, context="to slip into Resonant Vaults cleanly"):
                hero_bonus += 2
                self.apply_status(enemies[0], "surprised", 1, source="your ledge approach")
        else:
            self.player_action("Steady the line before the dead memory of this place gets teeth.")
            if self.skill_check(self.state.player, "Religion", 14, context="to keep the haunted threshold from owning the pace"):
                hero_bonus += 1
                self.apply_status(self.state.player, "blessed", 2, source="meeting the cave with deliberate faith")
        outcome = self.run_encounter(
            Encounter(
                title="Broken Prospect",
                description="The first Resonant Vaults guardians still answer old duties, even now that new masters are twisting them.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The Resonant Vaults' threshold throws the company back into the dark above.")
            return
        if outcome == "fled":
            self.return_to_act2_hub("You withdraw from the cave mouth before the threshold can swallow the approach.")
            return
        self.complete_act2_map_room(dungeon, room.room_id)
        self.act2_shift_metric(
            "act2_route_control",
            1,
            "the prospect approach now belongs to your side instead of whoever would have claimed it with confidence and bad intent",
        )
        if self.state.flags.get("act2_captive_outcome") == "captives_endangered":
            self.say(
                "The route is cleaner now, but nobody in camp mistakes that clean line for a moral victory while the South Adit still holds prisoners."
            )
        self.return_to_act2_hub("Broken Prospect finally resolves into a real route, and Resonant Vaults has one less way to lie about where it begins.")

    def _south_adit_delayed(self) -> bool:
        assert self.state is not None
        return self.state.flags.get("act2_first_late_route") == "broken_prospect"

    def _south_adit_prison_cadence(self, *, delayed: bool) -> int:
        assert self.state is not None
        cadence = 3 + (1 if delayed else 0)
        for flag in (
            "south_adit_patrol_rhythm_read",
            "south_adit_alarm_muted",
            "south_adit_hush_prayers_broken",
            "south_adit_counter_cadence_learned",
        ):
            if self.state.flags.get(flag):
                cadence -= 1
        if self.state.flags.get("south_adit_irielle_plan") == "break":
            cadence -= 1
        return max(0, min(5, cadence))

    def _south_adit_prison_cadence_label(self, cadence: int) -> str:
        if cadence <= 0:
            return "Broken"
        if cadence == 1:
            return "Suppressed"
        if cadence == 2:
            return "Shaken"
        if cadence == 3:
            return "Pressing"
        if cadence == 4:
            return "Hammering"
        return "Ironbound"

    def _south_adit_prison_cadence_summary(self, cadence: int) -> str:
        if cadence <= 0:
            return "The prison line loses its count completely."
        if cadence == 1:
            return "The wardens are off-step and shouting to recover the rhythm."
        if cadence == 2:
            return "The adit answers unevenly, buying the captives room to move."
        if cadence == 3:
            return "Every corridor is still taking the Choir's measure."
        if cadence == 4:
            return "The wardens are dragging the whole line back into obedience."
        return "The prison itself is marching with the Choir."

    def _south_adit_award_route_rewards(self) -> None:
        assert self.state is not None
        outcome = str(self.state.flags.get("act2_captive_outcome", "uncertain"))
        if outcome == "many_saved":
            self.act2_award_milestone_gear(
                "act2_south_adit_milestone_gear",
                "choirward_amulet_rare",
                source="the South Adit prisoner cache",
            )
            self.say(
                "Wrapped in oilcloth at the back of the prisoner cache is a Starforged Choirward Amulet, worked so one clean refusal can carry a whole fight."
            )
            return
        self.act2_award_milestone_gear(
            "act2_south_adit_milestone_gear",
            "choirward_amulet_uncommon",
            source="the South Adit prisoner cache",
        )
        if not self.state.flags.get("act2_south_adit_counter_cadence_cache"):
            if self.add_inventory_item("scroll_counter_cadence", source="Irielle's counter-cadence cache"):
                self.state.flags["act2_south_adit_counter_cadence_cache"] = True
        self.say(
            "The cache yields an ash-kissed choirward charm and Irielle's Counter-Cadence Script, a one-use answer to the Choir's rhythm."
        )

    def _south_adit_adit_mouth(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        if not self.state.flags.get("act2_first_late_route"):
            self.act2_mark_late_route_choice("south_adit")
        if not self.has_quest("free_wave_echo_captives"):
            self.grant_quest("free_wave_echo_captives")
        if not self.has_quest("sever_quiet_choir"):
            self.grant_quest("sever_quiet_choir")
        if not self.state.flags.get("south_adit_seen"):
            self.say(
                "The southern workings smell like old iron, cold water, and fear kept quiet too long. Cells have been built into the support chambers. "
                "The Quiet Choir turned part of Resonant Vaults into a sorting room.",
                typed=True,
            )
            if self._south_adit_delayed():
                self.say(
                    "Broken Prospect going first bought your side a cleaner route, but the adit has had longer to become a place of missing names and emptied cells."
                )
            self.state.flags["south_adit_seen"] = True
        choice = self.scenario_choice(
            "How do you read the prison mouth before the wardens know you are inside?",
            [
                self.skill_tag("PERCEPTION", self.action_option("Count the patrol bells and learn when the cell block breathes.")),
                self.skill_tag("SLEIGHT OF HAND", self.action_option("Mute the first alarm chain before it can carry sound down the line.")),
                self.skill_tag("MEDICINE", self.action_option("Mark the weakest voices first so the rescue starts with the living.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Count the patrol bells and learn when the cell block breathes.")
            if self.skill_check(self.state.player, "Perception", 13, context="to read the South Adit prison rhythm"):
                self.state.flags["south_adit_patrol_rhythm_read"] = True
                self.say("The wardens are disciplined, but not imaginative. You can hear the gap they trust too much.")
        elif choice == 2:
            self.player_action("Mute the first alarm chain before it can carry sound down the line.")
            if self.skill_check(self.state.player, "Sleight of Hand", 13, context="to mute the adit's first alarm chain"):
                self.state.flags["south_adit_alarm_muted"] = True
                self.say("The chain still moves, but it no longer sings for help.")
        else:
            self.player_action("Mark the weakest voices first so the rescue starts with the living.")
            if self.skill_check(self.state.player, "Medicine", 13, context="to triage the adit prisoners from the first signs"):
                self.state.flags["south_adit_triage_started"] = True
                self.say("You catch the signs that matter: shallow breath, bad silence, and who must leave first.")
        self.complete_act2_map_room(dungeon, room.room_id)

    def _south_adit_silent_cells(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("The first cell row holds people too tired to shout and wardens confident enough to mistake that for control.")
        choice = self.scenario_choice(
            "How do you open the silent cells?",
            [
                self.skill_tag("SLEIGHT OF HAND", self.action_option("Open the locks quietly and pass tools through before anyone runs.")),
                self.skill_tag("PERSUASION", self.action_option("Keep the prisoners silent, steady, and moving together.")),
                self.skill_tag("INTIMIDATION", self.action_option("Let the nearest warden see the cells opening and understand what comes next.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Open the locks quietly and pass tools through before anyone runs.")
            if self.skill_check(self.state.player, "Sleight of Hand", 14, context="to open the South Adit cells quietly"):
                self.state.flags["south_adit_cells_quietly_opened"] = True
                self.reward_party(xp=10, reason="opening the South Adit cells quietly")
                self.say("Locks give one after another, quiet enough that hope has to be whispered down the row.")
        elif choice == 2:
            self.player_speaker("No running blind. Breathe, pass it down, and move when I move.")
            if self.skill_check(self.state.player, "Persuasion", 13, context="to keep the captives steady"):
                self.state.flags["south_adit_prisoners_steadied"] = True
                self.say("The row becomes a line instead of a panic.")
        else:
            self.player_action("Let the nearest warden see the cells opening and understand what comes next.")
            if self.skill_check(self.state.player, "Intimidation", 14, context="to break the first warden's nerve"):
                self.state.flags["south_adit_warden_nerve_cracked"] = True
                self.say("The nearest guard backs away from the cell row before the fight has technically started.")
        self.complete_act2_map_room(dungeon, room.room_id)

    def _south_adit_drainage_exit(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("The drainage exit is a wet side cut full of dropped manacles, old boot prints, and things that learned to hunt by listening upward.")
        enemies = [create_enemy("grimlock_tunneler")]
        if len(self.state.party_members()) >= 4:
            enemies.append(self.act2_pick_enemy(("cult_lookout", "starblighted_miner", "grimlock_tunneler")))
        hero_bonus = self.apply_scene_companion_support("south_adit")
        if self.state.flags.get("south_adit_patrol_rhythm_read"):
            hero_bonus += 1
        choice = self.scenario_choice(
            "How do you secure the drainage exit?",
            [
                self.skill_tag("SURVIVAL", self.action_option("Move with the water noise and reach the hunters' blind angle.")),
                self.skill_tag("STEALTH", self.action_option("Let the drainage chain rattle without you under it.")),
                self.skill_tag("ATHLETICS", self.action_option("Force the grate open and turn the side cut into an exit lane.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Move with the water noise and reach the hunters' blind angle.")
            if self.skill_check(self.state.player, "Survival", 14, context="to secure the South Adit drainage route"):
                hero_bonus += 2
                self.apply_status(enemies[0], "surprised", 1, source="you moved inside the drainage noise")
        elif choice == 2:
            self.player_action("Let the drainage chain rattle without you under it.")
            if self.skill_check(self.state.player, "Stealth", 14, context="to misdirect the drainage ambush"):
                enemies[0].current_hp = max(1, enemies[0].current_hp - 4)
                hero_bonus += 1
        else:
            self.player_action("Force the grate open and turn the side cut into an exit lane.")
            if self.skill_check(self.state.player, "Athletics", 14, context="to wrench the drainage grate open"):
                hero_bonus += 2
                self.apply_status(self.state.player, "emboldened", 2, source="forcing the drainage exit")
        outcome = self.run_encounter(
            Encounter(
                title="South Adit Drainage Exit",
                description="A side-cut ambush tries to keep the delayed prison rescue from gaining a second exit.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The drainage route swallows the rescue and the prison line stays closed.")
            return
        if outcome == "fled":
            self.return_to_act2_hub("You pull back from the drainage exit before it turns the whole rescue into a drowned rush.")
            return
        self.complete_act2_map_room(dungeon, room.room_id)

    def _south_adit_infirmary_cut(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("The infirmary cut is not mercy. It is sorting: the weak on blankets, the useful on chains, and the dead already written off.")
        choice = self.scenario_choice(
            "What do you save from the infirmary cut?",
            [
                self.skill_tag("MEDICINE", self.action_option("Stabilize the captives who will not survive a running rescue.")),
                self.skill_tag("INSIGHT", self.action_option("Find the prisoner the wardens kept alive because they knew something.")),
                self.skill_tag("RELIGION", self.action_option("Break the Choir's hush-prayers before they follow the wounded out.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Stabilize the captives who will not survive a running rescue.")
            if self.skill_check(self.state.player, "Medicine", 14, context="to stabilize the weakest South Adit captives"):
                self.state.flags["south_adit_weakest_saved"] = True
                self.apply_status(self.state.player, "blessed", 1, source="saving the vulnerable first")
                self.reward_party(xp=10, reason="stabilizing the weakest South Adit captives")
        elif choice == 2:
            self.player_action("Find the prisoner the wardens kept alive because they knew something.")
            if self.skill_check(self.state.player, "Insight", 14, context="to spot the informed captive"):
                self.state.flags["south_adit_witness_found"] = True
                self.add_clue("A South Adit captive names the Quiet Choir's prisoner-sorting cadence and points toward the deeper nave.")
                self.say("One captive is less broken than hidden. They give you the rhythm the wardens use to move witnesses below.")
        else:
            self.player_action("Break the Choir's hush-prayers before they follow the wounded out.")
            if self.skill_check(self.state.player, "Religion", 14, context="to break the Choir's hush-prayers"):
                self.state.flags["south_adit_hush_prayers_broken"] = True
                self.act2_shift_metric(
                    "act2_whisper_pressure",
                    -1,
                    "the infirmary prayers stop carrying the Choir's cadence into the captives' breathing",
                )
        self.complete_act2_map_room(dungeon, room.room_id)

    def _south_adit_irielle_route_choice(self) -> None:
        assert self.state is not None
        if self.state.flags.get("south_adit_irielle_plan") in {"break", "clean_exit"}:
            return
        elira = self.find_companion("Elira Dawnmantle")
        elira_active = elira is not None and elira in self.state.companions
        self.speaker(
            "Irielle Ashwake",
            "Before we move, answer one thing for me. Do you want a way to break the Choir, or a way to leave cleaner than you came in?",
        )
        if elira_active:
            self.speaker(
                "Elira Lanternward",
                "Break the line if you have to. Just do not make the prisoners pay the price twice.",
            )
        choice = self.scenario_choice(
            "What do you ask Irielle for before the prison line breaks?",
            [
                self.quoted_option("BREAK", "Give us the note that breaks the Choir's step."),
                self.quoted_option("CLEAN", "Give us the way out that leaves fewer ghosts behind."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_speaker("Give us the note that breaks the Choir's step.")
            self.state.flags["south_adit_irielle_plan"] = "break"
            self.say(
                'Irielle traces a single wrong beat into the air. "When the wardens answer together, hit that note and the whole line will stumble."'
            )
            if elira_active:
                self.speaker(
                    "Elira Lanternward",
                    "Then keep the break on the wardens, not the people behind them.",
                )
        else:
            self.player_speaker("Give us the way out that leaves fewer ghosts behind.")
            self.state.flags["south_adit_irielle_plan"] = "clean_exit"
            self.say(
                'Irielle marks the quiet count the captives can follow without copying the Choir. "Keep them moving on this rhythm and the prison does not get to leave inside them."'
            )
            if elira_active:
                self.speaker(
                    "Elira Lanternward",
                    "Good. A clean escape is still a kind of justice down here.",
                )

    def _south_adit_recruit_irielle(self, *, delayed: bool) -> None:
        assert self.state is not None
        if self.has_companion("Irielle Ashwake"):
            return
        self.speaker(
            "Irielle Ashwake",
            "If you were trying to prove there was still a side worth escaping to, this was a convincing way to do it.",
        )
        recruit = self.scenario_choice(
            "A shaken tiefling augur stands among the freed captives, eyes fixed on the deeper dark.",
            [
                self.quoted_option("RECRUIT", "Then come with us and help end the Choir properly."),
                self.quoted_option("SAFE", "Get topside and take one clean breath first. We will speak in camp."),
            ],
            allow_meta=False,
        )
        self.recruit_companion(create_irielle_ashwake())
        self.state.flags["counter_cadence_known"] = True
        irielle = self.find_companion("Irielle Ashwake")
        if irielle is not None and delayed:
            self.adjust_companion_disposition(
                irielle,
                -1,
                "too many captives were left below long enough to vanish before you reached the adit",
            )
        elif irielle is not None:
            self.adjust_companion_disposition(
                irielle,
                1,
                "you chose the prison line before the cleaner route race",
            )
        if recruit == 2 and irielle is not None and irielle in self.state.companions:
            self.move_companion_to_camp(irielle)
            self.say("Irielle agrees to reach camp first and share what she knows once she can think without whispering walls around her.")

    def _south_adit_augur_cell(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        delayed = self._south_adit_delayed()
        self.say(
            "The augur cell has no proper lock left, only copper wire, blood-dulled chalk, and a tiefling prisoner tracing counter-rhythms into the stone."
        )
        choice = self.scenario_choice(
            "How do you reach the augur without letting the Choir hear the contact?",
            [
                self.skill_tag("ARCANA", self.action_option("Complete her counter-cadence before the wall answers wrong.")),
                self.skill_tag("PERSUASION", self.action_option("Tell her exactly who sent you and why this rescue is real.")),
                self.skill_tag("RELIGION", self.action_option("Name the Choir's prayer as a prison trick, not a revelation.")),
            ],
            allow_meta=False,
        )
        skill = "Arcana" if choice == 1 else "Persuasion" if choice == 2 else "Religion"
        if self.skill_check(self.state.player, skill, 14, context="to make clean contact with Irielle Ashwake"):
            self.state.flags["south_adit_counter_cadence_learned"] = True
            self.state.flags["counter_cadence_known"] = True
            self.reward_party(xp=15, reason="making contact with Irielle in the South Adit")
            self.say("The counter-cadence catches. For the first time in the adit, the wall sounds like stone instead of a mouth.")
        else:
            self.say("Irielle still understands enough to move, but the cadence keeps some of its teeth.")
        self._south_adit_irielle_route_choice()
        self._south_adit_recruit_irielle(delayed=delayed)
        self.complete_act2_map_room(dungeon, room.room_id)

    def _south_adit_warden_nave(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        delayed = self._south_adit_delayed()
        enemies = [create_enemy("survey_chain_revenant"), create_enemy("choir_adept")]
        if delayed:
            enemies.append(self.act2_pick_enemy(("memory_taker_adept", "oathbroken_revenant")))
        elif len(self.state.party_members()) >= 4:
            enemies.append(self.act2_pick_enemy(("memory_taker_adept", "choir_executioner")))
        if len(self.state.party_members()) >= 4:
            enemies.append(self.act2_pick_enemy(("cult_lookout", "memory_taker_adept", "survey_chain_revenant")))

        hero_bonus = self.apply_scene_companion_support("south_adit")
        cadence = self._south_adit_prison_cadence(delayed=delayed)
        irielle_plan = self.state.flags.get("south_adit_irielle_plan")
        if self.state.flags.get("elira_field_lantern"):
            hero_bonus += 1
            self.say("Elira's field lantern turns the adit's worst silence from sacred to merely ugly.")
        if self.state.flags.get("south_adit_cells_quietly_opened"):
            hero_bonus += 1
            self.apply_status(enemies[1], "surprised", 1, source="the cells opening behind them")
        if self.state.flags.get("south_adit_prisoners_steadied"):
            hero_bonus += 1
        if self.state.flags.get("south_adit_drainage_secured"):
            hero_bonus += 1
        if self.state.flags.get("south_adit_weakest_saved"):
            hero_bonus += 1
        if self.state.flags.get("south_adit_counter_cadence_learned"):
            hero_bonus += 1
        if self.state.flags.get("south_adit_warden_nerve_cracked"):
            hero_bonus += 1
        if irielle_plan == "break":
            hero_bonus += 1
            self.say("Irielle mouths the fracture note she promised, and the wardens answer half a step too late.")
        elif irielle_plan == "clean_exit":
            hero_bonus += 1
            self.say("Irielle counts off the quiet lane for the captives, mapping where panic will try to copy the Choir and fail.")
        self.state.flags["south_adit_prison_cadence_start"] = cadence
        self.say(
            f"Prison Cadence: {self._south_adit_prison_cadence_label(cadence)} ({cadence}/5). "
            f"{self._south_adit_prison_cadence_summary(cadence)}"
        )

        choice = self.scenario_choice(
            "How do you crack the prison line?",
            [
                self.skill_tag("SLEIGHT OF HAND", self.action_option("Open the last cells quietly and arm the captives before the wardens know.")),
                self.skill_tag("INTIMIDATION", self.action_option("Hit the wardens hard enough that the prisoners remember your side instead.")),
                self.skill_tag("MEDICINE", self.action_option("Go for the weakest captives first and keep the line from becoming a slaughter.")),
            ],
            allow_meta=False,
        )
        success = False
        if choice == 1:
            self.player_action("Open the last cells quietly and arm the captives before the wardens know.")
            success = self.skill_check(self.state.player, "Sleight of Hand", 14, context="to free the first prisoners without raising the line")
            if success:
                hero_bonus += 2
                self.apply_status(enemies[1], "surprised", 1, source="the cells opening behind them")
        elif choice == 2:
            self.player_action("Hit the wardens hard enough that the prisoners remember your side instead.")
            success = self.skill_check(self.state.player, "Intimidation", 14, context="to crack the adit's prison discipline")
            if success:
                hero_bonus += 1
        else:
            self.player_action("Go for the weakest captives first and keep the line from becoming a slaughter.")
            success = self.skill_check(self.state.player, "Medicine", 14, context="to keep the rescue from turning into a panic crush")
            if success:
                hero_bonus += 1
                self.apply_status(self.state.player, "blessed", 1, source="saving the vulnerable first")
        cadence = max(0, min(5, cadence - 1 if success else cadence + 1))
        self.state.flags["south_adit_prison_cadence_final"] = cadence
        self.say(
            f"Prison Cadence: {self._south_adit_prison_cadence_label(cadence)} ({cadence}/5). "
            f"{self._south_adit_prison_cadence_summary(cadence)}"
        )
        if cadence >= 4:
            for enemy in enemies:
                self.apply_status(enemy, "emboldened", 2, source="the prison line catches the Choir's cadence")
            self.say("The wardens fall back into the prison cadence together, and the whole line hits harder for it.")
        elif cadence <= 1:
            hero_bonus += 1
            if len(enemies) > 1:
                self.apply_status(enemies[1], "reeling", 1, source="Irielle's counter-cadence breaks the prison line")
            self.say("The cadence breaks under your push, and the wardens have to improvise in a place built to punish it.")

        outcome = self.run_encounter(
            Encounter(
                title="South Adit Wardens",
                description="The prison line beneath Resonant Vaults tries to bury witnesses before the truth can get out.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The South Adit stays a prison and the captives disappear back into the dark.")
            return
        if outcome == "fled":
            self.return_to_act2_hub("You fall back from the adit before the rescue turns fatal.")
            return

        self.complete_act2_map_room(dungeon, room.room_id)
        if irielle_plan == "clean_exit":
            self.act2_shift_metric(
                "act2_whisper_pressure",
                -1,
                "Irielle's clean-exit count keeps the prison cadence from following the survivors out of the adit",
            )
        if cadence >= 4:
            self.state.flags["act2_captive_outcome"] = "few_saved"
            self.say("The prison cadence snaps shut too often to clear every cell before the wardens regain the line.")
        elif delayed:
            self.state.flags["act2_captive_outcome"] = "few_saved"
            if irielle_plan == "clean_exit":
                self.say(
                    "You still free people, but the delay leaves too many cells empty. Irielle's quiet count at least keeps the survivors from carrying the prison line back out with them."
                )
            else:
                self.say("You still free people, but too many cells are already empty for the party to pretend this delay was clean.")
        else:
            self.state.flags["act2_captive_outcome"] = "many_saved"
            self.act2_shift_metric(
                "act2_town_stability",
                1,
                "the rescue reaches town as proof that this expedition still remembers the people trapped under it",
            )
        self._south_adit_recruit_irielle(delayed=delayed)
        self.reward_party(xp=60, gold=18, reason="freeing the South Adit prisoners")
        self._south_adit_award_route_rewards()
        self.return_to_act2_hub("The South Adit prison line breaks open behind you, and its survivors carry the first hard proof of the Choir back toward Iron Hollow.")

    def _wave_echo_rail_junction(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        if not self.state.flags.get("wave_echo_outer_seen"):
            self.say(
                "The outer galleries keep the mine's old grandeur and none of its safety. Echoing rails, broken cranes, and ancient runoffs "
                "turn every line of advance into a place where one mistake could still matter more than courage.",
                typed=True,
            )
            self.state.flags["wave_echo_outer_seen"] = True
        choice = self.scenario_choice(
            "How do you read the rail junction?",
            [
                self.skill_tag("INVESTIGATION", self.action_option("Follow the survey marks and keep the old mine from lying about its own shape.")),
                self.skill_tag("SURVIVAL", self.action_option("Find the side-runs the grimlocks trust before they find you.")),
                self.skill_tag("ATHLETICS", self.action_option("Test the haul rail and find where force can still reopen the route.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Follow the survey marks and keep the old mine from lying about its own shape.")
            if self.skill_check(self.state.player, "Investigation", 14, context="to read the Resonant Vaults' outer rail junction"):
                self.state.flags["outer_survey_marks_read"] = True
                self.say("The false marks fall away, and one usable route stays in your hand at this first junction.")
        elif choice == 2:
            self.player_action("Find the side-runs the grimlocks trust before they find you.")
            if self.skill_check(self.state.player, "Survival", 14, context="to read the grimlock side-runs"):
                self.state.flags["outer_side_run_read"] = True
                self.say("The side-runs have a rhythm: not safe, exactly, but honest about where the ambush wants to stand.")
        else:
            self.player_action("Test the haul rail and find where force can still reopen the route.")
            if self.skill_check(self.state.player, "Athletics", 14, context="to test the collapsed haul rail"):
                self.state.flags["outer_haul_rail_plan"] = True
                self.apply_status(self.state.player, "emboldened", 1, source="finding the rail's remaining strength")
        self.complete_act2_map_room(dungeon, room.room_id)

    def _wave_echo_slime_sluice(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("The slime sluice is a slick runoff channel where old alchemical waste has learned to move like an argument with gravity.")
        enemies = [create_enemy("ochre_slime")]
        if len(self.state.party_members()) >= 4 or self.act2_metric_value("act2_route_control") <= 2:
            enemies.append(self.act2_pick_enemy(("stirge_swarm", "hookclaw_burrower", "carrion_lash_crawler")))
        hero_bonus = self.apply_scene_companion_support("wave_echo_outer_galleries")
        if self.state.flags.get("outer_survey_marks_read"):
            hero_bonus += 1
        choice = self.scenario_choice(
            "How do you carry the company through the slime sluice?",
            [
                self.skill_tag("INVESTIGATION", self.action_option("Use the survey marks to find where the old runoff can be dropped safely.")),
                self.skill_tag("ATHLETICS", self.action_option("Force the crossing before the acid eats the last stable edge.")),
                self.skill_tag("SURVIVAL", self.action_option("Read the dry stone ribs and keep everyone out of the hungry center.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Use the survey marks to find where the old runoff can be dropped safely.")
            if self.skill_check(self.state.player, "Investigation", 14, context="to turn the sluice marks into an opening"):
                enemies[0].current_hp = max(1, enemies[0].current_hp - 5)
                self.apply_status(enemies[0], "reeling", 1, source="the old runoff gate dropping")
                hero_bonus += 2
        elif choice == 2:
            self.player_action("Force the crossing before the acid eats the last stable edge.")
            if self.skill_check(self.state.player, "Athletics", 14, context="to force the slime sluice crossing"):
                hero_bonus += 1
                self.apply_status(self.state.player, "emboldened", 2, source="forcing the slime sluice")
        else:
            self.player_action("Read the dry stone ribs and keep everyone out of the hungry center.")
            if self.skill_check(self.state.player, "Survival", 14, context="to read safe stone through the slime sluice"):
                hero_bonus += 2
        outcome = self.run_encounter(
            Encounter(
                title="Resonant Vaults Slime Sluice",
                description="Acidic runoff and cave predators try to turn the outer gallery into a dead end.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The outer galleries close around the party before the deeper route can be stabilized.")
            return
        if outcome == "fled":
            self.return_to_act2_hub("You retreat from the slime sluice to reset the approach.")
            return
        self.complete_act2_map_room(dungeon, room.room_id)

    def _wave_echo_grimlock_side_run(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("The grimlock side-run is less a passage than a hunting habit worn into stone.")
        enemies = [create_enemy("grimlock_tunneler")]
        if len(self.state.party_members()) >= 4 or self.act2_metric_value("act2_route_control") <= 2:
            enemies.append(self.act2_pick_enemy(("grimlock_tunneler", "hookclaw_burrower", "starblighted_miner")))
        hero_bonus = self.apply_scene_companion_support("wave_echo_outer_galleries")
        if self.state.flags.get("outer_side_run_read"):
            hero_bonus += 1
        choice = self.scenario_choice(
            "How do you beat the side-run ambush?",
            [
                self.skill_tag("SURVIVAL", self.action_option("Take the side-runs the grimlocks trust and beat them to the angle.")),
                self.skill_tag("STEALTH", self.action_option("Let the hunters hear a false company while you move around them.")),
                self.skill_tag("PERCEPTION", self.action_option("Count the echoes until one set of breathing separates from the rest.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Take the side-runs the grimlocks trust and beat them to the angle.")
            if self.skill_check(self.state.player, "Survival", 14, context="to move like something that actually belongs underground"):
                hero_bonus += 2
                self.apply_status(enemies[0], "surprised", 1, source="you reached their angle first")
        elif choice == 2:
            self.player_action("Let the hunters hear a false company while you move around them.")
            if self.skill_check(self.state.player, "Stealth", 14, context="to misdirect the grimlock side-run"):
                enemies[0].current_hp = max(1, enemies[0].current_hp - 4)
                hero_bonus += 1
        else:
            self.player_action("Count the echoes until one set of breathing separates from the rest.")
            if self.skill_check(self.state.player, "Perception", 14, context="to hear the hidden side-run ambush"):
                hero_bonus += 2
        outcome = self.run_encounter(
            Encounter(
                title="Resonant Vaults Grimlock Side-Run",
                description="Tunnel hunters try to make the outer galleries turn against the party's map sense.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The outer galleries close around the party before the deeper route can be stabilized.")
            return
        if outcome == "fled":
            self.return_to_act2_hub("You retreat from the grimlock side-run before the ambush can close the route behind you.")
            return
        self.complete_act2_map_room(dungeon, room.room_id)

    def _wave_echo_collapsed_crane(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("The collapsed crane blocks a direct haul line, all snapped chain, wedged beam, and one bad choice away from becoming an avalanche.")
        dc = 13 if self.state.flags.get("outer_haul_rail_plan") else 14
        choice = self.scenario_choice(
            "How do you reopen the crane route?",
            [
                self.skill_tag("ATHLETICS", self.action_option("Reopen the haul rail and force the cave to answer a direct advance.")),
                self.skill_tag("INVESTIGATION", self.action_option("Find the pin that lets the crane drop without taking the ceiling too.")),
                self.skill_tag("SURVIVAL", self.action_option("Use the old haul scars to choose where the collapse can safely fall.")),
            ],
            allow_meta=False,
        )
        skill = "Athletics" if choice == 1 else "Investigation" if choice == 2 else "Survival"
        if self.skill_check(self.state.player, skill, dc, context="to reopen the collapsed crane route"):
            self.state.flags["outer_crane_stabilized"] = True
            self.reward_party(xp=10, reason="reopening the Resonant Vaults' collapsed crane route")
            self.say("The crane drops with a sound like a verdict, and the direct haul line becomes ugly but usable.")
        else:
            self.say("The crane shifts badly. You get the route open, but every echo behind you sounds less forgiving.")
            self.act2_shift_metric(
                "act2_route_control",
                -1,
                "the crane route opens messily enough to make the outer gallery map less trustworthy",
            )
        self.complete_act2_map_room(dungeon, room.room_id)

    def _wave_echo_false_echo_loop(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("The false echo loop repeats footsteps that are not yours and distances that change when you trust them.")
        high_whisper = self.act2_metric_value("act2_whisper_pressure") >= 4
        hero_bonus = self.apply_scene_companion_support("wave_echo_outer_galleries")
        choice = self.scenario_choice(
            "How do you map the false echo loop?",
            [
                self.skill_tag("INVESTIGATION", self.action_option("Mark every repeated echo until only one path still matches your steps.")),
                self.skill_tag("ARCANA", self.action_option("Treat the false echoes as resonance and break their timing.")),
                self.skill_tag("SURVIVAL", self.action_option("Trust the air and stone instead of the sounds trying to guide you.")),
            ],
            allow_meta=False,
        )
        skill = "Investigation" if choice == 1 else "Arcana" if choice == 2 else "Survival"
        if self.skill_check(self.state.player, skill, 14, context="to map the false echo loop"):
            self.state.flags["outer_false_echo_named"] = True
            hero_bonus += 1
            self.say("The loop is still wrong, but it is now wrong in a shape you can use.")
        else:
            self.say("The loop gives you the path, but takes enough certainty that the next gate feels closer than it should.")
        if high_whisper:
            enemies = [self.act2_pick_enemy(("starblighted_miner", "whispermaw_blob", "hookclaw_burrower"))]
            if len(self.state.party_members()) >= 4:
                enemies.append(self.act2_pick_enemy(("starblighted_miner", "obelisk_eye", "grimlock_tunneler")))
            if self.state.flags.get("outer_false_echo_named"):
                self.apply_status(enemies[0], "reeling", 1, source="the loop's timing breaking")
            outcome = self.run_encounter(
                Encounter(
                    title="Resonant Vaults False Echo Loop",
                    description="The outer galleries answer high whisper pressure with starblighted shapes in the wrong echoes.",
                    enemies=enemies,
                    allow_flee=True,
                    allow_parley=False,
                    hero_initiative_bonus=hero_bonus,
                    allow_post_combat_random_encounter=False,
                )
            )
            if outcome == "defeat":
                self.handle_defeat("The false echo loop closes over the party before the deeper route can be named.")
                return
            if outcome == "fled":
                self.return_to_act2_hub("You retreat from the false echo loop before the mine can make a second set of footsteps permanent.")
                return
        self.complete_act2_map_room(dungeon, room.room_id)

    def _wave_echo_deep_haul_gate(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        enemies = [create_enemy("grimlock_tunneler"), create_enemy("ochre_slime")]
        if self.act2_metric_value("act2_whisper_pressure") >= 4:
            enemies.append(self.act2_pick_enemy(("starblighted_miner", "whispermaw_blob", "hookclaw_burrower")))
        elif self.act2_metric_value("act2_route_control") <= 2 or len(self.state.party_members()) >= 4:
            enemies.append(self.act2_pick_enemy(("stirge_swarm", "hookclaw_burrower", "carrion_lash_crawler")))
        if len(self.state.party_members()) >= 4:
            enemies.append(self.act2_pick_enemy(("grimlock_tunneler", "starblighted_miner", "hookclaw_burrower")))
        hero_bonus = self.apply_scene_companion_support("wave_echo_outer_galleries")
        if self.state.flags.get("outer_survey_marks_read"):
            hero_bonus += 1
        if self.state.flags.get("outer_grimlock_run_cleared"):
            hero_bonus += 1
        if self.state.flags.get("outer_crane_reopened"):
            hero_bonus += 1
        if self.state.flags.get("outer_false_echo_named"):
            hero_bonus += 1
        choice = self.scenario_choice(
            "How do you force the deep haul gate?",
            [
                self.skill_tag("INVESTIGATION", self.action_option("Follow the survey marks and keep the old mine from lying about its own shape.")),
                self.skill_tag("SURVIVAL", self.action_option("Take the side-runs the grimlocks trust and beat them to the angle.")),
                self.skill_tag("ATHLETICS", self.action_option("Reopen the haul rail and force the cave to answer a direct advance.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Follow the survey marks and keep the old mine from lying about its own shape.")
            if self.skill_check(self.state.player, "Investigation", 14, context="to keep the party on the usable line through false echoes"):
                hero_bonus += 2
        elif choice == 2:
            self.player_action("Take the side-runs the grimlocks trust and beat them to the angle.")
            if self.skill_check(self.state.player, "Survival", 14, context="to move like something that actually belongs underground"):
                hero_bonus += 2
                self.apply_status(enemies[0], "surprised", 1, source="you reached their angle first")
        else:
            self.player_action("Reopen the haul rail and force the cave to answer a direct advance.")
            if self.skill_check(self.state.player, "Athletics", 14, context="to turn the broken rail into a fighting line instead of a hazard"):
                hero_bonus += 1
                self.apply_status(self.state.player, "emboldened", 2, source="forcing the galleries to take your pace")
        outcome = self.run_encounter(
            Encounter(
                title="Outer Gallery Pressure",
                description="The Resonant Vaults' outer defenses are now a mix of scavengers, predators, and bad old engineering.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The outer galleries close around the party before the deeper route can be stabilized.")
            return
        if outcome == "fled":
            self.return_to_act2_hub("You retreat from the outer galleries to reset the approach.")
            return
        self.complete_act2_map_room(dungeon, room.room_id)
        self.reward_party(xp=50, gold=12, reason="forcing the outer galleries open")
        self.act2_shift_metric(
            "act2_route_control",
            1,
            "the company now owns a real line through the Resonant Vaults' outer galleries",
        )
        self.return_to_act2_hub("The Resonant Vaults' outer galleries settle behind you into a route the expedition can actually hold.")

    def _black_lake_causeway_lip(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        if not self.has_quest("sever_quiet_choir"):
            self.grant_quest("sever_quiet_choir")
        if not self.state.flags.get("black_lake_seen"):
            self.say(
                "The old black water cuts the cave in half beneath a narrow causeway of stone and broken dwarfwork. A drowned shrine leans off one side. "
                "A cult barracks squats on the other. This is the last clean threshold before the Meridian Forge, and the Quiet Choir knows it.",
                typed=True,
            )
            self.state.flags["black_lake_seen"] = True
        self._black_lake_apply_south_adit_payoff()
        self._black_lake_apply_conyberry_payoff()
        choice = self.scenario_choice(
            "What do you read first on the crossing?",
            [
                self.skill_tag("RELIGION", self.action_option("Mark the drowned shrine before the lake swallows its last clean prayer.")),
                self.skill_tag("STEALTH", self.action_option("Count the barracks watches and messenger lanes before you start crossing openly.")),
                self.skill_tag("ATHLETICS", self.action_option("Test the anchor pull and learn where the causeway can be made to lurch.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Mark the drowned shrine before the lake swallows its last clean prayer.")
            if self.skill_check(self.state.player, "Religion", 14, context="to hear what sanctity still survives over the black water"):
                self.state.flags["black_lake_shrine_route_marked"] = True
                self.add_clue("A thin thread of older sanctity still answers at Blackglass's drowned shrine, which means the crossing is not fully the Choir's yet.")
                self.reward_party(xp=10, reason="reading the drowned shrine before the crossing")
        elif choice == 2:
            self.player_action("Count the barracks watches and messenger lanes before you start crossing openly.")
            if self.skill_check(self.state.player, "Stealth", 14, context="to read the barracks watches without becoming part of the report"):
                self.state.flags["black_lake_barracks_watch_read"] = True
                self.reward_party(xp=10, reason="mapping the Blackglass barracks watches")
        else:
            self.player_action("Test the anchor pull and learn where the causeway can be made to lurch.")
            if self.skill_check(self.state.player, "Athletics", 14, context="to feel where the old line will break before it throws you with it"):
                self.state.flags["black_lake_anchor_stress_read"] = True
                self.reward_party(xp=10, reason="reading the causeway's anchor strain")
        self.complete_act2_map_room(dungeon, room.room_id)

    def _black_lake_apply_south_adit_payoff(self) -> None:
        assert self.state is not None
        if self.state.flags.get("black_lake_south_adit_payoff_applied"):
            return
        outcome = str(self.state.flags.get("act2_captive_outcome", "uncertain"))
        if outcome == "many_saved":
            self.state.flags["black_lake_south_adit_payoff_applied"] = True
            self.state.flags["black_lake_survivor_testimony"] = True
            self.state.flags["black_lake_barracks_watch_read"] = True
            self.say(
                "One of the South Adit survivors halts at the crossing and names the barracks blind-side watch they were forced to count from below."
            )
            self.add_clue(
                "A rescued South Adit witness identifies the Blackglass barracks blind-side watch and the messenger lane the Choir trusted most."
            )
            return
        if outcome != "few_saved":
            return
        self.state.flags["black_lake_south_adit_payoff_applied"] = True
        self.state.flags["black_lake_choir_reserve_intact"] = True
        self.say(
            "Too few captives escaped the adit soon enough to foul the Choir's reserve traffic. The Blackglass crossing feels more organized because of it."
        )
        self.act2_shift_metric(
            "act2_whisper_pressure",
            1,
            "the Choir's South Adit reserve line reaches Blackglass before the survivors can break its rhythm",
        )

    def _black_lake_apply_conyberry_payoff(self) -> None:
        assert self.state is not None
        if not self.state.flags.get("conyberry_chapel_relit"):
            return
        if not self.state.flags.get("black_lake_conyberry_lamp_guidance"):
            self.state.flags["black_lake_conyberry_lamp_guidance"] = True
            self.state.flags["black_lake_shrine_route_marked"] = True
            self.say(
                "The lamp discipline you restored at Hushfen catches at the Blackglass shrine before the water can make it sound like only drowning prayers belong here."
            )
            self.add_clue(
                "Hushfen's relit Chapel of Lamps gives the Blackglass shrine a clean line to answer before the Meridian Forge can drown it in Choir rhythm."
            )
        if self.state.flags.get("conyberry_chapel_pressure_payoff_applied"):
            return
        self.state.flags["conyberry_chapel_pressure_payoff_applied"] = True
        self.state.flags["black_lake_conyberry_pressure_payoff"] = True
        self.act2_shift_metric(
            "act2_whisper_pressure",
            -1,
            "Hushfen's relit chapel gives the Blackglass crossing one disciplined prayer the Choir cannot turn into panic",
        )

    def _black_lake_drowned_shrine(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say(
            "Stone saints lean half-submerged in black water while old lamp niches hold only cold mineral sheen. The shrine is not dead, but it is listening for who claims it next."
        )
        dc = 13 if self.state.flags.get("black_lake_shrine_route_marked") or self.state.flags.get("agatha_truth_clear") else 14
        choice = self.scenario_choice(
            "How do you reclaim the drowned shrine?",
            [
                self.skill_tag("RELIGION", self.action_option("Wake the old rite cleanly and force the crossing to remember its first purpose.")),
                self.skill_tag("INSIGHT", self.action_option("Read which prayer the lake is still willing to answer without taking a life for it.")),
                self.skill_tag("ARCANA", self.action_option("Thread the shrine's old resonance through the Forge's newer wrong song.")),
            ],
            allow_meta=False,
        )
        shrine_bonus = False
        if choice == 1:
            self.player_action("Wake the old rite cleanly and force the crossing to remember its first purpose.")
            shrine_bonus = self.skill_check(self.state.player, "Religion", dc, context="to reclaim the drowned shrine before the Choir notices")
        elif choice == 2:
            self.player_action("Read which prayer the lake is still willing to answer without taking a life for it.")
            shrine_bonus = self.skill_check(self.state.player, "Insight", dc, context="to find the one safe rite left in the shrine")
        else:
            self.player_action("Thread the shrine's old resonance through the Forge's newer wrong song.")
            shrine_bonus = self.skill_check(self.state.player, "Arcana", dc, context="to braid the shrine's older resonance against the forge-hum")
        self.complete_act2_map_room(dungeon, room.room_id)
        self.act2_shift_metric(
            "act2_whisper_pressure",
            -1,
            "the drowned shrine answers before the forge can drown it entirely in the Choir's rhythm",
        )
        if shrine_bonus:
            self.state.flags["black_lake_shrine_sanctity_named"] = True
            self.apply_status(self.state.player, "blessed", 2, source="the reclaimed Blackglass shrine")
            self.add_clue("The drowned shrine still answers an older sanctity, which means the Forge route has not been fully rewritten by the Quiet Choir.")
            self.reward_party(xp=15, reason="reclaiming the drowned shrine cleanly")
        else:
            self.say("The shrine answers, but only after taking a little more of the lake's cold into your bones than you wanted.")

    def _black_lake_choir_barracks(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        enemies = [create_enemy("cult_lookout"), create_enemy("choir_adept")]
        if self.state.flags.get("black_lake_choir_reserve_intact"):
            enemies.append(self.act2_pick_enemy(("cult_lookout", "starblighted_miner")))
        if self.act2_metric_value("act2_whisper_pressure") >= 4:
            enemies.append(self.act2_pick_enemy(("starblighted_miner", "obelisk_eye", "blacklake_pincerling")))
        elif len(self.state.party_members()) >= 4 or self.act2_metric_value("act2_route_control") <= 2:
            enemies.append(self.act2_pick_enemy(("starblighted_miner", "blacklake_pincerling", "cult_lookout")))
        hero_bonus = self.apply_scene_companion_support("black_lake_causeway")
        if self.state.flags.get("black_lake_survivor_testimony"):
            self.say("A rescued South Adit witness mouths the blind-side count as the barracks settles into it.")
        if self.state.flags.get("black_lake_barracks_watch_read"):
            hero_bonus += 1
            self.apply_status(enemies[0], "surprised", 1, source="you entered on the barracks blind side")
        if self.state.flags.get("black_lake_choir_reserve_intact"):
            self.say("The reserve line the captives could not break has already folded another body into the barracks.")
        options: list[tuple[str, str]] = [
            (
                "stealth",
                self.skill_tag("STEALTH", self.action_option("Cut the messengers first and keep the barracks from warning the far side.")),
            ),
            (
                "investigation",
                self.skill_tag("INVESTIGATION", self.action_option("Take the rota boards and reserve orders before the fighting scatters them.")),
            ),
            (
                "athletics",
                self.skill_tag("ATHLETICS", self.action_option("Turn the weapon racks and bunks into a collapsing choke point.")),
            ),
        ]
        if self.state.flags.get("stonehill_quiet_room_intel_decoded"):
            options.append(
                (
                    "quiet_room",
                    self.skill_tag(
                        "QUIET ROOM INTEL",
                        self.action_option("Use Nera's courier-reading and grab the live reserve orders before the room knows which satchel matters."),
                    ),
                )
            )
        choice = self.scenario_choice(
            "How do you strip the barracks?",
            [text for _, text in options],
            allow_meta=False,
        )
        selection_key, _ = options[choice - 1]
        if selection_key == "stealth":
            self.player_action("Cut the messengers first and keep the barracks from warning the far side.")
            if self.skill_check(self.state.player, "Stealth", 14, context="to kill the Blackglass message chain before it runs"):
                hero_bonus += 2
                self.apply_status(enemies[1], "surprised", 1, source="their messengers dropped first")
        elif selection_key == "investigation":
            self.player_action("Take the rota boards and reserve orders before the fighting scatters them.")
            if self.skill_check(self.state.player, "Investigation", 14, context="to seize the barracks orders intact"):
                hero_bonus += 1
                self.state.flags["black_lake_barracks_orders_taken"] = True
                self.add_clue("Blackglass barracks orders confirm the Quiet Choir keeps its last reserve line on the Meridian Forge side of the crossing.")
        elif selection_key == "athletics":
            self.player_action("Turn the weapon racks and bunks into a collapsing choke point.")
            if self.skill_check(self.state.player, "Athletics", 14, context="to make the barracks collapse inward on its own defenders"):
                hero_bonus += 1
                self.apply_status(enemies[0], "prone", 1, source="the barracks caving around them")
        else:
            self.player_action("Use Nera's courier-reading and grab the live reserve orders before the room knows which satchel matters.")
            hero_bonus += 1
            self.state.flags["black_lake_barracks_orders_taken"] = True
            self.apply_status(enemies[1], "surprised", 1, source="you took the live courier satchel first")
            self.add_clue("The quiet-room courier habits still hold underground: Blackglass reserve orders rode in the least impressive satchel in the room.")
        outcome = self.run_encounter(
            Encounter(
                title="Blackglass Barracks",
                description="The Quiet Choir's last organized staging room before the Forge has to be broken or stripped.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The barracks holds, and the far side of Blackglass stays reinforced.")
            return
        if outcome == "fled":
            self.return_to_act2_hub("You fall back from the Blackglass barracks before the whole crossing turns against you.")
            return
        self.complete_act2_map_room(dungeon, room.room_id)

    def _black_lake_anchor_chains(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say(
            "Old anchor chains descend into the black water beside split dwarfwork posts. The whole crossing can still be made to shudder if you know where to strike."
        )
        dc = 13 if self.state.flags.get("black_lake_anchor_stress_read") else 14
        choice = self.scenario_choice(
            "How do you sabotage the causeway anchors?",
            [
                self.skill_tag("ATHLETICS", self.action_option("Rip the right chain free and make the far landing fight on a trembling line.")),
                self.skill_tag("INVESTIGATION", self.action_option("Read the rivets and pick the exact weak point instead of guessing.")),
                self.skill_tag("SURVIVAL", self.action_option("Mark the safe footing first so your own people can move when the stone lurches.")),
            ],
            allow_meta=False,
        )
        clean_sabotage = False
        if choice == 1:
            self.player_action("Rip the right chain free and make the far landing fight on a trembling line.")
            clean_sabotage = self.skill_check(self.state.player, "Athletics", dc, context="to tear the anchor free without losing the crossing")
        elif choice == 2:
            self.player_action("Read the rivets and pick the exact weak point instead of guessing.")
            clean_sabotage = self.skill_check(self.state.player, "Investigation", dc, context="to pick the causeway's clean failure point")
            if clean_sabotage:
                self.state.flags["black_lake_anchor_weak_point_found"] = True
        else:
            self.player_action("Mark the safe footing first so your own people can move when the stone lurches.")
            clean_sabotage = self.skill_check(self.state.player, "Survival", dc, context="to mark a usable line across a shaking causeway")
            if clean_sabotage:
                self.state.flags["black_lake_causeway_footing_marked"] = True
        self.complete_act2_map_room(dungeon, room.room_id)
        if clean_sabotage:
            self.apply_status(self.state.player, "emboldened", 1, source="learning exactly how the causeway will jump")
            self.reward_party(xp=15, reason="sabotaging the Blackglass anchors cleanly")
        else:
            self.act2_shift_metric(
                "act2_route_control",
                -1,
                "the anchor sabotage had to be done messy and loud while the crossing fought back",
            )

    def _black_lake_blackwater_edge(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        enemies = [create_enemy("blacklake_pincerling"), create_enemy("animated_armor")]
        if self.act2_metric_value("act2_whisper_pressure") >= 4:
            enemies.append(self.act2_pick_enemy(("duskmire_matriarch", "obelisk_eye", "starblighted_miner")))
        elif len(self.state.party_members()) >= 4:
            enemies.append(self.act2_pick_enemy(("starblighted_miner", "blacklake_pincerling", "cult_lookout")))
        hero_bonus = self.apply_scene_companion_support("black_lake_causeway")
        if self.state.flags.get("black_lake_shrine_purified"):
            hero_bonus += 1
            self.apply_status(self.state.player, "blessed", 1, source="the Blackglass shrine")
        if self.state.flags.get("black_lake_barracks_raided"):
            hero_bonus += 1
        if self.state.flags.get("black_lake_causeway_shaken"):
            hero_bonus += 1
            self.apply_status(enemies[0], "prone", 1, source="the waterline lurching under the broken anchors")
        choice = self.scenario_choice(
            "How do you keep the black water from swallowing the route?",
            [
                self.skill_tag("SURVIVAL", self.action_option("Keep the party on the one line of stone that still behaves like ground.")),
                self.skill_tag("INVESTIGATION", self.action_option("Read the runoff and force the predators toward the shallows.")),
                self.skill_tag("ATHLETICS", self.action_option("Drag the line forward before the undertow can close around it.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Keep the party on the one line of stone that still behaves like ground.")
            if self.skill_check(self.state.player, "Survival", 14, context="to guide the party across the safe blackwater footing"):
                hero_bonus += 2
                self.state.flags["black_lake_waterline_read"] = True
        elif choice == 2:
            self.player_action("Read the runoff and force the predators toward the shallows.")
            if self.skill_check(self.state.player, "Investigation", 14, context="to turn the black water's flow against what lives in it"):
                hero_bonus += 1
                enemies[0].current_hp = max(1, enemies[0].current_hp - 4)
        else:
            self.player_action("Drag the line forward before the undertow can close around it.")
            if self.skill_check(self.state.player, "Athletics", 14, context="to beat the waterline's undertow by force"):
                hero_bonus += 1
                self.apply_status(self.state.player, "emboldened", 2, source="forcing the Blackglass edge")
        outcome = self.run_encounter(
            Encounter(
                title="Blackglass Waterline",
                description="Blackwater predators and old guardians make the last open stretch feel narrower than it is.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The black water swallows the approach before the far landing can be taken.")
            return
        if outcome == "fled":
            self.return_to_act2_hub("You fall back from the waterline before the lake can trap the whole company.")
            return
        self.complete_act2_map_room(dungeon, room.room_id)

    def _black_lake_far_landing(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        high_pressure = self.act2_metric_value("act2_whisper_pressure") >= 4
        bad_route = self.act2_metric_value("act2_route_control") <= 2
        strong_gear = self.act2_party_has_strong_route_gear()
        full_party = len(self.state.party_members()) >= 4
        enemies = [create_enemy("animated_armor"), create_enemy("starblighted_miner")]
        if full_party or high_pressure:
            enemies.append(self.act2_pick_enemy(("spectral_foreman", "blacklake_pincerling", "duskmire_matriarch", "obelisk_eye")))
        if full_party and (bad_route or high_pressure or strong_gear):
            enemies.append(self.act2_pick_enemy(("cult_lookout", "starblighted_miner", "blacklake_pincerling")))
        elif not self.state.flags.get("black_lake_barracks_raided"):
            enemies.append(self.act2_pick_enemy(("cult_lookout", "choir_adept", "starblighted_miner")))
        hero_bonus = self.apply_scene_companion_support("black_lake_causeway")
        if self.state.flags.get("black_lake_shrine_purified"):
            hero_bonus += 1
            self.apply_status(self.state.player, "blessed", 2, source="the reclaimed Blackglass shrine")
        if self.state.flags.get("black_lake_barracks_raided"):
            hero_bonus += 1
        if self.state.flags.get("black_lake_causeway_shaken"):
            hero_bonus += 1
            self.apply_status(enemies[0], "prone", 1, source="the causeway lurching under your sabotage")
        if self.state.flags.get("black_lake_barracks_orders_taken"):
            hero_bonus += 1
            enemies[1].current_hp = max(1, enemies[1].current_hp - 4)
        if self.state.flags.get("black_lake_causeway_footing_marked") or self.state.flags.get("black_lake_waterline_read"):
            hero_bonus += 1
        choice = self.scenario_choice(
            "How do you force the far landing?",
            [
                self.skill_tag("RELIGION", self.action_option("Carry the shrine's answered light into the last clean stretch before the Forge.")),
                self.skill_tag("STEALTH", self.action_option("Cut the last runners and reserves out from under the far side before it can brace.")),
                self.skill_tag("ATHLETICS", self.action_option("Fight while the whole causeway trembles and make the landing answer your pace.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Carry the shrine's answered light into the last clean stretch before the Forge.")
            if self.skill_check(self.state.player, "Religion", 14, context="to make the reclaimed shrine matter on the far landing"):
                hero_bonus += 1
                self.apply_status(enemies[1], "frightened", 1, source="older sanctity cutting through the lake-hum")
        elif choice == 2:
            self.player_action("Cut the last runners and reserves out from under the far side before it can brace.")
            if self.skill_check(self.state.player, "Stealth", 14, context="to gut the far landing's messenger chain before it settles"):
                hero_bonus += 2
                self.apply_status(enemies[0], "surprised", 1, source="the far side losing its runners")
        else:
            self.player_action("Fight while the whole causeway trembles and make the landing answer your pace.")
            if self.skill_check(self.state.player, "Athletics", 14, context="to turn the shaking causeway into your edge"):
                hero_bonus += 2
                self.apply_status(self.state.player, "emboldened", 2, source="forcing the far landing")
        outcome = self.run_encounter(
            Encounter(
                title="Blackglass Causeway",
                description="Constructs, corrupted miners, and old command echoes try to stop the final approach.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The causeway becomes a kill lane and the Forge remains out of reach.")
            return
        if outcome == "fled":
            self.return_to_act2_hub("You withdraw from the causeway before the line fully collapses around you.")
            return
        self.complete_act2_map_room(dungeon, room.room_id)
        self.reward_party(xp=55, gold=15, reason="crossing the Blackglass causeway")
        self.act2_award_milestone_gear(
            "act2_black_lake_milestone_gear",
            self.act2_black_lake_milestone_item(),
            source="the Blackglass reliquary",
        )
        self.add_journal("You crossed the Blackglass causeway and opened the last clean approach to the Meridian Forge.")
        self.return_to_act2_hub("The Blackglass causeway is finally yours, and the Meridian Forge lies open on the far side.")

    def _blackglass_relay_gate(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        if not self.has_quest("sever_quiet_choir"):
            self.grant_quest("sever_quiet_choir")
        if not self.state.flags.get("blackglass_relay_house_seen"):
            self.say(
                "The relay house perches above the far landing with black water dripping from its cable teeth. A brass bell ticks behind the wall, "
                "too slow for a warning and too steady for a broken clock.",
                typed=True,
            )
            if self.state.flags.get("black_lake_barracks_orders_taken"):
                self.say("The barracks orders put one red pencil mark beside this place: RESERVE ANSWERS THROUGH THE LITTLE BELL.")
            if self.state.flags.get("black_lake_shrine_purified"):
                self.say("The reclaimed shrine leaves a clean ache in the air, and the relay's bell hates the sound of it.")
            self.state.flags["blackglass_relay_route_known"] = True
        choice = self.scenario_choice(
            "How do you read the relay gate?",
            [
                self.skill_tag("INVESTIGATION", self.action_option("Match the cable teeth to the Forge traffic marks before the gate notices you.")),
                self.skill_tag("ARCANA", self.action_option("Listen for the support pulse riding under the little bell.")),
                self.skill_tag("ATHLETICS", self.action_option("Brace the wet winch so the first pull cannot throw the party into Blackglass.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Match the cable teeth to the Forge traffic marks before the gate notices you.")
            if self.skill_check(self.state.player, "Investigation", 14, context="to read the relay gate's cable traffic"):
                self.state.flags["blackglass_relay_gate_route_marked"] = True
                self.state.flags["forge_reserve_timing_known"] = True
                self.add_clue("The relay gate teeth match the Forge reserve traffic marks. Caldra's support pulse still comes through the little bell.")
                self.reward_party(xp=10, reason="reading the Blackglass relay gate")
        elif choice == 2:
            self.player_action("Listen for the support pulse riding under the little bell.")
            if self.skill_check(self.state.player, "Arcana", 14, context="to catch the relay pulse under the bell tick"):
                self.state.flags["blackglass_relay_pulse_read"] = True
                self.apply_status(self.state.player, "focused", 1, source="the relay pulse counted before it can hide")
                self.reward_party(xp=10, reason="counting the relay pulse")
        else:
            self.player_action("Brace the wet winch so the first pull cannot throw the party into Blackglass.")
            if self.skill_check(self.state.player, "Athletics", 14, context="to brace the relay gate winch"):
                self.state.flags["blackglass_relay_winch_braced"] = True
                self.apply_status(self.state.player, "emboldened", 1, source="the wet winch holding under your hands")
                self.reward_party(xp=10, reason="bracing the relay gate winch")
        self.complete_act2_map_room(dungeon, room.room_id)

    def _blackglass_relay_cable_sump(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        enemies = [create_enemy("blacklake_pincerling"), create_enemy("cult_lookout")]
        if self.act2_metric_value("act2_whisper_pressure") >= 4:
            enemies.append(self.act2_pick_enemy(("blackglass_listener", "obelisk_eye", "starblighted_miner")))
        elif len(self.state.party_members()) >= 4:
            enemies.append(self.act2_pick_enemy(("choir_adept", "blacklake_pincerling", "cult_lookout")))
        hero_bonus = self.apply_scene_companion_support("blackglass_relay_house")
        if self.state.flags.get("blackglass_relay_gate_route_marked"):
            hero_bonus += 1
            self.apply_status(enemies[1], "surprised", 1, source="the gate marks giving away the guard handoff")
        if self.state.flags.get("blackglass_relay_winch_braced"):
            hero_bonus += 1
            self.apply_status(enemies[0], "prone", 1, source="the braced winch jerking the cable under it")
        choice = self.scenario_choice(
            "How do you take the cable sump?",
            [
                self.skill_tag("SURVIVAL", self.action_option("Keep the party on the shallow lip while the cable tries to drag bodies under.")),
                self.skill_tag("STEALTH", self.action_option("Cut the guard chain before the sump can send a warning up the wall.")),
                self.skill_tag("ATHLETICS", self.action_option("Haul the cable sideways and make the sump fight its own machinery.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Keep the party on the shallow lip while the cable tries to drag bodies under.")
            if self.skill_check(self.state.player, "Survival", 14, context="to read the safe lip through the cable sump"):
                hero_bonus += 1
                self.state.flags["blackglass_relay_sump_line_marked"] = True
                self.apply_status(self.state.player, "focused", 1, source="the safe sump lip marked in mud")
        elif choice == 2:
            self.player_action("Cut the guard chain before the sump can send a warning up the wall.")
            if self.skill_check(self.state.player, "Stealth", 14, context="to cut the relay guard chain quietly"):
                hero_bonus += 2
                self.state.flags["blackglass_relay_guard_chain_cut"] = True
                self.apply_status(enemies[1], "surprised", 1, source="the warning chain falling slack")
        else:
            self.player_action("Haul the cable sideways and make the sump fight its own machinery.")
            if self.skill_check(self.state.player, "Athletics", 14, context="to wrench the relay cable out of rhythm"):
                hero_bonus += 1
                self.state.flags["blackglass_relay_cable_dragged"] = True
                enemies[0].current_hp = max(1, enemies[0].current_hp - 4)
        outcome = self.run_encounter(
            Encounter(
                title="Blackglass Relay Cable Sump",
                description="Blackglass predators and signal guards defend the wet cable that feeds the Forge support pulse.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The cable sump drags the party under and the relay keeps feeding the Forge.")
            return
        if outcome == "fled":
            self.return_to_act2_hub("You pull away from the relay sump before the cable can pin the whole company in black water.")
            return
        self.complete_act2_map_room(dungeon, room.room_id)
        self.add_journal("You cleared the Blackglass relay sump and left the Forge support cable coughing mud.")

    def _blackglass_relay_keeper_ledger(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say(
            "The keeper's office is a damp square of shelves, slate dust, and boot marks. A cracked timing board lists bell pulls by weight, with Caldra's name pressed hard enough to scar the wood."
        )
        dc = 13 if self.state.flags.get("black_lake_barracks_orders_taken") or self.state.flags.get("blackglass_relay_gate_route_marked") else 14
        choice = self.scenario_choice(
            "How do you strip the keeper's ledger?",
            [
                self.skill_tag("INVESTIGATION", self.action_option("Lay the timing slates beside the Blackglass orders and mark Caldra's reserve beat.")),
                self.skill_tag("INSIGHT", self.action_option("Read the keeper's panic notes and find which bell pull scared them most.")),
                self.skill_tag("ARCANA", self.action_option("Trace the slate dust where old bell timing has started behaving like spellwork.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Lay the timing slates beside the Blackglass orders and mark Caldra's reserve beat.")
            if self.skill_check(self.state.player, "Investigation", dc, context="to read the keeper ledger against the Blackglass orders"):
                self.state.flags["blackglass_relay_reserve_beat_marked"] = True
                self.add_clue("The relay ledger gives Caldra's reserve beat: three short bell pulls, one counterweight drop, then the Forge answers.")
                self.reward_party(xp=10, reason="marking the relay reserve beat")
        elif choice == 2:
            self.player_action("Read the keeper's panic notes and find which bell pull scared them most.")
            if self.skill_check(self.state.player, "Insight", dc, context="to find the feared bell pull in the keeper's notes"):
                self.state.flags["blackglass_relay_keeper_fear_read"] = True
                self.add_clue("The keeper feared the null bell more than Caldra. Its dead note can make the support pulse fall into its own counterweight.")
                self.reward_party(xp=10, reason="reading the relay keeper's panic")
        else:
            self.player_action("Trace the slate dust where old bell timing has started behaving like spellwork.")
            if self.skill_check(self.state.player, "Arcana", dc, context="to trace the relay ledger's spell-timing"):
                self.state.flags["blackglass_relay_spell_timing_traced"] = True
                self.add_clue("Old bell arithmetic has become spell timing inside the relay house, and the null bell can still spoil the count.")
                self.reward_party(xp=10, reason="tracing the relay spell timing")
        self.complete_act2_map_room(dungeon, room.room_id)
        self.add_journal("You took the Blackglass relay ledger and learned the timing Caldra's Forge support line expects.")

    def _blackglass_relay_null_bell_walk(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say(
            "The null-bell walk hangs over the sump on chain and old oak. Each bell has a cloth gag, each gag has a thumbprint, and every counterweight waits with patient malice."
        )
        dc = 14
        if self.state.flags.get("blackglass_relay_ledger_read") or self.state.flags.get("forge_reserve_timing_known"):
            dc -= 1
        if self.state.flags.get("blackglass_relay_cables_cleared") or self.state.flags.get("blackglass_relay_sump_line_marked"):
            dc -= 1
        choice = self.scenario_choice(
            "How do you tune the null bell?",
            [
                self.skill_tag("ARCANA", self.action_option("Set the dead note one beat ahead of the Forge support pulse.")),
                self.skill_tag("RELIGION", self.action_option("Name the older bell vow before the Choir's gag can teach it obedience.")),
                self.skill_tag("ATHLETICS", self.action_option("Lock the counterweight chain where the next support pulse has to fall into it.")),
            ],
            allow_meta=False,
        )
        clean_tune = False
        if choice == 1:
            self.player_action("Set the dead note one beat ahead of the Forge support pulse.")
            clean_tune = self.skill_check(self.state.player, "Arcana", max(12, dc), context="to tune the null bell ahead of the Forge pulse")
        elif choice == 2:
            self.player_action("Name the older bell vow before the Choir's gag can teach it obedience.")
            clean_tune = self.skill_check(self.state.player, "Religion", max(12, dc), context="to wake the null bell's older vow")
        else:
            self.player_action("Lock the counterweight chain where the next support pulse has to fall into it.")
            clean_tune = self.skill_check(self.state.player, "Athletics", max(12, dc), context="to lock the relay counterweight chain")
        self.complete_act2_map_room(dungeon, room.room_id)
        if clean_tune:
            self.state.flags["blackglass_relay_null_tone_clean"] = True
            self.apply_status(self.state.player, "blessed", 1, source="the relay's dead bell answering cleanly")
            self.add_clue("The null bell can make the Forge support pulse drop into dead weight before it reaches Caldra's dais.")
            self.reward_party(xp=15, reason="tuning the relay null bell cleanly")
        else:
            self.say("The bell answers with a dead note, but the chain bites and sparks before it settles.")
            self.act2_shift_metric(
                "act2_route_control",
                -1,
                "the relay's null bell had to be tuned loud enough for the Forge route to feel the drag",
            )

    def _blackglass_relay_counterweight_crown(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        high_pressure = self.act2_metric_value("act2_whisper_pressure") >= 4
        full_party = len(self.state.party_members()) >= 4
        enemies = [create_enemy("obelisk_chorister"), create_enemy("blackglass_listener")]
        if full_party or high_pressure:
            enemies.append(self.act2_pick_enemy(("pact_archive_warden", "blacklake_pincerling", "choir_adept")))
        if high_pressure and full_party:
            enemies.append(self.act2_pick_enemy(("obelisk_eye", "blackglass_listener", "starblighted_miner")))
        hero_bonus = self.apply_scene_companion_support("blackglass_relay_house")
        if self.state.flags.get("blackglass_relay_cables_cleared"):
            hero_bonus += 1
            self.apply_status(enemies[1], "reeling", 1, source="the sump cable coughing out of rhythm")
        if self.state.flags.get("forge_reserve_timing_known"):
            hero_bonus += 1
            self.apply_status(enemies[0], "surprised", 1, source="the keeper ledger exposing the bell count")
        if self.state.flags.get("blackglass_relay_bell_tuned"):
            hero_bonus += 1
            enemies[0].current_hp = max(1, enemies[0].current_hp - 5)
        choice = self.scenario_choice(
            "How do you ground the relay crown?",
            [
                self.skill_tag("ARCANA", self.action_option("Break the support pulse where the crown tries to pass it into the Forge wall.")),
                self.skill_tag("ATHLETICS", self.action_option("Drop the counterweight through the crown and make the bell answer gravity.")),
                self.skill_tag("INVESTIGATION", self.action_option("Use the ledger beat and cut the one cable the crown still trusts.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Break the support pulse where the crown tries to pass it into the Forge wall.")
            if self.skill_check(self.state.player, "Arcana", 14, context="to ground the relay support pulse"):
                hero_bonus += 2
                self.state.flags["blackglass_relay_grounding_arc"] = True
                enemies[0].current_hp = max(1, enemies[0].current_hp - 4)
        elif choice == 2:
            self.player_action("Drop the counterweight through the crown and make the bell answer gravity.")
            if self.skill_check(self.state.player, "Athletics", 14, context="to drop the relay counterweight through the crown"):
                hero_bonus += 2
                self.state.flags["blackglass_relay_counterweight_dropped"] = True
                self.apply_status(enemies[1], "prone", 1, source="the counterweight punching through the crown")
        else:
            dc = 13 if self.state.flags.get("forge_reserve_timing_known") else 14
            self.player_action("Use the ledger beat and cut the one cable the crown still trusts.")
            if self.skill_check(self.state.player, "Investigation", dc, context="to cut the relay crown's trusted cable"):
                hero_bonus += 2
                self.state.flags["blackglass_relay_trusted_cable_cut"] = True
                self.apply_status(enemies[0], "surprised", 1, source="the trusted cable going dead first")
        outcome = self.run_encounter(
            Encounter(
                title="Blackglass Relay Crown",
                description="Choir signal crews and old counterweight machinery fight to keep the Forge listening.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The relay crown keeps ticking, and the Forge support pulse keeps its clean route to Caldra.")
            return
        if outcome == "fled":
            self.return_to_act2_hub("You retreat from the relay crown before the counterweights can seal the upper walk.")
            return
        self.complete_act2_map_room(dungeon, room.room_id)
        self.reward_party(xp=55, gold=18, reason="grounding the Blackglass Relay House")
        self.add_clue("Grounding the Blackglass Relay House cuts one support signal before it can reach the Meridian Forge.")
        self.add_journal("You grounded the Blackglass Relay House and left Caldra's Forge support line dragging dead weight.")
        self.return_to_act2_hub("The relay house goes quiet behind you, except for one wet cable ticking against stone with nothing left to tell.")

    def _forge_threshold(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        if not self.state.flags.get("forge_seen"):
            self.say(
                "The Meridian Forge is no longer just a lost wonder. The Quiet Choir has turned it into an instrument. "
                "Shards hum inside old channels, the air sounds wrong when it moves, and the whole chamber feels like it is listening for the next hand bold enough to strike it.",
                typed=True,
            )
            if self.state.flags.get("black_lake_shrine_purified"):
                self.say("The answered sanctity from Blackglass keeps one line through the chamber sounding like craft instead of hunger.")
            if self.state.flags.get("black_lake_barracks_orders_taken"):
                self.say("The stolen barracks orders mark which choir lanes were supposed to reinforce the forge and which ones were only meant to witness.")
            elif self.state.flags.get("black_lake_barracks_raided"):
                self.say("Because you stripped the barracks on the crossing, the forge's outer support rhythm is thinner than Caldra expected.")
            if self.state.flags.get("black_lake_causeway_shaken"):
                self.say("The force you fed into the causeway still travels through the old foundations. The shard channels are venting on a rhythm instead of a mystery.")
            if self.state.flags.get("forge_signal_grounded"):
                self.say("The Blackglass relay line reaches the Forge wall and dies there, ticking once against stone before the chamber can answer it.")
            if self.state.flags.get("forge_reserve_timing_known"):
                self.say("The keeper's timing slates put Caldra's reserve beat on the table before the first Forge bell moves.")
            if self.state.flags.get("blackglass_relay_bell_tuned"):
                self.say("The null bell's dead note follows you into the threshold, a flat little refusal under the Forge hum.")
            self.state.flags["forge_seen"] = True
        if (
            self.act2_metric_value("act2_whisper_pressure") >= 4
            or self.state.flags.get("black_lake_causeway_shaken")
            or self.state.flags.get("black_lake_anchor_weak_point_found")
            or self.state.flags.get("forge_signal_grounded")
        ):
            self.state.flags["forge_shard_route_exposed"] = True
        nim = self.find_companion("Nim Ardentglass")
        if nim is not None and nim in self.state.companions:
            if self.state.flags.get("nim_countermeasure_notes"):
                self.speaker(
                    "Nim Ardentglass",
                    "The chamber's still honest in the margins. Read the traffic, not the glow, and it cannot lie about where it is feeding itself.",
                )
            else:
                self.speaker(
                    "Nim Ardentglass",
                    "Old routework always betrays who it still serves. The forge-light is a distraction; the traffic lines are the truth.",
                )
        choice = self.scenario_choice(
            "What do you read first in the forge chamber?",
            [
                self.skill_tag("INVESTIGATION", self.action_option("Lay the stolen support routes over the chamber and find the choir's real traffic line.")),
                self.skill_tag("RELIGION", self.action_option("Carry the shrine's answered sanctity forward before the forge swallows the last of it.")),
                self.skill_tag("ARCANA", self.action_option("Time the shard surges and learn which pulse the chamber cannot hide.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            dc = 13 if self.state.flags.get("black_lake_barracks_orders_taken") or self.state.flags.get("forge_reserve_timing_known") else 14
            self.player_action("Lay the stolen support routes over the chamber and find the choir's real traffic line.")
            if self.skill_check(self.state.player, "Investigation", dc, context="to read the forge's real support traffic"):
                self.state.flags["forge_threshold_orders_read"] = True
                self.add_clue("The Forge's real reinforcement traffic still runs through the choir pit, which means Caldra's dais is not the only thing holding her ritual up.")
                self.add_journal("You used the Blackglass orders to read the Forge threshold and find the chamber's real support traffic.")
                self.reward_party(xp=10, reason="reading the forge support routes")
        elif choice == 2:
            dc = 13 if self.state.flags.get("black_lake_shrine_purified") else 14
            self.player_action("Carry the shrine's answered sanctity forward before the forge swallows the last of it.")
            if self.skill_check(self.state.player, "Religion", dc, context="to carry clean sanctity into the forge threshold"):
                self.state.flags["forge_threshold_sanctified"] = True
                self.apply_status(self.state.player, "blessed", 1, source="the Blackglass shrine carried into the Forge")
                self.add_journal("You carried Blackglass's answered sanctity across the Forge threshold and kept one lane of the chamber honest.")
                self.reward_party(xp=10, reason="sanctifying the forge threshold")
        else:
            dc = (
                13
                if self.state.flags.get("black_lake_causeway_shaken")
                or self.state.flags.get("black_lake_anchor_weak_point_found")
                or self.state.flags.get("blackglass_relay_bell_tuned")
                else 14
            )
            self.player_action("Time the shard surges and learn which pulse the chamber cannot hide.")
            if self.skill_check(self.state.player, "Arcana", dc, context="to read the shard surges before they settle"):
                self.state.flags["forge_threshold_shard_timing"] = True
                self.state.flags["forge_shard_route_exposed"] = True
                self.add_clue("The force you fed into the Blackglass foundations has exposed a shard vent that Caldra was relying on the chamber to keep hidden.")
                self.add_journal("You timed the Forge's shard surges and exposed a side route the chamber was trying to keep buried.")
                self.reward_party(xp=10, reason="timing the forge shard surges")
        self.complete_act2_map_room(dungeon, room.room_id)

    def _forge_choir_pit(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        high_pressure = self.act2_metric_value("act2_whisper_pressure") >= 4
        hard_route = self.act2_metric_value("act2_route_control") <= 2 or self.act2_party_has_strong_route_gear()
        full_party = len(self.state.party_members()) >= 4
        enemies = [create_enemy("choir_adept"), create_enemy("cult_lookout")]
        if not self.state.flags.get("black_lake_barracks_raided") and not self.state.flags.get("forge_signal_grounded"):
            enemies.append(self.act2_pick_enemy(("cult_lookout", "choir_executioner", "starblighted_miner")))
        if full_party and (hard_route or high_pressure):
            enemies.append(self.act2_pick_enemy(("cult_lookout", "choir_executioner", "starblighted_miner")))
        elif high_pressure:
            enemies.append(self.act2_pick_enemy(("obelisk_eye", "starblighted_miner", "iron_prayer_horror")))
        hero_bonus = self.apply_scene_companion_support("forge_of_spells")
        if self.state.flags.get("black_lake_barracks_raided"):
            hero_bonus += 1
        if self.state.flags.get("forge_signal_grounded"):
            hero_bonus += 1
            self.apply_status(enemies[0], "reeling", 1, source="the Blackglass relay line dying before it reaches the pit")
        if self.state.flags.get("black_lake_barracks_orders_taken") or self.state.flags.get("forge_threshold_orders_read"):
            hero_bonus += 1
            self.apply_status(enemies[0], "surprised", 1, source="their reserve line already being read against them")
        choice = self.scenario_choice(
            "How do you break the choir pit?",
            [
                self.skill_tag("STEALTH", self.action_option("Kill the last signal line before the adepts can fold it back into the forge.")),
                self.skill_tag("ARCANA", self.action_option("Shatter their chant tempo and make the pit answer the forge instead of the Choir.")),
                self.skill_tag("INTIMIDATION", self.action_option("Hit the witnesses so hard the whole pit remembers fear before faith.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Kill the last signal line before the adepts can fold it back into the forge.")
            if self.skill_check(self.state.player, "Stealth", 14, context="to cut the choir pit's signal line cleanly"):
                hero_bonus += 2
                self.apply_status(enemies[1], "surprised", 1, source="the signal line dying first")
        elif choice == 2:
            self.player_action("Shatter their chant tempo and make the pit answer the forge instead of the Choir.")
            if self.skill_check(self.state.player, "Arcana", 14, context="to break the choir pit's chant tempo"):
                hero_bonus += 1
                enemies[0].current_hp = max(1, enemies[0].current_hp - 4)
        else:
            self.player_action("Hit the witnesses so hard the whole pit remembers fear before faith.")
            if self.skill_check(self.state.player, "Intimidation", 14, context="to crack the forge witnesses' nerve"):
                hero_bonus += 1
                self.apply_status(enemies[0], "frightened", 1, source="the pit losing its nerve")
        outcome = self.run_encounter(
            Encounter(
                title="Forge Choir Pit",
                description="The last organized choir support line still tries to keep Caldra's ritual supplied and witnessed.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The choir pit keeps feeding the Forge and the chamber never stops answering it.")
            return
        if outcome == "fled":
            self.return_to_act2_hub("You fall back from the choir pit before the Forge can seal the route behind you.")
            return
        self.complete_act2_map_room(dungeon, room.room_id)
        self.add_journal("You silenced the forge choir pit and cut one of Caldra's last organized support lines.")

    def _forge_pact_anvil(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say(
            "An old Meridian Compact anvil sits inside the Meridian Forge's newer desecration like a discipline the chamber still cannot quite kill. Heat moves through it in patient lines instead of hungry bursts."
        )
        dc = 15
        if self.state.flags.get("agatha_truth_clear"):
            dc -= 1
        if self.state.flags.get("nim_countermeasure_notes"):
            dc -= 1
        if self.state.flags.get("black_lake_shrine_purified") or self.state.flags.get("forge_threshold_sanctified"):
            dc -= 1
        choice = self.scenario_choice(
            "How do you work the Compact anvil?",
            [
                self.skill_tag("ARCANA", self.action_option("Break the forge-channel tempo before Caldra can finish tuning it.")),
                self.skill_tag("INVESTIGATION", self.action_option("Read the old craft rhythm and find the one line the Choir still has to fake.")),
                self.skill_tag("RELIGION", self.action_option("Ask the older vow to remember what this chamber was built to serve.")),
            ],
            allow_meta=False,
        )
        tuned = False
        if choice == 1:
            self.player_action("Break the forge-channel tempo before Caldra can finish tuning it.")
            tuned = self.skill_check(self.state.player, "Arcana", dc, context="to disrupt the forge-channel harmony at the anvil")
        elif choice == 2:
            self.player_action("Read the old craft rhythm and find the one line the Choir still has to fake.")
            tuned = self.skill_check(self.state.player, "Investigation", dc, context="to read the Forge's surviving craft rhythm")
        else:
            self.player_action("Ask the older vow to remember what this chamber was built to serve.")
            tuned = self.skill_check(self.state.player, "Religion", dc, context="to wake the older Meridian Compact discipline in the anvil")
        self.complete_act2_map_room(dungeon, room.room_id)
        if tuned:
            self.state.flags["forge_anvil_tuned"] = True
            if self.state.flags.get("south_adit_counter_cadence_learned") and self.find_companion("Irielle Ashwake") is not None:
                self.state.flags["irielle_counter_cadence"] = True
                self.state.flags["counter_cadence_known"] = True
            self.add_clue("The Meridian Compact anvil still carries a discipline that can crack the Choir's forge-tempo if you hit it cleanly.")
            self.add_journal("You woke the Meridian Compact anvil's older discipline and proved the Meridian Forge still remembers craft beneath the Choir's ritual.")
            self.reward_party(xp=15, reason="recovering the Forge's older rhythm")
        else:
            self.say("The anvil answers, but not cleanly enough to become certainty on its own.")

    def _forge_shard_channels(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        enemies = [create_enemy("obelisk_eye"), create_enemy("obelisk_chorister")]
        if self.act2_metric_value("act2_whisper_pressure") >= 4:
            enemies.append(self.act2_pick_enemy(("covenant_breaker_wight", "forge_echo_stalker", "obelisk_eye")))
        elif len(self.state.party_members()) >= 4:
            enemies.append(self.act2_pick_enemy(("blackglass_listener", "forge_echo_stalker", "obelisk_chorister")))
        hero_bonus = self.apply_scene_companion_support("forge_of_spells")
        if self.state.flags.get("black_lake_causeway_shaken"):
            hero_bonus += 1
            self.apply_status(enemies[0], "reeling", 1, source="the causeway shock still running through the foundations")
        if self.state.flags.get("black_lake_anchor_weak_point_found") or self.state.flags.get("forge_threshold_shard_timing"):
            hero_bonus += 1
        if self.state.flags.get("forge_signal_grounded"):
            hero_bonus += 1
            enemies[0].current_hp = max(1, enemies[0].current_hp - 4)
        if self.state.flags.get("black_lake_causeway_footing_marked"):
            hero_bonus += 1
        choice = self.scenario_choice(
            "How do you break the shard channels?",
            [
                self.skill_tag("ARCANA", self.action_option("Turn the channel pulse against itself before the eye can refocus it.")),
                self.skill_tag("ATHLETICS", self.action_option("Force the braces wide enough that the shard surge tears its own lane apart.")),
                self.skill_tag("SURVIVAL", self.action_option("Move on the marked footing and make the channel chase empty space.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Turn the channel pulse against itself before the eye can refocus it.")
            if self.skill_check(self.state.player, "Arcana", 14, context="to invert the shard-channel pulse"):
                hero_bonus += 2
                enemies[0].current_hp = max(1, enemies[0].current_hp - 5)
        elif choice == 2:
            self.player_action("Force the braces wide enough that the shard surge tears its own lane apart.")
            if self.skill_check(self.state.player, "Athletics", 14, context="to break the shard braces under pressure"):
                hero_bonus += 1
                self.apply_status(self.state.player, "emboldened", 2, source="breaking the shard braces")
        else:
            self.player_action("Move on the marked footing and make the channel chase empty space.")
            if self.skill_check(self.state.player, "Survival", 14, context="to move through the shard channel on the only safe line"):
                hero_bonus += 1
                self.apply_status(enemies[1], "surprised", 1, source="the channel losing your trail")
        outcome = self.run_encounter(
            Encounter(
                title="Forge Shard Channels",
                description="The Forge's worst shard pressure is no longer ambient. It is pointed at you on purpose.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The shard channels tear the party apart before the lens can be reached.")
            return
        if outcome == "fled":
            self.return_to_act2_hub("You retreat from the shard channels before the Forge can pin the whole company in them.")
            return
        self.complete_act2_map_room(dungeon, room.room_id)
        self.add_clue("The shard channels were feeding the Forge from a deeper pressure seam below Caldra's platform.")
        self.add_journal("You broke the shard channels and turned the Forge's hidden pressure seam into a wound instead of a weapon.")

    def _forge_resonance_lens(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say(
            "A lattice of humming shard-light hangs over the Forge's heart. This is where Caldra turns every side route into certainty and every witness into part of the instrument."
        )
        irielle = self.find_companion("Irielle Ashwake")
        if irielle is not None and irielle in self.state.companions:
            if self.state.flags.get("south_adit_counter_cadence_learned") or self.state.flags.get("irielle_counter_cadence"):
                self.speaker(
                    "Irielle Ashwake",
                    "There. The lens wants one obedience note under everything else. Answer it wrong on purpose and Caldra loses her clean certainty.",
                )
            else:
                self.speaker(
                    "Irielle Ashwake",
                    "This is the part the Choir never lets witnesses describe twice. Trust the second thought, not the first one it gives you.",
                )
        conyberry_sigil_copied = bool(self.state.flags.get("conyberry_sigil_copied"))
        if conyberry_sigil_copied:
            self.say(
                "The copied Hushfen sigil makes one strand of the lens painfully legible: the Choir is still teaching old service-wards to obey without looking conquered."
            )
            if not self.state.flags.get("forge_conyberry_sigil_risk_applied"):
                self.state.flags["forge_conyberry_sigil_risk_applied"] = True
                if self.state.flags.get("agatha_warning_bound"):
                    self.state.flags["forge_conyberry_sigil_bound_safely"] = True
                    self.say("Because the Pale Witness's warning was bound before it left Hushfen, the copied mark stays a key instead of becoming an open wound.")
                else:
                    self.state.flags["forge_conyberry_sigil_moral_risk"] = True
                    self.act2_shift_metric(
                        "act2_whisper_pressure",
                        1,
                        "using Hushfen's copied wound against the Meridian Forge gives the Choir one more live shape to answer through",
                    )
        dc = 15
        if self.state.flags.get("black_lake_shrine_purified"):
            dc -= 1
        if self.state.flags.get("black_lake_barracks_orders_taken"):
            dc -= 1
        if self.state.flags.get("black_lake_causeway_shaken") or self.state.flags.get("black_lake_anchor_weak_point_found"):
            dc -= 1
        if self.state.flags.get("forge_signal_grounded") or self.state.flags.get("blackglass_relay_bell_tuned"):
            dc -= 1
        if self.state.flags.get("forge_anvil_tuned"):
            dc -= 1
        if conyberry_sigil_copied:
            dc -= 1
        choice = self.scenario_choice(
            "How do you map the resonance lens before facing Caldra?",
            [
                self.skill_tag("INVESTIGATION", self.action_option("Lay every side objective over the lens and find the one support line she still needs.")),
                self.skill_tag("ARCANA", self.action_option("Break the lens tempo now, while it is still pretending to be stable.")),
                self.skill_tag("PERSUASION", self.action_option("Name the lie the Choir is telling itself and make the lens carry doubt instead of certainty.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Lay every side objective over the lens and find the one support line she still needs.")
            success = self.skill_check(self.state.player, "Investigation", dc, context="to map the Forge lens from the inside")
            if success:
                self.state.flags["forge_lens_support_line_named"] = True
        elif choice == 2:
            self.player_action("Break the lens tempo now, while it is still pretending to be stable.")
            success = self.skill_check(self.state.player, "Arcana", dc, context="to break the resonance lens tempo before the boss fight")
            if success:
                self.state.flags["forge_lens_tempo_broken"] = True
        else:
            persuasion_dc = dc
            if self.state.flags.get("act2_captive_outcome") == "many_saved":
                persuasion_dc -= 1
            if self.find_companion("Irielle Ashwake") is not None:
                persuasion_dc -= 1
            self.player_action("Name the lie the Choir is telling itself and make the lens carry doubt instead of certainty.")
            success = self.skill_check(self.state.player, "Persuasion", persuasion_dc, context="to name the lie the lens is built around")
            if success:
                self.state.flags["forge_lens_truth_named"] = True
        self.complete_act2_map_room(dungeon, room.room_id)
        if success:
            if self.state.flags.get("south_adit_counter_cadence_learned") and irielle is not None:
                self.state.flags["irielle_counter_cadence"] = True
                self.state.flags["counter_cadence_known"] = True
            if self.state.flags.get("forge_choir_pit_silenced"):
                self.state.flags["forge_support_line_broken"] = True
            if self.state.flags.get("forge_pact_rhythm_found"):
                self.state.flags["forge_ritual_line_broken"] = True
            if self.state.flags.get("forge_shard_channels_disrupted"):
                self.state.flags["forge_shard_line_broken"] = True
            if conyberry_sigil_copied:
                self.state.flags["forge_lens_conyberry_sigil_used"] = True
                self.add_journal("You used Hushfen's copied sigil to read one of the Meridian Forge lens's obedience seams before Caldra could hide it.")
            self.add_clue("The resonance lens only held because Caldra was braiding witness, ritual, and shard pressure into one engineered lie.")
            self.add_journal("You mapped the resonance lens from inside and learned exactly which lines were keeping Caldra's certainty standing.")
            self.reward_party(xp=15, reason="mapping the resonance lens before the final confrontation")
        else:
            self.say("You map enough of the lens to reach Caldra, but not enough to pretend the chamber is done with surprises.")

    def _forge_caldra_dais(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        high_pressure = self.act2_metric_value("act2_whisper_pressure") >= 4
        hard_route = self.act2_metric_value("act2_route_control") <= 2 or self.act2_party_has_strong_route_gear()
        full_party = len(self.state.party_members()) >= 4
        enemies = [create_enemy("caldra_voss"), create_enemy("obelisk_chorister")]
        if full_party:
            enemies.append(self.act2_pick_enemy(("forge_echo_stalker", "memory_taker_adept", "choir_executioner")))
        if self.state.flags.get("black_lake_barracks_raided") and full_party and (hard_route or high_pressure):
            enemies.append(self.act2_pick_enemy(("memory_taker_adept", "forge_echo_stalker")))
        elif not self.state.flags.get("black_lake_barracks_raided") and not self.state.flags.get("forge_signal_grounded"):
            enemies.append(self.act2_pick_enemy(("memory_taker_adept", "choir_executioner", "starblighted_miner")))
        if high_pressure:
            enemies.append(self.act2_pick_enemy(("forge_echo_stalker", "obelisk_eye", "covenant_breaker_wight")))

        hero_bonus = self.apply_scene_companion_support("forge_of_spells")
        parley_dc = 15
        if self.state.flags.get("black_lake_shrine_purified") or self.state.flags.get("forge_threshold_sanctified"):
            self.apply_status(self.state.player, "blessed", 2, source="the reclaimed Blackglass shrine")
            hero_bonus += 1
            parley_dc -= 1
        if self.state.flags.get("black_lake_barracks_orders_taken") or self.state.flags.get("forge_lens_support_line_named"):
            hero_bonus += 1
            if len(enemies) > 1:
                enemies[1].current_hp = max(1, enemies[1].current_hp - 4)
        if self.state.flags.get("forge_signal_grounded"):
            hero_bonus += 1
            parley_dc -= 1
            if len(enemies) > 1:
                self.apply_status(enemies[1], "reeling", 1, source="the grounded relay leaving Caldra's support bell dead")
        if self.state.flags.get("black_lake_causeway_shaken") or self.state.flags.get("forge_shard_channels_disrupted"):
            hero_bonus += 1
            if len(enemies) > 1:
                self.apply_status(enemies[1], "reeling", 1, source="the forge foundations never fully settled")
        if self.state.flags.get("forge_anvil_tuned") or self.state.flags.get("forge_ritual_line_broken"):
            hero_bonus += 1
            enemies[0].current_hp = max(1, enemies[0].current_hp - 6)
        if self.state.flags.get("south_adit_counter_cadence_learned") and self.find_companion("Irielle Ashwake") is not None:
            self.state.flags["irielle_counter_cadence"] = True
            self.state.flags["counter_cadence_known"] = True
        if self.state.flags.get("irielle_counter_cadence"):
            self.state.flags["counter_cadence_known"] = True
            hero_bonus += 1
            enemies[0].current_hp = max(1, enemies[0].current_hp - 4)
            self.say("Irielle's counter-cadence lands first and steals part of the forge's certainty before steel ever crosses it.")
            parley_dc -= 1

        self.speaker("Sister Caldra Voss", "The Forge does not create. It clarifies.")
        self.speaker("Sister Caldra Voss", "Every vow has an echo. Every echo has an owner.")
        self.speaker("Sister Caldra Voss", "The world is loud because it fears being counted.")
        choice = self.scenario_choice(
            "How do you open the final confrontation?",
            [
                self.quoted_option("ARCANA", "Break her ritual tempo before she finishes tuning the forge."),
                self.quoted_option("PERSUASION", "You have seen enough of what the Choir calls revelation. Step away from the forge."),
                self.action_option("Hit the chamber hard and trust momentum before the whispers settle in."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            dc = 15
            if self.state.flags.get("agatha_truth_clear"):
                dc -= 1
            if self.state.flags.get("nim_countermeasure_notes"):
                dc -= 1
            if self.state.flags.get("forge_anvil_tuned"):
                dc -= 1
            self.player_speaker("Break her ritual tempo before she finishes tuning the forge.")
            if self.skill_check(self.state.player, "Arcana", dc, context="to disrupt the forge-channel harmony"):
                hero_bonus += 2
                enemies[0].current_hp = max(1, enemies[0].current_hp - 6)
        elif choice == 2:
            dc = 15
            if self.state.flags.get("act2_captive_outcome") == "many_saved":
                dc -= 1
            if self.find_companion("Irielle Ashwake") is not None:
                dc -= 1
            if self.state.flags.get("forge_lens_truth_named"):
                dc -= 1
            self.player_speaker("You have seen enough of what the Choir calls revelation. Step away from the forge.")
            if self.skill_check(self.state.player, "Persuasion", dc, context="to force even a moment of doubt into Caldra's certainty"):
                hero_bonus += 1
                self.apply_status(enemies[1], "frightened", 1, source="hearing the certainty crack")
        else:
            self.player_action("Hit the chamber hard and trust momentum before the whispers settle in.")
            hero_bonus += 2
            self.apply_status(self.state.player, "emboldened", 2, source="storming the Meridian Forge")
            if self.state.flags.get("act2_sponsor") == "lionshield":
                hero_bonus += 1
        outcome = self.run_encounter(
            Encounter(
                title="Boss: Sister Caldra Voss",
                description="The Quiet Choir's cult agent makes the final stand at the Meridian Forge.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=True,
                parley_dc=max(12, parley_dc),
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("Caldra holds the Forge and the mine's song bends further away from anything mortal should trust.")
            return
        if outcome == "fled":
            self.return_to_act2_hub("You tear yourself out of the forge chamber before the whole room can close around the party.")
            return
        self.complete_act2_map_room(dungeon, room.room_id)
        self.add_clue("Caldra's notes describe the Forge as only a lens. Whatever the Quiet Choir truly serves is deeper, older, and not confined to the mine.")
        if self.act2_metric_value("act2_whisper_pressure") >= 4:
            self.add_clue(
                "Even broken, the Forge keeps trying to answer a call from farther down. The party is not leaving Resonant Vaults with clean silence."
            )
        self.add_journal("You broke Sister Caldra Voss and tore the Meridian Forge out of the Quiet Choir's grip.")
        self.reward_party(xp=120, gold=40, reason="breaking the Quiet Choir's Resonant Vaults cell")
        self.act2_record_epilogue_flags()
        self.return_to_act2_hub("The Forge's wrong song breaks apart behind you, and Resonant Vaults finally sounds like a place instead of an instrument.")

    def _old_owl_well_ring(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        if not self.state.flags.get("old_owl_well_seen"):
            self.say(
                "The old watchtower rises from the scrub like a cracked finger of Netherese stone. Dig lines, corpse-salt circles, and half-collapsed tents surround the well itself, "
                "and every gust of wind seems to carry up dust that should have stayed buried.",
                typed=True,
            )
            self.state.flags["old_owl_well_seen"] = True
        party_size = self.act1_party_size()
        enemies = [create_enemy("skeletal_sentry"), create_enemy("bandit", name="Ashen Brand Fixer")]
        if party_size >= 3:
            enemies.append(self.act1_pick_enemy(("skeletal_sentry", "rust_shell_scuttler", "ashstone_percher", "briar_twig")))
        hero_bonus = self.apply_scene_companion_support("old_owl_well")
        choice = self.scenario_choice(
            "How do you work the edge of the dig ring?",
            [
                self.skill_tag("STEALTH", self.action_option("Move along the broken irrigation trench and get inside the ring quietly.")),
                self.quoted_option("ARCANA", "Those sigils matter. Let me read what kind of wrongness is powering them."),
                self.quoted_option("DECEPTION", "Call out as hired salvage come to collect the next cart of bones."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Move along the broken irrigation trench and get inside the ring quietly.")
            success = self.skill_check(self.state.player, "Stealth", 13, context="to slip into the dig site unseen")
            if success:
                self.apply_status(enemies[0], "surprised", 1, source="your trench approach")
                enemies[0].current_hp = max(1, enemies[0].current_hp - 4)
                hero_bonus += 2
                self.say("You are inside the ward-ring before the first skull-lantern turns your way.")
                followup = self.scenario_choice(
                    "You have one clean opening inside the ring. How do you spend it?",
                    [
                        self.action_option("Sabotage the ritual salt before the gravecaller feels the breach."),
                        self.action_option("Pick off the nearest sentry before it can join the line."),
                        self.action_option("Slip deeper toward the well mouth and keep the initiative for later."),
                    ],
                    allow_meta=False,
                )
                if followup == 1:
                    self.player_action("Sabotage the ritual salt before the gravecaller feels the breach.")
                    self.state.flags["old_owl_ritual_sabotaged"] = True
                    for enemy in enemies[1:]:
                        self.apply_status(enemy, "reeling", 1, source="your ritual sabotage")
                    hero_bonus += 1
                    self.say("The ward-salt breaks into the wrong pattern and the whole ring starts answering itself badly.")
                elif followup == 2:
                    self.player_action("Pick off the nearest sentry before it can join the line.")
                    self.state.flags["old_owl_sentry_picked"] = True
                    sentry = enemies[-1]
                    sentry.current_hp = max(1, sentry.current_hp - 5)
                    self.apply_status(sentry, "surprised", 1, source="your silent opening strike")
                    hero_bonus += 1
                    self.say("One defender goes down half-ready, and the ring loses a piece of itself before the fight even forms.")
                else:
                    self.player_action("Slip deeper toward the well mouth and keep the initiative for later.")
                    self.state.flags["old_owl_deeper_infiltration"] = True
                    self.apply_status(self.state.player, "invisible", 1, source="your deeper infiltration")
                    hero_bonus += 1
                    self.say("You learn the shape of the ground all the way to the buried dark lip before the alarm finally catches up.")
            else:
                self.apply_status(self.state.player, "reeling", 1, source="loose stone and a snapped old bucket chain")
                self.say("A snapped chain and shower of stone give the site plenty of warning.")
        elif choice == 2:
            self.player_speaker("Those sigils matter. Let me read what kind of wrongness is powering them.")
            success = self.skill_check(self.state.player, "Arcana", 13, context="to read the ward sigils before they flare")
            if success:
                self.apply_status(self.state.player, "resist_poison", 3, source="ward-script countermeasures")
                self.apply_status(enemies[1], "reeling", 2, source="your disruption of the ritual ring")
                hero_bonus += 1
                self.say("You spoil the smooth flow of the ritual enough to leave the defenders moving through their own half-broken pattern.")
            else:
                self.say("The symbols are older and uglier than you wanted them to be, and the answer comes back as a pulse of cold air instead of clarity.")
        else:
            self.player_speaker("Hired salvage. Open the line before the carts start backing up.")
            success = self.skill_check(self.state.player, "Deception", 13, context="to bluff your way into the dig perimeter")
            if success:
                enemies[1].current_hp = max(1, enemies[1].current_hp - 3)
                self.apply_status(enemies[1], "surprised", 1, source="your sudden betrayal")
                hero_bonus += 1
                self.say("The bluff holds just long enough for your first strike to turn the whole ring inside out.")
            else:
                self.apply_status(self.state.player, "surprised", 1, source="a suspicious foreman's shout")
                self.say("The closest hireling narrows their eyes, then starts yelling for the dead to rise.")

        outcome = self.run_encounter(
            Encounter(
                title="Blackglass Well Dig Ring",
                description="Bone-haulers and animated sentries close around the well mouth.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The dead keep their watch at Blackglass Well.")
            return
        if outcome == "fled":
            self.return_to_phandalin("You fall back from the well before the site can swallow the whole party.")
            return

        self.complete_map_room(dungeon, room.room_id)
        self.say("The outer ring collapses. A salt cart lies off to one side, and a half-buried trench still holds soot-black notes and salvage tallies.")

    def _old_owl_salt_cart(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("A prospector is lashed to the salt cart, shaking hard enough that even the rope knots twitch with them.")
        choice = self.scenario_choice(
            "How do you handle the rescue?",
            [
                self.quoted_option("MEDICINE", "Cut them free and keep them steady long enough to speak."),
                self.quoted_option("PERSUASION", "Easy. You made it this far, so stay with me a little longer."),
                self.action_option("Break the cart brace, drag them clear, and let the camp sort itself out later."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_speaker("Cut them free and keep them steady long enough to speak.")
            success = self.skill_check(
                self.state.player,
                "Medicine",
                12,
                context="to stabilize the prospector before shock takes their memory with it",
            )
            if success:
                self.say("The prospector gasps out one useful truth: the gravecaller answers to Ashfall's coin and the manor's keys.")
                self.add_clue("A rescued prospector says the gravecaller at Blackglass Well was being paid through Ashfall Watch for work tied to the manor hill.")
                self.reward_party(xp=10, reason="saving the prospector at Blackglass Well")
            else:
                self.say("You save the prospector's life, but not a clean version of what they saw.")
        elif choice == 2:
            self.player_speaker("Easy. You made it this far, so stay with me a little longer.")
            success = self.skill_check(self.state.player, "Persuasion", 12, context="to keep the prospector focused")
            if success:
                self.say("The prospector steadies enough to point out the same payment trail running through Ashfall Watch.")
                self.add_clue("The prospector confirms the dig ring was part of Ashfall Watch's wider salvage route.")
                self.reward_party(xp=10, reason="steadying the Old Owl prospector")
            else:
                self.say("The prospector survives, but the answers stay ragged.")
        else:
            self.player_action("Break the cart brace, drag them clear, and let the camp sort itself out later.")
            self.say("You haul the prospector clear and leave the salt cart collapsed in the trench, ruining any quick reset of the ring.")

        self.act1_adjust_metric("act1_survivors_saved", 1)
        self.act1_adjust_metric("act1_town_fear", -1)
        self.complete_map_room(dungeon, room.room_id)

    def _old_owl_supply_trench(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("Half-buried trench ledgers and soot-black route slips still cling to the damp soil under the supply tarp.")
        bryn = self.active_companion_by_id("bryn_underbough", minimum_disposition=6)
        options = [
            self.quoted_option("INVESTIGATION", "Read the notes and sketch the route chain before the wind ruins them."),
            self.quoted_option("ARCANA", "The ink itself looks wrong. I want to know what was mixed into it."),
            self.action_option("Pocket the cleanest pages and kick the rest into the trench water."),
        ]
        if bryn is not None:
            options.append(self.action_option("Let Bryn skim the soot ledgers for smuggler marks she used to know."))
        choice = self.scenario_choice(
            "What do you do with the recovered notes?",
            options,
            allow_meta=False,
        )
        if choice == 1:
            self.player_speaker("Read the notes and sketch the route chain before the wind ruins them.")
            success = self.skill_check(self.state.player, "Investigation", 12, context="to preserve the gravecaller notes before they scatter")
            if success:
                self.say("The page names Ashfall Watch as the collection point and mentions a soot-key transfer beneath the old manor hill.")
                self.add_clue("The Blackglass Well notes point to Ashfall Watch as the collection point for salvage moved toward the manor hill.")
                self.reward_party(xp=10, reason="securing the Blackglass Well route notes")
            else:
                self.say("You save fragments, but the ugliest details go spinning away with the dust.")
        elif choice == 2:
            self.player_speaker("The ink itself looks wrong. I want to know what was mixed into it.")
            success = self.skill_check(self.state.player, "Arcana", 12, context="to read the tainted route slips")
            if success:
                self.say("The ash-ink still carries the smell of the signal basin at Ashfall, which ties the sites together even more cleanly.")
                self.add_clue("The trench notes were written in the same treated ash used by Ashfall Watch's signaling crews.")
                self.reward_party(xp=10, reason="decoding the tainted ledgers at Blackglass Well")
            else:
                self.say("The ritual residue is obvious, but the deeper trail slips away from you.")
        elif choice == 3:
            self.player_action("Pocket the cleanest pages and kick the rest into the trench water.")
            self.say("You take the useful scraps and ruin the rest rather than leave them for the next scavenger.")
        else:
            self.player_action("Let Bryn skim the soot ledgers for smuggler marks she used to know.")
            self.say("Bryn crouches over the pages for only a few breaths before old route habits click back into place.")
            self.add_clue("Bryn recognizes old smuggler shorthand in the trench ledgers, tying the Ashen Brand's salvage line to one of her abandoned caches.")
            if self.has_quest("bryn_loose_ends") and not self.state.flags.get("bryn_cache_found"):
                self.state.flags["bryn_cache_found"] = True
                self.say("One note in Bryn's old hand marks the cache site she hoped had stayed buried with the rest of that life.")
            self.reward_party(xp=10, reason="letting Bryn read the trench ledgers")

        self.add_clue("The recovered route slips mention Cinderfall Ruins, a backup ember relay still feeding Ashfall Watch from the east scrub.")
        self.state.flags["varyn_filter_logic_seen"] = True
        self.unlock_act1_hidden_route(
            "The soot-black route slips expose a hidden approach: Cinderfall Ruins, an abandoned ember relay still feeding Ashfall's reserve line."
        )
        self.complete_map_room(dungeon, room.room_id)

    def is_old_owl_vaelith_encounter(self, encounter) -> bool:
        return (
            getattr(encounter, "title", "") == "Miniboss: Vaelith Marr"
            and self.state is not None
            and self.state.current_scene == "old_owl_well"
        )

    def is_varyn_sable_encounter(self, encounter) -> bool:
        return (
            getattr(encounter, "title", "") == "Boss: Varyn Sable"
            and self.state is not None
            and self.state.current_scene == "emberhall_cellars"
        )

    def is_ashfall_alarm_encounter(self, encounter) -> bool:
        return (
            getattr(encounter, "title", "") in {"Ashfall Gate", "Ashfall Lower Barracks"}
            and self.state is not None
            and self.state.current_scene == "ashfall_watch"
        )

    def is_ashfall_barracks_encounter(self, encounter) -> bool:
        return (
            getattr(encounter, "title", "") == "Ashfall Lower Barracks"
            and self.state is not None
            and self.state.current_scene == "ashfall_watch"
        )

    def is_rukhar_cinderfang_encounter(self, encounter) -> bool:
        return (
            getattr(encounter, "title", "") == "Miniboss: Rukhar Cinderfang"
            and self.state is not None
            and self.state.current_scene == "ashfall_watch"
        )

    def is_tresendar_cistern_eye_encounter(self, encounter) -> bool:
        return (
            getattr(encounter, "title", "") == "The Cistern Eye"
            and self.state is not None
            and self.state.current_scene == "tresendar_manor"
        )

    def is_tresendar_cellar_encounter(self, encounter) -> bool:
        return (
            getattr(encounter, "title", "") == "Duskmere Cellars"
            and self.state is not None
            and self.state.current_scene == "tresendar_manor"
        )

    def is_tresendar_manor_encounter(self, encounter) -> bool:
        return (
            getattr(encounter, "title", "") in {"Duskmere Cellars", "The Cistern Eye"}
            and self.state is not None
            and self.state.current_scene == "tresendar_manor"
        )

    def find_enemy_by_archetype(self, enemies, archetype: str) -> Any | None:
        return next((enemy for enemy in enemies if getattr(enemy, "archetype", "") == archetype), None)

    def find_vaelith_marr(self, enemies) -> Any | None:
        return self.find_enemy_by_archetype(enemies, "vaelith_marr")

    def find_varyn_sable(self, enemies) -> Any | None:
        return self.find_enemy_by_archetype(enemies, "varyn")

    def find_rukhar_cinderfang(self, enemies) -> Any | None:
        return self.find_enemy_by_archetype(enemies, "rukhar")

    def find_cistern_eye(self, enemies) -> Any | None:
        return next(
            (
                enemy
                for enemy in enemies
                if getattr(enemy, "archetype", "") == "nothic" and ("Cistern Eye" in getattr(enemy, "name", ""))
            ),
            None,
        )

    def vaelith_gravecall_is_suppressed(self, vaelith) -> bool:
        return any(self.has_status(vaelith, status) for status in ("reeling", "frightened", "stunned"))

    def on_encounter_round_start(self, encounter, heroes, enemies, initiative, round_number: int) -> None:
        self.handle_old_owl_vaelith_gravecall(encounter, heroes, enemies, initiative, round_number)
        self.handle_old_owl_vaelith_ritual_terrain(encounter, heroes, enemies)
        self.handle_varyn_spell_clock(encounter, heroes, enemies, round_number)
        self.handle_ashfall_alarm_clock(encounter, enemies, initiative, round_number)
        self.handle_ashfall_barracks_shield_line(encounter, enemies)
        self.handle_rukhar_command_aura(encounter, enemies, round_number)
        self.handle_tresendar_cellar_alarm_chain(encounter, enemies, initiative, round_number)
        self.handle_tresendar_manor_collapse_timer(encounter, heroes, enemies, round_number)
        self.handle_cistern_eye_secret_tax(encounter, heroes, enemies, round_number)
        self.handle_cistern_eye_secret_hunger(encounter, heroes, enemies, round_number)

    def handle_old_owl_vaelith_gravecall(self, encounter, heroes, enemies, initiative, round_number: int) -> None:
        if not self.is_old_owl_vaelith_encounter(encounter):
            return
        vaelith = self.find_vaelith_marr(enemies)
        if vaelith is None or not vaelith.is_conscious():
            return
        if self.vaelith_gravecall_is_suppressed(vaelith):
            return

        gravecall = int(vaelith.bond_flags.get("gravecall_counter", 0)) + 1
        vaelith.bond_flags["gravecall_counter"] = gravecall
        if gravecall == 1:
            self.say("Vaelith starts a gravecall under the words of the fight, and the well answers with a slow scrape below.")
        elif gravecall == 2 and not vaelith.bond_flags.get("gravecall_support_raised"):
            vaelith.bond_flags["gravecall_support_raised"] = True
            support = create_enemy("skeletal_sentry", name="Gravecalled Sentry")
            support.notes.append("Raised by Vaelith Marr's gravecall ritual.")
            enemies.append(support)
            initiative.append(support)
            self.say("A Gravecalled Sentry claws out of the corpse-salt ring and joins Vaelith's line.")
        elif gravecall == 4 and not vaelith.bond_flags.get("gravecall_line_blessed"):
            vaelith.bond_flags["gravecall_line_blessed"] = True
            self.say("Vaelith finishes a harsh gravecall cadence, and the dead line moves with borrowed certainty.")
            for enemy in enemies:
                if enemy.is_conscious():
                    self.apply_status(enemy, "blessed", 2, source="Vaelith's gravecall")

    def handle_old_owl_vaelith_ritual_terrain(self, encounter, heroes, enemies) -> None:
        if not self.is_old_owl_vaelith_encounter(encounter):
            return
        vaelith = self.find_vaelith_marr(enemies)
        if vaelith is None or not vaelith.is_conscious():
            return
        conscious_heroes = [hero for hero in heroes if hero.is_conscious()]
        if not conscious_heroes:
            return
        target = max(conscious_heroes, key=self.old_owl_damage_pressure_score)
        self.say("The corpse-salt ring flexes underfoot and spits grave-ash toward the well lip.")
        if self.saving_throw(target, "DEX", 12, context="against the Blackglass corpse-salt ring"):
            self.say(f"{target.name} slips clear of the worst of the grave-ash spray.")
            return
        damage_roll = self.roll_with_display_bonus(
            "1d4",
            style="damage",
            context_label="Blackglass corpse-salt ring",
            outcome_kind="damage",
        )
        actual = self.apply_damage(target, damage_roll.total, damage_type="necrotic")
        self.apply_status(target, "reeling", 1, source="the Blackglass corpse-salt ring")
        self.say(f"The Blackglass corpse-salt ring bites {target.name} for {self.style_damage(actual)} necrotic damage.")

    def varyn_spell_dc(self, varyn) -> int:
        return max(14, 8 + varyn.proficiency_bonus + varyn.ability_mod("CHA"))

    def handle_varyn_spell_clock(self, encounter, heroes, enemies, round_number: int) -> None:
        if not self.is_varyn_sable_encounter(encounter):
            return
        varyn = self.find_varyn_sable(enemies)
        if varyn is None or not varyn.is_conscious() or self.is_incapacitated(varyn) or not self.can_make_hostile_action(varyn):
            return
        if (round_number - 1) % 4 != 0:
            return
        if varyn.bond_flags.get("sable_spell_round") == round_number:
            return
        varyn.bond_flags["sable_spell_round"] = round_number
        self.varyn_cast_black_ledger_edict(varyn, heroes)
        if any(hero.is_conscious() for hero in heroes):
            self.varyn_cast_ashen_knife_storm(varyn, heroes)

    def varyn_cast_black_ledger_edict(self, varyn, heroes) -> None:
        conscious_heroes = [hero for hero in heroes if hero.is_conscious()]
        if not conscious_heroes:
            return
        target = max(conscious_heroes, key=self.combat_damage_pressure_score)
        dc = self.varyn_spell_dc(varyn)
        self.say(f"{varyn.name} snaps open a black ledger page and reads {target.name}'s next mistake aloud.")
        if not self.saving_throw(target, "WIS", dc, context=f"against {varyn.name}'s Black Ledger Edict"):
            self.apply_status(target, "marked", 2, source=f"{varyn.name}'s Black Ledger Edict")
            self.apply_status(target, "incapacitated", 1, source=f"{varyn.name}'s Black Ledger Edict")
        else:
            self.apply_status(target, "marked", 1, source=f"{varyn.name}'s Black Ledger Edict")
            self.say(f"{target.name} keeps moving, but the ledger still leaves a bright cut of attention on them.")

    def varyn_cast_ashen_knife_storm(self, varyn, heroes) -> None:
        conscious_heroes = [hero for hero in heroes if hero.is_conscious()]
        if not conscious_heroes:
            return
        dc = self.varyn_spell_dc(varyn)
        targets = sorted(conscious_heroes, key=lambda hero: (hero.current_hp, hero.armor_class, hero.save_bonus("DEX")))[:2]
        self.say(f"{varyn.name} flicks two fingers, and ash-thin knives cross the chamber on impossible lines.")
        for target in targets:
            damage_roll = self.roll_with_display_bonus(
                "2d5+3",
                style="damage",
                context_label=f"{varyn.name}'s Ashen Knife Storm",
                outcome_kind="damage",
            )
            if self.saving_throw(target, "DEX", dc, context=f"against {varyn.name}'s Ashen Knife Storm"):
                actual = self.apply_damage(target, max(1, damage_roll.total // 2), damage_type="slashing")
                self.say(f"{target.name} twists through the worst of the knives but still takes {self.style_damage(actual)} damage.")
            else:
                actual = self.apply_damage(target, damage_roll.total, damage_type="slashing")
                self.say(f"The knife storm opens a line across {target.name} for {self.style_damage(actual)} damage.")
                if target.is_conscious():
                    self.apply_status(target, "reeling", 1, source=f"{varyn.name}'s Ashen Knife Storm")
            self.announce_downed_target(target)

    def ashfall_basin_alarm_is_suppressed(self) -> bool:
        if self.state is None:
            return False
        if self.state.flags.get("ashfall_signal_basin_cleanly_snuffed"):
            return True
        return bool(self.state.flags.get("ashfall_signal_basin_silenced") and not self.state.flags.get("ashfall_signal_basin_noisy"))

    def handle_ashfall_alarm_clock(self, encounter, enemies, initiative, round_number: int) -> None:
        if not self.is_ashfall_alarm_encounter(encounter) or round_number != 3:
            return
        if self.ashfall_basin_alarm_is_suppressed() or not enemies:
            return
        if any(enemy.bond_flags.get("ashfall_alarm_clock_triggered") for enemy in enemies):
            return
        enemies[0].bond_flags["ashfall_alarm_clock_triggered"] = True
        conscious_enemies = [enemy for enemy in enemies if enemy.is_conscious()]
        if len(conscious_enemies) <= 3:
            reinforcement = create_enemy("bandit", name="Ashfall Alarm Runner")
            reinforcement.notes.append("Pulled in by the unsnuffed Ashfall signal basin.")
            enemies.append(reinforcement)
            initiative.append(reinforcement)
            self.say("The signal basin coughs out a hard red flare, and an Ashfall Alarm Runner barrels into the line.")
        else:
            self.say("The signal basin answers with a red flare, and the Ashfall line surges behind it.")
            for enemy in conscious_enemies:
                self.apply_status(enemy, "emboldened", 1, source="the Ashfall alarm basin")

    def first_living_melee_enemy(self, enemies) -> Any | None:
        return next((enemy for enemy in enemies if enemy.is_conscious() and not getattr(enemy.weapon, "ranged", False)), None)

    def handle_ashfall_barracks_shield_line(self, encounter, enemies) -> None:
        if not self.is_ashfall_barracks_encounter(encounter):
            return
        shield_bearer = next(
            (enemy for enemy in enemies if enemy.is_conscious() and enemy.bond_flags.get("barracks_shield_bearer")),
            None,
        )
        if shield_bearer is None and not any(enemy.bond_flags.get("barracks_shield_bearer") for enemy in enemies):
            shield_bearer = self.first_living_melee_enemy(enemies)
            if shield_bearer is not None:
                shield_bearer.bond_flags["barracks_shield_bearer"] = True
                self.say(f"{shield_bearer.name} locks the barracks shield line and forces the party to break the front first.")
        if shield_bearer is None or not shield_bearer.is_conscious():
            return
        for ally in enemies:
            if ally is not shield_bearer and ally.is_conscious():
                self.apply_status(ally, "guarded", 1, source=f"{shield_bearer.name}'s shield line")

    def handle_rukhar_command_aura(self, encounter, enemies, round_number: int) -> None:
        if not self.is_rukhar_cinderfang_encounter(encounter):
            return
        rukhar = self.find_rukhar_cinderfang(enemies)
        if rukhar is None or not rukhar.is_conscious() or rukhar.current_hp * 2 <= rukhar.max_hp:
            return
        allies = [enemy for enemy in enemies if enemy is not rukhar and enemy.is_conscious()]
        if not allies:
            return
        target = max(allies, key=lambda ally: (ally.attack_bonus(), ally.current_hp))
        if round_number % 2:
            self.apply_status(target, "emboldened", 1, source=f"{rukhar.name}'s command aura")
            self.say(f"{rukhar.name} cuts one sharp order through the smoke, and {target.name} surges to answer it.")
        else:
            self.apply_status(target, "attack_pressure", 1, source=f"{rukhar.name}'s command aura")
            self.say(f"{rukhar.name} points {target.name} into the party's weakest angle.")

    def handle_cistern_eye_secret_tax(self, encounter, heroes, enemies, round_number: int) -> None:
        if not self.is_tresendar_cistern_eye_encounter(encounter) or round_number != 2:
            return
        if self.state is not None and self.state.flags.get("tresendar_eye_read"):
            return
        eye = self.find_cistern_eye(enemies)
        if eye is None or not eye.is_conscious() or eye.bond_flags.get("secret_tax_triggered"):
            return
        conscious_heroes = [hero for hero in heroes if hero.is_conscious()]
        if not conscious_heroes:
            return
        eye.bond_flags["secret_tax_triggered"] = True
        target = min(conscious_heroes, key=lambda hero: (hero.save_bonus("WIS"), hero.skill_bonus("Insight"), hero.current_hp))
        self.say(f"The Cistern Eye finds the softest unguarded thought in the party and speaks it in {target.name}'s voice.")
        if not self.saving_throw(target, "WIS", 13, context="against the Cistern Eye's secret tax"):
            self.apply_status(target, "reeling", 2, source="the Cistern Eye's secret tax")
        else:
            actual = self.apply_damage(
                target,
                self.roll_with_display_bonus(
                    "1d6",
                    style="damage",
                    context_label="Cistern Eye secret tax",
                    outcome_kind="damage",
                ).total,
                damage_type="psychic",
            )
            self.say(f"{target.name} keeps the secret closed, but the effort costs {self.style_damage(actual)} psychic damage.")
            self.announce_downed_target(target)

    def tresendar_cleared_room_count(self) -> int:
        if self.state is None or self.state.current_scene != "tresendar_manor":
            return 0
        self._sync_map_state_with_scene()
        payload = self._map_state_payload()
        cleared_rooms = set(payload["cleared_rooms"])
        dungeon_id = payload.get("current_dungeon_id")
        if dungeon_id == "tresendar_undercellars":
            dungeon = ACT1_HYBRID_MAP.dungeons[dungeon_id]
            return sum(1 for room_id in cleared_rooms if room_id in dungeon.rooms)
        return sum(
            1
            for flag_name in (
                "tresendar_stair_found",
                "tresendar_intake_cleared",
                "tresendar_cistern_found",
                "tresendar_records_secured",
                "tresendar_cleared",
            )
            if self.state.flags.get(flag_name)
        )

    def handle_tresendar_cellar_alarm_chain(self, encounter, enemies, initiative, round_number: int) -> None:
        if not self.is_tresendar_cellar_encounter(encounter) or round_number != 3:
            return
        if self.state is None or not self.state.flags.get("tresendar_entry_approach_failed"):
            return
        marker = enemies[0] if enemies else None
        if marker is None or marker.bond_flags.get("tresendar_cellar_alarm_chain_triggered"):
            return
        marker.bond_flags["tresendar_cellar_alarm_chain_triggered"] = True
        archer = create_enemy("bandit_archer", name="Records Passage Cutout")
        archer.notes.append("Arrived from the cage-store records passage after the entry alarm carried.")
        enemies.append(archer)
        initiative.append(archer)
        self.say("The failed entry finally pays off for the Ashen Brand: a cutout archer slides in from the records passage.")

    def handle_tresendar_manor_collapse_timer(self, encounter, heroes, enemies, round_number: int) -> None:
        if not self.is_tresendar_manor_encounter(encounter) or round_number != 3:
            return
        if self.tresendar_cleared_room_count() < 2:
            return
        marker = next((enemy for enemy in enemies if enemy.is_conscious()), None)
        if marker is None or marker.bond_flags.get("tresendar_collapse_timer_triggered"):
            return
        marker.bond_flags["tresendar_collapse_timer_triggered"] = True
        targets = []
        conscious_heroes = [hero for hero in heroes if hero.is_conscious()]
        conscious_enemies = [enemy for enemy in enemies if enemy.is_conscious()]
        if conscious_heroes:
            targets.append(self.rng.choice(conscious_heroes))
        if conscious_enemies:
            targets.append(self.rng.choice(conscious_enemies))
        if not targets:
            return
        self.say("Duskmere's old bones start losing the argument with the fight. Stone breaks loose from the ceiling.")
        for target in targets:
            self.resolve_tresendar_falling_stone(target)

    def resolve_tresendar_falling_stone(self, target) -> None:
        if self.saving_throw(target, "DEX", 12, context="against Duskmere's falling stones"):
            self.say(f"{target.name} twists clear before the ceiling finds them.")
            return
        actual = self.apply_damage(
            target,
            self.roll_with_display_bonus(
                "1d4",
                style="damage",
                context_label="Duskmere collapse",
                outcome_kind="damage",
            ).total,
            damage_type="bludgeoning",
        )
        if target.is_conscious():
            status = self.rng.choice(("prone", "reeling"))
            self.apply_status(target, status, 1, source="falling stone from Duskmere's collapse")
        self.say(f"{target.name} is clipped by falling stone for {self.style_damage(actual)} bludgeoning damage.")
        self.announce_downed_target(target)

    def handle_cistern_eye_secret_hunger(self, encounter, heroes, enemies, round_number: int) -> None:
        if not self.is_tresendar_cistern_eye_encounter(encounter) or round_number % 3 != 0:
            return
        eye = self.find_cistern_eye(enemies)
        if eye is None or not eye.is_conscious() or eye.bond_flags.get("secret_hunger_round") == round_number:
            return
        conscious_heroes = [hero for hero in heroes if hero.is_conscious()]
        if not conscious_heroes:
            return
        eye.bond_flags["secret_hunger_round"] = round_number
        target = min(conscious_heroes, key=lambda hero: (hero.current_hp, hero.max_hp))
        self.say(f"The Cistern Eye smells the thinnest pulse in the room and bites down on {target.name}'s hidden fear.")
        actual = self.apply_damage(
            target,
            self.roll_with_display_bonus(
                "1d6",
                style="damage",
                context_label="Cistern Eye secret hunger",
                outcome_kind="damage",
            ).total,
            damage_type="psychic",
        )
        self.say(f"{target.name} suffers {self.style_damage(actual)} psychic damage from the Eye's secret hunger.")
        self.announce_downed_target(target)

    def harmful_combat_statuses(self) -> set[str]:
        return {
            "acid",
            "bleeding",
            "blinded",
            "burning",
            "charmed",
            "cursed",
            "deafened",
            "exhaustion",
            "frightened",
            "grappled",
            "incapacitated",
            "marked",
            "paralyzed",
            "petrified",
            "poisoned",
            "prone",
            "reeling",
            "restrained",
            "stunned",
            "unconscious",
        }

    def clear_harmful_combat_statuses(self, actor) -> int:
        removed = 0
        for status in list(actor.conditions):
            if status in self.harmful_combat_statuses():
                actor.conditions.pop(status, None)
                removed += 1
        return removed

    def after_actor_damaged(self, target, *, previous_hp: int, damage: int, damage_type: str = "") -> None:
        encounter = getattr(self, "_active_encounter", None)
        self.handle_vaelith_bloodied_ward(encounter, target, previous_hp)
        self.handle_varyn_bloodied_reposition(encounter, target, previous_hp)
        self.handle_rukhar_bloodied_order(encounter, target, previous_hp)
        self.clear_barracks_shield_line_if_bearer_downed(encounter, target)
        self.handle_claimbinder_objection_break(target)

    def handle_vaelith_bloodied_ward(self, encounter, target, previous_hp: int) -> None:
        if not self.is_old_owl_vaelith_encounter(encounter):
            return
        if getattr(target, "archetype", "") != "vaelith_marr":
            return
        if target.bond_flags.get("grave_ward_triggered"):
            return
        if previous_hp * 2 < target.max_hp or target.current_hp <= 0 or target.current_hp * 2 >= target.max_hp:
            return

        target.bond_flags["grave_ward_triggered"] = True
        ward_hp = self.rng.randint(6, 8)
        target.grant_temp_hp(ward_hp)
        self.say(
            f"Blood darkens Vaelith's sleeve, and the well answers with a grave ward worth "
            f"{self.style_healing(ward_hp)} temporary hit points."
        )
        heroes = [hero for hero in getattr(self, "_active_combat_heroes", []) if hero.is_conscious()]
        if not heroes:
            return
        target_hero = max(heroes, key=self.old_owl_damage_pressure_score)
        if not self.saving_throw(target_hero, "WIS", 13, context=f"against {target.name}'s grave ward"):
            self.apply_status(target_hero, "frightened", 1, source=f"{target.name}'s grave ward")
        else:
            self.say(f"{target_hero.name} holds their nerve as the grave ward reaches for the party's sharpest blade.")

    def handle_varyn_bloodied_reposition(self, encounter, target, previous_hp: int) -> None:
        if not self.is_varyn_sable_encounter(encounter):
            return
        if getattr(target, "archetype", "") != "varyn":
            return
        if target.bond_flags.get("sable_reposition_triggered"):
            return
        if previous_hp * 2 <= target.max_hp or target.current_hp <= 0 or target.current_hp * 2 > target.max_hp:
            return
        target.bond_flags["sable_reposition_triggered"] = True
        removed = self.clear_harmful_combat_statuses(target)
        self.apply_status(target, "invisible", 1, source=f"{target.name}'s reserve route")
        if removed:
            self.say(f"{target.name} sheds every bad angle the party pinned on him and vanishes into the support line.")
        else:
            self.say(f"{target.name} breaks the line at the exact moment blood touches his glove and vanishes behind his support.")
        supports = [
            enemy
            for enemy in getattr(self, "_active_combat_enemies", [])
            if enemy is not target and enemy.is_conscious()
        ]
        for support in supports:
            self.apply_status(support, "guarded", 2, source=f"{target.name}'s reposition order")
            self.apply_status(support, "emboldened", 1, source=f"{target.name}'s reposition order")
        if supports:
            self.say("The remaining support closes ranks, buying Varyn the breath he needs to reset the fight.")

    def handle_rukhar_bloodied_order(self, encounter, target, previous_hp: int) -> None:
        if not self.is_rukhar_cinderfang_encounter(encounter):
            return
        if getattr(target, "archetype", "") != "rukhar":
            return
        heroes = [hero for hero in getattr(self, "_active_combat_heroes", []) if hero.is_conscious()]
        if target.current_hp <= 0:
            for hero in heroes:
                if hero.bond_flags.pop("marked_by_rukhar", None):
                    self.clear_status(hero, "marked")
            return
        if target.bond_flags.get("break_their_line_triggered"):
            return
        if previous_hp * 2 <= target.max_hp or target.current_hp * 2 > target.max_hp:
            return
        target.bond_flags["break_their_line_triggered"] = True
        if not heroes:
            return
        marked = max(heroes, key=self.combat_damage_pressure_score)
        marked.bond_flags["marked_by_rukhar"] = True
        target.bond_flags["marked_target"] = marked.name
        self.say(f"{target.name} snaps the order: Break their line. Every blade in the court starts hunting {marked.name}.")
        self.apply_status(marked, "marked", -1, source=f"{target.name}'s Break Their Line")

    def clear_barracks_shield_line_if_bearer_downed(self, encounter, target) -> None:
        if not self.is_ashfall_barracks_encounter(encounter):
            return
        if not target.bond_flags.get("barracks_shield_bearer") or target.is_conscious():
            return
        for enemy in getattr(self, "_active_combat_enemies", []):
            if enemy is not target:
                self.clear_status(enemy, "guarded")
        self.say(f"{target.name}'s shield line collapses, and the barracks formation finally opens.")

    def handle_claimbinder_objection_break(self, target) -> None:
        if getattr(target, "archetype", "") != "claimbinder_notary":
            return
        marked_name = str(target.bond_flags.pop("objection_target", "")).strip()
        if not marked_name:
            return
        heroes = list(getattr(self, "_active_combat_heroes", []))
        marked_hero = next((hero for hero in heroes if hero.name == marked_name), None)
        if marked_hero is None or not marked_hero.bond_flags.pop("marked_by_claimbinder", None):
            return
        self.clear_status(marked_hero, "marked")
        self.say(f"{target.name}'s objection collapses the instant the notary is hit, and {marked_hero.name} drops off the filed target list.")

    def combat_damage_pressure_score(self, hero) -> tuple[int, int, int]:
        class_pressure = {
            "Barbarian": 4,
            "Cleric": 2,
            "Fighter": 3,
            "Paladin": 3,
            "Rogue": 3,
            "Ranger": 2,
            "Monk": 2,
            "Warlock": 2,
            "Sorcerer": 2,
            "Wizard": 2,
        }.get(getattr(hero, "class_name", ""), 0)
        return (hero.attack_bonus() + hero.damage_bonus() + class_pressure, hero.level, hero.current_hp)

    def old_owl_damage_pressure_score(self, hero) -> tuple[int, int, int]:
        return self.combat_damage_pressure_score(hero)

    def _old_owl_gravecaller_lip(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say(
            "A hooded gravecaller rises from the well mouth itself, one hand blackened to the wrist by ritual soot. Their voice is calm in the way only committed fools and true fanatics manage."
        )
        self.speaker(
            "Vaelith Marr",
            "You are late. The dead were almost ready to remember who owned this land before your little town learned to squat on it.",
        )
        party_size = self.act1_party_size()
        boss_enemies = [create_enemy("vaelith_marr")]
        if party_size >= 2:
            boss_enemies.append(create_enemy("carrion_lash_crawler"))
        if party_size >= 4:
            boss_enemies.append(self.act1_pick_enemy(("skeletal_sentry", "graveblade_wight", "lantern_fen_wisp")))
        boss_enemies.append(create_enemy("skeletal_sentry", name="Corpse-Salt Sentry"))
        if not (self.state.flags.get("old_owl_prospector_rescued") or self.state.flags.get("old_owl_notes_found")):
            boss_enemies.append(create_enemy("skeletal_sentry", name="Gravecalled Sentry"))
            self.say("With no rescued witness or preserved notes to spoil the cadence, one more dead sentry rises beside the well.")
        boss_bonus = int(self.state.flags.get("old_owl_prospector_rescued", False)) + int(self.state.flags.get("old_owl_notes_found", False))
        if self.state.flags.get("old_owl_ritual_sabotaged"):
            boss_enemies[0].current_hp = max(1, boss_enemies[0].current_hp - 4)
            self.apply_status(boss_enemies[0], "reeling", 1, source="the sabotaged dig-ring")
            self.say("The broken ritual ring is still fighting Vaelith's control, and the gravecaller feels it.")
        if self.state.flags.get("old_owl_sentry_picked") and len(boss_enemies) > 1:
            picked_guard = boss_enemies.pop()
            self.say(f"{picked_guard.name} never reaches the well lip. Your earlier sentry kill left the gravecaller short one answer to the alarm.")
        if self.state.flags.get("old_owl_deeper_infiltration"):
            boss_bonus += 1
        choice = self.scenario_choice(
            "How do you answer the gravecaller?",
            [
                self.quoted_option("RELIGION", "These dead are not yours to command. Let them go."),
                self.quoted_option("INTIMIDATION", "You are finished here. Step away from the well and survive it."),
                self.action_option("Rush the ritual line before another corpse can stand."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_speaker("These dead are not yours to command. Let them go.")
            success = self.skill_check(self.state.player, "Religion", 13, context="to break the gravecaller's hold on the risen dead")
            if success:
                if len(boss_enemies) > 1:
                    self.apply_status(boss_enemies[1], "frightened", 2, source="your command over the dead")
                self.apply_status(boss_enemies[0], "reeling", 1, source="a broken ritual cadence")
                self.say("For one sharp moment the dead hesitate as if something older than Vaelith has finally been heard.")
            else:
                self.say("The words are right. The gravecaller simply believes the wrong thing harder.")
        elif choice == 2:
            self.player_speaker("You are finished here. Step away from the well and survive it.")
            success = self.skill_check(self.state.player, "Intimidation", 13, context="to crack the gravecaller's composure")
            if success:
                boss_enemies[0].current_hp = max(1, boss_enemies[0].current_hp - 4)
                self.apply_status(boss_enemies[0], "frightened", 1, source="your iron-edged demand")
                self.say("Vaelith gives ground almost without meaning to, and the dead feel the break in confidence.")
            else:
                self.apply_status(boss_enemies[0], "emboldened", 2, source="your failed threat")
                self.speaker("Vaelith Marr", "You speak like the living have ever held a thing permanently.")
        else:
            self.player_action("Rush the ritual line before another corpse can stand.")
            boss_enemies[0].current_hp = max(1, boss_enemies[0].current_hp - 3)
            boss_bonus += 2
            self.say("You break the distance fast enough to make the first exchange happen inside Vaelith's own ward-ring.")

        outcome = self.run_encounter(
            Encounter(
                title="Miniboss: Vaelith Marr",
                description="The gravecaller of Blackglass Well fights from the lip of the buried dark.",
                enemies=boss_enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=boss_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The well's corpse-lights burn on above the fallen party.")
            return
        if outcome == "fled":
            self.return_to_phandalin("You break contact and retreat to Iron Hollow with the well still active behind you.")
            return

        self.act1_adjust_metric("act1_ashen_strength", -1)
        self.complete_map_room(dungeon, room.room_id)
        self.add_clue("Blackglass Well is cleared, and its notes tie grave-salvage, Ashfall Watch, and the manor hill into one supply chain.")
        self.add_journal("You silenced Blackglass Well and broke one of the Ashen Brand's outer operations.")
        self.refresh_quest_statuses(announce=False)
        self.add_inventory_item("scroll_lesser_restoration", source="Vaelith's ritual satchel")
        self.return_to_phandalin("Blackglass Well falls quiet behind you as the road back to Iron Hollow opens again.")

    def _wyvern_goat_path(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        if not self.state.flags.get("wyvern_tor_seen"):
            self.say(
                "Red Mesa Hold looms out of the hills in broken shelves of wind-cut stone. Goat paths, old watch cairns, and smoke-stained hollows twist around the ridge, "
                "and something large has been pacing the high ground long enough to turn the dust into habitual scars.",
                typed=True,
            )
            self.state.flags["wyvern_tor_seen"] = True
        party_size = self.act1_party_size()
        enemies = [create_enemy("orc_raider"), create_enemy("worg")]
        if party_size >= 3:
            enemies.append(self.act1_pick_enemy(("orc_raider", "bugbear_reaver", "acidmaw_burrower", "cliff_harpy")))
        hero_bonus = self.apply_scene_companion_support("wyvern_tor")
        choice = self.scenario_choice(
            "How do you take the outer shelf?",
            [
                self.skill_tag("SURVIVAL", self.action_option("Use the goat path and the wind shadow to reach the upper shelf.")),
                self.skill_tag("STEALTH", self.action_option("Shadow the smoke line and hit the pickets first.")),
                self.quoted_option("NATURE", "The worg pack is the key. Let me read where it expects prey to run."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Use the goat path and the wind shadow to reach the upper shelf.")
            success = self.skill_check(self.state.player, "Survival", 13, context="to take the hidden path up Red Mesa Hold")
            if success:
                self.apply_status(enemies[0], "surprised", 1, source="your high approach")
                hero_bonus += 2
                self.say("You come out above the outer camp instead of below it, which changes the whole feel of the fight.")
            else:
                self.say("The path is real, but not as forgiving as the goats make it look.")
        elif choice == 2:
            self.player_action("Shadow the smoke line and hit the pickets first.")
            success = self.skill_check(self.state.player, "Stealth", 13, context="to get onto the shelf before the pickets spot you")
            if success:
                enemies[-1].current_hp = max(1, enemies[-1].current_hp - 4)
                self.apply_status(enemies[-1], "reeling", 1, source="your opening strike")
                hero_bonus += 1
                self.say("The closest lookout goes down hard enough that the alarm comes late and ugly.")
            else:
                self.apply_status(self.state.player, "reeling", 1, source="gravel underfoot")
                self.say("Loose scree gives you away and the shelf erupts into motion.")
        else:
            self.player_speaker("The worg pack is the key. Let me read where it expects prey to run.")
            success = self.skill_check(self.state.player, "Nature", 13, context="to predict the worg's line of attack")
            if success:
                self.apply_status(enemies[1], "frightened", 1, source="your perfect read of its momentum")
                hero_bonus += 1
                self.say("You move before the beast commits, which steals its best rush cleanly away.")
            else:
                self.say("You read enough to know the worg is clever, not enough to stop it from choosing the angle first.")

        outcome = self.run_encounter(
            Encounter(
                title="Red Mesa Hold Shelf Fight",
                description="Orc raiders and a hunting worg defend the tor's outer shelf.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("Red Mesa Hold keeps the high ground and the road below it.")
            return
        if outcome == "fled":
            self.return_to_phandalin("You break away from the tor and retreat before the shelf turns into a killing bowl.")
            return

        self.complete_map_room(dungeon, room.room_id)
        self.say("The outer shelf breaks. One hollow holds a terrified drover; another ledge keeps a half-defaced cairn shrine and the raiders' beast tethers.")

    def _wyvern_drover_hollow(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("A captured drover is bound in the hollow, bruised but still watching the upper shelf with desperate focus.")
        choice = self.scenario_choice(
            "How do you handle the drover?",
            [
                self.quoted_option("MEDICINE", "Get the drover breathing right and find out how many are still above us."),
                self.quoted_option("INSIGHT", "Tell me what the chief values enough to guard this hard."),
                self.action_option("Cut them loose, arm them, and send them downslope before the chief arrives."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_speaker("Get the drover breathing right and find out how many are still above us.")
            success = self.skill_check(self.state.player, "Medicine", 12, context="to steady the captured drover before shock takes over")
            if success:
                self.say("The drover coughs out one clean answer: a blood-chief named Brughor, one ogre, and enough ego to think the hill already belongs to him.")
                self.add_clue("A captured drover confirms Brughor holds Red Mesa Hold with an ogre and a small disciplined raiding party.")
                self.reward_party(xp=10, reason="saving the captured drover at Red Mesa Hold")
            else:
                self.say("The drover lives, but the useful details come back in broken pieces.")
        elif choice == 2:
            self.player_speaker("Tell me what the chief values enough to guard this hard.")
            success = self.skill_check(self.state.player, "Insight", 12, context="to read the chief through a terrified witness")
            if success:
                self.say("The drover points toward Brughor's pride more than his supplies, which makes the coming challenge easier to shape.")
                self.add_clue("Brughor cares more about holding the high shelf in sight of his crew than about any one crate or beast.")
                self.reward_party(xp=10, reason="reading Brughor through the drover")
            else:
                self.say("You get fear, blood, and smoke, but not the clean edge of an answer.")
        else:
            self.player_action("Cut them loose, arm them, and send them downslope before the chief arrives.")
            self.say("The drover staggers away with a stolen knife and a promise to tell Iron Hollow exactly what waits on this hill.")

        self.act1_adjust_metric("act1_survivors_saved", 1)
        self.act1_adjust_metric("act1_town_fear", -1)
        followup = self.scenario_choice(
            "With the drover free, what do you ask of them next?",
            [
                self.action_option("Send them hard for town with the cleanest warning they can carry."),
                self.action_option("Keep them hidden below the shelf to signal when Brughor commits his line."),
                self.action_option("Have them loose the remaining beasts uphill and turn the camp against itself."),
            ],
            allow_meta=False,
        )
        if followup == 1:
            self.player_action("Send them hard for town with the cleanest warning they can carry.")
            self.say("The drover leaves fast, taking one true account of Red Mesa Hold back toward people who still have time to listen.")
        elif followup == 2:
            self.player_action("Keep them hidden below the shelf to signal when Brughor commits his line.")
            self.state.flags["wyvern_spotter_signal"] = True
            self.say("The drover slips into a crack in the rock with a shepherd's whistle and a look that promises they will use it at the exact right second.")
        else:
            self.player_action("Have them loose the remaining beasts uphill and turn the camp against itself.")
            self.state.flags["wyvern_beast_stampede"] = True
            self.say("A moment later the upper shelf erupts in bells, hooves, and furious shouting as the pack animals tear through the camp line.")
        self.add_clue("The rescued drover heard raiders talk about Cinderfall, an abandoned relay they used to keep Ashfall supplied off the main road.")
        self.state.flags["varyn_detour_logic_seen"] = True
        self.unlock_act1_hidden_route(
            "The freed drover points you toward Cinderfall Ruins, a hidden relay route the raiders still use when Ashfall needs reserve supplies unseen."
        )
        self.complete_map_room(dungeon, room.room_id)

    def _wyvern_shrine_ledge(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("A cairn shrine to Tempus leans in the wind beside the raiders' remaining tethers and a scatter of stolen tack.")
        rhogar = self.active_companion_by_id("rhogar_valeguard", minimum_disposition=6)
        options = [
            self.quoted_option("RELIGION", "Set the cairn shrine right. I want the chief fighting under a bad sign."),
            self.action_option("Cut the pack tethers and send the remaining beasts into the upper camp."),
            self.action_option("Strip the tack, ruin the tethers, and leave the ledge empty."),
        ]
        if rhogar is not None:
            options.append(self.action_option("Let Rhogar reset the cairn and call the hill to witness against Brughor."))
        choice = self.scenario_choice(
            "What do you do on the ledge?",
            options,
            allow_meta=False,
        )
        if choice == 1:
            self.player_speaker("Set the cairn shrine right. I want the chief fighting under a bad sign.")
            success = self.skill_check(self.state.player, "Religion", 12, context="to restore the cairn shrine enough to unsettle the raiders")
            if success:
                self.apply_status(self.state.player, "blessed", 2, source="the restored cairn shrine")
                self.say("You set the cairn stones true again, and the hill stops feeling entirely like theirs.")
                self.reward_party(xp=10, reason="restoring the shrine on Red Mesa Hold")
            else:
                self.say("You do what you can with the broken shrine, but the best of the omen slips through your fingers.")
        elif choice == 2:
            self.player_action("Cut the pack tethers and send the remaining beasts into the upper camp.")
            self.say("Goats and half-starved pack animals scatter uphill in a chaos of bells and hooves, dragging the upper camp's attention sideways.")
        elif choice == 3:
            self.player_action("Strip the tack, ruin the tethers, and leave the ledge empty.")
            self.say("You leave the ledge useless as a staging point and deny the upper shelf one more clean response.")
        else:
            self.player_action("Let Rhogar reset the cairn and call the hill to witness against Brughor.")
            self.apply_status(self.state.player, "blessed", 2, source="Rhogar's shrine oath")
            self.state.flags["wyvern_rhogar_omen"] = True
            self.say("Rhogar rights the cairn with soldier-care and speaks one short oath into the wind. Even the raiders' ledge feels less owned after that.")

        self.complete_map_room(dungeon, room.room_id)

    def _wyvern_high_shelf(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say(
            "A broad-shouldered orc in scavenged scale laughs once as he comes down from the upper shelf, great axe low in one hand and old blood drying on his bracers. "
            "An ogre lumbers after him, dragging a club over stone."
        )
        self.speaker("Brughor Skullcleaver", "Good. I was getting tired of prey that ran downhill.")
        party_size = self.act1_party_size()
        boss_enemies = [create_enemy("orc_bloodchief", name="Brughor Skullcleaver")]
        if party_size >= 2:
            boss_enemies.append(self.act1_pick_enemy(("ogre_brute", "ettervine_webherd")))
        if party_size >= 4:
            boss_enemies.append(self.act1_pick_enemy(("orc_raider", "bugbear_reaver")))
        boss_bonus = int(self.state.flags.get("wyvern_drover_rescued", False)) + int(self.state.flags.get("wyvern_shrine_secured", False))
        if self.state.flags.get("wyvern_spotter_signal"):
            boss_bonus += 1
            self.say("A sharp whistle from below the shelf warns you exactly when Brughor commits his weight forward.")
        if self.state.flags.get("wyvern_beast_stampede") and len(boss_enemies) > 1:
            self.apply_status(boss_enemies[1], "surprised", 1, source="the stampede ripping through the shelf")
            boss_enemies[1].current_hp = max(1, boss_enemies[1].current_hp - 4)
            self.say("The camp stampede tears across the high shelf first, leaving Brughor's support line scrambling to regain itself.")
        if self.state.flags.get("wyvern_rhogar_omen"):
            boss_enemies[0].current_hp = max(1, boss_enemies[0].current_hp - 2)
        choice = self.scenario_choice(
            "How do you answer the blood-chief?",
            [
                self.quoted_option("INTIMIDATION", "You picked the wrong town to stalk."),
                self.quoted_option("ATHLETICS", "Then come down the rest of the way and see how long you stand."),
                self.action_option("Hit the chief before the ogre can settle into the fight."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_speaker("You picked the wrong town to stalk.")
            success = self.skill_check(self.state.player, "Intimidation", 13, context="to meet Brughor's violence with greater certainty")
            if success:
                boss_enemies[0].current_hp = max(1, boss_enemies[0].current_hp - 4)
                self.apply_status(boss_enemies[0], "frightened", 1, source="your refusal to yield ground")
                self.say("Brughor's grin slips for a heartbeat, and the hill feels smaller around him.")
            else:
                self.apply_status(boss_enemies[0], "emboldened", 2, source="your challenge feeding his pride")
                self.speaker("Brughor Skullcleaver", "Better. Fearless prey usually swings harder.")
        elif choice == 2:
            self.player_speaker("Then come down the rest of the way and see how long you stand.")
            success = self.skill_check(self.state.player, "Athletics", 13, context="to own the footing and force the chief into your timing")
            if success:
                self.apply_status(self.state.player, "emboldened", 2, source="holding the shelf against Brughor's rush")
                boss_bonus += 1
                self.say("You take the rock shelf like a shield line, and Brughor has to meet you on terms he did not choose.")
            else:
                self.say("The footing is uglier than your confidence suggested, and the chief sees it.")
        else:
            self.player_action("Hit the chief before the ogre can settle into the fight.")
            boss_enemies[0].current_hp = max(1, boss_enemies[0].current_hp - 3)
            boss_bonus += 2
            self.say("You crash into the upper shelf before the whole enemy line can come together cleanly.")

        outcome = self.run_encounter(
            Encounter(
                title="Miniboss: Brughor Skullcleaver",
                description="The blood-chief of Red Mesa Hold makes his stand on the broken high shelf.",
                enemies=boss_enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=boss_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("Brughor leaves the hill red and the road below it empty.")
            return
        if outcome == "fled":
            self.return_to_phandalin("You pull clear of the upper shelf and retreat to Iron Hollow to regroup.")
            return

        self.act1_adjust_metric("act1_ashen_strength", -1)
        self.complete_map_room(dungeon, room.room_id)
        self.add_clue("Red Mesa Hold is cleared, and its raiders were coordinating with Ashfall Watch rather than acting alone.")
        self.add_journal("You broke the raiders at Red Mesa Hold and stripped another outer shield away from the Ashen Brand.")
        self.refresh_quest_statuses(announce=False)
        self.add_inventory_item("greater_healing_draught", source="Brughor's travel chest")
        self.return_to_phandalin("Red Mesa Hold falls behind you as the ridge wind finally goes clean.")

    def _cinderfall_collapsed_gate(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say(
            "Cinderfall Ruins crouch around a half-buried relay road: a collapsed gatehouse, a burned chapel, and broken store sheds still feeding one stubborn ember node deeper in.",
            typed=True,
        )
        party_size = self.act1_party_size()
        enemies = [create_enemy("bandit", name="Relay Cutout"), create_enemy("carrion_stalker")]
        if party_size >= 3:
            enemies.append(self.act1_pick_enemy(("cinder_kobold", "ashstone_percher", "gutter_zealot")))
        hero_bonus = 0
        choice = self.scenario_choice(
            "How do you break into the relay ruin?",
            [
                self.skill_tag("STEALTH", self.action_option("Slide through the collapsed arch before the sentries settle.")),
                self.quoted_option("INVESTIGATION", "Show me the weak braces. I want the gate failing on my timing."),
                self.skill_tag("ATHLETICS", self.action_option("Rip the jammed gate wide enough that subtlety stops mattering.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Slide through the collapsed arch before the sentries settle.")
            success = self.skill_check(self.state.player, "Stealth", 13, context="to slip through the broken relay gate unseen")
            if success:
                self.apply_status(enemies[0], "surprised", 1, source="your silent breach")
                enemies[0].current_hp = max(1, enemies[0].current_hp - 3)
                hero_bonus += 2
                self.say("You are inside the ruin before the first relay runner realizes the gate already failed.")
            else:
                self.apply_status(self.state.player, "reeling", 1, source="shifting masonry")
                self.say("The broken arch gives under your boot and the ruin wakes up shouting.")
        elif choice == 2:
            self.player_speaker("Show me the weak braces. I want the gate failing on my timing.")
            success = self.skill_check(self.state.player, "Investigation", 13, context="to read the collapsed relay gate under pressure")
            if success:
                self.apply_status(enemies[-1], "reeling", 1, source="your perfectly timed breach")
                hero_bonus += 1
                self.say("You pull the right stone at the right second and the ruin's defenders lose their footing with it.")
            else:
                self.say("You find the weak point, just not before the sentries hear the search.")
        else:
            self.player_action("Rip the jammed gate wide enough that subtlety stops mattering.")
            success = self.skill_check(self.state.player, "Athletics", 13, context="to force open the collapsed relay gate")
            if success:
                self.apply_status(self.state.player, "emboldened", 2, source="bursting into Cinderfall")
                hero_bonus += 2
                self.say("The gate tears open in one ugly wrench and the relay line never gets a clean first volley.")
            else:
                self.apply_status(self.state.player, "reeling", 1, source="the collapsing hinge-stone")
                self.say("The gate gives, but not before the whole ruin hears it happen.")

        outcome = self.run_encounter(
            Encounter(
                title="Cinderfall Gate",
                description="Hidden relay sentries rush the collapsed gate to keep their reserve line alive.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("Cinderfall's hidden relay stays in enemy hands.")
            return
        if outcome == "fled":
            self.return_to_phandalin("You break away from Cinderfall before the relay line can close around you.")
            return

        self.complete_map_room(dungeon, room.room_id)
        self.say("Inside the ruin, one wing still shelters smoke-sick survivors in a chapel shell while the other holds reserve crates and route slates in a broken storehouse.")

    def _cinderfall_ash_chapel(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("A burned-out chapel still shelters two smoke-sick teamsters and a novice acolyte hiding behind fallen pews.")
        choice = self.scenario_choice(
            "How do you handle the chapel?",
            [
                self.quoted_option("MEDICINE", "Stay with me. I'll get the worst of the smoke out of your lungs first."),
                self.quoted_option("RELIGION", "The shrine still matters. Let me steady the room before we move." ),
                self.action_option("Break the rear wall wider and rush the survivors out through the ash scrub."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_speaker("Stay with me. I'll get the worst of the smoke out of your lungs first.")
            success = self.skill_check(self.state.player, "Medicine", 12, context="to stabilize the smoke-sick survivors in the chapel")
            if success:
                self.say("You get all three moving under their own power, with enough breath left to describe nightly crates bound for Ashfall Watch.")
                self.add_clue("Cinderfall's chapel survivors confirm the ruin is still feeding reserve crates toward Ashfall Watch.")
                self.reward_party(xp=10, reason="stabilizing Cinderfall's trapped survivors")
            else:
                self.say("You keep them alive and moving, even if the answers come back ragged.")
        elif choice == 2:
            self.player_speaker("The shrine still matters. Let me steady the room before we move.")
            success = self.skill_check(self.state.player, "Religion", 12, context="to calm the ash-choked chapel before moving the survivors")
            if success:
                self.apply_status(self.state.player, "blessed", 1, source="the chapel's steadied hush")
                self.say("The room stops feeling like a trap and starts feeling like an escape lane again.")
                self.add_clue("An acolyte in the chapel saw relay couriers carrying Emberhall seals through Cinderfall at dusk.")
                self.reward_party(xp=10, reason="steadying the chapel at Cinderfall")
            else:
                self.say("The prayer helps, but the escape still has to happen in a rush.")
        else:
            self.player_action("Break the rear wall wider and rush the survivors out through the ash scrub.")
            self.say("Fresh air and bad footing beat smoke and collapsing stone. You force an escape lane before the ruin can think better of it.")

        self.act1_adjust_metric("act1_survivors_saved", 2)
        self.act1_adjust_metric("act1_town_fear", -1)
        self.complete_map_room(dungeon, room.room_id)

    def _cinderfall_broken_storehouse(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("The broken storehouse still holds relay tags, burst powder sacks, and spare basin fuel lined up for a road that was never supposed to exist on paper.")
        choice = self.scenario_choice(
            "What do you do in the storehouse?",
            [
                self.quoted_option("INVESTIGATION", "Read the manifests. I want to know what Ashfall still thinks it can call on."),
                self.quoted_option("SLEIGHT OF HAND", "Tuck the powder where it will matter most once the relay starts shouting."),
                self.action_option("Kick the reserve crates open and ruin whatever they can still carry from here."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_speaker("Read the manifests. I want to know what Ashfall still thinks it can call on.")
            success = self.skill_check(self.state.player, "Investigation", 12, context="to read Cinderfall's reserve manifests before they scatter")
            if success:
                self.say("The manifests make it plain: Cinderfall is Ashfall's fallback line for fresh bowstrings, tonic crates, and ridge signal fuel.")
                self.add_clue("Cinderfall is the fallback relay feeding Ashfall's reserves, signal fuel, and emergency runners.")
                self.reward_party(xp=10, reason="reading the Cinderfall reserve manifests")
            else:
                self.say("You learn enough to know the ruin matters, just not enough to name every reserve moving through it.")
        elif choice == 2:
            self.player_speaker("Tuck the powder where it will matter most once the relay starts shouting.")
            success = self.skill_check(self.state.player, "Sleight of Hand", 12, context="to sabotage Cinderfall's reserve crates without losing the element of surprise")
            if success:
                self.say("You hide the failure inside the stockpile itself. The next hard pull on the relay will tear something important loose.")
                self.reward_party(xp=10, reason="planting a quiet sabotage line in Cinderfall's storehouse")
            else:
                self.say("You ruin some powder, but not cleanly enough to trust it as a plan all by itself.")
        else:
            self.player_action("Kick the reserve crates open and ruin whatever they can still carry from here.")
            self.say("Food tins split, powder fouls, and relay tarps go dark under ash and boot leather.")

        self.complete_map_room(dungeon, room.room_id)

    def _cinderfall_ember_relay(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say(
            "At the ruin's heart, a soot-black relay basin still glows behind broken stone while the last reserve crew tries to keep Ashfall's emergency line alive."
        )
        party_size = self.act1_party_size()
        boss_enemies = [
            create_enemy("ember_channeler", name="Ember Relay Keeper"),
            create_enemy("ash_brand_enforcer", name="Ashen Brand Runner"),
        ]
        if party_size >= 3:
            boss_enemies.append(self.act1_pick_enemy(("carrion_stalker", "cinder_kobold", "gutter_zealot", "ashstone_percher")))
        boss_bonus = int(self.state.flags.get("cinderfall_chapel_secured", False)) + int(
            self.state.flags.get("cinderfall_storehouse_searched", False)
        )
        choice = self.scenario_choice(
            "How do you hit the relay before it can warn Ashfall?",
            [
                self.skill_tag("STEALTH", self.action_option("Slip to the basin braces and cut the line before the crew settles.")),
                self.quoted_option("ARCANA", "The coals are being driven too hard. I can turn that against them."),
                self.action_option("Charge the keeper and break the relay in plain sight."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Slip to the basin braces and cut the line before the crew settles.")
            success = self.skill_check(self.state.player, "Stealth", 13, context="to sabotage the ember relay before the crew can rally")
            if success:
                self.apply_status(boss_enemies[0], "surprised", 1, source="your sabotage run")
                boss_enemies[0].current_hp = max(1, boss_enemies[0].current_hp - 4)
                boss_bonus += 1
                self.say("You cut the relay line first and the keeper spends the opening moments trying to save smoke instead of men.")
            else:
                self.say("You reach the basin, but not quietly enough to stop the crew from fighting for it.")
        elif choice == 2:
            self.player_speaker("The coals are being driven too hard. I can turn that against them.")
            success = self.skill_check(self.state.player, "Arcana", 13, context="to overload the ember relay without getting caught in it")
            if success:
                self.apply_status(boss_enemies[-1], "reeling", 2, source="the relay flaring back into the crew")
                boss_bonus += 1
                self.say("The relay spits hot ash back through its own crew and the whole defense comes apart around the basin.")
            else:
                self.say("The relay flares wrong and ugly, but not cleanly enough to ruin the defenders on its own.")
        else:
            self.player_action("Charge the keeper and break the relay in plain sight.")
            boss_enemies[0].current_hp = max(1, boss_enemies[0].current_hp - 3)
            boss_bonus += 2
            self.say("You hit the relay crew hard enough that they have to defend the basin and themselves at the same time.")

        outcome = self.run_encounter(
            Encounter(
                title="Cinderfall Ember Relay",
                description="The last reserve crew tries to keep Ashfall's hidden supply line alive.",
                enemies=boss_enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=boss_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("Cinderfall's relay burns on and Ashfall keeps its reserve line.")
            return
        if outcome == "fled":
            self.return_to_phandalin("You pull out of Cinderfall before the relay crew can pin you in the ruin.")
            return

        self.complete_map_room(dungeon, room.room_id)
        self.act1_adjust_metric("act1_ashen_strength", -1)
        self.state.flags["varyn_relay_broken"] = True
        self.add_clue("Destroying the Cinderfall relay cuts Ashfall Watch off from its reserve line and emergency signal fuel.")
        self.add_journal("You broke the hidden Cinderfall relay before the Ashfall assault.")
        self.reward_party(xp=35, gold=12, reason="breaking the Cinderfall relay")
        self.return_to_phandalin("Cinderfall goes dark behind you. Whatever waits at Ashfall will now be doing it with thinner reserves and worse timing.")

    def _ashfall_record_blue_scarf_truth(self, *, fallback: bool = False) -> None:
        assert self.state is not None
        if self.state.flags.get("ashfall_blue_scarf_truth_found"):
            if self.has_quest("find_dain_harl") and not self.state.flags.get("dain_harl_truth_found"):
                self.state.flags["dain_harl_truth_found"] = True
                self.refresh_quest_statuses(announce=False)
            return
        self.state.flags["ashfall_blue_scarf_truth_found"] = True
        knows_name = any(
            (
                self.has_quest("find_dain_harl"),
                self.quest_is_completed("find_dain_harl"),
                self.state.flags.get("stonehill_jerek_met"),
                self.state.flags.get("songs_for_missing_jerek_detail"),
            )
        )
        if fallback:
            if knows_name:
                self.say(
                    "One transfer slip catches harder than the rest: Dain Harl, road hand, dead in the prisoner disturbance. "
                    "Someone clipped a strip of blue scarf into the order as proof the body was counted."
                )
            else:
                self.say(
                    "One transfer slip has a strip of blue scarf pinned to it, proof that one east-road worker died in the prisoner disturbance."
                )
        else:
            if knows_name:
                self.say(
                    "Against the broken cage line lies a road hand in a soot-stiff blue scarf. "
                    "A freed prisoner swears Dain Harl cut two locks and shoved strangers through before the enforcers brought him down."
                )
            else:
                self.say(
                    "Against the broken cage line lies a road hand in a soot-stiff blue scarf. "
                    "A freed prisoner swears he cut two locks and shoved strangers through before the enforcers brought him down."
                )
        if knows_name:
            self.state.flags["dain_harl_truth_found"] = True
            self.add_clue("Dain Harl died at Ashfall Watch after cutting prisoners loose.")
            self.add_journal("At Ashfall Watch you confirmed Dain Harl died freeing prisoners in the yard.")
            self.refresh_quest_statuses(announce=False)
        else:
            self.add_clue("A blue-scarfed east-road worker died freeing prisoners at Ashfall Watch.")
            self.add_journal("At Ashfall Watch you found proof that one east-road worker died freeing prisoners in the yard.")

    def _ashfall_breach_gate(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say(
            "Ashfall Watch crouches over the road in layered ruin and fresh timber: a snapped tower, palisade repairs, prisoner cages, and a signal basin built to spit smoke across the hills. "
            "It is no longer just a raider den. It is a frontier choke point built on fear and scheduling.",
            typed=True,
        )
        party_size = self.act1_party_size()
        enemies = [create_enemy("bandit"), create_enemy("bandit_archer")]
        if party_size >= 3:
            enemies.append(self.act1_pick_enemy(("worg", "gutter_zealot", "rust_shell_scuttler")))
        hero_bonus = self.apply_scene_companion_support("ashfall_watch")
        choice = self.scenario_choice(
            "How do you open the assault?",
            [
                self.skill_tag("STEALTH", self.action_option("Slip up the ruin side and cut the outer line quietly.")),
                self.quoted_option("DECEPTION", "Late relief from the tor. Open up before the ridge goes black."),
                self.skill_tag("ATHLETICS", self.action_option("Hit the wagon gate before the watch can settle.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Slip up the ruin side and cut the outer line quietly.")
            success = self.skill_check(self.state.player, "Stealth", 13, context="to reach the outer ruin unseen")
            if success:
                self.apply_status(enemies[1], "surprised", 1, source="your silent wall-climb")
                enemies[1].current_hp = max(1, enemies[1].current_hp - 4)
                hero_bonus += 2
                self.say("You are inside the outer ruin before the first lookout can call the line.")
            else:
                self.apply_status(self.state.player, "reeling", 1, source="slipping on loose stone")
                self.say("Loose stone skips down the wall and the alarm comes early.")
        elif choice == 2:
            self.player_speaker("Late relief from the tor. Open up before the ridge goes black.")
            success = self.skill_check(self.state.player, "Deception", 13, context="to sell a field report at the gate")
            if success:
                self.apply_status(enemies[0], "surprised", 1, source="your sudden betrayal")
                enemies[0].current_hp = max(1, enemies[0].current_hp - 3)
                hero_bonus += 1
                self.say("The lie holds exactly long enough to put the first defender down badly.")
            else:
                self.apply_status(self.state.player, "surprised", 1, source="the sentry's barked alarm")
                self.say("The sentry does not buy it, and now the whole gate is shouting.")
        else:
            self.player_action("Hit the wagon gate before the watch can settle.")
            success = self.skill_check(self.state.player, "Athletics", 13, context="to burst through the wagon gate with momentum")
            if success:
                self.apply_status(self.state.player, "emboldened", 2, source="blasting through the gate")
                self.apply_status(enemies[0], "prone", 1, source="the splintered rush")
                hero_bonus += 2
                self.say("The gate gives under force and the outer line loses shape immediately.")
            else:
                self.apply_status(self.state.player, "reeling", 1, source="hitting the gate wrong")
                self.say("The gate still gives, but the impact costs you the clean opening.")

        outcome = self.run_encounter(
            Encounter(
                title="Ashfall Gate",
                description="Outer sentries scramble between ruined stone, cages, and signal braziers.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=True,
                parley_dc=13,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("Ashfall Watch remains in enemy hands.")
            return
        if outcome == "fled":
            self.return_to_phandalin("You fall back to Iron Hollow to rethink the assault.")
            return

        self.complete_map_room(dungeon, room.room_id)
        self.say("With the gate broken, you reach a prisoner yard, the tower's smoke basin, and a half-charred order board marked with Rukhar's hand.")
        choice = self.scenario_choice(
            "What do you handle before the inner barracks can form up?",
            [
                self.skill_tag("STEALTH", self.action_option("Snuff the signal basin before anyone can call the ridge.")),
                self.skill_tag("ATHLETICS", self.action_option("Break the prisoner cage and arm whoever can still stand.")),
                self.quoted_option("INVESTIGATION", "Read the order board. If Rukhar thinks in patterns, I want them now."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Snuff the signal basin before anyone can call the ridge.")
            success = self.skill_check(self.state.player, "Stealth", 12, context="to kill the signal basin without drawing the whole court")
            if success:
                self.state.flags["ashfall_signal_basin_cleanly_snuffed"] = True
                self.say("You smother the basin under wet tarp and grit. No help is coming from the ridge in time to matter.")
            else:
                self.state.flags["ashfall_signal_basin_noisy"] = True
                self.say("You kill the signal late and loud, but late still counts for something.")
            self.complete_map_room(dungeon, "signal_basin")
        elif choice == 2:
            self.player_action("Break the prisoner cage and arm whoever can still stand.")
            success = self.skill_check(self.state.player, "Athletics", 12, context="to break the cage open fast enough to matter")
            if success:
                self.apply_status(self.state.player, "emboldened", 1, source="freed prisoners roaring for revenge")
                self.reward_party(xp=15, reason="freeing Ashfall's prisoners under fire")
                self.say("A few freed prisoners grab dropped clubs and stones, throwing the barracks response into chaos.")
            else:
                self.say("You free them, but not cleanly enough to keep the barracks from organizing.")
            self._ashfall_record_blue_scarf_truth()
            self.complete_map_room(dungeon, "prisoner_yard")
        else:
            self.player_speaker("Read the order board. If Rukhar thinks in patterns, I want them now.")
            success = self.skill_check(
                self.state.player,
                "Investigation",
                12,
                context="to read Rukhar's order board in the middle of the assault",
            )
            if success:
                self.state.flags["ashfall_orders_read"] = True
                self.add_clue("Rukhar rotates his strongest fighters through the lower barracks before taking the courtyard himself.")
                self.reward_party(xp=15, reason="reading Rukhar's order board under pressure")
                self.say("You catch enough of the rotation to know exactly which door the inner response will use.")
            else:
                self.say("You get fragments, but not the whole shape of his defense.")
            self._ashfall_record_blue_scarf_truth()
            self.complete_map_room(dungeon, "prisoner_yard")

        self.set_current_map_room("lower_barracks")

    def _ashfall_prisoner_yard(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("The prisoner yard reeks of smoke, rope, and panic. A half-charred order board still hangs beside the cages.")
        choice = self.scenario_choice(
            "What do you handle first?",
            [
                self.skill_tag("ATHLETICS", self.action_option("Break the prisoner cage and arm whoever can still stand.")),
                self.quoted_option("INVESTIGATION", "Read the order board. If Rukhar thinks in patterns, I want them now."),
                self.action_option("Cut the locks, shove the prisoners toward cover, and keep moving."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Break the prisoner cage and arm whoever can still stand.")
            success = self.skill_check(self.state.player, "Athletics", 12, context="to break the cage open fast enough to matter")
            if success:
                self.apply_status(self.state.player, "emboldened", 1, source="freed prisoners roaring for revenge")
                self.reward_party(xp=15, reason="freeing Ashfall's prisoners under fire")
                self.say("A few freed prisoners grab dropped clubs and stones, throwing the barracks response into chaos.")
            else:
                self.say("You free them, but not cleanly enough to keep the barracks from organizing.")
        elif choice == 2:
            self.player_speaker("Read the order board. If Rukhar thinks in patterns, I want them now.")
            success = self.skill_check(
                self.state.player,
                "Investigation",
                12,
                context="to read Rukhar's order board in the middle of the assault",
            )
            if success:
                self.state.flags["ashfall_orders_read"] = True
                self.add_clue("Rukhar rotates his strongest fighters through the lower barracks before taking the courtyard himself.")
                self.reward_party(xp=15, reason="reading Rukhar's order board under pressure")
                self.say("You catch enough of the rotation to know exactly which door the inner response will use.")
            else:
                self.say("You get fragments, but not the whole shape of his defense.")
        else:
            self.player_action("Cut the locks, shove the prisoners toward cover, and keep moving.")
            self.say("The cages swing open and the yard turns from a pen into a problem the watch can no longer ignore.")

        self._ashfall_record_blue_scarf_truth()
        self.complete_map_room(dungeon, room.room_id)

    def _ashfall_signal_basin(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("The signal basin spits oily smoke toward the ridges, half-fed and still dangerous.")
        choice = self.scenario_choice(
            "How do you kill the signal line?",
            [
                self.skill_tag("STEALTH", self.action_option("Snuff the signal basin before anyone can call the ridge.")),
                self.quoted_option("SURVIVAL", "The wind is shifting. I can use it to turn the smoke back into the yard."),
                self.action_option("Kick the braziers apart and drown the whole thing in grit."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Snuff the signal basin before anyone can call the ridge.")
            success = self.skill_check(self.state.player, "Stealth", 12, context="to kill the signal basin without drawing the whole court")
            if success:
                self.state.flags["ashfall_signal_basin_cleanly_snuffed"] = True
                self.say("You smother the basin under wet tarp and grit. No help is coming from the ridge in time to matter.")
            else:
                self.state.flags["ashfall_signal_basin_noisy"] = True
                self.say("You kill the signal late and loud, but late still counts for something.")
        elif choice == 2:
            self.player_speaker("The wind is shifting. I can use it to turn the smoke back into the yard.")
            success = self.skill_check(self.state.player, "Survival", 12, context="to use the crosswind against the signal basin")
            if success:
                self.state.flags["ashfall_signal_basin_cleanly_snuffed"] = True
                self.say("The smoke whips back into the yard and wrecks the timing of anyone still trying to form a line.")
                self.reward_party(xp=10, reason="turning Ashfall's signal smoke back on the fort")
            else:
                self.state.flags["ashfall_signal_basin_noisy"] = True
                self.say("The wind helps, but not cleanly enough to hide the sabotage.")
        else:
            self.player_action("Kick the braziers apart and drown the whole thing in grit.")
            self.state.flags["ashfall_signal_basin_noisy"] = True
            self.say("The basin collapses into a coughing ruin of sparks, ash, and wet earth.")

        self.complete_map_room(dungeon, room.room_id)

    def _ashfall_lower_barracks(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        party_size = self.act1_party_size()
        second_enemies = [create_enemy("ash_brand_enforcer"), create_enemy("bandit_archer", name="Ashen Brand Barracks Archer")]
        if party_size >= 2:
            second_enemies.append(self.act1_pick_enemy(("ember_channeler", "bandit", "orc_raider", "gutter_zealot", "ashstone_percher")))
        if party_size >= 4:
            second_enemies.append(self.act1_pick_enemy(("orc_raider", "rust_shell_scuttler", "bugbear_reaver")))
        if self.act1_relay_sabotaged() and len(second_enemies) > 1:
            missing_reinforcement = second_enemies.pop()
            self.say(
                f"{missing_reinforcement.name} never makes the barracks line. Cinderfall's ruined relay has the reserve route bleeding men and time."
            )
        hero_bonus = int(self.state.flags.get("ashfall_signal_basin_silenced", False)) * 2
        if self.state.flags.get("ashfall_prisoners_freed"):
            hero_bonus += 2
        if self.state.flags.get("ashfall_orders_read"):
            hero_bonus += 1
        self.say("Veterans and hired blades spill out of the lower barracks in a hard organized rush.")
        outcome = self.run_encounter(
            Encounter(
                title="Ashfall Lower Barracks",
                description="Veterans and hired blades spill out of the lower barracks in a hard organized rush.",
                enemies=second_enemies,
                allow_flee=True,
                allow_parley=True,
                parley_dc=14,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("Ashfall's lower barracks break the party in the smoke.")
            return
        if outcome == "fled":
            self.return_to_phandalin("You drag the party clear of the lower yard and retreat before the courtyard can close on you.")
            return

        self.resolve_elira_faith_under_ash()
        self.complete_map_room(dungeon, room.room_id)
        if not self.state.flags.get("ashfall_signal_basin_silenced"):
            self.say("The barracks are broken, but the command post is still shielded by the active signal line. Another wing needs clearing first.")

    def _ashfall_rukhar_command(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("At the tower court's heart, a disciplined hobgoblin in darkened mail steps through the smoke with the calm of a soldier who has already sorted the dead from the living.")
        self.speaker(
            "Rukhar Cinderfang",
            "You have cost my employers time, coin, and useful subordinates. I will not pretend that leaves us room for civility.",
        )
        party_size = self.act1_party_size()
        boss_enemies = [create_enemy("rukhar")]
        boss_enemies.append(create_enemy("ash_brand_enforcer"))
        if not self.act1_relay_sabotaged():
            boss_enemies[0].grant_temp_hp(4)
            self.say("Reserve draughts and spare armor plates still reached Rukhar before you did. He squares up behind the fort's last full edge.")
        else:
            self.say("Rukhar is still dangerous, but Cinderfall's ruined relay leaves him without the fort's last reserve edge.")
        if party_size >= 2:
            boss_enemies.append(self.act1_pick_enemy(("ash_brand_enforcer", "gutter_zealot", "bugbear_reaver")))
        if party_size >= 4:
            boss_enemies.append(self.act1_pick_enemy(("orc_raider", "rust_shell_scuttler")))
        boss_bonus = 1 if self.state.flags.get("ashfall_orders_read") else 0
        if self.state.flags.get("elira_mercy_blessing"):
            self.apply_status(self.state.player, "blessed", 2, source="Elira's answer under ash")
            boss_bonus += 1
        if self.state.flags.get("elira_hard_verdict"):
            boss_bonus += 1
            boss_enemies[0].current_hp = max(1, boss_enemies[0].current_hp - 2)
        options: list[tuple[str, str]] = []
        if self.state.flags.get("stonehill_quiet_room_intel_decoded"):
            options.append(
                (
                    "quiet_room",
                    self.skill_tag(
                        "QUIET ROOM INTEL",
                        self.action_option("Use the stolen countersign and make Rukhar's own line doubt the next order."),
                    ),
                )
            )
        options.extend(
            [
                ("intimidation", self.quoted_option("INTIMIDATION", "Surrender the yard in Iron Hollow's name.")),
                ("persuasion", self.quoted_option("PERSUASION", "Your paymaster is already losing. Walk away with the people who still can.")),
                ("strike", self.action_option("Strike before he can settle the shield line.")),
            ]
        )
        choice = self.scenario_choice(
            "Rukhar raises his blade and waits to see how you answer.",
            [text for _, text in options],
            allow_meta=False,
        )
        selection_key, _ = options[choice - 1]
        if selection_key == "quiet_room":
            self.player_action("Use the stolen countersign and make Rukhar's own line doubt the next order.")
            boss_enemies[0].current_hp = max(1, boss_enemies[0].current_hp - 4)
            boss_bonus += 1
            self.apply_status(boss_enemies[0], "reeling", 1, source="Ashlamp's stolen countersign turning his line uncertain")
            if len(boss_enemies) > 1:
                wavering = boss_enemies.pop()
                self.say(f"When you bark the stolen countersign, {wavering.name} checks Rukhar instead of the line. The hesitation is all the opening you need.")
            else:
                self.say("You speak the countersign from Nera's packet and even Rukhar has to waste a heartbeat recalculating who betrayed whom.")
            self.reward_party(xp=10, reason="spending Ashlamp quiet-room intel at Ashfall")
        elif selection_key == "intimidation":
            self.player_speaker("Surrender the yard in Iron Hollow's name.")
            success = self.skill_check(self.state.player, "Intimidation", 13, context="to crack Rukhar's command posture")
            if success:
                boss_enemies[0].current_hp = max(1, boss_enemies[0].current_hp - 4)
                self.apply_status(boss_enemies[0], "frightened", 1, source="your iron-edged demand")
                self.say("Rukhar's line tightens too hard, which is its own kind of weakness.")
            else:
                self.apply_status(boss_enemies[0], "emboldened", 2, source="your failed demand")
                self.speaker("Rukhar Cinderfang", "Good. You arrived with a spine.")
        elif selection_key == "persuasion":
            self.player_speaker("Your paymaster is already losing. Walk away with the people who still can.")
            success = self.skill_check(self.state.player, "Persuasion", 13, context="to separate Rukhar from the men still taking his orders")
            if success:
                fleeing = boss_enemies.pop() if len(boss_enemies) > 1 else None
                if fleeing is not None:
                    self.say(f"{fleeing.name} looks at the smoke, looks at Rukhar, and decides not to die for bookkeeping.")
                self.apply_status(boss_enemies[0], "reeling", 1, source="his line cracking around him")
            else:
                self.say("Rukhar's discipline holds harder than your mercy can pry apart.")
        else:
            self.player_action("Strike before he can settle the shield line.")
            boss_enemies[0].current_hp = max(1, boss_enemies[0].current_hp - 3)
            boss_bonus += 2
            self.say("Steel answers before speeches can, and the final fight begins in motion.")

        outcome = self.run_encounter(
            Encounter(
                title="Miniboss: Rukhar Cinderfang",
                description="The Ashfall sergeant rallies the last disciplined core of the Ashen Brand field force.",
                enemies=boss_enemies,
                allow_flee=True,
                allow_parley=True,
                parley_dc=14,
                hero_initiative_bonus=boss_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("Rukhar drives the party from the tower in blood and smoke.")
            return
        if outcome == "fled":
            self.return_to_phandalin("You escape the watchtower and retreat to Iron Hollow to regroup.")
            return

        if not self.state.flags.get("ashfall_blue_scarf_truth_found"):
            self._ashfall_record_blue_scarf_truth(fallback=True)
        self.complete_map_room(dungeon, room.room_id)
        self.add_clue("Rukhar carried a soot-black key stamped with the Duskmere crest and orders to move captives beneath the manor hill.")
        self.add_journal("Ashfall Watch is broken, but the Ashen Brand's cellar routes beneath Iron Hollow are still active.")
        self.refresh_quest_statuses(announce=False)
        self.say(
            "Among Rukhar's orders you find a blackened key bearing the Duskmere crest, prisoner transfer notes, and references to a deeper reserve called Emberhall. "
            "The field base is broken, but the gang's thinking parts are still below town."
        )
        self.return_to_phandalin("Ashfall Watch breaks under the assault, and the road home finally opens.")

    def _tresendar_hidden_stair(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say(
            "The ruined manor crouches over Iron Hollow like a memory that never learned to stay buried. Beneath the broken shell, a hidden stair drops into wet stone, cistern corridors, and ash-marked cellars where the Ashen Brand keeps its quieter work.",
            typed=True,
        )
        choice = self.scenario_choice(
            "How do you enter the buried manor?",
            [
                self.quoted_option("INVESTIGATION", "There is a hidden stair here somewhere. Let me find the one they trust."),
                self.skill_tag("STEALTH", self.action_option("Slip through the collapsed chapel side and into the cellars.")),
                self.skill_tag("ATHLETICS", self.action_option("Rip the old cistern grate open and take the straight drop.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_speaker("There is a hidden stair here somewhere. Let me find the one they trust.")
            success = self.skill_check(self.state.player, "Investigation", 13, context="to find the concealed manor intake route")
            self.state.flags["tresendar_hidden_entry"] = success
            self.state.flags["tresendar_entry_approach_failed"] = not success
            if success:
                self.say("You find the concealed stair and enter on the defenders' blind side.")
            else:
                self.say("You find the route, just not before the noise of the search carries below.")
        elif choice == 2:
            self.player_action("Slip through the collapsed chapel side and into the cellars.")
            success = self.skill_check(self.state.player, "Stealth", 13, context="to cross the broken chapel without warning the cellars")
            self.state.flags["tresendar_chapel_entry"] = success
            self.state.flags["tresendar_entry_approach_failed"] = not success
            if success:
                self.say("You come through the chapel rubble already moving and the first lookout never gets set.")
            else:
                self.apply_status(self.state.player, "reeling", 1, source="a falling stone saint-head")
                self.say("A broken stone saint tumbles and announces you to the lower rooms.")
        else:
            self.player_action("Rip the old cistern grate open and take the straight drop.")
            success = self.skill_check(self.state.player, "Athletics", 13, context="to force the old grate without losing balance on the drop")
            self.state.flags["tresendar_cistern_breach"] = success
            self.state.flags["tresendar_entry_approach_failed"] = not success
            if success:
                self.apply_status(self.state.player, "emboldened", 2, source="a brutal manor breach")
                self.say("The grate comes free in a crash of iron and you land already driving the fight.")
            else:
                self.apply_status(self.state.player, "prone", 1, source="a bad landing through the cistern grate")
                self.say("The grate gives, but the landing is uglier than planned.")

        self.complete_map_room(dungeon, room.room_id)

    def _tresendar_cellar_intake(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        party_size = self.act1_party_size()
        enemies = [create_enemy("bandit", name="Ashen Brand Collector"), create_enemy("bandit_archer", name="Archive Cutout")]
        if party_size >= 3:
            enemies.append(self.act1_pick_enemy(("skeletal_sentry", "mireweb_spider", "cache_mimic", "ashstone_percher")))
        if party_size >= 4:
            enemies.append(self.act1_pick_enemy(("stonegaze_skulker", "cache_mimic", "ashstone_percher")))
        hero_bonus = self.apply_scene_companion_support("tresendar_manor")
        if self.state.flags.pop("tresendar_hidden_entry", False):
            self.apply_status(enemies[0], "surprised", 1, source="your hidden entry")
            hero_bonus += 2
        if self.state.flags.pop("tresendar_chapel_entry", False):
            enemies[1].current_hp = max(1, enemies[1].current_hp - 4)
            self.apply_status(enemies[1], "reeling", 1, source="your chapel-side opening")
            hero_bonus += 1
        if self.state.flags.pop("tresendar_cistern_breach", False):
            self.apply_status(self.state.player, "emboldened", 2, source="a brutal manor breach")
            self.apply_status(enemies[0], "prone", 1, source="the crashing grate and falling iron")
            hero_bonus += 1
        outcome = self.run_encounter(
            Encounter(
                title="Duskmere Cellars",
                description="Collectors, cutouts, and buried sentries hold the intake route beneath the manor.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=True,
                parley_dc=13,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The buried manor swallows the party beneath Iron Hollow.")
            return
        if outcome == "fled":
            self.return_to_phandalin("You pull back from the manor tunnels before the whole cellar network can close around you.")
            return

        self.complete_map_room(dungeon, room.room_id)
        self.state.flags.pop("tresendar_entry_approach_failed", None)
        self.say("The intake route is broken. Wet corridors open toward the cistern walk, and a barred side store lies deeper in the dark.")

    def _tresendar_cistern_walk(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("The cracked cistern walk stinks of wet stone and secrets. Something with a single reflective eye is moving through the dark water below.")
        choice = self.scenario_choice(
            "How do you handle the thing in the cistern before it fully commits?",
            [
                self.quoted_option("INSIGHT", "It is testing us. Let me read what it wants before it strikes."),
                self.quoted_option("ARCANA", "That is no simple cellar monster. I want its pattern before it gets mine."),
                self.action_option("Throw a ration sack into the dark and charge while it turns."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_speaker("It is testing us. Let me read what it wants before it strikes.")
            success = self.skill_check(self.state.player, "Insight", 13, context="to read the cistern horror's attention before it breaks cover")
            if success:
                self.state.flags["tresendar_eye_read"] = True
                self.say("The creature wants secrets and weakness first, flesh second. Knowing that lets you meet its gaze without offering either too freely.")
            else:
                self.say("You catch hunger, curiosity, and malice all at once, which is not the same as understanding.")
        elif choice == 2:
            self.player_speaker("That is no simple cellar monster. I want its pattern before it gets mine.")
            success = self.skill_check(self.state.player, "Arcana", 13, context="to identify the cistern horror before it opens the fight")
            if success:
                self.state.flags["tresendar_eye_read"] = True
                self.apply_status(self.state.player, "blessed", 1, source="naming the cistern horror correctly")
                self.say("Putting the creature into words steals some of the fear it was trying to weaponize.")
            else:
                self.say("Naming the horror correctly does not stop it from grinning at you out of the dark.")
        else:
            self.player_action("Throw a ration sack into the dark and charge while it turns.")
            self.state.flags["tresendar_eye_ambushed"] = True
            self.say("The sack hits water, the yellow eye turns, and you use the half-second it gives you.")

        self.complete_map_room(dungeon, room.room_id)

    def _tresendar_cage_store(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("The cage store holds ledger scraps, old chains, and one sealed coffer the Ashen Brand never got around to moving.")
        choice = self.scenario_choice(
            "What do you secure here?",
            [
                self.quoted_option("INVESTIGATION", "Give me the ledgers. I want the shape of Varyn's exits and lies."),
                self.quoted_option("SLEIGHT OF HAND", "Open the coffer quietly and take whatever matters before the hinges scream."),
                self.action_option("Take the whole coffer and drag it back the hard way."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_speaker("Give me the ledgers. I want the shape of Varyn's exits and lies.")
            success = self.skill_check(self.state.player, "Investigation", 13, context="to decode the cage-store papers before the boss room")
            if success:
                self.add_clue("Rukhar's ledger chain confirms Emberhall as Varyn's deeper reserve beneath town.")
                self.reward_party(xp=10, reason="decoding the cage-store records")
                self.say("The papers make it plain: Duskmere was only the intake route, not the final refuge.")
            else:
                self.say("You get enough to confirm the route, but not every name attached to it.")
        elif choice == 2:
            self.player_speaker("Open the coffer quietly and take whatever matters before the hinges scream.")
            success = self.skill_check(self.state.player, "Sleight of Hand", 13, context="to open the coffer without wrecking the contents")
            if success:
                self.add_inventory_item("scroll_arcane_refresh", source="a sealed coffer in the cistern alcove")
                self.say("The coffer opens cleanly and gives up one preserved scroll case before the hinges complain.")
            else:
                self.add_inventory_item("scroll_arcane_refresh", source="a dented coffer in the cistern alcove")
                self.say("The lock gives badly, but the scroll case inside survives well enough.")
        else:
            self.player_action("Take the whole coffer and drag it back the hard way.")
            self.add_inventory_item("scroll_arcane_refresh", source="a sealed coffer in the cistern alcove")
            self.say("You do not solve the lock so much as decide it is now a surface problem.")

        self.complete_map_room(dungeon, room.room_id)

    def _tresendar_nothic_background_read(self) -> None:
        assert self.state is not None
        background_reads = {
            "Soldier": "You still count the people who did not answer roll. Discipline did not save them all.",
            "Acolyte": "You washed blood from temple cloth and called it service. Some stains learned your name.",
            "Criminal": "False manifests. Back doors. The relief of being gone before blame arrives.",
            "Sage": "You hate missing records because you know gaps are where cowards hide knives.",
            "Outlander": "The birds warned you before the city did. You trusted silence, and silence was right.",
            "Charlatan": "You wear lies like good gloves. Soft inside. Clean outside. Useful in a crowd.",
            "Guild Artisan": "You know the difference between a shortage and a theft wearing numbers.",
            "Hermit": "You heard the road getting sick before anyone important learned to pronounce the fever.",
        }
        background = self.state.player.background
        self.state.flags["tresendar_nothic_background_read"] = background
        self.speaker(
            "Cistern Eye",
            background_reads.get(background, "You came south with one story on your tongue and another locked behind your teeth."),
        )

    def _active_tresendar_secret_companion(self, name: str):
        assert self.state is not None
        companion = self.find_companion(name)
        return companion if companion in self.state.companions else None

    def _record_tresendar_nothic_trade_info(self) -> None:
        assert self.state is not None
        if not self.state.flags.get("tresendar_nothic_trade_info_gained"):
            self.state.flags["deep_ledger_hint_count"] = int(self.state.flags.get("deep_ledger_hint_count", 0) or 0) + 1
        self.state.flags["tresendar_nothic_trade_info_gained"] = True
        self.add_clue("The Cistern Eye names Emberhall as Varyn's deeper refuge and calls Duskmere only the Ashen Brand's intake throat.")

    def _record_tresendar_nothic_cinderfall_lore(self) -> None:
        assert self.state is not None
        if not self.state.flags.get("tresendar_nothic_cinderfall_lore"):
            self.state.flags["deep_ledger_hint_count"] = int(self.state.flags.get("deep_ledger_hint_count", 0) or 0) + 1
        self.state.flags["tresendar_nothic_cinderfall_lore"] = True
        if self.state.flags.get("cinderfall_relay_destroyed"):
            self.add_clue(
                "The Cistern Eye confirms Cinderfall was an Ashen Brand relay; destroying it cut Ashfall's reserve channel before Rukhar could lean on it."
            )
            self.say("The Eye shows Cinderfall as a black hinge already broken: ash, route slates, and a reserve line that never answered Rukhar in time.")
        else:
            self.add_clue(
                "The Cistern Eye reveals Cinderfall was an Ashen Brand relay moving route slates, reserve orders, and supplies into Ashfall Watch."
            )
            self.say("The Eye shows Cinderfall as a relay, not a ruin: route slates, reserve orders, and supplies breathing toward Ashfall Watch.")

    def _record_tresendar_nothic_wave_echo_lore(self) -> None:
        assert self.state is not None
        if not self.state.flags.get("tresendar_nothic_wave_echo_lore"):
            self.state.flags["deep_ledger_hint_count"] = int(self.state.flags.get("deep_ledger_hint_count", 0) or 0) + 1
        self.state.flags["tresendar_nothic_wave_echo_lore"] = True
        self.add_clue(
            "The Cistern Eye says the Ashen Brand is a curtain over older Meridian routes, keeping Resonant Vaults unreachable until someone else can claim the first clean map."
        )
        self.add_clue("The Cistern Eye whispers that the Meridian Forge can listen as well as make, and something below the mine has started answering.")
        self.add_journal("The Cistern Eye forced a Resonant Vaults warning into the open: the Forge can listen, and something below it may answer.")
        self.say("For a heartbeat the cistern water becomes a mine-dark lake, and something under it seems to hear your breath.")

    def _tresendar_adjust_active_companions_for_bargain(self, delta: int, reason: str) -> None:
        assert self.state is not None
        for companion in list(self.state.companions):
            if companion.dead:
                continue
            self.adjust_companion_disposition(companion, delta, reason)

    def _tresendar_nothic_trade_secret(self) -> int:
        assert self.state is not None
        options: list[tuple[str, str]] = [
            ("memory", self.action_option("Give it a memory from your own past.")),
            ("self_truth", self.quoted_option("TRUTH", "The truth I keep walking around is mine to speak.")),
        ]
        bryn = self._active_tresendar_secret_companion("Bryn Underbough")
        if bryn is not None:
            options.append(
                (
                    "betray_bryn",
                    self.quoted_option("BETRAY BRYN", "Bryn knows the old smuggler marks because she used to run them."),
                )
            )
        rhogar = self._active_tresendar_secret_companion("Rhogar Valeguard")
        if rhogar is not None:
            options.append(
                (
                    "betray_rhogar",
                    self.quoted_option("BETRAY RHOGAR", "Rhogar's oath has a crack in it. He knows the sound."),
                )
            )

        choice = self.scenario_choice(
            "What price do you let the Cistern Eye taste?",
            [label for _, label in options],
            allow_meta=False,
        )
        trade_key = options[choice - 1][0]
        self.state.flags["tresendar_nothic_trade"] = trade_key
        self.state.flags["tresendar_nothic_trade_paid"] = True

        if trade_key == "memory":
            self.player_action("Give it a memory from your own past.")
            self.state.flags["tresendar_nothic_memory_paid"] = True
            self.apply_status(self.state.player, "reeling", 1, source="a hollowed memory")
            self.speaker("Cistern Eye", "Yes. A warm morning. A voice. A door you thought would stay open.")
            self.add_journal("The Cistern Eye took a personal memory in trade for Emberhall truth.")
            self._record_tresendar_nothic_trade_info()
            return 0

        if trade_key == "self_truth":
            self.player_speaker("The truth I keep walking around is mine to speak.")
            self.state.flags["tresendar_nothic_self_truth_spoken"] = True
            self.speaker("Cistern Eye", "Owned hurt. Bitter. Clean. It cuts you and still belongs to you.")
            self.apply_story_skill_modifier(
                self.state.player,
                "clear_eyed_wound",
                {"Arcana": 1, "Insight": 1, "Persuasion": 1},
                source="Clear-Eyed Wound",
                duration="through the Act 1 finale",
            )
            self.add_journal("Clear-Eyed Wound grants +1 Arcana, +1 Insight, and +1 Persuasion through the Act 1 finale.")
            self._record_tresendar_nothic_trade_info()
            self.say("Speaking the truth yourself turns the wound into a lens instead of a handle.")
            return 1

        if trade_key == "betray_bryn":
            assert bryn is not None
            self.player_speaker("Bryn knows the old smuggler marks because she used to run them.")
            self.state.flags["bryn_secret_exposed"] = True
            self.speaker("Cistern Eye", "Run them? No. Carry them. Little feet. Clean face. Dirty instructions.")
            self.speaker("Bryn Underbough", "You do not get to make that sound simple.")
            penalty = -3 if self.has_quest("bryn_loose_ends") and not self.state.flags.get("bryn_loose_ends_resolved") else -2
            self.adjust_companion_disposition(bryn, penalty, "you fed Bryn's past to the Cistern Eye")
            self.add_journal("Bryn's smuggling past was exposed to the Cistern Eye.")
            self._record_tresendar_nothic_trade_info()
            return 0

        assert rhogar is not None
        self.player_speaker("Rhogar's oath has a crack in it. He knows the sound.")
        self.state.flags["rhogar_secret_exposed"] = True
        self.state.flags["rhogar_cistern_conflict_pending"] = True
        self.speaker("Cistern Eye", "Threshold-keeper. Road-sworn. You held the line once while someone beyond it begged.")
        self.speaker("Rhogar Valeguard", "Stop.")
        self.adjust_companion_disposition(rhogar, -2, "you fed Rhogar's oath-wound to the Cistern Eye")
        self.add_journal("Rhogar's oath-wound was exposed to the Cistern Eye, and a reckoning remains pending.")
        self._record_tresendar_nothic_trade_info()
        return 0

    def _tresendar_nothic_deep_bargain(self) -> tuple[int, int]:
        assert self.state is not None
        enemy_bonus = 0
        self.state.flags["tresendar_nothic_bargain_tier"] = 1
        self.state.flags["tresendar_nothic_sanity_cost"] = 1
        self._record_tresendar_nothic_trade_info()
        self.apply_status(self.state.player, "reeling", 1, source="the Cistern Eye's first bargain")
        self.speaker("Cistern Eye", "Throat first. Manor throat. Emberhall belly. Varyn hiding where the ash still thinks.")
        choice = self.scenario_choice(
            "The Eye's first truth leaves another shape under the water.",
            [
                self.action_option("Take the Emberhall truth and end the bargain."),
                self.quoted_option("BARGAIN AGAIN", "What did Cinderfall really feed?"),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Take the Emberhall truth and end the bargain.")
            return 0, enemy_bonus

        self.player_speaker("What did Cinderfall really feed?")
        self.state.flags["tresendar_nothic_bargain_tier"] = 2
        self.state.flags["tresendar_nothic_sanity_cost"] = 2
        self._record_tresendar_nothic_cinderfall_lore()
        self.apply_status(self.state.player, "frightened", 1, source="the Cistern Eye naming Cinderfall")
        enemy_bonus += 1
        self._tresendar_adjust_active_companions_for_bargain(-1, "you kept feeding the Cistern Eye for more secrets")
        choice = self.scenario_choice(
            "The second truth tastes like ash, but the Eye is still grinning.",
            [
                self.action_option("Stop before the bargain takes anything else."),
                self.quoted_option("BARGAIN AGAIN", "What waits past the Ashen Brand?"),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Stop before the bargain takes anything else.")
            return 0, enemy_bonus

        self.player_speaker("What waits past the Ashen Brand?")
        self.state.flags["tresendar_nothic_bargain_tier"] = 3
        self.state.flags["tresendar_nothic_sanity_cost"] = 3
        self.state.flags["tresendar_nothic_bargain_whispered_through"] = True
        self._record_tresendar_nothic_wave_echo_lore()
        self.apply_status(self.state.player, "reeling", 2, source="the Cistern Eye's deepest bargain")
        self.apply_status(self.state.player, "frightened", 2, source="the Cistern Eye's deepest bargain")
        self.apply_story_skill_modifier(
            self.state.player,
            "whispered_through",
            {"Insight": -1, "Persuasion": -1},
            source="Whispered Through",
            duration="through the Act 1 finale",
        )
        self.add_journal("Whispered Through imposes -1 Insight and -1 Persuasion through the Act 1 finale.")
        self._tresendar_adjust_active_companions_for_bargain(-1, "you let the Cistern Eye press past useful truth into wrongness")
        enemy_bonus += 2
        return 0, enemy_bonus

    def _tresendar_nothic_route_shell(self, nothic) -> tuple[int, int]:
        assert self.state is not None
        self.say(
            "The water below the cracked cistern walk goes still. Then an eye opens in it: yellow, lidless, and fixed on the parts of you that would rather stay unnamed."
        )
        self.speaker("Cistern Eye", "Little bright things. Little walking locks. You came down carrying keys and called them hearts.")
        self._tresendar_nothic_background_read()
        choice = self.scenario_choice(
            "The Cistern Eye waits to learn what kind of answer you are.",
            [
                self.action_option("Kill it before it pries any deeper."),
                self.quoted_option("TRADE", "A memory, a truth, or betrayal. Name the price and speak what you know."),
                self.action_option("Bargain for every secret it is willing to spit up."),
                self.quoted_option("DECEPTION", "All right. I will give you a secret. A good one."),
            ],
            allow_meta=False,
        )
        hero_bonus = 0
        enemy_bonus = 0
        if choice == 1:
            self.state.flags["tresendar_nothic_route"] = "kill"
            self.player_action("Kill it before it pries any deeper.")
            tolan = self.find_companion("Tolan Ironshield")
            if tolan in self.state.companions and not self.state.flags.get("tresendar_nothic_tolan_kill_approved"):
                self.state.flags["tresendar_nothic_tolan_kill_approved"] = True
                self.adjust_companion_disposition(tolan, 1, "refusing the Cistern Eye's bargain")
            self.say("Steel and spell answer before the thing can turn confession into leverage.")
        elif choice == 2:
            self.state.flags["tresendar_nothic_route"] = "trade"
            self.player_speaker("A memory, a truth, or betrayal. Name the price and speak what you know.")
            self.speaker("Cistern Eye", "Warm price. Sweet price. A thing remembered, a thing admitted, or a friend opened from the inside.")
            hero_bonus += self._tresendar_nothic_trade_secret()
            self.say("The price is paid. The Eye gives you truth, then scrapes up the stone lip with claws first.")
        elif choice == 3:
            self.state.flags["tresendar_nothic_route"] = "bargain"
            self.player_action("Bargain for every secret it is willing to spit up.")
            self.speaker("Cistern Eye", "Greedy lock. Greedy key. Yes. Open wider.")
            bargain_hero_bonus, bargain_enemy_bonus = self._tresendar_nothic_deep_bargain()
            hero_bonus += bargain_hero_bonus
            enemy_bonus += bargain_enemy_bonus
            self.say("For one breath the cistern seems full of whispered names. Then the thing smiles too broadly and comes for more than words.")
        else:
            self.state.flags["tresendar_nothic_route"] = "deceive"
            self.player_speaker("All right. I will give you a secret. A good one.")
            success = self.skill_check(self.state.player, "Deception", 15, context="to bait the Cistern Eye with a false secret")
            if success:
                self.state.flags["tresendar_nothic_deceived"] = True
                self._record_tresendar_nothic_trade_info()
                self._record_tresendar_nothic_cinderfall_lore()
                self._record_tresendar_nothic_wave_echo_lore()
                self.apply_status(nothic, "reeling", 1, source="your false secret")
                hero_bonus += 2
                self.say("The lie has enough blood on it to smell alive. The Cistern Eye drinks, shudders, and loses the first clean beat of the fight.")
            else:
                self.state.flags["tresendar_nothic_deception_failed"] = True
                self.apply_status(self.state.player, "surprised", 1, source="the Cistern Eye catching the lie")
                self.apply_status(self.state.player, "reeling", 1, source="the Cistern Eye catching the lie")
                enemy_bonus += 2
                self.speaker("Cistern Eye", "Painted meat. False bone. Bad little lock.")
        return hero_bonus, enemy_bonus

    def _tresendar_nothic_lair(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        party_size = self.act1_party_size()
        second_enemies = [create_enemy("nothic", name="Cistern Eye")]
        if party_size >= 3:
            second_enemies.append(self.act1_pick_enemy(("skeletal_sentry", "stonegaze_skulker", "whispermaw_blob", "lantern_fen_wisp")))
        if party_size >= 4:
            second_enemies.append(self.act1_pick_enemy(("stonegaze_skulker", "whispermaw_blob", "graveblade_wight")))
        boss_bonus = int(self.state.flags.get("tresendar_eye_read", False)) + (2 if self.state.flags.get("tresendar_eye_ambushed", False) else 0)
        if not self.state.flags.get("tresendar_records_secured"):
            self.apply_status(second_enemies[0], "guarded", 2, source="unsecured cage-store reflections")
            second_enemies[0].bond_flags["cistern_reflection_active"] = True
            self.say("Unsecured cage-store records ripple through the cistern water, throwing false Eyes across the dark.")
        route_bonus, enemy_bonus = self._tresendar_nothic_route_shell(second_enemies[0])
        boss_bonus += route_bonus
        outcome = self.run_encounter(
            Encounter(
                title="The Cistern Eye",
                description="A warped cellar horror rises from the dark water below Duskmere Manor.",
                enemies=second_enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=boss_bonus,
                enemy_initiative_bonus=enemy_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The cistern horror keeps its secrets and your bodies with them.")
            return
        if outcome == "fled":
            self.return_to_phandalin("You retreat from the cistern dark before the manor can claim the rest of the night.")
            return

        self.complete_map_room(dungeon, room.room_id)
        self.add_clue("Duskmere Manor was the Ashen Brand's intake route; Varyn's remaining core has withdrawn into Emberhall below.")
        self.add_journal("You cleared the buried Duskmere route and confirmed Varyn has fallen back to Emberhall for the final stand.")
        if not self.state.flags.get("tresendar_records_secured"):
            self.add_inventory_item("scroll_arcane_refresh", source="a sealed coffer in the cistern alcove")
        self.return_to_phandalin("The cistern goes still, and the buried route beneath Duskmere finally breaks open.")

    def _emberhall_antechamber(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say(
            "Near midnight, you descend into Emberhall: old stone vaults, stolen crates, poison tables, ash-marked banners, and the last disciplined knot of the Ashen Brand. "
            "This is not a hideout anymore. It is an answer the gang built under the town while decent people slept overhead.",
            typed=True,
        )
        party_size = self.act1_party_size()
        enemies = [create_enemy("bandit", name="Ashen Brand Fixer"), create_enemy("bandit_archer", name="Cellar Sniper")]
        if party_size >= 3:
            enemies.append(self.act1_pick_enemy(("bandit", "gutter_zealot", "cache_mimic", "cinderflame_skull")))
        if party_size >= 4:
            enemies.append(self.act1_pick_enemy(("bandit_archer", "gutter_zealot", "cinderflame_skull")))
        hero_bonus = self.apply_scene_companion_support("emberhall_cellars")
        choice = self.scenario_choice(
            "How do you break the final approach open?",
            [
                self.skill_tag("STEALTH", self.action_option("Slip through the drainage run and hit the antechamber from behind.")),
                self.skill_tag("ATHLETICS", self.action_option("Kick in the main cellar door and force the issue immediately.")),
                self.quoted_option("PERSUASION", "Call for surrender before the last of them decides to die for Varyn."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Slip through the drainage run and hit the antechamber from behind.")
            success = self.skill_check(self.state.player, "Stealth", 13, context="to reach the antechamber quietly")
            if success:
                enemies[1].current_hp = max(1, enemies[1].current_hp - 5)
                self.apply_status(enemies[1], "surprised", 1, source="your tunnel approach")
                hero_bonus += 2
                self.say("You come out behind stacked crates and the first lookout never finds a clean line.")
            else:
                self.apply_status(self.state.player, "reeling", 1, source="a shrieking drainage grate")
                self.say("The grate screams and the last defenders know exactly where you are.")
        elif choice == 2:
            self.player_action("Kick in the main cellar door and force the issue immediately.")
            success = self.skill_check(self.state.player, "Athletics", 13, context="to blast the cellar door off its hinges")
            if success:
                self.apply_status(self.state.player, "emboldened", 2, source="blasting into Emberhall")
                self.apply_status(enemies[0], "prone", 1, source="the crashing cellar door")
                hero_bonus += 2
                self.say("The door explodes inward and the antechamber never really gets to become a line.")
            else:
                self.apply_status(self.state.player, "prone", 1, source="a collapsing door frame")
                self.say("The door gives badly and drags you down with it.")
        else:
            self.player_speaker("Call for surrender before the last of them decides to die for Varyn.")
            success = self.skill_check(self.state.player, "Persuasion", 14, context="to shake the final defenders before steel is fully drawn")
            if success:
                fleeing = enemies.pop()
                self.say(f"{fleeing.name} bolts for the far stair instead of dying for someone else's cut.")
                hero_bonus += 1
            else:
                self.say("The room tightens instead of yielding, and the last defenders settle in behind Varyn's certainty.")

        outcome = self.run_encounter(
            Encounter(
                title="Emberhall Antechamber",
                description="The gang's last disciplined guard line forms among poison tables and stolen crates.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=True,
                parley_dc=14,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("Emberhall's last guard line leaves the cellars to the Ashen Brand.")
            return
        if outcome == "fled":
            self.return_to_phandalin("You retreat to the surface before the last chamber can close around you.")
            return

        self.complete_map_room(dungeon, room.room_id)
        self.say("Beyond the antechamber, the ledger chain room and a smoke-choked archive split the last approach.")

    def _emberhall_ledger_chain(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("A chained clerk, a table full of ledgers, and a stack of poison vials wait in the narrow room outside the sanctum.")
        options: list[tuple[str, str]] = []
        if self.state.flags.get("stonehill_quiet_room_intel_decoded") and not self.state.flags.get("emberhall_ledger_read"):
            options.append(
                (
                    "quiet_room",
                    self.skill_tag(
                        "QUIET ROOM INTEL",
                        self.action_option("Match the quiet-room courier strip to these ledgers before the ink goes warm."),
                    ),
                )
            )
        options.extend(
            [
                ("medicine", self.quoted_option("MEDICINE", "The chained clerk is fading. Get them talking before the poison finishes the job.")),
                ("investigation", self.quoted_option("INVESTIGATION", "Give me the ledgers. I want the shape of Varyn's exits and lies.")),
                ("smash", self.action_option("Smash the poison table and flood the hall with glass, fumes, and noise.")),
            ]
        )
        choice = self.scenario_choice(
            "What do you do in the lull?",
            [text for _, text in options],
            allow_meta=False,
        )
        selection_key, _ = options[choice - 1]
        if selection_key == "quiet_room":
            self.player_action("Match the quiet-room courier strip to these ledgers before the ink goes warm.")
            self.state.flags["emberhall_ledger_read"] = True
            self.reward_party(xp=15, reason="matching Ashlamp quiet-room intel to Emberhall's ledgers")
            self.say("The Ashlamp packet fits the Emberhall books like a stolen key. You have Varyn's fallback routes before anyone can burn the proof.")
        elif selection_key == "medicine":
            self.player_speaker("The chained clerk is fading. Get them talking before the poison finishes the job.")
            success = self.skill_check(self.state.player, "Medicine", 13, context="to keep the poisoned clerk alive long enough for a final warning")
            if success:
                self.state.flags["emberhall_clerk_saved"] = True
                self.add_inventory_item("antitoxin_vial", source="the chained clerk's hidden pocket")
                self.reward_party(xp=15, reason="saving the chained clerk in Emberhall")
                self.say("The clerk rasps out one useful warning: Varyn keeps a reserve vial for the first enemy who lands a real hit.")
            else:
                self.say("You save what life you can, but the warning dies in fragments.")
        elif selection_key == "investigation":
            self.player_speaker("Give me the ledgers. I want the shape of Varyn's exits and lies.")
            success = self.skill_check(self.state.player, "Investigation", 13, context="to decode Varyn's fallback routes before the last fight")
            if success:
                self.state.flags["emberhall_ledger_read"] = True
                self.reward_party(xp=15, reason="decoding Varyn's fallback plan")
                self.say("You map the hall fast enough to know where Varyn intended to break line and reposition.")
            else:
                self.say("You get the broad shape of the chamber, but not every escape seam.")
        else:
            self.player_action("Smash the poison table and flood the hall with glass, fumes, and noise.")
            self.state.flags["emberhall_poison_table_broken"] = True
            self.say("Glass and reeking poison spread across the hall entrance, forcing the final fight to start amid chaos you chose.")

        self.complete_map_room(dungeon, room.room_id)

    def _emberhall_ash_archive(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say("The ash archive is part record room, part panic stash, with soot-marked ledgers stacked beside reserve doors.")
        choice = self.scenario_choice(
            "How do you work the archive?",
            [
                self.quoted_option("INVESTIGATION", "Search the ledgers and map which exits Varyn still believes in."),
                self.quoted_option("PERCEPTION", "There is something else hidden in here besides paperwork."),
                self.action_option("Sweep the room fast, pocket anything sharp, and keep moving."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_speaker("Search the ledgers and map which exits Varyn still believes in.")
            success = self.skill_check(self.state.player, "Investigation", 13, context="to search the ash archive under pressure")
            if success:
                self.state.flags["emberhall_archive_tip"] = True
                self.add_clue("The archive confirms Varyn planned to break toward a reserve room if the sanctum line folded.")
                self.reward_party(xp=10, reason="mapping Emberhall's reserve route")
                self.say("You trace the reserve route cleanly enough to turn the final chamber into a known problem.")
            else:
                self.say("You get the broad shape of the reserve route, but not every seam.")
        elif choice == 2:
            self.player_speaker("There is something else hidden in here besides paperwork.")
            success = self.skill_check(self.state.player, "Perception", 13, context="to find a useful reserve in the archive")
            if success:
                self.state.flags["emberhall_archive_tip"] = True
                self.add_inventory_item("potion_healing", source="a hidden archive shelf")
                self.say("A false shelf gives up a sealed potion case and a cleaner line on the reserve door.")
            else:
                self.say("You find the clutter, but not the clever part of it.")
        else:
            self.player_action("Sweep the room fast, pocket anything sharp, and keep moving.")
            self.say("You leave the archive in disorder and make sure whatever comes after you has to work harder than you did.")

        self.complete_map_room(dungeon, room.room_id)

    def _emberhall_black_reserve(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        party_size = self.act1_party_size()
        enemies = [create_enemy("bandit", name="Ashen Brand Enforcer"), create_enemy("bandit_archer", name="Reserve Sniper")]
        if party_size >= 3:
            enemies.append(self.act1_pick_enemy(("bandit", "cinderflame_skull", "whispermaw_blob")))
        if party_size >= 4:
            enemies.append(self.act1_pick_enemy(("bandit_archer", "cinderflame_skull", "whispermaw_blob")))
        self.say("The reserve room opens on a last cache of disciplined muscle, poison, and backup steel.")
        outcome = self.run_encounter(
            Encounter(
                title="Emberhall Black Reserve",
                description="The reserve room empties itself into the fight rather than let you reach Varyn cleanly.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=1 if self.state.flags.get("emberhall_archive_tip") else 0,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("Emberhall's reserve room slams shut around the party.")
            return
        if outcome == "fled":
            self.return_to_phandalin("You pull back from the reserve room before it can close around you.")
            return

        self.complete_map_room(dungeon, room.room_id)

    def _emberhall_varyn_sanctum(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        party_size = self.act1_party_size()
        boss_enemies = [create_enemy("varyn"), create_enemy("ash_brand_enforcer"), create_enemy("ember_channeler")]
        boss_enemies[0].max_hp += 8
        boss_enemies[0].current_hp += 8
        if party_size >= 3:
            boss_enemies.append(self.act1_pick_enemy(("bandit", "cinderflame_skull", "whispermaw_blob")))
        if party_size >= 4:
            boss_enemies.append(self.act1_pick_enemy(("bandit_archer", "cinderflame_skull", "gutter_zealot")))
        boss_bonus = 0
        if self.state.flags.get("emberhall_clerk_saved"):
            boss_bonus += 1
        if self.state.flags.get("emberhall_ledger_read"):
            boss_bonus += 1
        if self.state.flags.get("emberhall_poison_table_broken"):
            boss_bonus += 2
        if self.state.flags.get("emberhall_archive_tip"):
            boss_bonus += 1
        choice = self.scenario_choice(
            "Varyn Sable waits in the last chamber with ash banners at their back.",
            [
                self.quoted_option("PERSUASION", "It is over. Walk up the stairs alive, or do not walk them at all."),
                self.quoted_option("INTIMIDATION", "You are out of road, out of men, and out of time."),
                self.action_option("No more speeches. End this now."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_speaker("It is over. Walk up the stairs alive, or do not walk them at all.")
            success = self.skill_check(self.state.player, "Persuasion", 15, context="to make Varyn feel the walls finally closing in")
            if success:
                fleeing = boss_enemies.pop()
                self.say(f"{fleeing.name} breaks for the stairs before the first strike lands.")
                boss_bonus += 1
            else:
                self.speaker("Varyn Sable", "If it were over, you would not still be trying to talk me out of surviving it.")
        elif choice == 2:
            self.player_speaker("You are out of road, out of men, and out of time.")
            success = self.skill_check(self.state.player, "Intimidation", 15, context="to crack the captain's final composure")
            if success:
                boss_enemies[0].current_hp = max(1, boss_enemies[0].current_hp - 5)
                self.apply_status(boss_enemies[0], "reeling", 2, source="your certainty finally landing")
                self.say("For the first time, Varyn looks less amused than calculating.")
            else:
                self.apply_status(boss_enemies[0], "emboldened", 2, source="defying your threat")
                self.speaker("Varyn Sable", "That is what people say right before they become examples.")
        else:
            self.player_action("No more speeches. End this now.")
            boss_enemies[0].current_hp = max(1, boss_enemies[0].current_hp - 3)
            boss_bonus += 2
            self.say("Steel and spell-fire answer before Varyn can turn the room into a conversation again.")

        outcome = self.run_encounter(
            Encounter(
                title="Boss: Varyn Sable",
                description="The captain of the Ashen Brand makes the final stand beneath Iron Hollow.",
                enemies=boss_enemies,
                allow_flee=True,
                allow_parley=True,
                parley_dc=15,
                hero_initiative_bonus=boss_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The cellar banners remain standing above a fallen company.")
            return
        if outcome == "fled":
            self.return_to_phandalin("You escape the cellars and return to the surface to recover.")
            return

        self.complete_map_room(dungeon, room.room_id)
        self.state.flags["varyn_body_defeated_act1"] = True
        self.state.flags["varyn_route_displaced"] = True
        self.state.flags["act1_ashen_brand_broken"] = True
        if self.state.flags.get("emberhall_ledger_read") or self.state.flags.get("emberhall_archive_tip"):
            self.state.flags["emberhall_impossible_exit_seen"] = True
        self.say(
            "Varyn falls, but not cleanly. Body, cloak, and blade hit the cellar stones while the route behind him folds the wrong way. "
            "The remaining brigands scatter, the Ashen Brand breaks around that absence, and the pressure that has bent every road into Iron Hollow finally snaps. "
            "Among the captain's ledgers are references to older powers stirring beneath the Shatterbelt highlands, with whispers pointing toward deeper ruins, buried wealth, and unfinished business near Resonant Vaults."
        )
        if self.state.flags.get("emberhall_impossible_exit_seen"):
            self.say(
                "The exits you decoded before the fight all account for themselves except one: a route that appears in the ledger only after Varyn is gone."
            )
        victory_tier = self.act1_record_epilogue_flags()
        if victory_tier == "clean_victory":
            self.say("Iron Hollow takes the news like a town finally allowed to breathe. The roads are scarred, but not broken, and the company leaves Act I with loyalty mostly intact.")
        elif victory_tier == "costly_victory":
            self.say("The win holds, but it costs blood, trust, and more sleepless eyes than anyone in town will admit out loud. Iron Hollow survives this act tired rather than whole.")
        else:
            self.say("Varyn's local command is broken, but too many threads were left burning behind him. The Ashen Brand is beaten without being cleanly erased, and the next descent will begin under pressure.")
        self.add_journal("You broke the Ashen Brand and secured Iron Hollow through the end of Act 1.")
        self.reward_party(xp=250, gold=80, reason="securing Iron Hollow at the end of Act I")
        if 1 not in self.state.completed_acts:
            self.state.completed_acts.append(1)
        payload = self._map_state_payload()
        payload["current_dungeon_id"] = None
        payload["current_room_id"] = None
        payload["room_history"] = []
        payload["current_node_id"] = "emberhall_cellars"
        self.state.current_scene = "act1_complete"
        self._compact_hud_last_scene_key = None
        self.save_game(slot_name=f"{self.state.player.name}_act1_complete")
