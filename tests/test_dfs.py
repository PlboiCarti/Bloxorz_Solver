"""Kiểm thử Solver DFS (TV3)."""

from game import Engine, State, TransitionStatus, load_board
from solvers import solve_dfs


def _replay(engine: Engine, start: State, path) -> State:
    """Phát lại đường đi chỉ qua Engine API, trả về trạng thái cuối."""
    state = start
    for action in path:
        result = engine.transition(state, action)
        assert result.status is TransitionStatus.OK
        assert result.state is not None
        state = result.state
    return state


def test_dfs_solves_level1():
    """DFS giải được level1 và lời giải replay tới đích (không yêu cầu tối ưu)."""
    engine = Engine(load_board("levels/level1.json"))
    start = engine.get_initial_state()
    result = solve_dfs(start, engine)

    assert result.solved is True
    assert result.solution_length == len(result.path)
    assert result.expanded_nodes > 0
    assert engine.is_goal(_replay(engine, start, result.path))
