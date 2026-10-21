# Bloxorz AI Solver

Đồ án **CSC14003 — Introduction to Artificial Intelligence**: mô phỏng trò
chơi Bloxorz và giải màn chơi bằng BFS, DFS, UCS và A*. Dự án dùng Python 3.12
và sử dụng layout package ở thư mục gốc (`game/`,
`solvers/`), không có `src/`.

README này mô tả implementation hiện tại trong working tree. Engine, các solver,
HTTP adapter và GUI Three.js đã có; GUI gọi Python qua cùng-origin API. Entrypoint
main.py và phần benchmark chưa được triển khai.

## Trạng thái hiện tại

| Thành phần | Trạng thái | Nội dung |
| --- | --- | --- |
| Game Engine | Hoàn thành | Core movement, goal, fragile, bridge, soft/heavy/split switch, split/merge |
| BFS / DFS | Hoàn thành | Graph search, parent map, path reconstruction, metrics |
| UCS / A* | Hoàn thành | Priority queue, chi phí từ `Engine.step_cost`, H2 mặc định và heuristic injectable |
| HTTP adapter | Hoàn thành | FastAPI: levels, transition, solve, validation và error envelope |
| Levels | Hoàn thành | Level 0 để kiểm tra ô đặc biệt và level1–level10 cho bộ màn chơi |
| Tests | Chưa có trong checkout | Không có thư mục `tests/`; chưa thể xác nhận automated coverage |
| GUI | Đã tích hợp | gui/index.html gọi /transition cho thao tác và replay; gọi /solve để tìm đường bằng BFS/DFS/UCS/A* |
| Entrypoint | Chưa triển khai | `main.py` đang rỗng |
| Experiments | Chưa triển khai | `benchmark.py`, `run_experiments.py` và `results.csv` hiện rỗng |

Tài liệu kiến trúc, API và hướng dẫn GUI nằm trong docs/. Hai báo cáo nghiên cứu
heuristic là deep-research-report.md và h2 heuristic research.md. A* mặc định
dùng H2 split-aware; xem docs/API_CONTRACT.md để biết contract HTTP và giới hạn
cần nhóm xác nhận.

## Mục tiêu và kiến trúc

Engine là nguồn sự thật duy nhất của luật chơi. Solver dùng Engine API; heuristic
nhận snapshot tĩnh do Engine cung cấp. server.py chuyển JSON giữa GUI web với
Engine/Solver. GUI gọi /transition cho di chuyển và replay, /solve cho tìm đường;
mỗi bước replay lại được Engine xác nhận.

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
- `gui/index.html`: giao diện Three.js, client API, điều khiển và hoạt ảnh; `main.py` cùng `experiments/` vẫn là phần chưa triển khai.

## Luồng tích hợp GUI

GUI Three.js trong gui/index.html chỉ gửi trạng thái và ý định qua server.py;
Engine quyết định transition, còn solver tìm đường từ state hiện tại. /solve
trả action path và metrics. GUI phát lại path bằng request tuần tự tới /transition,
cập nhật mesh theo state backend trả về, và dừng nếu transition không còn hợp lệ.
Không chép luật game hoặc thuật toán tìm kiếm sang JavaScript.
Trong bảng `DI CHUYỂN`, chọn màn và thuật toán rồi bấm `SOLVE`. Bảng được mở rộng để hiện đầy đủ thông số và replay, không cần cuộn. Di chuyển bằng phím mũi tên, WASD hoặc vuốt; cụm bốn nút hướng trên màn hình đã được bỏ.

Three.js được nạp qua module CDN jsDelivr, nên trình duyệt cần truy cập được CDN.
Nếu chỉ thấy HUD/nền mà không có bàn chơi, mở DevTools Console để xem lỗi khởi tạo;
`GET /levels` phải trả danh sách file level JSON.

## Cài đặt và chạy nhanh

Các lệnh sau chạy từ PowerShell trong VS Code:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python server.py
```

Server lắng nghe tại `http://127.0.0.1:8000`. FastAPI cũng cung cấp OpenAPI
interactive docs tại /docs và schema tại /openapi.json. Endpoint / phục vụ
gui/index.html; giao diện và API dùng chung origin.

`requirements.txt` hiện liệt kê `fastapi` và `uvicorn`. Checkout chưa có
`pyproject.toml`, `uv.lock`, thư mục `tests/` hoặc cấu hình lint/type-check; vì vậy
README không mô tả các lệnh `uv`/test như những lệnh có thể chạy được ở trạng thái này.

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
JSON. `to_dict()` không tự thêm `occupied_cells`; trường này cũng không nằm trong
HTTP state. Server suy ra nó từ `State` để kiểm tra board bounds.

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
`bridge_cross_penalty` hiện là dự trữ và chưa được cộng vào cost. Mọi cost
trong `CostConfig` phải hữu hạn và không âm để UCS/A* dùng được.

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
    preprocessing_time: float  # giây dựng heuristic; 0 nếu không có
