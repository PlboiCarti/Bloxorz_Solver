# Bloxorz GUI & Integration — API Contract & Architecture Specifications

> **Target Audience:** TV5 (GUI & Integration), TV1/TV2 (Core & Advanced Engine), TV3/TV4 (AI Solvers).  
> **Status:** Draft v1 — pending review by TV5 and TV1/TV2.

---

## 1. Architectural Principles & Responsibilities

1. **GUI Purity & Single Source of Truth:**
   - The GUI never computes block movement physics, collision, or game rules directly.
   - Every movement, switch trigger, bridge toggle, split/merge, or win/loss condition **must** be evaluated exclusively through `Engine.transition()` and goal validation.
2. **Solver Decoupling:**
   - The GUI does not implement search algorithms. It triggers solvers via a standardized invocation contract and visualizes the resulting `SearchResult`.
3. **Non-blocking Search Execution:**
   - Solver execution must not block the UI render thread (e.g., using background worker threads, async tasks, or web workers).
4. **Deterministic Replay:**
   - Solver paths (`list[Action]`) are animated step-by-step through sequential `Engine.transition()` calls, maintaining a history stack for step-forward and step-backward (undo) navigation.

---

## 2. Directory Structure & Module Boundaries

```text
game/                   # Python engine (owned by TV1/TV2)
solvers/                # AI solvers (owned by TV3/TV4)
web/
├── index.html
└── src/
    ├── main.js         # entrypoint: wires UI, controller, renderer
    ├── controller.js   # state machine (modes), replay logic, keyboard input
    ├── renderer3d.js   # Three.js scene: board tiles, block mesh, bridges, switches
    ├── api.js          # HTTP client for the Python backend
    └── ui.js           # control panel, replay bar, metrics panel
server.py               # FastAPI backend at repo root (owned by TV1/TV2)
levels/                 # shared level JSON files
```

`gui/` (Python placeholder) is removed; replaced by `web/`.  
GUI is owned by TV5 and written in JavaScript (Three.js). Algorithms and the engine remain in Python. The two sides communicate only through the HTTP endpoints in §2.1.

### 2.1 Backend HTTP API

| Method | Path | Body | Response |
| :--- | :--- | :--- | :--- |
| GET | /levels | — | `["level1.json", ...]` |
| GET | /levels/{name} | — | Board JSON + `initial_state` (State.to_dict format with `occupied_cells`) |
| POST | /transition | `{level, state, action}` | TransitionResult JSON (see §3.3) |
| POST | /solve | `{level, algorithm, state}` where algorithm ∈ {"BFS","DFS","UCS","ASTAR"} | SearchResult JSON (see §4.2) |

**Action Encoding:**  
`action` is one of the strings `"UP" | "DOWN" | "LEFT" | "RIGHT" | "SWITCH_CUBE"`. This encoding is shared across `POST /transition` (input), `POST /solve` (output path array), and client-side replay.

Every move is validated by POST /transition. The GUI never computes movement locally.

#### Board JSON Schema
```json
{
  "rows": int,
  "cols": int,
  "tiles": [[char]],
  "start": [row, col],
  "goal": [row, col]
}
```
bridges and switches: see owner spec (pending).

---

## 3. Contract with Game Engine (`game`)

> **Note:** Python-side only. The GUI consumes the JSON produced by these functions through §2.1. The Python signatures below serve as the backend's reference, labelled "(backend, Python)".

### 3.1 Level Loading & Initialization (backend, Python)

<!-- OWNER: bridge/switch spec pending (team lead) -->

```python
board: Board = load_board("levels/level1.json")
engine: Engine = Engine(board)
initial_state: State = engine.get_initial_state()
```

- **`board.rows`**, **`board.cols`**: Grid dimensions for setting up the camera/canvas.
- **`board.tile_at(cell: Cell) -> TileType`**: Query tile type at `(row, col)`.
  - Tile types: `FLOOR` (`#`), `VOID` (`.`), `GOAL` (`G`), `FRAGILE` (`F`), `BRIDGE` (`B`), `SOFT_SWITCH` (`o`), `HEAVY_SWITCH` (`x`), `SPLIT_SWITCH` (`P`).
