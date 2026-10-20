"""Cấu hình hàm chi phí `step_cost` của Engine (TV2).

Chi phí phi đồng nhất giúp UCS/A* (TV4) phân biệt đường đi theo tư thế khối,
vẫn giữ heuristic hiện hành của A* admissible (mọi bước lăn tốn >= 1.0).
"""

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


DEFAULT_COST = CostConfig()
