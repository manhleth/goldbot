# CHANGELOG

Mọi thay đổi quy tắc vào/ra lệnh hoặc tham số phải ghi ở đây kèm lý do, và chạy lại backtest toàn bộ.

## 2026-11-23 — v0.1.0
- Khởi tạo: data (MT5 + cache CSV), structure, 4 setup (fvg_retest, sr_flip_retest, sweep_reversal,
  trendline_break_retest), MTF bias, risk, backtest, journal SQLite, báo cáo thống kê, live demo.
- Diễn giải bảo thủ cho các điểm mơ hồ của spec: xem CLAUDE.md mục 13.

## 2026-11-23 — v0.2.0
- Thêm giao diện web local (`python main.py web`): chart kiểu TradingView, phân tích đa khung, lệnh mở,
  điều khiển bot/kill switch, backtest, thống kê, sửa config, xem log.
- Thêm bộ lọc tin kinh tế Mỹ (ForexFactory, impact High): blackout ±30 phút và **quy tắc mới**
  `news.forecast_rule: block_against` — bỏ tín hiệu khi tổng chiều dự báo (forecast so với previous) của tin
  trong 24h tới ngược chiều lệnh. Lý do: người dùng yêu cầu dùng dự báo tin để quyết định vào lệnh.
  Journal ghi cột `news` (aligned/against/neutral/none) để đo hiệu quả bộ lọc trong báo cáo.
- `news_blackout_minutes`/`news_events` chuyển vào mục `news:` của config.

## 2026-11-23 — v0.3.0
- **Quản lý vốn (thay đổi quy tắc):** `risk.sizing: fixed_money`, mỗi lệnh rủi ro tối đa `risk_per_trade_money: 20` USD
  (lot làm tròn xuống), áp dụng cho cả backtest và live. Backtest vốn ban đầu `initial_equity: 1000`.
  Lý do: người dùng yêu cầu vốn 1000$, mỗi lệnh mất tối đa 20$. Kiểu cũ vẫn dùng được với `sizing: percent`.
- Kết quả backtest 2023-11-23 → 2026-11-23 sau thay đổi: 137 lệnh, +233.21$ (+23.3%), PF 1.14, max DD 25.8%.
  Số lệnh/R không đổi so với v0.2.0 (chỉ đổi khối lượng).
- Giao diện viết lại bằng React + TypeScript (Vite, Mantine, Recharts, Lightweight Charts) trong `frontend/`,
  build ra `web/static/dist`. Dashboard thống kê theo USD + R, bật/tắt biểu đồ, giới hạn số vùng vẽ trên chart.
- Tải lịch sử MT5 theo đoạn (`data.fetch_chunk_bars`) vì MT5 từ chối yêu cầu quá lớn.

## 2026-11-23 — v0.4.0 — Đổi phương pháp sang SMC + ICT (intraday)
Lý do: người dùng thấy lợi nhuận phương pháp cũ quá thấp (2025-01 → 2026-11: +3.3%, PF 1.03) và yêu cầu chuyển sang
thuần SMC kết hợp ICT, khung ngắn dưới D1. Code phương pháp cũ giữ nguyên, chỉ tắt (xem `enabled_setups`).
- Khung: bias H4 → setup M15 → vào lệnh M5. Bias `method: smc` = chiều lần phá cấu trúc H4 gần nhất (bỏ EMA/ADX/RSI).
- Setup mới: `sweep_mss_fvg` (quét PDH/PDL hoặc range London → MSS → hồi FVG) và `judas_swing`
  (trong killzone quét range phiên Á → MSS → hồi FVG). Lọc premium/discount theo dealing range H4.
- Giờ theo New York (tự theo DST): chỉ mở lệnh trong killzone London 02–05h & New York 07–10h,
  đóng hết lệnh lúc 16:00 NY (`management.flat_time`) → không giữ lệnh qua đêm/cuối tuần.
