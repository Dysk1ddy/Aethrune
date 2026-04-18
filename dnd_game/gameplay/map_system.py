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
            "Back in Phandalin, Bryn unwraps the smoke-stained ledger from the old cache. The names inside are part smugglers, part frightened teamsters, and part people who still live close enough to get hurt for what they once did."
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
        self.turn_in_quest("bryn_loose_ends")

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
        self.speaker("Elira Dawnmantle", "This is the moment that matters more than speeches ever do.")
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
        self.turn_in_quest("elira_faith_under_ash")

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
        if current_node_id == "neverwinter_briefing":
            self._remember_act1_nodes(payload, "neverwinter_briefing")
            return
        if current_node_id == "high_road_ambush":
            self._remember_act1_nodes(payload, "neverwinter_briefing", "high_road_ambush")
            return

        # Reaching any Phandalin-era node means the briefing and road ambush already happened.
        self._remember_act1_nodes(payload, "neverwinter_briefing", "high_road_ambush", "phandalin_hub")

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
        if current_node_id == "high_road_ambush":
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
                "You backtrack north toward Neverwinter, letting the familiar city road pull the party "
                "back to Mira's briefing room instead of pressing farther into the frontier."
            )
        if to_node_id == "high_road_ambush":
            return "You backtrack north along the High Road, returning to the scarred wagon site between Phandalin and Neverwinter."
        if from_node_id == "road_decision_post_blackwake" and to_node_id == "blackwake_crossing":
            return "You double back toward Blackwake Crossing, following the wet wagon scars and smoke-stained reeds instead of committing to the south road."
        if from_node_id == "phandalin_hub":
            return f"You leave Phandalin by the same track you used before, letting the road back to {to_title} replace the town's noise behind you."
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
            self.say("Behind you, Phandalin keeps moving: Tessa's runners argue supplies, road watches trade signals, and familiar voices fade into background work.")

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
            return f"You reopen the same expedition line from Phandalin, backtracking toward {to_title} before the council can turn the map into another argument."
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
            options.append(("withdraw", "phandalin_hub", self.action_option("Withdraw to Phandalin")))
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
            playable_sites = {"stonehollow_dig", "broken_prospect", "south_adit", "wave_echo_outer_galleries", "black_lake_causeway", "forge_of_spells"}
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
        lowered = raw.lower()
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
        self.banner("Phandalin")
        if not self.state.flags.get("phandalin_arrived"):
            self.say(
                "Phandalin rises from rocky foothills in a scatter of rebuilt homes, old stone scars, orchard walls, wagon sheds, and lantern-lit mud lanes. "
                "There are no proper walls, no garrison worth the name, and too many decent people living one bad week away from disaster.",
                typed=True,
            )
            self.state.flags["phandalin_arrived"] = True
            self.add_journal("You reached Phandalin, a hard-bitten frontier town under growing Ashen Brand pressure.")
            if self.state.flags.get("blackwake_completed"):
                self.describe_blackwake_phandalin_arrival()
            choice = self.scenario_choice(
                "How do you enter town?",
                [
                    self.quoted_option("INSIGHT", "I want to read the mood of the town before I speak."),
                    self.quoted_option("PERSUASION", "Let them know Neverwinter sent help."),
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
                        "Phandalin's fear points in three directions: the east road, the old manor hill, and the few locals still holding the place together."
                    )
                    self.add_clue(
                        "Old evacuation marks and nervous traffic patterns point toward Cinderfall Ruins, an abandoned relay east of Ashfall Watch."
                    )
                    self.unlock_act1_hidden_route(
                        "Reading Phandalin's fear exposes a third route: the abandoned Cinderfall Ruins, where Ashfall's reserve line still flickers behind the main road."
                    )
                    self.act1_adjust_metric("act1_town_fear", -1)
                    self.reward_party(xp=10, reason="reading Phandalin's mood on arrival")
                else:
                    self.say("The town's fear is real, but too tangled to untangle in one glance.")
            elif choice == 2:
                self.player_speaker("Let them know Neverwinter sent help.")
                success = self.skill_check(self.state.player, "Persuasion", 12, context="to steady the town's nerves")
                if success:
                    self.say("A few shoulders ease as your words sound more like a promise than a performance.")
                    self.act1_adjust_metric("act1_town_fear", -1)
                    self.reward_party(xp=10, gold=6, reason="reassuring Phandalin on arrival")
                else:
                    self.say("People listen, but frontier caution clings harder than hope.")
            else:
                self.player_action("Show me the tracks, barricades, and weak points first.")
                success = self.skill_check(self.state.player, "Investigation", 12, context="to assess the town's defenses")
                if success:
                    self.say("Fresh wagon ruts, anxious repairs, and redirected lanes give you a usable picture of how fear is reshaping the town.")
                    self.add_clue("Recent wagon ruts suggest the Ashen Brand watches both the east road and the manor-side lanes.")
                    self.reward_party(xp=10, reason="surveying Phandalin's defenses")
                else:
                    self.say("There are too many overlapping tracks and half-finished repairs for a quick clean read.")

        self.run_phandalin_council_event()
        self.run_after_watch_gathering()
        self._sync_story_beats_from_flags()
        self.maybe_offer_act1_personal_quests()
        self.maybe_resolve_bryn_loose_ends()
        self.maybe_run_act1_companion_conflict()

        while True:
            options: list[tuple[str, str]] = [
                ("steward", self.action_option("Report to Steward Tessa Harrow")),
                ("inn", self.action_option("Visit the Stonehill Inn")),
                ("shrine", self.action_option("Stop by the shrine of Tymora")),
                ("barthen", self.skill_tag("TRADE", self.action_option("Browse Barthen's Provisions"))),
                ("linene", self.skill_tag("TRADE", self.action_option("Call on Linene Graywind at the Lionshield trading post"))),
                ("orchard", self.action_option("Walk the old walls of Edermath Orchard")),
                ("exchange", self.action_option("Step into the Miner's Exchange")),
                ("camp", self.action_option("Return to camp")),
                ("rest", self.action_option("Take a short rest")),
            ]
            if not self.state.flags.get("old_owl_well_cleared"):
                label = self.action_option("Investigate Old Owl Well")
                if not self.can_visit_old_owl_well():
                    label = self.action_option("Investigate Old Owl Well (need a lead)")
                options.append(("old_owl", label))
            if not self.state.flags.get("wyvern_tor_cleared"):
                label = self.action_option("Hunt the raiders at Wyvern Tor")
                if not self.can_visit_wyvern_tor():
                    label = self.action_option("Hunt the raiders at Wyvern Tor (need a lead)")
                elif self.should_warn_for_wyvern_tor():
                    label = self.action_option(
                        f"Hunt the raiders at Wyvern Tor (recommended level {self.wyvern_tor_recommended_level()})"
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
                    label = self.action_option("Ride for Ashfall Watch (clear Old Owl Well and Wyvern Tor first)")
                options.append(("ashfall", label))
            elif not self.state.flags.get("tresendar_cleared"):
                label = self.action_option("Descend beneath Tresendar Manor")
                if not self.state.flags.get("tresendar_revealed"):
                    label = self.action_option("Descend beneath Tresendar Manor (wait for a firmer lead)")
                options.append(("tresendar", label))
            else:
                options.append(("emberhall", self.action_option("Descend into Emberhall Cellars")))

            backtrack_node = self.peek_act1_overworld_backtrack_node()
            if backtrack_node is not None:
                options.append(("backtrack", self.skill_tag("BACKTRACK", self.action_option(f"Backtrack to {backtrack_node.title}"))))

            choice = self.scenario_choice("Where do you go next?", [text for _, text in options])
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
            ("neverwinter", self.action_option("Return to Neverwinter with what you found.")),
            ("south", self.action_option("Press south toward the road to Phandalin.")),
            ("camp", self.action_option("Camp first, then decide.")),
        ]
        backtrack_node = self.peek_act1_overworld_backtrack_node()
        if backtrack_node is not None:
            options.append(("backtrack", self.skill_tag("BACKTRACK", self.action_option(f"Backtrack to {backtrack_node.title}"))))
        choice = self.scenario_choice("Where do you go now?", [text for _, text in options], allow_meta=False)
        selection_key, _ = options[choice - 1]
        if selection_key == "neverwinter":
            self.player_action("Return to Neverwinter with what you found.")
            self.state.flags["blackwake_return_destination"] = "neverwinter"
            self.speaker(
                "Mira Thann",
                "This is too close to the city to dismiss as frontier noise. Give me the names, the routes, and what you chose to leave standing.",
            )
            if not self.state.flags.get("blackwake_neverwinter_reported"):
                self.state.flags["blackwake_neverwinter_reported"] = True
                if resolution == "evidence":
                    self.reward_party(xp=20, gold=18, reason="bringing Blackwake proof back to Neverwinter")
                    self.say("Mira pays for the ledgers without pretending coin is the point.")
                elif resolution == "rescue":
                    self.add_inventory_item("potion_healing", 1, source="Mira's emergency stores")
                    self.say("Mira sends aid back toward the survivors before she finishes reading your account.")
                elif resolution == "sabotage":
                    self.add_inventory_item("antitoxin_vial", 1, source="a seized city-side medicine pouch")
                    self.say("Mira cannot prosecute ashes, but she can use the damage to tighten the next patrol net.")
            self.turn_in_quest("trace_blackwake_cell")
            self.say("With the report made, the south road waits again. The Phandalin writ is still yours to carry.")
            self.travel_to_act1_node("high_road_ambush")
            return
        if selection_key == "south":
            self.player_action("Press south toward the road to Phandalin.")
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
            self.say("The fire burns low. Blackwake is behind you; Neverwinter and Phandalin both still have claims on the morning.")
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
            self.return_to_phandalin(f"You withdraw from {node.title} and ride back to Phandalin to regroup.")
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
        handler(dungeon, room)

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
                self.say("You count the hired guards, the real loyalists, and the tent where the seals are being copied.")
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
                self.add_clue("A Reedbank lookout says someone in Neverwinter is paid to ignore missing toll seals.")
                self.say("The lookout gives up the cave name and keeps insisting the city side is not as clean as Mira hopes.")
        else:
            self.player_action("Copy the names and route marks before disturbing anything.")
            if self.skill_check(self.state.player, "Investigation", 12, context="to copy the forged route marks accurately"):
                self.state.flags["blackwake_route_names_copied"] = True
                self.state.flags["blackwake_forged_papers_found"] = True
                self.add_clue("Copied route marks tie Blackwake permits to a Neverwinter-facing paymaster mark.")
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
                self.add_clue("Copied Blackwake marks name route payments, seized cargo categories, and a future Phandalin pressure chain.")
                self.say("You take the names before the workshop loses its shape.")
            self.state.flags["blackwake_workshop_destroyed"] = True
        self.complete_map_room(dungeon, room.room_id)

    def _blackwake_ash_office(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say(
            "Sereth's ash office is a command room pretending to be a storeroom: partial Phandalin pressure routes, caravan hijack summaries, and a note about hobgoblin supervision farther south."
        )
        choice = self.scenario_choice(
            "Which record do you focus on?",
            [
                self.action_option("Trace the Phandalin pressure sites."),
                self.action_option("Read the caravan hijack summaries."),
                self.action_option("Search for the southern supervisor note."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Trace the Phandalin pressure sites.")
            self.state.flags["blackwake_phandalin_pressure_clue"] = True
            self.add_clue("Blackwake notes point to Phandalin pressure sites and supply timing, not isolated roadside theft.")
        elif choice == 2:
            self.player_action("Read the caravan hijack summaries.")
            self.state.flags["blackwake_caravan_hijack_clue"] = True
            self.add_clue("Blackwake summaries show selective theft: food, medicine, tools, and route authority are taken before luxuries.")
        else:
            self.player_action("Search for the southern supervisor note.")
            self.state.flags["blackwake_hobgoblin_supervision_clue"] = True
            self.add_clue("A Blackwake order references hobgoblin supervision farther south, foreshadowing the High Road and Ashfall chain.")
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
            self.add_clue("Blackwake ledgers prove organized route corruption from Neverwinter's edge toward Phandalin.")
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
        self.return_to_blackwake_decision("Blackwake Crossing is resolved. The choice now is whether its ashes go north to Mira or south toward Phandalin.")

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
            self.return_to_act2_hub(f"You withdraw from {node.title} and return to Phandalin's expedition table.")
            return

    def _run_act2_room(self, node_id: str, dungeon: DungeonMap, room: DungeonRoom) -> None:
        handlers = {
            ("stonehollow_dig", "survey_mouth"): self._stonehollow_survey_mouth,
            ("stonehollow_dig", "slime_cut"): self._stonehollow_slime_cut,
            ("stonehollow_dig", "warded_side_run"): self._stonehollow_warded_side_run,
            ("stonehollow_dig", "scholar_pocket"): self._stonehollow_scholar_pocket,
            ("stonehollow_dig", "collapse_lift"): self._stonehollow_collapse_lift,
            ("stonehollow_dig", "lower_breakout"): self._stonehollow_lower_breakout,
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
            ("forge_of_spells", "forge_threshold"): self._forge_threshold,
            ("forge_of_spells", "choir_pit"): self._forge_choir_pit,
            ("forge_of_spells", "pact_anvil"): self._forge_pact_anvil,
            ("forge_of_spells", "shard_channels"): self._forge_shard_channels,
            ("forge_of_spells", "resonance_lens"): self._forge_resonance_lens,
            ("forge_of_spells", "caldra_dais"): self._forge_caldra_dais,
        }
        handler = handlers[(node_id, room.room_id)]
        handler(dungeon, room)

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
        choice = self.scenario_choice(
            "How do you take the first measure of the dig?",
            [
                self.skill_tag("INVESTIGATION", self.action_option("Read the support lines and mark the one section that can still hold.")),
                self.skill_tag("ATHLETICS", self.action_option("Brace the lowest beam before the entry throat folds inward.")),
                self.skill_tag("ARCANA", self.action_option("Listen for the old Pact warding under the fresh collapse noise.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Read the support lines and mark the one section that can still hold.")
            if self.skill_check(self.state.player, "Investigation", 13, context="to read the dig braces under pressure"):
                self.state.flags["stonehollow_supports_stabilized"] = True
                self.reward_party(xp=10, reason="stabilizing Stonehollow's entry braces")
                self.say("You mark the honest braces and the whole entry stops feeling like a mouth about to close.")
            else:
                self.say("The support pattern is bad in too many places at once. You get through, but not cleanly.")
        elif choice == 2:
            self.player_action("Brace the lowest beam before the entry throat folds inward.")
            if self.skill_check(self.state.player, "Athletics", 13, context="to brace the collapsing entry"):
                self.state.flags["stonehollow_entry_braced"] = True
                self.apply_status(self.state.player, "emboldened", 1, source="holding Stonehollow's entry open")
                self.say("The beam groans, but you force it into usefulness long enough for the party to pass.")
            else:
                self.apply_status(self.state.player, "reeling", 1, source="Stonehollow's unstable entry")
                self.say("You keep the beam from killing anyone, but it takes a brutal shoulder and a shower of stone.")
        else:
            self.player_action("Listen for the old Pact warding under the fresh collapse noise.")
            if self.skill_check(self.state.player, "Arcana", 13, context="to hear the warded side-run beneath the collapse noise"):
                self.state.flags["stonehollow_ward_path_hint"] = True
                self.say("Beneath the bad echoes, one old ward still answers in a steady pattern. There is a cleaner side-run somewhere below.")
            else:
                self.say("The echoes answer, but not in any pattern you can trust yet.")
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
            "The side-run is narrower and older than the main dig, lined with Pact scratches that have survived better than the new timber."
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
            self.reward_party(xp=10, reason="reading Stonehollow's Pact warding")
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
                "If you're the reason I'm not dying under my own survey notes, I should probably stop pretending I can solve Wave Echo by myself.",
            )
            recruit = self.scenario_choice(
                "Nim gathers his satchel and looks between you and the ruined lane.",
                [
                    self.quoted_option("RECRUIT", "Then walk with us and keep the maps honest."),
                    self.quoted_option("SAFE", "Get back to Phandalin and recover. We can talk there."),
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
                    "reading the Pact warding correctly keeps one more part of the cave from teaching through panic",
                )
        self.return_to_act2_hub("Stonehollow exhales stone dust behind you, and the rescued survey truth finally reaches the expedition table.")

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
                "Broken Prospect is a jagged approach above Wave Echo Cave: half collapsed survey cut, half old dwarfwork scar, "
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
            if self.skill_check(self.state.player, "History", 14, context="to use the Pact survey marks correctly"):
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
        self.say("The Pact markers cut across stone, timber, and old claim stakes, half survey language and half warning prayer.")
        dc = 13 if self.state.flags.get("prospect_shelf_marks_read") or self.state.flags.get("nim_countermeasure_notes") else 14
        choice = self.scenario_choice(
            "How do you make the markers useful?",
            [
                self.skill_tag("HISTORY", self.action_option("Read the dwarfwork survey order and call the true span.")),
                self.skill_tag("INVESTIGATION", self.action_option("Compare new claim scratches against the older route logic.")),
                self.skill_tag("ARCANA", self.action_option("Find the parts of the marking that still answer old Pact law.")),
            ],
            allow_meta=False,
        )
        skill = "History" if choice == 1 else "Investigation" if choice == 2 else "Arcana"
        if self.skill_check(self.state.player, skill, dc, context="to decode Broken Prospect's Pact markers"):
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
                description="Delayed claimants and Choir scouts try to keep the cleaner Wave Echo approach from returning to your map.",
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
        enemies = [create_enemy("animated_armor")]
        if self.act2_metric_value("act2_whisper_pressure") >= 4:
            enemies.append(self.act2_pick_enemy(("obelisk_eye", "iron_prayer_horror")))
        elif len(self.state.party_members()) >= 4:
            enemies.append(self.act2_pick_enemy(("cult_lookout", "grimlock_tunneler", "starblighted_miner")))
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
                description="Old Pact armor tests the party before the cave approach can become a true route.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The sentinel span holds and Wave Echo's threshold throws the company back.")
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
            enemies.insert(0, create_enemy("animated_armor"))
        if delayed or self.act2_metric_value("act2_route_control") <= 2:
            enemies.append(self.act2_pick_enemy(("cult_lookout", "iron_prayer_horror", "obelisk_eye")))
        if len(self.state.party_members()) >= 4:
            enemies.append(self.act2_pick_enemy(("cult_lookout", "grimlock_tunneler", "starblighted_miner")))
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
            if self.skill_check(self.state.player, "History", 14, context="to use the Pact survey marks correctly"):
                hero_bonus += 2
        elif choice == 2:
            self.player_action("Use the broken prospect ledge and hit the foreman from the blind side.")
            if self.skill_check(self.state.player, "Stealth", 14, context="to slip into Wave Echo cleanly"):
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
                description="The first Wave Echo guardians still answer old duties, even now that new masters are twisting them.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("Wave Echo's threshold throws the company back into the dark above.")
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
        self.return_to_act2_hub("Broken Prospect finally resolves into a real route, and Wave Echo has one less way to lie about where it begins.")

    def _south_adit_delayed(self) -> bool:
        assert self.state is not None
        return self.state.flags.get("act2_first_late_route") == "broken_prospect"

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
                "The Quiet Choir has not just occupied Wave Echo. It has been sorting people here.",
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
                self.quoted_option("SAFE", "Get topside and breathe real air first. We will speak in camp."),
            ],
            allow_meta=False,
        )
        self.recruit_companion(create_irielle_ashwake())
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
            self.reward_party(xp=15, reason="making contact with Irielle in the South Adit")
            self.say("The counter-cadence catches. For the first time in the adit, the wall sounds like stone instead of a mouth.")
        else:
            self.say("Irielle still understands enough to move, but the cadence keeps some of its teeth.")
        self._south_adit_recruit_irielle(delayed=delayed)
        self.complete_act2_map_room(dungeon, room.room_id)

    def _south_adit_warden_nave(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        delayed = self._south_adit_delayed()
        enemies = [create_enemy("starblighted_miner"), create_enemy("choir_adept")]
        if delayed:
            enemies.append(self.act2_pick_enemy(("cult_lookout", "oathbroken_revenant")))
        elif len(self.state.party_members()) >= 4:
            enemies.append(self.act2_pick_enemy(("cult_lookout", "choir_executioner")))
        if len(self.state.party_members()) >= 4:
            enemies.append(self.act2_pick_enemy(("cult_lookout", "grimlock_tunneler", "starblighted_miner")))

        hero_bonus = self.apply_scene_companion_support("south_adit")
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

        choice = self.scenario_choice(
            "How do you crack the prison line?",
            [
                self.skill_tag("SLEIGHT OF HAND", self.action_option("Open the last cells quietly and arm the captives before the wardens know.")),
                self.skill_tag("INTIMIDATION", self.action_option("Hit the wardens hard enough that the prisoners remember your side instead.")),
                self.skill_tag("MEDICINE", self.action_option("Go for the weakest captives first and keep the line from becoming a slaughter.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Open the last cells quietly and arm the captives before the wardens know.")
            if self.skill_check(self.state.player, "Sleight of Hand", 14, context="to free the first prisoners without raising the line"):
                hero_bonus += 2
                self.apply_status(enemies[1], "surprised", 1, source="the cells opening behind them")
        elif choice == 2:
            self.player_action("Hit the wardens hard enough that the prisoners remember your side instead.")
            if self.skill_check(self.state.player, "Intimidation", 14, context="to crack the adit's prison discipline"):
                hero_bonus += 1
        else:
            self.player_action("Go for the weakest captives first and keep the line from becoming a slaughter.")
            if self.skill_check(self.state.player, "Medicine", 14, context="to keep the rescue from turning into a panic crush"):
                hero_bonus += 1
                self.apply_status(self.state.player, "blessed", 1, source="saving the vulnerable first")

        outcome = self.run_encounter(
            Encounter(
                title="South Adit Wardens",
                description="The prison line beneath Wave Echo tries to bury witnesses before the truth can get out.",
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
        if delayed:
            self.state.flags["act2_captive_outcome"] = "few_saved"
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
        self.return_to_act2_hub("The South Adit prison line breaks open behind you, and its survivors carry the first hard proof of the Choir back toward Phandalin.")

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
            if self.skill_check(self.state.player, "Investigation", 14, context="to read Wave Echo's outer rail junction"):
                self.state.flags["outer_survey_marks_read"] = True
                self.say("The false marks fall away from the real route, at least for this first junction.")
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
                title="Wave Echo Slime Sluice",
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
                self.skill_tag("PERCEPTION", self.action_option("Count the echoes until the real breathing separates from the false.")),
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
            self.player_action("Count the echoes until the real breathing separates from the false.")
            if self.skill_check(self.state.player, "Perception", 14, context="to hear the real side-run ambush"):
                hero_bonus += 2
        outcome = self.run_encounter(
            Encounter(
                title="Wave Echo Grimlock Side-Run",
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
            self.reward_party(xp=10, reason="reopening Wave Echo's collapsed crane route")
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
                self.skill_tag("INVESTIGATION", self.action_option("Mark every repeated echo until the real path is the only one left.")),
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
                    title="Wave Echo False Echo Loop",
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
            if self.skill_check(self.state.player, "Investigation", 14, context="to keep the party on the real line through false echoes"):
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
                description="Wave Echo's outer defenses are now a mix of scavengers, predators, and bad old engineering.",
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
            "the company now owns a real line through Wave Echo's outer galleries",
        )
        self.return_to_act2_hub("Wave Echo's outer galleries settle behind you into a route the expedition can actually hold.")

    def _black_lake_causeway_lip(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        if not self.has_quest("sever_quiet_choir"):
            self.grant_quest("sever_quiet_choir")
        if not self.state.flags.get("black_lake_seen"):
            self.say(
                "The old black water cuts the cave in half beneath a narrow causeway of stone and broken dwarfwork. A drowned shrine leans off one side. "
                "A cult barracks squats on the other. This is the last clean threshold before the Forge of Spells, and the Quiet Choir knows it.",
                typed=True,
            )
            self.state.flags["black_lake_seen"] = True
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
                self.add_clue("A thin thread of older sanctity still answers at Black Lake's drowned shrine, which means the crossing is not fully the Choir's yet.")
                self.reward_party(xp=10, reason="reading the drowned shrine before the crossing")
        elif choice == 2:
            self.player_action("Count the barracks watches and messenger lanes before you start crossing openly.")
            if self.skill_check(self.state.player, "Stealth", 14, context="to read the barracks watches without becoming part of the report"):
                self.state.flags["black_lake_barracks_watch_read"] = True
                self.reward_party(xp=10, reason="mapping the Black Lake barracks watches")
        else:
            self.player_action("Test the anchor pull and learn where the causeway can be made to lurch.")
            if self.skill_check(self.state.player, "Athletics", 14, context="to feel where the old line will break before it throws you with it"):
                self.state.flags["black_lake_anchor_stress_read"] = True
                self.reward_party(xp=10, reason="reading the causeway's anchor strain")
        self.complete_act2_map_room(dungeon, room.room_id)

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
            self.apply_status(self.state.player, "blessed", 2, source="the reclaimed Black Lake shrine")
            self.add_clue("The drowned shrine still answers an older sanctity, which means the Forge route has not been fully rewritten by the Quiet Choir.")
            self.reward_party(xp=15, reason="reclaiming the drowned shrine cleanly")
        else:
            self.say("The shrine answers, but only after taking a little more of the lake's cold into your bones than you wanted.")

    def _black_lake_choir_barracks(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        enemies = [create_enemy("cult_lookout"), create_enemy("choir_adept")]
        if self.act2_metric_value("act2_whisper_pressure") >= 4:
            enemies.append(self.act2_pick_enemy(("starblighted_miner", "obelisk_eye", "blacklake_pincerling")))
        elif len(self.state.party_members()) >= 4 or self.act2_metric_value("act2_route_control") <= 2:
            enemies.append(self.act2_pick_enemy(("starblighted_miner", "blacklake_pincerling", "cult_lookout")))
        hero_bonus = self.apply_scene_companion_support("black_lake_causeway")
        if self.state.flags.get("black_lake_barracks_watch_read"):
            hero_bonus += 1
            self.apply_status(enemies[0], "surprised", 1, source="you entered on the barracks blind side")
        choice = self.scenario_choice(
            "How do you strip the barracks?",
            [
                self.skill_tag("STEALTH", self.action_option("Cut the messengers first and keep the barracks from warning the far side.")),
                self.skill_tag("INVESTIGATION", self.action_option("Take the rota boards and reserve orders before the fighting scatters them.")),
                self.skill_tag("ATHLETICS", self.action_option("Turn the weapon racks and bunks into a collapsing choke point.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Cut the messengers first and keep the barracks from warning the far side.")
            if self.skill_check(self.state.player, "Stealth", 14, context="to kill the Black Lake message chain before it runs"):
                hero_bonus += 2
                self.apply_status(enemies[1], "surprised", 1, source="their messengers dropped first")
        elif choice == 2:
            self.player_action("Take the rota boards and reserve orders before the fighting scatters them.")
            if self.skill_check(self.state.player, "Investigation", 14, context="to seize the barracks orders intact"):
                hero_bonus += 1
                self.state.flags["black_lake_barracks_orders_taken"] = True
                self.add_clue("Black Lake barracks orders confirm the Quiet Choir keeps its last reserve line on the Forge side of the crossing.")
        else:
            self.player_action("Turn the weapon racks and bunks into a collapsing choke point.")
            if self.skill_check(self.state.player, "Athletics", 14, context="to make the barracks collapse inward on its own defenders"):
                hero_bonus += 1
                self.apply_status(enemies[0], "prone", 1, source="the barracks caving around them")
        outcome = self.run_encounter(
            Encounter(
                title="Black Lake Barracks",
                description="The Quiet Choir's last organized staging room before the Forge has to be broken or stripped.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The barracks holds, and the far side of Black Lake stays reinforced.")
            return
        if outcome == "fled":
            self.return_to_act2_hub("You fall back from the Black Lake barracks before the whole crossing turns against you.")
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
            self.reward_party(xp=15, reason="sabotaging the Black Lake anchors cleanly")
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
            self.apply_status(self.state.player, "blessed", 1, source="the Black Lake shrine")
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
                self.apply_status(self.state.player, "emboldened", 2, source="forcing the Black Lake edge")
        outcome = self.run_encounter(
            Encounter(
                title="Black Lake Waterline",
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
        enemies = [create_enemy("animated_armor"), create_enemy("starblighted_miner")]
        if len(self.state.party_members()) >= 4 or self.act2_metric_value("act2_whisper_pressure") >= 4:
            enemies.append(self.act2_pick_enemy(("spectral_foreman", "blacklake_pincerling", "duskmire_matriarch", "obelisk_eye")))
        if len(self.state.party_members()) >= 4:
            enemies.append(self.act2_pick_enemy(("cult_lookout", "starblighted_miner", "blacklake_pincerling")))
        elif not self.state.flags.get("black_lake_barracks_raided"):
            enemies.append(self.act2_pick_enemy(("cult_lookout", "choir_adept", "starblighted_miner")))
        hero_bonus = self.apply_scene_companion_support("black_lake_causeway")
        if self.state.flags.get("black_lake_shrine_purified"):
            hero_bonus += 1
            self.apply_status(self.state.player, "blessed", 2, source="the reclaimed Black Lake shrine")
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
            if self.skill_check(self.state.player, "Athletics", 14, context="to turn the shaking causeway into your advantage"):
                hero_bonus += 2
                self.apply_status(self.state.player, "emboldened", 2, source="forcing the far landing")
        outcome = self.run_encounter(
            Encounter(
                title="Black Lake Causeway",
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
        self.reward_party(xp=55, gold=15, reason="crossing the Black Lake causeway")
        self.add_journal("You crossed the Black Lake causeway and opened the last clean approach to the Forge of Spells.")
        self.return_to_act2_hub("The Black Lake causeway is finally yours, and the Forge lies open on the far side.")

    def _forge_threshold(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        if not self.state.flags.get("forge_seen"):
            self.say(
                "The Forge of Spells is no longer just a lost wonder. The Quiet Choir has turned it into an instrument. "
                "Shards hum inside old channels, the air sounds wrong when it moves, and the whole chamber feels like it is listening for the next hand bold enough to strike it.",
                typed=True,
            )
            if self.state.flags.get("black_lake_shrine_purified"):
                self.say("The answered sanctity from Black Lake keeps one line through the chamber sounding like craft instead of hunger.")
            if self.state.flags.get("black_lake_barracks_orders_taken"):
                self.say("The stolen barracks orders mark which choir lanes were supposed to reinforce the forge and which ones were only meant to witness.")
            elif self.state.flags.get("black_lake_barracks_raided"):
                self.say("Because you stripped the barracks on the crossing, the forge's outer support rhythm is thinner than Caldra expected.")
            if self.state.flags.get("black_lake_causeway_shaken"):
                self.say("The force you fed into the causeway still travels through the old foundations. The shard channels are venting on a rhythm instead of a mystery.")
            self.state.flags["forge_seen"] = True
        if (
            self.act2_metric_value("act2_whisper_pressure") >= 4
            or self.state.flags.get("black_lake_causeway_shaken")
            or self.state.flags.get("black_lake_anchor_weak_point_found")
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
            dc = 13 if self.state.flags.get("black_lake_barracks_orders_taken") else 14
            self.player_action("Lay the stolen support routes over the chamber and find the choir's real traffic line.")
            if self.skill_check(self.state.player, "Investigation", dc, context="to read the forge's real support traffic"):
                self.state.flags["forge_threshold_orders_read"] = True
                self.add_clue("The Forge's real reinforcement traffic still runs through the choir pit, which means Caldra's dais is not the only thing holding her ritual up.")
                self.add_journal("You used the Black Lake orders to read the Forge threshold and find the chamber's real support traffic.")
                self.reward_party(xp=10, reason="reading the forge support routes")
        elif choice == 2:
            dc = 13 if self.state.flags.get("black_lake_shrine_purified") else 14
            self.player_action("Carry the shrine's answered sanctity forward before the forge swallows the last of it.")
            if self.skill_check(self.state.player, "Religion", dc, context="to carry clean sanctity into the forge threshold"):
                self.state.flags["forge_threshold_sanctified"] = True
                self.apply_status(self.state.player, "blessed", 1, source="the Black Lake shrine carried into the Forge")
                self.add_journal("You carried Black Lake's answered sanctity across the Forge threshold and kept one lane of the chamber honest.")
                self.reward_party(xp=10, reason="sanctifying the forge threshold")
        else:
            dc = 13 if self.state.flags.get("black_lake_causeway_shaken") or self.state.flags.get("black_lake_anchor_weak_point_found") else 14
            self.player_action("Time the shard surges and learn which pulse the chamber cannot hide.")
            if self.skill_check(self.state.player, "Arcana", dc, context="to read the shard surges before they settle"):
                self.state.flags["forge_threshold_shard_timing"] = True
                self.state.flags["forge_shard_route_exposed"] = True
                self.add_clue("The force you fed into the Black Lake foundations has exposed a shard vent that Caldra was relying on the chamber to keep hidden.")
                self.add_journal("You timed the Forge's shard surges and exposed a side route the chamber was trying to keep buried.")
                self.reward_party(xp=10, reason="timing the forge shard surges")
        self.complete_act2_map_room(dungeon, room.room_id)

    def _forge_choir_pit(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        enemies = [create_enemy("choir_adept"), create_enemy("cult_lookout")]
        if not self.state.flags.get("black_lake_barracks_raided"):
            enemies.append(self.act2_pick_enemy(("cult_lookout", "choir_executioner", "starblighted_miner")))
        if len(self.state.party_members()) >= 4:
            enemies.append(self.act2_pick_enemy(("cult_lookout", "choir_executioner", "starblighted_miner")))
        elif self.act2_metric_value("act2_whisper_pressure") >= 4:
            enemies.append(self.act2_pick_enemy(("obelisk_eye", "starblighted_miner", "iron_prayer_horror")))
        hero_bonus = self.apply_scene_companion_support("forge_of_spells")
        if self.state.flags.get("black_lake_barracks_raided"):
            hero_bonus += 1
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
            "An old Pact anvil sits inside the Forge's newer desecration like a discipline the chamber still cannot quite kill. Heat moves through it in patient lines instead of hungry bursts."
        )
        dc = 15
        if self.state.flags.get("agatha_truth_clear"):
            dc -= 1
        if self.state.flags.get("nim_countermeasure_notes"):
            dc -= 1
        if self.state.flags.get("black_lake_shrine_purified") or self.state.flags.get("forge_threshold_sanctified"):
            dc -= 1
        choice = self.scenario_choice(
            "How do you work the Pact anvil?",
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
            tuned = self.skill_check(self.state.player, "Religion", dc, context="to wake the older Pact discipline in the anvil")
        self.complete_act2_map_room(dungeon, room.room_id)
        if tuned:
            self.state.flags["forge_anvil_tuned"] = True
            if self.state.flags.get("south_adit_counter_cadence_learned") and self.find_companion("Irielle Ashwake") is not None:
                self.state.flags["irielle_counter_cadence"] = True
            self.add_clue("The Pact anvil still carries a discipline that can crack the Choir's forge-tempo if you hit it cleanly.")
            self.add_journal("You woke the Pact anvil's older discipline and proved the Forge still remembers craft beneath the Choir's ritual.")
            self.reward_party(xp=15, reason="recovering the Forge's older rhythm")
        else:
            self.say("The anvil answers, but not cleanly enough to become certainty on its own.")

    def _forge_shard_channels(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        enemies = [create_enemy("obelisk_eye"), create_enemy("starblighted_miner")]
        if self.act2_metric_value("act2_whisper_pressure") >= 4:
            enemies.append(self.act2_pick_enemy(("iron_prayer_horror", "obelisk_eye", "starblighted_miner")))
        elif len(self.state.party_members()) >= 4:
            enemies.append(self.act2_pick_enemy(("cult_lookout", "starblighted_miner", "obelisk_eye")))
        hero_bonus = self.apply_scene_companion_support("forge_of_spells")
        if self.state.flags.get("black_lake_causeway_shaken"):
            hero_bonus += 1
            self.apply_status(enemies[0], "reeling", 1, source="the causeway shock still running through the foundations")
        if self.state.flags.get("black_lake_anchor_weak_point_found") or self.state.flags.get("forge_threshold_shard_timing"):
            hero_bonus += 1
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
        self.add_clue("The shard channels were feeding the Forge from a deeper pressure seam, not just from Caldra's platform.")
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
        dc = 15
        if self.state.flags.get("black_lake_shrine_purified"):
            dc -= 1
        if self.state.flags.get("black_lake_barracks_orders_taken"):
            dc -= 1
        if self.state.flags.get("black_lake_causeway_shaken") or self.state.flags.get("black_lake_anchor_weak_point_found"):
            dc -= 1
        if self.state.flags.get("forge_anvil_tuned"):
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
            if self.state.flags.get("forge_choir_pit_silenced"):
                self.state.flags["forge_support_line_broken"] = True
            if self.state.flags.get("forge_pact_rhythm_found"):
                self.state.flags["forge_ritual_line_broken"] = True
            if self.state.flags.get("forge_shard_channels_disrupted"):
                self.state.flags["forge_shard_line_broken"] = True
            self.add_clue("The resonance lens only held because Caldra was braiding witness, ritual, and shard pressure into one engineered lie.")
            self.add_journal("You mapped the resonance lens from inside and learned exactly which lines were keeping Caldra's certainty standing.")
            self.reward_party(xp=15, reason="mapping the resonance lens before the final confrontation")
        else:
            self.say("You map enough of the lens to reach Caldra, but not enough to pretend the chamber is done with surprises.")

    def _forge_caldra_dais(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        enemies = [create_enemy("caldra_voss"), create_enemy("choir_adept")]
        if len(self.state.party_members()) >= 4:
            enemies.append(self.act2_pick_enemy(("cult_lookout", "starblighted_miner", "choir_executioner")))
        if self.state.flags.get("black_lake_barracks_raided") and len(self.state.party_members()) >= 4:
            enemies.append(self.act2_pick_enemy(("cult_lookout", "starblighted_miner")))
        elif not self.state.flags.get("black_lake_barracks_raided"):
            enemies.append(self.act2_pick_enemy(("cult_lookout", "choir_executioner", "starblighted_miner")))
        if self.act2_metric_value("act2_whisper_pressure") >= 4:
            enemies.append(self.act2_pick_enemy(("starblighted_miner", "obelisk_eye", "iron_prayer_horror")))

        hero_bonus = self.apply_scene_companion_support("forge_of_spells")
        parley_dc = 15
        if self.state.flags.get("black_lake_shrine_purified") or self.state.flags.get("forge_threshold_sanctified"):
            self.apply_status(self.state.player, "blessed", 2, source="the reclaimed Black Lake shrine")
            hero_bonus += 1
            parley_dc -= 1
        if self.state.flags.get("black_lake_barracks_orders_taken") or self.state.flags.get("forge_lens_support_line_named"):
            hero_bonus += 1
            if len(enemies) > 1:
                enemies[1].current_hp = max(1, enemies[1].current_hp - 4)
        if self.state.flags.get("black_lake_causeway_shaken") or self.state.flags.get("forge_shard_channels_disrupted"):
            hero_bonus += 1
            if len(enemies) > 1:
                self.apply_status(enemies[1], "reeling", 1, source="the forge foundations never fully settled")
        if self.state.flags.get("forge_anvil_tuned") or self.state.flags.get("forge_ritual_line_broken"):
            hero_bonus += 1
            enemies[0].current_hp = max(1, enemies[0].current_hp - 6)
        if self.state.flags.get("south_adit_counter_cadence_learned") and self.find_companion("Irielle Ashwake") is not None:
            self.state.flags["irielle_counter_cadence"] = True
        if self.state.flags.get("irielle_counter_cadence"):
            hero_bonus += 1
            enemies[0].current_hp = max(1, enemies[0].current_hp - 4)
            self.say("Irielle's counter-cadence lands first and steals part of the forge's certainty before steel ever crosses it.")
            parley_dc -= 1

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
            self.apply_status(self.state.player, "emboldened", 2, source="storming the Forge of Spells")
            if self.state.flags.get("act2_sponsor") == "lionshield":
                hero_bonus += 1
        outcome = self.run_encounter(
            Encounter(
                title="Boss: Sister Caldra Voss",
                description="The Quiet Choir's cult agent makes the final stand at the Forge of Spells.",
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
                "Even broken, the Forge keeps trying to answer a call from farther down. The party is not leaving Wave Echo with clean silence."
            )
        self.add_journal("You broke Sister Caldra Voss and tore the Forge of Spells out of the Quiet Choir's grip.")
        self.reward_party(xp=120, gold=40, reason="breaking the Quiet Choir's Wave Echo cell")
        self.act2_record_epilogue_flags()
        self.return_to_act2_hub("The Forge's wrong song breaks apart behind you, and Wave Echo finally sounds like a place instead of an instrument.")

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
                title="Old Owl Well Dig Ring",
                description="Bone-haulers and animated sentries close around the well mouth.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The dead keep their watch at Old Owl Well.")
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
                self.add_clue("A rescued prospector says the gravecaller at Old Owl Well was being paid through Ashfall Watch for work tied to the manor hill.")
                self.reward_party(xp=10, reason="saving the prospector at Old Owl Well")
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
                self.add_clue("The Old Owl Well notes point to Ashfall Watch as the collection point for salvage moved toward the manor hill.")
                self.reward_party(xp=10, reason="securing the Old Owl Well route notes")
            else:
                self.say("You save fragments, but the ugliest details go spinning away with the dust.")
        elif choice == 2:
            self.player_speaker("The ink itself looks wrong. I want to know what was mixed into it.")
            success = self.skill_check(self.state.player, "Arcana", 12, context="to read the tainted route slips")
            if success:
                self.say("The ash-ink still carries the smell of the signal basin at Ashfall, which ties the sites together even more cleanly.")
                self.add_clue("The trench notes were written in the same treated ash used by Ashfall Watch's signaling crews.")
                self.reward_party(xp=10, reason="decoding the tainted ledgers at Old Owl Well")
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
        self.unlock_act1_hidden_route(
            "The soot-black route slips expose a hidden approach: Cinderfall Ruins, an abandoned ember relay still feeding Ashfall's reserve line."
        )
        self.complete_map_room(dungeon, room.room_id)

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
                description="The gravecaller of Old Owl Well fights from the lip of the buried dark.",
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
            self.return_to_phandalin("You break contact and retreat to Phandalin with the well still active behind you.")
            return

        self.act1_adjust_metric("act1_ashen_strength", -1)
        self.complete_map_room(dungeon, room.room_id)
        self.add_clue("Old Owl Well is cleared, and its notes tie grave-salvage, Ashfall Watch, and the manor hill into one supply chain.")
        self.add_journal("You silenced Old Owl Well and broke one of the Ashen Brand's outer operations.")
        self.refresh_quest_statuses(announce=False)
        self.add_inventory_item("scroll_lesser_restoration", source="Vaelith's ritual satchel")
        self.return_to_phandalin("Old Owl Well falls quiet behind you as the road back to Phandalin opens again.")

    def _wyvern_goat_path(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        if not self.state.flags.get("wyvern_tor_seen"):
            self.say(
                "Wyvern Tor looms out of the hills in broken shelves of wind-cut stone. Goat paths, old watch cairns, and smoke-stained hollows twist around the ridge, "
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
            success = self.skill_check(self.state.player, "Survival", 13, context="to take the hidden path up Wyvern Tor")
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
                title="Wyvern Tor Shelf Fight",
                description="Orc raiders and a hunting worg defend the tor's outer shelf.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("Wyvern Tor keeps the high ground and the road below it.")
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
                self.add_clue("A captured drover confirms Brughor holds Wyvern Tor with an ogre and a small disciplined raiding party.")
                self.reward_party(xp=10, reason="saving the captured drover at Wyvern Tor")
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
            self.say("The drover staggers away with a stolen knife and a promise to tell Phandalin exactly what waits on this hill.")

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
            self.say("The drover leaves fast, taking one true account of Wyvern Tor back toward people who still have time to listen.")
        elif followup == 2:
            self.player_action("Keep them hidden below the shelf to signal when Brughor commits his line.")
            self.state.flags["wyvern_spotter_signal"] = True
            self.say("The drover slips into a crack in the rock with a shepherd's whistle and a look that promises they will use it at the exact right second.")
        else:
            self.player_action("Have them loose the remaining beasts uphill and turn the camp against itself.")
            self.state.flags["wyvern_beast_stampede"] = True
            self.say("A moment later the upper shelf erupts in bells, hooves, and furious shouting as the pack animals tear through the camp line.")
        self.add_clue("The rescued drover heard raiders talk about Cinderfall, an abandoned relay they used to keep Ashfall supplied off the main road.")
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
                self.reward_party(xp=10, reason="restoring the shrine on Wyvern Tor")
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
                description="The blood-chief of Wyvern Tor makes his stand on the broken high shelf.",
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
            self.return_to_phandalin("You pull clear of the upper shelf and retreat to Phandalin to regroup.")
            return

        self.act1_adjust_metric("act1_ashen_strength", -1)
        self.complete_map_room(dungeon, room.room_id)
        self.add_clue("Wyvern Tor is cleared, and its raiders were coordinating with Ashfall Watch rather than acting alone.")
        self.add_journal("You broke the raiders at Wyvern Tor and stripped another outer shield away from the Ashen Brand.")
        self.refresh_quest_statuses(announce=False)
        self.add_inventory_item("greater_healing_draught", source="Brughor's travel chest")
        self.return_to_phandalin("Wyvern Tor falls behind you as the ridge wind finally goes clean.")

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
        self.add_clue("Destroying the Cinderfall relay cuts Ashfall Watch off from its reserve line and emergency signal fuel.")
        self.add_journal("You broke the hidden Cinderfall relay before the Ashfall assault.")
        self.reward_party(xp=35, gold=12, reason="breaking the Cinderfall relay")
        self.return_to_phandalin("Cinderfall goes dark behind you. Whatever waits at Ashfall will now be doing it with thinner reserves and worse timing.")

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
            self.return_to_phandalin("You fall back to Phandalin to rethink the assault.")
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
                self.say("You smother the basin under wet tarp and grit. No help is coming from the ridge in time to matter.")
            else:
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
                self.say("You smother the basin under wet tarp and grit. No help is coming from the ridge in time to matter.")
            else:
                self.say("You kill the signal late and loud, but late still counts for something.")
        elif choice == 2:
            self.player_speaker("The wind is shifting. I can use it to turn the smoke back into the yard.")
            success = self.skill_check(self.state.player, "Survival", 12, context="to use the crosswind against the signal basin")
            if success:
                self.say("The smoke whips back into the yard and wrecks the timing of anyone still trying to form a line.")
                self.reward_party(xp=10, reason="turning Ashfall's signal smoke back on the fort")
            else:
                self.say("The wind helps, but not cleanly enough to hide the sabotage.")
        else:
            self.player_action("Kick the braziers apart and drown the whole thing in grit.")
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
        choice = self.scenario_choice(
            "Rukhar raises his blade and waits to see how you answer.",
            [
                self.quoted_option("INTIMIDATION", "Surrender the yard in Phandalin's name."),
                self.quoted_option("PERSUASION", "Your paymaster is already losing. Walk away with the people who still can."),
                self.action_option("Strike before he can settle the shield line."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_speaker("Surrender the yard in Phandalin's name.")
            success = self.skill_check(self.state.player, "Intimidation", 13, context="to crack Rukhar's command posture")
            if success:
                boss_enemies[0].current_hp = max(1, boss_enemies[0].current_hp - 4)
                self.apply_status(boss_enemies[0], "frightened", 1, source="your iron-edged demand")
                self.say("Rukhar's line tightens too hard, which is its own kind of weakness.")
            else:
                self.apply_status(boss_enemies[0], "emboldened", 2, source="your failed demand")
                self.speaker("Rukhar Cinderfang", "Good. You arrived with a spine.")
        elif choice == 2:
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
            self.return_to_phandalin("You escape the watchtower and retreat to Phandalin to regroup.")
            return

        self.complete_map_room(dungeon, room.room_id)
        self.add_clue("Rukhar carried a soot-black key stamped with the Tresendar crest and orders to move captives beneath the manor hill.")
        self.add_journal("Ashfall Watch is broken, but the Ashen Brand's cellar routes beneath Phandalin are still active.")
        self.refresh_quest_statuses(announce=False)
        self.say(
            "Among Rukhar's orders you find a blackened key bearing the Tresendar crest, prisoner transfer notes, and references to a deeper reserve called Emberhall. "
            "The field base is broken, but the gang's thinking parts are still below town."
        )
        self.return_to_phandalin("Ashfall Watch breaks under the assault, and the road home finally opens.")

    def _tresendar_hidden_stair(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        self.say(
            "The ruined manor crouches over Phandalin like a memory that never learned to stay buried. Beneath the broken shell, a hidden stair drops into wet stone, cistern corridors, and ash-marked cellars where the Ashen Brand keeps its quieter work.",
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
            if success:
                self.say("You find the concealed stair and enter on the defenders' blind side.")
            else:
                self.say("You find the route, just not before the noise of the search carries below.")
        elif choice == 2:
            self.player_action("Slip through the collapsed chapel side and into the cellars.")
            success = self.skill_check(self.state.player, "Stealth", 13, context="to cross the broken chapel without warning the cellars")
            self.state.flags["tresendar_chapel_entry"] = success
            if success:
                self.say("You come through the chapel rubble already moving and the first lookout never gets set.")
            else:
                self.apply_status(self.state.player, "reeling", 1, source="a falling stone saint-head")
                self.say("A broken stone saint tumbles and announces you to the lower rooms.")
        else:
            self.player_action("Rip the old cistern grate open and take the straight drop.")
            success = self.skill_check(self.state.player, "Athletics", 13, context="to force the old grate without losing balance on the drop")
            self.state.flags["tresendar_cistern_breach"] = success
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
                title="Tresendar Cellars",
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
            self.handle_defeat("The buried manor swallows the party beneath Phandalin.")
            return
        if outcome == "fled":
            self.return_to_phandalin("You pull back from the manor tunnels before the whole cellar network can close around you.")
            return

        self.complete_map_room(dungeon, room.room_id)
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
                self.say("The papers make it plain: Tresendar was only the intake route, not the final refuge.")
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

    def _tresendar_nothic_lair(self, dungeon: DungeonMap, room: DungeonRoom) -> None:
        assert self.state is not None
        party_size = self.act1_party_size()
        second_enemies = [create_enemy("nothic", name="Cistern Eye")]
        if party_size >= 3:
            second_enemies.append(self.act1_pick_enemy(("skeletal_sentry", "stonegaze_skulker", "whispermaw_blob", "lantern_fen_wisp")))
        if party_size >= 4:
            second_enemies.append(self.act1_pick_enemy(("stonegaze_skulker", "whispermaw_blob", "graveblade_wight")))
        boss_bonus = int(self.state.flags.get("tresendar_eye_read", False)) + (2 if self.state.flags.get("tresendar_eye_ambushed", False) else 0)
        outcome = self.run_encounter(
            Encounter(
                title="The Cistern Eye",
                description="A warped cellar horror rises from the dark water below Tresendar Manor.",
                enemies=second_enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=boss_bonus,
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
        self.add_clue("Tresendar Manor was the Ashen Brand's intake route; Varyn's remaining core has withdrawn into Emberhall below.")
        self.add_journal("You cleared the buried Tresendar route and confirmed Varyn has fallen back to Emberhall for the final stand.")
        if not self.state.flags.get("tresendar_records_secured"):
            self.add_inventory_item("scroll_arcane_refresh", source="a sealed coffer in the cistern alcove")
        self.return_to_phandalin("The cistern goes still, and the buried route beneath Tresendar finally breaks open.")

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
        choice = self.scenario_choice(
            "What do you do in the lull?",
            [
                self.quoted_option("MEDICINE", "The chained clerk is fading. Get them talking before the poison finishes the job."),
                self.quoted_option("INVESTIGATION", "Give me the ledgers. I want the shape of Varyn's exits and lies."),
                self.action_option("Smash the poison table and flood the hall with glass, fumes, and noise."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_speaker("The chained clerk is fading. Get them talking before the poison finishes the job.")
            success = self.skill_check(self.state.player, "Medicine", 13, context="to keep the poisoned clerk alive long enough for a final warning")
            if success:
                self.state.flags["emberhall_clerk_saved"] = True
                self.add_inventory_item("antitoxin_vial", source="the chained clerk's hidden pocket")
                self.reward_party(xp=15, reason="saving the chained clerk in Emberhall")
                self.say("The clerk rasps out one useful warning: Varyn keeps a reserve vial for the first enemy who lands a real hit.")
            else:
                self.say("You save what life you can, but the warning dies in fragments.")
        elif choice == 2:
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
                description="The captain of the Ashen Brand makes the final stand beneath Phandalin.",
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
        self.say(
            "Varyn falls, the remaining brigands scatter, and the pressure that has bent every road into Phandalin finally breaks. Among the captain's ledgers are references to older powers stirring beneath the Sword Mountains, "
            "with whispers pointing toward deeper ruins, buried wealth, and unfinished business near Wave Echo Cave."
        )
        victory_tier = self.act1_record_epilogue_flags()
        if victory_tier == "clean_victory":
            self.say("Phandalin takes the news like a town finally allowed to breathe. The roads are scarred, but not broken, and the company leaves Act I with loyalty mostly intact.")
        elif victory_tier == "costly_victory":
            self.say("The win holds, but it costs blood, trust, and more sleepless eyes than anyone in town will admit out loud. Phandalin survives this act tired rather than whole.")
        else:
            self.say("Varyn is dead, but too many threads were left burning behind him. The Ashen Brand is beaten without being cleanly erased, and the next descent will begin under pressure.")
        self.add_journal("You broke the Ashen Brand and secured Phandalin through the end of Act 1.")
        self.reward_party(xp=250, gold=80, reason="securing Phandalin at the end of Act I")
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
