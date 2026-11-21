# Retro nhóm

## Phase 1 (nhanh)
(Chờ nhóm điền: tôi không có nội dung retro Phase 1 trong repo.)
- Điều tốt:
- Điều tệ:
- 1 hành động cho Phase 2:

## Phase 2 (nhanh)
(Nháp từ lịch sử git, cả nhóm xác nhận lại.)
- Điều tốt: chia module rõ (gather, quán, giao diện sáng, giao diện tối); mỗi PR có test chạy tự động; contract và CHANGELOG được ghi để các bên đọc cùng một nguồn.
- Điều tệ: nhiều nhánh sửa chung `index.html`, `inventory.py`, `game.contract.json` nên PR bị xung đột khi `main` đi trước (PR của Phase 2 và Phase 3 đều phải ghép lại); commit dưới nhiều tên/email khác nhau; luật quán dựa trên giả định vì chưa có PRD-0 mục F.
- 1 hành động cho Phase 3: chốt schema kho (cá thể) giữa gather và quán ngay đầu phase và kéo `main` về nhánh mình trước khi mở PR. Người nhận: Cao Trung Hiếu - 2A202603993 (Integrator).


## Phase 3 (nhanh)
(Nháp từ lịch sử git và ticket, cả nhóm xác nhận lại; nếu nhóm đã họp retro thì thay bằng nội dung thật.)
- Điều tốt: đổi schema kho từ đếm sang cá thể ({"items":[{id,kind,fresh}]}) mà `main` vẫn chạy: có cầu nối tạm ở gather rồi thay bằng giỏ cá thể thật của gather; test được đổi kèm lý do ghi trong `CHANGELOG.md`.
- Điều tệ: PR quán bị xung đột vì gather cũng sửa `inventory.py` và test cùng lúc; phải ghép tay hai cách làm. Hai bên chưa chốt trước tên hàm kho (`validate_items`, `hold_to_items`).
- Điều rút ra từ lần đổi kho: chốt tên hàm và hình dạng dữ liệu kho trong `docs/contracts/` trước khi hai người cùng viết; kéo `main` về nhánh mình trước khi mở PR.
- Rà hành động Phase 2: "chốt schema kho giữa gather và quán ngay đầu phase": làm được một phần (schema chốt, nhưng tên hàm chưa chốt).

## Phase 4 (cuối)
- Rà lại hành động Phase 2: đã làm chưa? vì sao?
- Điều tốt / điều tệ:
- Số liệu: số commit theo người, cách đọc code của nhau, token theo người:
- Một lần AI sai và cách nhóm phát hiện:
- Nếu làm lại, đổi gì:
