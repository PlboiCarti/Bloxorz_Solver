"""Context bất biến để solver sử dụng heuristic mà không đọc Board internals."""

from dataclasses import dataclass

from game.state import Cell


@dataclass(frozen=True, slots=True)
class SplitSwitchContext:
    """Thông tin tĩnh cần cho abstract split-pair transition."""

    cell: Cell
    split_cells: tuple[Cell, Cell]


@dataclass(frozen=True, slots=True)
class HeuristicContext:
    """Dữ liệu tĩnh và cost cần cho heuristic của một level.

    ``support_cells`` là relaxed support: mọi ô khác VOID đều được đưa vào,
    kể cả bridge đang đóng và fragile. ``split_switches`` chứa cả vị trí công
    tắc và hai vị trí cube sau khi split để H2 có thể xây split-pair graph.
    """

    support_cells: frozenset[Cell]
    goal: Cell
    split_switches: tuple[SplitSwitchContext, ...]
    stand_roll: float
    lie_roll: float

    @property
    def split_switch_cells(self) -> frozenset[Cell]:
        """Tương thích với API baseline: chỉ lấy vị trí các split switch."""
        return frozenset(item.cell for item in self.split_switches)

