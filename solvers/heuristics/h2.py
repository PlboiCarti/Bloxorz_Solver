"""H2: cost-aware relaxed pattern database cho Bloxorz.

H2 giữ rolling geometry, orientation và static VOID topology, nhưng relax
fragile/bridge/switch effects. Abstract graph còn giữ vị trí hai cube sau
split và các bước di chuyển của từng cube, nên heuristic không phải trả về 0
khi concrete state đã split.

Đồ thị được tính một lần bằng reverse Dijkstra (xem
``docs/deep-research-report.md``, Variant B và mục điều chỉnh khi cài đặt).
"""

from __future__ import annotations

import heapq
import itertools
import math
from collections import defaultdict, deque
from collections.abc import Hashable, Iterable
from dataclasses import dataclass
from functools import lru_cache
from time import perf_counter
from typing import TypeVar

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
Node = TypeVar("Node", bound=Hashable)


@dataclass(frozen=True, slots=True)
class H2Heuristic:
    """Bảng khoảng cách precompute và metadata đo preprocessing."""

    distances: dict[AbstractState, float]
    preprocessing_seconds: float
    abstract_state_count: int
    abstract_edge_count: int

    def __call__(self, state: State) -> float:
        """Khoảng cách abstract d_alpha của state; ``inf`` nghĩa là ngõ cụt đã được chứng minh.

        Giữ ``inf`` (không fallback về 0) để H2 consistent; A* bỏ các state có
        h = inf khỏi frontier (xem docs/deep-research-report.md, Mệnh đề 2).
        """
        if state.split_mode:
            if state.cube1_position is None or state.cube2_position is None:
                return math.inf
            split_pair = _canonical_pair(state.cube1_position, state.cube2_position)
            if split_pair is None:
                return math.inf
            return self.distances.get(split_pair, math.inf)
        pose = AbstractPose(state.block_position, state.orientation)
        return self.distances.get(pose, math.inf)


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


def reverse_dijkstra(
    states: Iterable[Node],
    reverse: dict[Node, list[tuple[Node, float]]],
    targets: Iterable[Node],
) -> dict[Node, float]:
    """Khoảng cách ngắn nhất từ mỗi state tới tập ``targets``; ``inf`` nếu không tới được.

    ``reverse[v]`` liệt kê các cặp ``(u, cost)`` của cạnh ``u -> v``. Dùng chung
    cho H2 và cho h* trong ``experiments/verify_heuristic.py``.
    """
    distances = {state: math.inf for state in states}
    serial = itertools.count()
    frontier: list[tuple[float, int, Node]] = []

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


def _build_abstract_graph(
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
def _build_h2_cached(context: HeuristicContext) -> H2Heuristic:
    started = perf_counter()
    poses = _enumerate_poses(context)
    states, reverse, edge_count = _build_abstract_graph(poses, context)
    goal = AbstractPose(context.goal, Orientation.STANDING)
    distances = reverse_dijkstra(states, reverse, (goal,))
    return H2Heuristic(
        distances=distances,
        preprocessing_seconds=perf_counter() - started,
        abstract_state_count=len(states),
        abstract_edge_count=edge_count,
    )


def clear_h2_cache() -> None:
    """Xoá cache H2 để lần A* kế tiếp đo lại thời gian và bộ nhớ dựng bảng."""
    _build_h2_cached.cache_clear()


def build_h2(context: HeuristicContext) -> H2Heuristic:
    """Build H2 cho một level/cost config.

    ``HeuristicContext`` hashable nên cache tự động phân biệt topology, goal,
    split targets và hai loại roll cost.
    """
    check_cancelled()
    return _build_h2_cached(context)
