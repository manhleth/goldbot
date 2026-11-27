# Khoá "K23 Alden Nguyen" (YouTube, 57 buổi) — tổng hợp kiến thức và đối chiếu với bot

Nguồn: phụ đề tự động tiếng Việt của playlist (tải bằng yt-dlp, 2026-11-26). Đã đọc kỹ 9 nhóm buổi về hệ thống
(ghi chú chi tiết từng nhóm, có mốc [h:mm]: `docs/knowledge/alden-k23/A1…A9`). Chưa đọc: các buổi tâm lý/kỷ luật và
phân tích thị trường thực tế (B10–13, 14–26, 28, 31–54 trừ các buổi đã liệt kê trong A7–A9).

**Lưu ý quan trọng**
- Mọi ví dụ trong khoá là BTC/crypto; người giảng nói rõ **không khuyến khích đánh vàng** (sóng loạn, nhiều tin bất thường).
- Các con số xác suất (80%, 70%, 9/10, 20-20-60…) là ước lượng cảm tính của người giảng, không phải thống kê.
- Nhiều khái niệm chỉ mô tả bằng hình ảnh ("mô hình đẹp", "lừng khừng", "hết xăng") → muốn code phải tự định lượng
  và backtest riêng cho XAUUSD.

## 1. Bộ công cụ
- Chỉ dùng **RSI** (chu kỳ không nói rõ, gần như chắc chắn 14 mặc định) + **2 đường MA vẽ trên RSI: EMA9 (nhanh),
  WMA45 (chậm)**; trên chart giá chỉ vẽ **hỗ trợ/kháng cự**. Không dùng MA trên giá, **cấm dùng phân kỳ RSI**.
- Đọc RSI riêng từng khung: ≥ 70 lực mua chiếm ưu thế, ≤ 30 lực bán chiếm ưu thế (không phải quá mua/quá bán để đánh
  ngược); 40–60 cân bằng; ≥ 80 / ≤ 20 một bên áp đảo.

## 2. Khái niệm cốt lõi (đã định lượng tới mức có thể)
| Khái niệm | Định nghĩa trong khoá | Gợi ý định lượng cho bot |
|---|---|---|
| **Mô hình RSI** (một sóng của khung) | RSI cắt qua cả 2 MA, EMA9 cắt WMA45, cả 3 đường dốc cùng chiều và tách xa nhau; chỉ tính nến đã đóng. MA đi ngang = không có mô hình | RSI > EMA9 > WMA45 (tăng), độ dốc WMA45 > 0 trong N nến, khoảng cách RSI–WMA45 tăng |
| **Quán tính** | Nến đóng với RSI ≥ 80 (≤ 20). Sau đó điều chỉnh nông (RSI không thủng 50, giá không quá Fibo 0.5) rồi có sóng tiếp diễn về ít nhất đỉnh cũ. Chạm 77–79 rồi quay đầu = fail | RSI(14) close ≥ 80/≤ 20; thử 70/75/80 |
| **Bình nhiên liệu** | Khoảng cách RSI ↔ 2 MA: vừa cắt và đang mở rộng = còn đầy (không đánh ngược); đi xa = gần cạn (thôi vào cùng chiều). Đảo chiều cần 2 MA co lại từ từ, không đảo chữ V | |RSI − WMA45| và độ dốc của nó |
| **Sideway loại 1 — không lực** | Đỉnh RSI gần nhất < 70, đáy gần nhất > 30, RSI trôi vào 40–60, MA đi ngang → **đứng ngoài** | dễ code |
| **Sideway loại 2 — tranh chấp** | Mô hình RSI khung nhỏ ngược chiều khung lớn liền kề; giá chạy trong kênh/tam giác → đánh 2 chiều ở biên, chốt biên đối diện | |
| **Sideway trong sideway** | Cụm W–M đang quyết định nhưng ngược pha → mọi khung dưới W nhiễu; 1–2 tuần mới có 1 lệnh, rủi ro 0.5% | |
| **Logic khung** | Hai khung ảnh hưởng nhau khi gấp 3–6 lần (≤ 2 lần coi như một). Một khung chạy sóng cần khung lớn liền kề có RSI cùng chiều (**cho phép**) và khung nhỏ liền kề có quán tính cùng chiều (**ủng hộ**). Sóng đi dần từ khung nhỏ lên khung lớn | H1–H4–D1, M15–H1–H4 |
| **Tịnh tiến** | Khung có mô hình nhưng không kéo được giá → quyền quyết định chuyển sang khung liền kề lớn hơn (H1→H2, H4→H6), không nhảy cóc | |
| **Chế độ thị trường** | Các khung D1→M đồng thuận = xu hướng (mua/chờ mua, giữ lâu, tăng kỳ vọng); ngược pha = sideway (chỉ vào ở biên, chốt non) | |

