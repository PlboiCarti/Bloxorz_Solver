"""Bộ kiểm thử toàn diện cho các cơ chế nâng cao (Advanced Mechanics — TV2).

Bao gồm:
- Ô cam / giòn (Fragile tiles)
- Cầu (Bridges: ban đầu đóng/mở, nâng đỡ khối)
- Công tắc nhẹ (Soft switches: đứng, nằm ngang/dọc, cube 1x1)
- Công tắc nặng (Heavy switches: chỉ đứng mới kích hoạt)
- Các chế độ cầu: toggle, permanent_open, permanent_closed
- Công tắc phân tách (Split switches) & Chế độ phân tách (Split mode)
- Đổi khối điều khiển (SWITCH_CUBE)
- Hợp nhất khối (Merge: kề ngang -> HORIZONTAL, kề dọc -> VERTICAL)
- Kiểm thực cấu hình cầu/công tắc (Level validation)
- Kiểm thử tích hợp giải thành công từ level2.json đến level10.json
"""

from collections import deque
from pathlib import Path

import pytest

from game.actions import Action, Orientation
from game.board import load_board, parse_board
from game.engine import Engine, TransitionStatus
from game.split_block import (
    active_cube_cell,
    make_split_state,
    switch_active_cube,
    try_merge,
)
from game.state import State
from game.switches import build_mechanics


def step(engine: Engine, state: State, action: Action) -> State | None:
    """Helper tương thích: trả về State khi bước đi OK, ngược lại None."""
    result = engine.transition(state, action)
    return result.state if result.status is TransitionStatus.OK else None


# --- Helper giải BFS nhanh cho integration tests ---


def _bfs_solve(engine: Engine) -> list[Action] | None:
    start = engine.get_initial_state()
    parent: dict[State, tuple[State, Action] | None] = {start: None}
    q = deque([start])
    while q:
        s = q.popleft()
        if engine.is_goal(s):
            path: list[Action] = []
            cur = s
            while parent[cur] is not None:
                prev, action = parent[cur]  # type: ignore[misc]
                path.append(action)
                cur = prev
            return path[::-1]
        for a in engine.legal_actions(s):
            nxt = step(engine, s, a)
            assert nxt is not None
            if nxt not in parent:
                parent[nxt] = (s, a)
                q.append(nxt)
    return None


# --- 1. Fragile Tiles (Ô cam) ---


def test_fragile_standing_breaks():
    """Khối 1x1x2 đứng thẳng trên ô fragile sẽ rơi (transition trả về None)."""
    # Đang đứng tại (1, 1). Lăn DOWN -> VERTICAL tại (2, 1)-(3, 1) nhưng ngoài biên
    # Lăn RIGHT -> HORIZONTAL tại (1, 2)-(1, 3).
    # Hãy tạo một bản đồ mở nơi khối đứng lên ô F:
    grid2 = [
        "#####",
        "#S###",
        "##F##",
        "#####",
        "####G",
    ]
    e2 = Engine(parse_board({"name": "fragile_stand_open", "grid": grid2}))
    s = e2.get_initial_state()  # STANDING tại (1, 1)
    # RIGHT -> HORIZONTAL tại (1, 2)-(1, 3)
    s_right = step(e2, s, Action.RIGHT)
    assert s_right is not None
    assert s_right.orientation == Orientation.HORIZONTAL

    # Từ HORIZONTAL tại (1, 2)-(1, 3):
    # Lăn DOWN -> HORIZONTAL tại (2, 2)-(2, 3), ô (2, 2) là F! Nằm đè lên F là hợp lệ!
    s_down = step(e2, s_right, Action.DOWN)
    assert s_down is not None
    assert s_down.orientation == Orientation.HORIZONTAL

    # Bây giờ từ s_right (HORIZONTAL (1, 2)-(1, 3)):
    # Lăn LEFT -> STANDING tại (1, 1)
    # Thử tình huống khối đứng thẳng trực tiếp lên F tại (2, 2):
    # Đặt block tại STANDING (0, 2), lăn DOWN -> VERTICAL (1, 2)-(2, 2) (nằm dọc)
    # Lăn DOWN tiếp -> STANDING tại (3, 2).
    # Nhưng nếu block từ (2, 0) STANDING lăn RIGHT -> HORIZONTAL (2, 1)-(2, 2),
    # lăn RIGHT tiếp -> STANDING tại (2, 3) (ô cạnh F).
    # Nếu block từ (2, 4) STANDING lăn LEFT -> HORIZONTAL (2, 2)-(2, 3),
    # rồi lăn LEFT -> STANDING tại (2, 1).
    # Nếu block đứng trực tiếp lên F: ví dụ từ HORIZONTAL (2, 0)-(2, 1) lăn RIGHT -> STANDING tại (2, 2) (F):
    # S tại (1, 3), F tại (2, 3). S đứng tại (1, 3).
    # Nếu lăn DOWN -> VERTICAL tại (2, 3)-(3, 3) (nằm dọc qua F -> an toàn).
    # Để STANDING trên F: S tại (0, 3). Lăn DOWN -> VERTICAL (1, 3)-(2, 3). Lăn DOWN -> STANDING (3, 3).
    # Để STANDING trên F (2, 3): cần đứng từ (2, 1) lăn RIGHT 2 lần:
    # (2, 1) STANDING -> RIGHT -> HORIZONTAL (2, 2)-(2, 3) (nằm ngang qua F) -> RIGHT -> STANDING (2, 4).
    # Ngược lại: từ (2, 0) STANDING -> RIGHT -> HORIZONTAL (2, 1)-(2, 2) -> RIGHT -> STANDING (2, 3) [F]!
    grid_break = [
        "#######",
        "S######",
        "###F###",
        "#######",
        "######G",
    ]
    e_break = Engine(parse_board({"name": "break_test", "grid": grid_break}))
    s_start = State(block_position=(2, 0), orientation=Orientation.STANDING)
    s_h = step(e_break, s_start, Action.RIGHT)
    assert s_h is not None
    assert s_h.orientation == Orientation.HORIZONTAL
    assert s_h.block_position == (2, 1)  # chiếm (2, 1) và (2, 2)
    # Từ (2, 1)-(2, 2) HORIZONTAL, lăn RIGHT -> STANDING tại (2, 3) (ô F)!
    s_fall = step(e_break, s_h, Action.RIGHT)
    assert s_fall is None  # Rơi vỡ ô fragile!


def test_fragile_lying_supported():
    """Khối nằm ngang hoặc dọc đè lên ô fragile thì được nâng đỡ an toàn."""
    grid = [
        "######",
        "#SFF##",
        "######",
        "####G#",
    ]
    board = parse_board({"name": "fragile_lie", "grid": grid})
    engine = Engine(board)
    s0 = engine.get_initial_state()  # STANDING tại (1, 1)
    # Lăn RIGHT -> HORIZONTAL tại (1, 2) và (1, 3), cả 2 đều là F!
    s1 = step(engine, s0, Action.RIGHT)
    assert s1 is not None
    assert s1.orientation == Orientation.HORIZONTAL
    assert s1.occupied_cells() == ((1, 2), (1, 3))
    # Lăn RIGHT tiếp -> STANDING tại (1, 4) là sàn # bình thường -> an toàn!
    s2 = step(engine, s1, Action.RIGHT)
    assert s2 is not None
    assert s2.orientation == Orientation.STANDING
    assert s2.block_position == (1, 4)


def test_cube_stands_safely_on_fragile():
    """Trong chế độ split, khối lập phương 1x1 đứng trên ô fragile không bị vỡ."""
    grid = [
        "#####",
        "#S#G#",
        "##F##",
        "#####",
    ]
    board = parse_board({"name": "cube_fragile", "grid": grid})
    engine = Engine(board)
    # Tạo state split thủ công
    s_split = make_split_state(bridge_states=(), cells=((1, 2), (3, 3)))
    # active_cube là 1 tại (1, 2). Lăn DOWN -> tới (2, 2) là ô F!
    s_next = step(engine, s_split, Action.DOWN)
    assert s_next is not None
    assert s_next.split_mode is True
    assert s_next.cube1_position == (2, 2)
    assert active_cube_cell(s_next) == (2, 2)


# --- 2. Bridges & Switches ---


