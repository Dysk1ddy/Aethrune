from __future__ import annotations

from ..dice import roll


STATUS_DEFINITIONS: dict[str, dict[str, object]] = {
    "surprised": {"name": "Surprised", "combat_only": True},
    "blinded": {"name": "Blinded", "combat_only": True},
    "charmed": {"name": "Charmed", "combat_only": True},
    "deafened": {"name": "Deafened", "combat_only": True},
    "exhaustion": {"name": "Exhaustion", "combat_only": True},
    "frightened": {"name": "Frightened", "combat_only": True},
    "grappled": {"name": "Grappled", "combat_only": True},
    "incapacitated": {"name": "Incapacitated", "combat_only": True},
    "invisible": {"name": "Invisible", "combat_only": True},
    "paralyzed": {"name": "Paralyzed", "combat_only": True},
    "petrified": {"name": "Petrified", "combat_only": True},
    "poisoned": {"name": "Poisoned", "combat_only": True},
    "burning": {
        "name": "Burning",
        "combat_only": True,
        "ongoing_damage": "1d6",
        "damage_type": "fire",
    },
    "acid": {
        "name": "Acid-Burned",
        "combat_only": True,
        "ongoing_damage": "1d4",
        "damage_type": "acid",
        "ac_penalty": 1,
    },
    "reeling": {
        "name": "Reeling",
        "combat_only": True,
        "attack_penalty": 2,
    },
    "prone": {
        "name": "Prone",
        "combat_only": True,
        "ac_penalty": 2,
    },
    "restrained": {
        "name": "Restrained",
        "combat_only": True,
        "ac_penalty": 2,
    },
    "emboldened": {
        "name": "Emboldened",
        "combat_only": True,
        "attack_bonus": 2,
        "save_bonus": 1,
    },
    "blessed": {
        "name": "Blessed",
        "combat_only": True,
        "attack_bonus": 1,
        "save_bonus": 2,
    },
    "guarded": {
        "name": "Guarded",
        "combat_only": True,
        "ac_bonus": 1,
    },
    "attack_pressure": {
        "name": "Attack Pressure",
        "combat_only": True,
        "attack_bonus": 1,
    },
    "marked": {"name": "Marked", "combat_only": True},
    "bleeding": {
        "name": "Bleeding",
        "combat_only": True,
        "ongoing_damage": "1d4",
        "damage_type": "bleeding",
    },
    "cursed": {
        "name": "Cursed",
        "combat_only": False,
        "attack_penalty": 1,
        "save_penalty": 1,
    },
    "resist_fire": {"name": "Fire-Resistant", "combat_only": True},
    "resist_cold": {"name": "Cold-Resistant", "combat_only": True},
    "resist_lightning": {"name": "Lightning-Resistant", "combat_only": True},
    "resist_poison": {"name": "Poison-Resistant", "combat_only": True},
    "stunned": {"name": "Stunned", "combat_only": True},
    "unconscious": {"name": "Unconscious", "combat_only": True},
}


