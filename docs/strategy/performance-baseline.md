# Baseline hiệu năng

Ngày: 2026-11-21 · Trạng thái: **chờ duyệt** · Thuộc [MASTER-IMPLEMENTATION-PLAN.md](MASTER-IMPLEMENTATION-PLAN.md)

Nhãn: MEASURED · OBSERVED · INFERRED · UNKNOWN (xem [master-audit.md](master-audit.md)).

## 1. Phương pháp
- **Dữ liệu:** `data/memory.db`, mở **chỉ-đọc** (`sqlite3.connect('file:data/memory.db?mode=ro', uri=True)`). Không dùng `bot.memory.Memory` hay `tools/baseline.py`, vì cả hai ghi schema vào DB thật (master-audit §4.3).
- **Khoảng dữ liệu:** 2026-11-19 00:29 → 2026-11-21 12:05.
  - Phần lớn lần ghé ở chế độ smart rơi vào 2026-11-20 20:23 → 2026-11-21 12:08.
  - Log có tên luồng `[#idx]` chỉ từ 2026-11-20 20:23.
- **Log:** `logs/bot-20261121.log` cho phân rã khởi động (n = 141 lần ghé). Vì log không ghi ngày, chỉ dùng log trong một ngày.
- **Benchmark CPU offline:** `logs/capture-540-city.png`, 10 lần lặp, lấy trung vị, trên máy chạy bot.
- **Hồi quy:** `tools/check_screens.py` (13/13, 189 ms/ảnh), `tools/check_tutorial.py` (34/34).
- **Không** bật LDPlayer trong lượt audit này, nên mọi số đo ADB đều là UNKNOWN.

## 2. Số đo hiện có

### 2.1 Thời gian máy và lần ghé
| Chỉ số | Giá trị | Nhãn | Truy vấn / nguồn |
|---|---|---|---|
| Tổng giờ VM bật | 31,6 h / 257 lần ghé | MEASURED | Q1 |
| Giờ trong bước | 25,5 h | MEASURED | Q2 |
| Giờ VM bật / ngày | #1 9,6 · #0 2,3 · #2 2,1 · #3 2,8 · #4 2,4 · #5 0,8 · #6 1,8 | MEASURED | Q3 |
| Kết quả lần ghé | ok 167 (24,1 h) · interrupted 62 (2,5 h) · error 18 (3,9 h) · stopped 10 (1,1 h) | MEASURED | Q4 |
| Khởi động: `ldconsole launch` + boot + `runapp` | trung vị 24 s, p90 91 s | MEASURED | log: "===== Instance" → "Game san sang" trừ đi thời gian chờ game |
| `_wait_game` | trung vị 30 s (sàn cứng 15 s) | MEASURED | log "Game san sang sau N s" |
| Bật máy → bước đầu | trung vị 73–75 s, p90 113 s, max 764 s | MEASURED | log + Q5 |
| Khoảng giữa 2 bước | trung vị 0,6 s, p90 2,4 s, tổng 24 phút | MEASURED | Q5 |
| Số bước / lần ghé smart | 4,8 | MEASURED | Q6 |
| Khoảng cách giữa 2 lần ghé smart, mỗi máy | trung vị 20–31 phút | MEASURED | Q7 |

### 2.2 Theo bước
Xem bảng đầy đủ ở [phase-0-audit.md §3.1](phase-0-audit.md). Năm bước tốn nhất (Q8):

| Bước | Phút | TB s | Trả 0 |
|---|---|---|---|
| `reddots` | 426 | 159 | 80/161 |
| `quests` | 313 | 126 | 132/149 |
| `tutorial` | 184 | 582 | – |
| `mainquest` | 172 | 63 | 156/163 |
| `notify` | 111 | 77 | – |

