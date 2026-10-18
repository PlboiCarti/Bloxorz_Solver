"""Mô-đun triển khai thuật toán tìm kiếm theo chiều sâu (DFS) cho Bloxorz."""

from __future__ import annotations

from game.actions import Action
from game.engine import Engine
from game.state import State
from solvers.base_solver import BaseSolver, ParentMap
from solvers.search_result import SearchResult


class DFSSolver(BaseSolver):
    """Bộ giải Bloxorz sử dụng thuật toán Depth-First Search (DFS).

    DFS khám phá không gian trạng thái bằng cách đi sâu tối đa vào một nhánh
    trước khi quay lui (backtrack), sử dụng ngăn xếp LIFO tường minh
    (explicit stack) để tránh lỗi tràn ngăn xếp đệ quy (RecursionError) trong Python.

    Để bảo toàn chặt chẽ thứ tự ưu tiên hành động theo quy ước của Engine (UP, DOWN,
    LEFT, RIGHT, SWITCH_CUBE) tương tự như DFS đệ quy, các trạng thái con hợp lệ
    được đẩy vào ngăn xếp theo thứ tự đảo ngược (reversed order). Nhờ đó, hành động
    xuất hiện trước trong legal_actions sẽ nằm ở đỉnh stack và được lấy ra mở rộng trước.

    Trạng thái được đánh dấu đã thăm (visited) và ghi nhận vết cha (parent) khi được
    lấy ra khỏi ngăn xếp (visited on pop). Nhờ đó, khi có nhiều nhánh dẫn đến cùng một
    trạng thái giao nhau, nhánh có thứ tự ưu tiên cao hơn (được duyệt trước) sẽ tiếp
    cận và ghi nhận trạng thái đó trước nhánh có độ ưu tiên thấp hơn.
    """

    def _search(self, initial_state: State) -> tuple[State | None, ParentMap, int]:
        """Thực thi vòng lặp tìm kiếm DFS.

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

        # Ngăn xếp lưu các bộ (trạng thái, trạng thái cha, hành động từ cha)
        stack: list[tuple[State, State | None, Action | None]] = [(initial_state, None, None)]
        visited: set[State] = set()
        parent: ParentMap = {}
        expanded_nodes = 0

        while stack:
            current, p_state, p_action = stack.pop()
            if current in visited:
                continue

            visited.add(current)
            if p_state is None or p_action is None:
                parent[current] = None
            else:
                parent[current] = (p_state, p_action)

            if self.engine.is_goal(current):
                return current, parent, expanded_nodes

            expanded_nodes += 1
            successors: list[tuple[State, Action]] = []
            for action in self.engine.legal_actions(current):
                next_state = self.engine.transition(current, action)
                if next_state is None:
                    continue
                if next_state not in visited:
                    successors.append((next_state, action))

            # Đẩy vào ngăn xếp theo thứ tự đảo ngược để hành động đầu tiên được pop ra trước
            for next_state, action in reversed(successors):
                stack.append((next_state, current, action))

        return None, parent, expanded_nodes


def solve(initial_state: State, engine: Engine) -> SearchResult:
    """Hàm tiện ích giải bài toán Bloxorz bằng thuật toán DFS theo API chung.

    Args:
        initial_state: Trạng thái ban đầu của màn chơi.
        engine: Game Engine quản lý bản đồ và thực thi luật chơi.

    Returns:
        Đối tượng SearchResult chứa kết quả giải và các chỉ số hiệu năng.
    """
    return DFSSolver(engine).solve(initial_state)
