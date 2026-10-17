"""Bộ kiểm thử chuyển đổi trạng thái và mô hình dữ liệu của Bloxorz."""

import json
from dataclasses import FrozenInstanceError

import pytest

from game.actions import Orientation
from game.board import Board, TileType, load_board, parse_board
from game.state import State, occupied_cells

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

