# Bloxorz_Solver

Đồ án CSC14003 — Bloxorz AI Solver. Python 3.12, quản lý bằng `uv`.
Ba stream: **Game Engine** (TV1/2), **AI Solver** (TV3/4), **GUI + Integration** (TV5).

## Chạy nhanh

```bash
uv sync --dev
uv run pytest -q        # 100 tests
uv run ruff check .
uv run pyright         # chỉ check game/ + tests/
```

## Tài liệu

- **Map / index:** [`docs/index.md`](docs/index.md)
- **Status + delete-zone:** [`docs/status.md`](docs/status.md)
- **Contract Engine (authoritative):** [`docs/api.md`](docs/api.md)
- **Contract GUI / integration:** [`docs/gui_api.md`](docs/gui_api.md)
- **Lịch sử quyết định (append-only):** [`docs/engine.md`](docs/engine.md)
- **Quy tắc agent:** [`AGENTS.md`](AGENTS.md)

## Trạng thái ngắn

Engine, Solver và HTTP adapter đã IMPLEMENTED; GUI, `main.py` và `experiments/` còn EMPTY.
Xem [`docs/status.md`](docs/status.md) để biết blocker hiện tại.
