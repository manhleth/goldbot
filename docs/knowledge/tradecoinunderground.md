# Kiến thức tham khảo: Trade Lab — tradecoinunderground.com

Nguồn: https://tradecoinunderground.com/trade-lab/phuong-phap (đọc ngày 2026-11-23).
Ghi chú tóm tắt, diễn giải lại bằng lời của mình, không chép nguyên văn. Trang tự ghi là môi trường giả lập trên dữ liệu
lịch sử, không phải lời khuyên đầu tư. **Không có số liệu backtest nào đọc được**: phần báo cáo tải bằng JavaScript,
nên không biết phương pháp nào thực sự có lãi. Mọi quy tắc dưới đây phải được backtest lại bằng bot này trước khi tin.

Trang chỉ mục có 23 chương trình (khoảng 591 bài): price-action, xau-playbook, smc-ict, opening-range, atr-trailing,
capital-risk, bollinger-bands, fibonacci, ichimoku, macd, rsi, dow-theory, nen, supply-demand, wyckoff, volume-profile,
vwap-anchored, elliott, time-series-momentum, trading-psychology, trading-process, ai-trading-workflow, zero-foundation.
Mỗi chương trình có các trang con `/quy-tac` (quy tắc), `/backtest`, `/kinh-nghiem`.

Ký hiệu dùng bên dưới:
- `[1]` = nến vừa đóng, `[2]` = nến trước nó.
- Giá tính theo USD/oz.
- ATR = ATR14 nếu không ghi khác.

---

## 1. Sổ tay Vàng MT5 — 13 phương pháp XAUUSD (`/xau-playbook/quy-tac`)

Quy ước chung:
- Điều kiện chỉ xét trên nến đã đóng.
- Lot làm tròn xuống theo bước 0,01.
- Giờ tính theo UTC nếu không ghi khác.
- Phần lớn các phương pháp bỏ thứ Sáu.
- Trang tự backtest 2018–2026 trên nến M5 bid/ask, có tính spread, phí, trượt giá; chưa tính swap.

| Mã | Khung | Vào lệnh | Tóm tắt |
|---|---|---|---|
| XAU-01 | H1 | market | Hồi về EMA21 trong xu hướng EMA21 > 55 > 200 |
| XAU-02 | H4 | market | MACD cắt, lọc chiều bằng EMA200 |
| XAU-03 | H1 | market | Râu chạm ngoài Bollinger, đóng trở vào, RSI cực đoan |
| XAU-04 | M15 | market | Pivot ngày + Stochastic 5,3,3 |
| XAU-05 | M15 | stop | Phá hộp phiên Á bằng lệnh chờ hai phía |
| XAU-06 | M15 | market | Phá hộp London khi nến đóng cửa vượt hộp |
| XAU-07 | M15 | stop | Lệnh stop theo màu nến (mục tiêu rất nhỏ, khó kiểm chứng) |
| XAU-08 | M5 | limit | Quét biên mở cửa New York + FVG |
| XAU-09 | M5 | limit | Phiên London quét biên Á + FVG |
| XAU-10 | M15+D1 | market | Hồi EMA9 thuận chiều D1 |
| XAU-11 | M15+D1 | market | Stochastic thuận chiều D1 |
| XAU-12 | D1 | market | Kênh Donchian 55/20 (đi theo xu hướng) |
| XAU-13 | M15+D1 | limit | Phá cấu trúc + hồi Fibonacci + FVG |

Chi tiết:

**XAU-01 — hồi EMA21 (H1).**
- Chiều: BUY khi EMA21 > EMA55 > EMA200.
- Setup: nến [2] đóng dưới EMA21, nến [1] đóng lại trên EMA21.
- Vào: market đầu nến kế.
- SL / TP: SL 1,5 ATR, TP 3 ATR, tính từ giá khớp thực.
- Biến thể: trailing SL tại giá − 1 ATR sau mỗi nến H1, chỉ dời theo hướng có lợi.
- Giờ: mở lệnh 07:00–21:00 UTC, bỏ thứ Sáu.

