# TV1 — Core Game Engine: Implementation Guide for the Agent

> Audience: a coding agent (Gemini via opencode) working in this repository.
> Owner of this workstream: **TV1 (Core Engine)**. The human reviews and commits; the agent does not.
> Language: this guide and all docs are in English. **Code comments and docstrings are in Vietnamese.** Identifiers are in English.

---

## 0. Operating rules (read first, obey always)

1. **Work step by step.** The work is split into Steps 0–6 below. After each step: run that step's checks, report the result briefly, then **STOP and wait for the human to approve** before starting the next step.
2. **Do not assume.** If something is not specified here, in `AGENTS.md`, `GEMINI.md`, `docs/Mô tả công việc.md` or `docs/bloxorz_project_requirements.md`, stop and ask. Section 8 lists the open items and how to handle each.
3. **Check before creating.** Per `AGENTS.md`, the repo is a scaffold where most files are empty (0 bytes). Read a file before writing to it.
4. **Stay in scope.** Do not edit `gui/`, `solvers/`, `experiments/`, `.github/`, or any test file other than the ones named in this guide. Do not implement advanced mechanics (see Section 2).
5. **Do not run `git commit`, `git add`, `git push` or change branches.** The human commits.
6. **Dependencies.** Add them with `uv add` (use `--dev` for dev tools), then regenerate `requirements.txt` with `uv export --format requirements-txt > requirements.txt`. Never hand-edit `requirements.txt`.
7. **Decision log.** After implementing any project-wide decision, append **one short bullet line** to `docs/engine.md`. One decision per line, no paragraphs.
8. **Engine purity.** The engine uses only the Python standard library. No GUI, solver, or third-party imports in `game/`.
9. **Do not change interfaces** in Section 5 without the human's agreement.

---

## 1. Project context

Course project CSC14003 (Bloxorz AI Solver), Python 3.12, managed with `uv`. The team splits work into three streams that talk only through fixed interfaces:

```
GAME ENGINE (TV1 + TV2)  --Engine API-->  GUI + INTEGRATION (TV5, Three.js)
AI SOLVER   (TV3 + TV4)  --SearchResult-> GUI
Solver -> Engine API (legal_actions / transition / is_goal / step_cost)
```

Architecture principles (from `docs/Mô tả công việc.md`):

- The Engine is the **only** place that contains Bloxorz rules.
- Solvers never check tiles or switches themselves; they only call the Engine API.
- The GUI never updates block coordinates itself; every state change goes through `engine.transition()`.
- `State` must be hashable so solvers can use it in a visited set.

**This guide covers only TV1: the core engine.** TV2 extends the same engine for advanced mechanics.

---

## 2. Scope

### In scope (TV1)

- `Orientation` and `Action` enums.
- `State` (immutable, hashable, with dict export/import).
- `Board` and the JSON level loader/validator.
- `Engine`: `get_initial_state`, `legal_actions`, `transition`, `is_goal`, `step_cost`.
- Core rules only: floor, void, goal, three orientations, four rolling moves, falling detection, win detection.
- Placeholders/hooks so TV2 can plug in advanced mechanics **without restructuring** the engine.
- Tests for the core and the supporting docs.

### Out of scope (TV2 — do NOT implement)

- Fragile tiles, bridges, soft/heavy/split switches, toggle/permanent bridge behavior.
- Splitting into two cubes, active-cube control, merging.
- Designing or filling the 10 test levels (TV2 owns them).

### Files

| Owner | Files |
|---|---|
| **TV1 (you)** | `game/__init__.py`, `game/actions.py`, `game/state.py`, `game/board.py`, `game/engine.py`, `tests/test_transition.py`, `docs/api.md`, `docs/engine.md`, `levels/level1.json` (schema sample only), `pyproject.toml` (limited edits in Step 0), `requirements.txt` (via `uv export` only) |
| **TV2 (do not edit)** | `game/tiles.py`, `game/switches.py`, `game/split_block.py`, `tests/test_advanced_tiles.py`, `levels/level2.json` and any other level file |
| **Others (do not edit)** | `gui/`, `solvers/`, `experiments/`, other `tests/test_*.py`, `.github/`, `main.py` |

The `src/` directory is **removed** (decision: single package layout with top-level `game/`).

---

## 3. Fixed conventions

### 3.1 Coordinates

