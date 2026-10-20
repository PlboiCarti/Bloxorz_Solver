# TÀI LIỆU PHÂN CHIA CÔNG VIỆC VÀ GIAO TIẾP GIỮA CÁC MODULE

## Đồ án Bloxorz AI Solver

---

# 1. Kiến trúc tổng thể

Đồ án được chia thành 3 nhóm công việc chính:

```text
┌──────────────────────────────┐
│ CÔNG VIỆC 1                  │
│ GAME ENGINE                  │
│ TV1 + TV2                    │
└──────────────┬───────────────┘
               │
               │ Engine API
               │ State / Transition
               ▼
┌──────────────────────────────┐
│                              │
│       CÔNG VIỆC 3            │
│ GUI + INTEGRATION            │
│ TV5                          │
│                              │
└──────────────▲───────────────┘
               │
               │ Solver API
               │ Path / Metrics
               │
┌──────────────┴───────────────┐
│ CÔNG VIỆC 2                  │
│ AI SOLVER                    │
│ TV3 + TV4                    │
└──────────────────────────────┘
```

Nguyên tắc kiến trúc:

- **Game Engine** chịu trách nhiệm mô hình hóa trạng thái và toàn bộ luật chơi Bloxorz.
- **AI Solver** chịu trách nhiệm tìm lời giải bằng các thuật toán tìm kiếm.
- **GUI + Integration** chịu trách nhiệm kết nối Engine và Solver, xử lý tương tác người dùng, animation và hiển thị kết quả.

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

TV2 đã hoàn thiện các cơ chế trên trong `game/tiles.py`, `game/switches.py`, `game/split_block.py`, hook trực tiếp vào `Engine` mà không thay đổi public API; kèm theo các màn `levels/level2.json`–`level10.json` và bộ test advanced mechanics.

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

Cấu hình cầu/công tắc nằm trong metadata `bridges`/`switches` của file JSON màn chơi và được kiểm thực sâu (deep validation) khi khởi tạo Engine:

```text
bridges[i]  = { "id": str, "cell": [r, c], "initial": "open" | "closed" }

switches[i] = { "cell": [r, c],
                "type": "soft" | "heavy" | "split",
                "targets": [ { "bridge": id, "mode": "toggle" | "permanent_open" | "permanent_closed" } ],
                "split_cells": [ [r, c], [r, c] ]   # chỉ với công tắc split
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

Trong đó `bridge_states` là tuple `bool`: phần tử thứ $i$ ứng với cầu thứ $i$ theo thứ tự danh sách `bridges` của màn chơi (`True` = cầu mở/đi được, `False` = cầu đóng/như void); màn chơi không có cầu thì `bridge_states = ()`.

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
T(State, Action) → State'
```

Ví dụ:

```python
next_state = engine.transition(
    current_state,
    RIGHT
)
```

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
State'
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

Được sử dụng chủ yếu cho UCS và A\*.

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

## 4.2. TV4 — UCS + A\*

TV4 phụ trách:

- UCS
- A\*
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

next_state = engine.transition(
    state,
    action
)
```

Riêng A* có thể sử dụng thêm API read-only:

```python
context = engine.get_heuristic_context()
```

Context này chỉ cung cấp topology tĩnh đã được Engine relaxed hóa và cost
configuration cho việc xây dựng H0/H1/H2. Solver không được đọc trực tiếp
`Board`, `TileType` hoặc metadata switch để tự thực thi luật game.

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
├── expanded_nodes
└── memory_usage
```

Có thể mô tả ngắn gọn:

> **Output của Công việc 2:** Một tập các Solver độc lập gồm BFS, DFS/IDS, UCS và A\*, sử dụng API của Game Engine và trả về một SearchResult thống nhất chứa Solution Path và các metrics cần thiết.

---

# 7. CÔNG VIỆC 3 — GUI + INTEGRATION

## Thành viên

- TV5

## Mục tiêu

Tiếp nhận đầu ra của Công việc 1 và Công việc 2 để xây dựng ứng dụng Bloxorz hoàn chỉnh.

TV5 không viết lại Engine và cũng không viết lại các thuật toán Solver.

---

# 8. INPUT CỦA CÔNG VIỆC 3

## Nhận từ Công việc 1

```text
ENGINE OUTPUT
│
├── Board
├── State
├── Initial State
├── legal_actions()
├── transition()
├── is_goal()
└── step_cost()
```

## Nhận từ Công việc 2

```text
SOLVER OUTPUT
│
└── SearchResult
       ├── solved
       ├── path
       ├── total_cost
       ├── search_time
       ├── memory_usage
       ├── expanded_nodes
       └── solution_length
```

---

# 9. TV5 SỬ DỤNG OUTPUT NHƯ THẾ NÀO?

## 9.1. Trường hợp người dùng chơi thủ công

Ví dụ người dùng nhấn:

```text
RIGHT
```

GUI gửi Action cho Engine:

```python
next_state = engine.transition(
    current_state,
    RIGHT
)
```

Sau đó GUI render:

```python
gui.render(next_state)
```

Luồng:

```text
Keyboard
    ↓
GUI
    ↓
Action
    ↓
ENGINE
    ↓
State'
    ↓
GUI
    ↓
Render
```

---

## 9.2. Trường hợp người dùng chọn Solver

Ví dụ:

```text
[Solve BFS]
```

GUI gọi:

```python
result = bfs.solve(
    current_state,
    engine
)
```

Solver trả về:

```python
result.path
```

Ví dụ:

```text
RIGHT
RIGHT
DOWN
LEFT
UP
```

