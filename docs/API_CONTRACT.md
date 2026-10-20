# Bloxorz GUI & Integration — API Contract & Architecture Specifications

> **Target Audience:** TV5 (GUI & Integration), TV1/TV2 (Core & Advanced Engine), TV3/TV4 (AI Solvers).
> **Status:** GUI/backend wire contract. TV2 advanced-tile semantics and the `TransitionResult` response are confirmed. `server.py` exposes the HTTP adapter; the Python engine API is documented in `docs/api.md`.

---

## 1. Architectural Principles & Responsibilities

1. **GUI Purity & Single Source of Truth:**
   - The GUI never computes block movement physics, collision, or game rules directly.
   - Every movement, switch trigger, bridge toggle, split/merge, or win/loss condition **must** be evaluated exclusively through the backend endpoints (§2.1), which call `Engine.transition()` / `Engine.is_goal()`.
   - GUI-side geometry is allowed only to interpolate animations between states returned by the engine; it must never decide legality, landing cells, or victory.
2. **Solver Decoupling:**
   - The GUI does not implement search algorithms. It calls /solve and replays the returned path through sequential /transition requests; Python remains authoritative for every step.
3. **Non-blocking Search Execution:**
   - `POST /solve` runs off the async event loop in a worker thread. At the 10-second deadline, the server returns `504` and signals cooperative cancellation; search and H2 loops check that signal at checkpoints (§4.3).
4. **Deterministic Replay:**
   - The GUI sends a returned path (`list[Action]`) step-by-step through sequential `POST /transition` calls, with history for step-forward and step-backward navigation (§7).
5. **Stateless Backend, Client-owned Session:**
   - `/transition` and `/solve` keep no server-side session or hidden state: every request carries the level name and the full current state.
   - The GUI owns the only game session: `currentState`, snapshot `history`, `initialState`, replay index (§7). There is no server undo/reset endpoint; `GET /levels/{name}` always returns a fresh `initial_state`.
6. **No Transition Events:**
   - The backend does not send an animation event list. The GUI derives movement animation from `(previous state, action, TransitionResult)`. A `fall_state` may provide rejected geometry for the fall animation only; it is never committed as game state (§3.3).

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

The tree above is the target modular layout. The current GUI is consolidated in `gui/index.html` with inline JavaScript; it is owned by TV5 and uses Three.js. Algorithms and the engine remain in Python. The two sides communicate through the HTTP endpoints in §2.1, and the current server serves the GUI and `/assets/*` from the same origin.

**Repository implementation note (2026-10-20):** `server.py` implements the FastAPI adapter, including `/transition` and `/solve`, and serves `gui/index.html` plus `/assets/*`. It serializes board/state data and transition results using this wire contract. BFS, DFS, UCS, and A* are registered in the server. The current GUI exposes algorithm selection, calls `/solve`, displays search metrics, and replays the returned actions through sequential `/transition` calls.

### 2.1 Backend HTTP API

Default base URL `http://127.0.0.1:8000`; routes have **no `/api` prefix**. JSON in, JSON out (UTF-8).

| Method | Path | Request Body | Success Response |
| :--- | :--- | :--- | :--- |
| GET | `/levels` | — | `["level1.json", ...]` |
| GET | `/levels/{name}` | — | `{"board": {...}, "initial_state": {...}}` (§3.1–3.2) |
| POST | `/transition` | `{"level": name, "state": {...}, "action": "UP"}` | `TransitionResult` JSON (§3.3) |
| POST | `/solve` | `{"level": name, "algorithm": "BFS", "state": {...}}` | `SearchResult` JSON (§4.2) |

The same-origin GUI entry point is `GET /`; static game assets are served from `/assets/*`.

Rules:

- `{name}` is a level file name **including** the `.json` extension, exactly as returned by `GET /levels`. Names never contain path separators or `..`; an unknown or malformed name is `404`.
- `GET /levels` lists only files that `load_board` accepts, so every listed name is guaranteed loadable (invalid/placeholder files are skipped by the server).
- `GET /levels` sorts names naturally, so numbered levels appear as `level1`, `level2`, …, `level10`.
- `GET /levels/{name}` returns the parsed board plus a **fresh** `initial_state`. The GUI uses it both to load a level and to reset it; no separate reset endpoint exists.
- `/transition` and `/solve` are stateless: level, board and state are validated from each request; nothing is cached between requests.
- The backend validates `level`, `state` and `action`; failures follow §2.2.
- `action` is one of `"UP" | "DOWN" | "LEFT" | "RIGHT" | "SWITCH_CUBE"`. This encoding is shared by `/transition` requests, `SearchResult.path`, and client-side replay.
- `algorithm` is one of `"BFS" | "DFS" | "UCS" | "ASTAR"`; API name `ASTAR` maps to display label `A*`.
- Application outcomes of a move (`ok`, `fall`, `illegal`) are always HTTP `200`; they are game results, not HTTP errors.
- **CORS:** the current development server serves `gui/index.html` and the API from the same origin, so CORS is not needed for the supported local workflow. A split-origin deployment must configure an explicit CORS allow-list.
- Request bodies are small (a state is a few hundred bytes); the server may reject bodies above a small configurable limit (default 256 KB) with `400 REQUEST_TOO_LARGE`.
- Every response carries the full state; the client never merges partial deltas.

