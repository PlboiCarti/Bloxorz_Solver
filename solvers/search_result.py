"""Kiểu kết quả thống nhất cho mọi thuật toán tìm kiếm."""

from dataclasses import dataclass

from game.actions import Action


@dataclass(slots=True)
class SearchResult:
    """Kết quả tìm kiếm và các chỉ số hiệu năng."""

    solved: bool
    path: list[Action]
    total_cost: float
    search_time: float
    memory_usage: float
    expanded_nodes: int
    solution_length: int
