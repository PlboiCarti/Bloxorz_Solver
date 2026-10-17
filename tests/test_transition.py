"""Bộ kiểm thử chuyển đổi trạng thái và mô hình dữ liệu của Bloxorz."""

import json
from collections import deque
from dataclasses import FrozenInstanceError

import pytest

from game.actions import Action, Orientation
from game.board import Board, TileType, load_board, parse_board
from game.engine import Engine
from game.state import Cell, State, occupied_cells

# --- State ---


def test_state_equality_and_hashing():
    """Kiểm tra hai State giống nhau so sánh bằng nhau và có cùng hash, khác nhau thì khác."""
    s1 = State(block_position=(3, 4), orientation=Orientation.STANDING)
    s2 = State(block_position=(3, 4), orientation=Orientation.STANDING)
    s3 = State(block_position=(3, 5), orientation=Orientation.STANDING)
    s4 = State(block_position=(3, 4), orientation=Orientation.HORIZONTAL)

    assert s1 == s2
    assert hash(s1) == hash(s2)
    assert s1 != s3
    assert s1 != s4
    assert hash(s1) != hash(s3)


def test_state_usable_in_set_and_dict():
    """Kiểm tra State có thể làm phần tử trong set và khóa trong dict."""
    s1 = State(block_position=(1, 2), orientation=Orientation.VERTICAL)
    s2 = State(block_position=(1, 2), orientation=Orientation.VERTICAL)
    s3 = State(block_position=(2, 2), orientation=Orientation.VERTICAL)

    state_set = {s1, s3}
    assert s2 in state_set
    assert len(state_set) == 2

    state_dict = {s1: "start", s3: "next"}
    assert state_dict[s2] == "start"
    assert len(state_dict) == 2


def test_state_immutability():
    """Kiểm tra State là bất biến, gán thuộc tính sẽ báo lỗi FrozenInstanceError."""
    s = State(block_position=(0, 0), orientation=Orientation.STANDING)
    with pytest.raises(FrozenInstanceError):
        # pyright: ignore[reportAttributeAccessIssue]
        s.block_position = (1, 1)  # type: ignore[misc]


def test_occupied_cells_all_orientations():
    """Kiểm tra occupied_cells tính toán đúng tọa độ các ô cho cả 3 hướng."""
    s_standing = State(block_position=(2, 3), orientation=Orientation.STANDING)
    assert s_standing.occupied_cells() == ((2, 3),)
    assert occupied_cells(s_standing) == ((2, 3),)

    s_horizontal = State(block_position=(2, 3), orientation=Orientation.HORIZONTAL)
    assert s_horizontal.occupied_cells() == ((2, 3), (2, 4))
    assert occupied_cells(s_horizontal) == ((2, 3), (2, 4))

    s_vertical = State(block_position=(2, 3), orientation=Orientation.VERTICAL)
    assert s_vertical.occupied_cells() == ((2, 3), (3, 3))
    assert occupied_cells(s_vertical) == ((2, 3), (3, 3))


def test_state_json_roundtrip():
    """Kiểm tra to_dict() và from_dict() bảo toàn dữ liệu và tương thích json."""
    s = State(
        block_position=(5, 6),
        orientation=Orientation.HORIZONTAL,
        bridge_states=(True, False),
        split_mode=False,
        cube1_position=None,
        cube2_position=None,
        active_cube=None,
    )
    d = s.to_dict()
    # Kiểm tra JSON dump thành công
    json_str = json.dumps(d)
    loaded_dict = json.loads(json_str)

    # Khôi phục từ dict
    restored = State.from_dict(loaded_dict)
    assert restored == s
    assert hash(restored) == hash(s)


def test_state_split_fields_roundtrip():
    """Kiểm tra to_dict và from_dict với các trường liên quan đến split_mode."""
    s_split = State(
        block_position=(0, 0),
        orientation=Orientation.STANDING,
        bridge_states=(),
        split_mode=True,
        cube1_position=(1, 2),
        cube2_position=(4, 5),
        active_cube=1,
    )
    d = s_split.to_dict()
    assert json.dumps(d)
    restored = State.from_dict(d)
    assert restored == s_split


# --- Board and Level Loader ---


