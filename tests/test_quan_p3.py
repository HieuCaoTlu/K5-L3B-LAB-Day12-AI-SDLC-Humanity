"""Quán Phase 3 (Mùa Nước Nổi): kho cá thể, hao tươi, ươn, giữ chỗ theo id, giá theo tươi, schema file kho v1.2."""

import copy
import json
import os
import tempfile
import unittest
from fractions import Fraction

from chonoi.contract import load_contract
from chonoi.errors import BadInput
from chonoi.inputs import InputState
from chonoi.inventory import read_inventory, write_inventory_items
from chonoi.runner import Session, run
from chonoi.scenario import load_scenario

BASE = load_contract()["tuning"]
T12 = copy.deepcopy(BASE)
T12["freshness"] = {"initial": 100, "gather_decay_per_s": 0.5, "quan_decay_per_s": 0.25, "spoiled_below": 30}


def item(i, kind, fresh):
    return {"id": i, "kind": kind, "fresh": fresh}


def step(sess, n=1, press=()):
    rows = []
    for i in range(n):
        rows += sess.step(InputState((0.0, 0.0), {}, set(press) if i == 0 else set()))
    return rows


def events(rows, name):
    return [r for r in rows if r["name"] == name]


def cust(cid="C1", table="T1", dish="ca_loc_nuong_trui", **kw):
    return dict({"id": cid, "table_id": table, "dish_id": dish}, **kw)


def session(stock, customers=(), tuning=T12, **extra):
    sc = {"stock": stock, "random_customers": False, "customers": list(customers)}
    sc.update(extra)
    return Session("quan", tuning, sc, 1)


class FreshInventoryFile(unittest.TestCase):
    def write(self, obj):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "k.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(obj, f)
        return p

    def test_valid_v12_file_and_empty(self):
        p = self.write({"items": [item("I1", "ca_linh", 100), item("I2", "ca_loc", 97.5)]})
        got = read_inventory(p, fresh=True)
        self.assertEqual([(x["id"], x["kind"], x["fresh"]) for x in got],
                         [("I1", "ca_linh", Fraction(100)), ("I2", "ca_loc", Fraction("97.5"))])
        self.assertEqual(read_inventory(self.write({"items": []}), fresh=True), [])

    def test_v12_rejects_count_schema_and_bad_items(self):
        bad = [{"items": {"ca_loc": 1}},
               {"items": [item("I1", "ca_loc", 100), item("I1", "ca_linh", 100)]},      # id trùng
               {"items": [item("I1", "pho", 100)]},                                       # kind lạ
               {"items": [item("I1", "ca_loc", 101)]}, {"items": [item("I1", "ca_loc", -1)]},   # fresh ngoài miền
               {"items": [item("I1", "ca_loc", "100")]}, {"items": [item("", "ca_loc", 100)]},
               {"items": [{"id": "I1", "kind": "ca_loc"}]},
               {"items": [item("I1", "ca_loc", 100)], "extra": 1}]
        for obj in bad:
            with self.assertRaises(BadInput, msg=str(obj)):
                read_inventory(self.write(obj), fresh=True)

    def test_v11_rejects_item_list(self):
        with self.assertRaises(BadInput):
            read_inventory(self.write({"items": [item("I1", "ca_loc", 100)]}), fresh=False)

    def test_write_sorted_by_id_and_roundtrip(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "o.json")
        write_inventory_items(p, [{"id": "I10", "kind": "ca_loc", "fresh": Fraction(7199, 240)},
                                  {"id": "I2", "kind": "ca_linh", "fresh": Fraction(100)}])
        data = json.load(open(p, encoding="utf-8"))
        self.assertEqual([x["id"] for x in data["items"]], ["I2", "I10"])        # I2 trước I10
        back = read_inventory(p, fresh=True)
        self.assertLess(back[1]["fresh"], 30)                                      # 29.995833 vẫn < 30 sau khi đọc lại
        write_inventory_items(p, [])
        self.assertEqual(json.load(open(p, encoding="utf-8")), {"items": []})

    def test_headless_run_snapshot_matches_file_at_tick0(self):
        items = [item("I1", "ca_linh", 100), item("I3", "ca_loc", 97.5), item("I2", "bong_sung", 61.25)]
        d = tempfile.mkdtemp()
        inv, out = os.path.join(d, "k.json"), os.path.join(d, "q.jsonl")
        write_inventory_items(inv, [{**x, "fresh": Fraction(str(x["fresh"]))} for x in items])
        run("quan", T12, {}, 1, [], 0, out, 10, inventory=read_inventory(inv, fresh=True))
        snap = json.loads(open(out, encoding="utf-8").readline())
        self.assertEqual(snap["stock"], [item("I1", "ca_linh", 100.0), item("I2", "bong_sung", 61.25), item("I3", "ca_loc", 97.5)])