**XAU-02 — MACD theo EMA200 (H4).**
- Setup BUY: close và EMA50 nằm trên EMA200; MACD main cắt lên signal (ở [2] main < signal, ở [1] main > signal).
- SL / TP: SL 2 ATR, TP 4 ATR.
- Biến thể: trailing 1,5 ATR.
- Giờ: 07:00–20:00 UTC, bỏ thứ Sáu.

**XAU-03 — Bollinger quay về (H1).**
- Setup BUY: low[1] chạm hoặc xuyên dải dưới, close[1] đóng trên dải dưới, RSI < 35. SELL đối xứng với RSI > 65.
- SL: 3,00.
- TP: dải giữa. Nếu dải giữa không nằm phía có lãi thì TP 5,00.
- Quản lý: lãi 2,00 thì dời SL về giá vào + 0,10.
- Giờ: 08:00–20:00 UTC.

**XAU-04 — pivot ngày + Stochastic 5,3,3 (M15).**
- Pivot lấy từ nến D1 (UTC) gần nhất.
- Setup BUY: K cắt lên D khi K < 25; close > EMA21; giá cách S1 hoặc S2 không quá 1,50.
- SL / TP: SL 1,50. TP1 1,00 (chốt 50%, dời SL về giá vào + 0,10), TP2 2,00.

**XAU-05 — phá hộp phiên Á (lệnh chờ).**
- Hộp: 00:00–07:00 UTC, rộng tối thiểu 1,50.
- Vào: từ 07:00 UTC đặt Buy Stop tại đỉnh hộp + 0,10 và Sell Stop tại đáy hộp − 0,10. Hủy lệnh chờ lúc 12:00 UTC.
- SL: ở phía bên kia hộp, thêm 0,50.
- TP: 2 lần khoảng SL. Không dời SL.

**XAU-06 — phá hộp London (đóng nến).**
- Hộp: 7 nến M15 từ 09:15 đến 10:45 UTC.
- Vào: trong 11:00–16:30 UTC, close M15 vượt hộp ± 0,05 thì vào market.
- SL = TP, cùng khoảng (theo công thức từ spread/stops level, tối thiểu 30 pip).
- Biến thể: trailing 15 pip.
- Đóng hết lệnh lúc 17:00 UTC.

**XAU-07 — stop theo màu nến (M15).**
- Vào: nến tăng thì Buy Stop tại high, nến giảm thì Sell Stop tại low.
- SL / TP: đều 0,20.
- Bản thân trang cũng ghi rằng mục tiêu nhỏ hơn biên độ một nến M5, nên không xác định được SL hay TP chạm trước. **Không dùng.**

**XAU-08 — quét biên mở cửa New York + FVG (M5).**
- Hộp: 6 nến M5 từ 09:30 đến 09:55 giờ New York.
- Setup: trong 10:00–12:00 New York, giá quét biên hộp rồi tạo FVG ngược chiều cú quét (rộng ≥ 0,06).
- Vào: limit ở mép FVG gần giá (BUY tại low của nến C).
- SL: sau nến A ± 0,09. TP: 2R.
- Quản lý: lãi 1,3R thì dời SL về giá khớp.
- Mỗi ngày tối đa một lần. Bỏ ngày nếu giá phá cả hai biên hộp trước khi vào.

**XAU-09 — phiên London quét biên Á + FVG (M5).**
- Hộp Á: 20:00–02:00 giờ New York.
- Setup: trong 02:00–05:00 New York, giá quét đỉnh hoặc đáy Á rồi tạo FVG ngược chiều như XAU-08.
- Vào: limit tại mép FVG.
- SL: sau cực trị London ± 0,09. TP: 2R.
- Quản lý: lãi 1,5R thì dời SL về giá vào.
- Mỗi ngày một lần.

**XAU-10 — hồi EMA9 thuận chiều D1 (M15).**
- Lọc D1: close > EMA50 thì chỉ BUY.
- Setup M15: EMA9 > EMA21; nến chạm EMA9 rồi đóng trên EMA9 và là nến tăng.
- SL: lớn nhất trong (2 ATR M15; 0,80). TP: 3 ATR.
- Giới hạn: spread ≤ 0,40; giờ 07:00–20:00 UTC.

