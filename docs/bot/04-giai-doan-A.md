# Báo cáo giai đoạn A — Trí nhớ + Lập lịch
Ngày: 2026-11-19 · Kế hoạch: [ke-hoach-A-tri-nho-lap-lich.md](../product/ke-hoach-A-tri-nho-lap-lich.md) · Chủ dự án cho làm liên tục A→D (2026-11-19)

## 1. Đã làm
| Bước | Việc | File |
|---|---|---|
| A0 | Ghi `visits` / `runs` / `observations` vào `data/memory.db`; báo cáo chỉ số | `bot/memory.py`, `bot/runner.py`, `bot/modules/observe.py`, `tools/baseline.py` |
| A1 | `timers` (đội quân về `march:<i>`), `facts` (số đội, tài nguyên, cấp nhà chính, tân thủ xong, NV chính chờ lực chiến); runner chép dữ kiện từ `state.json` sang sau mỗi lần ghé | `bot/memory.py`, `observe.remember()`, `Runner._remember_facts` |
| A2–A3 | Bộ lập lịch hàm thuần: trigger = **xây / thu thập / nghiên cứu** (+ tân thủ chưa xong); bước khác chạy kèm theo chu kỳ riêng `extra_every_min` (180) hoặc lần đầu sau reset 0h UTC; trần `max_gap_min` 240; vòng `smart` trong runner sau công tắc `schedule.mode` (mặc định `fixed`) | `bot/scheduler.py`, `Runner._loop_smart`, `config.yaml` → `schedule` |
| A3 | Giả lập offline 24 h `fixed` vs `smart` | `tools/sim_schedule.py` |
| A4 | Backoff (lỗi/kẹt liên tiếp → tạm bỏ 30→60→…≤6 h, chỉ áp dụng ở `smart`); web: "Ghé tiếp", "Tạm bỏ … Bỏ tạm dừng", nhóm tùy chọn "Lập lịch theo trí nhớ" | `Runner._backoff`, `web/server.py`, `web/index.html`, `web/options.py` |
| — | Quy tắc thu thập mới (chủ dự án 2026-11-19): **tải trọng đội ≥ trữ lượng mỏ**, không đọc được số thì không gửi; sơ tán phòng thủ bỏ qua kiểm tra | `bot/modules/gather.py` (`load_ge_mine`), `config.yaml`, `web/options.py` |

## 2. Giả thuyết → kiểm chứng
| # | Giả thuyết | Cách thử | Kết quả |
|---|---|---|---|
| H1 | Lập lịch theo timer giảm thời gian máy bật ≥ 30 % | giả lập 24 h, 6 máy | **Sai** lần đầu: +7 %. Nguyên nhân: "kiểm tra xây/nghiên cứu theo chu kỳ 60/120′" kéo mỗi máy lên mỗi giờ, mỗi lần chạy đủ ~10 bước chạy kèm |
| H2 | Bước chạy kèm có chu kỳ riêng + giãn chu kỳ xây 120′ sẽ sửa H1 | giả lập | 6 máy: thời gian bật ≈ không đổi (runner tuần tự đã **bão hòa**: 6 × 216′ ≈ 21,6 h/ngày), đội nằm không **−19…−32 %**. 2 máy: thời gian bật **−38…−43 %**, đội nằm không ≈ ngang |
| H3 | Đội nằm không còn cao vì `plan_gather` chờ 60′ khi có đội rảnh mà bỏ qua đội sắp về | đọc phân bố trong giả lập | **Đúng** → sửa: lấy mốc sớm hơn trong hai. (Kèm sửa lỗi giả lập cộng trùng thời gian nằm không) |

Số liệu trên là **[ĐO] trong giả lập** (mô hình: 3 đội, chuyến 2–5 h, bật máy 3′ + 1,5′/bước, 10 % lần gửi thất bại), **[CHƯA ĐO] trên máy thật**.

**Kết luận:** với 6 tài khoản, giới hạn thật là **một runner tuần tự**. Lập lịch giúp đội quân được gửi lại sớm hơn, nhưng muốn giảm thời gian máy bật thì phải rút ngắn lần ghé hoặc chạy 2 máy song song (đang cho phép `max_running: 2`, nhưng [ADR-0002](../adr/0002-chay-tuan-tu-tung-instance.md) chọn tuần tự) → đề xuất riêng, chờ chủ dự án.

