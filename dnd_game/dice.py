from __future__ import annotations

from dataclasses import dataclass, field
import random
import re


_DICE_RE = re.compile(r"\s*(?P<count>\d*)d(?P<sides>\d+)(?P<modifier>[+-]\d+)?\s*")


@dataclass(slots=True)
class RollOutcome:
    expression: str
    total: int
    rolls: list[int] = field(default_factory=list)
    modifier: int = 0

    def describe(self) -> str:
        core = "+".join(str(value) for value in self.rolls) if self.rolls else "0"
        if self.modifier > 0:
            core = f"{core}+{self.modifier}"
        elif self.modifier < 0:
            core = f"{core}{self.modifier}"
        return f"{self.expression}: {core} = {self.total}"


@dataclass(slots=True)
class D20Outcome:
    kept: int
    rolls: list[int]
    rerolls: list[tuple[int, int]] = field(default_factory=list)
    advantage_state: int = 0

    def describe(self) -> str:
        if self.advantage_state == 0:
            return f"d20 -> {self.kept}"
        mode = "edge" if self.advantage_state > 0 else "strain"
        shown = "/".join(str(value) for value in self.rolls)
        return f"d20 ({mode}) -> {shown}, kept {self.kept}"


def ability_modifier(score: int) -> int:
    return (score - 10) // 2


def roll(expression: str, rng: random.Random | None = None, *, critical: bool = False) -> RollOutcome:
    match = _DICE_RE.fullmatch(expression)
    if match is None:
        raise ValueError(f"Unsupported dice expression: {expression}")

    roller = rng or random.Random()
    count = int(match.group("count") or "1")
    sides = int(match.group("sides"))
    modifier = int(match.group("modifier") or "0")
    if critical:
        count *= 2
    rolls = [roller.randint(1, sides) for _ in range(count)]
    animator = getattr(roller, "dice_roll_animator", None)
    if callable(animator):
        display_bonus = getattr(roller, "dice_roll_display_bonus", 0)
        style = getattr(roller, "dice_roll_style", None)
        outcome_kind = getattr(roller, "dice_roll_outcome_kind", None)
        context_label = getattr(roller, "dice_roll_context_label", None)
        animator(
            kind="roll",
            expression=expression,
            sides=sides,
            rolls=list(rolls),
            modifier=modifier,
            display_modifier=modifier + display_bonus,
            critical=critical,
            style=style,
            outcome_kind=outcome_kind,
            context_label=context_label,
        )
    return RollOutcome(expression=expression, total=sum(rolls) + modifier, rolls=rolls, modifier=modifier)


def roll_d20(
    rng: random.Random | None = None,
    *,
    advantage_state: int = 0,
    lucky: bool = False,
) -> D20Outcome:
    roller = rng or random.Random()
    raw_rolls = [roller.randint(1, 20)]
    if advantage_state != 0:
        raw_rolls.append(roller.randint(1, 20))

    processed: list[int] = []
    rerolls: list[tuple[int, int]] = []
    for value in raw_rolls:
        if lucky and value == 1:
            rerolled = roller.randint(1, 20)
            rerolls.append((value, rerolled))
            processed.append(rerolled)
        else:
            processed.append(value)

    if advantage_state > 0:
        kept = max(processed)
    elif advantage_state < 0:
        kept = min(processed)
    else:
        kept = processed[0]
    animator = getattr(roller, "dice_roll_animator", None)
    if callable(animator):
        target_number = getattr(roller, "dice_roll_target_number", None)
        target_label = getattr(roller, "dice_roll_target_label", None)
        total_modifier = getattr(roller, "dice_roll_total_modifier", 0)
        context_label = getattr(roller, "dice_roll_context_label", None)
        style = getattr(roller, "dice_roll_style", None)
        outcome_kind = getattr(roller, "dice_roll_outcome_kind", None)
        animator(
            kind="d20",
            expression="d20",
            sides=20,
            rolls=list(processed),
            modifier=total_modifier,
            critical=False,
            advantage_state=advantage_state,
            rerolls=list(rerolls),
            kept=kept,
            target_number=target_number,
            target_label=target_label,
            context_label=context_label,
            style=style,
            outcome_kind=outcome_kind,
        )
    return D20Outcome(kept=kept, rolls=processed, rerolls=rerolls, advantage_state=advantage_state)
