# Changelog

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
