# Kế hoạch giai đoạn A — Trí nhớ + Bộ lập lịch
Lập: 2026-11-19 · Trạng thái: **chờ chủ dự án duyệt** ([ADR-0012](../adr/0012-lam-viec-theo-giai-doan.md)) · Ước lượng: **6 ngày làm việc** (A0–A5)

> Liên quan: [ke-hoach-hoan-thien-bot.md](ke-hoach-hoan-thien-bot.md) (các pha tính năng). Giai đoạn A là **nâng cấp kiến trúc**, chạy song song được với các pha tính năng vì không sửa logic thao tác trong module, chỉ thêm "biết khi nào cần làm".

## 1. Vấn đề
| Hiện tại | Hệ quả |
|---|---|
| `Runner._loop` chạy **mọi** instance, **mọi** bước bật trong `ORDER`, rồi nghỉ cố định `cycle.pause_between_cycles_min` (30 phút) | Bật máy khi không có việc (quân còn đi 3 h, nghiên cứu còn 6 h); ngược lại quân về sớm thì nằm chờ tới vòng sau |
| `data/state.json` chỉ là **ảnh chụp để web hiển thị**; module hầu như không đọc lại (trừ `mainquest_need_power`, `march_total`) | Bot không có trí nhớ: không biết lúc nào việc gì xong, mỗi lượt phải mở màn ra xem lại |
| Bước lỗi liên tục vẫn chạy lại mỗi lượt | Tốn thời gian máy, dễ kẹt → watchdog → khởi động lại game |
| `observe` đã tính được `return_at` / `gather_done` của hành quân nhưng **chỉ để web đếm ngược** | Thông tin quý nhất đang bị bỏ phí |

## 2. Mục tiêu và tiêu chí xong
Bot nhớ **khi nào có việc** cho từng tài khoản và chỉ bật máy / chạy bước khi đến lúc.

| Chỉ số (đo 48 h, 2 instance) | Cách đo | Mục tiêu so với chế độ cũ |
|---|---|---|
| Thời gian máy bật / tài khoản / ngày | bảng `runs` | **giảm ≥ 30 %** |
| Thời gian đội quân nằm không (về thành → được gửi đi lại) | `timers` hành quân + `runs.gather` | **giảm ≥ 50 %** (trung vị) |
| Số lượt bước "chạy mà không có việc" (vd `gather` khi hành quân đã đầy) | ghi chú kết quả bước | giảm rõ rệt |
| Tỉ lệ bước ổn | bảng thống kê hiện có | **không giảm** |
| Có sự cố mất khiên / bị đánh trong khoảng bot không ghé | log `defense` | 0 (xem §7, rủi ro 1) |

**Phạm vi ngoài A:** không đổi thứ tự bước trong một lượt (`ORDER` do chủ dự án chốt 2026-11-18 vẫn giữ nguyên), không phân loại màn hình (giai đoạn B), không mục tiêu dài hạn (giai đoạn D), **không chạm dữ liệu app**.

## 3. Thiết kế

### 3.1 Trí nhớ — `bot/memory.py`, file `data/memory.db` (SQLite, thư viện chuẩn)
Lý do chọn SQLite thay vì mở rộng `state.json`: truy vấn theo thời gian, lịch sử tăng dần không phải ghi lại cả file, 2 runner chạy song song an toàn (WAL + `busy_timeout`). `state.json` **giữ nguyên** cho web hiện tại.

| Bảng | Cột | Ví dụ |
|---|---|---|
| `timers` | `inst, key, due_at, src, conf, updated` | `march:1` về lúc 14:32 (`src=ocr`, `conf=0.9`); `research` xong 21:00; `chest:free` mở lại 18:00; `ally:donate` đủ lượt lúc 16:00 |
| `facts` | `inst, key, value_json, seen_at` | `hq_level=9`, `march_total=3`, `power=152340`, `tutorial_done=true`, `resources={...}` |
| `runs` | `id, inst, step, started, dur, result, note, why` | lịch sử từng lần chạy bước + **lý do lập lịch** (`why="march:1 về"`) |
| `backoff` | `inst, step, fails, until, last_note` | `research` lỗi 3 lần → tạm bỏ tới 17:00 |

