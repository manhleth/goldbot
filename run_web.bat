@echo off
rem Mở giao diện web GoldBot (double-click file này). Đóng cửa sổ này = tắt giao diện.
cd /d "%~dp0"
chcp 65001 >nul
".venv\Scripts\python.exe" main.py web
pause
