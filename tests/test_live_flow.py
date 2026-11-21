"""Ngày liền mạch của chonoi.live (--mode day): sáng -> tối mang kho -> sáng hôm sau."""

import json
import unittest

from chonoi.contract import load_contract
from chonoi.live import LiveGame
from chonoi.scenario import load_scenario


class LiveFlow(unittest.TestCase):
    def setUp(self):
        self.t = load_contract()["tuning"]
        sc = {m: load_scenario(None, m, self.t) for m in ("gather", "quan")}
        self.g = LiveGame("day", self.t, sc["gather"], 1, extras=True, scenarios=sc)

    def snap(self):
        return json.loads(self.g.state_json())

    def test_morning_to_evening_carries_stock(self):
        self.assertEqual(self.snap()["mode"], "gather")
        self.g.restart(next_day=True)                      # chưa xong buổi sáng: bỏ qua
        self.assertEqual(self.snap()["mode"], "gather")
        sim = self.g.session.sim
        sim.hold = [{"id": "I1", "kind": "ca_loc", "fresh": 90}, {"id": "I2", "kind": "ca_loc", "fresh": 80}]
        sim.done, sim.reason = True, "docked"
        self.g.restart(next_day=True)
        s = self.snap()
        self.assertEqual((s["mode"], s["day"], s["stock"]), ("quan", 1, {"ca_loc": 2}))

    def test_evening_to_next_morning_keeps_leftover(self):
        self.g.session.sim.done, self.g.session.sim.reason = True, "fainted"
        self.g.restart(next_day=True)                      # ngất -> tối với kho rỗng
        q = self.g.session.sim
        q.stock = {"bong_sung": 3}
        q.done, q.reason = True, "time"
        self.g.restart(next_day=True)
        s = self.snap()
        self.assertEqual((s["mode"], s["day"], s["carry_stock"]), ("gather", 2, {"bong_sung": 3}))
        self.g.restart(new_game=True)
        s = self.snap()
        self.assertEqual((s["mode"], s["day"], s["carry_stock"]), ("gather", 1, {}))


if __name__ == "__main__":
    unittest.main()
