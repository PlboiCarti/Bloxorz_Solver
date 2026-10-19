"""Kiểm thử Solver BFS (TV3)."""

from game import Engine, State, TransitionStatus, load_board
from solvers import solve_bfs


def _replay(engine: Engine, start: State, path) -> State:
    """Phát lại đường đi chỉ qua Engine API, trả về trạng thái cuối."""
    state = start
    for action in path:
        result = engine.transition(state, action)
        assert result.status is TransitionStatus.OK
        assert result.state is not None
        state = result.state
    return state


def test_bfs_solves_level1():
    """BFS giải được level1, lời giải hợp lệ và replay tới đích."""
    engine = Engine(load_board("levels/level1.json"))
    start = engine.get_initial_state()
    result = solve_bfs(start, engine)

    assert result.solved is True
    assert result.solution_length == len(result.path)
    assert result.total_cost == float(len(result.path))
    assert result.expanded_nodes > 0
    assert engine.is_goal(_replay(engine, start, result.path))