- A cell is `(row, col)`. Origin is the **top-left** of the grid. Row increases downward, col increases to the right.
- Type alias: `Cell = tuple[int, int]`.
- The block's `block_position` is its **anchor = the top-left occupied cell**.

### 3.2 Orientation and occupied cells

For a block at anchor `(r, c)`:

| Orientation | Occupied cells |
|---|---|
| `STANDING` | `(r, c)` |
| `HORIZONTAL` | `(r, c)`, `(r, c+1)` |
| `VERTICAL` | `(r, c)`, `(r+1, c)` |

### 3.3 Transition table (core rolls)

```
STANDING (r,c):
  UP    -> VERTICAL   anchor (r-2, c)
  DOWN  -> VERTICAL   anchor (r+1, c)
  LEFT  -> HORIZONTAL anchor (r,   c-2)
  RIGHT -> HORIZONTAL anchor (r,   c+1)

HORIZONTAL (r,c)  [occupies (r,c),(r,c+1)]:
  LEFT  -> STANDING   anchor (r,   c-1)
  RIGHT -> STANDING   anchor (r,   c+2)
  UP    -> HORIZONTAL anchor (r-1, c)
  DOWN  -> HORIZONTAL anchor (r+1, c)

VERTICAL (r,c)    [occupies (r,c),(r+1,c)]:
  UP    -> STANDING   anchor (r-1, c)
  DOWN  -> STANDING   anchor (r+2, c)
  LEFT  -> VERTICAL   anchor (r,   c-1)
  RIGHT -> VERTICAL   anchor (r,   c+1)
```

Implement this as a **data table** (a dict keyed by `(Orientation, Action)` giving the anchor delta and the new orientation), not as a chain of `if` statements.

### 3.4 Core rules

- A move is **illegal** (`transition` returns `None`) if any cell the block would occupy is outside the board or is a `VOID` cell. Falling is never a legal state; it is just an illegal move.
- The goal cell supports a lying block (it is a normal supporting cell). **Win** only when the block is `STANDING` exactly on the goal cell and not split. Lying across the goal is not a win.
- The start state is always `STANDING` on the start cell from the level file.
- `legal_actions(state)` returns the actions whose `transition` is not `None`, in this fixed order: `UP, DOWN, LEFT, RIGHT, SWITCH_CUBE`.
- `legal_actions` **still returns normal moves when `is_goal(state)` is true** (decision: solvers stop by calling `is_goal` themselves; the engine does not treat the goal as terminal).

---

## 4. Data model

### 4.1 `game/actions.py`

```python
class Action(Enum):
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    SWITCH_CUBE = "SWITCH_CUBE"   # chỉ hợp lệ khi đang ở chế độ split (TV2)

class Orientation(Enum):
    STANDING = "STANDING"
    HORIZONTAL = "HORIZONTAL"
    VERTICAL = "VERTICAL"
```

(`Orientation` may live in `state.py` if cleaner; keep it importable from `game`.)

`SWITCH_CUBE` exists in the enum now but is **never legal in the core**: with `split_mode == False`, `transition(state, SWITCH_CUBE)` returns `None`.

### 4.2 `game/state.py`

State is immutable and hashable: `@dataclass(frozen=True, slots=True)`. Fields (mirroring `docs/Mô tả công việc.md`):

| Field | Type | Core value |
|---|---|---|
| `block_position` | `Cell` | anchor cell |
| `orientation` | `Orientation` | |
| `bridge_states` | `BridgeStates` (see Section 8, item 1) | `()` in core |
| `split_mode` | `bool` | `False` |
| `cube1_position` | `Cell \| None` | `None` |
| `cube2_position` | `Cell \| None` | `None` |
| `active_cube` | `int \| None` (1 or 2) | `None` |

Requirements:

- Hashable and comparable by value. Every field must itself be hashable (use tuples, never lists/dicts).
- Helper `occupied_cells(state) -> tuple[Cell, ...]` for the non-split case, based on Section 3.2.
- JSON export for the Three.js GUI:
  - `State.to_dict() -> dict` returns only JSON-serializable values (lists for cells, enum **names** as strings). Shape:
    ```json
    {"block_position": [3, 4], "orientation": "STANDING", "bridge_states": [],
     "split_mode": false, "cube1_position": null, "cube2_position": null, "active_cube": null}
    ```
  - `State.from_dict(d) -> State` is the exact inverse. `from_dict(to_dict(s)) == s` must hold.

