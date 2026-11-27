# A2 — K23 Alden Nguyen: Buổi 3 (Lý thuyết RSI) + Buổi 5 Phần 1 (Logic khung thời gian)

Nguồn: `05_hUKu_qzZtGQ.txt` (~3h20, dài) và `06_NVC64bg-1lk.txt` (~30 phút, bị ngắt giữa chừng). Ví dụ trong bài là Bitcoin/crypto, người giảng nói lý thuyết dùng được cho mọi thị trường.

## 1. Tóm tắt từng buổi

**Buổi 3 — Lý thuyết RSI**
- [0:00–0:20] Chỉ dùng một hệ thống, không ghép thêm chỉ báo. Hệ thống phải cho biết **tương quan lực mua/bán**, không phải "cắt lên mua, cắt xuống bán". Cấm trade future/margin altcoin, chỉ BTC (tối đa ETH).
- [0:20–0:53] Quản trị rủi ro: thị trường tác động lên tài khoản theo 4 cách (lỗ lớn/lỗ nhỏ/lãi lớn/lãi nhỏ), phải loại bỏ "lỗ lớn". **SL tối đa 1% tài khoản mỗi lệnh.** Chấp nhận thua là một phần của nghề.
- [0:53–1:13] Thị trường đi ngang **70%** thời gian, có xu hướng **30%**. Hai trường phái: (1) chỉ đánh lúc có trend, sideway thì nghỉ; (2) đánh cả hai nhưng đổi chiến thuật. Trong trend: **chỉ buy/chờ buy (uptrend), chỉ sell/chờ sell (downtrend)**, không đánh ngược. Biên độ quá nhỏ thì đứng ngoài.
- [1:13–1:38] Cấu trúc giá, sóng điều chỉnh, Fibo 0.5, tỉ lệ người mua/bán theo từng dạng sideway.
- [1:38–1:53] Lý thuyết khung thời gian: mỗi khung là một nhóm nhà đầu tư; sóng luân phiên từ khung nhỏ lên khung lớn.
- [1:53–2:23] RSI: các ngưỡng 20/30/40–60/70/80, chuyển động kiểu hình sin, bỏ phân kỳ.
- [2:23–2:38] Thêm EMA9 và WMA45 lên RSI; tính chất đường trung bình (độ dốc, độ mở rộng).
- [2:38–3:18] "Mô hình tích lũy" (vòng cung) trên RSI, dùng RSI để xác định sóng theo khung, ước lượng thời gian.

**Buổi 5 Phần 1 — Logic khung thời gian (thực chất là lý thuyết "bình nhiên liệu")**
- [0:00–0:15] Chúc năm mới, nói chuyện đọc sách/tư duy (không có nội dung kỹ thuật).
- [0:15–0:20] Bộ công cụ chốt lại: chỉ RSI + 2 đường trung bình; trên chart giá chỉ vẽ kháng cự/hỗ trợ, **không dùng MA trên giá**.
- [0:20–0:25] **"RSI và bình nhiên liệu của sóng"**: dựa vào quãng đường đã đi của xu hướng RSI để đánh giá sóng còn bao nhiêu sức.
- [0:25–0:30] **"Độ mượt"**: chuyển động của đồ thị phải làm đường trung bình mượt, không có đảo chiều nhọn chữ V. Buổi bị ngắt ở đây.

## 2. Định nghĩa và quy tắc cụ thể

### 2.1 Cài đặt chỉ báo
- RSI của TradingView, **tắt đường "RSI-based MA"**. Người giảng không nói chu kỳ RSI, chỉ bảo "không cần chỉnh lại", nên hiểu là **RSI(14) mặc định**.
- Thêm lên RSI (indicator on indicator): **EMA(9) = trung bình nhanh**, **WMA(45) = trung bình chậm**. Ông không giải thích vì sao chọn 9/45, chỉ nói ý tưởng lấy từ một cuốn sách về RSI.

### 2.2 Các vùng RSI (đọc trên **từng khung riêng**)
| Vùng | Ý nghĩa theo người giảng |
|---|---|
| Thực tế dao động 10–90, hiếm khi tới 95 | 0 hoặc 100 không bao giờ xảy ra |
| Phần lớn thời gian nằm trong 30–70 | — |
| ≥ 70 | Lực mua nhiều hơn hẳn lực bán. **Không** hiểu là "quá mua" để bán ngược |
| ≤ 30 | Lực bán nhiều hơn hẳn. **Không** bắt đáy |
| RSI **đi ngang** trong 40–60 | Mua ≈ bán, giá sideway (ông nói tại 60 mua ≈ 1,1 lần bán) |
| ≥ 80 | Mua áp đảo, khoảng **4 lần** bán (80/20), xu hướng tăng cực mạnh |
| ≤ 20 | Bán áp đảo, khoảng 4 lần mua |
| 90 | Mua khoảng 6+ lần bán |

