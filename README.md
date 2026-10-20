# Bloxorz AI Solver

Đồ án **CSC14003 — Introduction to Artificial Intelligence**: mô phỏng trò
chơi Bloxorz và giải màn chơi bằng BFS, DFS, UCS và A*. Dự án dùng Python 3.12,
quản lý môi trường bằng `uv`, và sử dụng layout package ở thư mục gốc (`game/`,
`solvers/`), không có `src/`.

README này mô tả implementation hiện tại trong working tree. Engine, các solver,
HTTP adapter và bộ kiểm thử đã có; GUI, entrypoint `main.py` và phần benchmark
chưa được triển khai.

## Trạng thái hiện tại

| Thành phần | Trạng thái | Nội dung |
| --- | --- | --- |
| Game Engine | Hoàn thành | Core movement, goal, fragile, bridge, soft/heavy/split switch, split/merge |
| BFS / DFS | Hoàn thành | Graph search, parent map, path reconstruction, metrics |
| UCS / A* | Hoàn thành | Priority queue, chi phí từ `Engine.step_cost`, H2 mặc định và heuristic injectable |
| HTTP adapter | Hoàn thành | FastAPI: levels, transition, solve, validation và error envelope |
| Levels | Hoàn thành | 10 màn JSON, từ core đến màn kết hợp toàn bộ cơ chế |
| Tests | Hoàn thành | Unit, advanced mechanics, solver, integration và HTTP tests |
| GUI | Chưa triển khai | `gui/app.py`, `gui/controller.py`, `gui/renderer.py` đang rỗng |
| Entrypoint | Chưa triển khai | `main.py` đang rỗng |
| Experiments | Chưa triển khai | `experiments/*.py` và `results.csv` đang rỗng |

Các tài liệu yêu cầu và phân chia module còn lại ở `docs/`. File
`docs/deep-research-report.md` và `docs/h2 heuristic research.md` là các tài liệu
nghiên cứu heuristic. H2 split-safe hiện đã được nối vào A*. Một số tài liệu contract lịch sử như
`docs/api.md`, `docs/gui_api.md`, `docs/index.md`, `docs/status.md` và
`docs/engine.md` hiện không có trong working tree; README này không tạo lại hoặc
giả định các file đó tồn tại.

## Mục tiêu và kiến trúc

Engine là nguồn sự thật duy nhất của luật chơi. Solver chỉ gọi Engine API và
không tự đọc tile, switch hoặc board internals. HTTP adapter chuyển dữ liệu JSON
giữa client và Engine/Solver. GUI trong tương lai sẽ dùng chính HTTP contract
hoặc Engine API để render và replay.

```text
Level JSON
    │
    ▼
Board + LevelMechanics ───────┐
    │                         │
    ▼                         │
Engine ── transition() ──► State / TransitionResult
    │                         │
    └── legal_actions()       │
                              ▼
                    BFS / DFS / UCS / A*
                              │
                              ▼
                         SearchResult

FastAPI server.py cung cấp các đối tượng trên qua HTTP JSON.
```

Phân chia module:

- `game/`: board, state, luật di chuyển và cơ chế nâng cao.
- `solvers/`: bốn thuật toán tìm kiếm và schema kết quả chung.
- `server.py`: adapter FastAPI không trạng thái.
- `levels/`: dữ liệu màn chơi tái sử dụng cho Engine, solver và server.
- `tests/`: kiểm thử từ state/transition đến HTTP và toàn bộ level.
- `gui/`, `main.py`, `experiments/`: khung dành cho phần tích hợp đang chờ triển khai.

## Cài đặt và chạy nhanh

Các lệnh sau chạy từ PowerShell trong VS Code:

```powershell
Get-Location
uv sync --dev
uv run pytest -q
uv run ruff check .
uv run pyright
```

Nếu cần chạy một nhóm test:

```powershell
uv run pytest tests/test_transition.py -q
uv run pytest tests/test_advanced_tiles.py -q
uv run pytest tests/test_server.py -q
```

Khởi động HTTP adapter:

```powershell
uv run python server.py
```

Server lắng nghe tại `http://127.0.0.1:8000`. FastAPI cũng cung cấp OpenAPI
interactive docs tại `/docs` và schema tại `/openapi.json`. Vì GUI chưa có
`gui/index.html`, endpoint `/` hiện trả lỗi `404 NOT_FOUND` cho tới khi GUI được
triển khai.

