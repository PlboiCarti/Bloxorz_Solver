"""Bộ kiểm thử chuyển đổi trạng thái và mô hình dữ liệu của Bloxorz."""

import json
from dataclasses import FrozenInstanceError

import pytest

from game.actions import Orientation
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
