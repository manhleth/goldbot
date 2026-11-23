# Hướng dẫn deploy GoldBot chạy liên tục 24/7

Bot cần **Windows** và **MT5 terminal đang mở, đã đăng nhập tài khoản DEMO**: thư viện `MetaTrader5` chỉ chạy trên Windows
và gắn vào terminal đang chạy. Bot chỉ chạy tài khoản demo; gặp tài khoản thật thì từ chối và thoát.

Có hai cách:
- **A. VPS Windows** (khuyên dùng): thuê máy chủ chạy 24/7, máy nhà tắt thoải mái.
- **B. Máy nhà luôn bật**: không tốn phí, nhưng mất điện, mất mạng, máy ngủ hay Windows Update khởi động lại là bot dừng.

Các bước 1–6 giống nhau cho cả hai cách (máy nhà đã cài xong thì bỏ qua bước 2–5).

---

## 1. Thuê VPS Windows (chỉ cách A)

- **Cấu hình tối thiểu:** Windows Server 2019/2022 (hoặc Windows 10/11), 2 vCPU, **4 GB RAM**, ổ 40 GB SSD.
  - Bot trong ngày lúc khởi động trade nháp 3 năm dữ liệu M15, cần khoảng 1–2 GB RAM.
  - Hai bot + MT5 + web dùng khoảng 2–3 GB RAM.
- **Vị trí:** chọn VPS gần máy chủ broker (MetaQuotes-Demo) để độ trễ thấp. Châu Âu (London/Amsterdam) là lựa chọn tốt.
- **Kết nối:** từ máy nhà vào VPS bằng **Remote Desktop** (mstsc).
- ⚠️ **Khi rời VPS thì bấm dấu X đóng cửa sổ Remote Desktop (disconnect), KHÔNG chọn Sign out.**
  Sign out sẽ tắt MT5 và cả hai bot.

## 2. Cài phần mềm trên VPS

1. **Python 3.12 trở lên** (đang dùng 3.14): https://www.python.org/downloads/windows/ → tick **"Add python.exe to PATH"** khi cài.
2. **Git for Windows:** https://git-scm.com/download/win
3. **MetaTrader 5:** https://www.metatrader5.com/en/download → cài vào thư mục mặc định
   (`C:\Program Files\MetaTrader 5`; nếu khác thì sửa dòng `MT5_EXE` trong `start_all.bat`).

Node.js không cần, vì giao diện đã được build sẵn trong repo (`web/static/dist`).

## 3. Cấu hình MT5

1. Mở MT5 → **File → Login to Trade Account** → đăng nhập tài khoản **demo** (MetaQuotes-Demo).
   Tick **"Save password"** để MT5 tự đăng nhập khi khởi động lại.
2. **Bật Algo Trading:** nút **Algo Trading** trên thanh công cụ phải màu xanh.
3. **Công cụ → Tùy chọn (Ctrl+O) → Đồ thị → Số bars tối đa trên đồ thị → Unlimited** → OK → tắt và mở lại MT5.
4. Kéo **XAUUSD** vào Market Watch (cửa sổ "Theo dõi thị trường") nếu chưa có.

Bot không bao giờ nhập hay lưu mật khẩu: nó gắn vào terminal đã đăng nhập sẵn.

## 4. Lấy code và cài môi trường

Mở **Command Prompt** (cmd):

```bat
cd C:\
git clone https://github.com/manhleth/goldbot.git
cd goldbot
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m pytest -q
```

Dòng cuối chạy toàn bộ test, phải báo tất cả pass.

## 5. Tải dữ liệu cho bot (một lần, MT5 phải đang mở và đã đăng nhập)

```bat
.venv\Scripts\python main.py history --tf M15 --from 2015-01-01
.venv\Scripts\python main.py feeds --import-calls data\feeds\MJCapitalChannel_calls.json
.venv\Scripts\python main.py feeds --backfill
```

- **Dòng 1:** tải lịch sử M15 từ 2015 vào `cache/XAUUSD_M15_long.csv`, mất khoảng 1–2 phút. Bot dùng file này để trade nháp
  (học kinh nghiệm) và tính xu hướng EMA200 H4. **Thiếu file này thì lớp học không đủ dữ liệu.**
- **Dòng 2:** nạp 274 nhãn nhận định đã đọc từ channel MJ Capital, dùng cho bộ lọc hướng.
- **Dòng 3** (tuỳ chọn, khoảng 11 phút): lấy lại toàn bộ bài channel về database.

**Kiểm tra trước khi chạy thật** (chạy đủ quy trình nhưng không gửi lệnh; Ctrl+C để thoát):

```bat
.venv\Scripts\python main.py bot --name swing --dry-run
```

