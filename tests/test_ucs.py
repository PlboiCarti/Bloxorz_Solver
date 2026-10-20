"""Kiểm thử Solver UCS (TV4)."""

from game import Engine, State, TransitionStatus, load_board
from solvers import solve_bfs, solve_ucs


def _replay(engine: Engine, start: State, path) -> State:
    """Phát lại đường đi chỉ qua Engine API, trả về trạng thái cuối."""
    state = start
    for action in path:
        result = engine.transition(state, action)
        assert result.status is TransitionStatus.OK
        assert result.state is not None
        state = result.state
    return state


def test_ucs_optimal_like_bfs():
    """UCS tối ưu theo chi phí phi đồng nhất; không đắt hơn đường BFS."""
    engine = Engine(load_board("levels/level1.json"))
    start = engine.get_initial_state()

    result = solve_ucs(start, engine)
    baseline = solve_bfs(start, engine)

    assert result.solved is True
    assert result.solution_length == len(result.path)
    assert result.total_cost > 0
    assert result.total_cost <= baseline.total_cost + 1e-9
    assert engine.is_goal(_replay(engine, start, result.path))
