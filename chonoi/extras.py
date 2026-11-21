"""Sáng tạo của nhóm (chỉ bật ở chonoi.live, KHÔNG dùng ở headless nên không đụng Test Contract).

`build_tuning` trả bản sao số liệu đã chỉnh cho chế độ quán "nhiều ngày": 3 bếp (mỗi bếp một món) + tủ lạnh coca,
6 bàn, ông bán nguyên liệu giá cao, khách đòi nhiều món hơn và đến dày hơn khi qua nhiều ngày.
`game.contract.json` giữ nguyên.
"""

import copy

START_MONEY = 150


def max_dishes(day: int) -> int:
    """Số món tối đa một khách có thể đòi: ngày 1-2: 1; 3-4: 2; 5-6: 3; 7-8: 4; từ ngày 9: 5."""
    return min(5, 1 + (max(1, day) - 1) // 2)


def build_tuning(base: dict, day: int = 1, money: int = START_MONEY) -> dict:
    t = copy.deepcopy(base)
    q = t["quan"]
    q["start_pos"] = [8, 3.5]
    q["stoves"] = [
        {"id": "B1", "pos": [2, 8], "serves": "ca_loc_nuong_trui"},
        {"id": "B2", "pos": [5, 8], "serves": "goi_bong_sung"},
        {"id": "B3", "pos": [8, 8], "serves": "lau_ca_linh_dien_dien"},
        {"id": "B4", "pos": [11, 8], "serves": "coca"},
    ]
    q["tables"] = [{"id": f"T{i + 1}", "pos": [x, z]} for i, (x, z) in
                   enumerate([(4, 5), (8, 5), (12, 5), (4, 2), (8, 2), (12, 2)])]
    q["vendor"] = {"pos": [14.6, 8.4], "name": "Ông Hai",
                   "prices": {"ca_loc": 35, "ca_linh": 20, "bong_dien_dien": 25, "bong_sung": 15, "coca": 12}}
    t["menu"]["coca"] = {"recipe": {"coca": 1}, "cook_s": 1, "price": 20}
    q["first_customer_tick"] = 60  # khách đầu tiên đến sau 1 giây
    q["customer_interval_s"] = max(4.0, 10.0 - 1.0 * (day - 1))  # ngày 1: 10 s/khách; mỗi ngày dày thêm 1 s, tối thiểu 4 s
    q["max_dishes"] = max_dishes(day)
    q["upgrades"] = {
        "tasty": {"name": "Nấu ngon hơn", "icon": "chef", "desc": "Khách trả thêm +15% tiền món mỗi cấp", "costs": [80, 140, 220, 320, 450]},
        "speed": {"name": "Chạy nhanh hơn", "icon": "shoe", "desc": "+15% tốc độ chạy mỗi cấp", "costs": [60, 110, 170, 250]},
        "carry": {"name": "Khay bưng lớn", "icon": "tray", "desc": "Cầm thêm 1 món cùng lúc mỗi cấp", "costs": [120, 220, 350, 500]},
        "batch": {"name": "Bếp công suất lớn", "icon": "flame", "desc": "Mỗi bếp nấu thêm 1 phần cùng lúc mỗi cấp", "costs": [150, 300, 500]},
        "auto": {"name": "Bếp tự động", "icon": "gear", "desc": "Món tự nấu ngay khi có khách gọi, không cần bấm E", "costs": [400]},
    }
    q["rep_pay_scale"] = True  # uy tín thấp thì khách trả ít tiền hơn (0 -> 50%, 3.0 -> 100%, 5 -> 120%)
    q["start_money"] = money
    q["day"] = day
    return t
