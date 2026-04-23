from __future__ import annotations

from .factories import build_character


PRESET_CHARACTERS: dict[str, dict[str, object]] = {
    "Barbarian": {
        "name": "Brakka Stonewake",
        "race": "Goliath",
        "background": "Outlander",
        "base_ability_scores": {"STR": 15, "DEX": 13, "CON": 14, "INT": 8, "WIS": 12, "CHA": 10},
        "class_skill_choices": ["Athletics", "Survival"],
        "description": "A hard-charging bruiser tuned for high Strength, strong staying power, and fast frontline testing.",
    },
    "Bard": {
        "name": "Lark Voss",
        "race": "Half-Elf",
        "background": "Charlatan",
        "base_ability_scores": {"STR": 8, "DEX": 14, "CON": 13, "INT": 10, "WIS": 12, "CHA": 15},
        "class_skill_choices": ["Insight", "Performance", "Persuasion"],
        "description": "A charismatic control-and-support build made for dialogue coverage, party buffs, and quick social testing.",
    },
    "Fighter": {
        "name": "Riven Ashguard",
        "race": "Orc",
        "background": "Soldier",
        "base_ability_scores": {"STR": 15, "DEX": 12, "CON": 14, "INT": 8, "WIS": 10, "CHA": 13},
        "class_skill_choices": ["Perception", "Survival"],
        "description": "A brutal shield-line veteran built to absorb pressure and keep swinging in the thick of a fight.",
    },
    "Rogue": {
        "name": "Mira Quickstep",
        "race": "Halfling",
        "background": "Criminal",
        "base_ability_scores": {"STR": 8, "DEX": 15, "CON": 13, "INT": 12, "WIS": 14, "CHA": 10},
        "class_skill_choices": ["Acrobatics", "Insight", "Perception", "Sleight of Hand"],
        "expertise_choices": ["Stealth", "Perception"],
        "description": "A razor-clean scout and lockbreaker tuned for mobility, stealth, and reliable skill coverage.",
    },
    "Cleric": {
        "name": "Sister Elowen",
        "race": "Dwarf",
        "background": "Acolyte",
        "base_ability_scores": {"STR": 10, "DEX": 12, "CON": 13, "INT": 8, "WIS": 15, "CHA": 14},
        "class_skill_choices": ["Medicine", "Persuasion"],
        "description": "A frontline battle-priest who balances healing, resilience, and strong social support checks.",
    },
    "Wizard": {
        "name": "Theron Vale",
        "race": "Gnome",
        "background": "Sage",
        "base_ability_scores": {"STR": 8, "DEX": 14, "CON": 13, "INT": 15, "WIS": 12, "CHA": 10},
        "class_skill_choices": ["Arcana", "Investigation"],
        "description": "A clean arcane blaster setup with sharp utility skills, solid initiative, and enough toughness to survive mistakes.",
    },
    "Paladin": {
        "name": "Ser Jorren Dawnsteel",
        "race": "Dragonborn",
        "background": "Soldier",
        "base_ability_scores": {"STR": 15, "DEX": 10, "CON": 13, "INT": 8, "WIS": 12, "CHA": 14},
        "class_skill_choices": ["Athletics", "Persuasion"],
        "description": "A durable radiant bruiser built for melee pressure, emergency healing, and confident dialogue checks.",
    },
    "Ranger": {
        "name": "Kael Thornwatch",
        "race": "Elf",
        "background": "Outlander",
        "base_ability_scores": {"STR": 10, "DEX": 15, "CON": 13, "INT": 10, "WIS": 14, "CHA": 12},
        "class_skill_choices": ["Perception", "Stealth", "Investigation"],
        "description": "A high-accuracy archer and pathfinder made for scouting, initiative, and clean ranged pressure.",
    },
    "Druid": {
        "name": "Liora Fenbloom",
        "race": "Human",
        "background": "Hermit",
        "base_ability_scores": {"STR": 8, "DEX": 12, "CON": 13, "INT": 10, "WIS": 15, "CHA": 14},
        "class_skill_choices": ["Nature", "Perception"],
        "description": "A steady wilderness caster focused on healing, control, and broad exploration support.",
    },
    "Monk": {
        "name": "Shen Vale",
        "race": "Human",
        "background": "Hermit",
        "base_ability_scores": {"STR": 10, "DEX": 15, "CON": 13, "INT": 8, "WIS": 14, "CHA": 12},
        "class_skill_choices": ["Acrobatics", "Insight"],
        "description": "A high-mobility striker focused on Dexterity, Wisdom, and clean unarmored combat testing.",
    },
    "Sorcerer": {
        "name": "Iria Flamevein",
        "race": "Tiefling",
        "background": "Sage",
        "base_ability_scores": {"STR": 8, "DEX": 14, "CON": 13, "INT": 12, "WIS": 10, "CHA": 15},
        "class_skill_choices": ["Arcana", "Persuasion"],
        "description": "An innate blaster build with strong Charisma casting, good initiative, and clean arcane utility.",
    },
    "Warlock": {
        "name": "Cairn Blackwake",
        "race": "Tiefling",
        "background": "Charlatan",
        "base_ability_scores": {"STR": 8, "DEX": 14, "CON": 13, "INT": 10, "WIS": 12, "CHA": 15},
        "class_skill_choices": ["Intimidation", "Investigation"],
        "description": "A force-damage occultist built for strong Charisma pressure, unsettling dialogue, and repeatable ranged offense.",
    },
}


def build_preset_character(class_name: str):
    preset = PRESET_CHARACTERS[class_name]
    character = build_character(
        name=str(preset["name"]),
        race=str(preset["race"]),
        class_name=class_name,
        background=str(preset["background"]),
        base_ability_scores=dict(preset["base_ability_scores"]),
        class_skill_choices=list(preset["class_skill_choices"]),
        expertise_choices=list(preset.get("expertise_choices", [])),
        notes=[str(preset["description"]), "Preset build: optimized for faster testing and quick starts."],
        inventory={"Healing Potion": 1},
    )
    return character
