"""Kiểm thử Solver A* (TV4)."""

from game import Engine, State, TransitionStatus, load_board
from solvers import solve_astar, solve_bfs


def _replay(engine: Engine, start: State, path) -> State:
    """Phát lại đường đi chỉ qua Engine API, trả về trạng thái cuối."""
    state = start
    for action in path:
        result = engine.transition(state, action)
        assert result.status is TransitionStatus.OK
        assert result.state is not None
        state = result.state
    return state


def test_astar_optimal_and_solves_level1():
    """A* tối ưu (heuristic admissible) nên độ dài bằng BFS."""
    engine = Engine(load_board("levels/level1.json"))
    start = engine.get_initial_state()

    result = solve_astar(start, engine)
    baseline = solve_bfs(start, engine)

    assert result.solved is True
    assert result.solution_length == len(result.path)
    assert result.total_cost == float(len(result.path))
    assert result.solution_length == baseline.solution_length
    assert engine.is_goal(_replay(engine, start, result.path))