- TP1 = thanh khoản đối diện / cấu trúc M15 đầu tiên đạt R:R ≥ 2 (`tp1_mode: first_valid`); SL ngoài đáy/đỉnh cú quét.
- Giới hạn dữ liệu: MT5 mặc định 100.000 nến/khung → M5 chỉ có từ 2025-06-13.

## 2026-11-23 — v0.4.1 — Nới bộ lọc ICT (theo lựa chọn của người dùng)
Lý do: backtest v0.4.0 (2025-06-20 → 2026-11-23) chỉ có 3 lệnh. Đo phễu: 21 setup → 9 tín hiệu → 3 lệnh;
nghẽn ở số mức thanh khoản, yêu cầu nến xác nhận M5 và lọc premium/discount.
- Thêm thanh khoản cấu trúc cho sweep: swing M15 trong 12 giờ gần nhất và equal highs/lows (chênh ≤ 0.1 ATR).
- `trigger.types: [touch]`: nến M5 chạm FVG và đóng cửa chưa phá invalidation là vào (kiểu ICT, không cần nến xác nhận).
- `ict.premium_discount: false`.
- Quy ước đánh giá: tinh chỉnh trên 2025-06 → 2026-03, kiểm tra trên 2026-04 → 2026-11 (không chỉnh thêm sau khi xem).
- Kết quả v0.4.1 (2025-06-20 → 2026-11-23, vốn 1000$, rủi ro 20$/lệnh): 67 lệnh, +19.70$ (+2.0%), PF 1.02,
  winrate 37% (27–49%), max DD 17.3%. Giai đoạn chỉnh 06/2025–03/2026: 41 lệnh, +0.18R/lệnh, PF 1.32;
  giai đoạn kiểm tra 04–11/2026: 26 lệnh, −0.22R/lệnh, PF 0.69 → CHƯA có bằng chứng edge. judas_swing: 0 lệnh.

## 2026-11-23 — v0.5.0
- **SL (thay đổi quy tắc):** `risk.sl_anchor: zone` — SL sau mép xa của FVG (+0.2 ATR) thay vì sau đỉnh/đáy cú quét.
  Lý do: người dùng yêu cầu SL chặt hơn để tăng RR.
- **TP (thay đổi quy tắc):** `risk.tp1_mode: fixed_rr`, `tp1_rr: 2.0` — chốt 50% ở 2R cố định; runner chạy tới
  thanh khoản đối diện của setup / cấu trúc H4, trailing sau TP1.
- **Hòa vốn (quy tắc mới):** `management.breakeven_at_r: 1.0` — giá chạy thuận 1R thì dời SL mọi chân về giá vào
  (backtest áp dụng từ nến sau, live: nếu giá đã quay về sau giá vào thì đóng luôn).
- **Vào lệnh:** `trigger.types: [engulfing, pin_bar, mini_choch]` — chờ nến xác nhận M5 thay vì chạm FVG là vào.
- Kết quả (2025-06-20 → 2026-11-23, vốn 1000$, 20$/lệnh): 62 lệnh, +9.52$, PF 1.01, winrate 26% (17–38%),
  max DD 18.2%. Giai đoạn chỉnh 06/2025–03/2026: 45 lệnh, +0.20R, PF 1.41; giai đoạn kiểm tra 04–11/2026:
  17 lệnh, −0.52R, PF 0.29 → không cải thiện so với v0.4.1, vẫn CHƯA có edge. Hòa vốn cứu 10 lệnh (0R thay vì −1R).

## 2026-11-23 — v0.6.0
- **Phương pháp mới (thay hoàn toàn ICT intraday):** setup `range_breakout` — xu hướng H4 (cấu trúc SMC),
  range tích lũy H1 (≥12 nến, cao ≤ 3 ATR) bị phá bằng nến thân ≥ 0.8 ATR cùng chiều H4; vào lệnh khi giá hồi về
  FVG / order block của sóng phá (lần chạm đầu, hết hạn sau 24 nến H1), xác nhận nến engulfing/pin/CHoCH ở M15 hoặc M5
  (`timeframes.confirm`, khung nào xác nhận trước). Lý do: người dùng yêu cầu breakout thuận xu hướng H1/H4 + điểm vào SMC/ICT.
