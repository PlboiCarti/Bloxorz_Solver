"""Bộ kiểm thử cho thuật toán DFS (solvers/dfs.py)."""

from pathlib import Path

import pytest

from game.actions import Action, Orientation
from game.board import Board, load_board, parse_board
from game.engine import Engine
from game.state import State
from solvers.dfs import DFSSolver, solve as solve_dfs


def test_dfs_initial_state_is_goal():
    """Kiểm tra khi trạng thái ban đầu đã là đích thì trả về kết quả thành công ngay."""
    board = parse_board({"name": "start_is_goal", "grid": ["S#G"]})
    engine = Engine(board)
    goal_state = State(block_position=board.goal, orientation=Orientation.STANDING)

    result = solve_dfs(goal_state, engine)

    assert result.solved is True
    assert result.path == []
    assert result.solution_length == 0
    assert result.total_cost == 0.0
    assert result.expanded_nodes == 0
    assert result.search_time >= 0.0
    assert result.memory_usage >= 0.0


def test_dfs_linear_path():
    """Kiểm tra DFS tìm đúng đường đi trên hành lang tuyến tính thực sự không có nhánh rẽ."""
    # Hành lang 1x4 bao quanh bởi VOID. Chỉ có duy nhất hướng đi RIGHT hợp lệ:
    # (1, 1) STANDING -> RIGHT -> (1, 2) HORIZONTAL -> RIGHT -> (1, 4) STANDING (G).
    grid = [
        "......",
        "#S##G.",
        "......",
    ]
    board = parse_board({"name": "linear_corridor", "grid": grid})
    engine = Engine(board)
    start = engine.get_initial_state()

    result = DFSSolver(engine).solve(start)

    assert result.solved is True
    assert result.path == [Action.RIGHT, Action.RIGHT]
    assert result.solution_length == 2
    assert result.total_cost == 2.0
    # Mở rộng đúng 2 trạng thái: S (1) và (1, 2) HORIZONTAL (2); goal (1, 4) không bị mở rộng.
    assert result.expanded_nodes == 2

    # Replay xác nhận trạng thái đích
    curr = start
    for action in result.path:
        curr = engine.transition(curr, action)  # type: ignore[assignment]
        assert curr is not None
    assert engine.is_goal(curr)


def test_dfs_side_branches_exploration():
    """Kiểm tra bất biến của DFS khi bản đồ có các nhánh rẽ phụ.

    Trên bản đồ 3x6 có sàn ở hàng 0 và 2, khi đến (1, 2) HORIZONTAL, DFS ưu tiên
    hành động UP hơn RIGHT, nên rẽ lên hàng 0 và đi sâu vào toàn bộ không gian
    trạng thái ở nhánh trên trước khi quay lại tìm đến đích G.
    Kết quả thực tế mở rộng 44 trạng thái, vẫn bảo đảm tìm được lời giải hợp lệ về đích.
    """
    grid = [
        "######",
        "#S##G#",
        "######",
    ]
    board = parse_board({"name": "side_branches", "grid": grid})
    engine = Engine(board)
    start = engine.get_initial_state()

    result = solve_dfs(start, engine)

    assert result.solved is True
    assert result.expanded_nodes == 44

    # Xác nhận replay đường đi về đích
    curr = start
    for action in result.path:
        curr = engine.transition(curr, action)  # type: ignore[assignment]
        assert curr is not None
    assert engine.is_goal(curr)


def test_dfs_no_solution_unreachable_goal():
    """Kiểm tra khi đích bị cô lập thì DFS duyệt hết không gian trạng thái và trả về False."""
    grid = [
        "###...###",
        "#S#...#G#",
        "###...###",
    ]
    board = parse_board({"name": "unreachable", "grid": grid})
    engine = Engine(board)
    start = engine.get_initial_state()

    result = solve_dfs(start, engine)

    assert result.solved is False
    assert result.path == []
    assert result.solution_length == 0
    assert result.total_cost == 0.0
    assert result.expanded_nodes >= 1


def test_dfs_no_legal_actions_isolated_start():
    """Kiểm tra khi ô xuất phát không thể di chuyển đi đâu."""
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

    result = solve_dfs(start, engine)

    assert result.solved is False
    assert result.path == []
    assert result.solution_length == 0
    assert result.expanded_nodes == 1


