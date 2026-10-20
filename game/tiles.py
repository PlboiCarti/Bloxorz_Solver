"""Luật nâng đỡ của từng loại ô (fragile, bridge) — TV2."""

from game.board import Board, TileType
from game.state import BridgeStates, Cell
from game.switches import LevelMechanics

# Thứ tự ưu tiên lý do rơi khi một bước đi có nhiều ô cùng không được nâng đỡ.
_FALL_PRECEDENCE: tuple[str, ...] = ("off_board", "void", "bridge_closed", "fragile_standing")


def support_failure(
    board: Board,
    mechanics: LevelMechanics,
    cells: tuple[Cell, ...],
    bridge_states: BridgeStates,
    *,
    full_block_standing: bool,
) -> str | None:
    """Trả về lý do rơi của các ô `cells`, hoặc None nếu mọi ô đều được nâng đỡ.

    Lý do theo quy ước `docs/gui_api.md` §3.3: `off_board`, `void`, `bridge_closed`,
    `fragile_standing`. Thứ tự ưu tiên khi nhiều ô cùng lỗi:
    `off_board` -> `void` -> `bridge_closed` -> `fragile_standing`.

    Args:
        full_block_standing: True nếu là khối 1x1x2 (không split) đang STANDING.
    """
    reasons: set[str] = set()
    for cell in cells:
        if not board.in_bounds(cell):
            reasons.add("off_board")
            continue
        tile = board.tile_at(cell)
        if tile is TileType.VOID:
            reasons.add("void")
        elif tile is TileType.FRAGILE:
            if full_block_standing:
                reasons.add("fragile_standing")
        elif tile is TileType.BRIDGE and not bridge_states[mechanics.bridge_index_by_cell[cell]]:
            reasons.add("bridge_closed")
    for reason in _FALL_PRECEDENCE:
        if reason in reasons:
            return reason
    return None


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
