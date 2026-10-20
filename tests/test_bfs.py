"""Kiểm thử BFS theo Engine API hiện hành."""

from game import (
    Action,
    Engine,
    Orientation,
    State,
    TransitionStatus,
    load_board,
    parse_board,
)
from solvers import solve_bfs
from solvers.bfs import BFSSolver


def _replay(engine: Engine, start: State, path: list[Action]) -> State:
    """Phát lại path và trả về trạng thái cuối."""
    state = start
    for action in path:
        result = engine.transition(state, action)
        assert result.status is TransitionStatus.OK
        assert result.state is not None
        state = result.state
    return state


def test_bfs_initial_state_is_goal() -> None:
    board = parse_board({"name": "start_is_goal", "grid": ["S#G"]})
    engine = Engine(board)
    goal = State(board.goal, Orientation.STANDING)

    result = solve_bfs(goal, engine)

    assert result.solved is True
    assert result.path == []
    assert result.solution_length == 0
    assert result.total_cost == 0.0
    assert result.expanded_nodes == 0


def test_bfs_linear_path_and_class_api() -> None:
    board = parse_board(
        {"name": "linear_corridor", "grid": ["......", "#S##G.", "......"]}
    )
    engine = Engine(board)
    start = engine.get_initial_state()

    result = BFSSolver(engine).solve(start)

    assert result.solved is True
    assert result.path == [Action.RIGHT, Action.RIGHT]
    assert result.solution_length == 2
    assert result.total_cost == 2.5
    assert result.expanded_nodes == 2
    assert engine.is_goal(_replay(engine, start, result.path))


def test_bfs_no_solution() -> None:
    board = parse_board(
        {"name": "unreachable", "grid": ["###...###", "#S#...#G#", "###...###"]}
    )
    engine = Engine(board)

    result = solve_bfs(engine.get_initial_state(), engine)

    assert result.solved is False
    assert result.path == []
    assert result.total_cost == 0.0
    assert result.expanded_nodes >= 1


def test_bfs_solves_real_levels() -> None:
    for level in ("level1.json", "level2.json"):
        engine = Engine(load_board(f"levels/{level}"))
        start = engine.get_initial_state()
        result = solve_bfs(start, engine)

        assert result.solved is True, level
        assert result.solution_length == len(result.path)
        assert engine.is_goal(_replay(engine, start, result.path))
