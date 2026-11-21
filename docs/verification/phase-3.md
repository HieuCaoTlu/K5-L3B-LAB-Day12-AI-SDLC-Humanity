# Kiểm chứng Phase 3 (Mùa Nước Nổi, contract v1.2) và tổng hợp phần việc của nhóm

Số liệu lấy từ lịch sử git trên `main` (commit `c0da74d`) và lần chạy test cuối. Ghi đúng hiện trạng, chỗ chưa xong ghi rõ.

## 1. Việc từng thành viên đã làm

| Thành viên | Module | Đã làm xong |
|---|---|---|
| Cao Trung Hiếu - 2A202603993 (HieuCaoTlu) | `sim/quan`, contract, tích hợp | Luật quán: khách đến theo lịch, giữ chỗ nguyên liệu, kiên nhẫn, bếp, bưng món, trả tiền, boa, uy tín, đóng ca. Số liệu chuẩn v1.1 (2 bếp, 4 bàn, 6 món, kế hoạch ngày, Shop) và v1.2 (khối `freshness`). Kho cá thể: hao tươi quán 0.25/s, ươn khi tươi dưới 30 (event `spoiled`), giữ chỗ theo id, giá chốt theo độ tươi lúc nấu. Đọc/ghi file kho hai schema (`inventory.py`), kiểm scenario mức luật (mã 2). Bản chơi nhiều ngày ở `chonoi.live` (ông Hai, nâng cấp, đưa món tùy ý). Ghép các nhánh, `CHANGELOG.md`, `docs/contracts/phase-2-quan.md`, `phase-3-quan.md`, test `test_quan_p2.py`, `test_quan_p3.py`. |
| Cao Thanh Tùng - 2A202603982 (TungCTT) | `sim/gather` | Toàn bộ logic buổi sáng qua 3 phase: bơi, oxy và ngạt, Máu và ngất, hái nút, bắt cá, giỏ LIFO, cập bến; cá bơi và tự sinh thêm; Cá Sấu tuần tra làm mất Máu và rơi hàng; nút N5, N6, cá kèo, kèo nèo; giỏ cá thể có độ tươi (hao 0.5/s, `spoiled` ở giỏ). Sáng tạo: bơi nhanh `Shift`, cất nguyên liệu ở bến (`creative`). Test `test_gather.py`. |
| Lê Bá Nguyên - 2A202604100 (lbNGuyen06) | `client/ui` (buổi sáng) | Giao diện và âm thanh buổi sáng: nền pixel art dưới nước, sprite pixel, camera bám người chơi, HUD gỗ, cá sấu / cá kèo / kèo nèo, hiển thị giỏ theo độ tươi (v1.2), nút Làm lại, nhạc nền và hiệu ứng theo sự kiện. Lưu PRD-0 và Test Contract vào `docs/plan`. |
| Lê Phạm Thành Đạt - 2A202604027 (liliustwocout) | `client/ui` (buổi tối), day flow | Giao diện quán pixel art (khách Chiikawa, Hachiware, Usagi, 6 bàn, HUD gỗ, khung luật chơi, nâng cấp, ông Hai). Bộ asset PNG kèm công cụ build/kiểm và route `/assets`. Nối sáng và tối thành một ngày liền mạch: `--mode day` (headless 5 ngày và live), tiệm đồ lặn cạnh bến. Ảnh và test chứng minh cho quán. |

## 2. Bằng chứng