def test_bridge_closed_acts_as_void():
    """Cầu đang đóng hoạt động như void, khối đi vào sẽ rơi."""
    grid = [
        "####",
        "#S#B",
        "####",
        "###G",
    ]
    board = parse_board(
        {
            "name": "closed_bridge",
            "grid": grid,
            "bridges": [{"id": "B1", "cell": [1, 3], "initial": "closed"}],
        }
    )
    engine = Engine(board)
    s0 = engine.get_initial_state()
    # (1, 1) STANDING -> RIGHT -> HORIZONTAL tại (1, 2)-(1, 3) (trong đó (1, 3) là cầu đóng)
    nxt = step(engine, s0, Action.RIGHT)
    assert nxt is None


def test_bridge_open_supports_block():
    """Cầu mở nâng đỡ khối bình thường."""
    grid = [
        "####",
        "#S#B",
        "####",
        "###G",
    ]
    board = parse_board(
        {
            "name": "open_bridge",
            "grid": grid,
            "bridges": [{"id": "B1", "cell": [1, 3], "initial": "open"}],
        }
    )
    engine = Engine(board)
    s0 = engine.get_initial_state()
    nxt = step(engine, s0, Action.RIGHT)
    assert nxt is not None
    assert nxt.block_position == (1, 2)
    assert nxt.orientation == Orientation.HORIZONTAL


def test_soft_switch_activated_by_lying_and_standing():
    """Công tắc mềm 'o' kích hoạt khi đứng hoặc nằm đè lên."""
    grid = [
        "#####",
        "#SoB#",
        "#####",
        "####G",
    ]
    board = parse_board(
        {
            "name": "soft_switch_test",
            "grid": grid,
            "bridges": [{"id": "B1", "cell": [1, 3], "initial": "closed"}],
            "switches": [
                {
                    "cell": [1, 2],
                    "type": "soft",
                    "targets": [{"bridge": "B1", "mode": "toggle"}],
                }
            ],
        }
    )
    engine = Engine(board)
    s0 = engine.get_initial_state()
    assert s0.bridge_states == (False,)

    # Lăn RIGHT -> HORIZONTAL tại (1, 2)-(1, 3).
    # Nhưng ô (1, 3) là cầu đang closed TRƯỚC KHI bước chân xuống!
    # Nên bước đi này không hợp lệ vì (1, 3) chưa mở.
    assert step(engine, s0, Action.RIGHT) is None

    # Thay đổi bố cục: công tắc ở ô riêng để kích hoạt trước
    grid2 = [
        "######",
        "##o###",
        "#S##B#",
        "######",
        "#####G",
    ]
    board2 = parse_board(
        {
            "name": "soft_switch_layout2",
            "grid": grid2,
            "bridges": [{"id": "B1", "cell": [2, 4], "initial": "closed"}],
            "switches": [
                {
                    "cell": [1, 2],
                    "type": "soft",
                    "targets": [{"bridge": "B1", "mode": "toggle"}],
                }
            ],
        }
    )
    e2 = Engine(board2)
    s_init = e2.get_initial_state()
    assert s_init.bridge_states == (False,)
    # S tại (2, 1). Lăn UP -> VERTICAL tại (1, 1)-(0, 1).
    # Lăn RIGHT -> HORIZONTAL tại (2, 2)-(2, 3).
    s_r = step(e2, s_init, Action.RIGHT)
    assert s_r is not None
    # Từ HORIZONTAL tại (2, 2)-(2, 3), lăn UP -> HORIZONTAL tại (1, 2)-(1, 3)
    # Ô (1, 2) là 'o', khối đè lên khi đang HORIZONTAL (nằm)!
    s_up = step(e2, s_r, Action.UP)
    assert s_up is not None
    # Cầu B1 đã được toggle từ closed -> open!
    assert s_up.bridge_states == (True,)


