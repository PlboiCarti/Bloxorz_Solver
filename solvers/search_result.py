"""Kiểu dữ liệu kết quả tìm kiếm thống nhất cho mọi thuật toán (TV3/TV4)."""

from dataclasses import dataclass

from game.actions import Action


@dataclass
class SearchResult:
    """Kết quả trả về thống nhất của mọi Solver (theo `docs/gui_api.md` §4.2).

    Attributes:
        solved: True nếu tìm được lời giải.
        path: Chuỗi hành động dẫn từ trạng thái đầu tới đích.
        total_cost: Tổng chi phí các bước (tổng `step_cost`).
        search_time: Thời gian tìm kiếm (giây).
        memory_usage: Đỉnh bộ nhớ sử dụng (MB).
        expanded_nodes: Số trạng thái đã mở rộng.
        solution_length: Số bước của lời giải (len(path)).
    """

    solved: bool
    path: list[Action]
    total_cost: float
    search_time: float
    memory_usage: float
    expanded_nodes: int
    solution_length: int
