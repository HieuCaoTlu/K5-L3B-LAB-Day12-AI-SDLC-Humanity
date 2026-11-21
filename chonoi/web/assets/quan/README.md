# Asset Quán — pixel nhỏ

Bộ PNG dùng bảng màu và hình khối của giao diện mẫu trong repo, theo ảnh người dùng xác nhận ngày **2026-11-21**. Mỗi pixel gốc thành khối 4×4 px; nhân vật chỉ khoảng 18×25 pixel gốc trong canvas 24×32. Mỗi frame là một file riêng, nền alpha thật.

**87 PNG**: P0 **18**, P1 **56**, P2 **13**. Bao phủ đủ 57 file trong kế hoạch (tính thêm sao rỗng), cộng 30 frame để chuyển động đầy đủ. Danh sách, kích thước, điểm neo và SHA-256 nằm trong [manifest.json](manifest.json).

## Chuyển động và trạng thái

- Út Sen: đứng, đi hai nhịp, đứng bưng tô rỗng, đi bưng tô hai nhịp; đủ `front`, `back`, `side` (phải), `left`. Hướng trái đã xuất thành PNG, không cần lật lúc chạy.
- Khách chó, mèo, vịt, ếch: chờ, vui, giận và hai frame ăn.
- Bếp: nghỉ, ba frame nấu, hai frame chín.
- Nước ba frame, đèn lồng hai frame; khói, lửa, nước bắn mỗi loại ba frame.
- Đồ ăn, nguyên liệu, bàn, đồ trang trí, HUD và tranh kết ca.

[Xem toàn bộ ảnh](../../../../docs/proof/quan-assets-preview.png) · [Xem chuyển động GIF](../../../../docs/proof/quan-motion-preview.gif).

## Tích hợp

Client chọn frame từ `manifest.animations`, theo thời gian hiển thị hoặc tick của snapshot. Ví dụ nhóm `ut_sen.carry_walk.side` có hai đường dẫn và `frame_ms = 125`. Điểm neo chân Út Sen là **[48, 124]** px trong PNG 96×128; điểm neo khách là **[48, 128]**. Khi vẽ về lưới gốc, chia cả kích thước và điểm neo cho 4.

```js
// Sau khi preload toàn bộ Image; root tại /assets/quan/ trên máy chủ live.
const sequence = manifest.animations["ut_sen.walk.front"];
const index = Math.floor(displayTimeMs / sequence.frame_ms) % sequence.frames.length;
const image = loadedImages[sequence.frames[index]];
ctx.imageSmoothingEnabled = false;
ctx.drawImage(image, Math.round(footX - 12), Math.round(footY - 31), 24, 32);
```

Tô đang bưng để trống cho client chèn icon món. Chọn biểu cảm khách từ trạng thái/patience snapshot; giữ cách vẽ hình khối dự phòng khi ảnh không tải được. Các ảnh chỉ phục vụ hiển thị, không đưa vào luật headless. Khung HUD hỗ trợ 9-slice với lề **trái 16, trên 20, phải 16, dưới 20** px.

Riêng tranh kết ca giữ đúng **800×450** theo kế hoạch: hàng pixel cuối chỉ cao 2 px vì 450 không chia hết cho 4.

## Tạo lại và kiểm tra

Cần Python 3 và Pillow (`python3 -m pip install Pillow`).

```bash
python3 tools/quan_assets.py build
python3 tools/quan_assets.py check
python3 tools/quan_assets.py preview
```

Chạy từ thư mục gốc repo. `build` xuất lại các PNG của gói, manifest và ảnh xem thử; `check` kiểm tra hash, alpha, kích thước, lưới 4×4, biên tile nước và frame chuyển động.

Nguồn và quá trình đổi phong cách: [CREDITS](../../../../CREDITS.md), [bằng chứng](../../../../docs/proof/quan-assets.md). Gói này chưa được nối vào các hàm render của game.
