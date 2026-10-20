"""HTTP adapter (FastAPI) cho Bloxorz — tầng tích hợp TV5/lead.

Cung cấp 4 endpoint theo `docs/gui_api.md` §2.1:
    GET  /levels            -> danh sách file màn chơi nạp được
    GET  /levels/{name}     -> {"board": {...}, "initial_state": {...}}
    POST /transition        -> TransitionResult JSON
    POST /solve             -> SearchResult JSON

Backend không trạng thái: mỗi request mang đầy đủ level + state. Mọi phản hồi lỗi
là JSON theo hợp đồng `{"error": {"code", "message"}}` (§2.2).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from game import (
    Action,
    Engine,
    Orientation,
    State,
    TransitionResult,
    load_board,
)
from solvers import SearchResult, solve_astar, solve_bfs, solve_dfs, solve_ucs

ROOT = Path(__file__).resolve().parent
LEVELS_DIR = ROOT / "levels"
GUI_INDEX = ROOT / "gui" / "index.html"
ASSETS_DIR = ROOT / "assets"

MAX_BODY_BYTES = 256 * 1024
SOLVE_TIMEOUT_SECONDS = 10.0

_SOLVERS = {
    "BFS": solve_bfs,
    "DFS": solve_dfs,
    "UCS": solve_ucs,
    "ASTAR": solve_astar,
}

_REQUIRED_STATE_FIELDS = (
    "block_position",
    "orientation",
    "occupied_cells",
    "bridge_states",
    "split_mode",
    "cube1_position",
    "cube2_position",
    "active_cube",
)


class ApiError(Exception):
    """Lỗi HTTP có mã code/message theo hợp đồng §2.2."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


def _error_body(code: str, message: str) -> dict[str, Any]:
    return {"error": {"code": code, "message": message}}


# --- Serialization ---


def _board_json(engine: Engine) -> dict[str, Any]:
    board = engine.board
    return {
        "name": board.name,
        "rows": board.rows,
        "cols": board.cols,
        "grid": list(board.grid_raw),
        "start": [board.start[0], board.start[1]],
        "goal": [board.goal[0], board.goal[1]],
        "bridges": [dict(bridge) for bridge in board.bridges],
        "switches": [dict(switch) for switch in board.switches],
    }


def _state_json(state: State) -> dict[str, Any]:
    data = state.to_dict()
    return {
        "block_position": data["block_position"],
        "orientation": data["orientation"],
        "occupied_cells": [[r, c] for r, c in state.occupied_cells()],
        "bridge_states": data["bridge_states"],
        "split_mode": data["split_mode"],
        "cube1_position": data["cube1_position"],
        "cube2_position": data["cube2_position"],
        "active_cube": data["active_cube"],
    }


def _transition_json(result: TransitionResult) -> dict[str, Any]:
    return {
        "status": result.status.value,
        "state": _state_json(result.state) if result.state is not None else None,
        "isGoal": result.is_goal,
        "reason": result.reason,
    }


def _search_json(result: SearchResult) -> dict[str, Any]:
    return {
        "solved": result.solved,
        "path": [action.value for action in result.path],
        "total_cost": result.total_cost,
        "search_time": result.search_time,
        "memory_usage": result.memory_usage,
        "expanded_nodes": result.expanded_nodes,
        "solution_length": result.solution_length,
    }


# --- Validation ---


async def _read_json(request: Request) -> dict[str, Any]:
    body = await request.body()
    if len(body) > MAX_BODY_BYTES:
        raise ApiError(400, "REQUEST_TOO_LARGE", "Request body is too large.")
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        raise ApiError(400, "INVALID_JSON", "Request body is not valid JSON.") from None
    if not isinstance(data, dict):
        raise ApiError(400, "INVALID_JSON", "Request body must be a JSON object.")
    return data


def _engine_for(name: Any) -> Engine:
    if (
        not isinstance(name, str)
        or not name
        or not name.endswith(".json")
        or "/" in name
        or "\\" in name
        or ".." in name
    ):
        raise ApiError(404, "LEVEL_NOT_FOUND", "Level does not exist.")
    path = LEVELS_DIR / name
    if not path.is_file():
        raise ApiError(404, "LEVEL_NOT_FOUND", "Level does not exist.")
    try:
        return Engine(load_board(path))
    except (ValueError, TypeError) as exc:
        raise ApiError(400, "INVALID_LEVEL", f"Invalid level data: {exc}") from None


