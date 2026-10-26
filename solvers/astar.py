"""Thuật toán tìm kiếm A* với H2 mặc định — TV4."""

import heapq
import math
from collections.abc import Callable
from dataclasses import replace
from threading import Event
from time import perf_counter

from game.engine import Engine, TransitionStatus
from game.state import State
from solvers.base_solver import ParentMap, finalize, reconstruct_path
from solvers.heuristics.h2 import build_h2
from solvers.runtime import cancellation_scope, check_cancelled, track_peak_memory
from solvers.search_result import SearchResult

Heuristic = Callable[[State], float]


def solve(
    initial_state: State,
    engine: Engine,
    heuristic: Heuristic | None = None,
    *,
    cancel_event: Event | None = None,
) -> SearchResult:
    """Tìm lời giải bằng A*.

    Nếu không truyền heuristic, A* dùng H2 mặc định. Có thể truyền heuristic
    khác (ví dụ H1) để so sánh mà không thay đổi vòng lặp tìm kiếm.
    """
    with cancellation_scope(cancel_event):
        check_cancelled()
        with track_peak_memory() as peak_memory:
            check_cancelled()
            started = perf_counter()
            if engine.is_goal(initial_state):
                result = finalize(
                    engine,
                    initial_state,
                    solved=True,
                    path=[],
                    expanded_nodes=0,
                    search_time=0.0,
                    memory_usage=0.0,
                )
                return replace(
                    result,
                    search_time=perf_counter() - started,
                    memory_usage=peak_memory(),
                )

            preprocessing_started = perf_counter()
            estimate = (
                heuristic
                if heuristic is not None
                else build_h2(engine.get_heuristic_context())
            )
            preprocessing_time = (
                perf_counter() - preprocessing_started if heuristic is None else 0.0
            )
            check_cancelled()
            search_started = perf_counter()

            parent: ParentMap = {initial_state: None}
            best_cost: dict[State, float] = {initial_state: 0.0}
            counter = 0
            frontier: list[tuple[float, int, float, State]] = [
                (estimate(initial_state), counter, 0.0, initial_state)
            ]
            expanded = 0
            goal_state: State | None = None

            while frontier:
                check_cancelled()
                _, _, cost, state = heapq.heappop(frontier)
                if cost > best_cost.get(state, math.inf):
                    continue

                if engine.is_goal(state):
                    goal_state = state
                    break
                expanded += 1
                for action in engine.legal_actions(state):
                    check_cancelled()
                    result = engine.transition(state, action)
                    if result.status is not TransitionStatus.OK or result.state is None:
                        continue
                    nxt = result.state
                    new_g = cost + engine.step_cost(state, action, nxt)
                    if new_g < best_cost.get(nxt, math.inf):
                        best_cost[nxt] = new_g
                        parent[nxt] = (state, action)
                        counter += 1
                        heapq.heappush(
                            frontier,
                            (new_g + estimate(nxt), counter, new_g, nxt),
                        )

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
                preprocessing_time=preprocessing_time,
            )
            return replace(
                result,
                search_time=perf_counter() - search_started,
                memory_usage=peak_memory(),
            )