### 2.2 HTTP Error Contract

Every non-2xx response body is JSON; the GUI can parse every body unconditionally.

```json
{
  "error": {
    "code": "LEVEL_NOT_FOUND",
    "message": "Level does not exist."
  }
}
```

| Status | Example codes | When |
| :--- | :--- | :--- |
| `400` | `INVALID_JSON`, `INVALID_FIELD`, `INVALID_ACTION`, `UNKNOWN_ALGORITHM`, `REQUEST_TOO_LARGE`, `INVALID_LEVEL` | Malformed request, illegal value, or invalid level data |
| `404` | `LEVEL_NOT_FOUND`, `NOT_FOUND` | Unknown level or route |
| `422` | `INVALID_STATE` | Well-formed JSON but not a valid state for the given board (e.g. anchor outside the grid) |
| `500` | `INTERNAL_ERROR` | Unexpected server error; never leaks stack traces or secrets |
| `504` | `SOLVER_TIMEOUT` | Search exceeded the time budget (§4.3) |

- `fall` and `illegal` move outcomes are **not** HTTP errors (HTTP 200, §3.3).
- `500` responses use a generic message; details go to the server log only.

---

## 3. Contract with Game Engine (`game`)

> **Note:** Python-side only. The GUI consumes the JSON produced by these functions through §2.1. The Python signatures below serve as the backend's reference, labelled "(backend, Python)".

### 3.1 Level Loading & Board Object (backend, Python)

```python
board: Board = load_board("levels/level1.json")
engine: Engine = Engine(board)
initial_state: State = engine.get_initial_state()
```

`GET /levels/{name}` response:

```json
{
  "board": {
    "name": "level1",
    "rows": 5,
    "cols": 10,
    "grid": ["..###.....", "###S##....", "####.###..", "....#####.", ".....#G##."],
    "start": [1, 3],
    "goal": [4, 6],
    "bridges": [],
    "switches": []
  },
  "initial_state": {
    "block_position": [1, 3],
    "orientation": "STANDING",
    "bridge_states": [],
    "split_mode": false,
    "cube1_position": null,
    "cube2_position": null,
    "active_cube": null
  }
}
```

> The complete **input level-file** format (`name`/`grid`/`bridges`/`switches`, plus how `start`/`goal` are derived) with a full example is specified in `docs/api.md` §6.3.

- `grid` uses the level file characters (equal-length rows); `rows`, `cols`, `start` and `goal` are derived so the GUI never searches the grid. (`Board.grid` internally maps `S` to `FLOOR`; the `start` field identifies the start cell.)
- `start`/`goal` are inside the board; `goal` is the unique `G` tile.
- Loader validation surfaces as request errors: equal-length rows, valid characters, exactly one `S` and one `G`; `bridges`/`switches` must be lists.
- Tile symbols (case-sensitive):

| Char | `TileType` | Meaning |
| :--- | :--- | :--- |
| `#` | `FLOOR` | Normal floor |
| `.` | `VOID` | Hole; moving onto it is a fall |
| `S` | `FLOOR` | Start cell (see `start`) |
| `G` | `GOAL` | Goal tile |
| `F` | `FRAGILE` | TV2: breaks / drops the block when standing |
| `B` | `BRIDGE` | TV2: bridge tile controlled by switches |
| `o` | `SOFT_SWITCH` | TV2: soft switch |
| `x` | `HEAVY_SWITCH` | TV2: heavy switch |
| `P` | `SPLIT_SWITCH` | TV2: splits the block |

Coordinates everywhere in the API are `[row, col]`, origin top-left, row downward, col rightward (3D mapping in §9).

#### Bridge & Switch Metadata — CONFIRMED (2026-10-17)

The GUI must never infer bridge/switch relationships from tile order or tile count; all links are explicit:

```json
{
  "bridges": [
    { "id": "bridge_a", "cell": [1, 2], "initial": "closed" }
  ],
  "switches": [
    { "cell": [1, 1], "type": "soft",  "targets": [ { "bridge": "bridge_a", "mode": "toggle" } ] },
    { "cell": [2, 0], "type": "split", "split_cells": [[2, 1], [2, 3]] }
  ]
}
```