- **`board.start`**, **`board.goal`**: Coordinates of the start cell and target goal hole.
- **`board.bridges`**, **`board.switches`**: Raw metadata tuples defining bridge and switch connections.

#### Board JSON Schema
```json
{
  "rows": int,
  "cols": int,
  "tiles": [[char]],
  "start": [row, col],
  "goal": [row, col]
}
```
bridges and switches: see owner spec (pending).

### 3.2 State Data & Geometry Inspection

The GUI uses `State` properties and helper functions to render the block and interactive elements. The GUI must not call `occupied_cells` directly; it reads the precomputed `occupied_cells` field from the JSON:

| State Property | Type | GUI Usage |
| :--- | :--- | :--- |
| `state.block_position` | `tuple[int, int]` | Anchor cell `(row, col)` (top-left occupied cell of block) |
| `state.orientation` | `Orientation` | `STANDING`, `HORIZONTAL` (along col), or `VERTICAL` (along row) |
| `occupied_cells` | `list[tuple[int, int]]` | read from JSON field (cells covered by the block) |
| `state.split_mode` | `bool` | `True` when block is split into two $1\times1\times1$ cubes |
| `state.cube1_position` | `Cell \| None` | Position of Cube 1 (when `split_mode == True`) |
| `state.cube2_position` | `Cell \| None` | Position of Cube 2 (when `split_mode == True`) |
| `state.active_cube` | `int \| None` | Which cube is currently controllable (`1` or `2`) |
| `state.bridge_states` | `tuple[bool, ...]` | Open (`True`) or closed (`False`) state of each bridge |

#### 3D / Web Serialization (`State.to_dict`)
For web-based or Three.js renderers, `state.to_dict()` provides JSON-serializable primitives:
```json
{
  "block_position": [3, 4],
  "orientation": "STANDING",
  "occupied_cells": [[3, 4]],
  "bridge_states": [],
  "split_mode": false,
  "cube1_position": null,
  "cube2_position": null,
  "active_cube": null
}
```

### 3.3 Movement & Transition Handling (backend, Python)

```python
result: TransitionResult = engine.transition(current_state, action)
```

```python
class TransitionStatus(str, Enum):
    OK = "ok"          # move applied
    FALL = "fall"      # block fell (VOID, off-board, or standing on FRAGILE)
    ILLEGAL = "illegal"  # action not allowed in this state; state unchanged

@dataclass(frozen=True)
class TransitionResult:
    status: TransitionStatus
    state: State | None        # set only when status == OK
    isGoal: bool               # goal check when status == OK, else False
    reason: str | None = None  # FALL: "void" | "off_board" | "fragile_standing"
                               # ILLEGAL: "switch_cube_not_split" | "action_not_allowed"
```

#### TransitionResult JSON Shape
```json
{
  "status": "ok",
  "state": {
    "block_position": [3, 4],
    "orientation": "STANDING",
    "occupied_cells": [[3, 4]],
    "bridge_states": [],
    "split_mode": false,
    "cube1_position": null,
    "cube2_position": null,
    "active_cube": null
  },
  "isGoal": false,
  "reason": null
}
```

#### User Action Processing
1. `status == "ok"` → `current_state = result.state`; animate roll; if `result.isGoal` → trigger win.
2. `status == "fall"` → play fall animation; show restart/undo prompt.
3. `status == "illegal"` → do NOT animate a fall; play a short "blocked" feedback (shake or flash); keep `current_state`.

#### Legal Actions Hinting (Optional)
- Call `engine.legal_actions(current_state)` to get available valid actions `list[Action]`.
- Note: `legal_actions` at a goal state still returns normal moves (this is intentional).

### 3.4 Move Cost

**Engine method (backend, Python):**
```python
def step_cost(self, state: State, action: Action) -> float: ...
```

**Behaviour:**
- Raises `ValueError` if `action` is illegal from `state`.
- Cost of a legal move = `tile_costs.get(destination_tile, 1.0)`, where `destination_tile` is the tile under the moved block's new cell(s) (for a split move, the moved cube's new cell). Destination is taken as the tile the moved cube or block ends up on.
- `SWITCH_CUBE` costs `switch_cost`, default `1.0`.
- `Board` may carry an optional `tile_costs: dict[TileType, float]`; if absent, all tiles cost `1.0`.

