"""Cơ chế công tắc (switch) và cầu (bridge) của Bloxorz — TV2.

Module này:
- Kiểm thực sâu (deep validation) cấu hình `bridges`/`switches` thô của `Board`.
- Lập chỉ mục tra cứu nhanh: ô -> chỉ số cầu, ô -> công tắc.
- Cung cấp các hàm thuần túy để xét công tắc có kích hoạt không và cập nhật trạng thái cầu.

Quy ước `BridgeStates`: tuple[bool, ...], phần tử thứ i ứng với cầu thứ i trong
danh sách `bridges` của file màn chơi; True = cầu MỞ (đi được), False = cầu ĐÓNG (như VOID).
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from game.board import Board, TileType
from game.state import BridgeStates, Cell


class SwitchType(Enum):
    """Ba loại công tắc trong Bloxorz."""

    SOFT = "soft"    # Kích hoạt khi bất kỳ phần nào của khối đè lên
    HEAVY = "heavy"  # Chỉ kích hoạt khi khối 1x1x2 đứng thẳng lên
    SPLIT = "split"  # Chỉ kích hoạt khi khối 1x1x2 đứng thẳng; tách thành 2 khối lập phương


class BridgeMode(Enum):
    """Cách một công tắc tác động lên cầu mục tiêu."""

    TOGGLE = "toggle"                      # Đảo trạng thái mở/đóng
    PERMANENT_OPEN = "permanent_open"      # Luôn đặt thành mở
    PERMANENT_CLOSED = "permanent_closed"  # Luôn đặt thành đóng


# Loại ô bắt buộc trên lưới cho từng loại công tắc
_SWITCH_TILE: dict[SwitchType, TileType] = {
    SwitchType.SOFT: TileType.SOFT_SWITCH,
    SwitchType.HEAVY: TileType.HEAVY_SWITCH,
    SwitchType.SPLIT: TileType.SPLIT_SWITCH,
}

_INITIAL_VALUES: dict[str, bool] = {"open": True, "closed": False}


@dataclass(frozen=True, slots=True)
class BridgeSpec:
    """Cấu hình một ô cầu."""

    id: str
    cell: Cell
    initially_open: bool


@dataclass(frozen=True, slots=True)
class SwitchTarget:
    """Một cầu mục tiêu của công tắc cùng chế độ tác động."""

    bridge_index: int
    mode: BridgeMode


@dataclass(frozen=True, slots=True)
class SwitchSpec:
    """Cấu hình một công tắc."""

    cell: Cell
    type: SwitchType
    targets: tuple[SwitchTarget, ...]
    split_cells: tuple[Cell, Cell] | None = None


@dataclass(frozen=True, slots=True, eq=False)
class LevelMechanics:
    """Cấu hình cơ chế nâng cao đã kiểm thực của một màn chơi (chỉ đọc)."""

    bridges: tuple[BridgeSpec, ...]
    switches: tuple[SwitchSpec, ...]
    bridge_index_by_cell: dict[Cell, int]
    switch_by_cell: dict[Cell, SwitchSpec]

    def initial_bridge_states(self) -> BridgeStates:
        """Trạng thái cầu ban đầu theo trường `initial` của từng cầu."""
        return tuple(bridge.initially_open for bridge in self.bridges)


def is_triggered(switch: SwitchSpec, *, full_block_standing: bool) -> bool:
    """Xét công tắc có được kích hoạt bởi phần khối vừa đặt lên hay không.

    Args:
        switch: Công tắc bị đè.
        full_block_standing: True nếu là khối 1x1x2 (không split) đang STANDING.
    """
    if switch.type is SwitchType.SOFT:
        return True
    # HEAVY và SPLIT chỉ kích hoạt khi khối nguyên vẹn đứng thẳng
    return full_block_standing


def apply_targets(bridge_states: BridgeStates, targets: tuple[SwitchTarget, ...]) -> BridgeStates:
    """Trả về trạng thái cầu mới sau khi áp dụng các mục tiêu của công tắc (hàm thuần túy)."""
    if not targets:
        return bridge_states
    states = list(bridge_states)
    for target in targets:
        match target.mode:
            case BridgeMode.TOGGLE:
                states[target.bridge_index] = not states[target.bridge_index]
            case BridgeMode.PERMANENT_OPEN:
                states[target.bridge_index] = True
            case BridgeMode.PERMANENT_CLOSED:
                states[target.bridge_index] = False
    return tuple(states)


# --- Kiểm thực và lập chỉ mục ---


def _parse_cell(board: Board, value: Any, where: str) -> Cell:
    """Chuyển [r, c] thành Cell và kiểm tra nằm trong bảng."""
    if (
        not isinstance(value, (list, tuple))
        or len(value) != 2
        or not all(isinstance(v, int) and not isinstance(v, bool) for v in value)
    ):
        raise ValueError(f"{where}: tọa độ phải có dạng [row, col] gồm 2 số nguyên (nhận {value!r}).")
    cell: Cell = (value[0], value[1])
    if not board.in_bounds(cell):
        raise ValueError(f"{where}: tọa độ {cell} nằm ngoài bảng ({board.rows}x{board.cols}).")
    return cell


def _cells_of(board: Board, tile_types: set[TileType]) -> set[Cell]:
    """Tập các ô trên lưới có loại thuộc `tile_types`."""
    return {
        (r, c)
        for r in range(board.rows)
        for c in range(board.cols)
        if board.grid[r][c] in tile_types
    }


def _build_bridges(board: Board) -> tuple[tuple[BridgeSpec, ...], dict[str, int]]:
    bridges: list[BridgeSpec] = []
    index_by_id: dict[str, int] = {}
    seen_cells: set[Cell] = set()

    for i, raw in enumerate(board.bridges):
        where = f"bridges[{i}]"
        if not isinstance(raw, dict):
            raise ValueError(f"{where}: mỗi cầu phải là một object.")
        bridge_id = raw.get("id")
        if not isinstance(bridge_id, str) or not bridge_id:
            raise ValueError(f"{where}: thiếu 'id' dạng chuỗi khác rỗng.")
        if bridge_id in index_by_id:
            raise ValueError(f"{where}: trùng id cầu '{bridge_id}'.")
        cell = _parse_cell(board, raw.get("cell"), where)
        if board.tile_at(cell) is not TileType.BRIDGE:
            raise ValueError(f"{where}: ô {cell} trên lưới không phải ô cầu 'B'.")
        if cell in seen_cells:
            raise ValueError(f"{where}: ô {cell} đã được khai báo cho một cầu khác.")
        initial = raw.get("initial")
        if initial not in _INITIAL_VALUES:
            raise ValueError(f"{where}: 'initial' phải là 'open' hoặc 'closed' (nhận {initial!r}).")

        seen_cells.add(cell)
        index_by_id[bridge_id] = len(bridges)
        bridges.append(BridgeSpec(id=bridge_id, cell=cell, initially_open=_INITIAL_VALUES[initial]))

    missing = _cells_of(board, {TileType.BRIDGE}) - seen_cells
    if missing:
        raise ValueError(f"Các ô cầu 'B' sau chưa được khai báo trong 'bridges': {sorted(missing)}.")
    return tuple(bridges), index_by_id


def _build_switches(board: Board, index_by_id: dict[str, int]) -> tuple[SwitchSpec, ...]:
    switches: list[SwitchSpec] = []
    seen_cells: set[Cell] = set()

    for i, raw in enumerate(board.switches):
        where = f"switches[{i}]"
        if not isinstance(raw, dict):
            raise ValueError(f"{where}: mỗi công tắc phải là một object.")
        try:
            switch_type = SwitchType(raw.get("type"))
        except ValueError:
            raise ValueError(
                f"{where}: 'type' phải là 'soft', 'heavy' hoặc 'split' (nhận {raw.get('type')!r})."
            ) from None
        cell = _parse_cell(board, raw.get("cell"), where)
        expected_tile = _SWITCH_TILE[switch_type]
        if board.tile_at(cell) is not expected_tile:
            raise ValueError(
                f"{where}: ô {cell} phải là ký tự '{expected_tile.value}' cho công tắc {switch_type.value}."
            )
        if cell in seen_cells:
            raise ValueError(f"{where}: ô {cell} đã được khai báo cho một công tắc khác.")

        raw_targets = raw.get("targets", [])
        if not isinstance(raw_targets, list):
            raise ValueError(f"{where}: 'targets' phải là một danh sách.")
        targets: list[SwitchTarget] = []
        for j, raw_target in enumerate(raw_targets):
            twhere = f"{where}.targets[{j}]"
            if not isinstance(raw_target, dict):
                raise ValueError(f"{twhere}: mỗi mục tiêu phải là một object.")
            bridge_id = raw_target.get("bridge")
            if bridge_id not in index_by_id:
                raise ValueError(f"{twhere}: không tồn tại cầu có id {bridge_id!r}.")
            try:
                mode = BridgeMode(raw_target.get("mode"))
            except ValueError:
                raise ValueError(
                    f"{twhere}: 'mode' phải là 'toggle', 'permanent_open' hoặc 'permanent_closed' "
                    f"(nhận {raw_target.get('mode')!r})."
                ) from None
            targets.append(SwitchTarget(bridge_index=index_by_id[bridge_id], mode=mode))

        split_cells: tuple[Cell, Cell] | None = None
        raw_split = raw.get("split_cells")
        if switch_type is SwitchType.SPLIT:
            if not isinstance(raw_split, list) or len(raw_split) != 2:
                raise ValueError(f"{where}: công tắc split cần 'split_cells' gồm đúng 2 tọa độ.")
            c1 = _parse_cell(board, raw_split[0], f"{where}.split_cells[0]")
            c2 = _parse_cell(board, raw_split[1], f"{where}.split_cells[1]")
            if c1 == c2:
                raise ValueError(f"{where}: hai ô trong 'split_cells' phải khác nhau.")
            split_cells = (c1, c2)
        elif raw_split is not None:
            raise ValueError(f"{where}: chỉ công tắc split mới có 'split_cells'.")

        seen_cells.add(cell)
        switches.append(
            SwitchSpec(cell=cell, type=switch_type, targets=tuple(targets), split_cells=split_cells)
        )

    switch_tiles = {TileType.SOFT_SWITCH, TileType.HEAVY_SWITCH, TileType.SPLIT_SWITCH}
    missing = _cells_of(board, switch_tiles) - seen_cells
    if missing:
        raise ValueError(f"Các ô công tắc sau chưa được khai báo trong 'switches': {sorted(missing)}.")
    return tuple(switches)


def build_mechanics(board: Board) -> LevelMechanics:
    """Kiểm thực sâu cấu hình cầu/công tắc của `board` và lập chỉ mục tra cứu.

    Raises:
        ValueError: Nếu cấu hình cầu/công tắc không khớp với lưới hoặc sai định dạng.
    """
    bridges, index_by_id = _build_bridges(board)
    switches = _build_switches(board, index_by_id)
    return LevelMechanics(
        bridges=bridges,
        switches=switches,
        bridge_index_by_cell={bridge.cell: i for i, bridge in enumerate(bridges)},
        switch_by_cell={switch.cell: switch for switch in switches},
    )
