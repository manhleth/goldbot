# Phương pháp ONE — Phá cấu trúc theo xu hướng, gồng theo đỉnh/đáy

ONE là phương pháp duy nhất bot dùng để vào lệnh. Nó được tổng hợp từ toàn bộ kiến thức đã nạp:
- XAU Playbook: lọc xu hướng EMA50/EMA200.
- Mẫu hình trendline từ ảnh của bạn: cờ, tam giác, kênh, neckline.
- Cách vẽ và phân tích của MJ Capital (chỉ dùng để học cách vẽ, không lấy nhận định của channel làm bộ lọc):
  trendline là một vùng nối râu nến; cờ xuất hiện sau một cú chạy mạnh; mục tiêu theo measured move.

Mọi quy tắc đều cố định và lặp lại được. Backtest và bot live chạy **cùng một đoạn code** (`playbook/`).

## 1. Điều kiện vào lệnh (đủ cả 5 thì vào)

| # | Điều kiện | Chi tiết |
|---|---|---|
| 1 | **Xu hướng H4** | Close và EMA50 nằm trên EMA200 → chỉ BUY. Nằm dưới → chỉ SELL. Không rõ ràng → không trade |
| 2 | **Có mẫu hình** trên khung mẫu hình (swing: H2 + H4; scalp: H1 — chỉ giao dịch khung H1 trở lên) | Swing quét cạnh theo 2 cách rồi gộp: đường nhiều điểm chạm nhất và đường có điểm neo mới nhất; râu nến được xuyên qua cạnh tới 1 ATR. Hai cạnh nối râu đỉnh/đáy swing (fractal 3 nến trái/phải). Mỗi cạnh có ≥ 2 điểm chạm. Trendline là **vùng ± 0,3 ATR**: râu chạm trong vùng tính là chạm, râu xuyên nhẹ không làm hỏng đường. Mẫu hình kéo dài ≥ 12 nến, cao 1,5–12 ATR |
| 3 | **Nến đóng cửa phá cạnh** theo chiều xu hướng | Đóng cửa vượt cạnh quá 0,2 ATR. Chỉ nến **đóng cửa** mới tính là phá, râu thì không |
| 4 | **Loại mẫu hình đang có thành tích tốt** (lớp học kinh nghiệm) | Bot trade nháp mọi tín hiệu từ trước tới nay. Loại mẫu hình theo khung (vd `flag@H4`) phải có ≥ 5 kết quả nháp đã đóng, và trung bình 20 kết quả gần nhất > 0R |
| 5 | **Còn chỗ chạy tới vùng hỗ trợ/kháng cự cứng** | Vùng = cụm ≥ 2 đỉnh/đáy swing trong 0,5 ATR, hết hiệu lực khi lần chạm cuối quá cũ. Swing: vùng W1 (≤ 26 tuần) + D1 (≤ 120 ngày); scalp: vùng D1 (≤ 120 ngày) + H4 (≤ 180 nến). Bỏ lệnh nếu vùng cản phía trước gần hơn 0,5 × khoảng SL (giá vào nằm trong vùng cũng bỏ) |

**Các loại mẫu hình:**
- **Cờ** (`flag`): ngay trước mẫu hình có một nhịp chạy mạnh (cán cờ ≥ 4 ATR và ≥ chiều cao mẫu hình), rồi giá phá cùng chiều cán cờ.
- **Phá kênh** (`channel_break`): kênh có hai cạnh gần song song.
- **Phá tam giác** (`triangle_break`): hai cạnh hội tụ.
- **Thủng neckline** (`neckline_break`): một đường có ≥ 3 điểm chạm bị phá.
- **Không dùng:** bật cạnh kênh, mẫu hình loe, mẫu hình trên D1 — kết quả nháp đều âm.

## 2. Đặt lệnh

