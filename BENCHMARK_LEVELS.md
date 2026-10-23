# Benchmark trên các level GUI

Đây là bản tóm tắt của lần chạy benchmark hiện tại trên chính các màn mà GUI
cung cấp.

## Phạm vi

- Level: `level1.json` đến `level20.json`.
- Thuật toán: BFS, DFS, UCS và A*.
- Số lượt chạy: `20 × 4 = 80`.
- Kết quả: `80/80 solved`, không timeout, không error.
- Chỉ số: search time, peak memory, expanded nodes và solution length.

## Nhóm level

| Nhóm | Level |
| --- | --- |
| `basic` | `level1`-`level3` |
| `fragile` | `level4`, `level5`, `level12` |
| `switches_bridges` | `level6`-`level9`, `level11`, `level13`-`level17`, `level19` |
| `combined` | `level10`, `level18`, `level20` |

## Trung bình theo thuật toán

| Thuật toán | Số lượt | Search time (s) | Peak memory (MB) | Expanded nodes | Solution length |
| --- | ---: | ---: | ---: | ---: | ---: |
| BFS | 20 | 0.863338 | 0.260370 | 1312.05 | 41.65 |
| DFS | 20 | 0.206915 | 0.095740 | 335.70 | 179.45 |
| UCS | 20 | 0.875544 | 0.325079 | 1154.35 | 41.65 |
| A* | 20 | 0.353074 | 0.284946 | 392.45 | 41.65 |

Các giá trị chi tiết theo từng level nằm trong
`experiments/results.csv`. Thời gian và memory phụ thuộc môi trường chạy; khi
chạy lại bằng môi trường khác, cần cập nhật lại bảng này cùng với CSV metadata.
