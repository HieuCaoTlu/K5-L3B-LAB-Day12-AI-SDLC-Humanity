"""Buổi sáng — Lặn & Hái (`gather`) Phase 2.

Mặt cắt dòng sông nhìn NGANG: vị trí `[x, d]` (x sang phải, `d` độ sâu hướng xuống, d = 0 là mặt nước).
Bao gồm: bơi, oxy, ngạt, Máu, giỏ LIFO, hái nút (gồm kèo nèo), bắt cá, đàn cá bơi + sinh thêm,
Cá Sấu Năm Chèo (patrol / chase / hit / recoil), cập bến và xuất kho.
"""

import math

from ..ids import id_key, sort_by_id
from ..inventory import hold_to_items
from .ramp import ramp_velocity

TICK = 60.0
AXES = ("x", "d")
FRESH_SCALE = 240.0
DOCK_STORAGE_CAPACITY = 20


def _reflect(val, vel, lo, hi):
    while val < lo or val > hi:
        if val < lo:
            val = 2.0 * lo - val
            vel = -vel
        elif val > hi:
            val = 2.0 * hi - val
            vel = -vel
    return val, vel


class GatherSim:
    mode = "gather"
    phase = "gather"

    def __init__(self, tuning, scenario, streams, ids, creative=False):
        t = tuning["gather"]
        self.t = t
        self.rng = streams
        self.ids = ids
        self.creative = bool(creative)
        self._sprinting = False
        self.dock_storage = []
        self.day = scenario.get("day", 1)
        self.phase_tick = 0
        p = scenario.get("player", {})
        self.pos = [float(c) for c in p.get("pos", t["start_pos"])]
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0
        self.heading = float(p.get("heading_deg", t["start_heading_deg"]))
        self.oxygen_max = int(round(t["oxygen_max_s"] * TICK))
        self.oxygen_ticks = p.get("oxygen_ticks", self.oxygen_max)
        self.hp = p.get("hp", t["hp_max"])
        self.zero_oxy_ticks = p.get("zero_oxy_ticks", 0)
        self.invuln_ticks = p.get("invuln_ticks", 0)
        self.catch_cd_ticks = p.get("catch_cd_ticks", 0)
        fr = tuning["freshness"]
        self.fresh_initial = float(fr["initial"])
        self._decay_u = float(fr["gather_decay_per_s"]) * FRESH_SCALE / TICK
        self._spoiled_u = float(fr["spoiled_below"]) * FRESH_SCALE
        self.hold = []
        self._fresh_u = {}
        for it in scenario.get("hold", []):
            ids.reserve(it["id"])
            fresh = float(it["fresh"])
            u = fresh * FRESH_SCALE
            if abs(u - round(u)) < 1e-9:
                u = float(round(u))
            self._fresh_u[it["id"]] = u
            self.hold.append({"id": it["id"], "kind": it["kind"], "fresh": u / FRESH_SCALE})
        self.time_left_ticks = scenario.get("time_left_ticks", int(round(t["duration_s"] * TICK)))

        src_nodes = scenario["nodes"] if "nodes" in scenario else t["nodes"]
        self.nodes = [{"id": n["id"], "kind": n["kind"], "pos": [float(c) for c in n["pos"]],
                       "regrow_ticks": n.get("regrow_ticks", 0)} for n in src_nodes]
        for n in self.nodes:
            ids.reserve(n["id"])

        self.random_fish = scenario.get("random_fish", True)
        self.fish = []
        if "fish" in scenario:
            for f in scenario["fish"]:
                ids.reserve(f["id"])
                self.fish.append({
                    "id": f["id"], "kind": f["kind"],
                    "pos": [float(c) for c in f["pos"]],
                    "heading_deg": float(f.get("heading_deg", 0)),
                    "swim_ticks": int(f.get("swim_ticks", 0)),
                })
        elif self.random_fish:
            if t.get("fish_initial"):
                for f in t["fish_initial"]:
                    ids.reserve(f["id"])
                    self.fish.append({
                        "id": f["id"], "kind": f["kind"],
                        "pos": [float(c) for c in f["pos"]],
                        "heading_deg": float(f.get("heading_deg", 0)),
                        "swim_ticks": 0,
                    })
            else:
                self._spawn_initial_fish()

        self.crocs = []
        crocs_src = scenario.get("crocs", scenario.get("monsters"))
        if crocs_src is not None:
            for c in crocs_src:
                ids.reserve(c["id"])
                wps = [[float(w[0]), float(w[1])] for w in c.get("waypoints", [[60, 24], [64, 24]])]
                pos = [float(x) for x in c.get("pos", wps[0])]
                wp_idx = c.get("wp_index", 1 if len(wps) > 1 and pos == wps[0] else 0)
                self.crocs.append({
                    "id": c["id"],
                    "pos": pos,
                    "waypoints": wps,
                    "wp_index": wp_idx,
                    "state": c.get("state", "patrol"),
                    "recoil_ticks": int(c.get("recoil_ticks", 0)),
                    "recoil_dir": [float(x) for x in c.get("recoil_dir", [1.0, 0.0])],
                })
        else:
            for c in t.get("crocs_initial", []):
                if c.get("min_day", 1) <= self.day:
                    ids.reserve(c["id"])
                    wps = [[float(w[0]), float(w[1])] for w in c["waypoints"]]
                    self.crocs.append({
                        "id": c["id"],
                        "pos": list(wps[0]),
                        "waypoints": wps,
                        "wp_index": 1 if len(wps) > 1 else 0,
                        "state": "patrol",
                        "recoil_ticks": 0,
                        "recoil_dir": [1.0, 0.0],
                    })

        self.money = 0
        self.earned = 0
        self.reputation = tuning["quan"]["reputation_initial"]
        self.done = False
        self.reason = None

    # --- giao diện cho runner -------------------------------------------------
    def inventory_items(self):
        return hold_to_items(self.dock_storage + self.hold)

    def snapshot(self) -> dict:
        snap = {
            "player": {"pos": self.pos, "vel": self.vel, "heading_deg": self.heading,
                       "oxygen_ticks": self.oxygen_ticks, "oxygen_max_ticks": self.oxygen_max,
                       "hp": self.hp, "hp_max": self.t["hp_max"], "zero_oxy_ticks": self.zero_oxy_ticks,
                       "invuln_ticks": self.invuln_ticks, "catch_cd_ticks": self.catch_cd_ticks,
                       "at_surface": self._at_surface()},
            "hold": [dict(it) for it in self.hold], "hold_count": len(self.hold),
            "hold_capacity": self.t["hold_capacity"],
            "nodes": [{"id": n["id"], "pos": n["pos"], "kind": n["kind"],
                       "ready": n["regrow_ticks"] == 0, "regrow_ticks": n["regrow_ticks"]}
                      for n in sort_by_id(self.nodes)],
            "fish": [{"id": f["id"], "pos": f["pos"], "kind": f["kind"], "heading_deg": f["heading_deg"]}
                     for f in sort_by_id(self.fish)],
            "crocs": [{"id": c["id"], "pos": c["pos"], "state": c["state"], "recoil_ticks": c["recoil_ticks"]}
                      for c in sort_by_id(self.crocs)],
        }
        if self.creative:
            snap["dock_storage"] = [dict(it) for it in self.dock_storage]
            snap["dock_count"] = len(self.dock_storage)
            snap["dock_capacity"] = DOCK_STORAGE_CAPACITY
        return snap

    # --- một bước ---------------------------------------------------------------
    def step(self, inp):
        events = []
        # 1. đồng hồ và hàng có sẵn: giảm bộ đếm, nút mọc lại
        self.phase_tick += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        self.invuln_ticks = max(0, self.invuln_ticks - 1)
        self.catch_cd_ticks = max(0, self.catch_cd_ticks - 1)
        for n in sort_by_id(self.nodes):
            if n["regrow_ticks"] > 0:
                n["regrow_ticks"] -= 1
                if n["regrow_ticks"] == 0:
                    events.append(("node_regrown", {"node_id": n["id"]}))
        all_stored = [(it, "hold") for it in self.hold] + [(it, "dock") for it in self.dock_storage]
        for it, loc in sorted(all_stored, key=lambda pair: id_key(pair[0]["id"])):
            iid = it["id"]
            prev_u = self._fresh_u[iid]
            new_u = max(0.0, prev_u - self._decay_u)
            self._fresh_u[iid] = new_u
            it["fresh"] = new_u / FRESH_SCALE
            if prev_u >= self._spoiled_u and new_u < self._spoiled_u:
                events.append(("spoiled", {"item_id": iid, "kind": it["kind"], "location": loc}))
        # 2. bơi + chặn mép + vùng + oxy + ngạt
        self._sprinting = self.creative and bool(inp.held.get("sprint", False))
        was_at_surface = self._at_surface()
        self._move(inp)
        now_at_surface = self._at_surface()
        if was_at_surface and not now_at_surface:
            events.append(("dive", {"pos": list(self.pos)}))
        elif not was_at_surface and now_at_surface:
            events.append(("surface", {"pos": list(self.pos)}))
        if now_at_surface:
            self.oxygen_ticks = min(self.oxygen_max, self.oxygen_ticks + int(self.t["oxygen_refill_per_tick"]))
            self.zero_oxy_ticks = 0
        else:
            prev_oxygen = self.oxygen_ticks
            drain = 2 if self._sprinting else 1
            self.oxygen_ticks = max(0, self.oxygen_ticks - drain)
            if prev_oxygen > 0 and self.oxygen_ticks == 0:
                events.append(("oxygen_empty", {"oxygen_ticks": 0}))
            if self.oxygen_ticks == 0:
                self.zero_oxy_ticks += 1
                if self.zero_oxy_ticks >= int(self.t["choke_interval_ticks"]):
                    self.zero_oxy_ticks = 0
                    self.hp = max(0, self.hp - 1)
                    events.append(("choke", {"hp": self.hp}))
                    if self.hp == 0:
                        lost = list(reversed(self.hold))
                        self.hold.clear()
                        events.append(("faint", {"cause": "choke", "lost": lost, "hp": 0}))
                        self._finish("fainted", events)
                        return events

        # 2b. đàn cá bơi và sinh cá
        self._step_fish()
        spawn_interval = int(self.t.get("fish_spawn_interval_ticks", 360))
        if self.random_fish and self.phase_tick > 0 and self.phase_tick % spawn_interval == 0:
            if len(self.fish) < int(self.t.get("fish_max_count", 12)):
                self._spawn_periodic_fish()

        # 2c. Cá Sấu Năm Chèo di chuyển và kiểm tra chạm
        if self._step_crocs_and_hits(events):
            return events

        # 3. interact: bến trước, rồi hái
        if inp.pressed("interact"):
            if self._in_dock():
                if not self.creative:
                    self._finish("docked", events)
                    return events
                if self.hold:
                    space = DOCK_STORAGE_CAPACITY - len(self.dock_storage)
                    if space <= 0:
                        events.append(("dock_full", {"dock_count": len(self.dock_storage), "dock_capacity": DOCK_STORAGE_CAPACITY}))
                    else:
                        moved = self.hold[:space]
                        self.dock_storage.extend(moved)
                        self.hold = self.hold[space:]
                        events.append(("dock_stored", {
                            "stored": len(moved),
                            "dock_count": len(self.dock_storage),
                            "dock_capacity": DOCK_STORAGE_CAPACITY,
                            "hold_count": len(self.hold),
                        }))
            elif self._at_surface():
                node = self._nearest_in_range(
                    (n for n in self.nodes if n["regrow_ticks"] == 0),
                    self.t["interact_radius"],
                )
                if node is not None:
                    amount = int(self.t["node_yield"])
                    free = int(self.t["hold_capacity"]) - len(self.hold)
                    if free >= amount:
                        self._add_hold_items(node["kind"], amount)
                        node["regrow_ticks"] = int(round(self.t["regrow_s"] * TICK))
                        events.append(("gather", {"node_id": node["id"], "kind": node["kind"], "amount": amount}))
                    else:
                        events.append(("hold_full", {"action": "gather", "node_id": node["id"], "required": amount, "free": free}))
        # 4. bắt cá
        if inp.pressed("catch") and self.catch_cd_ticks == 0 and not self._at_surface():
            fish = self._nearest_in_range(self.fish, self.t["catch_radius"])
            if fish is not None:
                amount = int(self.t["fish_yield"][fish["kind"]])
                free = int(self.t["hold_capacity"]) - len(self.hold)
                if free >= amount:
                    self._add_hold_items(fish["kind"], amount)
                    self.fish.remove(fish)
                    self.catch_cd_ticks = int(round(self.t["catch_cooldown_s"] * TICK))
                    events.append(("fish_caught", {"fish_id": fish["id"], "kind": fish["kind"], "yield": amount}))
                else:
                    events.append(("hold_full", {"action": "catch", "fish_id": fish["id"], "required": amount, "free": free}))
        # 4b. kết thúc phiên bắt bằng phím Q (chỉ creative)
        if self.creative and inp.pressed("end_gather"):
            self._finish("docked", events)
            return events
        # 5. hết giờ
        if self.time_left_ticks <= 0:
            self._finish("time", events)
        return events

    # --- cá & cá sấu ------------------------------------------------------------
    def _spawn_points_by_kind(self):
        xs = self.t.get("fish_spawn_x", [15, 30, 45, 60, 75, 90])
        ds_map = self.t.get("fish_spawn_d", {"ca_linh": [5, 10], "ca_loc": [10, 16], "ca_keo": [24, 27]})
        return {k: [[float(x), float(d)] for x in xs for d in ds] for k, ds in ds_map.items()}

    def _pick_weighted_kind(self, valid_by_kind, rng):
        weights_cfg = self.t.get("fish_spawn_weights", {"ca_linh": 0.4, "ca_loc": 0.3, "ca_keo": 0.3})
        kinds = [k for k in sorted(valid_by_kind) if valid_by_kind[k]]
        if not kinds:
            return None
        weights = [float(weights_cfg.get(k, 1.0)) for k in kinds]
        return rng.choices(kinds, weights=weights, k=1)[0]

    def _spawn_initial_fish(self):
        rng = self.rng.get("fish_spawn")
        count = int(self.t.get("fish_initial_count", 8))
        by_kind = self._spawn_points_by_kind()
        used_geom = set()
        for _ in range(count):
            valid = {k: [pt for pt in pts if tuple(pt) not in used_geom] for k, pts in by_kind.items()}
            kind = self._pick_weighted_kind(valid, rng)
            if kind is None:
                break
            pt = rng.choice(valid[kind])
            used_geom.add(tuple(pt))
            heading = rng.uniform(0.0, 360.0)
            self.fish.append({
                "id": self.ids.new("F"),
                "kind": kind,
                "pos": list(pt),
                "heading_deg": heading,
                "swim_ticks": 0,
            })

    def _spawn_periodic_fish(self):
        rng = self.rng.get("fish_spawn")
        min_dist = float(self.t.get("fish_spawn_min_dist", 1.0))
        by_kind = self._spawn_points_by_kind()
        valid = {
            k: [pt for pt in pts if all(math.dist(pt, f["pos"]) > min_dist for f in self.fish)]
            for k, pts in by_kind.items()
        }
        kind = self._pick_weighted_kind(valid, rng)
        if kind is None:
            return
        pt = rng.choice(valid[kind])
        heading = rng.uniform(0.0, 360.0)
        self.fish.append({
            "id": self.ids.new("F"),
            "kind": kind,
            "pos": list(pt),
            "heading_deg": heading,
            "swim_ticks": 0,
        })

    def _step_fish(self):
        speed = float(self.t.get("fish_speed", 1.5))
        x_lo, x_hi = [float(v) for v in self.t.get("fish_bounds_x", [4, 96])]
        d_bounds = self.t.get("fish_depth_bounds", {"ca_linh": [3, 12], "ca_loc": [8, 20], "ca_keo": [22, 28]})
        turn_interval = int(self.t.get("fish_turn_interval_ticks", 120))
        rng = self.rng.get("fish_swim")
        for f in sort_by_id(self.fish):
            f["swim_ticks"] += 1
            if turn_interval > 0 and f["swim_ticks"] % turn_interval == 0:
                f["heading_deg"] = rng.uniform(0.0, 360.0)
            rad = math.radians(f["heading_deg"])
            vx = speed * math.cos(rad)
            vd = speed * math.sin(rad)
            d_lo, d_hi = [float(v) for v in d_bounds[f["kind"]]]
            nx, vx = _reflect(f["pos"][0] + vx / TICK, vx, x_lo, x_hi)
            nd, vd = _reflect(f["pos"][1] + vd / TICK, vd, d_lo, d_hi)
            f["pos"] = [nx, nd]
            f["heading_deg"] = math.degrees(math.atan2(vd, vx)) % 360

    def _clamp_croc(self, pos):
        bx_lo, bx_hi = [float(v) for v in self.t["bounds"]["x"]]
        cd_lo, cd_hi = [float(v) for v in self.t.get("croc_depth_bounds", [10, 30])]
        pos[0] = min(bx_hi, max(bx_lo, pos[0]))
        pos[1] = min(cd_hi, max(cd_lo, pos[1]))

    def _step_crocs_and_hits(self, events) -> bool:
        if not self.crocs:
            return False
        cd_lo = float(self.t.get("croc_depth_bounds", [10, 30])[0])
        patrol_speed = float(self.t.get("croc_patrol_speed", 1.0))
        chase_speed = float(self.t.get("croc_chase_speed", 3.0))
        detect_r = float(self.t.get("croc_detect_radius", 10.0))
        lose_r = float(self.t.get("croc_lose_radius", 16.0))
        hit_r = float(self.t.get("croc_hit_radius", 1.5))
        recoil_speed = float(self.t.get("croc_recoil_speed", 2.0))
        invuln_dur = int(self.t.get("croc_invuln_ticks", 90))
        recoil_dur = int(self.t.get("croc_recoil_ticks", 60))

        player_deep = self.pos[1] >= cd_lo
        active_for_hit = []

        for c in sort_by_id(self.crocs):
            if c["state"] == "recoil":
                step_d = recoil_speed / TICK
                c["pos"][0] += c["recoil_dir"][0] * step_d
                c["pos"][1] += c["recoil_dir"][1] * step_d
                self._clamp_croc(c["pos"])
                c["recoil_ticks"] -= 1
                if c["recoil_ticks"] <= 0:
                    c["recoil_ticks"] = 0
                    c["state"] = "patrol"
                continue

            dist_p = math.dist(c["pos"], self.pos)
            if c["state"] == "patrol":
                if player_deep and dist_p <= detect_r:
                    c["state"] = "chase"
            elif c["state"] == "chase":
                if not player_deep or dist_p > lose_r:
                    c["state"] = "patrol"

            if c["state"] == "chase":
                if dist_p > 0:
                    step_d = min(chase_speed / TICK, dist_p)
                    c["pos"][0] += ((self.pos[0] - c["pos"][0]) / dist_p) * step_d
                    c["pos"][1] += ((self.pos[1] - c["pos"][1]) / dist_p) * step_d
            else:
                wp = c["waypoints"][c["wp_index"]]
                d_wp = math.dist(c["pos"], wp)
                step_d = patrol_speed / TICK
                if d_wp <= step_d:
                    c["pos"] = [float(wp[0]), float(wp[1])]
                    if len(c["waypoints"]) > 1:
                        c["wp_index"] = (c["wp_index"] + 1) % len(c["waypoints"])
                else:
                    c["pos"][0] += ((wp[0] - c["pos"][0]) / d_wp) * step_d
                    c["pos"][1] += ((wp[1] - c["pos"][1]) / d_wp) * step_d

            self._clamp_croc(c["pos"])
            active_for_hit.append(c)

        if player_deep and self.invuln_ticks == 0:
            hitter = self._nearest_in_range(active_for_hit, hit_r)
            if hitter is not None:
                self.hp = max(0, self.hp - 1)
                drop_n = len(self.hold) // 2
                lost = [self.hold.pop() for _ in range(drop_n)]
                self.invuln_ticks = invuln_dur
                dx = hitter["pos"][0] - self.pos[0]
                dd = hitter["pos"][1] - self.pos[1]
                norm = math.hypot(dx, dd)
                rx, rd = (1.0, 0.0) if norm == 0 else (dx / norm, dd / norm)
                hitter["state"] = "recoil"
                hitter["recoil_ticks"] = recoil_dur
                hitter["recoil_dir"] = [rx, rd]
                events.append(("croc_hit", {
                    "croc_id": hitter["id"], "hp": self.hp, "lost": lost, "invuln_ticks": self.invuln_ticks,
                }))
                if self.hp == 0:
                    lost_all = lost + list(reversed(self.hold))
                    self.hold.clear()
                    events.append(("faint", {"cause": "croc", "lost": lost_all, "hp": 0}))
                    self._finish("fainted", events)
                    return True
        return False

    # --- tiện ích ---------------------------------------------------------------
    def _at_surface(self) -> bool:
        return self.pos[1] <= self.t["surface_depth"]

    def _in_dock(self) -> bool:
        return math.dist(self.pos, self.t["dock_pos"]) <= self.t["dock_radius"]

    def _nearest_in_range(self, entities, radius):
        best = None
        best_key = None
        for e in entities:
            d = math.dist(self.pos, e["pos"])
            if d <= radius:
                k = (d, id_key(e["id"]))
                if best_key is None or k < best_key:
                    best = e
                    best_key = k
        return best

    def _add_hold_items(self, kind, amount):
        for _ in range(amount):
            iid = self.ids.new("I")
            u = self.fresh_initial * FRESH_SCALE
            if abs(u - round(u)) < 1e-9:
                u = float(round(u))
            self._fresh_u[iid] = u
            self.hold.append({"id": iid, "kind": kind, "fresh": u / FRESH_SCALE})

    def _finish(self, reason, events):
        self.done = True
        self.reason = reason
        events.append(("gather_end", {"reason": reason, "inventory": {"items": self.inventory_items()}}))

    def _move(self, inp):
        speed = self.t["swim_speed"] * (1.5 if self._sprinting else 1.0)
        mx, md = inp.move
        self.vel = ramp_velocity(self, (mx * speed, md * speed), int(self.t["ramp_max_ticks"]))
        if (mx, md) != (0.0, 0.0):
            self.heading = math.degrees(math.atan2(md, mx)) % 360
        b = self.t["bounds"]
        for i, axis in enumerate(AXES):
            self.pos[i] += self.vel[i] / TICK
            lo, hi = b[axis]
            if self.pos[i] <= lo:
                self.pos[i] = lo
                self.vel[i] = max(0.0, self.vel[i])
            elif self.pos[i] >= hi:
                self.pos[i] = hi
                self.vel[i] = min(0.0, self.vel[i])
