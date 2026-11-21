# Phase 0 — Audit: từ bot chạy theo ORDER sang agent theo mục tiêu

Ngày: 2026-11-21 · Trạng thái: **chờ chủ dự án duyệt** (ADR-0012) · Không sửa code trong phase này.

Nhãn bằng chứng:
- **[MEASURED]**: số tính trực tiếp từ `data/memory.db` (bản sao, không ghi vào DB thật), `data/state.json`, `logs/bot-*.log`, hoặc đo offline trên ảnh đã lưu.
- **[OBSERVED]**: đọc thấy trong code/log, không phải suy diễn.
- **[INFERRED]**: suy ra từ code và số đo, chưa chạy thử để xác nhận.
- **[NOT VERIFIED]**: giả thuyết hoặc số do người khác ghi, chưa kiểm.

Dữ liệu dùng: `memory.db` (user_version 4): 257 lần ghé, 1.268 lần chạy bước, 11.133 lần chạm (`exp`), 9.820 dòng điều hướng (`nav`), 1.643 mẫu kNN. Khoảng thời gian **2026-11-19 00:29 → 2026-11-21 12:05** (~59,6 giờ). Log có tên luồng `[#idx]` từ 2026-11-20 20:23; log cũ hơn không có, nên không gán được cho từng máy.

---

## 1. Kết luận chính