Runtime dependencies được khai báo trong `pyproject.toml`:

- `fastapi`: HTTP API.
- `uvicorn`: ASGI server.

Development dependencies:

- `pytest`, `httpx`: test suite và FastAPI `TestClient`.
- `ruff`: lint.
- `pyright`: type checking.

`uv.lock` cố định dependency graph; `requirements.txt` là file export tự động,
không nên chỉnh tay.

## Mô hình game

### Board và level JSON

Mỗi level là một JSON object với các trường:

```json
{
  "name": "level1",
  "grid": ["..###.....", "###S##...."],
  "bridges": [],
  "switches": []
}
```

`grid` phải là ma trận ký tự chữ nhật, có đúng một `S` và một `G`:

| Ký tự | Ý nghĩa |
| --- | --- |
| `#` | Sàn bình thường |
| `.` | Void, không nâng đỡ block |
| `S` | Start, được lưu như sàn |
| `G` | Goal |
| `F` | Fragile tile |
| `B` | Bridge |
| `o` | Soft switch |
| `x` | Heavy switch |
| `P` | Split switch |

`parse_board(data)` kiểm tra grid, ký tự, start/goal và kiểu của hai metadata
list. `load_board(path)` đọc JSON rồi gọi parser. Khi tạo `Engine`,
`build_mechanics()` kiểm tra sâu metadata:

- Mỗi `B` phải có đúng một bridge record với `id`, `cell` và `initial` là
  `open` hoặc `closed`.
- Bridge ID phải duy nhất; target phải trỏ tới bridge tồn tại.
- Mỗi `o`/`x`/`P` phải có switch record đúng `cell` và đúng `type`.
- Mode target là `toggle`, `permanent_open` hoặc `permanent_closed`.
- Split switch phải có đúng hai `split_cells` khác nhau trong board; switch khác
  không được khai báo `split_cells`.

Các level hiện có:

| Level | Nội dung chính |
| --- | --- |
| `level1` | Màn core mẫu |
| `level2`, `level3` | Core path/corridor nâng dần độ khó |
| `level4`, `level5` | Fragile tiles |
| `level6` | Soft switch và toggle bridge |
| `level7` | Heavy switch permanent bridge và soft toggle bridge |
| `level8` | Split và merge |
| `level9` | Split kết hợp soft switch và bridge |
| `level10` | Kết hợp fragile, bridge, heavy/soft/split switch; màn lớn nhất |

### State

`State` là dataclass `frozen=True, slots=True`, immutable và hashable để dùng
trong `visited`, `dict` và priority queue:

```python
from game import Orientation, State

state = State(
    block_position=(1, 3),
    orientation=Orientation.STANDING,
    bridge_states=(),
    split_mode=False,
    cube1_position=None,
    cube2_position=None,
    active_cube=None,
)
```

Quy ước tọa độ là `(row, col)`, gốc ở góc trên trái. `block_position` là anchor
ở ô chiếm phía trên-trái:

- `STANDING`: `(r, c)`.
- `HORIZONTAL`: `(r, c)`, `(r, c+1)`.
- `VERTICAL`: `(r, c)`, `(r+1, c)`.

`occupied_cells()` trả về các ô đang bị chiếm. Trong split mode, state luôn có
`orientation=STANDING`, `cube1_position`, `cube2_position`, `active_cube` và
`block_position` bằng vị trí cube đang được điều khiển. Hai cube được trả về
theo thứ tự cube 1 rồi cube 2.

`State.to_dict()`/`State.from_dict()` dùng list tọa độ và tên enum để giao tiếp
JSON. `to_dict()` không tự thêm `occupied_cells`; server bổ sung trường dẫn xuất
này vào wire format.

### Action và transition

```python
from game import Action, Engine, TransitionStatus

engine = Engine(board)
result = engine.transition(state, Action.RIGHT)

if result.status is TransitionStatus.OK:
    next_state = result.state
```

`Action` có thứ tự cố định:

```text
UP, DOWN, LEFT, RIGHT, SWITCH_CUBE
```

Bảng lăn core:

| Hướng hiện tại | Action | Hướng mới | Anchor mới |
| --- | --- | --- | --- |
| Standing | Up | Vertical | `(r-2, c)` |
| Standing | Down | Vertical | `(r+1, c)` |
| Standing | Left | Horizontal | `(r, c-2)` |
| Standing | Right | Horizontal | `(r, c+1)` |
| Horizontal | Left | Standing | `(r, c-1)` |
| Horizontal | Right | Standing | `(r, c+2)` |
| Horizontal | Up/Down | Horizontal | `(r-1,c)` / `(r+1,c)` |
| Vertical | Up | Standing | `(r-1, c)` |
| Vertical | Down | Standing | `(r+2, c)` |
| Vertical | Left/Right | Vertical | `(r,c-1)` / `(r,c+1)` |

`Engine.transition()` là hàm thuần túy và trả về:

```python
@dataclass(frozen=True, slots=True)
class TransitionResult:
    status: TransitionStatus  # OK, FALL hoặc ILLEGAL
    state: State | None       # chỉ có giá trị khi OK
    is_goal: bool
    reason: str | None
```

- `OK`: action hợp lệ và `state` là trạng thái mới.
- `FALL`: block rơi, không tạo state hoạt động.
- `ILLEGAL`: action không hợp lệ trong state hiện tại.

Các `reason` hiện dùng là `off_board`, `void`, `bridge_closed`,
`fragile_standing`, `action_not_allowed`, `switch_cube_not_split` và
`cube_collision`. `legal_actions()` tự thử transition theo đúng thứ tự action,
chỉ giữ kết quả `OK`; goal không làm Engine trở thành terminal state. Solver tự
gọi `is_goal()` để dừng.

Điều kiện thắng là block nguyên vẹn (`split_mode=False`) ở `STANDING` đúng trên
ô `G`. Block nằm ngang/dọc vắt qua goal chưa thắng; split state cũng chưa thắng.

## Cơ chế nâng cao

### Fragile

`FRAGILE` chỉ làm rơi block nguyên vẹn đứng thẳng. Block nằm ngang/dọc và cube
đơn trong split mode vẫn được nâng đỡ. Fragile không bị phá hủy vĩnh viễn trong
state; đi lại vào cùng tile áp dụng cùng luật.

### Bridge và switch

`bridge_states` là tuple bool theo đúng thứ tự metadata `bridges`: `True` là mở,
`False` là đóng. Bridge đóng hoạt động như void.

- **Soft switch** kích hoạt khi bất kỳ phần block nào chạm ô switch; trong split
  mode chỉ cube đang active được xét.
- **Heavy switch** chỉ kích hoạt khi block nguyên vẹn đứng thẳng trên switch.
- **Split switch** cũng cần block nguyên vẹn đứng thẳng; nó đưa hai cube tới
  `split_cells` và chọn cube 1 làm active.
- `toggle` đảo trạng thái bridge.
- `permanent_open` đặt bridge mở.
- `permanent_closed` đặt bridge đóng.

Engine kiểm tra nền trước khi áp dụng hiệu ứng tile và kiểm tra lại sau khi
switch làm thay đổi bridge hoặc tạo split state. Nếu một bước có nhiều lỗi nền,
thứ tự ưu tiên reason là `off_board`, `void`, `bridge_closed`,
`fragile_standing`.

### Split, đổi cube và merge

Trong split mode:

- `SWITCH_CUBE` đổi `active_cube` và không tự kích hoạt switch.
- `UP`, `DOWN`, `LEFT`, `RIGHT` di chuyển cube active đúng một ô.
- Đi vào ô của cube còn lại trả `ILLEGAL/cube_collision`.
- Cube không được hoàn thành level một mình.
- Hai cube kề nhau theo phương ngang hoặc dọc tự động merge thành block chuẩn.

Các helper chính nằm ở `game/split_block.py`, còn validation và switch effects
ở `game/switches.py`.

### Chi phí bước đi

`CostConfig` hiện dùng các giá trị mặc định:

```python
CostConfig(
    stand_roll=1.5,
    lie_roll=1.0,
    switch_cube=0.1,
    bridge_cross_penalty=0.3,
)
```

`Engine.step_cost()` dùng `stand_roll` khi state trước đang đứng,
`lie_roll` khi đang nằm và `switch_cube` cho `SWITCH_CUBE`. Trường
`bridge_cross_penalty` hiện là dự trữ và chưa được cộng vào cost.

## Solver API

Mọi solver có cùng entrypoint:

```python
from solvers import solve_astar, solve_bfs, solve_dfs, solve_ucs

result = solve_bfs(engine.get_initial_state(), engine)
```

