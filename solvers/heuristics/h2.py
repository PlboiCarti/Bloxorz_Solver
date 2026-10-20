"""Cost-aware orientation-relaxed pattern database (H2).

H2 giữ rolling geometry, orientation và static VOID topology. Nó relax
fragile/bridge/switch effects. Split switch được biểu diễn bằng pseudo-goal:
đi tới một pose STANDING trên split switch được xem là còn cost bằng 0.
Sau khi concrete state đã split, heuristic trả 0; đây là bản split-safe
admissible, chưa phải full split-pair abstraction.
"""

from __future__ import annotations

import heapq
import itertools
import math
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from time import perf_counter

from game.actions import Action, Orientation
from game.geometry import pose_cells, roll_geometry
from game.heuristic_context import HeuristicContext
from game.state import State

_ROLL_ACTIONS: tuple[Action, ...] = (
    Action.UP,
    Action.DOWN,
    Action.LEFT,
    Action.RIGHT,
)
_ORIENTATIONS: tuple[Orientation, ...] = (
    Orientation.STANDING,
    Orientation.HORIZONTAL,
    Orientation.VERTICAL,
)


@dataclass(frozen=True, slots=True)
class AbstractPose:
    """Một trạng thái block intact trong abstract graph."""

    position: tuple[int, int]
    orientation: Orientation


@dataclass(frozen=True, slots=True)
class H2Heuristic:
    """Bảng khoảng cách precompute và metadata đo preprocessing."""

    distances: dict[AbstractPose, float]
    preprocessing_seconds: float
    abstract_state_count: int
    abstract_edge_count: int

    def __call__(self, state: State) -> float:
        """Tra H2 cho concrete state; split state dùng lower bound bằng zero."""
        if state.split_mode:
            return 0.0

        pose = AbstractPose(state.block_position, state.orientation)
        value = self.distances.get(pose)

        # Một legal concrete state phải map được vào relaxed graph. Fallback
        # về 0 an toàn hơn infinity nếu builder/context có lỗi chưa phát hiện.
        return 0.0 if value is None or math.isinf(value) else value


def _valid_pose(pose: AbstractPose, context: HeuristicContext) -> bool:
    return all(cell in context.support_cells for cell in pose_cells(pose.position, pose.orientation))


def _enumerate_poses(context: HeuristicContext) -> frozenset[AbstractPose]:
    poses: set[AbstractPose] = set()
    for position in context.support_cells:
        for orientation in _ORIENTATIONS:
            pose = AbstractPose(position, orientation)
            if _valid_pose(pose, context):
                poses.add(pose)
    return frozenset(poses)


def _edge_cost(pose: AbstractPose, context: HeuristicContext) -> float:
    if pose.orientation is Orientation.STANDING:
        return context.stand_roll
    return context.lie_roll


def _build_reverse_edges(
    poses: frozenset[AbstractPose],
    context: HeuristicContext,
) -> tuple[dict[AbstractPose, list[tuple[AbstractPose, float]]], int]:
    reverse: dict[AbstractPose, list[tuple[AbstractPose, float]]] = defaultdict(list)
    edge_count = 0

    for source in poses:
        for action in _ROLL_ACTIONS:
            result = roll_geometry(source.position, source.orientation, action)
            if result is None:
                continue

            target_position, target_orientation = result
            target = AbstractPose(target_position, target_orientation)
            if target not in poses:
                continue

            weight = _edge_cost(source, context)
            if weight < 0:
                raise ValueError("H2 yêu cầu abstract edge cost không âm.")

            reverse[target].append((source, weight))
            edge_count += 1

    return reverse, edge_count


def _reverse_dijkstra(
    poses: frozenset[AbstractPose],
    reverse: dict[AbstractPose, list[tuple[AbstractPose, float]]],
    targets: frozenset[AbstractPose],
) -> dict[AbstractPose, float]:
    distances = {pose: math.inf for pose in poses}
    serial = itertools.count()
    frontier: list[tuple[float, int, AbstractPose]] = []

    for target in targets:
        if target not in distances:
            continue
        distances[target] = 0.0
        heapq.heappush(frontier, (0.0, next(serial), target))

    while frontier:
        current_distance, _, current = heapq.heappop(frontier)
        if current_distance != distances[current]:
            continue

        for predecessor, edge_cost in reverse.get(current, ()):
            candidate = current_distance + edge_cost
            if candidate >= distances[predecessor]:
                continue

            distances[predecessor] = candidate
            heapq.heappush(frontier, (candidate, next(serial), predecessor))

    return distances


@lru_cache(maxsize=32)
def _build_h2_cached(context: HeuristicContext) -> H2Heuristic:
    started = perf_counter()
    poses = _enumerate_poses(context)
    reverse, edge_count = _build_reverse_edges(poses, context)

    targets = {
        AbstractPose(context.goal, Orientation.STANDING),
    }
    targets.update(
        AbstractPose(cell, Orientation.STANDING)
        for cell in context.split_switch_cells
    )

    distances = _reverse_dijkstra(poses, reverse, frozenset(targets))
    return H2Heuristic(
        distances=distances,
        preprocessing_seconds=perf_counter() - started,
        abstract_state_count=len(poses),
        abstract_edge_count=edge_count,
    )


def build_h2(context: HeuristicContext, *, use_cache: bool = True) -> H2Heuristic:
    """Build H2 cho một level/cost config.

    ``HeuristicContext`` hashable nên cache tự động phân biệt topology, goal,
    split switch và hai loại roll cost.
    """
    if use_cache:
        return _build_h2_cached(context)
    return _build_h2_cached.__wrapped__(context)


def clear_h2_cache() -> None:
    """Xóa cache H2, chủ yếu dùng trong test/benchmark."""
    _build_h2_cached.cache_clear()