## 3. Công thức vào lệnh và quản lý lệnh
**3 quy luật vào lệnh:** (1) có mô hình mới vào (khoảng 70% thời gian thị trường không rõ ràng, chỉ ~3–10 lệnh/tháng);
(2) mô hình ở khung nào thì **target = kháng cự/hỗ trợ của chính khung đó**; (3) **bắt buộc chờ một sóng hồi ở khung
nhỏ không phá cấu trúc** rồi mới vào — phá kháng cự chưa hồi là FOMO.
- Trigger: khung vào lệnh đang điều chỉnh mà RSI khung nhỏ hơn lên > 60 (buy) / M5 & M15 xuống < 40 (sell); hoặc tạo hỗ
  trợ / cấu trúc tăng dần / phá cấu trúc rồi retest.
- Không long sát dưới kháng cự, không short sát trên hỗ trợ, không đánh ngược quán tính; không vào khi mô hình nằm trọn
  trong 40–60; không vào khi sóng đã đi quá nửa; tránh gần tin lớn.
- **SL** ngoài đáy/đỉnh của sóng hồi khung nhỏ (S/R chỉ tham khảo). **Rủi ro 1%/lệnh** (0.3–0.5% khi setup kém hoặc
  thị trường nhiễu). Muốn khối lượng lớn → thu hẹp SL, không tăng %. R:R mục tiêu ~1:5 (người giảng tự nhận 1:5–1:10).
- **Quản lý:** quản lý sóng khung X bằng các khung nhỏ hơn X. Còn quán tính hoặc còn giữ hỗ trợ → giữ; hết quán tính
  **và** phá đáy gần nhất → thoát ngay. Dời SL theo đáy mới, không dời hòa vốn quá sớm. Sóng lớn: chốt 50% khi quán
  tính khung nhỏ hoàn thành, 50% khi vỡ cấu trúc (có chỗ nói 30/30/40). Sideway: chốt non ở biên đối diện.
- **20-20-60:** 20% sóng rõ ràng (phải vào), 20% fail rõ, 60% còn lại ~50/50 → đứng ngoài dù giá chạy mạnh.

## 4. Đối chiếu với bot ONE hiện tại
| Khoá học | Bot ONE | Ghi chú |
|---|---|---|
| Chỉ đánh theo xu hướng của khung lớn | Có (EMA H4 + vĩ mô W1/D1 dài hạn) | Khác công cụ: khoá dùng RSI đa khung, bot dùng EMA |
| Chờ sóng hồi rồi mới vào, không đuổi breakout | **Ngược lại**: bot vào ngay khi nến phá cạnh đóng cửa | Đã thử retest (2026): không cải thiện; nhưng chưa thử kiểu "hồi + trigger RSI khung nhỏ" |
| Thoát theo cấu trúc (phá đáy gần nhất) | Có (gồng SL theo swing khung mẫu hình) | Gần giống |
| Chốt 50% khi hết quán tính | Không | Đã thử chốt 1 phần tại vùng S/R: kém đi |
| Đứng ngoài khi sideway không lực (RSI 40–60) | Không | **Ứng viên mạnh nhất** cho bài toán các năm biên độ thấp 2021–2023 |
| Rủi ro 1% (0.5% khi nhiễu) | 10% swing / 5% scalp phần vốn bot | Khoá thận trọng hơn nhiều — khớp với kết luận backtest nên hạ rủi ro |
| Không đánh vàng | Bot chỉ đánh vàng | Mọi quy tắc phải kiểm chứng riêng |

## 5. Đề xuất backtest (theo thứ tự ưu tiên)
1. **Bộ lọc sideway không lực** (RSI H4/D1 trong 40–60 và đỉnh/đáy RSI gần nhất trong 30–70) → không vào lệnh ONE.
2. **Bộ lọc mô hình RSI**: chỉ nhận cú phá khi RSI khung mẫu hình có mô hình cùng chiều (RSI > EMA9 > WMA45 và đang dốc)
   và khung lớn liền kề có RSI cùng chiều (cho phép).
3. **Điểm vào kiểu khoá học** (setup mới): sau quán tính RSI ≥ 80 ở H1/H4, chờ nhịp hồi nông (RSI ≥ 50, không quá
   Fibo 0.5), vào khi RSI khung nhỏ (M15) > 60; SL dưới đáy nhịp hồi; target kháng cự khung mẫu hình / đỉnh cũ.
4. **Thoát 50% khi khung nhỏ hết quán tính**, phần còn lại gồng theo cấu trúc.
