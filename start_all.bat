@echo off
rem Khởi động toàn bộ GoldBot: MT5 terminal -> giao diện web (nền) -> 2 bot ONE.
rem Dùng cho Task Scheduler "At log on" hoặc thư mục Startup. Đường dẫn MT5 đổi ở dòng MT5_EXE nếu cài chỗ khác.
cd /d "%~dp0"
chcp 65001 >nul
set "MT5_EXE=C:\Program Files\MetaTrader 5\terminal64.exe"

tasklist /FI "IMAGENAME eq terminal64.exe" | find /I "terminal64.exe" >nul
if errorlevel 1 (
  echo Mo MT5...
  start "" "%MT5_EXE%"
  rem cho MT5 dang nhap tai khoan demo va tai du lieu
  timeout /t 60 /nobreak >nul
)

echo Mo giao dien web (http://localhost:8000)...
start "GoldBot web" /min ".venv\Scripts\python.exe" main.py web --no-browser

echo Khoi dong 2 bot ONE...
".venv\Scripts\python.exe" main.py start-bots
timeout /t 5 /nobreak >nul
