# Day 12 — AI SDLC: Quán Ăn Chợ Nổi

> **Làm theo nhóm 4–6 người** · Dùng AI để xây game 2D qua **4 phase** trong **3 giờ**: Út Sen lặn bắt cá, hái rau trên mặt nước rồi tối mở quán phục vụ khách.
> **Yêu cầu từng phase mở đúng mốc giờ tại lab board:** **[Chợ Nổi Lab](https://claude.ai/artifact/E35v787wSx2wDgPTNhMVDg)** (cần đăng nhập claude.ai; có trợ giảng AI cho từng phase).

## Bắt buộc (chỉ có thế)

Cách làm việc kỹ thuật là **tự do** (push thẳng, nhánh + PR, pair, có hay không CI…). Cái bắt buộc:

1. **Một repo chung:** trưởng nhóm **fork** repo này, đặt tên `K5-L3B-LAB-Day12-AI-SDLC-<ten-nhom>`, thêm mọi thành viên làm collaborator (*Settings → Collaborators*, quyền Write) và để repo **public** (giảng viên xem được, không cần mời).
2. **Cả nhóm cùng commit** bằng tài khoản GitHub của mình, mỗi người **≥ 3 commit có nội dung** (làm cặp thì ghi `Co-authored-by:`).
3. **Điền [`TEAM.md`](TEAM.md):** danh sách thành viên + thỏa thuận làm việc nhóm; sửa `team_size` trong [`game.contract.json`](game.contract.json). Commit của người không có trong `TEAM.md` không được tính.
4. **Gắn tag** `phase-1` … `phase-4` đúng hạn; chạy được tại từng tag.
5. **Ghi chép tối thiểu:** `docs/verification/phase-n.md`, `docs/clarify.md`, `docs/ai-usage-log.md`, `docs/retro.md`, `docs/members/<handle>.md`.

## Chạy game (v1.0.0)

**Yêu cầu:** Python ≥ 3.10 (chỉ thư viện chuẩn, không cần `pip install`), trình duyệt hiện đại (Chrome / Edge / Firefox / Safari). Benchmark cần thêm Chrome, Chromium hoặc Edge (tự tìm; hoặc đặt `CHONOI_BROWSER=<đường dẫn>`).

**Từ clone sạch, 3 lệnh (macOS / Linux):**

```bash
git clone https://github.com/HieuCaoTlu/K5-L3B-LAB-Day12-AI-SDLC-Humanity.git
cd K5-L3B-LAB-Day12-AI-SDLC-Humanity
python3 -m chonoi.live --mode day      # mở http://127.0.0.1:8000/ — một Ngày: Lặn & Hái -> Mở Quán -> Shop -> Ngày sau
```

Chơi riêng từng buổi: `python3 -m chonoi.live --mode gather` hoặc `--mode quan` (thêm `--classic` cho quán đúng số liệu contract).

**Điều khiển**

| Phím | Buổi sáng (Lặn & Hái) | Buổi tối (Mở Quán) |
|---|---|---|
| WASD / mũi tên | Bơi | Đi |
| Shift | Bơi nhanh | |
| E | Hái ở mặt nước · cất đồ / cập bến ở bến | Nấu, bưng, phục vụ, mua ở ông Hai |
| Space | Bắt cá (dưới nước) | |
| Q | Kết thúc buổi sáng | |
| Enter | Bắt đầu (màn chờ) · chơi lại khi hết buổi (chế độ một buổi) | Sang Ngày kế khi hết ca |
| M | Bật / tắt âm thanh | Bật / tắt âm thanh |
| H | Chế độ tương phản cao (hoặc mở `/?contrast=high`) | Chế độ tương phản cao |
| L | Nhật ký sự kiện thô | |

Cảnh báo dễ nhận biết (khung chữ + biểu tượng ⚠): **thủy quái gần / đang đuổi**, **oxy sắp hết**, **khách sắp giận**.

**Lệnh kiểm tra và đo**

```bash
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v                       # toàn bộ test (1 lệnh)
python3 -m chonoi.headless --mode gather --seed 1 --ticks 600 --out out.jsonl      # headless (gather | quan | day)
python3 -m chonoi.headless --mode day --seed 1 --ticks 108000 --out day.jsonl      # 5 Ngày liền mạch
python3 -m chonoi.bench --seed 42 --duration 30 --out bench.json                   # benchmark có render (bench_cmd)
python3 -m chonoi.soak --seed 7 --days 10 --out soak.json                          # soak 10 Ngày (soak_cmd)
```

Kết quả đo ở commit phát hành: [`docs/proof/phase-4/`](docs/proof/phase-4/) · ma trận kiểm chứng: [`docs/verification/phase-4.md`](docs/verification/phase-4.md). Chi tiết khung kỹ thuật: [`docs/STARTER.md`](docs/STARTER.md).

## Tự do sáng tạo

Ngoài phần đề yêu cầu, nhóm được **thêm** nhân vật, loài cá/cây, sinh vật, món, bản đồ, cơ chế, câu chuyện, đồ họa, âm nhạc… với ba điều kiện: **không phá phần cố định** (tắt ở headless), ghi mục **"Sáng tạo của nhóm"** trong README của nhóm, và **làm lõi đúng trước**.

### Sáng tạo của nhóm
- **Bơi nhanh (`Shift`) ở buổi sáng (`gather`)**: Khi giữ phím `Shift` trong chế độ chơi trực tiếp (`python3 -m chonoi.live --mode gather`), Út Sen tăng tốc độ bơi gấp **1.5×** (`swim_speed * 1.5`) nhưng tiêu hao oxy nhanh gấp **2×** (`2` tick/tick khi dưới nước).
- **Cất nguyên liệu ở bến (`E`) & tổng kết phiên (`Q`)**: Trong chế độ chơi trực tiếp (`creative=True`), bấm `E` tại bến sẽ cất nguyên liệu từ giỏ vào kho bến (tối đa **20 ô**, chưa kể 12 ô đang giữ trên người) để tiếp tục lặn; bấm `Q` để tổng kết phiên bắt và gộp toàn bộ kho bến + giỏ mang về quán.
- **Bảo đảm đúng Test Contract**: Cả hai tính năng chỉ bật khi `creative=True` ở `chonoi.live`; ở chế độ `headless` (`creative=False`), nút `sprint`/`end_gather` bị vô hiệu hóa hoàn toàn và `E` tại bến vẫn kết thúc ngay `docked` theo đúng Contract v1.2.
- **Bằng chứng lõi vẫn đúng**: `GatherCreativeSprintTest` và `GatherCreativeDockStorageTest` trong `tests/test_gather.py` cùng bộ test smoke/unit/live/team-check chạy PASS.

## Lịch 3 giờ

| Mốc | Phase | Hạn tag |
|---|---|---|
| 0:00 | Phase 1 (PRD-0) | `phase-1` trước 1:00 |
| 1:00 | Phase 2 | `phase-2` trước 1:55 |
| 1:55 | Phase 3 | `phase-3` trước 2:30 |
| 2:30 | Phase 4 | `phase-4` + Release `v1.0.0` trước 3:00 |

Hết giờ mỗi phase thì gắn tag rồi đi tiếp; chỗ chưa xong ghi trung thực trong bằng chứng.

## Đánh giá (100 điểm)

| Hạng mục | Điểm |
|---|---|
| Test tự động ẩn (headless, gồm kiểm tra lại phase trước) | 25 |
| Làm việc nhóm (một repo chung, chia việc, tích hợp, đổi yêu cầu) | 25 |
| Kiểm chứng & bằng chứng | 15 |
| Harness AI (AGENTS.md, skill, nhật ký dùng AI) | 10 |
| Đánh giá & retro | 10 |
| Chất lượng sản phẩm (đúng yêu cầu, mở rộng/sáng tạo) | 10 |
| Demo | 5 |

## Quy định

- Dùng AI thoải mái; **không sao chép repo của nhóm khác**; bằng chứng phải thật.
- Nhân vật, bối cảnh là bản gốc của lab; asset ngoài chỉ dùng CC0/CC-BY/MIT hoặc tự tạo, ghi nguồn trong `CREDITS.md`. Không commit API key, token, `.env`.

## Sáng tạo của nhóm

- Bộ [asset Quán pixel nhỏ](chonoi/web/assets/quan/README.md): Út Sen vẫn là người; khách chó, mèo, vịt, ếch là tạo hình trang trí. Có đủ đi và bưng món bốn hướng, biểu cảm khách, bếp và hiệu ứng chuyển động.
- Các PNG chỉ dùng cho phần hiển thị; headless không tải ảnh và không có luật phụ thuộc vào sprite.
- [Xem ảnh](docs/proof/quan-assets-preview.png) · [Xem chuyển động](docs/proof/quan-motion-preview.gif). Các PNG đang được bàn giao riêng, chưa nối vào renderer.
