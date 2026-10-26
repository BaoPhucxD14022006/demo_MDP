# KỊCH BẢN DEMO MDP BẰNG GYMNASIUM

Bài thuyết trình: **Markov Decision Processes (MDP) – AI & Reinforcement Learning**
Phạm vi: Slide 09/12 (Minh họa 1: Gridworld 4x4) và Slide 11/12 (Minh họa 2: Robot AMR trong nhà kho thông minh).

---

## 0. Nguyên tắc chung

Cả hai demo đi theo cùng một mạch để khán giả dễ nhớ:

1. **Mô hình hóa MDP**: chỉ ra S, A, P, R đúng như trên slide.
2. **Agent ngẫu nhiên**: thất bại, tạo "vấn đề".
3. **Thuật toán học**: Value Iteration (Demo 1), PPO/SAC (Demo 2).
4. **Agent thông minh**: thành công, đối chiếu với kết luận trên slide.

Thông điệp xuyên suốt: *cùng một khung MDP (S, A, P, R) dùng được từ bảng 16 ô rời rạc đến robot liên tục trong nhà kho*. Cả hai môi trường đều kế thừa `gymnasium.Env` với giao diện `reset()`, `step()`, `render()`.

### Nguyên tắc khi trình bày
- **Train trước, demo bằng model đã lưu.** Không train trực tiếp khi thuyết trình.
- **Quay sẵn video dự phòng** cho cả hai demo.
- **Cố định `seed`** để kết quả lặp lại được.
- Mọi con số trong demo (tỉ lệ thành công, số vòng lặp...) phải **chạy thật rồi mới ghi vào lời thoại**, không ghi theo ước đoán.

### Môi trường và thư viện

```bash
pip install gymnasium numpy matplotlib pygame stable-baselines3 torch
```

### Cấu trúc project

```
mdp_demo/
├── gridworld_env.py        # Env 1: GridWorld 4x4 (Gymnasium)
├── value_iteration.py      # Value Iteration, heatmap, mũi tên chính sách
├── demo1.py                # Kịch bản chạy Demo 1
├── warehouse_env.py        # Env 2: WarehouseAMREnv (Gymnasium)
├── train_ppo.py            # Huấn luyện PPO (và SAC)
├── demo2.py                # Kịch bản chạy Demo 2
├── models/                 # Model đã train (ppo_amr.zip, sac_amr.zip)
├── figures/                # Ảnh/GIF xuất sẵn
└── videos/                 # Video dự phòng
```

---

# PHẦN 1. MINH HỌA 1: GRIDWORLD 4x4 + VALUE ITERATION

**Mục tiêu:** chứng minh robot tự động chọn đường vòng an toàn nhờ động lực ngẫu nhiên, không cần ai lập trình "hãy tránh bẫy".

## 1.1. Vì sao phải tự viết môi trường

`FrozenLake` có sẵn trong Gymnasium **không khớp** với slide:

| Thuộc tính | FrozenLake | Slide 09 |
|---|---|---|
| Trượt | 1/3 mỗi hướng (đúng, trái, phải) | 80% đúng, 10% trái, 10% phải |
| Phần thưởng | 1 khi tới đích, 0 còn lại | +10 đích, -10 bẫy, -0.04 mỗi bước |
| Bố cục | Lưới hồ băng cố định | Bẫy ở (hàng 3, cột 3) và (hàng 2, cột 3) |

Vì vậy cần viết `class GridWorldEnv(gym.Env)`.

## 1.2. Ánh xạ slide sang code

