from __future__ import annotations

SPELL_SLOT_LEVELS = (1, 2, 3, 4)

FULL_CASTER_CLASSES = {"Bard", "Cleric", "Druid", "Sorcerer", "Wizard"}
HALF_CASTER_CLASSES = {"Paladin", "Ranger"}
WARLOCK_CLASSES = {"Warlock"}

FULL_CASTER_SLOT_TABLE: dict[int, dict[int, int]] = {
    1: {1: 2},
    2: {1: 3},
    3: {1: 4, 2: 2},
    4: {1: 4, 2: 3},
    5: {1: 4, 2: 3, 3: 2},
    6: {1: 4, 2: 3, 3: 3},
    7: {1: 4, 2: 3, 3: 3, 4: 1},
    8: {1: 4, 2: 3, 3: 3, 4: 2},
}

HALF_CASTER_SLOT_TABLE: dict[int, dict[int, int]] = {
    1: {},
    2: {1: 2},
    3: {1: 3},
    4: {1: 3},
    5: {1: 4, 2: 2},
    6: {1: 4, 2: 2},
    7: {1: 4, 2: 3},
    8: {1: 4, 2: 3},
}

WARLOCK_PACT_SLOT_TABLE: dict[int, dict[int, int]] = {
    1: {1: 1},
    2: {1: 2},
    3: {2: 2},
    4: {2: 2},
    5: {3: 2},
    6: {3: 2},
    7: {4: 2},
    8: {4: 2},
}


def spell_slot_resource_name(slot_level: int) -> str:
    return f"spell_slots_{slot_level}"


def spell_slot_resource_names() -> list[str]:
    return [spell_slot_resource_name(level) for level in SPELL_SLOT_LEVELS]


def is_spell_slot_resource(resource_name: str) -> bool:
    return resource_name in set(spell_slot_resource_names())


def spell_slot_capacity_for(class_name: str, level: int) -> dict[int, int]:
    bounded_level = max(1, min(8, int(level)))
    if class_name in FULL_CASTER_CLASSES:
        return dict(FULL_CASTER_SLOT_TABLE.get(bounded_level, {}))
    if class_name in HALF_CASTER_CLASSES:
        return dict(HALF_CASTER_SLOT_TABLE.get(bounded_level, {}))
    if class_name in WARLOCK_CLASSES:
        return dict(WARLOCK_PACT_SLOT_TABLE.get(bounded_level, {}))
    return {}


def synchronize_spell_slots(actor, *, refill: bool) -> dict[int, int]:
    capacities = spell_slot_capacity_for(actor.class_name, actor.level)
    actor.resources.pop("spell_slots", None)
    actor.max_resources.pop("spell_slots", None)
    for slot_level in SPELL_SLOT_LEVELS:
        key = spell_slot_resource_name(slot_level)
        maximum = int(capacities.get(slot_level, 0))
        if maximum <= 0:
            actor.max_resources.pop(key, None)
            actor.resources.pop(key, None)
            continue
        actor.max_resources[key] = maximum
        current = int(actor.resources.get(key, maximum))
        actor.resources[key] = maximum if refill else min(current, maximum)
    return capacities


def spell_slot_counts(actor, *, maximum: bool = False) -> dict[int, int]:
    source = actor.max_resources if maximum else actor.resources
    counts: dict[int, int] = {}
    for slot_level in SPELL_SLOT_LEVELS:
        key = spell_slot_resource_name(slot_level)
        value = int(source.get(key, 0))
        if value > 0:
            counts[slot_level] = value
    return counts


def has_spell_slots(actor, *, minimum_level: int = 1) -> bool:
    return any(count > 0 for level, count in spell_slot_counts(actor).items() if level >= minimum_level)


def total_spell_slots(actor, *, maximum: bool = False) -> int:
    return sum(spell_slot_counts(actor, maximum=maximum).values())


def spend_spell_slot(actor, *, minimum_level: int = 1, preferred_level: int | None = None) -> int | None:
    available = spell_slot_counts(actor)
    if preferred_level is not None and preferred_level >= minimum_level and available.get(preferred_level, 0) > 0:
        key = spell_slot_resource_name(preferred_level)
        actor.resources[key] -= 1
        return preferred_level
    for slot_level in sorted(available):
        if slot_level < minimum_level or available[slot_level] <= 0:
            continue
        key = spell_slot_resource_name(slot_level)
        actor.resources[key] -= 1
        return slot_level
    return None


def restore_spell_slots(actor, amount: int = 1) -> list[int]:
    restored_levels: list[int] = []
    for _ in range(max(0, amount)):
        for slot_level in SPELL_SLOT_LEVELS:
            key = spell_slot_resource_name(slot_level)
            maximum = int(actor.max_resources.get(key, 0))
            current = int(actor.resources.get(key, 0))
            if maximum > current:
                actor.resources[key] = current + 1
                restored_levels.append(slot_level)
                break
        else:
            break
    return restored_levels


def restore_all_spell_slots(actor) -> None:
    for slot_level in SPELL_SLOT_LEVELS:
        key = spell_slot_resource_name(slot_level)
        if key in actor.max_resources:
            actor.resources[key] = int(actor.max_resources[key])


def spell_slot_summary(actor) -> str:
    parts: list[str] = []
    maximums = spell_slot_counts(actor, maximum=True)
    for slot_level in SPELL_SLOT_LEVELS:
        maximum = maximums.get(slot_level, 0)
        if maximum <= 0:
            continue
        current = int(actor.resources.get(spell_slot_resource_name(slot_level), 0))
        parts.append(f"Band {slot_level} {current}/{maximum}")
    return ", ".join(parts) if parts else "None"


def restored_spell_slot_summary(levels: list[int]) -> str:
    if not levels:
        return ""
    counts: dict[int, int] = {}
    for level in levels:
        counts[level] = counts.get(level, 0) + 1
    parts = [f"{count} charge band {level}{'s' if count != 1 else ''}" for level, count in sorted(counts.items())]
    return ", ".join(parts)
