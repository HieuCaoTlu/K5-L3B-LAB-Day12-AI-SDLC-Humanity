# Hợp đồng Phase 3 — Quán (Mùa Nước Nổi, độ tươi)

Người giữ: Hiếu (`sim/quan`). Nguồn: TICKET-03, Test Contract v1.2.

## Cách bật v1.2 (chưa bật trong `game.contract.json`)
Quán bật độ tươi khi số liệu có khối `freshness`. **Chưa thêm vào `game.contract.json`** vì buổi sáng (`gather`) chưa xuất kho cá thể; bật khi cả hai đầu sẵn sàng:
1. Thêm vào `tuning`: `"freshness": {"initial": 100, "gather_decay_per_s": 0.5, "quan_decay_per_s": 0.25, "spoiled_below": 30}` và đổi `contract_version` thành `"1.2"`.
2. `gather` phải: giữ giỏ là mảng cá thể (id I1, I2… nối tiếp xuyên pha/ngày), hao 0.5/s, phát `spoiled` (location `hold`), ghi file kho bằng `inventory.write_inventory_items`, `gather_end.data.inventory` theo schema mới.
3. Khi đó file kho đếm bị từ chối (mã 2) cả hai phía; `read_inventory(path, fresh=True)` tự chọn theo `"freshness" in tuning` (đã nối vào `headless.py` và `live.py`).

## Phần quán đã làm
- **Kho cá thể** `{id, kind, fresh}`; `fresh` là `Fraction` (chính xác ở ngưỡng 30). File kho: `chonoi/inventory.py` (`validate_item_list`, `read_inventory(fresh=True)`, `write_inventory_items`; ghi nguyên tử, sắp theo id, làm tròn 6 chữ số).
- **Hao tươi quán** 0.25/s kể cả hàng đang giữ chỗ; kẹp đáy 0. **Ươn** khi `fresh < 30`: phát `spoiled {item_id, kind, location:"stock"}` đúng một lần, theo id.
- **Giữ chỗ theo id:** mỗi loại lấy cá thể chưa ươn tươi nhất rồi id nhỏ. Phần giữ vừa ươn thì nhả hết và thử giữ lại đúng một lần (theo `order_tick` rồi id bàn); không đủ thì đơn `unfulfillable`, khách chờ tới hết kiên nhẫn.
- **Giá theo tươi:** lúc bắt đầu nấu tiêu đúng các id đang giữ, chốt `base_price = floor(giá × TB fresh / 100)`; boa `floor(0.2 × giá đã chốt)`. `cook_started.data.items` là mảng cá thể sắp theo kind rồi id.
- **Thứ tự tick quán:** đồng hồ → hao tươi/ươn (rồi xử lý giữ chỗ bị ươn) → bếp chín → di chuyển + tối đa một tương tác → kiên nhẫn / trả tiền / đóng ca → (nếu còn giờ) khách mới. Giao đúng tick kiên nhẫn chạm 0 vẫn hợp lệ.
- **Scenario:** `quan.stock` là mảng cá thể (kho đếm → mã 2); `customers[].reserved` là mảng id, kiểm tồn tại / chưa ươn / khớp công thức / không dùng chung → mã 2; bỏ `reserved` thì cấp theo `order_tick` rồi id bàn.
- **Snapshot:** `stock` và `customers[].reserved` theo schema cá thể khi có `freshness`; không có thì giữ dạng đếm như v1.1.
- Test: `tests/test_quan_p3.py` (18 test).

## Chưa làm / thuộc người khác
- Buổi sáng: hao tươi giỏ, `spoiled` ở giỏ, ghi kho cá thể, `lost` là mảng cá thể, dòng lũ (`current`).
- `--mode day` và bàn giao trong cùng tick; Chợ Chú Sáu; khách đặt trước (mở rộng, không bắt buộc với nhóm 4 người).
- `docs/verification/phase-3.md`, `CHANGELOG.md` (breaking change: schema kho), bằng chứng trong `docs/proof/phase-3/`.

## Chỉ ở `chonoi.live` (không ảnh hưởng headless)
Quán rộng 22×12, 7 trạm (6 món + coca), 8 bàn, khách đến dù kho thiếu (chờ mua hàng ở ông Hai), ca tối 90 s, khó hơn từ đầu (8 s/khách, kiên nhẫn 50 s). Chu kỳ ngày: quán → bấm "Ngày tiếp theo" → bắt cá → tự sang quán.
