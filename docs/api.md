# Bloxorz Solver — API Contract & Architecture Specifications

> **Target Audience:** TV1 (Core Engine), TV2 (Advanced Mechanics), TV3 & TV4 (Solvers), TV5 (GUI & Integration).
> **Status:** Stable contract for Core Engine (TV1). Items marked `TEMPORARY` are confirmed placeholders awaiting future work; items marked `CONFIRMED` are decided (see Section 6).

---

## 1. Architectural & Integration Principles

1. **Single Source of Truth:** The `Engine` is the **only** module that contains and enforces Bloxorz game rules.
2. **Solver Isolation:** Solvers never inspect tiles, switches, or board details directly. They interact with the game solely via the Engine API (`legal_actions`, `transition`, `is_goal`, `step_cost`).
3. **GUI Purity (HTTP architecture):** The GUI never manipulates block coordinates or game state directly, and never calls the Engine in-process. It talks only to the backend HTTP endpoints (`docs/gui_api.md` §2.1), which invoke `engine.transition()`; every visual state change and replay step originates from a backend `TransitionResult`.
4. **State Immutability & Hashability:** `State` instances are strictly immutable and hashable so solvers can safely use them in `visited` sets and priority queues.
5. **Uniform Solver Contract:** All search algorithms (BFS, DFS/IDS, UCS, A\*) return the identical `SearchResult` data structure.

---

## 2. Types & Enums

### 2.1 Coordinates

- A board cell is represented as `Cell = tuple[int, int]` in `(row, col)` order.
- Origin `(0, 0)` is at the top-left. `row` increases downward, `col` increases to the right.
- `block_position` denotes the **anchor cell**, defined as the top-left occupied cell of the block.

### 2.2 Action

```python
class Action(Enum):
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    SWITCH_CUBE = "SWITCH_CUBE"  # TV2 split mode only; never legal in TV1 core
```

### 2.3 Orientation

```python
class Orientation(Enum):
    STANDING = "STANDING"      # Occupies 1 cell: (r, c)
    HORIZONTAL = "HORIZONTAL"  # Occupies 2 cells: (r, c), (r, c+1)
    VERTICAL = "VERTICAL"      # Occupies 2 cells: (r, c), (r+1, c)
```

### 2.4 Public Package Exports

Consumers import from the top-level `game` package (defined in `game/__init__.py`):
`Action`, `Board`, `BridgeStates`, `Cell`, `Engine`, `Orientation`, `State`,
`TileType`, `load_board`, `occupied_cells`, `parse_board`.

---

## 3. State Data Model

### 3.1 `State` Definition

```python
@dataclass(frozen=True, slots=True)
class State:
    block_position: tuple[int, int]
    orientation: Orientation
    bridge_states: tuple[bool, ...]  # ordered per Board.bridges; Section 6.1
    split_mode: bool = False
    cube1_position: tuple[int, int] | None = None
    cube2_position: tuple[int, int] | None = None
    active_cube: int | None = None
```

In TV1 Core Engine:

- `bridge_states`: `()` (empty tuple)
- `split_mode`: `False`
- `cube1_position`: `None`
- `cube2_position`: `None`
- `active_cube`: `None`

### 3.2 State Serialization (`to_dict` / `from_dict`)

For serialization and communication with the Three.js GUI:

- `State.to_dict() -> dict`: Returns JSON-serializable primitives (lists for coordinates, enum member names as strings).
- `State.from_dict(d: dict) -> State`: Inverts `to_dict()`, ensuring `State.from_dict(state.to_dict()) == state`.

**Exported JSON Shape:**

```json
{
  "block_position": [3, 4],
  "orientation": "STANDING",
  "bridge_states": [],
  "split_mode": false,
  "cube1_position": null,
  "cube2_position": null,
  "active_cube": null
}
```

### 3.3 Occupied Cells

- `State.occupied_cells() -> tuple[Cell, ...]`: Returns the cells occupied by the block in non-split mode, per Section 2.3.
- Module-level convenience function `occupied_cells(state: State) -> tuple[Cell, ...]` in `game/state.py` returns the same result.

