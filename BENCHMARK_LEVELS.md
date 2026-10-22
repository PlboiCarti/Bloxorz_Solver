# Thống kê giải 11 màn Bloxorz

## Phạm vi và cách đo

- Dữ liệu: `levels/level0.json` đến `levels/level10.json`.
- Thuật toán: BFS, DFS, UCS và A*.
- Mỗi ô trong bảng là một lần chạy độc lập từ trạng thái ban đầu của màn.
- `Độ dài` là số bước trong đường đi tìm được.
- `Chi phí` là tổng chi phí đường đi theo cấu hình chi phí mặc định.
- `Thời gian` là thời gian tìm kiếm, tính bằng giây.
- `Bộ nhớ` là mức sử dụng đỉnh đo được trong quá trình tìm kiếm, tính bằng MB thập phân.
- `Mở rộng` là số node đã mở rộng.
- Tất cả 44 lượt chạy đều có `Solved = Có`.

## Kết quả chi tiết

| Màn | Thuật toán | Solved | Độ dài | Chi phí | Thời gian (s) | Bộ nhớ (MiB) | Mở rộng |
|---|---|:---:|---:|---:|---:|---:|---:|
| level0 | BFS | Có | 9 | 10.5 | 0.025384 | 0.114 | 275 |
| level0 | DFS | Có | 174 | 203.5 | 0.017238 | 0.064 | 187 |
| level0 | UCS | Có | 9 | 10.5 | 0.019090 | 0.086 | 267 |
| level0 | A* | Có | 9 | 10.5 | 0.002886 | 0.900 | 25 |
| level1 | BFS | Có | 14 | 16.5 | 0.001366 | 0.005 | 25 |
| level1 | DFS | Có | 28 | 32.5 | 0.002241 | 0.008 | 37 |
| level1 | UCS | Có | 14 | 16.5 | 0.001379 | 0.006 | 24 |
| level1 | A* | Có | 14 | 16.5 | 0.000991 | 0.024 | 14 |
| level2 | BFS | Có | 7 | 8.0 | 0.003448 | 0.011 | 64 |
| level2 | DFS | Có | 45 | 52.0 | 0.003593 | 0.013 | 56 |
| level2 | UCS | Có | 7 | 8.0 | 0.003639 | 0.013 | 62 |
| level2 | A* | Có | 7 | 8.0 | 0.001061 | 0.039 | 14 |
| level3 | BFS | Có | 20 | 23.5 | 0.003247 | 0.010 | 62 |
| level3 | DFS | Có | 57 | 67.0 | 0.005282 | 0.024 | 88 |
| level3 | UCS | Có | 20 | 23.5 | 0.003566 | 0.012 | 62 |
| level3 | A* | Có | 20 | 23.5 | 0.001812 | 0.043 | 26 |
| level4 | BFS | Có | 14 | 15.0 | 0.004836 | 0.016 | 92 |
| level4 | DFS | Có | 59 | 67.0 | 0.004777 | 0.022 | 78 |
| level4 | UCS | Có | 14 | 15.0 | 0.005260 | 0.020 | 84 |
| level4 | A* | Có | 14 | 15.0 | 0.002553 | 0.043 | 38 |
| level5 | BFS | Có | 14 | 16.5 | 0.006354 | 0.018 | 120 |
| level5 | DFS | Có | 84 | 98.0 | 0.007118 | 0.028 | 111 |
| level5 | UCS | Có | 14 | 16.5 | 0.008300 | 0.023 | 117 |
| level5 | A* | Có | 14 | 16.5 | 0.001984 | 0.060 | 27 |
| level6 | BFS | Có | 11 | 13.5 | 0.005148 | 0.018 | 94 |
| level6 | DFS | Có | 79 | 91.0 | 0.006948 | 0.027 | 108 |
| level6 | UCS | Có | 11 | 13.5 | 0.005644 | 0.022 | 89 |
| level6 | A* | Có | 11 | 13.5 | 0.000906 | 0.039 | 11 |
| level7 | BFS | Có | 19 | 22.5 | 0.006926 | 0.023 | 126 |
| level7 | DFS | Có | 82 | 92.5 | 0.007157 | 0.028 | 107 |
| level7 | UCS | Có | 19 | 22.5 | 0.008004 | 0.028 | 136 |
| level7 | A* | Có | 19 | 22.5 | 0.002551 | 0.040 | 35 |
| level8 | BFS | Có | 17 | 21.5 | 0.028389 | 0.060 | 322 |
| level8 | DFS | Có | 50 | 62.0 | 0.006304 | 0.028 | 95 |
| level8 | UCS | Có | 17 | 20.6 | 0.033588 | 0.086 | 354 |
| level8 | A* | Có | 17 | 20.6 | 0.008104 | 0.095 | 77 |
| level9 | BFS | Có | 22 | 28.1 | 0.122159 | 0.180 | 1146 |
| level9 | DFS | Có | 356 | 485.0 | 0.049387 | 0.162 | 419 |
| level9 | UCS | Có | 22 | 28.1 | 0.125876 | 0.248 | 1128 |
| level9 | A* | Có | 22 | 28.1 | 0.018390 | 0.286 | 151 |
| level10 | BFS | Có | 37 | 45.6 | 0.570011 | 0.986 | 4786 |
| level10 | DFS | Có | 788 | 1102.9 | 0.107377 | 0.311 | 859 |
| level10 | UCS | Có | 37 | 45.1 | 0.496444 | 1.175 | 3960 |
| level10 | A* | Có | 37 | 45.1 | 0.154200 | 1.015 | 1222 |

## Tóm tắt

- Tỷ lệ giải thành công: **44/44 (100%)**.
- A* cho đường đi có chi phí tối ưu hoặc đồng tối ưu với UCS ở các màn đã kiểm tra, đồng thời mở rộng ít node nhất trong 10/11 màn.
- BFS và UCS cho cùng độ dài ở hầu hết màn; ở `level8` và `level10`, UCS/A* có chi phí thấp hơn BFS do chi phí bước không đồng nhất.
- DFS thường tìm được lời giải nhanh ở các màn lớn nhưng đường đi dài hơn đáng kể; trường hợp lớn nhất là `level10` với 788 bước và chi phí 1102.9.
- Màn có nhiều node mở rộng nhất là `level10`: BFS 4786, UCS 3960, A* 1222, DFS 859.
- Thời gian A* thấp nhất ở 10/11 màn trong lần đo này; ngoại lệ là `level10`, nơi DFS nhanh hơn do dừng sớm theo thứ tự duyệt. Thời gian A* thấp nhất là ở `level6` với 0.000906 giây.

## Ghi chú tái lập

Kết quả được tạo bằng cách nạp từng file trong `levels/`, khởi tạo `Engine`, rồi gọi lần lượt các hàm solver public trong package `solvers`. Thời gian và bộ nhớ phụ thuộc môi trường chạy nên có thể dao động nhẹ giữa các lần thực thi.
