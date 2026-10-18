"""Kiểm thử tích hợp trên các màn chơi chính thức."""

from pathlib import Path

import pytest

from game.board import load_board
from game.engine import Engine
from solvers import solve_bfs, solve_dfs


@pytest.mark.parametrize("level_file", ["level1.json", "level2.json", "level3.json"])
def test_bfs_dfs_solvers_integration_and_optimality(level_file: str):
    """Kiểm thử tích hợp BFS và DFS trên các màn chơi có sẵn:

    1. Cả hai thuật toán đều giải thành công (solved=True).
    2. Độ dài lời giải của BFS luôn nhỏ hơn hoặc bằng DFS (tính tối ưu của BFS).
    3. Đường đi của cả hai đều replay hợp lệ qua Engine và kết thúc tại đích.
    4. Các chỉ số metrics đều có giá trị hợp lệ.
    """
    path = Path("levels") / level_file
    if not path.exists():
        pytest.skip(f"Level {level_file} không tồn tại.")

    board = load_board(path)
    engine = Engine(board)
    start = engine.get_initial_state()

    bfs_result = solve_bfs(start, engine)
    dfs_result = solve_dfs(start, engine)

    # 1. Thành công
    assert bfs_result.solved is True, f"BFS không giải được {level_file}"
    assert dfs_result.solved is True, f"DFS không giải được {level_file}"

    # 2. BFS tối ưu số bước đi so với DFS
    assert bfs_result.solution_length <= dfs_result.solution_length

    # 3. Replay hợp lệ
    for name, res in [("BFS", bfs_result), ("DFS", dfs_result)]:
        curr = start
        for action in res.path:
            nxt = engine.transition(curr, action)
            assert nxt is not None, f"Hành động {action} trong lời giải của {name} không hợp lệ!"
            curr = nxt
        assert engine.is_goal(curr), f"Lời giải của {name} không kết thúc ở đích!"

    # 4. Metrics nhất quán
    for res in [bfs_result, dfs_result]:
        assert res.solution_length == len(res.path)
        assert res.total_cost == float(len(res.path))
        assert res.expanded_nodes > 0
        assert res.search_time >= 0.0
        assert res.memory_usage >= 0.0
