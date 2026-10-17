# Bloxorz Solver — API Contract & Architecture Specifications

> **Target Audience:** TV1 (Core Engine), TV2 (Advanced Mechanics), TV3 & TV4 (Solvers), TV5 (GUI & Integration).
> **Status:** Stable contract for Core Engine (TV1). Items marked `TEMPORARY` are confirmed placeholders awaiting future work; items marked `CONFIRMED` are decided (see Section 6).

---

## 1. Architectural & Integration Principles

1. **Single Source of Truth:** The `Engine` is the **only** module that contains and enforces Bloxorz game rules.
2. **Solver Isolation:** Solvers never inspect tiles, switches, or board details directly. They interact with the game solely via the Engine API (`legal_actions`, `transition`, `is_goal`, `step_cost`).
3. **GUI Purity:** The GUI never manipulates block coordinates or game state directly. Every visual state change and replay step must be driven by `engine.transition()`.
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
    bridge_states: tuple[bool, ...]  # [TEMPORARY - Section 6.1]
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
    def transition(self, state: State, action: Action) -> State | None: ...
    def is_goal(self, state: State) -> bool: ...
    def step_cost(self, state: State, action: Action, next_state: State) -> float: ...
```

### 4.1 Method Specifications

#### `get_initial_state() -> State`

- Returns the initial state of the stage.
- Block orientation is `Orientation.STANDING`.
- Anchor is at the board's designated start cell `S`.

#### `legal_actions(state: State) -> list[Action]`

- Returns a list of actions where `transition(state, action)` does not evaluate to `None`.
- Fixed deterministic ordering: `[Action.UP, Action.DOWN, Action.LEFT, Action.RIGHT, Action.SWITCH_CUBE]`.
- Goal states are **not** treated as terminal by `legal_actions`: legal moves continue to be generated if the block can roll from that position. Solvers check `is_goal(state)` themselves.

#### `transition(state: State, action: Action) -> State | None`

- **Pure function:** Never mutates `state` or internal board structures; has no side effects.
- Returns the resulting successor `State` if the move is legal.
- Returns `None` if the move is illegal (e.g. block rolls off-board or any occupied cell lands on `VOID`).
- Falling is not represented as an active state.

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

### 6.1 `bridge_states` Representation (`TEMPORARY — owner: TV2`)

- `BridgeStates = tuple[bool, ...]` is a provisional alias in `game/state.py`; kept as-is until TV2 implements bridges.
- TV2 finalizes the indexing/representation and updates this section plus `docs/engine.md` when it does.
- Until then, all other streams treat `State.bridge_states` as an opaque hashable tuple (`()` in core) — do not inspect its contents outside TV2 code.

### 6.2 Cost Function (`TEMPORARY — owner: team, consumed by TV4`)

- `step_cost` returns `1.0`; this placeholder is confirmed.
- BFS/DFS (TV3) are unaffected. UCS/A\* (TV4) must not invent weights; they wait for the team's final cost specification.
- When agreed, change `Engine.step_cost` in one place and update this doc.

### 6.3 Level JSON Format (`CONFIRMED`)

- Approved and implemented in `game/board.py` as proposed: character grid (`#`: floor, `.`: void, `S`: start, `G`: goal, `F`: fragile, `B`: bridge, `o`: soft switch, `x`: heavy switch, `P`: split switch) plus metadata lists `bridges`/`switches`.
- TV2 owns the other level files; every level must use this schema so it stays reusable across all solvers.
- If the schema ever changes, the loader, this doc, and `docs/engine.md` change together.

### 6.4 Advanced-Tile Behavior in Core (`CONFIRMED`)

- TV1 parses `FRAGILE`, `BRIDGE` and switch tiles but treats them as plain floor; only `VOID` and off-board cells block a move (the loader does not reject advanced tiles).
- TV2 replaces this behavior behind the hooks in 6.5 without changing the public Engine API.

### 6.5 TV2 Extension Hooks in `Engine`

TV1 provides modular extension methods within `Engine` so TV2 can integrate advanced tile logic without altering the public API:

- `_roll(state, action) -> tuple[Cell, Orientation] | None`: Pure geometry roll table.
- `_cells_supported(state, cells) -> bool`: Checks boundary and floor support (`# TODO(TV2)` for fragile/bridge).
- `_apply_tile_effects(state, new_state) -> State`: Applies switches, bridges, and split/merge effects (`# TODO(TV2)`; core returns `new_state` unchanged).

The split-mode/`SWITCH_CUBE` early exits in `transition` also carry `# TODO(TV2)` markers in `game/engine.py`.

### 6.6 Core Rule Notes

- `legal_actions` checks `transition` for each action in the fixed order `UP, DOWN, LEFT, RIGHT, SWITCH_CUBE` and returns those that are not `None`.
- `SWITCH_CUBE` always returns `None` in TV1 (`split_mode == False`).
- TV1 treats `FRAGILE`, `BRIDGE`, and switch tiles as plain floor; only `VOID` and off-board cells block a move.

### 6.7 Stream Dependency Summary

| Stream                   | Can rely on now                                                                                | Must wait for                                        |
| ------------------------ | ---------------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| TV2 (advanced mechanics) | Public Engine API, hooks (6.5), parsed `bridges`/`switches` on `Board`, `BridgeStates` alias   | Final `bridge_states` representation (6.1, TV2 owns) |
| TV3 (BFS/DFS)            | Full Engine API, `step_cost == 1.0`, level schema (6.3)                                        | —                                                    |
| TV4 (UCS/A\*)            | Full Engine API, level schema (6.3)                                                            | Final cost function (6.2)                            |
| TV5 (GUI/integration)    | `State.to_dict` shape, `engine.board`, level schema (6.3), `SearchResult` contract (Section 5) | Solver outputs and final cost values                 |
