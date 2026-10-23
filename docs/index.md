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
| API contract Engine (authoritative)          | `api.md`                      | `game/engine.py`, `game/__init__.py`      |
| Contract GUI / integration (wire format)     | `gui_api.md`                  | `server.py`, `gui/index.html`             |
| Ranh giới module / luồng dữ liệu             | `Mô tả công việc.md`          | `game/`, `solvers/`, `gui/`              |
| Yêu cầu môn học / rubric                     | `AI - Project 1.docx`         | —                                        |
| Trạng thái hiện tại, blocker, delete-zone    | `status.md`                   | `git status`, inspect code and API docs    |
| Lịch sử thay đổi                             | `CHANGELOG.md`                | `git diff`, `git log`                     |
| Vai trò & lịch gốc (đã lịch sử)              | `plan.md`                     | `git log`                                |

## 3. Module map (ownership)

| Stream      | Owner  | Thư mục      | Trạng thái                                        |
| ----------- | ------ | ------------ | ------------------------------------------------- |
| Game Engine | TV1/2  | `game/`      | IMPLEMENTED (core + advanced mechanics)           |
| AI Solver   | TV3/4  | `solvers/`   | IMPLEMENTED (BFS/DFS/UCS/A*)                      |
| GUI         | TV5    | `gui/`       | INTEGRATED (`index.html`); Python GUI stubs chưa dùng |
| Integration | lead   | `server.py`, `experiments/` | `server.py` phục vụ GUI/API; benchmark tự động chạy trên 20 level GUI; `main.py` vẫn rỗng |

Chi tiết ranh giới code: `Agents.md` §"Architecture rules".

## 4. Liên kết chéo nhanh

- Contract Engine authoritative: `api.md`
- Contract GUI/integration: `gui_api.md`
- Log thay đổi: `CHANGELOG.md`
- Status + delete-zone: `status.md`
- Hướng dẫn luồng UI/API: `Hướng dẫn UI.md`
