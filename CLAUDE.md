# CLAUDE.md — Bot phân tích đa khung & vào lệnh DEMO (XAUUSD)

## 1. Mục tiêu và ràng buộc

**Mục tiêu:** xây bot chạy local, tự phân tích XAUUSD đa khung thời gian, tự vào lệnh trên **tài khoản DEMO**, ghi nhật ký và tính thống kê (tỉ lệ thắng, expectancy, profit factor, drawdown) để kiểm chứng phương pháp.

**Ràng buộc bắt buộc (không được vi phạm):**
- Chỉ chạy trên tài khoản demo. Khi khởi động, bot PHẢI kiểm tra `account.trade_mode == DEMO`; nếu không phải thì thoát ngay, không đặt lệnh.
- Mọi quy tắc vào/ra lệnh là **code xác định (deterministic)**, không dùng LLM để quyết định vào lệnh. LLM chỉ dùng (tùy chọn) để đọc nhật ký và đề xuất chỉnh tham số sau khi có đủ mẫu.
- Không look-ahead: tại thời điểm t chỉ được dùng nến đã đóng trước t.
- Mọi tham số nằm trong `config.yaml`, không hard-code trong logic.
- Mỗi tín hiệu và mỗi lệnh đều được ghi log kèm lý do (setup nào, điều kiện nào thỏa).

**Lưu ý trung thực về kỳ vọng:** các tỉ lệ xác suất kiểu "60-65%" trong các phân tích chat trước chỉ là ước lượng theo cảm nhận, không phải thống kê. Chỉ tin vào số liệu bot đo được, và chỉ khi mẫu đủ lớn (xem mục 8).

---

## 2. Kiến trúc

```
data/            # nạp dữ liệu nến (MT5 hoặc CSV), cache
structure/       # swing, xu hướng, vùng S/R, FVG, thanh khoản, trendline
signals/         # mỗi phương pháp = 1 module trả về Signal hoặc None
mtf/             # gộp bias đa khung (top-down)
risk/            # tính SL, TP, khối lượng, giới hạn rủi ro
execution/       # gửi lệnh demo, quản lý lệnh đang mở
journal/         # SQLite: signals, trades, equity
stats/           # báo cáo thống kê, breakdown theo setup
backtest/        # chạy cùng logic trên dữ liệu lịch sử
config.yaml
main.py          # vòng lặp live-demo
```

**Luồng mỗi vòng lặp (khi có nến mới đóng ở khung vào lệnh):**
1. Nạp nến đã đóng cho D1, H4, H1, M15.
2. `structure/` tính swing, xu hướng, vùng, FVG cho từng khung.
3. `mtf/` ra **bias** (BUY / SELL / NEUTRAL) từ khung lớn.
4. `signals/` kiểm tra các setup ở H1/M15, chỉ chấp nhận setup **cùng chiều bias**.
5. `risk/` tính SL, TP, size; kiểm tra các giới hạn.
6. `execution/` đặt lệnh demo nếu qua hết bộ lọc; ghi journal.
7. Quản lý lệnh đang mở (dời SL, chốt một phần) theo quy tắc cố định.

---

## 3. Phân cấp khung thời gian (top-down)

| Khung | Vai trò | Dùng cho |
|---|---|---|
| **D1** | Bối cảnh lớn | Xu hướng chính, vùng S/R lớn, trendline lớn |
| **H4** | Cấu trúc | Xác nhận xu hướng, vùng FVG/OB lớn, mốc invalidation |
| **H1** | Setup | Tìm vùng quan tâm, retest, phá trendline |
| **M15** | Trigger | Nến xác nhận vào lệnh, SL chặt |

**Quy tắc đồng thuận:**
- `bias_D1` và `bias_H4` phải **không đối nghịch** với chiều lệnh. Nếu D1 và H4 ngược nhau → `NEUTRAL`, không vào lệnh.
- Chỉ vào lệnh theo chiều bias. Không đánh ngược xu hướng khung lớn.
- Vào lệnh khi H1 có setup hợp lệ VÀ M15 có nến trigger.