API (hàm thuần quanh 1 kết nối, không lộ SQL ra module):
```python
mem = Memory(idx)                       # moi tai khoan 1 doi tuong, gan vao ctx.mem
mem.set_timer("march:1", due_at, src="ocr", conf=0.9)
mem.timers(prefix="march:")             # -> [(key, due_at, conf)]
mem.fact("hq_level"); mem.set_fact("hq_level", 9)
mem.log_run(step, result, dur, note, why)
mem.backoff(step) / mem.fail(step) / mem.ok(step)
```

**Nguyên tắc:** trí nhớ là *gợi ý*, màn hình là *sự thật*. Khi module nhìn thấy điều trái với trí nhớ (vd timer bảo còn 2 h nhưng màn hình báo đã xong) thì làm theo màn hình và ghi đè trí nhớ. Trí nhớ hỏng/trống → quay về hành vi cũ (chạy hết).

### 3.2 Giao diện mới cho module — hàm thuần `plan()`
Thêm **tùy chọn** vào mỗi module (module chưa có `plan()` coi như "luôn cần chạy" = hành vi cũ, nên làm dần được):
```python
def plan(mem, cfg, now) -> Plan:
    """Khong mo game, chi doc tri nho. Tra ve:
       Plan(ready=True/False, at=epoch|None (lan som nhat co viec), kind='trigger'|'extra', why='...')"""
```
- `trigger`: việc **đáng để bật máy**. Chủ dự án chốt 2026-11-19: **chỉ 3 loại — xây nhà, thu thập, nghiên cứu** (thợ xây rảnh, đội quân về, nghiên cứu xong).
- `extra`: mọi việc còn lại — chỉ làm **khi máy đã bật** vì một trigger, không tự mình kéo máy lên.

| Bước | Loại | Nguồn timer (ai ghi) | Ghi chú |
|---|---|---|---|
| `gather` | **trigger** | `observe` đã có `return_at`/`gather_done` → ghi `march:i`; `gather` ghi số đội rảnh | sẵn số liệu, **làm đầu tiên** |
| `train` | extra | (A4) OCR thời gian còn lại trong "Đội ngũ huấn luyện" để biết có nên huấn luyện lúc ghé | |
| `research` | **trigger** | OCR thời gian nghiên cứu (cần ROI, chưa có ảnh mẫu `research/*`) | phụ thuộc Pha 3 kế hoạch chính → tạm cooldown |
| `quests` / `mainquest` (xây) | **trigger** | thời gian xây còn lại trên hàng thợ xây (cần ROI) | `mainquest_need_power` chuyển sang `facts` |
| `daily`, `rewards` (điểm danh) | extra | reset ngày **0h UTC = 7h giờ VN** (chủ dự án xác nhận 2026-11-19) → lần ghé đầu tiên sau 7h thì chạy | |
| `alliance` | extra | `TURNS_ROI` "Lượt x/10" + tốc độ hồi | |
| `intel` | extra | `notify.energy()` + tốc độ hồi năng lượng | |
| `campaign` (treo máy) | extra | cooldown cấu hình | |
| `notify`, `collect_city`, `rewards` (khác) | extra | — | chấm đỏ chỉ biết khi nhìn → chạy kèm mỗi lần ghé |
| `tutorial` | extra | `facts.tutorial_done` | chỉ bật cho TK mới, khi đó chạy mỗi lần ghé như cũ |
| `observe` | luôn chạy cuối | — | là nơi chính **ghi** trí nhớ |