```

`search_time` đo tìm kiếm và đóng gói path; A* báo riêng thời gian dựng H2 ở
`preprocessing_time`. `expanded_nodes` chỉ đếm state đã lấy khỏi frontier và
đã sinh successor, không tính goal. Việc đo peak `tracemalloc` được tuần tự hóa
giữa các solver vì tracer dùng chung trong process; nếu profiler ngoài đã bật
tracing thì `memory_usage` trả `0` thay vì lấy số đo không riêng cho request.

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

H2 giữ `VOID`, giữ rolling geometry, coi fragile là support và coi mọi bridge là
mở. Bản mặc định là split-aware: graph có `AbstractPose` và canonical
`AbstractSplitPair`; khi hai cube kề nhau, graph chuyển về pose nằm ngang/dọc
để mô phỏng merge. Graph bỏ chi phí `SWITCH_CUBE` và được precompute bằng reverse
Dijkstra theo `stand_roll`/`lie_roll`, cache theo `HeuristicContext`. Đây là thiết kế
relaxation; admissibility/consistency vẫn cần được xác nhận với toàn bộ luật chuyển
trạng thái và cost cuối cùng trước khi khẳng định A* tối ưu.

Baseline cũ vẫn có thể dựng bằng `build_h2(context, split_aware=False)`:
split switch là pseudo-goal và mọi concrete split state nhận heuristic `0`.

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
thread với deadline 10 giây. Khi hết deadline, server gửi tín hiệu hủy; BFS,
DFS, UCS, A*, và các vòng dựng H2 dừng tại checkpoint kế tiếp.

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
│   ├── runtime.py          # cancellation, serialized memory tracking
│   ├── bfs.py              # BFS
│   ├── dfs.py              # DFS
│   ├── ucs.py              # UCS
│   ├── astar.py            # A*
│   ├── heuristics/         # H1/H2 và abstract distance table
│   └── search_result.py    # SearchResult
├── server.py               # FastAPI adapter
├── levels/                 # level0.json ... level10.json
├── gui/
│   ├── index.html          # Three.js web GUI
│   ├── app.py              # stub GUI Python, hiện rỗng
│   ├── controller.py       # stub GUI Python, hiện rỗng
│   └── renderer.py         # stub GUI Python, hiện rỗng
├── experiments/            # stub benchmark và file kết quả, hiện rỗng
├── main.py                 # entrypoint dự kiến, hiện rỗng
├── docs/
│   ├── Agents.md
│   ├── API_CONTRACT.md
│   ├── api.md / gui_api.md
│   ├── Hướng dẫn UI.md / Mô tả công việc.md
│   ├── CHANGELOG.md
│   ├── deep-research-report.md
│   └── h2 heuristic research.md
└── requirements.txt
```

## Kiểm thử và chất lượng

Checkout hiện tại không có thư mục `tests/`, `pyproject.toml`, `uv.lock` hoặc
`.github/workflows/`. Các mục smoke test trong `docs/API_CONTRACT.md` là tiêu
chí cần kiểm tra, không phải bằng chứng test đã chạy. Chưa chạy test trong lượt
cập nhật này.

## Việc còn lại

Các phần tiếp theo để hoàn thiện và nghiệm thu đồ án:

1. Kiểm tra thủ công GUI/API qua level0–level10, gồm các ô đặc biệt, solver và replay.
2. Chốt workflow khởi động; `python server.py` chạy web GUI cùng API.
   `main.py` chưa phải entrypoint của web GUI.
3. Hoàn thiện `experiments/benchmark.py`, `run_experiments.py` và bảng kết quả
   để so sánh search time, peak memory, expanded nodes, solution length và cost.
4. Xác nhận ý nghĩa cost và admissibility/consistency của H2 trước khi khẳng định
   điều kiện tối ưu của A*; sau đó hoàn thiện
   benchmark cold/warm cho H0/H1/H2/UCS trong `experiments/`.
5. Bổ sung report PDF và video demo theo yêu cầu môn học.

## Quy ước phát triển

- Giữ public export của `game/__init__.py` ổn định.
- Mọi luật game mới phải nằm trong Engine hoặc helper của `game/`, không sao
  chép luật sang solver/GUI.
- Giữ `State` immutable/hashable và bảo toàn thứ tự `bridge_states` theo metadata.
- Solver chỉ dùng Engine API.
- Level JSON phải dùng chung được cho Engine, solver, server và GUI tương lai.
- Code, comment và docstring hiện dùng tiếng Việt; tên class/function theo Python
  convention.
- Cập nhật `requirements.txt` khi dependency runtime thay đổi. Nếu sau này thêm
  `pyproject.toml`/lockfile, đồng bộ hướng dẫn cài đặt trong README.
- Không thêm lại `src/` layout.
