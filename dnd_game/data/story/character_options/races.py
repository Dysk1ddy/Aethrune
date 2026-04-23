from __future__ import annotations

from ..public_terms import format_bonus_list, race_option_label, rules_text


RACES = {
    "Human": {
        "description": "Humans are adaptable survivors found across Aethrune's roads, ports, farms, and rebuilt towns.",
        "bonuses": {"STR": 1, "DEX": 1, "CON": 1, "INT": 1, "WIS": 1, "CHA": 1},
        "features": [],
        "skills": [],
    },
    "Dwarf": {
        "description": "Dwarves are hardy deep-infrastructure people shaped by stonework, pressure, and stubborn resolve.",
        "bonuses": {"CON": 2},
        "features": ["darkvision", "dwarven_resilience"],
        "skills": [],
    },
    "Elf": {
        "description": "Elves are long-lived observers whose keen senses and long memories suit subtle work.",
        "bonuses": {"DEX": 2},
        "features": ["darkvision", "keen_senses", "fey_ancestry"],
        "skills": ["Perception"],
    },
    "Halfling": {
        "description": "Halflings survive by quick feet, readiness, and refusing to stay intimidated for long.",
        "bonuses": {"DEX": 2},
        "features": ["lucky", "brave"],
        "skills": [],
    },
    "Dragonborn": {
        "description": "Forged carry visible old-system weight and often meet danger head-on.",
        "bonuses": {"STR": 2, "CHA": 1},
        "features": ["draconic_presence"],
        "skills": [],
    },
    "Gnome": {
        "description": "Unrecorded people are clever, hard-to-categorize survivors with restless, curious minds.",
        "bonuses": {"INT": 2},
        "features": ["gnome_cunning"],
        "skills": ["Investigation"],
    },
    "Half-Elf": {
        "description": "Elven Variants bridge perception and memory with adaptable talent, charm, and sharp instincts.",
        "bonuses": {"CHA": 2, "DEX": 1, "WIS": 1},
        "features": ["fey_ancestry"],
        "skills": ["Insight", "Persuasion"],
    },
    "Half-Orc": {
        "description": "Orc-Blooded survivors rely on strength, grit, and fierce presence.",
        "bonuses": {"STR": 2, "CON": 1},
        "features": ["relentless_endurance", "menacing"],
        "skills": ["Intimidation"],
    },
    "Tiefling": {
        "description": "Fire-Blooded people carry controlled inner heat and learn early how to turn suspicion into poise.",
        "bonuses": {"INT": 1, "CHA": 2},
        "features": ["darkvision", "hellish_resistance"],
        "skills": [],
    },
    "Goliath": {
        "description": "Riverfolk are pressure-tested people who meet hardship with endurance and motion.",
        "bonuses": {"STR": 2, "CON": 1},
        "features": ["stone_endurance"],
        "skills": ["Athletics"],
    },
    "Orc": {
        "description": "Orcs bring forceful presence, lowlight sight, and a refusal to stop when momentum matters most.",
        "bonuses": {"STR": 2, "CON": 1},
        "features": ["darkvision", "adrenaline_rush"],
        "skills": ["Intimidation"],
    },
}


def format_racial_bonuses(race: str) -> str:
    bonuses = RACES[race]["bonuses"]
    return format_bonus_list(bonuses, include_codes=True)


def format_race_selection(race: str) -> str:
    return f"{race_option_label(race)}: {format_racial_bonuses(race)}. {rules_text(RACES[race]['description'])}"
