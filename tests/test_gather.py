"""Test hộp đen cho chế độ gather (buổi sáng): chuyển vùng mặt nước/dưới nước và tính oxy."""

import json
import unittest

from helpers import Workdir, events, frames, read_jsonl, run_headless, snapshots, write_json


def tuning_gather():
    with open("game.contract.json", encoding="utf-8") as f:
        return json.load(f)["tuning"]["gather"]


def _run_gather(w, scenario_gather, input_frames=None, ticks=1, snapshot_every=1, inventory_out=None, tag="run"):
    sc = write_json(w.path(f"{tag}_sc.json"), {"gather": scenario_gather})
    args = ["--mode", "gather", "--seed", "1", "--ticks", str(ticks),
            "--scenario", sc, "--snapshot-every", str(snapshot_every),
            "--out", w.path(f"{tag}.jsonl")]
    if input_frames is not None:
        inp = write_json(w.path(f"{tag}_in.json"), frames(*input_frames))
        args.extend(["--inputs", inp])
    if inventory_out is not None:
        args.extend(["--inventory-out", inventory_out])
    code, err = run_headless(*args)
    if code != 0:
        raise AssertionError(f"headless failed with code {code}: {err}")
    return read_jsonl(w.path(f"{tag}.jsonl"))


class GatherRegionAndOxygenTest(unittest.TestCase):
    def test_dive_and_surface_events(self):
        g = tuning_gather()
        sd = g["surface_depth"]
        with Workdir() as w:
            rows = _run_gather(
                w,
                {"player": {"pos": [20, sd]}},
                input_frames=[
                    {"tick": 0, "move": [0, 1]},
                    {"tick": 10, "move": [0, -1]},
                    {"tick": 35, "move": [0, 0]},
                ],
                ticks=40,
            )
            snaps = {r["tick"]: r for r in snapshots(rows)}
            dive_evs = events(rows, "dive")
            surf_evs = events(rows, "surface")

            self.assertEqual(len(dive_evs), 1)
            self.assertEqual(len(surf_evs), 1)

            dive_tick = dive_evs[0]["tick"]
            self.assertEqual(dive_evs[0]["data"]["pos"], snaps[dive_tick]["player"]["pos"])
            self.assertTrue(snaps[dive_tick - 1]["player"]["at_surface"])
            self.assertFalse(snaps[dive_tick]["player"]["at_surface"])

            surf_tick = surf_evs[0]["tick"]
            self.assertGreater(surf_tick, dive_tick)
            self.assertEqual(surf_evs[0]["data"]["pos"], snaps[surf_tick]["player"]["pos"])
            self.assertFalse(snaps[surf_tick - 1]["player"]["at_surface"])
            self.assertTrue(snaps[surf_tick]["player"]["at_surface"])
            self.assertTrue(snaps[40]["player"]["at_surface"])

    def test_oxygen_drain_and_empty_once(self):
        with Workdir() as w:
            rows = _run_gather(
                w,
                {"player": {"pos": [20, 10], "oxygen_ticks": 3}},
                ticks=5,
            )
            snaps = {r["tick"]: r for r in snapshots(rows)}
            self.assertEqual([snaps[t]["player"]["oxygen_ticks"] for t in range(6)], [3, 2, 1, 0, 0, 0])
            empty_evs = events(rows, "oxygen_empty")
            self.assertEqual(len(empty_evs), 1)
            self.assertEqual(empty_evs[0]["tick"], 3)
            self.assertEqual(empty_evs[0]["data"], {"oxygen_ticks": 0})

    def test_oxygen_empty_not_emitted_if_already_zero(self):
        with Workdir() as w:
            rows = _run_gather(
                w,
                {"player": {"pos": [20, 10], "oxygen_ticks": 0}},
                ticks=3,
            )
            for s in snapshots(rows):
                self.assertEqual(s["player"]["oxygen_ticks"], 0)
            self.assertEqual(events(rows, "oxygen_empty"), [])

    def test_surface_refill_clamp_and_reset_zero_oxy(self):
        g = tuning_gather()
        sd = g["surface_depth"]
        speed = g["swim_speed"]
        omax = int(round(g["oxygen_max_s"] * 60))
        refill = g["oxygen_refill_per_tick"]
        with Workdir() as w:
            rows_a = _run_gather(
                w,
                {
                    "player": {
                        "pos": [20, sd + speed / 120.0],
                        "vel": [0, -speed],
                        "oxygen_ticks": 0,
                        "zero_oxy_ticks": 10,
                    }
                },
                input_frames=[{"tick": 0, "move": [0, -1]}],
                ticks=1,
                tag="refill",
            )
            self.assertEqual([e["name"] for e in events(rows_a)], ["surface"])
            snap_a = snapshots(rows_a)[-1]["player"]
            self.assertTrue(snap_a["at_surface"])
            self.assertEqual(snap_a["oxygen_ticks"], min(omax, refill))
            self.assertEqual(snap_a["zero_oxy_ticks"], 0)

            rows_b = _run_gather(
                w,
                {"player": {"pos": [20, 0], "oxygen_ticks": omax - 1}},
                ticks=1,
                tag="clamp",
            )
            snap_b = snapshots(rows_b)[-1]["player"]
            self.assertEqual(snap_b["oxygen_ticks"], omax)

    def test_dive_and_oxygen_empty_same_tick_order(self):
        g = tuning_gather()
        sd = g["surface_depth"]
        speed = g["swim_speed"]
        with Workdir() as w:
            rows = _run_gather(
                w,
                {"player": {"pos": [20, sd], "vel": [0, speed], "oxygen_ticks": 1}},
                input_frames=[{"tick": 0, "move": [0, 1]}],
                ticks=1,
            )
            evs = events(rows)
            self.assertEqual([e["name"] for e in evs], ["dive", "oxygen_empty"])
            self.assertTrue(all(e["tick"] == 1 for e in evs))
            snap = snapshots(rows)[-1]["player"]
            self.assertFalse(snap["at_surface"])
            self.assertEqual(snap["oxygen_ticks"], 0)

    def test_surface_on_last_oxygen_tick_refills_without_empty(self):
        g = tuning_gather()
        sd = g["surface_depth"]
        speed = g["swim_speed"]
        omax = int(round(g["oxygen_max_s"] * 60))
        refill = g["oxygen_refill_per_tick"]
        with Workdir() as w:
            rows = _run_gather(
                w,
                {"player": {"pos": [20, sd + speed / 120.0], "vel": [0, -speed], "oxygen_ticks": 1}},
                input_frames=[{"tick": 0, "move": [0, -1]}],
                ticks=1,
            )
            evs = events(rows)
            self.assertEqual([e["name"] for e in evs], ["surface"])
            snap = snapshots(rows)[-1]["player"]
            self.assertTrue(snap["at_surface"])
            self.assertEqual(snap["oxygen_ticks"], min(omax, 1 + refill))


