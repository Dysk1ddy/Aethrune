from __future__ import annotations

import re
from collections.abc import Mapping


CLASS_PUBLIC_LABELS: dict[str, str] = {}


RACE_PUBLIC_LABELS = {
    "Human": "Human",
    "Dwarf": "Dwarf",
    "Elf": "Elf",
    "Halfling": "Halfling",
    "Dragonborn": "Forged",
    "Gnome": "Unrecorded",
    "Half-Elf": "Astral Elf",
    "Half-Orc": "Orc-Blooded",
    "Tiefling": "Fire-Blooded",
    "Goliath": "Riverfolk",
    "Orc": "Orc",
}


ABILITY_PUBLIC_LABELS = {
    "STR": "Strength",
    "DEX": "Agility",
    "CON": "Endurance",
    "INT": "Intelligence",
    "WIS": "Wisdom",
    "CHA": "Charisma",
}


ABILITY_FULL_LABELS = {
    "STR": "Strength",
    "DEX": "Dexterity",
    "CON": "Constitution",
    "INT": "Intelligence",
    "WIS": "Wisdom",
    "CHA": "Charisma",
}


SKILL_PUBLIC_LABELS: dict[str, str] = {}


SPELL_PUBLIC_LABELS = {
    "sacred_flame": "Lantern Flare",
    "produce_flame": "Embercall",
    "vicious_mockery": "Cutting Cadence",
    "fire_bolt": "Ember Lance",
    "eldritch_blast": "Void Surge",
    "cure_wounds": "Field Mend",
    "healing_word": "Pulse Restore",
    "magic_missile": "Arc Pulse",
    "divine_smite": "Oathflare Strike",
}


SPELL_NAME_TO_ID = {
    "Sacred Flame": "sacred_flame",
    "Produce Flame": "produce_flame",
    "Vicious Mockery": "vicious_mockery",
    "Fire Bolt": "fire_bolt",
    "Eldritch Blast": "eldritch_blast",
    "Cure Wounds": "cure_wounds",
    "Healing Word": "healing_word",
    "Magic Missile": "magic_missile",
    "Divine Smite": "divine_smite",
}


FEATURE_PUBLIC_LABELS = {
    "rage": "Battle Surge",
    "unarmored_defense_barbarian": "Scar Guard",
    "bard_spellcasting": "Bard Channeling",
    "bardic_inspiration": "Rally Note",
    "cleric_spellcasting": "Cleric Channeling",
    "druid_spellcasting": "Druid Channeling",
    "second_wind": "Second Breath",
    "martial_arts": "Close Form",
    "unarmored_defense_monk": "Empty-Hand Guard",
    "lay_on_hands": "Oath Mend",
    "divine_smite": "Oathflare Strike",
    "natural_explorer": "Route Sense",
    "sneak_attack": "Veilstrike",
    "expertise": "Deep Practice",
    "sorcerer_spellcasting": "Sorcerer Channeling",
    "warlock_spellcasting": "Warlock Channeling",
    "wizard_spellcasting": "Wizard Channeling",
    "arcane_recovery": "Pattern Recovery",
    "darkvision": "Lowlight Sight",
    "dwarven_resilience": "Dwarven Resilience",
    "keen_senses": "Keen Senses",
    "fey_ancestry": "Signal Distance",
    "lucky": "Halfling Luck",
    "brave": "Small Courage",
    "draconic_presence": "Forged Presence",
    "gnome_cunning": "Unrecorded Cunning",
    "relentless_endurance": "Orcish Grit",
    "menacing": "Hard Stare",
    "hellish_resistance": "Fire-Blooded Resistance",
    "stone_endurance": "Riverfolk Endurance",
    "adrenaline_rush": "Orc Rush",
    "reckless_pressure": "Reckless Pressure",
    "primal_tenacity": "Primal Tenacity",
    "ferocious_presence": "Ferocious Presence",
    "cutting_wit": "Cutting Wit",
    "silver_tongue_bard": "Silver Tongue",
    "stage_courage": "Stage Courage",
    "channel_divinity": "Lantern Surge",
    "disciple_of_life": "Field Medic Doctrine",
    "radiant_potency": "Lantern Potency",
    "natural_recovery": "Natural Recovery",
    "wildfire_adept": "Wildfire Adept",
    "lands_embrace": "Land's Embrace",
    "action_surge": "Battle Surge",
    "improved_critical": "Keen Critical",
    "martial_mastery": "Martial Mastery",
    "ki": "Focus",
    "flurry_of_blows": "Twinflow Strikes",
    "patient_defense": "Still Guard",
    "step_of_the_wind": "Wind Step",
    "unarmored_focus": "Unarmored Focus",
    "open_hand_timing": "Open-Hand Timing",
    "centered_spirit": "Centered Spirit",
    "divine_health": "Oath Health",
    "aura_of_resolve": "Resolve Aura",
    "radiant_strikes": "Oathlit Strikes",
    "hunters_quarry": "Marked Quarry",
    "skirmisher_eye": "Skirmisher's Eye",
    "fieldcraft": "Fieldcraft",
    "cunning_action": "Veil Step",
    "improved_sneak_attack": "Deadly Veilstrike",
    "evasion": "Evasion",
    "arcane_overflow": "Flux Overflow",
    "warped_grace": "Warped Grace",
    "focused_will": "Focused Will",
    "patrons_sting": "Patron's Sting",
    "unnerving_presence": "Unnerving Presence",
    "eldritch_precision": "Void Precision",
    "sculpted_cantrips": "Sculpted Minor Channels",
    "spellguard": "Scriptguard",
    "arcane_focus": "Channel Focus",
}


