@echo off
rem Khởi động lại giao diện web (vd sau khi cập nhật code). KHÔNG ảnh hưởng 2 bot (tiến trình riêng).
cd /d "%~dp0"
chcp 65001 >nul
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000 " ^| findstr LISTENING') do (
  echo Tat web cu (pid %%p)...
  taskkill /F /PID %%p >nul 2>&1
)
echo Mo web moi...
start "GoldBot web" /min ".venv\Scripts\python.exe" main.py web --no-browser
timeout /t 6 /nobreak >nul
start "" http://localhost:8000