- Invalidation = thấp hơn giữa mép xa vùng và giữa range; mục tiêu runner = measured move 1× chiều cao range.
- **Giữ lệnh qua đêm:** `management.flat_weekday: 4` — chỉ đóng hết lệnh 16:00 NY thứ Sáu (ngày giao dịch bắt đầu
  `sessions.trading_day_start: 17:00`); bỏ giới hạn killzone (`risk.entry_sessions: []`). Trail/invalidation theo H1.
- Kết quả (2023-11-22 → 2026-11-23, vốn 1000$, 20$/lệnh, tham số chọn trước, chưa tối ưu): 373 lệnh, +105.22$ (+10.5%),
  PF 1.03, winrate 28% (24–33%), expectancy +0.015R, max DD 33.5%. Nửa đầu (11/2023–05/2025): 190 lệnh −0.00R;
  nửa sau (05/2025–11/2026): 183 lệnh +0.03R → ổn định giữa hai nửa nhưng gần hòa vốn, CHƯA có edge rõ ràng.

## 2026-11-23 — v0.7.0
- Thêm module `playbook/` + `playbook.yaml` + lệnh `python main.py playbook`: backtest 12 phương pháp XAU Playbook
  (docs/knowledge/tradecoinunderground.md; bỏ XAU-07 vì không kiểm chứng được). Không đổi bot live.
  Khớp lệnh trên M5 bid/ask (market/limit/stop, lệnh chờ hết hạn/hủy, SL trước TP, nến khớp lệnh chờ chỉ xét SL,
  hòa vốn, chốt một phần, thoát theo giờ/sự kiện), rủi ro 20$/lệnh, vốn 1000$, khung lớn gộp từ M5 theo giờ UTC.
- Kết quả 2024-03-01 → 2026-11-21 (giai đoạn vàng tăng mạnh; chưa tối ưu tham số):
  | Phương pháp | Lệnh | WR | E (R) | PF | Lãi $ | Max DD |
  |---|---|---|---|---|---|---|
  | XAU-01 Hồi EMA21 H1 | 248 | 33% | −0.016 | 0.98 | −50 | 34.6% |
  | XAU-02 MACD/EMA200 H4 | 47 | 49% | +0.467 | 1.91 | +366 | 7.8% |
  | XAU-03 Bollinger H1 | 279 | 52% | −0.038 | 0.92 | −209 | 39.7% |
  | XAU-04 Pivot + Stoch M15 | 3 | — | — | — | +6 | — |
  | XAU-05 Phá hộp Á (stop) | 320 | 42% | +0.252 | 1.43 | +1433 | 18.2% |
  | XAU-06 Phá hộp London | 7771 | 44% | −0.138 | 0.76 | −21206 | cháy |
  | XAU-08 NY open + FVG | 366 | 30% | +0.014 | 1.02 | +82 | 26.6% |
  | XAU-09 Á/London + FVG | 328 | 28% | −0.035 | 0.94 | −224 | 44.4% |
  | XAU-10 EMA9 thuận D1 | 993 | 42% | +0.057 | 1.10 | +1118 | 33.4% |
  | XAU-11 Stoch thuận D1 | 818 | 45% | +0.110 | 1.20 | +1748 | 37.0% |
  | XAU-12 Donchian 55/20 D1 | 8 | 75% | +4.566 | 19.3 | +537 | 1.6% |
  | XAU-13 BOS + Fib + FVG | 151 | 35% | +0.052 | 1.09 | +158 | 24.8% |
