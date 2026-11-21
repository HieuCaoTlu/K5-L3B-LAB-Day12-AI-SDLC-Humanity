"""Buổi tối — Mở Quán. Bản chơi thử: khách, bếp, bưng món, trả tiền, boa, uy tín.

GIẢ ĐỊNH (chưa đối chiếu PRD-0 mục F; sửa lại khi có PRD): khách đến khi có bàn trống và đủ nguyên liệu
cho ít nhất một món (giữ chỗ nguyên liệu ngay), nguyên liệu bị trừ khi bắt đầu nấu món đó, kiên nhẫn chỉ
giảm khi chờ, khách bỏ đi nếu hết kiên nhẫn (món đang nấu cho họ bị bỏ), trả tiền khi ăn xong; boa nếu còn
đủ tỉ lệ kiên nhẫn lúc được phục vụ nốt món cuối.

Tính năng sáng tạo (chỉ bật khi số liệu có `vendor` / `serves` / `max_dishes`, tức là ở chonoi.live; headless
dùng game.contract.json nên không có): mỗi bếp một món (`serves`), khách đòi nhiều món, ông bán nguyên liệu.
"""

import math

from ..ids import id_key, sort_by_id
from .ramp import ramp_velocity

TICK = 60.0
STOCK_KINDS = ("ca_loc", "ca_linh", "bong_dien_dien", "bong_sung", "coca")


