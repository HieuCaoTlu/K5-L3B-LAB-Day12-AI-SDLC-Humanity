"""Buổi tối — Mở Quán. Khách, bếp, bưng món, trả tiền, boa, uy tín, kho cá thể có độ tươi (v1.2).

GIẢ ĐỊNH (chưa đối chiếu PRD-0 mục F; sửa lại khi có PRD): khách đến khi có bàn trống và đủ nguyên liệu
cho ít nhất một món (giữ chỗ cá thể nguyên liệu ngay), nguyên liệu bị trừ khi bắt đầu nấu món đó, kiên nhẫn
chỉ giảm khi chờ, khách bỏ đi nếu hết kiên nhẫn (món đang nấu cho họ bị bỏ), trả tiền khi ăn xong; boa nếu
còn đủ tỉ lệ kiên nhẫn lúc được phục vụ nốt món cuối.

Kho là DANH SÁCH CÁ THỂ {id, kind, fresh} (fresh = Fraction, chính xác ở ngưỡng 30). Chỉ khi số liệu có khối
`freshness` (contract v1.2) mới hao tươi / ươn và snapshot xuất kho dạng mảng cá thể; không có thì mọi cá thể
tươi 100, không hao, snapshot xuất kho dạng đếm theo loại như v1.1.

Tính năng sáng tạo (chỉ bật khi số liệu có `vendor` / `serves` / `max_dishes`, tức là ở chonoi.live; headless
dùng game.contract.json nên không có): mỗi bếp một món (`serves`), khách đòi nhiều món, ông bán nguyên liệu.
"""

import math
from fractions import Fraction

from ..errors import BadInput
from ..ids import id_key, sort_by_id
from ..inventory import item_to_json, items_to_json
from .ramp import ramp_velocity

TICK = 60.0
STOCK_KINDS = ("ca_loc", "ca_linh", "bong_dien_dien", "bong_sung", "ca_keo", "keo_neo", "coca")


def _frac(v):
    return v if isinstance(v, Fraction) else Fraction(str(v))


