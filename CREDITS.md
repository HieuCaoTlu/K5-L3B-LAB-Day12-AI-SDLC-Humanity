# Credits
Liệt kê asset ngoài (nguồn, giấy phép CC0/CC-BY/MIT) và công cụ AI đã dùng.

## 2026-11-21 — asset Quán / UI-UX

- **87 PNG** tại `chonoi/web/assets/quan/`: bản vẽ pixel do AI (Codex) tạo bằng code, tái sử dụng bảng màu và các khối vẽ nhân vật, bếp, bàn, icon từ giao diện canvas của repo; bổ sung khách mèo/vịt/ếch và các frame chuyển động. Bản cuối theo ảnh game mẫu người dùng cung cấp, còn chờ nhóm kiểm duyệt.
- Đã thử công cụ AI tạo ảnh tích hợp `image_gen` **26 lần**. Các bản thử không được dùng trong gói cuối vì cần pixel nhỏ và các frame đồng nhất hơn. [Prompt và lý do loại](docs/proof/quan-assets-generation-trials.json).
- *Salty Dogs* — Crossbridge Game Studios là nguồn cảm hứng phong cách ban đầu trong kế hoạch: [trang Steam chính thức](https://store.steampowered.com/app/4213930/Salty_Dogs/). Không đưa ảnh chụp hay asset của game đó vào sản phẩm; bản cuối dùng phong cách ảnh mẫu trong repo.
- Giai đoạn bàn giao: **asset Quán / UI-UX**; số phase lab chưa được PO xác nhận trong yêu cầu này. Nhóm bổ sung số phase khi nộp bài.

## Âm thanh (Phần Quán — buổi tối)
- Nhạc nền, không khí sông đêm, jingle kết ca và bộ 16 hiệu ứng âm thanh (SFX) tổng hợp trực tiếp bằng Web Audio API trong `chonoi/web/index.html` / `chonoi/web/mock_quan.html` (và bộ `.wav` xuất riêng trong `chonoi/web/assets/audio/quan/` qua `tools/quan_audio.py`): tự sáng tác & tổng hợp 100%, không sử dụng mẫu âm thanh bản quyền bên ngoài.

## Buổi sáng (Lặn & Hái) — đồ họa và âm thanh
- **Đồ họa:** nền pixel art (trời, bờ dừa, nhà sàn, ghe, nước, đá, san hô, rêu), sprite Út Sen, cá lóc, cá linh, cá kèo, Cá Sấu, điên điển, bông súng, kèo nèo và HUD gỗ đều **vẽ bằng code canvas** trong `chonoi/web/index.html` (do AI Claude Code viết theo yêu cầu của nhóm). Không dùng ảnh hay asset bên ngoài. Ảnh tham khảo bố cục dưới nước (ảnh stock có watermark do người dùng gửi) chỉ dùng để lấy ý tưởng, không đưa vào sản phẩm.
- **Âm thanh:** nhạc "Sớm mai trên sông", lớp nhạc dưới nước, môi trường và hiệu ứng **tổng hợp trực tiếp bằng Web Audio API**, dùng chung bộ máy âm thanh của Quán. Không dùng mẫu âm thanh bên ngoài.
- **Công cụ AI:** Claude Code (Anthropic) hỗ trợ viết code đồ họa, âm thanh, benchmark/soak Phase 4; nhóm chơi thử, nghe thử và kiểm chứng (xem `docs/ai-usage-log.md`).

## Giấy phép
- Repo chưa có file `LICENSE`. Khung `chonoi/` do giảng viên cung cấp cho lab; phần nhóm viết và toàn bộ asset tự tạo ở trên. Nhóm cần chốt giấy phép (ví dụ MIT) trước khi phát hành ngoài lớp học.

