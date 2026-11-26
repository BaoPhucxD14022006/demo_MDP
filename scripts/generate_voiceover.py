"""Tạo giọng đọc thuyết trình ~5 phút bằng VieNeu-TTS-v3-Turbo và xuất Transcript_5phut.md."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np
import soundfile as sf
from vieneu import Vieneu

SAMPLE_RATE = 48000
GAP_BETWEEN_SEGMENTS_SEC = 1.20
ROOT_DIR = Path(__file__).resolve().parent.parent

# 7 phân đoạn khớp với 6 cảnh trong web/app.js (Cảnh 1 có 2 beat: s1a, s1b)
SEGMENTS: list[dict] = [
    {
        "key": "s1a",
        "filename": "seg_1a.mp3",
        "title": "Cảnh 1 (Phần 1) — Mô hình hóa MDP trên GridWorld 4x4",
        "visual_cue": "Hiển thị lưới 4×4 với START (1,1), ĐÍCH (4,4) +10, hai ô BẪY (3,3) và (3,2) −10 cùng thẻ thông số S, A, R, γ.",
        "tts_sentences": [
            "Xin chào thầy cô và các bạn, hôm nay mình sẽ minh họa Quy hoạch động trên lưới bốn nhân bốn theo khung toán học Em Đi Pi.",
            "Trên màn hình là không gian trạng thái Ét gồm mười sáu ô lưới từ ô một một ở góc dưới trái đến ô bốn bốn ở góc trên phải, với bốn hành động lên, xuống, trái, phải.",
            "Về phần thưởng, ô đích bốn bốn thưởng cộng mười, hai ô bẫy tại ba ba và ba hai phạt nặng âm mười và kết thúc lượt đi ngay lập tức.",
            "Mỗi bước đi thông thường trừ nhẹ âm không phẩy không bốn điểm, va tường biên đứng yên và phạt thêm âm không phẩy hai.",
            "Hệ số chiết khấu gam ma bằng không phẩy chín mươi chín cho thấy tác tử ưu tiên giá trị dài hạn.",
        ],
        "display_text": (
            "Xin chào thầy cô và các bạn, hôm nay mình sẽ minh họa Quy hoạch động trên lưới 4×4 theo khung toán học Markov Decision Process (MDP).\n\n"
            "Trên màn hình là không gian trạng thái $S$ gồm 16 ô lưới từ `(1,1)` ở góc dưới trái đến `(4,4)` ở góc trên phải, với 4 hành động $A = \\{\\text{Lên}, \\text{Xuống}, \\text{Trái}, \\text{Phải}\\}$. "
            "Ô Đích `(4,4)` thưởng `+10`, còn hai ô Bẫy tại `(3,3)` và `(3,2)` phạt `-10` và kết thúc lượt đi ngay lập tức. "
            "Mỗi bước đi trừ nhẹ `-0.04`, va tường biên đứng yên và phạt thêm `-0.2`. Hệ số chiết khấu $\\gamma = 0.99$ giúp tác tử ưu tiên giá trị dài hạn."
        ),
    },
    {
        "key": "s1b",
        "filename": "seg_1b.mp3",
        "title": "Cảnh 1 (Phần 2) — Động lực chuyển trạng thái ngẫu nhiên 80 / 10 / 10",
        "visual_cue": "Hiện 3 mũi tên minh họa tại ô START (1,1): mũi tên thẳng 80%, hai mũi tên trượt trái/phải 10%.",
        "tts_sentences": [
            "Điểm quan trọng nhất của bài toán Em Đi Pi là yếu tố ngẫu nhiên trong động lực chuyển trạng thái.",
            "Mỗi khi rô bốt ra lệnh đi theo một hướng, chỉ có tám mươi phần trăm xác suất là nó đi đúng hướng mong muốn.",
            "Hai mươi phần trăm còn lại chia đều, mười phần trăm trượt vuông góc sang trái và mười phần trăm trượt sang phải.",
            "Chính độ trượt hai mươi phần trăm này khiến việc đi sát mép bẫy trở nên cực kỳ nguy hiểm.",
        ],
        "display_text": (
            "Điểm quan trọng nhất của bài toán MDP là yếu tố ngẫu nhiên trong động lực chuyển trạng thái $P(s' \\mid s, a)$. "
            "Mỗi khi robot ra lệnh di chuyển, chỉ có **80%** xác suất đi đúng hướng mong muốn; **20%** còn lại chia đều **10%** trượt vuông góc sang trái và **10%** trượt sang phải.\n\n"
            "Chính độ trượt 20% này khiến việc đi sát mép bẫy trở nên cực kỳ nguy hiểm."
        ),
    },
    {
        "key": "s2",
        "filename": "seg_2.mp3",
        "title": "Cảnh 2 — Agent hành động ngẫu nhiên (Baseline thất bại)",
        "visual_cue": "Robot chạy liên tiếp các tập ngẫu nhiên, vệt xám loằng ngoằng, liên tục nháy đỏ rơi vào Bẫy −10; bảng thống kê 1000 tập bên phải.",
        "tts_sentences": [
            "Bây giờ, ta quan sát tác tử hành động hoàn toàn ngẫu nhiên trên lưới bốn nhân bốn.",
            "Ở mỗi bước, rô bốt chọn ngẫu nhiên một trong bốn hướng mà không hề xét đến vị trí đích hay hai ô bẫy ở cột ba.",
            "Chỉ sau vài bước di chuyển loằng ngoằng, do có hai ô bẫy nằm ngay trung tâm cộng thêm xác suất trượt hai mươi phần trăm, rô bốt nhanh chóng rơi thẳng vào ô bẫy âm mười.",
            "Kiểm chứng một nghìn tập với giới hạn tối đa năm mươi bước mỗi tập, tác tử ngẫu nhiên chỉ tới đích thành công sáu phẩy tám phần trăm.",
            "Tỉ lệ rơi bẫy lên tới chín mươi phẩy hai phần trăm, ba phần trăm còn lại bị tham ao do đi quá năm mươi bước, kéo điểm trung bình xuống âm chín phẩy tám mươi chín.",
            "Vì vậy, ta cần áp dụng hai thuật toán Quy hoạch động kinh điển để tìm chính sách tối ưu.",
        ],
        "display_text": (
            "Bây giờ, ta quan sát tác tử hành động hoàn toàn ngẫu nhiên trên lưới 4×4. Ở mỗi bước, robot chọn đều một trong 4 hướng mà không xét đến vị trí Đích hay hai ô Bẫy ở cột 3.\n\n"
            "Chỉ sau vài bước di chuyển loằng ngoằng, cộng thêm xác suất trượt 20%, robot nhanh chóng rơi vào Bẫy `−10`. "
            "Kiểm chứng Monte Carlo trên **1.000 tập** (tối đa **50 bước/tập**) cho thấy: tỉ lệ thành công chỉ đạt **6.8%**, tỉ lệ rơi bẫy lên tới **90.2%**, và **3.0%** bị **Timeout** do đi quá 50 bước, kéo điểm thưởng trung bình xuống **−9.90**.\n\n"
            "Vì vậy, ta cần áp dụng hai thuật toán Quy hoạch động kinh điển để tìm chính sách tối ưu."
        ),
    },
    {
        "key": "s3",
        "filename": "seg_3.mp3",
        "title": "Cảnh 3 — Thuật toán Value Iteration & Trích xuất chính sách π*",
        "visual_cue": "Bản đồ nhiệt V(s) lan tỏa qua 48 vòng lặp đến khi hội tụ (V*(1,1)=6.78), sau đó phủ mũi tên trích xuất chính sách π* trực tiếp lên bảng V*.",
        "tts_sentences": [
            "Đầu tiên là thuật toán Lặp giá trị, hay còn gọi là Va liu I tơ rây sần.",
            "Thuật toán khởi tạo giá trị V bằng không, rồi lặp lại phép cập nhật tối ưu BEO men trên toàn bộ mười sáu trạng thái.",
            "Ở mỗi vòng lặp, giá trị mới của một ô bằng giá trị lớn nhất theo bốn hành động của phần thưởng tức thời cộng với gam ma nhân kỳ vọng các ô kế tiếp.",
            "Trên bản đồ nhiệt, giá trị dương lan tỏa ngược dần từ ô đích bốn bốn ra các ô lân cận như ba bốn và bốn ba.",
            "Ngược lại, hai ô hàng một là ba một và bốn một có giá trị thấp hơn hẳn do nằm sát bẫy và chịu hai mươi phần trăm nguy cơ trượt.",
            "Trên đồ thị thang lô ga rít, sai số cực đại giảm đều và cắt xuống ngưỡng mười mũ trừ bốn sau bốn mươi tám vòng lặp, cho V sao tại một một bằng sáu phẩy bảy mươi tám.",
            "Tuy nhiên, riêng bảng số V sao chưa chỉ ra ngay hướng đi; mục đích của việc tính V sao là để bước cuối cùng ta trích xuất ra chính sách tối ưu pi sao.",
            "Tại mỗi ô, rô bốt nhìn trước một bước sang các ô kề cạnh và chọn hành động cho kỳ vọng cao nhất, chẳng hạn từ một một chọn đi lên ô sáu phẩy chín sáu thay vì sang phải sáu phẩy sáu lăm.",
        ],
        "display_text": (
            "Đầu tiên là thuật toán **Value Iteration**. Ta khởi tạo $V(s) = 0$ rồi lặp lại phép cập nhật Bellman Optimality Backup trên toàn bộ 16 trạng thái: "
            "$V_{k+1}(s) \\leftarrow \\max_a \\sum_{s'} P(s' \\mid s,a)[R + \\gamma V_k(s')]$.\n\n"
            "Trên bản đồ nhiệt, giá trị dương lan tỏa ngược dần từ ô Đích `(4,4)`. Ngược lại, hai ô `(3,1)` và `(4,1)` có giá trị thấp hơn hẳn do nằm sát bẫy và chịu 20% nguy cơ trượt. "
            "Sau đúng **48 vòng lặp**, sai số $\\max|\\Delta V|$ cắt xuống dưới ngưỡng $\\theta = 10^{-4}$, cho $V^*(1,1) = 6.78$.\n\n"
            "**Sau khi tính xong $V^*$ để làm gì?** Riêng bảng số $V^*$ chưa chỉ ra hướng hành động, nên bước cuối cùng ta thực hiện **trích xuất chính sách (Policy Extraction)**: tại mỗi ô, robot nhìn trước 1 bước và chọn hướng cho kỳ vọng cao nhất $\\pi^*(s) = \\arg\\max_a Q^*(s,a)$ — ví dụ tại `(1,1)` chọn đi **Lên** sang `(1,2) = 6.96` thay vì sang Phải `(2,1) = 6.65`."
        ),
    },
    {
        "key": "s4",
        "filename": "seg_4.mp3",
        "title": "Cảnh 4 — Thuật toán Policy Iteration (Lặp chính sách)",
        "visual_cue": "Luân phiên Pha 1 (Đánh giá V^π) và Pha 2 (Cải tiến π, tô vàng các ô đổi hướng mũi tên); hội tụ hoàn toàn sau 3 vòng.",
        "tts_sentences": [
            "Tiếp theo là thuật toán Lặp chính sách, gọi là Po li xi I tơ rây sần, tách rõ thành hai pha luân phiên nhau.",
            "Ở pha một, Đánh giá chính sách, ta cố định bộ mũi tên hiện tại và giải hệ phương trình tuyến tính BEO men để tính chính xác bảng giá trị V pi.",
            "Ở pha hai, Cải tiến chính sách, thuật toán duyệt từng ô và chọn lại hướng mũi tên tốt nhất theo giá trị Q.",
            "Các ô được tô màu vàng trên lưới chính là những ô vừa thay đổi hướng mũi tên so với bước trước.",
            "Chỉ sau đúng ba vòng lặp lớn luân phiên giữa đánh giá và cải tiến, không còn bất kỳ ô nào thay đổi hướng nữa.",
            "Chính sách đã ổn định hoàn toàn và hội tụ về cùng một chính sách tối ưu pi sao, nhưng với số vòng lặp ngoài ít hơn rất nhiều.",
        ],
        "display_text": (
            "Tiếp theo là thuật toán **Policy Iteration**, tách riêng thành 2 pha luân phiên:\n"
            "- **Pha 1 (Đánh giá $V^\\pi$):** Cố định bộ mũi tên hiện tại và tính chính xác bảng giá trị kỳ vọng $V^{\\pi_k}$.\n"
            "- **Pha 2 (Cải tiến $\\pi$):** Chọn lại hướng mũi tên tốt nhất theo $\\arg\\max_a Q(s,a)$; các ô vừa đổi hướng được tô màu vàng.\n\n"
            "Chỉ sau đúng **3 vòng lặp lớn**, không còn ô nào đổi hướng nữa — thuật toán hội tụ về cùng chính sách tối ưu $\\pi^*$ với số vòng lặp ngoài ít hơn rất nhiều."
        ),
    },
    {
        "key": "s5",
        "filename": "seg_5.mp3",
        "title": "Cảnh 5 — Thực thi chính sách tối ưu π*",
        "visual_cue": "Hiển thị bộ mũi tên π* màu xanh lá; robot chạy ổn định dọc Cột 1 lên Hàng 4 rồi rẽ phải về Đích (4,4).",
        "tts_sentences": [
            "Từ bảng giá trị tối ưu vừa tìm được, ta rút trích chính sách pi sao biểu diễn bằng các mũi tên màu xanh lá trên từng ô.",
            "Từ ô xuất phát một một, rô bốt đi thẳng lên dọc theo cột một đến hàng bốn, sau đó rẽ phải theo hàng bốn để tiến về đích bốn bốn.",
            "Thậm chí tại ô hai một, mũi tên còn chủ động chỉ sang trái quay về cột một an toàn thay vì tiến gần cụm bẫy cột ba.",
            "Kiểm chứng trên một nghìn tập mô phỏng, chính sách pi sao đạt tỉ lệ tới đích thành công lên tới tám mươi tám phẩy năm phần trăm.",
            "Tỉ lệ rơi bẫy giảm mạnh từ hơn chín mươi phần trăm xuống chỉ còn mười một phẩy năm phần trăm, chủ yếu xảy ra tại ô ba bốn ngay trên bẫy ba ba.",
            "Toàn bộ hành vi né bẫy thông minh này đều tự sinh ra từ phép tối ưu BEO men mà không cần lập trình điều kiện thủ công.",
        ],
        "display_text": (
            "Rút trích từ $V^*$, ta thu được chính sách tối ưu $\\pi^*$ (các mũi tên xanh lá). "
            "Từ `(1,1)`, robot đi lên dọc **Cột 1** đến **Hàng 4**, rồi sang phải về Đích `(4,4)`. Tại ô `(2,1)`, mũi tên cũng chủ động quay trái về Cột 1 an toàn.\n\n"
            "Kiểm chứng trên **1.000 tập**: tỉ lệ thành công đạt **88.5%**, tỉ lệ rơi bẫy giảm xuống còn **11.5%** (chủ yếu tại ô `(3,4)` ngay trên bẫy `(3,3)`).\n\n"
            "Toàn bộ hành vi né bẫy tự nảy sinh từ phép tối ưu Bellman mà không cần lập trình thủ công."
        ),
    },
    {
        "key": "s6",
        "filename": "seg_6.mp3",
        "title": "Cảnh 6 — Đối chiếu nghiệm tối ưu π* và Chính sách tự đặt sát bẫy",
        "visual_cue": "Hai lưới chạy đua song song: bên trái nghiệm tối ưu π* (xanh lá) đi vòng an toàn Cột 1 → Hàng 4; bên phải chính sách tự đặt sát bẫy (đỏ nét đứt) đi qua 3 điểm rủi ro và dễ rơi bẫy hoặc kẹt tường trên.",
        "tts_sentences": [
            "Ở cảnh cuối cùng này, để thấy rõ vì sao thuật toán lại chọn nhánh đi vòng bên trái, ta đặt nghiệm tối ưu pi sao đối chiếu trực tiếp với một chính sách tự đặt bằng tay ở bên phải.",
            "Bên trái là chính sách tối ưu pi sao do Quy hoạch động giải ra: rô bốt đi thẳng lên dọc cột một tới hàng bốn rồi rẽ phải về đích, tốn đúng sáu bước lý thuyết.",
            "Còn bên phải không phải nghiệm của thuật toán, mà là một chiến lược đối chứng tự chọn: ép rô bốt đi sang phải hết hàng một rồi đi thẳng lên theo cột bốn, cũng dài đúng sáu bước như nhau.",
            "Nếu môi trường không có độ trượt, hai lộ trình sáu bước này sẽ tốt ngang nhau; nhưng khi có hai mươi phần trăm xác suất trượt vuông góc ở mỗi bước, độ an toàn của chúng lại khác biệt hoàn toàn.",
            "Với chính sách pi sao bên trái, suốt chặng đi lên cột một rô bốt tránh xa hẳn cụm bẫy; lỡ trượt sang cột hai thì mũi tên tại đó lại đưa nó quay về cột một, nên chỉ chịu rủi ro trượt duy nhất một lần tại ô ba bốn sát đích.",
            "Ngược lại, lộ trình tự đặt bên phải đi men sát cụm bẫy nên phải băng qua tới ba điểm nguy hiểm liên tiếp tại các ô ba một, bốn hai và bốn ba, nơi chỉ một cú trượt mười phần trăm là rơi thẳng vào bẫy âm mười.",
            "Chưa kể ở bên phải, nếu từ hàng một rô bốt lỡ trượt sớm lên vùng phía trên bên trái, các mũi tên chỉ thẳng lên sẽ làm nó kẹt cứng ở tường trên cùng cho đến khi hết năm mươi bước.",
            "Kiểm chứng trên một nghìn tập mô phỏng cho thấy sự chênh lệch rất lớn: chính sách tối ưu bên trái đạt giá trị kỳ vọng sáu phẩy bảy mươi tám, tỉ lệ thắng tám mươi tám phẩy năm phần trăm, rơi bẫy mười một phẩy năm phần trăm và không có tập nào bị tham ao.",
            "Trong khi đó, chính sách sát bẫy bên phải có kỳ vọng sụt mạnh xuống chỉ còn hai phẩy không bảy, tỉ lệ thắng giảm còn sáu mươi ba phẩy bốn phần trăm, rơi bẫy tăng vọt lên hai mươi tám phẩy ba phần trăm và tám phẩy ba phần trăm bị tham ao.",
            "Từ thực nghiệm này, ta rút ra thông điệp cốt lõi của Em Đi Pi: trong môi trường ngẫu nhiên, đường ngắn nhất chưa chắc đã tối ưu; phương trình BEO men tự động định lượng rủi ro để chọn lộ trình an toàn dài hạn mà không cần gán bất kỳ quy tắc né bẫy thủ công nào.",
            "Phần trình bày minh họa thực nghiệm Quy hoạch động trên lưới bốn nhân bốn của nhóm mình đến đây là kết thúc. Xin chân thành cảm ơn thầy cô và các bạn đã chú ý lắng nghe.",
        ],
        "display_text": (
            "Ở cảnh cuối cùng này, để thấy rõ vì sao thuật toán lại chọn nhánh đi vòng bên trái, ta đặt **nghiệm tối ưu $\\pi^*$** đối chiếu trực tiếp với **một chính sách tự đặt bằng tay** ở bên phải.\n\n"
            "Bên trái là chính sách tối ưu $\\pi^*$ do Quy hoạch động giải ra: robot đi thẳng lên dọc Cột 1 tới Hàng 4 rồi rẽ phải về Đích, tốn đúng **6 bước lý thuyết**. Còn bên phải **không phải nghiệm của thuật toán**, mà là một chiến lược đối chứng tự chọn: ép robot đi sang phải hết Hàng 1 rồi đi thẳng lên theo Cột 4, cũng dài đúng **6 bước** như nhau. Nếu môi trường không có độ trượt, hai lộ trình 6 bước này sẽ tốt ngang nhau; nhưng khi có **20% xác suất trượt vuông góc** ở mỗi bước, độ an toàn của chúng lại khác biệt hoàn toàn.\n\n"
            "Với chính sách $\\pi^*$ bên trái, suốt chặng đi lên Cột 1 robot tránh xa hẳn cụm bẫy; lỡ trượt sang Cột 2 thì mũi tên tại đó lại đưa nó quay về Cột 1, nên chỉ chịu rủi ro trượt **duy nhất 1 lần** tại ô `(3,4)` sát Đích. Ngược lại, lộ trình tự đặt bên phải đi men sát cụm bẫy nên phải băng qua tới **3 điểm nguy hiểm liên tiếp** tại các ô `(3,1)`, `(4,2)` và `(4,3)`, nơi chỉ một cú trượt 10% là rơi thẳng vào bẫy `-10`. Chưa kể ở bên phải, nếu từ Hàng 1 robot lỡ trượt sớm lên vùng phía trên bên trái, các mũi tên chỉ thẳng lên sẽ làm nó **kẹt cứng ở tường trên cùng** cho đến khi hết 50 bước.\n\n"
            "Kiểm chứng trên **1.000 tập mô phỏng** cho thấy sự chênh lệch rất lớn: chính sách tối ưu bên trái đạt giá trị kỳ vọng **6.78**, tỉ lệ thắng **88.5%**, rơi bẫy **11.5%** và không có tập nào bị **Timeout** (`0.0%`). Trong khi đó, chính sách sát bẫy bên phải có kỳ vọng sụt mạnh xuống chỉ còn **2.07**, tỉ lệ thắng giảm còn **63.4%**, rơi bẫy tăng vọt lên **28.3%** và **8.3%** bị **Timeout**.\n\n"
            "**Thông điệp cốt lõi của MDP:** Trong môi trường ngẫu nhiên, đường ngắn nhất chưa chắc đã tối ưu; phương trình Bellman tự động định lượng rủi ro để chọn lộ trình an toàn dài hạn mà không cần gán bất kỳ quy tắc né bẫy thủ công nào.\n\n"
            "Phần trình bày minh họa thực nghiệm Quy hoạch động trên lưới 4×4 của nhóm mình đến đây là kết thúc. Xin chân thành cảm ơn thầy cô và các bạn đã chú ý lắng nghe!"
        ),
    },
]


def _fmt_mmss(sec: float) -> str:
    total = int(round(sec))
    return f"{total // 60:02d}:{total % 60:02d}"


def _assemble_segment(
    sentence_wavs: list[np.ndarray],
    lead_sec: float,
    pause_sec: float,
    tail_sec: float,
) -> np.ndarray:
    lead = np.zeros(int(round(lead_sec * SAMPLE_RATE)), dtype=np.float32)
    pause = np.zeros(int(round(pause_sec * SAMPLE_RATE)), dtype=np.float32)
    tail = np.zeros(int(round(tail_sec * SAMPLE_RATE)), dtype=np.float32)

    parts: list[np.ndarray] = [lead]
    for i, w in enumerate(sentence_wavs):
        parts.append(w.astype(np.float32, copy=False))
        if i < len(sentence_wavs) - 1:
            parts.append(pause)
    parts.append(tail)
    return np.concatenate(parts)


def generate_all(only_keys: set[str] | None = None) -> None:
    audio_dir = ROOT_DIR / "web" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    target_segs = [seg for seg in SEGMENTS if only_keys is None or seg["key"] in only_keys]

    print("[1/4] Khởi tạo VieNeu-TTS-v3-Turbo (ONNX CPU)...")
    t_init = time.time()
    tts = Vieneu()
    print(f"      Khởi tạo xong sau {time.time() - t_init:.1f}s")

    raw_sentences: dict[str, list[np.ndarray]] = {}
    t_start = time.time()

    try:
        for seg_idx, seg in enumerate(target_segs, start=1):
            key = seg["key"]
            sent_list = seg["tts_sentences"]
            wavs: list[np.ndarray] = []
            print(f"[2/4] Đang đọc phân đoạn {seg_idx}/{len(target_segs)} ({key}, {len(sent_list)} câu)...")
            for s_idx, text in enumerate(sent_list, start=1):
                wav = tts.infer(text)
                wav = np.asarray(wav, dtype=np.float32).reshape(-1)
                wavs.append(wav)
                print(f"      - Câu {s_idx}/{len(sent_list)}: {len(wav)/SAMPLE_RATE:.2f}s")
            raw_sentences[key] = wavs
    finally:
        tts.close()

    print(f"      Tổng thời gian suy luận TTS: {time.time() - t_start:.1f}s")

    lead_sec = 0.40
    tail_sec = 0.50
    pause_sec = 0.55 if only_keys else 0.42

    if only_keys is None:
        def compute_total(p_sec: float) -> float:
            speech_sum = 0.0
            for seg in SEGMENTS:
                wavs = raw_sentences[seg["key"]]
                dur = lead_sec + tail_sec + sum(len(w) / SAMPLE_RATE for w in wavs) + max(0, len(wavs) - 1) * p_sec
                speech_sum += dur
            return speech_sum + (len(SEGMENTS) - 1) * GAP_BETWEEN_SEGMENTS_SEC

        total_est = compute_total(pause_sec)
        if total_est < 292.0 or total_est > 312.0:
            n_pauses = sum(max(0, len(raw_sentences[seg["key"]]) - 1) for seg in SEGMENTS)
            speech_only = total_est - n_pauses * pause_sec
            target = 300.0
            pause_sec = max(0.25, min(0.85, (target - speech_only) / max(1, n_pauses)))

    print(f"[3/4] Đóng gói audio (pause_sec={pause_sec:.2f}s)...")

    gap_samples = np.zeros(int(round(GAP_BETWEEN_SEGMENTS_SEC * SAMPLE_RATE)), dtype=np.float32)
    combined_parts: list[np.ndarray] = []
    meta_segments: dict[str, dict] = {}
    timeline_rows: list[dict] = []

    cursor_sec = 0.0
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        for idx, seg in enumerate(SEGMENTS):
            key = seg["key"]
            mp3_file = audio_dir / seg["filename"]

            if key in raw_sentences:
                cur_ms = int(round(lead_sec * 1000))
                for s_i, w in enumerate(raw_sentences[key], start=1):
                    print(f"      [Cue {key} #{s_i}] start={cur_ms}ms")
                    cur_ms += int(round((len(w) / SAMPLE_RATE + pause_sec) * 1000))
                seg_wav = _assemble_segment(raw_sentences[key], lead_sec, pause_sec, tail_sec)
                wav_file = tmp_path / f"{key}.wav"
                sf.write(str(wav_file), seg_wav, SAMPLE_RATE)
                subprocess.run(
                    ["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav_file), "-codec:a", "libmp3lame", "-b:a", "192k", str(mp3_file)],
                    check=True,
                )
            else:
                # Giải mã file MP3 sẵn có về WAV 48kHz mono để ghép nối liền mạch
                decoded_wav = tmp_path / f"{key}_decoded.wav"
                subprocess.run(
                    ["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3_file), "-ar", str(SAMPLE_RATE), "-ac", "1", str(decoded_wav)],
                    check=True,
                )
                seg_wav, _ = sf.read(str(decoded_wav), dtype="float32")
                seg_wav = np.asarray(seg_wav, dtype=np.float32).reshape(-1)

            seg_dur = len(seg_wav) / SAMPLE_RATE
            dur_ms = int(round(seg_dur * 1000))

            meta_segments[key] = {
                "src": f"audio/{seg['filename']}?d={dur_ms}",
                "durationMs": dur_ms,
            }
            timeline_rows.append(
                {
                    "seg": seg,
                    "start_sec": cursor_sec,
                    "end_sec": cursor_sec + seg_dur,
                    "duration_sec": seg_dur,
                }
            )

            combined_parts.append(seg_wav)
            cursor_sec += seg_dur
            if idx < len(SEGMENTS) - 1:
                combined_parts.append(gap_samples)
                cursor_sec += GAP_BETWEEN_SEGMENTS_SEC

    full_wav = np.concatenate(combined_parts)
    full_wav_path = audio_dir / "full_voiceover_5min.wav"
    full_mp3_path = audio_dir / "full_voiceover_5min.mp3"
    sf.write(str(full_wav_path), full_wav, SAMPLE_RATE)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(full_wav_path), "-codec:a", "libmp3lame", "-b:a", "192k", str(full_mp3_path)],
        check=True,
    )

    total_sec = len(full_wav) / SAMPLE_RATE
    audio_meta = {
        "gapMs": int(round(GAP_BETWEEN_SEGMENTS_SEC * 1000)),
        "totalSec": round(total_sec, 2),
        "segments": meta_segments,
    }
    (ROOT_DIR / "web" / "audio_meta.js").write_text(
        "window.MDP_AUDIO = " + json.dumps(audio_meta, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )

    md_lines = [
        "# KỊCH BẢN & LỜI THUYẾT TRÌNH DEMO MDP GRIDWORLD 4×4 (~6 PHÚT)",
        "",
        f"- **Tổng thời lượng audio:** `{_fmt_mmss(total_sec)}` ({total_sec:.1f} giây)",
        "- **Giọng đọc AI:** `pnnbao-ump/VieNeu-TTS-v3-Turbo` (48 kHz)",
        "- **File âm thanh tổng hợp:** `web/audio/full_voiceover_5min.mp3` (và `.wav`)",
        "- **Cách quay video khớp lời tự động:** Mở `web/index.html`, bấm **F** (toàn màn hình) → **H** (ẩn thanh phím tắt) → **A** (tự động phát hình + giọng đọc từ đầu đến cuối).",
        "",
        "---",
        "",
        "## Bảng phân bổ thời gian",
        "",
        "| Mốc thời gian | Phân đoạn | Thời lượng |",
        "|---|---|---|",
    ]
    for row in timeline_rows:
        md_lines.append(
            f"| `{_fmt_mmss(row['start_sec'])} – {_fmt_mmss(row['end_sec'])}` | {row['seg']['title']} | {row['duration_sec']:.1f}s |"
        )
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")

    for row in timeline_rows:
        seg = row["seg"]
        md_lines.extend(
            [
                f"## [{_fmt_mmss(row['start_sec'])} – {_fmt_mmss(row['end_sec'])}] {seg['title']}",
                "",
                f"> **Hiệu ứng trên màn hình:** {seg['visual_cue']}  ",
                f"> **File audio:** `web/audio/{seg['filename']}` ({row['duration_sec']:.1f}s)",
                "",
                seg["display_text"],
                "",
                "---",
                "",
            ]
        )

    (ROOT_DIR / "docs" / "Transcript_5phut.md").write_text("\n".join(md_lines), encoding="utf-8")
    print(f"[4/4] Hoàn tất! Tổng thời lượng: {_fmt_mmss(total_sec)} ({total_sec:.2f}s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tạo giọng đọc thuyết trình ~5 phút.")
    parser.add_argument("--only", nargs="+", help="Chỉ tổng hợp lại các phân đoạn chỉ định (vd: --only s2 s6)")
    args = parser.parse_args()
    generate_all(set(args.only) if args.only else None)