class StatusEffectMixin:
    def status_definition(self, status: str) -> dict[str, object]:
        return STATUS_DEFINITIONS.get(status, {"name": status.replace("_", " ").title(), "combat_only": True})

    def status_name(self, status: str) -> str:
        return str(self.status_definition(status)["name"])

    def has_status(self, actor, status: str) -> bool:
        if status == "unconscious":
            return actor.current_hp == 0 and not actor.dead
        return actor.conditions.get(status, 0) != 0

    def status_value(self, actor, key: str) -> int:
        total = 0
        for status, duration in actor.conditions.items():
            if duration == 0:
                continue
            definition = self.status_definition(status)
            total += int(definition.get(key, 0))
        exhaustion = max(0, int(actor.conditions.get("exhaustion", 0)))
        if key == "attack_penalty":
            total += 1 if exhaustion >= 2 else 0
        if key == "save_penalty":
            total += 1 if exhaustion >= 3 else 0
        return total

    def effective_armor_class(self, actor) -> int:
        return max(1, actor.armor_class + self.status_value(actor, "ac_bonus") - self.status_value(actor, "ac_penalty"))

    def apply_status(self, actor, status: str, duration: int, *, source: str = "") -> None:
        definition = self.status_definition(status)
        if status in {"charmed", "frightened"} and "dark_devotion" in getattr(actor, "features", []):
            if not actor.bond_flags.get("dark_devotion_used"):
                actor.bond_flags["dark_devotion_used"] = True
                self.say(f"{self.style_name(actor)} steels themselves and shrugs off {self.status_name(status)}.")
                return
        if status in {"charmed", "frightened", "incapacitated"} and "spellward_plating" in getattr(actor, "features", []):
            if not actor.bond_flags.get("spellward_plating_used"):
                actor.bond_flags["spellward_plating_used"] = True
                self.say(f"{self.style_name(actor)}'s warded plating rejects the first attempt to {status.replace('_', ' ')} it.")
                return
        current = actor.conditions.get(status, 0)
        if status == "exhaustion" and duration > 0:
            actor.conditions[status] = current + duration
        elif current < 0 or duration < 0:
            actor.conditions[status] = -1
        else:
            actor.conditions[status] = max(current, duration)
        source_text = f" from {source}" if source else ""
        self.say(f"{self.style_name(actor)} is now {self.status_name(status)}{source_text}.")

    def clear_temporary_statuses(self, actor) -> None:
        for status in list(actor.conditions):
            definition = self.status_definition(status)
            if actor.conditions[status] < 0 or not bool(definition.get("combat_only", True)):
                continue
            actor.conditions.pop(status, None)

    def clear_status(self, actor, status: str) -> None:
        actor.conditions.pop(status, None)

    def clear_after_encounter(self, actors) -> None:
        for actor in actors:
            self.clear_temporary_statuses(actor)

    def is_incapacitated(self, actor) -> bool:
        return any(
            self.has_status(actor, name)
            for name in ("incapacitated", "paralyzed", "petrified", "stunned", "unconscious")
        )

    def blocks_movement(self, actor) -> bool:
        return any(self.has_status(actor, name) for name in ("grappled", "restrained", "paralyzed", "petrified", "stunned", "unconscious"))

    def auto_fail_save(self, actor, ability: str) -> bool:
        if ability not in {"STR", "DEX"}:
            return False
        return any(self.has_status(actor, name) for name in ("paralyzed", "petrified", "stunned", "unconscious"))

    def d20_disadvantage_state(self, actor, *, skill: str | None = None, context: str = "", attack: bool = False) -> int:
        state = 0
        lowered = context.lower()
        if self.has_status(actor, "poisoned"):
            state -= 1
        if self.has_status(actor, "frightened"):
            state -= 1
        if attack and self.has_status(actor, "restrained"):
            state -= 1
        if attack and self.has_status(actor, "blinded") and "blind_sense" not in getattr(actor, "features", []):
            state -= 1
        if attack and self.has_status(actor, "grappled"):
            state -= 1
        exhaustion = max(0, int(actor.conditions.get("exhaustion", 0)))
        if attack and exhaustion >= 3:
            state -= 1
        if not attack and exhaustion >= 1:
            state -= 1
        if skill is not None and self.has_status(actor, "blinded") and skill in {"Perception", "Investigation", "Survival"}:
            state -= 1
        if skill is not None and self.has_status(actor, "deafened") and (skill == "Perception" or any(token in lowered for token in ("hear", "hearing", "listen", "sound", "noise"))):
            state -= 1
        if skill == "Stealth" and actor.gear_bonuses.get("stealth_advantage", 0):
            state += 1
        return 1 if state > 0 else -1 if state < 0 else 0

    def can_make_hostile_action(self, actor) -> bool:
        return not self.has_status(actor, "charmed")

    def resolve_start_of_turn_statuses(self, actor) -> bool:
        if actor.conditions.get("surprised", 0) > 0:
            self.say(f"{self.style_name(actor)} is caught off guard and loses the turn.")
            actor.conditions["surprised"] -= 1
            if actor.conditions["surprised"] <= 0:
                actor.conditions.pop("surprised", None)
            return False
        if self.is_incapacitated(actor):
            self.say(f"{self.style_name(actor)} cannot act while {self.describe_blocking_condition(actor)}.")
            return False
        return True

    def describe_blocking_condition(self, actor) -> str:
        for name in ("stunned", "paralyzed", "petrified", "incapacitated", "unconscious"):
            if self.has_status(actor, name):
                return self.status_name(name)
        return "disabled"

    def tick_conditions(self, actor) -> None:
        ongoing = [(name, self.status_definition(name)) for name, value in actor.conditions.items() if value != 0]
        for name, definition in ongoing:
            damage_roll = definition.get("ongoing_damage")
            if not damage_roll or not actor.is_conscious():
                continue
            actual = self.apply_damage(
                actor,
                self.roll_with_animation_context(
                    str(damage_roll),
                    style="damage",
                    context_label=f"{self.status_name(name)} damages {actor.name}",
                    outcome_kind="damage",
                ).total,
                damage_type=str(definition.get("damage_type", "")),
            )
            self.say(
                f"{self.style_name(actor)} suffers {self.style_damage(actual)} "
                f"{str(definition.get('damage_type', '')).strip() or 'ongoing'} damage from {self.status_name(name)}."
            )
            self.announce_downed_target(actor)
        for name in list(actor.conditions):
            if actor.conditions[name] < 0:
                continue
            actor.conditions[name] -= 1
            if actor.conditions[name] <= 0:
                actor.conditions.pop(name, None)