def test_heavy_switch_requires_standing():
    """Công tắc nặng 'x' CHỈ kích hoạt khi khối STANDING lên nó."""
    grid = [
        "######",
        "##x###",
        "#S####",
        "###BB#",
        "#####G",
    ]
    board = parse_board(
        {
            "name": "heavy_switch_test",
            "grid": grid,
            "bridges": [
                {"id": "B1", "cell": [3, 3], "initial": "closed"},
                {"id": "B2", "cell": [3, 4], "initial": "closed"},
            ],
            "switches": [
                {
                    "cell": [1, 2],
                    "type": "heavy",
                    "targets": [
                        {"bridge": "B1", "mode": "permanent_open"},
                        {"bridge": "B2", "mode": "permanent_open"},
                    ],
                }
            ],
        }
    )
    engine = Engine(board)
    s0 = engine.get_initial_state()
    assert s0.bridge_states == (False, False)

    # 1. Nằm đè lên heavy switch:
    # S tại (2, 1) -> RIGHT -> HORIZONTAL (2, 2)-(2, 3)
    s_h = step(engine, s0, Action.RIGHT)
    assert s_h is not None
    # UP -> HORIZONTAL (1, 2)-(1, 3). Ô (1, 2) là 'x' nhưng khối đang nằm ngang!
    s_lying = step(engine, s_h, Action.UP)
    assert s_lying is not None
    # Cầu KHÔNG được kích hoạt!
    assert s_lying.bridge_states == (False, False)

    # 2. Đứng thẳng lên heavy switch:
    # Từ s_lying tại (1, 2)-(1, 3) HORIZONTAL:
    # Lăn LEFT -> STANDING tại (1, 1).
    s_stand1 = step(engine, s_lying, Action.LEFT)
    assert s_stand1 is not None
    assert s_stand1.orientation == Orientation.STANDING
    assert s_stand1.block_position == (1, 1)

    # Từ (1, 1) STANDING, nếu lăn RIGHT -> HORIZONTAL (1, 2)-(1, 3).
    # Để đứng lên (1, 2): cần đứng từ (3, 2) lăn UP 2 lần, hoặc từ (1, 4) lăn LEFT:
    # Thử từ (1, 4) STANDING:
    # Lăn LEFT -> HORIZONTAL (1, 2)-(1, 3)
    # Lăn LEFT tiếp -> STANDING tại (1, 1).
    # Để STANDING trên (1, 2):
    # (1, 0) STANDING -> RIGHT -> HORIZONTAL (1, 1)-(1, 2) -> RIGHT -> STANDING (1, 3)
    # (3, 2) STANDING -> UP -> VERTICAL (1, 2)-(2, 2) -> UP -> STANDING (0, 2).
    # (-1, 2) STANDING -> DOWN -> VERTICAL (0, 2)-(1, 2) -> DOWN -> STANDING (2, 2).
    # (1, 3) HORIZONTAL (chiếm (1, 3)-(1, 4)) -> LEFT -> STANDING (1, 2)!
    s_h_right = State(
        block_position=(1, 3), orientation=Orientation.HORIZONTAL, bridge_states=(False, False)
    )
    s_stand_on_x = step(engine, s_h_right, Action.LEFT)
    assert s_stand_on_x is not None
    assert s_stand_on_x.orientation == Orientation.STANDING
    assert s_stand_on_x.block_position == (1, 2)  # Đứng thẳng trên 'x'!
    # Đã kích hoạt -> Cầu mở!
    assert s_stand_on_x.bridge_states == (True, True)


def test_cube_cannot_activate_heavy_switch():
    """Khối lập phương 1x1 trong chế độ split không thể kích hoạt Heavy switch."""
    grid = [
        "#####",
        "#x#G#",
        "##B##",
        "#S###",
    ]
    board = parse_board(
        {
            "name": "cube_heavy",
            "grid": grid,
            "bridges": [{"id": "B1", "cell": [2, 2], "initial": "closed"}],
            "switches": [
                {
                    "cell": [1, 1],
                    "type": "heavy",
                    "targets": [{"bridge": "B1", "mode": "permanent_open"}],
                }
            ],
        }
    )
    engine = Engine(board)
    s_split = make_split_state(bridge_states=(False,), cells=((0, 1), (3, 3)))
    # active_cube 1 tại (0, 1) lăn DOWN -> đến (1, 1) là 'x'
    s_next = step(engine, s_split, Action.DOWN)
    assert s_next is not None
    assert s_next.cube1_position == (1, 1)
    # Cầu vẫn đóng vì cube 1x1 không kích hoạt heavy switch!
    assert s_next.bridge_states == (False,)


