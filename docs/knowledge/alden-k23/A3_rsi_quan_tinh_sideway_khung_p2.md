# A3 — RSI: quán tính, 2 hình thái sideway, logic khung thời gian (K23 Alden Nguyen)

Nguồn: Buổi 4 (`07_XtIL5TU-xBs`) và Buổi 5 Phần 2 (`01_HG0N7FRfDE0`). Ví dụ trong bài chủ yếu là BTC.
Bộ chỉ báo dùng trong khoá: RSI kèm 2 đường trung bình vẽ trên chính RSI. Theo câu hỏi của học viên, đường nhanh là MA9 (màu đỏ) và đường chậm là WMA45 (màu vàng). Người giảng nói ý tưởng lấy từ Ichimoku (9 ≈ 1,5 tuần, 45 ≈ 1,5 tháng) và chọn bộ số này vì backtest thấy "mượt nhất". Chu kỳ RSI không được nhắc trong 2 buổi này.

---

## 1. Tóm tắt từng buổi

### Buổi 4 — Lý thuyết quán tính + 2 hình thái sideway
- [0:00–0:10] Phần nói về tâm lý học viên: 3–4 tháng đầu không dùng tiền thật, phải hỏi nhiều. Người giảng phản đối kiểu hệ thống "cắt lên mua, cắt xuống bán".
- [0:10–0:15] Mục đích của quán tính: đo xem lực mua/bán của một con sóng còn đủ để xu hướng tiếp diễn hay không. Với lý thuyết sóng thông thường phải chờ có sóng A rồi sóng B (hồi về vùng Fibo 0.5 trở lên là còn giữ lực) mới đoán được sóng C. Với quán tính RSI thì biết trước ngay từ đỉnh A.
- [0:15–0:35] Định nghĩa quán tính tăng (RSI ≥ 80), kèm ví dụ trên D1, W1, MN và H4. Nếu RSI có nhiều đỉnh liên tiếp trên 80 thì lực mua rất mạnh, kể cả khi nến tăng chậm.
- [0:35–0:45] 4 giai đoạn của quán tính tăng.
- [0:45–0:50] "Sóng trong sóng": muốn biết sóng W1 còn tăng tiếp không thì xem D1 có tạo quán tính không.
- [0:50–1:00] Quán tính giảm (≤ 20) là đối xứng. Phân biệt "tạm nghỉ lực mua" với "gia tăng lực bán".
- [1:00–1:20] Hai hình thái sideway. Giải thích RSI là tỉ số mua/bán.
- [1:33–3:18] Hỏi đáp. Các ý đáng chú ý: tiêu chí xác nhận RSI cắt, cách xác định sóng thuộc khung nào, mô hình bắt đầu và kết thúc trong vùng 40–60 thì bỏ, không mua ngay lúc RSI vừa lên 80, SL futures ≤ 1% tài khoản.

### Buổi 5 Phần 2 — Bình nhiên liệu + logic khung thời gian
- [0:00–0:25] RSI và "bình nhiên liệu" của sóng. Đồ thị phải di chuyển sao cho đường trung bình mượt. Khi RSI đi quá xa MA thì bị hút ngược về. Lý thuyết "giảm gia tốc".
- [0:25–0:40] Logic khung thời gian: các khung là các nhóm nhà đầu tư cùng biểu quyết. Hai khung chỉ chi phối nhau khi tỉ lệ gấp 3–6 lần. Bài liệt kê các cụm khung.
- [0:40–1:05] Bản chất sóng: khung lớn cho phép, khung nhỏ ủng hộ. Phân biệt sóng với cấu trúc. Đánh giá mức nguy hiểm khi có quán tính ngược chiều ở khung nhỏ.
- [1:09–1:20] Dự báo trước sideway loại 2 bằng hiện tượng ngược pha giữa khung nhỏ và khung lớn liền kề.
- [1:31–1:46] Kịch bản BTC dài hạn (chỉ là ví dụ minh hoạ, không phải quy tắc).

---

## 2. Định nghĩa và quy tắc cụ thể