Log phải hiện "Đã kết nối MT5 DEMO" và dòng "Kinh nghiệm: …".

## 6. Chạy bot

- **Chạy tay:** double-click **`start_all.bat`**. File này:
  1. mở MT5 nếu chưa mở, rồi chờ 60 giây cho MT5 đăng nhập;
  2. chạy giao diện web ẩn (http://localhost:8000);
  3. khởi động 2 bot.
- **Xem và điều khiển:** mở http://localhost:8000 trên VPS. Các nút **Bot swing** / **Bot trong ngày** để bật/tắt, **Kill switch**
  để chặn mọi lệnh mới. Tab **Log** để xem nhật ký từng bot.
- **Dừng:** bấm nút bot trên web. Bot dừng êm, lệnh đang mở vẫn giữ SL trên MT5.

## 7. Tự khởi động khi VPS/máy bật lại

Phải làm cả hai bước, vì MT5 cần một phiên đăng nhập Windows mới chạy được.

**a) Windows tự đăng nhập** (chỉ làm trên VPS/máy riêng, an toàn):
`Win + R` → gõ `netplwiz` → bỏ tick **"Users must enter a user name and password"** → OK → nhập mật khẩu Windows
(bạn tự nhập, mật khẩu được Windows lưu). Nếu không thấy ô tick này thì dùng công cụ **Autologon** của Microsoft Sysinternals.

**b) Task Scheduler chạy `start_all.bat` khi đăng nhập:**
1. `Win + R` → `taskschd.msc` → **Create Task…**
2. **General:**
   - Name: `GoldBot`.
   - Chọn **"Run only when user is logged on"** (MT5 cần màn hình phiên đăng nhập).
3. **Triggers → New:**
   - Begin the task: **At log on**.
   - Delay task for: **1 minute**.
4. **Actions → New:**
   - Program: `C:\goldbot\start_all.bat`.
   - Start in: `C:\goldbot`.
5. **Settings:** bỏ tick **"Stop the task if it runs longer than…"**.

Cách nhanh hơn: `Win + R` → `shell:startup` → tạo shortcut tới `start_all.bat` trong thư mục vừa mở.

## 8. Giữ máy không ngủ và hạn chế khởi động lại

- **Settings → System → Power** (hoặc *Power & sleep*):
  - Screen: tuỳ ý.
  - **Sleep: Never**.
- **Windows Update:** **Settings → Windows Update → Advanced options → Active hours**. Đặt khung giờ thị trường bạn cần bot chạy,
  để Windows không tự khởi động lại trong khung đó.
  - Nhờ bước 7, nếu Windows có khởi động lại thì bot cũng tự chạy lại.
  - Bot tự đồng bộ lệnh đã đóng và quản lý tiếp lệnh đang mở.

## 9. Cập nhật bot khi có code mới

```bat
cd C:\goldbot
.venv\Scripts\python main.py feeds --export-calls data\feeds\MJCapitalChannel_calls.json
git pull
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m pytest -q
```

Lệnh đầu tiên chỉ cần nếu bạn đã ghi nhãn thêm trên máy này. Sau khi cập nhật, dừng 2 bot trên web rồi bật lại
(hoặc chạy lại `start_all.bat`).

## 10. Khi có sự cố

| Hiện tượng | Kiểm tra |
|---|---|
| Web báo "MT5 offline" | MT5 có đang mở và đã đăng nhập không; Algo Trading có xanh không |
| Bot thoát ngay, log báo không phải tài khoản demo | Bot chỉ chạy demo. Đăng nhập lại tài khoản demo trong MT5 |
| Log "Kinh nghiệm: …" có rất ít lệnh nháp | Thiếu `cache/XAUUSD_M15_long.csv` → chạy lại bước 5 |
| Bot không vào lệnh | Tab **Tín hiệu** ghi lý do từng tín hiệu bị bỏ. Mẫu hình H4 hiếm nên vài ngày không có lệnh là bình thường |
| Tắt máy/VPS khi đang có lệnh | SL vẫn nằm trên máy chủ MT5. Nhưng trong lúc tắt, bot không dời SL và không đóng lệnh trong ngày lúc 16:30 NY |

## Lưu ý an toàn

- Bot từ chối chạy khi MT5 đăng nhập **tài khoản thật**.
- Không lưu mật khẩu MT5 vào `config.yaml`. Cũng không cần lưu: bot gắn vào terminal đã đăng nhập.
- Rủi ro đang đặt **5% equity mỗi lệnh** (sửa ở `playbook.yaml`, mục `one_swing` / `one_day`, khoá `risk_pct`).
  Backtest cho thấy mức này có thể cháy tài khoản. Chỉ dùng cho demo.