## 3. Kiểm chứng offline
- Runner với thiết bị giả: ghi đúng ok/err/stuck, `gather` trả số đội, DB hỏng không làm dừng lượt.
- Vòng `smart`: lần ghé đầu chạy đủ bước; lần sau hẹn đúng lúc đội về (+50′), bỏ bước chạy kèm chưa tới chu kỳ; backoff 30′→60′; "Chạy ngay" vẫn chạy đủ.

## 4. Còn lại của A
- **[CHƯA ĐO]** lượt `fixed` thật trên 6 máy (đang chạy 2026-11-19 00:38) → mốc chuẩn; sau đó chạy `smart` và so bằng `python tools/baseline.py --mode smart`.
- OCR giờ xây xong / nghiên cứu xong (để thay chu kỳ ước lượng) — cần ảnh màn hàng thợ xây & viện nghiên cứu.

---

# Giai đoạn B — Nhận diện màn + `goto()` (2026-11-19)
| Việc | File |
|---|---|
| `identify(ảnh) → màn` (hàm thuần): exit_dialog / reward / popup / city / world / dialog / panel / panel_key / loading / unknown, theo thứ tự ưu tiên (màn chồng lên nhau) | `bot/screens.py` |
| Vùng tìm cố định cho từng ảnh mẫu (đo trên 240 ảnh `logs/`): **387 → ~190 ms/ảnh**, khớp 300/301 ảnh so với tìm cả màn (ảnh lệch đã sửa ROI) | `screens.ROI` |
| `ctx.goto(city/world/home)`: nhận diện → hành động → lặp; chạm 2 lần màn không đổi → chuyển phím Back; màn lạ lưu `logs/unknown/` (bỏ trùng theo dHash, tối đa 300) | `bot/ctx.py` |
| `ensure_city` / `ensure_world` dùng `goto()`, không tới được thì dùng cách cũ; tắt bằng `nav.smart: false` | `bot/ctx.py`, `config.yaml` |
| Hồi quy: `python tools/check_screens.py` (12/12) | `tools/check_screens.py`, `tests/fixtures/screens/` |

**Kiểm chứng offline [ĐO]:** 480 ảnh `logs/` → 95 % nhận ra; 26 ảnh "unknown" gồm: trận đánh/thua tân thủ, màn tải game (cửa thép), **màn hình chính Android (game đã thoát)**, bảng tìm mỏ (→ đã thêm `panel_key`). `goto()` đúng 4 tình huống ảnh thật (bản đồ→thành phố, thư→thành phố, thành phố→bản đồ, đứng yên→Back).

