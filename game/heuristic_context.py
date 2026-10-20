"""Context bất biến để solver sử dụng heuristic mà không đọc Board internals."""

from dataclasses import dataclass

from game.state import Cell


@dataclass(frozen=True, slots=True)
class HeuristicContext:
    """Dữ liệu tĩnh và cost cần cho heuristic của một level.

    ``support_cells`` là relaxed support: mọi ô khác VOID đều được đưa vào,
    kể cả bridge đang đóng và fragile. ``split_switch_cells`` chỉ chứa vị trí
    các split switch; bản H2 split-safe dùng chúng làm pseudo-goals.
    """

    support_cells: frozenset[Cell]
    goal: Cell
    split_switch_cells: frozenset[Cell]
    stand_roll: float
    lie_roll: float

