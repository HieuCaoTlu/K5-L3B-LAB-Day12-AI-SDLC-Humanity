# Bằng chứng — bộ asset Quán pixel nhỏ

Ngày: **2026-11-21**. Giai đoạn công việc: **asset Quán / UI-UX**, chưa được cung cấp số phase lab.

## Kết quả

- **87 PNG** riêng trong `chonoi/web/assets/quan/`: P0 18, P1 56, P2 13; khoảng 50 KB tổng PNG.
- Đủ 57 file theo kế hoạch (bao gồm sao rỗng) và 30 frame bổ sung.
- Út Sen đứng/đi/đứng bưng/đi bưng đủ bốn hướng; khách có bốn biểu cảm và hai frame ăn; bếp, nước, đèn và FX có chuyển động.
- `manifest.json` có **27 nhóm**: 8 nhóm đứng một frame và **19 nhóm chuyển động nhiều frame**, kèm thời lượng, đường dẫn, kích thước và điểm neo.
- [Bảng ảnh](quan-assets-preview.png), [GIF chuyển động](quan-motion-preview.gif), [khung xem chuyển động](quan-motion-preview.png).

## Kiểm chứng

```text
python3 tools/quan_assets.py build
PASS: 87 PNGs; 27 animation groups; sizes, alpha, 4x4 grid, hashes, references and water seams

PYTHONPATH=tests:. python3 -m unittest discover -s tests -v
Ran 51 tests in 15.353s
OK
```

Môi trường Windows của phiên làm việc có Python 3.13.13 do uv quản lý, chưa có `python3` trong PATH. Lần chạy test đầu báo lỗi tìm interpreter ở các test gọi headless. Đã tạo venv tạm trong `tmp/quan-assets/test-venv`, thêm tên `Scripts/python3.exe` từ launcher venv vào PATH và chạy lại **nguyên bộ test**. Không sửa test hoặc contract để xử lý việc này.

Pillow 13.0.0 được cài vào thư mục tạm bị git ignore để tạo/kiểm ảnh; runtime game không cần Pillow. Với PowerShell, `PYTHONPATH` của test đặt là `tests;.`.

Lần kiểm cuối có hai test âm thanh được thêm song song. Đã cài NumPy/SciPy vào cùng thư mục tạm để chạy bộ test chung; `PYTHONPATH` đầy đủ là `tmp/quan-assets/packages;tests;.`. Cả 51 test đều đạt.

Các kiểm tra bổ sung đều đạt: đối chiếu đủ **57 đường dẫn/kích thước** trong kế hoạch; GIF có **6 frame**, lặp vô hạn; các liên kết tài liệu trỏ tới file có thật; máy chủ live phục vụ manifest và PNG với MIME/kích thước đúng.

Đã xem trực tiếp bảng ảnh và khung chuyển động: điểm ảnh rõ, tạo hình nhỏ theo mock, bốn hướng phân biệt, tô bưng rỗng để chèn món. Hướng trái xuất bằng mirror của hướng phải. Tất cả nhóm chuyển động đều có ít nhất hai frame khác nhau theo kiểm tra hash.

Ngoại lệ có chủ đích: tranh kết ca 800×450 có hàng pixel cuối cao 2 px; phần còn lại là lưới 4×4 nguyên vẹn.

## Nguồn và phạm vi

26 bản thử bằng công cụ tạo ảnh tích hợp đã được loại; [prompt/lý do](quan-assets-generation-trials.json). Bộ cuối vẽ bằng các khối pixel nguyên theo palette và hình mẫu trong repo, không dùng bitmap Salty Dogs.

Tác vụ này tạo PNG, manifest, công cụ build/check và tài liệu. Renderer chưa được nối với PNG. Các thay đổi song song trong `chonoi/live.py`, `chonoi/web/index.html`, âm thanh và luật game không thuộc tác vụ asset này và được giữ nguyên.