class QuanSim:
    mode = "quan"
    phase = "quan"

    def __init__(self, tuning, scenario, streams, ids, inventory=None):
        t = tuning["quan"]
        self.t = t
        self.menu = tuning["menu"]
        self.rng = streams
        self.ids = ids
        fr = tuning.get("freshness")
        self.fresh_on = fr is not None
        self.fresh0 = Fraction(str(fr["initial"])) if fr else Fraction(100)
        self.decay = Fraction(str(fr["quan_decay_per_s"])) / 60 if fr else Fraction(0)   # mỗi tick
        self.spoil_below = Fraction(str(fr["spoiled_below"])) if fr else Fraction(0)
        p = scenario.get("player", {})
        self.pos = list(p.get("pos", t["start_pos"]))
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0
        # kho: --inventory HOẶC scenario.stock (cả hai -> cli đã báo mã 2). Dict đếm hoặc list cá thể.
        self.items = self._load_items(inventory if inventory is not None else scenario.get("stock", {}))
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
        self.wait_for_stock = t.get("wait_for_stock", False)  # sáng tạo (live): khách vẫn tới khi kho thiếu, chờ có hàng
        self.vendor = t.get("vendor")
        self.customers = [self._customer_from_scenario(c) for c in scenario.get("customers", [])]
        for e in self.customers:
            ids.reserve(e["id"])
        self._reserve_missing()
        self.random_customers = scenario.get("random_customers", True)
        self.debug_full_stock = False  # chỉ bật từ chonoi.live --debug-stock, headless không dùng
        self.money = scenario.get("money", t.get("start_money", 0))
        self.earned = scenario.get("earned", 0)
        self.plan_dishes = scenario.get("plan_dishes")  # chế độ day: khách chỉ gọi món trong kế hoạch ngày
        self.stats = {"served": 0, "left": 0, "tips": 0, "sold": {}, "rep_start": self.reputation, "spoiled": 0}
        self.shift_earned = 0
        self._elapsed = 0
        self.done = False
        self.reason = None

    # --- kho cá thể -------------------------------------------------------------
    def _load_items(self, src):
        if isinstance(src, list):
            out = [{"id": x["id"], "kind": x["kind"], "fresh": _frac(x["fresh"])} for x in src]
            for it in out:
                self.ids.reserve(it["id"])
            return out
        out = []
        for kind in sorted(src):                      # kho đếm (v1.0/v1.1): cấp id I1, I2... theo loại rồi thứ tự
            for _ in range(int(src[kind])):
                out.append({"id": self.ids.new("I"), "kind": kind, "fresh": self.fresh0})
        return out

    def _new_item(self, kind):
        it = {"id": self.ids.new("I"), "kind": kind, "fresh": self.fresh0}
        self.items.append(it)
        return it

    def _spoiled(self, it):
        return self.fresh_on and it["fresh"] < self.spoil_below

    def stock_counts(self):
        """Số cá thể CHƯA ươn theo loại (dùng cho HUD / tương thích)."""
        out = {}
        for it in self.items:
            if not self._spoiled(it):
                out[it["kind"]] = out.get(it["kind"], 0) + 1
        return out

    def carry_items(self):
        """Kho còn lại dạng danh sách cá thể (dùng để mang sang ngày kế ở chế độ chơi nhiều ngày)."""
        return items_to_json(self.items)

    def _reserved_ids(self):
        s = set()
        for c in self.customers:
            for o in c["orders"]:
                if o["state"] == "pending":
                    s.update(o.get("items", ()))
        return s

    def _try_reserve(self, dish_id, taken=()):
        """Mỗi loại trong công thức lấy các cá thể chưa ươn, chưa giữ, tươi nhất rồi id nhỏ. None nếu không đủ."""
        used = set(taken) | self._reserved_ids()
        out = []
        for kind, n in self.menu[dish_id]["recipe"].items():
            cands = [it for it in self.items if it["kind"] == kind and it["id"] not in used and not self._spoiled(it)]
            cands.sort(key=lambda it: (-it["fresh"], id_key(it["id"])))
            if len(cands) < n:
                return None
            out += [c["id"] for c in cands[:n]]
        return out

    def _reserve_missing(self):
        """Khách dựng sẵn từ scenario: đơn chưa có phần giữ thì cấp theo order_tick rồi id bàn (tươi nhất, id nhỏ)."""
        pending = [(c, o) for c in sorted(self.customers, key=lambda c: (c.get("order_tick", 0), id_key(c["table_id"])))
                   for o in c["orders"] if o["state"] == "pending" and "items" not in o]
        for c, o in pending:
            got = self._try_reserve(o["dish_id"])
            if got is None:
                o["state"], o["items"] = "unfulfillable", []
            else:
                o["items"] = got

    def _customer_from_scenario(self, c):
        c = dict(c)
        state = c.get("state", "waiting")
        orders = c.get("orders")
        if orders is None:
            orders = ([{"dish_id": c["dish_id"], "state": "served" if state == "eating" else "pending"}]
                      if c.get("dish_id") else [])
        c["orders"] = [dict(o) for o in orders]
        res = c.pop("reserved", None)
        if isinstance(res, list):       # v1.2: reserved là mảng id cá thể; sai/mâu thuẫn -> mã 2
            self._check_reserved(c, res)
            pend = [o for o in c["orders"] if o["state"] == "pending"]
            if pend:
                pend[0]["items"] = list(res)
        c["state"] = state
        c.setdefault("patience_max", self.patience_max)
        c.setdefault("patience_ticks_left", c["patience_max"])
        if state == "eating":
            c.setdefault("eat_ticks_left", self.eat_max)
        c.setdefault("tip_ok", False)
        c.setdefault("order_tick", 0)
        return c

    def _check_reserved(self, c, res):
        by_id = {it["id"]: it for it in self.items}
        if len(set(res)) != len(res):
            raise BadInput(f"customers.{c['id']}.reserved có id trùng")
        for rid in res:
            if rid not in by_id:
                raise BadInput(f"customers.{c['id']}.reserved: id không có trong kho: {rid}")
            if self._spoiled(by_id[rid]):
                raise BadInput(f"customers.{c['id']}.reserved: cá thể đã ươn: {rid}")
        for o in c["orders"]:
            if o["state"] != "pending":
                continue
            need = {}
            for k, n in self.menu[o["dish_id"]]["recipe"].items():
                need[k] = n
            got = {}
            for rid in res:
                got[by_id[rid]["kind"]] = got.get(by_id[rid]["kind"], 0) + 1
            if got != need:
                raise BadInput(f"customers.{c['id']}.reserved không khớp công thức {o['dish_id']}")
        for other in getattr(self, "customers", []):  # không dùng chung với đơn khác
            for oo in other["orders"]:
                if set(oo.get("items", ())) & set(res):
                    raise BadInput(f"customers.{c['id']}.reserved dùng chung cá thể với khách {other['id']}")
        self._scenario_reserved = getattr(self, "_scenario_reserved", [])
        for prev in self._scenario_reserved:
            if set(prev) & set(res):
                raise BadInput(f"customers.{c['id']}.reserved dùng chung cá thể với khách khác")
        self._scenario_reserved.append(list(res))

    @staticmethod
    def _merge(defaults, updates):
        by_id = {d["id"]: dict(d) for d in defaults}
        for u in updates:
            if u["id"] not in by_id:
                raise BadInput(f"id bếp/bàn không tồn tại: {u['id']}")
            by_id[u["id"]].update(u)
        return sort_by_id(list(by_id.values()))

    # --- snapshot -------------------------------------------------------------
    def _reserved_of(self, c):
        """Phần giữ của khách: v1.2 -> mảng id cá thể; v1.1 -> đếm theo loại."""
        ids_ = []
        for o in c["orders"]:
            if o["state"] == "pending":
                ids_ += o.get("items", [])
        if self.fresh_on:
            return sorted(ids_, key=id_key)
        kinds = {it["id"]: it["kind"] for it in self.items}
        res = {}
        for i in ids_:
            if i in kinds:
                res[kinds[i]] = res.get(kinds[i], 0) + 1
        return res

    def _customer_view(self, c):
        v = {"id": c["id"], "table_id": c["table_id"], "state": c["state"],
             "dish_id": c["orders"][0]["dish_id"] if c["orders"] else None,
             "patience_ticks_left": c["patience_ticks_left"], "reserved": self._reserved_of(c)}
        if c["state"] == "eating":
            v["eat_ticks_left"] = c["eat_ticks_left"]
        if self.fresh_on and c["orders"]:
            v["base_price"] = c["orders"][0].get("base_price")
        if self.vendor is not None:  # phần sáng tạo
            v["orders"] = [dict(o) for o in c["orders"]]
            v["patience_max"] = c["patience_max"]
        return v

    def _stock_view(self):
        if self.fresh_on and self.vendor is None:      # contract: mảng cá thể; live (sáng tạo): đếm + tóm tắt `fresh`
            return items_to_json(self.items)
        counts = self.stock_counts()
        return {k: counts[k] for k in sorted(counts)}

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
            "stock": self._stock_view(),
            "hand": self.tray[0] if self.tray else None,
            "stoves": stoves,
            "tables": [{"id": tb["id"], "pos": tb["pos"], "customer_id": occupied.get(tb["id"])} for tb in self.tables],
            "customers": [self._customer_view(c) for c in sort_by_id(self.customers)],
        }
        if self.vendor is not None:
            if self.fresh_on:   # tóm tắt độ tươi theo loại cho HUD: số cá thể chưa ươn, TB, thấp nhất, số ươn
                summ = {}
                for it in self.items:
                    s_ = summ.setdefault(it["kind"], {"n": 0, "spoiled": 0, "sum": Fraction(0), "min": Fraction(100)})
                    if self._spoiled(it):
                        s_["spoiled"] += 1
                    else:
                        s_["n"] += 1
                        s_["sum"] += it["fresh"]
                        s_["min"] = min(s_["min"], it["fresh"])
                snap["fresh"] = {k: {"n": v["n"], "spoiled": v["spoiled"],
                                     "avg": round(float(v["sum"] / v["n"]), 1) if v["n"] else 0,
                                     "min": round(float(v["min"]), 1) if v["n"] else 0} for k, v in sorted(summ.items())}
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
            snap["upgrades"] = [{"key": k, "name": c["name"], "icon": c["icon"], "desc": c["desc"],
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
        """Thứ tự (Phase 3): đồng hồ → hao tươi + ươn (rồi xử lý giữ chỗ bị ươn) → bếp chín → di chuyển và tối đa
        một tương tác → kiên nhẫn / trả tiền / đóng ca → (nếu còn giờ) khách mới."""
        events = []
        if self.debug_full_stock:
            for it in self.items:
                it["fresh"] = self.fresh0
            for k in STOCK_KINDS:
                have = sum(1 for it in self.items if it["kind"] == k)
                for _ in range(max(0, 30 - have)):
                    self._new_item(k)
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        self._elapsed = int(round(self.t["duration_s"] * TICK)) - self.time_left_ticks  # số tick đã chạy
        self._decay_and_spoil(events)
        self._fill_waiting()
        self._tick_stoves(events)
        self._move(inp)
        if inp.pressed("interact"):
            self._interact(events)
        self._tick_customers(events)
        if self.time_left_ticks <= 0:
            self._close_shift(events)
            self.done = True
            self.reason = "time"
            events.append(("quan_end", {"reason": "time", "money": self.money, "earned": self.earned,
                                        "shift_earned": self.shift_earned, "reputation": self.reputation}))
            return events
        if self.random_customers:
            self._maybe_spawn(events)
        if self._lv("auto") > 0:  # nâng cấp: món tự nấu ngay khi có khách gọi
            for st in self.stoves:
                if st["state"] == "idle" and st.get("serves"):
                    self._try_start(st, events)
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
        self._new_item(kind)
        return ("bought", {"item": kind, "price": price})

    # --- độ tươi ---------------------------------------------------------------
    def _decay_and_spoil(self, events):
        """Kho thô hao 0.25/s kể cả hàng đang giữ chỗ. Phát `spoiled` (theo id) khi đi từ >= 30 xuống < 30,
        rồi mới xử lý các đơn có phần giữ vừa ươn: nhả hết phần giữ và thử giữ lại ĐÚNG MỘT lần
        (theo order_tick rồi id bàn); không đủ thì đơn thành `unfulfillable`, khách chờ tới hết kiên nhẫn."""
        if not self.fresh_on or not self.items:
            return
        crossed = []
        for it in self.items:
            was_ok = it["fresh"] >= self.spoil_below
            it["fresh"] = max(Fraction(0), it["fresh"] - self.decay)
            if was_ok and it["fresh"] < self.spoil_below:
                crossed.append(it)
        if not crossed:
            return
        for it in sort_by_id(crossed):
            self.stats["spoiled"] += 1
            events.append(("spoiled", {"item_id": it["id"], "kind": it["kind"], "location": "stock"}))
        bad = {it["id"] for it in crossed}
        affected = [(c, o) for c in sorted(self.customers, key=lambda c: (c.get("order_tick", 0), id_key(c["table_id"])))
                    for o in c["orders"] if o["state"] == "pending" and bad & set(o.get("items", ()))]
        for c, o in affected:
            o["items"] = []                       # nhả toàn bộ phần giữ của đơn
            got = self._try_reserve(o["dish_id"])  # thử giữ lại đúng một lần
            if got is None:
                if not self.wait_for_stock:
                    o["state"] = "unfulfillable"
            else:
                o["items"] = got

    def _fill_waiting(self):
        """wait_for_stock: đơn chưa có phần giữ (kho thiếu) thì giữ ngay khi có hàng (order_tick rồi id bàn)."""
        if not self.wait_for_stock:
            return
        for c in sorted(self.customers, key=lambda c: (c.get("order_tick", 0), id_key(c["table_id"]))):
            for o in c["orders"]:
                if o["state"] == "pending" and not o.get("items"):
                    got = self._try_reserve(o["dish_id"])
                    if got:
                        o["items"] = got

    # --- khách / bếp -----------------------------------------------------------
    def _every(self):
        return int(round(self.t["customer_interval_s"] * TICK))

    def _pick_orders(self, n):
        """Chọn tối đa n món còn nấu được (cá thể chưa ươn, chưa giữ) và giữ chỗ luôn. -> list (món, [id cá thể])."""
        picked, taken = [], set()
        for _ in range(n):
            allowed = [name for name in sorted(self.menu) if self.plan_dishes is None or name in self.plan_dishes]
            options = allowed if self.wait_for_stock else [name for name in allowed if self._try_reserve(name, taken) is not None]
            if not options:
                break
            d = options[int(self.rng.get("customer_dish").random() * len(options)) % len(options)]
            got = self._try_reserve(d, taken) or []     # wait_for_stock: chưa đủ hàng thì giữ rỗng, có hàng sẽ giữ sau
            taken |= set(got)
            picked.append((d, got))
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
        picked = self._pick_orders(want)
        if not picked:
            events.append(("no_dish", {"customer_id": cid}))
            return
        pmax = int(self.patience_max * (1 + 0.5 * (len(picked) - 1)))
        self.customers.append({"id": cid, "table_id": free[0]["id"], "state": "waiting",
                               "orders": [{"dish_id": d, "state": "pending", "items": ids_} for d, ids_ in picked],
                               "patience_ticks_left": pmax, "patience_max": pmax, "tip_ok": False,
                               "order_tick": self._elapsed})
        events.append(("customer_arrived", {"customer_id": cid, "table_id": free[0]["id"],
                                            "dishes": [d for d, _ in picked]}))

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
                    self.stats["left"] += 1
                    events.append(("customer_left", {"customer_id": c["id"], "reputation": self.reputation}))
            elif c["state"] == "eating":
                c["eat_ticks_left"] -= 1
                if c["eat_ticks_left"] <= 0:
                    self._pay(c, events)

    def _rep_pay_mult(self):
        """Sáng tạo (chỉ chonoi.live): uy tín thấp thì khách trả ít hơn. 0 -> 50%, 3.0 -> 100%, 5 -> 120%."""
        if not self.t.get("rep_pay_scale"):
            return 1.0
        r = self.reputation
        return 0.5 + 0.5 * r / 3.0 if r <= 3.0 else 1.0 + 0.1 * (r - 3.0)

    def _pay(self, c, events):
        """Khách ăn xong (hoặc đóng ca khi đang ăn): trả giá đã chốt theo độ tươi + boa (floor), boa dương thì +uy tín."""
        base = sum(o.get("base_price", self.menu[o["dish_id"]]["price"]) for o in c["orders"])
        price = int(round(base * (1 + 0.15 * self._lv("tasty")) * self._rep_pay_mult()))
        tip = int(math.floor(price * self.t["tip_rate"])) if c["tip_ok"] else 0
        if tip > 0:
            self._adjust_rep(self.t["tip_reputation"])
        self.money += price + tip
        self.earned += price + tip
        self.shift_earned += price + tip
        self.stats["served"] += 1
        self.stats["tips"] += tip
        for o in c["orders"]:
            self.stats["sold"][o["dish_id"]] = self.stats["sold"].get(o["dish_id"], 0) + 1
        self.customers.remove(c)
        events.append(("paid", {"customer_id": c["id"], "price": price, "tip": tip}))

    def _close_shift(self, events):
        """Hết giờ: khách đang ăn trả ngay; khách đang chờ rời đi, KHÔNG trừ uy tín; dọn món và phần giữ."""
        for c in sort_by_id(self.customers):
            if c["state"] == "eating":
                self._pay(c, events)
            else:
                self.customers.remove(c)
                events.append(("customer_left", {"customer_id": c["id"], "reputation": self.reputation,
                                                 "reason": "closing"}))
        for st in self.stoves:
            st.update(jobs=[], state="idle", dish=None, cook_ticks_left=0, ready_ticks=0)
        self.tray = []

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
        """Bếp rảnh: nấu cho các món đang chờ (tối đa `batch` phần cùng một món, cùng lúc).
        Tiêu đúng các cá thể đang giữ và chốt base_price = floor(giá niêm yết × trung bình fresh / 100)."""
        serves = e.get("serves")
        todo = [(c, i) for c in sorted(self.customers, key=lambda c: (c.get("order_tick", 0), id_key(c["table_id"])))
                if c["state"] == "waiting"
                for i, o in enumerate(c["orders"])
                if o["state"] == "pending" and o.get("items") and (serves is None or o["dish_id"] == serves)]
        if not todo:
            return
        dish_id = todo[0][0]["orders"][todo[0][1]]["dish_id"]
        dish = self.menu[dish_id]
        started, used_all = [], []
        for c, i in [x for x in todo if x[0]["orders"][x[1]]["dish_id"] == dish_id][:self.batch]:
            o = c["orders"][i]
            by_id = {it["id"]: it for it in self.items}
            used = [by_id[x] for x in o.get("items", ()) if x in by_id]
            if not used or len(used) != len(o.get("items", ())):
                o["state"] = "unfulfillable"      # phần giữ không còn trong kho
                continue
            for it in used:
                self.items.remove(it)
            total = sum((it["fresh"] for it in used), Fraction(0))
            o["base_price"] = int(math.floor(Fraction(dish["price"]) * total / (len(used) * 100)))
            o["state"] = "cooking"
            started.append({"customer_id": c["id"], "order": i})
            used_all += used
        if not started:
            return
        e.update(state="cooking", dish=dish_id, jobs=started, cook_ticks_left=int(round(dish["cook_s"] * TICK)), ready_ticks=0)
        data = {"stove_id": e["id"], "dish_id": dish_id, "customer_id": started[0]["customer_id"]}
        if self.fresh_on:   # v1.2: các cá thể đã dùng, sắp theo kind rồi id
            data["items"] = [item_to_json(it) for it in sorted(used_all, key=lambda x: (x["kind"], id_key(x["id"])))]
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

    def _flex_match(self, c):
        """Sáng tạo (flex_serve): món đang cầm nấu cho khách khác vẫn đưa được cho khách này nếu họ gọi đúng món đó.
        Hai đơn đổi chỗ cho nhau (trạng thái, phần giữ nguyên liệu, giá chốt, việc đang nấu, món trên khay)."""
        for it in list(self.tray):
            c0, i0 = it.get("customer_id"), it.get("order")
            if c0 is None or i0 is None or c0 == c["id"]:
                continue
            other = next((x for x in self.customers if x["id"] == c0), None)
            if other is None or not (0 <= i0 < len(other["orders"])):
                continue
            held = {(t_.get("customer_id"), t_.get("order")) for t_ in self.tray}
            cand = [(0 if o["state"] == "cooking" else 1, j) for j, o in enumerate(c["orders"])
                    if o["dish_id"] == it["dish_id"] and o["state"] in ("cooking", "pending") and (c["id"], j) not in held]
            if not cand:
                continue
            j = min(cand)[1]
            a, b = other["orders"][i0], c["orders"][j]
            for k in ("state", "items", "base_price"):
                av, bv = a.get(k), b.get(k)
                for o_, v_ in ((a, bv), (b, av)):
                    if v_ is None:
                        o_.pop(k, None)
                    else:
                        o_[k] = v_
            swap = {(c0, i0): (c["id"], j), (c["id"], j): (c0, i0)}     # nối lại việc đang nấu / món trên khay theo hai đơn vừa đổi
            for st in self.stoves:
                for job in st["jobs"]:
                    key = swap.get((job["customer_id"], job["order"]))
                    if key:
                        job["customer_id"], job["order"] = key
            for t_ in self.tray:
                if t_ is it:
                    t_["customer_id"], t_["order"] = c["id"], j
                else:
                    key = swap.get((t_.get("customer_id"), t_.get("order")))
                    if key:
                        t_["customer_id"], t_["order"] = key

    def _use_table(self, e, events):
        c = next((c for c in self.customers if c["table_id"] == e["id"]), None)
        if not (c and c["state"] == "waiting"):
            return
        if self.t.get("flex_serve"):
            self._flex_match(c)
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