### 4.3 `game/board.py`

`Board` is immutable level data. Define a `TileType` enum **inside `board.py`** (do not touch `game/tiles.py`) with all level characters so the loader can parse full level files:

`FLOOR, VOID, GOAL, FRAGILE, BRIDGE, SOFT_SWITCH, HEAVY_SWITCH, SPLIT_SWITCH`

`Board` provides at least: `rows`, `cols`, `start: Cell`, `goal: Cell`, `tile_at(cell) -> TileType`, `in_bounds(cell) -> bool`, plus the parsed (but, in core, uninterpreted) `bridges` and `switches` data.

### 4.4 Level JSON format (**PROPOSAL — pending human review**, see Section 8, item 3)

The grid is an array of strings, one string per row, one character per cell.

| Char | Tile | Interpreted by TV1? |
|---|---|---|
| `#` | floor | yes |
| `.` | void | yes |
| `S` | start (floor) | yes |
| `G` | goal | yes |
| `F` | fragile | parsed only |
| `B` | bridge | parsed only |
| `o` | soft switch | parsed only |
| `x` | heavy switch | parsed only |
| `P` | split switch | parsed only |

Example:

```json
{
  "name": "level1",
  "grid": [
    "..###.....",
    "###S##....",
    "####.###..",
    "....#####.",
    ".....#G##."
  ],
  "bridges": [],
  "switches": []
}
```

Optional fields for advanced tiles (TV1 parses and stores them but does not interpret them):

```json
"bridges":  [{"id": "B1", "cell": [1, 4], "initial": "closed"}],
"switches": [{"cell": [2, 2], "type": "soft", "targets": [{"bridge": "B1", "mode": "toggle"}]}]
```

(`type` is `soft | heavy | split`; `mode` is `toggle | permanent_open | permanent_closed`; a split switch additionally has `"split_cells": [[r, c], [r, c]]`.)

Loader validation (raise `ValueError` with a clear message, in Vietnamese or English):

- Grid is non-empty and rectangular.
- Only characters from the table above.
- Exactly one `S` and exactly one `G`.
- `bridges`/`switches`, if present, are lists (deep validation belongs to TV2).

Provide `load_board(path) -> Board` and `parse_board(data: dict) -> Board` (the second one makes tests easy without files).

---

## 5. Engine API (fixed contract — do not change signatures)

```python
class Engine:
    def __init__(self, board: Board) -> None: ...
    def get_initial_state(self) -> State: ...
    def legal_actions(self, state: State) -> list[Action]: ...
    def transition(self, state: State, action: Action) -> State | None: ...
    def is_goal(self, state: State) -> bool: ...
    def step_cost(self, state: State, action: Action, next_state: State) -> float: ...
```

- `transition` is a **pure function**: it never mutates its input and never has side effects.
- `step_cost` returns `1.0` for now (final cost function is pending, Section 8 item 2).
- `legal_actions` is derived from `transition` (do not duplicate rule logic).

### 5.1 Extension hooks for TV2

`Engine.transition` must be structured so TV2 can extend the **same class** (by editing or subclassing) without rewriting it. Implement the core flow as small overridable methods:

```python
def _roll(self, state, action) -> tuple[Cell, Orientation] | None:
    """Áp dụng bảng chuyển đổi (Section 3.3). Không kiểm tra nền."""

def _cells_supported(self, state, cells) -> bool:
    """Core: mọi ô nằm trong bảng và không phải VOID.
    # TODO(TV2): fragile, bridge đóng/mở."""

def _apply_tile_effects(self, state, new_state) -> State:
    """Core: trả về new_state không đổi.
    # TODO(TV2): switch, bridge, split/merge."""
```

Flow inside `transition` (core): reject unsupported action (e.g. `SWITCH_CUBE`) -> `_roll` -> compute occupied cells -> `_cells_supported` -> build new `State` -> `_apply_tile_effects` -> return.

In the core, tiles `FRAGILE`, `BRIDGE` and the three switch types are **recognized by the loader but treated like plain floor** by `_cells_supported` / `_apply_tile_effects`, each marked with a `# TODO(TV2)` comment. Do not add any real advanced behavior.

---

## 6. Steps

### Step 0 — Preflight and tooling

