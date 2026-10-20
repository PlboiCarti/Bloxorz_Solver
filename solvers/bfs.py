"""Thuật toán tìm kiếm theo chiều rộng (BFS)."""

from __future__ import annotations

from collections import deque
from threading import Event

from game.engine import Engine, TransitionStatus
from game.state import State
from solvers.base_solver import BaseSolver, ParentMap
from solvers.runtime import check_cancelled
from solvers.search_result import SearchResult


class BFSSolver(BaseSolver):
    """BFS graph search, ưu tiên hành động theo ``Engine.legal_actions``."""

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
            for action in self.engine.legal_actions(current):
                check_cancelled()
                result = self.engine.transition(current, action)
                if result.status is not TransitionStatus.OK or result.state is None:
                    continue
                if result.state not in parent:
                    parent[result.state] = (current, action)
                    queue.append(result.state)

        return None, parent, expanded_nodes


def solve(
    initial_state: State,
    engine: Engine,
    *,
    cancel_event: Event | None = None,
) -> SearchResult:
    """Giải bài toán bằng BFS theo API solver thống nhất."""
    return BFSSolver(engine).solve(initial_state, cancel_event=cancel_event)
