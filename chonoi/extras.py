"""Sáng tạo của nhóm (chỉ bật ở chonoi.live, KHÔNG dùng ở headless nên không đụng Test Contract).

`build_tuning` trả bản sao số liệu đã chỉnh cho chế độ quán "nhiều ngày": 6 bếp (mỗi bếp một món) + tủ lạnh coca,
8 bàn trong quán rộng 22 × 12, ông bán nguyên liệu giá cao, khách đòi nhiều món hơn và đến dày hơn khi qua nhiều ngày.
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
    t["freshness"] = {"initial": 100, "gather_decay_per_s": 0.5, "quan_decay_per_s": 0.25, "spoiled_below": 30}  # Mùa Nước Nổi
    q["flex_serve"] = True  # món nấu cho khách này vẫn đưa được cho khách khác gọi cùng món (không phải đưa theo thứ tự)
    q["wait_for_stock"] = True  # khách vẫn tới khi chưa có hàng; mua nguyên liệu ở ông Hai rồi nấu (không cần --debug-stock)
    q["duration_s"] = 90  # ca tối chơi thử rút còn 1 phút 30 giây (contract chuẩn vẫn là 180 s)
    q["bounds"] = {"x": [0, 22], "z": [0, 12]}  # quán mở rộng (contract chuẩn: 16 × 10)
    q["start_pos"] = [11, 4.4]
    serves = ["ca_loc_nuong_trui", "goi_bong_sung", "lau_ca_linh_dien_dien", "canh_chua_ca_loc", "ca_keo_nuong", "lau_mam", "coca"]
    q["stoves"] = [{"id": f"B{i + 1}", "pos": [2.5 + 3 * i, 10], "serves": d} for i, d in enumerate(serves)]   # mỗi món một bếp, coca ở tủ lạnh
    q["tables"] = [{"id": f"T{i + 1}", "pos": [x, z]} for i, (x, z) in
                   enumerate([(3.5, 6.2), (8, 6.2), (12.5, 6.2), (17, 6.2), (3.5, 2.4), (8, 2.4), (12.5, 2.4), (17, 2.4)])]
    q["vendor"] = {"pos": [20.2, 4.4], "name": "Ông Hai",
                   "prices": {"ca_loc": 35, "ca_linh": 20, "bong_dien_dien": 25, "bong_sung": 15, "ca_keo": 22, "keo_neo": 12, "coca": 12}}
    t["menu"]["coca"] = {"recipe": {"coca": 1}, "cook_s": 1, "price": 20, "instant": True}   # lấy liền, bấm E một lần là cầm được
    q["first_customer_tick"] = 60  # khách đầu tiên đến sau 1 giây
    q["customer_interval_s"] = max(3.5, 8.0 - 0.8 * (day - 1))  # ngày 1: 8 s/khách; mỗi ngày dày thêm 0.8 s, tối thiểu 3.5 s
    q["patience_s"] = 50  # kiên nhẫn ngắn hơn chuẩn (60 s) cho khó ngay từ đầu
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