| Trên slide | Trong code |
|---|---|
| Không gian trạng thái S: 16 ô (i, j), i, j ∈ {1..4} | `observation_space = Discrete(16)`; `s = (hàng-1)*4 + (cột-1)` |
| Không gian hành động A: {Lên, Xuống, Trái, Phải} | `action_space = Discrete(4)`; 0=Lên, 1=Xuống, 2=Trái, 3=Phải |
| Start (1,1) | `start = (hàng 1, cột 1)` |
| Đích (4,4), +10 | Trạng thái kết thúc, thưởng +10 |
| Bẫy (3,3) và (2,3), -10 | Hai trạng thái kết thúc, thưởng -10 |
| Động lực ngẫu nhiên 80/10/10 | Với mỗi (s, a): 0.8 hướng đúng, 0.1 trượt trái, 0.1 trượt phải (so với hướng đi) |
| Chi phí mỗi bước R = -0.04 | Mọi bước không kết thúc đều nhận -0.04 |
| Va tường | Đứng yên tại chỗ, vẫn nhận -0.04 |

**Lưu ý quy ước tọa độ:** trên slide, *Hàng 1 nằm ở dưới cùng*, *Hàng 4 ở trên cùng*, còn *Cột 1 ở bên trái*. Khi vẽ bằng matplotlib/pygame phải đảo trục hàng (`y_vẽ = 4 - hàng`) để hình giống slide.

**Lưu ý "trượt trái/phải":** trái/phải được hiểu **tương đối theo hướng đi**:

| Hành động | Trượt trái thành | Trượt phải thành |
|---|---|---|
| Lên | Trái | Phải |
| Xuống | Phải | Trái |
| Trái | Xuống | Lên |
| Phải | Lên | Xuống |

(Nếu chọn quy ước khác, cần ghi rõ trong demo và giữ nhất quán.)

## 1.3. Thiết kế `gridworld_env.py`

Nguyên tắc: **xây bảng chuyển `P` giống `env.P` của FrozenLake**. Value Iteration dùng bảng này, còn `step()` lấy mẫu từ chính bảng này, nên mô hình và môi trường luôn nhất quán.

```python
# P[s][a] = [(prob, next_state, reward, terminated), ...]
import numpy as np, gymnasium as gym
from gymnasium import spaces

ACTIONS = {0: (1, 0), 1: (-1, 0), 2: (0, -1), 3: (0, 1)}  # (d_hàng, d_cột)
# Lưu ý: hàng tăng = đi lên (hàng 4 ở trên cùng)

class GridWorldEnv(gym.Env):
    metadata = {"render_modes": ["rgb_array", "human"]}

    def __init__(self, slip=0.2, step_cost=-0.04, render_mode=None):
        self.n = 4
        self.start = (1, 1)
        self.goal = (4, 4)
        self.traps = {(3, 3), (2, 3)}
        self.slip, self.step_cost = slip, step_cost
        self.observation_space = spaces.Discrete(16)
        self.action_space = spaces.Discrete(4)
        self.P = self._build_P()
        self.render_mode = render_mode

    def _move(self, cell, a):
        r, c = cell
        dr, dc = ACTIONS[a]
        nr, nc = r + dr, c + dc
        if 1 <= nr <= self.n and 1 <= nc <= self.n:
            return (nr, nc)
        return cell                      # va tường: đứng yên

    def _build_P(self):
        # TODO: với mỗi s không phải terminal, mỗi a:
        #   - a_left, a_right = hướng trượt trái/phải theo bảng ở mục 1.2
        #   - outcomes = [(1-slip, a), (slip/2, a_left), (slip/2, a_right)]
        #   - với mỗi outcome: next_cell = self._move(cell, a')
        #       reward = +10 nếu goal, -10 nếu trap, ngược lại step_cost
        #       terminated = next_cell in {goal} | traps
        # Trạng thái terminal: P[s][a] = [(1.0, s, 0.0, True)]
        ...

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.s = self._to_idx(self.start)
        return self.s, {}

    def step(self, a):
        outcomes = self.P[self.s][a]
        probs = [o[0] for o in outcomes]
        i = self.np_random.choice(len(outcomes), p=probs)
        _, self.s, r, term = outcomes[i]
        return self.s, r, term, False, {}
```

Tham số `slip` (mặc định 0.2) cho phép demo tùy chọn "tắt ngẫu nhiên" ở mục 1.5.