- Ứng viên: XAU-05 (E dương cả 3 năm +0.24/+0.28/+0.23R, nhưng BUY +0.33R vs SELL +0.08R), XAU-11 (dương cả hai
  chiều, 2024 chỉ +0.03R), XAU-02 (ít lệnh). Cần kiểm tra trên giai đoạn dài hơn / thị trường giảm trước khi tin.

## 2026-11-23 — v0.7.1
- `playbook` chạy được trên khung gốc M15 (`--base M15 --data cache/XAUUSD_M15_long.csv`); tải M15 từ MT5 về tới
  2015-01. Kiểm chứng: cùng giai đoạn 2024–2026, nền M15 cho kết quả gần như nền M5 (XAU-05 +0.242R vs +0.252R).
- Kết quả 2015-04-01 → 2026-11-21 (11.6 năm, gồm giai đoạn vàng đi ngang/giảm):
  | Phương pháp | Lệnh | WR | E (R) | PF | Năm dương |
  |---|---|---|---|---|---|
  | XAU-02 MACD/EMA200 H4 | 206 | 40% | **+0.192** | 1.32 | 9/12 |
  | XAU-12 Donchian 55/20 D1 | 49 | 39% | **+0.855** | 2.72 | 7/12 (2025 chiếm ~2/3 tổng R) |
  | XAU-05 Phá hộp Á | 1635 | 35% | +0.041 | 1.06 | 6/12, DD 57% |
  | XAU-01 / 03 / 04 / 06 / 10 / 11 / 13 | — | — | âm | < 1 | — |
- Kết luận: XAU-10, XAU-11 (và XAU-05 phần lớn) chỉ lãi nhờ đợt tăng 2024–2026. XAU-02 là ứng viên bền nhất:
  lãi cả nửa đầu (+0.16R) lẫn nửa sau (+0.21R); BUY +0.35R, SELL −0.03R.

## 2026-11-23 — kiểm tra 2026 (01-01 → 11-21, nền M5)
- Lãi: XAU-11 265 lệnh +0.156R PF 1.29 +788$ (DD 17%); XAU-05 85 lệnh +0.234R PF 1.40 +291$ (DD 10%);
  XAU-13 58 lệnh +0.234R PF 1.49 +265$; bot hiện tại (range_breakout) 93 lệnh +0.086R PF 1.18 +153$ (DD 29%);
  XAU-02 14 lệnh +7$; XAU-12 4 lệnh +17$.
- Lỗ: XAU-01 −397$, XAU-03 −401$, XAU-06 cháy, XAU-08 −38$, XAU-09 −27$, XAU-10 −88$; XAU-04 không có lệnh.
- Lưu ý: 2026 là năm vàng tăng mạnh (3500 → 5600); trên 11.6 năm XAU-11 và XAU-13 âm.

## 2026-11-23 — v0.8.0
- **Biến thể gồng lệnh theo cấu trúc** (`playbook.yaml: variants`, `--variant hold_h1|hold_h4|hold_d1`): bỏ TP cố định,
  SL dời theo đỉnh/đáy swing (3 nến trái/phải) của khung H1/H4/D1 xác nhận SAU lúc vào lệnh, lùi 0.2 ATR, chỉ siết
  một chiều. Lý do: người dùng muốn dùng đỉnh/đáy làm hỗ trợ cứng để gồng lệnh dài.
- 12 năm (2015-04 → 2026-11, nền M15), hold_h4 so với TP cố định:
  | Phương pháp | TP cố định E / PF | Gồng H4 E / PF | Gồng H4 lệnh, DD, năm dương |
  |---|---|---|---|
  | XAU-01 | −0.008 / 0.99 | **+0.200 / 1.25** | 765, 47%, 8/12 |
  | XAU-02 | +0.192 / 1.32 | **+0.250 / 1.52** | 223, 13%, 8/12 |
  | XAU-05 | +0.041 / 1.06 | **+0.218 / 1.32** | 1298, 43%, 8/12 |
  | XAU-10 | −0.042 / 0.93 | **+0.193 / 1.22** | 1635, 61%, 7/12 |
  | XAU-11 | −0.050 / 0.92 | +0.099 / 1.12 | 1782, 108%, 6/12 |
  hold_h1 yếu hơn; hold_d1 E cao hơn nhưng DD lớn hơn. XAU-13 không đổi (thoát theo phá cấu trúc/96 nến).
  Lãi chủ yếu từ BUY (XAU-02 BUY +0.48R, SELL −0.06R; XAU-05 BUY +0.28R, SELL +0.09R).