### 2.1 Trạng thái xu hướng của RSI (nền cho mọi quy tắc khác)
- **RSI đang tăng:** RSI nằm trên cả 2 MA, MA nhanh nằm trên MA chậm, cả 3 đường dốc lên và "mở rộng" ra. RSI đang giảm thì ngược lại.
- **Xác nhận đổi xu hướng** phải đủ 3 điều kiện: (1) RSI cắt qua cả 2 MA, (2) MA nhanh cắt MA chậm, (3) cả 3 đường dốc theo chiều mới và mở rộng. Nếu RSI đã cắt 2 MA nhưng MA nhanh chưa cắt MA chậm thì chỉ là **nhiễu**.
- Mức RSI tại điểm cắt (30/40/60/70) **không quan trọng**, chỉ cần nhìn mô hình.
- **Chỉ tính nến đã đóng.** Trong lúc nến đang chạy, RSI vọt qua 80 rồi đóng nến ở 70 thì không tính.
- **Sóng thuộc khung nào:** một sóng giá là sóng của khung X nếu nó trùng với đúng một pha xu hướng RSI của khung X, tính từ lúc cắt lên đến lúc cắt xuống (hoặc ngược lại).
- **Một sóng tương ứng một mô hình RSI.** Cấu trúc tăng/giảm là chuỗi mô hình lên, xuống nối tiếp nhau (đỉnh và đáy cao dần hoặc thấp dần).
- Không có tỉ lệ quy đổi giữa biên độ RSI và biên độ giá. Mục tiêu giá phải lấy theo kháng cự/hỗ trợ.

### 2.2 Quán tính tăng/giảm ("năng lượng của sóng")
**4 giai đoạn của quán tính tăng:**
1. RSI vào xu hướng tăng **cùng lúc** giá tăng ở sóng đầu. Nếu RSI tăng mà giá đi ngang thì không tính.
2. RSI **đóng nến ≥ 80** thì xác nhận có quán tính tăng. Dự báo hai điều: sóng điều chỉnh sau đó **không sâu**, và sau điều chỉnh sẽ có một sóng tiếp diễn **ít nhất về lại đỉnh cũ hoặc vượt lên**. Đỉnh cũ là đỉnh giá tại lúc RSI ≥ 80. Người giảng đưa xác suất "trên 80%".
3. Điều chỉnh: RSI cắt xuống 2 MA, MA nhanh cắt xuống MA chậm, 3 đường dốc xuống và mở rộng. RSI tạo một "vòng cung".
4. RSI kết thúc vòng cung giảm (cắt lên trở lại), sóng tiếp diễn đưa giá về ít nhất đỉnh cũ. Đến đây quán tính coi như hoàn thành. Nếu đỉnh mới lại có RSI ≥ 80 thì lặp lại 4 bước. Khi đỉnh mới không còn chạm 80 (ví dụ chỉ chớm 70) thì lực đã cạn.

- **Quán tính giảm** đối xứng: RSI đóng nến ≤ 20, mục tiêu ít nhất về lại đáy cũ hoặc sâu hơn. Trên khung lớn trong thị trường bull thì hiếm gặp.
- Mức độ: RSI gần 90 là cực mạnh. Chỉ "chớm 80" là lực đã yếu đi. Dưới 80 thì không đủ điều kiện quán tính.
- **Chiến thuật:** khi còn quán tính tăng thì **chỉ mua hoặc chờ mua**, không short cho tới khi quán tính "reset". Ngay lúc RSI vừa lên 80 thì **không mua đuổi**: phải chờ sóng điều chỉnh rồi mua, hoặc vào lệnh theo sóng nhỏ hơn ở khung thấp hơn.
- **Tạm nghỉ lực mua hay gia tăng lực bán:** cần biết sóng chủ đạo ngay trước đó. Nếu sóng trước là sóng mua (có quán tính) và nhịp chỉnh nông, RSI giữ trên khoảng 40, thì đó là **tạm nghỉ lực mua**. Nếu sóng trước là sóng giảm mà giờ RSI hồi lên thì đó là lực bán đang tạm nghỉ.
- **RSI là tỉ số mua/bán**, nên RSI tăng có hai khả năng: lực mua tăng, hoặc lực bán giảm. RSI ≥ 70 thì chắc chắn lực mua đã trội. RSI ≤ 60 thì còn mơ hồ, phải xem giá: **RSI tăng mà giá đi ngang** nghĩa là lực bán chỉ đang nghỉ, không có lực mua thật vào.
- RSI giảm trong khi giá vẫn nhích lên chỉ xảy ra khi xu hướng cực mạnh. Lực đẩy giá lúc đó đến từ các khung khác.

### 2.3 Hai hình thái sideway
| | Loại 1: không có lực | Loại 2: tranh chấp giữa các khung |
|---|---|---|
| Nguyên nhân | Không bên nào mua/bán đáng kể | Lực mua và bán đều có, thậm chí mạnh, nhưng ngược pha giữa hai khung (ví dụ D1 tăng trong khi W1 giảm) |
| Dấu hiệu RSI | Đỉnh RSI gần nhất **không vượt 70**, đáy gần nhất **không dưới 30** (một cú giật xuống dưới 30 rồi bật lên ngay vẫn tính là yếu). Sau đó RSI trôi dần vào **40–60, về quanh 50**. RSI và 2 MA đi ngang, không dốc, không mở rộng, cắt qua lại nhiều lần | RSI khung nhỏ có mô hình rõ ràng, ngược chiều xu hướng RSI của khung lớn liền kề, trong khi RSI khung lớn còn đang mở rộng |
| Giá | Biên độ nhỏ, giật lên xuống bất thường | Chạy **có quy luật** trong kênh giá hoặc tam giác, biên độ rõ ràng |
| Hành động | **Đứng ngoài** ("sóng rủi ro, không phải sóng lợi nhuận"), hoặc đánh theo mô hình ở khung khác | Đánh hai chiều mua/bán trong kênh (chiến thuật dạy ở buổi riêng). Nếu là kênh của khung nhỏ (M15 ngược H1) thì biên độ quá bé, đứng ngoài |

