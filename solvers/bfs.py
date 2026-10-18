"""Mô-đun triển khai thuật toán tìm kiếm theo chiều rộng (BFS) cho Bloxorz."""

from __future__ import annotations

from collections import deque

from game.actions import Action
from game.engine import Engine
from game.state import State
from solvers.base_solver import BaseSolver, ParentMap
from solvers.search_result import SearchResult


class BFSSolver(BaseSolver):
    """Bộ giải Bloxorz sử dụng thuật toán Breadth-First Search (BFS).

    BFS khám phá không gian trạng thái theo từng mức độ sâu bằng hàng đợi FIFO
    (collections.deque). Thuật toán đảm bảo tìm ra đường đi ngắn nhất theo số
    bước đi khi mọi hành động có cùng chi phí (uniform step cost).

    Trạng thái được đánh dấu phát hiện ngay khi đưa vào hàng đợi (discovered on
    enqueue) để tránh đưa trùng lặp một trạng thái vào hàng đợi nhiều lần.
    Việc kiểm tra đích (goal test) được thực hiện nhất quán khi lấy trạng thái ra
    khỏi hàng đợi (goal-on-dequeue).
    """

    def _search(self, initial_state: State) -> tuple[State | None, ParentMap, int]:
        """Thực thi vòng lặp tìm kiếm BFS.

        Args:
            initial_state: Trạng thái bắt đầu tìm kiếm (đã được xác nhận không
                phải là đích bởi BaseSolver.solve, nhưng vẫn được kiểm tra an toàn).

        Returns:
            Tuple gồm:
                - State đích nếu tìm thấy, hoặc None nếu cạn frontier.
                - ParentMap chứa thông tin vết đường đi: initial_state ánh xạ về
                  None, mỗi trạng thái khác ánh xạ về (parent_state, action).
                - Số lượng trạng thái đã được mở rộng (expanded_nodes).
        """
        if self.engine.is_goal(initial_state):
            return initial_state, {initial_state: None}, 0

        parent: ParentMap = {initial_state: None}
        queue: deque[State] = deque([initial_state])
        expanded_nodes = 0

        while queue:
            current = queue.popleft()
            if self.engine.is_goal(current):
                return current, parent, expanded_nodes

            expanded_nodes += 1
            for action in self.engine.legal_actions(current):
                next_state = self.engine.transition(current, action)
                if next_state is None:
                    continue
                if next_state not in parent:
                    parent[next_state] = (current, action)
                    queue.append(next_state)

        return None, parent, expanded_nodes


def solve(initial_state: State, engine: Engine) -> SearchResult:
    """Hàm tiện ích giải bài toán Bloxorz bằng thuật toán BFS theo API chung.

    Args:
        initial_state: Trạng thái ban đầu của màn chơi.
        engine: Game Engine quản lý bản đồ và thực thi luật chơi.

    Returns:
        Đối tượng SearchResult chứa kết quả giải và các chỉ số hiệu năng.
    """
    return BFSSolver(engine).solve(initial_state)
