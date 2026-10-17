# Bloxorz Solver — API Contract & Architecture Specifications

> **Target Audience:** TV1 (Core Engine), TV2 (Advanced Mechanics), TV3 & TV4 (Solvers), TV5 (GUI & Integration).  
> **Status:** Stable contract for Core Engine (TV1). Specific items marked as `PENDING` await final team cross-stream agreement.

---

## 1. Architectural & Integration Principles

1. **Single Source of Truth:** The `Engine` is the **only** module that contains and enforces Bloxorz game rules.
2. **Solver Isolation:** Solvers never inspect tiles, switches, or board details directly. They interact with the game solely via the Engine API (`legal_actions`, `transition`, `is_goal`, `step_cost`).
3. **GUI Purity:** The GUI never manipulates block coordinates or game state directly. Every visual state change and replay step must be driven by `engine.transition()`.
4. **State Immutability & Hashability:** `State` instances are strictly immutable and hashable so solvers can safely use them in `visited` sets and priority queues.
5. **Uniform Solver Contract:** All search algorithms (BFS, DFS/IDS, UCS, A*) return the identical `SearchResult` data structure.

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

---

## 3. State Data Model

### 3.1 `State` Definition
```python
@dataclass(frozen=True, slots=True)
class State:
    block_position: tuple[int, int]
    orientation: Orientation
    bridge_states: tuple[bool, ...]  # [PENDING - Section 6.1]
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
- `[PENDING - Section 6.2]` Returns `1.0` by default in TV1.
- Provides edge weight / step cost for UCS and A*.

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

## 6. Pending Items & TV2 Extension Hooks

### 6.1 `bridge_states` Representation (`PENDING`)
- In TV1, `BridgeStates = tuple[bool, ...]` is defined as a provisional type alias in `game/state.py`.
- TV2 will finalize the exact indexing and data structure when implementing bridges.

### 6.2 Cost Function (`PENDING`)
- `step_cost` currently returns `1.0`.
- The non-uniform cost function for UCS and A* (e.g. differential costs for fragile tiles, switch toggles, or split cubes) will be specified by the team.

### 6.3 Level JSON Format (`PENDING`)
- Proposed format uses a character grid (`#`: floor, `.`: void, `S`: start, `G`: goal, `F`: fragile, `B`: bridge, `o`: soft switch, `x`: heavy switch, `P`: split switch) alongside metadata lists for `bridges` and `switches`.

### 6.4 TV2 Extension Hooks in `Engine`
TV1 provides modular extension methods within `Engine` so TV2 can integrate advanced tile logic without altering the public API:
- `_roll(state, action) -> tuple[Cell, Orientation] | None`: Pure geometry roll table.
- `_cells_supported(state, cells) -> bool`: Checks boundary and floor support.
- `_apply_tile_effects(state, new_state) -> State`: Applies switches, bridges, and split/merge effects.
