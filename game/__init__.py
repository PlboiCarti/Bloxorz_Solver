"""Gói game chứa logic cốt lõi của trò chơi Bloxorz."""

from game.actions import Action, Orientation
from game.board import Board, TileType, load_board, parse_board
from game.cost_config import DEFAULT_COST, CostConfig
from game.engine import Engine, TransitionResult, TransitionStatus
from game.heuristic_context import HeuristicContext, SplitSwitchContext
from game.state import BridgeStates, Cell, State, occupied_cells
from game.switches import BridgeMode, SwitchType

__all__ = [
    "DEFAULT_COST",
    "Action",
    "Board",
    "BridgeMode",
    "BridgeStates",
    "Cell",
    "CostConfig",
    "Engine",
    "HeuristicContext",
    "Orientation",
    "SplitSwitchContext",
    "State",
    "SwitchType",
    "TileType",
    "TransitionResult",
    "TransitionStatus",
    "load_board",
    "occupied_cells",
    "parse_board",
]
