# Clarify — câu hỏi và câu trả lời (PO ghi, cả nhóm dùng chung)

| # | Ngày giờ | Câu hỏi | Trả lời / giả định | Ai quyết |
|---|---|---|---|---|
| 1 | Phase 2 | Tên luồng RNG và cách chọn món khách ("chọn đều theo seed") theo PRD-0 là gì? | Giả định: luồng `customer_dish`, chọn đều trong các món đủ nguyên liệu theo thứ tự id. Chưa đối chiếu PRD-0. | PO hỏi giảng viên |
| 2 | Phase 2 | Có được bắt đầu nấu khi tay đang cầm món không? | Giả định: được (chỉ lấy món mới cần tay trống). | PO hỏi giảng viên |
| 3 | Phase 2 | Thứ tự sự kiện lúc đóng ca (paid / customer_left / quan_end)? | Giả định: `paid` (theo id) → `customer_left reason:closing` → `quan_end`. | PO hỏi giảng viên |
