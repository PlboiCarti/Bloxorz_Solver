# Nghiên cứu và thiết kế heuristic \(h_2\) tối ưu cho A* trong đồ án Bloxorz của bạn

## Kết luận chính

Sau khi đối chiếu ba thứ: mã nguồn `lozia/bloxorz-ai`, ý tưởng \(h_2\) trong ảnh bạn gửi, và kiến trúc hiện tại của đồ án trong README, kết luận của tôi là:

**Không nên copy heuristic của `lozia/bloxorz-ai`.** Repository đó dùng một heuristic khá ad-hoc: lấy khoảng cách của một đầu khối tới goal, gán các giá trị đặc biệt `1` hoặc `3` khi ở vùng gần goal, còn xa thì dùng \((d_x+d_y)/2\). Nó có cải thiện số node trên ví dụ của repo, nhưng không thực sự mô hình hóa orientation, obstacle, chi phí không đồng nhất, bridge, switch hay split. citeturn1view0turn2view0

Với đồ án của bạn, **ý tưởng trong ảnh “Orientation-aware Relaxed Distance” là đúng hướng**, nhưng tôi khuyến nghị sửa hai điểm quan trọng:

1. **Không dùng reverse BFS mà dùng multi-source reverse Dijkstra**, vì đồ án của bạn có `stand_roll=1.5` và `lie_roll=1.0`, tức cạnh không đồng trọng số. fileciteturn0file0
2. **Không được đơn giản hóa split switch `P` thành một ô sàn bình thường.** Split switch của project có khả năng “teleport” khối thành hai cube tại `split_cells`; bỏ hiệu ứng này một cách ngây thơ có thể làm heuristic **overestimate**, mất admissibility. Cách an toàn là xem mỗi tư thế `STANDING` trên split switch như một **abstract terminal/pseudo-goal có distance 0**. fileciteturn0file0

Thiết kế tôi đề xuất là:

\[
\boxed{
h_2(s)=
\begin{cases}
0,& s\text{ đang split}\\[4pt]
d_{\text{relaxed}}\left(
(r,c,o),
\{G\}\cup\{P_1,\ldots,P_k\}
\right),&\text{ngược lại}
\end{cases}}
\]

trong đó \(d_{\text{relaxed}}\) là shortest-path cost trong một abstract graph vẫn giữ **tọa độ + orientation + quy tắc lăn Bloxorz**, giữ `void` là chướng ngại vật, nhưng coi fragile là sàn bình thường, mọi bridge là mở và bỏ trạng thái switch. Với weighted costs hiện tại, bảng distance được tính một lần bằng reverse Dijkstra rồi A* lookup \(O(1)\). Đây về bản chất là một **instance-specific pattern database / abstraction heuristic**: pattern database lưu trước shortest distance của các abstract state đến abstract goal để dùng làm heuristic. citeturn4search2turn5search0

Quan trọng hơn nữa: nghiên cứu README hiện tại cho thấy **heuristic A* hiện có của bạn chưa thể được tuyên bố là admissible trên mọi level có split switch**. README đang dùng

\[
h_1(s)=\left\lceil\frac{\text{Manhattan(anchor,goal)}}{2}\right\rceil
\]

cho state không split và `0` khi split. Nhưng một state chưa split có thể đi tới `P`, rồi `P` đưa hai cube đến vị trí rất xa gần goal. Khi đó Manhattan trực tiếp tới goal có thể lớn hơn true remaining cost qua teleport. Đây là một suy luận trực tiếp từ semantics của split switch mà README mô tả. fileciteturn0file0

Vì vậy, nếu mục tiêu là **A* vừa nhanh vừa còn bảo đảm optimal cost**, tôi sẽ chọn:

> **\(h_2\) = Cost-aware Orientation Static-Relaxed Pattern Database, với split-switch pseudo-goals.**

Đây là phiên bản tôi cho là phù hợp nhất với kiến trúc hiện tại của đồ án.

## Repo `lozia/bloxorz-ai` thực sự đang làm gì

Repository bạn đưa ban đầu là một project A* Bloxorz khá cũ và nhỏ. README của repo nói heuristic chia thành hai trường hợp: khi gần goal trong vùng khoảng \(3\times3\), tác giả gán một số giá trị đặc biệt; khi xa thì dùng khoảng cách tọa độ chia hai. citeturn1view0

Code thực tế của `heuristic1()` xác nhận điều đó. Tác giả lấy:

```python
p1, p2 = node
sX1, sY1 = p1
(eX, eY) = self.board.goal
```

sau đó tính \(d_x,d_y\). Nếu cả hai nhỏ hơn 3 thì heuristic trả `1` hoặc `3` theo một số điều kiện; nếu không thì:

```python
h = (dX + dY) / 2
```

Tức heuristic không tra cứu orientation-aware shortest path mà chỉ dùng tọa độ của `p1` để xấp xỉ. citeturn2view0

