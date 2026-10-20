"""Kiểm thử contract chung của BaseSolver."""

from game import Action, Engine, State, TransitionStatus, parse_board
from solvers.base_solver import BaseSolver, ParentMap


class FixedPathSolver(BaseSolver):
    """Solver giả dùng một path cố định để kiểm tra logic nền."""

    def _search(self, initial_state: State) -> tuple[State | None, ParentMap, int]:
        parent: ParentMap = {initial_state: None}
        current = initial_state
        for action in (Action.RIGHT, Action.RIGHT):
            result = self.engine.transition(current, action)
            assert result.status is TransitionStatus.OK
            assert result.state is not None
            parent[result.state] = (current, action)
            current = result.state
        return current, parent, 2


class NoSolutionSolver(BaseSolver):
    """Solver giả mô phỏng trường hợp frontier cạn mà không có goal."""

    def _search(self, initial_state: State) -> tuple[State | None, ParentMap, int]:
        return None, {initial_state: None}, 1


def make_engine() -> Engine:
    board = parse_board(
        {
            "name": "base_solver_test",
            "grid": ["######", "#S##G#", "######"],
        }
    )
    return Engine(board)


def test_base_solver_reconstructs_path_and_metrics() -> None:
    engine = make_engine()
    initial_state = engine.get_initial_state()

    result = FixedPathSolver(engine).solve(initial_state)

    assert result.solved is True
    assert result.path == [Action.RIGHT, Action.RIGHT]
    assert result.solution_length == len(result.path) == 2
    assert result.total_cost == 2.5
    assert result.expanded_nodes == 2
    assert result.search_time >= 0.0
    assert result.memory_usage >= 0.0

    current = initial_state
    for action in result.path:
        transition = engine.transition(current, action)
        assert transition.status is TransitionStatus.OK
        assert transition.state is not None
        current = transition.state
    assert engine.is_goal(current)


def test_base_solver_handles_initial_state_as_goal() -> None:
    engine = make_engine()
    initial_state = engine.get_initial_state()
    goal_state = State(
        block_position=engine.board.goal,
        orientation=initial_state.orientation,
        bridge_states=initial_state.bridge_states,
    )

    # Dùng trạng thái goal làm initial input để xác nhận không cần gọi _search.
    result = FixedPathSolver(engine).solve(goal_state)

    assert result.solved is True
    assert result.path == []
    assert result.solution_length == 0
    assert result.total_cost == 0.0
    assert result.expanded_nodes == 0


def test_base_solver_returns_consistent_no_solution_result() -> None:
    engine = make_engine()
    result = NoSolutionSolver(engine).solve(engine.get_initial_state())

    assert result.solved is False
    assert result.path == []
    assert result.solution_length == 0
    assert result.total_cost == 0.0
    assert result.expanded_nodes == 1
