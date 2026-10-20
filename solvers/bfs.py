"""Thuật toán tìm kiếm theo chiều rộng (BFS) — TV3."""

import time
import tracemalloc
from collections import deque

from game.engine import Engine, TransitionStatus
from game.state import State
from solvers.base_solver import ParentMap, finalize, reconstruct_path
from solvers.search_result import SearchResult


def solve(initial_state: State, engine: Engine) -> SearchResult:
    """Tìm lời giải bằng BFS (tối ưu theo số bước khi mọi chi phí bằng nhau)."""
    tracemalloc.start()
    started = time.perf_counter()

    parent: ParentMap = {initial_state: None}
    frontier: deque[State] = deque([initial_state])
    expanded = 0
    goal_state: State | None = None

    while frontier:
        state = frontier.popleft()
        expanded += 1
        if engine.is_goal(state):
            goal_state = state
            break
        for action in engine.legal_actions(state):
            result = engine.transition(state, action)
            if result.status is not TransitionStatus.OK or result.state is None:
                continue
            nxt = result.state
            if nxt not in parent:
                parent[nxt] = (state, action)
                frontier.append(nxt)

    elapsed = time.perf_counter() - started
    memory = tracemalloc.get_traced_memory()[1] / 1e6
    tracemalloc.stop()

    if goal_state is None:
        return finalize(
            engine, initial_state, solved=False, path=[], expanded_nodes=expanded,
            search_time=elapsed, memory_usage=memory,
        )
    return finalize(
        engine, initial_state, solved=True, path=reconstruct_path(parent, goal_state),
        expanded_nodes=expanded, search_time=elapsed, memory_usage=memory,
    )
