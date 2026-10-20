"""Tiện ích runtime dùng chung cho solver và HTTP adapter."""

from __future__ import annotations

import tracemalloc
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from threading import Event, RLock

_CANCEL_EVENT: ContextVar[Event | None] = ContextVar("solver_cancel_event", default=None)
_TRACEMALLOC_LOCK = RLock()


class SolverCancelled(RuntimeError):
    """Solver được yêu cầu dừng sau khi request hết thời gian."""


@contextmanager
def cancellation_scope(event: Event | None) -> Iterator[None]:
    """Gắn event hủy vào context hiện tại, bao gồm cả bước dựng heuristic."""
    token = _CANCEL_EVENT.set(event)
    try:
        yield
    finally:
        _CANCEL_EVENT.reset(token)


def check_cancelled() -> None:
    """Dừng solver tại checkpoint tiếp theo nếu request đã bị hủy."""
    event = _CANCEL_EVENT.get()
    if event is not None and event.is_set():
        raise SolverCancelled("Solver request was cancelled.")


@contextmanager
def track_peak_memory() -> Iterator[Callable[[], float]]:
    """Đo peak tracemalloc an toàn giữa các solver chạy trong thread pool.

    tracemalloc có trạng thái toàn tiến trình, nên lock được giữ suốt lần solve.
    Nếu profiler bên ngoài đã bật tracing, solver không dừng session đó.
    """
    with _TRACEMALLOC_LOCK:
        owns_trace = not tracemalloc.is_tracing()
        if not owns_trace:
            yield lambda: 0.0
            return

        tracemalloc.start()
        try:
            yield lambda: tracemalloc.get_traced_memory()[1] / 1_000_000
        finally:
            tracemalloc.stop()
