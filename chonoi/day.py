"""Chế độ `day` (contract v1.1+): 5 ngày liền mạch, sáng gather -> tối quan -> Shop -> ngày kế.

`DaySession` có cùng giao diện với `runner.Session` (tick, done, snapshot, step, end_row) nên headless dùng chung vòng tick.
Giả định của nhóm (ghi ở docs/clarify.md, mục D1-D5):
- `tick` / `sim_tick` là tick toàn cục, `phase_tick` tính trong pha hiện tại; input đọc theo tick toàn cục.
- Bàn giao pha trong CÙNG tick: sim vừa kết thúc phát sự kiện cuối, pha sau dựng xong ngay, bước đầu của nó ở tick kế.
- Shop không có giao diện ở headless: tự mua theo luật cố định (xem `_shop`), kết thúc ngay trong tick bàn giao.
- Số liệu chỉ đọc từ `tuning` (day_plan, shop, gather, quan). Ngẫu nhiên đi qua một `Streams(seed)` chung.
"""

import copy
import math

from .ids import IdAllocator
from .rng import Streams
from .sim.gather import GatherSim
from .sim.quan import QuanSim


class DaySession:
    mode = "day"

    def __init__(self, tuning, seed):
        self.base = tuning
        self.plan = sorted(tuning["day_plan"], key=lambda d: d["day"])
        self.shop = tuning["shop"]
        self.streams, self.ids = Streams(seed), IdAllocator()
        self.tick = 0
        self.phase_tick = 0
        self.day_index = 0
        self.money = 0
        self.earned = 0
        self.reputation = tuning["quan"]["reputation_initial"]
        self.level = {"oxygen": 0, "hp": 0}
        self.done = False
        self.reason = None
        self._pending = []
        self._begin_gather()

    @property
    def sim(self):
        return self._sim

    @property
    def phase(self):
        return self._sim.phase

    @property
    def day(self):
        return self.plan[self.day_index]["day"]

    # --- dựng pha -------------------------------------------------------------------
    def _day_tuning(self):
        t = copy.deepcopy(self.base)
        for key, field in (("oxygen", "oxygen_max_s"), ("hp", "hp_max")):
            if self.level[key]:
                t["gather"][field] = self.shop["upgrades"][key][self.level[key] - 1][field]
        return t

    def _begin_gather(self):
        self._tuning = self._day_tuning()
        self._sim = GatherSim(self._tuning, {"day": self.day}, self.streams, self.ids)
        self.phase_tick = 0
        self._pending.append(("day_start", {"day": self.day, "plan": self.plan[self.day_index]}))

    def _begin_quan(self, items):
        scen = {"money": self.money, "earned": self.earned, "reputation": self.reputation,
                "plan_dishes": sorted(self.plan[self.day_index]["dishes"])}
        self._sim = QuanSim(self._tuning, scen, self.streams, self.ids, inventory=[dict(x) for x in items])
        self.phase_tick = 0

    def _shop(self):
        """Luật mua cố định: lần lượt oxy rồi Máu, mua bậc kế tiếp nếu đủ tiền; dừng khi không mua nổi bậc nào."""
        events = []
        bought = True
        while bought:
            bought = False
            for key in ("oxygen", "hp"):
                tiers = self.shop["upgrades"][key]
                lv = self.level[key]
                if lv < len(tiers) and self.money >= tiers[lv]["price"]:
                    price = tiers[lv]["price"]
                    self.money -= price
                    self.level[key] = lv + 1
                    events.append(("shop_buy", {"item": key, "level": lv + 1, "price": price, "money": self.money}))
                    bought = True
        return events

    # --- giao diện runner -----------------------------------------------------------
    def step(self, inp):
        sim = self._sim
        rows = [(n, d, "gather") for n, d in self._pending]
        self._pending = []
        rows += [(n, d, sim.phase) for n, d in sim.step(inp)]
        self.tick += 1
        self.phase_tick += 1
        if sim.done:
            if sim.mode == "gather":
                self._begin_quan(sim.inventory_items())
            else:
                self.money, self.earned, self.reputation = sim.money, sim.earned, sim.reputation
                after = [("day_end", {"day": self.day, "money": self.money, "earned": self.earned,
                                      "reputation": self.reputation, "stats": sim.stats}),
                         ("shop_start", {"day": self.day, "money": self.money})]
                after += self._shop()
                after.append(("shop_end", {"day": self.day, "money": self.money, "levels": dict(self.level)}))
                if self.day_index + 1 >= len(self.plan):
                    self.done, self.reason = True, "days_complete"
                    after.append(("game_end", {"days": self.day, "money": self.money, "earned": self.earned,
                                               "reputation": self.reputation, "score": self._score(self.earned, self.reputation)}))
                else:
                    self.day_index += 1
                    self._begin_gather()
                rows += [(n, d, "shop") for n, d in after]
        return [{"type": "event", "tick": self.tick, "phase": ph, "name": n, "data": d} for n, d, ph in rows]

    def _score(self, earned, rep):
        return earned + self.base["score"]["reputation_multiplier"] * math.floor(rep)

    def _totals(self):
        if self.done:
            return self.money, self.earned, self.reputation
        s = self._sim
        return s.money, s.earned, s.reputation

    def snapshot(self):
        money, earned, rep = self._totals()
        row = {"type": "snapshot", "tick": self.tick, "sim_tick": self.tick, "mode": "day", "phase": self.phase,
               "phase_tick": self.phase_tick, "state": "finished" if self.done else "playing",
               "day": self.day, "levels": dict(self.level), "time_left_ticks": self._sim.time_left_ticks,
               "money": money, "earned": earned, "reputation": rep, "score": self._score(earned, rep)}
        snap = self._sim.snapshot()
        snap.pop("mode", None)
        row.update(snap)
        return row

    def end_row(self):
        money, earned, rep = self._totals()
        return {"type": "end", "ticks": self.tick, "sim_tick": self.tick, "mode": "day",
                "state": "finished" if self.done else "playing",
                "reason": self.reason if self.done else "tick_limit", "day": self.day,
                "money": money, "earned": earned, "reputation": rep, "score": self._score(earned, rep)}

    def write_inventory_if_done(self, inventory_out):
        pass
