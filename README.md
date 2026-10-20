# Bloxorz Solver — GUI & luồng tích hợp

Tài liệu này hướng dẫn các thành viên đọc luồng chạy của GUI, cách GUI trao đổi với Python API và vị trí của các thành phần liên quan. GUI hiện được viết trong một file HTML dùng Three.js; backend mới là nơi xác nhận luật chơi và trạng thái hợp lệ.

## Chạy ứng dụng local

Từ thư mục gốc của repository, tạo/kích hoạt môi trường Python nếu cần, cài dependencies và chạy FastAPI:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn server:app --reload --host 127.0.0.1 --port 8000
```

Mở **http://127.0.0.1:8000**. GUI và API được phục vụ cùng origin. Nếu gặp `WinError 10013` khi bind port `8000`, kiểm tra xem đã có tiến trình khác sử dụng port này chưa; không chạy hai Uvicorn trên cùng địa chỉ và port. Có thể dùng port khác, ví dụ `--port 8001`, rồi mở địa chỉ tương ứng.

## Các thành phần chính

| Thành phần | Vai trò |
| --- | --- |
| [`gui/index.html`](gui/index.html) | Giao diện Three.js, HTTP client, chuyển đổi định dạng board/state, input, animation, lịch sử và phát lại. |
| [`server.py`](server.py) | FastAPI adapter; phục vụ GUI, assets, danh sách/load level và endpoint transition/solve. |
| [`game/`](game/) | Engine và các luật chuyển trạng thái; được gọi bởi API. Thay đổi luật nên được thực hiện ở backend, không lặp lại trong GUI. |
| [`levels/`](levels/) | Level 0 dùng để thử ô đặc biệt; level1–level10 là bộ màn chơi chính. `/levels` chỉ liệt kê các file backend đọc được. |
| [`assets/`](assets/) | Texture/model được GUI tải qua `/assets/`. |
| [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md) | Hợp đồng JSON giữa GUI và backend. |
| [`docs/api.md`](docs/api.md) | Mô tả API Python và định dạng dữ liệu board/level. |

JavaScript của GUI hiện được gom trong `gui/index.html`, không chia thành các module `controller.js`, `renderer.js`, `api.js` riêng. API client là lớp `PythonEngineAPI` bên trong file này.

## Luồng khởi động GUI

1. Trình duyệt tải `GET /`; FastAPI trả `gui/index.html`. Các texture/model được lấy từ `/assets/...`.
2. GUI đồng thời gọi `GET /levels` và tải model khối.
3. GUI chọn level đầu tiên trong danh sách API trả về, rồi gọi `GET /levels/{name}`. `level0.json` được xếp đầu để thử nhanh; server sắp tên theo thứ tự tự nhiên (`level2` đứng trước `level10`).
4. Backend trả `board` cùng `initial_state`. GUI chuẩn hóa dữ liệu, dựng lưới 3D, đặt khối, cập nhật tên/kích thước level và bật các điều khiển.
5. Nếu tải level hoặc API lỗi, GUI hiển thị lỗi trạng thái thay vì tự tạo một trạng thái game thay thế.

## Luồng một nước đi

```text
Phím / nút / vuốt
        |
        v
GUI gửi POST /transition (level + state đầy đủ + action)
        |
        v
server.py kiểm tra request -> Engine.transition(...)
        |
        +-- illegal: GUI giữ state, báo nước đi không hợp lệ
        +-- fall:   GUI giữ state logic trước đó, lăn tới hình học bẫy từ `fall_state`, rơi xuống và vào trạng thái LOST
        +-- ok:     GUI nhận state mới, animate giữa hai state rồi cập nhật HUD/bàn