## 1.4. Thiết kế `value_iteration.py`

```python
def value_iteration(P, n_states=16, n_actions=4, gamma=0.99, theta=1e-4):
    V = np.zeros(n_states)
    history, deltas = [V.copy()], []
    while True:
        delta = 0
        V_new = V.copy()
        for s in range(n_states):
            q = [sum(p * (r + gamma * V[s2] * (not done))
                     for p, s2, r, done in P[s][a]) for a in range(n_actions)]
            V_new[s] = max(q)
            delta = max(delta, abs(V_new[s] - V[s]))
        V = V_new
        history.append(V.copy()); deltas.append(delta)
        if delta < theta: break
    policy = extract_policy(P, V, gamma)
    return V, policy, history, deltas
```

**Siêu tham số:**
- `gamma = 0.99` (slide chưa nêu γ, phải ghi rõ trên màn hình demo).
- `theta = 1e-4` (có thể chỉnh để số vòng hội tụ gần "khoảng 25 vòng" như slide).
- **Cần chạy thật để biết số vòng lặp.** Nếu kết quả khác 25 thì sửa lại lời thoại hoặc chỉnh `theta`, `gamma` cho hợp lý, không nên nói sai số liệu.

Các hàm vẽ cần có:
- `plot_heatmap(V)`: bản đồ nhiệt giá trị V\*(s) trên lưới 4x4, ghi số trong từng ô.
- `plot_policy(policy)`: mũi tên π\*(s) trên mỗi ô.
- `plot_convergence(deltas)`: đồ thị `max|ΔV|` theo số vòng lặp (trục y thang log).
- `plot_trajectory(path)`: vẽ đường đi lên lưới, màu xanh lá.

## 1.5. Kịch bản trình bày Demo 1 (khoảng 3-4 phút)

| # | Thời gian | Màn hình | Lời thoại gợi ý | Mục đích |
|---|---|---|---|---|
| 1 | 0:00-0:30 | Lưới 4x4 đúng màu slide (start xanh dương, đích xanh lá, bẫy đỏ) | "Đây là môi trường đúng như slide: 16 trạng thái, 4 hành động. Mỗi lần robot ra lệnh đi, 80% đi đúng hướng, 10% trượt trái, 10% trượt phải." | Giới thiệu S, A, P |
| 2 | 0:30-1:00 | Agent ngẫu nhiên chạy 3-5 episode (GIF/animation) + dòng chữ tỉ lệ thành công | "Nếu chọn hành động ngẫu nhiên, robot lang thang và thường rơi vào bẫy. Chạy 1000 episode, tỉ lệ tới đích chỉ khoảng X%." (X lấy từ chạy thật) | Tạo vấn đề |
| 3 | 1:00-2:00 | Heatmap V\*(s) tại vòng lặp 1, 5, 10, hội tụ (4 khung cạnh nhau) và đồ thị `max|ΔV|` | "Value Iteration lan truyền giá trị từ ô đích ra xung quanh. Sau khoảng N vòng, bảng giá trị hội tụ. Ô sát bẫy có giá trị thấp hơn hẳn." | Cho thấy hội tụ (khớp ô "Tốc độ hội tụ") |
| 4 | 2:00-2:30 | Lưới có mũi tên π\*(s) trên từng ô | "Từ V\*, ta rút ra chính sách tối ưu: ở mỗi ô nên đi hướng nào. Chú ý robot không đi sát bẫy." | Rút trích π\* |
| 5 | 2:30-3:00 | Robot chạy theo π\*, vẽ quỹ đạo xanh lá; kèm kết quả 1000 episode (tỉ lệ thành công, thưởng trung bình) | "Robot đi lên cột 1 rồi sang phải theo hàng 4, tránh xa cặp bẫy." | Khớp đường xanh trên slide |
| 6 | 3:00-3:45 | So sánh 2 chính sách cạnh nhau: π\* và "đi sát bẫy" (đường đỏ nét đứt trên slide). Bảng: V(start), tỉ lệ rơi bẫy | "Hai đường dài như nhau, nhưng đường sát bẫy có kỳ vọng thấp hơn vì 20% rủi ro trượt. Toán học MDP tự cân bằng giữa chi phí bước đi và độ an toàn." | Khớp ô "Bản chất toán học" |
| 7 | 3:45-4:00 *(tùy chọn)* | Chạy lại với `slip=0` và so sánh chính sách | "Khi môi trường không còn ngẫu nhiên, robot không cần né, chính sách đổi theo. Vậy chính tính ngẫu nhiên tạo ra hành vi đi vòng." | Chứng minh nguyên nhân |

