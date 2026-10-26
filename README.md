# HỆ THỐNG MÔ PHỎNG TRỰC QUAN MARKOV DECISION PROCESSES (MDP)
**Môn học: Cơ sở Trí tuệ Nhân tạo & Reinforcement Learning (CSAI)**  
**Giao diện đồ họa:** Thư viện `pygame-ce` kết hợp `gymnasium` & `stable-baselines3` (PPO)  
**Kho mã nguồn GitHub:** [https://github.com/BaoPhucxD14022006/demo_MDP.git](https://github.com/BaoPhucxD14022006/demo_MDP.git)

---

## 1. Tổng quan hệ thống

Dự án cung cấp bộ công cụ mô phỏng trực quan tương tác phục vụ thuyết trình chuyên sâu về **Markov Decision Processes (MDP)** và **Học tăng cường (Reinforcement Learning)**, bao gồm 2 nghiên cứu điển hình:

1. **Demo 1: Không gian rời rạc - GridWorld 4x4 & Quy hoạch động (Slide 09/12)**
   - Mô hình hóa toán học 4 thành phần $\langle S, A, P, R, \gamma \rangle$.
   - Kiểm chứng sự thất bại của tác tử ngẫu nhiên (tỉ lệ rơi bẫy $89\%$).
   - Minh họa 2 thuật toán Quy hoạch động kinh điển:
     - **Value Iteration (Lập giá trị tối ưu):** Cập nhật Bellman Optimality Backup qua 48 vòng lặp.
     - **Policy Iteration (Lập chính sách):** Luân phiên giữa *Pha 1 (Policy Evaluation)* và *Pha 2 (Policy Improvement)*, hội tụ chỉ sau **2 - 3 vòng lặp lớn**.
   - Rút trích chính sách tối ưu $\pi^*(s)$ và mô phỏng Robot thực thi hành trình né bẫy.
   - **Đối chiếu 2 Ma trận 4x4 cạnh nhau:** Ma trận Tối ưu $\pi^*$ (đường xanh) vs Ma trận Sát bẫy (đường đỏ), chứng minh toán học Bellman tự cân bằng rủi ro mà không cần code cứng.

2. **Demo 2: Không gian liên tục - Robot AMR trong nhà kho thông minh (Slide 11/12)**
   - Môi trường nhà kho $20\text{ m} \times 12\text{ m}$, 5 kệ hàng A-E, 1 chướng ngại vật động (xe nâng tự hành).
   - Động học Unicycle liên tục: vận tốc $v \in [0, 2.0]\text{ m/s}$, góc quay $\omega \in [-1.5, 1.5]\text{ rad/s}$.
   - Hệ cảm biến **19 tia LiDAR 2D** quét góc $180^\circ$ phía trước thời gian thực.
   - Huấn luyện mô hình **Deep RL - Proximal Policy Optimization (PPO)** với 200,000 timesteps đạt tỉ lệ thành công $76 - 80\%$.
   - Cho phép lái thủ công bằng phím WASD hoặc phím mũi tên để so sánh với AI.

3. **Trải nghiệm giao diện cao cấp (Executive UI):**
   - **Màn hình to & chuẩn:** Mặc định $1440 \times 840$ px, tự động co giãn (`RESIZABLE`).
   - **Toàn màn hình Fullscreen (F11):** Bật/tắt Fullscreen không viền (Borderless) tức thì bằng phím **F11** hoặc nút bấm trên thanh công cụ.
   - **DPI Awareness & Font Segoe UI:** Chữ tiếng Việt sắc nét, vẽ mũi tên vector polygon hình học không bị nhầm lẫn với chữ cái.
   - **Thanh điều hướng cố định (TopNavBar):** Chuyển đổi tức thì giữa Menu chính, Demo 1 và Demo 2 (`M`, `F1`, `F2`).

---

## 2. Cấu trúc mã nguồn

```
TT_T6_MDP/
├── Kich_ban.md              # Kịch bản chi tiết bài thuyết trình Slide 09 & Slide 11
├── MDP_Presentation.pptx    # File slide thuyết trình PowerPoint
├── gridworld_env.py         # Môi trường Gymnasium GridWorld 4x4 (Slide 09)
├── value_iteration.py       # Thuật toán Value Iteration, Policy Iteration & Monte Carlo
├── demo1.py                 # Giao diện Pygame tương tác cho Demo 1 (GridWorld 4x4)
├── warehouse_env.py         # Môi trường Gymnasium WarehouseAMREnv (Slide 11)
├── train_ppo.py             # Huấn luyện mô hình PPO & chuẩn hóa VecNormalize
├── demo2.py                 # Giao diện Pygame tương tác cho Demo 2 (AMR Warehouse)
├── main.py                  # Master Launcher điều phối giao diện, Fullscreen & TopNavBar
├── export_figures.py        # Xuất ảnh biểu đồ độ phân giải cao phục vụ chèn vào Slide
├── models/                  # Checkpoint mô hình PPO đã huấn luyện sẵn (best_model.zip, vecnorm.pkl)
├── figures/                 # Các ảnh biểu đồ đã xuất sẵn (PNG độ phân giải cao)
├── README.md                # Tài liệu hướng dẫn sử dụng và thuyết minh kỹ thuật
└── .gitignore               # Cấu hình bỏ qua file tạm, cache và môi trường ảo
```

---

## 3. Cài đặt môi trường

Yêu cầu: **Python 3.10+** (đã kiểm thử hoàn hảo trên Python 3.12).

Cài đặt các thư viện phụ thuộc:
```bash
pip install pygame-ce gymnasium numpy torch stable-baselines3 matplotlib
```

---

## 4. Hướng dẫn chạy chương trình

### Cách 1: Khởi chạy Master Launcher tổng hợp (Khuyên dùng)
```bash
python main.py
```
> Cửa sổ ứng dụng hiển thị với thanh điều hướng đầu trang. Bấm **F1** để vào Demo 1, **F2** để vào Demo 2, **M** để về Menu, **F11** để phóng to Toàn màn hình.

### Cách 2: Khởi chạy trực tiếp từng Demo độc lập
```bash
# Chạy Demo 1 (GridWorld 4x4 + Value Iteration & Policy Iteration)
python demo1.py
# Hoặc: python main.py --demo 1

# Chạy Demo 2 (Robot AMR Warehouse + PPO Deep RL)
python demo2.py
# Hoặc: python main.py --demo 2
```

### Cách 3: Xuất lại toàn bộ ảnh biểu đồ cho Slide PowerPoint
```bash
python export_figures.py
```
> Ảnh biểu đồ chất lượng cao sẽ được lưu vào thư mục `figures/` gồm:
> - `demo1_convergence.png`: Đường cong hội tụ sai số $\max \|\Delta V\|$ qua từng vòng lặp.
> - `demo1_heatmap_values.png`: Bản đồ nhiệt lan truyền giá trị Bellman $V^*(s)$.
> - `demo1_policy_arrows.png`: Bản đồ mũi tên chính sách tối ưu $\pi^*(s)$.
> - `demo2_ppo_learning_curve.png`: Tiến trình phần thưởng huấn luyện PPO 200,000 bước.

---

## 5. Thuyết minh chi tiết các Demo

### PHẦN 1. DEMO 1: GRIDWORLD 4x4 (SLIDE 09/12)

#### 1. Mô hình hóa toán học MDP:
- **Không gian trạng thái $S$:** 16 ô lưới rời rạc (Hàng 1 đáy $\to$ Hàng 4 đỉnh, Cột 1 trái $\to$ Cột 4 phải).
- **Không gian hành động $A$:** 4 hành động cơ bản: {Lên (0), Xuống (1), Trái (2), Phải (3)}.
- **Hàm phần thưởng $R(s, a)$:**
  - Ô Đích $(4, 4)$: $+10.0$ (kết thúc tập).
  - Ô Bẫy nguy hiểm $(3, 3)$ và $(2, 3)$: $-10.0$ (kết thúc tập).
  - Chi phí mỗi bước di chuyển: $-0.04$ (khuyến khích tìm đường ngắn nhất).
  - Va vào tường biên: Đứng yên tại chỗ và chịu phạt va chạm $-0.2$.
- **Động lực chuyển trạng thái ngẫu nhiên $P(s' \mid s, a)$:**
  - $80\%$ đi đúng hướng mong muốn.
  - $10\%$ trượt sang hướng vuông góc bên trái.
  - $10\%$ trượt sang hướng vuông góc bên phải.
- **Hệ số chiết khấu:** $\gamma = 0.99$.

#### 2. Đối chiếu 2 Thuật toán Quy hoạch động (Tab 3):
| Tiêu chí | Value Iteration (Lập giá trị) | Policy Iteration (Lập chính sách) |
| :--- | :--- | :--- |
| **Bản chất toán học** | Cập nhật trực tiếp Bellman Optimality Backup:<br>$V_{k+1}(s) \leftarrow \max_a \left[ R(s,a) + \gamma \sum P V_k \right]$ | Luân phiên qua 2 pha rõ rệt:<br>• **Pha 1 (Evaluation):** Giải hệ Bellman tìm $V^{\pi_k}$<br>• **Pha 2 (Improvement):** $\pi_{k+1} \leftarrow \arg\max Q(s,a)$ |
| **Số vòng lặp hội tụ** | Cần **48 vòng lặp nhỏ** ($\theta = 10^{-4}$). | **Chỉ đúng 2 - 3 vòng lặp lớn** là chính sách đã ổn định! |
| **Đặc điểm tính toán** | Mỗi bước tính toán cực nhanh, đơn giản. | Mỗi vòng giải $V^\pi$ rất nặng về chi phí tính toán. |
| **Trực quan hóa UI** | Xem bản đồ nhiệt và số $V$ lan tỏa dần. | Xem các mũi tên $\pi_k$ tự động lật hướng né bẫy sau mỗi pha. |

#### 3. Đối chiếu 2 Chính sách trên 2 Ma trận cạnh nhau (Tab 5):
| Chỉ tiêu so sánh | Chính sách tối ưu $\pi^*$ (Né bẫy an toàn) | Chính sách sát bẫy (Thiển cận - Mạo hiểm) |
| :--- | :--- | :--- |
| **Hành trình trên lưới** | Lên dọc Cột 1 $\to$ Sang phải Hàng 4 về Đích | Sang phải Hàng 1 $\to$ Lên dọc Cột 4 về Đích |
| **Kỳ vọng $V(\text{Start})$** | **$6.78$** (Giá trị kỳ vọng cao vượt trội) | **$2.07$** (Bị kéo sụt giảm nghiêm trọng) |
| **Tỉ lệ thành công (1000 ep)** | **$88.5\%$** | **$63.4\%$** |
| **Tỉ lệ rơi vào bẫy** | **$11.5\%$** (Chỉ chịu rủi ro tại ô $(4,3)$) | **$28.3\%$** (Rủi ro trượt cao gấp gần 3 lần) |
| **Độ dài lý thuyết** | **6 bước** (3 Lên + 3 Phải) | **6 bước** (3 Phải + 3 Lên - BẰNG NHAU) |
| **Kết luận toán học** | Toán Bellman tự cân bằng giữa bước đi và rủi ro trượt vào bẫy $(-10)$ để tự chọn đường đi vòng an toàn mà không cần code cứng! |

---

### PHẦN 2. DEMO 2: ROBOT AMR WAREHOUSE & DEEP RL (SLIDE 11/12)

#### 1. Mô hình hóa toán học MDP liên tục:
- **Mặt bằng nhà kho:** Kích thước thực tế $20\text{ m} \times 12\text{ m}$, 5 kệ hàng A, B, C, D, E.
- **Vật cản động:** Một xe nâng tự hành di chuyển tuần hoàn qua lại tại khu vực hành lang trung tâm ($x \approx 8.5\text{ m}$).
- **Không gian trạng thái $S$:** Vector liên tục 27 chiều:
  - 8 biến động học: $(x, y, \cos\theta, \sin\theta, v, \omega, d_{\text{goal}}, \theta_{\text{goal}})$.
  - 19 tia cảm biến LiDAR 2D quét cung $180^\circ$ phía trước (tầm đo tối đa $6.0\text{ m}$, phát hiện cả tường, kệ và vật cản động).
- **Không gian hành động $A$:** Bộ điều khiển vận tốc liên tục $a = (v, \omega)$:
  - Vận tốc tiến: $v \in [0.0, 2.0]\text{ m/s}$.
  - Vận tốc góc lái: $\omega \in [-1.5, 1.5]\text{ rad/s}$.
- **Hàm phần thưởng $R(s, a)$:**
  - Về đích thành công (giao hàng): $+100.0$.
  - Va chạm kệ/tường/vật cản động: Phạt nặng $-500.0$ (kết thúc tập).
  - Tiến gần mục tiêu (Potential-based reward shaping): $+2.0 \times \Delta d$.
  - Chi phí bước đi & thời gian: $-0.01$ mỗi bước.

#### 2. Kết quả huấn luyện Deep RL (Mô hình trong `models/`):
- **Agent ngẫu nhiên:** Thất bại $100\%$, va chạm chỉ sau $1 - 2\text{ s}$, điểm số âm $-500$.
- **Huấn luyện PPO (200,000 steps):** Điểm số trung bình tăng từ $-475.0$ lên $+141.5$.
- **Kiểm thử độc lập 100 Episodes:**
  - Tỉ lệ tới đích thành công: **$76.0\%$**
  - Tỉ lệ va chạm vật cản: **$11.0\%$**
  - Thời gian di chuyển trung bình: **$17.7\text{ giây}$**

---

## 6. Bảng phím tắt thao tác điều khiển

| Phím tắt | Vị trí áp dụng | Chức năng chi tiết |
| :--- | :--- | :--- |
| **F11** | Toàn bộ ứng dụng | **Bật/Tắt Toàn màn hình (Borderless Fullscreen)** sắc nét |
| **F1** hoặc **1** | Mọi màn hình | Chuyển ngay sang **Demo 1: GridWorld 4x4** |
| **F2** hoặc **2** | Mọi màn hình | Chuyển ngay sang **Demo 2: Robot AMR Warehouse** |
| **M** hoặc **Esc** | Mọi màn hình | Quay trở lại **Menu chính** |
| **Phím 1 đến 5** | Trong Demo 1 | Chuyển trực tiếp giữa 5 Tab của Demo 1 |
| **Phím 1 đến 7** | Trong Demo 2 | Chuyển trực tiếp giữa 7 Giai đoạn của Demo 2 |
| **Space** | Cả 2 Demo | Tạm dừng (Pause) / Tiếp tục (Resume) mô phỏng |
| **N** | Cả 2 Demo | Thực hiện **1 bước tiếp theo** (Next step) hoặc 1 vòng lặp Bellman |
| **R** | Cả 2 Demo | Đặt lại vị trí Robot về ô xuất phát (Reset Episode) |
| **S** | Trong Demo 2 | Đổi Seed mới (ngẫu nhiên hóa vị trí xuất phát và vật cản động) |
| **W / A / S / D** | Demo 2 (Tab 7) | Lái Robot thủ công bằng bàn phím để đối đầu với AI |

---

## 7. Giấy phép & Tác giả
- Đồ án môn học: **Cơ sở Trí tuệ Nhân tạo (CSAI) & Reinforcement Learning**.
- Nhóm sinh viên thực hiện và xây dựng kịch bản thuyết trình chi tiết.
- GitHub Repository: [BaoPhucxD14022006/demo_MDP](https://github.com/BaoPhucxD14022006/demo_MDP.git)
