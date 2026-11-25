# KỊCH BẢN DEMO MDP BẰNG GYMNASIUM

Bài thuyết trình: **Markov Decision Processes (MDP) – Cơ sở Trí tuệ Nhân tạo (CSAI)**  
Phạm vi: **Minh họa GridWorld 4x4 & Quy hoạch động (Dynamic Programming)**.

---

## 0. Nguyên tắc chung

Mạch trình bày xuyên suốt để khán giả dễ nhớ:

1. **Mô hình hóa MDP**: chỉ ra S, A, P, R, $\gamma$ đúng như trên slide.
2. **Agent ngẫu nhiên**: thất bại, tạo "vấn đề".
3. **Thuật toán giải**: Value Iteration & Policy Iteration.
4. **Agent thông minh**: thành công, đối chiếu với kết luận trên slide.

Môi trường `GridWorldEnv` kế thừa `gymnasium.Env` với giao diện chuẩn `reset()`, `step()`.

### Nguyên tắc khi trình bày
- **Cố định `seed`** để kết quả lặp lại được.
- Mọi con số trong demo (tỉ lệ thành công, số vòng lặp...) đều được **chạy thật** từ mô phỏng Monte Carlo và Quy hoạch động.

### Môi trường và thư viện

```bash
pip install gymnasium numpy matplotlib pygame-ce
```

### Cấu trúc project

```
TT_T6_MDP/
├── main.py                      # Trình điều phối giao diện Pygame
├── src/
│   ├── gridworld_env.py         # Môi trường GridWorld 4x4 (Gymnasium)
│   ├── value_iteration.py       # Value Iteration, Policy Iteration & Monte Carlo
│   ├── sketch_style.py          # Đồ họa ô đá, kim cương, vụ nổ và robot
│   └── demo1.py                 # Giao diện Pygame chạy mô phỏng MDP
├── scripts/
│   ├── export_figures.py        # Xuất ảnh đồ thị độ phân giải cao
│   ├── export_web_data.py       # Xuất dữ liệu cho demo HTML
│   └── generate_voiceover.py    # Tạo giọng đọc AI ~5 phút
├── docs/
│   ├── figures/                 # Ảnh biểu đồ xuất sẵn
│   └── Transcript_5phut.md      # Lời thoại demo 5 phút
└── web/                         # Bản demo HTML5 quay video
```

---

# MINH HỌA: GRIDWORLD 4x4 + VALUE ITERATION & POLICY ITERATION

**Mục tiêu:** chứng minh robot tự động chọn đường vòng an toàn nhờ động lực ngẫu nhiên, không cần ai lập trình "hãy tránh bẫy".

## 1. Vì sao phải tự viết môi trường

`FrozenLake` có sẵn trong Gymnasium **không khớp** với bài toán:

| Thuộc tính | FrozenLake | Bài toán MDP GridWorld 4x4 |
|---|---|---|
| Trượt | 1/3 mỗi hướng (đúng, trái, phải) | 80% đúng, 10% trượt trái, 10% trượt phải |
| Phần thưởng | 1 khi tới đích, 0 còn lại | +10 đích, -10 bẫy, -0.04 mỗi bước, -0.2 va tường |
| Bố cục | Lưới hồ băng cố định | Bẫy ở (hàng 3, cột 3) và (hàng 2, cột 3) |

Vì vậy cần viết `class GridWorldEnv(gym.Env)`.

## 2. Ánh xạ lý thuyết sang code

| Trên slide | Trong code |
|---|---|
| Không gian trạng thái S: 16 ô (i, j), i, j ∈ {1..4} | `observation_space = Discrete(16)`; `s = (hàng-1)*4 + (cột-1)` |
| Không gian hành động A: {Lên, Xuống, Trái, Phải} | `action_space = Discrete(4)`; 0=Lên, 1=Xuống, 2=Trái, 3=Phải |
| Start (1,1) | `start_cell = (hàng 1, cột 1)` |
| Đích (4,4), +10 | Trạng thái kết thúc, thưởng +10 |
| Bẫy (3,3) và (2,3), -10 | Hai trạng thái kết thúc, thưởng -10 |
| Động lực ngẫu nhiên 80/10/10 | Với mỗi (s, a): 0.8 hướng đúng, 0.1 trượt trái, 0.1 trượt phải (so với hướng đi) |
| Chi phí mỗi bước R = -0.04 | Mọi bước không kết thúc đều nhận -0.04 |
| Va tường | Đứng yên tại chỗ, chịu thêm phạt va chạm -0.2 |

**Lưu ý quy ước tọa độ:** *Hàng 1 nằm ở dưới cùng*, *Hàng 4 ở trên cùng*, còn *Cột 1 ở bên trái*. Khi vẽ bằng matplotlib/pygame phải đảo trục hàng (`y_vẽ = 4 - hàng`) để hình khớp với hệ trục chuẩn.

**Lưu ý "trượt trái/phải":** trái/phải được hiểu **tương đối theo hướng đi**:

| Hành động | Trượt trái thành | Trượt phải thành |
|---|---|---|
| Lên | Trái | Phải |
| Xuống | Phải | Trái |
| Trái | Xuống | Lên |
| Phải | Lên | Xuống |

## 3. Thiết kế `gridworld_env.py`

Nguyên tắc: **xây bảng chuyển `P` giống `env.P` của FrozenLake**. Value Iteration và Policy Iteration dùng bảng này, còn `step()` lấy mẫu từ chính bảng này, nên mô hình và môi trường luôn nhất quán.

Tham số `slip` (mặc định 0.2) cho phép kiểm thử sự thay đổi của chính sách khi thay đổi độ ngẫu nhiên.

## 4. Thiết kế `value_iteration.py`

Bao gồm:
- `ValueIterationSolver`: Bellman Optimality Backup tìm $V^*$ và $\pi^*$.
- `PolicyIterationSolver`: Luân phiên Policy Evaluation và Policy Improvement.
- `evaluate_policy()`: Giải lặp $V^\pi$ cho một chính sách bất kỳ.
- `simulate_policy()`: Mô phỏng Monte Carlo 1000 episode thống kê tỉ lệ tới đích, tỉ lệ rơi bẫy.

**Siêu tham số:**
- `gamma = 0.99`
- `theta = 1e-4`

## 5. Kịch bản trình bày (khoảng 3-4 phút)

| # | Thời gian | Màn hình | Lời thoại gợi ý | Mục đích |
|---|---|---|---|---|
| 1 | 0:00-0:30 | Lưới 4x4 (Start, Đích +10, Bẫy -10) | "Đây là môi trường MDP: 16 trạng thái, 4 hành động. Mỗi lần robot ra lệnh đi, 80% đi đúng hướng, 10% trượt trái, 10% trượt phải." | Giới thiệu S, A, P |
| 2 | 0:30-1:00 | Agent ngẫu nhiên chạy thử + thống kê 1000 episode | "Nếu chọn hành động ngẫu nhiên, robot lang thang và thường xuyên rơi vào bẫy." | Tạo vấn đề |
| 3 | 1:00-2:00 | Tab Quy hoạch động: Value Iteration (48 vòng) & Policy Iteration (2-3 vòng) | "Value Iteration lan truyền giá trị từ ô đích ra xung quanh; Policy Iteration chỉ cần 2-3 vòng lặp lớn để hội tụ chính sách. Ô sát bẫy có giá trị thấp hơn hẳn." | Cho thấy hội tụ |
| 4 | 2:00-2:30 | Lưới có mũi tên π\*(s) trên từng ô và robot chạy theo π\* | "Từ V\*, ta rút ra chính sách tối ưu: robot đi lên cột 1 rồi sang phải theo hàng 4, tránh xa cặp bẫy." | Rút trích π\* |
| 5 | 2:30-3:45 | So sánh 2 chính sách cạnh nhau: π\* và "đi sát bẫy" + bảng V(start), tỉ lệ rơi bẫy | "Hai đường dài như nhau (6 bước), nhưng đường sát bẫy có kỳ vọng thấp hơn hẳn (2.07 vs 6.78) vì rủi ro trượt vào bẫy. Toán học MDP tự cân bằng giữa chi phí bước đi và độ an toàn." | Bản chất toán học MDP |

## 6. Điều cần kiểm tra trước khi demo

1. **Đối chiếu đường đi.** Đường xanh tối ưu đi lên dọc cột 1 đến hàng 4, rồi sang phải dọc hàng 4 tới đích.
2. **Chiều dài các đường.** Cả đường xanh và đường sát bẫy đều **6 bước** (3 lên + 3 sang phải). Vậy "đường vòng" thực chất là *né bẫy mà không tốn thêm bước*, không phải đường dài hơn.
3. **Mức rủi ro.** Đường xanh đi qua ô (hàng 4, cột 3) nằm ngay trên bẫy (hàng 3, cột 3), nên vẫn có 10% trượt xuống bẫy ở đúng ô đó (tỉ lệ rơi bẫy $\approx 11.5\%$). Đường sát bẫy dọc cột 4 có nhiều ô kề bẫy hơn nên tỉ lệ rơi bẫy cao hơn nhiều ($\approx 28.3\%$).
4. **Tính nhất quán**: tổng xác suất mỗi `P[s][a]` bằng 1; trạng thái terminal đứng yên.

---

# PHỤ LỤC: CÂU HỎI THƯỜNG GẶP

- **"Tại sao không đi đường ngắn nhất sát bẫy?"** Vì 20% trượt khiến kỳ vọng thưởng thấp hơn; Value Iteration tính kỳ vọng nên tự chọn đường an toàn hơn.
- **"Vì sao γ = 0.99?"** Nhằm ưu tiên thưởng dài hạn nhưng vẫn đảm bảo hội tụ.
- **"Sự khác nhau giữa Value Iteration và Policy Iteration?"** Value Iteration cập nhật thẳng `max Q` qua 48 vòng nhỏ; Policy Iteration tách riêng Evaluation và Improvement nên hội tụ chỉ sau 2-3 vòng lớn.
