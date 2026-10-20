"""Thuật toán tìm kiếm A* với heuristic admissible — TV4."""

import heapq
import math
import time
import tracemalloc

from game.engine import Engine, TransitionStatus
from game.state import State
from solvers.base_solver import ParentMap, finalize, reconstruct_path
from solvers.search_result import SearchResult


def _heuristic(state: State, engine: Engine) -> float:
    """Heuristic admissible theo `docs/gui_api.md` §3.4.

    Mỗi bước lăn đổi neo tối đa 2 ô Manhattan, nên `ceil(manhattan / 2)` không vượt
    chi phí thật (mọi `step_cost` hiện bằng 1). Ở split_mode đặt `h = 0` để giữ admissible.
    """
    if state.split_mode:
        return 0.0
    r, c = state.block_position
    gr, gc = engine.board.goal
    return float(math.ceil((abs(r - gr) + abs(c - gc)) / 2))


def solve(initial_state: State, engine: Engine) -> SearchResult:
    """Tìm lời giải bằng A* (tối ưu khi heuristic admissible)."""
    tracemalloc.start()
    started = time.perf_counter()

    parent: ParentMap = {initial_state: None}
    best_cost: dict[State, float] = {initial_state: 0.0}
    counter = 0
    frontier: list[tuple[float, int, State]] = [
        (_heuristic(initial_state, engine), counter, initial_state)
    ]
    expanded = 0
    goal_state: State | None = None

    while frontier:
        _, _, state = heapq.heappop(frontier)
        expanded += 1
        if engine.is_goal(state):
            goal_state = state
            break
        g = best_cost[state]
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
                heapq.heappush(frontier, (new_g + _heuristic(nxt, engine), counter, nxt))

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