- Mô hình RSI **bắt đầu và kết thúc trong vùng 40–60 thì bỏ qua**. Mô hình đẹp là mô hình xuất phát từ vùng cực trị (dưới khoảng 30 hoặc trên khoảng 70).
- Cách gọi tên: vòng cung úp xuống là "chuẩn bị cho sóng giảm", vòng cung ngửa lên là "chuẩn bị cho sóng tăng".

### 2.4 Bình nhiên liệu (Buổi 5)
- Khoảng cách RSI–MA và độ mở giữa 2 MA chính là "nhiên liệu" của xu hướng. **Vừa cắt và đang mở toác** nghĩa là còn nhiều nhiên liệu, xu hướng mới bắt đầu, không đánh ngược. **Đã đi xa và bắt đầu thu hẹp** nghĩa là còn ít nhiên liệu, có thể bắt đầu tìm tín hiệu theo chiều ngược.
- Muốn đảo chiều thì RSI phải kéo 2 MA lại gần nhau **từ từ** cho đến khi MA nhanh cắt MA chậm. Không có kiểu đảo hình chữ V nhọn. Một cú vọt lên mà không có tích luỹ thì sẽ bị xả ngay ("giảm gia tốc" trước rồi mới đảo).
- Thời gian tích luỹ dài hay ngắn tuỳ dòng tiền. Ví dụ: trong uptrend một sóng H4 mất 3–4 ngày, thị trường ảm đạm thì hơn 1 tuần.

### 2.5 Logic khung thời gian
- Các khung lân cận **đồng thuận tăng** thì mới tạo ra lực tăng, **đồng thuận giảm** thì mới tạo ra lực giảm. **Ngược pha** thì sinh xung đột.
- **Khung lớn quyết định xu hướng, khung nhỏ là chất xúc tác.**
- Hai khung chỉ chi phối hoặc xung đột với nhau khi **tỉ lệ gấp 3–6 lần**. Gấp từ 2 lần trở xuống thì coi như cùng một khung: H1/H2, H1/90m, 12H/D1, W1/2W, W1/6D, 10m/15m. Hai khung quá xa nhau thì không ảnh hưởng nhau (M15 với 3D, H4 với MN).
- Các cụm khung: 1m-5m-15m (scalping, không khuyến khích) · 5m-15m-H1 · 15m-H1-H4 · **H1-H4-D1 (cụm hay dùng nhất)** · D1-(3D/4D)-W1 · W1-(2W/3W)-MN.
- Đồng thuận được xét **trên trạng thái xu hướng RSI** (mục 2.1), không xét trên giá, và chỉ dùng nến đã đóng.
- **Bản chất sóng:** một khung muốn chạy sóng thì cần (a) **sự cho phép** của khung lớn liền kề, tức khung lớn đang có RSI cùng chiều, và (b) **sự ủng hộ** của khung nhỏ liền kề, cụ thể là khung nhỏ có **quán tính** cùng chiều. Ví dụ: sóng tăng D1 được bảo đảm bởi cấu trúc tăng H4 kèm quán tính tăng H4. Quán tính H1 chỉ kéo được H4, không kéo thẳng được D1.
- Trong một sóng tăng D1: gặp quán tính giảm ở M15 thì không đáng lo. Gặp **quán tính giảm ở H1 thì phải cẩn thận**, vì nó có thể khiến H4 điều chỉnh quá sâu, làm hỏng cấu trúc tăng H4 và kéo theo sóng D1 thất bại.
- Ví dụ trong bài: D1 có mô hình giảm trong khi 3D và W1 vẫn tăng, tức ngược pha, nên **không short**. Chờ RSI D1 cắt lên trở lại để đồng thuận với khung lớn rồi mua.
- **Dự báo sideway loại 2:** khi mô hình RSI ở khung nhỏ ngược với xu hướng của khung lớn liền kề thì **khả năng cao (khoảng 80%) sẽ có một vùng sideway trên chính khung nhỏ đó** (không phải trên khung lớn). Ngoại lệ là khi khung nhỏ đủ mạnh để kéo khung lớn đổi chiều. Cách kiểm tra: xem khung nhỏ hơn nữa có tạo quán tính không (ví dụ D1 tăng thì H4 phải có RSI ≥ 80). Nếu không có thì sóng yếu, sẽ thành sideway. Chỉ cần 1–2 sóng đầu là đủ để kết luận.
- Phải xác định đúng sideway thuộc khung nào, vì điều đó quyết định mục tiêu giá và loại sóng nằm bên trong vùng sideway.

