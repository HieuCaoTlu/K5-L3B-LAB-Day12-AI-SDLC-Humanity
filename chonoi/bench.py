"""Benchmark CÓ RENDER (Ticket-04, contract v1.3): đo FPS cảnh lặn thật trong trình duyệt.

    python3 -m chonoi.bench --seed 42 --duration 30 --out bench.json

Cảnh đo: buổi sáng lõi (độ tươi, cá bơi, Cá Sấu, hiệu ứng mặc định), Út Sen đứng yên ở bến, cửa sổ 1280x720.
Cách chạy: bật server `chonoi.live` (cùng sim với headless) ở cổng ngẫu nhiên, mở Chrome/Chromium/Edge ở chế độ headless
tới `/?bench=<s>&warmup=3&t0=<ms>`; trang tự đo thời gian từng khung (requestAnimationFrame), làm nóng 3 s, đo <s> giây,
rồi POST kết quả về `/bench`. Trình duyệt: biến môi trường CHONOI_BROWSER, hoặc tự tìm (google-chrome, chromium, Edge...).

bench.json: frames, measured_s (khung và giây thực đo sau làm nóng), avg_fps = frames / measured_s,
p1_low_fps = 1 / (thời gian trung bình của max(1, ceil(1% * frames)) khung chậm nhất, tính bằng giây),
load_ms = mili giây từ lúc khởi chạy lệnh tới khung đầu tiên của cảnh đo.
Mã thoát: 0 xong, 2 cờ sai, 1 không tìm thấy trình duyệt / quá thời gian / không ghi được file.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer

from .contract import load_contract
from .errors import BadInput
from .live import LiveGame, _Handler

WARMUP_S = 3
WINDOW = (1280, 720)
_CANDIDATES = [
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "msedge", "chrome",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def find_browser():
    env = os.environ.get("CHONOI_BROWSER")
    for c in ([env] if env else []) + _CANDIDATES:
        path = shutil.which(c) or (c if os.path.isfile(c) else None)
        if path:
            return path
    return None


class _BenchHandler(_Handler):
    result = None            # gán trên lớp con: dict chứa {"data": ..., "event": threading.Event}

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/bench":
            return super().do_POST()
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n).decode("utf-8")) if 0 < n <= 4_000_000 else None
            if not isinstance(body, dict):
                raise ValueError("body sai")
        except (ValueError, UnicodeDecodeError):
            self._send(400, b'{"error":"body sai"}')
            return
        self.result["data"] = body
        self.result["event"].set()
        self._send(200, b'{"ok":true}')


def compute(frame_ms, load_ms):
    """Tính 5 trường từ danh sách thời gian khung (mili giây) trong khoảng đo."""
    frames = len(frame_ms)
    measured_s = sum(frame_ms) / 1000.0
    k = max(1, -(-frames // 100))                       # ceil(0.01 * frames)
    slowest = sorted(frame_ms, reverse=True)[:k]
    p1 = 1.0 / (sum(slowest) / len(slowest) / 1000.0) if slowest and sum(slowest) > 0 else 0.0
    return {"avg_fps": round(frames / measured_s, 2) if measured_s > 0 else 0.0, "p1_low_fps": round(p1, 2),
            "frames": frames, "measured_s": round(measured_s, 3), "load_ms": int(round(load_ms))}


class _QuietServer(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):   # trình duyệt bị tắt giữa chừng -> kết nối reset: không phải lỗi bench
        if not isinstance(sys.exc_info()[1], (ConnectionResetError, BrokenPipeError, ConnectionAbortedError)):
            super().handle_error(request, client_address)


def run_bench(seed, duration, out):
    t_start_ms = time.time() * 1000.0                   # mốc "khởi chạy" cho load_ms
    browser = find_browser()
    if not browser:
        raise RuntimeError("không tìm thấy Chrome/Chromium/Edge; đặt biến CHONOI_BROWSER=<đường dẫn trình duyệt>")
    tuning = load_contract()["tuning"]
    game = LiveGame("gather", tuning, {}, seed)         # buổi sáng lõi: cá bơi, Cá Sấu, độ tươi theo contract
    result = {"data": None, "event": threading.Event()}
    handler = type("BenchHandler", (_BenchHandler,), {"game": game, "result": result})
    httpd = _QuietServer(("127.0.0.1", 0), handler)
    game.start()
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = (f"http://127.0.0.1:{httpd.server_address[1]}/?bench={duration}&warmup={WARMUP_S}"
           f"&t0={int(t_start_ms)}")
    profile = tempfile.mkdtemp(prefix="chonoi-bench-")
    proc = subprocess.Popen([browser, "--headless=new", f"--window-size={WINDOW[0]},{WINDOW[1]}", "--mute-audio",
                             "--no-first-run", "--no-default-browser-check", "--disable-extensions",
                             "--disable-background-timer-throttling", "--disable-renderer-backgrounding",
                             f"--user-data-dir={profile}", url],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        if not result["event"].wait(timeout=WARMUP_S + duration + 60):
            raise RuntimeError("quá thời gian chờ kết quả từ trình duyệt")
    finally:
        proc.kill()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        httpd.shutdown()
        httpd.server_close()
        game.stop()
        shutil.rmtree(profile, ignore_errors=True)
    d = result["data"]
    report = compute([float(x) for x in d.get("frame_ms", [])], float(d.get("load_ms", 0)))
    tmp = out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False)
    os.replace(tmp, out)
    return report


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="chonoi.bench", description="Benchmark có render cảnh lặn (Ticket-04).")
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--duration", type=float, required=True, help="số giây đo sau 3 s làm nóng")
    p.add_argument("--out", required=True)
    try:
        a = p.parse_args(argv)
    except SystemExit as e:
        return 2 if e.code else 0
    if not (a.duration > 0):
        sys.stderr.write("đầu vào sai: --duration phải dương\n")
        return 2
    try:
        r = run_bench(a.seed, a.duration, a.out)
    except (RuntimeError, OSError, BadInput) as e:
        sys.stderr.write(f"bench lỗi: {e}\n")
        return 1
    print(f"bench: avg {r['avg_fps']} FPS · 1% low {r['p1_low_fps']} FPS · {r['frames']} khung / {r['measured_s']} s"
          f" · load {r['load_ms']} ms -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
