# Master audit: toàn bộ repository AOW-BOT

Ngày: 2026-11-21 · Trạng thái: **chờ chủ dự án duyệt** · Thuộc [MASTER-IMPLEMENTATION-PLAN.md](MASTER-IMPLEMENTATION-PLAN.md)

Nhãn: **MEASURED** (đo bằng dữ liệu runtime, benchmark hoặc phân tích AST) · **OBSERVED** (đọc trực tiếp trong code) · **INFERRED** (giả thuyết hợp lý, chưa chứng minh) · **UNKNOWN** (thiếu dữ liệu; có ghi cách điều tra).

Tài liệu này **tổng hợp và bổ sung**, không lặp lại chi tiết đã có ở:
- [phase-0-audit.md](phase-0-audit.md): trace luồng chạy, số đo lập lịch, luồng hành quân, retry, vòng đời đa tài khoản
- [../architecture/system-overview.md](../architecture/system-overview.md): vấn đề kiến trúc P1–P13
- [../architecture/module-contracts.md](../architecture/module-contracts.md): hợp đồng thực tế từng module

---

## 1. Phạm vi và phương pháp
- **Mã nguồn:** đã đọc toàn bộ `bot/` (19 file), `bot/modules/` (19), `web/`, `tools/`, `main.py`, `config.yaml`, `data/settings.json`, `requirements.txt`, `.gitignore`, `docs/`. Các module ít đọc trực tiếp được 2 agent chỉ-đọc rà soát, rồi kiểm chéo các điểm quan trọng bằng grep và đọc code (đánh dấu "đã kiểm" bên dưới).
- **Dữ liệu runtime:** `data/memory.db` mở `mode=ro` (257 lần ghé, 1.268 lần chạy bước, 11.133 lần chạm, 9.820 dòng điều hướng, 168 quan sát; từ 2026-11-19 00:29 đến 2026-11-21 12:05), `data/state.json`, `logs/bot-2026111*.log`, `logs/bot-2026112*.log`.
- **Benchmark offline:** OpenCV/Tesseract trên `logs/capture-540-city.png`.
- **Hồi quy có sẵn:** `tools/check_screens.py` **13/13**, `tools/check_tutorial.py` **34/34** (MEASURED, chạy 2026-11-21).
- **Phân tích tĩnh:** AST (độ dài hàm, độ phức tạp vòng, tham số, `except`, import trong hàm, trạng thái global) và đồ thị import.

## 2. Điểm vào runtime [OBSERVED]
| Điểm vào | Làm gì |
|---|---|
| `main.py --web` / `run.bat` | `setup_log` → `yaml.safe_load(config.yaml)` → `Store()` → `Vision` → `Runner` → Flask `web.server.create_app` (127.0.0.1:8080) |
| `main.py --once [--only] [--modules]` | Runner chạy 1 vòng |
| `main.py --capture ID`, `--check` | Chụp màn hình; kiểm ảnh mẫu thiếu (`bot/tplcheck.py`) |
| `tools/*.py` | Công cụ offline/online (§8) |
| `poc/*.sh` | Account Manager PoC (Git Bash) — **không thuộc phạm vi kế hoạch này** |

Luồng chính `Runner → scheduler → run_account → module.run(ctx) → Ctx → Device → Store/Memory/Learner`: xem [phase-0-audit.md §2](phase-0-audit.md).

## 3. Phát hiện an toàn (ưu tiên cao nhất)

