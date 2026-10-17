"""Mô hình dữ liệu bảng chơi (Board) và bộ nạp cấp độ (Level Loader)."""

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from game.state import Cell


class TileType(Enum):
    """Các loại ô trên bản đồ Bloxorz."""

    FLOOR = "#"          # Ô sàn bình thường
    VOID = "."           # Ô rỗng (vực thẳm)
    GOAL = "G"           # Ô đích
    FRAGILE = "F"        # Ô cam / giòn (TV2)
    BRIDGE = "B"         # Ô cầu (TV2)
    SOFT_SWITCH = "o"    # Công tắc nhẹ (TV2)
    HEAVY_SWITCH = "x"   # Công tắc nặng (TV2)
    SPLIT_SWITCH = "P"   # Công tắc phân tách (TV2)


# Bảng ánh xạ ký tự trong file JSON sang TileType
_CHAR_TO_TILE_TYPE: dict[str, TileType] = {
    "#": TileType.FLOOR,
    ".": TileType.VOID,
    "S": TileType.FLOOR,  # Ô xuất phát là sàn bình thường
    "G": TileType.GOAL,
    "F": TileType.FRAGILE,
    "B": TileType.BRIDGE,
    "o": TileType.SOFT_SWITCH,
    "x": TileType.HEAVY_SWITCH,
    "P": TileType.SPLIT_SWITCH,
}


@dataclass(frozen=True, slots=True)
class Board:
    """Biểu diễn dữ liệu bản đồ bất biến.

    Attributes:
        rows: Số lượng hàng của bảng.
        cols: Số lượng cột của bảng.
        start: Tọa độ ô xuất phát (S).
        goal: Tọa độ ô đích (G).
        grid: Lưới các ô biểu diễn bằng tuple 2 chiều của TileType.
        bridges: Danh sách cấu hình cầu (chưa thông dịch trong core TV1).
        switches: Danh sách cấu hình công tắc (chưa thông dịch trong core TV1).
        name: Tên của màn chơi (tùy chọn).
    """

    rows: int
    cols: int
    start: Cell
    goal: Cell
    grid: tuple[tuple[TileType, ...], ...]
    bridges: tuple[dict[str, Any], ...] = ()
    switches: tuple[dict[str, Any], ...] = ()
    name: str = ""

    def in_bounds(self, cell: Cell) -> bool:
        """Kiểm tra một tọa độ (r, c) có nằm trong kích thước bảng hay không."""
        r, c = cell
        return 0 <= r < self.rows and 0 <= c < self.cols

    def tile_at(self, cell: Cell) -> TileType:
        """Trả về loại ô tại tọa độ chỉ định. Ném lỗi IndexError nếu ngoài biên."""
        if not self.in_bounds(cell):
            raise IndexError(f"Tọa độ {cell} nằm ngoài giới hạn bảng ({self.rows}x{self.cols}).")
        return self.grid[cell[0]][cell[1]]


def parse_board(data: dict[str, Any]) -> Board:
    """Phân tích cú pháp và kiểm thực (validate) dữ liệu bản đồ từ từ điển dict.

    Raises:
        ValueError: Nếu bản đồ rỗng, các hàng không đều, chứa ký tự lạ,
                    hoặc số lượng ô S/G không chính xác bằng 1.
    """
    if "grid" not in data:
        raise ValueError("Dữ liệu màn chơi thiếu trường 'grid'.")

    grid_raw = data["grid"]
    if not isinstance(grid_raw, list) or len(grid_raw) == 0:
        raise ValueError("Lưới bản đồ ('grid') không được rỗng.")

    rows = len(grid_raw)
    cols = len(grid_raw[0])
    if cols == 0:
        raise ValueError("Các hàng trong bản đồ không được có độ dài bằng 0.")

    start_cell: Cell | None = None
    goal_cell: Cell | None = None
    s_count = 0
    g_count = 0

    parsed_rows: list[tuple[TileType, ...]] = []

    for r, row_str in enumerate(grid_raw):
        if not isinstance(row_str, str):
            raise TypeError(f"Hàng {r} trong 'grid' phải là kiểu chuỗi (str).")
        if len(row_str) != cols:
            raise ValueError(
                f"Bản đồ không phải hình chữ nhật: hàng {r} có độ dài {len(row_str)}, "
                f"khác với độ dài hàng đầu tiên là {cols}."
            )

        row_tiles: list[TileType] = []
        for c, ch in enumerate(row_str):
            if ch not in _CHAR_TO_TILE_TYPE:
                raise ValueError(f"Ký tự không hợp lệ '{ch}' tại tọa độ ({r}, {c}).")

            if ch == "S":
                s_count += 1
                start_cell = (r, c)
            elif ch == "G":
                g_count += 1
                goal_cell = (r, c)

            row_tiles.append(_CHAR_TO_TILE_TYPE[ch])

        parsed_rows.append(tuple(row_tiles))

    if s_count != 1 or start_cell is None:
        raise ValueError(f"Bản đồ phải chứa chính xác một ô xuất phát 'S' (tìm thấy {s_count}).")

    if g_count != 1 or goal_cell is None:
        raise ValueError(f"Bản đồ phải chứa chính xác một ô đích 'G' (tìm thấy {g_count}).")

    raw_bridges = data.get("bridges", [])
    if not isinstance(raw_bridges, list):
        raise TypeError("Trường 'bridges' phải là một danh sách (list).")

    raw_switches = data.get("switches", [])
    if not isinstance(raw_switches, list):
        raise TypeError("Trường 'switches' phải là một danh sách (list).")

    name = str(data.get("name", ""))

    return Board(
        rows=rows,
        cols=cols,
        start=start_cell,
        goal=goal_cell,
        grid=tuple(parsed_rows),
        bridges=tuple(raw_bridges),
        switches=tuple(raw_switches),
        name=name,
    )


def load_board(path: str | Path) -> Board:
    """Nạp và kiểm thực bản đồ từ file JSON.

    Raises:
        FileNotFoundError: Nếu file không tồn tại.
        ValueError, TypeError: Nếu định dạng JSON hoặc dữ liệu bản đồ không hợp lệ.
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"Không tìm thấy file màn chơi: {file_path}")

    with file_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise TypeError("Nội dung file JSON của màn chơi phải là một object/dict.")

    return parse_board(data)
