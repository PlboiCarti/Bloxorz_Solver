# Status

> **Role: Status.** Sức khoẻ hiện tại, blocker, và delete-zone.
> Không chứa cấu trúc (xem `docs/index.md`) hay quyết định (xem `docs/engine.md`).
>
> Cập nhật lần cuối: **2026-10-19**.

## 1. Sức khoẻ

| Thành phần                | Trạng thái                                                                 |
| ------------------------- | -------------------------------------------------------------------------- |
| Game Engine (TV1/TV2)     | IMPLEMENTED — core + advanced mechanics, có test riêng                    |
| AI Solver (TV3/TV4)       | IMPLEMENTED — `solvers/` BFS/DFS/UCS/A* + `SearchResult`                  |
| HTTP adapter              | IMPLEMENTED — `server.py` (FastAPI): `/levels`, `/levels/{name}`, `/transition`, `/solve` |
| GUI (TV5)                 | EMPTY — `gui/*.py` là file 0 byte                                          |
| Entrypoint                | EMPTY — `main.py` 0 byte                                                   |
| Experiments               | EMPTY — `experiments/*.py` 0 byte, `results.csv` rỗng                      |

- Toàn bộ test: **100 passed** (`uv run pytest -q`, ~5s).
- `ruff check .` và `pyright` sạch (`pyright` chỉ include `game` + `tests`).
- 10/10 `levels/level1-10.json` nạp + validate + khởi tạo state được.

## 2. Blocker / việc đang mở

| Việc                                   | Blocker cho                          | Ghi chú                                             |
| -------------------------------------- | ------------------------------------- | --------------------------------------------------- |
| GUI (`gui/app.py`, `controller.py`, `renderer.py`) | `main.py` chưa có entrypoint | Contract đã có sẵn ở `docs/gui_api.md`              |
| `main.py`                              | phụ thuộc GUI                          | Dự kiến khởi chạy `gui.app`                          |
| `experiments/`                         | phụ thuộc GUI + solver output         | `benchmark.py`, `run_experiments.py`, `results.csv` |
| `step_cost`                            | placeholder `1.0` (TEMPORARY)         | `docs/api.md` §6.2 — owner: team, consumer: TV4     |

## 3. Delete-zone

> Khu vực đã xoá/cấm tái tạo. Giữ lý do để tránh việc file bị tạo lại vô tình.

| Path / khái niệm                    | Vì sao bị xoá/bỏ                       | Thay thế                              | Điều kiện xem xét lại            |
| ----------------------------------- | -------------------------------------- | ------------------------------------- | ------------------------------- |
| `src/` layout                       | Chuyển sang top-level package          | `game/`, `solvers/`, `gui/` (không `src/`) | Không bao giờ reintroduce `src/` |
| `transition(...) -> State \| None`  | Thay bằng contract mới                 | `TransitionResult` (`TransitionStatus.OK/FALL/ILLEGAL`) | Chỉ dùng `TransitionResult` |
| `game/__init__.py` export list cũ   | Thiếu `TransitionResult`/`TransitionStatus` | `game/__init__.py` hiện tại        | Sửa qua `game/__init__.py` duy nhất |

## 4. Nguyên tắc cần nhớ khi cập nhật status

- Thay đổi cấu trúc/ownership → sửa **Map** (`docs/index.md`) trong cùng commit.
- Thay đổi blocker/threshold/milestone → sửa **Status** (file này).
- Quyết định khó đảo/removal/incident → thêm một dòng vào **History** (`docs/engine.md`).
