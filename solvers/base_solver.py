"""Lớp nền cung cấp các thao tác dùng chung cho các solver."""

from __future__ import annotations

from abc import ABC, abstractmethod
from time import perf_counter
import tracemalloc

from game.actions import Action
from game.engine import Engine
from game.state import State
from solvers.search_result import SearchResult

# Với trạng thái đầu, không có trạng thái cha; các trạng thái khác lưu (cha, hành động).
ParentMap = dict[State, tuple[State, Action] | None]


class BaseSolver(ABC):
    """Template chung cho BFS/DFS/UCS/A*.

    Lớp cơ sở quản lý thời gian, đo bộ nhớ, xử lý trường hợp trạng thái đầu đã là
    đích, khôi phục path và tính tổng chi phí. Thuật toán con chỉ cần triển khai
    `_search`, chịu trách nhiệm quản lý frontier, visited/parent và số node mở rộng.

    Args:
        engine: Engine thực thi luật chơi và cung cấp chi phí bước đi.
    """

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def solve(self, initial_state: State) -> SearchResult:
        """Tìm lời giải từ `initial_state` và trả về kết quả theo schema chung."""
        was_tracing = tracemalloc.is_tracing()
        if not was_tracing:
            tracemalloc.start()

        started_at = perf_counter()
        try:
            if self.engine.is_goal(initial_state):
                goal_state: State | None = initial_state
                parent: ParentMap = {initial_state: None}
                expanded_nodes = 0
            else:
                goal_state, parent, expanded_nodes = self._search(initial_state)

            if goal_state is None:
                path: list[Action] = []
                total_cost = 0.0
                solved = False
            else:
                path = self._reconstruct_path(initial_state, goal_state, parent)
                total_cost = self._calculate_path_cost(initial_state, path)
                solved = True

            elapsed = perf_counter() - started_at
            _, peak_bytes = tracemalloc.get_traced_memory()
            memory_mb = peak_bytes / 1_000_000

            return SearchResult(
                solved=solved,
                path=path,
                total_cost=total_cost,
                search_time=elapsed,
                memory_usage=memory_mb,
                expanded_nodes=expanded_nodes,
                solution_length=len(path),
            )
        finally:
            # Không dừng tracemalloc nếu caller đã bật nó trước khi gọi solver.
            if not was_tracing:
                tracemalloc.stop()

    @abstractmethod
    def _search(self, initial_state: State) -> tuple[State | None, ParentMap, int]:
        """Chạy thuật toán cụ thể.

        Returns:
            Tuple gồm trạng thái đích (None nếu không có lời giải), bản đồ cha và
            số trạng thái đã mở rộng. `parent[initial_state]` phải là None; với
            mỗi trạng thái được phát hiện khác, lưu `(parent_state, action)`.
        """
        raise NotImplementedError

    @staticmethod
    def _reconstruct_path(
        initial_state: State,
        goal_state: State,
        parent: ParentMap,
    ) -> list[Action]:
        """Khôi phục danh sách Action theo thứ tự từ trạng thái đầu đến đích."""
        reversed_path: list[Action] = []
        node = goal_state

        while node != initial_state:
            entry = parent.get(node)
            if entry is None:
                raise RuntimeError(
                    "Không thể khôi phục path: thiếu trạng thái cha cho một node "
                    "trên đường từ goal về initial_state."
                )
            previous_state, action = entry
            reversed_path.append(action)
            node = previous_state

        reversed_path.reverse()
        return reversed_path

    def _calculate_path_cost(self, initial_state: State, path: list[Action]) -> float:
        """Tính tổng cost bằng cách phát lại path qua API Engine chính thức."""
        total_cost = 0.0
        current_state = initial_state
        for action in path:
            next_state = self.engine.transition(current_state, action)
            if next_state is None:
                raise RuntimeError(
                    "Path do thuật toán tìm kiếm trả về chứa một hành động không "
                    "hợp lệ theo Engine.transition()."
                )
            total_cost += self.engine.step_cost(current_state, action, next_state)
            current_state = next_state

        if not self.engine.is_goal(current_state):
            raise RuntimeError(
                "Path do thuật toán tìm kiếm trả về không kết thúc ở trạng thái đích."
            )
        return total_cost