---

## 4. Định nghĩa khách quan cho từng phương pháp

> Mọi thứ phải định lượng được. Không dùng khái niệm cảm tính như "trông có vẻ mạnh".

### 4.1 Swing và cấu trúc (nền tảng của mọi thứ)
- **Swing high/low (fractal N nến):** nến i là swing high nếu `high[i]` lớn nhất trong `[i-N, i+N]`. Mặc định `N = 3` cho M15/H1, `N = 5` cho H4/D1. Swing chỉ được xác nhận sau N nến, tránh repaint.
- **Xu hướng tăng:** chuỗi HH + HL gần nhất. **Giảm:** LH + LL. Còn lại: đi ngang.
- **BOS (phá cấu trúc):** nến đóng vượt swing gần nhất cùng chiều xu hướng.
- **CHoCH (đổi tính chất):** nến đóng phá swing ngược chiều xu hướng hiện tại (HL trong uptrend hoặc LH trong downtrend).

### 4.2 Xu hướng / bias (trend following)
Điểm bias mỗi khung = tổng các điều kiện (+1 tăng, -1 giảm, 0 trung tính):
- Cấu trúc swing (HH/HL hoặc LH/LL).
- Giá so với EMA(50) và EMA(200).
- Độ dốc EMA(50) (so với 10 nến trước).
- ADX(14) > 20 mới coi là có xu hướng; dưới ngưỡng → trung tính.

`bias_khung = BUY nếu điểm >= +2`, `SELL nếu <= -2`, ngược lại `NEUTRAL`.

### 4.3 Vùng hỗ trợ / kháng cự (price action)
- Gom các swing có giá nằm trong khoảng `0.5 * ATR(14)` thành **một vùng**; vùng có >= 2 lần chạm là vùng hợp lệ.
- Độ dày vùng = từ min đến max của các swing trong cụm.
- Vùng bị coi là "vỡ" khi có nến đóng xuyên hết vùng. Vùng vỡ có thể đổi vai (kháng cự ↔ hỗ trợ) để dùng cho retest.

### 4.4 FVG (Fair Value Gap)
- **Bullish FVG:** với 3 nến liên tiếp (c1, c2, c3): `low[c3] > high[c1]`. Vùng = `[high[c1], low[c3]]`.
- **Bearish FVG:** `high[c3] < low[c1]`. Vùng = `[high[c3], low[c1]]`.
- Chỉ nhận FVG khi kích thước >= `0.3 * ATR(14)` (loại gap quá nhỏ) và nến c2 là nến thân lớn (body >= 1.0 * ATR).
- **Trạng thái:** `fresh` (chưa chạm) → `tested` (đã chạm một phần) → `filled` (đóng xuyên hết). Chỉ dùng FVG `fresh` hoặc `tested` lần đầu; FVG đã `filled` bị loại.
- **Setup vào lệnh:** giá hồi vào FVG ngược chiều xung lực (sell tại bearish FVG trong downtrend) và có nến trigger M15 (xem 5).
- **Confluence cộng điểm:** FVG trùng vùng S/R đổi vai, hoặc FVG H1 nằm trong FVG H4.

### 4.5 Order Block (bản đơn giản)
- Bearish OB: nến tăng cuối cùng ngay trước một đợt giảm tạo BOS. Bullish OB: nến giảm cuối cùng trước đợt tăng tạo BOS.
- Vùng = `[low, high]` của nến đó. Chỉ dùng khi đợt di chuyển sau đó >= `2 * ATR`.
- Quy tắc trạng thái giống FVG (fresh/tested/mitigated).

