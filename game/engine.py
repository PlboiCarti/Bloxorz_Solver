"""Bộ điều khiển quy tắc và logic cốt lõi (Game Engine) của Bloxorz."""

from game.actions import Action, Orientation
from game.board import Board, TileType
from game.state import Cell, State

# Thứ tự cố định khi trả về legal_actions theo quy ước đặc tả
_ACTION_ORDER: tuple[Action, ...] = (
    Action.UP,
    Action.DOWN,
    Action.LEFT,
    Action.RIGHT,
    Action.SWITCH_CUBE,
)

# Bảng chuyển đổi trạng thái lăn khối hộp: (Orientation, Action) -> (anchor_delta, new_orientation)
_ROLL_TABLE: dict[tuple[Orientation, Action], tuple[tuple[int, int], Orientation]] = {
    # Khối đang STANDING:
    (Orientation.STANDING, Action.UP): ((-2, 0), Orientation.VERTICAL),
    (Orientation.STANDING, Action.DOWN): ((1, 0), Orientation.VERTICAL),
    (Orientation.STANDING, Action.LEFT): ((0, -2), Orientation.HORIZONTAL),
    (Orientation.STANDING, Action.RIGHT): ((0, 1), Orientation.HORIZONTAL),
    # Khối đang HORIZONTAL (chiếm (r, c) và (r, c+1)):
    (Orientation.HORIZONTAL, Action.LEFT): ((0, -1), Orientation.STANDING),
    (Orientation.HORIZONTAL, Action.RIGHT): ((0, 2), Orientation.STANDING),
    (Orientation.HORIZONTAL, Action.UP): ((-1, 0), Orientation.HORIZONTAL),
    (Orientation.HORIZONTAL, Action.DOWN): ((1, 0), Orientation.HORIZONTAL),
    # Khối đang VERTICAL (chiếm (r, c) và (r+1, c)):
    (Orientation.VERTICAL, Action.UP): ((-1, 0), Orientation.STANDING),
    (Orientation.VERTICAL, Action.DOWN): ((2, 0), Orientation.STANDING),
    (Orientation.VERTICAL, Action.LEFT): ((0, -1), Orientation.VERTICAL),
    (Orientation.VERTICAL, Action.RIGHT): ((0, 1), Orientation.VERTICAL),
}


class Engine:
    """Game Engine chịu trách nhiệm thực thi toàn bộ luật chơi Bloxorz."""

    def __init__(self, board: Board) -> None:
        """Khởi tạo Game Engine với bản đồ tương ứng."""
        self.board = board

    def get_initial_state(self) -> State:
        """Trả về trạng thái ban đầu của màn chơi (khối đứng tại ô start 'S')."""
        return State(
            block_position=self.board.start,
            orientation=Orientation.STANDING,
            bridge_states=(),
            split_mode=False,
            cube1_position=None,
            cube2_position=None,
            active_cube=None,
        )

    def legal_actions(self, state: State) -> list[Action]:
        """Trả về danh sách các hành động hợp lệ từ trạng thái hiện tại.

        Thứ tự hành động được cố định: UP, DOWN, LEFT, RIGHT, SWITCH_CUBE.
        Trạng thái đích (goal) không bị xem là kết thúc trong legal_actions.
        """
        return [
            action
            for action in _ACTION_ORDER
            if self.transition(state, action) is not None
        ]

    def transition(self, state: State, action: Action) -> State | None:
        """Hàm thuần túy (pure function) tính toán trạng thái tiếp theo sau hành động.

        Trả về None nếu bước đi không hợp lệ (rơi ra ngoài biên hoặc rơi vào ô VOID).
        """
        # SWITCH_CUBE chỉ có ý nghĩa khi ở split_mode (TV2)
        if action == Action.SWITCH_CUBE:
            if not state.split_mode:
                return None
            # TODO(TV2): xử lý chuyển đổi giữa cube1 và cube2 khi ở split_mode
            return None

        # TODO(TV2): xử lý di chuyển từng khối cube riêng lẻ khi split_mode == True

        # Áp dụng bảng chuyển đổi hình học
        roll_res = self._roll(state, action)
        if roll_res is None:
            return None

        new_anchor, new_orientation = roll_res
        candidate_state = State(
            block_position=new_anchor,
            orientation=new_orientation,
            bridge_states=state.bridge_states,
            split_mode=False,
            cube1_position=None,
            cube2_position=None,
            active_cube=None,
        )

        occupied = candidate_state.occupied_cells()
        if not self._cells_supported(state, occupied):
            return None

        return self._apply_tile_effects(state, candidate_state)

    def is_goal(self, state: State) -> bool:
        """Kiểm tra điều kiện chiến thắng: khối STANDING chính xác trên ô đích G."""
        return (
            not state.split_mode
            and state.orientation == Orientation.STANDING
            and state.block_position == self.board.goal
        )

    def step_cost(self, state: State, action: Action, next_state: State) -> float:
        """Trả về chi phí bước đi (mặc định 1.0 trong TV1 core)."""
        # TODO(TV2/TV4): cấu hình hàm chi phí phi đồng nhất cho UCS/A*
        return 1.0

    # --- Các hook mở rộng cho TV2 ---

    def _roll(self, state: State, action: Action) -> tuple[Cell, Orientation] | None:
        """Áp dụng bảng chuyển đổi (Section 3.3). Không kiểm tra nền."""
        lookup = _ROLL_TABLE.get((state.orientation, action))
        if lookup is None:
            return None
        delta, new_orientation = lookup
        r, c = state.block_position
        new_anchor: Cell = (r + delta[0], c + delta[1])
        return new_anchor, new_orientation

    def _cells_supported(self, state: State, cells: tuple[Cell, ...]) -> bool:
        """Kiểm tra các ô mà khối chiếm giữ có được nâng đỡ bởi sàn hay không.

        Core: mọi ô nằm trong bảng và không phải VOID.
        # TODO(TV2): fragile (ô cam làm rơi khối nếu đứng), bridge (kiểm tra đóng/mở).
        """
        for cell in cells:
            if not self.board.in_bounds(cell):
                return False
            tile = self.board.tile_at(cell)
            if tile == TileType.VOID:
                return False
            # TODO(TV2): kiểm tra fragile tile khi đứng
            # TODO(TV2): kiểm tra bridge tile đóng/mở dựa vào state.bridge_states
        return True

    def _apply_tile_effects(self, state: State, new_state: State) -> State:
        """Áp dụng hiệu ứng ô sau khi bước đi thành công.

        Core: trả về new_state không đổi.
        # TODO(TV2): switch (soft, heavy, split), kích hoạt cầu, tách/hợp khối.
        """
        return new_state