def test_parse_valid_grid():
    """Kiểm tra parse_board nạp đúng kích thước, ô xuất phát, ô đích và các loại ô."""
    data = {
        "name": "sample",
        "grid": [
            "S#.",
            "FBo",
            "xPG",
        ],
        "bridges": [{"id": "B1"}],
        "switches": [{"type": "soft"}],
    }
    board = parse_board(data)
    assert isinstance(board, Board)
    assert board.name == "sample"
    assert board.rows == 3
    assert board.cols == 3
    assert board.start == (0, 0)
    assert board.goal == (2, 2)

    assert board.tile_at((0, 0)) == TileType.FLOOR
    assert board.tile_at((0, 1)) == TileType.FLOOR
    assert board.tile_at((0, 2)) == TileType.VOID
    assert board.tile_at((1, 0)) == TileType.FRAGILE
    assert board.tile_at((1, 1)) == TileType.BRIDGE
    assert board.tile_at((1, 2)) == TileType.SOFT_SWITCH
    assert board.tile_at((2, 0)) == TileType.HEAVY_SWITCH
    assert board.tile_at((2, 1)) == TileType.SPLIT_SWITCH
    assert board.tile_at((2, 2)) == TileType.GOAL

    assert len(board.bridges) == 1
    assert len(board.switches) == 1


def test_parse_board_rejections():
    """Kiểm tra parse_board từ chối các bản đồ không hợp lệ."""
    # Thiếu hoặc rỗng grid
    with pytest.raises(ValueError, match="không được rỗng|thiếu"):
        parse_board({"grid": []})

    with pytest.raises(ValueError, match="thiếu"):
        parse_board({})

    # Hàng không đều (ragged)
    with pytest.raises(ValueError, match="hình chữ nhật"):
        parse_board({"grid": ["S#", "G"]})

    # Hàng có độ dài 0
    with pytest.raises(ValueError, match="độ dài bằng 0"):
        parse_board({"grid": [""]})

    # Ký tự lạ
    with pytest.raises(ValueError, match="Ký tự không hợp lệ"):
        parse_board({"grid": ["S#", "G?"]})

    # Không có hoặc nhiều hơn 1 ô S
    with pytest.raises(ValueError, match="chính xác một ô xuất phát"):
        parse_board({"grid": ["##", "G#"]})
    with pytest.raises(ValueError, match="chính xác một ô xuất phát"):
        parse_board({"grid": ["SS", "G#"]})

    # Không có hoặc nhiều hơn 1 ô G
    with pytest.raises(ValueError, match="chính xác một ô đích"):
        parse_board({"grid": ["S#", "##"]})
    with pytest.raises(ValueError, match="chính xác một ô đích"):
        parse_board({"grid": ["SG", "#G"]})

    # bridges hoặc switches không phải là list
    with pytest.raises(TypeError, match="bridges"):
        parse_board({"grid": ["SG"], "bridges": "not-a-list"})
    with pytest.raises(TypeError, match="switches"):
        parse_board({"grid": ["SG"], "switches": "not-a-list"})


def test_load_board_level1():
    """Kiểm tra load_board nạp thành công file levels/level1.json."""
    board = load_board("levels/level1.json")
    assert board.name == "level1"
    assert board.rows == 5
    assert board.cols == 10
    assert board.start == (1, 3)
    assert board.goal == (4, 6)

    # Kiểm tra một số ô đại diện
    assert board.tile_at((1, 3)) == TileType.FLOOR
    assert board.tile_at((4, 6)) == TileType.GOAL
    assert board.tile_at((0, 0)) == TileType.VOID
    assert board.tile_at((2, 0)) == TileType.FLOOR


def test_board_in_bounds_and_edges():
    """Kiểm tra hàm in_bounds tại 4 góc, các cạnh và ngoài biên."""
    board = load_board("levels/level1.json")

    # Các ô hợp lệ ở 4 góc
    assert board.in_bounds((0, 0)) is True
    assert board.in_bounds((0, board.cols - 1)) is True
    assert board.in_bounds((board.rows - 1, 0)) is True
    assert board.in_bounds((board.rows - 1, board.cols - 1)) is True

    # Ngoài biên ở cả 4 phía
    assert board.in_bounds((-1, 0)) is False
    assert board.in_bounds((0, -1)) is False
    assert board.in_bounds((board.rows, 0)) is False
    assert board.in_bounds((0, board.cols)) is False

    # Truy vấn tile_at ngoài biên ném IndexError
    with pytest.raises(IndexError):
        board.tile_at((-1, 0))
    with pytest.raises(IndexError):
        board.tile_at((board.rows, board.cols))