- Trong một xu hướng, RSI chạy **kiểu hình sin** giữa biên trên và biên dưới (không có số cụ thể), thể hiện tâm lý đổi qua lại giữa hưng phấn và sợ hãi.
- **Phân kỳ: tuyệt đối không dùng để ra quyết định.** Trong trend, phân kỳ chỉ là lực mua tạm nghỉ, và khi nhìn thấy được thì giá đã chạy rồi.

### 2.3 Tính chất đường trung bình (áp dụng lên RSI)
- Xu hướng thể hiện qua **độ dốc** và **độ mở rộng** giữa 2 MA: dốc càng lớn, mở càng rộng thì xu hướng càng mạnh.
- RSI đang có xu hướng tăng khi: RSI nằm trên cả 2 MA, EMA9 > WMA45, cả hai dốc lên và đang tách xa nhau. Xu hướng giảm thì ngược lại.
- Không có xu hướng khi 2 MA đi ngang, quấn vào nhau "như dây điện", cắt qua lại liên tục.
- 2 MA **thu hẹp khoảng cách** = xu hướng sắp kết thúc.

### 2.4 "Mô hình tích lũy" (vòng cung) — đơn vị xác định sóng
- Một đoạn RSI có xu hướng rõ (như 2.3) tạo hình vòng cung: đầu đoạn dốc mạnh nhất, sau đó cong dần và mềm lại, kết thúc khi RSI cắt ngược qua 2 MA.
- Cách gọi tên dễ gây nhầm: **xu hướng tăng của RSI = "mô hình tích lũy cho lực bán" = sóng TĂNG trên giá**. Xu hướng giảm của RSI = "tích lũy cho lực mua" = sóng GIẢM trên giá.
- Nếu MA đi ngang hoặc không mở rộng thì **không phải mô hình**.
- **Mỗi mô hình tương ứng với một con sóng của đúng khung đó.** Điểm RSI cắt lên/cắt xuống qua 2 MA là điểm bắt đầu/kết thúc của sóng giá.
- Vì sao là vòng cung: tâm lý đám đông chỉ đổi dần dần, nên RSI không đảo chiều kiểu chữ V hay hình vuông.

### 2.5 RSI giảm có phải lực bán tăng không?
- **Xu hướng giảm của RSI không đồng nghĩa với giá giảm.** Phải xem kèm giá:
  - RSI điều chỉnh mà giá đi ngang hoặc hồi nông → **lực mua chỉ tạm nghỉ**, không có lực bán vào. Nếu xu hướng tiếp diễn thì sóng sau mạnh.
  - RSI điều chỉnh, giá giảm sâu và phá đáy cấu trúc → **lực bán tăng thật**.

### 2.6 Cấu trúc giá và tỉ lệ lực
- Cấu trúc tăng là đỉnh sau cao hơn, đáy sau cao hơn. Sóng điều chỉnh **không sâu quá Fibo 0.5** của sóng trước thì chỉ là lực mua tạm nghỉ, không phải lực bán tăng.
- Phá **đáy gần nhất** → xu hướng tăng **mất hiệu lực, nhưng chưa phải downtrend**. Xác nhận giảm khi có sóng A phá đáy, sau đó B hồi không quá 50% A (ông nói xác suất khoảng 90% sẽ giảm tiếp), rồi giá phá đáy của A. Thời điểm xác nhận này đã muộn và SL xa.
- Sóng điều chỉnh xóa gần hết sóng trước = lực bán tăng.
- Tỉ lệ minh họa (trên 100 người): sideway ngang 50/50; sideway hướng xuống (đỉnh thấp dần) bán 60/mua 40; sideway hướng lên mua 60/bán 40; cấu trúc tăng (hồi ≤ 0.5) mua 90/bán 10; cấu trúc giảm thì ngược lại. Chênh lệch ít không làm giá tạo xu hướng.
- Kênh hướng lên nhưng hồi về 0.6–0.7 thì **không** tính là cấu trúc tăng.

### 2.7 Lý thuyết khung thời gian
- Mỗi khung đại diện cho một nhóm nhà đầu tư với vốn, mục tiêu, SL và thời gian khác nhau. Ví dụ: sóng M5 khoảng 2 giờ, sóng H4 vài ngày, sóng D1 nửa tháng đến 1 tháng, sóng 2W có thể nửa năm.
- **Sóng luân phiên từ khung nhỏ lên khung lớn liền kề**: 1m → 5m → 15m → 1H → H4 → (12H) → 1D → 3D/4D → 1W → 2W → 1M. Khung nhỏ chạy xong sóng thì nhường quyền quyết định cho khung lớn kế tiếp. Có hiện tượng sóng trong sóng.
- Khi RSI của một khung **không có mô hình** (chạy lòng vòng) → khung đó đã chạy xong, đang chờ khung lớn hơn.
- Giai đoạn khó chịu nhất: tất cả khung nhỏ nằm im chờ khung lớn quyết định.
- Ví dụ xác định sóng: một nhịp giảm chỉ là **điều chỉnh của 1W** khi RSI 1W thoát khỏi xu hướng tăng. Nếu RSI 1W vẫn đang tăng thì đó chỉ là điều chỉnh của khung D1. Xác định sai khung thì đặt sai target.
- "Lý thuyết tịnh tiến" (học sau): mô hình ở khung nhỏ thất bại vì khung lớn hơn đang có lực ngược chiều. Ví dụ: 100 người mua ở 1W bị 500 người bán ở 1M đè xuống.
- Ước lượng thời gian: 2 MA trên RSI 2W đang thu hẹp → còn khoảng 3–6 nến nữa (1–2 tháng) mới có sóng 2W.

