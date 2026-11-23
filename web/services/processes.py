"""Chạy bot live / backtest thành tiến trình con `python main.py ...` để giao diện không bị chặn."""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path


def pid_alive(pid: int) -> bool:
    if os.name == "nt":  # os.kill(pid, 0) trên Windows sẽ GIẾT tiến trình → dùng WinAPI
        import ctypes

        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        ok = ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(handle)
        return bool(ok) and code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


class ManagedProcess:
    def __init__(self, name: str, root: Path, config_path: Path) -> None:
        self.name = name
        self._root = root
        self._config_path = config_path
        self._proc: subprocess.Popen | None = None
        self.pid_file = root / "run" / f"{name}.pid"
        self.log_file = root / "logs" / f"{name}.console.log"
        self.started_at: float | None = None

    def _pid(self) -> int | None:
        if self._proc is not None:
            return self._proc.pid
        try:
            return int(self.pid_file.read_text())
        except (OSError, ValueError):
            return None

    def is_running(self) -> bool:
        if self._proc is not None:
            return self._proc.poll() is None
        pid = self._pid()
        return pid is not None and pid_alive(pid)

    def exit_code(self) -> int | None:
        return self._proc.poll() if self._proc is not None else None

    def start(self, args: list[str]) -> None:
        if self.is_running():
            raise RuntimeError(f"{self.name} đang chạy")
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        with open(self.log_file, "w", encoding="utf-8") as log:
            self._proc = subprocess.Popen(
                [sys.executable, str(self._root / "main.py"), "--config", str(self._config_path), *args],
                cwd=self._root, stdout=log, stderr=subprocess.STDOUT, creationflags=flags,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        self.pid_file.write_text(str(self._proc.pid))
        self.started_at = time.time()

    def stop(self, graceful_file: Path | None = None, timeout: float = 15.0) -> None:
        """Tạo file yêu cầu dừng êm (nếu có), chờ tối đa `timeout` giây rồi mới buộc dừng."""
        pid = self._pid()
        if pid is None or not self.is_running():
            return
        if graceful_file is not None:
            graceful_file.parent.mkdir(parents=True, exist_ok=True)
            graceful_file.touch()
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline and self.is_running():
                time.sleep(0.5)
        if self.is_running():
            if self._proc is not None:
                self._proc.kill()
            elif os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, check=False)
            else:
                os.kill(pid, 9)
        self.pid_file.unlink(missing_ok=True)

    def tail(self, lines: int = 200) -> str:
        return tail_file(self.log_file, lines)


def tail_file(path: Path, lines: int) -> str:
    if not path.exists():
        return ""
    with open(path, encoding="utf-8", errors="replace") as fh:
        return "".join(fh.readlines()[-lines:])