# --- Engine Core ---


def make_open_board(
    rows: int = 12,
    cols: int = 12,
    start: Cell = (0, 0),
    goal: Cell | None = None,
) -> Board:
    """Tạo bảng mở gồm toàn ô sàn, có 1 ô S và 1 ô G."""
    if goal is None:
        goal = (rows - 1, cols - 1)
    grid_rows: list[str] = []
    for r in range(rows):
        chars: list[str] = []
        for c in range(cols):
            if (r, c) == start:
                chars.append("S")
            elif (r, c) == goal:
                chars.append("G")
            else:
                chars.append("#")
        grid_rows.append("".join(chars))
    return parse_board({"name": "open_board", "grid": grid_rows})


@pytest.mark.parametrize(
    ("from_ori", "action", "expected_ori", "expected_pos"),
    [
        (Orientation.STANDING, Action.UP, Orientation.VERTICAL, (3, 5)),
        (Orientation.STANDING, Action.DOWN, Orientation.VERTICAL, (6, 5)),
        (Orientation.STANDING, Action.LEFT, Orientation.HORIZONTAL, (5, 3)),
        (Orientation.STANDING, Action.RIGHT, Orientation.HORIZONTAL, (5, 6)),
        (Orientation.HORIZONTAL, Action.LEFT, Orientation.STANDING, (5, 4)),
        (Orientation.HORIZONTAL, Action.RIGHT, Orientation.STANDING, (5, 7)),
        (Orientation.HORIZONTAL, Action.UP, Orientation.HORIZONTAL, (4, 5)),
        (Orientation.HORIZONTAL, Action.DOWN, Orientation.HORIZONTAL, (6, 5)),
        (Orientation.VERTICAL, Action.UP, Orientation.STANDING, (4, 5)),
        (Orientation.VERTICAL, Action.DOWN, Orientation.STANDING, (7, 5)),
        (Orientation.VERTICAL, Action.LEFT, Orientation.VERTICAL, (5, 4)),
        (Orientation.VERTICAL, Action.RIGHT, Orientation.VERTICAL, (5, 6)),
    ],
)
def test_engine_12_transitions_table(
    from_ori: Orientation,
    action: Action,
    expected_ori: Orientation,
    expected_pos: tuple[int, int],
):
    """Kiểm tra chính xác 12 bước chuyển trạng thái chuẩn trên bảng mở tại anchor (5, 5)."""
    board = make_open_board(12, 12)
    engine = Engine(board)
    current_state = State(block_position=(5, 5), orientation=from_ori)

    next_state = engine.transition(current_state, action)
    assert next_state is not None
    assert next_state.orientation == expected_ori
    assert next_state.block_position == expected_pos


def test_engine_off_board_moves_return_none():
    """Kiểm tra lăn ra ngoài biên ở cả 4 cạnh và 3 hướng trả về None."""
    board = make_open_board(10, 10)
    engine = Engine(board)

    # Cạnh trên (UP)
    assert engine.transition(State((0, 5), Orientation.STANDING), Action.UP) is None
    assert engine.transition(State((0, 5), Orientation.HORIZONTAL), Action.UP) is None
    assert engine.transition(State((0, 5), Orientation.VERTICAL), Action.UP) is None

    # Cạnh dưới (DOWN)
    assert engine.transition(State((9, 5), Orientation.STANDING), Action.DOWN) is None
    assert engine.transition(State((9, 5), Orientation.HORIZONTAL), Action.DOWN) is None
    assert engine.transition(State((8, 5), Orientation.VERTICAL), Action.DOWN) is None

    # Cạnh trái (LEFT)
    assert engine.transition(State((5, 0), Orientation.STANDING), Action.LEFT) is None
    assert engine.transition(State((5, 0), Orientation.HORIZONTAL), Action.LEFT) is None
    assert engine.transition(State((5, 0), Orientation.VERTICAL), Action.LEFT) is None

    # Cạnh phải (RIGHT)
    assert engine.transition(State((5, 9), Orientation.STANDING), Action.RIGHT) is None
    assert engine.transition(State((5, 8), Orientation.HORIZONTAL), Action.RIGHT) is None
    assert engine.transition(State((5, 9), Orientation.VERTICAL), Action.RIGHT) is None


