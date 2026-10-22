# Thực nghiệm và đánh giá hiệu năng

Thư mục này chứa bộ dữ liệu benchmark cố định, được thiết kế độc lập, cùng các tập lệnh dùng để so sánh BFS, DFS, UCS và A* trên cùng một tập hợp bài toán tìm kiếm.

## Các tệp trong thư mục

- `test_set.json`: Bộ dữ liệu cố định gồm 100 bản đồ được thiết kế mới. Không thay đổi tệp này giữa các lần chạy thuật toán để đảm bảo tính công bằng khi so sánh.
- `benchmark.py`: Chứa danh sách đăng ký thuật toán giải và cơ chế xử lý thời gian chờ (timeout) dùng chung.
- `run_experiments.py`: Điểm khởi chạy benchmark, đọc dữ liệu bản đồ được nhúng trong bộ dữ liệu.
- `results.csv` và tệp metadata tương ứng: Lưu kết quả đo lường từ bộ dữ liệu test_set.json.
- `analysis.ipynb`: Notebook để phân tích và trực quan hóa kết quả.

## Thiết kế bộ dữ liệu

Bộ dữ liệu gồm 100 bản đồ kích thước 13 × 17, được thiết kế độc lập. Các bản đồ không được lấy từ hoặc suy ra từ những level trong `levels/level0.json` đến `levels/level10.json`.

Mỗi trường hợp chứa đầy đủ định nghĩa bản đồ và trạng thái khởi đầu chuẩn tắc (canonical initial state). Vì vậy, quá trình benchmark không phụ thuộc vào các tệp level có sẵn trong repository.

Bộ dữ liệu được chia đều thành bốn nhóm, mỗi nhóm gồm 25 trường hợp:

- **`basic`**: Địa hình thông thường, không có ô dễ vỡ, cầu hoặc công tắc.
- **`fragile`**: Có các ô dễ vỡ, được đặt ngoài một đường đi hợp lệ đã biết.
- **`switches_bridges`**: Công tắc mềm điều khiển một cây cầu đang đóng ở trạng thái ban đầu.
- **`combined`**: Kết hợp ô dễ vỡ với cầu được điều khiển bằng công tắc và đang đóng ở trạng thái ban đầu.

Trước khi được đưa vào bộ dữ liệu, tất cả các trường hợp đều đã được phân tích cú pháp và giải thành công bằng BFS. Mỗi trường hợp đáp ứng hai điều kiện:

- Độ dài lời giải tối ưu được BFS xác minh đạt ít nhất 18 hành động.
- Số trạng thái được BFS mở rộng đạt ít nhất 100.

Các điều kiện này xác nhận tính hợp lệ và mức độ không tầm thường của bài toán, nhưng không đảm bảo mọi thuật toán đều tìm được lời giải có cùng độ dài. Đặc biệt, DFS không đảm bảo tìm được lời giải tối ưu.

Nhãn độ khó được phân chia gần đúng dựa trên độ dài lời giải tối ưu đã xác minh bằng BFS:

- **Easy**: Dưới 22 hành động.
- **Medium**: Từ 22 đến 31 hành động.
- **Hard**: Từ 32 hành động trở lên.

Độ dài lời giải chỉ là một chỉ số đại diện cho độ khó. Số trạng thái được mở rộng, hệ số phân nhánh và mức độ tương tác giữa các ô đặc biệt cũng ảnh hưởng đến độ khó thực tế.

## Cách chạy benchmark

Chạy các lệnh sau từ thư mục gốc của repository bằng PowerShell.

Chạy benchmark với cả bốn thuật toán trên 100 trường hợp, tương ứng tổng cộng 400 lượt chạy:

    .\.venv\Scripts\python.exe -m experiments.run_experiments

Thời gian chờ mặc định là 15 giây cho mỗi thuật toán trên mỗi trường hợp.

Để chạy lặp lại mỗi trường hợp ba lần:

    .\.venv\Scripts\python.exe -m experiments.run_experiments --repeat 3

Một số tùy chọn hữu ích khác:

- Tăng thời gian chờ lên 30 giây cho mỗi lượt chạy:

      .\.venv\Scripts\python.exe -m experiments.run_experiments --timeout 30

- Chỉ chạy BFS và A*:

      .\.venv\Scripts\python.exe -m experiments.run_experiments --algorithms BFS "A*"

- Ghi kết quả vào một tệp CSV riêng để giữ lại kết quả cũ:

      .\.venv\Scripts\python.exe -m experiments.run_experiments --output experiments/results_trial.csv

Mỗi lần chạy sẽ ghi đè tệp CSV được chỉ định và tạo thêm một tệp metadata tương ứng có hậu tố `_metadata.json`. Hãy sử dụng đường dẫn `--output` khác nhau nếu muốn lưu giữ và so sánh kết quả từ nhiều lần chạy.

## Các chỉ số đánh giá

Benchmark ghi nhận các chỉ số sau:

- **`search_time_seconds`**: Thời gian tìm kiếm do thuật toán giải báo cáo, tính bằng giây. Thời gian tiền xử lý heuristic của A* không được tính vào chỉ số này mà được ghi riêng.
- **`preprocessing_time_seconds`**: Thời gian xây dựng dữ liệu tiền xử lý heuristic, chủ yếu liên quan đến A*.
- **`peak_memory_mb`**: Bộ nhớ cấp phát đỉnh được đo bằng `tracemalloc`, tính theo MB thập phân. Chỉ số này không đại diện cho tổng dung lượng bộ nhớ RAM mà toàn bộ tiến trình sử dụng (RSS).
- **`expanded_nodes`**: Số trạng thái được thuật toán mở rộng. Trạng thái đích không được tính vào chỉ số này.
- **`solution_length`**: Số hành động trong đường đi được trả về.
- **`total_cost`**: Tổng chi phí của đường đi, được tính bằng cách cộng `Engine.step_cost` cho từng bước.
- **`status`**: Trạng thái kết thúc của lượt chạy, gồm `solved`, `unsolved`, `timeout` hoặc `error`.