| ID | Vị trí | Phát hiện | Nhãn |
|---|---|---|---|
| S1 | `bot/modules/defense.py:shield` (75–117) | Mua khiên bằng kim cương **khi lỗi vẫn tiếp tục mua**: `gems_before` None (OCR hỏng) thì bỏ qua kiểm tra số dư (104) mà vẫn mua; chi tiêu chỉ được ghi khi **cả hai** lần `ocr.topbar` đọc được (113), nên trần `gem_cap_daily` bị đếm thiếu; số vật phẩm đọc sai thành 0 (94–95) thì đi nhánh mua; `ROWS/PRICE[hours]` gây KeyError nếu `shield_hours` ∉ {1, 12, 72}; ngày theo giờ địa phương, không theo UTC. Cấu hình hiện tại `shield_buy_gems: true` (`config.yaml` và `settings.json`) | OBSERVED (đã kiểm) |
| S2 | `bot/modules/reddots.py:_handle` (75–99) | Gọi `intel.run` (dùng Thuốc thể lực), `rewards` VIP, `daily`, `notify.recruit`, `notify.heroes` **mà không kiểm** `modules.*`/`notify.*`, trong khi `notify.run` có kiểm (563+). Tùy chọn tắt của chủ dự án bị bỏ qua | OBSERVED (đã kiểm) |
| S3 | `bot/modules/play.py:arena` (316+, ~350) | `own` (lực chiến mình) là None → điều kiện `own and pw > own*ratio` luôn sai → mọi đối thủ hợp lệ → `max(cands)` chọn đối thủ **mạnh nhất** | OBSERVED (đã kiểm) |
| S4 | `bot/modules/notify.py:recruit` (334+, ~355) | Không khớp mẫu `recruit/free_wait` → bấm "1 lần" và coi như miễn phí. Nếu mẫu trượt khi đang hồi chiêu, bot có thể tiêu phiếu ngoài chính sách (memory `aow-recruit-ticket-policy`) | OBSERVED cơ chế; hậu quả INFERRED |
| S5 | `bot/modules/alliance.py:35` | Tìm `btn_donate_gold` không có ROI, cạnh nút quyên góp bằng kim cương | INFERRED; điều tra bằng fixture `tests/fixtures/ally_tech_i1.png` |
| S6 | `bot/modules/defense.py:under_attack` | Ảnh mẫu `defense/alert_attack.png` **không tồn tại**, nên phát hiện bị tấn công chỉ dựa vào mép đỏ nhấp nháy (`red_flash`) | OBSERVED (đã kiểm `ls templates/defense`) |

## 4. Ma trận trách nhiệm và quyết định từng module

Cột "Quyết định": **Keep** (A1) · **Optimize** (A2) · **Refactor** (A3) · **Wrap** (A4) · **Replace** (A5) · **Remove** (A6). Một module có thể có nhiều quyết định theo thời gian. Chi phí lấy từ `runs` trong `memory.db` (tổng phút, TB giây/lần, tỉ lệ trả 0).

