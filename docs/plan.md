# plan

## vai trò

Core Engine — thành viên 1
- Board, State, Action.
- Vị trí và hướng của block.
- Bốn hành động di chuyển.
- Kiểm tra bước đi hợp lệ và trạng thái thắng.
- Hash/equality của state.
- Chuyển trạng thái cơ bản.




Advanced Mechanics — thành viên 2
- Fragile tiles.
- Bridges, soft/heavy/split switches.
- Toggle và permanent bridge.
- Tách hai khối lập phương, đổi khối đang điều khiển và ghép lại.
- Test các cơ chế nâng cao.

## tham khảo 

https://github.com/aimacode/aima-python/tree/59fa07ce33a2ddaf4fd5f6c8015c81202fbc6085
https://github.com/ugurmengilli/bloxorz-ai-solver?utm_source=chatgpt.com
https://github.com/YesterKo/bloxorz-solver-py?utm_source=chatgpt.com
https://github.com/VLTisME/CSC14003-Bloxorz?utm_source=chatgpt.com

## lịch 

16/10

Chốt kiến trúc và khảo sát code
- Kiểm tra repository hiện có, không ghi đè code của trưởng nhóm.
- Đọc các repository tham khảo và xác nhận license.
- Chốt biểu diễn State, cách biểu diễn tile và quy ước tọa độ.
- Tạo branch riêng cho Engine.



17/10

Hoàn thiện core mechanics
- Board, State, Action.
- Bốn hướng di chuyển và ba orientation.
- Kiểm tra tile, biên bản đồ và goal.
- Hash/equality và test transition cho toàn bộ tổ hợp hướng.
- Bàn giao API sơ bộ cho người viết Solver.



18/10

Advanced mechanics
- Fragile tiles.
- Soft và heavy switches.
- Toggle/permanent bridges.
- Split switch, split/merge và active cube.
- Kiểm tra các tổ hợp state để tránh trùng state sai.



19/10

Tích hợp và sửa lỗi
- Chạy test core và advanced.
- Cho Solver chạy trực tiếp trên Engine thật.
- Kiểm tra step_cost, goal và state hashing.
- Chốt các vấn đề API với người làm GUI.



20/10

Đóng gói bàn giao
- Chạy lại test từ đầu.
- Merge qua pull request hoặc quy trình nhóm thống nhất.
- Cập nhật README, ví dụ sử dụng và danh sách test.
- Xác nhận các module Solver và GUI có thể gọi Engine.