# TÀI LIỆU PHÂN CHIA CÔNG VIỆC VÀ GIAO TIẾP GIỮA CÁC MODULE
## Đồ án Bloxorz AI Solver

---

# 1. Kiến trúc tổng thể

Đồ án được chia thành ba nhóm công việc. Luồng hiện tại nối GUI với Engine qua HTTP API Python cho cả chơi thủ công lẫn giải tự động: GUI gửi state hiện tại tới `/solve`, rồi phát lại từng action qua `/transition`. Engine vẫn là nguồn chuẩn của luật và state.

```text
┌──────────────────┐      HTTP JSON       ┌───────────────────┐
│ GUI · TV5        │ ───────────────────► │ server.py         │
│ gui/index.html   │  GET /levels         │ Python API adapter│
│ Three.js + input │  POST /transition    └─────────┬─────────┘
└────────▲─────────┘                                │
         │                         Engine.transition│
         │ board / state / result                   ▼
         └───────────────────────────────────┌──────────────────┐
                                             │ Engine · TV1/TV2 │
                                             │ game/            │
                                             └──────────────────┘

TV3/TV4 sở hữu các thuật toán Solver và dùng Engine Python. TV5 tích hợp chúng qua API; GUI không tự cài thuật toán hoặc luật Bloxorz.
```

Nguyên tắc kiến trúc:

- **Game Engine** chịu trách nhiệm mô hình hóa trạng thái và toàn bộ luật chơi Bloxorz.
- **AI Solver** chịu trách nhiệm tìm lời giải bằng các thuật toán tìm kiếm.
- **GUI + Integration** chịu trách nhiệm lấy level và gửi thao tác qua HTTP API Python, xử lý input, animation và hiển thị kết quả Engine.
- Trình duyệt không import hoặc gọi trực tiếp module Python. `server.py` chuyển tiếp request tới Engine và chuyển kết quả thành JSON.

---

# 2. CÔNG VIỆC 1 — GAME ENGINE

## Thành viên
- TV1
- TV2

## Mục tiêu

Xây dựng một Game Engine hoàn chỉnh cho Bloxorz, có khả năng mô phỏng chính xác trạng thái và luật chơi mà không phụ thuộc vào GUI hoặc thuật toán tìm kiếm.

Engine phải hỗ trợ cả basic mechanics và advanced mechanics.

---

## 2.1. TV1 — Core Engine

TV1 phụ trách:

- `Board`
- `State`
- `Action`
- Block position
- Orientation
- Standing / Horizontal / Vertical
- UP / DOWN / LEFT / RIGHT
- Floor
- Void
- Goal
- Kiểm tra bước đi hợp lệ
- Goal test
- Hash / Equality của State
- Transition cơ bản

State nên được thiết kế đủ từ đầu để hỗ trợ:

```text
State
├── block position
├── orientation
├── bridge states
├── split mode
├── cube1 position
├── cube2 position
└── active cube
```

---

## 2.2. TV2 — Advanced Mechanics

TV2 phụ trách:

- Fragile tile
- Bridge
- Soft switch
- Heavy switch
- Split switch
- Toggle bridge
- Permanent bridge
- Split block
- Active cube
- Merge block
- Kiểm thử advanced mechanics

TV2 mở rộng Engine của TV1 và không tạo một Game Engine riêng.

---

# 3. ĐẦU RA CỦA CÔNG VIỆC 1

Công việc 1 phải bàn giao một **Game Engine đã kiểm thử và có API ổn định**, không chỉ bàn giao các file code rời rạc.

## 3.1. Board

Board đại diện cho bản đồ của màn chơi.

```text
Board
├── floor tiles
├── void
├── goal
├── fragile tiles
├── switches
├── bridges
└── mapping switch → bridge
```

Ví dụ:

```python
board = Board(...)
```

---

## 3.2. State

State là ảnh chụp toàn bộ trạng thái động của trò chơi tại một thời điểm.

