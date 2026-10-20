"""H2: cost-aware relaxed pattern database cho Bloxorz.

H2 giữ rolling geometry, orientation và static VOID topology, nhưng relax
fragile/bridge/switch effects. Với ``split_aware=True``, abstract graph còn
giữ vị trí hai cube sau split và các bước di chuyển của từng cube. Vì vậy
heuristic không phải trả về 0 ngay khi concrete state đã split.

Đồ thị được tính một lần bằng reverse Dijkstra. Khi ``split_aware=False``,
module vẫn cung cấp baseline split-safe cũ: các split switch là pseudo-goal và
mọi concrete split state có heuristic bằng 0.
"""

from __future__ import annotations

import heapq
import itertools
import math
from collections import defaultdict, deque
from dataclasses import dataclass
from functools import lru_cache
from time import perf_counter

from game.actions import Action, Orientation
from game.geometry import pose_cells, roll_geometry
from game.heuristic_context import HeuristicContext
from game.state import Cell, State
from solvers.runtime import check_cancelled

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
_SPLIT_DELTAS: tuple[tuple[int, int], ...] = (
    (-1, 0),
    (1, 0),
    (0, -1),
    (0, 1),
)


@dataclass(frozen=True, slots=True)
class AbstractPose:
    """Một trạng thái block intact trong abstract graph."""

    position: Cell
    orientation: Orientation


@dataclass(frozen=True, slots=True)
class AbstractSplitPair:
    """Hai cube split, được lưu theo thứ tự canonical để tránh trùng state."""

    first: Cell
    second: Cell


AbstractState = AbstractPose | AbstractSplitPair


@dataclass(frozen=True, slots=True)
class H2Heuristic:
    """Bảng khoảng cách precompute và metadata đo preprocessing."""

    distances: dict[AbstractState, float]
    preprocessing_seconds: float
    abstract_state_count: int
    abstract_edge_count: int
    split_aware: bool = False

    def __call__(self, state: State) -> float:
        """Tra H2 cho concrete state."""
        if state.split_mode:
            if not self.split_aware:
                return 0.0
            if state.cube1_position is None or state.cube2_position is None:
                return 0.0
            split_pair = _canonical_pair(state.cube1_position, state.cube2_position)
            if split_pair is None:
                return 0.0
            value = self.distances.get(split_pair)
        else:
            pose = AbstractPose(state.block_position, state.orientation)
            value = self.distances.get(pose)

        # Một legal concrete state phải map được vào relaxed graph. Fallback
        # về 0 an toàn hơn infinity nếu builder/context có lỗi chưa phát hiện.
        return 0.0 if value is None or math.isinf(value) else value


def _valid_pose(pose: AbstractPose, context: HeuristicContext) -> bool:
    return all(
        cell in context.support_cells
        for cell in pose_cells(pose.position, pose.orientation)
    )


def _enumerate_poses(context: HeuristicContext) -> frozenset[AbstractPose]:
    poses: set[AbstractPose] = set()
    for position in context.support_cells:
        check_cancelled()
        for orientation in _ORIENTATIONS:
            pose = AbstractPose(position, orientation)
            if _valid_pose(pose, context):
                poses.add(pose)
    return frozenset(poses)


def _edge_cost(pose: AbstractPose, context: HeuristicContext) -> float:
    if pose.orientation is Orientation.STANDING:
        return context.stand_roll
    return context.lie_roll


def _canonical_pair(first: Cell, second: Cell) -> AbstractSplitPair | None:
    if first == second:
        return None
    left, right = sorted((first, second))
    return AbstractSplitPair(left, right)


def _merged_pose(pair: AbstractSplitPair) -> AbstractPose | None:
    row_delta = abs(pair.first[0] - pair.second[0])
    col_delta = abs(pair.first[1] - pair.second[1])
    if (row_delta, col_delta) == (0, 1):
        return AbstractPose(pair.first, Orientation.HORIZONTAL)
    if (row_delta, col_delta) == (1, 0):
        return AbstractPose(pair.first, Orientation.VERTICAL)
    return None


def _abstract_split_state(
    first: Cell,
    second: Cell,
    context: HeuristicContext,
) -> AbstractState | None:
    """Đổi cặp cube thành split state hoặc pose sau merge tự động."""
    if first not in context.support_cells or second not in context.support_cells:
        return None
    pair = _canonical_pair(first, second)
    if pair is None:
        return None
    return _merged_pose(pair) or pair


def _reverse_dijkstra(
    states: frozenset[AbstractState],
    reverse: dict[AbstractState, list[tuple[AbstractState, float]]],
    targets: frozenset[AbstractState],
) -> dict[AbstractState, float]:
    distances = {state: math.inf for state in states}
    serial = itertools.count()
    frontier: list[tuple[float, int, AbstractState]] = []

    for target in targets:
        if target not in distances:
            continue
        distances[target] = 0.0
        heapq.heappush(frontier, (0.0, next(serial), target))

    while frontier:
        check_cancelled()
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
def _build_h2_safe_cached(context: HeuristicContext) -> H2Heuristic:
    """Bản baseline: split switch là pseudo-goal, split state trả 0."""
    started = perf_counter()
    poses = _enumerate_poses(context)
    reverse: dict[AbstractState, list[tuple[AbstractState, float]]] = defaultdict(list)
    edge_count = 0

    for source in poses:
        check_cancelled()
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

    targets = {AbstractPose(context.goal, Orientation.STANDING)}
    targets.update(
        AbstractPose(item.cell, Orientation.STANDING)
        for item in context.split_switches
    )
    distances = _reverse_dijkstra(
        frozenset(poses), reverse, frozenset(targets)
    )
    return H2Heuristic(
        distances=distances,
        preprocessing_seconds=perf_counter() - started,
        abstract_state_count=len(poses),
        abstract_edge_count=edge_count,
        split_aware=False,
    )


