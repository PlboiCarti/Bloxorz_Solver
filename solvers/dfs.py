"""Thuật toán tìm kiếm theo chiều sâu (DFS)."""

from __future__ import annotations

from threading import Event

from game.actions import Action
from game.engine import Engine
from game.state import State
from solvers.base_solver import BaseSolver, ParentMap
from solvers.runtime import check_cancelled
from solvers.search_result import SearchResult


class DFSSolver(BaseSolver):
    """DFS graph search dùng stack tường minh và thứ tự hành động ổn định."""

    def _search(self, initial_state: State) -> tuple[State | None, ParentMap, int]:
        stack: list[tuple[State, State | None, Action | None]] = [
            (initial_state, None, None)
        ]
        visited: set[State] = set()
        parent: ParentMap = {}
        expanded_nodes = 0

        while stack:
            check_cancelled()
            current, previous, action_from_previous = stack.pop()
            if current in visited:
                continue

            visited.add(current)
            parent[current] = (
                None
                if previous is None or action_from_previous is None
                else (previous, action_from_previous)
            )
            if self.engine.is_goal(current):
                return current, parent, expanded_nodes

            expanded_nodes += 1
            successors: list[tuple[State, Action]] = []
            for action, nxt in self.engine.successors(current):
                check_cancelled()
                if nxt not in visited:
                    successors.append((nxt, action))

            for next_state, action in reversed(successors):
                stack.append((next_state, current, action))

        return None, parent, expanded_nodes


def solve(
    initial_state: State,
    engine: Engine,
    *,
    cancel_event: Event | None = None,
) -> SearchResult:
    """Giải bài toán bằng DFS theo API solver thống nhất."""
    return DFSSolver(engine).solve(initial_state, cancel_event=cancel_event)