### Chi tiết bước 6: cách so sánh chính sách

- **Chính sách π\***: lấy từ Value Iteration.
- **Chính sách "đi sát bẫy"**: cố định, ví dụ đi sang phải dọc hàng 1 đến cột 4 rồi đi lên dọc cột 4 (cột kề bẫy ở cột 3).
- Dùng **Policy Evaluation** (giải lặp `V^π`) để tính chính xác `V^π(start)`, đồng thời **Monte Carlo 1000 episode** để kiểm chứng bằng mô phỏng.
- Báo cáo: `V(start)`, tỉ lệ rơi bẫy, thưởng trung bình.

## 1.6. Điều cần kiểm tra trước khi demo (rất quan trọng)

1. **Đối chiếu đường đi với slide.** Slide vẽ đường xanh: lên dọc cột 1 đến hàng 4, rồi sang phải dọc hàng 4 tới đích. Chạy thật xem π\* có ra đúng đường này không. Có thể ra đường khác tương đương (do hòa giá trị) hoặc phụ thuộc γ.
2. **Chiều dài các đường.** Cả đường xanh và đường sát bẫy đều **6 bước** (3 lên + 3 sang phải). Vậy "đường vòng" thực chất là *né bẫy mà không tốn thêm bước*, không phải đường dài hơn. Lời thoại nên nói chính xác như vậy.
3. **Mức rủi ro.** Đường xanh đi qua ô (hàng 4, cột 3) nằm ngay trên bẫy (hàng 3, cột 3), nên vẫn có 10% trượt xuống bẫy ở đúng ô đó. Đường sát bẫy dọc cột 4 có **2 ô** chịu rủi ro tương tự. Hãy tính số liệu thật để nói "ít rủi ro hơn", không nói "hoàn toàn an toàn".
4. **Số vòng lặp hội tụ** có thật sự gần 25 không (xem mục 1.4).
5. **Tính nhất quán**: tổng xác suất mỗi `P[s][a]` bằng 1; trạng thái terminal đứng yên.

---

# PHẦN 2. MINH HỌA 2: ROBOT AMR TRONG NHÀ KHO + PPO/SAC

**Mục tiêu:** cho thấy bài toán cơ điện tử phức tạp (liên tục, có cảm biến LiDAR, có vật cản động) vẫn quy về MDP và được giải bằng Deep RL, robot học né vật cản mà **không cần bản đồ tĩnh**.

## 2.1. Ánh xạ slide sang code

| Trên slide | Trong code |
|---|---|
| Trạng thái S: (x, y, θ, v, ω) + vector LiDAR 2D | `observation_space = Box`: 5 giá trị + `n_rays` (16-24) khoảng cách LiDAR chuẩn hóa về [0, 1] |
| Hành động A: v ∈ [0, 2.0] m/s, ω ∈ [-1.5, +1.5] rad/s | `action_space = Box(low=[0, -1.5], high=[2.0, 1.5])` |
| Thưởng +100 khi giao hàng đúng kệ đích | Tới trong bán kính `goal_radius` (0.5 m): +100, kết thúc |
| Phạt -500 khi va chạm | Va kệ, tường hoặc vật cản: -500, kết thúc |
| -0.1 / giây | Mỗi bước `-0.1 * dt` (dt = 0.1 s) |
| Kệ A-E, vật cản động (công nhân/xe nâng) | 5 hình chữ nhật cố định + 1 hình tròn di chuyển |
| Quét LiDAR 2D/3D hình quạt | Ray casting trong numpy, vẽ tia mờ hình quạt |

