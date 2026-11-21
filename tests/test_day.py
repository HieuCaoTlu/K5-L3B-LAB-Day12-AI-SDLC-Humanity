"""Chế độ day (headless): 5 ngày, bàn giao pha cùng tick, Shop tự mua, tất định."""

import os
import tempfile
import unittest

from chonoi.contract import load_contract
from chonoi.day import DaySession
from chonoi.inputs import InputPlayer
from helpers import read_jsonl, run_headless


def _run(sess, ticks):
    player = InputPlayer([])
    rows = []
    while sess.tick < ticks and not sess.done:
        rows += sess.step(player.advance(sess.tick))
    return rows


class DayModeTests(unittest.TestCase):
    def setUp(self):
        self.tuning = load_contract()["tuning"]

    def test_full_five_days_deterministic(self):
        with tempfile.TemporaryDirectory() as d:
            outs = []
            for n in "ab":
                p = os.path.join(d, n + ".jsonl")
                self.assertEqual(run_headless("--mode", "day", "--seed", "3", "--ticks", "200000", "--out", p)[0], 0)
                with open(p, "rb") as f:
                    outs.append(f.read())
            self.assertEqual(outs[0], outs[1])
            rows = read_jsonl(os.path.join(d, "a.jsonl"))
        end = rows[-1]
        self.assertEqual((end["type"], end["reason"], end["day"], end["mode"]), ("end", "days_complete", 5, "day"))
        starts = [r["data"]["day"] for r in rows if r["type"] == "event" and r["name"] == "day_start"]
        self.assertEqual(starts, [1, 2, 3, 4, 5])
        names = [r["name"] for r in rows if r["type"] == "event"]
        self.assertEqual(names.count("gather_end"), 5)
        self.assertEqual(names.count("quan_end"), 5)
        self.assertEqual(names[-1], "game_end")

    def test_tick_limit_and_phases(self):
        s = DaySession(self.tuning, 1)
        _run(s, 10900)
        self.assertEqual(s.phase, "quan")
        self.assertEqual(s.phase_tick, 100)
        self.assertEqual(s.snapshot()["day"], 1)
        self.assertEqual(s.end_row()["reason"], "tick_limit")

    def test_handover_stock_and_plan(self):
        s = DaySession(self.tuning, 1)
        s.sim.inventory_items = lambda: [{"id": "I1", "kind": "ca_loc", "fresh": 100}]
        _run(s, 10800)
        self.assertEqual(s.phase, "quan")
        self.assertEqual([it["id"] for it in s.sim.items], ["I1"])
        self.assertEqual(s.sim.plan_dishes, ["ca_loc_nuong_trui", "goi_bong_sung"])

    def test_shop_buys_in_order_and_applies_next_day(self):
        s = DaySession(self.tuning, 1)
        s.money = 650
        ev = s._shop()
        self.assertEqual([(e[1]["item"], e[1]["level"]) for e in ev], [("oxygen", 1), ("hp", 1)])
        self.assertEqual(s.money, 200)
        s2 = DaySession(self.tuning, 1)
        s2.level = {"oxygen": 1, "hp": 1}
        s2._begin_gather()
        self.assertEqual(s2.sim.oxygen_max, 45 * 60)
        self.assertEqual(s2.sim.hp, 4)
        self.assertEqual(self.tuning["gather"]["oxygen_max_s"], 30)  # số liệu gốc không bị sửa

    def test_rejects_scenario(self):
        with tempfile.TemporaryDirectory() as d:
            code, _ = run_headless("--mode", "day", "--seed", "1", "--ticks", "5", "--out", os.path.join(d, "o.jsonl"),
                                   "--scenario", os.path.join(d, "x.json"))
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
