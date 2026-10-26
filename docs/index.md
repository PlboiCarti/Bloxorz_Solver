# Docs Index — Map

> **Role: Map.** Mô tả repo có gì, nằm ở đâu, ai sở hữu, và đọc file nào tiếp theo.
> Không chứa status hay quyết định. Status → `status.md`; lịch sử → `CHANGELOG.md`.
>
> **Read order khi vào session:** đọc Map này → `status.md` (blockers + delete-zone) →
> chỉ phần history/ADR liên quan tới task.

## 1. Bốn vai trò tài liệu (mỗi fact một canonical owner)

| Vai trò       | Canonical source                          | Việc của nó                                              |
| ------------- | ----------------------------------------- | -------------------------------------------------------- |
| Constitution  | `Agents.md`                          | Quy tắc repo và ranh giới code                            |
| Map           | `index.md` (file này)                | Cái gì tồn tại, ownership, đọc file nào                  |
| Status        | `status.md`                          | Sức khoẻ hiện tại, blocker, delete-zone                   |
| History       | `CHANGELOG.md`                       | Các thay đổi theo ngày                                   |

## 2. Jump table — "cần X thì đọc đâu, verify bằng gì"

| Cần                                          | Đọc tại                            | Verify bằng                              |
| -------------------------------------------- | ---------------------------------- | ---------------------------------------- |
| Cài đặt, chạy GUI, tổng quan                 | `../README.md`                     | `python server.py`                       |
| API contract Engine/solver (authoritative)   | `api.md`                           | `game/`, `solvers/__init__.py`           |
| Contract GUI/HTTP + luồng tích hợp GUI       | `gui_api.md`                       | `server.py`, `gui/index.html`            |
| Phân công, ranh giới module, lịch gốc        | `Mô tả công việc.md`               | `game/`, `solvers/`, `gui/`              |
| Benchmark: cách chạy và kết quả gần nhất     | `../experiments/README.md`         | `experiments/results.csv`                |
| Nghiên cứu và chứng minh H2 (nguồn cho report; đọc mục "Điều chỉnh khi cài đặt" trước) | `deep-research-report.md` | `solvers/heuristics/h2.py` |
| Yêu cầu môn học / rubric                     | `../AI - Project 1 (đã fix).pdf`   | —                                        |
| Trạng thái hiện tại, blocker, delete-zone    | `status.md`                        | `git status`, inspect code and API docs  |
| Lịch sử thay đổi                             | `CHANGELOG.md`                     | `git diff`, `git log`                    |

## 3. Module map (ownership)

| Stream      | Owner  | Thư mục      | Trạng thái                                        |
| ----------- | ------ | ------------ | ------------------------------------------------- |
| Game Engine | TV1/2  | `game/`      | IMPLEMENTED (core + advanced mechanics)           |
| AI Solver   | TV3/4  | `solvers/`   | IMPLEMENTED (BFS/DFS/UCS/A*)                      |
| GUI         | TV5    | `gui/`       | INTEGRATED (`gui/index.html`) |
| Integration | lead   | `server.py`, `experiments/` | `server.py` phục vụ GUI/API; benchmark chạy trên 20 level GUI |

Chi tiết ranh giới code: `Agents.md` §"Architecture rules".

## 4. Liên kết chéo nhanh

- Contract Engine authoritative: `api.md`
- Contract GUI/integration: `gui_api.md`
- Log thay đổi: `CHANGELOG.md`
- Status + delete-zone: `status.md`
- Benchmark: `../experiments/README.md`
