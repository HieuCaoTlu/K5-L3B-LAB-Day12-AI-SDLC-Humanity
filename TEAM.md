# TEAM

**Tên nhóm:** Humanity  **Số người:** 4  (khớp `team_size` trong `game.contract.json`)

| Thành viên | GitHub handle | Module chính | Vai quy trình | Người dự phòng cho |
|---|---|---|---|---|
| Cao Trung Hiếu (2A202603993) | HieuCaoTlu | `sim/gather` (lát 1) | Integrator (giữ `docs/contracts/`, gắn tag) + QA lead (kiêm) | Lê Bá Nguyên |
| Lê Phạm Thành Đạt (2A202604027) | liliustwocout | `client/ui` | Scrum/Release | Cao Thanh Tùng |
| Cao Thanh Tùng (2A202603982) | TungCTT | `sim/quan` | PO (đầu mối hỏi giảng viên, giữ `docs/clarify.md`) | Lê Phạm Thành Đạt |
| Lê Bá Nguyên (2A202604100) | lbNGuyen06 | `sim/gather` (lát 2) | (không giữ vai riêng) | Cao Trung Hiếu |

**Vai quy trình:** PO (đầu mối hỏi giảng viên, giữ `docs/clarify.md`) · Integrator (giữ `docs/contracts/`, gắn tag) · QA lead · Scrum/Release. Có thể kiêm.

## Công việc từng module

- **`sim/gather`** (buổi sáng): lát 1 (Hiếu) gồm bơi, oxy, ngạt, Máu, giỏ; lát 2 (Nguyên) gồm hái nút, bắt cá, cập bến.
- **`sim/quan`** (buổi tối): khách, bếp, bưng món, tiền, uy tín.
- **`client/ui`**: HUD, đồ họa, âm thanh; chỉ đọc snapshot, không sửa luật.
- **Kiểm chứng:** mỗi người tự test phần mình; Hiếu điền `docs/verification/` và xác nhận test xanh trước khi gắn tag.

## Thỏa thuận làm việc nhóm (điền trong 15 phút kickoff, ≤ 10 dòng)

- Kênh liên lạc: nhóm chat chung (Discord) cho trao đổi nhanh; việc cần lưu vết ghi vào GitHub Issues và `docs/clarify.md`.
- Khi bất đồng về thiết kế: mỗi người nói tối đa 2 phút, không thống nhất thì Integrator (Hiếu) quyết và ghi lý do vào `docs/adr/`.
- Khi ai đó trễ hoặc vướng quá 10 phút: báo ngay trong kênh chat, người dự phòng (cột cuối bảng) nhận việc.
- Giờ standup giữa phase: tại mốc giữa mỗi phase (khoảng phút 30 của Phase 1), 3 phút/người, ghi vào `docs/standup.md`.
- Cách đọc code của nhau: mỗi người đọc lại lát của người dự phòng trước khi gộp; xem PR hoặc xem trực tiếp.
- Cách làm việc với Git: mỗi người làm nhánh ngắn riêng theo module rồi gộp vào `main` qua PR; chạy test trước khi đẩy; Integrator gắn tag `phase-n`; commit có nội dung, làm cặp thì ghi `Co-authored-by:`.