### 3.3 Bộ lập lịch — `bot/scheduler.py` (hàm thuần, test offline)
```python
def decide(mems, cfg, now) -> list[Visit]   # Visit(idx, at, steps, why)
```
1. Với mỗi tài khoản bật auto: gọi `plan()` của mọi bước bật → `next_trigger = min(at của trigger)`.
2. Thời điểm ghé = `min(next_trigger, last_visit + schedule.max_gap_min)` (trần an toàn, xem rủi ro 1), không sớm hơn `last_visit + schedule.min_gap_min`.
3. Gom: nếu tài khoản khác cũng có trigger trong `schedule.batch_window_min` tới thì ghé luôn trong cùng đợt (đỡ bật/tắt máy lẻ tẻ).
4. Bước chạy trong lần ghé = mọi trigger đã đến hạn + mọi `extra`, **theo đúng thứ tự `ORDER`**; bước đang `backoff` bị bỏ.
5. Nhiều tài khoản cùng đến hạn → tài khoản trễ hạn lâu nhất đi trước.

`Runner._loop` đổi thành: `decide()` → chạy các visit đến hạn (vẫn **lần lượt**, vẫn ≤ `ldplayer.max_running`) → ngủ tới visit sớm nhất (`_wake` vẫn đánh thức khi bấm "Chạy ngay"/"Dừng"). "Chạy ngay" = chạy mọi bước bật như cũ, bỏ qua lịch và backoff.

Công tắc: `schedule.mode: fixed | smart` trong `config.yaml` (mặc định `fixed` tới khi duyệt kết quả A5) → quay lại hành vi cũ chỉ bằng 1 tùy chọn.

### 3.4 Học từ lỗi tối thiểu — backoff
Bước kết thúc `err`/`stuck` (đã có trong `runner`) → `mem.fail(step)`: tạm bỏ `min(base × 2^(n-1), cap)` (mặc định 30 phút → 6 h). `ok` → xóa backoff. `warn`/`miss` không tính (thiếu ảnh mẫu là việc của người cắt mẫu, không phải lỗi tạm thời).

### 3.5 Web
- Mỗi máy: **"Ghé tiếp: 14:32 — đội 2 về"**, danh sách timer, các bước đang backoff (nút "Bỏ tạm dừng").
- Nhóm tùy chọn mới "Lập lịch" trong `web/options.py`: `mode`, `max_gap_min`, `min_gap_min`, `batch_window_min`, `backoff_base_min`, `backoff_cap_h`, `daily_reset_utc` (0).

## 4. Lộ trình
| Ngày | Việc | Xong khi |
|---|---|---|
| **A0** 🟡 | Đo **mốc chuẩn** ở chế độ cũ: thêm ghi `runs` vào SQLite (chỉ ghi, chưa dùng), chạy 24 h trên 2 instance | Có số liệu §2 cho chế độ `fixed` **[ĐO]** — **code xong 2026-11-19** (`bot/memory.py`: `visits`/`runs`/`observations`; ghi từ `runner` + `observe`; báo cáo `python tools/baseline.py --since 24`), kiểm thử offline đạt; **còn chạy đo 24 h** |
| **A1** | `bot/memory.py` + `ctx.mem`; `observe` ghi `march:*`, `facts` (tài nguyên, lực chiến, số đội); chuyển `mainquest_need_power`, `tutorial_done` sang `facts` (vẫn ghi song song `state.json` cho web) | Đọc lại DB thấy timer khớp màn hình hành quân |
| **A2** | `plan()` cho `gather`, `tutorial`, `mainquest`, `daily`, `rewards`; cooldown cấu hình cho `train`, `research`, `alliance`, `intel`, `campaign` | Mọi bước có `plan()`; test offline từng `plan()` bằng trí nhớ giả |
| **A3** | `bot/scheduler.py` + `tools/sim_schedule.py` (giả lập 24 h với timer giả, in dòng thời gian, so giờ bật máy `fixed` vs `smart`); tích hợp `Runner._loop` sau công tắc `schedule.mode` | Giả lập: không visit nào vượt `max_gap`, mọi trigger được phục vụ ≤ `batch_window` sau hạn; `fixed` chạy y như cũ |
| **A4** | Backoff + web (§3.4, §3.5); OCR thời gian còn lại cho `train` / hàng xây (ROI, cần màn hình thật) | Web hiện "Ghé tiếp", timer, backoff; bỏ tạm dừng bằng nút được |
| **A5** | Chạy `smart` 48 h trên 2 instance, so với mốc A0; báo cáo `docs/bot/04-giai-doan-A.md` (**[ĐO] / [CHƯA ĐO]**) + ADR-0013 "Lập lịch theo trí nhớ" | Đạt tiêu chí §2 → đề nghị đổi mặc định sang `smart`, **chờ duyệt** |

