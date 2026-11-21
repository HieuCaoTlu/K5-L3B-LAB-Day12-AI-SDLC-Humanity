# Nhật ký dùng AI (theo phase và theo người)

| Phase | Người | Công cụ / model | Việc | Token / chi phí ước tính | Ghi chú (AI sai ở đâu?) |
|---|---|---|---|---|---|
| Asset Quán / UI-UX (chưa xác nhận số phase) | Người yêu cầu + Codex | `imagegen` (built-in), Python/Pillow; skill `ponytail` | Tạo asset theo `docs/plan/assets-quan.md`, sau đó đổi sang pixel nhỏ theo ảnh người dùng; xuất 87 PNG và 27 nhóm trạng thái/chuyển động | Công cụ không trả token/chi phí; không ước đoán | 18 bản thử ban đầu quá chi tiết; thêm 8 bản thử tối giản (3 ảnh sinh lại, 5 frame mới). Loại cả 26 bản thử để dùng nét pixel có sẵn trong canvas, giữ điểm neo và bảng màu giữa các frame. |

Ngày **2026-11-21**. Prompt chính ban đầu: “Pixel art game asset … cute, scruffy, expressive … chunky crisp pixels … Vietnamese Mekong floating market boat restaurant at night …”. Sau phản hồi người dùng: “pixel nhỏ thôi không cần phải chi tiết … đầy đủ chuyển động”, prompt chuyển sang mảng phẳng, khoảng 14×22 pixel, tối đa 10 màu.

[Toàn bộ 26 prompt/bản thử](proof/quan-assets-generation-trials.json) ghi đúng ảnh và lý do loại. Không có lỗi sinh ảnh; một lần ghi metadata bằng patch sai định dạng đã được sửa, không sinh lại ảnh vì lỗi đó. Gói cuối được vẽ từ code pixel theo `chonoi/web/mock_quan.html` / các hàm tương ứng trong `index.html`, có thể tạo lại bằng `python3 tools/quan_assets.py build`.

Kiểm chứng: 87 PNG hợp lệ, 27 nhóm trạng thái/chuyển động, **51 test dự án đạt** (gồm hai test âm thanh được thêm song song). Xem [bằng chứng và lệnh chạy](proof/quan-assets.md).
