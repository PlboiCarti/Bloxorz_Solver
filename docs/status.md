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
| HTTP adapter              | IMPLEMENTED — `server.py` (FastAPI): `/levels`, `/levels/{name}`, `/transition`, `/solve` |
| GUI (TV5)                 | INTEGRATED — `gui/index.html` dùng Three.js và gọi API để chuyển trạng thái, solve/replay |
| Entrypoint                | `main.py` vẫn rỗng; chạy GUI/API bằng `python server.py`                   |
| Experiments               | VERIFIED — 20 level GUI; benchmark BFS/DFS/UCS/A* chạy 80 lượt, 80/80 solved |
| Automated checks          | CONFIGURED — `.github/workflows/ci.yml` chạy syntax/import smoke check; chưa có `tests/` |

- Chưa có test suite; CI chỉ chạy syntax/import smoke check. Benchmark và import/syntax check đã chạy thành công trong lượt cập nhật này.
- A* mặc định dùng H2 split-aware; admissibility/consistency cần được đối chiếu với semantics cuối cùng trước khi công bố bảo đảm tối ưu.
- Cost hiện tại là `stand_roll=1.5`, `lie_roll=1.0`, `switch_cube=0.1`; `bridge_cross_penalty=0.3` chưa được dùng. Đây là hành vi code hiện tại, chưa phải quyết định cost cuối cùng của nhóm.

## 2. Blocker / việc đang mở

| Việc                                   | Blocker cho                          | Ghi chú                                             |
| -------------------------------------- | ------------------------------------- | --------------------------------------------------- |
| H2 admissibility/consistency           | Chưa có xác nhận bằng kiểm tra đối chiếu | Không tuyên bố A* tối ưu đến khi xác nhận với cost và transition cuối |
| Cost semantics                         | Cần thống nhất trong nhóm             | `docs/api.md` §6.2; `bridge_cross_penalty` hiện chưa áp dụng |
| Automated validation                  | Checkout chưa có test suite            | Bổ sung kiểm tra Engine, các solver, timeout và API trước nghiệm thu; CI hiện chỉ là smoke check |
| `experiments/`                         | Benchmark 20 level GUI đã chạy          | Phân tích số liệu, bảng/biểu đồ và thảo luận trong report |
| `main.py`                              | Chưa phải entrypoint                   | Dùng `python server.py` để chạy GUI cùng API          |

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
| `web/src/*.js` layout               | Chưa từng được tạo                     | Inline module trong `gui/index.html`  | Chỉ khi tách GUI thành module thật |

## 4. Nguyên tắc cần nhớ khi cập nhật status

- Thay đổi cấu trúc/ownership → sửa **Map** (`docs/index.md`) trong cùng commit.
- Thay đổi blocker/threshold/milestone → sửa **Status** (file này).
- Thay đổi cần lưu lịch sử → thêm một dòng vào `docs/CHANGELOG.md`.