Ví dụ về mặt khái niệm:

```python
State(
    block_position,
    orientation,
    bridge_states,
    split_mode,
    cube1_position,
    cube2_position,
    active_cube
)
```

Ví dụ:

```text
State S0

Block:
    position = (3, 4)
    orientation = STANDING

Bridges:
    B1 = CLOSED
    B2 = OPEN

Split:
    False
```

State là dữ liệu quan trọng được dùng bởi cả Solver và GUI.

---

## 3.3. Engine API

### `get_initial_state()`

```text
Input:
    Level / Board

Output:
    Initial State
```

Ví dụ:

```python
initial_state = engine.get_initial_state()
```

---

### `legal_actions(state)`

Input:

```python
state
```

Output:

```python
[UP, LEFT, RIGHT]
```

Ví dụ:

```python
actions = engine.legal_actions(state)
```

Solver không tự kiểm tra luật chơi. Engine chịu trách nhiệm xác định hành động nào hợp lệ.

---

### `transition(state, action)`

Đây là API quan trọng nhất.

```text
T(State, Action) → TransitionResult
```

Ví dụ:

```python
result = engine.transition(
    current_state,
    Action.RIGHT
)
```

`TransitionResult` có `status` (`ok`, `fall`, `illegal`), `state` (chỉ có khi `ok`), `is_goal`, `reason` và `fall_state` (hình học nước đi bị rơi, chỉ dùng cho animation). HTTP adapter đổi `is_goal` thành `isGoal` trong JSON. GUI chỉ commit `state` khi `status == "ok"`; `fall_state` không được dùng làm state logic.

Luồng xử lý bên trong Engine:

```text
Action
  ↓
Move block
  ↓
Update orientation
  ↓
Check board bounds
  ↓
Check supporting tiles
  ↓
Check fragile
  ↓
Check switch
  ↓
Update bridges
  ↓
Handle split / merge
  ↓
Validate state
  ↓
TransitionResult
```

---

### `is_goal(state)`

Input:

```python
state
```

Output:

```python
True / False
```

Ví dụ:

```python
if engine.is_goal(state):
    ...
```

---

### `step_cost(state, action, next_state)`

Được sử dụng chủ yếu cho UCS và A*.

Ví dụ:

```python
cost = engine.step_cost(
    state,
    action,
    next_state
)
```

Nếu mọi bước có chi phí bằng nhau:

```text
cost = 1
```

Nếu nhóm thiết kế weighted cost thì Engine vẫn là nơi cung cấp Step Cost cho Solver.

---

## 3.4. Output cuối cùng của Công việc 1

```text
ENGINE OUTPUT

1. Board
2. State representation
3. Initial State
4. legal_actions(state)
5. transition(state, action)
6. is_goal(state)
7. step_cost(state, action, next_state)
8. Bộ test xác nhận Engine hoạt động đúng
```

Có thể mô tả ngắn gọn như sau:

> **Output của Công việc 1:** Một module Game Engine đã được kiểm thử, cung cấp Board, Initial State và API ổn định cho việc truy vấn hành động hợp lệ, chuyển đổi trạng thái, kiểm tra Goal và xác định Step Cost.

---

# 4. CÔNG VIỆC 2 — AI SOLVER

## Thành viên
- TV3
- TV4

## Mục tiêu

Xây dựng các thuật toán tìm kiếm độc lập sử dụng Game Engine làm môi trường.

---

## 4.1. TV3 — BFS + DFS/IDS

TV3 phụ trách:

- BFS
- DFS hoặc IDS
- Visited-state handling
- Parent tracking
- Path reconstruction

---

## 4.2. TV4 — UCS + A*

TV4 phụ trách:

- UCS
- A*
- Priority Queue
- Cost handling
- Heuristic
- Phân tích heuristic
- Path reconstruction

---

# 5. INPUT CỦA CÔNG VIỆC 2

Solver nhận:

```text
Engine API
+
Initial State
```

Ví dụ:

```python
result = bfs.solve(
    initial_state,
    engine
)
```

Luồng:

```text
Initial State
     ↓
   Solver
     ↓
legal_actions(state)
     ↓
transition(state, action)
     ↓
TransitionResult
     ↓ (chỉ khi status == ok)
  State'
     ↓
đưa vào frontier
```

## Nguyên tắc quan trọng

Solver **không được tự xử lý luật Bloxorz**.

Không nên:

```python
if tile == FRAGILE:
    ...
```

Không nên:

```python
if switch == HEAVY:
    ...
```

Solver chỉ sử dụng:

```python
actions = engine.legal_actions(state)

result = engine.transition(
    state,
    action
)

if result.status == TransitionStatus.OK:
    next_state = result.state
```

---

# 6. ĐẦU RA CỦA CÔNG VIỆC 2

Tất cả Solver phải trả về cùng một kiểu dữ liệu thống nhất:

```python
SearchResult
```

Ví dụ:

```python
class SearchResult:
    solved: bool
    path: list
    total_cost: float
    search_time: float
    expanded_nodes: int
    memory_usage: float
    solution_length: int
    preprocessing_time: float = 0.0
```

---

## 6.1. Solution Path

Ví dụ:

```python
result.path
```

trả về:

```python
[
    RIGHT,
    DOWN,
    DOWN,
    LEFT,
    UP
]
```

Đây là dữ liệu GUI sử dụng để chạy animation tự động.

---

## 6.2. Search Metrics

Các metric chính:

```text
Search Time
Memory Usage
Expanded Nodes
Solution Length
Total Cost
```

Ví dụ:

```python
result.search_time
result.preprocessing_time
result.memory_usage
result.expanded_nodes
result.solution_length
result.total_cost
```

Có thể bổ sung:

```text
Generated Nodes
Maximum Frontier Size
```

nếu nhóm cần phân tích sâu hơn.

---

## 6.3. Search Status

Ví dụ:

```python
result.solved
```

Nếu không tìm được lời giải:

```python
SearchResult(
    solved=False,
    path=[],
    ...
)
```

---

## 6.4. Output cuối cùng của Công việc 2

```text
SOLVER OUTPUT

SearchResult
│
├── solved
├── path
├── solution_length
├── total_cost
├── search_time
├── preprocessing_time
├── expanded_nodes
└── memory_usage
```

Có thể mô tả ngắn gọn:

> **Output của Công việc 2:** Các Solver BFS, DFS, UCS và A* sử dụng API của Game Engine và trả về `SearchResult` thống nhất gồm solution path cùng metrics. IDS chưa có trong danh sách thuật toán được đăng ký hiện tại.

---

# 7. CÔNG VIỆC 3 — GUI + INTEGRATION

## Thành viên
- TV5

## Phạm vi hiện tại

TV5 nối giao diện với Engine qua HTTP API Python cho thao tác thủ công và Solver. GUI gửi state hiện tại tới `/solve`, hiển thị metrics, rồi phát lại từng action bằng `/transition`. TV5 không viết lại luật, không import module game Python trong trình duyệt và không tự tính state kế tiếp.

Các file đang tham gia luồng:

| File | Vai trò |
|---|---|
| gui/index.html | Giao diện Three.js, input, API client PythonEngineAPI, chuyển đổi dữ liệu, animation và hiển thị state. |
| server.py | HTTP adapter: phục vụ trang/assets, đọc level, kiểm tra request, gọi Engine và chuyển kết quả thành JSON. |
| game/ | Board, State, Action, Engine và toàn bộ luật chuyển trạng thái. |

---

# 8. HỢP ĐỒNG TV5 NHẬN TỪ ENGINE

GUI nhận dữ liệu qua các endpoint hiện có:

| Request | Dữ liệu GUI nhận/gửi |
|---|---|
| GET /levels | Danh sách tên level mà backend tải được. |
| GET /levels/{name} | Board và initial_state mới của level. |
| POST /transition | Gửi level, state hiện tại đầy đủ và action; nhận TransitionResult. |