---

## 3. Quy trình từng bước (ghép lại từ bài, chưa có điểm vào lệnh)
1. Chọn cụm khung, ví dụ H1-H4-D1. Xác định trạng thái RSI (tăng/giảm/đi ngang) và mức nhiên liệu ở từng khung, chỉ dùng nến đã đóng.
2. Ở khung giao dịch (giữa cụm), nếu thấy dấu hiệu sideway loại 1 thì đứng ngoài.
3. Kiểm tra khung lớn liền kề. Nếu ngược pha thì không đánh theo xu hướng, dự báo sideway trên khung giữa, rồi xem bước 4 để biết có ngoại lệ không.
4. Kiểm tra khung nhỏ liền kề có quán tính cùng chiều không. Có thì sóng có lực, giữ lệnh hoặc nhắm tới đỉnh/đáy cũ. Không có thì sóng yếu, khả năng sideway hoặc thất bại.
5. Nếu khung giao dịch có quán tính (≥ 80 / ≤ 20): chờ điều chỉnh (giai đoạn 3) rồi vào theo chiều quán tính khi vòng cung kết thúc. Mục tiêu tối thiểu là đỉnh/đáy cũ, mục tiêu cụ thể lấy theo S/R.
6. Trong khi giữ lệnh, theo dõi xem khung ngay dưới khung nhỏ (ví dụ H1 khi D1 đang tăng) có xuất hiện quán tính ngược chiều không. Có thì cảnh giác hoặc thoát lệnh.
7. Quản lý vốn được nhắc qua: futures SL ≤ 1% tài khoản; spot SL khoảng 7%; khoảng 10 lệnh/tháng, mỗi lệnh 5–10% (con số người giảng tự báo, chưa kiểm chứng).

---

## 4. Điểm mơ hồ khi code thành bot
- **Tham số:** chu kỳ RSI không được nêu (thường là 14). Chưa rõ MA9 là SMA hay EMA. WMA45 tính trên RSI. Cần đưa hết vào config.
- **"Dốc" và "mở rộng"** chưa có ngưỡng. Phải tự định nghĩa, ví dụ: độ dốc MA trong k nến > ε, khoảng cách (MA nhanh − MA chậm) tăng liên tiếp n nến, khoảng cách RSI−MA dùng làm "nhiên liệu" (chuẩn hoá theo độ lệch chuẩn).
- **"Vòng cung" và "mô hình đẹp"** mang tính cảm tính. Có thể thay bằng chuỗi: cắt xuống → cực trị → khoảng cách co lại → cắt lên. Mô hình đẹp thì yêu cầu điểm xuất phát < 30 hoặc > 70.
- **Lọc nhiễu khi cắt:** dùng đúng 3 điều kiện ở mục 2.1, có thể thêm điều kiện giữ ít nhất m nến.
- **Quán tính:** dùng nến đóng ≥ 80 / ≤ 20. Cần định nghĩa "đỉnh cũ": nên lấy giá cao nhất của sóng có RSI ≥ 80 cho tới lúc RSI cắt xuống. Thế nào là "điều chỉnh không sâu" thì chưa có số (Fibo 0.5 chỉ được nhắc trong phần sóng cơ bản). Con số "80%" là ước lượng của người giảng, cần backtest lại.
- **Sideway loại 1:** "đỉnh/đáy gần nhất" cần định nghĩa bằng swing của RSI. Ngoại lệ "giật xuống dưới 30 rồi bật lên ngay" cần ngưỡng số nến.
- **Ánh xạ khung cho XAUUSD:** M15-H1-H4 hoặc H1-H4-D1 khớp tỉ lệ 3–6. Riêng D1→W1 là 5 lần (vàng 5 phiên/tuần), vẫn hợp lệ. Muốn có 2D/3D/2W thì phải tự gộp nến (resample).
- **Điểm vào, SL, TP chưa được dạy** trong 2 buổi này (hẹn buổi sau). Bot chưa đủ thông tin để vào lệnh, mới dùng được như bộ lọc bias hoặc bộ lọc "có nên đứng ngoài không".
- Một số khái niệm còn mơ hồ: "khung nhỏ đủ mạnh kéo khung lớn", "cộng hưởng lực", "ngoại lệ lực bán bất thường". Khi gặp những trường hợp này thì chọn hướng bảo thủ: bỏ tín hiệu.
- Người giảng nói nhiều tình huống "học sau" (đa khung nâng cao, chiến thuật sideway, quán tính thất bại). Note này chưa đủ để xử lý trọn các trường hợp đó.