**XAU-11 — Stochastic thuận chiều D1 (M15).**
- Lọc D1 như XAU-10.
- Setup BUY: ở [2] K < D và K < 20; ở [1] K cắt lên D và K < 30.
- SL / TP như XAU-10.

**XAU-12 — Donchian 55/20 (D1, kiểu Turtle).**
- Vào: close vượt đỉnh 55 ngày thì BUY, thủng đáy 55 ngày thì SELL.
- Thoát: close phá kênh 20 ngày ngược chiều, hoặc chạm SL 2 ATR D1. Không có TP cố định.
- Có tín hiệu ngược chiều thì đảo lệnh.

**XAU-13 — phá cấu trúc + Fibonacci + FVG (M15).**
- Lọc D1: close > EMA50.
- Setup:
  - Nến M15 đóng trên swing high đã xác nhận (fractal 3 trái / 3 phải).
  - Chân sóng (từ swing low tới nến phá) ≥ 1 ATR.
  - Có FVG trong 8 nến gần đó, nằm chồng lên vùng hồi 61,8–78,6%.
- Vào: Buy Limit tại giữa vùng hồi.
- SL: dưới chân sóng − 0,25 ATR, chỉ hợp lệ nếu SL trong khoảng 0,5–6 ATR. TP: 2R.
- Hủy lệnh chờ:
  - sau 12 nến M15, hoặc
  - khi có phá cấu trúc ngược chiều.
- Thoát lệnh đã khớp:
  - khi có phá cấu trúc ngược chiều, hoặc
  - sau 96 nến M15.
- Chỉ tìm setup mới trong 07:00–16:00 UTC.

---

## 2. SMC / ICT (`/smc-ict/quy-tac`) — 14 bộ quy tắc

Setup tìm trên M15, khớp lệnh trên M5. Mọi bộ đều bắt đầu bằng một cú **quét pivot 3/3**: pivot đã xác nhận 3 nến trái /
3 nến phải, bị râu nến xuyên qua.

| Mã | Ý chính |
|---|---|
| smc-fvg-close | Quét, rồi FVG cùng hướng trong 10 nến → vào market |
| smc-fvg-limit | Như trên, limit tại 50% FVG, hết hạn sau 20 nến |
| smc-sweep | Râu xuyên pivot, close đóng trở vào → vào market |
| smc-mss | Quét, rồi close phá pivot đối diện trong 10 nến, thân ≥ 0,5 ATR |
| smc-ob | Quét + MSS → limit tại giá open của nến ngược màu cuối cùng trước MSS |
| smc-ote | Quét + MSS → limit tại mức hồi 70,5% của sóng |
| smc-discount | Chỉ BUY khi FVG nằm dưới mức cân bằng (giữa range hai pivot) |
| smc-killzone | FVG phải hình thành trong 02–05 hoặc 07–10 giờ New York |
| smc-silver | FVG trong 03–04, 10–11 hoặc 14–15 giờ New York (Silver Bullet) |
| smc-2022 | Quét → MSS (thân ≥ 0,5 ATR) → FVG trong 10 nến; limit tại giữa FVG |
| smc-breaker | Breaker block, limit tại giữa thân nến |
| smc-unicorn | Breaker chồng FVG; limit tại 50% vùng giao nhau |
| smc-mitigation | Mitigation block (cấu trúc 3 pivot) |
| smc-judas | Range 00–02 giờ New York + giá mở cửa nửa đêm; bias theo nến ngày trước; quét trong 02–05 giờ New York |

Trang chính không ghi SL/TP. Chi tiết nằm ở `/smc-ict/quy-tac/<id>` (chưa đọc).

---

## 3. Price Action (`/price-action`) — đọc tín hiệu trên D1, khớp lệnh trên M5, 17 bộ quy tắc

Định nghĩa chính:
- **Pin bar:** râu từ chối ≥ 2/3 biên độ nến, thân ≤ 1/3.
- **Lọc xu hướng:** EMA8 so với EMA21 trên D1.
- **Range:** 20 phiên, rộng 3–12 ATR, và |EMA8 − EMA21| ≤ 0,5 ATR.