class GatherChokeAndFaintTest(unittest.TestCase):
    def test_choke_timing_from_oxygen_empty(self):
        g = tuning_gather()
        interval = g["choke_interval_ticks"]
        with Workdir() as w:
            rows = _run_gather(
                w,
                {"player": {"pos": [20, 10], "oxygen_ticks": 1, "hp": 3}},
                ticks=interval * 2,
            )
            snaps = {r["tick"]: r["player"] for r in snapshots(rows)}
            self.assertEqual([e["tick"] for e in events(rows, "oxygen_empty")], [1])
            choke_evs = events(rows, "choke")
            self.assertEqual([(e["tick"], e["data"]) for e in choke_evs], [
                (interval, {"hp": 2}),
                (interval * 2, {"hp": 1}),
            ])
            self.assertEqual(snaps[interval - 1]["hp"], 3)
            self.assertEqual(snaps[interval - 1]["zero_oxy_ticks"], interval - 1)
            self.assertEqual(snaps[interval]["hp"], 2)
            self.assertEqual(snaps[interval]["zero_oxy_ticks"], 0)
            self.assertEqual(snaps[interval * 2]["hp"], 1)
            self.assertEqual(snaps[interval * 2]["zero_oxy_ticks"], 0)

    def test_surface_on_choke_tick_avoids_choke(self):
        g = tuning_gather()
        sd = g["surface_depth"]
        speed = g["swim_speed"]
        omax = int(round(g["oxygen_max_s"] * 60))
        refill = g["oxygen_refill_per_tick"]
        interval = g["choke_interval_ticks"]
        with Workdir() as w:
            rows = _run_gather(
                w,
                {
                    "player": {
                        "pos": [20, sd + speed / 120.0],
                        "vel": [0, -speed],
                        "oxygen_ticks": 0,
                        "zero_oxy_ticks": interval - 1,
                        "hp": 3,
                    }
                },
                input_frames=[{"tick": 0, "move": [0, -1]}],
                ticks=1,
            )
            self.assertEqual([e["name"] for e in events(rows)], ["surface"])
            p = snapshots(rows)[-1]["player"]
            self.assertTrue(p["at_surface"])
            self.assertEqual(p["hp"], 3)
            self.assertEqual(p["zero_oxy_ticks"], 0)
            self.assertEqual(p["oxygen_ticks"], min(omax, refill))

    def test_faint_clears_hold_lifo_writes_empty_inventory_and_stops(self):
        g = tuning_gather()
        interval = g["choke_interval_ticks"]
        with Workdir() as w:
            inv = w.path("inv.json")
            rows = _run_gather(
                w,
                {
                    "player": {"pos": [20, 10], "oxygen_ticks": 0, "zero_oxy_ticks": interval - 1, "hp": 1},
                    "hold": ["ca_loc", "bong_sung", "ca_linh"],
                },
                ticks=10,
                inventory_out=inv,
            )
            evs = events(rows)
            self.assertEqual([(e["tick"], e["name"], e["data"]) for e in evs], [
                (1, "choke", {"hp": 0}),
                (1, "faint", {"cause": "choke", "lost": ["ca_linh", "bong_sung", "ca_loc"], "hp": 0}),
                (1, "gather_end", {"reason": "fainted", "inventory": {"items": {}}}),
            ])
            snap = snapshots(rows)[-1]
            self.assertEqual(snap["tick"], 1)
            self.assertEqual(snap["state"], "finished")
            self.assertEqual(snap["player"]["hp"], 0)
            self.assertEqual(snap["hold"], [])
            self.assertEqual(snap["hold_count"], 0)
            self.assertEqual(rows[-1]["type"], "end")
            self.assertEqual(rows[-1]["ticks"], 1)
            self.assertEqual(rows[-1]["reason"], "fainted")
            with open(inv, encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"items": {}})

    def test_faint_stops_step_before_dock_and_time(self):
        g = tuning_gather()
        sd = g["surface_depth"]
        dp = g["dock_pos"]
        dr = g["dock_radius"]
        interval = g["choke_interval_ticks"]
        under_dock_d = sd + min(0.5, max(0.1, dr - sd))
        with Workdir() as w:
            inv = w.path("inv.json")
            rows = _run_gather(
                w,
                {
                    "player": {
                        "pos": [dp[0], under_dock_d],
                        "oxygen_ticks": 0,
                        "zero_oxy_ticks": interval - 1,
                        "hp": 1,
                    },
                    "hold": ["ca_loc"],
                    "time_left_ticks": 1,
                },
                input_frames=[{"tick": 0, "interact": True}],
                ticks=5,
                inventory_out=inv,
            )
            self.assertEqual([e["name"] for e in events(rows)], ["choke", "faint", "gather_end"])
            self.assertEqual(rows[-1]["reason"], "fainted")
            with open(inv, encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"items": {}})


