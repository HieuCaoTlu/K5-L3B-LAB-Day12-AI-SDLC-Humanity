"""Soak headless (Ticket-04, contract v1.3): chạy N Ngày liền trong MỘT tiến trình, gather -> quan -> shop mỗi Ngày.

    python3 -m chonoi.soak --seed 7 --days 10 --out soak.json

- Dựa trên `day.DaySession` (cùng luật / số liệu với `headless --mode day`); kế hoạch D1-D5 lặp lại ở Ngày 6-10.
  Tiền, tổng thu, uy tín, cấp nâng cấp, số Ngày và id cá thể đi tiếp xuyên suốt (cùng Streams, cùng IdAllocator).
- "Bot" tất định: không điều khiển (input rỗng) -> cùng seed cho cùng kết quả gameplay; chỉ `duration_s` là đo thời gian thực.
- Kết quả: {"days", "days_completed", "crashes", "results": [{day, earned, reputation, score}], "duration_s"},
  mỗi phần tử results lấy tại lúc Shop đóng (sự kiện shop_end) của Ngày đó.
- Mã thoát: 0 chạy xong (kể cả khi có crash, đã ghi vào soak.json), 2 cờ sai, 1 không ghi được file.
"""

import argparse
import json
import os
import sys
import time
import traceback

from .contract import load_contract
from .day import DaySession
from .errors import BadInput
from .inputs import InputPlayer


class SoakSession(DaySession):
    """DaySession kéo dài `days` Ngày: Ngày thứ i dùng kế hoạch D((i-1) mod len(plan) + 1), số Ngày vẫn tăng 1..days."""

    def __init__(self, tuning, seed, days):
        super().__init__(tuning, seed)          # dựng buổi sáng Ngày 1 bằng kế hoạch D1
        base = list(self.plan)
        self.plan = [dict(base[i % len(base)], day=i + 1) for i in range(days)]


def run_soak(tuning, seed, days):
    sess = SoakSession(tuning, seed, days)
    player = InputPlayer([])                    # bot tất định: đứng yên
    results, crashes, started = [], 0, time.perf_counter()
    day_state = {}
    try:
        while not sess.done:
            for row in sess.step(player.advance(sess.tick)):
                if row["name"] == "day_end":
                    day_state = row["data"]
                elif row["name"] == "shop_end":   # Shop đóng: chốt kết quả Ngày
                    d = row["data"]["day"]
                    earned, rep = day_state.get("earned", sess.earned), day_state.get("reputation", sess.reputation)
                    results.append({"day": d, "earned": earned, "reputation": rep, "score": sess._score(earned, rep)})
    except Exception:  # crash trong luật: ghi nhận, dừng lượt, vẫn xuất soak.json
        crashes = 1
        sys.stderr.write(traceback.format_exc())
    return {"days": days, "days_completed": len(results), "crashes": crashes, "results": results,
            "duration_s": round(time.perf_counter() - started, 3)}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="chonoi.soak", description="Soak headless: N Ngày liền trong một tiến trình.")
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--days", type=int, required=True)
    p.add_argument("--out", required=True)
    try:
        a = p.parse_args(argv)
    except SystemExit as e:
        return 2 if e.code else 0
    try:
        if a.days < 1:
            raise BadInput("--days phải là số nguyên dương")
        tuning = load_contract()["tuning"]
    except BadInput as e:
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2
    report = run_soak(tuning, a.seed, a.days)
    tmp = a.out + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        os.replace(tmp, a.out)
    except OSError as e:
        sys.stderr.write(f"không ghi được {a.out}: {e}\n")
        return 1
    print(f"soak: {report['days_completed']}/{report['days']} Ngày, crashes={report['crashes']}, {report['duration_s']} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