def test_bridge_modes():
    """Kiểm tra các chế độ cầu: toggle, permanent_open, permanent_closed."""
    grid = [
        "######",
        "#So###",
        "##BBB#",
        "#####G",
    ]
    board = parse_board(
        {
            "name": "bridge_modes",
            "grid": grid,
            "bridges": [
                {"id": "B1", "cell": [2, 2], "initial": "closed"},
                {"id": "B2", "cell": [2, 3], "initial": "closed"},
                {"id": "B3", "cell": [2, 4], "initial": "open"},
            ],
            "switches": [
                {
                    "cell": [1, 2],
                    "type": "soft",
                    "targets": [
                        {"bridge": "B1", "mode": "toggle"},
                        {"bridge": "B2", "mode": "permanent_open"},
                        {"bridge": "B3", "mode": "permanent_closed"},
                    ],
                }
            ],
        }
    )
    engine = Engine(board)
    s0 = engine.get_initial_state()
    assert s0.bridge_states == (False, False, True)

    # Đưa khối giẫm lên switch tại (1, 2)
    # Lăn DOWN -> VERTICAL tại (1, 2)-(2, 2), nhưng ô (2, 2) là cầu closed!
    # Thử từ (1, 1) STANDING lăn RIGHT -> HORIZONTAL tại (1, 2)-(1, 3):
    s_from = State(
        block_position=(1, 1), orientation=Orientation.STANDING, bridge_states=s0.bridge_states
    )
    s_triggered = step(engine, s_from, Action.RIGHT)
    assert s_triggered is not None
    # B1 toggle: False -> True
    # B2 permanent_open: False -> True
    # B3 permanent_closed: True -> False
    assert s_triggered.bridge_states == (True, True, False)


# --- 3. Split Mode & Merge ---


def test_split_switch_triggers_split_mode():
    """Đứng lên ô 'P' sẽ phân tách khối và chuyển sang split_mode."""
    grid = [
        "######",
        "#S#P##",
        "######",
        "#####G",
    ]
    board = parse_board(
        {
            "name": "split_test",
            "grid": grid,
            "switches": [
                {
                    "cell": [1, 3],
                    "type": "split",
                    "targets": [],
                    "split_cells": [[0, 1], [3, 4]],
                }
            ],
        }
    )
    engine = Engine(board)
    # Đứng tại (1, 2) HORIZONTAL (1, 2)-(1, 3) lăn RIGHT không được vì sẽ đứng tại (1, 4).
    # Đặt block HORIZONTAL tại (1, 4)-(1, 5), lăn LEFT -> STANDING tại (1, 3) (ô P)
    s_h = State(block_position=(1, 4), orientation=Orientation.HORIZONTAL)
    s_split = step(engine, s_h, Action.LEFT)
    assert s_split is not None
    assert s_split.split_mode is True
    assert s_split.cube1_position == (0, 1)
    assert s_split.cube2_position == (3, 4)
    assert s_split.active_cube == 1
    assert s_split.block_position == (0, 1)


def test_switch_cube_action():
    """Hành động SWITCH_CUBE đổi quyền điều khiển giữa cube 1 và cube 2."""
    s = make_split_state(bridge_states=(), cells=((1, 1), (3, 3)))
    assert s.active_cube == 1
    assert s.block_position == (1, 1)

    s2 = switch_active_cube(s)
    assert s2.active_cube == 2
    assert s2.block_position == (3, 3)

    s3 = switch_active_cube(s2)
    assert s3.active_cube == 1
    assert s3.block_position == (1, 1)


def test_cube_movement_and_collision():
    """Khối lập phương di chuyển từng ô một và không thể đi vào vị trí khối kia."""
    grid = [
        "#####",
        "#S###",
        "#####",
        "####G",
    ]
    board = parse_board({"name": "cube_move", "grid": grid})
    engine = Engine(board)
    # Đặt cube 2 ở xa (3, 3) để khi cube 1 đi sang (1, 2) không bị tự động merge
    s = make_split_state(bridge_states=(), cells=((1, 1), (3, 3)))
    # active_cube là 1 tại (1, 1). Lăn RIGHT -> tới (1, 2)
    s_right = step(engine, s, Action.RIGHT)
    assert s_right is not None
    assert s_right.split_mode is True
    assert s_right.cube1_position == (1, 2)

    # Thử va chạm: đặt cube 2 tại (1, 2)
    s_block = make_split_state(bridge_states=(), cells=((1, 1), (1, 2)))
    # Từ (1, 1), cube 1 muốn lăn RIGHT vào (1, 2) (vị trí cube 2) -> Bị chặn (None)!
    assert step(engine, s_block, Action.RIGHT) is None