class GatherHarvestAndCatchTest(unittest.TestCase):
    def test_gather_node_boundary_tiebreak_and_regrow_same_tick(self):
        g = tuning_gather()
        r = g["interact_radius"]
        y = g["node_yield"]
        regrow_ticks = int(round(g["regrow_s"] * 60))
        with Workdir() as w:
            rows = _run_gather(
                w,
                {
                    "player": {"pos": [20, 0]},
                    "nodes": [
                        {"id": "N10", "kind": "bong_sung", "pos": [20 + r, 0]},
                        {"id": "N2", "kind": "bong_dien_dien", "pos": [20 - r, 0], "regrow_ticks": 1},
                    ],
                },
                input_frames=[{"tick": 0, "interact": True}],
                ticks=1,
            )
            evs = events(rows)
            self.assertEqual([(e["name"], e["data"]) for e in evs], [
                ("node_regrown", {"node_id": "N2"}),
                ("gather", {"node_id": "N2", "kind": "bong_dien_dien", "amount": y}),
            ])
            snap = snapshots(rows)[-1]
            self.assertEqual(snap["hold"], ["bong_dien_dien"] * y)
            n2 = next(n for n in snap["nodes"] if n["id"] == "N2")
            self.assertFalse(n2["ready"])
            self.assertEqual(n2["regrow_ticks"], regrow_ticks)

    def test_gather_requires_surface_and_dock_has_priority(self):
        g = tuning_gather()
        sd = g["surface_depth"]
        dp = g["dock_pos"]
        with Workdir() as w:
            rows_under = _run_gather(
                w,
                {
                    "player": {"pos": [20, sd + 0.1]},
                    "nodes": [{"id": "N1", "kind": "bong_sung", "pos": [20, 0]}],
                },
                input_frames=[{"tick": 0, "interact": True}],
                ticks=1,
                tag="under",
            )
            self.assertEqual(events(rows_under), [])
            self.assertEqual(snapshots(rows_under)[-1]["hold"], [])

            rows_dock = _run_gather(
                w,
                {
                    "player": {"pos": dp},
                    "nodes": [{"id": "N1", "kind": "bong_sung", "pos": [dp[0], 0]}],
                },
                input_frames=[{"tick": 0, "interact": True}],
                ticks=1,
                tag="dock",
            )
            self.assertEqual([e["name"] for e in events(rows_dock)], ["gather_end"])
            self.assertEqual(rows_dock[-1]["reason"], "docked")
            self.assertEqual(snapshots(rows_dock)[-1]["hold"], [])

    def test_gather_hold_full_keeps_node(self):
        g = tuning_gather()
        cap = g["hold_capacity"]
        y = g["node_yield"]
        with Workdir() as w:
            rows = _run_gather(
                w,
                {
                    "player": {"pos": [20, 0]},
                    "hold": ["ca_loc"] * cap,
                    "nodes": [{"id": "N1", "kind": "bong_sung", "pos": [20, 0]}],
                },
                input_frames=[{"tick": 0, "interact": True}],
                ticks=1,
            )
            self.assertEqual([(e["name"], e["data"]) for e in events(rows)], [
                ("hold_full", {"action": "gather", "node_id": "N1", "required": y, "free": 0}),
            ])
            self.assertTrue(snapshots(rows)[-1]["nodes"][0]["ready"])

    def test_catch_fish_boundary_tiebreak_cooldown_and_reuse(self):
        g = tuning_gather()
        cr = g["catch_radius"]
        cd = int(round(g["catch_cooldown_s"] * 60))
        fy = g["fish_yield"]
        with Workdir() as w:
            inp_frames = [{"tick": 0, "catch": True}, {"tick": 1, "catch": False}]
            if cd >= 3:
                inp_frames.extend([
                    {"tick": cd - 2, "catch": True},
                    {"tick": cd - 1, "catch": False},
                    {"tick": cd, "catch": True},
                ])
            rows = _run_gather(
                w,
                {
                    "player": {"pos": [20, 10]},
                    "fish": [
                        {"id": "F10", "kind": "ca_loc", "pos": [20 + cr, 10]},
                        {"id": "F2", "kind": "ca_linh", "pos": [20 - cr, 10]},
                    ],
                },
                input_frames=inp_frames,
                ticks=cd + 2,
            )
            caught = events(rows, "fish_caught")
            self.assertEqual([(e["tick"], e["data"]) for e in caught], [
                (1, {"fish_id": "F2", "kind": "ca_linh", "yield": fy["ca_linh"]}),
                (1 + cd, {"fish_id": "F10", "kind": "ca_loc", "yield": fy["ca_loc"]}),
            ])
            snap = snapshots(rows)[-1]
            self.assertEqual(snap["fish"], [])
            self.assertEqual(snap["hold"], ["ca_linh"] * fy["ca_linh"] + ["ca_loc"] * fy["ca_loc"])

    def test_catch_hold_full_keeps_fish_no_fallback_no_cooldown(self):
        g = tuning_gather()
        cap = g["hold_capacity"]
        fy = g["fish_yield"]
        with Workdir() as w:
            rows = _run_gather(
                w,
                {
                    "player": {"pos": [20, 10]},
                    "hold": ["bong_sung"] * (cap - 1),
                    "fish": [
                        {"id": "F1", "kind": "ca_linh", "pos": [20, 10]},
                        {"id": "F2", "kind": "ca_loc", "pos": [20.5, 10]},
                    ],
                },
                input_frames=[{"tick": 0, "catch": True}],
                ticks=1,
            )
            self.assertEqual([(e["name"], e["data"]) for e in events(rows)], [
                ("hold_full", {"action": "catch", "fish_id": "F1", "required": fy["ca_linh"], "free": 1}),
            ])
            snap = snapshots(rows)[-1]
            self.assertEqual([f["id"] for f in snap["fish"]], ["F1", "F2"])
            self.assertEqual(snap["player"]["catch_cd_ticks"], 0)

    def test_catch_ignored_at_surface_and_when_no_fish_in_range(self):
        g = tuning_gather()
        sd = g["surface_depth"]
        with Workdir() as w:
            rows_surf = _run_gather(
                w,
                {
                    "player": {"pos": [20, 0]},
                    "fish": [{"id": "F1", "kind": "ca_loc", "pos": [20, sd + 0.2]}],
                },
                input_frames=[{"tick": 0, "catch": True}],
                ticks=1,
                tag="surf",
            )
            self.assertEqual(events(rows_surf), [])
            self.assertEqual(snapshots(rows_surf)[-1]["player"]["catch_cd_ticks"], 0)

            rows_empty = _run_gather(
                w,
                {"player": {"pos": [20, 10]}, "fish": []},
                input_frames=[{"tick": 0, "catch": True}],
                ticks=1,
                tag="empty",
            )
            self.assertEqual(events(rows_empty), [])
            self.assertEqual(snapshots(rows_empty)[-1]["player"]["catch_cd_ticks"], 0)

    def test_catch_on_last_tick_included_in_inventory(self):
        g = tuning_gather()
        fy = g["fish_yield"]
        with Workdir() as w:
            inv = w.path("inv.json")
            rows = _run_gather(
                w,
                {
                    "player": {"pos": [20, 10]},
                    "fish": [{"id": "F1", "kind": "ca_loc", "pos": [20, 10]}],
                    "time_left_ticks": 1,
                },
                input_frames=[{"tick": 0, "catch": True}],
                ticks=5,
                inventory_out=inv,
            )
            self.assertEqual([e["name"] for e in events(rows)], ["fish_caught", "gather_end"])
            self.assertEqual(rows[-1]["reason"], "time")
            with open(inv, encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"items": {"ca_loc": fy["ca_loc"]}})


if __name__ == "__main__":
    unittest.main()
