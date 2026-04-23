from __future__ import annotations

from ..content import POINT_BUY_COSTS
from ..data.story.public_terms import ability_label
from ..models import ABILITY_ORDER


POINT_BUY_BUDGET = 27


class PointBuyCreationMixin:
    def choose_point_buy_scores(self) -> dict[str, int]:
        while True:
            self.banner("Point Buy")
            scores: dict[str, int] = {}
            spent = 0
            for ability in ABILITY_ORDER:
                score = self.prompt_point_buy_score(ability, points_left=POINT_BUY_BUDGET - spent)
                scores[ability] = score
                spent += POINT_BUY_COSTS[score]
                self.say(f"{ability_label(ability, include_code=True)} set to {score}. Points left: {POINT_BUY_BUDGET - spent}.")

            summary = ", ".join(f"{ability_label(ability, include_code=True)} {scores[ability]}" for ability in ABILITY_ORDER)
            self.say(f"Point-buy draft: {summary}.")
            self.say(f"Total spent: {spent} of {POINT_BUY_BUDGET}. Points left: {POINT_BUY_BUDGET - spent}.")
            if self.confirm("Keep these point-buy scores?"):
                return scores
            self.say("Let's repick the full stat spread.")

    def prompt_point_buy_score(self, ability: str, *, points_left: int) -> int:
        while True:
            self.output_fn("")
            self.say(
                f"Set {ability_label(ability, include_code=True)}. Enter a score from 8 to 15. "
                f"Points left before this pick: {points_left}."
            )
            raw = self.read_input("> ").strip()
            if self.handle_meta_command(raw):
                continue
            if raw.isdigit():
                score = int(raw)
                if score not in POINT_BUY_COSTS:
                    self.say("Point-buy scores must be between 8 and 15.")
                    continue
                cost = POINT_BUY_COSTS[score]
                if cost > points_left:
                    self.say(f"{score} costs {cost} points, but you only have {points_left} left.")
                    continue
                return score
            self.say("Enter a number from 8 to 15.")
