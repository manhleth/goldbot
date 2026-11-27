# Kiến thức: channel "Kho tài liệu IRONMAN CAPITAL" (t.me/tailieuironman)

- **Nguồn:** 66 bài (09/2022 → 02/2026), đã đọc 12 bài liên quan tới trade / quản lý rủi ro, kèm 33 ảnh (đọc tạm rồi xoá).
- **Nội dung channel:** chủ yếu là crypto (soi dự án scam, tokenomics, on-chain, memecoin) và chuyện sàn/quỹ.
- **Độ tin cậy:** không bài nào công bố số liệu backtest. Channel tự nhận là đối tác Exness, nên có xung đột lợi ích khi nói về sàn.
- Diễn giải bằng lời của mình, không chép nguyên văn.

## 1. Bẫy phá vỡ (bull/bear trap) — bài 174, phần đáng giá nhất

- **Định nghĩa:**
  - Giá phá một mức, người đuổi theo vào lệnh, rồi giá quay đầu chạy mạnh theo hướng ngược lại.
  - Lý do theo tác giả: thị trường cần người mua để xả hàng (bull trap), hoặc người bán để kéo giá lên (bear trap), đồng thời quét SL.
- **Ba dấu hiệu trap:**
  1. Nến phá "đẹp quá mức": phá rất mạnh, chạy thẳng, không retest, không có thời gian xây nền.
  2. Nến tin có râu hai đầu: spread giãn, trượt giá, giá quét cả hai chiều trước khi chọn hướng. Ví dụ trong bài: CPI Mỹ, giá vọt lên rồi đảo chiều giảm kéo dài.
  3. Phá xong đứng hình: giá không đi tiếp theo hướng phá.
- **Checklist trước khi vào lệnh:**
  - Hôm nay có tin lớn không?
  - Giá phá xong đã retest chưa?
  - Điểm vô hiệu nằm ở đâu?
  - R:R còn ổn hay đang đuổi nến?
  - Khối lượng có đủ nhỏ để sống sót nếu bị quét không?

## 2. Quản lý vốn — bài 56, 120

- **Mục tiêu bền vững:** khoảng 10–20%/tháng với rủi ro khoảng 2%/lệnh.
- **Cách tài khoản cháy:** thắng vài lệnh rồi nâng rủi ro lên 20–30%/lệnh.
- **Ví dụ trong bài:** 43 lệnh thắng khoảng +1% và 6 lệnh thua −2% thì được +31%. Nếu đặt sai khối lượng để mỗi lệnh thua mất −10% thì kết quả thành −17%. Hệ thắng nhỏ / thua to rất nhạy với khối lượng của lệnh thua.
- **Bài 120:** hệ R:R 1:1, winrate 60% thì expectancy = +0,2R/lệnh. Bài chỉ có link Google Sheet, không có nội dung.

## 3. Rủi ro sàn và khớp lệnh — bài 132, 166, 169 (lời kể của người dùng, chưa kiểm chứng)

- **XAUUSD ngày 28/11/2025** (sau Lễ Tạ ơn Mỹ, thanh khoản mỏng):
  - Một sàn có 2 nến M1 cắm râu xuống khoảng 4156, sàn khác chỉ khoảng 4171–4176.
  - Râu dài khoảng 25$, hồi gần hết ngay trong nến, lặp lại 2 lần.
  - Người dùng bị quét SL hoặc cháy tài khoản, trong khi trên sàn khác lệnh không bị quét.
  - **Kết luận:** độ dài râu khác nhau giữa các sàn → backtest phải dùng dữ liệu của chính broker đang chạy.
- **Lúc biến động mạnh** (BTCUSD 21/12/2024): báo giá bị từ chối (off-quotes), không đóng được lệnh khoảng 10 phút, giá chạy qua TP mà không khớp.
- **Sàn giữ tiền rút khi lời lớn:** không ảnh hưởng tài khoản demo.

## 4. Quỹ cấp vốn (FTMO) — bài 165, 173 (theo tóm tắt của channel, cần đối chiếu điều khoản gốc)

- **Bị cấm:**
  - Copytrade / chép lệnh giữa các tài khoản, trade theo nhóm, nhờ người khác trade hộ.
  - Lợi dụng lỗi giá; bot tốc độ cao.
  - Mở lệnh khi thị trường đóng, hoặc trong khoảng 2 giờ trước tin lớn.
  - Khối lượng quá lớn (overexposure); hedge chéo giữa các tài khoản; spam lệnh nhỏ.
  - Không đặt SL / all-in.
- **Từ 08/12/2025, FTMO siết thêm:** rủi ro trên mỗi ý tưởng giao dịch, lot tăng đột biến, dồn lệnh (stacking), martingale. FTMO có thể huỷ tài khoản dù chưa chạm giới hạn lỗ.
- **Liên quan tới bot:** bot swing nhồi tối đa 5 lệnh × 5% = 25% rủi ro trên một ý tưởng. Mức này **không dùng được cho tài khoản quỹ**.

## 5. Đề xuất cho bot vàng (ONE) — phải backtest trước khi bật

| # | Quy tắc | Tham số đề xuất | Nguồn |
|---|---|---|---|
| B | Bỏ tín hiệu nếu nến phá quá đà (đuổi nến) | Biên độ nến phá > 2 ATR, hoặc đóng cửa vượt cạnh > 1 ATR | 174 |
| C | Bỏ nếu nến phá có râu cả hai đầu (dấu vết quét hai chiều) | Mỗi râu ≥ 30% biên độ, biên độ ≥ 1,5 ATR | 174 |
| D | Phá thất bại → thoát sớm: trong N nến sau khi vào, có nến đóng cửa quay lại trong mẫu hình | N = 3 | 174 |
| E | Yêu cầu nến kế tiếp xác nhận cùng chiều rồi mới vào | 1 nến | 174 |
| F | Vào khi giá retest cạnh vừa phá thay vì vào ngay | Hiệu lực 10 nến, vùng ± 0,3 ATR | 174 |
| G | Setup ngược: "fade trap" (phá thất bại thì vào ngược chiều cú phá, vẫn theo xu hướng H4) | N = 3, SL ngoài đỉnh/đáy cú phá + 0,3 ATR | 174 |
| A | Chặn tín hiệu quanh tin USD High | ± 15/30/60 phút. Cần CSV lịch tin lịch sử | 174 |
| S1 | Chặn vào lệnh khi spread cao (hiện bot ONE chỉ ghi lại spread) | > 0,40$ hoặc > 3 lần trung vị gần đây | 166, 174 |
| S3 | Nhận diện nến spike, không lấy làm đỉnh/đáy cho mẫu hình hay mốc dời SL; tạm dừng 30 phút | Râu ≥ 5 ATR, hồi ≥ 80% | 169 |
| S5 | Gặp off-quotes / requote / mất kết nối: thử lại có giãn cách; vượt số lần thì bật kill switch | Tối đa 5 lần, giãn 2 giây | 132 |

**Không dùng được:**
- Volume (MT5 chỉ có tick volume của broker).
- Bộ lọc tìm coin trên TradingView, EMA34/89, RSI > 50: chỉ dùng cho crypto, không có bằng chứng hiệu quả.
- Lời cáo buộc "sàn thao túng": không kiểm chứng được.
