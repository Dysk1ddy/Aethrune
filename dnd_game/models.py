from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .data.quests import QuestLogEntry
from .data.story.public_terms import class_label, race_label
from .dice import ability_modifier


ABILITY_ORDER = ("STR", "DEX", "CON", "INT", "WIS", "CHA")

SKILL_TO_ABILITY = {
    "Acrobatics": "DEX",
    "Animal Handling": "WIS",
    "Arcana": "INT",
    "Athletics": "STR",
    "Deception": "CHA",
    "History": "INT",
    "Insight": "WIS",
    "Intimidation": "CHA",
    "Investigation": "INT",
    "Medicine": "WIS",
    "Nature": "INT",
    "Perception": "WIS",
    "Performance": "CHA",
    "Persuasion": "CHA",
    "Religion": "INT",
    "Sleight of Hand": "DEX",
    "Stealth": "DEX",
    "Survival": "WIS",
}


@dataclass(slots=True)
class Weapon:
    name: str
    damage: str
    ability: str = "STR"
    weapon_type: str = "simple"
    to_hit_bonus: int = 0
    damage_bonus: int = 0
    finesse: bool = False
    ranged: bool = False
    hands_required: int = 1
    properties: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Armor:
    name: str
    base_ac: int
    armor_type: str = "light"
    dex_cap: int | None = None
    heavy: bool = False
    stealth_disadvantage: bool = False