## 2.2. Bố cục nhà kho (gợi ý, đồng bộ với sơ đồ slide)

Mặt bằng 20 m x 12 m (gốc tọa độ ở góc dưới trái):

| Đối tượng | Hình dạng | Vị trí (x, y, rộng x cao) |
|---|---|---|
| Kệ A | Chữ nhật | (3, 8), 4 x 2 |
| Kệ B | Chữ nhật | (9, 8), 4 x 2 |
| Kệ C | Chữ nhật | (15, 8), 4 x 2 |
| Kệ D | Chữ nhật | (3, 2), 4 x 2 |
| Kệ E | Chữ nhật | (9, 2), 4 x 2 |
| Đích giao hàng | Vùng xanh lá | Tâm (16.5, 3), bán kính 0.5-1 |
| AMR (xuất phát) | Hình tròn bán kính 0.3 | (1.5, 5) hướng sang phải (có thể ngẫu nhiên hóa nhẹ) |
| Vật cản động (công nhân/xe nâng) | Hình tròn bán kính 0.5 | Đi qua lại theo trục y trong hành lang tại x ≈ 8-9, tốc độ 0.5-1 m/s |

Hành lang giữa hai hàng kệ (y từ 4 đến 8) là nơi AMR di chuyển và nơi vật cản động cắt ngang, đúng tinh thần trong sơ đồ slide. Có thể điều chỉnh số liệu cho hợp màn hình, miễn tuân theo logic trên.

## 2.3. Thiết kế `warehouse_env.py`

**Động học (unicycle):**
```
x     += v * cos(θ) * dt
y     += v * sin(θ) * dt
θ     += ω * dt
```
Với `dt = 0.1 s`, giới hạn `max_steps = 600` (60 giây).

**LiDAR:** `n_rays = 16-24` tia phủ góc quạt khoảng 180° phía trước; ray casting với hình chữ nhật (kệ, tường) và hình tròn (vật cản động); khoảng cách tối đa 5 m, chuẩn hóa về [0, 1].

**Observation đề xuất:**
```
[ x/W, y/H, sin θ, cos θ, v/2.0, ω/1.5,
  khoảng cách tới đích (chuẩn hóa), góc tới đích so với hướng robot,
  lidar_1 ... lidar_n ]
```

**Ghi chú về những điểm khác slide (cần nói thẳng khi trình bày):**
- Slide mô tả trạng thái gồm (x, y, θ, v, ω, LiDAR). Trong thực tế **phải bổ sung khoảng cách và góc tới đích**, nếu không agent không biết đích ở đâu (đích đổi vị trí thì không tổng quát được). Đây là bổ sung nhỏ cho đủ tính Markov.
- Dùng (sin θ, cos θ) thay cho θ thô để tránh bước nhảy tại ±π, đây vẫn là cùng thông tin.
- **Reward shaping (tùy chọn):** thêm thành phần nhỏ thưởng khi tiến gần đích, ví dụ `+k * (d_trước - d_sau)` với k nhỏ, để huấn luyện nhanh hơn. Phải nói rõ đây là kỹ thuật phụ trợ, còn 3 thành phần thưởng chính vẫn đúng như slide. Nếu huấn luyện được mà không cần shaping thì càng bám sát slide.

**Hàm chính:**
```python
class WarehouseAMREnv(gym.Env):
    metadata = {"render_modes": ["rgb_array", "human"], "render_fps": 20}

    def __init__(self, n_rays=16, render_mode=None): ...
    def reset(self, seed=None, options=None): ...   # ngẫu nhiên hóa vị trí/pha vật cản
    def step(self, action):
        # 1. clip action, cập nhật động học
        # 2. cập nhật vật cản động
        # 3. kiểm tra va chạm -> reward = -500, terminated = True
        # 4. kiểm tra tới đích  -> reward = +100, terminated = True
        # 5. ngược lại reward = -0.1 * dt (+ shaping nếu dùng)
        # 6. truncated = (steps >= max_steps)
        ...
    def render(self): ...  # vẽ kệ, vật cản, AMR, tia LiDAR hình quạt, quỹ đạo
```

