"""Cửa sổ chơi trực tiếp bằng TRÌNH DUYỆT, chỉ dùng thư viện chuẩn Python.

    python3 -m chonoi.live --mode gather|quan [--seed N] [--port 8000]

Máy chủ HTTP nhỏ (ThreadingHTTPServer) phục vụ `chonoi/web/index.html` và hai API:
    GET  /state  -> snapshot JSON hiện tại (cùng trường như dòng snapshot của headless) + `meta` + `events`
    POST /input  -> {"move": [a, b], "interact": bool, "catch": bool}   (trạng thái phím đang giữ)
    POST /restart -> chơi lại từ đầu (cùng seed, cùng scenario)

Mô phỏng chạy 60 tick/s trong một luồng nền, dùng CÙNG lớp sim như headless (qua `runner.Session`).
Client chỉ ĐỌC snapshot và tự bỏ qua trường chưa có, nên luật do nhóm viết thêm trường nào cũng không vỡ.
Ngẫu nhiên vẫn đi qua `Streams` (seed); chỉ nhịp chạy theo đồng hồ thật, không đi vào luật.
"""

import argparse
import json
import os
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote

from .contract import load_contract
from .errors import BadInput
from .extras import START_MONEY, build_tuning
from .inputs import LiveInputs
from .inventory import read_inventory
from .runner import Session
from .scenario import load_scenario

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
TICK_S = 1.0 / 60.0
MAX_BODY = 4096
RECENT_EVENTS = 40
_ASSET_TYPES = {".png": "image/png", ".wav": "audio/wav", ".json": "application/json", ".gif": "image/gif"}


def _as_items(s, start=1):
    """Kho (dict đếm hoặc list cá thể) -> list cá thể {id, kind, fresh}; kho đếm cấp id I<start>, I<start+1>..."""
    if isinstance(s, list):
        return [dict(x) for x in s]
    out, n = [], start
    for kind in sorted(s or {}):
        for _ in range(int(s[kind])):
            out.append({"id": f"I{n}", "kind": kind, "fresh": 100})
            n += 1
    return out


def _merge_stock(left, gathered):
    """Kho dư của quán + hàng vừa gom được (dict đếm từ buổi sáng) -> list cá thể, id mới nối tiếp, tươi 100."""
    items = _as_items(left)
    top = 0
    for it in items:
        tail = "".join(ch for ch in it["id"] if ch.isdigit())
        top = max(top, int(tail) if tail else 0)
    return items + _as_items(gathered, top + 1)


def _clone_stock(s):
    """Kho (dict đếm v1.1 hoặc list cá thể v1.2) -> bản sao độc lập."""
    return [dict(x) for x in s] if isinstance(s, list) else dict(s or {})


