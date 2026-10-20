# Bloxorz Solver — API Contract & Architecture Specifications

> **Target Audience:** TV1 (Core Engine), TV2 (Advanced Mechanics), TV3 & TV4 (Solvers), TV5 (GUI & Integration).
> **Status:** Python Engine API implemented in `game/`. `docs/gui_api.md` is the GUI/backend wire contract. `TEMPORARY` marks a confirmed placeholder decision; `CONFIRMED` marks an agreed behavior or representation.

---

## 1. Architectural & Integration Principles

1. **Single Source of Truth:** The `Engine` is the **only** module that contains and enforces Bloxorz game rules.
2. **Solver Isolation:** Solvers never inspect tiles, switches, or board details directly. They interact with the game solely via the Engine API (`legal_actions`, `transition`, `is_goal`, `step_cost`).
3. **GUI Purity:** The GUI never decides game transitions. The browser sends actions through `server.py` over HTTP; the adapter calls `Engine.transition()` and returns the authoritative result for rendering.
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
`Action`, `Board`, `Bridge`, `BridgeStates`, `Cell`, `Engine`, `Orientation`,
`State`, `Switch`, `SwitchTarget`, `TileType`, `TransitionResult`,
`TransitionStatus`, `load_board`, `occupied_cells`, `parse_board`.

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

- `State.occupied_cells() -> tuple[Cell, ...]`: Returns occupied cells in canonical order for both standard and split states, per Section 2.3.
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

`transition` returns a `TransitionResult`, separating the game outcome from the HTTP envelope (encoding in `docs/gui_api.md` §3.3):

```python
class TransitionStatus(str, Enum):
    OK = "ok"
    FALL = "fall"
    ILLEGAL = "illegal"

@dataclass(frozen=True)
class TransitionResult:
    status: TransitionStatus
    state: State | None
    is_goal: bool
    reason: str | None = None
    fall_state: State | None = None  # rejected geometry for fall animation only
```

When `status == FALL`, `state` remains `None`. `fall_state` carries the attempted geometry that caused the fall so the GUI can animate the block into the unsupported/trap cell. It is presentation data only and must not replace the current game state.

### 4.1 Method Specifications

#### `get_initial_state() -> State`

- Returns the initial state of the stage.
- Block orientation is `Orientation.STANDING`.
- Anchor is at the board's designated start cell `S`.

#### `legal_actions(state: State) -> list[Action]`

- Tries each `Action` in enum declaration order: `UP`, `DOWN`, `LEFT`, `RIGHT`, `SWITCH_CUBE`.
- Returns only actions whose `transition(state, action).status` is `TransitionStatus.OK`. `FALL` and `ILLEGAL` results are excluded; `SWITCH_CUBE` can be returned only in split mode.
- Goal states are **not** treated as terminal by `legal_actions`: legal moves continue to be generated if the block can roll from that position. Solvers check `is_goal(state)` themselves.

#### `transition(state: State, action: Action) -> TransitionResult`

- **Pure function:** Never mutates `state` or internal board structures; has no side effects.
- Returns `OK` with a successor `State`, `FALL` with `state=None` plus rejected `fall_state` geometry for unsupported movement, or `ILLEGAL` with `state=None` for an action invalid in the current state. Canonical reasons and HTTP encoding are specified in `docs/gui_api.md` §3.3.
- Falling is not represented as an active state, and does not persist board damage.

#### `is_goal(state: State) -> bool`

- Returns `True` if and only if the block is `Orientation.STANDING` directly on the goal cell `G`, and `split_mode` is `False`.
- Returns `False` if the block is lying (`HORIZONTAL` or `VERTICAL`) across the goal cell. (Note: the goal tile safely supports a lying block, but does not trigger victory).

#### `step_cost(state: State, action: Action, next_state: State) -> float`

- `[TEMPORARY - Section 6.2]` Returns `1.0` by default in TV1.
- Provides edge weight / step cost for UCS and A\*.

### 4.2 Board & Level Loader (`game/board.py`)

`Engine` is constructed with an immutable `Board` (frozen dataclass) and exposes it as `engine.board`.

`Board` is a frozen dataclass. Its level data is immutable; the derived lookup maps are read-only.

| Field           | Type                               | Meaning                                                                                     |
| --------------- | ---------------------------------- | ------------------------------------------------------------------------------------------- |
| `rows`, `cols`  | `int`                              | Dimensions derived from the character grid.                                                 |
| `start`, `goal` | `Cell`                             | Coordinates of the unique `S` and `G`; the `S` cell is stored as `FLOOR` in `grid`.         |
| `grid`          | `tuple[tuple[TileType, ...], ...]` | Parsed tile matrix.                                                                         |
| `grid_raw`      | `tuple[str, ...]`                  | Original JSON row strings (used by the HTTP adapter to re-emit `grid`).                     |
| `bridges`       | `tuple[dict[str, Any], ...]`       | Raw bridge metadata records in input JSON order; deep-validated when the `Engine` is built. |
| `switches`      | `tuple[dict[str, Any], ...]`       | Raw switch metadata records in input JSON order; deep-validated when the `Engine` is built. |
| `name`          | `str`                              | Level name; defaults to `""`.                                                               |
| `bridge_at`     | read-only `Mapping[Cell, Bridge]`  | Derived lookup from a bridge cell to its metadata (`Bridge`).                               |
| `switch_at`     | read-only `Mapping[Cell, Switch]`  | Derived lookup from a switch cell to its metadata (`Switch`).                               |