### 4.6 Quét thanh khoản (liquidity sweep)
- Giá đâm qua swing high/low gần nhất (wick vượt) nhưng **đóng nến quay lại bên trong**.
- Sweep dưới đáy rồi đóng lại phía trên → tín hiệu BUY tiềm năng (kiểu spring). Sweep trên đỉnh rồi đóng lại phía dưới → SELL.
- Dùng như **bộ lọc/cộng điểm**, hoặc setup độc lập tại vùng S/R lớn.

### 4.7 Trendline và phá vỡ
- Trendline giảm: nối >= 2 swing high liên tiếp thấp dần; trendline tăng: nối >= 2 swing low cao dần.
- Hợp lệ khi >= 2 điểm chạm và không có nến đóng cửa xuyên đường giữa các điểm chạm.
- **Phá vỡ:** nến đóng cửa vượt đường >= `0.2 * ATR`.
- **Setup retest:** sau phá vỡ, giá quay lại chạm đường (hoặc vùng S/R trùng) trong tối đa `K` nến (mặc định 20), rồi có nến trigger đúng chiều phá vỡ.

### 4.8 RSI (bộ lọc, không phải tín hiệu độc lập)
- BUY: RSI(14) không ở vùng quá mua cực đoan (< 75) tại khung vào lệnh; SELL: không < 25.
- Có thể dùng phân kỳ ở D1/H4 như điểm cộng, không bắt buộc.

### 4.9 Elliott Wave — KHÔNG tự động hóa
Việc đếm sóng quá chủ quan để code thành quy tắc khách quan. **Không đưa vào logic vào lệnh.** Nếu muốn dùng, chỉ để người dùng nhập tay một mốc invalidation/vùng mục tiêu vào `config.yaml` làm bộ lọc, và đo xem bộ lọc đó có cải thiện kết quả không.

---

## 5. Quy tắc trigger (M15)

Chỉ vào lệnh khi giá đang ở trong vùng setup H1 và có **một** trong các nến xác nhận đã đóng:
- **Engulfing:** thân nến nuốt trọn thân nến trước, đúng chiều lệnh.
- **Pin bar:** bóng nến >= 2 lần thân, bóng hướng về phía vùng bị từ chối.
- **CHoCH nhỏ ở M15:** phá swing M15 ngược chiều hồi, đúng chiều lệnh.

Entry = giá đóng cửa của nến trigger (hoặc lệnh thị trường ngay sau khi nến đóng).

---

## 6. Quản trị rủi ro

| Tham số | Mặc định |
|---|---|
| Rủi ro mỗi lệnh | 1% equity demo |
| Lệnh mở đồng thời tối đa | 2 (và không cùng chiều + cùng vùng) |
| Lỗ tối đa trong ngày | 3% → dừng giao dịch đến hết ngày |
| Lỗ liên tiếp tối đa | 4 lệnh → tạm dừng 1 phiên |
| R:R tối thiểu tới TP1 | 1.5 |
| Spread tối đa cho phép | theo `config.yaml`, vượt thì bỏ qua tín hiệu |

**Stop loss:** đặt ngoài cấu trúc làm vô hiệu setup, cộng đệm theo ATR:
- BUY: dưới đáy của vùng/nến trigger/sweep một đoạn `0.3 * ATR(14, H1)`. SELL: ngược lại.
- Bỏ qua tín hiệu nếu SL xa hơn `2 * ATR(14, H1)` (R:R sẽ kém).

**Take profit:**
- TP1: vùng S/R đối diện gần nhất hoặc swing gần nhất, tối thiểu R:R 1.5.
- TP2: vùng lớn kế tiếp ở H4/D1.

**Quản lý lệnh (cố định, không điều chỉnh theo cảm xúc):**
- Chốt 50% tại TP1, dời SL về hòa vốn.
- Phần còn lại chạy tới TP2 hoặc trailing theo swing gần nhất ở H1.
- Đóng lệnh sớm nếu nến H4 đóng cửa phá mốc invalidation của setup.

