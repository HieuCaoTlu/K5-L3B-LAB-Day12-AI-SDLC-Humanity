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
(Nháp từ lịch sử git, PR và ticket; cả nhóm xác nhận lại, nếu nhóm đã họp retro thì thay bằng nội dung thật.)

- **Rà lại hành động Phase 2** ("chốt schema kho giữa gather và quán ngay đầu phase, kéo `main` về nhánh mình trước khi mở PR" — người nhận: Cao Trung Hiếu - 2A202603993):
  - *Chốt schema kho:* **làm được** ở Phase 3 (kho cá thể `{id, kind, fresh}`, ghi trong `CHANGELOG.md`, `docs/contracts/phase-3-quan.md`); tên hàm kho chưa chốt trước nên vẫn phải ghép tay.
  - *Kéo `main` trước khi mở PR:* **làm được một phần.** PR #17 (âm thanh) và PR #18 (Phase 4) đều rebase lên `main` mới nhất trước khi mở, PR #17 merge sạch. Nhưng nhiều người vẫn sửa chung `chonoi/web/index.html` nên PR #9, #17 phải gộp 3 chiều; và có việc làm trùng: chế độ chơi liền mạch được làm hai lần (`--flow` của Nguyên, `--mode day` của Đạt) vì chưa báo nhau ai đang làm gì.
  - *Vì sao vướng:* một file `index.html` chứa cả UI sáng, UI tối, âm thanh; nhóm chưa có bảng "ai đang sửa phần nào".
- **Điều tốt:**
  - Lõi P1–P3 giữ được qua 4 phase: 113 test, regression đạt (trừ 1 lỗi môi trường `numpy`); headless `--mode day` 5 Ngày và soak 10 Ngày chạy bền, lặp lại được.
  - Phase 4 làm song song nhanh: contract v1.3, bench có render (avg 60 FPS, 1% low 55 FPS, load 0.5 s), soak, cảnh báo + tương phản cao, tài liệu phát hành (PR #18).
  - Mỗi PR có mô tả + bằng chứng chạy; phần sáng tạo (đồ họa, âm thanh, nhiều ngày) chỉ bật ở `chonoi.live`, không đụng Test Contract.
- **Điều tệ:**
  - Chưa gắn tag `phase-1`…`phase-3` đúng hạn (trên GitHub chưa có tag nào khi vào Phase 4).
  - Gần như không có review chéo trên GitHub: phần lớn PR do chính tác giả merge; lỗi lọt vào `main` (ví dụ `updateMenu` gọi biến `br` đã xoá, xem dưới).
  - Commit dưới nhiều tên/email; có tác giả **"Hai Duong" (9 commit) chưa khớp ai trong `TEAM.md`** — cần đối chiếu, nếu không commit đó không được tính.
  - Khách ở Quán dùng hình Chiikawa / Hachiware / Usagi (có bản quyền), trái quy định asset của lab.
- **Số liệu** (`git shortlog -sn --no-merges` trên `main` + nhánh Phase 4; PR trên GitHub):

  | Tên trong git | Commit | Tài khoản GitHub | PR |
  |---|---|---|---|
  | Đạt | 14 | liliustwocout | 6 |
  | Hai Duong | 9 | (chưa rõ) | — |
  | HieuCaoTlu | 8 | HieuCaoTlu | 3 |
  | Le Nguyen | 8 | lbNGuyen06 | 4 |
  | Cao Thanh Tùng | 6 | TungCTT | 5 |

  - *Cách đọc code của nhau:* đọc khi tích hợp / gộp xung đột và qua mô tả PR; chưa dùng review/approval của GitHub (0 lượt review).
  - *Token theo người:* chưa đo (ghi "chưa đo" trong `docs/ai-usage-log.md`).
- **Một lần AI sai và cách nhóm xác minh:** khi gộp các nhánh UI, đoạn `updateMenu` trong `index.html` còn dòng `br.style.display = ...` trỏ tới nút "Làm lại" đã bị xoá khỏi HTML → `ReferenceError` ở **mọi khung hình**, phần cập nhật menu phía sau không chạy. Toàn bộ test Python vẫn xanh vì không có test chạy JS. Phát hiện bằng cách mở trang trong Edge headless và đọc lỗi console qua DevTools Protocol; sửa ở PR #16 (bỏ dòng sót). Từ đó mỗi lần đổi UI đều chạy thử trang và kiểm lỗi console trước khi mở PR.
- **Nếu làm lại, đổi gì / hành động tiếp theo:**
  1. Gắn tag ngay khi hết mỗi phase (Integrator), kiểm bằng `git ls-remote --tags origin`.
  2. Tách `index.html` thành file riêng cho sáng / tối / âm thanh, hoặc ghi bảng "ai đang sửa phần nào" trong `docs/standup.md` để tránh làm trùng.
  3. Bắt buộc 1 người khác approve trước khi merge (ruleset `main`), thêm một smoke test mở trang và kiểm lỗi console.
  4. Thống nhất `git config user.name/user.email` theo `TEAM.md` từ phút đầu.
