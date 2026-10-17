"""Mô hình trạng thái (State) của trò chơi Bloxorz."""

from dataclasses import dataclass
from typing import Any

from game.actions import Orientation

# Kiểu tọa độ cho một ô trên bảng (row, col)
Cell = tuple[int, int]

# TODO(TV2): chốt kiểu biểu diễn trạng thái cầu với TV2
BridgeStates = tuple[bool, ...]


@dataclass(frozen=True, slots=True)
class State:
    """Trạng thái bất biến (immutable) và có thể băm (hashable) của trò chơi.

    Attributes:
        block_position: Tọa độ neo (anchor) của khối hộp (ô trên cùng bên trái).
        orientation: Hướng hiện tại của khối hộp (STANDING, HORIZONTAL, VERTICAL).
        bridge_states: Trạng thái đóng/mở của các cây cầu (provisional).
        split_mode: Cờ đánh dấu khối có đang bị tách thành 2 khối lập phương hay không.
        cube1_position: Tọa độ khối lập phương 1 khi ở chế độ split.
        cube2_position: Tọa độ khối lập phương 2 khi ở chế độ split.
        active_cube: Khối lập phương đang được điều khiển (1 hoặc 2) trong chế độ split.
    """

    block_position: Cell
    orientation: Orientation
    bridge_states: BridgeStates = ()
    split_mode: bool = False
    cube1_position: Cell | None = None
    cube2_position: Cell | None = None
    active_cube: int | None = None

    def occupied_cells(self) -> tuple[Cell, ...]:
        """Trả về danh sách tọa độ các ô mà khối đang chiếm giữ (chế độ không split)."""
        r, c = self.block_position
        match self.orientation:
            case Orientation.STANDING:
                return ((r, c),)
            case Orientation.HORIZONTAL:
                return ((r, c), (r, c + 1))
            case Orientation.VERTICAL:
                return ((r, c), (r + 1, c))

    def to_dict(self) -> dict[str, Any]:
        """Xuất trạng thái ra dạng từ điển (dict) tương thích JSON cho Three.js GUI."""
        return {
            "block_position": [self.block_position[0], self.block_position[1]],
            "orientation": self.orientation.name,
            "bridge_states": list(self.bridge_states),
            "split_mode": self.split_mode,
            "cube1_position": (
                [self.cube1_position[0], self.cube1_position[1]]
                if self.cube1_position is not None
                else None
            ),
            "cube2_position": (
                [self.cube2_position[0], self.cube2_position[1]]
                if self.cube2_position is not None
                else None
            ),
            "active_cube": self.active_cube,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "State":
        """Khôi phục đối tượng State từ từ điển dữ liệu (dict)."""
        block_pos: Cell = (int(data["block_position"][0]), int(data["block_position"][1]))
        orientation = Orientation[data["orientation"]]
        bridge_states: BridgeStates = tuple(bool(x) for x in data.get("bridge_states", ()))
        split_mode = bool(data.get("split_mode", False))

        c1 = data.get("cube1_position")
        cube1_pos: Cell | None = (int(c1[0]), int(c1[1])) if c1 is not None else None

        c2 = data.get("cube2_position")
        cube2_pos: Cell | None = (int(c2[0]), int(c2[1])) if c2 is not None else None

        active_cube = data.get("active_cube")
        if active_cube is not None:
            active_cube = int(active_cube)

        return cls(
            block_position=block_pos,
            orientation=orientation,
            bridge_states=bridge_states,
            split_mode=split_mode,
            cube1_position=cube1_pos,
            cube2_position=cube2_pos,
            active_cube=active_cube,
        )


def occupied_cells(state: State) -> tuple[Cell, ...]:
    """Hàm tiện ích trả về danh sách các ô mà khối đang chiếm giữ."""
    return state.occupied_cells()
