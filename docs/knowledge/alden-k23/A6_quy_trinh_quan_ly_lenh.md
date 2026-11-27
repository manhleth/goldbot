# A6 — Buổi 9: Quy trình vào lệnh và quản lý lệnh (K23 Alden Nguyen)

Nguồn: `11_fhKzP_yUxjo.txt` (~4h35). Ví dụ trong buổi chủ yếu là BTC (Futures Binance). Đơn vị "giá" = điểm giá BTC, không dùng thẳng cho XAUUSD được.

## 1. Tóm tắt các phần

- **[0:00–0:15]** Mở đầu về tâm lý. Người giảng cho rằng khoảng buổi 35–40 thì ai cũng phân tích được như nhau; thắng thua là do kỷ luật (tâm lý chiếm ~60%, kiến thức/tư duy/chiến thuật ~40%). Nhắc lại nguyên tắc: có mô hình thì vào, không có thì đứng ngoài.
- **[0:15–0:20]** Ôn lại hệ thống: RSI đo lực mua/bán, mô hình tích lũy, tìm khung đang quyết định thị trường để ra target/SL/entry; lý thuyết Dow + đa khung giúp có R:R rất tốt nên không cần đòn bẩy lớn (ví dụ một lệnh lãi ~15% tài khoản trong vài ngày).
- **[0:20–0:55]** **Quy trình vào lệnh**, minh họa trực tiếp: 1D đang tăng mạnh và chạm kháng cự (RSI >70). Ý chính: hình ảnh "đoàn tàu" phải giảm tốc rồi mới quay đầu; sóng tịnh tiến từ khung nhỏ lên khung lớn; tìm khung "đang chạy sóng" (lúc đó là H1); điều kiện đồng pha/ngược pha với khung lớn liền kề; thời gian giá di chuyển cũng phản ánh lực.
- **[0:50–0:52]** Volume trên 1D không đột phá, nên sóng tăng này nghi do cá mập đẩy ở khung nhỏ. Có thể phải chuẩn bị vị thế short.
- **[0:52–1:12]** **Quản lý lệnh** dựa trên 2 kiến thức: bản chất sóng (quán tính tăng/giảm) và cấu trúc sóng (Dow). Đánh hai chiều trong sideway, chốt từng phần, dời SL theo đỉnh/đáy.
- **[1:00–1:02]** "Công tắc" chuyển chế độ: chỉ khi các khung từ 1D trở lên cùng đồng thuận tăng mạnh mới chuyển sang chiến thuật uptrend (mua rồi chờ mua tiếp).
- **[1:14–1:20]** Quy luật volume: chỉ để so sánh, không định lượng; chỉ so với vùng liền kề; chỉ xem từ H4 trở lên.
- **[1:20–1:28]** Tóm tắt lại quy trình.
- **[1:28–4:30]** Hỏi đáp. Các ý đáng chú ý: lý do chọn rủi ro 1%, entry khung nhỏ + target khung lớn, SL dưới đáy sóng điều chỉnh, sóng hồi "đúng" là sóng nào, mô hình thế nào là đẹp, Fibo 0.5, vào spot 30/30/40, cách tính khối lượng, quy tắc 70/30.

## 2. Quy trình vào lệnh và quy tắc quản lý lệnh

### 2.1 Checklist vào lệnh
1. **Xác định xu hướng khung chính**: với Futures là 1D/2D. Chỉ đánh sóng dưới 1D (sóng H4 mất vài ngày, sóng H1 khoảng 2 ngày). Không giữ lệnh Futures theo sóng 1D/3D vì tốn phí.
2. **Không long ngay dưới kháng cự, không short ngay trên hỗ trợ.** Nếu sóng khung lớn đã chạy xa thì SL sẽ quá xa, nên không đuổi theo khung đó nữa.
3. **Tìm khung đang quyết định thị trường**: xem từ khung nhỏ lên. Khung đã chạy xong sóng (hết quán tính, không tạo quán tính mới) sẽ đi ngang và nhường quyền cho khung lớn liền kề. Các cụm H4/H6/H8, M30/M45/H1/90m coi như cùng một khung, chọn khung có mô hình đẹp hơn mà nhìn.
4. **Kiểm tra đồng pha**: mô hình của khung X chỉ chạy được khi khung lớn liền kề cùng chiều. Nếu ngược pha thì khung X dễ đi ngang hoặc thất bại.
5. **Không đánh ngược quán tính**: khung đang có quán tính tăng thì không short. Khung đang điều chỉnh thì cũng chưa long ngay mà chờ.
6. **Đánh giá cách khung quyết định điều chỉnh**:
   - Điều chỉnh **nhanh** trong khi RSI của khung lớn liền kề vẫn ở cao: lực mạnh, long theo khung đó.
   - Điều chỉnh **lâu**: khung lớn kịp quay xuống, khung nhỏ hoàn thành quán tính yếu. Lúc đó tìm short tại nhịp hồi thất bại, lấy trigger ở khung nhỏ hơn (ví dụ M15 cuộn xuống).
