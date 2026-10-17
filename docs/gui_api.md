# Bloxorz GUI & Integration — API Contract & Architecture Specifications

> **Target Audience:** TV5 (GUI & Integration), TV1/TV2 (Core & Advanced Engine), TV3/TV4 (AI Solvers).  
> **Status:** Approved Interface Contract for GUI implementation.

---

## 1. Architectural Principles & Responsibilities

1. **GUI Purity & Single Source of Truth:**
   - The GUI never computes block movement physics, collision, or game rules directly.
   - Every movement, switch trigger, bridge toggle, split/merge, or win/loss condition **must** be evaluated exclusively through `Engine.transition()` and `Engine.is_goal()`.
2. **Solver Decoupling:**
   - The GUI does not implement search algorithms. It triggers solvers via a standardized invocation contract and visualizes the resulting `SearchResult`.
3. **Non-blocking Search Execution:**
   - Solver execution must not block the UI render thread (e.g., using background worker threads, async tasks, or web workers).
4. **Deterministic Replay:**
   - Solver paths (`list[Action]`) are animated step-by-step through sequential `Engine.transition()` calls, maintaining a history stack for step-forward and step-backward (undo) navigation.

---

## 2. Directory Structure & Module Boundaries

The `gui` package lives at the top level of the repository:

```text
gui/
├── __init__.py      # Package export
├── app.py           # Application entrypoint & window / layout management
├── controller.py    # State machine, user input handling, replay logic
└── renderer.py      # Rendering engine (2D/3D viewport, board tiles, block meshes)
```

- **`gui/`** is owned exclusively by **TV5**.
- `main.py` at the repo root serves as the program launcher that initializes and starts `gui.app`.

---

## 3. Contract with Game Engine (`game`)

The GUI interacts with the Engine using public interfaces exported from `game`:

```python
from game import (
    Action,
    Board,
    Cell,
    Engine,
    Orientation,
    State,
    TileType,
    load_board,
    occupied_cells,
)
```

### 3.1 Level Loading & Initialization

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

### 3.2 State Data & Geometry Inspection

The GUI uses `State` properties and helper functions to render the block and interactive elements:

| State Property | Type | GUI Usage |
| :--- | :--- | :--- |
| `state.block_position` | `tuple[int, int]` | Anchor cell `(row, col)` (top-left occupied cell of block) |
| `state.orientation` | `Orientation` | `STANDING`, `HORIZONTAL` (along col), or `VERTICAL` (along row) |
| `occupied_cells(state)` | `tuple[Cell, ...]` | List of cells currently covered by the block (1 cell if standing, 2 if lying) |
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
  "bridge_states": [],
  "split_mode": false,
  "cube1_position": null,
  "cube2_position": null,
  "active_cube": null
}
```

### 3.3 Movement & Transition Handling

#### User Action Processing
```python
next_state: State | None = engine.transition(current_state, action)
```

1. **Valid Move (`next_state is not None`):**
   - Update `current_state = next_state`.
   - Check victory: `if engine.is_goal(current_state): trigger_win()`.
   - Animate the roll transition towards `next_state`.
2. **Invalid Move / Fall (`next_state is None`):**
   - Occurs when the block rolls off the board, lands on `VOID`, or stands upright on a `FRAGILE` tile.
   - GUI displays falling/defeat animation.
   - Prompt user to restart (`R`) or undo move.
3. **Legal Actions Hinting (Optional):**
   - Call `engine.legal_actions(current_state)` to get available valid actions `list[Action]`.

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

## 5. GUI Internal Architecture & Component Contracts

### 5.1 Game Controller (`gui/controller.py`)

Manages the gameplay state machine and bridges Engine and Renderer.

#### State Machine Modes:
- `MANUAL_PLAY`: User directly controls the block using keyboard.
- `SEARCHING`: Solver is executing in background; UI displays loading spinner/progress.
- `REPLAYING`: Solution path is automatically being stepped through with a timer.
- `REPLAY_PAUSED`: Replay paused; user can manually step forward/backward.
- `WON`: Block has reached goal; victory banner displayed.
- `LOST`: Block fell; defeat message displayed with restart option.

#### Key Controller Methods:
```python
class GameController:
    def __init__(self, level_path: str) -> None: ...
    def load_level(self, level_path: str) -> None: ...
    def restart_level(self) -> None: ...
    def handle_action(self, action: Action) -> bool: ...
    def undo_action(self) -> bool: ...
    def run_solver(self, algorithm_name: str) -> None: ...
    def start_replay(self) -> None: ...
    def pause_replay(self) -> None: ...
    def step_replay_forward(self) -> None: ...
    def step_replay_backward(self) -> None: ...
    def set_replay_speed(self, moves_per_second: float) -> None: ...
```

### 5.2 Renderer (`gui/renderer.py`)

Handles drawing the board, entities, and UI overlays.

```python
class Renderer:
    def render_board(self, board: Board, bridge_states: tuple[bool, ...]) -> None: ...
    def render_block(self, state: State) -> None: ...
    def render_fall_animation(self, state: State, action: Action) -> None: ...
    def render_victory_animation(self) -> None: ...
    def render_metrics(self, result: SearchResult) -> None: ...
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
| `Space` | `Action.SWITCH_CUBE` | Switch active cube (Split Mode only) |
| `R` | Restart | Reset stage to initial state |
| `U` / `Backspace` | Undo | Undo last move |
| `Space` (in replay) | Play / Pause | Toggle solution playback |

### 6.2 UI Control Panel Buttons

- **Stage Selector:** Dropdown listing available levels from `levels/*.json`.
- **Game Controls:** `New Game`, `Restart Level`, `Undo`.
- **Solver Buttons:** `Solve BFS`, `Solve DFS`, `Solve UCS`, `Solve A*`.
- **Replay Bar:** `⏮ First`, `◀ Step Back`, `▶ Play / ⏸ Pause`, `▶ Step Forward`, `⏭ Last`.
- **Speed Slider:** Adjust playback delay (e.g. `0.1s` to `1.0s` per step).

---

## 7. Replay Implementation Protocol

To guarantee that animations stay synchronized and never desync from the game rules:

```python
def play_solution_step(self) -> None:
    if self.replay_index >= len(self.solution_path):
        self.mode = Mode.WON
        return

    action = self.solution_path[self.replay_index]
    next_state = self.engine.transition(self.current_state, action)
    
    assert next_state is not None, f"Illegal move {action} at replay step {self.replay_index}"
    
    self.history.append(self.current_state)
    self.current_state = next_state
    self.replay_index += 1
    
    self.renderer.render_block(self.current_state)
    if self.engine.is_goal(self.current_state):
        self.mode = Mode.WON
```

---

## 8. Integration Verification & Smoke Tests

TV5 should verify GUI integration against:
1. `levels/level1.json` with manual keyboard navigation.
2. Running `solve_bfs` on `level1.json` and verifying that the replayed path ends with `engine.is_goal(final_state) == True`.
3. Fall animation trigger when rolling into `VOID`.
4. Split block control when level with split switches (`P`) is introduced.
