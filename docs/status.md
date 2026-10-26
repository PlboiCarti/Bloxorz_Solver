# Status

> **Role: Status.** Sức khoẻ hiện tại, blocker, và delete-zone.
> Không chứa cấu trúc (xem `docs/index.md`) hay lịch sử (xem `docs/CHANGELOG.md`).
>
> Cập nhật lần cuối: **2026-10-26**.

## 1. Sức khoẻ

| Thành phần                | Trạng thái                                                                 |
| ------------------------- | -------------------------------------------------------------------------- |
| Game Engine (TV1/TV2)     | IMPLEMENTED — core + advanced mechanics trong `game/`; chưa có test suite trong checkout |
| AI Solver (TV3/TV4)       | IMPLEMENTED — BFS/DFS/UCS/A* + `SearchResult`; timeout hủy hợp tác tại các checkpoint |
| HTTP adapter              | IMPLEMENTED — `server.py` (FastAPI): `/`, `/assets/{path}`, `/levels`, `/levels/{name}`, `/transition`, `/solve` (timeout 10 s) |
| GUI (TV5)                 | INTEGRATED — `gui/index.html` dùng Three.js và gọi API để chuyển trạng thái, solve/replay |
| Entrypoint                | `python server.py` (GUI + API)                                             |
| Experiments               | VERIFIED — test set cố định 120 case (`experiments/test_set.json`: 100 độc lập + 20 level GUI nhúng board, 5 nhóm gồm `advanced_switches` cho heavy/split switch); BFS/DFS/UCS/A* chạy 480 lượt, 480/480 solved |
| Automated checks          | CONFIGURED — `.github/workflows/ci.yml` chạy syntax/import smoke check; chưa có `tests/` |

- Chưa có test suite; CI chỉ chạy syntax/import smoke check. Benchmark và import/syntax check đã chạy thành công trong lượt cập nhật này.
- A* mặc định dùng H2. H2 admissible và consistent (chứng minh + `experiments/verify_heuristic.py`: 0 vi phạm trên 115.043 state / 379.858 cạnh của 120 case), nên A* tối ưu. H2 trả ∞ cho ngõ cụt, và A* bỏ các state đó khỏi frontier (bỏ fallback ∞ → 0 từ 2026-10-26).
- Cost hiện tại là `stand_roll=1.5`, `lie_roll=1.0`, `switch_cube=0.1`; `bridge_cross_penalty=0.3` chưa được dùng. Đây là hành vi code hiện tại, chưa phải quyết định cost cuối cùng của nhóm.

## 2. Blocker / việc đang mở

| Việc                                   | Blocker cho                          | Ghi chú                                             |
| -------------------------------------- | ------------------------------------- | --------------------------------------------------- |
| Cost semantics                         | Cần thống nhất trong nhóm             | `docs/api.md` §6.2; `bridge_cross_penalty` hiện chưa áp dụng |
| Automated validation                  | Checkout chưa có test suite            | Bổ sung kiểm tra Engine, các solver, timeout và API trước nghiệm thu; CI hiện chỉ là smoke check |
| `experiments/`                         | Benchmark 120 case cố định đã chạy      | Phân tích số liệu, bảng/biểu đồ và thảo luận trong report |

## 3. Delete-zone

> Khu vực đã xoá/cấm tái tạo. Giữ lý do để tránh việc file bị tạo lại vô tình.

| Path / khái niệm                    | Vì sao bị xoá/bỏ                       | Thay thế                              | Điều kiện xem xét lại            |
| ----------------------------------- | -------------------------------------- | ------------------------------------- | ------------------------------- |
| `src/` layout                       | Chuyển sang top-level package          | `game/`, `solvers/`, `gui/` (không `src/`) | Không bao giờ reintroduce `src/` |
| `transition(...) -> State \| None`  | Thay bằng contract mới                 | `TransitionResult` (`TransitionStatus.OK/FALL/ILLEGAL`) | Chỉ dùng `TransitionResult` |
| `game/__init__.py` export list cũ   | Thiếu `TransitionResult`/`TransitionStatus` | `game/__init__.py` hiện tại        | Sửa qua `game/__init__.py` duy nhất |
| `docs/API_CONTRACT.md`              | Bản sao cũ của `gui_api.md`            | `docs/gui_api.md`                     | Không tạo lại bản sao contract    |
| `docs/Hướng dẫn UI.md`              | Trùng `gui_api.md` + `api.md`          | `docs/gui_api.md` §5–§8               | —                               |
| `docs/plan.md`                      | Lịch đã lịch sử, trùng phân công      | Phụ lục của `docs/Mô tả công việc.md` | —                               |
| `BENCHMARK_LEVELS.md`               | Trùng phần benchmark                   | `experiments/README.md` §Kết quả gần nhất | —                           |
| Runner đọc trực tiếp `levels/` (`discover_gui_levels`) | Test set phải cố định, không đổi theo level GUI | Level GUI nhúng vào `test_set.json` qua `experiments/build_test_set.py` | — |
| `main.py`, `gui/app.py`, `gui/controller.py`, `gui/renderer.py`, `gui/__init__.py` | File rỗng, không dùng | `server.py`, `gui/index.html` | Chỉ khi thật sự làm GUI desktop |
| `docs/h2 heuristic research.md`     | Phương án split-safe H2 không còn trong code | `docs/deep-research-report.md` §Điều chỉnh khi cài đặt | — |
| H2 fallback ∞ → 0, `H2Heuristic.distance`, cột `H2_inf` | Fallback làm H2 mất consistency (84 cạnh ở `level15`/`level17`) | `H2Heuristic.__call__` trả ∞; A* bỏ state h = ∞ | — |
| H2 `split_aware=False`, `Board.bridge_at/switch_at`, `board.Bridge/Switch/SwitchTarget`, `tiles.is_cell_supported`, `engine._ROLL_TABLE`, `HeuristicContext.split_switch_cells` | Không có chỗ gọi | H2 split-aware; `game/switches.py` | — |
| `web/src/*.js` layout               | Chưa từng được tạo                     | Inline module trong `gui/index.html`  | Chỉ khi tách GUI thành module thật |

## 4. Nguyên tắc cần nhớ khi cập nhật status

- Thay đổi cấu trúc/ownership → sửa **Map** (`docs/index.md`) trong cùng commit.
- Thay đổi blocker/threshold/milestone → sửa **Status** (file này).
- Thay đổi cần lưu lịch sử → thêm một dòng vào `docs/CHANGELOG.md`.
