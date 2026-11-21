# Kiểm chứng Phase 4 (Ticket-04, contract v1.3) — phát hành v1.0.0

Ticket không ghi sẵn mã AC; nhóm đánh mã **AC-P4-xx theo từng mục DoD** của `docs/plan/ticket-04.md`. Kết quả chạy trên máy Windows 11 (Python 3.13, Edge) ở nhánh Phase 4 trước khi gắn tag; Integrator chạy lại trên commit bàn giao và ghi hash vào cuối file.

## Ma trận truy vết

| AC | Yêu cầu | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|---|
| AC-P4-01 | Contract v1.3 khai `bench_cmd`, `soak_cmd` ở gốc | Đọc `game.contract.json`; test `ContractV13` | `game.contract.json`, `tests/test_phase4.py` | Đạt |
| AC-P4-02 | `bench_cmd --seed 42 --duration 30 --out bench.json` chạy cảnh chuẩn, tạo đúng 5 trường | `python3 -m chonoi.bench --seed 42 --duration 30 --out docs/proof/phase-4/bench.json` | [`bench.json`](../proof/phase-4/bench.json): avg 60.0 · 1% low 55.13 · 1800 khung / 30.001 s · load 532 ms | Đạt (đủ cả 3 mốc báo cáo) |
| AC-P4-03 | Công thức `avg_fps`, `p1_low_fps` (ceil 1%, tối thiểu 1 khung), `load_ms`; cờ sai mã 2 | `tests/test_phase4.py` (`BenchMath`) | test | Đạt |
| AC-P4-04 | `soak_cmd --seed 7 --days 10` chạy 10 Ngày gather → quan → shop, lặp D1–D5, `days_completed = days`, `crashes = 0`, lặp lại được | `python3 -m chonoi.soak --seed 7 --days 10 --out docs/proof/phase-4/soak.json`; test `Soak` (7 Ngày, chạy 2 lần so `results`) | [`soak.json`](../proof/phase-4/soak.json): 10/10 Ngày, 0 crash | Đạt |
| AC-P4-05 | Ba cảnh báo có chữ hoặc biểu tượng: thủy quái gần, oxy sắp hết, khách sắp giận | Chơi thử bằng scenario (Út Sen cạnh Cá Sấu M1, oxy 300 tick; khách T1 còn 300 tick kiên nhẫn), đọc `activeWarnings()` qua DevTools | [`warnings-hc-gather.png`](../proof/phase-4/warnings-hc-gather.png), [`warnings-hc-quan.png`](../proof/phase-4/warnings-hc-quan.png) | Đạt |
| AC-P4-06 | Chế độ tương phản cao hoạt động, đã chơi thử cả ba cảnh báo ở chế độ đó | Mở `/?contrast=high` (hoặc phím H), chụp cả hai cảnh | hai ảnh trên (khung đen, chữ vàng, viền nhấp nháy) | Đạt |
| AC-P4-07 | Clone sạch chạy bản có giao diện trong ≤ 3 lệnh; README ghi môi trường, điều khiển, test, headless, bench | Đọc mục "Chạy game (v1.0.0)" trong `README.md`; Đóng gói chạy thử trên máy sạch | `README.md` | Đã viết; **chờ thử clone sạch trên macOS/Linux** |
| AC-P4-08 | Regression P1–P3 còn hiệu lực | `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v` | 113 test: 112 đạt, 1 lỗi môi trường `test_quan_audio` (cần `numpy`, không liên quan luật) | Đạt (trừ lỗi môi trường có sẵn) |
| AC-P4-09 | CHANGELOG theo phase, release notes, CREDITS / LICENSE | Đọc file | `CHANGELOG.md`, `docs/release/v1.0.0.md`, `CREDITS.md` | Đạt; **chưa có `LICENSE`** (ghi trong CREDITS, nhóm cần chốt) |
| AC-P4-10 | Tag `phase-4` + GitHub Release `v1.0.0` (kèm gói chạy được) cùng trỏ một commit trên main trước 3:00 | `git ls-remote --tags origin`; trang Releases | — | **Chưa làm** (Integrator) |
| AC-P4-11 | Retro rà hành động P2, chốt việc tiếp theo; phản tư đủ người | Đọc `docs/retro.md`, `docs/members/` | — | **Chưa làm** (Điều phối retro + từng người) |
| AC-P4-12 | Ghi chép làm rõ và nhật ký AI cập nhật | Đọc file | `docs/clarify.md` (P4-1…P4-4), `docs/ai-usage-log.md` | Đạt (phần Nguyên); các thành viên khác bổ sung |

## Lệnh tái lập

```bash
python3 -m chonoi.bench --seed 42 --duration 30 --out bench.json
python3 -m chonoi.soak --seed 7 --days 10 --out soak.json
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v
python3 -m chonoi.live --mode day        # rồi mở /?contrast=high để thử cảnh báo
```

## Chưa xong / rủi ro (ghi trung thực)

- **Tag:** trên GitHub chưa có tag nào (`phase-1`…`phase-3` cũng chưa có) — Integrator cần gắn bù và gắn `phase-4`.
- **Benchmark** chỉ chạy khi máy có Chrome/Chromium/Edge; FPS bị trần 60 Hz của trình duyệt.
- **Soak** dùng bot đứng yên nên `earned` luôn 0 — chứng minh chạy bền, lặp lại được.
- Mở rộng Phase 4 (bảng xếp hạng, phụ đề SFX) không làm (nhóm 4 người không bắt buộc).

## Commit bàn giao

- Commit gắn `phase-4` / `v1.0.0`: _(Integrator điền hash sau khi gắn tag)_
