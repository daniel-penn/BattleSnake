from typing import Callable

from api import CodeBattlesBot, Context

DIRECTIONS = ("U", "D", "L", "R")
WeightFunction = Callable[[Context, str], float]

# Add functions taking (context, direction) and returning a numeric score here.
WEIGHT_FUNCTIONS: list[WeightFunction] = []


def lifter(context: Context, weight_functions: list[WeightFunction]) -> str:
    """Score all four directions, set the highest-scoring move, and return it."""
    scores = {
        direction: sum(weight(context, direction) for weight in weight_functions)
        for direction in DIRECTIONS
    }
    direction = max(scores, key=scores.get)
    context.set_direction(direction)
    return direction


class MyBot(CodeBattlesBot):
    def setup(self) -> None:
        self.weight_functions = list(WEIGHT_FUNCTIONS)

    def run(self) -> None:
        lifter(self.context, self.weight_functions)
