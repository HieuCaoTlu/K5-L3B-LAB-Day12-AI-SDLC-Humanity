# Clarify — câu hỏi và câu trả lời (PO ghi, cả nhóm dùng chung)

| # | Ngày giờ | Câu hỏi | Trả lời / giả định | Ai quyết |
|---|---|---|---|---|
| A1 | 2026-11-21 | Mức chi tiết và chuyển động của asset Quán? | Người dùng cung cấp ảnh game mẫu: pixel nhỏ, ít chi tiết; ưu tiên đủ chuyển động. Giữ tên/kích thước PNG của kế hoạch, dùng nét và bảng màu canvas mẫu; xuất đứng/đi/bưng món bốn hướng, có PNG hướng trái lật từ phải. | Người dùng xác nhận phong cách; Codex chọn cách xuất frame |
| A2 | 2026-11-21 | Tranh kết ca cao 450 px không chia hết cho lưới 4 px? | Giữ kích thước 800×450 của kế hoạch; hàng pixel cuối cao 2 px. Các sprite còn lại giữ lưới 4×4 đầy đủ. | Quy ước xuất ảnh, nhóm có thể đổi sau |
| 1 | Phase 2 | Tên luồng RNG và cách chọn món khách ("chọn đều theo seed") theo PRD-0 là gì? | Giả định: luồng `customer_dish`, chọn đều trong các món đủ nguyên liệu theo thứ tự id. Chưa đối chiếu PRD-0. | PO hỏi giảng viên |
| 2 | Phase 2 | Có được bắt đầu nấu khi tay đang cầm món không? | Giả định: được (chỉ lấy món mới cần tay trống). | PO hỏi giảng viên |
| 3 | Phase 2 | Thứ tự sự kiện lúc đóng ca (paid / customer_left / quan_end)? | Giả định: `paid` (theo id) → `customer_left reason:closing` → `quan_end`. | PO hỏi giảng viên |
| D1 | Phase 2 | Định dạng JSONL của `--mode day`? | Giả định: dùng chung dạng snapshot/event/end. `tick`/`sim_tick` là tick toàn cục, `phase_tick` tính trong pha (gather/quan); snapshot thêm `day`, `levels`; sự kiện thêm `day_start`, `day_end`, `shop_start`, `shop_buy`, `shop_end`, `game_end`. Dòng `end` có `reason: days_complete` hoặc `tick_limit`. | PO hỏi giảng viên |
| D2 | Phase 2 | Shop ở headless nhận lệnh mua qua đâu? | Giả định: không có input cho Shop; tự mua theo luật cố định: lần lượt bình oxy rồi áo phao, mua bậc kế nếu đủ tiền, lặp tới khi không mua nổi. Shop xong ngay trong tick bàn giao (`shop.max_ticks` chưa dùng). | PO hỏi giảng viên |
| D3 | Phase 2 | Bàn giao pha: sáng → tối → ngày kế? | Giả định: cùng tick sim vừa kết thúc; pha sau bước đầu ở tick kế. Kho từ `gather_end` chuyển nguyên cá thể sang quán; kho dư bỏ sau Shop; tiền/earned/uy tín/cấp nâng cấp giữ qua ngày; oxy/Máu hồi đầy. | PO hỏi giảng viên |
| D4 | Phase 2 | Input (`--inputs`) của `day` tính theo tick nào? | Giả định: tick toàn cục; `move` kế thừa qua ranh giới pha. | PO hỏi giảng viên |
| D5 | Phase 2 | `--mode day` có nhận `--scenario`/`--inventory`/`--inventory-out`? | Giả định: không (mã thoát 2); tiền đầu game = 0, uy tín đầu = `reputation_initial`. | PO hỏi giảng viên |
