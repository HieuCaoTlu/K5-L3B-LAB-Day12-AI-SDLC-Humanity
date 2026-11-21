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


if __name__ == "__main__":
    unittest.main()