The metadata records are frozen dataclasses:

```python
@dataclass(frozen=True, slots=True)
class Bridge:
    id: str
    cell: Cell
    initial: str  # "open" or "closed"

@dataclass(frozen=True, slots=True)
class SwitchTarget:
    bridge: str
    mode: str  # "toggle", "permanent_open", or "permanent_closed"

@dataclass(frozen=True, slots=True)
class Switch:
    cell: Cell
    type: str  # "soft", "heavy", or "split"
    targets: tuple[SwitchTarget, ...] = ()
    split_cells: tuple[Cell, Cell] | None = None
```

`Board` methods:

- `in_bounds(cell: Cell) -> bool`
- `tile_at(cell: Cell) -> TileType` — raises `IndexError` if `cell` is out of bounds.

`TileType` (defined in `game/tiles.py`): `FLOOR` (`#`), `VOID` (`.`), `GOAL` (`G`), `FRAGILE` (`F`), `BRIDGE` (`B`), `SOFT_SWITCH` (`o`), `HEAVY_SWITCH` (`x`), `SPLIT_SWITCH` (`P`). The start char `S` maps to `FLOOR`.

Loader functions:

- `load_board(path: str | Path) -> Board` — reads and validates a JSON level file.
- `parse_board(data: dict) -> Board` — validates level data from a dict (used by tests).

`parse_board` validates grid shape/symbols and bridge/switch metadata against the grid: each `B` tile and each `o`/`x`/`P` tile must have exactly one matching metadata entry; bridge IDs must be unique; bridge references and target modes must be valid; and split destinations must be distinct in-bounds cells. Loader errors:

- `ValueError` — invalid grid, tile, start/goal count, bridge/switch metadata, or split destination.
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

- Approved wire/input format: character grid (`#`: floor, `.`: void, `S`: start, `G`: goal, `F`: fragile, `B`: bridge, `o`: soft switch, `x`: heavy switch, `P`: split switch) plus metadata lists `bridges`/`switches`. `game/board.py` parses and validates this format; `server.py` uses the resulting `Board`.
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
- `switches`: each entry has `cell` and `type` ∈ `{"soft","heavy","split"}`. `targets` is an optional list of `{"bridge", "mode"}` entries; if omitted it defaults to `[]`. Each mode is in `{"toggle","permanent_open","permanent_closed"}`. A `split` switch may omit `targets` or set it to `[]`, but cannot target bridges; it must provide `split_cells` (two cells). Non-split switches must not define `split_cells`.
- `bridges`/`switches` are validated against the grid by `parse_board`.

### 6.4 Advanced-Tile Behavior (implemented)

- Implemented by `game/engine.py` and its board/tile/switch helpers, and exposed through the HTTP layer.
- `FRAGILE`: unsupported under a standing block or single split cube; supported under a lying block. Fragile tiles do not persist damage.
- Ô `BRIDGE`: chỉ nâng đỡ khi mở.
- Công tắc `soft`, `heavy`, `split`: kích hoạt và cập nhật trạng thái cầu / tách khối.

### 6.5 TV2 Engine Mechanics

`Engine.transition()` owns the rules without changing the public wire API. The implementation separates geometry, support checks, and switch effects:

- `Engine._roll(position, orientation, action) -> tuple[Cell, Orientation] | None`: Pure geometry roll table for a standard block.
- `Engine._move_split_cube(state, action) -> tuple[State, str | None]`: Moves the active cube or reports an illegal collision/action.
- `support_failure(board, cells, orientation, bridge_states, split_mode) -> str | None` in `game/tiles.py`: Checks bounds and tile support.
- `activated_switches(board, state)` and `update_bridge_states(board, current, activated)` in `game/switches.py`: Resolve switch activation and apply bridge targets.
- `Engine._merge_if_adjacent(state) -> State`: Merges adjacent split cubes back into the standard block.

The engine applies switch effects deterministically: it inspects the resulting block's occupied cells in canonical `occupied_cells` order (in split mode, only the active cube's cell), then applies each switch's targets in their listed order. This also defines the order when multiple switches update the same bridge.

### 6.6 Core Rule Notes

- `legal_actions` checks `transition` for each `Action` in enum declaration order (`UP, DOWN, LEFT, RIGHT, SWITCH_CUBE`) and returns only actions whose result has `TransitionStatus.OK`; `FALL` and `ILLEGAL` are excluded. A goal state is not treated as terminal by this method.
- `SWITCH_CUBE` chỉ hợp lệ khi `split_mode == True`.
- Cơ chế nâng cao: `FRAGILE`, `BRIDGE`, switches (`soft`, `heavy`, `split`) đã được kích hoạt đầy đủ.

### 6.7 Stream Dependency Summary

| Stream                   | Can rely on now                                                       | Must wait for                        |
| ------------------------ | --------------------------------------------------------------------- | ------------------------------------ |
| TV2 (advanced mechanics) | Implemented Board loader, Engine transitions, and confirmed mechanics | —                                    |
| TV3 (BFS/DFS)            | Solver interface and stateless `/solve` request contract              | Solver modules and level set         |
| TV4 (UCS/A\*)            | Solver interface and `step_cost == 1.0` placeholder                   | Solver modules and final cost rule   |
| TV5 (GUI/integration)    | GUI, same-origin server, board/state/transition wire schema           | Solver outputs and final cost values |
