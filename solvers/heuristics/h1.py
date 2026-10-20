"""Heuristic Manhattan baseline (H1) cho benchmark."""

import math
from collections.abc import Callable

from game.heuristic_context import HeuristicContext
from game.state import State


def build_h1(context: HeuristicContext) -> Callable[[State], float]:
    """Tạo H1 anchor-Manhattan, giữ split state ở giá trị zero.

    H1 chỉ là baseline. Với level có split teleport, không nên dùng nó làm
    bằng chứng admissibility vì nó không mô hình hóa shortcut đó.
    """

    def heuristic(state: State) -> float:
        if state.split_mode:
            return 0.0

        row, col = state.block_position
        goal_row, goal_col = context.goal
        return float(math.ceil((abs(row - goal_row) + abs(col - goal_col)) / 2))

    return heuristic