Repo có một kết quả thú vị: trong doctest của cùng `AStarSearcher`, heuristic mặc định `0` mở rộng khoảng 1.259 path, còn `heuristic1` khoảng 845 path trên board ví dụ. Điều đó chứng minh heuristic có thông tin vẫn tốt hơn \(h=0\) trong trường hợp của họ, nhưng không chứng minh heuristic đó là tốt nhất, cũng không chứng minh admissibility/consistency cho game mở rộng như project của bạn. citeturn2view0

Đặc biệt, state space của đồ án bạn phức tạp hơn hẳn: `State` chứa orientation, bridge state, split mode, vị trí hai cube và active cube; engine có fragile, bridge, soft/heavy/split switch và merge. Chi phí cũng không còn “mỗi action = 1” mà hiện là `stand_roll=1.5`, `lie_roll=1.0`, `switch_cube=0.1`. fileciteturn0file0

Do đó có thể tóm tắt sự khác biệt:

| Heuristic | Hiểu orientation | Hiểu board topology | Hợp weighted cost | An toàn với split teleport | Precompute |
|---|---:|---:|---:|---:|---:|
| `lozia heuristic1` | Rất hạn chế | Không | Không | Không | Không |
| \(h_1=\lceil M/2\rceil\) hiện tại | Gián tiếp | Không | Một phần | **Không đảm bảo** | Không |
| \(h_2\) trong ảnh, reverse BFS | Có | Tùy implementation | Không tối ưu | Cần sửa | Có |
| **\(h_2\) tôi đề xuất** | **Có** | **Có** | **Có** | **Có** | **Có** |

A* về mặt lý thuyết cần heuristic là lower bound để giữ bảo đảm tìm minimum-cost path; consistency là điều kiện mạnh hơn rất hữu ích cho graph search. Đây là nền tảng từ công trình gốc của Hart, Nilsson và Raphael và phần correction sau đó. citeturn3search0turn3search5

## Thiết kế \(h_2\) phù hợp chính xác với engine hiện tại

### Abstract state

Không cần copy toàn bộ concrete `State`.

Với block chưa split, chỉ giữ:

\[
q=(r,c,o)
\]

với:

\[
o\in\{\text{STANDING},\text{HORIZONTAL},\text{VERTICAL}\}
\]

và `(r,c)` chính là anchor theo convention hiện tại của project. Đây khớp trực tiếp với mô hình `State` trong README: standing chiếm một cell, horizontal chiếm `(r,c),(r,c+1)`, vertical chiếm `(r,c),(r+1,c)`. fileciteturn0file0

Ta **loại khỏi abstraction**:

\[
bridge\_states,\ split\_mode,\ cube1,\ cube2,\ active\_cube
\]

vì \(h_2\) baseline chỉ cần lower bound cho intact block.

Đây chính là nguyên lý của abstraction heuristic: giữ một phần thông tin quan trọng của state, giải bài toán đơn giản hơn, rồi dùng optimal abstract cost làm lower bound. Pattern databases thường thực hiện đúng ý tưởng “precompute abstract-state distance rồi lookup khi search”. citeturn4search2turn4search10

### Relaxed board

Tôi không khuyên làm đúng câu trong ảnh là “bỏ qua ô trống”.

**Void `.` nên tiếp tục là void.**

Void là obstacle tĩnh: một intact block hợp lệ trong concrete game cũng không thể đứng trên void. Giữ void vì thế không loại bỏ một concrete transition hợp lệ nào, nhưng làm heuristic mạnh hơn đáng kể so với coi cả rectangle là sàn. Đây là một relaxation mạnh hơn Manhattan nhưng vẫn an toàn theo mô hình engine của README. fileciteturn0file0

Mapping tôi đề xuất:

| Concrete tile | Trong \(h_2\) |
|---|---|
| `#`, `S`, `G` | support |
| `F` | support bình thường |
| `B` | **luôn support/open** |
| `o`, `x` | support bình thường, bỏ effect |
| `P` | support + special pseudo-goal khi đứng |
| `.` | **void, không support** |

`F` được relax vì concrete cấm block đứng trên fragile, còn abstraction cho phép; tức abstraction chỉ thêm đường đi. Bridge được xem như luôn mở vì bridge concrete có thể đóng, còn abstraction cho phép đi qua mọi lúc. Soft/heavy switch được coi như floor vì bridge đã được optimistic-open nên không cần mô hình trạng thái switch nữa. fileciteturn0file0

Đây là loại “spurious paths” mà abstraction chủ động chấp nhận: abstract state space có thể chứa những đường không tồn tại trong concrete problem; chính việc cho phép thêm đường đi khiến abstract shortest cost trở thành lower bound thay vì upper bound. Nghiên cứu về abstraction heuristic cũng xem các spurious paths là đặc trưng tự nhiên của abstraction. citeturn3search7

### Giữ nguyên rolling geometry

Điểm mạnh quan trọng nhất của \(h_2\) so với Manhattan là **không bỏ orientation**.

Ví dụ từ standing:

\[
(r,c,S)\xrightarrow{RIGHT}(r,c+1,H)
\]

từ horizontal lăn tiếp theo chiều ngang:

\[
(r,c,H)\xrightarrow{RIGHT}(r,c+2,S)
\]

và tương tự cho tám trường hợp còn lại.

Nói cách khác, graph abstract dùng **chính bảng rolling geometry mà engine hiện dùng**, chỉ bỏ mechanics động. Vì vậy \(h_2\) hiểu rằng đứng, nằm ngang và nằm dọc có ảnh hưởng rất khác nhau tới số bước cần để đứng đúng trên goal. README hiện đã định nghĩa đầy đủ các transition geometry này. fileciteturn0file0

Ví dụ hai state có cùng Manhattan anchor distance tới goal:

```text
State A: HORIZONTAL, cách goal 2 cell
State B: VERTICAL,   cách goal 2 cell
```

\(h_1\) có thể xem chúng gần như tương đương, trong khi orientation-aware graph có thể cho hai cost khác hẳn nhau.

### Split switch là điểm phải xử lý đặc biệt

Đây là phần quan trọng nhất của toàn bộ thiết kế.

Project của bạn có `P`: khi intact block đứng thẳng trên split switch, engine đưa hai cube tới `split_cells`. fileciteturn0file0

Nếu abstraction chỉ biến `P` thành floor và tiếp tục bắt block lăn từ P tới goal, abstraction **đã xóa mất một shortcut có thật**.

Một relaxation hợp lệ không được làm bài toán abstract khó hơn bài toán concrete theo cách đó.

Giải pháp đơn giản và rất sạch:

\[
T=\{q_G\}\cup\{q_{P_1},q_{P_2},\ldots,q_{P_k}\}
\]

trong đó:

\[
q_G=(g_r,g_c,\text{STANDING})
\]

và:

\[
q_{P_i}=(p_{i,r},p_{i,c},\text{STANDING})
\]

Mỗi standing split-switch pose được xem như một **abstract goal có cost-to-go bằng 0**.

Khi A* đang ở một intact state, \(h_2\) hỏi:

> Trong relaxed block-rolling problem, rẻ nhất là tới goal trực tiếp hay tới bất kỳ split switch nào?

Tức:

\[
h_2(s)=
\min
\left(
d(q,q_G),
\min_i d(q,q_{P_i})
\right)
\]

Sau khi concrete game đã split:

\[
h_2(s)=0
\]

Cách này rất conservative nhưng quan trọng là **đúng**.

Nó nói rằng:

> “Nếu block đến được P thì từ đó tôi giả sử phần còn lại miễn phí.”

Concrete game thực tế chắc chắn không rẻ hơn “miễn phí”, nên không thể overestimate.

### Dùng reverse Dijkstra thay vì reverse BFS

Ý tưởng trong ảnh dùng reverse BFS. Điều đó đúng nếu mỗi roll có cùng cost.

Nhưng project hiện dùng:

```python
CostConfig(
    stand_roll=1.5,
    lie_roll=1.0,
    switch_cube=0.1,
    bridge_cross_penalty=0.3,
)
```

và `bridge_cross_penalty` hiện chưa được cộng vào step cost. fileciteturn0file0

Vì vậy một edge trong abstract graph nên có:

\[
w(q\rightarrow q')=
\begin{cases}
stand\_roll,&orientation(q)=STANDING\\
lie\_roll,&orientation(q)\in\{HORIZONTAL,VERTICAL\}
\end{cases}
\]

với config hiện tại:

\[
w=
\begin{cases}
1.5,&standing\\
1.0,&lying
\end{cases}
\]

Đây là lý do **Dijkstra đúng hơn BFS**: graph có non-negative edge weights nhưng không uniform. Dijkstra là thuật toán shortest-path cổ điển cho loại weighted graph này. citeturn5search0

Nếu giữ reverse BFS, bạn vẫn có thể tạo một heuristic an toàn bằng cách tính số rolls rồi nhân:

\[
\min(stand\_roll, lie\_roll)
\]

nhưng với config hiện tại điều đó chỉ là nhân `1.0`, làm mất thông tin của các standing roll giá `1.5`.

Reverse Dijkstra cho \(h_2\) mạnh hơn mà chi phí precompute trên board Bloxorz nhỏ gần như không đáng kể.

### Multi-source reverse search

Ta không cần chạy shortest path cho từng state.

Tạo graph abstract một lần:

\[
V\le3RC
\]

vì mỗi anchor có tối đa ba orientation.

Mỗi state có tối đa bốn rolling actions:

\[
E\le4V
\]

Sau đó khởi tạo Dijkstra với **nhiều source** cùng distance `0`:

```text
Goal standing
Split switch 1 standing
Split switch 2 standing
...
```

nhưng chạy trên reverse edges.

Kết quả:

```python
distance[(row, col, orientation)] -> minimum relaxed cost
```

A* chỉ cần:

```python
h = distance[key]
```

nên mỗi heuristic call:

\[
O(1)
\]

Còn một lần preprocessing bằng binary heap là khoảng:

\[
O(RC\log(RC))
\]

với số state thực tế rất nhỏ cho level game thông thường. Đây cũng chính là kiểu precomputed lookup table thường được gọi là pattern database. citeturn4search2

## Vì sao \(h_2\) này admissible và consistent

Đây là phần tôi khuyên đưa thẳng vào report đồ án, vì nó giúp heuristic có nền tảng rõ ràng hơn rất nhiều so với heuristic ad-hoc của repo tham khảo.

### Admissibility

Gọi:

\[
h^*(s)
\]

là concrete optimal cost từ \(s\) tới goal.

Ta cần chứng minh:

\[
h_2(s)\le h^*(s)
\]

cho mọi state.

A* với heuristic là lower bound như vậy giữ được bảo đảm optimality theo lý thuyết heuristic search cổ điển. citeturn3search0turn3search5

Xét một concrete optimal solution bắt đầu từ intact state \(s\).

Có hai trường hợp.

**Trường hợp solution tới goal mà không split.**

Mọi concrete intact roll trên solution đều cũng tồn tại trong relaxed graph, vì \(h_2\):

- cho bridge luôn mở;
- cho đứng trên fragile;
- bỏ switch constraints;
- chỉ giữ void thật sự là void.

Mỗi abstract edge có cost không lớn hơn concrete edge tương ứng.

Do đó:

\[
d_{\text{relaxed}}(s,G)
\le
cost_{\text{concrete}}(s\leadsto G)
\]

nên:

\[
h_2(s)\le h^*(s)
\]

**Trường hợp solution dùng split switch.**

Gọi \(P\) là split switch đầu tiên mà optimal path kích hoạt.

Phần concrete path trước khi split:

\[
s\leadsto P
\]

cũng được biểu diễn trong relaxed graph.

Do \(P\) được coi là abstract terminal có distance 0:

\[
h_2(s)\le d_{\text{relaxed}}(s,P)
\]

và:

\[
d_{\text{relaxed}}(s,P)
\le cost_{\text{concrete}}(s\leadsto P)
\]

trong khi:

\[
cost_{\text{concrete}}(s\leadsto P)
\le h^*(s)
\]

suy ra:

\[
\boxed{h_2(s)\le h^*(s)}
\]

Nếu state đã split:

\[
h_2(s)=0
\]

hiển nhiên:

\[
0\le h^*(s)
\]

Vậy heuristic admissible.

### Consistency

Ta cần:

\[
h_2(s)\le c(s,a,s')+h_2(s')
\]

với mọi legal concrete transition.

Consistency là điều kiện đặc biệt hữu ích trong graph-search A*; công trình nền tảng về A* phân biệt lower-bound admissibility và consistency condition. citeturn3search5

Có bốn loại transition.

**Intact → intact**

Vì \(h_2\) là shortest-path distance trên abstract graph:

\[
d(s,T)
\le
w(s,s')+d(s',T)
\]

và abstract edge weight không lớn hơn real step cost:

\[
w(s,s')\le c(s,s')
\]

nên:

\[
h_2(s)\le c(s,s')+h_2(s')
\]

**Intact → split**

Transition này vừa đứng lên `P` vừa kích hoạt split.

Vì `P` là abstract terminal:

\[
h_2(s)\le w(s,P)
\]

và:

\[
w(s,P)\le c(s,s')
\]

trong khi:

\[
h_2(s')=0
\]

nên:

\[
h_2(s)\le c(s,s')+0
\]

**Split → split**

Hai heuristic đều bằng 0:

\[
0\le c(s,s')+0
\]

**Split → merged intact**

State trước merge có heuristic 0:

\[
0\le c(s,s')+h_2(s')
\]

do mọi cost không âm.

Vậy:

\[
\boxed{h_2\text{ consistent}}
\]

với cost model hiện tại.

Điều kiện quan trọng là `stand_roll`, `lie_roll`, `switch_cube` và mọi penalty phải không âm. README hiện tại thỏa điều kiện đó. fileciteturn0file0

## Cách tích hợp để vẫn match kiến trúc đồ án

Có một mâu thuẫn nhỏ nhưng quan trọng trong README hiện tại.

README quy định:

> Solver không được đọc tile/switch/board internals; solver chỉ dùng `legal_actions`, `transition`, `is_goal`, `step_cost`.

Đồng thời \(h_2\) muốn biết static topology, goal, bridge cells và split-switch cells. fileciteturn0file0

**Không nên phá quy tắc kiến trúc bằng cách cho `solvers/astar.py` import `TileType` hoặc đọc `engine.board`.**

Thay vào đó nên đặt heuristic bên phía `game/` hoặc `Engine`.

Kiến trúc tôi khuyên dùng:

```text
game/
├── actions.py
├── state.py
├── board.py
├── engine.py
├── ...
└── heuristics/
    ├── __init__.py
    └── orientation_relaxed.py

solvers/
└── astar.py
```

Luồng phụ thuộc:

```text
Board + LevelMechanics + CostConfig
              │
              ▼
 OrientationRelaxedHeuristic
              │
        precompute once
              │
              ▼
 Engine.estimate_cost_to_goal(state, "h2")
              │
              ▼
             A*
```

Như vậy nguyên tắc “Engine là source of truth” trong README vẫn nguyên vẹn. fileciteturn0file0

### API nên thêm

Tôi thích API này:

```python
class Engine:
    def estimate_cost_to_goal(
        self,
        state: State,
        heuristic: str = "h2",
    ) -> float:
        ...
```

Sau đó `astar.py`:

```python
h = engine.estimate_cost_to_goal(state, "h2")
```

Thay vì:

```python
# Không nên
engine.board.grid
engine.mechanics.switches
TileType.BRIDGE
```

Bạn cũng có thể dùng object callback:

```python
heuristic = engine.get_heuristic("h2")
h = heuristic(state)
```

nhưng `estimate_cost_to_goal()` dễ đọc hơn cho đồ án sinh viên.

### Skeleton cho implementation

Phần dưới đây không phải drop-in chính xác 100% vì tôi chỉ có README chứ chưa có toàn bộ working tree của project, nhưng nó thể hiện cấu trúc implementation nên dùng:

```python
# game/heuristics/orientation_relaxed.py

from __future__ import annotations

from dataclasses import dataclass
import heapq
import itertools
import math

from game.actions import Orientation
from game.state import State


@dataclass(frozen=True, slots=True)
class AbstractPose:
    row: int
    col: int
    orientation: Orientation


class OrientationRelaxedHeuristic:
    """Cost-aware relaxed orientation PDB for Bloxorz."""

    def __init__(self, board, mechanics, cost_config):
        self._board = board
        self._mechanics = mechanics
        self._cost = cost_config

        self._poses = self._build_valid_poses()
        self._reverse_edges = self._build_reverse_edges()
        self._distance = self._build_distance_table()

    def __call__(self, state: State) -> float:
        # Baseline h2 deliberately gives no estimate while split.
        if state.split_mode:
            return 0.0

        key = AbstractPose(
            row=state.block_position[0],
            col=state.block_position[1],
            orientation=state.orientation,
        )

        # Defensive fallback. A legal concrete state should normally
        # correspond to a valid relaxed pose.
        value = self._distance.get(key)
        if value is None or math.isinf(value):
            return 0.0

        return value
```

Điểm quan trọng là `_build_valid_poses()` phải quyết định support dựa trên **relaxed support**, không phải support hiện tại của bridge.

Pseudo-code:

```python
def relaxed_support(cell):
    tile = board.tile_at(cell)

    if tile is VOID:
        return False

    # NORMAL, START, GOAL, FRAGILE, BRIDGE,
    # SOFT, HEAVY, SPLIT are all support.
    return True
```

Sau đó generate pose:

```python
STANDING:
    (r, c) must be supported

HORIZONTAL:
    (r, c), (r, c + 1) must be supported

VERTICAL:
    (r, c), (r + 1, c) must be supported
```

Tôi khuyên **không tự viết predecessor equations bằng tay**.

An toàn hơn là:

1. enumerate tất cả valid abstract pose;
2. từ mỗi pose thử 4 rolling actions bằng helper geometry;
3. nếu destination pose valid thì thêm forward edge;
4. đồng thời lưu reverse edge.

Ví dụ:

```python
for source in poses:
    for action in ROLL_ACTIONS:
        target = relaxed_roll(source, action)

        if target not in poses:
            continue

        weight = (
            cost_config.stand_roll
            if source.orientation is Orientation.STANDING
            else cost_config.lie_roll
        )

        reverse_edges[target].append((source, weight))
```

Sau đó targets:

```python
targets = {
    AbstractPose(goal_row, goal_col, Orientation.STANDING)
}

for split_switch in split_switches:
    targets.add(
        AbstractPose(
            split_switch.row,
            split_switch.col,
            Orientation.STANDING,
        )
    )
```

Multi-source reverse Dijkstra:

```python
def build_distance_table(targets, reverse_edges):
    inf = math.inf
    dist = {pose: inf for pose in poses}

    counter = itertools.count()
    heap = []

    for target in targets:
        if target not in dist:
            continue

        dist[target] = 0.0
        heapq.heappush(heap, (0.0, next(counter), target))

    while heap:
        current_dist, _, node = heapq.heappop(heap)

        if current_dist != dist[node]:
            continue

        for predecessor, edge_cost in reverse_edges[node]:
            candidate = current_dist + edge_cost

            if candidate >= dist[predecessor]:
                continue

            dist[predecessor] = candidate
            heapq.heappush(
                heap,
                (candidate, next(counter), predecessor),
            )

    return dist
```

Đây chính là phần thay thế cho “reverse BFS” trong ảnh.

### A* nên giữ `g_score`, không dùng heuristic làm visited condition

A* cần ưu tiên:

\[
f(n)=g(n)+h_2(n)
\]

và state dominance phải dựa trên `g_score`, không phải `f`.

Skeleton:

```python
g_score = {start: 0.0}
parent = {}

heapq.heappush(
    frontier,
    (
        engine.estimate_cost_to_goal(start, "h2"),
        next(counter),
        start,
    ),
)

while frontier:
    f_score, _, state = heapq.heappop(frontier)

    g = g_score[state]

    if engine.is_goal(state):
        ...
```

Khi relax successor:

```python
new_g = g + engine.step_cost(state, action, next_state)

if new_g >= g_score.get(next_state, math.inf):
    continue

g_score[next_state] = new_g
parent[next_state] = (state, action)

new_h = engine.estimate_cost_to_goal(next_state, "h2")

heapq.heappush(
    frontier,
    (
        new_g + new_h,
        next(counter),
        next_state,
    ),
)
```

Hart, Nilsson và Raphael đặt nền tảng cho A* như một minimum-cost graph search sử dụng heuristic estimate; với lower-bound heuristic, mục tiêu vẫn là minimum-cost path chứ không phải minimum number of actions. citeturn3search0

## Những chỗ README hiện tại nên sửa

README hiện tại nhìn chung khá nhất quán với kiến trúc, nhưng phần heuristic cần sửa trước khi bạn tuyên bố \(h_2\) admissible.

### Sửa phần “Solver API”

README hiện mô tả:

> A* — Min-heap theo `g+h`; non-split dùng `ceil(Manhattan/2)`, split dùng `h=0`. fileciteturn0file0

Sau khi tích hợp nên thành:

```markdown
| Solver | Cách hoạt động |
| --- | --- |
| BFS | FIFO queue, đánh dấu state khi enqueue |
| DFS | LIFO stack, graph search với visited |
| UCS | Min-heap theo tổng `step_cost` |
| A* | Min-heap theo `g+h`; mặc định dùng cost-aware orientation-relaxed heuristic `h2` được precompute bởi Engine |
```

### Thay toàn bộ phần “Heuristic A*”

Tôi đề xuất README dùng gần như nguyên văn phần này:

```markdown
### Heuristic A*

A* mặc định sử dụng `h2`, một cost-aware orientation-relaxed
pattern database.

Abstract state chỉ giữ:

```text
(row, col, orientation)
```

với ba orientation `STANDING`, `HORIZONTAL`, `VERTICAL`.
Quy tắc lăn của block được giữ nguyên.

Abstract board là relaxation của game thật:

- void vẫn không hỗ trợ block;
- fragile được coi như sàn bình thường;
- mọi bridge được coi là đang mở;
- soft/heavy switch được coi như sàn và không thay đổi bridge state;
- trạng thái bridge không được đưa vào abstract state.

Goal abstract là block `STANDING` tại ô goal.

Để giữ admissibility khi level có split switch, mỗi trạng thái
`STANDING` trên một split switch cũng được xem như một terminal
abstract state có remaining cost bằng 0. Điều này mô hình hóa
split/teleport một cách optimistic thay vì bỏ hiệu ứng split.

Vì `stand_roll` và `lie_roll` có thể khác nhau, distance table được
precompute bằng multi-source reverse Dijkstra thay vì BFS. Edge cost
của một abstract roll là lower bound của `Engine.step_cost()` tương ứng.

```text
h2(state) = 0                                  nếu state đang split
h2(state) = relaxed_distance(position, orient) nếu block còn nguyên
```

Distance table được xây một lần cho mỗi Engine/level và được cache.
Mỗi lần A* đánh giá heuristic chỉ cần dictionary lookup.

`h2` là admissible và consistent đối với cost model không âm hiện tại:
abstract problem chỉ loại bỏ constraints hoặc cho phép kết thúc sớm tại
split switch, nên abstract optimal cost không lớn hơn concrete optimal
cost.
```

Phần này match tốt hơn với implementation thực tế của project và với lý thuyết abstraction/PDB. PDB được định nghĩa trong literature như bảng precomputed shortest distances trong abstract state space và được dùng phổ biến trong heuristic search. citeturn4search2turn4search15

### Không nên giữ nguyên câu chứng minh cho \(h_1\)

README hiện viết đại ý rằng một lần lăn dịch anchor tối đa hai ô, cost ít nhất 1, nên `ceil(Manhattan/2)` là lower bound cho state không split. fileciteturn0file0

Lập luận đó chỉ đúng nếu các remaining paths bị giới hạn bởi rolling geometry trực tiếp.

Nó **không đủ để chứng minh** khi một future split switch có thể chuyển hai cube tới `split_cells` ở nơi xa.

Tôi sẽ sửa thành:

```markdown
Heuristic cũ `h1 = ceil(Manhattan(anchor, goal) / 2)` được giữ lại
cho benchmark. Nó là một lower bound đơn giản trên các level không có
split teleport, nhưng không được dùng làm heuristic mặc định cho các
level có split switch vì khoảng cách tọa độ trực tiếp tới goal không mô
hình hóa shortcut do split tạo ra.
```

Đây là thay đổi quan trọng nhất về mặt correctness.

### Sửa phần kiến trúc solver

README hiện nói solver chỉ dùng:

```text
legal_actions
transition
is_goal
step_cost
```

fileciteturn0file0

Sau \(h_2\), nên đổi thành:

```markdown
Solver không đọc `TileType`, switch metadata hoặc board internals.
Mọi luật game và heuristic domain-specific đều được cung cấp qua Engine.

Solver chỉ dùng public Engine API:

- `legal_actions(state)`
- `transition(state, action)`
- `is_goal(state)`
- `step_cost(...)`
- `estimate_cost_to_goal(state, heuristic)`
```

Như vậy không phá nguyên tắc kiến trúc ban đầu.

### Sửa repository tree

Thêm:

```text
game/
└── heuristics/
    ├── __init__.py
    └── orientation_relaxed.py

tests/
└── test_heuristics.py
```

Nếu muốn đơn giản hơn cho đồ án, chỉ cần:

```text
game/
└── heuristic.py
```

Tôi nghiêng về một file `game/heuristics.py` nếu hiện tại project chưa lớn; không cần over-engineer thành package chỉ vì một heuristic.

### Cập nhật “Việc còn lại”

Hiện README ghi `h2` vẫn chỉ là đề xuất trong `docs/deep-research-report.md`. fileciteturn0file0

Sau implementation nên đổi thành:

```markdown
- Hoàn thành `h2`: cost-aware orientation-relaxed pattern database.
- Cần hoàn thiện benchmark `h0/h1/h2/UCS` trên toàn bộ 10 level.
- Có thể nghiên cứu split-aware abstraction mạnh hơn như hướng mở rộng.
```

## Kiểm thử và benchmark nên làm trước khi gọi \(h_2\) là “tốt nhất”

Không nên đánh giá heuristic chỉ bằng search time.

Một heuristic có thể cho thời gian nhỏ trên một run nhưng mất optimality hoặc tốn nhiều preprocessing. Repo `lozia` cho thấy heuristic có thể giảm expansions từ khoảng 1.259 xuống 845 trên ví dụ của họ, nhưng project của bạn cần benchmark riêng vì state space và mechanics khác hẳn. citeturn2view0

Tôi đề xuất benchmark bốn configuration:

| Cấu hình | Heuristic |
|---|---|
| UCS | \(h=0\) |
| A*-h0 | \(h=0\) |
| A*-h1 | Manhattan/2 cũ |
| **A*-h2** | orientation-relaxed PDB |

UCS và A*-h0 về mặt ordering cost gần như cùng baseline; giữ cả hai chỉ khi rubric cần algorithm comparison.

### Correctness tests quan trọng hơn performance tests

Test đầu tiên:

```python
def test_h2_goal_is_zero():
    assert h2(goal_state) == 0.0
```

Test split:

```python
def test_h2_split_state_is_zero():
    assert h2(split_state) == 0.0
```

Test non-negative:

```python
assert h2(state) >= 0.0
```

Quan trọng nhất là consistency:

```python
for state in reachable_states:
    for action in engine.legal_actions(state):
        result = engine.transition(state, action)
        successor = result.state

        assert (
            h2(state)
            <= engine.step_cost(state, action, successor)
               + h2(successor)
               + 1e-9
        )
```

Test này nên chạy trên **tất cả reachable states của các level nhỏ**.

Sau đó kiểm admissibility bằng UCS:

```python
assert h2(state) <= exact_cost_to_goal_from_ucs(state) + 1e-9
```

Không nhất thiết chạy mọi state của level10 trong CI nếu quá nặng; có thể exhaust level nhỏ và sample state ở level lớn.

Cuối cùng, test quan trọng nhất cho solver:

```python
assert astar_h2_result.total_cost == ucs_result.total_cost
```

trên tất cả 10 level.

Nếu test này fail, chưa nên đưa kết luận “A* h2 optimal” vào report.

Lý thuyết A* yêu cầu heuristic không overestimate để bảo toàn minimum-cost solution; consistency còn cung cấp monotonic relationship trên edges, vì vậy việc test trực tiếp hai tính chất này rất có giá trị. citeturn3search0turn3search5

### Benchmark nên đo cả preprocessing

Với \(h_2\), nên tách:

```text
heuristic_build_time
search_time
total_time = build_time + search_time
```

và thêm:

```text
expanded_nodes
peak_memory_mb
solution_length
solution_cost
```

Bạn nên có hai loại timing:

**Cold A\***:

\[
T_{\text{cold}}=T_{\text{precompute}}+T_{\text{search}}
\]

**Warm A\***:

\[
T_{\text{warm}}=T_{\text{search}}
\]

Warm benchmark hợp lý nếu cùng level được giải nhiều lần, chẳng hạn GUI cho phép solve lại từ state khác; cold benchmark hợp lý cho lần solve đầu tiên.

Pattern databases đổi preprocessing/memory để lấy heuristic lookup nhanh hơn, nên chỉ báo search time mà bỏ preprocessing sẽ không phản ánh đầy đủ trade-off. Công trình PDB trong heuristic search cũng xem lưu trữ abstract-distance tables là yếu tố cốt lõi của phương pháp. citeturn4search2turn4search5

### Kỳ vọng theo từng nhóm level

Dựa trên mô tả 10 level trong README, chưa phải số liệu benchmark thực nghiệm, tôi kỳ vọng như sau. fileciteturn0file0

| Level | Kỳ vọng |
|---|---|
| level1–3 | \(h_2\) mạnh hơn Manhattan nhờ orientation + topology |
| level4–5 | fragile được relax nên vẫn admissible; topology vẫn giúp |
| level6–7 | bridge luôn-open tạo lower bound nhưng vẫn hiểu static shape |
| level8 | split fallback `0` làm heuristic yếu trong split phase nhưng đúng |
| level9–10 | split pseudo-goal đặc biệt quan trọng để giữ optimality |

Trên level không có `P`, \(h_2\) rất đẹp:

\[
h_2(s)=
\text{optimal cost trong board relaxation}
\]

và vì relaxed path vẫn phải tuân theo orientation, nó thường chứa nhiều thông tin hơn `Manhattan/2`.

Trên level có `P`, đôi lúc \(h_2\) sẽ **nhỏ hơn \(h_1\)** trước split switch. Đây không phải lỗi. Nó xảy ra vì \(h_1\) có thể đang đánh giá khoảng cách trực tiếp tới goal trong khi concrete solution có teleport shortcut.

Vì vậy **không nên benchmark heuristic chỉ bằng “heuristic nào có số lớn hơn”**.

Mục tiêu là:

\[
\text{large lower bound}
\]

nhưng vẫn phải:

\[
h(s)\le h^*(s)
\]

## Thiết kế cuối cùng tôi khuyên chốt cho đồ án

Nếu cần chốt một version duy nhất để implementation và trình bày trong báo cáo, tôi sẽ dùng specification sau:

> **\(h_2\): Cost-aware Orientation Static-Relaxed Pattern Database**

Abstract state:

\[
(r,c,orientation)
\]

Giữ:

```text
rolling geometry
board bounds
static void topology
goal position
orientation
```

Relax:

```text
fragile restriction       -> bỏ
bridge open/closed        -> luôn open
soft/heavy switch effects -> bỏ
bridge states             -> bỏ
```

Split:

```text
split state          -> h2 = 0
standing on P target -> pseudo-goal distance 0
```

Cost:

\[
w=
\begin{cases}
stand\_roll,&S\\
lie\_roll,&H,V
\end{cases}
\]

Precompute:

```text
multi-source reverse Dijkstra
```

Cache:

```text
once per level + CostConfig
```

Runtime heuristic:

```text
O(1) dictionary lookup
```

Architecture:

```text
Board / mechanics
       ↓
game/heuristics.py
       ↓
Engine.estimate_cost_to_goal()
       ↓
solvers/astar.py
```

Tests:

```text
h(goal) = 0
h(split) = 0
admissibility vs UCS
consistency over legal transitions
A* total_cost == UCS total_cost
```

Benchmark:

```text
UCS
A*-h0
A*-h1
A*-h2
```

Đây vừa match với kiến trúc “Engine là source of truth” của project, vừa phù hợp với weighted `step_cost`, vừa xử lý đúng điểm khó nhất là split teleport. fileciteturn0file0

Về mặt học thuật, thiết kế cũng có câu chuyện rất rõ để trình bày: A* dùng heuristic lower bound theo nền tảng Hart–Nilsson–Raphael; \(h_2\) được tạo bằng abstraction/pattern database; bảng weighted shortest distances được tính bằng Dijkstra; relaxation chủ động tạo thêm abstract paths để không overestimate. citeturn3search0turn3search5turn4search2turn5search0

Điểm tôi **không** khuyên làm là copy `heuristic1()` của `lozia/bloxorz-ai`. Heuristic đó có giá trị tham khảo để chứng minh “A* có heuristic tốt hơn \(h=0\)”, nhưng thiết kế của nó là khoảng cách tọa độ với các rule `1/3/(dx+dy)/2`, phù hợp với bài Bloxorz đơn giản của repo hơn là engine advanced của bạn. citeturn1view0turn2view0

Nếu phải chọn giữa đúng \(h_2\) trong ảnh và phiên bản tôi đề xuất, tôi sẽ **giữ tên và ý tưởng “Orientation-aware Relaxed Distance”, nhưng đổi implementation từ reverse BFS sang reverse Dijkstra, giữ void, và thêm split-switch pseudo-goals**. Đó là ba thay đổi làm \(h_2\) thực sự khớp với đồ án hiện tại và có cơ sở mạnh để gọi là heuristic A* chính của project.