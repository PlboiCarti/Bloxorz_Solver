"""Kiểm thử tích hợp solver với Engine trên các màn chơi chính thức."""

from pathlib import Path

import pytest

from game import Engine, TransitionStatus, load_board
from solvers import solve_astar, solve_bfs, solve_dfs, solve_ucs

LEVEL_FILES = [f"level{i}.json" for i in range(1, 11)]
SOLVERS = [solve_bfs, solve_dfs, solve_ucs, solve_astar]


def _replay_to_goal(engine: Engine, path) -> bool:
    """Phát lại toàn bộ đường đi qua Engine API."""
    state = engine.get_initial_state()
    for action in path:
        result = engine.transition(state, action)
        if result.status is not TransitionStatus.OK or result.state is None:
            return False
        state = result.state
    return engine.is_goal(state)


@pytest.mark.parametrize("level_file", LEVEL_FILES)
def test_bfs_solves_every_level(level_file: str) -> None:
    engine = Engine(load_board(Path("levels") / level_file))
    result = solve_bfs(engine.get_initial_state(), engine)

    assert result.solved is True, f"{level_file} không giải được bằng BFS"
    assert result.solution_length == len(result.path)
    assert _replay_to_goal(engine, result.path)


@pytest.mark.parametrize("level_file", ["level1.json", "level2.json", "level10.json"])
@pytest.mark.parametrize("solver", SOLVERS, ids=lambda fn: fn.__module__)
def test_all_solvers_replay_and_cost(level_file: str, solver) -> None:
    engine = Engine(load_board(Path("levels") / level_file))
    result = solver(engine.get_initial_state(), engine)
    baseline = solve_bfs(engine.get_initial_state(), engine)

    assert result.solved is True
    assert _replay_to_goal(engine, result.path)
    assert result.solution_length == len(result.path)
    assert result.total_cost > 0
    if solver in (solve_ucs, solve_astar):
        assert result.total_cost <= baseline.total_cost + 1e-9


@pytest.mark.parametrize("level_file", ["level8.json", "level9.json", "level10.json"])
def test_astar_split_aware_h2_matches_ucs_on_split_levels(level_file: str) -> None:
    engine = Engine(load_board(Path("levels") / level_file))
    ucs = solve_ucs(engine.get_initial_state(), engine)
    astar = solve_astar(engine.get_initial_state(), engine)

    assert ucs.solved is True
    assert astar.solved is True
    assert astar.total_cost == pytest.approx(ucs.total_cost)
    assert _replay_to_goal(engine, astar.path)
