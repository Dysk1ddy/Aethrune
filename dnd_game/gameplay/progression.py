from __future__ import annotations

from ..content import CLASS_LEVEL_PROGRESSION, CLASSES
from .magic_points import synchronize_magic_points
from .spell_slots import synchronize_spell_slots
from ..models import Character
from .constants import LEVEL_XP_THRESHOLDS


class ProgressionMixin:
    def reconcile_level_progression(self, actor: Character) -> None:
        self.scale_level_resources(actor, refill=True)
        for level in range(2, actor.level + 1):
            self.apply_class_level_features(actor, level, announce=False)

    def current_level_target(self) -> int | None:
        if self.state is None:
            return None
        return LEVEL_XP_THRESHOLDS.get(self.state.player.level + 1)

    def xp_to_next_level(self) -> int | None:
        if self.state is None:
            return None
        target = self.current_level_target()
        if target is None:
            return None
        return max(0, target - self.state.xp)

    def xp_progress_summary(self) -> str:
        if self.state is None:
            return "No party XP yet."
        target = self.current_level_target()
        if target is None:
            return f"Party XP: {self.state.xp} (maximum implemented level reached)"
        return f"Party XP: {self.state.xp} | Next level in {max(0, target - self.state.xp)} XP"

    def apply_class_level_features(self, actor: Character, level: int, *, announce: bool) -> list[str]:
        progression = CLASS_LEVEL_PROGRESSION.get(actor.class_name, {}).get(level)
        if progression is None:
            return []
        feature_ids = list(progression.get("feature_ids", []))
        if feature_ids and all(feature_id in actor.features for feature_id in feature_ids):
            return []
        for feature_id in feature_ids:
            if feature_id not in actor.features:
                actor.features.append(feature_id)
        for resource_name, amount in dict(progression.get("resources", {})).items():
            actor.max_resources[resource_name] = max(actor.max_resources.get(resource_name, 0), amount)
            actor.resources[resource_name] = actor.max_resources[resource_name]
        for bonus_name, amount in dict(progression.get("equipment_bonuses", {})).items():
            actor.equipment_bonuses[bonus_name] = actor.equipment_bonuses.get(bonus_name, 0) + amount
        feature_lines = [f"{title}: {description}" for title, description in progression.get("features", [])]
        if announce:
            for line in feature_lines:
                self.say(line)
        actor.features.sort()
        return feature_lines

    def reward_party(self, *, xp: int = 0, gold: int = 0, reason: str) -> None:
        assert self.state is not None
        gained_parts: list[str] = []
        if xp:
            self.state.xp += xp
            gained_parts.append(f"{xp} XP")
        if gold:
            self.state.gold += gold
            gained_parts.append(f"{gold} gp")
        if gained_parts:
            self.say(f"Reward gained for {reason}: {', '.join(gained_parts)}.")
            self.say(self.xp_progress_summary())
            self.add_journal(f"Reward from {reason}: {', '.join(gained_parts)}.")
        self.resolve_level_ups()

    def resolve_level_ups(self) -> None:
        assert self.state is not None
        while self.state.player.level + 1 in LEVEL_XP_THRESHOLDS and self.state.xp >= LEVEL_XP_THRESHOLDS[self.state.player.level + 1]:
            new_level = self.state.player.level + 1
            self.banner(f"Level {new_level}")
            self.say(f"The party reaches level {new_level}. Training and hard road lessons start to pay off.")
            for member in [self.state.player, *self.state.all_companions()]:
                self.level_up_character(member, new_level)

    def level_up_character(self, actor: Character, new_level: int) -> None:
        actor.level = new_level
        hp_gain = max(1, actor.hit_die // 2 + 1 + actor.ability_mod("CON"))
        actor.max_hp += hp_gain
        actor.current_hp += hp_gain
        self.scale_level_resources(actor)
        feature_lines = self.apply_class_level_features(actor, new_level, announce=False)
        if actor is self.state.player:
            self.say(f"{actor.name} gains {hp_gain} max HP.")
            for line in feature_lines:
                self.say(line)
            self.choose_level_up_skill(actor)
        else:
            picked = self.auto_choose_level_up_skill(actor)
            summary_parts = [f"{actor.name} gains {hp_gain} max HP"]
            if picked is not None:
                summary_parts.append(f"learns {picked}")
            self.say(", and ".join(summary_parts) + ".")
            for line in feature_lines:
                self.say(f"{actor.name}: {line}")

    def scale_level_resources(self, actor: Character, *, refill: bool = True) -> None:
        synchronize_spell_slots(actor, refill=refill)
        synchronize_magic_points(actor, refill=refill)
        if actor.class_name == "Paladin":
            actor.max_resources["lay_on_hands"] = actor.level * 5
            if refill:
                actor.resources["lay_on_hands"] = actor.max_resources["lay_on_hands"]
        if actor.class_name == "Fighter":
            actor.max_resources["second_wind"] = max(actor.max_resources.get("second_wind", 1), 1)
            if refill:
                actor.resources["second_wind"] = actor.max_resources["second_wind"]
        if actor.class_name == "Monk" and actor.level >= 2:
            actor.max_resources["ki"] = max(actor.max_resources.get("ki", actor.level), actor.level)
            if refill:
                actor.resources["ki"] = actor.max_resources["ki"]

    def choose_level_up_skill(self, actor: Character) -> None:
        available = [skill for skill in CLASSES[actor.class_name]["skill_choices"] if skill not in actor.skill_proficiencies]
        if not available:
            self.say(f"{actor.name} has no new class skills available to learn.")
            return
        choice = self.choose(
            f"Choose a new {actor.class_name} skill for {actor.name}.",
            available,
            allow_meta=False,
        )
        picked = available[choice - 1]
        actor.skill_proficiencies.append(picked)
        actor.skill_proficiencies.sort()
        self.say(f"{actor.name} learns {picked}.")

    def auto_choose_level_up_skill(self, actor: Character) -> str | None:
        available = [skill for skill in CLASSES[actor.class_name]["skill_choices"] if skill not in actor.skill_proficiencies]
        if not available:
            return None
        picked = available[0]
        actor.skill_proficiencies.append(picked)
        actor.skill_proficiencies.sort()
        return picked

    def random_choose_level_up_skill(self, actor: Character) -> str | None:
        available = [skill for skill in CLASSES[actor.class_name]["skill_choices"] if skill not in actor.skill_proficiencies]
        if not available:
            return None
        picked = self.rng.choice(available)
        actor.skill_proficiencies.append(picked)
        actor.skill_proficiencies.sort()
        return picked

    def level_up_character_automatically(
        self,
        actor: Character,
        new_level: int,
        *,
        randomize_skill_choice: bool = False,
        announce: bool = True,
    ) -> None:
        actor.level = new_level
        hp_gain = max(1, actor.hit_die // 2 + 1 + actor.ability_mod("CON"))
        actor.max_hp += hp_gain
        actor.current_hp += hp_gain
        self.scale_level_resources(actor)
        feature_lines = self.apply_class_level_features(actor, new_level, announce=False)
        picked = (
            self.random_choose_level_up_skill(actor)
            if randomize_skill_choice
            else self.auto_choose_level_up_skill(actor)
        )
        if announce:
            summary_parts = [f"{actor.name} gains {hp_gain} max HP"]
            if picked is not None:
                summary_parts.append(f"learns {picked}")
            self.say(", and ".join(summary_parts) + ".")
            for line in feature_lines:
                self.say(f"{actor.name}: {line}")