---

## 4. Engine API Contract

```python
class Engine:
    def __init__(self, board: Board) -> None: ...
    def get_initial_state(self) -> State: ...
    def legal_actions(self, state: State) -> list[Action]: ...
    def transition(self, state: State, action: Action) -> TransitionResult: ...
    def is_goal(self, state: State) -> bool: ...
    def step_cost(self, state: State, action: Action, next_state: State) -> float: ...
```

`TransitionResult` is the approved transition contract (`docs/gui_api.md` §3.3): `status` ∈ `ok | fall | illegal`, `state` set only when `status == "ok"`, plus `is_goal` and `reason`. **Implementation pending (TV1/TV2):** until the engine change lands, `game/engine.py` returns `State | None` (`None` = no legal successor, i.e. `fall` or `illegal`), and the backend wraps it into `TransitionResult` for the GUI. The Engine is invoked by the backend only; the GUI consumes it over HTTP (`docs/gui_api.md` §2.1; known deltas of the current adapter are listed in `docs/gui_api.md` §11).

### 4.1 Method Specifications

#### `get_initial_state() -> State`

- Returns the initial state of the stage.
- Block orientation is `Orientation.STANDING`.
- Anchor is at the board's designated start cell `S`.

#### `legal_actions(state: State) -> list[Action]`

- Returns a list of actions whose `transition(state, action)` yields `status == "ok"` (before the `TransitionResult` change lands: actions where `transition(...) is not None`).
- Fixed deterministic ordering: `[Action.UP, Action.DOWN, Action.LEFT, Action.RIGHT, Action.SWITCH_CUBE]`.
- Goal states are **not** treated as terminal by `legal_actions`: legal moves continue to be generated if the block can roll from that position. Solvers check `is_goal(state)` themselves.

#### `transition(state: State, action: Action) -> TransitionResult`

- **Pure function:** Never mutates `state` or internal board structures; has no side effects.
- Returns the approved `TransitionResult` (`docs/gui_api.md` §3.3):
  - `status="ok"`: `state` is the successor `State` and `is_goal = engine.is_goal(state)`.
  - `status="fall"`: the move leaves the block/cubes unsupported (off-board, `VOID`, closed `BRIDGE`, or `STANDING` block/cube on `FRAGILE`); `state` is `None`, `is_goal` is `False`.
  - `status="illegal"`: the action is not allowed from this state; `state` is `None`, `is_goal` is `False`.
  - `reason` is `None` for `ok`, otherwise one of the fixed lowercase codes in `docs/gui_api.md` §3.3.
- **Implementation pending (TV1/TV2):** until the engine change lands it returns `State | None`, where `None` covers both `fall` and `illegal`; the backend adapts that into `TransitionResult` for the GUI.
- Falling is not represented as an active `State`.

#### `is_goal(state: State) -> bool`

- Returns `True` if and only if the block is `Orientation.STANDING` directly on the goal cell `G`, and `split_mode` is `False`.
- Returns `False` if the block is lying (`HORIZONTAL` or `VERTICAL`) across the goal cell. (Note: the goal tile safely supports a lying block, but does not trigger victory).

#### `step_cost(state: State, action: Action, next_state: State) -> float`

- `[TEMPORARY - Section 6.2]` Returns `1.0` by default in TV1.
- Provides edge weight / step cost for UCS and A\*.

### 4.2 Board & Level Loader (`game/board.py`)

`Engine` is constructed with an immutable `Board` (frozen dataclass) and exposes it as `engine.board`.

`Board` fields:

- `rows: int`, `cols: int` — grid dimensions.
- `start: Cell`, `goal: Cell` — coordinates of `S` and `G`.
- `grid: tuple[tuple[TileType, ...], ...]` — parsed tile types.
- `bridges: tuple[dict, ...]`, `switches: tuple[dict, ...]` — raw TV2 config, parsed but not interpreted in TV1.
- `name: str` — level name (`""` if absent).

