"""Hình học lăn khối dùng chung cho Engine và heuristic trừu tượng.

Module này chỉ chứa hình học thuần túy. Nó không kiểm tra nền, công tắc,
cầu hay điều kiện thắng; các phần đó vẫn thuộc về ``Engine``.
"""

from game.actions import Action, Orientation
from game.state import Cell

# (độ lệch anchor, orientation mới) cho block 1x1x2.
ROLL_TABLE: dict[
    tuple[Orientation, Action], tuple[tuple[int, int], Orientation]
] = {
    (Orientation.STANDING, Action.UP): ((-2, 0), Orientation.VERTICAL),
    (Orientation.STANDING, Action.DOWN): ((1, 0), Orientation.VERTICAL),
    (Orientation.STANDING, Action.LEFT): ((0, -2), Orientation.HORIZONTAL),
    (Orientation.STANDING, Action.RIGHT): ((0, 1), Orientation.HORIZONTAL),
    (Orientation.HORIZONTAL, Action.LEFT): ((0, -1), Orientation.STANDING),
    (Orientation.HORIZONTAL, Action.RIGHT): ((0, 2), Orientation.STANDING),
    (Orientation.HORIZONTAL, Action.UP): ((-1, 0), Orientation.HORIZONTAL),
    (Orientation.HORIZONTAL, Action.DOWN): ((1, 0), Orientation.HORIZONTAL),
    (Orientation.VERTICAL, Action.UP): ((-1, 0), Orientation.STANDING),
    (Orientation.VERTICAL, Action.DOWN): ((2, 0), Orientation.STANDING),
    (Orientation.VERTICAL, Action.LEFT): ((0, -1), Orientation.VERTICAL),
    (Orientation.VERTICAL, Action.RIGHT): ((0, 1), Orientation.VERTICAL),
}


def roll_geometry(
    position: Cell,
    orientation: Orientation,
    action: Action,
) -> tuple[Cell, Orientation] | None:
    """Tính anchor/orientation sau một lần lăn, không kiểm tra nền."""
    lookup = ROLL_TABLE.get((orientation, action))
    if lookup is None:
        return None

    delta, new_orientation = lookup
    return (position[0] + delta[0], position[1] + delta[1]), new_orientation


def pose_cells(position: Cell, orientation: Orientation) -> tuple[Cell, ...]:
    """Trả về các ô bị block chiếm khi ở một abstract pose."""
    row, col = position
    match orientation:
        case Orientation.STANDING:
            return ((row, col),)
        case Orientation.HORIZONTAL:
            return ((row, col), (row, col + 1))
        case Orientation.VERTICAL:
            return ((row, col), (row + 1, col))