- 2026 (nền M5) gồng H4: XAU-05 72 lệnh +0.61R PF 2.02 +740$ DD 10%; XAU-11 117 lệnh +0.53R +1216$ DD 23%;
  XAU-10 112 lệnh +0.65R +1431$ DD 38%; XAU-01 +213$; XAU-02 +69$.
- Lưu ý chọn lọc: đã thử 3 biến thể × 6 phương pháp trên cùng dữ liệu; hiệu ứng nhất quán (H4 cải thiện gần hết) nên
  đáng tin hơn một kết quả đơn lẻ, nhưng vẫn cần forward test.

## 2026-11-23 — v0.8.1
- Thêm phương pháp trendline đa khung (`playbook/trendlines.py`, `methods_trendline.py`): trendline nối 2 đáy/đỉnh swing
  đã xác nhận (đúng độ dốc, không bị đóng cửa xuyên), chiều theo trendline H4, điểm vào theo trendline H1.
  `tl_bounce` = bật trendline H1; `tl_retest` = phá trendline sóng hồi H1 + retest. Lý do: người dùng yêu cầu thử trendline.
- Kết quả 12 năm (nền M15): TP 2R đều âm (bounce −0.065R PF 0.91; retest −0.093R PF 0.87).
  Gồng H4: bounce 1191 lệnh +0.131R PF 1.15, 7/12 năm dương, DD 168R; retest 940 lệnh +0.244R PF 1.27, 6/12 năm,
  DD 132R, WR 11%. 2026 (M5) gồng H4: bounce +0.477R +870$; retest −0.565R −752$.
- Kết luận: không tốt hơn XAU-02/XAU-05 gồng H4 (DD 13R / 43%); drawdown quá sâu, kết quả theo năm thất thường.

## 2026-11-23 — v0.8.2
- Trendline yêu cầu ≥ 3 đỉnh/đáy chạm (dung sai 0.3 ATR, không bị xuyên) + phát hiện kênh giá song song (≥ 2 điểm chạm
  phía đối diện); thêm `tl_bounce_channel`, `tl_retest_channel` (`require_channel: true`); `playbook.yaml` hỗ trợ `fn`
  để dùng lại hàm với tham số riêng. Lý do: người dùng yêu cầu trendline 3 đỉnh/3 đáy, ưu tiên kênh giá.
- 12 năm (nền M15): TP 2R đều âm (−0.04 … −0.14R). Gồng H4: TL-1 455 lệnh +0.292R PF 1.34 (DD 178%);
  TL-1K (kênh) 129 lệnh +0.770R PF 1.93 nhưng nửa đầu +1.95R / nửa sau −0.26R; TL-2 +0.146R; TL-2K 59 lệnh +0.157R.
  2026 (M5) gồng H4: TL-1 32 lệnh +0.754R +435$; các biến thể khác âm.
- Kết luận: 3 chạm cải thiện TL-1, kênh giá làm ít lệnh và kết quả phụ thuộc vài lệnh rất lớn, không ổn định giữa hai
  nửa giai đoạn → chưa thay XAU-02/XAU-05 gồng H4.

## 2026-11-23 — v0.8.3
- Trendline chỉ vẽ trên H4 (3 chạm), chiều lệnh theo chính trendline; vào lệnh tại trendline H4, xác nhận bằng nến H4
  hoặc H1 (`line_tf`, `tf`, `trend_tf: null`). Mục `tl4_*` trong playbook.yaml (dùng YAML anchor cho tham số chung).
  Lý do: người dùng chỉ tin trendline từ H4 trở lên, chỉ backtest 2025 → nay.