- **Vào lệnh:** lệnh market ngay sau khi nến phá đóng cửa.
- **SL:** lùi vào trong cạnh vừa bị phá 1 ATR. Giá quay lại sâu vào mẫu hình nghĩa là cú phá thất bại.
- **TP:** không đặt TP cố định. Mục tiêu measured move (chiều cao mẫu hình hoặc chiều dài cán cờ) chỉ vẽ trên chart để tham khảo.
- **Khối lượng:** tính để nếu chạm SL thì mất đúng **% rủi ro trên phần vốn của bot** (swing 10%, scalp 5%). Phần vốn = 50% equity lúc bot chạy lần đầu + lãi/lỗ đã chốt của chính bot. Lot làm tròn xuống.

## 3. Quản lý lệnh: gồng theo đỉnh/đáy

- Mỗi khi khung mẫu hình (H4, H2 hoặc H1) xác nhận một đáy swing mới **sau lúc vào lệnh** (với lệnh BUY), SL dời lên dưới đáy đó 0,2 ATR. SL chỉ siết lại, không bao giờ nới ra.
- Lệnh đóng khi giá phá đáy/đỉnh gần nhất, tức là khi cấu trúc xu hướng gãy.
- **Bot scalp:** giữ lệnh trong tuần, đóng hết lúc **15:30 New York thứ Sáu** (sàn đóng vàng sớm, tránh gap cuối tuần); không vào lệnh mới từ 14:30 thứ Sáu tới phiên tuần mới.

## 4. Hai bot chạy song song (cùng tài khoản demo, magic khác nhau)

| | Bot swing (`swing`) | Bot trong ngày (`day`) |
|---|---|---|
| Khung mẫu hình | H2 + H4 | H1 |
| Gồng theo đỉnh/đáy | Khung của chính mẫu hình (H2 hoặc H4) | H1 |
| Giữ lệnh | Nhiều ngày (trung vị ~4,5 ngày) | Trong tuần, đóng 15:30 NY thứ Sáu |
| Phần vốn | 1/2 tài khoản | 1/2 tài khoản |
| Giới hạn | Tối đa 3 lệnh mở cùng lúc. Có tín hiệu đạt chuẩn là vào thêm, kể cả cùng chiều (nhồi lệnh dương) | Tối đa 10 lệnh mỗi ngày giao dịch, tối đa 3 lệnh cùng lúc |
| Rủi ro | 10% phần vốn/lệnh (= 5% tài khoản) | 5% phần vốn/lệnh (= 2,5% tài khoản) |
| Chặn rủi ro / lot | Vốn bot ≥ 500$: tối đa 10%; ≥ 5.000$: tối đa 5%; tối đa 2 lot/lệnh | như swing |
| Magic MT5 / journal | 20261124 / `journal/live_swing.db` | 20261125 / `journal/live_day.db` |

## 5. Lý do và chart của từng lệnh

Mỗi lệnh (backtest và live) đều lưu:
- **Lý do:** loại mẫu hình và khung; hình dạng, số nến, chiều cao, số điểm chạm từng cạnh; giá trị cạnh bị phá và mục tiêu measured move.
- **Chart SVG:**
  - Nến của khung mẫu hình, các cạnh trendline (chấm trắng là điểm neo).
  - Điểm vào (tam giác xanh), SL ban đầu (nét đứt đỏ), mục tiêu tham khảo (nét chấm cam), điểm thoát (vòng vàng) và kết quả theo R.
  - Xem trên giao diện: tab **Lịch sử lệnh** → cột **Chart** → **Xem**.
- **Lý do không vào lệnh** (tab **Tín hiệu**):

| Mã | Nghĩa |
|---|---|
| `learning_insufficient` | Loại mẫu hình chưa đủ kết quả nháp |
| `learning_negative` | Loại mẫu hình đang thua gần đây |
| `max_open_trades` | Đã đủ số lệnh mở cùng lúc |
| `max_trades_per_day` | Đã đủ số lệnh trong ngày |
| `stale_signal` | Tín hiệu cũ |
| `stop_file` | Đang bật kill switch |