State trên wire dùng tọa độ [row, col]. Action dùng các chuỗi UP, DOWN, LEFT, RIGHT; SWITCH_CUBE chỉ áp dụng khi Engine đang ở split mode.

`GET /levels` sắp xếp tự nhiên theo số, nên `level2` đứng trước `level10`.

TransitionResult trên HTTP có status là ok, fall hoặc illegal; `state` chỉ có giá trị khi ok; `fall_state` chứa hình học bị từ chối khi fall để GUI đưa khối tới đúng ô bẫy rồi mới thả; `isGoal` cho biết đã thắng; `reason` mô tả kết quả fall/illegal. Trong Python, trường tương ứng là `is_goal`.

---

# 9. LUỒNG CHƠI THỦ CÔNG

Ví dụ người chơi nhấn phím phải:

```text
Keyboard / button / swipe
        ↓
GUI ánh xạ input thành action RIGHT
        ↓
PythonEngineAPI gửi POST /transition
        ↓
server.py kiểm tra request và khôi phục State
        ↓
Engine.transition(state, Action.RIGHT)
        ↓
server.py trả TransitionResult dạng JSON
        ↓
GUI cập nhật state logic nếu status == ok, sau đó render/animate
```

Ánh xạ input:

| GUI | Action gửi API |
|---|---|
| U, D, L, R | UP, DOWN, LEFT, RIGHT |
| SWITCH | SWITCH_CUBE |

Kết quả được xử lý như sau:

- ok: lưu state hiện tại vào history, nhận state mới từ Engine, phát animation giữa hai state; chỉ isGoal từ phản hồi mới đưa GUI vào trạng thái thắng.
- fall: Engine trả `state = null` và hình học đích trong `fall_state`; GUI giữ nguyên state logic trước nước đi, lăn tới ô bẫy rồi chạy animation rơi và khóa di chuyển ở trạng thái thua.
- illegal: Engine trả state = null; GUI giữ nguyên state logic và thông báo hành động không hợp lệ.

GUI không cần gọi legal_actions để tự quyết định nước đi. GUI gửi ý định của người chơi tới transition; Engine là nơi xác định hành động đó thành công, rơi hay không hợp lệ.

---

# 10. TRÁCH NHIỆM VỚI STATE VÀ occupied_cells

Engine là nguồn dữ liệu chuẩn cho occupied_cells:

1. game/state.py tính occupied_cells() nội bộ từ block_position, orientation hoặc hai cube khi split. Engine dùng danh sách này để kiểm tra nền và kích hoạt luật tile.
2. server.py khôi phục State từ bảy trường API rồi tự lấy state.occupied_cells() để kiểm tra các ô nằm trong board. occupied_cells không bắt buộc trong request và không được gửi trong JSON response.
3. GUI không đọc, tạo, chuyển đổi hoặc gửi occupied_cells. GUI đặt khối thường từ block_position + orientation, và đặt hai cube từ cube1_position/cube2_position.

Engine/State là nguồn duy nhất xác định hình học logic. GUI chỉ đổi tọa độ anchor/cube sang hệ Three.js và tạo hình ảnh; việc đặt tâm của khối nằm ngang/dọc dùng orientation như phép biến đổi hiển thị, không phải luật chuyển trạng thái.

Quy ước tọa độ:

- Backend: [row, col], row tăng xuống dưới và col tăng sang phải.
- Three.js: x = col, z = row, y là chiều cao.
- occupied_cells là dữ liệu nội bộ Python, không thuộc HTTP state schema. Quy ước thứ tự nội bộ: anchor trước rồi ô kế tiếp; split state là cube1 rồi cube2.

---

# 11. RANH GIỚI GUI VÀ ENGINE