### 4.1 Lõi
| File | Trách nhiệm thật | Chi phí runtime | Lỗi / rủi ro đã biết | Trùng lặp | Nơi dùng | Độ khó migration | Quyết định |
|---|---|---|---|---|---|---|---|
| `bot/runner.py` | Vòng lặp fixed/smart, vòng đời VM, mở game, cổng nghiệp vụ, phòng thủ trước mỗi bước, theo hướng dẫn, backoff, watchdog, chép facts | Khởi động lần ghé trung vị 73 s (MEASURED) | `_remember_facts` làm tươi dữ liệu cũ (B4); `ORDER` lệch tài liệu; không log `parallel`/`mode` thật (settings ghi 1, log ghi 2) | – | `main`, `tools/sim_schedule` | Cao (CC 52) | Refactor nhỏ (sửa lỗi) → Replace dần bằng agent |
| `bot/scheduler.py` | Luật lập lịch thuần trên `Memory` | Rẻ | B1 (`plan_build` không xét khả thi); B11 (`plan_gather` coi đội không có timer là rảnh); `value_factor` dừng đếm khi gặp kết quả khác "ok" | – | runner, ctx (lazy), web, `sim_schedule` | Thấp | Refactor (sửa lỗi) → luật chuyển sang `aowbot.domain` |
| `bot/ctx.py` | I/O, vision, điều hướng, học, watchdog, nhận thưởng, chính sách VIP, OCR hành quân | 39 lần chạm/lần ghé | `Ctx._ocr_tesseract` đặt lại `tesseract_cmd` mỗi lần gọi; `read_marches` tới 3 lần Tesseract | 3 đường Tesseract; danh sách nút đóng trùng `screens` | runner, mọi module, tools | Cao (596 dòng) | Wrap bằng port hẹp; chính sách VIP → `domain.policy` |
| `bot/device.py` | ldconsole + adb (1 tiến trình con/lệnh) | screencap raw ~400 ms (**NOT VERIFIED**, comment); tối đa ~75 s khi treo | `Device.recent/backs` tạo lười, 2 luồng dùng không khóa (`human.py`) | – | runner, main, tools | Trung bình | Optimize (đo + fail-fast) → Wrap |
| `bot/memory.py` | SQLite; nuốt mọi lỗi ghi | – | Mỗi kết nối chạy `executescript(SCHEMA)` + `PRAGMA user_version`, nên công cụ "đọc" cũng ghi DB; comment "v5" nhưng `VERSION = 4` | – | runner, tools | Thấp | Keep schema; Refactor mở chỉ-đọc |
| `bot/state.py` | `state.json` + `settings.json` | `update` ghi lại 46 KB mỗi lần (11 ms, MEASURED) | Chồng chéo với `facts`; không có timestamp theo trường | – | main, web, mọi module qua `ctx.store` | Trung bình | Keep (web) → World Model thay vai trò kho dữ kiện |
| `bot/learn.py` | Kinh nghiệm, kNN, biến thể ảnh mẫu, H1/H2 | `feat` 2 ms | Singleton `_inst`; `summary()` dựng `Learner` mới mỗi lần gọi web | `dhash`, `thumb` trùng `screens` | ctx, human, web, tools | Trung bình | Keep → Wrap ở B8 |
| `bot/vision.py` | Khớp mẫu màu `TM_CCOEFF_NORMED` + cache + "prior" | `find` 32 ms toàn màn (MEASURED) | Cache dict dùng chung giữa các luồng, không khóa; `prior_hits` không ai đọc | – | khắp nơi | Thấp | Keep; Remove `prior_hits` |
| `bot/screens.py` | `identify` (tới 19 mẫu), `same`, `dhash`, lưu màn lạ | 129 ms (MEASURED) | 9/19 mẫu không ROI; `_tl` là kênh trả kết quả ngầm | `POPUPS` = `Ctx.POPUP_CLOSERS` | ctx, learn, notify, defense, tools | Thấp | Keep; Optimize ROI (sau) |
| `bot/ocr.py` | Tesseract qua pytesseract (1 tiến trình/lần gọi) | `text` 130 ms; `topbar` 1.057 ms (MEASURED) | `_ok` global | 3 đường Tesseract | 16 module | Thấp | Keep; parse thuần (`amount`, `seconds`) → domain |
| `bot/badges.py` | Chấm đỏ theo HSV, bong bóng "Free" | `red_dots` 4,6 ms | Đọc `templates/common/btn_free_text.png` theo đường dẫn tương đối CWD | – | 8 module | Thấp | Keep |
| `bot/build.py` | Nâng cấp qua UI (Nhảy, Tăng cấp) | – | Lõi import ngược `modules.observe.progress_bars`; chuỗi "Nhảy" thường kết thúc `none` (A-INV-1) | `builders` trùng `observe.read_builders` | quests, mainquest, tutorial | Trung bình | Refactor (tách `progress_bars`) → Wrap |
| `bot/human.py` | Ghi thao tác tay của chủ dự án (getevent) | **UNKNOWN**: mỗi lần bot chạm cũng sinh thêm 1 screencap vì luồng "ảnh trước" chạy trước bộ lọc (dòng 99/105, OBSERVED) | Bật mặc định (`learn.watch_human`) | – | runner | Thấp | Optimize (A-OPT-5) |
| `bot/steer.py`, `touch.py`, `stream.py` | Lái quân trong trận | – | `stream.Shell` không dùng; thread đọc nuốt lỗi | `touch.SX/SY` nghịch đảo của `human.SX/SY` | ctx, campaign, play, tutorial | Cao (thời gian thực) | Keep; Remove `Shell` |
| `bot/tplcheck.py` | Kiểm ảnh mẫu thiếu | – | – | – | main, snap | – | Keep |

### 4.2 Module bước (`bot/modules/`)
"Trả 0" là tỉ lệ lần chạy mà `ret` bằng 0 (MEASURED, toàn bộ `runs`).

