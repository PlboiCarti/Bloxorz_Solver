# engine

- dùng python 3.12
- quản lí bằng uv cho python project
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
- `State.occupied_cells()` and the module-level `occupied_cells(state)` helper both return the occupied cells for all three orientations.
- `game/__init__.py` exports the public names: `Action`, `Board`, `BridgeStates`, `Cell`, `Engine`, `Orientation`, `State`, `TileType`, `load_board`, `occupied_cells`, `parse_board`.
- The level loader raises `ValueError` for grid/start/goal errors and `TypeError` for non-list `bridges`/`switches` or a non-object JSON root.
- An integration smoke test in `tests/test_transition.py` solves `levels/level1.json` with a BFS written inside the test, using only the Engine API.