- Engine kiểm tra bounds, nền, tile đặc biệt, switch, cầu, split/merge, trạng thái thắng và tạo TransitionResult.
- server.py chỉ kiểm tra/đổi dạng dữ liệu HTTP và gọi Engine; không tạo một bộ luật thứ hai.
- GUI xử lý input, state hiển thị, history, camera và animation. Animation nội suy từ state trước tới state được Engine chấp nhận, hoặc tới `fall_state` chỉ dùng trình bày khi nước đi bị rơi.
- GUI có thể kiểm tra dữ liệu wire để phát hiện phản hồi sai, nhưng không tự tính trạng thái kế tiếp hoặc tự kết luận thắng/thua.
- Reset tải lại GET /levels/{name}; undo khôi phục snapshot do GUI lưu. Backend không giữ phiên chơi và không có endpoint reset/undo.

---

# 12. BÀN GIAO VÀ TIÊU CHÍ HOÀN THÀNH

| Nhóm | Đầu ra cần bàn giao cho luồng này |
|---|---|
| TV1 | Board, State, Action và Engine cốt lõi; get_initial_state, legal_actions, transition, is_goal, step_cost. |
| TV2 | Cơ chế tile đặc biệt, cầu, switch, split/merge và xác thực metadata level trong cùng Engine. |
| TV5 | GUI gọi được GET /levels, GET /levels/{name}, POST /transition; hiển thị đúng kết quả ok/fall/illegal và state đặc biệt mà Engine trả về. |

TV5 không cần truy cập trực tiếp class Engine từ JavaScript. Hợp đồng Python được mô tả trong docs/api.md; hợp đồng HTTP giữa browser và server được mô tả trong docs/gui_api.md.

Tiêu chí kiểm tra tích hợp:

1. Level được tải từ backend; board và initial_state khớp nhau.
2. Một action hợp lệ cập nhật GUI theo state trả về, bao gồm block_position, orientation, cube positions và bridge_states; GUI không cần occupied_cells.
3. Fall/illegal không ghi đè state logic; khi fall, animation đi tới `fall_state` rồi rơi vào ô bẫy.
4. Switch, split, đổi cube và merge được render theo state Engine trả về.
5. Restart và undo khôi phục đúng board/state cục bộ.
6. GUI chạy cùng FastAPI server, không chạy bằng static server nếu cần gọi API.

---

# 13. CÁCH CHẠY LUỒNG GUI + ENGINE

Từ thư mục gốc repository, chạy:

```powershell
python -m uvicorn server:app --reload --host 127.0.0.1 --port 8000
```

Mở http://127.0.0.1:8000. FastAPI phục vụ GUI và API cùng origin. Chạy python -m http.server chỉ phục vụ file tĩnh, không cung cấp các route /levels hoặc /transition.

---

# 14. NGUYÊN TẮC TÍCH HỢP

1. Chỉ Engine được chứa luật chơi và quyết định successor state.
2. Trình duyệt chỉ gọi Python qua PythonEngineAPI trong GUI và server.py.
3. Thay đổi schema board/state/action phải đồng bộ Engine, server, GUI và docs/gui_api.md.
4. GUI chỉ commit state mới với status ok; fall và illegal không thay đổi state logic.
5. occupied_cells do State/Engine sinh và server dùng nội bộ để kiểm tra board bounds; trường này không đi qua GUI/API wire.
6. Animation nước đi hợp lệ kết thúc ở state Engine trả về; animation rơi dùng `fall_state` làm đích trình bày nhưng không commit state đó.
7. Khi kiểm tra luật, dùng code hiện tại làm nguồn xác nhận nếu tài liệu cũ khác với triển khai.

---

# 15. MỤC TIÊU CỦA PHẦN TV1, TV2 VÀ TV5

Người chơi mở GUI qua FastAPI, tải level từ Python, thao tác trên giao diện và nhìn thấy kết quả transition do Engine xác định. GUI trình bày đúng bàn chơi, khối, ô đặc biệt và phản hồi thắng/thua mà không sao chép luật từ Python sang JavaScript.