`research` đọc thời gian thật phụ thuộc ảnh mẫu `templates/research/*` (Pha 3 kế hoạch chính); trước đó dùng cooldown.

## 5. File thay đổi
| File | Thay đổi |
|---|---|
| `bot/memory.py` (mới) | lớp `Memory`, tạo bảng, ghi atomic |
| `bot/scheduler.py` (mới) | `Plan`, `Visit`, `decide()` |
| `bot/runner.py` | `_loop` theo lịch khi `smart`; ghi `runs`, backoff sau mỗi bước |
| `bot/ctx.py` | gắn `ctx.mem` |
| `bot/modules/observe.py`, `gather.py`, `train.py`, `daily.py`, `rewards.py`, `mainquest.py`, `tutorial.py`, `alliance.py`, `notify.py`/`intel.py`, `campaign.py`, `research.py` | thêm `plan()`; ghi timer/fact ở chỗ đã đọc được số |
| `bot/ocr.py` | ROI thời gian còn lại (huấn luyện, thợ xây) |
| `config.yaml`, `web/options.py`, `web/server.py`, `web/index.html` | nhóm `schedule`, hiển thị lịch/timer/backoff |
| `tools/sim_schedule.py`, `tests/fixtures/schedule/` (mới) | giả lập offline |

## 6. An toàn
- Không đụng dữ liệu app, không `pm clear`, không root → chạy được trên instance bot thường (#0, #2–#6), không cần instance Account Manager.
- Không thêm thao tác bấm mới nào ngoài đọc thời gian (OCR) → không có đường tiêu kim cương mới ([ADR-0008](../adr/0008-chinh-sach-kim-cuong.md)).
- Vẫn ≤ 2 instance cùng lúc; lịch chỉ quyết định **khi nào**, không chạy song song thêm.
- `memory.db` không chứa thông tin xác thực; `data/` đã ngoài phạm vi chia sẻ.

## 7. Rủi ro
| # | Rủi ro | Giảm thiểu |
|---|---|---|
| 1 | **Bị tấn công khi bot ghé thưa hơn** — `defense` chỉ kiểm tra lúc máy bật | Trần `max_gap_min` = 240 phút (chủ dự án chốt 2026-11-19); chấp nhận rủi ro trong khoảng này |
| 2 | OCR đọc sai thời gian → ngủ quá lâu | Kiểm tra khoảng hợp lý (vd hành quân ≤ 12 h), `conf` thấp thì cộng biên/lấy cooldown; `max_gap` chặn trên |
| 3 | Game đổi giờ/được tăng tốc bởi trợ giúp liên minh → timer trễ | Timer chỉ là cận trên; ghé sớm hơn vẫn đúng vì màn hình là sự thật |
| 4 | Hai runner ghi DB cùng lúc | WAL + `busy_timeout`, mỗi runner chỉ ghi tài khoản của mình |
| 5 | Hành vi khác lạ khi mới bật `smart` | Công tắc `schedule.mode`, mặc định `fixed` tới khi duyệt A5 |

## 8. Quyết định của chủ dự án
1. **Khi nào ghé** (2026-11-19): khi cần **xây nhà, thu thập, nghiên cứu** — chỉ 3 loại này là trigger. **Trần an toàn** (2026-11-19): giữ `schedule.max_gap_min: 240` — quá 4 h không ghé thì vẫn vào 1 lần (phòng OCR đọc sai giờ, và `defense` chỉ kiểm tra khi máy bật).
2. **Giờ reset ngày**: 0h UTC = 7h giờ VN (2026-11-19) → `schedule.daily_reset_utc: 0`.
3. **Instance đo A0/A5**: #0 và #5 (2026-11-19, đo A0 bắt đầu 00:29).
4. Đồng ý giữ nguyên thứ tự `ORDER` trong một lượt ở giai đoạn A (chỉ đổi *bước nào* và *khi nào*)?