7. **Phải có mô hình mới vào.** Mô hình đẹp gồm: hai MA của RSI có xu hướng và mở rộng, RSI vẽ dạng vòng cung, chạm vùng 30/70 (càng tốt nếu tới 20/80). Mô hình chỉ quanh vùng 40–60 là xấu.
8. **Entry**: có 2 cách.
   - (a) Vào sớm khi khung nhỏ đã reset hết lực ngược chiều (không còn quán tính ngược) và tạo được hỗ trợ/kháng cự. Giá đẹp nhưng rủi ro hơn.
   - (b) Chờ khung lớn đã cắt hẳn, rồi vào ở sóng hồi đầu tiên. An toàn hơn nhưng giá kém hơn.
   - Sóng hồi cần chờ là sóng hồi **xác nhận cấu trúc của con sóng muốn ăn**. Ví dụ muốn ăn sóng tăng M15 thì chờ M5 đi lên trước, rồi vào ở nhịp hồi đầu tiên của M5 mà vẫn giữ hỗ trợ. Không vào ở nhịp M5 điều chỉnh khi M15 đã chạy xong, người giảng gọi đây là "sai trầm trọng". Khung nhỏ nhất được dùng là M5.
9. **Điểm cắt nhau của RSI/MA không phải là tín hiệu.** Người giảng nói "cắt lên mua, cắt xuống bán" là cách tự sát nhanh nhất. Điểm cắt chỉ dùng để xác nhận pha điều chỉnh.
10. **Bộ lọc tổng**: chỉ vào khi tự ước lượng xác suất thắng ≥ 80%. Thị trường có 70% thời gian là sóng không rõ ràng, chỉ 30% là rõ ràng. Người giảng chỉ vào khoảng hơn 10 sóng/tháng, và có tháng gần như không có lệnh.

### 2.2 Stop loss
- Đặt **dưới đáy (hoặc trên đỉnh) gần nhất của sóng điều chỉnh** ở khung entry. Mức này đo được bằng giá cụ thể. Đường S/R chỉ mang tính tham khảo, trừ khi giá đã retest và xác nhận nó.
- Nếu M5 tách ra thành một sóng rõ ràng thì có thể đặt SL dưới đáy M5. Khi đánh M15 thì đặt SL dưới đáy gần nhất của mô hình M15.
- **Không bao giờ** lấy cả entry, SL và TP trên khung lớn, vì SL sẽ luôn xa hơn khung nhỏ (sóng nhỏ luôn chạy trước).
- Độ rộng SL thay đổi theo biến động. Ví dụ BTC: sideway SL ~50 giá; 150 giá vẫn bình thường; khi sóng H4 chạy ~3000 giá thì SL ~300 giá cũng chấp nhận được. Trong sideway, SL của M15 và H1 gần như bằng nhau.

### 2.3 Take profit
- **Entry theo khung nhỏ, target theo khung có mô hình (khung lớn)**: ví dụ mô hình H6 thì target là kháng cự của H6. Đây là lý do R:R lớn.
- Nếu trade theo khung nhỏ (M15) thì chỉ kỳ vọng tới kháng cự gần.
- Nếu lệnh đi ngược sóng chính (là sóng điều chỉnh) thì chỉ đặt target gần và khả thi, không kỳ vọng xa.
- Nếu đã tới kháng cự khung nhỏ mà hết lực thì vẫn chốt ("trade what you see"), không giữ vì hy vọng.
- R:R tối thiểu khoảng **1:5** ("mất 1% thì ăn 5%"). Trong ví dụ có target short "ít cũng 500–700 giá".