**Khối lượng:** `lot = (equity * risk%) / (khoảng_SL_theo_tiền_cho_1_lot)`, làm tròn xuống theo bước lot của broker (đọc `symbol_info`: contract size, tick value, volume_step).

**Bộ lọc tin tức/phiên:** tránh vào lệnh trong ±30 phút quanh tin lớn của USD (CPI, NFP, FOMC) và khung giờ thanh khoản mỏng cuối tuần. Cấu hình bằng danh sách thời điểm trong `config.yaml`.

---

## 7. Nhật ký và dữ liệu cần lưu

**Bảng `signals`:** thời gian, setup, chiều, bias các khung, vùng, điểm confluence, `accepted` (có vào lệnh không), lý do bỏ qua.

**Bảng `trades`:** id, thời gian vào/ra, chiều, entry, SL, TP1, TP2, khối lượng, setup, bias D1/H4, điểm confluence, kết quả (R-multiple), lý do thoát, MAE/MFE, spread lúc vào.

**Bảng `equity`:** thời gian, equity, drawdown.

Lưu **R-multiple** (lãi/lỗ chia cho rủi ro ban đầu) làm thước đo chính, không chỉ lãi/lỗ tiền.

---

## 8. Thống kê và tiêu chuẩn đánh giá

Báo cáo gồm: số lệnh, tỉ lệ thắng, R trung bình thắng/thua, **expectancy** `E = winrate * avgWin_R - (1 - winrate) * avgLoss_R`, profit factor, max drawdown, chuỗi thua dài nhất, và **breakdown theo setup, theo chiều, theo phiên, theo bias**.

**Tiêu chuẩn kết luận:**
- Dưới 30 lệnh: không kết luận gì.
- Tối thiểu **100+ lệnh** (tốt nhất 200+) cho mỗi cấu hình trước khi tin vào con số.
- Báo kèm **khoảng tin cậy** của tỉ lệ thắng (ví dụ Wilson 95%), vì 55% trên 40 lệnh chưa khác biệt đáng kể với 45%.
- Một phương pháp chỉ "có edge" khi expectancy dương **sau khi trừ spread/slippage** và ổn định giữa các giai đoạn.

**Chống overfitting:**
- Chia dữ liệu: huấn luyện/tinh chỉnh tham số trên một giai đoạn, **kiểm tra trên giai đoạn chưa từng thấy** (walk-forward).
- Không chỉnh tham số sau khi nhìn kết quả của tập kiểm tra rồi báo cáo như kết quả mới.
- Giới hạn số tham số được tinh chỉnh; ưu tiên quy tắc đơn giản.
- Forward test trên demo live (mục 9, bước 5) là bằng chứng cuối cùng.

---

## 9. Thứ tự triển khai (làm lần lượt, mỗi bước có test)

1. **Data layer:** nạp nến M15/H1/H4/D1 từ MT5 (thư viện `MetaTrader5`, chạy trên Windows) hoặc từ CSV. Hàm chuẩn hóa timezone, chỉ trả nến đã đóng.
2. **Structure:** swing, xu hướng, ATR, EMA, RSI, ADX. Unit test bằng dữ liệu nhỏ có đáp án biết trước.
3. **Detectors:** vùng S/R, FVG (có vòng đời trạng thái), OB, sweep, trendline + phá vỡ. Test từng cái riêng.
4. **Signals + MTF:** mỗi setup là module độc lập trả `Signal(direction, setup, zone, sl_ref, tp_ref, score)`; module `mtf` ra bias.
5. **Backtest engine:** chạy cùng code signal trên lịch sử, mô phỏng spread + slippage + thứ tự chạm SL/TP trong nến (giả định bảo thủ: nếu cả SL và TP nằm trong một nến, tính là chạm SL trước).
6. **Journal + stats:** SQLite và báo cáo như mục 8.
7. **Execution demo:** gửi lệnh qua MT5 demo, có guard chỉ-demo, kill switch (file `STOP` trong thư mục thì bot ngừng đặt lệnh mới), xử lý mất kết nối, tránh đặt lệnh trùng.
8. **Chạy live-demo** liên tục, so kết quả thực tế với backtest để phát hiện chênh lệch (slippage, spread, logic lệch).