`Board` methods:

- `in_bounds(cell: Cell) -> bool`
- `tile_at(cell: Cell) -> TileType` — raises `IndexError` if `cell` is out of bounds.

`TileType` (defined in `game/board.py`): `FLOOR` (`#`), `VOID` (`.`), `GOAL` (`G`), `FRAGILE` (`F`), `BRIDGE` (`B`), `SOFT_SWITCH` (`o`), `HEAVY_SWITCH` (`x`), `SPLIT_SWITCH` (`P`). The start char `S` maps to `FLOOR`.

Loader functions:

- `load_board(path: str | Path) -> Board` — reads and validates a JSON level file.
- `parse_board(data: dict) -> Board` — validates level data from a dict (used by tests).

Loader errors:

- `ValueError` — missing/empty grid, zero-length row, ragged rows, invalid character, or a number of `S`/`G` different from exactly one.
- `TypeError` — `bridges`/`switches` is not a list; JSON root is not an object.
- `FileNotFoundError` — level file does not exist.

---

## 5. Solver Output Contract (`SearchResult`)

For reference across TV2, TV3, TV4, and TV5 (owned by `solvers/search_result.py`):

```python
@dataclass
class SearchResult:
    solved: bool
    path: list[Action]
    total_cost: float
    search_time: float
    memory_usage: float
    expanded_nodes: int
    solution_length: int
```

---

## 6. Decisions, Temporary Assumptions & Cross-Stream Dependencies

Status legend: `CONFIRMED` = decided (human, 2026-10-17); `TEMPORARY` = confirmed placeholder with future work required (owner noted).

### 6.1 `bridge_states` Representation (`CONFIRMED`)

- `BridgeStates = tuple[bool, ...]` in `game/state.py`.
- Phần tử thứ $i$ tương ứng với cầu thứ $i$ theo thứ tự danh sách `bridges` trong file JSON của màn chơi (`True` = mở/đi được, `False` = đóng/như void). Nếu màn chơi không có cầu thì là `()`.
- Hashing và equality của State được bảo toàn tuyệt đối, tương thích serialization `to_dict` / `from_dict`.

### 6.2 Cost Function (`TEMPORARY — owner: team, consumed by TV4`)

- `step_cost` returns `1.0`; this placeholder is confirmed.
- BFS/DFS (TV3) are unaffected. UCS/A\* (TV4) must not invent weights; they wait for the team's final cost specification.
- When agreed, change `Engine.step_cost` in one place and update this doc.

### 6.3 Level JSON Format (`CONFIRMED`)

- Approved and implemented in `game/board.py` as proposed: character grid (`#`: floor, `.`: void, `S`: start, `G`: goal, `F`: fragile, `B`: bridge, `o`: soft switch, `x`: heavy switch, `P`: split switch) plus metadata lists `bridges`/`switches`.
- TV2 owns the other level files; every level must use this schema so it stays reusable across all solvers.
- If the schema ever changes, the loader, this doc, and `docs/engine.md` change together.

**Complete example** (`levels/level10.json`, which exercises every tile type):

```json
{
  "name": "level10 - everything combined",
  "grid": [
    "####..FF##..........",
    "#S##BB##P#..........",
    "##x#..FF##..........",
    "..............####..",
    "####..#####FFF####..",
    "#o##BB#####FFF##G#..",
    "####..#####...####.."
  ],
  "bridges": [
    { "id": "A1", "cell": [1, 4], "initial": "closed" },
    { "id": "A2", "cell": [1, 5], "initial": "closed" },
    { "id": "C1", "cell": [5, 4], "initial": "closed" },
    { "id": "C2", "cell": [5, 5], "initial": "closed" }
  ],
  "switches": [
    {
      "cell": [2, 2],
      "type": "heavy",
      "targets": [
        { "bridge": "A1", "mode": "permanent_open" },
        { "bridge": "A2", "mode": "permanent_open" }
      ]
    },
    {
      "cell": [5, 1],
      "type": "soft",
      "targets": [
        { "bridge": "C1", "mode": "toggle" },
        { "bridge": "C2", "mode": "toggle" }
      ]
    },
    {
      "cell": [1, 8],
      "type": "split",
      "targets": [],
      "split_cells": [
        [4, 0],
        [6, 10]
      ]
    }
  ]
}
```

