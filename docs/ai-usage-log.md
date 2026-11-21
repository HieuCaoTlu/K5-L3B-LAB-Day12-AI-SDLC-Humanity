# Nhật ký dùng AI (theo phase và theo người)

| Phase | Người | Công cụ / model | Việc | Token / chi phí ước tính | Ghi chú (AI sai ở đâu?) |
|---|---|---|---|---|---|
| Asset Quán / UI-UX (chưa xác nhận số phase) | Người yêu cầu + Codex | `imagegen` (built-in), Python/Pillow; skill `ponytail` | Tạo asset theo `docs/plan/assets-quan.md`, sau đó đổi sang pixel nhỏ theo ảnh người dùng; xuất 87 PNG và 27 nhóm trạng thái/chuyển động | Công cụ không trả token/chi phí; không ước đoán | 18 bản thử ban đầu quá chi tiết; thêm 8 bản thử tối giản (3 ảnh sinh lại, 5 frame mới). Loại cả 26 bản thử để dùng nét pixel có sẵn trong canvas, giữ điểm neo và bảng màu giữa các frame. |
| Phase 2 | Cao Trung Hiếu - 2A202603993 + Claude Code | Claude Code (model Sonnet 5.5) | Luật quán, số liệu v1.1, đóng ca, boa, kế hoạch ngày; bản chơi `chonoi.live` (ông Hai, nâng cấp, 6 bếp, 8 bàn); tóm tắt contract | Không có số liệu token | Viết luật khi chưa có PRD-0 mục F; sai boa `round` thay `floor` và thứ tự bếp theo id khách (đối chiếu ticket mới thấy). Khách chỉ tới khi đủ nguyên liệu nên không `--debug-stock` thì trống (phát hiện khi chơi thử). |
| Phase 3 | Cao Trung Hiếu - 2A202603993 + Claude Code | Claude Code (model Sonnet 5.5) | Kho cá thể và độ tươi, giữ chỗ theo id, giá theo tươi, bật contract v1.2, ghép nhánh với gather của Tùng, đưa món tùy ý, giao diện pixel cho bảng/nút | Không có số liệu token | Test kỳ vọng giá sai vì quên hao tươi 1 tick đầu bước (101 thay vì 102, phát hiện nhờ test đỏ). Một lần commit nhầm lên `main`, chuyển sang nhánh riêng trước khi push. |

Ngày **2026-11-21**. Prompt chính ban đầu: “Pixel art game asset … cute, scruffy, expressive … chunky crisp pixels … Vietnamese Mekong floating market boat restaurant at night …”. Sau phản hồi người dùng: “pixel nhỏ thôi không cần phải chi tiết … đầy đủ chuyển động”, prompt chuyển sang mảng phẳng, khoảng 14×22 pixel, tối đa 10 màu.

[Toàn bộ 26 prompt/bản thử](proof/quan-assets-generation-trials.json) ghi đúng ảnh và lý do loại. Không có lỗi sinh ảnh; một lần ghi metadata bằng patch sai định dạng đã được sửa, không sinh lại ảnh vì lỗi đó. Gói cuối được vẽ từ code pixel theo `chonoi/web/mock_quan.html` / các hàm tương ứng trong `index.html`, có thể tạo lại bằng `python3 tools/quan_assets.py build`.

Kiểm chứng: 87 PNG hợp lệ, 27 nhóm trạng thái/chuyển động, **51 test dự án đạt** (gồm hai test âm thanh được thêm song song). Xem [bằng chứng và lệnh chạy](proof/quan-assets.md).
