# Docs Index — Map

> **Role: Map.** Mô tả repo có gì, nằm ở đâu, ai sở hữu, và đọc file nào tiếp theo.
> Không chứa status hay quyết định. Status → `status.md`; lịch sử → `engine.md`.
>
> **Read order khi vào session:** đọc Map này → `status.md` (blockers + delete-zone) →
> chỉ phần history/ADR liên quan tới task.

## 1. Bốn vai trò tài liệu (mỗi fact một canonical owner)

| Vai trò       | Canonical source                          | Việc của nó                                              |
| ------------- | ----------------------------------------- | -------------------------------------------------------- |
| Constitution  | `AGENTS.md` (opencode), `GEMINI.md` (Gemini) | Quy tắc bắt buộc + link tới chi tiết canonical           |
| Map           | `index.md` (file này) + `AGENTS.md` §Repo layout | Cái gì tồn tại, ownership, đọc file nào                  |
| Status        | `status.md`                          | Sức khoẻ hiện tại, blocker, delete-zone                   |
| History       | `engine.md`                          | Quyết định bền vững, removal/replacement, incident       |

## 2. Jump table — "cần X thì đọc đâu, verify bằng gì"

| Cần                                          | Đọc tại                            | Verify bằng                              |
| -------------------------------------------- | ---------------------------------- | ---------------------------------------- |
| API contract Engine (authoritative)          | `api.md`                      | `game/engine.py`, `game/__init__.py`, tests |
| Contract GUI / integration (wire format)     | `gui_api.md`                  | `server.py`                              |
| Ranh giới module / luồng dữ liệu             | `Mô tả công việc.md`          | `game/`, `solvers/`, `gui/`              |
| Hướng dẫn cài TV1 từng bước                  | `tv1_engine_guide.md`         | `game/`                                  |
| Yêu cầu môn học / rubric                     | `bloxorz_project_requirements.md` | —                                    |
| Trạng thái hiện tại, blocker, delete-zone    | `status.md`                   | `git status`, `uv run pytest -q`         |
| Quyết định / removal / incident              | `engine.md`                   | `git log`                                |
| Vai trò & lịch gốc (đã lịch sử)              | `plan.md`                     | `git log`                                |

## 3. Module map (ownership)

| Stream      | Owner  | Thư mục      | Trạng thái                                        |
| ----------- | ------ | ------------ | ------------------------------------------------- |
| Game Engine | TV1/2  | `game/`      | IMPLEMENTED (core + advanced mechanics)           |
| AI Solver   | TV3/4  | `solvers/`   | IMPLEMENTED (BFS/DFS/UCS/A*)                      |
| GUI         | TV5    | `gui/`       | EMPTY (chưa bắt đầu)                              |
| Integration | lead   | `main.py`, `server.py`, `experiments/` | `server.py` OK; `main.py`, `experiments/` EMPTY |

Chi tiết ownership đầy đủ: `AGENTS.md` §"Module ownership".

## 4. Liên kết chéo nhanh

- Contract Engine authoritative: `api.md`
- Contract GUI/integration: `gui_api.md`
- Log quyết định (append-only): `engine.md`
- Status + delete-zone: `status.md`
- Hướng dẫn onboarding engine: `tv1_engine_guide.md`