| Hạng mục | Cách kiểm chứng | Kết quả |
|---|---|---|
| Toàn bộ test | `PYTHONPATH=tests:. python -m unittest discover -s tests` | 104 test chạy; 103 đạt; 1 lỗi môi trường: `tests/test_quan_audio.py` cần `numpy`, máy kiểm chưa cài (không liên quan luật chơi) |
| Kho cá thể, schema file kho v1.2 (đọc/ghi, từ chối kho đếm, id trùng, kind lạ, fresh sai) | `tests/test_quan_p3.py` (`FreshInventoryFile`) | Đạt |
| Hao tươi, ngưỡng 30 chính xác theo tick, `spoiled` đúng một lần theo id | `tests/test_quan_p3.py` (`FreshRules`) | Đạt |
| Giữ chỗ theo id (tươi nhất rồi id nhỏ), nhả và giữ lại một lần khi hàng vừa ươn, giá chốt theo tươi và boa | `tests/test_quan_p3.py` | Đạt |
| Giao đúng tick kiên nhẫn chạm 0, đóng ca (khách ăn trả ngay, khách chờ rời không trừ uy tín) | `tests/test_quan_p2.py`, `test_quan_p3.py` | Đạt |
| Bàn giao kho gather sang quán (file, snapshot tick 0, dung sai ±0.01) | `tests/test_smoke_p1.py` (`test_inv_01`) | Đạt |
| Buổi sáng (cá bơi/sinh, Cá Sấu, giỏ cá thể) | `tests/test_gather.py` | Đạt |
| Chế độ nhiều ngày (`--mode day`) | test của Lê Phạm Thành Đạt - 2A202604027 | Đạt |
| Phần sáng tạo không phá lõi | Chỉ bật ở `chonoi.live`; headless dùng `game.contract.json` | Đạt (test lõi vẫn chạy trên số liệu contract) |

Bằng chứng hình ảnh của quán: `docs/proof/quan-assets-preview.png`, `quan-motion-preview.gif`, `quan-png-in-game.png`.

## 3. Ma trận truy vết

Bảng AC chưa điền được: chưa có mã AC-P3-xx từ lab board trong repo. PO điền cột AC khi có.

| AC | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| (chờ mã AC-P3) | | | |

## 4. Chưa xong (ghi trung thực)

- **Mở rộng không bắt buộc, chưa làm:** dòng nước lũ, khách đặt trước, Chợ Chú Sáu.
- **HUD độ tươi:** ở quán hiện chỉ có chữ theo loại (số cá thể, tươi trung bình, số ươn) trong thanh kho; chưa có thanh hay biểu tượng riêng cho từng cá thể.
- **Giả định chưa đối chiếu PRD-0 mục F:** tên luồng RNG chọn món khách, nấu khi đang cầm món, thứ tự sự kiện đóng ca (ghi ở `docs/clarify.md`).
- **Thứ tự nhặt trong giỏ:** đã khớp với giỏ cá thể của gather; id nối tiếp xuyên ngày ở `--mode day` cần kiểm lại với PRD.
- **Tài liệu còn thiếu:** `docs/members/<handle>.md` (mỗi người tự viết phần "AI sai ở đâu", "điều học được"), `docs/retro.md`, `docs/ai-usage-log.md` còn thiếu mục của các phase 1–3.
- README đang có hai mục "Sáng tạo của nhóm"; cần gộp thành một.
- Lịch sử git có commit dưới nhiều tên/email (Lê Phạm Thành Đạt - 2A202604027 dưới tên "Đạt" và "Thành Đạt"; Cao Thanh Tùng - 2A202603982 có hai email; Lê Bá Nguyên - 2A202604100 dưới tên "Le Nguyen" và "lbNGuyen06"): kiểm tra khớp tài khoản GitHub trong `TEAM.md`.

## 5. Đánh giá ngắn

- **Đạt:** lõi Phase 1 và 2 (luật quán, số liệu chuẩn, hai buổi nối với nhau); lõi Phase 3 phần quán và bàn giao kho cá thể.
- **Chưa đạt / chưa làm:** các mục mở rộng Phase 3, bảng AC, ghi chép cá nhân.
- **Điều cần chỉnh cho phase sau:** chốt mã AC sớm, đối chiếu giả định với PRD-0 trước khi code, thống nhất tên commit và email trước khi làm.
