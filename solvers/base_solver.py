"""Tiện ích nền dùng chung cho các thuật toán tìm kiếm."""

from __future__ import annotations

from abc import ABC, abstractmethod
from threading import Event
from time import perf_counter

from game.actions import Action
from game.engine import Engine, TransitionStatus
from game.state import State
from solvers.runtime import cancellation_scope, check_cancelled, track_peak_memory
from solvers.search_result import SearchResult

# Với trạng thái đầu, không có trạng thái cha; các trạng thái khác lưu
# (trạng thái cha, hành động từ cha).
ParentMap = dict[State, tuple[State, Action] | None]


def reconstruct_path(parent: ParentMap, goal: State) -> list[Action]:
    """Khôi phục đường đi từ trạng thái đích về trạng thái gốc."""
    path: list[Action] = []
    node = goal
    while True:
        check_cancelled()
        entry = parent[node]
        if entry is None:
            break
        previous, action = entry
        path.append(action)
        node = previous
    path.reverse()
    return path


def path_cost(engine: Engine, initial_state: State, path: list[Action]) -> float:
    """Tính tổng chi phí bằng cách replay path qua Engine API."""
    state = initial_state
    total = 0.0
    for action in path:
        check_cancelled()
        result = engine.transition(state, action)
        if result.status is not TransitionStatus.OK or result.state is None:
            raise RuntimeError(
                "Path do solver trả về chứa hành động không hợp lệ theo Engine."
            )
        total += engine.step_cost(state, action, result.state)
        state = result.state
    return total


def finalize(
    engine: Engine,
    initial_state: State,
    *,
    solved: bool,
    path: list[Action],
    expanded_nodes: int,
    search_time: float,
    memory_usage: float,
    preprocessing_time: float = 0.0,
) -> SearchResult:
    """Đóng gói kết quả tìm kiếm theo schema chung."""
    return SearchResult(
        solved=solved,
        path=path,
        total_cost=path_cost(engine, initial_state, path) if solved else 0.0,
        search_time=search_time,
        memory_usage=memory_usage,
        expanded_nodes=expanded_nodes,
        solution_length=len(path),
        preprocessing_time=preprocessing_time,
    )


class BaseSolver(ABC):
    """Template chung cho BFS và DFS.

    Lớp này quản lý metrics, trường hợp trạng thái đầu là đích, truy vết path
    và tính chi phí. Thuật toán con chỉ cần triển khai ``_search``.
    """

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def solve(
        self,
        initial_state: State,
        *,
        cancel_event: Event | None = None,
    ) -> SearchResult:
        """Tìm lời giải từ ``initial_state``."""
        with cancellation_scope(cancel_event):
            check_cancelled()
            with track_peak_memory() as peak_memory:
                check_cancelled()
                started_at = perf_counter()
                if self.engine.is_goal(initial_state):
                    goal_state: State | None = initial_state
                    parent: ParentMap = {initial_state: None}
                    expanded_nodes = 0
                else:
                    goal_state, parent, expanded_nodes = self._search(initial_state)

                solved = goal_state is not None
                path = reconstruct_path(parent, goal_state) if goal_state is not None else []
                total_cost = path_cost(self.engine, initial_state, path) if solved else 0.0
                elapsed = perf_counter() - started_at
                return SearchResult(
                    solved=solved,
                    path=path,
                    total_cost=total_cost,
                    search_time=elapsed,
                    memory_usage=peak_memory(),
                    expanded_nodes=expanded_nodes,
                    solution_length=len(path),
                )

    @abstractmethod
    def _search(self, initial_state: State) -> tuple[State | None, ParentMap, int]:
        """Chạy thuật toán cụ thể và trả về goal, parent map, expanded count."""
        raise NotImplementedError
