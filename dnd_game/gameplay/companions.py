from __future__ import annotations

from ..data.story.companions import ACTIVE_COMPANION_LIMIT, COMPANION_PROFILES, PARTY_LIMIT, relationship_label
from ..items import EQUIPMENT_SLOTS, LEGACY_ITEM_NAMES, starter_item_ids_for_character


class CompanionSystemMixin:
    def has_companion(self, name: str) -> bool:
        assert self.state is not None
        if any(companion.name == name for companion in self.state.all_companions()):
            return True
        return name in set(self.state.flags.get("departed_companions", []))

    def current_party_size(self) -> int:
        assert self.state is not None
        return len(self.state.party_members())

    def highest_active_party_level(self) -> int:
        assert self.state is not None
        return max(member.level for member in self.state.party_members())

    def active_companion_limit(self) -> int:
        return ACTIVE_COMPANION_LIMIT

    def all_companions(self):
        assert self.state is not None
        return self.state.all_companions()

    def find_companion(self, name: str):
        assert self.state is not None
        for companion in self.state.all_companions():
            if companion.name == name:
                return companion
        return None

    def relationship_label_for(self, companion) -> str:
        return relationship_label(companion.disposition)

    def relationship_threshold(self, companion, minimum: str) -> bool:
        order = {"Terrible": -2, "Bad": -1, "Neutral": 0, "Good": 1, "Great": 2, "Exceptional": 3}
        return order[self.relationship_label_for(companion)] >= order[minimum]

    def refresh_companion_state(self, companion) -> None:
        if not companion.companion_id:
            companion.relationship_bonuses = {}
            return
        profile = COMPANION_PROFILES.get(companion.companion_id, {})
        bonuses: dict[str, int] = {}
        if companion.disposition >= 6:
            bonuses.update(dict(profile.get("great_bonuses", {})))
        if companion.disposition >= 9:
            for key, value in dict(profile.get("exceptional_bonuses", {})).items():
                bonuses[key] = bonuses.get(key, 0) + value
        companion.relationship_bonuses = bonuses

    def adjust_companion_disposition(self, companion, delta: int, reason: str) -> None:
        previous = companion.disposition
        companion.disposition += delta
        self.refresh_companion_state(companion)
        label = self.relationship_label_for(companion)
        if delta:
            direction = "improves" if delta > 0 else "drops"
            self.say(f"{companion.name}'s trust {direction} ({reason}). Relationship: {label} ({companion.disposition}).")
        if previous < 6 <= companion.disposition:
            self.say(COMPANION_PROFILES[companion.companion_id]["great_dialogue"])
        if previous < 9 <= companion.disposition:
            self.say(COMPANION_PROFILES[companion.companion_id]["exceptional_dialogue"])
        if companion.disposition <= -6:
            self.force_companion_departure(companion, reason=reason)

    def force_companion_departure(self, companion, *, reason: str) -> None:
        assert self.state is not None
        self.state.companions = [member for member in self.state.companions if member is not companion]
        self.state.camp_companions = [member for member in self.state.camp_companions if member is not companion]
        departed = set(self.state.flags.get("departed_companions", []))
        departed.add(companion.name)
        self.state.flags["departed_companions"] = sorted(departed)
        self.say(f"{companion.name} decides they can no longer trust you and leaves the company.")
        self.add_journal(f"{companion.name} left the party after trust collapsed ({reason}).")

    def sync_companion_to_active_party_level(self, companion) -> bool:
        assert self.state is not None
        target_level = self.highest_active_party_level()
        if companion.level >= target_level:
            return False
        previous_level = companion.level
        for next_level in range(companion.level + 1, target_level + 1):
            self.level_up_character_automatically(companion, next_level, announce=False)
        self.say(f"{companion.name} catches up from level {previous_level} to level {target_level} to match the active party.")
        return True

    def recruit_companion(self, companion) -> None:
        assert self.state is not None
        if self.has_companion(companion.name):
            return
        self.introduce_character(companion)
        if not companion.equipment_slots:
            companion.equipment_slots = {slot: None for slot in EQUIPMENT_SLOTS}
            for slot, item_id in starter_item_ids_for_character(companion).items():
                companion.equipment_slots[slot] = item_id
                if item_id is not None:
                    self.state.inventory[item_id] = self.state.inventory.get(item_id, 0) + 1
        for legacy_name, quantity in list(companion.inventory.items()):
            item_id = LEGACY_ITEM_NAMES.get(legacy_name)
            if item_id is not None:
                self.state.inventory[item_id] = self.state.inventory.get(item_id, 0) + quantity
        companion.inventory.clear()
        self.refresh_companion_state(companion)
        if len(self.state.companions) >= ACTIVE_COMPANION_LIMIT:
            self.state.camp_companions.append(companion)
            self.add_journal(f"{companion.name} joined your wider company and was sent to camp because the active party is full.")
            self.say(f"{companion.name} joins your wider company, but the active party is full. They head to camp for now.")
        else:
            self.state.companions.append(companion)
            self.sync_companion_to_active_party_level(companion)
            self.add_journal(f"{companion.name} joined the active party.")
        self.sync_equipment(companion)

    def move_companion_to_camp(self, companion) -> None:
        assert self.state is not None
        if companion not in self.state.companions:
            return
        self.state.companions.remove(companion)
        self.state.camp_companions.append(companion)
        tutorial_tracker = getattr(self, "record_opening_tutorial_companion_event", None)
        if callable(tutorial_tracker):
            tutorial_tracker("moved_to_camp", companion_name=companion.name)
        self.say(f"{companion.name} heads back to camp and leaves the active party.")

    def move_companion_to_party(self, companion) -> bool:
        assert self.state is not None
        if companion not in self.state.camp_companions:
            return False
        if len(self.state.companions) >= ACTIVE_COMPANION_LIMIT:
            self.say(f"The active party is already at the limit of {PARTY_LIMIT} total members.")
            return False
        self.state.camp_companions.remove(companion)
        self.state.companions.append(companion)
        self.sync_companion_to_active_party_level(companion)
        tutorial_tracker = getattr(self, "record_opening_tutorial_companion_event", None)
        if callable(tutorial_tracker):
            tutorial_tracker("moved_to_party", companion_name=companion.name)
        self.say(f"{companion.name} returns from camp and joins the active party.")
        return True

    def apply_scene_companion_support(self, scene_key: str) -> int:
        assert self.state is not None
        total_bonus = 0
        for companion in self.state.companions:
            if companion.disposition < 6 or not companion.companion_id:
                continue
            scene_support = COMPANION_PROFILES[companion.companion_id].get("scene_support", {}).get(scene_key)
            if scene_support is None:
                continue
            self.say(scene_support["text"])
            total_bonus += int(scene_support.get("hero_bonus", 0))
            for status, duration in dict(scene_support.get("ally_statuses", {})).items():
                self.apply_status(self.state.player, status, int(duration), source=companion.name)
            if companion.disposition >= 9 and scene_support.get("hero_bonus", 0):
                total_bonus += 1
        return total_bonus

    def companion_status_line(self, companion) -> str:
        location = "Active party" if companion in self.state.companions else "Camp"
        if companion.dead:
            location = f"Dead ({location})"
        return (
            f"{companion.name}: Level {companion.level} {companion.race} {companion.class_name} | "
            f"{self.format_health_bar(companion.current_hp, companion.max_hp)}{self.health_status_suffix(companion.current_hp, dead=companion.dead)} | "
            f"{self.relationship_label_for(companion)} ({companion.disposition}) | {location}"
        )