```

Các action trên giao diện được ánh xạ sang API như sau:

| GUI | API |
| --- | --- |
| `U`, `D`, `L`, `R` | `UP`, `DOWN`, `LEFT`, `RIGHT` |
| `SWITCH` | `SWITCH_CUBE` |

GUI gửi toàn bộ state mỗi lần gọi API; backend không giữ session và không có endpoint undo/reset. Chỉ khi backend trả `status: "ok"` thì GUI mới dùng `state` nhận về làm trạng thái logic mới. Với `fall` và `illegal`, `state` là `null`; riêng `fall_state` khi `fall` chỉ cung cấp hình học nước đi bị rơi để animation đi vào ô bẫy, không được commit vào state. Animation là phần trình bày, không quyết định một nước đi có hợp lệ hay khối đã thắng/thua.

### Chuyển đổi tọa độ và state

Wire contract của backend dùng tọa độ `[row, col]`. GUI dùng `{x, z}` để đặt vật thể trong Three.js, với `x = col`, `z = row`; khi gửi request, GUI chuyển ngược lại `[row, col]`. State trên wire gồm vị trí, hướng, trạng thái cầu và thông tin hai cube khi split. `occupied_cells` chỉ là dữ liệu nội bộ của Python; GUI đặt khối từ anchor/orientation và không nhận hoặc gửi trường này.

## Phân công và luồng TV1, TV2, TV5 hiện tại

- TV1/TV2 sở hữu `game/`: Engine tạo và xác nhận mọi trạng thái sau nước đi.
- TV5 sở hữu GUI trong `gui/index.html`; trình duyệt gọi Python qua `PythonEngineAPI` và `server.py`, không import Engine trực tiếp.
- `occupied_cells` được `State`/Engine tính nội bộ; `server.py` dùng các ô này để kiểm tra trạng thái có nằm trong board. Trường này không thuộc HTTP state schema và GUI không xử lý nó.
- Phân chia công việc và tiêu chí bàn giao xem tại [docs/Mô tả công việc.md](<docs/Mô tả công việc.md>).

## Điều khiển và hành vi giao diện

- **Di chuyển:** phím mũi tên, `W/A/S/D`, nút mũi tên trên màn hình hoặc vuốt trên bàn chơi.
- **Chọn level:** chọn level trong menu sẽ tải board và initial state mới.
- **Level 0:** màn thử có ô đích, ô dễ vỡ, cầu đóng, công tắc mềm/nặng và công tắc tách để kiểm tra hiển thị cùng hoạt ảnh.
- **NEW GAME:** bắt đầu từ level đang chọn; nếu level đó chính là level hiện tại thì tương đương restart.
- **RESTART:** tải lại level hiện tại từ `GET /levels/{name}`, dựng lại board và initial state, đưa số bước về 0, xóa undo/replay/metrics. Nút nằm ở góc trên bên phải.
- **UNDO:** khôi phục snapshot do GUI lưu trước nước đi. Undo không gọi API riêng.
- **Split:** khi level kích hoạt split, GUI hiển thị hai cube; có thể đổi cube đang điều khiển bằng `SPACE` hoặc nút đổi khối. Tọa độ/cube active sau mỗi thao tác vẫn do backend xác định.
- **Thua:** khi API trả `fall`, GUI lăn khối tới đúng hình học đích trong `fall_state` rồi thả xuống ô không có hỗ trợ; vị trí logic không được cập nhật từ animation. RESTART tải lại màn; UNDO khôi phục snapshot hợp lệ gần nhất trong history cục bộ.
- **Hướng dẫn trong màn:** dòng “SWIPE TO START / KEEP ROLLING” được đặt cao hơn để tách khỏi cạnh dưới và cụm điều khiển; chú giải ô đặc biệt căn cùng mép trên với nút RESTART.
- **Thắng:** chỉ khi API trả `isGoal: true`; GUI diễn hoạt ảnh chiến thắng và chuyển sang trạng thái WON.

GUI render các tile theo ký tự/metadata của board, gồm ô đích `G`, ô dễ vỡ `F`, cầu `B`, công tắc mềm `o`, công tắc nặng `x` và công tắc tách `P`. Metadata bridge/switch trong level phải phù hợp với grid; xem định dạng chi tiết trong [`docs/api.md`](docs/api.md).

## Endpoint GUI đang sử dụng

| Endpoint | Mục đích |
| --- | --- |
| `GET /` | Trả trang GUI. |
| `GET /assets/{path}` | Phục vụ texture/model tĩnh. |
| `GET /levels` | Lấy danh sách level hợp lệ. |
| `GET /levels/{name}` | Lấy board và initial state; cũng là nguồn dữ liệu để restart. |
| `POST /transition` | Xác nhận action và trả transition result từ Engine. |
| `POST /solve` | Endpoint backend nhận yêu cầu tìm lời giải; GUI hiện không gọi endpoint này. |

### Trạng thái tích hợp solver

GUI hiển thị bảng trạng thái BFS, DFS, UCS và A* ở góc dưới bên trái viewport với trạng thái **Chưa bật**. Nút SOLVE, chọn thuật toán và replay vẫn bị khóa; GUI không gọi `/solve` cho đến khi nhóm tích hợp và bật lại luồng solver.

## Khi thay đổi hoặc tích hợp

1. Thay đổi luật/transition trong Engine và contract backend trước; không thêm luật di chuyển tương đương vào JavaScript.
2. Nếu đổi JSON board, state hoặc action, cập nhật đồng bộ [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md), backend và adapter trong `gui/index.html`.
3. Thêm/sửa level cần bảo đảm có đúng start/goal, grid hợp lệ và metadata đặc biệt khớp các ô tương ứng. Backend bỏ qua file level không hợp lệ khỏi `GET /levels`.
4. Kiểm tra trực tiếp các trường hợp `ok`, `illegal`, `fall`, restart và đổi level trên GUI. Với split, kiểm tra switch/di chuyển/merge theo phản hồi Engine.
5. Nếu đưa GUI và API sang hai origin khác nhau, cần cấu hình CORS allow-list ở server; luồng local mặc định dùng cùng origin nên không cần CORS.
