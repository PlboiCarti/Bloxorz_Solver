# Benchmark

Benchmark dùng đúng các màn đang được GUI cung cấp trong `levels/`.
`run_experiments.py` tự quét `levels/level*.json`, nạp board bằng cùng
`load_board()` như server và lấy trạng thái bắt đầu bằng
`Engine.get_initial_state()`.

## Chạy benchmark

Chạy từ thư mục gốc repository:

```powershell
python -m experiments.run_experiments
```

Mặc định runner chạy BFS, DFS, UCS và A* trên toàn bộ 20 level GUI:

```text
20 level × 4 thuật toán = 80 lượt chạy
```

Kết quả được ghi vào:

```text
experiments/results.csv
experiments/results_metadata.json
```

Các tùy chọn hiện có:

```powershell
python -m experiments.run_experiments --timeout 30
python -m experiments.run_experiments --algorithms BFS "A*"
python -m experiments.run_experiments --repeat 3
python -m experiments.run_experiments --output experiments/results_trial.csv
```

## Chỉ số theo yêu cầu PDF

Với mỗi level và mỗi thuật toán, CSV ghi bốn chỉ số cần cho phần thực nghiệm:

- `search_time_seconds`: thời gian tìm kiếm;
- `peak_memory_mb`: bộ nhớ peak được đo bằng `tracemalloc`;
- `expanded_nodes`: số trạng thái được mở rộng;
- `solution_length`: số action trong lời giải.

CSV còn giữ `status` và thông tin định danh để phân biệt solved, unsolved,
timeout hoặc error khi lập bảng báo cáo. Các trường cost/preprocessing là dữ liệu
đã có trong `SearchResult` của solver và không thay thế bốn chỉ số bắt buộc.

Runner nhóm level theo mechanics để mô tả bộ test trong report:

- `basic`: không có fragile, bridge hoặc switch;
- `fragile`: có fragile tile nhưng không có bridge/switch;
- `switches_bridges`: có bridge hoặc switch;
- `combined`: có fragile cùng bridge/switch.

`test_set.json` custom đã được loại khỏi project. Benchmark hiện tại chỉ lấy dữ
liệu từ các level GUI.