def test_engine_move_onto_void_returns_none():
    """Kiểm tra rơi vào ô VOID (cả khi chỉ 1 trong 2 ô là VOID) trả về None."""
    # Bảng có ô (1, 3) là VOID
    grid = [
        "S#####",
        "###.##",
        "#####G",
    ]
    board = parse_board({"name": "void_test", "grid": grid})
    engine = Engine(board)

    # Đứng tại (1, 1), lăn RIGHT -> HORIZONTAL anchor (1, 2) chiếm (1, 2) [FLOOR] và (1, 3) [VOID]
    s_stand = State(block_position=(1, 1), orientation=Orientation.STANDING)
    assert engine.transition(s_stand, Action.RIGHT) is None

    # Đứng tại (0, 3), lăn DOWN -> VERTICAL anchor (1, 3) chiếm (1, 3) [VOID] và (2, 3) [FLOOR]
    s_stand_v = State(block_position=(0, 3), orientation=Orientation.STANDING)
    assert engine.transition(s_stand_v, Action.DOWN) is None

    # Đứng tại (0, 0), lăn RIGHT -> HORIZONTAL anchor (0, 1) chiếm (0, 1) [FLOOR] và (0, 2) [FLOOR], hợp lệ
    s_stand_ok = State(block_position=(0, 0), orientation=Orientation.STANDING)
    assert engine.transition(s_stand_ok, Action.RIGHT) is not None


def test_engine_legal_actions_order_and_filtering():
    """Kiểm tra legal_actions lọc bỏ bước đi sai và giữ thứ tự UP, DOWN, LEFT, RIGHT."""
    board = make_open_board(10, 10)
    engine = Engine(board)

    # Tại góc trên trái (0, 0), UP và LEFT ra ngoài biên -> chỉ còn DOWN, RIGHT
    s_corner = State(block_position=(0, 0), orientation=Orientation.STANDING)
    actions = engine.legal_actions(s_corner)
    assert actions == [Action.DOWN, Action.RIGHT]

    # Tại giữa bảng (5, 5), cả 4 hướng đều hợp lệ, SWITCH_CUBE bị loại
    s_center = State(block_position=(5, 5), orientation=Orientation.STANDING)
    assert engine.legal_actions(s_center) == [
        Action.UP,
        Action.DOWN,
        Action.LEFT,
        Action.RIGHT,
    ]


def test_engine_is_goal():
    """Kiểm tra điều kiện thắng: STANDING trên G là True, nằm ngang/dọc qua G là False."""
    board = make_open_board(10, 10, goal=(4, 6))
    engine = Engine(board)

    # STANDING trên G
    s_win = State(block_position=(4, 6), orientation=Orientation.STANDING)
    assert engine.is_goal(s_win) is True

    # HORIZONTAL vắt ngang qua G: anchor (4, 5) chiếm (4, 5) và (4, 6)
    s_lying_h = State(block_position=(4, 5), orientation=Orientation.HORIZONTAL)
    assert engine.is_goal(s_lying_h) is False

    # VERTICAL vắt dọc qua G: anchor (3, 6) chiếm (3, 6) và (4, 6)
    s_lying_v = State(block_position=(3, 6), orientation=Orientation.VERTICAL)
    assert engine.is_goal(s_lying_v) is False

    # STANDING ở ô khác G
    s_other = State(block_position=(0, 0), orientation=Orientation.STANDING)
    assert engine.is_goal(s_other) is False


def test_engine_lying_block_supported_on_goal():
    """Kiểm tra khối nằm trên ô đích vẫn được nâng đỡ bình thường (không rơi, không thắng)."""
    board = make_open_board(10, 10, goal=(5, 6))
    engine = Engine(board)

    # Từ STANDING (5, 5), lăn RIGHT -> HORIZONTAL (5, 6) chiếm (5, 6) [G] và (5, 7) [FLOOR]
    s_start = State(block_position=(5, 5), orientation=Orientation.STANDING)
    s_next = engine.transition(s_start, Action.RIGHT)
    assert s_next is not None
    assert s_next.block_position == (5, 6)
    assert s_next.orientation == Orientation.HORIZONTAL
    assert engine.is_goal(s_next) is False


