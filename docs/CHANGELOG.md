# Changelog

## 2026-10-26

- Rà soát tài liệu so với code và gộp các file `.md` trùng lặp: xoá `docs/API_CONTRACT.md` (bản sao cũ của `docs/gui_api.md`), gộp `docs/Hướng dẫn UI.md` vào `docs/gui_api.md`, gộp `docs/plan.md` vào phụ lục `docs/Mô tả công việc.md`, gộp `BENCHMARK_LEVELS.md` vào `experiments/README.md`. Rút gọn `Mô tả công việc.md` thành tài liệu phân công, trỏ sang `api.md`/`gui_api.md` thay vì chép lại API (bỏ cả ghi chú cũ `cost = 1`).
- Sửa sai lệch với code: `docs/api.md` (danh sách export của `game`/`solvers`, `Engine(board, cost_config)`, `get_heuristic_context()`, `TileType` nằm ở `game/board.py`, tên helper thật trong §6.5, bỏ "DFS/IDS"); `docs/gui_api.md` (cấu trúc thật của `gui/index.html` thay cho `web/src/*.js`, metrics solver đang bị ẩn bằng CSS, điều khiển hiện tại); `docs/index.md` (PDF yêu cầu thay vì `.docx`, thêm benchmark/nghiên cứu H2); `docs/Agents.md` (vuốt thay cho nút hướng); comment trong `gui/index.html` trỏ tới `docs/gui_api.md`. README rút gọn phần benchmark và trỏ tới `experiments/README.md`.
- Kiểm tra đã chạy: đối chiếu số liệu trung bình trong `experiments/results.csv` với bảng kết quả (khớp), grep liên kết tới các file đã xoá. Không chạy server/GUI; chỉ đổi tài liệu và một dòng comment.
- Gộp tài liệu H2: thêm mục "Điều chỉnh khi cài đặt (đối chiếu với code)" vào `docs/deep-research-report.md` (ánh xạ báo cáo → `h2.py`, trọng số cost 1.5/1.0, `SWITCH_CUBE` không có cạnh, `HeuristicContext`, lập luận admissible/consistent, phần nên dùng/bỏ cho report); xoá `docs/h2 heuristic research.md`, vốn mô tả phương án split-safe không còn được dùng.
- Xoá code không có chỗ gọi: H2 `split_aware=False` (`_build_h2_safe_cached`), `clear_h2_cache`, tham số `use_cache`/`split_aware` của `build_h2`; `Board.bridge_at`/`switch_at` cùng `board.Bridge`/`Switch`/`SwitchTarget`/`_as_cell` (bỏ khỏi export của `game`); `tiles.is_cell_supported`; alias `engine._ROLL_TABLE`; `HeuristicContext.split_switch_cells`; các file rỗng `main.py`, `gui/__init__.py`, `gui/app.py`, `gui/controller.py`, `gui/renderer.py`. Cập nhật `api.md`, `gui_api.md`, `index.md`, `status.md`, README.
- Kiểm tra đã chạy: `python -m compileall -q game solvers experiments server.py` và import `game, solvers, server` (giống CI); chạy A* trên 20 level, kết quả trùng `experiments/results.csv` (cùng expanded nodes, solution length, total cost). Chưa chạy GUI trên trình duyệt; chưa chạy lại toàn bộ benchmark.
- Khôi phục benchmark trên test set cố định 100 mẫu (`experiments/test_set.json`, `run_experiments.py`, `README.md` của commit `4998551`), bỏ benchmark trên 20 level GUI (`discover_gui_levels`/`classify_level`). Bỏ nhánh legacy đọc `levels/` trong runner vì mọi case đều nhúng board; `load_dataset` từ chối case thiếu `board`. Cập nhật README, `experiments/README.md` (bảng kết quả mới), `status.md`, `index.md`, `api.md`, `Mô tả công việc.md`. Sửa ký tự điều khiển lọt vào LaTeX (`lpha`, `	ext`, `	o`) trong mục điều chỉnh của `deep-research-report.md`.
- Kiểm tra đã chạy: kiểm tra trùng trong test set (không trùng `case_id`, grid hay địa hình; không case nào trùng level GUI); `python -m experiments.run_experiments` đầy đủ: 400/400 solved, 0 timeout, 0 error, total cost A* = UCS ở cả 100 case; `compileall` và `--help`.
- Gộp test set thành 120 case: thêm `experiments/build_test_set.py`, nhúng 20 level GUI vào `test_set.json` (`GUI-001`…`GUI-020`, board nhúng sẵn, group theo mechanics, difficulty và reference BFS tính lại; `dataset_version` 3). Runner không đổi và vẫn không đọc `levels/`. Chạy lại benchmark: 480/480 solved.
- Kiểm chứng heuristic: thêm `experiments/verify_heuristic.py` (duyệt toàn bộ state đạt được, tính h* chính xác, kiểm tra admissible/consistent cho H2, H2 giữ ∞ và H1; ghi `experiments/heuristic_check.csv`). Tách `H2Heuristic.distance` (trả d_alpha, giữ ∞) khỏi `__call__` (vẫn fallback ∞ → 0, hành vi A* không đổi). Viết chứng minh (Bổ đề 1, Mệnh đề 2–3) vào `docs/deep-research-report.md`. Cập nhật README, `experiments/README.md`, `status.md`, `index.md`, `api.md`, `gui_api.md`, `Mô tả công việc.md`.
- Kiểm tra đã chạy: `build_test_set` chạy hai lần cho cùng file (idempotent, 120 `case_id` không trùng); `verify_heuristic` trên 120 case (115.043 state, 379.858 cạnh): H2 0 vi phạm admissible, 84 vi phạm consistent (GUI-015: 60, GUI-017: 24); H2 giữ ∞ 0/0; H1 0 vi phạm admissible, 21 vi phạm consistent. `run_experiments`: 480/480 solved, total cost A* = UCS ở mọi case; 80 dòng của 20 case GUI trùng hoàn toàn với `results.csv` trước đó (status, expanded nodes, solution length, total cost). `compileall`, import `game, solvers, server`, `--help` của ba script. Chưa chạy lại `analysis.ipynb`; chưa chạy GUI.

