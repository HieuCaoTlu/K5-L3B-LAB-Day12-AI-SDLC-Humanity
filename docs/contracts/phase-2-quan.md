# Hợp đồng Phase 2 — Quán (sim/quan) và gameplay tóm tắt

Người giữ: Hiếu (`sim/quan`). Nguồn: TICKET-02, Test Contract v1.1. Số liệu nằm trong `game.contract.json` (không hard-code trong luật).

## Gameplay tóm tắt
- **Ngày = sáng lặn hái → tối mở quán → Shop → ngày kế** (5 ngày). Má Tư công bố món cần nấu và nguyên liệu cần lấy đầu ngày.
- **Sáng:** Út Sen bơi, hái bông, bắt cá, giữ oxy, tránh Cá Sấu. Cập bến, hết giờ hoặc ngất thì sang quán với kho đã gom (ngất = kho rỗng).
- **Tối (quán):** 2 bếp, 4 bàn, tay cầm 1 món. Khách đến lúc tick 120 rồi mỗi 900 tick nếu có bàn trống, gọi 1 món trong kế hoạch ngày (đủ nguyên liệu mới gọi, nguyên liệu bị giữ chỗ ngay). Quy trình: `E` ở bếp để nấu → món chín `E` lấy → `E` ở bàn để phục vụ → khách ăn 10 s rồi trả tiền.
- **Kiên nhẫn 60 s:** hết thì khách bỏ đi (−0.5 uy tín, món đang nấu cho họ bị bỏ). Giao khi còn ≥ 50% kiên nhẫn thì boa `floor(giá×0.2)` và +0.2 uy tín. Uy tín 0–5, đầu game 3.0.
- **Đóng ca:** khách đang ăn trả ngay; khách đang chờ rời đi, không trừ uy tín; món và phần giữ bị dọn.
- **Điểm:** `earned + 100 × floor(uy tín)`. Tiền, earned, uy tín, cấp nâng cấp giữ qua ngày; oxy/Máu hồi đầy, giỏ và kho dư bỏ.
- **Shop:** mua bình oxy (200 → 45 s, 400 → 60 s) và áo phao (250 → 4 Máu, 500 → 5 Máu); có hiệu lực từ ngày sau.

## Số liệu quán chuẩn (v1.1)
| Mục | Giá trị |
|---|---|
| Phòng / xuất phát / tốc độ | x∈[0,16], z∈[0,10] / [8,5] / 4.0 m/s |
| Bếp | B1 [2,8], B2 [5,8] |
| Bàn | T1 [9,2], T2 [13,2], T3 [9,6], T4 [13,6] |
| Khách | đầu tick 120, sau đó +900; kiên nhẫn 3600 tick; ăn 600 tick |
| Nguyên liệu | `ca_loc, ca_linh, bong_dien_dien, bong_sung, ca_keo, keo_neo` |

6 món (công thức / nấu / giá): cá lóc nướng trui `ca_loc×1` 6s 60 · gỏi bông súng `bong_sung×2` 4s 40 · lẩu cá linh `ca_linh×3+bong_dien_dien×1` 10s 120 · canh chua `ca_loc+bong_dien_dien` 8s 90 · cá kèo nướng `ca_keo×2` 6s 70 · lẩu mắm `ca_linh×2+ca_keo+keo_neo+bong_dien_dien` 12s 200.

`tuning.day_plan` (5 ngày, nguyên liệu = tổng công thức × số suất) và `tuning.shop` đã có trong `game.contract.json`; số ô cần D1–D5 là 9, 10, 12, 9, 10.

## Giao diện `QuanSim` cho người làm chế độ `day`
Dựng qua `QuanSim(tuning, scenario, streams, ids, inventory)`. Các khóa scenario nội bộ (chỉ `day` dùng, headless độc lập không nhận):
- `money`, `earned`, `reputation`: trạng thái mang từ ngày trước.
- `plan_dishes`: danh sách id món của ngày; khách chỉ gọi trong đó (và đủ nguyên liệu sau phần giữ).
- `inventory`: kho bàn giao từ `gather_end` (đếm theo id).
Sau ca đọc: `sim.stock` (kho dư, bỏ sau Shop), `sim.money`, `sim.earned`, `sim.reputation`, `sim.stats` = `{served, left, tips, sold{món: số}, rep_start}` cho màn DayResult.

## Sự kiện quán
`customer_arrived`, `no_dish`, `cook_started`, `dish_ready`, `dish_picked`, `served`, `paid {customer_id, price, tip}`, `customer_left {customer_id, reputation[, reason:"closing"]}`, `dish_wasted`, `quan_end`. Thứ tự lúc đóng ca: `paid` (khách đang ăn, theo id) → `customer_left reason:closing` (khách chờ) → `quan_end`.

## Đã làm / chưa làm (phần quán)
- Đã làm: số liệu v1.1 và 6 món trong `game.contract.json`, `ca_keo`/`keo_neo` trong `inventory.py`, boa `floor`, bếp lấy đơn cũ nhất theo `order_tick` rồi id bàn, đóng ca, lọc món theo kế hoạch, mang tiền/earned/uy tín, thống kê DayResult, kiểm scenario mức luật (món lạ, giữ chỗ vượt kho khi có `stock`), test `tests/test_quan_p2.py`.
- Chưa làm: chế độ `--mode day` và điều phối pha (người khác), Shop/pause/HUD, mở rộng (món cháy, Chợ), nguyên liệu mới ở buổi sáng (`gather`: N5/N6, cá kèo) và các khóa `gather.*` của v1.1. `contract_version` đã là `1.1` nhưng phần `gather` trong file còn là Phase 1.
- Câu hỏi mở ghi ở `docs/clarify.md` (tên luồng RNG, nấu khi đang cầm món, thứ tự sự kiện đóng ca).
