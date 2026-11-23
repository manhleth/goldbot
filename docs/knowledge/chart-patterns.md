# Kiến thức mẫu hình trendline (từ ảnh người dùng cung cấp, 2026-11-23)

Nguồn: 9 ảnh biểu đồ người dùng gửi (XAUUSD, VNINDEX, BTC, ETH, BTC.D; phần lớn khung 1W/1M).
Bot áp dụng cùng logic trên **H4 và D1** của XAUUSD.

## Nguyên tắc chung

- **Trendline là một vùng, không phải đường chính xác:**
  - Nối các râu nến (đỉnh/đáy swing).
  - Đỉnh/đáy cách đường ≤ dung sai (theo ATR) thì tính là một lần chạm.
  - Râu nến xuyên nhẹ không làm hỏng đường. Chỉ nến **đóng cửa** xuyên vùng mới tính là phá.
- **Số điểm chạm:** đường đáng tin cần ≥ 2–3 điểm chạm. Trong ảnh, các đường tốt có 3–4 điểm chạm (ví dụ VNINDEX có 4 mũi tên ở cạnh dưới).
- **Trade theo mẫu hình, không theo một đường đơn lẻ:** mẫu hình gồm hai cạnh (kênh, cờ, tam giác), hoặc một đường neckline.
- **Mục tiêu giá theo measured move:**
  - Lấy chiều cao mẫu hình, hoặc chiều dài cán cờ.
  - Đo từ điểm phá, theo hướng phá.

## Các mẫu hình

| Mẫu hình | Nhận diện | Vào lệnh | Mục tiêu | Ảnh ví dụ |
|---|---|---|---|---|
| **Cờ / nêm tiếp diễn** | Nhịp mạnh (cán cờ) → kênh hồi ngược chiều hoặc đi ngang, hai cạnh gần song song hoặc hội tụ nhẹ | Nến đóng cửa phá cạnh kênh **theo chiều cán cờ** | Chiều dài cán cờ | BTC (2 kênh), ETH log, BTC.D (cờ giảm → 53,32%) |
| **Tam giác** | Cạnh trên đi xuống, cạnh dưới đi lên, hội tụ | Nến đóng cửa phá một cạnh | Chiều cao tam giác ở điểm bắt đầu | XAU 1W: phá cạnh dưới → 3.479 |
| **Tam giác tăng** | Cạnh trên ngang, cạnh dưới đi lên | Phá cạnh trên (tiếp diễn) hoặc cạnh dưới | Chiều cao mẫu hình | ETH log (sau cờ) |
| **Neckline / vai-đầu-vai** | Đường nối các đáy (thường đi lên nhẹ), đỉnh "đầu" ở giữa | Nến đóng cửa thủng neckline | Chiều cao từ "đầu" tới neckline | XAU 1W → 3.383; Gold |
| **Kênh giá** | Hai cạnh song song, mỗi cạnh ≥ 2–3 chạm | Bật ở cạnh dưới → BUY, bật ở cạnh trên → SELL; hoặc phá kênh | Cạnh đối diện; khi phá thì lấy chiều rộng kênh | VNINDEX (2 kịch bản 2.531 / 1.349), BTC kênh log dài hạn |
| **Hộp tích lũy** | Vùng đi ngang nhiều năm (XAU 2013–2019) | Phá hộp theo xu hướng lớn | Chiều cao hộp | XAU 1M |

## Quy tắc tất định trong bot (`playbook/patterns.py`)

- **Đỉnh/đáy swing:** fractal 3 nến trái/phải trên H4, 2 nến trên D1. Chỉ dùng swing đã xác nhận, không nhìn trước tương lai.
- **Cạnh trên:** đường qua 2 đỉnh swing trong cửa sổ gần đây, thỏa đủ ba điều kiện:
  - Mọi đỉnh trong cửa sổ không vượt đường quá dung sai.
  - Không nến nào đóng cửa trên đường kể từ điểm đầu.
  - Có ≥ `min_touches` điểm chạm.
- **Cạnh dưới:** tìm tương tự qua các đáy.
- **Phân loại hình dạng theo độ dốc hai cạnh:**
  - Song song → kênh.
  - Hội tụ → tam giác/nêm.
  - Kèm điều kiện cán cờ (nhịp ≥ N × ATR ngay trước mẫu hình) → cờ.
- **Loại tín hiệu:** `flag`, `channel_break`, `triangle_break` (phá cạnh), `channel_bounce` (bật cạnh kênh), `neckline_break` (một đường ≥ 3 chạm bị thủng).
- **Thoát lệnh:** gồng theo đỉnh/đáy H4, theo lựa chọn của người dùng. Measured move được lưu làm mục tiêu tham khảo.
- **Rút kinh nghiệm** (`learning` trong playbook.yaml):
  - Mọi tín hiệu đều được trade nháp.
  - Bot chỉ vào lệnh thật với loại tín hiệu (theo khung) có ≥ `min_trades` kết quả nháp đã đóng trước thời điểm đó, và trung bình R của `window` kết quả gần nhất > `min_expectancy`.
  - Lý do từ chối được ghi vào journal: `learning_insufficient` (chưa đủ kết quả nháp) hoặc `learning_negative` (thành tích gần đây âm).
