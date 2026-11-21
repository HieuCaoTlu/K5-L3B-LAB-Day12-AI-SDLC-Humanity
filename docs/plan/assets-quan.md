# Kế hoạch asset — Buổi tối (chế độ `quan`) — phong cách pixel art kiểu Salty Dogs

> Dùng để giao cho Codex tạo ảnh. Người phụ trách: UI/UX. Làm theo thứ tự ưu tiên P0 → P1 → P2.
> Tham chiếu phong cách: game *Salty Dogs* (Crossbridge Game Studios). **Chỉ lấy tinh thần**, không chép nhân vật, không đưa ảnh của họ vào game.

## 0. Giới hạn của kế hoạch này (đọc trước)

Tôi **chưa xem được hình ảnh thực tế của Salty Dogs**. Thông tin có được chỉ từ mô tả công khai:

- Thẻ Steam ghi **Pixel Graphics**, trang mô tả "bright colors, odd locals and strange encounters" (màu tươi, dân địa phương kỳ quặc).
- [Gematsu](https://www.gematsu.com/games/salty-dogs) mô tả thợ lặn **mặt chó trông bẩn bẩn dễ thương** với **biểu cảm rất rõ**, thế giới "tactile, cute, and alive", hơi phi lý nhưng đáng yêu.

Nên các điều dưới đây là **suy luận từ mô tả**. Hãy lưu 3–5 ảnh chụp màn hình Salty Dogs vào [`ref/`](ref/) (đặt tên `salty_dogs_1.png`…) và đưa kèm cho Codex ở mọi lần sinh. Ảnh thật sẽ đúng hơn đoạn chữ này. Cũng nên rà lại giấy phép nếu dùng ảnh chụp của họ ngoài việc tham khảo.

## 1. Phong cách (khóa cho mọi ảnh)

**Bối cảnh:** quán ăn trên xuồng giữa chợ nổi miền Tây, buổi tối. Game 2D nhìn từ trên xuống (hơi chéo, kiểu Overcooked), chạy trên web bằng canvas.

**Từ mô tả, giữ những điểm sau:**

- **Pixel art**, điểm ảnh to, rõ khối, **không làm mịn, không chống răng cưa kiểu vector**.
- **Màu tươi, bão hòa vừa cao**, tương phản rõ, nhưng nhìn "ấm" chứ không chói.
- **Nhân vật hài hước, kỳ quặc, dễ thương**: mặt to, mắt/miệng biểu cảm mạnh, dáng "xồm xoàm".
- Thế giới có cảm giác **sờ được, sống động**: có vết bẩn, vết sờn, đồ vật lệch lạc, đầy chi tiết nhỏ.
- Hơi **phi lý**: khách kỳ quặc, đồ ăn kỳ quặc, nhưng không đáng sợ.

**Điều chỉnh cho game này:**

- **Út Sen vẫn là người** (nhân vật của lab, không đổi thành chó). Cho cô biểu cảm to, lanh lợi, tóc/nón xồm xoàm.
- **Khách là dân chợ nổi kỳ quặc**, đề xuất mặt thú: chó, mèo, vịt, ếch… (phần "Sáng tạo của nhóm", chỉ là hình ảnh, không ảnh hưởng luật, tắt ở headless). Bỏ ý này nếu cả nhóm không đồng ý; khi đó vẽ khách là người.
- Cảnh ban đêm: nền nước teal đậm, sàn gỗ nâu ấm, **đèn lồng tạo vệt sáng vàng** ở các cạnh. Vẫn đủ sáng để đọc được chi tiết.

**Lưới pixel:** 1 đơn vị game = **16 px gốc** (native). Xuất ra gấp **4 lần**, tức 64 px/đơn vị, mỗi điểm ảnh gốc là khối 4×4 px. Màn quán = 16 × 10 đơn vị = 256×160 px gốc, xuất 1024×640. Khi hiển thị trong game, dùng `imageSmoothingEnabled = false`.

**Nền trong suốt:** Codex thường không xuất được PNG trong suốt thật. Yêu cầu nền phẳng một màu `#FF00FF` rồi xóa nền. Không dùng nền caro giả.

**Mỗi ảnh một file** (không gộp sprite sheet). Đặt vào `chonoi/web/assets/quan/<nhóm>/<tên>.png`, tên viết thường không dấu, gạch dưới.

**Prompt đầu cho mọi ảnh (dán lặp lại, kèm ảnh tham chiếu Salty Dogs):**
> Pixel art game asset in the spirit of the attached reference (cute, scruffy, expressive, slightly absurd), chunky crisp pixels on a 4x4 px grid, no anti-aliasing, no blur, limited bright-but-warm palette, small grime/wear details for a lived-in feel, top-down 3/4 view, Vietnamese Mekong floating market boat restaurant at night with warm lantern glow, no text, no watermark, single object isolated on a flat #FF00FF background. Match only the style; do not copy any character or item from the reference.

**Cảnh báo kỹ thuật:** công cụ tạo ảnh thường không giữ được lưới pixel thật (điểm ảnh bị lệch hoặc mờ). Sau khi sinh, kiểm tra bằng cách phóng to 400%. Nếu bị mờ, giảm xuống kích thước gốc rồi phóng lại bằng nearest-neighbor (hoặc sinh ở kích thước gốc nhỏ). Nếu vẫn không đạt thì chuyển sang vẽ pixel bằng công cụ khác hoặc chấp nhận pixel art "xấp xỉ".

## 2. Danh sách asset (kích thước là kích thước xuất, gấp 4 lần gốc)

### P0 — cần để chơi được

| # | Tên file | Kích thước | Mô tả |
|---|---|---|---|
| 1 | `env/san_xuong.png` | 1024×640 | Sàn gỗ xuồng lớn nhìn từ trên: ván nâu ấm có vết sờn, mạn viền, vệt sáng vàng ở góc. Chừa chỗ cho bếp (góc trái dưới) và bàn (bên phải). Không có bếp, bàn, người. |
| 2 | `env/nuoc_tile.png` | 256×256 | Nước teal đậm, **lặp liền mạch**, vài vệt sóng pixel sáng, phản chiếu đèn. Không trong suốt. |
| 3 | `char/ut_sen_front.png` | 96×128 | Út Sen nhìn từ phía trước: nón lá hoặc khăn rằn, áo bà ba, tạp dề lem nhem, mặt to biểu cảm, dáng lanh lợi. |
| 4 | `char/ut_sen_back.png` | 96×128 | Cùng nhân vật nhìn từ phía sau. |
| 5 | `char/ut_sen_side.png` | 96×128 | Cùng nhân vật nhìn nghiêng phải (nghiêng trái lật bằng code). |
| 6 | `station/bep_idle.png` | 128×128 | Bếp lò than/củi cũ kỹ, nồi/chảo trống, có vết muội, tắt lửa. |
| 7 | `station/bep_cooking.png` | 128×128 | Cùng bếp, lửa cam, nồi sôi, hơi nước. |
| 8 | `station/bep_ready.png` | 128×128 | Cùng bếp, món chín, nắp mở, ánh xanh lá nhẹ. |
| 9 | `station/ban.png` | 128×128 | Bàn gỗ tròn nhỏ và ghế đẩu, nhìn từ trên, trống, hơi lệch, có vết sờn. |
| 10 | `customer/khach_1.png`, `khach_2.png` | 96×128 | 2 khách đầu: chú chó lái xuồng, bà mèo bán trái cây (hoặc người, tùy quyết định ở mục 1). Dáng ngồi nhìn từ trước, nét mặt **đang chờ**. |
| 11 | `item/ca_loc.png` | 64×64 | Cá lóc, nhìn nghiêng. |
| 12 | `item/ca_linh.png` | 64×64 | Cá linh (vài con cá nhỏ bạc). |
| 13 | `item/bong_dien_dien.png` | 64×64 | Cụm bông điên điển (hoa vàng). |
| 14 | `item/bong_sung.png` | 64×64 | Bông súng (hoa hồng tím). |
| 15 | `dish/ca_loc_nuong_trui.png` | 64×64 | Cá lóc nướng trui trên lá chuối, hơi cháy xém. |
| 16 | `dish/goi_bong_sung.png` | 64×64 | Gỏi bông súng trong tô sứ sứt mẻ. |
| 17 | `dish/lau_ca_linh_dien_dien.png` | 64×64 | Nồi lẩu cá linh điên điển bốc hơi, hoa vàng nổi. |

### P1 — cho cảm giác "sống động, hài hước"

| # | Tên file | Kích thước | Mô tả |
|---|---|---|---|
| 18 | `customer/khach_3.png`, `khach_4.png` | 96×128 | Khách thứ 3 và 4 (vịt đi chợ, ông ếch đội nón). |
| 19 | `customer/khach_<n>_vui.png`, `_gian.png`, `_an.png` | 96×128 | Với mỗi khách: nét mặt vui, giận, đang ăn. Đây là điểm ăn tiền của phong cách "biểu cảm mạnh". Đủ 4 khách × 3 biểu cảm = 12 ảnh (làm 2 khách đầu trước). |
| 20 | `char/ut_sen_walk_front_1.png`, `_2.png` (và `back`, `side`) | 96×128 | 2 khung hình đi bộ cho mỗi hướng (6 ảnh), thay cho nhún bằng code. |
| 21 | `char/ut_sen_cam_do.png` | 96×128 | Út Sen bưng tô/đĩa bằng hai tay (nhìn trước). Món code vẽ đè lên. |
| 22 | `ui/bong_bong_dat_mon.png` | 96×96 | Bong bóng thoại trống (khung pixel, đuôi nhọn), để code chèn icon món. |
| 23 | `ui/emote_vui.png`, `emote_doi.png`, `emote_gian.png` | 64×64 | Biểu cảm nổi trên đầu khách (tim, dấu chấm than, mây đen…). |
| 24 | `ui/dong_xu.png`, `ui/sao_uy_tin.png`, `ui/dong_ho.png` | 48×48 | Icon tiền, sao uy tín (đầy và rỗng), đồng hồ. |
| 25 | `ui/phim_e.png` | 48×48 | Khung phím "E" gợi ý tương tác. |
| 26 | `ui/khung_hud.png` | 512×96 | Khung gỗ ngang pixel cho thanh trên cùng, bên trong trống (9-slice được). |
| 27 | `env/den_long.png` | 64×96 | Đèn lồng đỏ treo ở mạn xuồng, phát sáng vàng. |
| 28 | `env/trang_tri_1.png`, `trang_tri_2.png` | 96×96 | Chum nước sứt, giỏ tre chất rau (trang trí mạn xuồng). |

### P2 — nếu còn thời gian

| # | Tên file | Kích thước | Mô tả |
|---|---|---|---|
| 29 | `fx/khoi.png` | 64×64 | Làn khói/hơi nước pixel trắng (dùng nhiều lần). |
| 30 | `fx/lua.png` | 64×64 | Ngọn lửa pixel nhỏ. |
| 31 | `fx/nuoc_bat.png` | 64×64 | Giọt nước bắn. |
| 32 | `env/xuong_khach.png` | 192×96 | Chiếc xuồng nhỏ của khách cập mạn. |
| 33 | `ui/man_ket_thuc.png` | 800×450 | Tranh kết ca: Út Sen và đám khách kỳ quặc dưới đèn lồng. Không chữ. |

## 3. Quy trình đề xuất

1. Làm **style test** trước: Út Sen (ảnh 3), bếp (ảnh 6), một khách (ảnh 10) và một món (ảnh 15). Phóng 400% để xem lưới pixel có sạch không, rồi mới sinh phần còn lại.
2. Sinh theo nhóm P0. Với mỗi ảnh kiểm tra: đúng lưới pixel, không mờ, nền sạch, đúng kích thước, vẫn nhận ra khi thu nhỏ còn 48 px.
3. Xóa nền (nếu dùng chroma `#FF00FF`) và cắt sát khung, giữ nguyên kích thước canvas ở bảng trên.
4. Lưu đúng tên và thư mục. Ảnh nào lệch phong cách thì sinh lại, không sửa tay.

## 4. Ghi chép bắt buộc của lab

- Thêm vào [`CREDITS.md`](../../CREDITS.md): "Ảnh do công cụ AI (Codex) tạo, nhóm kiểm duyệt", kèm ngày và phase; ghi *Salty Dogs* là nguồn cảm hứng phong cách (không dùng asset của game).
- Ghi vào [`docs/ai-usage-log.md`](../ai-usage-log.md): prompt chính, số lần sinh lại, ảnh nào bị loại và vì sao.
- Mục khách mặt thú nếu giữ: ghi vào README ở phần "Sáng tạo của nhóm".

## 5. Lưu ý khi tích hợp (cho phần UI)

- Client hiện chỉ đọc snapshot và vẽ hình khối tạm (xem `chonoi/web/index.html`). Thay bằng `drawImage` với `imageSmoothingEnabled = false`, và **giữ phương án vẽ hình khối làm dự phòng**.
- Tải trước toàn bộ ảnh rồi mới vẽ, để không nhấp nháy. Làm tròn tọa độ vẽ về số nguyên (hoặc bội của 4 px) để pixel không bị rung.
- Khách có biểu cảm theo trạng thái: kiên nhẫn còn nhiều dùng nét mặt chờ, còn dưới 25% dùng giận, trả tiền dùng vui. Đọc từ snapshot, không đổi luật.
- Sprite không được ảnh hưởng luật. Mọi hiệu ứng sáng tạo phải tắt ở headless.
