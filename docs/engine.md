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