Các nhóm quy tắc:
- **Pin bar (5 bộ):** vào bằng market, lệnh stop (vượt high + 0,05 ATR, hết hạn 72 giờ), hoặc limit ở 50% nến; pin ở biên range; hai pin liên tiếp.
- **Inside bar (3 bộ):** lệnh stop vượt nến mẹ; inside rồi nến sau đóng cửa vượt nến mẹ; hai inside lồng nhau (coil).
- **Fakey / phá giả (3 bộ):** râu xuyên biên nến mẹ hoặc range 20 phiên rồi đóng trở vào.
- **Breakout (5 bộ):**
  - Close vượt đỉnh/đáy 20 phiên theo EMA.
  - Retest bằng limit tại biên đã phá.
  - Sự kiện phá (thân ≥ 1 ATR), sau đó có pin retest biên.
  - Pin chạm giữa sóng phá.
- **Hồi EMA21 (1 bộ):** chạm EMA21, đóng trên, nến tăng.

Bài giảng:
- Thoát lệnh theo S/R, MA hoặc ATR. Kế hoạch 2R.
- Trailing dời SL từng nấc 1R.
- Setup tìm ở D1, vào ở H1 để SL ngắn hơn, rồi tính lại lot để rủi ro tiền không đổi.
- Điểm vào cần ít nhất 3 yếu tố hợp lưu độc lập.
- Chỉ đánh setup rõ ràng tại mức giá quan trọng.

---

## 4. Opening Range (`/opening-range/quy-tac`)

- Vùng OR = 3 nến M5 từ 09:30 đến 09:45 giờ New York.
- **orb-close:** nến M5 đầu tiên đóng cửa vượt OR trước 11:00 New York → vào market ở nến kế.
- **orb-retest:** sau cú phá, đặt limit tại biên OR vừa phá; hết hạn sau 10 nến hoặc lúc 11:00 New York.
- Bài giảng: bỏ qua ngày có OR quá rộng; tách riêng phá thất bại (giá quay vào OR) thành lệnh đảo chiều.

## 5. ATR / trailing stop (`/atr-trailing`)

- **Supertrend** (ATR10 × 3) trên M15: đổi hướng thì vào market.
- **EMA20/50** trên M15: dùng để so sánh các cách đặt stop, dời BE và trailing.
- Nguyên tắc:
  - Stop ban đầu tính bằng ATR, quy đổi ra lot theo tick value.
  - Trailing chỉ siết một chiều, có xử lý gap.
  - Kết hợp chốt một phần và dời về hòa vốn.
  - Khi thêm vị thế phải tính tổng rủi ro.

## 6. Quản lý vốn (`/capital-risk`)

- Tách vốn giao dịch khỏi tiền sinh hoạt, đặt sẵn mức lỗ buộc phải dừng.
- Drawdown tính từ đỉnh equity. Cần tính trước tỉ lệ phải lãi lại để phục hồi.
- SL đặt tại điểm mà ý tưởng sai, cộng buffer, tính cả rủi ro gap.
- Lot tính từ khoảng SL → tick → tiền, làm tròn xuống, có tính phí.
- So sánh fixed size, fixed fraction và Kelly. Không dùng thẳng Kelly tính từ mẫu nhỏ.
- Giới hạn tổng rủi ro đang mở và tương quan giữa các lệnh. Giới hạn lỗ theo phiên và theo tuần.
- Đánh giá hệ thống bằng thống kê R: mean R, payoff, và stress test chi phí.

## 7. Bollinger Bands (`/bollinger-bands`)

- Chỉ số: %b, Band Width, squeeze.
- Ba chế độ:
  - bật lại khi thị trường đi ngang (limit ở dải, có lọc S/R),
  - phá squeeze (lệnh stop, phân biệt phá thật và phá giả),
  - nến nằm hẳn ngoài dải (xu hướng mạnh hay kiệt sức, chờ price action xác nhận).

---

## 8. Đối chiếu với bot (D:\gold-bot)

Bot đã có:
- **SMC:** FVG, order block, MSS/BOS, quét thanh khoản, killzone, Judas (`sweep_mss_fvg`, `judas_swing`).
- **Breakout:** range H1 (`range_breakout`).
- **Quản lý lệnh:** dời BE theo R, chốt một phần, trailing theo swing, sizing rủi ro tiền cố định.