class QuanSim:
    mode = "quan"
    phase = "quan"

    def __init__(self, tuning, scenario, streams, ids, inventory=None):
        t = tuning["quan"]
        self.t = t
        self.menu = tuning["menu"]
        self.rng = streams
        self.ids = ids
        p = scenario.get("player", {})
        self.pos = list(p.get("pos", t["start_pos"]))
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0
        # kho: --inventory HOẶC scenario.stock (cả hai -> cli đã báo mã 2)
        self.stock = dict(inventory if inventory is not None else scenario.get("stock", {}))
        h0 = scenario.get("hand")  # khay bưng: danh sách món đang cầm (mặc định chỉ cầm được 1)
        self.tray = [] if not h0 else [h0 if isinstance(h0, dict) else {"dish_id": h0, "customer_id": None, "order": None}]
        self.upg_cfg = t.get("upgrades", {})
        lv = scenario.get("upgrades", {})
        self.up = {k: int(lv.get(k, 0)) for k in self.upg_cfg}
        self.time_left_ticks = scenario.get("time_left_ticks", int(round(t["duration_s"] * 60)))
        self.reputation = scenario.get("reputation", t["reputation_initial"])
        self.stoves = [dict(s, state=s.get("state", "idle"), dish=s.get("dish"),
                            cook_ticks_left=s.get("cook_ticks_left", 0), ready_ticks=s.get("ready_ticks", 0))
                       for s in self._merge(t["stoves"], scenario.get("stoves", []))]
        for s in self.stoves:
            s["jobs"] = list(s.get("jobs") or ([{"customer_id": s["customer_id"], "order": s.get("order")}]
                                               if s.get("customer_id") else []))
        self.tables = self._merge(t["tables"], scenario.get("tables", []))
        self.patience_max = int(round(t["patience_s"] * TICK))
        self.eat_max = int(round(t["eat_s"] * TICK))
        self.max_dishes = t.get("max_dishes", 1)
        self.vendor = t.get("vendor")
        self.customers = [self._customer_from_scenario(c) for c in scenario.get("customers", [])]
        for e in self.customers:
            ids.reserve(e["id"])
        self.random_customers = scenario.get("random_customers", True)
        self.debug_full_stock = False  # chỉ bật từ chonoi.live --debug-stock, headless không dùng
        self.money = t.get("start_money", 0)
        self.earned = 0
        self.shift_earned = 0
        self._elapsed = 0
        self.done = False
        self.reason = None

    def _customer_from_scenario(self, c):
        c = dict(c)
        state = c.get("state", "waiting")
        orders = c.get("orders")
        if orders is None:
            orders = ([{"dish_id": c["dish_id"], "state": "served" if state == "eating" else "pending"}]
                      if c.get("dish_id") else [])
        c["orders"] = [dict(o) for o in orders]
        c["state"] = state
        c.setdefault("patience_max", self.patience_max)
        c.setdefault("patience_ticks_left", c["patience_max"])
        if state == "eating":
            c.setdefault("eat_ticks_left", self.eat_max)
        c.setdefault("tip_ok", False)
        return c

    @staticmethod
    def _merge(defaults, updates):
        by_id = {d["id"]: dict(d) for d in defaults}
        for u in updates:
            if u["id"] not in by_id:
                from ..errors import BadInput
                raise BadInput(f"id bếp/bàn không tồn tại: {u['id']}")
            by_id[u["id"]].update(u)
        return sort_by_id(list(by_id.values()))

    # --- snapshot -------------------------------------------------------------
    def _reserved_of(self, c):
        res = {}
        for o in c["orders"]:
            if o["state"] == "pending":
                for k, n in self.menu[o["dish_id"]]["recipe"].items():
                    res[k] = res.get(k, 0) + n
        return res

    def _customer_view(self, c):
        v = {"id": c["id"], "table_id": c["table_id"], "state": c["state"],
             "dish_id": c["orders"][0]["dish_id"] if c["orders"] else None,
             "patience_ticks_left": c["patience_ticks_left"], "reserved": self._reserved_of(c)}
        if c["state"] == "eating":
            v["eat_ticks_left"] = c["eat_ticks_left"]
        if self.vendor is not None:  # phần sáng tạo
            v["orders"] = [dict(o) for o in c["orders"]]
            v["patience_max"] = c["patience_max"]
        return v

    def snapshot(self) -> dict:
        occupied = {c["table_id"]: c["id"] for c in self.customers}
        keys = ("id", "pos", "state", "dish", "cook_ticks_left", "ready_ticks")
        stoves = []
        for s in self.stoves:
            d = {k: s.get(k) for k in keys}
            if "serves" in s:  # phần sáng tạo
                d["serves"] = s["serves"]
                d["recipe"] = self.menu[s["serves"]]["recipe"]
                d["customer_id"] = s["jobs"][0]["customer_id"] if s["jobs"] else None
                d["jobs"] = len(s["jobs"])
                d["batch"] = self.batch
            stoves.append(d)
        snap = {
            "player": {"pos": self.pos},
            "stock": {k: self.stock[k] for k in sorted(self.stock) if self.stock[k] > 0},
            "hand": self.tray[0] if self.tray else None,
            "stoves": stoves,
            "tables": [{"id": tb["id"], "pos": tb["pos"], "customer_id": occupied.get(tb["id"])} for tb in self.tables],
            "customers": [self._customer_view(c) for c in sort_by_id(self.customers)],
        }
        if self.vendor is not None:
            first = self.t["first_customer_tick"]
            every = self._every()
            nxt = first - self._elapsed if self._elapsed < first else every - (self._elapsed - first) % every
            snap["vendor"] = self.vendor
            snap["next_customer_ticks"] = nxt
            snap["customer_interval_ticks"] = every
            snap["menu_prices"] = {k: v["price"] for k, v in self.menu.items()}
            snap["max_dishes"] = self.max_dishes
            snap["tray"] = [dict(x) for x in self.tray]
            snap["carry_limit"] = self.carry_limit
            snap["upgrades"] = [{"key": k, "name": c["name"], "emoji": c["emoji"], "desc": c["desc"],
                                 "level": self.up[k], "max": len(c["costs"]),
                                 "next_cost": c["costs"][self.up[k]] if self.up[k] < len(c["costs"]) else None}
                                for k, c in self.upg_cfg.items()]
        return snap

    # --- nâng cấp (phần sáng tạo) ---------------------------------------------
    def _lv(self, key):
        return self.up.get(key, 0)

    @property
    def carry_limit(self):
        return self.t.get("carry_limit", 1) + self._lv("carry")

    @property
    def batch(self):
        return 1 + self._lv("batch")

    def upgrade(self, key):
        """Mua một cấp nâng cấp bằng tiền. Trả (tên_sự_kiện, data) hoặc None nếu key sai / đã tối đa."""
        c = self.upg_cfg.get(key)
        if c is None or self.done or self.up[key] >= len(c["costs"]):
            return None
        cost = c["costs"][self.up[key]]
        if self.money < cost:
            return ("upgrade_failed", {"key": key, "cost": cost, "reason": "no_money"})
        self.money -= cost
        self.up[key] += 1
        return ("upgraded", {"key": key, "level": self.up[key], "cost": cost})

    # --- một bước -------------------------------------------------------------
    def step(self, inp):
        events = []
        if self.debug_full_stock:
            for k in STOCK_KINDS:
                self.stock[k] = max(self.stock.get(k, 0), 99)
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        self._elapsed = int(round(self.t["duration_s"] * TICK)) - self.time_left_ticks  # số tick đã chạy
        self._tick_stoves(events)
        self._tick_customers(events)
        self._move(inp)
        if inp.pressed("interact"):
            self._interact(events)
        if self.random_customers:
            self._maybe_spawn(events)
        if self._lv("auto") > 0:  # nâng cấp: món tự nấu ngay khi có khách gọi
            for st in self.stoves:
                if st["state"] == "idle" and st.get("serves"):
                    self._try_start(st, events)
        if self.time_left_ticks <= 0:
            self.done = True
            self.reason = "time"
            events.append(("quan_end", {"reason": "time", "money": self.money, "earned": self.earned,
                                        "shift_earned": self.shift_earned, "reputation": self.reputation}))
        return events

    def buy(self, kind):
        """Mua 1 phần nguyên liệu từ ông bán hàng (chỉ khi có vendor). Trả (tên_sự_kiện, data) hoặc None."""
        v = self.vendor
        if v is None or self.done or kind not in v["prices"]:
            return None
        price = v["prices"][kind]
        if self.money < price:
            return ("buy_failed", {"item": kind, "price": price, "reason": "no_money"})
        self.money -= price
        self.stock[kind] = self.stock.get(kind, 0) + 1
        return ("bought", {"item": kind, "price": price})

    # --- khách / bếp -----------------------------------------------------------
    def _every(self):
        return int(round(self.t["customer_interval_s"] * TICK))

    def _reserved_total(self):
        tot = {}
        for c in self.customers:
            for k, n in self._reserved_of(c).items():
                tot[k] = tot.get(k, 0) + n
        return tot

    def _pick_orders(self, n):
        """Chọn tối đa n món còn nấu được (tính cả phần đã giữ chỗ và các món vừa chọn)."""
        res = self._reserved_total()
        picked = []
        for _ in range(n):
            options = [name for name in sorted(self.menu)
                       if all(self.stock.get(k, 0) - res.get(k, 0) >= q for k, q in self.menu[name]["recipe"].items())]
            if not options:
                break
            d = options[int(self.rng.get("customer_dish").random() * len(options)) % len(options)]
            picked.append(d)
            for k, q in self.menu[d]["recipe"].items():
                res[k] = res.get(k, 0) + q
        return picked

    def _adjust_rep(self, delta):
        self.reputation = min(self.t["reputation_max"], max(self.t["reputation_min"], self.reputation + delta))

    def _maybe_spawn(self, events):
        first = self.t["first_customer_tick"]
        every = self._every()
        if self._elapsed < first or (self._elapsed - first) % every != 0:
            return
        busy = {c["table_id"] for c in self.customers}
        free = [tb for tb in self.tables if tb["id"] not in busy]
        if not free:
            return
        cid = self.ids.new("C")
        want = 1 + int(self.rng.get("customer_size").random() * self.max_dishes) % self.max_dishes
        dishes = self._pick_orders(want)
        if not dishes:
            events.append(("no_dish", {"customer_id": cid}))
            return
        pmax = int(self.patience_max * (1 + 0.5 * (len(dishes) - 1)))
        self.customers.append({"id": cid, "table_id": free[0]["id"], "state": "waiting",
                               "orders": [{"dish_id": d, "state": "pending"} for d in dishes],
                               "patience_ticks_left": pmax, "patience_max": pmax, "tip_ok": False})
        events.append(("customer_arrived", {"customer_id": cid, "table_id": free[0]["id"], "dishes": dishes}))

    def _tick_stoves(self, events):
        for st in self.stoves:
            if st["state"] == "cooking":
                st["cook_ticks_left"] -= 1
                if st["cook_ticks_left"] <= 0:
                    st["cook_ticks_left"] = 0
                    st["state"] = "ready"
                    events.append(("dish_ready", {"stove_id": st["id"], "dish_id": st["dish"]}))
            elif st["state"] == "ready":
                st["ready_ticks"] += 1

    def _customer_gone(self, c, events):
        """Khách bỏ đi: bỏ các món đang nấu / đang cầm cho họ."""
        for st in self.stoves:
            mine = [j for j in st["jobs"] if j["customer_id"] == c["id"]]
            if not mine or st["state"] not in ("cooking", "ready"):
                continue
            for _ in mine:
                events.append(("dish_wasted", {"stove_id": st["id"], "dish_id": st["dish"]}))
            st["jobs"] = [j for j in st["jobs"] if j["customer_id"] != c["id"]]
            if not st["jobs"]:
                st.update(state="idle", dish=None, cook_ticks_left=0, ready_ticks=0)
        for it in [x for x in self.tray if x.get("customer_id") == c["id"]]:
            events.append(("dish_wasted", {"stove_id": None, "dish_id": it.get("dish_id")}))
            self.tray.remove(it)

    def _tick_customers(self, events):
        for c in sort_by_id(self.customers):
            if c["state"] == "waiting":
                c["patience_ticks_left"] -= 1
                if c["patience_ticks_left"] <= 0:
                    self.customers.remove(c)
                    self._customer_gone(c, events)
                    self._adjust_rep(self.t["left_reputation_delta"])
                    events.append(("customer_left", {"customer_id": c["id"], "reputation": self.reputation}))
            elif c["state"] == "eating":
                c["eat_ticks_left"] -= 1
                if c["eat_ticks_left"] <= 0:
                    price = int(round(sum(self.menu[o["dish_id"]]["price"] for o in c["orders"])
                                      * (1 + 0.15 * self._lv("tasty"))))
                    tip = int(round(price * self.t["tip_rate"])) if c["tip_ok"] else 0
                    if tip:
                        self._adjust_rep(self.t["tip_reputation"])
                    self.money += price + tip
                    self.earned += price + tip
                    self.shift_earned += price + tip
                    self.customers.remove(c)
                    events.append(("paid", {"customer_id": c["id"], "price": price, "tip": tip}))

    def _interact(self, events):
        r = self.t["interact_radius"]
        cands = []
        for kind, order, arr in (("stove", 0, self.stoves), ("table", 1, self.tables)):
            for e in arr:
                d = math.dist(self.pos, e["pos"])
                if d <= r:
                    cands.append((d, order, id_key(e["id"]), kind, e))
        if not cands:
            return
        _, _, _, kind, e = min(cands, key=lambda c: c[:3])
        if kind == "stove":
            self._use_stove(e, events)
        else:
            self._use_table(e, events)

    def _try_start(self, e, events):
        """Bếp rảnh: nấu cho các món đang chờ (tối đa `batch` phần cùng một món, cùng lúc)."""
        serves = e.get("serves")
        todo = [(c, i) for c in sort_by_id(self.customers) if c["state"] == "waiting"
                for i, o in enumerate(c["orders"])
                if o["state"] == "pending" and (serves is None or o["dish_id"] == serves)]
        if not todo:
            return
        dish_id = todo[0][0]["orders"][todo[0][1]]["dish_id"]
        dish = self.menu[dish_id]
        started = []
        for c, i in [x for x in todo if x[0]["orders"][x[1]]["dish_id"] == dish_id][:self.batch]:
            if any(self.stock.get(k, 0) < n for k, n in dish["recipe"].items()):
                break
            for k, n in dish["recipe"].items():
                self.stock[k] -= n
            c["orders"][i]["state"] = "cooking"
            started.append({"customer_id": c["id"], "order": i})
        if not started:
            return
        e.update(state="cooking", dish=dish_id, jobs=started, cook_ticks_left=int(round(dish["cook_s"] * TICK)), ready_ticks=0)
        data = {"stove_id": e["id"], "dish_id": dish_id, "customer_id": started[0]["customer_id"]}
        if len(started) > 1:
            data["count"] = len(started)
        events.append(("cook_started", data))

    def _use_stove(self, e, events):
        if e["state"] == "idle":
            self._try_start(e, events)
        elif e["state"] == "ready" and len(self.tray) < self.carry_limit:
            if not e["jobs"]:  # bếp dựng sẵn từ scenario, không rõ cho khách nào
                self.tray.append({"dish_id": e["dish"], "customer_id": None, "order": None})
                events.append(("dish_picked", {"stove_id": e["id"], "dish_id": e["dish"]}))
            while e["jobs"] and len(self.tray) < self.carry_limit:
                j = e["jobs"].pop(0)
                self.tray.append({"dish_id": e["dish"], "customer_id": j["customer_id"], "order": j["order"]})
                events.append(("dish_picked", {"stove_id": e["id"], "dish_id": e["dish"]}))
            if not e["jobs"]:
                e.update(state="idle", dish=None, cook_ticks_left=0, ready_ticks=0)

    def _use_table(self, e, events):
        c = next((c for c in self.customers if c["table_id"] == e["id"]), None)
        if not (c and c["state"] == "waiting"):
            return
        for it in [x for x in self.tray if x.get("customer_id") == c["id"]]:
            i = it.get("order")
            if i is None or not (0 <= i < len(c["orders"])) or c["orders"][i]["state"] != "cooking":
                continue
            c["orders"][i]["state"] = "served"
            self.tray.remove(it)
            events.append(("served", {"customer_id": c["id"], "table_id": e["id"], "dish_id": c["orders"][i]["dish_id"]}))
        if c["orders"] and all(o["state"] == "served" for o in c["orders"]):
            c["tip_ok"] = c["patience_ticks_left"] >= self.t["tip_min_patience_ratio"] * c["patience_max"]
            c["state"], c["eat_ticks_left"] = "eating", self.eat_max

    def _move(self, inp):
        speed = self.t["walk_speed"] * (1 + 0.15 * self._lv("speed"))
        mx, mz = inp.move
        self.vel = ramp_velocity(self, (mx * speed, mz * speed), int(self.t.get("ramp_max_ticks", 6)))
        b = self.t["bounds"]
        for i, axis in enumerate(("x", "z")):
            self.pos[i] += self.vel[i] / TICK
            lo, hi = b[axis]
            if self.pos[i] <= lo:
                self.pos[i], self.vel[i] = lo, max(0.0, self.vel[i])
            elif self.pos[i] >= hi:
                self.pos[i], self.vel[i] = hi, min(0.0, self.vel[i])
