# Thực nghiệm và đánh giá hiệu năng

Thư mục này chứa bộ dữ liệu benchmark cố định 120 case (100 bản đồ thiết kế độc lập + 20 level GUI), cùng các tập lệnh dùng để so sánh BFS, DFS, UCS và A* trên cùng một tập hợp bài toán tìm kiếm.

## Các tệp trong thư mục

- `test_set.json`: Bộ dữ liệu cố định gồm 120 case. Không thay đổi tệp này giữa các lần chạy thuật toán để đảm bảo tính công bằng khi so sánh.
- `benchmark.py`: Chứa danh sách đăng ký thuật toán giải và cơ chế xử lý thời gian chờ (timeout) dùng chung.
- `build_test_set.py`: Nhúng 20 level GUI (`levels/level*.json`) vào `test_set.json` dưới dạng case `GUI-001`…`GUI-020`. ID lấy theo số trong tên file (`level7.json` → `GUI-007`), nên không bị lệch khi thêm hoặc xoá level. Chạy lại được nhiều lần: chỉ thay phần case GUI, giữ nguyên 100 case độc lập, và cập nhật `groups`, `cases_per_group` theo dữ liệu thật.
- `run_experiments.py`: Điểm khởi chạy benchmark, đọc dữ liệu bản đồ được nhúng trong bộ dữ liệu.
- `verify_heuristic.py`: Kiểm chứng thực nghiệm admissible/consistent của H2 và H1 trên toàn bộ state đạt được của từng case; ghi `heuristic_check.csv`.
- `results.csv` và tệp metadata tương ứng: Lưu kết quả đo lường từ bộ dữ liệu test_set.json.
- `analysis.ipynb`: Notebook để phân tích và trực quan hóa kết quả.

## Thiết kế bộ dữ liệu

Bộ dữ liệu gồm hai phần:

- **`BXN-001`…`BXN-100`**: 100 bản đồ 13 × 17 được thiết kế độc lập, không lấy từ hoặc suy ra từ level GUI.
- **`GUI-001`…`GUI-020`**: 20 level GUI (`level1.json`…`level20.json`), nhúng nguyên bản, gồm cả heavy switch và split switch.

Mỗi trường hợp chứa đầy đủ định nghĩa bản đồ và trạng thái khởi đầu chuẩn tắc (canonical initial state). Vì vậy, quá trình benchmark không đọc `levels/`. Nếu sửa level GUI, chạy `python -m experiments.build_test_set` để cập nhật test set rồi chạy lại benchmark.

100 case độc lập được chia đều thành bốn nhóm, mỗi nhóm gồm 25 trường hợp (`design_constraints.independent_cases_per_group`):

- **`basic`**: Địa hình thông thường, không có ô dễ vỡ, cầu hoặc công tắc.
- **`fragile`**: Có các ô dễ vỡ, được đặt ngoài một đường đi hợp lệ đã biết.
- **`switches_bridges`**: Công tắc mềm điều khiển một cây cầu đang đóng ở trạng thái ban đầu.
- **`combined`**: Kết hợp ô dễ vỡ với cầu được điều khiển bằng công tắc và đang đóng ở trạng thái ban đầu.

Case GUI được xếp nhóm theo mechanics có trên board, khớp với định nghĩa nhóm:

- Level có heavy hoặc split switch thuộc nhóm thứ năm **`advanced_switches`** (11 level: 7, 8, 9, 10, 13, 14, 15, 17, 18, 19, 20). Các mechanics này không có trong 100 case độc lập.
- 9 level còn lại vào bốn nhóm trên: `basic` 3, `fragile` 3, `switches_bridges` 3 (chỉ có bridge và soft switch).

Số case thật của từng nhóm (`design_constraints.cases_per_group`): `basic` 28, `fragile` 28, `switches_bridges` 28, `combined` 25, `advanced_switches` 11.

