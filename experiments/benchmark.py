"""Các tiện ích chạy benchmark trên một bộ test cố định."""
from __future__ import annotations

import queue
import threading
from collections.abc import Callable
from typing import Any

from game import Engine, State
from solvers import clear_h2_cache, solve_astar, solve_bfs, solve_dfs, solve_ucs
from solvers.runtime import SolverCancelled

SOLVERS: dict[str, Callable[..., Any]] = {
    "BFS": solve_bfs,
    "DFS": solve_dfs,
    "UCS": solve_ucs,
    "A*": solve_astar,
}


def run_with_timeout(
    solver: Callable[..., Any],
    initial_state: State,
    engine: Engine,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Chạy solver với timeout hợp tác, không làm treo toàn bộ benchmark.

    Cache H2 bị xoá trước mỗi lượt để A* luôn tự dựng bảng: preprocessing time
    và peak memory phản ánh chi phí thật, kể cả khi ``--repeat`` > 1.
    """
    clear_h2_cache()
    cancel_event = threading.Event()
    result_queue: queue.Queue[tuple[str, Any]] = queue.Queue(maxsize=1)

    def target() -> None:
        try:
            result_queue.put(("ok", solver(initial_state, engine, cancel_event=cancel_event)))
        except SolverCancelled:
            result_queue.put(("cancelled", None))
        except BaseException as exc:  # ghi lại lỗi từng case, không mất cả batch
            result_queue.put(("error", exc))

    worker = threading.Thread(target=target, daemon=True)
    worker.start()
    worker.join(timeout_seconds)
    if worker.is_alive():
        cancel_event.set()
        worker.join(2.0)
        return {
            "status": "timeout",
            "search_time_seconds": timeout_seconds,
            "peak_memory_mb": None,
            "expanded_nodes": None,
            "solution_length": None,
            "total_cost": None,
            "preprocessing_time_seconds": None,
            "error": "Timeout; cancellation requested.",
        }

    try:
        kind, payload = result_queue.get_nowait()
    except queue.Empty:
        return {
            "status": "error",
            "search_time_seconds": None,
            "peak_memory_mb": None,
            "expanded_nodes": None,
            "solution_length": None,
            "total_cost": None,
            "preprocessing_time_seconds": None,
            "error": "Worker exited without returning a result.",
        }

    if kind == "cancelled":
        return {
            "status": "timeout",
            "search_time_seconds": timeout_seconds,
            "peak_memory_mb": None,
            "expanded_nodes": None,
            "solution_length": None,
            "total_cost": None,
            "preprocessing_time_seconds": None,
            "error": "Solver cancelled after timeout.",
        }
    if kind == "error":
        return {
            "status": "error",
            "search_time_seconds": None,
            "peak_memory_mb": None,
            "expanded_nodes": None,
            "solution_length": None,
            "total_cost": None,
            "preprocessing_time_seconds": None,
            "error": f"{type(payload).__name__}: {payload}",
        }

    return {
        "status": "solved" if payload.solved else "unsolved",
        "search_time_seconds": payload.search_time,
        "peak_memory_mb": payload.memory_usage,
        "expanded_nodes": payload.expanded_nodes,
        "solution_length": payload.solution_length if payload.solved else None,
        "total_cost": payload.total_cost if payload.solved else None,
        "preprocessing_time_seconds": payload.preprocessing_time,
        "error": None,
    }
