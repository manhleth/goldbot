# Tính chu kỳ của vàng (XAUUSD) — đo trên dữ liệu MT5 2004-06 → 2026-11

Script: phân tích D1/MN1 kéo từ MT5 (22 năm). Kết luận chỉ dựa trên số đo, mẫu nhiều năm còn nhỏ.

## 1. Chu kỳ nhiều năm (kiểu 4 năm của BTC) — KHÔNG đáng tin để giao dịch
- BTC có chu kỳ vì nguồn cung bị cắt theo lịch (halving). Vàng không có cơ chế tương tự; giá chịu tác động của lãi suất
  thực, USD, ngân hàng trung ương mua vào, địa chính trị.
- Đỉnh lớn (cao nhất ±18 tháng): 2011-08, 2016-07, 2020-07 → cách nhau 4.9 và 4.0 năm.
  Đáy lớn: 2015-12, 2018-09, 2022-10 → cách nhau 2.7 và 4.1 năm. Chỉ 3 điểm mỗi loại, không đủ kết luận.
- Tự tương quan lợi nhuận năm ≈ 0 (lag1 +0.07, lag2 +0.01, lag3 −0.11, lag4 −0.13): năm trước không dự báo năm sau.
- Theo nhiệm kỳ tổng thống Mỹ: năm thứ 2 yếu nhất (trung vị −0.9%) nhưng chỉ 6 mẫu, không có ý nghĩa thống kê.

## 2. Mùa vụ theo tháng — có tín hiệu
| Tháng | TB 2004-26 | % tháng tăng | t | TB 2015+ | % tăng 2015+ |
|---|---|---|---|---|---|
| **1** | **+3.8%** | 68% | **3.37** | +4.2% | 75% |
| 2 | +1.4% | 59% | 1.39 | +0.9% | 50% |
| 4 | +1.7% | 64% | 1.74 | +1.7% | 67% |
| 5 | −0.4% | 45% | −0.49 | +0.1% | 58% |
| **6** | −0.7% | 41% | −0.60 | −0.8% | **33%** |
| 7 | +1.3% | 61% | 1.46 | +1.3% | 67% |
| **8** | **+2.1%** | 61% | **2.09** | +1.9% | 50% |
| **9** | +0.1% | 43% | 0.06 | −1.1% | **25%** |
| 11 | +0.9% | 52% | 0.70 | −1.7% | 42% |
| 12 | +0.8% | 59% | 0.82 | +2.2% | 73% |
- Tháng 1 tăng mạnh và ổn định nhất (t > 3); tháng 8 tăng có ý nghĩa; tháng 6 và tháng 9 yếu (gần đây).

## 3. Ngày trong tuần
- Thứ Sáu: +0.116%/ngày, t = 3.35 (có ý nghĩa); thứ Hai hơi âm; các ngày khác ≈ 0.

## 4. Pha xu hướng / đi ngang (ADX D1 trung bình 20 ngày ≥ 25 = xu hướng)
- Pha xu hướng dài trung bình 51 ngày (trung vị 47, dài nhất 164); pha đi ngang trung bình 68 ngày (dài nhất 213).
- Các pha đổi nhau khoảng mỗi 2–3 tháng, ngay trong cùng một năm → nên nhận diện theo trạng thái D1 hiện tại,
  không theo chu kỳ năm.

## 5. Liên hệ với kết quả bot ONE (backtest từng năm 2020-2026)
| Năm | Lợi nhuận vàng | Hiệu suất xu hướng* | Biên độ năm | Swing H4 gốc | Scalp |
|---|---|---|---|---|---|
| 2020 | +24.6% | 0.09 | 43% | +73R | −12R |
| 2021 | −3.5% | 0.04 | **17%** | −8R | −1R |
| 2022 | −0.3% | **0.01** | 28% | −7R | −9R |
| 2023 | +13.1% | 0.07 | **19%** | −3R | −2R |
| 2024 | +27.2% | 0.13 | 41% | +11R | +7R |
| 2025 | +64.6% | **0.21** | **74%** | +82R | +37R |
| 2026 | −19.4% | 0.06 | 63% | +40R | +32R |
\* |thay đổi cả năm| / tổng quãng đường giá đi trong năm.
- Bot thắng lớn khi biên độ năm rộng (≥ 40%), thua khi vàng đi ngang hẹp (biên độ < 30%, hiệu suất xu hướng ≤ 0.07).
- Biên độ cả năm chỉ biết sau khi năm kết thúc → muốn dùng phải đo trạng thái theo thời gian thực (ADX/biên độ
  range D1 gần nhất), không dùng được như một "chu kỳ" dự báo trước.