**Notes:**
- Default is uniform cost `1.0`. Costs may be re-weighted later; the interface does not change.
- `SearchResult.total_cost` = sum of `step_cost` over path. With uniform costs it equals `solution_length`.
- `step_cost` is called only for legal moves; solvers must check legality first.
- <!-- TODO: team to confirm cost table; ML weighting optional -->

**Solver Rules:**
- **BFS, DFS:** ignore cost during search; still report `total_cost` as the sum.
- **UCS:** priority $g$ = sum of `step_cost` from start.
- **A\*:** $f = g + h$. $h$ must be admissible. Use:
  ```python
  if not split_mode:
      h = min_step_cost * ceil(manhattan(anchor, goal) / 2)
  else:
      h = 0   # TODO: owner to confirm split-mode goal rule
  ```
  Justification: one roll changes the block's anchor by at most 2 cells in Manhattan distance.
- `min_step_cost` = min of `tile_costs` values (or `1.0` if none, and `switch_cost` if smaller).

---

## 4. Contract with AI Solvers (`solvers`)

### 4.1 Solver Invocation Interface

All solvers expose a uniform function signature:

```python
# solvers/bfs.py, solvers/dfs.py, solvers/ucs.py, solvers/astar.py
def solve(initial_state: State, engine: Engine) -> SearchResult: ...
```

Or via a unified solver dispatcher in `solvers/`:
```python
from solvers import solve_bfs, solve_dfs, solve_ucs, solve_astar

# Example call
result = solve_astar(current_state, engine)
```

### 4.2 `SearchResult` Data Schema

```python
@dataclass
class SearchResult:
    solved: bool
    path: list[Action]
    total_cost: float
    search_time: float      # in seconds (e.g. 0.042)
    memory_usage: float     # in MB (e.g. 12.4)
    expanded_nodes: int     # e.g. 350
    solution_length: int    # len(path), e.g. 28
```

### 4.3 Metrics Display Panel

Upon receiving `SearchResult`, the GUI updates the metrics sidebar:

| Metric Label | Source Field | Display Format |
| :--- | :--- | :--- |
| **Status** | `result.solved` | `Solved` (Green) / `No Solution` (Red) |
| **Algorithm** | Algorithm choice | `BFS` / `DFS` / `UCS` / `A*` |
| **Solution Length** | `result.solution_length` | Integer steps (e.g. `24 moves`) |
| **Total Cost** | `result.total_cost` | Float / Int (e.g. `24.0`) |
| **Execution Time** | `result.search_time` | Seconds (`{time:.4f} s` or `{time*1000:.1f} ms`) |
| **Memory Peak** | `result.memory_usage` | Megabytes (`{memory:.2f} MB`) |
| **Nodes Expanded** | `result.expanded_nodes` | Integer (`{nodes:,}`) |

---

## 5. GUI Internal Architecture & Component Contracts (JavaScript)

### 5.1 Game Controller (`web/src/controller.js`)

Manages the gameplay state machine, user inputs, and replay coordination.

#### State Machine Modes (String Constants):
- `"MANUAL_PLAY"`: User directly controls the block using keyboard.
- `"SEARCHING"`: Solver is executing in background; UI displays loading spinner/progress.
- `"REPLAYING"`: Solution path is automatically being stepped through with a timer.
- `"REPLAY_PAUSED"`: Replay paused; user can manually step forward/backward.
- `"WON"`: Block has reached goal; victory banner displayed.
- `"LOST"`: Block fell; defeat message displayed with restart option.
- `"ERROR"`: Replay or transition failed; message shown.

#### Key Controller Methods:
```javascript
// web/src/controller.js
export class GameController {
    constructor(api, renderer, ui) { ... }
    async loadLevel(levelName) { ... }
    async restartLevel() { ... }
    async handleAction(action) { ... }
    undoAction() { ... }
    async runSolver(algorithmName) { ... }
    startReplay() { ... }
    pauseReplay() { ... }
    stepReplayForward() { ... }
    stepReplayBackward() { ... }
    setReplaySpeed(movesPerSecond) { ... }
}
```

