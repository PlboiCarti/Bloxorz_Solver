"""Kiểu kết quả thống nhất cho mọi thuật toán tìm kiếm."""

from dataclasses import dataclass

from game.actions import Action


@dataclass(slots=True)
class SearchResult:
    """Kết quả tìm kiếm cùng các chỉ số hiệu năng.

    Attributes:
        solved: Có tìm thấy trạng thái đích hay không.
        path: Danh sách hành động từ trạng thái đầu đến trạng thái đích.
        total_cost: Tổng chi phí các bước trong path theo Engine.step_cost.
        search_time: Thời gian chạy solve, tính bằng giây.
        memory_usage: Bộ nhớ đỉnh được tracemalloc ghi nhận, tính bằng MB thập phân.
        expanded_nodes: Số trạng thái được thuật toán mở rộng.
        solution_length: Số hành động trong path; luôn bằng len(path).
    """

    solved: bool
    path: list[Action]
    total_cost: float
    search_time: float
    memory_usage: float
    expanded_nodes: int
    solution_length: int