| Module | Trách nhiệm | Phút / TB s / trả 0 | Lỗi / rủi ro | Trùng lặp | Quyết định |
|---|---|---|---|---|---|
| `reddots` | Quét chấm đỏ cuối lượt, gọi 6 module khác | **426 / 159 / 50 %**; ok 7 % | S2; `notify.badged` chạy 2 lần; thứ tự trong `ORDER` do chủ dự án chốt 2026-11-21 | `_near` ~ `notify._dot_near` | Refactor (S2) → **chờ chủ dự án** về vị trí/tần suất → Wrap |
| `quests` | Chương/Chính: "Đến" → nâng cấp | **313 / 126 / 89 %** | tab Chính "Đến" → `none` 391 lần (cơ chế **UNKNOWN**) | `_power` ×3 | Investigate (A-INV-1) → Wrap |
| `mainquest` | Theo thanh nhiệm vụ chính | **172 / 63 / 96 %** | Bị chặn `need_power` không có hành động tăng lực chiến; nếu OCR lực chiến None thì chặn mãi | `_power` ×3 | Wrap |
| `tutorial` | Tân thủ + `follow` + `decide()` thuần | 184 / 582 / – | `guide_visible` chạy cả `decide()` sau mỗi bước (`runner._follow_guide`); `read_count` dùng đường dẫn Tesseract cứng | `_colored` = `Ctx.is_colored`; đặt công trình trùng `construct` | Keep (34/34 hồi quy); Optimize lời gọi sau bước |
| `notify` | Phúc lợi, hoạt động, tình báo, chiêu mộ, tướng, sự kiện | 111 / 77 / (dict) | S4; `hub` luôn vuốt 3 lần, mỗi lần 1 s | đoạn gửi quân lặp ở rebels/alliance/gather | Refactor (S4) → Wrap |
| `gather` | Gửi quân đi mỏ | 65 / 73 / 62 % | Phụ thuộc B11 ở scheduler; `gather/btn_recommended` 111 lần chạm, 0 % đổi màn | – | **Wrap** (`try_dispatch` là Action nguyên tử) |
| `observe` | Quan sát cuối lượt | 47 / 17 / – | Chỉ 30/126 dòng hành quân đọc được thời gian (#1) | `read_builders` ~ `build.builders` | Wrap + tách parse thuần |
| `rewards` | Thư, VIP, lễ hội, quà nổi | 46 / 38 / 28 % | Chính sách VIP nằm trong `Ctx.claim_loop` | vòng chấm đỏ tab trùng `dot_strips` | Wrap |
| `campaign` | Chiến dịch + `battle`/`predicted_win` dùng chung | 44 / 59 / 75 % | – | `rebels.pred_win` ~ `predicted_win` | Keep → Wrap |
| `intel` | Lớp mỏng gọi `notify.intel` | 32 / 34 / 79 % | – | – | Wrap (hoặc gộp khi migration) |
| `daily` | Thưởng nhiệm vụ + rương năng động | 22 / 21 / 72 % | – | tên `claim_tab` trùng `rewards` | Wrap |
| `play` | Mỏ khoáng sản, đấu trường, cướp xe | 21 / 49 / 92 % | S3; `loot_ok` cho qua mọi lực chiến khi chưa có lịch sử; 13 lần `save_debug` | vòng đọc kết quả trận trùng `campaign` | Refactor (S3) → Wrap |
| `train` | Huấn luyện | 17 / 23 / 72 % | Ghi `ctx.cfg["_use_help"/"_use_free"]` (rò rỉ trong lần ghé) | – | Refactor nhỏ → Wrap |
| `alliance` | Quyên góp vàng, trợ giúp, quà, boss, mỏ | 10 / 14 / 79 % | S5; cổng bằng `quests.alliance` thay vì `modules.alliance`; ghi `_use_free=False` | đoạn gửi quân | Wrap |
| `research` | Nghiên cứu | 8 / 16 / **100 %** | `badges()`: Hough + 1 OCR mỗi vòng tròn × 3 tab × 4 lần cuộn; `save_debug` mỗi lần; khóa YAML `use_help/use_free_speedup/max_starts` không ai đọc | – | Wrap; Optimize khi farm tới HQ8 |
| `construct` | Xây công trình mới (kéo thả) | 5 / 39 / 57 % | Chỉ ROI tránh nút "Xây dựng ngay" | trùng hàm đặt công trình của `tutorial` | Wrap |
| `collect_city` | Nhặt tài nguyên nổi | 4 / 5 / 92 % | `ctx.dev.tap` trực tiếp, bỏ qua learner/watchdog | – | Wrap |
| `rebels` | Tự mở tập kết + tham gia | 2 / 4 / **100 %** | `join` không bao giờ chạy: thiếu `rebels/rally_mech.png`, `rebels/btn_join.png` (đã kiểm) | `pred_win` | Wrap; `join` → **hỏi chủ dự án** (cắt mẫu hay bỏ) |
| `defense` | Phát hiện tấn công, khiên, sơ tán | – (chạy trước mỗi bước) | S1, S6; `under_attack` có thể chụp 3 ảnh | – | **Refactor ngay (S1)** → Policy |

### 4.3 Giao diện và công cụ
| Thành phần | Phát hiện | Quyết định |
|---|---|---|
| `web/server.py` | `/api/state` tự tính `rebels_info`/`timers_info`; `/api/learn/candidate` trùng `Learner.candidate` (ghi `meta.json` không khóa, có thể đua với luồng bot) | Keep; logic chuyển sang use case khi có; sửa race `meta.json` (A3) |
| `web/index.v1.html` | Không ai phục vụ (đã kiểm grep) | Remove |
| `tools/baseline.py`, `tools/learn.py` | Mở `Memory()`, nên ghi schema và `user_version` vào DB thật; `learn.py train` ghi `screen_samples` | Refactor: mở chỉ-đọc |
| `tools/sim_schedule.py` | Dùng DB tạm (an toàn); import `bot.runner.ORDER` | Keep (dùng để nghiệm thu A-FIX) |
| `tools/check_screens.py`, `check_tutorial.py` | Hồi quy đang pass | Wrap thành pytest |
| `tools/snap.py`, `record.py`, `run_tutorial.py`, `replay_tutorial.py` | Không có import hỏng | Keep |

## 5. Cấu hình, logging, lưu trữ, test, dependency [OBSERVED]
- **Cấu hình:** `yaml.safe_load`, không có schema; `Store.cfg_for` gộp sâu `config.yaml ← settings.global ← settings.instances[idx]`.
  - Khóa đọc trong code nhưng thiếu ở YAML: `observe.read_hq`, `learn.adaptive_wait/knn_max/dup_sim`, `mainquest.busy_recheck_h`, `schedule.extra_every_min` (chỉ có trong `DEFAULTS`), `adb_serials` (tra theo `int`, nhưng khóa YAML/JSON là chuỗi), `guide_follow`, `defense.red_flash`, `notify.events`, `reddots.dead_h`, `train.use_max_button`, `tutorial.trace_dir`.
  - Default lệch nhau: `notify.intel_max` 5 trong code / 20 trong YAML; `gather.fallback_march_slots` 2 / 1.
  - Khóa không ai đọc: `research.use_help/use_free_speedup/max_starts`.
- **Logging:** `main.py:23-31`. Định dạng `%H:%M:%S` **không có ngày**; `FileHandler` theo ngày khởi động nên **không xoay file**. Log là văn bản, không có cấu trúc. Lỗi parse YAML xảy ra trước khi cấu hình log nên không được ghi.
- **Lưu trữ:** `memory.db` (WAL, thread-local), `state.json`, `settings.json`, `data/exp/crops`, `data/learn/cand`, `templates/**/*@auto*.png` (ghi vào cây mã nguồn, đã gitignore).
- **Test:** không có framework. 2 script hồi quy đang pass. Fixture 97 MB bị gitignore; chủ dự án đã chọn **không đưa ảnh vào git**.
- **Dependency:** `requirements.txt` gồm `opencv-python` (5.0.0.93), `numpy` (2.5.5), `pyyaml`, `pytesseract`, `flask`; không ghim phiên bản; không có `pyproject.toml`.
- **Git:** remote `origin` có sẵn; mới có 1 commit. CLAUDE.md vẫn ghi "Thư mục chưa phải git repo", đã lỗi thời.

## 6. Trùng lặp và mã chết (tổng hợp, OBSERVED)
- **Trùng lặp:**
  - `_power()` ×3: `quests.py:24`, `mainquest.py:20`, `tutorial.py:680`
  - `dhash` ×2: `learn.py:61`, `screens.py:121`
  - ảnh thu nhỏ 54×96 ×4: `screens.same`, `Ctx._watch`, `learn.thumb`, `screens.is_loading`
  - đọc thợ xây ×2: `build.builders`, `observe.read_builders`
  - Tesseract ×3: `ocr.text`, `Ctx._ocr_tesseract`, `tutorial.read_count`
  - danh sách nút đóng/quay lại ×3: `screens.POPUPS`/`BACKS`, `Ctx.POPUP_CLOSERS`/`back_out`, `learn.LEARNABLE`
  - đoạn gửi quân ×4: `notify`, `rebels`, `alliance`, `gather`
  - đọc kết quả trận ×3: `campaign`, `play` ×2
  - dự đoán thắng ×2: `rebels.pred_win`, `campaign.predicted_win`
  - đặt công trình ×2: `construct`, `tutorial`
  - duyệt ứng viên ảnh mẫu ×2: `Learner.candidate`, `server.learn_candidate`
- **Mã chết:**
  - `stream.Shell`
  - `Vision.prior_hits` (được tăng nhưng không ai đọc)
  - `web/index.v1.html`
  - `rebels.join` (luôn trả 0 vì thiếu ảnh mẫu)
  - ảnh mẫu không ai tham chiếu: `rebels/tab_mech`, `rebels/title_mech`, `rebels/btn_rally_start`, `defense/btn_use_gems` (đã kiểm grep)
  - import thừa: `notify` re, `play` json, `rebels`/`research` numpy, `train`/`alliance` time
  - `play.py:357-358` không có tác dụng
- Không module nào chết hoàn toàn: mọi hàm cấp cao đều có nơi gọi.

## 7. Đính chính so với các audit trước
- **Ca B11 (#1, 15 lần ghé "đội rảnh"):**
  - 11/15 lần ghé xảy ra ngay sau quan sát 5/5 đầy.
  - Chỉ **5/15** lần gửi 0 đội. Ở các lần còn lại, đội đã về thật nên vẫn gửi được.
  - Vì vậy lợi ích của A-FIX-1 phải tính trên **5 lần ghé vô ích**, không phải 11.
  - Thiết kế sửa không được coi đội không có đồng hồ là "bận vô thời hạn", nếu không mức tận dụng hành quân sẽ giảm. Cần ước lượng giờ về.
- `value_factor` (H3) chỉ đếm các lần `result == "ok"` liên tiếp (dừng ở lần đầu khác "ok"). `mainquest` chỉ ok 58 %, nên dùng nguyên `value_factor` cho A-FIX-3 **sẽ không có tác dụng**.
- Thứ tự `ORDER` và việc `reddots` thuộc `ALWAYS` là **quyết định của chủ dự án** (2026-11-20/21), không phải lỗi. Đề xuất đổi phải để chủ dự án quyết.

## 8. Thông tin còn UNKNOWN và cách điều tra
| UNKNOWN | Cách điều tra | Task |
|---|---|---|
| Độ trễ ADB (tap, screencap) trên máy hiện tại; số ảnh/OCR mỗi bước; chi phí `human.py`; thời gian `_follow_guide`, `defense` | Bộ đếm hiệu năng trong `Device`/`ocr`/`screens` + các khoảng thời gian trong runner → bảng `perf`; 1 lượt có duyệt | A-MEAS-1 |
| Vì sao tab Chính "Đến" → `none` (391 lần), chuỗi "Nhảy" → `follow_idle` | Lưu 1 ảnh/dòng/ngày ở nhánh `none`; chủ dự án chạy 1 lượt | A-INV-1 |
| Điều kiện nâng nhà chính và chi phí theo cấp | Chủ dự án cung cấp, hoặc ghi lại khi gặp màn Tăng cấp | B3 (Construction) |
| Giá trị `parallel`/`mode` mà tiến trình web đang dùng | Log cấu hình hiệu lực khi runner khởi động | A-REL-4 |
| Mốc 4 h thủ công: điều kiện đầu | Chủ dự án mô tả, hoặc dùng bản ghi `tools/record.py` | performance-baseline §6 |
| S5 (nút quyên góp kim cương) | Chạy `vision.find` trên fixture `ally_tech_i1.png` với/không ROI | A-SAFE-5 |
