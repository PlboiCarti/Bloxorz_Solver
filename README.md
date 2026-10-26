# Bloxorz AI Solver

Đồ án CSC14003 - Introduction to Artificial Intelligence: xây dựng game
Bloxorz có GUI web và bốn solver BFS, DFS, UCS, A*. Luật game nằm duy nhất
trong Python `Engine`; GUI chỉ hiển thị trạng thái, gửi action lên server và
phát lại lời giải.

## Trạng thái hiện tại

- `Engine` hỗ trợ core mechanics, fragile tiles, bridges, soft/heavy/split
  switches, split/merge, đổi khối điều khiển và kiểm tra thắng/thua.
- GUI web dùng Three.js trong một file `gui/index.html`, được `server.py`
  phục vụ cùng HTTP API và texture/model trong `assets/`.
- Có 20 màn chơi GUI: `levels/level1.json` đến `levels/level20.json`.
- BFS, DFS, UCS và A* dùng chung `Engine` và trả về `SearchResult` có metrics.
  A* mặc định dùng heuristic H2 (relaxed pattern database).
- Benchmark dùng bộ test cố định 120 case (`experiments/test_set.json`): 100 bản
  đồ độc lập và 20 level GUI được nhúng sẵn board. Kết quả gần nhất: 480/480 lượt
  solved, không timeout, không error.
- H2 được chứng minh admissible bằng lập luận và kiểm chứng trên toàn bộ state
  đạt được của 120 case. Hàm A* đang dùng chưa consistent ở 2 level
  (`level15`, `level17`); xem `docs/deep-research-report.md`.
- Chưa có automated test suite. CI (`.github/workflows/ci.yml`) chỉ chạy smoke
  check: compile và import `game`, `solvers`, `server`.

## Cài đặt và chạy GUI

Yêu cầu Python 3.10 trở lên (CI dùng 3.12). Chạy từ PowerShell tại thư mục gốc
repository:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python server.py
```

Mở trình duyệt tại `http://127.0.0.1:8000`. Tài liệu API tự sinh của FastAPI có
ở `http://127.0.0.1:8000/docs`.

`requirements.txt` chỉ chứa dependency của server (`fastapi`, `uvicorn`). Core
game, solver và benchmark chỉ dùng thư viện chuẩn Python. Notebook
`experiments/analysis.ipynb` cần thêm các gói phân tích:

```powershell
python -m pip install numpy pandas matplotlib jupyter ipykernel
```

### Điều khiển trong GUI

| Phím / nút | Tác dụng |
| --- | --- |
| Mũi tên hoặc `W` `A` `S` `D` | Lăn khối (hoặc cube đang active khi split) |
| `Space` / **ĐỔI KHỐI** | Đổi cube điều khiển khi đang split |
| `U`, `Backspace` / **UNDO** | Hoàn tác một bước |
| `R` / **RESTART** | Chơi lại level hiện tại |
| **SOLVE** | Gọi solver đã chọn (BFS/DFS/UCS/A*) và hiển thị metrics |
| ⏮ ◀ ▶ ▶ ⏭, thanh **TỐC ĐỘ** | Phát lại lời giải từng bước hoặc tự động |

## Cấu trúc chính

```text
game/                         # Luật game: Board, State, Engine
  board.py                    #   parse/validate level JSON (load_board, parse_board)
  engine.py                   #   transition, legal_actions, step_cost, is_goal
  geometry.py, split_block.py #   hình học lăn khối, split/merge
  switches.py, tiles.py       #   switch/bridge và loại ô
  cost_config.py              #   CostConfig (chi phí bước đi)
  heuristic_context.py        #   dữ liệu tĩnh cho heuristic
solvers/                      # BFS, DFS, UCS, A* và SearchResult
  heuristics/h1.py, h2.py     #   H1 Manhattan baseline, H2 pattern database
  runtime.py                  #   hủy hợp tác (cancel_event)
levels/                       # level1.json ... level20.json của GUI
gui/index.html                # GUI Three.js (single file)
assets/rollingcat/            # texture/model, phục vụ tại /assets/* (MIT)
server.py                     # FastAPI app: API + GUI + assets
experiments/                  # benchmark trên bộ test cố định
  test_set.json               #   120 case: 100 bản đồ độc lập + 20 level GUI
  build_test_set.py           #   nhúng lại 20 level GUI vào test_set.json
  benchmark.py                #   đăng ký solver và timeout dùng chung
  run_experiments.py          #   benchmark runner
  verify_heuristic.py         #   kiểm chứng admissible/consistent của H1/H2
  results.csv                 #   kết quả benchmark gần nhất
  results_metadata.json       #   cấu hình và môi trường của lần chạy đó
  heuristic_check.csv         #   kết quả kiểm chứng heuristic
  analysis.ipynb              #   notebook phân tích kết quả
docs/                         # API, GUI contract, status, báo cáo heuristic
.github/workflows/ci.yml      # smoke check trên branch gui_v2
requirements.txt              # dependency runtime của server
```

Entrypoint duy nhất của ứng dụng là `python server.py`.

## Level JSON

Mỗi level là một object có `name`, `grid`, `bridges` và `switches`:

```json
{
  "name": "level1",
  "grid": ["..###.....", "###S##...."],
  "bridges": [],
  "switches": []
}
```

`grid` là ma trận chữ nhật có đúng một `S` và một `G`:

| Ký tự | Ý nghĩa |
| --- | --- |
| `#` | Sàn bình thường |
| `.` | Void |
| `S` | Ô xuất phát |
| `G` | Ô đích |
| `F` | Fragile tile (khối không được đứng thẳng) |
| `B` | Bridge |
| `o` | Soft switch (chạm là kích hoạt) |
| `x` | Heavy switch (phải đứng thẳng lên) |
| `P` | Split switch (tách khối thành hai cube) |

Metadata trong `bridges`/`switches` phải khớp với ký tự trong grid.
`load_board()` và `parse_board()` validate level trước khi server, GUI hay solver
dùng tới. Schema đầy đủ và ví dụ: `docs/api.md` §6.3.

## Solver

```python
from game import Engine, load_board
from solvers import solve_astar, solve_bfs, solve_dfs, solve_ucs

engine = Engine(load_board("levels/level1.json"))
initial_state = engine.get_initial_state()
result = solve_astar(initial_state, engine)
print(result.solved, result.total_cost, result.expanded_nodes)
```

Mọi solver dùng `Engine` để sinh successor và kiểm tra goal, và nhận tùy chọn
`cancel_event` để dừng giữa chừng:

- **BFS**: lời giải ít bước nhất (không xét cost).
- **DFS**: graph search với visited set; không đảm bảo tối ưu.
- **UCS**: tối thiểu tổng `Engine.step_cost()`.
- **A\***: ưu tiên `g + h`, mặc định H2 (truyền `heuristic=` để đổi). Cho phép
  reopen state nên vẫn tối ưu với heuristic admissible.

Chi phí mặc định (`DEFAULT_COST`): lăn khi đứng `1.5`, lăn khi nằm `1.0`, đổi cube
`0.1`.

`SearchResult` gồm `solved`, `path`, `total_cost`, `search_time`,
`memory_usage`, `expanded_nodes`, `solution_length` và `preprocessing_time`
(thời gian dựng H2, chỉ khác 0 với A*).

## HTTP API

| Method | Endpoint | Mục đích |
| --- | --- | --- |
| `GET` | `/` | Phục vụ `gui/index.html` |
| `GET` | `/assets/{path}` | Phục vụ file trong `assets/` |
| `GET` | `/levels` | Liệt kê level JSON hợp lệ |
| `GET` | `/levels/{name}` | Trả board và initial state |
| `POST` | `/transition` | Thực hiện một action (`UP`/`DOWN`/`LEFT`/`RIGHT`/`SWITCH_CUBE`) |
| `POST` | `/solve` | Chạy `BFS`/`DFS`/`UCS`/`ASTAR`, giới hạn 10 giây |

Server không giữ trạng thái: mỗi request mang đủ level và state. Lỗi trả về dạng
`{"error": {"code", "message"}}`. Chi tiết contract: `docs/gui_api.md`.

## Benchmark và kiểm chứng heuristic

PDF yêu cầu đánh giá trên một bộ test cố định dùng chung cho mọi thuật toán, đo
search time, memory usage, expanded nodes và solution length. Runner chạy 120
case × 4 thuật toán = 480 lượt:

```powershell
python -m experiments.run_experiments              # ghi experiments/results.csv
python -m experiments.run_experiments --repeat 3   # lặp để lấy trung bình time/memory
python -m experiments.verify_heuristic             # ghi experiments/heuristic_check.csv
```

Các tùy chọn khác của runner: `--dataset`, `--output`, `--timeout` (mặc định 15
giây mỗi lượt), `--algorithms`. Sau khi sửa file trong `levels/`, chạy
`python -m experiments.build_test_set` để nhúng lại level GUI vào test set.

Kết quả gần nhất (trung bình trên 120 case):

| Thuật toán | Expanded nodes | Solution length | Total cost |
| --- | --- | --- | --- |
| BFS | 418.9 | 27.21 | 32.34 |
| DFS | 196.3 | 94.03 | 113.69 |
| UCS | 392.0 | 27.21 | 32.30 |
| A* | 87.2 | 27.21 | 32.30 |

Expanded nodes, solution length và total cost tái lập được giữa các lần chạy.
Time và memory thay đổi theo máy và tải. Thiết kế bộ test, định nghĩa cột CSV và
bảng chi tiết nằm trong [`experiments/README.md`](experiments/README.md).

## Tài liệu liên quan

- [`experiments/README.md`](experiments/README.md): benchmark, bộ test và kết quả.
- [`docs/index.md`](docs/index.md): bản đồ toàn bộ tài liệu.
- [`docs/api.md`](docs/api.md): contract Python của Engine/solver.
- [`docs/gui_api.md`](docs/gui_api.md): contract GUI/HTTP và luồng tích hợp.
- [`docs/deep-research-report.md`](docs/deep-research-report.md): thiết kế H2, chứng minh và kiểm chứng.
- [`docs/status.md`](docs/status.md): trạng thái hiện tại và blocker.
- [`docs/CHANGELOG.md`](docs/CHANGELOG.md): lịch sử thay đổi.
- [`docs/Agents.md`](docs/Agents.md): quy tắc làm việc trong repo.
- [`AI - Project 1 (đã fix).pdf`](AI%20-%20Project%201%20%28đã%20fix%29.pdf): yêu cầu môn học.

## Kiểm tra nhanh

Giống smoke check của CI:

```powershell
python -m compileall -q game solvers experiments server.py
python -c "import game, solvers, server; print('Core imports OK')"
python -m experiments.run_experiments --help
```

Chưa có test suite tự động. Khi thêm test, cài `pytest` riêng và không commit
`__pycache__/`.