def test_dfs_handles_cycles_without_infinite_loop():
    """Kiểm tra DFS không bị lặp vô hạn trên đồ thị có chu trình."""
    grid = [
        "######",
        "#S###G",
        "######",
        "######",
    ]
    board = parse_board({"name": "cycles", "grid": grid})
    engine = Engine(board)
    start = engine.get_initial_state()

    result = solve_dfs(start, engine)

    assert result.solved is True
    assert result.solution_length > 0
    curr = start
    for a in result.path:
        curr = engine.transition(curr, a)  # type: ignore[assignment]
        assert curr is not None
    assert engine.is_goal(curr)


def test_dfs_branching_and_intersecting_states_preserves_priority():
    """Kiểm tra DFS bảo toàn chặt chẽ thứ tự ưu tiên UP -> DOWN -> LEFT -> RIGHT
    khi có nhiều nhánh giao nhau (intersecting branches).

    Bản đồ thiết kế có 2 nhánh chính từ S (2, 2):
    - Nhánh 1 (UP): UP -> RIGHT -> DOWN đến trạng thái giao nhau (2, 3) STANDING,
      sau đó tiếp tục RIGHT -> RIGHT đến đích (2, 6) STANDING.
    - Nhánh 2 (DOWN): DOWN -> RIGHT -> UP cũng đến trạng thái giao nhau (2, 3) STANDING.

    Do thứ tự ưu tiên UP > DOWN, DFS bắt buộc phải chọn Nhánh 1:
    1. Hành động đầu tiên trong path phải là Action.UP.
    2. Trạng thái giao nhau (2, 3) STANDING phải được thăm qua Nhánh 1 (từ hướng DOWN từ (0, 3)),
       và Nhánh 2 khi đến (2, 3) sẽ bị bỏ qua vì trạng thái này đã nằm trong visited.
    3. Đường đi chính xác là [UP, RIGHT, DOWN, RIGHT, RIGHT].
    """
    grid = [
        "..##....",
        "..##....",
        "..S###G.",
        "..##....",
        "..##....",
    ]
    board = parse_board({"name": "intersecting_priority", "grid": grid})
    engine = Engine(board)
    start = engine.get_initial_state()

    result = solve_dfs(start, engine)

    assert result.solved is True
    # 1. Bắt buộc bắt đầu bằng Action.UP do ưu tiên UP > DOWN > RIGHT
    assert result.path[0] == Action.UP
    # 2. Toàn bộ đường đi theo nhánh UP và đến đích qua trạng thái giao nhau
    assert result.path == [
        Action.UP,
        Action.RIGHT,
        Action.DOWN,
        Action.RIGHT,
        Action.RIGHT,
    ]
    assert result.solution_length == 5

    # 3. Replay qua Engine bảo đảm toàn bộ đường đi hợp lệ
    curr = start
    for action in result.path:
        nxt = engine.transition(curr, action)
        assert nxt is not None
        curr = nxt
    assert engine.is_goal(curr)


def test_dfs_solves_real_level1():
    """Kiểm tra DFS giải thành công màn chơi level1.json thật và replay hợp lệ."""
    level_path = Path("levels/level1.json")
    if not level_path.exists():
        pytest.skip("File levels/level1.json không tồn tại.")

    board = load_board(level_path)
    engine = Engine(board)
    start = engine.get_initial_state()

    result = solve_dfs(start, engine)

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


def test_dfs_solves_advanced_level_with_switches():
    """Kiểm tra DFS giải thành công level2.json có chứa cầu và công tắc."""
    level_path = Path("levels/level2.json")
    if not level_path.exists():
        pytest.skip("File levels/level2.json không tồn tại.")

    board = load_board(level_path)
    engine = Engine(board)
    start = engine.get_initial_state()

    result = solve_dfs(start, engine)

    assert result.solved is True
    assert result.solution_length > 0
    curr = start
    for action in result.path:
        curr = engine.transition(curr, action)  # type: ignore[assignment]
        assert curr is not None
    assert engine.is_goal(curr)
