"""chonoi.live --mode day: ngày bắt đầu từ buổi sáng, kho mang sang quán, hết ca quán sang sáng hôm sau."""

import json
import unittest

from chonoi.contract import load_contract
from chonoi.live import LiveGame
from chonoi.scenario import load_scenario


class LiveDayFlow(unittest.TestCase):
    def make(self, phase):
        t = load_contract()["tuning"]
        return LiveGame("quan", t, load_scenario(None, "quan", t), 1, extras=True, start_phase=phase)

    def snap(self, g):
        return json.loads(g.state_json())

    def test_default_starts_in_quan(self):
        self.assertEqual(self.snap(self.make("quan"))["mode"], "quan")

    def test_day_starts_in_morning_then_enters_quan_with_catch(self):
        g = self.make("gather")
        self.assertEqual(self.snap(g)["mode"], "gather")
        sim = g.session.sim
        sim.done, sim.reason = True, "docked"
        g._enter_quan()
        self.assertEqual(self.snap(g)["mode"], "quan")

    def test_new_game_returns_to_morning(self):
        g = self.make("gather")
        g._enter_quan()
        g.restart(new_game=True)
        s = self.snap(g)
        self.assertEqual((s["mode"], s["day"]), ("gather", 1))

    def test_dive_shop_only_near_dock_in_morning(self):
        g = self.make("gather")
        s = self.snap(g)
        self.assertTrue(s["dive_shop"]["open"])            # Út Sen xuất phát ở bến, trong tầm tiệm
        g.session.sim.pos = [40.0, 0.0]
        g._ver += 1                                         # làm mới cache snapshot
        self.assertFalse(self.snap(g)["dive_shop"]["open"])
        with self.assertRaises(ValueError):
            g.dive_buy("oxygen")
        g.session.sim.pos = [7.0, 3.0]                      # đang lặn: không mua được
        with self.assertRaises(ValueError):
            g.dive_buy("oxygen")
        g._enter_quan()
        self.assertNotIn("dive_shop", self.snap(g))        # ca tối không có tiệm

    def test_dive_shop_buy_applies_now_and_persists(self):
        g = self.make("gather")
        g._carry["money"] = 700
        g.dive_buy("oxygen")
        g.dive_buy("hp")
        s = self.snap(g)
        self.assertEqual((s["player"]["oxygen_max_ticks"], s["player"]["oxygen_ticks"]), (45 * 60, 45 * 60))
        self.assertEqual((s["player"]["hp"], s["player"]["hp_max"]), (4, 4))
        self.assertEqual(s["money"], 250)
        with self.assertRaises(ValueError):
            g.dive_buy("oxygen")          # bậc 2 giá 400 > 250
        g.restart()                       # làm lại buổi sáng: đồ đã mua vẫn còn
        s = self.snap(g)
        self.assertEqual((s["player"]["oxygen_max_ticks"], s["player"]["hp_max"], s["money"]), (45 * 60, 4, 250))
        g.restart(new_game=True)
        self.assertEqual(self.snap(g)["player"]["oxygen_max_ticks"], 30 * 60)


if __name__ == "__main__":
    unittest.main()