1. **[MEASURED] Bot gần như không xây.** Từ 2026-11-20 20:23 đến 2026-11-21 12:08: **223 lần ghé, 24,9 giờ máy bật**, nhưng log chỉ có **9 lần "Đã bắt đầu nâng cấp"** trên cả 7 máy. Tính ra khoảng **2,8 giờ máy bật cho một lần nâng cấp**. Các farm đang ở **nhà chính cấp 3–5** (#0=5, #2=3, #3=4, #4=3, #5=3, #6=4), và `builders_busy = 0` ở cả 6 farm.
2. **[MEASURED] Thợ xây rảnh kéo máy lên, nhưng lần ghé không có kết quả.** 111/189 lần ghé ở chế độ smart (**13,3/23,3 giờ, 57 %**) có lý do "thợ xây rảnh (0/1)". `mainquest` trả về 0 trong **156/163** lần, `quests` trả về 0 trong **132/149** lần. Hai bước này tốn **415 phút** mà không tạo ra lần nâng cấp nào.
3. **[OBSERVED → INFERRED] Nguyên nhân gốc: bộ lập lịch biết *thợ rảnh* nhưng không biết *vì sao không xây được*.** `plan_build` ([scheduler.py:101](../../bot/scheduler.py)) kéo máy lên mỗi khi `builders_busy < max_builders`. Nó không kiểm tra điều kiện, tài nguyên, hay kết quả của lần thử trước. Lần ghé không xây được không đổi trạng thái gì, nên **cứ ~20–30 phút lại ghé lại** (khoảng cách trung vị đo được: 20–31 phút/máy).
4. **[MEASURED] Nút "Đến" ở tab Chính hầu như không dẫn tới màn nâng cấp.** Log có 391 lần `Nhiem vu tab_2_main -> none`, so với 21 lần `started`. Mỗi lần tốn ~8 giây cho chạm, `upgrade_here` rồi `back_out`.
5. **[MEASURED] `reddots` tốn thời gian nhất:** **426 phút**, trung bình 159 s/lần, chỉ 7 % lần kết thúc "ok" (còn lại là warn do lưu ảnh `reddots_left`). Bước này nằm trong `ALWAYS` nên chạy **mỗi** lần ghé và không bị giãn chu kỳ theo giá trị H3 (`value_factor` chỉ áp dụng cho `extra_due`). Trong `ORDER` nó đứng **thứ 3**, trước mọi bước xây. CLAUDE.md lại ghi là "cuối lượt", nên tài liệu và code đang lệch nhau.
6. **[OBSERVED → INFERRED] Nhà chính có thể không bao giờ được đọc lại.** `Runner._remember_facts` ([runner.py](../../bot/runner.py), `FACT_KEYS`) chép `hq_level` từ `state.json` sang `facts` sau mỗi lần ghé, và `set_fact` đặt `seen_at = now`. `observe.read_hq` chỉ đọc OCR khi `seen_at` cũ hơn 6 giờ. Vì vậy, sau lần đọc đầu, giá trị cũ cứ được "làm tươi" mãi. Số đo phù hợp với điều này: cả 3 ngày log chỉ có **~10 lần** "Nha chinh (Xuong kien truc) cap N". Đây là ví dụ cụ thể cho việc **dữ liệu cũ bị coi là hiện tại**.
7. **[INFERRED] Chiến lược đang tự chặn tài nguyên.** Thu thập tắt khi nhà chính < 9 (`gather.min_hq_level`), bản đồ thế giới tắt khi < 6, nghiên cứu tắt khi < 8. Farm cấp 3–5 vì vậy chỉ có thu nhập từ quà và nhiệm vụ. Tài nguyên đo được: #2 có 44k kim loại / 29k lương thực, #4 33k/28k, #5 30k/37k. #0 có 797k/943k nhưng `mainquest` bị chặn vì "thua" (`mainquest_need_power = 933.040`). **[NOT VERIFIED]** Chưa có dữ liệu chi phí nâng cấp từng cấp, nên chưa chứng minh được tài nguyên là blocker chính. Log chỉ có 1 dòng "Không nâng cấp được (thiếu tài nguyên)", vì phần lớn lần thử **không tới được** màn nâng cấp.
8. **[MEASURED] Mỗi lần ghé tốn ~75 s chi phí cố định** (từ bật máy tới bước đầu: trung vị 75 s, p90 113 s, max 764 s). Riêng phần game vào màn chơi mất trung vị 28 s, p90 44 s. Với 257 lần ghé, tổng chi phí này là **~5,4 giờ**.
9. **[OBSERVED] Phần ML hiện có chỉ phục vụ chiến thuật (điều hướng), chưa có chiến lược:** kNN dùng cho màn lạ, Thompson chọn giữa "nút đóng" và "phím Back", adaptive wait dùng sau mỗi lần chạm, H3 giãn chu kỳ bước chạy kèm. Không có thành phần nào biết mục tiêu (nhà chính), phụ thuộc giữa công trình, hay chi phí và lợi ích của bước.

**Đánh giá:** thứ tự ưu tiên cho các phase sau **không phải** thêm ML. Việc cần làm trước là (a) WorldModel phân biệt được dữ liệu mới và cũ, (b) mô hình hóa *vì sao* nâng cấp bị chặn, và (c) lập lịch theo blocker thay vì theo cờ "thợ rảnh". Ba việc này giải quyết được phần lớn trong 13,3 giờ ghé vô ích.

---

## 2. Luồng thực thi thực tế (trace)

### 2.1 Runner → lập lịch
- `main.py --web`: tạo `Runner(base_cfg, store, vision)`. `Runner.start()` khởi động luồng `_loop`.
- **[OBSERVED]** `data/settings.json` ghi đè `schedule.mode = smart`, `parallel = 1`, `gather_retry_min = 10`, `max_gap_min = 480`, `speed.wait_scale = 0.5`. Log 2026-11-21 lại ghi "Runner bat dau (**2** may song song)". Settings được nạp một lần lúc `Store()` khởi tạo, nên giá trị trong file có thể đã đổi sau khi tiến trình web chạy. Hiện chưa biết chắc tiến trình đang dùng giá trị nào **[NOT VERIFIED]**.
- `_loop_smart` ([runner.py:198](../../bot/runner.py)) gọi `scheduler.decide()`. Đây là **hàm thuần** đọc `memory.db` và trả về `Visit(idx, at, steps, why, full)` cho từng máy, xếp theo `at`. Máy đến hạn trễ nhất sẽ được `_spawn(idx, modules=steps)`.
- Trigger (`TRIGGERS`): `gather`, `mainquest`, `quests`, `research`, `rebels` (cùng `tutorial` khi chưa xong). Các bước khác chạy kèm theo `extra_due` (180 phút × `value_factor`, hoặc lần đầu sau reset ngày với `DAILY`). `reddots` thuộc `ALWAYS`.

### 2.2 Một lần ghé (`run_account`, [runner.py:323](../../bot/runner.py))
1. `LDConsole.launch` (giữ khóa và kiểm tra `max_running`), sau đó `Device.wait_ready` (`getprop sys.boot_completed`).
2. `Ctx(dev, vision, cfg)`, rồi `HumanWatch.start()` (getevent để ghi thao tác tay).
3. `ldconsole runapp`, sau đó `_wait_game` chờ ít nhất `launch_min_wait` (15 s), rồi cứ 2 s chạy `screens.identify` một lần, tối đa 45 s. Tiếp theo là `close_popups(rounds=10, settle=3)`.
4. Với từng `(name, mod)` trong `ORDER + observe`:
   - các cổng kiểm tra trước bước: nghiên cứu (nhà chính < 8), `rebels_ready`, `march_full()` (OCR), `WORLD_STEPS` + `world_ready`
   - `app_alive` (`pidof`), nếu game đã chết thì `_restart_game`
   - `defense.under_attack(ctx)` (**chụp màn hình mỗi bước**)
   - `mod.run(ctx)`, rồi phân loại kết quả ok / warn (có `save_debug`) / miss (thiếu ảnh mẫu) / err / stuck (watchdog)
   - `store.step_result` + `mem.log_run` + `mem.log_nav`
   - `_follow_guide(ctx)` sau hầu hết các bước (chụp thêm 1 lần để tìm hướng dẫn game)
   - `ctx.exp_flush()` ghi bảng `exp` và cập nhật thống kê học
   - `_backoff`: lỗi hoặc kẹt thì tạm bỏ bước 30→60→…→360 phút
5. `finally`: `HumanWatch.stop`, `ld.quit` (kiểm tra máy đã tắt), `_remember_facts` (chép state sang facts), `visit_end`, `sleep(5)`.

### 2.3 Module → Ctx → Device
- Mọi thao tác đi qua `Ctx`: `shot()` gọi `dev.screencap()` (raw, không PNG), rồi `_exp_end` (đo kết quả lần chạm trước), rồi `_watch` (watchdog).
- `tap/tap_tpl/tap_first`: `_exp_begin`, `dev.tap` (`adb shell input tap`), `_after_tap` (H1: chờ theo p80 đã học hoặc chụp liên tục tới khi màn đổi).
- `goto(target)`: lặp tối đa 10 vòng gồm `screens.nav_action` (nhận diện bằng ảnh mẫu), học kNN, `dead_spot`, Thompson (`choose_close`), rồi tap, Back hoặc chờ.
- `ensure_city()` được gọi **rất dày**. Mỗi lần gọi là ít nhất 1 lần chụp, 1 lần `identify` (~130 ms CPU) và `close_popups`. Đếm tĩnh: rewards 7, notify 7, play 6, mainquest 6, quests 5…
- Mỗi lần `Device.tap/swipe/back` chạy một tiến trình `adb` riêng (`subprocess.run`). **[NOT VERIFIED]** Comment trong code ghi `input tap` mất ~1 s và screencap raw ~400 ms (đo trên #4 ngày 2026-11-20). Phase này không bật máy nên chưa đo lại.

### 2.4 Memory / State
| Kho | Nội dung | Ghi bởi | Vấn đề |
|---|---|---|---|
| `data/state.json` (`Store`) | Trạng thái chạy cho web **lẫn** dữ kiện game (hq_level, resources, march_*, `mainquest_need_power`, `quests_need_power`…) | mọi module qua `ctx.store.update` | **[MEASURED]** Mỗi `update` đọc và ghi lại toàn bộ file 46 KB (~11 ms). Không có timestamp riêng cho từng trường. |
| `memory.db.facts` | hq_level, builders_busy, march_total, resources, world_open… | observe, ctx, runner | Có `seen_at` nhưng **không có nguồn hay độ tin cậy**. `_remember_facts` làm tươi `seen_at` bằng giá trị cũ (xem §1.6). |
| `memory.db.timers` | build:*, research, march:*, arrive:* (có `src`, `conf`) | observe, mainquest | Chỉ còn 3 dòng, đều của #1. Farm **không có timer xây** vì không có gì đang xây. |
| `memory.db.runs/visits/nav/exp` | nhật ký | runner, ctx | Đủ dùng để đánh giá. `runs.ret` là "số việc làm được", nhưng mỗi module định nghĩa khác nhau. |

Một dữ kiện như `hq_level` đang có **3 nguồn ghi**: `build.upgrade_here` (state), `observe.read_hq` (state + facts), `_remember_facts` (state → facts). Không có quy tắc chọn nguồn nào thắng.

---

## 3. Số đo hiệu suất

### 3.1 Thời gian theo bước [MEASURED, toàn bộ `runs`]
| Bước | Lần | Tổng (phút) | TB (s) | Max (s) | ok % | Lần trả về 0 |
|---|---|---|---|---|---|---|
| reddots | 161 | **426** | 159 | 1207 | 7 | 80 |
| quests | 149 | **313** | 126 | 575 | 68 | 132 |
| tutorial | 19 | 184 | 582 | 3219 | 21 | – |
| mainquest | 163 | **172** | 63 | 418 | 58 | 156 |
| notify | 86 | 111 | 77 | 307 | 74 | (trả dict) |
| gather | 53 | 65 | 73 | 413 | 32 | 33 |
| observe | 168 | 47 | 17 | 380 | 96 | – |
| rewards | 74 | 46 | 38 | 475 | 96 | 21 |
| campaign | 44 | 44 | 59 | 278 | 68 | 33 |
| intel | 57 | 32 | 34 | 185 | 93 | 45 |
| daily | 65 | 22 | 21 | 167 | 91 | 47 |
| play | 26 | 21 | 49 | 383 | 77 | 24 |
| train | 43 | 17 | 23 | 380 | 67 | 31 |
| alliance | 43 | 10 | 14 | 40 | 100 | 34 |
| research | 30 | 8 | 16 | 91 | 37 | **30/30** |
| construct | 7 | 5 | 39 | 108 | 71 | 4 |
| collect_city | 53 | 4 | 5 | 47 | 98 | 49 |
| rebels | 27 | 2 | 4 | 39 | 85 | **27/27** |

Tổng thời gian trong bước là 25,5 giờ trên tổng 31,6 giờ máy bật. Phần chênh **~6,1 giờ** là bật máy, mở game, đóng popup và tắt máy.

### 3.2 Chi phí cố định và khoảng chết [MEASURED]
| Chỉ số | Giá trị |
|---|---|
| Bật máy → bước đầu (lần ghé ok, n=167) | trung vị **75 s**, p90 113 s, max 764 s |
| `_wait_game`: game sẵn sàng (n=164, log) | trung vị 28 s, p90 44 s (sàn cứng 15 s) |
| Khoảng giữa 2 bước (n=921) | trung vị 0,6 s, p90 2,4 s, tổng 24 phút |
| Kết quả lần ghé | ok 167 (24,1 h) · interrupted 62 (2,5 h) · error 18 (3,9 h) · stopped 10 (1,1 h) |
| Khoảng cách giữa 2 lần ghé smart, mỗi máy | trung vị 20–31 phút |
| Số bước / lần ghé smart | TB 4,8 |

### 3.3 Chi phí CPU đo offline [MEASURED, ảnh `logs/capture-540-city.png`, 10 lần]
| Thao tác | Trung vị |
|---|---|
| `ocr.topbar` (6–7 lần Tesseract) | **1.057 ms** |
| `ocr.text` 1 ROI nhỏ | 130 ms |
| `screens.identify` / `nav_action` | 129 ms |
| `vision.find` 1 ảnh mẫu toàn màn | 32–37 ms |
| `badges.red_dots` toàn màn | 4,6 ms |
| `learn.feat` (vector kNN) | 2,1 ms |
| `Store.update` (đọc + ghi state.json 46 KB) | 11 ms |

Có 16 chỗ gọi `topbar`/`_power`. Mỗi lần gọi `mainquest._blocked` hay `quests._battle_blocked` chạy lại `ensure_city()` + `topbar` (~1,2 s+) chỉ để đọc lực chiến.

### 3.4 Chạm và điều hướng [MEASURED, `exp`, `nav`]
- 10.107 lần chạm của bot, **91,3 %** làm màn đổi. Thời gian trung bình từ chạm tới lần chụp kế: 2,07 s. Riêng `tap_tpl`: 3,21 s.
- Chạm ít ăn nhất: `notify.claim_content` 398 lần, chỉ 31 % đổi màn. `gather/btn_recommended` 111 lần, **0 %**. `notify.hub` 241 lần, 61 %.
- Số dòng điều hướng mỗi lần ghé: `reddots` 18, `quests` 18, `gather` 8,3, `rewards` 8,4. Có 443 lần gặp màn `unknown`.
- Đếm tĩnh: 98 lời gọi `time.sleep(<hằng số>)`, tổng 86,8 s trên mọi nhánh code. `wait_scale = 0.5` chỉ áp dụng cho `tap*`, không áp dụng cho các `sleep` này.

### 3.5 Kết quả nhiệm vụ / xây dựng [MEASURED, log 11-19 → 11-21]
| Kết quả | Lần |
|---|---|
| `Nhiem vu tab_2_main -> none` | **391** |
| `Nhiem vu chuong -> follow_idle / follow_weak / follow_max` | 69 / 57 / 37 |
| `Nhiem vu ... -> started` (+ follow_build_started) | 21 + 2 + 2 |
| `Thieu dieu kien (cap 4) -> Nhay` | 18 (cùng 12 lần ở cấp 1–3) |
| `Nhiem vu chinh: follow_idle / follow_max / follow_stuck` | 34 / 29 / 22 |
| `Nhiem vu chinh: build_started` | 2 |

**[INFERRED]** Sau "Nhảy", `upgrade_here` đệ quy và thường trả về `none`: camera đã tới công trình nhưng menu công trình chưa mở. Lúc đó `mainquest` chuyển sang `tutorial.follow`, chạy tới 40 bước rồi kết thúc `idle`/`max`. Đây là chuỗi điều kiện tiên quyết mà agent mới phải mô hình hóa tường minh thay vì dò theo nút "Nhảy".

---

## 4. Bottleneck theo mức ảnh hưởng tới mục tiêu nâng nhà chính

| # | Vấn đề | Ảnh hưởng đo được | Nhãn |
|---|---|---|---|
| B1 | Lập lịch kéo máy theo "thợ rảnh" mà không xét khả thi hay blocker | 111 lần ghé, 13,3 h, ~0 nâng cấp | MEASURED + OBSERVED |
| B2 | Chuỗi điều kiện nâng cấp ("Nhảy") không đi tới nút nâng cấp, và tab Chính "Đến" thường dẫn sang màn khác | 391 + 30 lần thử vô ích, ~415 phút | MEASURED, INFERRED cơ chế |
| B3 | `reddots` ALWAYS, đứng trước bước xây, không giãn chu kỳ | 426 phút, 7 % ok | MEASURED |
| B4 | Dữ kiện cũ được làm tươi (`_remember_facts`), nhà chính không được đọc lại | hq_level có thể sai; ~10 lần đọc trong 3 ngày | OBSERVED + INFERRED |
| B5 | Thu thập, bản đồ và nghiên cứu bị cổng theo nhà chính, farm không có nguồn tài nguyên chủ động | tài nguyên farm 30–45k | INFERRED, chưa có chi phí nâng cấp để chứng minh |
| B6 | `mainquest`/`quests` bị chặn chờ lực chiến (`need_power`), nhưng không có hành động nào được chọn **để** tăng lực chiến | #0 chặn với need 933.040 | OBSERVED |
| B7 | Chi phí cố định mỗi lần ghé ~75 s + tắt máy + `sleep(5)` | ~5,4 h / 257 lần ghé | MEASURED |
| B8 | OCR `topbar` ~1 s, gọi lặp lại để đọc lực chiến; `ensure_city` dày đặc | chưa tách được tổng thời gian | MEASURED đơn vị, chưa đo tổng |
| B9 | Lỗi chụp màn hình ("Khong chup duoc man hinh") làm hỏng bước và gây backoff | 6/6 backoff hiện tại do lỗi này; `quests` #3 264 s, `mainquest` #3 418 s rồi lỗi | MEASURED |
| B10 | Nhánh chạm vô ích: `gather/btn_recommended` (0 %), `notify.claim_content` (31 %) | 111 + 398 lần chạm | MEASURED |

---

## 5. Module chạy thừa / sai thứ tự

- **`reddots`**: CLAUDE.md và docstring ghi "cuối lượt", nhưng `ORDER` đặt nó **thứ 3**. Nó chạy mỗi lần ghé (`ALWAYS`), kể cả lần ghé chỉ vì thợ rảnh. Bước này nên theo giá trị (H3) hoặc đứng sau các bước có mục tiêu. **[OBSERVED]**
- **`research`** trên farm: 30/30 lần trả về 0, đa số là `miss` (thiếu ảnh mẫu) hoặc bị cổng nhà chính < 8. **[MEASURED]**
- **`rebels`**: 27/27 lần trả về 0, trung bình 4 s, phần lớn dừng ở cổng kiểm tra. Tốn ít, nhưng mỗi lần vẫn chạy `march_full()` (OCR) và `defense.under_attack`. **[MEASURED]**
- **`collect_city`** 49/53, **`daily`** 47/65, **`intel`** 45/57, **`alliance`** 34/43 lần trả về 0. Tốn ít, nhưng mỗi bước cộng thêm khoảng ~1 s cho `defense` + `_follow_guide` + `ensure_city`. **[MEASURED]**
- **`mainquest` và `quests`** cùng làm một việc (đi theo nhiệm vụ) và cùng bị kéo bởi một trigger. Mỗi bước tự chạy lại `ensure_city` + `_power` + `follow`. **[OBSERVED]**
- `observe` chạy **cuối**, nên lập lịch luôn dựa trên quan sát của **lần ghé trước**. Đầu lần ghé không có quan sát nào để quyết định nên làm bước nào. **[OBSERVED]**

---

## 6. Hiện trạng ML và mức có thể tận dụng

| Thành phần | Vị trí | Dùng cho | Tái dùng trong agent mới |
|---|---|---|---|
| Nhật ký kinh nghiệm `exp` | `Ctx._exp_*`, `Learner.record` | kết quả từng lần chạm | Có: ước lượng xác suất thành công và thời lượng của Action (verification, retry policy) |
| kNN màn hình (1.643 mẫu) | `learn.Learner.predict` | màn `unknown` trong `goto` | Có: tầng nhận biết "đang ở màn nào" cho WorldModel (Observed) |
| Biến thể ảnh mẫu (F2) | `learn.promote` | nút đóng/quay lại | Giữ nguyên, chỉ trong `LEARNABLE` |
| Thompson (H2) | `Learner.choose_close` | chạm nút đóng hay phím Back | Mẫu để mở rộng sau cho lựa chọn **an toàn** giữa các cách điều hướng |
| Adaptive wait (H1) | `Ctx._after_tap`, `react_wait` | chờ sau mỗi lần chạm | Giữ nguyên. Không giảm thêm khi chưa có điều kiện xác nhận |
| Giá trị bước (H3) | `scheduler.value_factor` | giãn chu kỳ bước chạy kèm | Thay bằng ước lượng "giá trị kỳ vọng" của Action trong DecisionEngine |

Chưa có thành phần nào học **chiến lược**. Nhận định này khớp với yêu cầu: chưa nên thêm ML chiến lược vì `runs.ret` chưa có ngữ nghĩa thống nhất, và chưa có dữ liệu chi phí/kết quả nâng cấp.

---

## 7. Đầu vào cho WorldModel: phân loại dữ liệu hiện có

| Trường | Nguồn hiện tại | Phân loại hiện thực | Ghi chú |
|---|---|---|---|
| HQ level | `read_hq` (OCR avatar), `upgrade_here` (màn tăng cấp) | Observed lúc đọc, sau đó **Stale nhưng bị dán nhãn mới** | B4 |
| Cấp các công trình khác | không có | **Unknown** | Chỉ thấy lúc ở màn tăng cấp/menu (`menu_level`) và không được lưu |
| Tài nguyên | `observe` → `ocr.topbar` | Observed cuối lần ghé | Không có seen_at riêng trong state (dùng `resources_at`) |
| Thợ xây | `observe.read_builders` (x/y) | Observed | Farm hiện x/2 nhưng chỉ dùng được 1 |
| Timer xây | `observe` thanh tiến độ (`src=ocr_bar`, conf 0,7), mainquest busy | Inferred | Farm không có timer nào |
| Nghiên cứu | timer `research` | Observed/Inferred | Chỉ có ở #1 |
| Quân / hành quân | `read_marches`, `observations` | Observed (TTL ngầm 15–20 phút trong `march_full`) | TTL viết cứng trong code |
| Nhiệm vụ hiện tại | không lưu | **Unknown** | Chỉ có log văn bản |
| Điều kiện nâng HQ (công trình cần cấp X) | không có | **Unknown** | Thiếu dữ liệu nền quan trọng nhất |
| Chi phí nâng cấp | không có | **Unknown** | |
| Lực chiến | `topbar`, `need_power` (state.json) | Observed, lưu rời rạc | `quests_need_power` không sang `facts` |

---

## 8. Rủi ro

- **R1 – Dữ liệu tài khoản (ADR-0010):** Phase 0 không chạm vào máy hay dữ liệu app. Các phase sau chỉ thêm tầng quyết định, **không** thêm thao tác ghi dữ liệu app.
- **R2 – Kim cương (ADR-0008):** ActionRegistry phải có danh sách cấm cứng (giữ quy tắc của `build.upgrade_here`, `claim_loop`) đứng **ngoài** DecisionEngine. Utility không được phép chọn một Action có `cost.premium > 0`.
- **R3 – `memory.db`:** schema `CREATE TABLE IF NOT EXISTS` + `ALTER` bỏ qua lỗi. Migration mới phải chỉ thêm bảng/cột. Phase này chỉ đọc trên bản sao.
- **R4 – Hai tiến trình runner** có thể cùng chạy: `state.py` có xử lý ghi đè, và log cho thấy song song 2 máy trong khi settings ghi 1. Cần làm rõ trước khi gắn adapter mới.
- **R5 – OCR sai làm WorldModel sai:** mỗi trường cần `confidence` + `source` + `observed_at` + TTL. Khi dữ liệu Stale, agent phải lên kế hoạch "quan sát lại" thay vì hành động mù.
- **R6 – Không có test tự động.** Có 44 fixture ảnh và `tools/check_*`, nhưng chưa có pytest. Phase 1 sẽ thêm test thuần, không cần thiết bị.

## 9. Dữ liệu còn thiếu

1. **Điều kiện nâng nhà chính theo cấp** (công trình nào, cấp mấy) và **chi phí tài nguyên/thời gian**. Đây là dữ liệu nền cho dependency graph. Đề xuất: chủ dự án cung cấp bảng (hoặc ảnh màn "Tăng cấp" từng cấp từ #1 / farm), bot ghi thêm khi gặp màn tăng cấp.
2. **Baseline thủ công 4 giờ**: thứ tự thao tác người chơi làm (đã có `tools/record.py`, `logs/human/`). Cần 1 bản ghi đầy đủ để so sánh.
3. **Thời gian ADB thực tế** (screencap, `input tap`) trên máy hiện tại. Cần đo khi được phép bật 1 instance.
4. **Lịch sử nhà chính theo thời gian** từng farm: log cũ không có tên luồng, `facts` chỉ giữ giá trị cuối.
5. **Ý nghĩa thống nhất của `runs.ret`** (số nâng cấp, số quà…). Hiện mỗi module tự định nghĩa.
6. **Ảnh màn sau "Đến" ở tab Chính** (391 lần `none`), để biết nó dẫn đi đâu.

---

## 10. Đề xuất Phase 1 — WorldModel (chờ duyệt)

> **Đã được thay thế** bởi [MASTER-IMPLEMENTATION-PLAN.md](MASTER-IMPLEMENTATION-PLAN.md): mã mới nằm trong `src/aowbot/` (ADR-0013) thay vì `bot/agent/`. Task tương ứng là B2a/B2b.

Phạm vi (chỉ thêm, không sửa luồng runner hiện tại):
- `bot/agent/world.py`: dataclass `Fact(value, source, observed_at, confidence, ttl)` với trạng thái suy ra `observed | inferred | stale | unknown` (hàm thuần theo `now`). `WorldModel` gồm HQ, công trình, tài nguyên, thợ, timer, nghiên cứu, quân, hành quân, nhiệm vụ, lực chiến.
- `WorldModel.from_memory(mem, store_snapshot, now)`: adapter **chỉ đọc** từ `facts`/`timers`/`observations`/`state.json`. Nó không coi giá trị `_remember_facts` làm tươi là Observed: dùng `observations.at` và `resources_at` khi có.
- Cấu hình TTL cho từng trường trong `config.yaml` (`agent.ttl.*`).
- `tests/test_world.py` (pytest hoặc unittest thư viện chuẩn, không thêm dependency nặng): dựng từ DB giả và từ bản chụp `memory.db` cố định. Phải xác định được trạng thái stale/unknown và cho kết quả giống nhau qua nhiều lần chạy.
- Lệnh xem: `python main.py --world <idx>` (dry-run, không bật máy) in ra WorldModel cùng nhãn tin cậy.

Không thuộc Phase 1 (để dành Phase 2+, cần duyệt riêng): sửa `_remember_facts` (B4), đổi vị trí `reddots` (B3), sửa `plan_build` (B1). Đây là thay đổi hành vi. Nếu chủ dự án muốn, có thể làm thành "bản vá nhanh" riêng trước Phase 1.

**Chờ chủ dự án xác nhận** trước khi bắt đầu Phase 1.

---
---

# Phần B: Bổ sung theo đặc tả "Goal-Driven Agent Architecture" (bản 2, 2026-11-21)

Bản 2 đổi mục tiêu sản phẩm: **hiệu quả farm và phát triển tài khoản bền vững**, ra quyết định **theo sự kiện**. Tiêu chí thành công đầu tiên là vòng *đội về → cập nhật trạng thái → chọn mỏ → gửi quân → xác minh → hẹn sự kiện kế*, không chạy lại cả chuỗi module. Phần A ở trên vẫn đúng. Phần B bổ sung các mục bản 2 yêu cầu mà phần A chưa có, cộng kế hoạch migration. **Vẫn không sửa code.**

## B1. Hợp đồng module hiện có [OBSERVED]

| Thuộc tính | Hiện trạng |
|---|---|
| Chữ ký | `run(ctx)` (`defense.run(ctx, force)`, `tutorial.run(ctx, max_steps, …, follow, no_battle)`) |
| Đầu vào | Toàn bộ `ctx`: thiết bị, vision, cfg đã gộp, `ctx.store`, `ctx.mem`, `ctx.visit`, `ctx.step` |
| Giá trị trả về | Số nguyên "số việc làm được" ở 15/18 module. Ngoại lệ: `observe` trả `dict`, `tutorial` trả chuỗi hoặc bool, `defense` trả `None`/kết quả. **Ý nghĩa không thống nhất**: `gather` = số đội đã gửi, `rewards` = số lần nhận, `notify` = dict |
| Điều kiện trước | Rải rác ở 3 nơi: cổng trong `run_account` (research < HQ8, `rebels_ready`, `march_full`, `WORLD_STEPS`), đầu `run()` của module (gather < HQ9, `_blocked` lực chiến), và `scheduler.plan_*` |
| Hiệu ứng | Ghi thẳng vào `ctx.store` (state.json) và `ctx.mem` (facts/timers), không khai báo. `observe` có 10 chỗ ghi, `mainquest` 3, `defense` 3, `gather.record_dispatch` 1 |
| Xác minh | Ngầm: module tự kiểm (vd `gather` thấy `btn_march` còn trên màn → `NO_TROOPS`). Runner chỉ phân loại ok/warn/miss/err/stuck theo ngoại lệ và số ảnh debug, **không theo việc mục tiêu có đạt hay không** |
| Điều hướng | Module tự `ensure_city()`/`ensure_world()` ở đầu và cuối, nên cùng một màn được dựng lại nhiều lần |
| Phạm vi | Mỗi `run()` là cả một nhóm việc: `gather` lặp tới khi đầy hành quân (tối đa 40 lần thử). Một Action nguyên tử của agent sẽ nhỏ hơn module hiện tại |

**Hệ quả cho adapter:** bọc nguyên module thành Action "thô" (`LegacyModuleAction`) dùng được ngay, nhưng chỉ xác minh được ở mức "chạy xong". Với vòng hành quân (tiêu chí đầu tiên), cần tách `gather.try_dispatch(ctx, rtype, level, max_level)`. Hàm này **đã gần như là một Action nguyên tử**: 1 mỏ, trả mã kết quả rõ ràng (`ok/notfound/full/notroops/toobig/locked/nosearch/error`), đọc được tải trọng, trữ lượng và thời gian đi. Có thể dùng lại mà không viết lại thao tác UI.

## B2. Cơ chế sự kiện / timer hiện có [OBSERVED]

- **Không có event bus.** Mọi thứ là **polling**: `_loop_smart` gọi `scheduler.decide()` mỗi `idle_check_min` (15 phút), hoặc mỗi 15 s khi có máy đang chạy. Lần ghé nào cũng chạy hết các bước được chọn theo `ORDER`.
- **Timer** = bảng `timers(inst, key, due_at, src, conf)`, key `march:i`, `arrive:i`, `build:*`, `research`. `observe.remember` **xóa và ghi lại toàn bộ** `march:*`/`arrive:*` sau mỗi lần ghé, nên timer không có danh tính ổn định (không biết "đội số 2 đã về").
- **Tín hiệu đánh thức trong tiến trình:** `threading.Event _wake` (Chạy ngay / Dừng / luồng máy xong). Đây là cơ chế duy nhất gần giống sự kiện.
- **"Sự kiện" ngầm khác:** `facts.mainquest_busy_until`, bảng `backoff.until`, `last_reset()` (reset ngày 0h UTC, `loot.reset_utc` 4h), cảnh báo tấn công (`defense.under_attack` kiểm **trước mỗi bước**, chụp 1 ảnh mỗi lần).
- **Không có chống trùng.** Hai trigger cùng máy được gộp thành một `Visit`, nhưng không có id sự kiện, không có nhật ký sự kiện đã xử lý.

## B3. Vòng thử lại (retry) hiện có [OBSERVED, số max là cấu hình hoặc hằng trong code]

| Vòng | Giới hạn | Chi phí xấu nhất |
|---|---|---|
| `Device._screencap` | 4 lần, chờ 1,5·k s, sau đó `wait_ready(30)` và chụp thêm 4 lần | **~75 s cho một lần `shot()`** khi máy treo. Đo được: `quests` #3 264 s, `mainquest` #3 418 s rồi lỗi |
| `Device.wait_ready` | `boot_timeout` 120 s, thử 3 địa chỉ adb | 120 s |
| `LDConsole.launch` (chờ chỗ) | `wait_slot_min` 60 phút, kiểm tra mỗi 30 s | 60 phút |
| `LDConsole.quit` | 2 × 25 s | 50 s |
| `_wait_game` | 45 s, mở lại game 1 lần | ~105 s |
| Watchdog | màn đứng yên 5 phút; bước 20 phút (tutorial 120, mainquest/reddots 30); `max_restarts` 2 | ~60–90 phút mỗi lần ghé |
| Runner | `blind ≥ 2` hoặc `lost ≥ 3` thì bỏ cả lần ghé | – |
| Backoff (chỉ smart) | 30 → 60 → … → 360 phút cho mỗi (máy, bước) | 6 h |
| Trong module | `goto` 10 vòng, `close_popups` 5–10, `claim_loop` `max_taps×2`, `gather` 40 lần thử, `reddots` 6 vòng, `tutorial` 600 bước | – |

**Có giới hạn ở mọi vòng (không có vòng vô hạn) [OBSERVED].** Nhưng **không có giới hạn theo giá trị**: "thợ rảnh" hay "4 đội rảnh" kéo máy lên lặp lại vô thời hạn khi lần ghé không tạo ra kết quả (B1 ở phần A, B5 dưới đây).

## B4. Vòng đời đa tài khoản [OBSERVED]

- **1 tài khoản = 1 instance LDPlayer** (không chuyển tài khoản trong instance; Account Manager vẫn là PoC). Một lần ghé gồm: bật VM → mở game → các bước → tắt VM.
- **Song song:** tối đa `schedule.parallel` luồng (≤ `max_running` = 2). Khóa `LDConsole._slot` làm việc kiểm tra số máy + launch nguyên tử. `_busy[idx]` chặn 2 luồng trên cùng máy **trong cùng một Runner**. **[INFERRED]** Hai tiến trình (web + CLI) vẫn có thể ghé cùng một máy, vì không có khóa liên tiến trình. `state.py` có comment về "2 runner chạy song song".
- **Tài nguyên dùng chung giữa các luồng:** `Vision`, `Learner` (singleton, có lock), `Memory` (kết nối SQLite theo luồng, WAL), `Store` (RLock toàn cục, ghi lại cả file mỗi `update`), `steer._battle_cv` (máy đang lái quân giành CPU, máy kia chờ tối đa 150 s).
- **Khởi động lại tiến trình:** `close_open_visits()` đánh dấu lần ghé dở là `interrupted` (62 lần, 2,5 h) và tắt VM còn sót. **Không lưu trạng thái hành động đang dở**, nên không biết đội đã gửi hay chưa nếu chết giữa `try_dispatch`. Hiện bù bằng cách đọc lại "Hành quân x/y" ở lần sau.
- **Chi phí phiên:** bật máy đến bước đầu mất trung vị 75 s (phần A §3.2), cộng thời gian tắt và `sleep(5)`. Chính sách hiện tại **luôn tắt VM** sau mỗi lần ghé, kể cả khi sự kiện kế của máy đó chỉ vài phút sau.

## B5. Luồng hành quân (tiêu chí thành công đầu tiên) [MEASURED trên #1, nhà chính 30, 5 đội]

Trace hiện tại: `observe` (cuối lần ghé) → `ocr.marches` đọc trạng thái và đồng hồ từng dòng → `remember` ghi `march:i`/`arrive:i` → `scheduler.plan_gather` → `Visit` → `run_account` chạy **mọi** bước được chọn (reddots, notify…) → `gather.run` → `read_marches` → `try_dispatch` nhiều lần → `observe`.

| Số đo | Giá trị |
|---|---|
| Dòng hành quân đọc được thời gian (#1, tất cả `observations`) | **30/126 (24 %)**; 96 dòng `unknown` hoặc không có đồng hồ |
| Lần ghé có lý do "N đội rảnh" | 15 lần, 85 phút máy bật |
| … mà quan sát **ngay trước đó** ghi 5/5 đầy | **11/15** |
| … mà `gather` gửi 0 đội | 5/15 |
| `gather` trên #1: tổng | 28 lần, 49,5 phút, gửi 26 đội; kết quả ok 9 · warn 13 · miss 5 · err 1 |
| Thời gian một lần `gather` có gửi | 36–413 s (trung vị ~110 s) |

**Nguyên nhân [OBSERVED trong code]:** `plan_gather` tính `busy = len(timers "march:")`. Đội nào OCR không đọc được đồng hồ thì không có timer, nên bị **tính là rảnh**. Kết quả là máy bị kéo lên dù cả 5 đội đang đi. Đây là ví dụ rõ nhất cho nguyên tắc "Unknown ≠ rảnh" mà WorldModel phải thực thi.

**Hệ quả cho tiêu chí đầu tiên:**
1. Sự kiện "đội về" hiện **không phát hiện tin cậy được** từ OCR danh sách hành quân. Nguồn chắc chắn hơn là con số "Hành quân x/y" (`read_marches`, nhiều tầng OCR), quan sát **khi máy đã bật**.
2. Farm (nhà chính 3–5) bị `gather.min_hq_level = 9` chặn và bản đồ chưa mở, nên **chỉ #1 (và có lúc #0) dùng được để nghiệm thu tiêu chí đầu tiên** [OBSERVED].
3. Dùng lại được ngay: `try_dispatch` (Action), `too_big_known` + `facts mine_cap:*` (tri thức mỏ), `last_travel` (đi = về), `arrive:*` (giờ tới mỏ, conf 0,9).

## B6. Bottleneck bổ sung (đánh số tiếp phần A)

| # | Vấn đề | Bằng chứng |
|---|---|---|
| B11 | Đội không đọc được thời gian bị coi là rảnh, kéo máy lên vô ích | 11/15 lần ghé "đội rảnh" ngay sau quan sát 5/5 [MEASURED] |
| B12 | Không có danh tính đội hay sự kiện; timer bị xóa và ghi lại mỗi lần ghé | `observe.remember` [OBSERVED] |
| B13 | Mỗi sự kiện = 1 phiên VM đầy đủ (~75 s khởi động + các bước kèm), VM luôn bị tắt | phần A §3.2 + B4 |
| B14 | `defense.under_attack` + `_follow_guide` chụp thêm ảnh quanh **mỗi** bước | `run_account` [OBSERVED]; chưa đo tổng |
| B15 | Một lần `shot()` có thể mất ~75 s khi ADB treo, nhân với số lần chụp trong bước | `_screencap` + B9 |

---

## B7. Kế hoạch migration (đề xuất, chờ duyệt)

### B7.1 Ánh xạ 11 domain vào mã hiện có

Gói mới `bot/agent/` (thư viện chuẩn + numpy/OpenCV đã có, **không thêm dependency**). Mỗi domain một gói con. Code cũ chỉ được **gọi qua adapter**, không bị sửa ở Phase 1–3.

| Domain | Mới | Dùng lại / bọc |
|---|---|---|
| `core` | `Event`, `EventBus` (hàng đợi ưu tiên theo `due_at`, trong tiến trình), `Dispatcher`, `Clock` (giả lập được cho test) | `Runner._wake`, `_stop` |
| `perception` | `Observation(value, source, at, confidence)`, `Perceiver` (bọc OCR/vision trả kèm độ tin) | `screens.identify`, `ocr.*`, `ctx.read_marches`, `observe.*`, `learn.predict` |
| `world` | `AccountWorld`, `Fact` (observed/inferred/unknown/stale theo TTL), lưu trữ | `memory.db` `facts`/`timers`/`observations` (chỉ **thêm** bảng/cột), đọc `state.json` |
| `goals` | `Goal(satisfied(world), deficit(world))`: MarchUtilization, ResourceFarming, ContinuousConstruction/Research/Training, ResourceBalance, AccountMaintenance | `scheduler.plan_*` làm nguồn ngưỡng ban đầu |
| `planning` | `ActionSpec(pre, effects, duration_est, cost, risk, verify, retry)`, `ActionRegistry`, `Planner` (dependency/GOAP rút gọn) | `scheduler.world_ready`, `rebels_ready`, cổng trong `run_account` |
| `decision` | `UtilityScorer` (trọng số trong `config.yaml → agent.weights`), `Explanation` | `scheduler.value_factor` (H3) |
| `execution` | `Executor` (1 Action/lần, khóa theo tài khoản), `Verifier`, `Recovery` | `Ctx`, `ensure_city`, watchdog `Stuck`, `_restart_game`, `gather.try_dispatch` |
| `scheduling` | `TimerRegistry` (id ổn định, chống trùng), quản lý wake-up và **phiên VM** | bảng `timers`, `last_reset`, `backoff` |
| `learning` | ước lượng thời lượng/xác suất thành công của Action từ log | `exp`, `runs`, `learn.Learner` (H1/H2 giữ nguyên) |
| `accounts` | `AccountAgent` (1/tài khoản), `SessionCoordinator` (≤ `max_running`, khóa liên tiến trình bằng file/SQLite) | `LDConsole._slot`, `Runner._busy` |
| `adapters` | `LegacyModuleAction`, `DeviceSession` (bật/tắt VM + mở game) | `ORDER`, `run_account` các bước 1–3, `defense` |

### B7.2 Quyết định thiết kế đề xuất

1. **Phiên VM là tài nguyên, không phải đơn vị công việc.** Executor xin "lease" phiên cho tài khoản. Sau một Action, nếu sự kiện kế của tài khoản đó đến trong `agent.keep_alive_min` **và** không có tài khoản khác đang chờ chỗ, thì giữ VM. Nếu không, tắt VM. Giải quyết B13 mà vẫn giữ trần 2 máy (CLAUDE.md quy tắc 4).
2. **Unknown không bao giờ được hiểu là "rảnh" hay "xong".** Goal có deficit với dữ liệu unknown/stale sẽ sinh **Action quan sát** (rẻ, khi VM đang bật) thay vì Action tác động. Sửa B4/B11 theo cách có cấu trúc.
3. **Sự kiện có khóa chống trùng** `(account, type, subject, due_bucket)` và trạng thái `pending → claimed → done/failed`, lưu trong bảng mới `events` (ghi thêm vào `memory.db`, chỉ `CREATE TABLE IF NOT EXISTS`). Khởi động lại thì đưa `claimed` quá hạn về `pending` nếu Action có `idempotent_check` (vd đọc lại "Hành quân x/y" trước khi gửi lại).
4. **Chính sách đứng trước Executor, không trong Scorer.** `Policy.allow(action, world)` chặn mọi Action có `cost.premium > 0` trừ danh sách trắng ADR-0008 (khiên có trần), chặn Action tác động khi `screen_confidence < ngưỡng`, chặn khi đã vượt `retry_limit`. Học máy chỉ được đổi ước lượng và xếp hạng.
5. **Fallback:** `schedule.mode` thêm giá trị `agent` (mặc định vẫn `smart`). `Runner._loop` chọn `_loop_agent` chỉ khi bật. `dry_run: true` chạy toàn bộ vòng quyết định, ghi giải thích, **không chạm game**.
6. **Giải thích:** mỗi quyết định ghi 1 dòng `decisions` (bảng mới) gồm sự kiện, goal, ứng viên + điểm thành phần, policy, Action chọn, hiệu ứng kỳ vọng, kết quả thực, lần đánh giá kế. Web đọc bảng này.

### B7.3 Phase và tiêu chí nghiệm thu

| Phase | Nội dung | Thay đổi hành vi | Nghiệm thu |
|---|---|---|---|
| **1 – Hạ tầng sự kiện** | `core` + `scheduling`: Event, EventBus, Dispatcher, Clock giả lập, TimerRegistry, bảng `events` + log; sinh sự kiện từ `timers` hiện có (chỉ đọc) | **Không** (chạy song song ở chế độ quan sát, ghi sự kiện "lẽ ra sẽ phát") | Unit: chống trùng, thứ tự theo `due_at`, khôi phục sau restart. Tích hợp: phát lại `memory.db` (bản sao) cho cùng dãy sự kiện sau 2 lần chạy. Benchmark: số sự kiện so với số lần ghé thực tế |
| **2 – WorldModel + ActionRegistry** | `perception`, `world`, `adapters`: Fact/TTL/confidence, `AccountWorld.from_memory`, `LegacyModuleAction` cho 18 module, `DispatchGatherAction` bọc `try_dispatch`, `ObserveMarchesAction` | Không | Unit: phân loại observed/inferred/unknown/stale; "đội không có đồng hồ" là unknown (B11). Tích hợp: dựng world cho #0–#6 từ bản sao DB |
| **3 – Goal + Planner (dry-run)** | `goals`, `planning`, `decision` (chấm điểm chỉ để giải thích); `python main.py --plan <idx>` | Không | Mỗi quyết định có giải thích; tất định với cùng world + Clock; tái hiện 15 lần ghé "đội rảnh" của #1 và chứng minh planner **không** kéo máy lên ở 11 lần sai |
| **4 – Tự hành có kiểm soát** | `execution`, `accounts`, Policy, khóa, verify, retry, recovery, phiên VM; `schedule.mode: agent` chỉ cho vòng hành quân trên #1 | **Có**, bật theo máy | Tiêu chí đầu tiên: phát hiện đội về → chọn mỏ → `try_dispatch` → xác minh x/y tăng → hẹn sự kiện kế, **không** chạy `ORDER`. Thử 1 lượt + 1 lần chạy lại (memory `aow-test-one-pass-recheck`) |
| **5 – Học + tối ưu** | ước lượng thời lượng Action, bandit ngữ cảnh chọn (loại, cấp) mỏ trong tập an toàn, analytics | Có (trong khuôn Policy) | So với `smart` cùng trạng thái đầu: tỉ lệ đội đi, phút VM bật / đội gửi, số lần ghé vô ích |

### B7.4 Tương thích ngược
- `memory.db`: chỉ thêm `events`, `decisions` (và có thể `facts.source/confidence` qua `ALTER … ADD COLUMN`, bỏ qua nếu đã có). Không đổi hay xóa bảng cũ. `user_version` tăng lên 5 (code cũ không đọc giá trị này).
- `config.yaml`: thêm khối `agent:` (mặc định tắt); khóa cũ giữ nguyên nghĩa. `settings.json` không đổi cấu trúc.
- `state.json`: agent ghi thêm khóa `agent_*` cho web. Web cũ bỏ qua khóa lạ.
- Module cũ: không sửa ở Phase 1–3. Phase 4 có thể cần tách nhỏ `gather.run` (đã có `try_dispatch` nên ít rủi ro). Mọi sửa đổi module phải nêu rõ và chờ duyệt.

### B7.5 Mâu thuẫn cần chủ dự án quyết định
1. **Mục tiêu chính:** bản 1 ưu tiên **nâng nhà chính**, bản 2 ưu tiên **hiệu quả farm**. Farm cấp 3–5 không thu thập được (`gather.min_hq_level = 9`, bản đồ < 6), nên "farming efficiency" trên farm **phụ thuộc** vào việc nâng nhà chính trước. Đề xuất: Goal `ContinuousConstruction` có trọng số cao nhất khi nhà chính < `gather.min_hq_level`, sau đó chuyển sang farm.
2. **"Full autonomy"** so với ADR-0012 (duyệt từng phase): giữ ADR-0012, tự hành chỉ bật theo máy ở Phase 4.
3. **Giữ VM bật giữa các sự kiện** (B7.2-1) là thay đổi chính sách vận hành. Cần chủ dự án đồng ý ngưỡng `keep_alive_min`.
4. **Các bản vá nhanh B1/B3/B4/B11** (sửa trên runner cũ) có làm trước Phase 1 hay không.