def test_engine_get_initial_state():
    """Kiểm tra get_initial_state() trả về trạng thái STANDING tại ô xuất phát."""
    board = make_open_board(8, 8, start=(2, 3))
    engine = Engine(board)

    s0 = engine.get_initial_state()
    assert s0.block_position == (2, 3)
    assert s0.orientation == Orientation.STANDING
    assert s0.split_mode is False
    assert s0.bridge_states == ()


def test_engine_legal_actions_on_goal_state():
    """Kiểm tra legal_actions vẫn sinh bước đi khi khối đang đứng ở ô đích (không terminal)."""
    board = make_open_board(10, 10, goal=(5, 5))
    engine = Engine(board)
    s_goal = State(block_position=(5, 5), orientation=Orientation.STANDING)

    actions = engine.legal_actions(s_goal)
    assert Action.UP in actions
    assert Action.DOWN in actions
    assert Action.LEFT in actions
    assert Action.RIGHT in actions


def test_engine_switch_cube_illegal_in_core():
    """Kiểm tra transition(state, SWITCH_CUBE) luôn trả về None trong non-split mode."""
    board = make_open_board(10, 10)
    engine = Engine(board)
    s = State(block_position=(5, 5), orientation=Orientation.STANDING, split_mode=False)

    assert engine.transition(s, Action.SWITCH_CUBE) is None


def test_engine_transition_immutability_and_determinism():
    """Kiểm tra transition không thay đổi state ban đầu và có tính đơn định (deterministic)."""
    board = make_open_board(10, 10)
    engine = Engine(board)
    s = State(block_position=(5, 5), orientation=Orientation.STANDING)

    s1 = engine.transition(s, Action.RIGHT)
    s2 = engine.transition(s, Action.RIGHT)

    assert s.block_position == (5, 5)
    assert s.orientation == Orientation.STANDING
    assert s1 == s2
    assert s1 is not s


def test_engine_roundtrip_roll():
    """Kiểm tra lăn đi và lăn ngược lại (e.g. RIGHT rồi LEFT) quay về state ban đầu."""
    board = make_open_board(10, 10)
    engine = Engine(board)
    s = State(block_position=(5, 5), orientation=Orientation.STANDING)

    s_right = engine.transition(s, Action.RIGHT)
    assert s_right is not None
    s_back = engine.transition(s_right, Action.LEFT)
    assert s_back == s


def test_engine_step_cost():
    """Kiểm tra step_cost trả về 1.0 trong TV1 core."""
    board = make_open_board(10, 10)
    engine = Engine(board)
    s1 = State(block_position=(5, 5), orientation=Orientation.STANDING)
    s2 = engine.transition(s1, Action.RIGHT)
    assert s2 is not None
    assert engine.step_cost(s1, Action.RIGHT, s2) == 1.0


# --- Integration smoke test ---


def test_integration_level1_bfs_reaches_goal():
    """Smoke test: BFS thuần viết trong test, chỉ dùng Engine API để giải levels/level1.json."""
    board = load_board("levels/level1.json")
    engine = Engine(board)
    start = engine.get_initial_state()

    # BFS tìm đường đi ngắn nhất từ trạng thái xuất phát đến trạng thái đích
    parent: dict[State, tuple[State, Action] | None] = {start: None}
    queue: deque[State] = deque([start])
    goal_state: State | None = None

    while queue and goal_state is None:
        current = queue.popleft()
        if engine.is_goal(current):
            goal_state = current
            break
        for action in engine.legal_actions(current):
            next_state = engine.transition(current, action)
            assert next_state is not None
            if next_state not in parent:
                parent[next_state] = (current, action)
                queue.append(next_state)

    assert goal_state is not None

    # Truy vết đường đi ngược từ đích về xuất phát
    path: list[Action] = []
    node = goal_state
    while node != start:
        entry = parent[node]
        assert entry is not None
        node, action = entry
        path.append(action)
    path.reverse()

    # Phát lại đường đi chỉ qua Engine API để xác nhận trạng thái đích
    replay = start
    for action in path:
        next_state = engine.transition(replay, action)
        assert next_state is not None
        replay = next_state
    assert engine.is_goal(replay)
