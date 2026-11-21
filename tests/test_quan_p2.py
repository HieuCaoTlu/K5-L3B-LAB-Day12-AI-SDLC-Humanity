"""Luật quán Phase 2 (đóng ca, boa floor, thứ tự đơn, kế hoạch ngày, mang tiền qua ngày). Chạy trực tiếp trên sim."""

import unittest

from chonoi.contract import load_contract
from chonoi.errors import BadInput
from chonoi.inputs import InputState
from chonoi.runner import Session
from chonoi.scenario import load_scenario

CONTRACT = load_contract()
TUNING = {k: v for k, v in CONTRACT["tuning"].items() if k != "freshness"}   # regression P1-P2: số liệu v1.1 (kho đếm, không hao tươi)
FULL = {"ca_loc": 9, "ca_linh": 9, "bong_dien_dien": 9, "bong_sung": 9, "ca_keo": 9, "keo_neo": 9}


def step(sess, n=1, press=()):
    rows = []
    for i in range(n):
        rows += sess.step(InputState((0.0, 0.0), {}, set(press) if i == 0 else set()))
    return rows


def names(rows):
    return [r["name"] for r in rows]


class QuanP2(unittest.TestCase):
    def test_contract_v11_values(self):
        c = CONTRACT
        self.assertEqual(c["contract_version"], "1.3")   # "1.1" -> "1.2" (Phase 3, độ tươi) -> "1.3" (Phase 4: bench_cmd, soak_cmd; gameplay giữ v1.2)
        self.assertEqual([s["id"] for s in TUNING["quan"]["stoves"]], ["B1", "B2"])
        self.assertEqual([t["id"] for t in TUNING["quan"]["tables"]], ["T1", "T2", "T3", "T4"])
        self.assertEqual(len(TUNING["menu"]), 6)
        self.assertEqual(TUNING["day_plan"][3]["ingredients"]["keo_neo"], 1)

    def test_first_customer_and_interval(self):
        s = Session("quan", TUNING, {"stock": dict(FULL)}, 1)
        t = [r["tick"] for r in step(s, 2000) if r["name"] == "customer_arrived"]
        self.assertEqual(t[:3], [120, 1020, 1920])

    def test_closing_pays_eaters_and_releases_waiters_without_penalty(self):
        sc = {"stock": dict(FULL), "time_left_ticks": 5, "random_customers": False,
              "customers": [{"id": "C1", "table_id": "T1", "dish_id": "goi_bong_sung", "state": "eating", "eat_ticks_left": 500},
                            {"id": "C2", "table_id": "T2", "dish_id": "ca_loc_nuong_trui"}]}
        s = Session("quan", TUNING, sc, 1)
        rows = step(s, 5)
        self.assertEqual(names(rows), ["paid", "customer_left", "quan_end"])
        self.assertEqual(rows[1]["data"]["reason"], "closing")
        self.assertEqual(s.sim.reputation, TUNING["quan"]["reputation_initial"])
        self.assertEqual(s.sim.money, 40)
        self.assertEqual(s.sim.customers, [])

    def test_tip_is_floor_and_adds_reputation(self):
        s = Session("quan", TUNING, {"stock": dict(FULL), "random_customers": False,
                                     "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_keo_nuong", "state": "eating",
                                                    "eat_ticks_left": 1, "tip_ok": True}]}, 1)
        rows = step(s)
        self.assertEqual(rows[0]["data"], {"customer_id": "C1", "price": 70, "tip": 14})
        self.assertAlmostEqual(s.sim.reputation, 3.2)

    def test_stove_takes_oldest_order_tick_first(self):
        sc = {"stock": dict(FULL), "random_customers": False,
              "customers": [{"id": "C1", "table_id": "T3", "dish_id": "ca_loc_nuong_trui", "order_tick": 50},
                            {"id": "C2", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "order_tick": 10}]}
        s = Session("quan", TUNING, sc, 1)
        s.sim.pos = list(s.sim.stoves[0]["pos"])
        rows = step(s, 1, ("interact",))
        self.assertEqual([r["data"]["customer_id"] for r in rows if r["name"] == "cook_started"], ["C2"])

    def test_plan_dishes_limit_customer_choice(self):
        sc = {"stock": dict(FULL), "plan_dishes": ["goi_bong_sung"]}
        s = Session("quan", TUNING, sc, 3)
        step(s, 130)
        self.assertEqual([c["dish_id"] for c in s.snapshot()["customers"]], ["goi_bong_sung"])

    def test_carry_money_earned_reputation(self):
        s = Session("quan", TUNING, {"money": 200, "earned": 250, "reputation": 4.0, "random_customers": False}, 1)
        snap = s.snapshot()
        self.assertEqual((snap["money"], snap["earned"], snap["reputation"]), (200, 250, 4.0))

    def test_scenario_rules(self):
        import json, os, tempfile
        def load(block):
            with tempfile.TemporaryDirectory() as d:
                p = os.path.join(d, "s.json")
                with open(p, "w", encoding="utf-8") as f:
                    json.dump({"quan": block}, f)
                return load_scenario(p, "quan", TUNING)
        with self.assertRaises(BadInput):
            load({"customers": [{"id": "C1", "table_id": "T1", "dish_id": "pho"}]})
        with self.assertRaises(BadInput):
            load({"stock": {}, "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"}]})
        load({"stock": {"ca_loc": 1}, "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"}]})


if __name__ == "__main__":
    unittest.main()