### Ví dụ (backtest bot swing 2025–2026)

**Phá kênh H4 — BUY, +3,80R**

![Phá kênh H4](img/channel_break-H4_win.svg)

**Cờ H4 — BUY, +1,99R**

![Cờ H4](img/flag-H4_win.svg)

**Thủng neckline H4 — BUY, +2,10R**

![Neckline H4](img/neckline_break-H4_win.svg)

**Phá tam giác H4 — SELL, +1,57R**

![Tam giác H4](img/triangle_break-H4_win.svg)

**Lệnh thua — cờ H4 BUY, −1R:** giá phá lên rồi quay lại sâu vào trong mẫu hình và chạm SL.

![Lệnh thua](img/flag-H4_loss.svg)

## 6. Kết quả backtest (vốn 1.000$, khớp lệnh trên nến M5/M15 bid/ask, có spread và trượt giá)

| | Lệnh | Tỉ lệ thắng | R/lệnh | PF | Max DD |
|---|---|---|---|---|---|
| ONE H4, 12 năm (2015–2026), tối đa 2 lệnh | 311 | 35% | +0,50 | 1,93 | 26,8R |
| Bot swing, 2025 → 11/2026, 5%/lệnh lãi kép | 76 | 53% | +1,28 | 4,03 | 26% |
| Bot trong ngày M15+H1, 2025 → 11/2026, 5%/lệnh (cũ) | 721 | 41% | +0,25 | 1,52 | 77% |
| Bot scalp H1, 2026 → 11/2026, 5% phần vốn/lệnh | 149 | 48% | +0,21 | 1,42 | 32% |

**Cảnh báo:**
- 5% equity mỗi lệnh là mức rủi ro rất cao. Trên 12 năm, drawdown 26,8R tương đương khoảng −134% ở mức 5%, tức cháy tài khoản. Phù hợp để thử trên demo, **không phù hợp với tiền thật**.
- Các cấu hình đã được chọn trên chính dữ liệu quá khứ. Chạy demo là bước xác nhận bắt buộc.

## 7. Trường hợp đã biết: kênh giảm D1 năm 2022 (điểm yếu, chưa giải quyết)

- Vàng giảm trong một kênh D1 rõ ràng từ 03/2022 (≈ 2070) tới 11/2022 (≈ 1615), các nhịp hồi chạm cạnh trên khoảng
  04, 06, 08, 10/2022, rồi phá lên khỏi kênh 11/2022.
- Bot swing (phá mẫu hình H2/H4) lỗ cả hai chiều trong năm này: BUY 15 lệnh −8.6R, SELL 10 lệnh −8.3R. Lý do: SELL vào lúc
  giá phá xuống thường là đáy kênh rồi bị nhịp hồi quét SL; BUY theo nhịp hồi ngược kênh.
- Bot không tự vẽ được kênh này: cách chọn cạnh hiện tại nối 2 đỉnh/đáy fractal gần nhau, không ra kênh 8 tháng.
- Đã thử (backtest từng năm 2020–2026, không bật):
  - Kênh D1 hồi quy 120/60 ngày làm bộ lọc (chỉ đánh cùng chiều kênh, ở nửa "đắt" của kênh): nhận ra kênh muộn
    (từ 24/05 hoặc 26/07/2022), 2022 vẫn lỗ, và chặn mất các cú phá đỉnh kênh tăng — tổng +165R → +36…+90R.
  - Vĩ mô W1/D1 dài hạn có xác nhận (playbook/macro.py): 2022 −17R → −9R, 2021 −20R → +5R, tổng +219R.
- Hướng cần làm: kiểu vào lệnh riêng cho kênh D1 — SELL khi giá hồi chạm cạnh trên kênh giảm (BUY khi chạm cạnh dưới
  kênh tăng), TP cạnh đối diện, SL ngoài cạnh; và cách vẽ kênh dài hạn sát với cách người vẽ tay.

