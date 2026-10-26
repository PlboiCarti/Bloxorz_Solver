"""Chế độ tách khối (split), đổi khối điều khiển và hợp khối (merge) — TV2.

Quy ước State khi split_mode == True:
- cube1_position, cube2_position: vị trí hai khối lập phương 1x1x1.
- active_cube: 1 hoặc 2, khối đang nhận lệnh di chuyển.
- block_position: luôn bằng vị trí khối đang điều khiển; orientation luôn STANDING.
"""

from dataclasses import replace

from game.actions import Action, Orientation
from game.state import BridgeStates, Cell, State

# Mỗi bước, khối lập phương lăn đúng 1 ô
_CUBE_DELTA: dict[Action, tuple[int, int]] = {
    Action.UP: (-1, 0),
    Action.DOWN: (1, 0),
    Action.LEFT: (0, -1),
    Action.RIGHT: (0, 1),
}


def _cubes(state: State) -> tuple[Cell, Cell]:
    """Lấy vị trí hai khối lập phương (giả định state đang split)."""
    if state.cube1_position is None or state.cube2_position is None:
        raise ValueError("State ở split_mode phải có đủ cube1_position và cube2_position.")
    return state.cube1_position, state.cube2_position


def make_split_state(bridge_states: BridgeStates, cells: tuple[Cell, Cell]) -> State:
    """Tạo state sau khi tách khối: cube1, cube2 dịch chuyển tới `cells`, điều khiển cube1."""
    c1, c2 = cells
    return State(
        block_position=c1,
        orientation=Orientation.STANDING,
        bridge_states=bridge_states,
        split_mode=True,
        cube1_position=c1,
        cube2_position=c2,
        active_cube=1,
    )


def active_cube_cell(state: State) -> Cell:
    """Vị trí khối lập phương đang được điều khiển."""
    c1, c2 = _cubes(state)
    return c1 if state.active_cube == 1 else c2


def switch_active_cube(state: State) -> State:
    """Đổi quyền điều khiển sang khối lập phương còn lại (Action.SWITCH_CUBE)."""
    c1, c2 = _cubes(state)
    new_active = 2 if state.active_cube == 1 else 1
    return replace(state, active_cube=new_active, block_position=c2 if new_active == 2 else c1)


def move_active_cube(state: State, action: Action) -> State | None:
    """Di chuyển khối đang điều khiển 1 ô. Không kiểm tra nền (Engine kiểm tra sau).

    Trả về None nếu action không phải hướng di chuyển hoặc ô đích đang có khối còn lại.
    """
    delta = _CUBE_DELTA.get(action)
    if delta is None:
        return None
    c1, c2 = _cubes(state)
    r, c = active_cube_cell(state)
    target: Cell = (r + delta[0], c + delta[1])
    if state.active_cube == 1:
        if target == c2:
            return None
        return replace(state, cube1_position=target, block_position=target)
    if target == c1:
        return None
    return replace(state, cube2_position=target, block_position=target)


def try_merge(state: State) -> State:
    """Hợp hai khối lập phương thành khối 1x1x2 nếu chúng nằm ở hai ô kề nhau.

    Kề ngang -> HORIZONTAL, kề dọc -> VERTICAL; anchor là ô trên cùng bên trái.
    Nếu không kề nhau, trả về nguyên state.
    """
    c1, c2 = _cubes(state)
    dr, dc = abs(c1[0] - c2[0]), abs(c1[1] - c2[1])
    if (dr, dc) == (0, 1):
        orientation = Orientation.HORIZONTAL
    elif (dr, dc) == (1, 0):
        orientation = Orientation.VERTICAL
    else:
        return state
    return State(
        block_position=min(c1, c2),
        orientation=orientation,
        bridge_states=state.bridge_states,
        split_mode=False,
        cube1_position=None,
        cube2_position=None,
        active_cube=None,
    )
