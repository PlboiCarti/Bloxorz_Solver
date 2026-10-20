"""Bộ điều khiển quy tắc và logic cốt lõi (Game Engine) của Bloxorz."""

from dataclasses import dataclass, replace
from enum import Enum

from game import split_block
from game.actions import Action, Orientation
from game.board import Board
from game.cost_config import DEFAULT_COST, CostConfig
from game.state import Cell, State
from game.switches import SwitchType, apply_targets, build_mechanics, is_triggered
from game.tiles import support_failure


class TransitionStatus(str, Enum):
    """Kết quả của một bước chuyển trạng thái (theo `docs/gui_api.md` §3.3)."""

    OK = "ok"            # Bước đi hợp lệ, đã áp dụng
    FALL = "fall"        # Khối/khối lập phương rơi (VOID, ngoài biên, cầu đóng, fragile đứng)
    ILLEGAL = "illegal"  # Hành động không hợp lệ từ trạng thái hiện tại; state giữ nguyên


@dataclass(frozen=True, slots=True)
class TransitionResult:
    """Kết quả trả về của `Engine.transition`.

    Attributes:
        status: Trạng thái kết quả (OK/FALL/ILLEGAL).
        state: Trạng thái mới, chỉ khác None khi `status == OK`.
        is_goal: True nếu trạng thái mới thỏa điều kiện thắng.
        reason: Mã lý do (lowercase) khi FALL/ILLEGAL, None khi OK.
    """

    status: TransitionStatus
    state: State | None
    is_goal: bool
    reason: str | None = None


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

    def __init__(
        self, board: Board, cost_config: CostConfig = DEFAULT_COST
    ) -> None:
        """Khởi tạo Game Engine với bản đồ tương ứng.

        Args:
            board: Bản đồ màn chơi.
            cost_config: Cấu hình chi phí bước đi (mặc định `DEFAULT_COST`).

        Raises:
            ValueError: Nếu cấu hình cầu/công tắc của bản đồ không hợp lệ (TV2).
        """
        self.board = board
        self.mechanics = build_mechanics(board)
        self._cost = cost_config

    def get_initial_state(self) -> State:
        """Trả về trạng thái ban đầu của màn chơi (khối đứng tại ô start 'S')."""
        return State(
            block_position=self.board.start,
            orientation=Orientation.STANDING,
            bridge_states=self.mechanics.initial_bridge_states(),
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
            if self.transition(state, action).status is TransitionStatus.OK
        ]

    def transition(self, state: State, action: Action) -> TransitionResult:
        """Hàm thuần túy (pure function) tính toán kết quả của một hành động.

        Trả về `TransitionResult` với `status` là OK/FALL/ILLEGAL kèm `reason` tương ứng.

        Luồng (theo `docs/gui_api.md` §3.3): di chuyển -> kiểm tra nền dưới trạng thái
        cầu hiện tại -> hiệu ứng ô (switch, cầu, split/merge) -> kiểm tra nền lần nữa.
        """
        if state.split_mode:
            # SWITCH_CUBE: chỉ đổi khối điều khiển, không di chuyển, không kích hoạt ô
            if action == Action.SWITCH_CUBE:
                return self._ok(split_block.switch_active_cube(state))
            candidate_state = split_block.move_active_cube(state, action)
            if candidate_state is None:
                return self._illegal("cube_collision")
        else:
            # SWITCH_CUBE chỉ có ý nghĩa khi ở split_mode
            if action == Action.SWITCH_CUBE:
                return self._illegal("switch_cube_not_split")

            # Áp dụng bảng chuyển đổi hình học
            roll_res = self._roll(state, action)
            if roll_res is None:
                return self._illegal("action_not_allowed")

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

        reason = self._support_failure(candidate_state, candidate_state.occupied_cells())
        if reason is not None:
            return self._fall(reason)

        result = self._apply_tile_effects(state, candidate_state)

        # Switch có thể đóng cầu ngay dưới khối, hoặc split dịch chuyển khối tới ô không có nền
        if result is not candidate_state:
            reason = self._support_failure(result, result.occupied_cells())
            if reason is not None:
                return self._fall(reason)
        return self._ok(result)

    def is_goal(self, state: State) -> bool:
        """Kiểm tra điều kiện chiến thắng: khối STANDING chính xác trên ô đích G."""
        return (
            not state.split_mode
            and state.orientation == Orientation.STANDING
            and state.block_position == self.board.goal
        )

    def step_cost(self, state: State, action: Action, next_state: State) -> float:
        """Trả về chi phí của một bước đi theo `CostConfig` hiện hành.

        Chi phí phi đồng nhất theo tư thế: lăn từ STANDING (dịch neo 2 ô) tốn
        `stand_roll`, lăn khi đang nằm (dịch 1 ô) tốn `lie_roll`; đổi khối điều
        khiển trong split_mode tốn `switch_cube`.
        """
        if action == Action.SWITCH_CUBE:
            return self._cost.switch_cube
        if state.orientation == Orientation.STANDING:
            return self._cost.stand_roll
        return self._cost.lie_roll

    # --- Các hook mở rộng (TV2 đã cài đặt) ---

    def _ok(self, state: State) -> TransitionResult:
        """Tạo kết quả OK kèm đánh giá điều kiện thắng."""
        return TransitionResult(TransitionStatus.OK, state, self.is_goal(state))

    def _fall(self, reason: str) -> TransitionResult:
        """Tạo kết quả FALL với lý do rơi."""
        return TransitionResult(TransitionStatus.FALL, None, False, reason)

    def _illegal(self, reason: str) -> TransitionResult:
        """Tạo kết quả ILLEGAL với lý do không hợp lệ."""
        return TransitionResult(TransitionStatus.ILLEGAL, None, False, reason)

    def _roll(self, state: State, action: Action) -> tuple[Cell, Orientation] | None:
        """Áp dụng bảng chuyển đổi (Section 3.3). Không kiểm tra nền."""
        lookup = _ROLL_TABLE.get((state.orientation, action))
        if lookup is None:
            return None
        delta, new_orientation = lookup
        r, c = state.block_position
        new_anchor: Cell = (r + delta[0], c + delta[1])
        return new_anchor, new_orientation

    def _support_failure(self, state: State, cells: tuple[Cell, ...]) -> str | None:
        """Trả về lý do rơi của các ô `cells` trong ngữ cảnh `state`, hoặc None.

        `state` cung cấp orientation, split_mode, bridge_states cho phép kiểm tra nền.
        - Ngoài bảng / VOID: không đỡ.
        - FRAGILE: vỡ khi khối 1x1x2 đứng thẳng lên.
        - BRIDGE: chỉ đỡ khi đang mở.
        """
        full_block_standing = (
            not state.split_mode and state.orientation == Orientation.STANDING
        )
        return support_failure(
            self.board,
            self.mechanics,
            cells,
            state.bridge_states,
            full_block_standing=full_block_standing,
        )

    def _apply_tile_effects(self, state: State, new_state: State) -> State:
        """Áp dụng hiệu ứng ô sau khi bước đi đã được nâng đỡ.

        - Chỉ phần khối vừa di chuyển mới đè công tắc (khối lập phương đứng yên không kích hoạt lại).
        - Soft: mọi phần khối; Heavy/Split: chỉ khối 1x1x2 đứng thẳng.
        - Split switch: tách thành 2 khối lập phương tại `split_cells`, điều khiển cube1.
        - Sau cùng, nếu đang split và hai khối kề nhau thì tự động hợp khối.
        """
        if new_state.split_mode:
            pressed: tuple[Cell, ...] = (split_block.active_cube_cell(new_state),)
            full_block_standing = False
        else:
            pressed = new_state.occupied_cells()
            full_block_standing = new_state.orientation == Orientation.STANDING

        bridge_states = new_state.bridge_states
        split_cells: tuple[Cell, Cell] | None = None
        for cell in pressed:
            switch = self.mechanics.switch_by_cell.get(cell)
            if switch is None or not is_triggered(switch, full_block_standing=full_block_standing):
                continue
            bridge_states = apply_targets(bridge_states, switch.targets)
            if switch.type is SwitchType.SPLIT:
                split_cells = switch.split_cells

        if split_cells is not None:
            result = split_block.make_split_state(bridge_states, split_cells)
        elif bridge_states != new_state.bridge_states:
            result = replace(new_state, bridge_states=bridge_states)
        else:
            result = new_state

        if result.split_mode:
            result = split_block.try_merge(result)
        return result