| Object | Field | Type | Required | Meaning |
| :--- | :--- | :--- | :--- | :--- |
| bridge | `id` | string | yes | Unique per bridge entry |
| bridge | `cell` | `[row, col]` | yes | The `B` grid cell this entry controls (one entry per `B` tile) |
| bridge | `initial` | `"open" \| "closed"` | yes | Initial state (`open` = passable) |
| switch | `cell` | `[row, col]` | yes | Must equal the grid tile position |
| switch | `type` | `"soft" \| "heavy" \| "split"` | yes | Must match the grid char (`o` / `x` / `P`) |
| switch | `targets` | `[{ "bridge": id, "mode": ... }, ...]` | no; defaults to `[]` | Bridges affected on activation |
| switch | `targets[].mode` | `"toggle" \| "permanent_open" \| "permanent_closed"` | yes per target | Effect applied to that bridge |
| switch | `split_cells` | `[[row, col], [row, col]]` | yes for `split` | The two cells where the cubes appear after the split |

Validation rules (loader):

- One bridge entry per `B` grid tile: every `B` tile has exactly one entry with that `cell`, and no two entries share a cell.
- Every `o` / `x` / `P` grid tile has exactly one switch entry with the same `cell` and matching `type`, and vice versa.
- `id`s are unique; all cells are in bounds; `initial` ∈ `{"open", "closed"}`; each target's `bridge` must exist; `mode` ∈ `{"toggle", "permanent_open", "permanent_closed"}`.
- `targets` may be omitted for any switch and defaults to `[]`; if supplied, it must be an array. Split switches may not have any bridge targets.
- `split` requires `split_cells` (two distinct in-bounds cells); non-`split` switches must not define `split_cells`.
- `bridges`/`switches` are `[]` when the level has none; `parse_board` validates their metadata against the grid and raises `ValueError` for mismatches before an `Engine` is constructed.
- `bridge_states` follows `bridges` order: `bridge_states[i]` ↔ `bridges[i].id`, initialized from `initial` (§3.2).

#### Switch Activation & Bridge Effects — CONFIRMED (2026-10-17)