---

## 10. Mẫu `config.yaml`

Xem file `config.yaml` ở gốc project (đã mở rộng từ mẫu ban đầu, mọi tham số đều có chú thích).

---

## 11. Quy ước khi code (dành cho Claude Code)

- Python 3.11+, type hints, `pandas`/`numpy`, `pytest` cho test, `sqlite3` cho journal.
- Hàm thuần (pure) cho mọi phần phát hiện cấu trúc: nhận DataFrame, trả kết quả, không side effect, để backtest và live dùng chung một logic.
- Không sửa logic signal để "làm đẹp" kết quả backtest mà không ghi lại lý do trong `CHANGELOG.md`.
- Mỗi lần thay đổi quy tắc/tham số phải chạy lại backtest toàn bộ và lưu báo cáo có gắn phiên bản config.
- Khi gặp điều kiện mơ hồ, chọn phương án bảo thủ (bỏ qua tín hiệu) thay vì đoán.

---

## 12. Quyết định đã chốt với người dùng

- Nền tảng: **MT5 demo** trên Windows, thư viện `MetaTrader5`. Symbol mặc định `XAUUSD` (sửa trong `config.yaml` nếu broker đặt tên khác).
- Dữ liệu backtest: kéo trực tiếp từ MT5, cache CSV trong `cache/` (có thể thả file CSV cùng định dạng vào đó để dùng nguồn khác).
- Setup kiểm chứng: cả 4 — `fvg_retest`, `trendline_break_retest`, `sweep_reversal`, `sr_flip_retest`. Báo cáo luôn breakdown theo setup để đánh giá riêng từng cái.

## 13. Các diễn giải bảo thủ đã áp dụng (chỗ spec còn mơ hồ)

- "FVG tested lần đầu": chỉ vào lệnh trong **lần chạm đầu tiên** (`max_touch_episodes: 1`), áp dụng giống nhau cho S/R flip.
- Vai trò vùng S/R trước khi vỡ được xác định bằng lần đóng cửa gần nhất nằm ngoài vùng; không xác định được thì bỏ qua.
- TP1 = mức cấu trúc gần nhất; nếu mức đó chưa đạt R:R tối thiểu thì bỏ tín hiệu (`tp1_mode: nearest`). Không có mức cấu trúc nào → bỏ (`tp1_fallback_rr: null`).
- Pin bar thêm điều kiện bóng chính >= 50% biên độ nến (`pin_min_wick_range`) để loại doji.
- Hai chân lệnh (TP1 + runner) chỉ dùng khi tài khoản là hedging; tài khoản netting dùng một lệnh duy nhất tới TP1.
- Hòa vốn (R = 0) không tính là thua khi đếm chuỗi thua liên tiếp.

## 14. Giao diện web và bộ lọc tin (v0.2.0)

- `python main.py web` (hoặc double-click `run_web.bat`) → FastAPI ở `127.0.0.1:8000` (`web/`).
- Frontend: React 18 + TypeScript trong `frontend/` (Vite, Mantine 7, TanStack Query, Recharts, Lightweight Charts 4.2.3).
  Sửa giao diện xong phải `cd frontend && npm run build` (ra `web/static/dist`, FastAPI phục vụ bản build này).
  `npm run build` dùng `build.mjs` để chạy Vite từ đường dẫn thật vì `D:` là ổ subst/junction tới `C:\D_data`.