def _build_split_aware_graph(
    poses: frozenset[AbstractPose],
    context: HeuristicContext,
) -> tuple[
    frozenset[AbstractState],
    dict[AbstractState, list[tuple[AbstractState, float]]],
    int,
]:
    """Xây forward transitions rồi lưu dưới dạng reverse adjacency.

    Normal poses được liệt kê đầy đủ. Split pairs chỉ được mở rộng từ các
    ``split_cells`` đã khai báo và những pair tiếp theo có thể đạt tới; nhờ đó
    không phải tạo toàn bộ tích Descartes của các ô support.
    """
    states: set[AbstractState] = set(poses)
    reverse: dict[AbstractState, list[tuple[AbstractState, float]]] = defaultdict(list)
    pending: deque[AbstractSplitPair] = deque()
    queued_pairs: set[AbstractSplitPair] = set()
    edge_count = 0

    def register_pair(pair: AbstractSplitPair) -> None:
        if pair in queued_pairs:
            return
        queued_pairs.add(pair)
        states.add(pair)
        pending.append(pair)

    split_targets = {item.cell: item.split_cells for item in context.split_switches}

    for item in context.split_switches:
        check_cancelled()
        split_state = _abstract_split_state(
            item.split_cells[0], item.split_cells[1], context
        )
        if isinstance(split_state, AbstractSplitPair):
            register_pair(split_state)

    # Edges của intact block. Đứng trên P được ánh xạ ngay vào pair mà P tạo ra;
    # không tạo một đường giả đi xuyên qua P như một floor bình thường.
    for source in poses:
        check_cancelled()
        for action in _ROLL_ACTIONS:
            result = roll_geometry(source.position, source.orientation, action)
            if result is None:
                continue

            target_position, target_orientation = result
            target_pose = AbstractPose(target_position, target_orientation)
            if target_pose not in poses:
                continue

            target: AbstractState = target_pose
            split_cells = split_targets.get(target_position)
            if target_orientation is Orientation.STANDING and split_cells is not None:
                split_target = _abstract_split_state(
                    split_cells[0], split_cells[1], context
                )
                if split_target is None:
                    continue
                target = split_target
                if isinstance(target, AbstractSplitPair):
                    register_pair(target)

            weight = _edge_cost(source, context)
            if weight < 0:
                raise ValueError("H2 yêu cầu abstract edge cost không âm.")
            reverse[target].append((source, weight))
            edge_count += 1

    # Edges của split pair. Có thể chọn move cube nào mà không trả thêm
    # switch_cube; bỏ chi phí đó là một relaxation hợp lệ và giữ lower bound.
    while pending:
        check_cancelled()
        source = pending.popleft()
        for moving in (source.first, source.second):
            other = source.second if moving == source.first else source.first
            for delta_row, delta_col in _SPLIT_DELTAS:
                check_cancelled()
                target_cell = (moving[0] + delta_row, moving[1] + delta_col)
                next_state = _abstract_split_state(
                    first=target_cell,
                    second=other,
                    context=context,
                )
                if next_state is None:
                    continue

                reverse[next_state].append((source, context.stand_roll))
                edge_count += 1
                if isinstance(next_state, AbstractSplitPair):
                    register_pair(next_state)

    return frozenset(states), reverse, edge_count


@lru_cache(maxsize=32)
def _build_h2_split_aware_cached(context: HeuristicContext) -> H2Heuristic:
    started = perf_counter()
    poses = _enumerate_poses(context)
    states, reverse, edge_count = _build_split_aware_graph(poses, context)
    goal = AbstractPose(context.goal, Orientation.STANDING)
    distances = _reverse_dijkstra(states, reverse, frozenset({goal}))
    return H2Heuristic(
        distances=distances,
        preprocessing_seconds=perf_counter() - started,
        abstract_state_count=len(states),
        abstract_edge_count=edge_count,
        split_aware=True,
    )


def build_h2(
    context: HeuristicContext,
    *,
    split_aware: bool = True,
    use_cache: bool = True,
) -> H2Heuristic:
    """Build H2 cho một level/cost config.

    ``split_aware=True`` là bản đầy đủ và được A* dùng mặc định. Đặt
    ``split_aware=False`` để tái tạo baseline split-safe trong benchmark.
    ``HeuristicContext`` hashable nên cache tự động phân biệt topology, goal,
    split targets và hai loại roll cost.
    """
    check_cancelled()
    if split_aware:
        if use_cache:
            return _build_h2_split_aware_cached(context)
        return _build_h2_split_aware_cached.__wrapped__(context)
    if use_cache:
        return _build_h2_safe_cached(context)
    return _build_h2_safe_cached.__wrapped__(context)


def clear_h2_cache() -> None:
    """Xóa cache H2, chủ yếu dùng trong test/benchmark."""
    _build_h2_safe_cached.cache_clear()
    _build_h2_split_aware_cached.cache_clear()