def _parse_state(engine: Engine, data: Any) -> State:
    if not isinstance(data, dict):
        raise ApiError(422, "INVALID_STATE", "State must be a JSON object.")
    for field in _REQUIRED_STATE_FIELDS:
        if field not in data:
            raise ApiError(400, "INVALID_FIELD", f"Missing state field '{field}'.")
    try:
        state = State.from_dict(data)
    except (KeyError, ValueError, TypeError, IndexError):
        raise ApiError(422, "INVALID_STATE", "State is malformed.") from None

    board = engine.board
    if len(state.bridge_states) != len(board.bridges):
        raise ApiError(422, "INVALID_STATE", "bridge_states must have one entry per bridge.")
    for cell in state.occupied_cells():
        if not board.in_bounds(cell):
            raise ApiError(422, "INVALID_STATE", f"Cell {cell} is outside the board.")
    expected = [[r, c] for r, c in state.occupied_cells()]
    if data.get("occupied_cells") != expected:
        raise ApiError(422, "INVALID_STATE", "occupied_cells does not match the state.")

    if state.split_mode:
        if (
            state.cube1_position is None
            or state.cube2_position is None
            or state.active_cube not in (1, 2)
        ):
            raise ApiError(422, "INVALID_STATE", "Split state requires both cubes and active_cube.")
        if state.cube1_position == state.cube2_position:
            raise ApiError(422, "INVALID_STATE", "The two cubes must occupy distinct cells.")
        if state.orientation is not Orientation.STANDING:
            raise ApiError(422, "INVALID_STATE", "A split state must be STANDING.")
        active_cell = (
            state.cube1_position if state.active_cube == 1 else state.cube2_position
        )
        if state.block_position != active_cell:
            raise ApiError(422, "INVALID_STATE", "block_position must equal the active cube.")
    elif (
        state.cube1_position is not None
        or state.cube2_position is not None
        or state.active_cube is not None
    ):
        raise ApiError(422, "INVALID_STATE", "Non-split state must have null cube fields.")
    return state


# --- App ---

app = FastAPI(title="Bloxorz Solver API")


@app.exception_handler(ApiError)
async def _handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(_error_body(exc.code, exc.message), status_code=exc.status_code)


@app.exception_handler(StarletteHTTPException)
async def _handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
    return JSONResponse(_error_body(code, str(exc.detail)), status_code=exc.status_code)


@app.exception_handler(Exception)
async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(_error_body("INTERNAL_ERROR", "Internal server error."), status_code=500)


@app.get("/levels")
def list_levels() -> list[str]:
    """Liệt kê các file màn chơi mà `load_board` nạp được."""
    names: list[str] = []
    for path in sorted(LEVELS_DIR.glob("*.json")):
        try:
            load_board(path)
        except (ValueError, TypeError, OSError):
            continue
        names.append(path.name)
    return names


@app.get("/levels/{name}")
def get_level(name: str) -> dict[str, Any]:
    """Trả về board đã phân tích kèm `initial_state` mới."""
    engine = _engine_for(name)
    return {
        "board": _board_json(engine),
        "initial_state": _state_json(engine.get_initial_state()),
    }


@app.post("/transition")
async def transition(request: Request) -> dict[str, Any]:
    """Áp dụng một hành động và trả về TransitionResult."""
    data = await _read_json(request)
    engine = _engine_for(data.get("level"))
    action_raw = data.get("action")
    if not isinstance(action_raw, str):
        raise ApiError(400, "INVALID_ACTION", "Missing or invalid 'action'.")
    try:
        action = Action(action_raw)
    except ValueError:
        raise ApiError(400, "INVALID_ACTION", f"Unknown action {action_raw!r}.") from None
    state = _parse_state(engine, data.get("state"))
    return _transition_json(engine.transition(state, action))


@app.post("/solve")
async def solve(request: Request) -> dict[str, Any]:
    """Chạy Solver trong worker thread với timeout cứng, trả về SearchResult."""
    data = await _read_json(request)
    engine = _engine_for(data.get("level"))
    algorithm = data.get("algorithm")
    if not isinstance(algorithm, str) or algorithm not in _SOLVERS:
        raise ApiError(400, "UNKNOWN_ALGORITHM", f"Unknown algorithm {algorithm!r}.")
    state = _parse_state(engine, data.get("state"))

    solver = _SOLVERS[algorithm]
    loop = asyncio.get_running_loop()
    future = loop.run_in_executor(None, solver, state, engine)
    try:
        result = await asyncio.wait_for(future, timeout=SOLVE_TIMEOUT_SECONDS)
    except TimeoutError:
        raise ApiError(504, "SOLVER_TIMEOUT", "Search exceeded the time budget.") from None
    return _search_json(result)


@app.get("/")
def index() -> FileResponse:
    """Phục vụ GUI (gui/index.html) cùng origin nếu tồn tại."""
    if GUI_INDEX.is_file():
        return FileResponse(GUI_INDEX)
    raise ApiError(404, "NOT_FOUND", "GUI is not available.")


@app.get("/assets/{path:path}")
def assets(path: str) -> FileResponse:
    """Phục vụ tệp tĩnh dưới thư mục `assets/`."""
    target = (ASSETS_DIR / path).resolve()
    assets_root = ASSETS_DIR.resolve()
    if assets_root not in target.parents or not target.is_file():
        raise ApiError(404, "NOT_FOUND", "Asset not found.")
    return FileResponse(target)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
