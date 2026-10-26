"""Thuật toán tìm kiếm chi phí thấp nhất trước (UCS) — TV4."""

import heapq
import math
from dataclasses import replace
from threading import Event
from time import perf_counter

from game.engine import Engine
from game.state import State
from solvers.base_solver import ParentMap, finalize, reconstruct_path
from solvers.runtime import cancellation_scope, check_cancelled, track_peak_memory
from solvers.search_result import SearchResult


def solve(
    initial_state: State,
    engine: Engine,
    *,
    cancel_event: Event | None = None,
) -> SearchResult:
    """Tìm lời giải bằng UCS (tối ưu theo tổng `step_cost`)."""
    with cancellation_scope(cancel_event):
        check_cancelled()
        with track_peak_memory() as peak_memory:
            check_cancelled()
            search_started = perf_counter()
            parent: ParentMap = {initial_state: None}
            best_cost: dict[State, float] = {initial_state: 0.0}
            counter = 0
            frontier: list[tuple[float, int, State]] = [(0.0, counter, initial_state)]
            expanded = 0
            goal_state: State | None = None

            while frontier:
                check_cancelled()
                cost, _, state = heapq.heappop(frontier)
                if cost > best_cost.get(state, math.inf):
                    continue
                if engine.is_goal(state):
                    goal_state = state
                    break
                expanded += 1
                for action, nxt in engine.successors(state):
                    check_cancelled()
                    new_cost = cost + engine.step_cost(state, action, nxt)
                    if new_cost < best_cost.get(nxt, math.inf):
                        best_cost[nxt] = new_cost
                        parent[nxt] = (state, action)
                        counter += 1
                        heapq.heappush(frontier, (new_cost, counter, nxt))

            solved = goal_state is not None
            path = reconstruct_path(parent, goal_state) if goal_state is not None else []
            result = finalize(
                engine,
                initial_state,
                solved=solved,
                path=path,
                expanded_nodes=expanded,
                search_time=0.0,
                memory_usage=0.0,
            )
            return replace(
                result,
                search_time=perf_counter() - search_started,
                memory_usage=peak_memory(),
            )