### 2.4 Giữ lệnh, chốt từng phần, dời SL, thoát sớm
- **Nguyên tắc**: lệnh theo sóng khung X thì quản lý bằng các khung **nhỏ hơn X**. Ví dụ sóng H1 thì nhìn M5/M15, sóng H6 thì nhìn các khung dưới H6.
- **Giữ lệnh** khi khung nhỏ còn quán tính cùng chiều.
- **Giữ lệnh** cả khi không có quán tính, miễn là cấu trúc chưa vỡ: RSI điều chỉnh mà giá đi ngang, giữ được hỗ trợ, nghĩa là không có lực bán. Trường hợp này gặp nhiều trong sideway.
- **Thoát** khi khung nhỏ không còn quán tính VÀ phá đáy gần nhất (vỡ cấu trúc). Thoát ngay khi giá phá đáy, không chờ hình thành cấu trúc giảm. "Cấu trúc" ở đây là đỉnh/đáy gần nhất, không phải Fibo.
- **Chốt 2 phần** với sóng khung lớn (kiểu H4): chốt **50%** khi quán tính hoàn thành (giá vút lên), chốt **50% còn lại** khi vỡ cấu trúc tăng.
- **Dời SL** theo các đáy (đỉnh) mới, đến mức rủi ro gần như bằng 0.
- **Khi H1 hoàn thành quán tính** (lúc khung lớn chưa rõ xu hướng): chốt bớt và chờ xem H4/H6 điều chỉnh. Nếu điều chỉnh đẹp và 1D vẫn tăng thì vào lại hoặc giữ phần còn lại. Nếu H6 kéo 1D xuống theo thì chốt nốt.
- **Thoát sớm** khi khung đang chạy sóng điều chỉnh quá lâu và kéo khung lớn liền kề vào điều chỉnh (thành ngược pha), hoặc giá cứ loằng ngoằng mãi không lên được.
- **Bị SL do râu nến**: nếu râu chỉ vượt một chút rồi khung nhỏ dựng lại cấu trúc thì vào lại. Nếu râu xa thì coi như kịch bản khác.

### 2.5 Nhồi lệnh và vào từng phần
- **Futures**: được nhồi thêm khi H1 điều chỉnh tốt mà H4/H6 vẫn trong xu hướng tăng. Trong giai đoạn uptrend mạnh thì chốt rồi vào lại liên tục.
- **Spot sóng lớn (1W/3D)**:
  - **20–30%** khi khung nhỏ đã reset hết lực giảm, giữ được hỗ trợ và giá giảm tốc rồi dừng hẳn.
  - **30–40%** khi 1D mở xu hướng tăng (RSI 60–70) và các khung H1/H4 ủng hộ.
  - **Phần còn lại** khi phá kháng cự khung D.
  - Nếu thủng hỗ trợ thì SL phần 30% (lỗ nhỏ) và chờ vùng thấp hơn. Cần thêm "hiệu ứng truyền thông". Với spot thì không theo dõi H1.

### 2.6 Khối lượng và rủi ro
- **Rủi ro 1% tài khoản mỗi lệnh**, khuyên không vượt quá 1%. Lý do: mất 1% không ảnh hưởng tâm lý, chịu được 100 lệnh thua liên tiếp (2% thì chỉ còn 50 lệnh). Ai thấy 1% vẫn áp lực thì hạ xuống 0,5%. Người giảng nói không có công thức cụ thể nào cho con số này.
- **Cách tính**: khối lượng = (1% vốn) / khoảng cách SL. Ví dụ: vốn 20.000$, 1% = 200$, SL 100 giá thì vào 2 BTC; SL 400 giá thì vào 0,5 BTC.
- Được dùng đòn bẩy để khỏi chôn vốn, miễn tổng rủi ro vẫn là 1%. Tổng exposure của người giảng khoảng x1 tài khoản.
- **Số lệnh tối đa**: không nêu con số cố định. Không có giới hạn lỗ ngày.
- Kỳ vọng lợi nhuận: 20–30%/tháng "không khó" khi có sóng; tháng sideway chỉ vài %, tháng 12 gần như không có gì.

## 3. Khác biệt giữa xu hướng và sideway

