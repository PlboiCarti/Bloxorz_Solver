"""Cấu hình cost `step_cost` của Engine; giá trị phải hữu hạn và không âm."""

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CostConfig:
    """Tham số chi phí phi đồng nhất cho `Engine.step_cost`.

    Attributes:
        stand_roll: Chi phí lăn một bước khi đang STANDING (dịch neo 2 ô).
        lie_roll: Chi phí lăn một bước khi đang nằm HORIZONTAL/VERTICAL (dịch 1 ô).
        switch_cube: Chi phí đổi khối điều khiển trong split_mode.
        bridge_cross_penalty: Phụ phí dự trữ khi băng qua cầu (chưa dùng trong
            `step_cost` phiên bản này).
    """

    stand_roll: float = 1.5
    lie_roll: float = 1.0
    switch_cube: float = 0.1
    bridge_cross_penalty: float = 0.3

    def __post_init__(self) -> None:
        """Dijkstra/UCS/A* chỉ hỗ trợ cost hữu hạn và không âm."""
        for name, value in (
            ("stand_roll", self.stand_roll),
            ("lie_roll", self.lie_roll),
            ("switch_cube", self.switch_cube),
            ("bridge_cross_penalty", self.bridge_cross_penalty),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{name} must be a finite non-negative number.")
            try:
                valid = math.isfinite(value) and value >= 0
            except OverflowError:
                valid = False
            if not valid:
                raise ValueError(f"{name} must be a finite non-negative number.")


DEFAULT_COST = CostConfig()
