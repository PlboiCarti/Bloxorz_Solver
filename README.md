# Bloxorz AI Solver

Đồ án CSC14003 - Introduction to Artificial Intelligence: xây dựng game
Bloxorz có GUI web và bốn solver BFS, DFS, UCS, A*. Luật game được giữ trong
Python Engine; GUI chỉ hiển thị trạng thái, gửi action và phát lại lời giải.

## Trạng thái hiện tại

- Game Engine hỗ trợ core mechanics, fragile tiles, bridges, soft/heavy/split
  switches, split/merge và kiểm tra thắng/thua.
- GUI web dùng Three.js trong `gui/index.html`, được phục vụ cùng HTTP API bởi
  `server.py`.
- Có 20 màn GUI: `levels/level1.json` đến `levels/level20.json`.
- BFS, DFS, UCS và A* dùng chung `Engine` và trả về `SearchResult` có metrics.
- Benchmark dùng chính 20 level GUI: 80 lượt chạy cho bốn thuật toán. Kết quả
  hiện tại: 80/80 lượt solved, không timeout và không error.
- Checkout hiện không có automated test suite; thư mục `tests/` không còn mã
  nguồn test. Các file cache Python được bỏ qua bởi `.gitignore`.

## Cài đặt và chạy GUI

Chạy từ PowerShell tại thư mục gốc repository:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m ensurepip --upgrade
python -m pip install -r requirements.txt
python server.py
```

Mở trình duyệt tại:

```text
http://127.0.0.1:8000
```

API documentation của FastAPI:

```text
http://127.0.0.1:8000/docs
```

`requirements.txt` hiện chứa dependency runtime của server là `fastapi` và
`uvicorn`. Core game, solver và benchmark chỉ dùng thư viện chuẩn Python.

Notebook `experiments/analysis.ipynb` cần thêm các gói phân tích nếu muốn chạy:

```powershell
python -m pip install numpy pandas matplotlib jupyter ipykernel
```

## Cấu trúc chính

```text
game/                         # Board, State, Engine và luật game
solvers/                      # BFS, DFS, UCS, A* và heuristic H1/H2
levels/                       # level1.json ... level20.json của GUI
gui/index.html                # GUI Three.js
server.py                     # FastAPI app và static file server
experiments/                  # benchmark trên các level GUI
  benchmark.py                # đăng ký solver và timeout dùng chung
  run_experiments.py          # benchmark runner
  results.csv                 # kết quả benchmark gần nhất
  results_metadata.json       # cấu hình và môi trường chạy
requirements.txt              # dependency runtime
docs/                         # API, GUI handoff và status
```

`main.py` hiện không phải entrypoint. Dùng `python server.py` để chạy GUI/API.

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
| `F` | Fragile tile |
| `B` | Bridge |
| `o` | Soft switch |
| `x` | Heavy switch |
| `P` | Split switch |

Các metadata bridge/switch phải khớp với ký tự trong grid. `load_board()` và
`Engine` thực hiện validation trước khi level được dùng bởi server, GUI hoặc
solver.

Các nhóm mechanics hiện có trong 20 level:

| Nhóm | Level |
| --- | --- |
| `basic` | `level1`-`level3` |
| `fragile` | `level4`, `level5`, `level12` |
| `switches_bridges` | `level6`-`level9`, `level11`, `level13`-`level17`, `level19` |
| `combined` | `level10`, `level18`, `level20` |

## Solver

Các public entrypoint:

```python
from game import Engine, load_board
from solvers import solve_astar, solve_bfs, solve_dfs, solve_ucs

engine = Engine(load_board("levels/level1.json"))
initial_state = engine.get_initial_state()
result = solve_bfs(initial_state, engine)
```

Mọi solver dùng Engine để sinh successor và kiểm tra goal:

- **BFS**: tìm lời giải ít bước trong trường hợp cost đồng nhất.
- **DFS**: graph search với visited set; không đảm bảo lời giải tối ưu.
- **UCS**: ưu tiên tổng `Engine.step_cost()` nhỏ nhất.
- **A***: ưu tiên `g + h`, mặc định dùng heuristic H2.

`SearchResult` chứa path và các chỉ số `search_time`, `memory_usage`,
`expanded_nodes`, `solution_length`. A* còn có `preprocessing_time`; kết quả
solver cũng lưu `total_cost` để phục vụ semantics của UCS/A*.

## HTTP API và GUI

| Method | Endpoint | Mục đích |
| --- | --- | --- |
| `GET` | `/` | Phục vụ `gui/index.html` |
| `GET` | `/levels` | Liệt kê level JSON hợp lệ |
| `GET` | `/levels/{name}` | Trả board và initial state |
| `POST` | `/transition` | Thực hiện một action |
| `POST` | `/solve` | Chạy BFS/DFS/UCS/A* |

Engine là nguồn sự thật duy nhất cho transition. GUI không tự mô phỏng luật
game; sau mỗi action, GUI dùng state do server trả về để cập nhật màn hình.

## Benchmark theo yêu cầu đồ án

PDF yêu cầu đánh giá hiệu năng trên một bộ test cố định, dùng cùng bộ test cho
các thuật toán và đo bốn chỉ số: search time, memory usage, expanded nodes và
solution length. Runner hiện thực yêu cầu này trực tiếp trên các level mà GUI
đang cung cấp.

Chạy benchmark:

```powershell
python -m experiments.run_experiments
```

Mặc định chạy:

```text
20 level × 4 thuật toán = 80 lượt
```

Kết quả được ghi vào:

```text
experiments/results.csv
experiments/results_metadata.json
```

Một số tùy chọn hiện có:

```powershell
python -m experiments.run_experiments --timeout 30
python -m experiments.run_experiments --algorithms BFS "A*"
python -m experiments.run_experiments --repeat 3
python -m experiments.run_experiments --output experiments/results_trial.csv
```

Runner tự quét `levels/level*.json`, dùng `Engine.get_initial_state()` và không
phụ thuộc vào `test_set.json`. Các chỉ số trong CSV cần dùng cho report là:

- `search_time_seconds`
- `peak_memory_mb`
- `expanded_nodes`
- `solution_length`

Report cần trình bày bảng, biểu đồ và nhận xét về kết quả theo yêu cầu PDF.

## Tài liệu liên quan

- [`experiments/README.md`](experiments/README.md): cách chạy và phạm vi benchmark.
- [`docs/api.md`](docs/api.md): contract của Engine.
- [`docs/gui_api.md`](docs/gui_api.md): contract GUI/HTTP.
- [`docs/Hướng dẫn UI.md`](docs/Hướng%20dẫn%20UI.md): luồng tích hợp GUI.
- [`docs/status.md`](docs/status.md): trạng thái hiện tại và blocker.
- [`AI - Project 1 (đã fix).pdf`](AI%20-%20Project%201%20%28đã%20fix%29.pdf): yêu cầu môn học.

## Kiểm tra nhanh

Compile/import smoke check:

```powershell
python -m compileall -q game solvers experiments server.py
python -m experiments.run_experiments --help
```

Không có test suite tự động trong checkout hiện tại. Khi thêm test source sau
này, cài `pytest` riêng và không commit các file trong `__pycache__/`.