class FreshRules(unittest.TestCase):
    def test_decay_quarter_point_per_second_and_floor_zero(self):
        s = session([item("I1", "ca_loc", 100), item("I2", "ca_loc", 0.001)])
        step(s, 60)
        got = {x["id"]: x["fresh"] for x in s.snapshot()["stock"]}
        self.assertAlmostEqual(got["I1"], 99.75, places=3)
        self.assertEqual(got["I2"], 0)                                              # kẹp đáy 0

    def test_spoiled_exact_threshold_tick_and_once(self):
        s = session([item("I2", "ca_loc", 30.01), item("I1", "ca_linh", 30)])
        r1 = step(s, 1)
        self.assertEqual([(e["tick"], e["data"]) for e in events(r1, "spoiled")],
                         [(1, {"item_id": "I1", "kind": "ca_linh", "location": "stock"})])   # đúng 30 -> ươn ở bước đầu
        r2 = step(s, 5)
        sp = events(r2, "spoiled")
        self.assertEqual([(e["tick"], e["data"]["item_id"]) for e in sp], [(3, "I2")])      # 30.01 - 3/240 < 30, một lần duy nhất

    def test_spoiled_events_ordered_by_id(self):
        s = session([item("I10", "ca_loc", 30), item("I2", "ca_loc", 30), item("I1", "ca_linh", 30)])
        self.assertEqual([e["data"]["item_id"] for e in events(step(s, 1), "spoiled")], ["I1", "I2", "I10"])

    def test_spoiled_item_not_usable_for_new_customers(self):
        s = Session("quan", T12, {"stock": [item("I1", "ca_loc", 29.9)], "random_customers": True}, 1)
        rows = step(s, 130)
        self.assertEqual(events(rows, "customer_arrived"), [])
        self.assertTrue(events(rows, "no_dish"))

    def test_reserve_freshest_then_smallest_id(self):
        s = session([item("I1", "ca_loc", 60), item("I3", "ca_loc", 90), item("I2", "ca_loc", 90)], [cust()])
        self.assertEqual(s.snapshot()["customers"][0]["reserved"], ["I2"])

    def test_reserved_spoils_then_rereserve_once(self):
        s = session([item("I1", "ca_loc", 30), item("I2", "ca_loc", 80)], [cust(reserved=["I1"])])
        self.assertEqual(s.snapshot()["customers"][0]["reserved"], ["I1"])
        rows = step(s, 1)
        self.assertEqual([e["data"]["item_id"] for e in events(rows, "spoiled")], ["I1"])
        self.assertEqual(s.snapshot()["customers"][0]["reserved"], ["I2"])

    def test_reserved_spoils_no_replacement_becomes_unfulfillable(self):
        s = session([item("I1", "ca_loc", 30)], [cust(reserved=["I1"])])
        step(s, 1)
        self.assertEqual(s.sim.customers[0]["orders"][0]["state"], "unfulfillable")
        s.sim.pos = list(s.sim.stoves[0]["pos"])
        self.assertEqual(events(step(s, 1, ("interact",)), "cook_started"), [])           # không nấu được; khách vẫn chờ
        self.assertEqual(len(s.sim.customers), 1)

    def test_cook_consumes_reserved_items_and_prices_by_freshness(self):
        # lẩu cá linh: ca_linh×3 + bong_dien_dien×1, giá 120; fresh 100, 90, 80, 70.8 (sau hao 1 tick ở đầu bước) -> TB ≈ 85.196 -> floor = 102
        stock = [item("I1", "ca_linh", 100), item("I2", "ca_linh", 90), item("I3", "ca_linh", 80), item("I4", "bong_dien_dien", 70.8),
                 item("I5", "ca_linh", 10)]
        s = session(stock, [cust(dish="lau_ca_linh_dien_dien")])
        s.sim.pos = list(s.sim.stoves[0]["pos"])
        rows = step(s, 1, ("interact",))
        ck = events(rows, "cook_started")[0]["data"]
        self.assertEqual([x["id"] for x in ck["items"]], ["I4", "I1", "I2", "I3"])             # sắp theo kind rồi id
        self.assertEqual([x["kind"] for x in ck["items"]], ["bong_dien_dien", "ca_linh", "ca_linh", "ca_linh"])
        left = {x["id"] for x in s.snapshot()["stock"]}
        self.assertEqual(left, {"I5"})                                                        # tiêu đúng các id đang giữ
        self.assertEqual(s.sim.customers[0]["orders"][0]["base_price"], 102)                   # floor(120 × TB / 100)

    def test_final_price_and_tip_use_locked_base_price(self):
        s = session([item("I1", "ca_loc", 55.1)], [cust()])
        sim = s.sim
        sim.pos = list(sim.stoves[0]["pos"])
        step(s, 1, ("interact",))                                                             # nấu (sau hao 1 tick): floor(60×55.0958/100) = 33
        self.assertEqual(sim.customers[0]["orders"][0]["base_price"], 33)
        step(s, 6 * 60)                                                                       # chín
        step(s, 1, ("interact",))                                                             # lấy món
        sim.pos = list(sim.tables[0]["pos"])
        step(s, 1, ("interact",))                                                             # phục vụ ngay -> đủ kiên nhẫn
        paid = events(step(s, sim.eat_max + 2), "paid")[0]["data"]
        self.assertEqual((paid["price"], paid["tip"]), (33, 6))                              # floor(33×0.2) = 6

    def test_serve_on_tick_patience_hits_zero_is_valid(self):
        s = session([item("I1", "ca_loc", 100)], [cust(patience_ticks_left=1)])
        sim = s.sim
        sim.stoves[0].update(state="ready", dish="ca_loc_nuong_trui", jobs=[{"customer_id": "C1", "order": 0}])
        sim.customers[0]["orders"][0].update(state="cooking", items=[])
        sim.pos = list(sim.stoves[0]["pos"])
        step(s, 1, ("interact",))                                                             # lấy món (kiên nhẫn còn 1 -> hết ở bước này)
        self.assertEqual(sim.customers, [])                                                   # bước này khách rời
        # fixture khác: món đã ở khay, đứng ở bàn, kiên nhẫn còn 1 -> giao đúng tick hợp lệ
        s2 = session([item("I1", "ca_loc", 100)], [cust(patience_ticks_left=1)])
        s2.sim.tray = [{"dish_id": "ca_loc_nuong_trui", "customer_id": "C1", "order": 0}]
        s2.sim.customers[0]["orders"][0].update(state="cooking", items=[])
        s2.sim.pos = list(s2.sim.tables[0]["pos"])
        rows = step(s2, 1, ("interact",))
        self.assertEqual([e["name"] for e in rows], ["served"])
        self.assertEqual(s2.sim.customers[0]["state"], "eating")

    def test_scenario_reserved_conflicts_exit_2(self):
        stock = [item("I1", "ca_loc", 100), item("I2", "ca_loc", 100), item("I3", "ca_loc", 29)]
        bad = [[cust(reserved=["I9"])],                                                       # không có trong kho
               [cust(reserved=["I3"])],                                                       # đã ươn
               [cust(reserved=["I1", "I2"])],                                                 # không khớp công thức
               [cust("C1", "T1", reserved=["I1"]), cust("C2", "T2", reserved=["I1"])]]        # dùng chung
        for customers in bad:
            with self.assertRaises(BadInput, msg=str(customers)):
                session(stock, customers)

    def test_scenario_count_stock_rejected_in_v12(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "s.json")
        json.dump({"quan": {"stock": {"ca_loc": 1}}}, open(p, "w", encoding="utf-8"))
        with self.assertRaises(BadInput):
            load_scenario(p, "quan", T12)
        json.dump({"quan": {"stock": [item("I1", "ca_loc", 100)]}}, open(p, "w", encoding="utf-8"))
        load_scenario(p, "quan", T12)

    def test_v11_unchanged_without_freshness_block(self):
        s = Session("quan", BASE, {"stock": {"ca_loc": 2, "bong_sung": 1}, "random_customers": False}, 1)
        step(s, 600)
        self.assertEqual(s.snapshot()["stock"], {"bong_sung": 1, "ca_loc": 2})                # không hao, xuất dạng đếm


if __name__ == "__main__":
    unittest.main()