**Kiểm tra môi trường trước khi train:**
```python
from stable_baselines3.common.env_checker import check_env
check_env(WarehouseAMREnv())
```

## 2.4. Huấn luyện (`train_ppo.py`)

```python
from stable_baselines3 import PPO, SAC
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from stable_baselines3.common.callbacks import EvalCallback

env = VecNormalize(DummyVecEnv([lambda: WarehouseAMREnv()] * 8))
model = PPO("MlpPolicy", env, learning_rate=3e-4, n_steps=2048,
            batch_size=256, gamma=0.99, tensorboard_log="./logs", seed=0)
model.learn(total_timesteps=1_000_000)
model.save("models/ppo_amr")
env.save("models/vecnorm.pkl")   # nhớ lưu cả thống kê chuẩn hóa
```

- Ước lượng: 300k-1M bước, từ vài phút đến vài chục phút trên CPU với môi trường đơn giản (cần chạy thử để biết).
- Lưu **checkpoint** và **đường cong reward** (`mean episode reward`) để dùng ở bước 3 của kịch bản.
- Tùy chọn: train thêm SAC (`SAC("MlpPolicy", env, ...)`), chỉ đổi một dòng, để so sánh.
- **Cẩn thận:** nếu dùng `VecNormalize`, khi demo phải nạp lại thống kê chuẩn hóa, nếu không robot sẽ hành xử sai.
- Nếu agent không học được (hay đứng yên hoặc quay tròn), thử: bật reward shaping, giảm độ khó (vật cản chậm hơn), curriculum (đích gần trước rồi xa dần), tăng số bước.

## 2.5. Kịch bản trình bày Demo 2 (khoảng 4-5 phút)

| # | Thời gian | Màn hình | Lời thoại gợi ý | Mục đích |
|---|---|---|---|---|
| 1 | 0:00-0:45 | Cảnh nhà kho (kệ A-E, đích giao hàng, vật cản, AMR) kèm tia LiDAR hình quạt | "Đây là nhà kho thông minh như trên slide. Trạng thái gồm vị trí, hướng, vận tốc và dữ liệu LiDAR. Hành động là vận tốc thẳng v và vận tốc góc ω." | Giới thiệu S, A |
| 2 | 0:45-1:15 | Agent ngẫu nhiên: xoay loạn xạ rồi đâm vào kệ. Hiển thị thưởng của episode | "Với hành động ngẫu nhiên, robot nhanh chóng va chạm và bị phạt -500." | Tạo vấn đề, giải thích R |
| 3 | 1:15-2:00 | Đồ thị mean episode reward theo bước huấn luyện (đã train sẵn); có thể kèm 2-3 ảnh chụp robot ở các mốc huấn luyện đầu, giữa, cuối | "Sau khi học bằng PPO, thưởng trung bình tăng dần từ rất âm lên dương. Robot tự học mà không ai chỉ dẫn quy tắc né." | Cho thấy quá trình học |
| 4 | 2:00-3:00 | Agent PPO đã train: đi từ AMR đến Đích giao hàng, vòng qua vật cản đang di chuyển, vẽ quỹ đạo màu xanh dương (giống slide) | "Robot đi theo quỹ đạo này, chậm lại và đổi hướng khi vật cản cắt ngang, đến đích nhận +100." | Khớp sơ đồ slide |
| 5 | 3:00-3:45 | Chạy lại với 3-4 hạt giống khác (vị trí/pha vật cản khác nhau) | "Mỗi lần vật cản ở một chỗ khác, robot vẫn né được. Nó học phản xạ từ cảm biến, không cần bản đồ tĩnh." | Khớp ô "Thuật toán triển khai" |
| 6 | 3:45-4:30 | Bảng thống kê 100 episode: tỉ lệ đến đích, tỉ lệ va chạm, thời gian trung bình | "Trong 100 episode, robot tới đích N lần, va chạm M lần." (số thật) | Số liệu thuyết phục |
| 7 | 4:30-5:00 *(tùy chọn)* | So sánh PPO và SAC (đường cong học + tỉ lệ thành công) | "Cùng một môi trường MDP, ta có thể thay thuật toán." | Mở rộng |

