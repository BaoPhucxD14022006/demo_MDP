# KỊCH BẢN & LỜI THUYẾT TRÌNH DEMO MDP GRIDWORLD 4×4 (~5 PHÚT)

- **Tổng thời lượng audio:** `05:08` (307.5 giây)
- **Giọng đọc AI:** `pnnbao-ump/VieNeu-TTS-v3-Turbo` (48 kHz)
- **File âm thanh tổng hợp:** `web/audio/full_voiceover_5min.mp3` (và `.wav`)
- **Cách quay video khớp lời tự động:** Mở `web/index.html`, bấm **F** (toàn màn hình) → **H** (ẩn thanh phím tắt) → **A** (tự động phát hình + giọng đọc từ đầu đến cuối).

---

## Bảng phân bổ thời gian

| Mốc thời gian | Phân đoạn | Thời lượng |
|---|---|---|
| `00:00 – 00:34` | Cảnh 1 (Phần 1) — Mô hình hóa MDP trên GridWorld 4x4 | 34.5s |
| `00:36 – 00:58` | Cảnh 1 (Phần 2) — Động lực chuyển trạng thái ngẫu nhiên 80 / 10 / 10 | 22.5s |
| `00:59 – 01:40` | Cảnh 2 — Agent hành động ngẫu nhiên (Baseline thất bại) | 41.0s |
| `01:42 – 02:44` | Cảnh 3 — Thuật toán Value Iteration & Trích xuất chính sách π* | 62.1s |
| `02:45 – 03:24` | Cảnh 4 — Thuật toán Policy Iteration (Lặp chính sách) | 39.2s |
| `03:25 – 04:09` | Cảnh 5 — Thực thi chính sách tối ưu π* | 44.1s |
| `04:11 – 05:08` | Cảnh 6 — Đối chiếu π* vs Đường tắt sát bẫy | 56.9s |

---

## [00:00 – 00:34] Cảnh 1 (Phần 1) — Mô hình hóa MDP trên GridWorld 4x4

> **Hiệu ứng trên màn hình:** Hiển thị lưới 4×4 với START (1,1), ĐÍCH (4,4) +10, hai ô BẪY (3,3) và (3,2) −10 cùng thẻ thông số S, A, R, γ.  
> **File audio:** `web/audio/seg_1a.mp3` (34.5s)

Xin chào thầy cô và các bạn, hôm nay mình sẽ minh họa Quy hoạch động trên lưới 4×4 theo khung toán học Markov Decision Process (MDP).

Trên màn hình là không gian trạng thái $S$ gồm 16 ô lưới từ `(1,1)` ở góc dưới trái đến `(4,4)` ở góc trên phải, với 4 hành động $A = \{\text{Lên}, \text{Xuống}, \text{Trái}, \text{Phải}\}$. Ô Đích `(4,4)` thưởng `+10`, còn hai ô Bẫy tại `(3,3)` và `(3,2)` phạt `-10` và kết thúc lượt đi ngay lập tức. Mỗi bước đi trừ nhẹ `-0.04`, va tường biên đứng yên và phạt thêm `-0.2`. Hệ số chiết khấu $\gamma = 0.99$ giúp tác tử ưu tiên giá trị dài hạn.

---

## [00:36 – 00:58] Cảnh 1 (Phần 2) — Động lực chuyển trạng thái ngẫu nhiên 80 / 10 / 10

> **Hiệu ứng trên màn hình:** Hiện 3 mũi tên minh họa tại ô START (1,1): mũi tên thẳng 80%, hai mũi tên trượt trái/phải 10%.  
> **File audio:** `web/audio/seg_1b.mp3` (22.5s)