RESOURCE_PUBLIC_LABELS = {
    "mp": "channel reserve",
    "rage": "battle surge",
    "bardic_inspiration": "rally note",
    "lay_on_hands": "oath mend",
    "channel_divinity": "lantern surge",
    "action_surge": "battle surge",
    "ki": "focus",
    "second_wind": "second breath",
}


TERM_REPLACEMENTS = (
    (r"\bArmor Class\b", "Guard"),
    (r"\barmor class\b", "Guard"),
    (r"\bSaving Throws\b", "Resist Checks"),
    (r"\bsaving throws\b", "resist checks"),
    (r"\bSaving Throw\b", "Resist Check"),
    (r"\bsaving throw\b", "resist check"),
    (r"\bspell attack rolls\b", "channel strike checks"),
    (r"\bspell attack roll\b", "channel strike check"),
    (r"\bspell attack\b", "channel strike"),
    (r"\bSpell attack\b", "Channel strike"),
    (r"\bAttack Rolls\b", "Strike Checks"),
    (r"\battack rolls\b", "strike checks"),
    (r"\bAttack Roll\b", "Strike Check"),
    (r"\battack roll\b", "strike check"),
    (r"\bweapon attacks\b", "weapon strikes"),
    (r"\bWeapon attacks\b", "Weapon strikes"),
    (r"\bspell slots\b", "charge bands"),
    (r"\bSpell Slots\b", "Charge Bands"),
    (r"\bspell slot\b", "charge band"),
    (r"\bSpell Slot\b", "Charge Band"),
    (r"\bspellcasting\b", "channeling"),
    (r"\bSpellcasting\b", "Channeling"),
    (r"\bspell damage\b", "channel damage"),
    (r"\bSpell damage\b", "Channel damage"),
    (r"\bcantrips\b", "minor channels"),
    (r"\bCantrips\b", "Minor channels"),
    (r"\bcantrip\b", "minor channel"),
    (r"\bCantrip\b", "Minor channel"),
    (r"\bmagic item\b", "relic"),
    (r"\bMagic item\b", "Relic"),
    (r"\bmagic items\b", "relics"),
    (r"\bMagic items\b", "Relics"),
    (r"\bpotion\b", "draught"),
    (r"\bPotion\b", "Draught"),
    (r"\bscroll\b", "script"),
    (r"\bScroll\b", "Script"),
    (r"\badvantage\b", "edge"),
    (r"\bAdvantage\b", "Edge"),
    (r"\bdisadvantage\b", "strain"),
    (r"\bDisadvantage\b", "Strain"),
)


def class_label(class_name: str) -> str:
    return CLASS_PUBLIC_LABELS.get(class_name, class_name)


def race_label(race_name: str) -> str:
    return RACE_PUBLIC_LABELS.get(race_name, race_name)


def ability_label(code: str, *, include_code: bool = False) -> str:
    public = ABILITY_PUBLIC_LABELS.get(code, code)
    if include_code and code in ABILITY_PUBLIC_LABELS:
        return f"{public} ({code})"
    return public


def ability_full_label(code: str) -> str:
    public = ABILITY_PUBLIC_LABELS.get(code)
    base = ABILITY_FULL_LABELS.get(code, code)
    return f"{public} ({base})" if public and public != base else base


def skill_label(skill_name: str) -> str:
    return SKILL_PUBLIC_LABELS.get(skill_name, skill_name)


def skill_option_label(skill_name: str) -> str:
    public = skill_label(skill_name)
    return public if public == skill_name else f"{public} ({skill_name})"


def feature_label(feature_id: str) -> str:
    if feature_id in FEATURE_PUBLIC_LABELS:
        return FEATURE_PUBLIC_LABELS[feature_id]
    label = feature_id.replace("_barbarian", "").replace("_monk", "")
    return label.replace("_", " ").title()


def resource_label(resource_name: str) -> str:
    if resource_name.startswith("spell_slots_"):
        return f"charge band {resource_name.rsplit('_', 1)[-1]}"
    return RESOURCE_PUBLIC_LABELS.get(resource_name, resource_name.replace("_", " "))


def spell_label(spell_id_or_name: str, fallback: str | None = None) -> str:
    spell_id = SPELL_NAME_TO_ID.get(spell_id_or_name, spell_id_or_name)
    return SPELL_PUBLIC_LABELS.get(spell_id, fallback or spell_id_or_name.replace("_", " ").title())


def class_option_label(class_name: str) -> str:
    public = class_label(class_name)
    return public if public == class_name else f"{public} ({class_name})"


def race_option_label(race_name: str) -> str:
    public = race_label(race_name)
    return public if public == race_name else f"{public} ({race_name})"


def character_role_line(race_name: str, class_name: str) -> str:
    return f"{race_label(race_name)} {class_label(class_name)}"


def format_bonus_list(bonuses: Mapping[str, int], *, include_codes: bool = False) -> str:
    return ", ".join(f"{ability_label(ability, include_code=include_codes)} +{value}" for ability, value in bonuses.items())


def marks_label(value: int) -> str:
    return f"{value} mark" if value == 1 else f"{value} marks"


def guard_label(value: int) -> str:
    return f"Guard {value}"


def target_guard_label(value: int) -> str:
    return f"Guard {value}"


def d20_edge_label(advantage_state: int) -> str:
    if advantage_state > 0:
        return "edge"
    if advantage_state < 0:
        return "strain"
    return ""


def rules_text(text: str) -> str:
    rendered = text
    for pattern, replacement in TERM_REPLACEMENTS:
        rendered = re.sub(pattern, replacement, rendered)
    return rendered