Còn thiếu để thử các phương pháp trên:
1. **Lệnh limit / stop chờ khớp** (XAU-05, 08, 09, 13, smc-fvg-limit, smc-ote, orb-retest). Hiện bot chỉ vào market.
   Cần thêm lệnh chờ có hạn hủy vào simulator và live.
2. **SL / TP theo ATR cố định** (XAU-01, 02, 10, 11). Hiện SL theo cấu trúc, TP theo R.
3. **Chỉ báo:** MACD, Bollinger, Stochastic, Donchian, Supertrend. Hiện chỉ có EMA, ATR, RSI, ADX.
4. **Hộp theo giờ** (hộp Á 00–07 UTC, hộp London, hộp mở cửa New York). Đã có `sessions.windows`, dùng lại được.
5. **Thoát theo thời gian** (XAU-13: 96 nến) và **đảo lệnh** (XAU-12).

Ưu tiên đề xuất (đơn giản, ít tham số, kiểm chứng được):
- **XAU-12 Donchian 55/20 D1:** đi theo xu hướng thuần, cực ít tham số. Đặc điểm của kiểu này là tỉ lệ thắng thấp nhưng lệnh thắng rất lớn.
- **XAU-05 / XAU-06:** phá hộp theo giờ, quy tắc rõ ràng, dễ backtest.
- **XAU-13 và smc-2022:** gần nhất với SMC đã có; chỉ cần thêm lệnh limit.

---

## 9. Trang tín hiệu (`/signals`, đọc 2026-11-23)

- **Nội dung:** danh sách tín hiệu, phần lớn là XAUUSD (một ít USOIL, XAGUSD, BTCUSD).
- **Nguồn tín hiệu:** từ các kênh "Gold Sclap Signal 2", "Bot Bắn Tỉa UG", và nhóm "Private" (trả phí, ẩn entry/SL/TP).
- **Quy tắc tạo tín hiệu:** không công bố. Không có khung thời gian, điều kiện vào, hay cách đặt SL/TP → **không tái tạo được bằng quy tắc tất định.**
- **Mẫu hình quan sát được** (suy ra từ các tín hiệu đang hiển thị, không phải quy tắc của trang):
  - **Gold Scalp:**
    - Vùng entry rộng 10$, giá vào lấy ở mép xa.
    - SL cách mép gần 10$, tức cách giá vào khoảng 20$.
    - TP1/2/3 = giá vào ± 20 / 40 / 60$, tức 1R / 2R / 3R.
  - **Bot Bắn Tỉa:**
    - Vùng entry rộng khoảng 3$.
    - SL cách khoảng 13$.
    - TP1 chỉ +5$, tức khoảng **0,4R**: tỉ lệ thắng cao nhưng mỗi lệnh thua mất gấp khoảng 2,6 lần lệnh thắng.
- **Cách trang chấm kết quả:**
  - Entry phải khớp trong 24 giờ.
  - TP/SL theo dõi tối đa 72 giờ.
  - Thống kê tính từ 16/07/2026.
  - "Thắng" = chạm TP1 trở lên. Định nghĩa này **làm winrate cao hơn thực tế**, vì TP1 thường gần hơn SL.
- **Số liệu công bố:**
  - Winrate 43–44% toàn trang, nhưng 59,4% riêng XAUUSD (554 thắng / 379 thua) — hai số mâu thuẫn với nhau.
  - Không có PF, expectancy, R hay drawdown.
  - Nhãn pip không nhất quán: có lệnh ghi TP 2000 pip trong khi các lệnh khác 200 pip.
- **Kết quả các tín hiệu công khai đọc được (16–21/11):**
  - Có những ngày toàn thua, ví dụ ngày 20/11: 0 thắng / 8 thua.
  - Lệnh thắng phần lớn chỉ chạm TP1.
- **Xung đột lợi ích:** trang là đối tác giới thiệu (IB) của Exness, nhận hoa hồng theo khối lượng giao dịch của người đăng ký qua họ.
- **Có thể dùng làm:** nguồn ý tưởng về vùng giá. **Không nên dùng làm:** chiến lược cho bot.