### 2.3 Kết quả hữu ích
| Chỉ số | Giá trị | Nhãn |
|---|---|---|
| Số lần bắt đầu nâng cấp (log có tag, 11-20 20:23 → 11-21 12:08) | 9 trên cả 7 máy (#0 3, #1 1, #2 1, #3 1, #4 3), trong khi có 223 lần ghé / 24,9 h VM | MEASURED (log) |
| Lần ghé do "thợ rảnh" | 111 lần, 13,3 h | MEASURED (Q9) |
| Lần ghé "đội rảnh" ở #1 | 15 lần, 85 phút; 11 lần ngay sau quan sát 5/5 đầy; **5 lần gửi 0 đội** | MEASURED (Q10) |
| Đội đã gửi (`gather.ret`) | #1: 26 đội / 28 lần chạy / 49,5 phút; farm gần như 0 (bị chặn khi nhà chính < 9) | MEASURED |
| Tài nguyên #1 | kim loại 46,0 M → 56,2 M trong 10,3 h (~1 M/h); lương thực +3 M; hợp kim +0,4 M | MEASURED (OCR làm tròn K/M, độ tin trung bình) |
| Tài nguyên farm (#2, #4, #5) | 28–44 k kim loại/lương thực | MEASURED |
| Tận dụng hành quân #1 | ~0,87 | INFERRED: chỉ lấy mẫu lúc quan sát (cuối lần ghé), nên lệch lên |
| Dòng hành quân đọc được thời gian (#1) | 30/126 (24 %) | MEASURED |

### 2.4 Tương tác thiết bị và perception
| Chỉ số | Giá trị | Nhãn |
|---|---|---|
| Lần chạm / lần ghé | 39,3; 91,3 % làm đổi màn | MEASURED (`exp`) |
| Thời gian chạm → ảnh kế | TB 2,07 s (`tap_tpl` 3,21 s) | MEASURED (`exp.lat`) |
| Chạm vô ích nhiều nhất | `gather/btn_recommended` 111 lần (0 %); `notify.claim_content` 398 lần (31 %) | MEASURED |
| Dòng điều hướng / lần ghé | `reddots` 18, `quests` 18, `rewards` 8,4, `gather` 8,3; 443 màn `unknown` | MEASURED (`nav`) |
| `ocr.topbar` / `ocr.text` / `screens.identify` / `vision.find` / `red_dots` / `learn.feat` | 1.057 / 130 / 129 / 32 / 4,6 / 2,1 ms | MEASURED offline |
| `Store.update` (state.json 46 KB) | 11 ms | MEASURED offline |
| `time.sleep` hằng số trong code | 98 lời gọi, tổng 86,8 s trên mọi nhánh | OBSERVED (đếm tĩnh, không phải thời gian runtime) |
| ADB `input tap`, `screencap` | ~1 s / ~400 ms | **NOT VERIFIED** (comment `device.py:144,177`) |
| Số ảnh, số OCR mỗi bước | – | **UNKNOWN** |
| Screencap thừa do `human.py` (mỗi lần bot chạm) | – | **UNKNOWN** (cơ chế OBSERVED) |
| Thời gian `defense.under_attack` + `_follow_guide` mỗi bước | – | **UNKNOWN** |
| Đổi máy (tắt VM → bật VM kế tiếp) | `ld.quit` + `sleep(5)` + khởi động 73 s | Một phần MEASURED; `quit` UNKNOWN |

## 3. Truy vấn tái lập (chạy bằng Python, DB mở `mode=ro`)
```sql
-- Q1/Q4 thời gian VM theo kết quả
SELECT result, COUNT(*), SUM(COALESCE(ended,started)-started)/3600.0 FROM visits GROUP BY result;
-- Q2 giờ trong bước
SELECT SUM(dur)/3600.0 FROM runs;
-- Q3 giờ VM / ngày / máy
SELECT inst, SUM(COALESCE(ended,started)-started)/3600.0/((MAX(started)-MIN(started))/86400.0) FROM visits GROUP BY inst;
-- Q5 bật máy -> bước đầu, khoảng giữa các bước: lặp visits(result='ok') + runs ORDER BY started
-- Q6 số bước / lần ghé smart
SELECT AVG(n) FROM (SELECT COUNT(*) n FROM runs r JOIN visits v ON v.id=r.visit WHERE v.mode='smart' GROUP BY r.visit);
-- Q7 khoảng cách lần ghé: chênh lệch started liên tiếp, visits WHERE mode='smart', theo inst
-- Q8 theo bước
SELECT step, COUNT(*), SUM(dur)/60, AVG(dur), SUM(CAST(COALESCE(ret,'0') AS REAL)=0) FROM runs GROUP BY step;
-- Q9 lần ghé do thợ rảnh
SELECT COUNT(*), SUM(COALESCE(ended,started)-started)/3600.0 FROM visits WHERE mode='smart' AND why LIKE '%tho xay ranh%';
-- Q10 #1 "doi ranh": với mỗi lần ghé, observation gần nhất trước started (march_used = march_total?) + runs(step='gather').ret
SELECT id, started, why FROM visits WHERE inst=1 AND why LIKE '%doi ranh%';
```
Các truy vấn trên được đóng thành script chỉ-đọc `tools/report_ro.py` (F4L, 2026-11-21), dùng để lấy số trước/sau cho mọi task A-*. Script có thêm chỉ số **lần ghé smart vô ích**: mọi bước trigger trong lý do ghé đều trả 0. Trên toàn bộ dữ liệu là **124 lần / 17,43 h** (MEASURED).
Ví dụ so sánh trước/sau một bản sửa: `python tools/report_ro.py --split "2026-11-22 09:00"`.

## 4. Kế hoạch lấp các chỉ số UNKNOWN (A-MEAS-1, thiết kế tối thiểu)
- **`bot/perf.py` mới** (~50 dòng, chỉ dùng thư viện chuẩn): `Perf.add(kind, dt)` và `drain()`, trả về `(kind, src, n, total, p50, p90, max)`. Mỗi `Device` giữ một instance. `src` là thread-local, mặc định `bot`.
- **Hook:**
  - `Device._cmd`: các loại `tap`, `swipe`, `key`, `screencap_raw`, `screencap_png`, `pidof`
  - `Device.screencap`: tổng thời gian kể cả retry, và đếm `fail`
  - `ocr.text`, `Ctx._ocr_tesseract`, `screens.identify`
  - khoảng thời gian trong runner: `defense_check`, `follow_guide`
  - bước giả quanh các lời gọi sẵn có trong `run_account`: `_launch`, `_adb_ready`, `_runapp`, `_wait_game`, `_popups`, `_quit`
- **Chi phí của `human.py`:** `HumanWatch._shot` đặt `src = human`, và đếm số lần `_bot_touch()` trả True (mỗi lần là một ảnh "trước" bị chụp thừa).
- **Lưu trữ:** bảng tổng hợp mới `perf(visit, inst, step, kind, src, n, total, p50, p90, max)` (`CREATE TABLE IF NOT EXISTS`), ghi ngay cạnh `log_run`. **Không** tăng `VERSION`.
- **Phần còn lại:** `runs.dur − Σ(adb, ocr, identify)` ≈ thời gian ngủ + CPU, nên không cần sửa 98 chỗ `sleep`.
- **Chạy đo:** chủ dự án duyệt, tối đa 2 VM, 10 lần ghé (#1 + một farm).

## 5. Xếp hạng bottleneck

| # | Bottleneck | Nhóm | Tác động | Độ tin |
|---|---|---|---|---|
| 1 | Lần ghé "thợ rảnh" không xây được (B1) | Lập lịch kém | 13,3 h VM / ~1,5 ngày | Cao (MEASURED) |
| 2 | Chuỗi nhiệm vụ trả 0 (`quests` 132/149, `mainquest` 156/163); tab Chính "Đến" → `none` ×391 | Chạy module thừa + điều hướng sai | 415 phút | Cao về chi phí; cơ chế UNKNOWN |
| 3 | `reddots` chạy mỗi lần ghé | Chạy module thừa | 426 phút, ok 7 % | Cao về chi phí; giá trị nhận được chưa định lượng |
| 4 | Khởi động lần ghé ~73 s × 257 | Khởi động VM / đổi máy | ~5,4 h | Cao |
| 5 | Lỗi chụp màn hình kéo dài (tới ~75 s/ảnh; 6/6 backoff) | Tương tác thiết bị | Bước 264–418 s rồi lỗi | Trung bình |
| 6 | `human.py` chụp thừa mỗi lần bot chạm | Tương tác thiết bị thừa | ~39 ảnh/lần ghé nếu đúng | Thấp: cơ chế OBSERVED, chi phí UNKNOWN |
| 7 | `defense` + `_follow_guide` sau mỗi bước | Tương tác thiết bị thừa + perception | – | Thấp (UNKNOWN) |
| 8 | Ghé "đội rảnh" sai (B11) | Lập lịch kém | 5 lần ghé thừa / 10 h ở #1 | Cao |
| 9 | `ocr.topbar` lặp để đọc lực chiến | Perception chậm | ~1 s mỗi lần | Cao về đơn giá; tần suất UNKNOWN |
| 10 | Chờ cố định (sàn `_wait_game` 15 s, `close_popups settle=3`) | Chờ thừa | phần của 30 + 19 s | Trung bình |
| – | Thời gian xây, nghiên cứu, hành quân | **Trễ do game** | Không tối ưu được, chỉ tận dụng được (làm việc khác trong lúc chờ) | – |

Kết luận về loại vấn đề:
- **Lập lịch và chọn việc** chiếm phần lớn thời gian VM vô ích (MEASURED).
- **Tối ưu thao tác/perception** chỉ có giá trị sau khi đã có số đo A-MEAS-1. Không giảm thời gian chờ khi chưa có điều kiện xác nhận game đã phản hồi.

## 6. Kịch bản benchmark (dùng chung cho Workstream A và B)
| Kịch bản | Dữ liệu | Chỉ số |
|---|---|---|
| **S-replay** (offline) | Bản sao chỉ-đọc `memory.db` + `tools/sim_schedule.py` | số lần ghé theo lý do; lần ghé vô ích (bước trigger trả 0); phút VM ước tính |
| **S-farm-1pass** | 1 farm (HQ 3–5), 1 lượt cố định + 1 lần chạy lại (memory `aow-test-one-pass-recheck`) | phút VM/lần ghé, số lần nâng cấp bắt đầu, ADB/ảnh/OCR mỗi bước (sau A-MEAS-1) |
| **S-main-24h** | #1, chế độ smart (sau này agent), 24 h | đội gửi/giờ, thời gian đội nằm không, tài nguyên/giờ, phút VM, số lần ghé gửi 0 đội |
| **S-perception** (offline) | `tests/fixtures/screens`, `tutorial` (local) | ms/ảnh, độ đúng 13/13, 34/34 |

**Mốc 4 h thủ công:** điều kiện đầu chưa chuẩn hóa (cấp nhà chính, tài nguyên, số đội, tân thủ). Chỉ dùng để tham khảo. Muốn so sánh nghiêm túc cần chủ dự án mô tả điều kiện đầu và mục tiêu cuối, hoặc một bản ghi `tools/record.py`.

## 7. Giới hạn của baseline
- Chế độ chạy thay đổi trong khoảng đo (fixed → smart, `parallel` 1/2, `wait_scale` 0,5), nên các số không cùng một cấu hình.
- 62 lần ghé `interrupted` (tiến trình bị tắt giữa chừng) làm lệch thời gian lần ghé.
- Tài nguyên đọc bằng OCR với đơn vị K/M nên độ phân giải thấp.
- Log trước 2026-11-20 20:23 không có tên luồng; log không có ngày.
- Mới có ~2,5 ngày dữ liệu; #1 mới chỉ có dữ liệu từ 2026-11-21.
