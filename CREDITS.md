# Credits
Liệt kê asset ngoài (nguồn, giấy phép CC0/CC-BY/MIT) và công cụ AI đã dùng.

## 2026-11-21 — asset Quán / UI-UX

- **87 PNG** tại `chonoi/web/assets/quan/`: bản vẽ pixel do AI (Codex) tạo bằng code, tái sử dụng bảng màu và các khối vẽ nhân vật, bếp, bàn, icon từ giao diện canvas của repo; bổ sung khách mèo/vịt/ếch và các frame chuyển động. Bản cuối theo ảnh game mẫu người dùng cung cấp, còn chờ nhóm kiểm duyệt.
- Đã thử công cụ AI tạo ảnh tích hợp `image_gen` **26 lần**. Các bản thử không được dùng trong gói cuối vì cần pixel nhỏ và các frame đồng nhất hơn. [Prompt và lý do loại](docs/proof/quan-assets-generation-trials.json).
- *Salty Dogs* — Crossbridge Game Studios là nguồn cảm hứng phong cách ban đầu trong kế hoạch: [trang Steam chính thức](https://store.steampowered.com/app/4213930/Salty_Dogs/). Không đưa ảnh chụp hay asset của game đó vào sản phẩm; bản cuối dùng phong cách ảnh mẫu trong repo.
- Giai đoạn bàn giao: **asset Quán / UI-UX**; số phase lab chưa được PO xác nhận trong yêu cầu này. Nhóm bổ sung số phase khi nộp bài.

## Âm thanh (Phần Quán — buổi tối)
- Nhạc nền, không khí sông đêm, jingle kết ca và bộ 16 hiệu ứng âm thanh (SFX) tổng hợp trực tiếp bằng Web Audio API trong `chonoi/web/index.html` / `chonoi/web/mock_quan.html` (và bộ `.wav` xuất riêng trong `chonoi/web/assets/audio/quan/` qua `tools/quan_audio.py`): tự sáng tác & tổng hợp 100%, không sử dụng mẫu âm thanh bản quyền bên ngoài.
