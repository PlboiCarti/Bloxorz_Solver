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
| [`levels/`](levels/) | Các level JSON. `/levels` chỉ liệt kê các file backend đọc được. |
| [`assets/`](assets/) | Texture/model được GUI tải qua `/assets/`. |
| [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md) | Hợp đồng JSON giữa GUI và backend. |
| [`docs/api.md`](docs/api.md) | Mô tả API Python và định dạng dữ liệu board/level. |

JavaScript của GUI hiện được gom trong `gui/index.html`, không chia thành các module `controller.js`, `renderer.js`, `api.js` riêng. API client là lớp `PythonEngineAPI` bên trong file này.

## Luồng khởi động GUI

1. Trình duyệt tải `GET /`; FastAPI trả `gui/index.html`. Các texture/model được lấy từ `/assets/...`.
2. GUI đồng thời gọi `GET /levels` và tải model khối.
3. GUI chọn level đầu tiên trong danh sách API trả về, rồi gọi `GET /levels/{name}`.
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
        +-- fall:   GUI giữ state logic trước đó, chạy animation rơi và vào trạng thái LOST
        +-- ok:     GUI nhận state mới, animate giữa hai state rồi cập nhật HUD/bàn
```

Các action trên giao diện được ánh xạ sang API như sau:

| GUI | API |
| --- | --- |
| `U`, `D`, `L`, `R` | `UP`, `DOWN`, `LEFT`, `RIGHT` |
| `SWITCH` | `SWITCH_CUBE` |

GUI gửi toàn bộ state mỗi lần gọi API; backend không giữ session và không có endpoint undo/reset. Chỉ khi backend trả `status: "ok"` thì GUI mới dùng state nhận về làm trạng thái logic mới. Với `fall` và `illegal`, `state` phải là `null`. Animation là phần trình bày, không quyết định một nước đi có hợp lệ hay khối đã thắng/thua.

### Chuyển đổi tọa độ và state

Wire contract của backend dùng tọa độ `[row, col]`. GUI dùng `{x, z}` để đặt vật thể trong Three.js, với `x = col`, `z = row`; khi gửi request, GUI chuyển ngược lại `[row, col]`. State bao gồm vị trí, hướng, `occupied_cells`, trạng thái cầu và thông tin hai cube khi split. GUI kiểm tra dữ liệu nhận về khớp hình học trước khi render; không tự tính successor state.

## Điều khiển và hành vi giao diện

- **Di chuyển:** phím mũi tên, `W/A/S/D`, nút mũi tên trên màn hình hoặc vuốt trên bàn chơi.
- **Chọn level:** chọn level trong menu sẽ tải board và initial state mới.
- **NEW GAME:** bắt đầu từ level đang chọn; nếu level đó chính là level hiện tại thì tương đương restart.
- **RESTART:** tải lại level hiện tại từ `GET /levels/{name}`, dựng lại board và initial state, đưa số bước về 0, xóa undo/replay/metrics. Nút nằm ở góc trên bên phải.
- **UNDO:** khôi phục snapshot do GUI lưu trước nước đi. Undo không gọi API riêng.
- **Split:** khi level kích hoạt split, GUI hiển thị hai cube; có thể đổi cube đang điều khiển bằng `SPACE` hoặc nút đổi khối. Tọa độ/cube active sau mỗi thao tác vẫn do backend xác định.
- **Thua:** khi API trả `fall`, GUI diễn hoạt ảnh lăn theo hướng thao tác rồi rơi xuống; vị trí logic không được cập nhật từ animation. RESTART tải lại màn; UNDO khôi phục snapshot hợp lệ gần nhất trong history cục bộ.
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
| `POST /solve` | GUI gọi khi người dùng yêu cầu solver. |

### Trạng thái tích hợp solver

Giao diện đã có chọn thuật toán, nút SOLVE, hiển thị metrics và điều khiển replay theo path. Tuy nhiên, `server.py` hiện trả **HTTP 501 `SOLVER_NOT_AVAILABLE`** cho `/solve`; vì vậy các chức năng tìm lời giải/replay chưa hoạt động cho đến khi solver được triển khai và endpoint trả `SearchResult` đúng contract. Không nên xem các control này là bằng chứng solver đã được tích hợp hoàn chỉnh.

## Khi thay đổi hoặc tích hợp

1. Thay đổi luật/transition trong Engine và contract backend trước; không thêm luật di chuyển tương đương vào JavaScript.
2. Nếu đổi JSON board, state hoặc action, cập nhật đồng bộ [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md), backend và adapter trong `gui/index.html`.
3. Thêm/sửa level cần bảo đảm có đúng start/goal, grid hợp lệ và metadata đặc biệt khớp các ô tương ứng. Backend bỏ qua file level không hợp lệ khỏi `GET /levels`.
4. Kiểm tra trực tiếp các trường hợp `ok`, `illegal`, `fall`, restart và đổi level trên GUI. Với split, kiểm tra switch/di chuyển/merge theo phản hồi Engine.
5. Nếu đưa GUI và API sang hai origin khác nhau, cần cấu hình CORS allow-list ở server; luồng local mặc định dùng cùng origin nên không cần CORS.