# Changelog

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
