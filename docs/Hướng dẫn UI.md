# Hướng dẫn UI cho Bloxorz AI Solver

Tài liệu này là handoff cho TV5. Nó mô tả cách xây GUI dựa trên source hiện
tại, không yêu cầu UI tự cài đặt lại luật Bloxorz.

## 1. Trạng thái source hiện tại

Backend đã có:

- `game/`: Board, State, Engine, core mechanics và advanced mechanics;
- `solvers/`: BFS, DFS, UCS, A* và `SearchResult`;
- `solvers/heuristics/h2.py`: H2 orientation-aware, cost-aware và
  split-pair-aware;
- `levels/level1.json` đến `levels/level20.json`, gồm các màn core và advanced mechanics;
- `server.py`: HTTP adapter cho level, transition và solve;
- Checkout hiện tại không có thư mục `tests/`; checklist contract bên dưới là
  những việc cần kiểm tra, không phải kết quả test đã xác nhận.

Thành phần GUI web hiện tại:

- `gui/index.html`: Three.js renderer, input, HUD, solver panel và replay controls;
- `server.py`: cùng origin phục vụ GUI và HTTP API;
- `PythonEngineAPI` trong `gui/index.html`: gọi `/levels`, `/transition` và `/solve`.

GUI đang dùng HTTP API; luật chơi và trạng thái sau mỗi nước đi do Python Engine
xác nhận. `gui/app.py`, `gui/controller.py`, `gui/renderer.py` và `main.py` là
hướng tổ chức cho một GUI desktop riêng, không phải entrypoint của web GUI hiện tại.

## 2. Hai cách tích hợp

### 2.1. Gọi trực tiếp Python

Phù hợp với desktop GUI hoặc GUI Python chạy cùng process:

```python
from game import Engine, load_board

engine = Engine(load_board("levels/level1.json"))
state = engine.get_initial_state()
```

Sau đó controller gọi trực tiếp:

```python
from game import Action, TransitionStatus

result = engine.transition(state, Action.RIGHT)
if result.status is TransitionStatus.OK:
    state = result.state
```

Đây là cách khuyến nghị nếu GUI được viết bằng Tkinter, PySide/PyQt,
Pygame hoặc framework desktop tương tự.

### 2.2. Gọi HTTP API

Phù hợp với frontend web tách khỏi Python. Khởi động server:

```powershell
python server.py
```

Các endpoint:

| Method | Endpoint | Mục đích |
| --- | --- | --- |
| `GET` | `/levels` | Liệt kê level hợp lệ |
| `GET` | `/levels/{name}` | Lấy board và initial state |
| `POST` | `/transition` | Thực hiện một action |
| `POST` | `/solve` | Chạy BFS/DFS/UCS/A* |

`GET /` phục vụ `gui/index.html`; khởi động bằng `python server.py`
để GUI và API dùng cùng origin.

## 3. State model mà UI phải hiểu

`State` là immutable snapshot. UI không sửa trực tiếp field của State mà nhận
state mới từ Engine.

### Normal mode

```python
state.split_mode is False
state.block_position       # anchor (row, col)
state.orientation          # STANDING/HORIZONTAL/VERTICAL
state.bridge_states        # tuple[bool, ...]
```

Các ô bị block chiếm được lấy bằng:

```python
cells = state.occupied_cells()
```

Quy ước:

- `STANDING`: một ô `(r, c)`;
- `HORIZONTAL`: `(r, c)` và `(r, c + 1)`;
- `VERTICAL`: `(r, c)` và `(r + 1, c)`.

`block_position` luôn là anchor ở ô trên-trái đối với trạng thái nằm.

### Split mode

```python
state.split_mode is True
state.cube1_position
state.cube2_position
state.active_cube       # 1 hoặc 2
state.block_position    # vị trí cube đang active
state.orientation       # luôn STANDING
```

Khi split, renderer vẽ hai cube từ `cube1_position` và `cube2_position`.
Cube đang active nên có highlight khác. `block_position` không phải một block
1x1x2 trong mode này; nó chỉ là vị trí cube đang nhận input.

`State.occupied_cells()` chỉ là helper hình học nội bộ cho Engine/backend. State
trên HTTP có bảy trường: `block_position`, `orientation`, `bridge_states`,
`split_mode`, `cube1_position`, `cube2_position` và `active_cube`; GUI không gửi
`occupied_cells`. Server khôi phục `State`, tự suy ra các ô bị chiếm và kiểm tra
chúng trong board.

## 4. Board và rendering

Với direct Python, renderer có thể đọc board đã parse từ `engine.board`:

```python
board = engine.board
board.grid_raw       # các chuỗi grid gốc
board.grid           # tile enum theo từng ô
board.rows
board.cols
board.start
board.goal
board.bridges
board.switches
```

Mapping tile trong grid:

| Ký tự | Hiển thị |
| --- | --- |
| `#` | sàn |
| `.` | void |
| `S` | start |
| `G` | goal |
| `F` | fragile |
| `B` | bridge |
| `o` | soft switch |
| `x` | heavy switch |
| `P` | split switch |

Bridge mở/đóng không chỉ dựa vào ký tự `B`. Hãy dùng `state.bridge_states`:
phần tử thứ `i` tương ứng với `engine.board.bridges[i]`. `True` là mở, `False`
là đóng.

Renderer không được tự kết luận action có hợp lệ hay không. Nó chỉ hiển thị
snapshot hiện tại và trạng thái kết quả từ Engine.

## 5. Luồng input thủ công

Controller nên giữ tối thiểu:

```python
engine: Engine
current_state: State
history: list[State]
```

Luồng thực hiện action:

```python
def apply_action(self, action: Action) -> None:
    result = self.engine.transition(self.current_state, action)

    if result.status is TransitionStatus.OK and result.state is not None:
        self.history.append(self.current_state)
        self.current_state = result.state
        self.renderer.render(self.engine.board, self.current_state)

        if result.is_goal:
            self.show_win_message()
    else:
        self.show_transition_feedback(result.reason)
```

Không tạo state mới bằng cách tự cập nhật tọa độ. Engine phải xử lý:

- rolling và orientation;
- off-board/void/fall;
- fragile;
- bridge và switch;
- split, đổi active cube, collision và merge;
- goal.

`TransitionResult` là kiểu trả về thực tế. Không giả định
`engine.transition()` trả trực tiếp `State` hoặc `None`.

Input nên hỗ trợ:

| Input | Action/command |
| --- | --- |
| Arrow keys hoặc WASD | `UP`, `DOWN`, `LEFT`, `RIGHT` |
| Space | `SWITCH_CUBE` khi đang split; có thể dùng pause ngoài split |
| `R` | Restart level |
| `U` hoặc Backspace | Undo |

`Engine.legal_actions(current_state)` có thể dùng để disable hoặc đánh dấu
action không hợp lệ, nhưng vẫn phải gọi `transition()` khi thực hiện action.

## 6. Restart, undo và thắng/thua

Restart:

```python
current_state = engine.get_initial_state()
history.clear()
```

Undo chỉ khôi phục snapshot trước đó trong history; không tự đảo ngược action.
Nếu `transition()` trả `FALL` hoặc `ILLEGAL`, state hiện tại không đổi và không
được push vào history.

Có thể kiểm tra thắng bằng một trong hai cách:

```python
result.is_goal
```

hoặc:

```python
engine.is_goal(current_state)
```

Điều kiện thắng là block nguyên vẹn, `STANDING`, đúng trên goal. Lying block và
split state chưa thắng.

## Luồng solver của GUI web

gui/index.html không import solver Python trực tiếp. PythonEngineAPI.solve()
gửi POST /solve với level, thuật toán và state hiện tại; server parse state,
tạo Engine rồi gọi BFS/DFS/UCS/A*. GUI hiển thị SearchResult metrics và ánh xạ
action API về action điều khiển nội bộ.

Replay không tự tính trạng thái trong JavaScript. Mỗi action trong SearchResult.path
được gửi qua POST /transition; GUI chỉ animate và render state Engine trả về.
Nếu API trả fall, illegal, lỗi hoặc timeout, replay dừng và hiển thị lỗi.
Undo/restart/lựa chọn level vẫn quản lý history và state phía client theo contract.

## 7. Chạy solver và replay

Solver nhận `initial_state` và `engine`, rồi trả `SearchResult`:

```python
from solvers import solve_astar, solve_bfs, solve_dfs, solve_ucs

result = solve_astar(current_state, engine)
```

Chọn solver bằng mapping:

```python
SOLVERS = {
    "BFS": solve_bfs,
    "DFS": solve_dfs,
    "UCS": solve_ucs,
    "ASTAR": solve_astar,
}
```

Các field cần hiển thị:

```python
result.solved
result.path              # list[Action]
result.total_cost
result.search_time
result.preprocessing_time # thời gian dựng H2; 0 nếu không dùng
result.memory_usage
result.expanded_nodes
result.solution_length
```

A* tự dùng H2 split-aware mặc định. GUI không cần gọi hoặc tính H2 trực tiếp.

### Replay path

Replay vẫn phải đi qua Engine:

```python
for action in result.path:
    transition = engine.transition(current_state, action)
    if transition.status is not TransitionStatus.OK:
        stop_replay_with_error()
        break
    current_state = transition.state
    renderer.render(engine.board, current_state)
    wait_animation_step()
```

Không được chỉ nội suy tọa độ từ danh sách action, vì split, bridge và merge có
thể làm state thay đổi ngoài rolling geometry đơn giản.

Solver chạy đồng bộ sẽ khóa event loop. Với GUI desktop, chạy solver trong
worker thread/executor, disable nút điều khiển trong lúc tìm kiếm, sau đó đưa
`SearchResult` về UI thread để bắt đầu replay.

## 8. HTTP contract

### Lấy level

```http
GET /levels/level8.json
```

Response có:

```json
{
  "board": {
    "name": "level8 - split and merge",
    "rows": 5,
    "cols": 12,
    "grid": ["..."],
    "start": [1, 1],
    "goal": [3, 9],
    "bridges": [],
    "switches": [
      {
        "cell": [1, 3],
        "type": "split",
        "targets": [],
        "split_cells": [[1, 7], [4, 11]]
      }
    ]
  },
  "initial_state": {
    "block_position": [1, 1],
    "orientation": "STANDING",
    "bridge_states": [],
    "split_mode": false,
    "cube1_position": null,
    "cube2_position": null,
    "active_cube": null
  }
}
```

### Thực hiện action

```json
POST /transition
{
  "level": "level8.json",
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

`status` có thể là `ok`, `fall` hoặc `illegal`. Khi `fall`/`illegal`, `state`
là `null` và `reason` giải thích lỗi.

### Chạy solver

```json
POST /solve
{
  "level": "level10.json",
  "algorithm": "ASTAR",
  "state": {"...": "state wire format"}
}
```

`algorithm` nhận `BFS`, `DFS`, `UCS` hoặc `ASTAR`. HTTP server chạy solver
trong worker thread, gửi tín hiệu hủy tại deadline 10 giây và solver dừng ở
checkpoint tiếp theo. Path trong HTTP response là chuỗi:

```json
{
  "solved": true,
  "path": ["RIGHT", "DOWN"],
  "total_cost": 3.5,
  "search_time": 0.001,
  "memory_usage": 0.02,
  "expanded_nodes": 12,
  "solution_length": 2,
  "preprocessing_time": 0.0
}
```

## 9. Kiến trúc file đề xuất cho TV5

```text
gui/
├── app.py          # khởi động ứng dụng, tạo window/page và binding event
├── controller.py   # Engine, State, history, input, solver, replay
├── renderer.py     # board/state -> pixels hoặc HTML/canvas
└── index.html      # chỉ cần nếu chọn web GUI

assets/             # tùy chọn; route server hiện phục vụ thư mục này ở root
```

Nếu dùng thư viện GUI mới, thêm dependency runtime vào `requirements.txt` và
đồng bộ hướng dẫn cài đặt trong README.

Không đưa luật game vào `renderer.py`. Controller cũng không được tự mô phỏng
split/bridge; nó chỉ điều phối Engine và hiển thị kết quả.

## 10. Checklist nghiệm thu

- [ ] Chọn và load được cả 20 level.
- [ ] Vẽ đúng `#`, `.`, `S`, `G`, `F`, `B`, `o`, `x`, `P`.
- [ ] Điều khiển được bốn hướng và restart.
- [ ] Hiển thị đúng standing/horizontal/vertical.
- [ ] Hiển thị đúng bridge mở/đóng theo `bridge_states`.
- [ ] Hiển thị đúng split mode, active cube, collision và merge.
- [ ] Có undo không làm thay đổi Engine state ngoài history.
- [ ] Hiển thị win và fall/illegal feedback.
- [ ] Chạy được BFS, DFS, UCS và A* qua `POST /solve`.
- [ ] Replay path tuần tự qua `POST /transition`, không tự mô phỏng state.
- [ ] Hiển thị đủ search time, memory, expanded nodes, solution length và cost.
- [ ] Solver không khóa event loop/UI thread.
- [ ] Kiểm tra tối thiểu các level 8, 9, 10, 18 và 20 trước khi quay demo.

## 11. Những điều không được phá vỡ

- Không đổi convention tọa độ `(row, col)`.
- Không đổi thứ tự `Action`: `UP`, `DOWN`, `LEFT`, `RIGHT`, `SWITCH_CUBE`.
- Không sửa trực tiếp field của immutable `State`.
- Không tự viết lại luật Engine trong GUI.
- Không coi lying block hoặc split state là goal.
- Không bỏ `bridge_states` khi lưu history hoặc gửi HTTP.
- Không replay bằng cách tự tính tọa độ; luôn gọi `Engine.transition()`.