`SearchResult` gồm:

```python
@dataclass
class SearchResult:
    solved: bool
    path: list[Action]
    total_cost: float
    search_time: float       # giây
    memory_usage: float      # MB, peak tracemalloc
    expanded_nodes: int
    solution_length: int
```

| Solver | Cách hoạt động |
| --- | --- |
| BFS | FIFO queue, đánh dấu state khi enqueue, tìm đường ít bước trong chi phí đồng nhất |
| DFS | LIFO stack, graph search với visited, giữ thứ tự ưu tiên action của Engine |
| UCS | Min-heap theo tổng `step_cost`, tối ưu theo cost không âm hiện tại |
| A* | Min-heap theo `g+h`; mặc định H2, có thể truyền H0/H1/H2 qua callback |

BFS và DFS cũng cung cấp class `BFSSolver`/`DFSSolver` dựa trên
`BaseSolver`. `BaseSolver` và helper `finalize`, `path_cost`,
`reconstruct_path` dùng chung việc đo metrics, replay path và tính tổng chi phí.

Solvers không được đọc `TileType`, switch hay cấu trúc board để tự quyết định
luật; chúng chỉ dùng Engine API, gồm `get_heuristic_context()` cho heuristic.

### Heuristic A*

A* mặc định dùng H2, một orientation-aware relaxed pattern database:

```text
h0(state) = 0
h1(state) = ceil(Manhattan(anchor, goal) / 2)
h2(state) = relaxed shortest-path cost theo orientation và topology
```

H2 giữ `VOID`, giữ rolling geometry, coi fragile là support, coi mọi bridge là
mở và dùng các split switch ở trạng thái STANDING làm pseudo-goal cost `0`.
Sau khi concrete state đã split, H2 trả `0` để giữ lower bound an toàn; full
split-pair abstraction là hướng mở rộng sau này. H2 được precompute bằng reverse
Dijkstra theo `stand_roll`/`lie_roll` và cache theo `HeuristicContext`.

Có thể benchmark các heuristic bằng callback:

```python
from solvers import build_h1, build_h2, solve_astar

context = engine.get_heuristic_context()
result_h1 = solve_astar(start, engine, heuristic=build_h1(context))
result_h2 = solve_astar(start, engine, heuristic=build_h2(context))
```

## HTTP API

`server.py` tạo FastAPI app không trạng thái: mỗi request mang đủ level và state.
Các level chỉ được lấy từ `levels/*.json`; tên file bị kiểm tra để ngăn path
traversal. Request body tối đa 256 KiB và `/solve` chạy solver trong worker
thread với timeout 10 giây.

### `GET /levels`

Trả danh sách tên level JSON hợp lệ. Level lỗi validation sẽ bị bỏ qua.

### `GET /levels/{name}`

Trả về board đã parse và initial state:

```json
{
  "board": {
    "name": "level1",
    "rows": 5,
    "cols": 10,
    "grid": ["..."],
    "start": [1, 3],
    "goal": [4, 6],
    "bridges": [],
    "switches": []
  },
  "initial_state": {
    "block_position": [1, 3],
    "orientation": "STANDING",
    "occupied_cells": [[1, 3]],
    "bridge_states": [],
    "split_mode": false,
    "cube1_position": null,
    "cube2_position": null,
    "active_cube": null
  }
}
```

### `POST /transition`

Request:

```json
{
  "level": "level1.json",
  "state": {"...": "state wire format"},
  "action": "RIGHT"
}
```

Response:

```json
{
  "status": "ok",
  "state": {"...": "next state"},
  "isGoal": false,
  "reason": null
}
```

### `POST /solve`

Request:

```json
{
  "level": "level1.json",
  "algorithm": "BFS",
  "state": {"...": "state wire format"}
}
```

`algorithm` nhận `BFS`, `DFS`, `UCS` hoặc `ASTAR`. Response là `SearchResult`
với path được serialize thành chuỗi action (`"UP"`, `"RIGHT"`, ...).

### Error envelope

Mọi lỗi API dùng dạng:

```json
{
  "error": {
    "code": "INVALID_STATE",
    "message": "..."
  }
}
```

Các nhóm lỗi chính gồm `INVALID_JSON`, `REQUEST_TOO_LARGE`,
`LEVEL_NOT_FOUND`, `INVALID_LEVEL`, `INVALID_ACTION`, `INVALID_FIELD`,
`INVALID_STATE`, `UNKNOWN_ALGORITHM`, `SOLVER_TIMEOUT` và `NOT_FOUND`.

