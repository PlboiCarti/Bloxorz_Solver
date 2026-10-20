"""Kiểm thử H2 split-safe và API context dùng chung với Engine."""

from collections import deque

from game import Engine, Orientation, State, TransitionStatus, load_board
from solvers.heuristics.h1 import build_h1
from solvers.heuristics.h2 import build_h2, clear_h2_cache


def _reachable_states(engine: Engine, limit: int = 5000) -> set[State]:
    """Liệt kê một miền reachable nhỏ để kiểm consistency của H2."""
    initial = engine.get_initial_state()
    seen = {initial}
    queue: deque[State] = deque([initial])

    while queue and len(seen) < limit:
        state = queue.popleft()
        for action in engine.legal_actions(state):
            result = engine.transition(state, action)
            assert result.status is TransitionStatus.OK
            assert result.state is not None
            if result.state not in seen:
                seen.add(result.state)
                queue.append(result.state)

    return seen


def test_heuristic_context_relaxes_tiles_and_exposes_split_switches():
    engine = Engine(load_board("levels/level8.json"))
    context = engine.get_heuristic_context()

    assert context.goal == engine.board.goal
    assert context.split_switch_cells
    assert all(cell in context.support_cells for cell in context.split_switch_cells)
    assert all(
        cell not in context.support_cells
        for row, cells in enumerate(engine.board.grid)
        for col, tile in enumerate(cells)
        if tile.value == "."
        for cell in [(row, col)]
    )


def test_h2_goal_and_split_modes_are_safe():
    engine = Engine(load_board("levels/level8.json"))
    clear_h2_cache()
    context = engine.get_heuristic_context()
    h2 = build_h2(context)
    h2_safe = build_h2(context, split_aware=False)

    goal = State(engine.board.goal, Orientation.STANDING)
    split_switch = State(
        block_position=next(iter(engine.get_heuristic_context().split_switch_cells)),
        orientation=Orientation.STANDING,
    )
    split = State(
        block_position=(0, 0),
        orientation=Orientation.STANDING,
        split_mode=True,
        cube1_position=(0, 0),
        cube2_position=(2, 2),
        active_cube=1,
    )

    assert h2(goal) == 0.0
    assert h2(split_switch) >= 0.0
    assert h2_safe(split_switch) == 0.0
    assert h2(split) == 0.0
    assert h2_safe(split) == 0.0


def test_h2_is_consistent_on_reachable_level1_states():
    engine = Engine(load_board("levels/level1.json"))
    h2 = build_h2(engine.get_heuristic_context())

    for state in _reachable_states(engine):
        assert h2(state) >= 0.0
        for action in engine.legal_actions(state):
            result = engine.transition(state, action)
            assert result.status is TransitionStatus.OK
            assert result.state is not None
            assert h2(state) <= (
                engine.step_cost(state, action, result.state) + h2(result.state) + 1e-9
            )


def test_split_aware_h2_keeps_a_nonzero_split_pair_distance():
    engine = Engine(load_board("levels/level8.json"))
    h2 = build_h2(engine.get_heuristic_context(), split_aware=True)
    split_states = [state for state in _reachable_states(engine) if state.split_mode]

    assert split_states
    assert any(h2(state) > 0.0 for state in split_states)

    for state in split_states:
        for action in engine.legal_actions(state):
            result = engine.transition(state, action)
            assert result.status is TransitionStatus.OK
            assert result.state is not None
            assert h2(state) <= (
                engine.step_cost(state, action, result.state) + h2(result.state) + 1e-9
            )


def test_h2_is_not_weaker_than_zero_baseline_on_initial_state():
    engine = Engine(load_board("levels/level1.json"))
    start = engine.get_initial_state()
    h1 = build_h1(engine.get_heuristic_context())
    h2 = build_h2(engine.get_heuristic_context())

    assert h2(start) >= 0.0
    assert h1(start) >= 0.0