class LiveGame:
    """Một lượt chơi + luồng nền bước 60 tick/s. Mọi truy cập trạng thái đi qua khóa."""

    def __init__(self, mode, tuning, scenario, seed, inventory=None, inventory_out=None, debug_stock=False,
                 extras=False, day=1):
        self.debug_stock = debug_stock
        self.extras = bool(extras) and mode == "quan"  # phần sáng tạo: nhiều ngày, 6 bàn, ông bán hàng... (xem extras.py)
        self.mode = mode
        self.base_tuning = tuning
        self.tuning = tuning
        self._scenario = scenario
        self._seed = seed
        self._inventory = inventory
        self._start_day = day
        self.inventory_out = inventory_out
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._ver = 0          # tăng mỗi khi trạng thái đổi -> dùng lại JSON đã dựng cho các lần poll trong cùng tick
        self._cache = (-1, b"")
        self._after = 0        # số tick đã chờ sau khi buổi sáng kết thúc, trước khi tự sang quán
        self._new_carry()
        self._reset()

    def _new_carry(self):
        """Trạng thái đầu ngày (nhiều ngày: tiền, kho, uy tín chuyển sang ngày sau)."""
        self._carry = {"day": self._start_day, "money": START_MONEY, "stock": _clone_stock(self._inventory), "rep": None, "upgrades": {},
                       "phase": "quan"}   # chu kỳ ngày: bắt đầu ở quán; sang ngày mới thì bắt cá (gather) rồi tự sang quán

    def _reset(self):
        if self.extras:
            c = self._carry
            self.mode = c.get("phase", "quan")
            self.tuning = build_tuning(self.base_tuning, c["day"], c["money"])
            if self.mode == "gather":
                self._args = ("gather", self.tuning, {"day": c["day"]}, self._seed + c["day"] - 1, None)
            else:
                scen = dict(self._scenario)
                if c["rep"] is not None:
                    scen.setdefault("reputation", c["rep"])
                scen["upgrades"] = dict(c.get("upgrades", {}))
                self._args = ("quan", self.tuning, scen, self._seed + c["day"] - 1, _clone_stock(c["stock"]))
        else:
            self._args = (self.mode, self.tuning, self._scenario, self._seed, self._inventory)
        self.session = Session(*self._args, creative=True)
        if self.debug_stock and self.mode == "quan":
            self.session.sim.debug_full_stock = True
        self._after = 0
        self._ver += 1
        self.inputs = LiveInputs(buttons=("interact", "catch", "sprint", "end_gather"))
        self.events = []
        self._saved = False
        self.error = None

    # --- luồng nền ----------------------------------------------------------------
    def start(self):
        self._thread = threading.Thread(target=self._loop, name="chonoi-sim", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _loop(self):
        nxt = time.perf_counter()
        while not self._stop.is_set():
            nxt += TICK_S
            with self._lock:
                try:
                    self._tick_once()
                except Exception:  # luật của nhóm lỗi: báo ra terminal + client, dừng bước (restart để chơi lại)
                    self.error = traceback.format_exc()
                    sys.stderr.write(self.error)
                    self.session.sim.done = True
                    self.session.sim.reason = "error"
            delay = nxt - time.perf_counter()
            if delay > 0:
                self._stop.wait(delay)
            elif delay < -0.25:  # chạy chậm quá thì bỏ bù, tránh chạy dồn
                nxt = time.perf_counter()

    def _tick_once(self):
        s = self.session
        if s.done:
            if self.extras and self.mode == "gather" and not self.error and s.sim.reason != "error":
                self._after += 1                       # cho người chơi thấy màn kết thúc buổi sáng ~1.5 s rồi sang quán
                if self._after >= 90:
                    self._enter_quan()
            return
        for row in s.step(self.inputs.advance()):
            self.events.append(row)
        del self.events[:-RECENT_EVENTS]
        self._ver += 1
        if s.done and not self._saved:
            self._saved = True
            if self.inventory_out:
                try:
                    s.write_inventory_if_done(self.inventory_out)
                except OSError as e:
                    sys.stderr.write(f"lỗi ghi kho: {e}\n")

    def _enter_quan(self):
        """Hết buổi sáng: hàng gom được (kể cả rỗng nếu ngất) nhập vào kho quán cùng kho dư, rồi mở quán."""
        gathered = self.session.sim.inventory_items() if hasattr(self.session.sim, "inventory_items") else {}
        self._carry["stock"] = _merge_stock(self._carry["stock"], gathered)
        self._carry["phase"] = "quan"
        self._reset()

    # --- API cho handler -----------------------------------------------------------
    def state_json(self) -> bytes:
        with self._lock:
            if self._cache[0] == self._ver:
                return self._cache[1]
            snap = self.session.snapshot()
            snap["meta"] = self.tuning[self.mode]
            snap["events"] = list(self.events)
            snap["finished"] = self.session.done
            snap["reason"] = self.session.sim.reason if self.session.done else None
            snap["error"] = self.error
            if self.extras:
                snap["day"] = self._carry["day"]
            body = json.dumps(snap, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self._cache = (self._ver, body)
            return body

    def set_input(self, body: dict):
        move = body.get("move")
        if move is not None:
            ok = (isinstance(move, list) and len(move) == 2 and
                  all(isinstance(c, (int, float)) and not isinstance(c, bool) and abs(c) <= 1 for c in move))
            if not ok:
                raise ValueError("move phải là [a, b] trong [-1, 1]")
        buttons = {}
        for b in ("interact", "catch", "sprint", "end_gather"):
            if b in body:
                if not isinstance(body[b], bool):
                    raise ValueError(f"{b} phải là boolean")
                buttons[b] = body[b]
        with self._lock:
            self.inputs.set(move, **buttons)

    def restart(self, new_game=False, next_day=False):
        with self._lock:
            if self.extras:
                sim = self.session.sim
                if new_game:
                    self._new_carry()
                elif next_day and self.mode == "quan" and self.session.done and sim.reason == "time":
                    self._carry = {"day": self._carry["day"] + 1, "money": sim.money,   # sang ngày kế: bắt cá trước, rồi tự sang quán
                                   "stock": sim.carry_items(), "rep": sim.reputation,
                                   "upgrades": dict(sim.up), "phase": "gather"}
            self._reset()

    def upgrade(self, key):
        """Mua nâng cấp nhân vật (chỉ chế độ quán sáng tạo)."""
        with self._lock:
            ev = self.session.sim.upgrade(key) if hasattr(self.session.sim, "upgrade") else None
            if ev is None:
                raise ValueError("không nâng cấp được mục này")
            self.events.append({"type": "event", "tick": self.session.tick, "phase": self.session.sim.phase,
                                "name": ev[0], "data": ev[1]})
            del self.events[:-RECENT_EVENTS]
            self._ver += 1

    def buy(self, item):
        """Mua nguyên liệu từ ông bán hàng (chỉ chế độ quán sáng tạo)."""
        with self._lock:
            ev = self.session.sim.buy(item) if hasattr(self.session.sim, "buy") else None
            if ev is None:
                raise ValueError("không mua được món này")
            self.events.append({"type": "event", "tick": self.session.tick, "phase": self.session.sim.phase,
                                "name": ev[0], "data": ev[1]})
            del self.events[:-RECENT_EVENTS]
            self._ver += 1


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    game: LiveGame = None  # gán trên lớp con trong make_server

    def log_message(self, fmt, *args):  # yên lặng
        pass

    def _send(self, code, body: bytes, ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/state":
            self._send(200, self.game.state_json())
        elif path in ("/", "/index.html"):
            try:
                with open(os.path.join(WEB_DIR, "index.html"), "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except OSError:
                self._send(404, b'{"error":"thieu index.html"}')
        elif path.startswith("/assets/"):
            self._send_asset(path[len("/assets/"):])
        else:
            self._send(404, b'{"error":"khong co"}')

    def _send_asset(self, rel):
        """Phục vụ file tĩnh trong web/assets (ảnh, âm thanh, manifest); chặn thoát khỏi thư mục."""
        root = os.path.realpath(os.path.join(WEB_DIR, "assets"))
        full = os.path.realpath(os.path.join(root, unquote(rel)))
        ctype = _ASSET_TYPES.get(os.path.splitext(full)[1].lower())
        if ctype is None or os.path.commonpath([root, full]) != root or not os.path.isfile(full):
            self._send(404, b'{"error":"khong co"}')
            return
        with open(full, "rb") as f:
            self._send(200, f.read(), ctype)

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = -1
        if n < 0 or n > MAX_BODY:
            self._send(400, b'{"error":"body sai"}')
            return
        raw = self.rfile.read(n) if n else b""
        try:
            if path == "/input":
                body = json.loads(raw.decode("utf-8") or "{}")
                if not isinstance(body, dict):
                    raise ValueError("body phải là object")
                self.game.set_input(body)
            elif path == "/buy":
                body = json.loads(raw.decode("utf-8") or "{}")
                if not isinstance(body, dict) or not isinstance(body.get("item"), str):
                    raise ValueError("body phải có item (chuỗi)")
                self.game.buy(body["item"])
            elif path == "/upgrade":
                body = json.loads(raw.decode("utf-8") or "{}")
                if not isinstance(body, dict) or not isinstance(body.get("key"), str):
                    raise ValueError("body phải có key (chuỗi)")
                self.game.upgrade(body["key"])
            elif path == "/restart":
                body = json.loads(raw.decode("utf-8") or "{}") if raw else {}
                ok = isinstance(body, dict)
                self.game.restart(new_game=ok and body.get("new") is True, next_day=ok and body.get("next") is True)
            else:
                self._send(404, b'{"error":"khong co"}')
                return
        except (ValueError, UnicodeDecodeError) as e:
            self._send(400, json.dumps({"error": str(e)}).encode("utf-8"))
            return
        self._send(200, b'{"ok":true}')


class LiveServer:
    """Máy chủ + mô phỏng. port=0 -> cổng ngẫu nhiên (đọc `.port`)."""

    def __init__(self, game: LiveGame, host="127.0.0.1", port=8000):
        handler = type("Handler", (_Handler,), {"game": game})
        self.game = game
        self.httpd = ThreadingHTTPServer((host, port), handler)
        self.httpd.daemon_threads = True
        self.host = host
        self.port = self.httpd.server_address[1]
        self._thread = None

    @property
    def url(self):
        return f"http://{self.host}:{self.port}/"

    def start(self):
        self.game.start()
        self._thread = threading.Thread(target=self.httpd.serve_forever, name="chonoi-http", daemon=True)
        self._thread.start()

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        if self._thread:
            self._thread.join(timeout=2)
        self.game.stop()


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="chonoi.live", description="Chơi trực tiếp trên trình duyệt (starter).")
    p.add_argument("--mode", required=True, choices=["gather", "quan"])
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--port", type=int, default=8000, help="0 = cổng ngẫu nhiên")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--scenario")
    p.add_argument("--inventory", help="chỉ với quan: nạp kho từ file")
    p.add_argument("--inventory-out", dest="inventory_out", help="chỉ với gather: ghi kho khi kết thúc buổi")
    p.add_argument("--debug-stock", dest="debug_stock", action="store_true",
                   help="chỉ với quan: luôn đầy nguyên liệu (debug)")
    p.add_argument("--classic", action="store_true",
                   help="chỉ với quan: tắt phần sáng tạo (1 bếp, 1 bàn, đúng số liệu contract)")
    p.add_argument("--day", type=int, default=1, help="chỉ với quan sáng tạo: ngày bắt đầu (độ khó tăng theo ngày)")
    a = p.parse_args(argv)
    try:
        if a.inventory and a.mode != "quan":
            raise BadInput("--inventory chỉ dùng với quan")
        if a.inventory_out and a.mode != "gather":
            raise BadInput("--inventory-out chỉ dùng với gather")
        if a.debug_stock and a.mode != "quan":
            raise BadInput("--debug-stock chỉ dùng với quan")
        tuning = load_contract()["tuning"]
        scenario = load_scenario(a.scenario, a.mode, tuning)
        inventory = read_inventory(a.inventory, fresh="freshness" in tuning) if a.inventory else None
        if inventory is not None and "stock" in scenario:
            raise BadInput("vừa có quan.stock vừa có --inventory")
        game = LiveGame(a.mode, tuning, scenario, a.seed, inventory, a.inventory_out, a.debug_stock,
                        extras=(a.mode == "quan" and not a.classic), day=max(1, a.day))
        server = LiveServer(game, a.host, a.port)
    except BadInput as e:
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2
    except OSError as e:
        sys.stderr.write(f"không mở được cổng {a.port}: {e}\n")
        return 1
    server.start()
    print(f"Mở trình duyệt tại {server.url}  (chế độ {a.mode}, seed {a.seed}). Ctrl+C để dừng.", flush=True)
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