## Cấu trúc repository

```text
.
├── game/
│   ├── actions.py          # Action, Orientation
│   ├── state.py            # immutable State, serialization
│   ├── board.py            # TileType, Board, level loader
│   ├── engine.py           # transition, goal, cost, orchestration
│   ├── tiles.py            # support/fall rules
│   ├── switches.py         # validation, bridges, switches
│   ├── split_block.py      # split, active cube, merge
│   ├── cost_config.py      # CostConfig và default costs
│   ├── geometry.py         # rolling geometry dùng chung
│   └── heuristic_context.py # relaxed topology/cost snapshot cho solver
├── solvers/
│   ├── base_solver.py      # metrics, parent/path/cost helpers
│   ├── bfs.py              # BFS
│   ├── dfs.py              # DFS
│   ├── ucs.py              # UCS
│   ├── astar.py            # A*
│   ├── heuristics/         # H1/H2 và abstract distance table
│   └── search_result.py    # SearchResult
├── server.py               # FastAPI adapter
├── levels/                 # level1.json ... level10.json
├── tests/                  # test suite
├── gui/                    # khung GUI, hiện rỗng
├── experiments/            # khung benchmark, hiện rỗng
├── main.py                 # entrypoint dự kiến, hiện rỗng
├── docs/
│   ├── bloxorz_project_requirements.md
│   ├── Mô tả công việc.md
│   ├── deep-research-report.md
│   └── h2 heuristic research.md
├── pyproject.toml
├── requirements.txt
└── uv.lock
```

## Kiểm thử và chất lượng

Test suite bao phủ:

- equality, hashing, immutability và JSON round-trip của `State`;
- parser, loader, grid shape, start/goal và board bounds;
- 12 transition geometry cases cùng fall/illegal/goal behavior;
- fragile, bridge, soft/heavy/split switch, bridge modes, split/merge và collision;
- BFS, DFS, UCS, A*, metrics, cycle handling và replay path;
- H2: relaxed topology, pseudo-goal split switch, cache và consistency trên level nhỏ;
- tất cả 10 level, gồm các màn advanced;
- HTTP schema, state validation, error envelope và solver endpoint.

Các lệnh kiểm tra chính:

```powershell
uv run pytest -q
uv run ruff check .
uv run pyright
pre-commit run --config .github/pre-commit.yaml --all-files
```

CI GitHub Actions chạy trên Python 3.12, cài dependency bằng `uv sync --dev`
và chạy pytest. Cấu hình pytest đặt `pythonpath=["."]`, vì vậy import package
theo dạng `from game import ...` và `from solvers import ...`.

## Việc còn lại

Để biến phần backend hiện tại thành ứng dụng hoàn chỉnh theo rubric, các phần
sau vẫn cần triển khai:

1. Xây dựng GUI trong `gui/` để render board/state, điều khiển keyboard, restart,
   undo, solver replay và hiển thị metrics.
2. Tạo `main.py` để khởi động GUI hoặc server theo workflow thống nhất.
3. Hoàn thiện `experiments/benchmark.py`, `run_experiments.py` và bảng kết quả
   để so sánh search time, peak memory, expanded nodes, solution length và cost.
4. Hoàn thiện benchmark cold/warm cho H0/H1/H2/UCS trong `experiments/`.
5. Nếu cần heuristic mạnh hơn sau split, mở rộng H2 thành full split-pair abstraction.
6. Bổ sung report PDF và video demo theo yêu cầu môn học.

## Quy ước phát triển

- Giữ public export của `game/__init__.py` ổn định.
- Mọi luật game mới phải nằm trong Engine hoặc helper của `game/`, không sao
  chép luật sang solver/GUI.
- Giữ `State` immutable/hashable và bảo toàn thứ tự `bridge_states` theo metadata.
- Solver chỉ dùng Engine API.
- Level JSON phải dùng chung được cho Engine, solver, server và GUI tương lai.
- Code, comment và docstring hiện dùng tiếng Việt; tên class/function theo Python
  convention.
- Không sửa tay `requirements.txt`; khi dependency thay đổi, cập nhật
  `pyproject.toml` rồi export lại bằng `uv`.
- Không thêm lại `src/` layout.