Điểm quan trọng nhất của bài toán MDP là yếu tố ngẫu nhiên trong động lực chuyển trạng thái $P(s' \mid s, a)$. Mỗi khi robot ra lệnh di chuyển, chỉ có **80%** xác suất đi đúng hướng mong muốn; **20%** còn lại chia đều **10%** trượt vuông góc sang trái và **10%** trượt sang phải.

Chính độ trượt 20% này khiến việc đi sát mép bẫy trở nên cực kỳ nguy hiểm.

---

## [00:59 – 01:40] Cảnh 2 — Agent hành động ngẫu nhiên (Baseline thất bại)

> **Hiệu ứng trên màn hình:** Robot chạy liên tiếp các tập ngẫu nhiên, vệt xám loằng ngoằng, liên tục nháy đỏ rơi vào Bẫy −10; bảng thống kê 1000 tập bên phải.  
> **File audio:** `web/audio/seg_2.mp3` (41.0s)

Bây giờ, ta quan sát tác tử hành động hoàn toàn ngẫu nhiên trên lưới 4×4. Ở mỗi bước, robot chọn đều một trong 4 hướng mà không xét đến vị trí Đích hay hai ô Bẫy ở cột 3.

Chỉ sau vài bước di chuyển loằng ngoằng, cộng thêm xác suất trượt 20%, robot nhanh chóng rơi vào Bẫy `−10`. Kiểm chứng Monte Carlo trên **1.000 tập** (tối đa **50 bước/tập**) cho thấy: tỉ lệ thành công chỉ đạt **6.8%**, tỉ lệ rơi bẫy lên tới **90.2%**, và **3.0%** bị **Timeout** do đi quá 50 bước, kéo điểm thưởng trung bình xuống **−9.90**.

Vì vậy, ta cần áp dụng hai thuật toán Quy hoạch động kinh điển để tìm chính sách tối ưu.

---

## [01:42 – 02:44] Cảnh 3 — Thuật toán Value Iteration & Trích xuất chính sách π*

> **Hiệu ứng trên màn hình:** Bản đồ nhiệt V(s) lan tỏa qua 48 vòng lặp đến khi hội tụ (V*(1,1)=6.78), sau đó phủ mũi tên trích xuất chính sách π* trực tiếp lên bảng V*.  
> **File audio:** `web/audio/seg_3.mp3` (62.1s)

Đầu tiên là thuật toán **Value Iteration**. Ta khởi tạo $V(s) = 0$ rồi lặp lại phép cập nhật Bellman Optimality Backup trên toàn bộ 16 trạng thái: $V_{k+1}(s) \leftarrow \max_a \sum_{s'} P(s' \mid s,a)[R + \gamma V_k(s')]$.

Trên bản đồ nhiệt, giá trị dương lan tỏa ngược dần từ ô Đích `(4,4)`. Ngược lại, hai ô `(3,1)` và `(4,1)` có giá trị thấp hơn hẳn do nằm sát bẫy và chịu 20% nguy cơ trượt. Sau đúng **48 vòng lặp**, sai số $\max|\Delta V|$ cắt xuống dưới ngưỡng $\theta = 10^{-4}$, cho $V^*(1,1) = 6.78$.

**Sau khi tính xong $V^*$ để làm gì?** Riêng bảng số $V^*$ chưa chỉ ra hướng hành động, nên bước cuối cùng ta thực hiện **trích xuất chính sách (Policy Extraction)**: tại mỗi ô, robot nhìn trước 1 bước và chọn hướng cho kỳ vọng cao nhất $\pi^*(s) = \arg\max_a Q^*(s,a)$ — ví dụ tại `(1,1)` chọn đi **Lên** sang `(1,2) = 6.96` thay vì sang Phải `(2,1) = 6.65`.

---

## [02:45 – 03:24] Cảnh 4 — Thuật toán Policy Iteration (Lặp chính sách)

> **Hiệu ứng trên màn hình:** Luân phiên Pha 1 (Đánh giá V^π) và Pha 2 (Cải tiến π, tô vàng các ô đổi hướng mũi tên); hội tụ hoàn toàn sau 3 vòng.  
> **File audio:** `web/audio/seg_4.mp3` (39.2s)

Tiếp theo là thuật toán **Policy Iteration**, tách riêng thành 2 pha luân phiên:
- **Pha 1 (Đánh giá $V^\pi$):** Cố định bộ mũi tên hiện tại và tính chính xác bảng giá trị kỳ vọng $V^{\pi_k}$.
- **Pha 2 (Cải tiến $\pi$):** Chọn lại hướng mũi tên tốt nhất theo $\arg\max_a Q(s,a)$; các ô vừa đổi hướng được tô màu vàng.

Chỉ sau đúng **3 vòng lặp lớn**, không còn ô nào đổi hướng nữa — thuật toán hội tụ về cùng chính sách tối ưu $\pi^*$ với số vòng lặp ngoài ít hơn rất nhiều.

---

## [03:25 – 04:09] Cảnh 5 — Thực thi chính sách tối ưu π*

> **Hiệu ứng trên màn hình:** Hiển thị bộ mũi tên π* màu xanh lá; robot chạy ổn định dọc Cột 1 lên Hàng 4 rồi rẽ phải về Đích (4,4).  
> **File audio:** `web/audio/seg_5.mp3` (44.1s)

Rút trích từ $V^*$, ta thu được chính sách tối ưu $\pi^*$ (các mũi tên xanh lá). Từ `(1,1)`, robot đi lên dọc **Cột 1** đến **Hàng 4**, rồi sang phải về Đích `(4,4)`. Tại ô `(2,1)`, mũi tên cũng chủ động quay trái về Cột 1 an toàn.

Kiểm chứng trên **1.000 tập**: tỉ lệ thành công đạt **88.5%**, tỉ lệ rơi bẫy giảm xuống còn **11.5%** (chủ yếu tại ô `(3,4)` ngay trên bẫy `(3,3)`).

Toàn bộ hành vi né bẫy tự nảy sinh từ phép tối ưu Bellman mà không cần lập trình thủ công.

---

## [04:11 – 05:08] Cảnh 6 — Đối chiếu π* vs Đường tắt sát bẫy

> **Hiệu ứng trên màn hình:** Hai lưới chạy đua song song: bên trái π* (xanh lá) về đích đều đặn; bên phải đường sát bẫy (đỏ nét đứt) thường xuyên trượt vào bẫy −10.  
> **File audio:** `web/audio/seg_6.mp3` (56.9s)

Cảnh cuối đối chiếu trực tiếp hai chiến lược có **cùng độ dài lý thuyết 6 bước** (giới hạn 50 bước/tập):
- **Bên trái — Chính sách tối ưu $\pi^*$:** lên Cột 1, sang phải Hàng 4 → $V(\text{Start}) = 6.78$, thành công **88.5%**, rơi bẫy **11.5%**, Timeout **0.0%**.
- **Bên phải — Đường tắt sát bẫy:** sang phải Hàng 1, lên Cột 4 → $V(\text{Start}) = 2.07$, thành công **63.4%**, rơi bẫy **28.3%**, Timeout **8.3%**.

**Kết luận:** Cùng 6 bước đi, nhưng đường sát bẫy rủi ro cao hơn nhiều. Toán học MDP đã tự cân bằng giữa chi phí từng bước (`-0.04`) và độ an toàn dài hạn trước rủi ro trượt 20%. Cảm ơn thầy cô và các bạn đã theo dõi!

---
