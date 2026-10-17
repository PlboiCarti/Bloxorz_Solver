"""Luật nâng đỡ của từng loại ô (fragile, bridge) — TV2."""

from game.board import Board, TileType
from game.state import BridgeStates, Cell
from game.switches import LevelMechanics


def is_cell_supported(
    board: Board,
    mechanics: LevelMechanics,
    cell: Cell,
    bridge_states: BridgeStates,
    *,
    full_block_standing: bool,
) -> bool:
    """Kiểm tra một ô có nâng đỡ được phần khối đặt lên hay không.

    - Ngoài bảng hoặc VOID: không đỡ.
    - FRAGILE: vỡ nếu khối 1x1x2 đứng thẳng lên; khối nằm hoặc khối lập phương 1x1x1 thì an toàn.
    - BRIDGE: chỉ đỡ khi cầu đang mở theo `bridge_states`.
    - Các ô còn lại (sàn, đích, công tắc): luôn đỡ.

    Args:
        full_block_standing: True nếu là khối 1x1x2 (không split) đang STANDING.
    """
    if not board.in_bounds(cell):
        return False
    tile = board.tile_at(cell)
    if tile is TileType.VOID:
        return False
    if tile is TileType.FRAGILE:
        return not full_block_standing
    if tile is TileType.BRIDGE:
        return bridge_states[mechanics.bridge_index_by_cell[cell]]
    return True