- The JSON root is an object; in code only `grid` is strictly required — `name` defaults to `""` and `bridges`/`switches` default to `[]`. Authoring convention: always include all four keys.
- `start` and `goal` are **not** stored in the file. Exactly one `S` and one `G` are required; `parse_board` derives `board.start`/`board.goal` from them (the `S` tile maps to `FLOOR`).
- `grid`: list of equal-length strings; `rows`/`cols` are derived (this level is 7×20).
- `bridges`: one entry per `B` tile (`{"id", "cell", "initial"}`; `initial` ∈ `{"open", "closed"}`). A multi-tile bridge is expressed as one entry per cell (here `A1`/`A2`, `C1`/`C2`).
- `switches`: `{"cell", "type" ∈ {"soft","heavy","split"}, "targets": [{"bridge", "mode"}], "split_cells"}` with `mode` ∈ `{"toggle","permanent_open","permanent_closed"}`; `split_cells` (two cells) is present only for `split`.
- `bridges`/`switches` are deep-validated against the grid when `Engine(board)` is constructed (`build_mechanics`), not by `parse_board`; any mismatch raises `ValueError`.

### 6.4 Advanced-Tile Behavior in Engine (`CONFIRMED`)

- Implemented by TV2 in `game/tiles.py`, `game/switches.py`, `game/split_block.py` and hooked into `Engine`.
- Ô `FRAGILE`: vỡ khi khối đứng thẳng; nâng đỡ khi khối nằm hoặc khối 1x1.
- Ô `BRIDGE`: chỉ nâng đỡ khi mở.
- Công tắc `soft`, `heavy`, `split`: kích hoạt và cập nhật trạng thái cầu / tách khối.

### 6.5 TV2 Extension Hooks in `Engine` (`CONFIRMED — IMPLEMENTED`)

TV2 đã tích hợp toàn bộ logic cơ chế nâng cao vào `Engine` mà không làm thay đổi public API:

- `_roll(state, action) -> tuple[Cell, Orientation] | None`: Pure geometry roll table.
- `_cells_supported(state, cells) -> bool`: Kiểm tra ô trong bảng, không phải VOID, không phải fragile bị vỡ, và cầu đang mở.
- `_apply_tile_effects(state, new_state) -> State`: Áp dụng hiệu ứng công tắc, chuyển đổi trạng thái cầu, xử lý split switch và tự động merge.

Logic split-mode và `SWITCH_CUBE` đã được TV2 hoàn thiện trực tiếp trong `transition`.

### 6.6 Core Rule Notes

- `legal_actions` checks `transition` for each action in the fixed order `UP, DOWN, LEFT, RIGHT, SWITCH_CUBE` and returns those that are not `None`.
- `SWITCH_CUBE` chỉ hợp lệ khi `split_mode == True`.
- Cơ chế nâng cao: `FRAGILE`, `BRIDGE`, switches (`soft`, `heavy`, `split`) đã được kích hoạt đầy đủ.

### 6.7 Stream Dependency Summary

| Stream                   | Can rely on now                                                                         | Must wait for                        |
| ------------------------ | --------------------------------------------------------------------------------------- | ------------------------------------ |
| TV2 (advanced mechanics) | Full Engine API, advanced mechanics, levels 1–10 completed                              | —                                    |
| TV3 (BFS/DFS)            | Full Engine API (core + advanced), `step_cost == 1.0`, levels 1–10                      | —                                    |
| TV4 (UCS/A\*)            | Full Engine API (core + advanced), levels 1–10                                          | Final cost function (6.2)            |
| TV5 (GUI/integration)    | `State.to_dict` shape, `engine.board`, levels 1–10, `SearchResult` contract (Section 5) | Solver outputs and final cost values |