- 2025-01-01 → 2026-11-21 (nền M5):
  | Phương pháp | TP 2R: lệnh, E, lãi | Gồng H4: lệnh, E, PF, lãi, DD |
  |---|---|---|
  | TL4-1 bật TL H4, nến H4 | 58, −0.28R, −284$ | 47, +0.26R, 1.35, +264$, 17% |
  | TL4-1H bật TL H4, nến H1 | 68, −0.04R, −48$ | 53, **+0.85R, 2.12, +909$, 14%** |
  | TL4-2 phá + retest, nến H4 | 39, **+0.23R, +165$** | 35, +0.15R, 1.21, +78$, 16% |
  | TL4-2H phá + retest, nến H1 | 39, −0.08R, −59$ | 38, +0.39R, 1.45, +254$, 31% |
  | XAU-02 (so sánh) | 32, +0.41R, +199$ | 29, +0.39R, 1.82, +194$, 12% |
  | XAU-05 (so sánh) | 202, +0.26R, +876$ | 160, +0.76R, 2.34, +2181$, 17% |
- TL4-1H gồng H4: BUY +0.91R, SELL +0.77R, nhưng 3 lệnh lớn nhất (+18.6/+25.4/+27.5R) chiếm hơn toàn bộ lãi.

## 2026-11-23 — v0.9.0
- **Kiến thức mẫu hình** từ 9 ảnh người dùng: `docs/knowledge/chart-patterns.md` (cờ/nêm, tam giác, neckline, kênh,
  hộp; trendline là vùng; mục tiêu measured move).
- **Nhận diện mẫu hình** `playbook/patterns.py` (H4 + D1, trendline vùng ± 0.3 ATR): flag, channel_break,
  triangle_break, broadening_break, neckline_break (≥ 3 chạm), channel_bounce. Thoát lệnh: gồng H4 (người dùng chọn).
- **Rút kinh nghiệm** `playbook/learning.py` (`learning` trong playbook.yaml): mọi tín hiệu được trade nháp; chỉ vào lệnh
  thật với loại tín hiệu@khung có ≥ 5 kết quả nháp đã đóng trước đó và trung bình 20 kết quả gần nhất > 0R. Tất định,
  không nhìn trước, lý do từ chối ghi journal (`learning_insufficient`, `learning_negative`). Lý do: mục tiêu của người
  dùng là bot vừa trade vừa rút kinh nghiệm.
- Kết quả 2025-01-01 → 2026-11-21 (nền M5, gồng H4):
  | Cấu hình | Lệnh | E | PF | Lãi | DD |
  |---|---|---|---|---|---|
  | Không học, tối đa 1 lệnh | 107 | +0.320R | 1.70 | +544$ | 12.7% |
  | Có học, tối đa 1 lệnh | 98 | +0.333R | 1.73 | +466$ | 12.2% |
  | Không học, tối đa 3 lệnh | 263 | +0.307R | 1.64 | +1412$ | 33.7% |
  | Có học, tối đa 3 lệnh | 202 | +0.334R | 1.66 | +1178$ | 24.7% |
  Kinh nghiệm nháp (từ 11/2023): neckline_break H4 +0.47R, triangle_break H4 +0.33R, channel_break H4 +0.26R,
  flag +0.14…0.26R; âm: channel_bounce, triangle/channel_break D1, broadening.

## 2026-11-23 — v0.10.0
- Thêm module `feeds/` + mục `feeds` trong config + lệnh `python main.py feeds [--backfill] [--media] [--watch]`:
  đọc channel Telegram công khai qua t.me/s/<channel> (không cần đăng nhập), lưu bài vào journal/feeds.db, tải ảnh vào
  data/telegram/<channel>/. Lấy lịch sử bằng cách lùi trang (`?before=`), theo dõi bài mới mỗi `poll_minutes`.
  Lý do: người dùng muốn bot học từ nhận định dài hạn của channel MJCapitalChannel (cả bài cũ và bài mới).
