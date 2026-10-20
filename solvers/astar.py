"""Thuật toán tìm kiếm A* với heuristic admissible — TV4."""

import heapq
import math
import time
import tracemalloc
from collections.abc import Callable

from game.engine import Engine, TransitionStatus
from game.state import State
from solvers.base_solver import ParentMap, finalize, reconstruct_path
from solvers.heuristics.h2 import build_h2
from solvers.search_result import SearchResult

Heuristic = Callable[[State], float]


def solve(
    initial_state: State,
    engine: Engine,
    heuristic: Heuristic | None = None,
) -> SearchResult:
    """Tìm lời giải bằng A*.

    Nếu không truyền heuristic, A* dùng H2 mặc định. Có thể truyền H0/H1/H2
    khác nhau khi benchmark mà không thay đổi vòng lặp tìm kiếm.
    """
    estimate = (
        heuristic
        if heuristic is not None
        else build_h2(engine.get_heuristic_context(), split_aware=True)
    )
    tracemalloc.start()
    started = time.perf_counter()

    parent: ParentMap = {initial_state: None}
    best_cost: dict[State, float] = {initial_state: 0.0}
    counter = 0
    frontier: list[tuple[float, int, float, State]] = [
        (estimate(initial_state), counter, 0.0, initial_state)
    ]
    expanded = 0
    goal_state: State | None = None

    while frontier:
        _, _, cost, state = heapq.heappop(frontier)
        if cost > best_cost.get(state, math.inf):
            continue

        expanded += 1
        if engine.is_goal(state):
            goal_state = state
            break
        g = cost
        for action in engine.legal_actions(state):
            result = engine.transition(state, action)
            if result.status is not TransitionStatus.OK or result.state is None:
                continue
            nxt = result.state
            new_g = g + engine.step_cost(state, action, nxt)
            if new_g < best_cost.get(nxt, math.inf):
                best_cost[nxt] = new_g
                parent[nxt] = (state, action)
                counter += 1
                heapq.heappush(
                    frontier,
                    (new_g + estimate(nxt), counter, new_g, nxt),
                )

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