Sau đó GUI replay từng Action thông qua Engine:

```python
for action in result.path:

    current_state = engine.transition(
        current_state,
        action
    )

    gui.render(current_state)
```

Luồng:

```text
Solver Path
     ↓
GUI
     ↓
Action #1
     ↓
Engine.transition()
     ↓
State'
     ↓
Render
     ↓
Action #2
     ↓
Engine.transition()
     ↓
...
```

GUI không được tự thay đổi tọa độ block mà phải luôn sử dụng Engine.

---

# 10. HIỂN THỊ METRICS

Sau khi Solver trả về `SearchResult`, GUI có thể hiển thị:

```text
Algorithm: A*

Solution Length: 14
Path Cost: 14
Expanded Nodes: 82
Search Time: 0.021 s
Memory Usage: 4.2 MB
```

Các dữ liệu này đồng thời được sử dụng cho phần Experiments và Report.

---

# 11. DATA FLOW TOÀN HỆ THỐNG

```text
                       USER
                        │
          ┌─────────────┴─────────────┐
          │                           │
      Play manually                Solve AI
          │                           │
          ▼                           ▼
        GUI                          GUI
          │                           │
       Action                     Algorithm
          │                           │
          ▼                           ▼
┌───────────────────┐        ┌────────────────────┐
│    GAME ENGINE    │◄───────│     AI SOLVER      │
│                   │        │                    │
│ State             │        │ BFS                │
│ Transition        │        │ DFS / IDS          │
│ Legal Actions     │        │ UCS                │
│ Goal Test         │        │ A*                 │
│ Step Cost         │        │                    │
└─────────┬─────────┘        └──────────┬─────────┘
          │                             │
          │ State'            SearchResult
          │                             │
          │                  ┌──────────┴─────────┐
          │                  │ path               │
          │                  │ time               │
          │                  │ memory             │
          │                  │ expanded nodes     │
          │                  └──────────┬─────────┘
          │                             │
          └──────────────┬──────────────┘
                         ▼
                        GUI
                         │
                     Animation
                         │
                     Statistics
```

---

# 12. INTERFACE CONTRACT GIỮA 3 NHÓM

Nhóm nên thống nhất các interface này trước khi bắt đầu code.

```text
================================================
ENGINE CONTRACT
================================================

get_initial_state()
    → State

legal_actions(state)
    → List[Action]

transition(state, action)
    → State | None

is_goal(state)
    → bool

step_cost(state, action, next_state)
    → float


================================================
SOLVER CONTRACT
================================================

solve(initial_state, engine)
    → SearchResult


================================================
SEARCH RESULT
================================================

SearchResult:
    solved
    path
    total_cost
    search_time
    memory_usage
    expanded_nodes
    solution_length
```

Một khi các interface này được thống nhất, Engine Team và Solver Team có thể phát triển tương đối độc lập.

---

# 13. TÓM TẮT BÀN GIAO GIỮA 3 CÔNG VIỆC

| Công việc                | Thành viên | Đầu vào                    | Đầu ra phải bàn giao                                               |
| ------------------------ | ---------- | -------------------------- | ------------------------------------------------------------------ |
| **1. Game Engine**       | TV1 + TV2  | Map / Action               | Engine API + State + Board + toàn bộ luật Bloxorz + tests          |
| **2. AI Solver**         | TV3 + TV4  | Engine API + Initial State | BFS, DFS/IDS, UCS, A\* + SearchResult                              |
| **3. GUI / Integration** | TV5        | Engine + Solver            | Ứng dụng hoàn chỉnh: chơi tay, chọn thuật toán, animation, metrics |

---

# 14. TÓM TẮT LUỒNG DỮ LIỆU

```text
CÔNG VIỆC 1
Map + Action
      ↓
STATE / TRANSITION / ENGINE API


CÔNG VIỆC 2
Initial State + Engine API
      ↓
SOLUTION PATH + METRICS


CÔNG VIỆC 3
Engine + SearchResult
      ↓
GAME Bloxorz HOÀN CHỈNH
```

---

# 15. NGUYÊN TẮC TÍCH HỢP

1. Engine là nơi duy nhất chứa luật chơi Bloxorz.
2. Solver không tự xử lý tile hoặc switch.
3. GUI không tự cập nhật tọa độ block.
4. Mọi thay đổi State phải đi qua `engine.transition()`.
5. Tất cả Solver phải dùng cùng một `SearchResult`.
6. State phải hashable để Solver có thể sử dụng `visited`.
7. API giữa các nhóm cần được thống nhất từ đầu và hạn chế thay đổi trong quá trình phát triển.
8. TV5 nên tích hợp liên tục trong quá trình phát triển, không chờ đến cuối đồ án mới merge.
9. Engine Team phải cung cấp test để xác nhận Core và Advanced Mechanics hoạt động đúng.
10. Solver Team phải test thuật toán bằng Engine thật hoặc mock Engine có cùng API trước khi bàn giao.

---

# 16. MỤC TIÊU CUỐI CÙNG

Kiến trúc mong muốn:

```text
                 GAME ENGINE
              TV1 + TV2
                  │
                  │ Engine API
                  ▼
              INTEGRATION
                 TV5
                  ▲
                  │ SearchResult
                  │
               AI SOLVER
              TV3 + TV4
```

Khi kiến trúc này được giữ đúng, mỗi nhóm có thể phát triển độc lập nhưng vẫn tích hợp được thành một hệ thống hoàn chỉnh mà không phải viết lại logic của nhóm khác.