@dataclass(slots=True)
class Character:
    name: str
    race: str
    class_name: str
    background: str
    level: int
    ability_scores: dict[str, int]
    skill_proficiencies: list[str]
    saving_throw_proficiencies: list[str]
    features: list[str]
    weapon: Weapon
    armor: Armor | None
    hit_die: int
    current_hp: int
    max_hp: int
    shield: bool = False
    spellcasting_ability: str | None = None
    skill_expertise: list[str] = field(default_factory=list)
    bonus_proficiencies: list[str] = field(default_factory=list)
    resources: dict[str, int] = field(default_factory=dict)
    max_resources: dict[str, int] = field(default_factory=dict)
    inventory: dict[str, int] = field(default_factory=dict)
    conditions: dict[str, int] = field(default_factory=dict)
    equipment_bonuses: dict[str, int] = field(default_factory=dict)
    gear_bonuses: dict[str, int] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    equipment_slots: dict[str, str | None] = field(default_factory=dict)
    archetype: str = ""
    companion_id: str = ""
    disposition: int = 0
    lore: list[str] = field(default_factory=list)
    bond_flags: dict[str, Any] = field(default_factory=dict)
    relationship_bonuses: dict[str, int] = field(default_factory=dict)
    story_skill_bonuses: dict[str, int] = field(default_factory=dict)
    stable: bool = False
    dead: bool = False
    death_successes: int = 0
    death_failures: int = 0
    temp_hp: int = 0
    xp_value: int = 0
    gold_value: int = 0

    @property
    def proficiency_bonus(self) -> int:
        return 2 + max(0, (self.level - 1) // 4)

    @property
    def public_race(self) -> str:
        return race_label(self.race)

    @property
    def public_class(self) -> str:
        return class_label(self.class_name)

    @property
    def public_identity(self) -> str:
        return f"{self.public_race} {self.public_class}"

    def ability_mod(self, ability: str) -> int:
        return ability_modifier(self.ability_scores[ability])

    def skill_bonus(self, skill: str) -> int:
        bonus = self.ability_mod(SKILL_TO_ABILITY[skill])
        if skill in self.skill_proficiencies:
            bonus += self.proficiency_bonus
        if skill in self.skill_expertise:
            bonus += self.proficiency_bonus
        bonus += self.equipment_bonuses.get(skill, 0)
        bonus += self.gear_bonuses.get(skill, 0)
        bonus += self.relationship_bonuses.get(skill, 0)
        bonus += self.story_skill_bonuses.get(skill, 0)
        return bonus

    def save_bonus(self, ability: str) -> int:
        bonus = self.ability_mod(ability)
        if ability in self.saving_throw_proficiencies:
            bonus += self.proficiency_bonus
        bonus += self.equipment_bonuses.get(f"{ability}_save", 0)
        bonus += self.gear_bonuses.get(f"{ability}_save", 0)
        bonus += self.relationship_bonuses.get(f"{ability}_save", 0)
        return bonus

    def attack_ability(self) -> str:
        if self.weapon.ability == "SPELL":
            return self.spellcasting_ability or "INT"
        if self.weapon.ability == "DEX":
            return "DEX"
        if self.weapon.ability == "FINESSE" or self.weapon.finesse:
            return "DEX" if self.ability_mod("DEX") >= self.ability_mod("STR") else "STR"
        return self.weapon.ability

    @property
    def armor_class(self) -> int:
        dex_mod = self.ability_mod("DEX")
        if self.armor is None and "unarmored_defense_barbarian" in self.features:
            base = 10 + dex_mod + self.ability_mod("CON")
        elif self.armor is None and "unarmored_defense_monk" in self.features:
            base = 10 + dex_mod + self.ability_mod("WIS")
        elif self.armor is None:
            base = 10 + dex_mod
        elif self.armor.dex_cap is None:
            base = self.armor.base_ac + dex_mod
        else:
            base = self.armor.base_ac + min(dex_mod, self.armor.dex_cap)
        if self.shield:
            base += 2
        base += self.equipment_bonuses.get("AC", 0)
        base += self.gear_bonuses.get("AC", 0)
        base += self.relationship_bonuses.get("AC", 0)
        return base

    def attack_bonus(self) -> int:
        return (
            self.ability_mod(self.attack_ability())
            + self.proficiency_bonus
            + self.weapon.to_hit_bonus
            + self.equipment_bonuses.get("attack", 0)
            + self.gear_bonuses.get("attack", 0)
            + self.relationship_bonuses.get("attack", 0)
        )

    def damage_bonus(self) -> int:
        return (
            self.ability_mod(self.attack_ability())
            + self.weapon.damage_bonus
            + self.equipment_bonuses.get("damage", 0)
            + self.gear_bonuses.get("damage", 0)
            + self.relationship_bonuses.get("damage", 0)
        )

    def is_conscious(self) -> bool:
        return not self.dead and self.current_hp > 0

    def is_dying(self) -> bool:
        return not self.dead and self.current_hp == 0 and not self.stable and "enemy" not in self.tags

    def can_act(self) -> bool:
        return self.is_conscious()

    def heal(self, amount: int) -> int:
        if self.dead:
            return 0
        previous = self.current_hp
        self.current_hp = min(self.max_hp, self.current_hp + max(0, amount))
        if self.current_hp > 0:
            self.stable = False
            self.death_successes = 0
            self.death_failures = 0
        return self.current_hp - previous

    def grant_temp_hp(self, amount: int) -> int:
        self.temp_hp = max(self.temp_hp, amount)
        return self.temp_hp

    def spend_resource(self, name: str, amount: int = 1) -> bool:
        if self.resources.get(name, 0) < amount:
            return False
        self.resources[name] -= amount
        return True

    def spend_item(self, name: str, amount: int = 1) -> bool:
        if self.inventory.get(name, 0) < amount:
            return False
        self.inventory[name] -= amount
        if self.inventory[name] <= 0:
            self.inventory.pop(name, None)
        return True

    def reset_for_rest(self) -> None:
        self.current_hp = self.max_hp
        self.conditions.clear()
        self.resources = dict(self.max_resources)
        self.stable = False
        self.dead = False
        self.death_successes = 0
        self.death_failures = 0
        self.temp_hp = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Character":
        payload = dict(data)
        payload["weapon"] = Weapon(**payload["weapon"])
        if payload["armor"] is not None:
            payload["armor"] = Armor(**payload["armor"])
        return cls(**payload)


@dataclass(slots=True)
class GameState:
    player: Character
    companions: list[Character] = field(default_factory=list)
    camp_companions: list[Character] = field(default_factory=list)
    current_act: int = 1
    current_scene: str = "neverwinter_briefing"
    flags: dict[str, Any] = field(default_factory=dict)
    clues: list[str] = field(default_factory=list)
    journal: list[str] = field(default_factory=list)
    quests: dict[str, QuestLogEntry] = field(default_factory=dict)
    completed_acts: list[int] = field(default_factory=list)
    xp: int = 0
    gold: int = 0
    inventory: dict[str, int] = field(default_factory=dict)
    short_rests_remaining: int = 2

    def party_members(self) -> list[Character]:
        return [self.player, *self.companions]

    def all_companions(self) -> list[Character]:
        return [*self.companions, *self.camp_companions]

    def to_dict(self) -> dict[str, Any]:
        return {
            "player": self.player.to_dict(),
            "companions": [companion.to_dict() for companion in self.companions],
            "camp_companions": [companion.to_dict() for companion in self.camp_companions],
            "current_act": self.current_act,
            "current_scene": self.current_scene,
            "flags": dict(self.flags),
            "clues": list(self.clues),
            "journal": list(self.journal),
            "quests": {quest_id: entry.to_dict() for quest_id, entry in self.quests.items()},
            "completed_acts": list(self.completed_acts),
            "xp": self.xp,
            "gold": self.gold,
            "inventory": dict(self.inventory),
            "short_rests_remaining": self.short_rests_remaining,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GameState":
        return cls(
            player=Character.from_dict(data["player"]),
            companions=[Character.from_dict(item) for item in data.get("companions", [])],
            camp_companions=[Character.from_dict(item) for item in data.get("camp_companions", [])],
            current_act=data.get("current_act", 1),
            current_scene=data.get("current_scene", "neverwinter_briefing"),
            flags=dict(data.get("flags", {})),
            clues=list(data.get("clues", [])),
            journal=list(data.get("journal", [])),
            quests={
                str(quest_id): QuestLogEntry.from_dict(entry_data)
                for quest_id, entry_data in dict(data.get("quests", {})).items()
            },
            completed_acts=list(data.get("completed_acts", [])),
            xp=data.get("xp", 0),
            gold=data.get("gold", 0),
            inventory=dict(data.get("inventory", {})),
            short_rests_remaining=data.get("short_rests_remaining", 2),
        )
