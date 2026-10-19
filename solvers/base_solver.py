"""Tiện ích dùng chung cho các thuật toán tìm kiếm (TV3/TV4).

Các Solver chỉ được dùng Engine API (`legal_actions`, `transition`, `is_goal`,
`step_cost`) — không tự kiểm tra tile/switch của bàn chơi.
"""

from game.actions import Action
from game.engine import Engine, TransitionStatus
from game.state import State
from solvers.search_result import SearchResult

# Cha của một trạng thái: (trạng thái trước, hành động) hoặc None nếu là gốc.
ParentMap = dict[State, "tuple[State, Action] | None"]


def reconstruct_path(parent: ParentMap, goal: State) -> list[Action]:
    """Truy vết đường đi từ `goal` về gốc dựa trên bảng cha `parent`."""
    path: list[Action] = []
    node = goal
    while True:
        entry = parent[node]
        if entry is None:
            break
        prev, action = entry
        path.append(action)
        node = prev
    path.reverse()
    return path


def path_cost(engine: Engine, initial_state: State, path: list[Action]) -> float:
    """Tổng chi phí của `path` bằng cách phát lại qua Engine và cộng `step_cost`."""
    state = initial_state
    cost = 0.0
    for action in path:
        result = engine.transition(state, action)
        if result.status is not TransitionStatus.OK or result.state is None:
            break
        cost += engine.step_cost(state, action, result.state)
        state = result.state
    return cost


def finalize(
    engine: Engine,
    initial_state: State,
    *,
    solved: bool,
    path: list[Action],
    expanded_nodes: int,
    search_time: float,
    memory_usage: float,
) -> SearchResult:
    """Đóng gói kết quả tìm kiếm thống nhất."""
    return SearchResult(
        solved=solved,
        path=path,
        total_cost=path_cost(engine, initial_state, path) if solved else 0.0,
        search_time=search_time,
        memory_usage=memory_usage,
        expanded_nodes=expanded_nodes,
        solution_length=len(path),
    )
