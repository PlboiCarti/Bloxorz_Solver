"""Thuật toán tìm kiếm theo chiều rộng (BFS)."""

from __future__ import annotations

from collections import deque
from threading import Event

from game.engine import Engine
from game.state import State
from solvers.base_solver import BaseSolver, ParentMap
from solvers.runtime import check_cancelled
from solvers.search_result import SearchResult


class BFSSolver(BaseSolver):
    """BFS graph search, ưu tiên hành động theo thứ tự ``Engine.successors``."""

    def _search(self, initial_state: State) -> tuple[State | None, ParentMap, int]:
        parent: ParentMap = {initial_state: None}
        queue: deque[State] = deque([initial_state])
        expanded_nodes = 0

        while queue:
            check_cancelled()
            current = queue.popleft()
            if self.engine.is_goal(current):
                return current, parent, expanded_nodes

            expanded_nodes += 1
            for action, nxt in self.engine.successors(current):
                check_cancelled()
                if nxt not in parent:
                    parent[nxt] = (current, action)
                    queue.append(nxt)

        return None, parent, expanded_nodes


def solve(
    initial_state: State,
    engine: Engine,
    *,
    cancel_event: Event | None = None,
) -> SearchResult:
    """Giải bài toán bằng BFS theo API solver thống nhất."""
    return BFSSolver(engine).solve(initial_state, cancel_event=cancel_event)