Tất cả các trường hợp đều đã được phân tích cú pháp và giải thành công bằng BFS. Mỗi case độc lập còn đáp ứng hai điều kiện (case GUI giữ nguyên, không lọc theo điều kiện này):

- Độ dài lời giải tối ưu được BFS xác minh đạt ít nhất 18 hành động.
- Số trạng thái được BFS mở rộng đạt ít nhất 100.

Các điều kiện này xác nhận tính hợp lệ và mức độ không tầm thường của bài toán, nhưng không đảm bảo mọi thuật toán đều tìm được lời giải có cùng độ dài. Đặc biệt, DFS không đảm bảo tìm được lời giải tối ưu.

Nhãn độ khó được phân chia gần đúng dựa trên độ dài lời giải tối ưu đã xác minh bằng BFS:

- **Easy**: Dưới 22 hành động.
- **Medium**: Từ 22 đến 31 hành động.
- **Hard**: Từ 32 hành động trở lên.

Độ dài lời giải chỉ là một chỉ số đại diện cho độ khó. Số trạng thái được mở rộng, hệ số phân nhánh và mức độ tương tác giữa các ô đặc biệt cũng ảnh hưởng đến độ khó thực tế.

## Cách chạy benchmark

Chạy các lệnh sau từ thư mục gốc của repository bằng PowerShell, sau khi đã kích hoạt `.venv`.

Chạy benchmark với cả bốn thuật toán trên 120 trường hợp, tương ứng tổng cộng 480 lượt chạy:

    python -m experiments.run_experiments

Thời gian chờ mặc định là 15 giây cho mỗi thuật toán trên mỗi trường hợp.

Để chạy lặp lại mỗi trường hợp ba lần:

    python -m experiments.run_experiments --repeat 3

Một số tùy chọn hữu ích khác:

- Tăng thời gian chờ lên 30 giây cho mỗi lượt chạy:

      python -m experiments.run_experiments --timeout 30

- Chỉ chạy BFS và A*:

      python -m experiments.run_experiments --algorithms BFS "A*"

- Ghi kết quả vào một tệp CSV riêng để giữ lại kết quả cũ:

      python -m experiments.run_experiments --output experiments/results_trial.csv

Mỗi lần chạy sẽ ghi đè tệp CSV được chỉ định và tạo thêm một tệp metadata tương ứng có hậu tố `_metadata.json`. Metadata ghi đường dẫn tương đối so với gốc repo (ví dụ `experiments/test_set.json`). Hãy sử dụng đường dẫn `--output` khác nhau nếu muốn lưu giữ và so sánh kết quả từ nhiều lần chạy.

## Các chỉ số đánh giá

Benchmark ghi nhận các chỉ số sau:

- **`search_time_seconds`**: Thời gian tìm kiếm do thuật toán giải báo cáo, tính bằng giây. Thời gian tiền xử lý heuristic của A* không được tính vào chỉ số này mà được ghi riêng.
- **`preprocessing_time_seconds`**: Thời gian dựng bảng H2 của A*. Runner xoá cache H2 (`clear_h2_cache()`) trước mỗi lượt, nên A* luôn tự dựng bảng. Nhờ vậy giá trị này và `peak_memory_mb` phản ánh chi phí thật, kể cả với `--repeat` > 1.
- **`peak_memory_mb`**: Bộ nhớ cấp phát đỉnh được đo bằng `tracemalloc`, tính theo MB thập phân. Chỉ số này không đại diện cho tổng dung lượng bộ nhớ RAM mà toàn bộ tiến trình sử dụng (RSS).
- **`expanded_nodes`**: Số trạng thái được thuật toán mở rộng. Trạng thái đích không được tính vào chỉ số này.
- **`solution_length`**: Số hành động trong đường đi được trả về.
- **`total_cost`**: Tổng chi phí của đường đi, được tính bằng cách cộng `Engine.step_cost` cho từng bước.
- **`status`**: Trạng thái kết thúc của lượt chạy, gồm `solved`, `unsolved`, `timeout` hoặc `error`.