### 2.8 Bình nhiên liệu (Buổi 5 P1)
- Xu hướng RSI = bình xăng. **Mới cắt qua 2 MA và đang mở rộng → bình còn đầy**, nên tìm điểm vào cùng chiều. **RSI đã đi xa → bình gần cạn**, không tìm điểm vào cùng chiều nữa mà chờ chiều ngược lại (ví dụ: đã tăng xa thì thôi long, chờ short).
- Ví dụ: xu hướng giảm của RSI 2W đã đi xa → chuẩn bị tinh thần long sóng hồi. Lực mua mạnh có thể tạo sóng hồi đơn, yếu thì chỉ thành sideway. RSI 1M thì "còn khá nhiều nhiên liệu".
- **Độ mượt**: chuyển động của RSI phải làm đường trung bình mượt. Khi 2 MA đang mở rất rộng, RSI không thể bật ngược ngay. Hoặc RSI kéo dần để MA đuổi theo, hoặc nếu bị giật mạnh thì phải tích lũy thêm một "vòng cung thứ hai" rồi mới đi tiếp. Lý do là cú sốc tâm lý.

## 3. Quy trình từng bước (theo những gì đã dạy)
1. Xác định giai đoạn: trend hay sideway (bằng độ dốc/độ mở của MA trên RSI và cấu trúc giá) ở nhiều khung.
2. Tìm khung đang "quyết định": khung nhỏ nhất đang có mô hình RSI rõ, trong khi các khung nhỏ hơn đã chạy xong.
3. Trong trend chỉ vào lệnh cùng chiều, ưu tiên lúc bình nhiên liệu còn đầy. Bình gần cạn thì chốt lời, đứng ngoài, chờ.
4. Khi RSI điều chỉnh, xem giá: lực mua chỉ nghỉ thì chờ mua tiếp, lực bán tăng thật thì không mua.
5. SL 1% tài khoản. Biên độ quá nhỏ thì không vào.
- Thời điểm vào lệnh cụ thể (trigger, SL đặt ở đâu, target) **chưa được dạy**. Ông nói sẽ dùng khung nhỏ hơn để vào sớm, không chờ RSI khung lớn cắt qua MA.

## 4. Điểm mơ hồ nếu muốn code thành bot
- **Chu kỳ RSI** không nói rõ, giả định 14. EMA9/WMA45 tính trên chuỗi RSI.
- Các tỉ lệ lực ông đưa ra **sai so với công thức** RS = 100/(100−RSI) − 1. RSI 60 cho RS = 1,5 (ông nói 1,1); RSI 80 cho RS = 4 (đúng); RSI 90 cho RS = 9 (ông nói khoảng 6+). Chỉ nên dùng các ngưỡng, không dùng các tỉ lệ này.
- "Độ dốc", "mở rộng", "đi ngang", "thu hẹp" đều không có ngưỡng số. Cần tự định nghĩa, ví dụ slope của EMA9/WMA45 qua N nến, khoảng cách (EMA9 − WMA45) tăng hay giảm, phần trăm thời gian RSI nằm trong 40–60.
- Mô hình vòng cung cần quy tắc bắt đầu/kết thúc: bắt đầu khi RSI cắt qua cả 2 MA và EMA9 cắt WMA45, kết thúc khi RSI cắt ngược qua MA. Chưa rõ RSI cắt EMA9 thôi hay phải cắt cả 2.
- "Bình nhiên liệu" đầy hay cạn không định lượng. Có thể đo bằng số nến từ lúc cắt, quãng RSI đã đi, hoặc độ rộng đỉnh của 2 MA rồi bắt đầu thu hẹp.
- "Lực mua nghỉ" hay "lực bán tăng" dựa vào độ sâu điều chỉnh của giá (≤ 0.5 Fibo, có phá đáy cấu trúc hay không). Cần thuật toán swing/fractal để có sóng và Fibo.
- Chuỗi khung (1m…1M, 2W, 3D, 12H) có những khung MT5 không có sẵn (2W, 3D), phải tự gộp nến. Logic "khung nào đang quyết định" và "lý thuyết tịnh tiến" chưa dạy xong.
- Chưa có quy tắc entry/SL/TP cụ thể. Phân biệt trend/sideway "trước khi xảy ra" thì ông hứa dạy ở buổi sau.
- Phần lớn ví dụ là khung tuần/tháng của BTC, cần kiểm chứng lại trên XAUUSD H1/M15.
