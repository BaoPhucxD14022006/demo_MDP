# HỆ THỐNG MÔ PHỎNG TRỰC QUAN MARKOV DECISION PROCESSES (MDP)
**Môn học: Cơ sở Trí tuệ Nhân tạo (CSAI)**  
**Giao diện đồ họa:** Thư viện `pygame-ce` kết hợp `gymnasium` & `numpy`  
**Kho mã nguồn GitHub:** [https://github.com/BaoPhucxD14022006/demo_MDP.git](https://github.com/BaoPhucxD14022006/demo_MDP.git)

---

## 1. Tổng quan hệ thống

Dự án cung cấp bộ công cụ mô phỏng trực quan tương tác phục vụ thuyết trình chuyên sâu về **Markov Decision Processes (MDP)** với bài toán **GridWorld 4x4 & Quy hoạch động (Slide 09)**:

1. **GridWorld 4x4 & Quy hoạch động (Dynamic Programming):**
   - Mô hình hóa toán học 5 thành phần $\langle S, A, P, R, \gamma \rangle$.
   - Kiểm chứng sự thất bại của tác tử ngẫu nhiên (tỉ lệ rơi bẫy $\approx 89\%$).
   - Minh họa 2 thuật toán Quy hoạch động kinh điển:
     - **Value Iteration (Lập giá trị tối ưu):** Cập nhật Bellman Optimality Backup qua 48 vòng lặp.
     - **Policy Iteration (Lập chính sách):** Luân phiên giữa *Pha 1 (Policy Evaluation)* và *Pha 2 (Policy Improvement)*, hội tụ chỉ sau **2 - 3 vòng lặp lớn**.
   - Rút trích chính sách tối ưu $\pi^*(s)$ và mô phỏng Robot thực thi hành trình né bẫy.
   - **Đối chiếu 2 Ma trận 4x4 cạnh nhau:** Ma trận Tối ưu $\pi^*$ (đường xanh) vs Ma trận Sát bẫy (đường đỏ), chứng minh toán học Bellman tự cân bằng rủi ro mà không cần code cứng.

2. **Trải nghiệm giao diện cao cấp (Executive UI):**
   - **Màn hình to & chuẩn:** Mặc định $1440 \times 840$ px, tự động co giãn (`RESIZABLE`).
   - **Toàn màn hình Fullscreen (F11):** Bật/tắt Fullscreen không viền (Borderless) tức thì bằng phím **F11** hoặc nút bấm trên thanh công cụ.
   - **DPI Awareness & Font Segoe UI:** Chữ tiếng Việt sắc nét, vẽ mũi tên vector polygon hình học và đồ họa đá/robot trực quan (`sketch_style.py`).
   - **Thanh điều hướng cố định (TopNavBar):** Chuyển đổi tức thì giữa Menu chính và mô phỏng GridWorld 4x4 (`M`, `F1`).

---

## 2. Cấu trúc mã nguồn

```
TT_T6_MDP/
├── README.md                    # Tài liệu hướng dẫn sử dụng và thuyết minh kỹ thuật
├── .gitignore                   # Cấu hình bỏ qua file tạm, cache và môi trường ảo
├── main.py                      # Master Launcher điều phối giao diện Pygame
├── src/                         # Mã nguồn cốt lõi MDP & giao diện Pygame
│   ├── __init__.py
│   ├── gridworld_env.py         # Môi trường Gymnasium GridWorld 4x4
│   ├── value_iteration.py       # Thuật toán Value Iteration, Policy Iteration & Monte Carlo
│   ├── sketch_style.py          # Bộ vẽ đồ họa ô đá, kim cương, vụ nổ và robot
│   └── demo1.py                 # Giao diện Pygame tương tác cho GridWorld 4x4
├── scripts/                     # Các script xuất dữ liệu, biểu đồ và giọng đọc AI
│   ├── export_figures.py        # Xuất ảnh biểu đồ độ phân giải cao vào docs/figures/
│   ├── export_web_data.py       # Xuất dữ liệu thực nghiệm ra web/data.js
│   └── generate_voiceover.py    # Tạo giọng đọc AI (~5 phút) & docs/Transcript_5phut.md
├── docs/                        # Tài liệu thuyết trình, kịch bản, slide & hình ảnh
│   ├── MDP_Presentation_v22.pdf # Slide thuyết trình PDF
│   ├── Kich_ban.md              # Kịch bản chi tiết bài thuyết trình MDP
│   ├── Transcript_5phut.md      # Lời thuyết trình ~5 phút khớp giọng đọc AI
│   └── figures/                 # Ảnh biểu đồ đã xuất sẵn (PNG độ phân giải cao)
└── web/                         # Bản Demo HTML5/JS để quay video (mở web/index.html)
    ├── index.html               # Trang trình chiếu 16:9 (1920×1080)
    ├── style.css                # Giao diện sáng tối giản
    ├── app.js                   # Logic 6 cảnh + trình phát giọng đọc đồng bộ
    ├── data.js                  # Dữ liệu thực nghiệm xuất từ Python
    ├── audio_meta.js            # Metadata thời lượng các phân đoạn giọng đọc
    └── audio/                   # File âm thanh 48 kHz (seg_*.mp3 & full_voiceover_5min.*)
```

---

## 3. Cài đặt môi trường

Yêu cầu: **Python 3.10+** (đã kiểm thử trên Python 3.12).

Cài đặt các thư viện phụ thuộc:
```bash
pip install pygame-ce gymnasium numpy matplotlib
```

---

## 4. Hướng dẫn chạy chương trình

### Cách 1: Khởi chạy Master Launcher tổng hợp (Khuyên dùng)
```bash
python main.py
```
> Cửa sổ ứng dụng hiển thị với thanh điều hướng đầu trang. Bấm **F1** để vào mô phỏng GridWorld 4x4, **M** để về Menu, **F11** để phóng to Toàn màn hình.

### Cách 2: Khởi chạy trực tiếp mô phỏng GridWorld 4x4
```bash
python src/demo1.py
# Hoặc: python main.py --demo 1
```

### Cách 3: Demo HTML cho video (giao diện 16:9 tối giản, đồng bộ giọng đọc ~5 phút)
```bash
# 1. Xuất dữ liệu thực nghiệm ra web/data.js
python scripts/export_web_data.py

# 2. (Tùy chọn) Tạo lại file giọng đọc AI (~5 phút) bằng VieNeu-TTS-v3-Turbo
python scripts/generate_voiceover.py
```
Sau đó mở trực tiếp file `web/index.html` bằng trình duyệt (Chrome / Edge), bấm **F** (hoặc **F11**) để vào toàn màn hình, bấm **H** để ẩn thanh gợi ý phím tắt và bấm **A** để tự động phát toàn bộ 6 cảnh kèm giọng đọc AI khớp thời gian khi quay video. Kịch bản lời thoại chi tiết nằm trong `docs/Transcript_5phut.md`, file âm thanh ghép sẵn nằm tại `web/audio/full_voiceover_5min.mp3`.

Các phím tắt trong Demo HTML:
- **Space** / **→**: Chuyển bước tiếp theo (hoặc sang cảnh kế tiếp)
- **←**: Quay lại cảnh trước
- **1** – **6**: Nhảy trực tiếp đến từng cảnh (1: Môi trường MDP, 2: Agent ngẫu nhiên, 3: Value Iteration, 4: Policy Iteration, 5: Chính sách tối ưu $\pi^*$, 6: So sánh $\pi^*$ vs đường tắt sát bẫy)
- **P**: Tạm dừng / Tiếp tục hoạt ảnh và giọng đọc
- **R**: Chạy lại cảnh hiện tại
- **A**: Tự động phát toàn bộ demo (~5 phút) từ đầu đến cuối
- **M**: Bật/tắt giọng đọc AI khi phát tự động
- **F**: Bật/tắt toàn màn hình
- **H**: Ẩn/hiện thanh phím tắt dưới đáy màn hình

### Cách 4: Xuất lại toàn bộ ảnh biểu đồ cho Slide PowerPoint
```bash
python scripts/export_figures.py
```
> Ảnh biểu đồ chất lượng cao sẽ được lưu vào thư mục `docs/figures/` gồm:
> - `demo1_convergence.png`: Đường cong hội tụ sai số $\max \|\Delta V\|$ qua từng vòng lặp.
> - `demo1_heatmap_values.png`: Bản đồ nhiệt lan truyền giá trị Bellman $V^*(s)$.
> - `demo1_policy_arrows.png`: Bản đồ mũi tên chính sách tối ưu $\pi^*(s)$.

---

## 5. Thuyết minh chi tiết GridWorld 4x4 (MDP)

### 1. Mô hình hóa toán học MDP:
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

### 2. Đối chiếu 2 Thuật toán Quy hoạch động (Tab 3):
| Tiêu chí | Value Iteration (Lập giá trị) | Policy Iteration (Lập chính sách) |
| :--- | :--- | :--- |
| **Bản chất toán học** | Cập nhật trực tiếp Bellman Optimality Backup:<br>$V_{k+1}(s) \leftarrow \max_a \left[ R(s,a) + \gamma \sum P V_k \right]$ | Luân phiên qua 2 pha rõ rệt:<br>• **Pha 1 (Evaluation):** Giải hệ Bellman tìm $V^{\pi_k}$<br>• **Pha 2 (Improvement):** $\pi_{k+1} \leftarrow \arg\max Q(s,a)$ |
| **Số vòng lặp hội tụ** | Cần **48 vòng lặp nhỏ** ($\theta = 10^{-4}$). | **Chỉ đúng 2 - 3 vòng lặp lớn** là chính sách đã ổn định! |
| **Đặc điểm tính toán** | Mỗi bước tính toán cực nhanh, đơn giản. | Mỗi vòng giải $V^\pi$ nặng hơn về chi phí tính toán. |
| **Trực quan hóa UI** | Xem bản đồ nhiệt và số $V$ lan tỏa dần. | Xem các mũi tên $\pi_k$ tự động lật hướng né bẫy sau mỗi pha. |

### 3. Đối chiếu 2 Chính sách trên 2 Ma trận cạnh nhau (Tab 5):
| Chỉ tiêu so sánh | Chính sách tối ưu $\pi^*$ (Né bẫy an toàn) | Chính sách sát bẫy (Thiển cận - Mạo hiểm) |
| :--- | :--- | :--- |
| **Hành trình trên lưới** | Lên dọc Cột 1 $\to$ Sang phải Hàng 4 về Đích | Sang phải Hàng 1 $\to$ Lên dọc Cột 4 về Đích |
| **Kỳ vọng $V(\text{Start})$** | **$6.78$** (Giá trị kỳ vọng cao vượt trội) | **$2.07$** (Bị kéo sụt giảm nghiêm trọng) |
| **Tỉ lệ thành công (1000 ep)** | **$88.5\%$** | **$63.4\%$** |
| **Tỉ lệ rơi vào bẫy** | **$11.5\%$** (Chỉ chịu rủi ro tại ô $(4,3)$) | **$28.3\%$** (Rủi ro trượt cao gấp gần 3 lần) |
| **Độ dài lý thuyết** | **6 bước** (3 Lên + 3 Phải) | **6 bước** (3 Phải + 3 Lên - BẰNG NHAU) |
| **Kết luận toán học** | Toán Bellman tự cân bằng giữa bước đi và rủi ro trượt vào bẫy $(-10)$ để tự chọn đường đi vòng an toàn mà không cần code cứng! |

---

## 6. Bảng phím tắt thao tác điều khiển

| Phím tắt | Vị trí áp dụng | Chức năng chi tiết |
| :--- | :--- | :--- |
| **F11** | Toàn bộ ứng dụng | **Bật/Tắt Toàn màn hình (Borderless Fullscreen)** sắc nét |
| **F1** hoặc **1** | Mọi màn hình | Chuyển ngay sang **GridWorld 4x4** |
| **M** hoặc **Esc** | Mọi màn hình | Quay trở lại **Menu chính** |
| **Phím 1 đến 5** | Trong GridWorld 4x4 | Chuyển trực tiếp giữa 5 Tab của mô phỏng |
| **Space** | Trong GridWorld 4x4 | Tạm dừng (Pause) / Tiếp tục (Resume) mô phỏng |
| **N** | Trong GridWorld 4x4 | Thực hiện **1 bước tiếp theo** (Next step) hoặc 1 vòng lặp Bellman |
| **R** | Trong GridWorld 4x4 | Đặt lại vị trí Robot về ô xuất phát (Reset Episode) |

---

## 7. Giấy phép & Tác giả
- Đồ án môn học: **Cơ sở Trí tuệ Nhân tạo (CSAI)**.
- GitHub Repository: [BaoPhucxD14022006/demo_MDP](https://github.com/BaoPhucxD14022006/demo_MDP.git)