| Switch | Triggers when | Effect |
| :--- | :--- | :--- |
| `soft` (`o`) | After a move, any **occupied cell** is the switch cell (any orientation; in split mode the active cube's cell counts) | Apply each target's `mode` to its bridge |
| `heavy` (`x`) | After a move the state is a **non-split `STANDING`** block exactly on the switch cell | Same |
| `split` (`P`) | After a move the state is a **non-split `STANDING`** block exactly on the switch cell | Teleport + split to `split_cells` (§3.3); never affects bridges |

- `toggle` flips each linked bridge; `permanent_open` sets it open (`true`); `permanent_closed` sets it closed (`false`).
- If one move activates multiple switches, inspect the resulting non-split block's occupied cells in their canonical `occupied_cells` order (standing: anchor; horizontal: left cell then right cell; vertical: top cell then bottom cell). Apply each activated switch's targets in the order listed in that switch's `targets` array. In split mode, inspect only the active cube's cell. This ordering determines the result when multiple effects update the same bridge.
- An open bridge is floor; a **closed bridge is unsupported** like a void cell (fall reason `bridge_closed`).
- In split mode only the **active** cube's cell is checked, so a stationary cube does not re-press a switch; a split cube can trigger `soft` only, never `heavy` or `split`.

#### Fragile Support — CONFIRMED (2026-10-17)

- A lying block (`HORIZONTAL` / `VERTICAL`) is supported by `FRAGILE` tiles.
- A `STANDING` block or a single split cube on `FRAGILE` falls (`fragile_standing`).
- Fragile tiles never change state: there is no persistent damage and no `broken_tiles` field (§3.2).

### 3.2 State Data & Geometry Inspection

The GUI renders from the state JSON returned by `/transition` and `GET /levels/{name}`. `occupied_cells` is an internal Python geometry helper and is not part of the HTTP state schema. The GUI places the block from `block_position` and `orientation`, and places split cubes from their individual positions.

| State field | Type | GUI usage |
| :--- | :--- | :--- |
| `block_position` | `[row, col]` | Anchor = top-left occupied cell; in split mode = the active cube's cell |
| `orientation` | `"STANDING" \| "HORIZONTAL" \| "VERTICAL"` | `HORIZONTAL` = along a row, `VERTICAL` = along a column; in split mode always `STANDING` |
| `bridge_states` | `[bool, ...]` | Bridge open (`true`) / closed (`false`); index `i` ↔ `board.bridges[i].id` |
| `split_mode` | `bool` | Block is split into two 1×1×1 cubes |
| `cube1_position` / `cube2_position` | `[row, col] \| null` | Cube positions when `split_mode == true` |
| `active_cube` | `1 \| 2 \| null` | Controllable cube when `split_mode == true` |

**State JSON shape (HTTP):**

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

Semantics and guarantees:

- The HTTP state uses seven fields: `block_position`, `orientation`, `bridge_states`, `split_mode`, `cube1_position`, `cube2_position`, and `active_cube`. Unused cube fields must be explicit `null` values. The server derives occupied cells from the parsed Python `State` and validates that the derived cells are inside the board. Unknown extra request fields are ignored.
- `State.occupied_cells()` remains an internal Engine helper. Its canonical order is `STANDING` → `[(r,c)]`; `HORIZONTAL` → `[(r,c),(r,c+1)]`; `VERTICAL` → `[(r,c),(r+1,c)]`; split states return cube 1 then cube 2. It is used by Engine rules and backend validation, not sent over HTTP or handled by the GUI.
- Tuples serialize as JSON arrays `[row, col]`, never as strings.
- `split_mode == false`: `cube1_position`, `cube2_position` and `active_cube` are `null`; `block_position`/`orientation` describe the whole block.
- `split_mode == true` (CONFIRMED): `block_position` mirrors the active cube's cell and `orientation` is `STANDING`; `active_cube` is `1` or `2`.
- **Merge (CONFIRMED):** after a cube move, if the two cubes occupy orthogonally adjacent cells they merge into the standard block: `HORIZONTAL` when they share a row, `VERTICAL` when they share a column, anchor = the top-left of the two cells, `split_mode = false`, cube fields `null`.
- **Goal (CONFIRMED):** a split state can never win; the cubes must merge and the block must stand on `G` (`is_goal` requires `not split_mode`).
- `bridge_states` CONFIRMED representation: exactly one entry per bridge in `board.bridges`, in the same order, initialized from `initial`, including bridges that have not changed state (`[]` when the level has no bridges). `State.to_dict/from_dict`, `docs/api.md` and this section change together if it ever changes.
- The server rejects a state with a missing required field as `400 INVALID_FIELD`; malformed or inconsistent state data is `422 INVALID_STATE`. `bridge_states` must contain exactly one boolean per board bridge. Every occupied cell must be inside the board. In split mode, `block_position` must equal the position of `active_cube`; the two cube positions must be distinct, and `orientation` must be `STANDING`. Outside split mode, both cube positions and `active_cube` must be `null`.
- There is **no `status` field and no `broken_tiles` field** in the state. The engine has no won/lost state and fragile tiles are non-persistent by design (§3.1): `WON`/`LOST` are GUI modes only (§3.3), a fall never mutates the board, and re-entering a fragile cell behaves the same every time (`fragile_standing`).
- Round-trip guarantee (backend): any state the server emitted can be posted back and equals its Python `State` after `from_dict`.

### 3.3 Movement & Transition Handling (backend, Python)

```python
# game/engine.py — exported from `game`
result: TransitionResult = engine.transition(current_state, action)
```

```python
class TransitionStatus(str, Enum):
    OK = "ok"            # move applied
    FALL = "fall"        # block or split cube fell: VOID, off-board, closed bridge, or standing on FRAGILE
    ILLEGAL = "illegal"  # action not allowed from this state; state unchanged

@dataclass(frozen=True)
class TransitionResult:
    status: TransitionStatus
    state: State | None   # the resulting state; set only when status == OK
    is_goal: bool         # engine.is_goal(state) when status == OK, else False
    reason: str | None = None
    fall_state: State | None = None  # rejected geometry for fall animation only
```

HTTP JSON encoding: `status` (lowercase), `state` (State JSON or `null`), `fall_state` (attempted State JSON or `null`), `isGoal` (camelCase), `reason`. On `fall`, `state` stays `null`; `fall_state` is rejected target geometry for animation only and must never update the GUI's logical state. On `ok` and `illegal`, `fall_state` is `null`.

`reason` values (lowercase, fixed):

| Status | `reason` | Meaning |
| :--- | :--- | :--- |
| `fall` | `void` | A cell the block/cube would occupy is `VOID` |
| `fall` | `off_board` | A cell the block/cube would occupy is outside the grid |
| `fall` | `bridge_closed` | A cell the block/cube would occupy is a closed `BRIDGE` |
| `fall` | `fragile_standing` | A `STANDING` block or a single cube lands on `FRAGILE` |
| `illegal` | `switch_cube_not_split` | `SWITCH_CUBE` while `split_mode == false` |
| `illegal` | `cube_collision` | In split mode, a cube would move into the other cube's cell |
| `illegal` | `action_not_allowed` | Any other disallowed action |

Precedence when several apply: `off_board` → `void` → `bridge_closed` → `fragile_standing`. With TV2 advanced mechanics implemented, all fall/illegal reasons above apply; the plain-core engine (TV1 only) produced only `switch_cube_not_split`.

#### TransitionResult JSON — `ok`

(`RIGHT` from the `level1` start: standing at `(1,3)`.)

```json
{
  "status": "ok",
  "state": {
    "block_position": [1, 4],
    "orientation": "HORIZONTAL",
    "bridge_states": [],
    "split_mode": false,
    "cube1_position": null,
    "cube2_position": null,
    "active_cube": null
  },
  "fall_state": null,
  "isGoal": false,
  "reason": null
}
```

#### TransitionResult JSON — `fall`

(From `HORIZONTAL` at anchor `(1,4)`, `RIGHT` would land on `VOID`.)

```json
{
  "status": "fall",
  "state": null,
  "fall_state": {
    "block_position": [1, 6],
    "orientation": "STANDING",
    "bridge_states": [],
    "split_mode": false,
    "cube1_position": null,
    "cube2_position": null,
    "active_cube": null
  },
  "isGoal": false,
  "reason": "void"
}
```

#### TransitionResult JSON — `illegal`

(`SWITCH_CUBE` while not in split mode.)

```json
{
  "status": "illegal",
  "state": null,
  "fall_state": null,
  "isGoal": false,
  "reason": "switch_cube_not_split"
}
```

#### User Action Processing

1. `status == "ok"` → push the current state to `history`; `currentState = result.state`; animate the roll; if `result.isGoal` → enter `WON`.
2. `status == "fall"` → do **not** change `currentState` or `history`; animate toward `fall_state` if supplied, then drop through that unsupported cell; enter `LOST`. `fall_state` is never committed and the GUI does not infer the failed destination from game rules.
3. `status == "illegal"` → do not animate movement/fall; play a short "blocked" feedback (shake or flash); keep `currentState`.

Additional rules:

- `WON`/`LOST` are **GUI modes**. The engine does not treat the goal as terminal (`transition` still returns `ok` for rolls from the goal), so the GUI must lock input itself in `WON`/`LOST`.
- **Split mode (CONFIRMED):** the active cube moves like a 1×1 cube; a move that ends unsupported is a `fall` (either cube falling loses the stage); a move into the other cube's cell is `illegal` (`cube_collision`); cubes merge automatically when adjacent (§3.2).
- Undo and restart are client-side and valid in every mode, including after a `fall` and after `WON` (§7).
- **Split switch (CONFIRMED):** when a non-split `STANDING` block lands exactly on a `P` cell, the block is teleported and split: cube 1 → `split_cells[0]`, cube 2 → `split_cells[1]`, `active_cube = 1`, `split_mode = true`. Both destination cells must be supported under the current bridge states; otherwise the result is a `fall` with the destination's reason.
- **`SWITCH_CUBE` (CONFIRMED):** legal only when `split_mode == true`; it flips `active_cube` (1 ↔ 2) and updates `block_position` to the newly active cube's cell. Neither cube moves. It counts as one step in `history`, `SearchResult.path`, `solution_length`, and `step_cost`.
- **Transition events: not used** (§1.6). The optional `fall_state` is rejected geometry for presentation, not a game-state event.

#### Transition Pipeline — CONFIRMED (order matters)

1. Compute the rolled geometry (active cube move when `split_mode == true`).
2. If any resulting occupied cell is off-board → `fall` (`off_board`).
3. Support check under the **current** bridge states: `VOID` → `void`; closed `BRIDGE` → `bridge_closed`; `STANDING` block/cube on `FRAGILE` → `fragile_standing`.
4. Apply tile effects in this order: inspect the resulting occupied cells in canonical `occupied_cells` order (split mode: active cube only), activate each switch found and apply its targets in listed order → update bridge states → split-switch teleport/split or cube merge.
5. Re-check support after bridge updates: if a bridge that just closed is under the block/cubes → `fall` (`bridge_closed`).
6. Otherwise `ok`.

#### Legal Actions Hinting (Optional)

- The backend may expose `engine.legal_actions(state)` for UI hints; there is no endpoint for it in v1. `legal_actions` does **not** treat the goal as terminal.
- The GUI never pre-filters input by local rules; an illegal action is answered by the server.

### 3.4 Move Cost and A* Heuristic

```python
def step_cost(self, state: State, action: Action, next_state: State) -> float: ...
```

- Current code defaults (`game/cost_config.py`): `stand_roll=1.5`, `lie_roll=1.0`, and `switch_cube=0.1`; `bridge_cross_penalty=0.3` is not currently applied. These values still need team confirmation.
- `CostConfig` rejects negative or non-finite values because UCS/A* require non-negative edge costs.
- `total_cost` = sum of `step_cost` over the path; with these non-unit costs it may differ from `solution_length`.
- **BFS, DFS:** ignore cost during search; still report `total_cost` as the sum.
- **UCS:** priority `g` = sum of `step_cost` from start.
- **A\*:** `f = g + h`. The current implementation uses precomputed, cost-aware H2 by default. It keeps roll geometry/orientation and static VOID topology, relaxes fragile/bridge effects, and can include split cube-pair states. Engine passes static inputs through `HeuristicContext`.

  H2 runs reverse Dijkstra over the relaxed abstract graph. The branch enables `split_aware=True`, so split states use the abstract cube-pair distance instead of the older `h=0` fallback. Treat admissibility/consistency as requiring verification against the final transition and cost semantics; do not claim solver optimality until that review is complete.

---

## 4. Contract with AI Solvers (`solvers`)

### 4.1 Solver Invocation Interface

All solvers expose a uniform function signature:

```python
# solvers/bfs.py, solvers/dfs.py, solvers/ucs.py, solvers/astar.py
def solve(initial_state: State, engine: Engine) -> SearchResult: ...
```

Or via the unified dispatcher in `solvers/`:

```python
from solvers import solve_bfs, solve_dfs, solve_ucs, solve_astar

result = solve_astar(current_state, engine)
```

### 4.2 `SearchResult` Data Schema

```python
@dataclass
class SearchResult:
    solved: bool
    path: list[Action]
    total_cost: float
    search_time: float      # seconds (e.g. 0.042)
    memory_usage: float     # MB, peak (e.g. 12.4)
    expanded_nodes: int     # e.g. 350
    solution_length: int    # len(path), e.g. 28
    preprocessing_time: float = 0.0  # H2 build time; 0 for other solvers
```

`POST /solve` returns this object **directly** (no `result` envelope):

```json
{
  "solved": true,
  "path": ["RIGHT", "DOWN", "SWITCH_CUBE"],
  "total_cost": 3.0,
  "search_time": 0.042,
  "memory_usage": 12.4,
  "expanded_nodes": 350,
  "solution_length": 3,
  "preprocessing_time": 0.0
}
```

Rules:

- `path` contains action strings (§2.1); `solution_length == len(path)`. `SWITCH_CUBE` entries are legal by construction.
- `solved == false` means "search exhausted, no solution exists": `path: []`, `solution_length: 0`, `total_cost: 0.0`; metrics are still reported.
- `search_time` = solver search plus path/result construction; A* H2 construction is reported separately in `preprocessing_time` (0 for BFS/DFS/UCS or injected heuristics). Solver-side elapsed time is `search_time + preprocessing_time`.
- `memory_usage` = peak traced MB during the solver call. Measurement is serialized because `tracemalloc` is process-global; an H2 cache built by an earlier call is already allocated before the next measurement. If an external profiler already owns tracing, this field is `0` (unavailable).
- `expanded_nodes` = popped non-goal states whose successors were generated. Goal states are not counted, including an initial state that is already the goal.
- All metrics are finite JSON numbers — never `NaN`, `Infinity`, or `null`; an unavailable metric is `0`.
- Solving starts from the `state` sent in the request (usually the current GUI state).

### 4.3 `POST /solve` — Non-blocking & Timeouts

- The endpoint returns `SearchResult` when the worker finishes, or `504 SOLVER_TIMEOUT` when `SOLVE_TIMEOUT_SECONDS` (default `10`) is reached. On timeout or client cancellation, the server sets a cancellation event; solver and H2 loops stop at their next checkpoint.
- The backend runs the solver in a worker thread so the async event loop stays responsive; the GUI `fetch` is asynchronous and the UI thread stays free (spinner + `SEARCHING` mode).
- Unknown algorithm → `400 UNKNOWN_ALGORITHM`. The current server registers BFS, DFS, UCS, and ASTAR. The GUI submits the selected algorithm and current state to this route.

### 4.4 Metrics Display Panel

Upon receiving `SearchResult`, the GUI updates the metrics sidebar:

| Metric Label | Source Field | Display Format |
| :--- | :--- | :--- |
| **Status** | `result.solved` | `Solved` (Green) / `No Solution` (Red) |
| **Algorithm** | Algorithm choice | `BFS` / `DFS` / `UCS` / `A*` |
| **Solution Length** | `result.solution_length` | Integer steps (e.g. `24 moves`) |
| **Total Cost** | `result.total_cost` | Float / Int (e.g. `24.0`) |
| **Execution Time** | `result.search_time` | Seconds (`{time:.4f} s` or `{time*1000:.1f} ms`) |
| **H2 Preprocessing** | `result.preprocessing_time` | Seconds; shown separately from A* search |
| **Memory Peak** | `result.memory_usage` | Megabytes (`{memory:.2f} MB`) |
| **Nodes Expanded** | `result.expanded_nodes` | Integer (`{nodes:,}`) |

---

## 5. GUI Internal Architecture & Component Contracts (JavaScript)

### 5.1 Game Controller (`web/src/controller.js`)

Manages the gameplay state machine, user inputs, and replay coordination. It owns the session state: `currentState`, `initialState`, `history`, `path`, `replayIndex`, `mode` (§7).

#### State Machine Modes (String Constants):
- `"MANUAL_PLAY"`: User directly controls the block using keyboard.
- `"SEARCHING"`: Solver is executing in the backend; UI displays a loading spinner.
- `"REPLAYING"`: Solution path is automatically being stepped through with a timer.
- `"REPLAY_PAUSED"`: Replay paused; user can manually step forward/backward.
- `"WON"`: Block has reached goal; victory banner displayed.
- `"LOST"`: Block fell; defeat message displayed with restart/undo options.
- `"ERROR"`: Replay or transition failed; message shown with the failing step and reason.

#### Key Controller Methods:
```javascript
// web/src/controller.js
export class GameController {
    constructor(api, renderer, ui) { ... }
    async loadLevel(levelName) { ... }      // load + reset: sets initialState, clears history
    async restartLevel() { ... }
    async handleAction(action) { ... }
    undoAction() { ... }
    async runSolver(algorithmName) { ... }
    startReplay() { ... }
    pauseReplay() { ... }
    stepReplayForward() { ... }
    stepReplayBackward() { ... }
    jumpToStart() { ... }
    jumpToEnd() { ... }
    setReplaySpeed(movesPerSecond) { ... }
}
```

### 5.2 Renderer (`web/src/renderer3d.js`)

Handles the Three.js 3D scene, drawing board tiles, block meshes, bridges, switches, and animations. All positions come from state JSON; meshes interpolate between the previous and the returned state.

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
| `Space` | Multi-mode | `SWITCH_CUBE` in `MANUAL_PLAY` **only when `split_mode == true`**; Play/Pause in `REPLAYING` / `REPLAY_PAUSED` |
| `R` | Restart | Reset to `initialState` and clear history |
| `U` / `Backspace` | Undo | Undo one step (client-side, §7) |

- Movement keys are ignored while `SEARCHING` / `REPLAYING`; the user must pause or wait.
- Undo and Restart work in every mode, including `LOST` and `WON`.
- API name `ASTAR` maps to display label `A*`.

### 6.2 UI Control Panel Buttons

- **Stage Selector:** Dropdown listing available levels from `GET /levels`.
- **Game Controls:** `New Game`, `Restart Level`, `Undo` (exact semantics in §7.1).
- **Solver Buttons:** BFS, DFS, UCS and A*; enabled when the level/API is ready.
- **Replay Bar and Speed Slider:** control returned-path playback; each forward step is validated through /transition.

---

## 7. Replay, History & Undo (Client-owned)

### 7.1 Session & History Rules

- `history` is a stack of **state snapshots** owned by the controller; the backend is stateless and has no undo endpoint.
- Before applying an `ok` result: `history.push(currentState)`, then `currentState = result.state`.
- `fall` / `illegal` push nothing and never change `currentState` (the server did not change the logical state either).
- **Undo** = pop from `history` and re-render; it is allowed at any time (after `fall`, after `WON`, paused replay, manual play).
- **Restart** = set `currentState = initialState`, clear `history`, reset `replayIndex`, enter `MANUAL_PLAY`. `initialState` is cached from `GET /levels/{name}` (or refetched).
- **New Game** (control panel) = start the level selected in the Stage Selector fresh: fetch `GET /levels/{name}`, replace `board`/`initialState`, clear `history`, solver result and metrics, reset `replayIndex`, enter `MANUAL_PLAY`. It differs from **Restart** only by re-fetching the level; both are client-side resets with no server write.
- Replay step-forward calls `POST /transition` with `path[replayIndex]` (the same code path as manual play, so history stays consistent); step-backward is a local `history` pop (no server call).
- If any replay step returns `fall` or `illegal`: stop the replay, enter `ERROR`, show the step index and `reason`; never continue the path.
- A legal `SWITCH_CUBE` counts as a normal step: recorded in `history`, counted in `solution_length`, and priced by `step_cost`.

### 7.2 Replay Loop (reference implementation)

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
        ui.showMessage(`Replay failed at step ${replayIndex + 1}: ${result.reason}`);
        return;   // path must not continue
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

Contract smoke tests (each test states the request and expected response; some need TV2/TV3/TV4/backend code first):

1. `GET /levels` returns a non-empty list; every listed name loads through `GET /levels/{name}`.
2. Board object: `rows`/`cols` match `grid`, `start`/`goal` are valid, exactly one `S` and one `G`; all chars are in the §3.1 table.
3. `initial_state` conforms to §3.2 (seven state fields and null cube fields outside split mode).
4. Transition `ok` updates position, orientation, and `bridge_states`.
5. Transition `illegal` keeps `state: null` and the client state unchanged; an illegal action is never mistaken for a fall.
6. Transition `fall` returns `state: null`, the correct `reason`, and rejected geometry in `fall_state`; GUI animates into the trap then enters `LOST`; `history`/`currentState` unchanged.
7. Advanced tiles (TV2, implemented): `P` teleport/split, `SWITCH_CUBE`, cube movement/merge, soft/heavy activation rules, closed-bridge fall (`bridge_closed`), fragile-standing fall (`fragile_standing`) — all visible in the result state.
8. Solver integration check: each registered algorithm returns a schema-conform `SearchResult`; replay each solved path through `POST /transition` and verify the final state is the goal. The GUI follows this sequence; this contract check still needs to be run.
9. Error contract (§2.2): no solution, unknown algorithm, solver not available, malformed request, unknown level, timeout — every body is JSON with `error.code`.
10. Undo/replay: state stays in sync after each step; replay stops at the first non-`ok` step; Undo works after `fall` and after `WON`.

---

## 9. 3D Conventions

*(default, to be confirmed with team)*

- **World Mapping:** cell `(row, col)` → world `x = col`, `z = row`; `y` is up.
- **Block Dimensions & Placement:** standing block sits on its tile; lying block spans two tiles. Render from `block_position` and `orientation` (or individual split-cube positions); never compute a game transition in JS.
- **Camera Viewport:** Camera frames the board using `board.rows` and `board.cols`.
- **Animation Speed:** Default roll animation duration: 0.3 s per move (configurable). Fall animation: ~0.5 s.
- **Fall animation:** animate to rejected `fall_state` geometry and drop through the unsupported cell (presentation only; the server already decided the `fall`).

---

## 10. Open Items

| Item | Owner | Status |
| :--- | :--- | :--- |
| `TransitionResult` as the Python Engine return type | TV1/TV2 | Implemented in `game/`; HTTP adapter emits the contract result |
| Bridge/switch metadata schema; `bridge_states` representation; split-mode state semantics | TV2 | Implemented by `game/board.py`, `game/engine.py`, and the HTTP adapter |
| Cost function for UCS/A\* (`step_cost`) | team | Current defaults 1.5/1.0/0.1; confirm final semantics (`docs/api.md` §6.2) |
| `server.py` FastAPI backend (endpoints, worker thread, timeout) | TV1/TV2 | `/transition` and `/solve` routes, worker execution, and timeout are implemented |
| BFS/DFS/UCS/A\* solver modules | TV3/TV4 | Present and registered; cost/heuristic semantics still require team confirmation before relying on UCS/A* results |
| Solver/replay GUI controls | TV5 | Integrated with /solve and sequential /transition replay |
| Static serving vs CORS decision | TV5/lead | Same-origin static serving implemented; cross-origin deployment needs explicit CORS configuration |

---

## Changelog

- v9 (2026-10-20): documented cooperative solve cancellation and metric semantics; added `preprocessing_time` to the SearchResult wire schema.
- v8 (2026-10-20): enabled GUI solver selection and connected /solve to replay through /transition.
- v7 (2026-10-20): synchronized solver_v2 H2, recorded current weighted costs and the need to confirm H2 guarantees; preserved fall_state compatibility.
- v6 (2026-10-20): natural level ordering; added visual-only `fall_state` so the GUI drops into the rejected trap cell without committing it; recorded that solver/replay UI is disabled.
- v5 (2026-10-17): records the running `gui/index.html` + standard-library server layout, implemented HTTP wire serialization/validation, same-origin serving, and the remaining internal Engine/FastAPI/solver work.
- v4 (2026-10-17): TV2 semantics finalized, no TV2 assumptions left. Added: bridge/switch metadata schema + loader validation + switch activation/bridge effect rules + fragile support (§3.1); split-mode state/merge/goal rules (§3.2); transition pipeline + new reasons `bridge_closed`/`cube_collision` + split-switch/`SWITCH_CUBE` rules (§3.3); A\* split heuristic fixed at `h = 0` (§3.4). Updated Space binding, smoke test 7 and open items.
- v3 (2026-10-17): Incorporates TV5 review feedback. Decided: `Engine.transition()` returns `TransitionResult` (implementation pending); `POST /solve` is synchronous with a hard timeout (no job API); `bridge_states` stays an ordered array pending TV2. Added: official endpoint/state-lifecycle rules (§2.1), HTTP error contract (§2.2), full board/tile/bridge/switch schema (§3.1), state JSON semantics (§3.2), `ok`/`fall`/`illegal` examples and reason table (§3.3), solve timeout/501 rules (§4.3), history/undo rules + New Game/Restart semantics (§7), split-mode fall note (§3.3), expanded smoke tests (§8), open items (§10).
- v2: fixes F1–F9 (isGoal, Action encoding, Board JSON, occupied_cells, renderMetrics location, ERROR mode, tree, Space binding, step_cost note).
- v1 (2026-10-17): Switched GUI to Three.js web frontend; added HTTP API (§2.1); replaced transition() return type with TransitionResult (E3); added move cost and admissible heuristic rules (§3.4); algorithms BFS/DFS/UCS/A*.