- Chưa có: ghi nhãn nhận định và kiểm chứng với giá thật (bước sau).

## 2026-11-23 — v0.10.1
- Lấy toàn bộ lịch sử MJCapitalChannel: 5.932 bài (07/2022 → nay); lọc chủ đề vàng/bạc/dầu (`feeds.topics`,
  `feeds/topics.py`): 274 bài, 162 ảnh. Ảnh chỉ đọc tạm rồi xoá (người dùng không cần lưu).
- Ghi nhãn 274 bài (bảng `calls` trong journal/feeds.db): 103 bài phân tích thật, XAUUSD 52 bài có hướng.
- Kiểm chứng `feeds/verify.py` (giá tham chiếu = giá mở H1 đầu tiên sau giờ đăng; mốc 1d/1w/1m/3m; mục tiêu vs vô hiệu):
  XAUUSD đúng hướng 51/59/65/67% so với mức nền cùng thời điểm 52/56/65/69% → chưa có lợi thế về hướng; không dùng
  làm bộ lọc. Kiến thức cách vẽ/phân tích: docs/knowledge/mj-capital.md.

## 2026-11-23 — v0.11.0 — PHƯƠNG PHÁP DUY NHẤT
- `playbook/methods_unified.py` + mục `unified` trong playbook.yaml: **phá cấu trúc H4 theo xu hướng, gồng theo
  đỉnh/đáy H4, có học kinh nghiệm**. Lý do: người dùng muốn một phương pháp duy nhất dựa trên toàn bộ kiến thức đã nạp.
  - Chiều: close & EMA50 > EMA200 trên H4 → chỉ BUY; ngược lại chỉ SELL (từ XAU-02).
  - Điểm vào: nến H4 đóng cửa phá cạnh mẫu hình dạng vùng: cờ, tam giác, kênh, neckline (chart-patterns.md,
    mj-capital.md); SL lùi vào trong cạnh 1 ATR; thoát: SL dời theo đỉnh/đáy H4 (hold_h4), không TP cố định.
  - Học: chỉ vào lệnh với loại mẫu hình có ≥ 5 kết quả nháp và trung bình 20 kết quả gần nhất > 0R. Tối đa 2 lệnh.
- Chọn cấu hình bằng thử bật/tắt thành phần trên 12 năm (2015-04 → 2026-11, nền M15), tiêu chí định trước
  R/năm ÷ max DD (R):
  | Tổ hợp | R/năm | DD (R) | Tỉ số | Năm dương | Năm tệ nhất |
  |---|---|---|---|---|---|
  | E1 mẫu hình | +14.3 | 89.8 | 0.16 | 8/12 | −30 |
  | E2 + xu hướng | +14.3 | 63.2 | 0.23 | 7/12 | −19 |
  | **E3 + xu hướng + học (chọn)** | +13.4 | **26.8** | **0.50** | 6/12 | −15 |
  | E4 hộp Á + xu hướng | +23.9 | 54.6 | 0.44 | 7/12 | −36 |
  | E5 mẫu hình + hộp Á + xu hướng + học | +19.0 | 48.6 | 0.39 | 7/12 | −28 |
  | E6 mẫu hình + hộp Á + học | +19.5 | 52.6 | 0.37 | 8/12 | −8 |
  | E7 mẫu hình + hộp Á + xu hướng | +25.2 | 68.2 | 0.37 | 7/12 | −33 |
- E3 12 năm: 311 lệnh, +0.500R, PF 1.93, nửa đầu +0.42R / nửa sau +0.57R; BUY +0.94R, SELL −0.17R.
  2025-01 → 2026-11 (nền M5): 79 lệnh, +1.198R, PF 4.05, +1674$, DD 9.3%; BUY +1.48R, SELL +0.62R;
  bỏ 5 lệnh lớn nhất vẫn +45R. Lưu ý: chọn trên cùng dữ liệu đã thử nhiều lần → cần forward test demo.