### 5.2 Renderer (`web/src/renderer3d.js`)

Handles the Three.js 3D scene, drawing board tiles, block meshes, bridges, switches, and animations.

```javascript
// web/src/renderer3d.js
export class Renderer3D {
    constructor(container) { ... }
    renderBoard(board, bridgeStates) { ... }
    renderBlock(state) { ... }
    renderFallAnimation(state, action) { ... }
    renderVictoryAnimation() { ... }
}
```

### 5.3 UI Components (`web/src/ui.js`)

Handles the control panel, replay bar, metrics display, and status notifications.

```javascript
// web/src/ui.js
export class UI {
    constructor() { ... }
    showMessage(message) { ... }
    renderMetrics(result) { ... }
}
```

---

## 6. User Controls & Keybindings

### 6.1 Keyboard Controls

| Key | Action | Description |
| :--- | :--- | :--- |
| `ArrowUp` / `W` | `Action.UP` | Roll block Up |
| `ArrowDown` / `S` | `Action.DOWN` | Roll block Down |
| `ArrowLeft` / `A` | `Action.LEFT` | Roll block Left |
| `ArrowRight` / `D` | `Action.RIGHT` | Roll block Right |
| `Space` | Multi-mode | `SWITCH_CUBE` in `MANUAL_PLAY` when split; Play/Pause in `REPLAYING` or `REPLAY_PAUSED` |
| `R` | Restart | Reset stage to initial state |
| `U` / `Backspace` | Undo | Undo last move |

*Note: API name `ASTAR` maps to display label `A*`.*

### 6.2 UI Control Panel Buttons

- **Stage Selector:** Dropdown listing available levels from `levels/*.json`.
- **Game Controls:** `New Game`, `Restart Level`, `Undo`.
- **Solver Buttons:** `Solve BFS`, `Solve DFS`, `Solve UCS`, `Solve A*`.
- **Replay Bar:** `⏮ First`, `◀ Step Back`, `▶ Play / ⏸ Pause`, `▶ Step Forward`, `⏭ Last`.
- **Speed Slider:** Adjust playback delay (e.g. `0.1s` to `1.0s` per step).

---

## 7. Replay Implementation Protocol (JavaScript)

To guarantee that animations stay synchronized and never desync from the game rules:

```javascript
async function playSolutionStep() {
    if (replayIndex >= path.length) {
        mode = "WON";
        return;
    }

    const action = path[replayIndex];
    const result = await api.transition(level, currentState, action);

    if (result.status !== "ok") {
        mode = "ERROR";
        ui.showMessage(`Replay failed at step ${replayIndex}: ${result.reason}`);
        return;
    }

    history.push(currentState);
    currentState = result.state;
    replayIndex++;

    renderer.renderBlock(currentState);
    if (result.isGoal) {
        mode = "WON";
    }
}
```

---

## 8. Integration Verification & Smoke Tests

TV5 should verify GUI integration against:
1. `levels/level1.json` with manual keyboard navigation.
2. POST /solve with algorithm BFS on `level1.json` (invoking backend `solve_bfs`) and verifying that the replayed path reaches the goal state.
3. Fall animation trigger when rolling into `VOID`.
4. Split block control when level with split switches (`P`) is introduced.

---

## 9. 3D Conventions

*(default, to be confirmed with team)*

- **World Mapping:** cell `(row, col)` → world `x = col`, `z = row`; `y` is up.
- **Block Dimensions & Placement:** Standing block sits on its tile; lying block spans two tiles.
- **Camera Viewport:** Camera frames the board using `board.rows` and `board.cols`.
- **Animation Speed:** Default roll animation duration: 0.3 s per move (configurable).

---

## Changelog

- v1 (2026-10-17): Switched GUI to Three.js web frontend; added HTTP API (§2.1); replaced transition() return type with TransitionResult (E3); added move cost and admissible heuristic rules (§3.4); algorithms BFS/DFS/UCS/A*.
- v2: fixes F1–F9 (isGoal, Action encoding, Board JSON, occupied_cells, renderMetrics location, ERROR mode, tree, Space binding, step_cost note).