## 2026-10-22

- Đồng bộ tài liệu với GUI hiện tại: bảng `DI CHUYỂN` rộng 250px trên desktop và 210px trên màn hình hẹp; bốn nút hướng đã được bỏ, giữ điều khiển bằng bàn phím và vuốt.
- Thêm `.github/workflows/ci.yml` để branch `gui_v2` có check status tự động cho syntax và import smoke check.
- Thêm `BENCHMARK_LEVELS.md` với kết quả chạy 11 màn bằng BFS, DFS, UCS và A*.

## 2026-10-21

- Tăng chữ metrics lời giải trong `DI CHUYỂN` từ 8px lên 12px, và 7px lên 11px ở cửa sổ thấp; giảm khoảng cách lưới trong chế độ cửa sổ thấp để giữ bảng gọn. Cập nhật README. Chưa chạy browser/test.
- Rà soát lỗi hiển thị bảng `DI CHUYỂN`: hợp nhất các khai báo CSS trùng lặp, đưa cấu hình chiều rộng về một bộ breakpoint thống nhất, giữ nội dung hai cột và bỏ giới hạn cuộn riêng ở cả bảng lẫn khung cha. Route `/` đã trỏ tới `gui/index.html`; tại lúc kiểm tra không có server lắng nghe cổng 8000 nên chưa xác nhận được trang thực tế trên trình duyệt. Cập nhật README; chưa chạy browser/test.
- Mở rộng bảng điều khiển để hiện đầy đủ lựa chọn màn, thuật toán, metrics và replay mà không cuộn; bỏ bốn nút hướng trên GUI, giữ điều khiển bằng phím và vuốt. Cập nhật README. Chưa chạy browser/test.

## 2026-10-20

