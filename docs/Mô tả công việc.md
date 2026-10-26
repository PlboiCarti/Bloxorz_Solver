# PHÂN CHIA CÔNG VIỆC VÀ RANH GIỚI MODULE — Bloxorz AI Solver

> Tài liệu này chỉ mô tả **ai làm gì, bàn giao gì và các module nói chuyện với
> nhau ra sao**. Chi tiết API không chép lại ở đây:
>
> - Contract Python (Engine, State, Board, `SearchResult`, cost): `docs/api.md`.
> - Contract HTTP/GUI (endpoint, JSON, replay, phím điều khiển): `docs/gui_api.md`.
>
> Khi tài liệu khác với code, code là nguồn xác nhận.

---

## 1. Kiến trúc tổng thể

```text
┌──────────────────┐      HTTP JSON       ┌───────────────────┐
│ GUI · TV5        │ ───────────────────► │ server.py         │
│ gui/index.html   │  GET  /levels        │ FastAPI adapter   │
│ Three.js + input │  GET  /levels/{name} └───┬───────────┬───┘
└────────▲─────────┘  POST /transition        │           │
         │            POST /solve             │           │ solve_*(state, engine)
         │ board / state / result             ▼           ▼
         └──────────────────────────  ┌──────────────┐ ┌──────────────────┐
                                      │ Engine       │◄│ Solver · TV3/TV4 │
                                      │ game/ TV1/TV2│ │ solvers/         │
                                      └──────────────┘ └──────────────────┘
```

- **Game Engine** (`game/`) là nơi duy nhất chứa luật chơi và quyết định state kế tiếp.
- **AI Solver** (`solvers/`) chỉ dùng Engine API: `legal_actions`, `transition`,
  `is_goal`, `step_cost` và `get_heuristic_context` (cho H2). Solver không tự
  kiểm tra tile, switch hay bridge.
- **GUI + Integration** (`gui/index.html`, `server.py`) gửi ý định người chơi qua
  HTTP, render state Engine trả về. Trình duyệt không import Python và không
  tự tính state. Solve: GUI gửi state hiện tại tới `/solve`, rồi phát lại từng
  action của `path` qua `/transition`.
- `occupied_cells` là dữ liệu nội bộ Python; server tự suy ra để kiểm tra bounds,
  không đi qua HTTP.

---

## 2. Phân công

| Thành viên | Phạm vi | Thư mục |
| --- | --- | --- |
| TV1 — Core Engine | `Board`, `State`, `Action`, ba orientation, bốn hướng lăn, floor/void/goal, legal move, goal test, hash/equality của State, transition cơ bản. State được thiết kế đủ từ đầu cho bridge và split. | `game/` |
| TV2 — Advanced Mechanics | Fragile, bridge, soft/heavy/split switch, toggle/permanent bridge, split block, active cube, merge, validation metadata level. Mở rộng Engine của TV1, không tạo Engine riêng. | `game/`, `levels/` |
| TV3 — BFS + DFS | Visited set, parent tracking, path reconstruction. | `solvers/bfs.py`, `solvers/dfs.py`, `solvers/base_solver.py` |
| TV4 — UCS + A* | Priority queue, cost handling, heuristic H1/H2 và phân tích heuristic. | `solvers/ucs.py`, `solvers/astar.py`, `solvers/heuristics/` |
| TV5 — GUI + Integration | Giao diện Three.js, input bàn phím/vuốt, animation, solve + replay, HTTP adapter. | `gui/index.html`, `server.py` |
| Lead | Benchmark, CI, report. | `experiments/`, `.github/` |

---

## 3. Đầu ra bàn giao

| Nhóm | Bàn giao | Trạng thái (xem `docs/status.md`) |
| --- | --- | --- |
| TV1 + TV2 | Engine với `get_initial_state`, `legal_actions`, `transition -> TransitionResult`, `is_goal`, `step_cost`, `get_heuristic_context`; loader `load_board`; 20 level JSON. | Đã có; chưa có bộ test tự động |
| TV3 + TV4 | `solve_bfs`, `solve_dfs`, `solve_ucs`, `solve_astar` cùng trả `SearchResult` (path + search time, memory, expanded nodes, solution length, total cost, preprocessing time). | Đã có; H2 admissible (lập luận + thực nghiệm), chưa consistent ở 2 level |
| TV5 | GUI tải level, chơi thủ công, hiển thị đúng ok/fall/illegal, split/bridge, undo/restart, solve và replay qua API. | Đã tích hợp |
| Lead | `python -m experiments.run_experiments` trên 120 case cố định (`experiments/test_set.json`) × 4 thuật toán. | Đã chạy 480/480 solved |

Tiêu chí tích hợp chi tiết: `docs/gui_api.md` §8.

---

## 4. Luồng chơi thủ công (ví dụ phím phải)

```text
Phím / vuốt → GUI ánh xạ thành "RIGHT"
→ PythonEngineAPI gửi POST /transition {level, state, action}
→ server.py kiểm tra request, khôi phục State
→ Engine.transition(state, Action.RIGHT)
→ server.py trả TransitionResult JSON
→ GUI: ok → push history, nhận state mới, animate (isGoal → thắng)
        fall → giữ state, lăn tới fall_state rồi rơi, khóa ở trạng thái thua
        illegal → giữ state, báo hành động không hợp lệ
```

Restart tải lại `GET /levels/{name}`; undo khôi phục snapshot GUI lưu. Backend
không giữ phiên chơi.

---

## 5. Nguyên tắc tích hợp

1. Chỉ Engine chứa luật chơi và quyết định successor state.
2. Trình duyệt chỉ gọi Python qua `PythonEngineAPI` → `server.py`.
3. Đổi schema board/state/action phải đồng bộ Engine, server, GUI, `docs/api.md`
   và `docs/gui_api.md` trong cùng thay đổi.
4. GUI chỉ commit state mới khi `status == ok`; `fall_state` chỉ dùng cho animation.
5. Chạy GUI bằng `python server.py` (hoặc
   `python -m uvicorn server:app --reload --host 127.0.0.1 --port 8000`); static
   server như `python -m http.server` không có các route API.

---

## Phụ lục — Lịch gốc của nhóm (lịch sử)

Giữ để tham khảo; không phản ánh trạng thái hiện tại.

| Ngày | Mục tiêu |
| --- | --- |
| 16/10 | Chốt kiến trúc, khảo sát code và repo tham khảo (xác nhận license), chốt biểu diễn State/tile/tọa độ, tạo branch Engine. |
| 17/10 | Core mechanics: Board/State/Action, bốn hướng và ba orientation, kiểm tra tile/biên/goal, hash/equality, bàn giao API sơ bộ cho Solver. |
| 18/10 | Advanced mechanics: fragile, soft/heavy switch, toggle/permanent bridge, split/merge và active cube. |
| 19/10 | Tích hợp: cho Solver chạy trên Engine thật, kiểm tra `step_cost`, goal, hashing; chốt API với GUI. |
| 20/10 | Đóng gói: merge qua pull request, cập nhật README và ví dụ, xác nhận Solver/GUI gọi được Engine. |

Repo tham khảo đã khảo sát:

- https://github.com/aimacode/aima-python/tree/59fa07ce33a2ddaf4fd5f6c8015c81202fbc6085
- https://github.com/ugurmengilli/bloxorz-ai-solver
- https://github.com/YesterKo/bloxorz-solver-py
- https://github.com/VLTisME/CSC14003-Bloxorz
