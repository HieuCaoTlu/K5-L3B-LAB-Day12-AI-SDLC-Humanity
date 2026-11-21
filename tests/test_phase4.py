"""Phase 4 (Ticket-04, contract v1.3): soak headless, công thức bench, khai lệnh trong game.contract.json.
Bench thật cần trình duyệt nên ở đây chỉ kiểm phần tính toán và kiểm cờ (không mở trình duyệt)."""

import json
import os
import subprocess
import sys
import unittest

from chonoi.bench import compute
from chonoi.bench import main as bench_main
from chonoi.contract import load_contract
from chonoi.soak import main as soak_main
from chonoi.soak import run_soak
from helpers import Workdir

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ContractV13(unittest.TestCase):
    def test_contract_declares_bench_and_soak(self):
        with open(os.path.join(ROOT, "game.contract.json"), encoding="utf-8") as f:
            c = json.load(f)
        self.assertEqual(c["contract_version"], "1.3")
        self.assertTrue(c["bench_cmd"].strip() and c["soak_cmd"].strip())


class Soak(unittest.TestCase):
    def test_days_complete_no_crash_and_repeatable(self):
        tuning = load_contract()["tuning"]
        a, b = run_soak(tuning, 7, 7), run_soak(tuning, 7, 7)   # > 5 Ngày: kế hoạch D1-D5 phải lặp lại
        self.assertEqual((a["days"], a["days_completed"], a["crashes"]), (7, 7, 0))
        self.assertEqual([r["day"] for r in a["results"]], list(range(1, 8)), "số Ngày tăng liên tục, không quay về 1")
        for r in a["results"]:
            self.assertEqual(set(r), {"day", "earned", "reputation", "score"})
        self.assertEqual(a["results"], b["results"], "cùng seed -> cùng kết quả gameplay")

    def test_cli_writes_json_and_rejects_bad_flags(self):
        with Workdir() as w:
            out = w.path("soak.json")
            self.assertEqual(soak_main(["--seed", "7", "--days", "2", "--out", out]), 0)
            with open(out, encoding="utf-8") as f:
                rep = json.load(f)
            self.assertEqual(set(rep), {"days", "days_completed", "crashes", "results", "duration_s"})
            self.assertEqual(soak_main(["--seed", "7", "--days", "0", "--out", out]), 2)
            self.assertEqual(soak_main(["--seed", "7", "--out", out]), 2)

    def test_soak_cmd_from_contract_runs(self):
        with open(os.path.join(ROOT, "game.contract.json"), encoding="utf-8") as f:
            cmd = json.load(f)["soak_cmd"].split()
        if cmd and cmd[0] in ("python3", "python"):
            cmd[0] = sys.executable
        with Workdir() as w:
            p = subprocess.run(cmd + ["--seed", "1", "--days", "1", "--out", w.path("s.json")], cwd=ROOT, capture_output=True)
            self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))


class BenchMath(unittest.TestCase):
    def test_fields_and_formula(self):
        frames = [10.0] * 99 + [50.0]                          # 100 khung: 1% chậm nhất = 1 khung 50 ms
        r = compute(frames, 1234.4)
        self.assertEqual(set(r), {"avg_fps", "p1_low_fps", "frames", "measured_s", "load_ms"})
        self.assertEqual(r["frames"], 100)
        self.assertAlmostEqual(r["measured_s"], 1.04, places=3)
        self.assertAlmostEqual(r["avg_fps"], 100 / 1.04, places=1)
        self.assertAlmostEqual(r["p1_low_fps"], 20.0, places=2)
        self.assertEqual(r["load_ms"], 1234)

    def test_one_percent_uses_ceil_and_at_least_one_frame(self):
        r = compute([20.0] * 150 + [40.0, 60.0], 0)            # 152 khung -> ceil(1.52) = 2 khung chậm nhất (60, 40)
        self.assertAlmostEqual(r["p1_low_fps"], 1 / 0.05, places=2)
        self.assertAlmostEqual(compute([25.0], 0)["p1_low_fps"], 40.0, places=2)

    def test_bad_flags_exit_2(self):
        with Workdir() as w:
            self.assertEqual(bench_main(["--seed", "42", "--duration", "0", "--out", w.path("b.json")]), 2)
            self.assertEqual(bench_main(["--seed", "42", "--out", w.path("b.json")]), 2)


if __name__ == "__main__":
    unittest.main()
