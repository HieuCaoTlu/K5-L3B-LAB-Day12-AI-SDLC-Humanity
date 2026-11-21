# Clarify — câu hỏi và câu trả lời (PO ghi, cả nhóm dùng chung)

| # | Ngày giờ | Câu hỏi | Trả lời / giả định | Ai quyết |
|---|---|---|---|---|
| A1 | 2026-11-21 | Mức chi tiết và chuyển động của asset Quán? | Người dùng cung cấp ảnh game mẫu: pixel nhỏ, ít chi tiết; ưu tiên đủ chuyển động. Giữ tên/kích thước PNG của kế hoạch, dùng nét và bảng màu canvas mẫu; xuất đứng/đi/bưng món bốn hướng, có PNG hướng trái lật từ phải. | Người dùng xác nhận phong cách; Codex chọn cách xuất frame |
| A2 | 2026-11-21 | Tranh kết ca cao 450 px không chia hết cho lưới 4 px? | Giữ kích thước 800×450 của kế hoạch; hàng pixel cuối cao 2 px. Các sprite còn lại giữ lưới 4×4 đầy đủ. | Quy ước xuất ảnh, nhóm có thể đổi sau |
| 1 | Phase 2 | Tên luồng RNG và cách chọn món khách ("chọn đều theo seed") theo PRD-0 là gì? | Giả định: luồng `customer_dish`, chọn đều trong các món đủ nguyên liệu theo thứ tự id. Chưa đối chiếu PRD-0. | PO hỏi giảng viên |
| 2 | Phase 2 | Có được bắt đầu nấu khi tay đang cầm món không? | Giả định: được (chỉ lấy món mới cần tay trống). | PO hỏi giảng viên |
| 3 | Phase 2 | Thứ tự sự kiện lúc đóng ca (paid / customer_left / quan_end)? | Giả định: `paid` (theo id) → `customer_left reason:closing` → `quan_end`. | PO hỏi giảng viên |
