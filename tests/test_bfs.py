"""Bộ kiểm thử cho thuật toán BFS (solvers/bfs.py)."""

from pathlib import Path

import pytest

from game.actions import Action, Orientation
from game.board import Board, load_board, parse_board
from game.engine import Engine
from game.state import State
from solvers.bfs import BFSSolver, solve as solve_bfs


def test_bfs_initial_state_is_goal():
    """Kiểm tra khi trạng thái ban đầu đã là đích thì trả về kết quả thành công ngay."""
    board = parse_board({"name": "start_is_goal", "grid": ["S#G"]})
    engine = Engine(board)
    goal_state = State(block_position=board.goal, orientation=Orientation.STANDING)

    result = solve_bfs(goal_state, engine)

    assert result.solved is True
    assert result.path == []
    assert result.solution_length == 0
    assert result.total_cost == 0.0
    assert result.expanded_nodes == 0
    assert result.search_time >= 0.0
    assert result.memory_usage >= 0.0


def test_bfs_linear_path():
    """Kiểm tra BFS tìm đúng đường đi trên hành lang tuyến tính thực sự không có nhánh rẽ."""
    # Hành lang 1x4 bao quanh bởi VOID. Chỉ có duy nhất hướng đi RIGHT hợp lệ:
    # (1, 1) STANDING -> RIGHT -> (1, 2) HORIZONTAL -> RIGHT -> (1, 4) STANDING (G).
    # Các hướng UP, DOWN, LEFT đều rơi vào VOID nên không sinh thêm node con.
    grid = [
        "......",
        "#S##G.",
        "......",
    ]
    board = parse_board({"name": "linear_corridor", "grid": grid})
    engine = Engine(board)
    start = engine.get_initial_state()

    result = BFSSolver(engine).solve(start)

    assert result.solved is True
    assert result.path == [Action.RIGHT, Action.RIGHT]
    assert result.solution_length == 2
    assert result.total_cost == 2.0
    # Mở rộng đúng 2 trạng thái: S (1) và (1, 2) HORIZONTAL (2); goal (1, 4) không bị mở rộng.
    assert result.expanded_nodes == 2

    # Kiểm tra replay qua Engine
    curr = start
    for action in result.path:
        curr = engine.transition(curr, action)  # type: ignore[assignment]
        assert curr is not None
    assert engine.is_goal(curr)


def test_bfs_corridor_with_side_branches():
    """Kiểm tra bất biến tổng quát của BFS trên bản đồ có nhánh phụ bên cạnh.

    Trên bản đồ 3x6 có sàn ở hàng 0 và 2, khi khối ở trạng thái HORIZONTAL tại (1, 2),
    hành động UP và DOWN hợp lệ và được đưa vào hàng đợi trước RIGHT (do thứ tự UP, DOWN, LEFT, RIGHT).
    Với cơ chế goal-on-dequeue, BFS lấy và mở rộng 2 nhánh phụ đó trước khi lấy goal ra,
    do đó expanded_nodes = 4, nhưng độ dài đường đi tối ưu vẫn luôn là 2.
    """
    grid = [
        "######",
        "#S##G#",
        "######",
    ]
    board = parse_board({"name": "with_branches", "grid": grid})
    engine = Engine(board)
    start = engine.get_initial_state()

    result = solve_bfs(start, engine)

    assert result.solved is True
    assert result.path == [Action.RIGHT, Action.RIGHT]
    assert result.solution_length == 2
    assert result.total_cost == 2.0
    assert result.expanded_nodes == 4


def test_bfs_finds_shortest_path_optimality():
    """Kiểm tra BFS luôn chọn đường đi có ít bước nhất khi có nhiều nhánh đến đích."""
    grid = [
        "#######",
        "#S##G##",
        "#######",
    ]
    board = parse_board({"name": "shortest", "grid": grid})
    engine = Engine(board)
    start = engine.get_initial_state()

    result = solve_bfs(start, engine)

    assert result.solved is True
    assert result.solution_length == 2
    assert result.path == [Action.RIGHT, Action.RIGHT]


def test_bfs_no_solution_unreachable_goal():
    """Kiểm tra khi đích bị cô lập hoàn toàn thì BFS trả về solved=False."""
    grid = [
        "###...###",
        "#S#...#G#",
        "###...###",
    ]
    board = parse_board({"name": "unreachable", "grid": grid})
    engine = Engine(board)
    start = engine.get_initial_state()

    result = solve_bfs(start, engine)

    assert result.solved is False
    assert result.path == []
    assert result.solution_length == 0
    assert result.total_cost == 0.0
    assert result.expanded_nodes >= 1


def test_bfs_no_legal_actions_isolated_start():
    """Kiểm tra khi ô xuất phát không thể di chuyển đi đâu mà không rơi."""
    grid = [
        ".#.",
        "#S#",
        ".#.",
        "..G",
    ]
    board = parse_board({"name": "stuck", "grid": grid})
    engine = Engine(board)
    start = engine.get_initial_state()
    assert engine.legal_actions(start) == []

    result = solve_bfs(start, engine)

    assert result.solved is False
    assert result.path == []
    assert result.solution_length == 0
    assert result.expanded_nodes == 1


def test_bfs_handles_cycles_without_infinite_loop():
    """Kiểm tra BFS dừng chính xác trên đồ thị có chu trình di chuyển qua lại."""
    grid = [
        "######",
        "#S###G",
        "######",
        "######",
    ]
    board = parse_board({"name": "cycles", "grid": grid})
    engine = Engine(board)
    start = engine.get_initial_state()

    result = solve_bfs(start, engine)

    assert result.solved is True
    assert result.solution_length > 0
    curr = start
    for a in result.path:
        curr = engine.transition(curr, a)  # type: ignore[assignment]
        assert curr is not None
    assert engine.is_goal(curr)


def test_bfs_solves_real_level1():
    """Kiểm tra BFS giải thành công levels/level1.json và sinh ra lời giải chuẩn."""
    level_path = Path("levels/level1.json")
    if not level_path.exists():
        pytest.skip("File levels/level1.json không tồn tại.")

    board = load_board(level_path)
    engine = Engine(board)
    start = engine.get_initial_state()

    result = solve_bfs(start, engine)

    assert result.solved is True
    assert result.solution_length > 0
    assert result.solution_length == len(result.path)
    assert result.total_cost == float(result.solution_length)
    assert result.expanded_nodes > 0
    assert result.search_time > 0.0

    # Xác nhận từng bước replay qua Engine
    curr = start
    for action in result.path:
        next_s = engine.transition(curr, action)
        assert next_s is not None, f"Hành động {action} không hợp lệ từ {curr}"
        curr = next_s
    assert engine.is_goal(curr)


def test_bfs_solves_advanced_level_with_switches():
    """Kiểm tra BFS giải thành công level2.json có chứa cầu và công tắc."""
    level_path = Path("levels/level2.json")
    if not level_path.exists():
        pytest.skip("File levels/level2.json không tồn tại.")

    board = load_board(level_path)
    engine = Engine(board)
    start = engine.get_initial_state()

    result = solve_bfs(start, engine)

    assert result.solved is True
    assert result.solution_length >= 7
    curr = start
    for action in result.path:
        curr = engine.transition(curr, action)  # type: ignore[assignment]
        assert curr is not None
    assert engine.is_goal(curr)