**Do:**
1. Read `AGENTS.md`, `GEMINI.md`, `docs/Mô tả công việc.md`, `docs/bloxorz_project_requirements.md`, and check which files are empty. Report findings briefly.
2. Run `uv sync --dev`.
3. Remove the `src/` directory.
4. Edit `pyproject.toml` (this is the only allowed edit of the file):
   - Remove the `bloxorz-solver` package configuration that points at `src/bloxorz_solver/`. If `uv sync` then fails, set `package = false` under `[tool.uv]` and tell the human.
   - Add pytest config: `[tool.pytest.ini_options]` with `pythonpath = ["."]` and `testpaths = ["tests"]`.
   - Add `ruff` and `pyright` as dev dependencies via `uv add --dev ruff pyright`. Config: `[tool.ruff]` with only `target-version = "py312"` (default rules, no extra rules); `[tool.pyright]` with `pythonVersion = "3.12"`, `typeCheckingMode = "standard"`, `include = ["game", "tests"]`.
5. Regenerate `requirements.txt` with `uv export --format requirements-txt > requirements.txt`.
6. Append decision bullets to `docs/engine.md` (see Section 7).

**Checks:** `uv sync --dev` succeeds; `uv run pytest` runs (exit code 5 for "no tests" is acceptable at this point); `uv run ruff --version` and `uv run pyright --version` work.

**DoD:** `src/` gone, tooling configured, `requirements.txt` regenerated, no other files touched. **STOP.**

### Step 1 — Contract docs

**Do:** Write `docs/api.md` as the fixed contract: Engine API (Section 5), `State` fields and `to_dict` shape, `Action`/`Orientation`, the `SearchResult` shape from `docs/Mô tả công việc.md` (copy for reference only), and the integration principles. Keep it short and factual. Mark pending items (Section 8) as `PENDING` in the doc.

**Checks:** every signature in `docs/api.md` matches Section 5.

**DoD:** `docs/api.md` is readable by TV2/TV3/TV4/TV5 without opening the code. **STOP.**

### Step 2 — Actions and State

**Do:** implement `game/actions.py` and `game/state.py` (Section 4.1, 4.2). Export the public names from `game/__init__.py`.

**Tests** (put them in `tests/test_transition.py` under a `# --- State ---` section):
- two equal states compare equal and have equal hashes; different states differ
- usable as dict keys / in a `set`
- assigning to a field raises `FrozenInstanceError`
- `occupied_cells` is correct for all three orientations
- `from_dict(to_dict(s)) == s`, and `json.dumps(s.to_dict())` succeeds

**Checks:** `uv run pytest tests/test_transition.py -q`, `uv run ruff check game tests/test_transition.py`, `uv run pyright`.

**DoD:** all above pass, zero pyright errors in `game/`. **STOP.**

### Step 3 — Board and level loader

**Do:** implement `game/board.py` (Section 4.3, 4.4): `TileType`, `Board`, `parse_board`, `load_board`. Write `levels/level1.json` as a small core-only sample of the schema (do **not** touch other level files).

**Tests:**
- parse a valid grid: size, start, goal, tile types
- reject: empty grid, ragged rows, unknown char, zero or two `S`, zero or two `G`
- `load_board("levels/level1.json")` works
- `in_bounds` is correct at all four edges

**Checks:** as Step 2, plus the loader tests.

**DoD:** loader and validation pass, error messages are clear. **STOP.**

### Step 4 — Engine core

**Do:** implement `game/engine.py` (Section 5 and 5.1) using the data-table transition (Section 3.3).

**Tests (all on an open board, e.g. 12x12 all floor, block anchor at `(5, 5)`):**

| From | Action | Expected |
|---|---|---|
| STANDING (5,5) | UP | VERTICAL (3,5) |
| STANDING (5,5) | DOWN | VERTICAL (6,5) |
| STANDING (5,5) | LEFT | HORIZONTAL (5,3) |
| STANDING (5,5) | RIGHT | HORIZONTAL (5,6) |
| HORIZONTAL (5,5) | LEFT | STANDING (5,4) |
| HORIZONTAL (5,5) | RIGHT | STANDING (5,7) |
| HORIZONTAL (5,5) | UP | HORIZONTAL (4,5) |
| HORIZONTAL (5,5) | DOWN | HORIZONTAL (6,5) |
| VERTICAL (5,5) | UP | STANDING (4,5) |
| VERTICAL (5,5) | DOWN | STANDING (7,5) |
| VERTICAL (5,5) | LEFT | VERTICAL (5,4) |
| VERTICAL (5,5) | RIGHT | VERTICAL (5,6) |

