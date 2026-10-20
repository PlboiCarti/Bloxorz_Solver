"""Thuật toán tìm kiếm chi phí thấp nhất trước (UCS) — TV4."""

import heapq
import math
import time
import tracemalloc

from game.engine import Engine, TransitionStatus
from game.state import State
from solvers.base_solver import ParentMap, finalize, reconstruct_path
from solvers.search_result import SearchResult


def solve(initial_state: State, engine: Engine) -> SearchResult:
    """Tìm lời giải bằng UCS (tối ưu theo tổng `step_cost`)."""
    tracemalloc.start()
    started = time.perf_counter()

    parent: ParentMap = {initial_state: None}
    best_cost: dict[State, float] = {initial_state: 0.0}
    counter = 0
    frontier: list[tuple[float, int, State]] = [(0.0, counter, initial_state)]
    expanded = 0
    goal_state: State | None = None

    while frontier:
        cost, _, state = heapq.heappop(frontier)
        if cost > best_cost.get(state, math.inf):
            continue
        expanded += 1
        if engine.is_goal(state):
            goal_state = state
            break
        for action in engine.legal_actions(state):
            result = engine.transition(state, action)
            if result.status is not TransitionStatus.OK or result.state is None:
                continue
            nxt = result.state
            new_cost = cost + engine.step_cost(state, action, nxt)
            if new_cost < best_cost.get(nxt, math.inf):
                best_cost[nxt] = new_cost
                parent[nxt] = (state, action)
                counter += 1
                heapq.heappush(frontier, (new_cost, counter, nxt))

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