## 2.6. Điều cần kiểm tra trước khi demo

1. Agent đã train **đạt tỉ lệ thành công đủ cao** (nên mục tiêu ≥ 80-90%), nếu thấp thì sửa trước khi thuyết trình.
2. Video/GIF thể hiện **đúng cả tia LiDAR và quỹ đạo** để khớp hình trên slide.
3. Nạp đúng model và `VecNormalize`.
4. Chạy thử toàn bộ demo trên máy trình chiếu thật (độ phân giải, hiệu năng pygame).

---

# PHẦN 3. KẾ HOẠCH THỰC HIỆN

| Bước | Công việc | Ưu tiên |
|---|---|---|
| 1 | Viết `gridworld_env.py`, kiểm tra tổng xác suất `P` | Cao |
| 2 | Viết `value_iteration.py`, đối chiếu π\* với slide | Cao |
| 3 | Viết các hàm vẽ heatmap, mũi tên, quỹ đạo và `demo1.py` | Cao |
| 4 | Viết `warehouse_env.py` (động học, LiDAR, va chạm, render) | Cao |
| 5 | `check_env`, chạy thử agent ngẫu nhiên | Cao |
| 6 | Train PPO, theo dõi đường cong reward, tinh chỉnh | Cao |
| 7 | Viết `demo2.py`, xuất ảnh/GIF/video | Trung bình |
| 8 | Train SAC để so sánh | Thấp (tùy chọn) |
| 9 | Quay video dự phòng, chạy thử trên máy trình chiếu | Cao |

---

# PHỤ LỤC

## A. Câu hỏi khán giả có thể hỏi và gợi ý trả lời

- **"Tại sao không đi đường ngắn nhất sát bẫy?"** Vì 20% trượt khiến kỳ vọng thưởng thấp hơn; Value Iteration tính kỳ vọng nên tự chọn đường an toàn hơn.
- **"Value Iteration có dùng được cho bài toán AMR không?"** Không trực tiếp: không gian trạng thái liên tục, quá lớn để lập bảng và ta không có sẵn mô hình P. Vì vậy dùng Deep RL (PPO/SAC), học từ tương tác.
- **"Vì sao γ = 0.99?"** Nhằm ưu tiên thưởng dài hạn nhưng vẫn đảm bảo hội tụ; slide không nêu nên đây là lựa chọn của demo.
- **"Tại sao PPO/SAC?"** PPO ổn định, dễ tinh chỉnh; SAC hiệu quả mẫu tốt, hợp không gian hành động liên tục.
- **"Môi trường này có giống thực tế không?"** Đây là mô phỏng 2D đơn giản (unicycle, LiDAR giả lập); để đưa vào robot thật cần thêm nhiễu cảm biến, động học thực, sim-to-real.

## B. Danh sách kiểm tra trước ngày thuyết trình

- [ ] Hai demo chạy được từ dòng lệnh, không cần sửa code
- [ ] Mọi số liệu trong lời thoại đã được chạy thật và điền vào
- [ ] Model và file chuẩn hóa nằm trong `models/`
- [ ] Ảnh/GIF/video xuất sẵn trong `figures/`, `videos/`
- [ ] Đã quay video dự phòng cho cả hai demo
- [ ] Đã chạy thử trên máy sẽ trình chiếu
- [ ] Đã tập thuyết trình theo thời lượng (Demo 1: 3-4 phút, Demo 2: 4-5 phút)