- Web KHÔNG tự đặt lệnh: bot live và backtest chạy thành tiến trình con `main.py live|backtest`
  (`web/services/processes.py`); dừng bot = tạo `run/bot.shutdown` để bot thoát êm. Web có kết nối MT5 riêng
  (`web/services/mt5_gateway.py`) chỉ để đọc dữ liệu/tài khoản; không có MT5 thì đọc cache CSV.
- Tin tức (`news/`): feed ForexFactory tuần hiện tại, lưu dồn vào `journal/news.db`; lịch sử cho backtest phải
  nhập CSV (cột time,title,country,impact,forecast,previous). Quy tắc xác định: mỗi tin USD High có
  forecast & previous là số → chiều USD theo `news.usd_rules` → vàng ngược chiều; cộng điểm các tin trong
  `lookahead_hours`. `forecast_rule`: off | block_against | require_aligned. Cột `news` trong journal dùng để
  đo xem bộ lọc có cải thiện kết quả không (chạy backtest với `off` để so sánh).

## 15. Phương pháp hiện tại: breakout range H1 theo xu hướng H4 (v0.6.0)

- Khung H4 (bias SMC) → H1 (range + breakout, `signals/range_breakout.py`) → xác nhận M15 hoặc M5 (`timeframes.confirm`)
  → vòng lặp/khớp lệnh M5 (`timeframes.trigger`). Định nghĩa từng bước trong docstring của `signals/range_breakout.py`.
- Giữ lệnh qua đêm, đóng hết 16:00 NY thứ Sáu (`management.flat_weekday`, `sessions.trading_day_start`).
  `flat_weekday: null` = đóng hằng ngày như ICT intraday.
- Hồ sơ cũ vẫn chạy được: ICT intraday v0.5 (`ict_profile`) và phương pháp D1/H4 → H1 → M15 (`legacy_profile`),
  xem tests/conftest.py. Bản config v0.5 lưu ở `config.v050.bak.yaml`.
- Backtest M5 bị giới hạn bởi "Max bars in chart" của MT5 (mặc định 100.000 nến ≈ 17 tháng M5).

## 16. Tài liệu kiến thức tham khảo

- `docs/knowledge/tradecoinunderground.md`: tóm tắt quy tắc từ Trade Lab (XAU Playbook 13 phương pháp, SMC/ICT,
  Price Action, Opening Range, ATR, quản lý vốn) + đối chiếu với tính năng bot còn thiếu. Nguồn không công bố số liệu
  backtest đọc được → mọi quy tắc phải tự backtest lại.
- `playbook/` + `playbook.yaml`: backtest các phương pháp sổ tay (`python main.py playbook --from … --to … [--only xau05]`),
  khung lớn gộp từ M5 theo UTC, mỗi phương pháp một run trong journal (params.title hiện trên giao diện). Chưa có live.

## 17. Hai bot ONE (từ v0.12.0)

- Phương pháp duy nhất: ONE (`docs/methods/ONE.md`, `playbook.yaml` mục `unified`, `one_swing`, `one_day`).
- Bot live mới: `python main.py bot --name swing|day [--dry-run]` (`execution/one_bot.py` + `playbook/live_engine.py`).
  Bot cũ (`main.py live`, range_breakout) không còn dùng. Mỗi bot magic + journal riêng (`bots` trong config.yaml).
- Live phải loại nến khung lớn chưa đóng (`build_market(..., now)`), quét mẫu hình tăng dần (`scan_since`).

## 18. Vẽ tay + nhận xét lệnh

- Chart chính và tab "Vẽ & nhận xét" của từng lệnh (`frontend/src/components/chart/DrawingLayer.tsx`,
  `components/trades/ReviewPanel.tsx`) lưu vào `journal/reviews.db` (`journal/reviews.py`, API `web/routes/review.py`).
- Khi người dùng nhờ "học từ nhận xét": chạy `python main.py reviews`, tìm lỗi lặp lại, đề xuất quy tắc xác định, backtest
  lại rồi mới áp dụng. Không để bot tự đổi quy tắc từ nhận xét.
