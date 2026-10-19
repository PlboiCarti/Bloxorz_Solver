"""Thuật toán tìm kiếm theo chiều sâu (DFS) — TV3."""

import time
import tracemalloc

from game.engine import Engine, TransitionStatus
from game.state import State
from solvers.base_solver import ParentMap, finalize, reconstruct_path
from solvers.search_result import SearchResult


def solve(initial_state: State, engine: Engine) -> SearchResult:
    """Tìm lời giải bằng DFS (graph search, dùng visited để tránh lặp vô hạn).

    DFS không đảm bảo tối ưu; dùng `visited` để đảm bảo kết thúc trên không gian hữu hạn.
    """
    tracemalloc.start()
    started = time.perf_counter()

    parent: ParentMap = {initial_state: None}
    visited: set[State] = {initial_state}
    stack: list[State] = [initial_state]
    expanded = 0
    goal_state: State | None = None

    while stack:
        state = stack.pop()
        expanded += 1
        if engine.is_goal(state):
            goal_state = state
            break
        actions = engine.legal_actions(state)
        # Đẩy ngược để trạng thái lấy ra tuân theo đúng thứ tự khai báo
        for action in reversed(actions):
            result = engine.transition(state, action)
            if result.status is not TransitionStatus.OK or result.state is None:
                continue
            nxt = result.state
            if nxt not in visited:
                visited.add(nxt)
                parent[nxt] = (state, action)
                stack.append(nxt)

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