| | Sideway / khung lớn chưa đồng thuận | Xu hướng mạnh (các khung ≥1D đồng thuận + volume mạnh) |
|---|---|---|
| Chiều lệnh | **Hai chiều**: short ở kháng cự, long ở hỗ trợ | Một chiều: mua rồi chờ mua tiếp |
| Kỳ vọng | Giảm kỳ vọng, tăng cẩn trọng, target gần | Được kỳ vọng xa, chốt rồi vào lại |
| Quán tính | Hay gặp sóng không có quán tính nhưng giữ được hỗ trợ, nên phải chờ vỡ hỗ trợ mới chốt | Quán tính liên tục |
| Chốt lệnh | Chốt sớm hơn theo sóng nhỏ (H1 xong thì chốt bớt) | Giữ lâu hơn |
| SL | Hẹp (~50 giá BTC) | Rộng (~300 giá BTC) nhưng target cũng xa |
| Giai đoạn rất trầm lắng | Chấp nhận 2–3 tháng không có sóng để đánh | Một giai đoạn có thể bằng lợi nhuận cả năm |

Ví dụ đánh hai chiều trong sideway: H6 hồi retest kháng cự thì short với SL ngắn, target chỉ tới hỗ trợ gần. Nếu về tới đó mà H6 tích lũy trong khi 1D vẫn tăng thì chốt short và tìm long. Ở cạnh trên của vùng, nếu khung nhỏ hết quán tính và vỡ cấu trúc thì chốt long và tìm short.

## 4. Điểm mơ hồ nếu muốn code thành bot

1. **"Quán tính tăng/giảm"** không có định nghĩa số trong buổi này. Có lẽ là RSI vượt 70/80 (hoặc dưới 30/20) rồi điều chỉnh. Cần chốt ngưỡng và số nến.
2. **4 giai đoạn quán tính**: (1) xu hướng tăng, (2) hình thành quán tính, (3) điều chỉnh = RSI cắt xuống dưới cả 2 MA và MA nhanh cắt xuống MA chậm, (4) hoàn thành. Buổi này không nêu chu kỳ của RSI và các MA, cũng không nêu thế nào là "mở rộng".
3. **"Mô hình đẹp"/"vòng cung"** cần định lượng: độ dốc MA, khoảng cách hai MA, RSI có chạm 30/70 không.
4. **"Điều chỉnh nhanh/lâu"** và "lực mạnh/yếu" cần ngưỡng số nến so với khung lớn liền kề, cùng điều kiện RSI khung lớn còn > X.
5. **"Khung đang chạy sóng"**: phải viết thuật toán quét từ khung nhỏ lên, xem khung nào đã hết quán tính hoặc đi ngang. Các cặp khung "gần như một" (H4/H6, M30/H1/M45/90m) cần quy tắc gộp. MT5 có H6/H8 nhưng không có 2D/3D/45m/90m, phải resample.
6. **"Reset hết lực"** (khung nhỏ không còn quán tính ngược chiều) cần định nghĩa xác định.
7. **Đồng pha/ngược pha**: có thể dùng hướng MA của RSI hoặc vị trí RSI so với 50, nhưng cần chốt cách đo.
8. **Đỉnh/đáy gần nhất** cho SL và cho "vỡ cấu trúc": dùng fractal N nến ở khung nào thì chưa rõ. Đặc biệt quy tắc "nếu M5 tách sóng thì dùng đáy M5" là chủ quan.
9. **Kháng cự/hỗ trợ của khung X** = các đỉnh/đáy ứng với pha điều chỉnh RSI của khung X. Cách này có thể code được nhưng phức tạp.
10. **"Xác suất thắng ≥ 80%"** và "sóng rõ ràng (30%)" không định lượng được. Bot phải thay bằng bộ điều kiện cứng và đo winrate thực tế.
11. **Volume** chỉ là tham khảo ở khung H4 trở lên, và chỉ so với vùng liền kề. Volume tick trên XAUUSD (MT5) không phải volume thật, nên có thể bỏ.
12. **Hiệu ứng truyền thông** và **cá mập** không code được.
13. **Đánh hai chiều** cùng lúc cần tài khoản hedging. Chốt 50/50 cũng cần hedging hoặc chia volume.
14. **Fibo 0.5**: sóng điều chỉnh ở khung nhỏ sâu quá 0.5 thì coi là yếu. Quy tắc này dễ code nhưng phải chốt điểm neo (đỉnh/đáy nào).
15. **Con số "giá"** (50/150/300/500–700) là của BTC. Với XAUUSD nên chuẩn hóa theo ATR.
16. **Vào lại sau khi bị SL do râu**: chưa rõ "râu nhỏ" là bao nhiêu và trong bao nhiêu nến.