Additional tests:
- off-board moves return `None` (test each edge and each orientation at least once)
- a move onto a `VOID` cell returns `None`, including a move where only one of the two cells is void
- `legal_actions` excludes illegal moves and keeps the order `UP, DOWN, LEFT, RIGHT`
- `is_goal`: standing on goal is true; lying horizontally or vertically across the goal is false; standing elsewhere is false
- a lying block can be supported on the goal cell (no win, no fall)
- `get_initial_state()` is STANDING at the start cell
- `legal_actions` still returns moves when the state is a goal state
- `transition(state, SWITCH_CUBE)` returns `None` in non-split mode
- `transition` does not mutate its input and is deterministic
- round trip: roll out and back (e.g. STANDING -> RIGHT -> LEFT) returns the original state
- `step_cost` returns `1.0`

**Checks:** `uv run pytest tests/test_transition.py -q`, `uv run ruff check .`, `uv run pyright`.

**DoD:** all 12 table cases and the edge cases pass; hooks exist with `# TODO(TV2)` markers; no advanced behavior implemented. **STOP.**

### Step 5 — Integration smoke test and docs

**Do:**
- Add one small integration test (in `tests/test_transition.py`): load `levels/level1.json`, use a plain BFS **written inside the test** (do not import `solvers/`) to confirm the goal is reachable using only the Engine API.
- Update `docs/api.md` and `docs/engine.md` so they match the final code.
- Run the full check suite once.

**Checks:** `uv run pytest -q`, `uv run ruff check .`, `uv run pyright`, `pre-commit run --config .github/pre-commit.yaml --all-files` (report failures; do not edit the config).

**DoD:** everything green; docs match code. **STOP.**

### Step 6 — Handover checklist

Report to the human (do not commit):

- [ ] Engine API exactly matches Section 5
- [ ] `State` is hashable, immutable, JSON round-trips
- [ ] 12 transition cases + edge cases pass
- [ ] Hooks for TV2 listed with file and method names
- [ ] `docs/api.md` and `docs/engine.md` up to date
- [ ] List of files created or changed, and the list of PENDING items (Section 8)

The human commits and then hands the engine to TV2 (advanced mechanics) and to TV3/TV4/TV5.

---

## 7. Decision log: initial bullets for `docs/engine.md`

Append these (one bullet per line; keep them short) in Step 0 and add more as decisions are made:

- Coordinates are `(row, col)`, origin top-left; block anchor is the top-left occupied cell.
- Orientation transitions are a data table keyed by `(Orientation, Action)`.
- Illegal moves (off-board or onto void) return `None` from `transition`; falling is never a state.
- The goal cell supports a lying block; win only when standing on the goal and not split.
- `legal_actions` is derived from `transition` and does not treat the goal as terminal.
- `Action` includes `SWITCH_CUBE`, which is never legal in the core.
- `State` is a frozen, slotted dataclass with `to_dict`/`from_dict` for the Three.js export.
- Level format is JSON with a grid as an array of strings; advanced tiles are parsed but not interpreted by TV1.
- `src/` is removed; the single package layout uses the top-level `game/`.
- Tooling: pytest with `pythonpath = ["."]`, ruff default rules, pyright `standard`; `requirements.txt` comes from `uv export`.
- `step_cost` returns `1.0` until the team fixes the cost function.

---

## 8. Open items (do not decide on your own)

1. **`bridge_states` representation** — not agreed with TV2. Use a provisional alias in `state.py`: `BridgeStates = tuple[bool, ...]`, indexed by bridge order in the level file, with a `# TODO(TV2): chốt kiểu biểu diễn` comment. Keep every use of the type behind the alias so it can be swapped in one place. Tell the human it is provisional.
2. **Cost function** — `step_cost` returns `1.0`. The non-uniform cost function for UCS/A* is pending. Do not invent weights.
3. **Level JSON schema** — Section 4.4 is a proposal. If the human changes it, update the loader, `docs/api.md` and `docs/engine.md` accordingly.
4. **Hook behavior for advanced tiles** — in the core, advanced tiles are treated as plain floor (Section 5.1). If the human prefers the loader to reject advanced tiles instead, change this in one place and log it.
5. Anything else not covered by this guide: stop and ask.