- Đưa bộ chọn BFS/DFS/UCS/A* và nút `SOLVE` lên đầu bảng điều khiển để dễ thấy; thêm nhãn thuật toán và cuộn nội bộ cho bảng ở màn hình thấp. Cập nhật README. Chưa chạy browser/test.
- Đồng bộ tài liệu với code hiện tại: state HTTP không chứa `occupied_cells`; GUI đã gọi `/solve` và phát lại action; phân biệt chứng minh của heuristic nghiên cứu với bảo đảm chưa được xác nhận của H2 trong implementation. Giữ các mục changelog cũ như lịch sử.
- Sửa lỗi cú pháp JavaScript trong `autoSolve()`: bỏ khai báo `const metrics` trùng khiến toàn bộ module GUI dừng trước khi dựng bàn và tải danh sách level. README bổ sung cách chẩn đoán khi chỉ hiện HUD/nền; xác nhận vị trí lỗi từ Console người dùng và rà diff tĩnh, chưa chạy browser/test.
- Đồng bộ runtime solver: tuần tự hóa đo peak memory, thêm hủy hợp tác cho timeout ở BFS/DFS/UCS/A* và H2, báo riêng thời gian preprocessing A*, thống nhất `expanded_nodes`, và từ chối cost âm/không hữu hạn. Cập nhật SearchResult wire field, GUI, README, contract, hướng dẫn, phân công và status/map; sửa lệnh cài đặt theo `requirements.txt`, ghi rõ test/CI chưa có và không tuyên bố H2 tối ưu khi chưa xác nhận. Chưa chạy test hoặc khởi chạy server.
- Nối GUI với `/solve`: bật chọn BFS/DFS/UCS/A*, gửi state hiện tại, hiển thị metrics và replay action path qua `/transition`; xử lý endpoint solver không khả dụng. Khôi phục controls sau các nhánh kết thúc tìm kiếm/lỗi; đồng bộ README, Agents, API contracts và hướng dẫn UI. Chưa chạy test hoặc mở GUI.

- Đồng bộ `game/` và `solvers/` từ commit `f6a3557` của `solver_v2`: thêm hình học lăn dùng chung, `HeuristicContext`, H1/H2, lớp solver cơ sở và cập nhật BFS/DFS/A*.
- Giữ tương thích giao diện hiện hành bằng cách khôi phục `fall_state` trong `TransitionResult`; Engine trả hình học đích bị rơi cho cả lỗi hỗ trợ trước và sau hiệu ứng ô. Trường này chỉ dùng cho animation, không commit state.
- Cập nhật README và tài liệu API/nghiên cứu để ghi rõ cấu hình cost và H2 hiện có; GUI solver vẫn khóa. Chưa chạy test hoặc khởi chạy ứng dụng.

## 2026-10-20

- Chuyển bảng solver khỏi thẻ điều khiển và đặt cố định ở góc dưới bên trái viewport để không bị cắt khỏi khung nhìn; bố cục hẹp cũng dành riêng vị trí cho bảng.
- Thêm `levels/level0.json` với `F`, cầu `B`, công tắc mềm/nặng và split `P`; thêm bảng BFS/DFS/UCS/A* chỉ hiển thị trạng thái khóa trong GUI, giữ nguyên các level1–level10. Cập nhật README; chưa chạy kiểm thử Engine hoặc GUI.
- Bổ sung 10 file level JSON vào `levels/` từ gói `bloxorz_10_levels.zip` có sẵn trong workspace; xác nhận đủ tên level1–level10 và mỗi lưới có đúng một `S`/`G` bằng kiểm tra cấu trúc JSON. Chưa chạy kiểm thử Engine.
- Đưa chú giải ô đặc biệt lên cùng mép trên với nút RESTART; áp dụng cả màn hình lớn và bố cục hẹp.
- Sắp xếp danh sách level theo thứ tự tự nhiên (`level1` … `level10`) trong `GET /levels`.
- Bổ sung `fall_state` chỉ dùng cho trình bày vào kết quả transition `fall`; GUI lăn đến ô bẫy theo hình học Engine trả về rồi mới thả khối, không đổi logical state.
- Nâng vị trí dòng hướng dẫn chơi trên viewport để tránh sát đáy.
- Cập nhật README và tài liệu API/Python cho thứ tự level và trường `fall_state`; không chạy test hoặc ứng dụng trong lượt này.

- Chuyển `occupied_cells` thành dữ liệu nội bộ backend: server tự suy ra/kiểm tra từ `State`; GUI đặt khối từ `block_position`, `orientation` và vị trí cube split.
- Tạm khóa nút/chọn thuật toán/tốc độ replay của Solver trong GUI; thêm guard để giao diện không gọi `/solve` khi đang khóa.
- Đồng bộ `docs/Agents.md`, `docs/gui_api.md`, `docs/API_CONTRACT.md`, tài liệu phân công và README với schema state và phạm vi UI hiện tại.
- Sửa mô tả tích hợp solver cũ: backend hiện có `/solve` và đăng ký bốn thuật toán; GUI vẫn tạm ngưng luồng này, còn chi phí/heuristic UCS/A* cần nhóm xác nhận.
- Rà soát tĩnh các luồng chuyển state; không chạy test hoặc ứng dụng trong lượt này.