**Lỗi thật phát hiện ở lượt 07:35 (#0):** màn **CONGRATULATIONS** (kết quả chiêu mộ) có nút X đỏ chưa có ảnh mẫu → kẹt trên cùng, làm `rewards`, `daily`, `intel`, `gather` của cả lượt thất bại. Đã cắt `common/btn_x_red` (chỉ khớp màn CONGRATULATIONS) và thêm vào nút đóng popup.

# Giai đoạn C — Học từ lỗi (2026-11-19)
- Nhật ký điều hướng: mỗi hành động `goto()` ghi `(bước, màn, hành động, màn có đổi)` vào bảng `nav` (`data/memory.db`).
- Backoff bước lỗi liên tiếp (giai đoạn A4) + hiển thị/huỷ trên web.
- Báo cáo: `python tools/baseline.py` mục 4 (điều hướng theo bước: số màn lạ, chạm không ăn, số lần Back) và mục 5 (bước đang tạm bỏ).
- Màn lạ gom ở `logs/unknown/` → chủ dự án/agent dán nhãn: chép vào `tests/fixtures/screens/<nhãn>/` và cắt ảnh mẫu.

# Thu thập theo tải trọng (2026-11-19)
Số liệu thật #0: tải trọng đội **18.750**, mỏ đọc được **80.000–800.000** → với quy tắc "tải trọng ≥ trữ lượng mỏ" không mỏ nào hợp lệ. Chủ dự án chốt: chưa đủ thì làm nhiệm vụ trong căn cứ; từ **nhà chính cấp 9** (đủ 3 nhà lính) mới thu thập được mỏ lv1.
- `gather.min_hq_level: 9` (web: "Bắt đầu thu thập từ nhà chính cấp"): dưới mốc → `gather` thoát ngay, không mở bản đồ; bộ lập lịch không bật máy vì thu thập.
- `observe` đọc cấp nhà chính từ màn Thông tin chỉ huy (chạm avatar, OCR "Cấp Xưởng kiến trúc: N"), tối đa mỗi 6 giờ.
- Trí nhớ dung tích mỏ: mỗi lần mở mỏ đầy ghi `mine_cap:<loại>:<cấp>` và `march_load`; lần sau bỏ qua cấp đã biết quá sức chở mà không mở bản đồ (cấp thấp nhất luôn thử để đọc lại tải trọng khi lính tăng).
- Kiểm thử offline: nhà chính 3 → `gather` trả 0, không mở bản đồ; lịch "chưa thu thập"; cấp 6 (800.000 > 18.750) bị bỏ, cấp 1 vẫn thử.

# Lỗi thật trong lượt 6 máy (2026-11-19 sáng) và cách sửa
| Giờ | Máy | Hiện tượng | Nguyên nhân | Sửa |
|---|---|---|---|---|
| 07:41 | #0 | rewards/daily/intel/gather cùng hỏng | màn CONGRATULATIONS (kết quả chiêu mộ) có X đỏ chưa có ảnh mẫu | ảnh mẫu `common/btn_x_red` |
| 07:45 | — | bấm "Dừng" mà runner vẫn ngủ 30 phút | cờ đánh thức bị xoá sau khi "Dừng" đã đặt (lỗi có sẵn) | kiểm tra `_stop` trước khi ngủ (cả `fixed` và `smart`) |
| 08:08 | #0 | không đọc được cấp nhà chính | chưa rõ (không có ảnh) | đọc lại 1 lần, hỏng thì lưu `hq_unread` |
| 08:11–08:27 | #2 | mỗi bước ~3 phút rồi lỗi "Không chụp được màn hình", adb vẫn báo `device` | máy ảo treo phần chụp màn hình | 2 bước liên tiếp không chụp được → bỏ lượt máy đó (kiểm thử offline đạt) |
| 08:35 | #0 | gửi đội tới kim loại cấp 6 dù mỏ ~800.000 > tải trọng 18.750 | OCR đọc trữ lượng thành **606** → qua được quy tắc | trữ lượng mỏ đầy phải ≥ 10.000, tròn nghìn, ≥ 90 % dung tích đã nhớ; không hợp lý → đọc lại, vẫn sai → không gửi |
| 08:43 | #0 | không đọc được cấp nhà chính (màn đúng, "Cấp Xưởng kiến trúc: 5") | OCR đọc "truc" thành "tric" | lấy số sau dấu ":"; dự phòng đọc riêng vùng số; ảnh hồi quy `tests/fixtures/hq/` |
| 09:17 | #2 | không đọc được cấp nhà chính | TK đang tân thủ: hướng dẫn chiếm màn (bảng nâng Xưởng kiến trúc), chạm avatar không mở | bỏ đọc cấp nhà chính khi đang tân thủ |
| 09:28 | #3 | `goto(world)` thử 10 lần ×2, mất ~1 phút | bản đồ thế giới chưa mở (chuỗi "Dọn dẹp khu phế tích", Liên minh/Tạo đội còn khóa) | chạm nút chuyển bản đồ 2 lần không đổi → dừng, không dùng cách cũ dự phòng |
| 09:35–09:46 | #4 | tân thủ chạm giữa/Back mãi trên cảnh tối đen; các bước sau mỗi bước ~40 s `goto` thất bại (màn "loading") | cảnh tân thủ tối (đã gặp trong ảnh "unknown"), `decide()` không qua được — lỗi tân thủ có từ trước (Pha 1) | 3 bước liên tiếp không về được thành phố/bản đồ → bỏ lượt máy (kiểm thử offline đạt); lỗi tân thủ ghi lại để xử lý ở Pha 1 |

**[ĐO] goto() trên máy thật (#0, 1 lượt):** 79 hành động điều hướng, 0 màn lạ, 0 lần chạm không ăn, 0 lần phải dùng Back.

## Lượt `fixed` 6 máy với code B/C (08:45 → 10:25, 2026-11-19) [ĐO]
- Cả lượt **99,6 phút** (#0 14′, #2 ~20′, #3 15′, #4 21,7′, #5 6,1′, #6 22,7′).
- Thu thập: #0 và #5 bỏ qua đúng (nhà chính 5 và 3 < 9). #2/#3/#4 không mở được bản đồ thế giới (tân thủ / chưa mở) → đã có bản sửa dừng sớm.
- Cấp nhà chính đọc được: #0 = 5, #3 = 7, #5 = 3. #2, #4 đang tân thủ → bỏ đọc.
- Điều hướng: 552 hành động, 2 màn lạ; màn "loading" 310 lần gần như toàn bộ do cảnh tối tân thủ của #4.
- "Dừng" có tác dụng ngay (bản sửa lỗi ngủ 30 phút xác nhận trên máy thật).

## Bắt đầu đo A5: chế độ `smart` (10:25, 2026-11-19)
- Bật `schedule.mode = smart` trên web (tùy chọn chung, trả lại "Cố định" bất cứ lúc nào trên web).
- Phát hiện ngay: TK bật tân thủ luôn "có việc" → 4 máy (#2, #3, #4, #6) bị ghé mỗi 10 phút, kể cả #4 đang kẹt. Sửa: chu kỳ `schedule.tutorial_every_min: 30`.
- Sửa thêm: TK không đọc được số đội (bản đồ thế giới chưa mở: #2, #4) bị coi là "có việc" mỗi 10 phút → chờ theo `gather_retry_min`.
- **[ĐO] 10:42–11:40 #4:** bước tân thủ chạy **54 phút**, lặp "trận lái quân 15 s" liên tục rồi máy treo chụp màn hình → bỏ lượt (bản sửa "2 bước mù" hoạt động). Watchdog không bắt vì khung hình trong trận vẫn đổi, giới hạn bước tân thủ 120′. Ở `smart`, tân thủ #2/#4 tự vào backoff. **Lỗi tân thủ ghi cho Pha 1.**
- Hệ quả runner tuần tự: trong 58 phút đó #0, #3 trễ hạn ~50 phút.

### A5 — mốc đo 48 giờ (chủ dự án chốt 2026-11-19)
- Chủ dự án chọn **giữ smart 48 giờ**.
- Lượt smart đầu (11:41) bị ngắt lúc 13:16, vì ứng dụng đóng làm web tắt theo. Máy nghỉ 13:16–20:07 nên không tính vào A5.
- **Bắt đầu đo lại: 2026-11-19 20:07**, kết thúc khoảng 2026-11-21 20:07.
- So sánh: `python tools/baseline.py --mode smart --since 48` với `--mode fixed`.
- Lưu ý: web chạy qua preview của ứng dụng Claude, nên đóng ứng dụng sẽ dừng bot. Nếu muốn đo liền mạch thì chạy `run.bat` riêng.

### Sửa lỗi #4 (2026-11-19 tối)
| Triệu chứng | Nguyên nhân | Sửa | Kiểm chứng |
|---|---|---|---|
| Tân thủ chạm (157,914) 40 lần → đạt giới hạn bước; sau đó `goto(city)` kẹt màn panel (#4 13:15, #2 12:54) | Màn nâng cấp Xưởng kiến trúc có lớp phủ hướng dẫn, chữ V chỉ nút **"Tăng cấp"**; luật 5a luôn ưu tiên nút "Miễn phí" nhưng nút này bị khóa dưới lớp phủ | `decide()` 5a: nếu chữ V ở hàng nút dưới chỉ nút khác (lệch > 80 px) → theo V | `check_tutorial.py` 18/18 (thêm 2 ca `hq_upgrade_locked_free_i4/i2`); máy thật 20:26: chạm V (378,918) → tân thủ đi tiếp ~50 bước |
| Trận đánh mục tiêu "Thất bại nặng nề" thua 5 lần liên tiếp, lần ghé sau lại đánh tiếp (vòng lặp như 54 phút trước đó) | Lực chiến không đủ, đánh lại vô ích | Thua `max_retry` lần → ghi `tutorial_need_power` = lực chiến × 1,05 và `tutorial_wait_until` (+6 h); lần sau `tutorial.run` trả `weak_wait` nếu chưa đủ; lịch không coi tân thủ là trigger trong thời gian này | Máy thật 20:51: "tạm dừng, đánh lại khi lực chiến ≥ 74920"; lịch #4 không còn lý do `tutorial` |
| #4 được ghé mỗi giờ vì "chưa biết số đội hành quân" | Tài khoản tân thủ chưa mở bản đồ thế giới | Lịch: tài khoản đang tân thủ → `gather` không kéo máy | Lịch #4: ghé 22:54 (chu kỳ xây) thay vì 21:54 |

Cấu hình mới: `tutorial.power_gain_pct` (5), `tutorial.weak_retry_h` (6).
| Bàn tay xanh chỉ thùng tiếp tế nhưng bot không chạm (ảnh chủ dự án gửi 2026-11-19 21:00) | Bàn tay nhấp nháy, mẫu `hand_green` chỉ khớp 0,79 < 0,85 | Thêm mẫu `tutorial/hand_green2` (cắt từ ảnh gửi), ngưỡng 0,85; quét ~4.700 khung cũ: mọi khớp ≥ 0,80 đều là bàn tay thật | `check_tutorial.py` 19/19 (ca `hand_supply_box`: chạm giữa thùng) |