## 2026-11-23 — v0.11.1
- Bộ lọc hướng từ nhận định channel (`playbook/bias.py`; chỉ dùng HƯỚNG, không dùng mục tiêu — theo người dùng):
  `strict` (chỉ cùng hướng) / `block_against` (chặn ngược hướng); thêm `channel_bias` vào phương pháp ONE:
  **block_against, nhận định còn hiệu lực 60 ngày**.
- So sánh 8 phương pháp × 5 cách lọc (2024-04 → 2026-11, nền M5, gồng H4), xếp theo tổng R ÷ max DD (R):
  ONE đứng đầu ở mọi cách lọc (11.2–20.5; phương pháp thứ hai XAU-05 ≤ 7.6). ONE: không lọc 103 lệnh +94.7R DD 7.5R
  (12.6); block_against 60d 71 lệnh +76.8R DD 5.1R (14.9); strict 30d 41 lệnh +61.5R DD 3.0R (20.5, quá ít lệnh).
- ONE (có lọc) 2024-04 → 2026-11: 71 lệnh, +1.082R, PF 3.64, +1373$, DD 8.2% (nửa đầu +0.14R / nửa sau +1.90R);
  2025-01 → 2026-11: 53 lệnh, +1.352R, PF 4.40, +1277$, DD 8.9%.

## 2026-11-23 — v0.12.0 — HAI BOT ONE CHẠY SONG SONG TRÊN DEMO
- Bản mô tả phương pháp: `docs/methods/ONE.md` (điều kiện vào lệnh, SL, gồng lệnh, 2 bot, lý do từ chối, ví dụ chart).
- Chart lý do cho từng lệnh (`playbook/chart_svg.py`, SVG thuần): nến khung mẫu hình, cạnh trendline, vào/SL/mục tiêu
  tham khảo/thoát; lưu ở journal/charts/, cột `chart` trong bảng trades; xem qua `/api/charts/{mode}/{id}`.
- Backtest bổ sung: rủi ro % equity (lãi kép), giới hạn lệnh/ngày (`playbook/portfolio.py`), chế độ trong ngày
  (không vào sau 15:30 NY, đóng 16:30 NY), gồng theo khung của chính mẫu hình (`variants.hold_tf`).
- Hai bot (`bots` trong config, `python main.py bot --name swing|day [--dry-run]`, `execution/one_bot.py`,
  `playbook/live_engine.py` dùng đúng code backtest; nến khung lớn chưa đóng bị loại):
  - swing: ONE H4, tối đa 5 lệnh cùng lúc (nhồi lệnh khi có tín hiệu đạt chuẩn), 5% equity/lệnh, magic 20261124.
  - day: ONE M15 + H1, tối đa 10 lệnh/ngày, 5 lệnh cùng lúc, đóng 16:30 NY, 5% equity/lệnh, magic 20261125.
  Lý do: người dùng yêu cầu 2 bot (trong ngày + swing) chạy song song trên tài khoản demo, rủi ro 5%/lệnh.
- Backtest 2025-01 → 2026-11 (nền M5, vốn 1000$, 5%/lệnh lãi kép): swing 76 lệnh +1.28R PF 4.03 DD 26%;
  day M15+H1 721 lệnh +0.25R PF 1.52 DD 77%; day chỉ M15 DD 76%; day chỉ H1 211 lệnh +0.32R PF 1.94 DD 29%.
- Web: nút bật/tắt từng bot, nguồn dữ liệu theo bot, cột Chart ở Lịch sử lệnh, log từng bot.
- Đã chạy dry-run cả 2 bot với MT5 demo, rồi khởi động thật lúc 2026-11-23 10:30 UTC (equity demo 100.000$).
