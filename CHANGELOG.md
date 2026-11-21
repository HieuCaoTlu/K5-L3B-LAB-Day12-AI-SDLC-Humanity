# Changelog

Ghi theo từng phase của lab. Số liệu chuẩn luôn ở `game.contract.json`; phần sáng tạo chỉ bật ở `chonoi.live`.

## v1.0.0 — Phase 4 (contract v1.3, phát hành)
- **Contract v1.3:** `contract_version:"1.3"`, khai `bench_cmd` (`python3 -m chonoi.bench`) và `soak_cmd` (`python3 -m chonoi.soak`) ở gốc. Gameplay, tuning, kho, JSONL giữ nguyên v1.2.
- **Benchmark có render** (`chonoi/bench.py`): bật server live ở cảnh lặn lõi (seed, cá bơi, Cá Sấu, độ tươi), mở Chrome/Chromium/Edge headless 1280×720, làm nóng 3 s, đo N giây bằng requestAnimationFrame; xuất `avg_fps, p1_low_fps, frames, measured_s, load_ms`.
- **Soak headless** (`chonoi/soak.py`): N Ngày trong một tiến trình (gather → quan → shop), kế hoạch D1–D5 lặp ở Ngày 6+, tiền / uy tín / nâng cấp / id cá thể đi tiếp; bot tất định đứng yên; xuất `days, days_completed, crashes, results, duration_s`.
- **Cảnh báo dễ nhận biết:** khung chữ + biểu tượng cho thủy quái gần / đang đuổi, oxy sắp hết, khách sắp giận. **Chế độ tương phản cao** (phím H hoặc `/?contrast=high`, nhớ lựa chọn).
- **Âm thanh buổi sáng:** nhạc "Sớm mai trên sông" (đàn bầu, D ngũ cung), lớp nhạc dưới nước, môi trường, nhịp căng thẳng, hiệu ứng theo sự kiện; dùng chung bộ máy âm thanh của Quán.
- **Đóng gói:** README chạy từ clone sạch trong 3 lệnh; release notes `docs/release/v1.0.0.md`; bằng chứng `docs/proof/phase-4/`; test `tests/test_phase4.py`. Test đổi: `test_quan_p2` kiểm `contract_version` "1.3" (contract nâng phiên bản, luật không đổi).

## Phase 3 — Mùa Nước Nổi (contract v1.2)
- **BREAKING (Phase 3, contract v1.2 "Mùa Nước Nổi"):** file kho đổi từ đếm theo loại `{"items":{"ca_loc":2}}` sang cá thể `{"items":[{"id":"I1","kind":"ca_loc","fresh":100}]}`; `game.contract.json` có khối `freshness` và `contract_version:"1.2"`. Chạy v1.2 thì file kho đếm bị từ chối (mã 2). Quán: hao tươi 0.25/s, ươn khi `fresh < 30` (event `spoiled`), giữ chỗ theo id (tươi nhất rồi id nhỏ), `base_price` chốt theo độ tươi lúc nấu, `cook_started.data.items`. Cập nhật fixture: đổi kho đếm thành mảng cá thể, `{"items":{}}` thành `{"items":[]}`. Test đổi vì luật mới: `test_smoke_p1` (inv_01: snapshot kho quán là mảng cá thể, dung sai ±0.01), `test_quan_p2` (chạy trên số liệu v1.1 để giữ regression). Gather dùng giỏ cá thể thật (PR của Tùng); gộp với phần quán, `inventory.py` hỗ trợ cả hai schema. Chi tiết: `docs/contracts/phase-3-quan.md`.
- **Âm thanh Quán (buổi tối):** Tích hợp trực tiếp bộ tổng hợp nhạc nền ngũ cung Nam Bộ (`night` ~111 BPM + `rush` ~133 BPM), không khí sông đêm, jingle kết ca và 16 SFX tương tác/bếp/khách/mua bán vào `chonoi/web/index.html` (kèm nút loa pixel trên HUD dưới + bảng chỉnh âm lượng, tắt hoàn toàn ở headless) và `chonoi/web/mock_quan.html`; giữ bộ file `.wav` xuất riêng trong `chonoi/web/assets/audio/quan/` (`tools/quan_audio.py`).
- **Buổi sáng:** giỏ cá thể có độ tươi (hao 0.5/s, `spoiled` ở giỏ); bơi nhanh `Shift`, cất đồ ở bến (`dock_stored` / `dock_full`), `Q` kết thúc buổi.
- **Ngày liền mạch:** `chonoi.live --mode day` (sáng tự sang quán, hết ca sang Ngày kế), headless `--mode day` 5 Ngày (`chonoi/day.py`), Tiệm đồ lặn cạnh bến, màn hình chờ có cốt truyện.
- **Giao diện:** buổi sáng hiển thị giỏ theo độ tươi; Quán dùng bộ asset PNG (tải theo gói, `/assets`).

## Phase 2 — contract v1.1
- **Buổi sáng:** cá bơi và tự sinh thêm, Cá Sấu tuần tra / đuổi / đẩy lùi làm mất Máu và rơi hàng, nút N5–N6, cá kèo, kèo nèo.
- **Quán:** số liệu chuẩn v1.1 (2 bếp, 4 bàn, 6 món, kế hoạch ngày, Shop); bản chơi nhiều ngày ở `chonoi.live` (ông Hai, nâng cấp, đưa món tùy ý). Test `test_quan_p2.py`.
- **Giao diện:** sprite pixel art buổi sáng, camera bám người chơi + bản đồ nhỏ, HUD gỗ, phản hồi sự kiện; Quán giao diện pixel art.

## Phase 1 — PRD-0 (contract v1.0)
- **Lõi:** buổi sáng (bơi, oxy, ngạt, Máu, ngất, hái nút, bắt cá, giỏ LIFO, cập bến, ghi file kho) và buổi tối (khách, giữ chỗ, kiên nhẫn, bếp, bưng, phục vụ, tiền, boa, uy tín), nối qua file kho; headless theo Test Contract v1.0.
- **Giao diện:** nền pixel art buổi sáng (trời, bờ, nước, đá, san hô); `docs/plan/PRD-0.md`.