def test_cubes_auto_merge_horizontally_and_vertically():
    """Khi 2 khối lập phương đứng kề nhau, chúng tự động hợp nhất."""
    # 1. Kề ngang -> HORIZONTAL
    s_horiz = State(
        block_position=(2, 2),
        orientation=Orientation.STANDING,
        split_mode=True,
        cube1_position=(2, 2),
        cube2_position=(2, 3),
        active_cube=1,
    )
    merged_h = try_merge(s_horiz)
    assert merged_h.split_mode is False
    assert merged_h.orientation == Orientation.HORIZONTAL
    assert merged_h.block_position == (2, 2)
    assert merged_h.cube1_position is None

    # 2. Kề dọc -> VERTICAL
    s_vert = State(
        block_position=(3, 2),
        orientation=Orientation.STANDING,
        split_mode=True,
        cube1_position=(3, 2),
        cube2_position=(2, 2),
        active_cube=1,
    )
    merged_v = try_merge(s_vert)
    assert merged_v.split_mode is False
    assert merged_v.orientation == Orientation.VERTICAL
    assert merged_v.block_position == (2, 2)  # anchor là min
    assert merged_v.cube1_position is None


def test_cannot_win_while_split():
    """Khối lập phương đứng trên ô đích G không thể thắng nếu chưa hợp nhất."""
    grid = [
        "#####",
        "#S#G#",
        "#####",
    ]
    board = parse_board({"name": "split_win", "grid": grid})
    engine = Engine(board)
    s = make_split_state(bridge_states=(), cells=((1, 3), (1, 1)))  # cube1 tại G (1, 3)
    assert engine.is_goal(s) is False


# --- 4. Deep Validation of Level Mechanics ---


def test_mechanics_validation_errors():
    """Kiểm tra báo lỗi với cấu hình bridges/switches không hợp lệ."""
    grid = ["SG"]
    # 1. Cầu không có id
    with pytest.raises(ValueError, match="id"):
        build_mechanics(
            parse_board({"grid": grid, "bridges": [{"cell": [0, 1], "initial": "open"}]})
        )

    # 2. Ô cầu khai báo không phải ký tự 'B'
    with pytest.raises(ValueError, match="không phải ô cầu"):
        build_mechanics(
            parse_board(
                {
                    "grid": grid,
                    "bridges": [{"id": "B1", "cell": [0, 0], "initial": "open"}],
                }
            )
        )

    # 3. Target tới cầu không tồn tại
    with pytest.raises(ValueError, match="không tồn tại cầu"):
        build_mechanics(
            parse_board(
                {
                    "grid": ["SGo"],
                    "switches": [
                        {
                            "cell": [0, 2],
                            "type": "soft",
                            "targets": [{"bridge": "NO_SUCH_BRIDGE", "mode": "toggle"}],
                        }
                    ],
                }
            )
        )

    # 4. Split switch thiếu split_cells
    with pytest.raises(ValueError, match="split_cells"):
        build_mechanics(
            parse_board(
                {
                    "grid": ["SGP"],
                    "switches": [{"cell": [0, 2], "type": "split", "targets": []}],
                }
            )
        )


# --- 5. Integration Tests on all stages (level2.json to level10.json) ---


@pytest.mark.parametrize(
    "level_file,expected_min_len",
    [
        ("level2.json", 7),
        ("level3.json", 15),
        ("level4.json", 10),
        ("level5.json", 10),
        ("level6.json", 10),
        ("level7.json", 15),
        ("level8.json", 15),
        ("level9.json", 15),
        ("level10.json", 30),
    ],
)
def test_all_designed_levels_solvable(level_file: str, expected_min_len: int):
    """Xác nhận tất cả các màn chơi thiết kế đều giải được và có đường đi tối ưu hợp lý."""
    path = Path("levels") / level_file
    board = load_board(path)
    engine = Engine(board)
    solution = _bfs_solve(engine)
    assert solution is not None, f"Màn chơi {level_file} không thể giải được!"
    assert len(solution) >= expected_min_len, (
        f"Màn chơi {level_file} có đường đi quá ngắn ({len(solution)} < {expected_min_len})"
    )