## Kết quả gần nhất

Lượt chạy `20261026T065916Z` (timeout 15 s, `repeat 1`): 480/480 lượt solved, không timeout, không error. Giá trị trung bình:

| Thuật toán | Phần | Search time (s) | Peak memory (MB) | Expanded nodes | Solution length | Total cost |
| --- | --- | --- | --- | --- | --- | --- |
| BFS | 120 case | 0.0426 | 0.072 | 418.9 | 27.21 | 32.34 |
| DFS | 120 case | 0.0216 | 0.045 | 196.3 | 94.03 | 113.69 |
| UCS | 120 case | 0.0433 | 0.094 | 392.0 | 27.21 | 32.30 |
| A* | 120 case | 0.0123 | 0.160 | 87.2 | 27.21 | 32.30 |
| BFS | 100 BXN | 0.0212 | 0.035 | 240.3 | 24.32 | 28.85 |
| DFS | 100 BXN | 0.0174 | 0.036 | 168.5 | 76.94 | 90.36 |
| UCS | 100 BXN | 0.0230 | 0.048 | 239.5 | 24.32 | 28.81 |
| A* | 100 BXN | 0.0036 | 0.135 | 26.2 | 24.32 | 28.81 |
| BFS | 20 GUI | 0.1497 | 0.258 | 1312.0 | 41.65 | 49.79 |
| DFS | 20 GUI | 0.0425 | 0.092 | 335.7 | 179.45 | 230.31 |
| UCS | 20 GUI | 0.1449 | 0.323 | 1154.3 | 41.65 | 49.72 |
| A* | 20 GUI | 0.0557 | 0.282 | 392.4 | 41.65 | 49.72 |

Expanded nodes theo nhóm (trung bình):

| Nhóm | Số case | BFS | DFS | UCS | A* |
| --- | --- | --- | --- | --- | --- |
| `basic` | 28 | 189.8 | 153.7 | 188.5 | 25.2 |
| `fragile` | 28 | 184.1 | 144.8 | 183.9 | 29.2 |
| `switches_bridges` | 28 | 286.5 | 178.1 | 287.1 | 30.8 |
| `combined` | 25 | 261.7 | 174.2 | 258.4 | 28.9 |
| `advanced_switches` | 11 | 2294.6 | 532.9 | 2009.7 | 669.1 |

A* có thêm `preprocessing_time_seconds` trung bình 0.0183 s cho việc dựng H2. Total cost của A* trùng UCS ở cả 120 case. So với lượt `20261026T040427Z` (trước khi H2 giữ ∞ và trước khi thêm `Engine.successors`), các cột `status`, `expanded_nodes`, `solution_length` và `total_cost` trùng nhau ở cả 480 dòng. Expanded nodes của A* không đổi vì trên 120 case, A* không mở rộng state ngõ cụt nào trước khi tới goal. Thời gian phụ thuộc máy; xem `results_metadata.json` để biết môi trường chạy.

## Kiểm chứng heuristic

    python -m experiments.verify_heuristic

Duyệt toàn bộ state đạt được của 120 case (115.043 state, 379.858 cạnh `OK`), tính chi phí tối ưu thật h* bằng reverse Dijkstra từ goal, rồi kiểm tra:

| Heuristic | Vi phạm admissible | Vi phạm consistent | h(goal) ≠ 0 |
| --- | --- | --- | --- |
| `H2` (đúng hàm A* dùng, giữ ∞ cho ngõ cụt) | 0 | 0 | 0 |
| `H1` (baseline) | 0 | 21 (GUI-008/009/010/015/017) | 0 |

Trước 2026-10-26, H2 đổi ∞ thành 0 và có 84 vi phạm consistent (GUI-015: 60, GUI-017: 24). Bản hiện tại giữ ∞, và A* bỏ các state có h = ∞ khỏi frontier. Lập luận chứng minh: `docs/deep-research-report.md`, mục "Điều chỉnh khi cài đặt".
