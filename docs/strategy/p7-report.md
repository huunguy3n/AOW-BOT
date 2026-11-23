# Báo cáo P7 — sửa lỗi sau lượt chạy thật #1 (2026-11-24)

Nhánh `p7-live-fixes` (tách từ `p6-agent-24h` @ 4dfeb28). **Chưa push.** Không chạy bot thật, không bật LDPlayer.
Nguồn: `logs/pm-live1.txt`, `logs/bot-20261124.log`, ảnh chủ dự án `data/pm-shots/owner-20261124/` (chỉ để hiểu giao diện).

Kiểm tra trước mỗi commit: `python -m pytest` (toàn bộ), `python -m ruff check .`, `python -m mypy`, `python main.py --check`.
Lần cuối: **1047 test pass**, ruff sạch, mypy sạch (72 file), `lint-imports` 8/8 hợp đồng, `tools/check_tutorial.py` 34/34.

## Tổng quan

| Mục | Trạng thái | Commit |
|---|---|---|
| P7-1 Thứ tự gather | XONG | 36dbc67 |
| P7-2 Liên minh mỗi lần đăng nhập | XONG (cần ảnh mẫu) | 22d6648 |
| P7-3 Thư & quà | XONG (cần ảnh mẫu) | e3d0c8b |
| P7-4 Tình báo | XONG (cần ảnh mẫu bình 10 điểm) | 60f9b67 |
| P7-5 Nhiệm vụ | XONG | 4cf15f6 |
| P7-6 Mỏ khoáng sản (cướp xe) | XONG (cần ảnh mẫu) | d6b0c8c |
| P7-7 Sự kiện "Sứ mệnh" | XONG (cần 5 ảnh mẫu, chưa cắt thì bỏ qua êm) | d4b477f, 00520f5 |
| P7-8 Minigame runner (cổng đỏ lật "+") | XONG (chưa kiểm trên trận thật) | f1a0dc4 |
| P7-9 Trận chiến dịch | XONG một phần (xem dưới) | e02ab3b |
| P7-10 Phản quân / tập kết / đấu trường | XONG (cần ảnh mẫu) | 03c78a5 |
| P7-11 Đăng nhập hẹn giờ | XONG | 63ac22d |
| P7-12 Khiên | XONG (kiểm lại + 1 sửa) | 55efc94 |

## Chi tiết từng mục

### P7-1 Thứ tự gather (36dbc67)
- Gather luôn chạy **cuối lượt** mọi ngày (`aowbot.domain.warday.gather_last`), xả việc (`drain`) chạy trước gather.
- Thứ 2: vẫn cuối lượt nhưng gửi **hết** quân đoàn còn lại (bỏ `gather_first` của P6).
- Mỏ cấp 1 `toobig`: không ghi `gather_top`; cấp bắt đầu nâng theo bảng dung tích + tải quân đoàn lớn nhất; `toobig` bỏ luôn các cấp thấp hơn vẫn quá tải.

### P7-2 Liên minh (22d6648)
- Liên minh → "Lãnh thổ" → "Tranh Đoạt Cứ Điểm" → "Nhận" mỗi lần đăng nhập (thiếu ảnh mẫu → bỏ qua êm).
- "Quà tặng liên minh" → tab "Quà thường" → "Nhận toàn bộ" lặp tới khi "Có thể nhận" = 0.
- Quyên góp "Liên minh vĩnh cửu": chỉ nút vàng "100" (nửa phải-nửa dưới), từ chối nút xanh dương kim cương "40" và vùng nút ngón cái.

### P7-3 Thư & quà (e3d0c8b)
- Thư: nhận ở tab **đầu tiên** trước, rồi các tab có chấm đỏ; mở lại tới khi icon thư hết số đỏ.
- Icon quà liên minh (số đỏ) lặp tới khi hết; reddots ưu tiên số đỏ có thể nhận, xóa huy hiệu chat để cuối.

### P7-4 Tình báo (60f9b67)
- Sau "Xuất chinh" / "Tiếp tế" **kiểm quân đoàn thật sự đi**: nút biến mất và (nếu đọc được) "Hành quân x/y" tăng. Không đi → bấm lại 1 lần → `not_departed` + ảnh `logs/inv/intel_not_departed/`.
- Hộp quà mọi màu: tối đa `notify.intel_pickup_max` = 2 hộp đang nhặt; đầy → chờ (≤ `intel_pickup_wait_max_s` 120 s), lâu hơn thì bỏ ghim (`pickup_busy`); tick xanh giải phóng chỗ sớm.
- Làm xong nhiệm vụ → quét lại bản đồ (`intel_rescans` 3 lần, chờ `intel_rescan_wait_s`) tới khi không còn điểm mới.
- Hết thể lực: "+" → "Thuốc Thể Lực" → nút "Dùng" **cùng hàng bình 10 điểm** (`intel/potion_10`); nút "Dùng" khớp trùng vị trí nút "Mua" (`intel/btn_buy_potion`) bị loại; **không bao giờ bấm "Mua"**. Chưa có ảnh bình 10 → dùng nút "Dùng" trên cùng như cũ.
- Live1 log không có lần "không di chuyển" nào được ghi (chỉ `win`/`picked`) → kiểm xuất phát là phòng ngừa theo mô tả của chủ dự án.

### P7-5 Nhiệm vụ (4cf15f6)
- **Nguyên nhân `quests` không chạy ở live1:** `data/settings.json` → `instances."1".modules.quests = false`. Runner bỏ bước tắt **im lặng** (P7-1 đã thêm log "Buoc dang tat"). Không sửa cài đặt của chủ dự án; thay vào đó bước tắt → **chỉ nhận thưởng** ở tab có chấm đỏ, không bấm "Đến" (`quests.claim_when_off: true`, `quest_rules.quests_mode`). Test tái hiện: `tests/legacy/test_p7_quests.py`.
- Bảng nhiệm vụ **không cuộn** nữa (`daily._claim_tab` bỏ swipe); `quests` vốn không cuộn.

### P7-6 Cướp xe (d6b0c8c)
- Đọc "Số lần cướp bóc còn lại X/4" (X = 0 → bỏ).
- **Không bao giờ đánh xe đang cháy** (dấu X đỏ nét mảnh, `play.is_burning`), kiểm cả lúc chọn và ngay trước khi bấm.
- Chỉ xe SR/SSR chở **pha lê xanh** (`loot.crystal_only`; ảnh `play/item_crystal`, chưa có → nhận theo màu xanh nhạt trong hàng vật phẩm popup).
- Chưa có xe hợp lệ → nút làm mới (`play/btn_refresh`, tối đa `loot.refresh_max` 3); bấm mà hiện hộp thoại lạ → đóng, không xác nhận, dừng.
- Kết quả "Thắng lợi" (`play/res_loot_win`) / "Thất bại" → "Đóng".

### P7-7 Sứ mệnh (d4b477f, 00520f5)
- Module mới `bot/modules/mission.py` (ngay sau `rewards`; `config.yaml modules.mission`, web `MODULES`).
- Chỉ tab "Nhiệm vụ hằng ngày" → nút "Nhận" xanh; "Quà kỳ diệu" → rương góc trên-trái nhận miễn phí **chỉ khi có chấm đỏ**.
- An toàn: mọi lần chạm qua `mission.tap_ok` (vùng cho phép theo màn) + lọc chữ trả phí (`₫`, 250000/500000/1250000, "Mua", "Thẻ thông hành", "Săn kho báu"). Reddots chuyển chấm đỏ icon Sứ mệnh sang module (khi đã có ảnh `mission/icon`).

### P7-8 Minigame runner (f1a0dc4)
- Cổng đỏ (bảng đỏ có số rộng ≥ 60 px): OCR số qua các khung (`GateTrack`, ≤ 2 cổng/khung) → tốc độ tăng do bắn; `flip_ok`: lật thành "+" kịp trước khi chạm đội quân (an toàn 80 %) → lao vào như buff; không → né (như cũ).
- **Chưa kiểm trên trận thật**: cần một trận chạy đường có `battle.debug_dir` để xem OCR số trên cổng (vùng chữ trắng giữa bảng).

### P7-9 Trận chiến dịch (e02ab3b)
- **Nguyên nhân thật** của trận thua live1: log `00:32:30 Khong xac nhan duoc dang trong tran - khong lai` → bot không đặt ngón tay → không né, không ăn buff (không chỉ do 79,7M < 83,1M).
- Sửa: chiến dịch dùng `steer.campaign_battle` (battle_hud ngưỡng 0,85, biến thể `campaign/battle_hud_*`, dấu hiệu trận chạy đường tân thủ) và chờ `battle.enter_wait_s` = 25 s; không xác nhận → lưu khung `logs/inv/steer_no_battle/` để cắt HUD. Ngón tay giữ bằng `sendevent` (không `input swipe`) như cũ.
- Buff bổ sung theo ảnh mẫu `templates/steer/buff_*` (tùy chọn).
- **Chưa xong hẳn:** chưa có khung trận chiến dịch #1 để xác nhận HUD — nếu lần chạy sau vẫn log "Khong xac nhan…", cắt `campaign/battle_hud_2.png` từ ảnh trong `logs/inv/steer_no_battle/`. Trận thanh xe tăng (không phải lính áo xanh) làm `squad_x` không thấy đội quân → bot dựa vào ước lượng vị trí ngón tay.

### P7-10 Phản quân / tập kết / đấu trường (03c78a5)
- Tìm Cơ giáp: chạm ô "Cấp" (giữa nút −/+) → `Device.type_digits` (chỉ chữ số) → đọc lại; sai → +/- như cũ (`rebels.type_level`).
- Bảng "Thời gian tập kết": tick "3Phút" + "Đủ thành viên sẽ xuất phát" (ảnh ô **chưa chọn**; đã chọn thì không chạm) → "Xác nhận" → "Xuất chinh".
- Nhà chính < `rebels.min_hq_level` (15) **không bao giờ** tham gia tập kết Cơ giáp, kể cả khi bật `join_mech_rally` (mặc định vẫn `false`).
- Đấu trường: chỉ đối thủ lực chiến **yếu hơn** (`arena.weaker_only`, màu đỏ không còn được miễn); không có → "Làm mới" (`play/btn_arena_refresh`, tối đa 3; chữ trên nút có số/kim cương → không bấm; hộp thoại lạ → đóng, dừng).

### P7-11 Đăng nhập hẹn giờ (63ac22d)
- Khung `warday.timed_login_windows_utc` = [[18,19],[8,9]] (01–02h, 15–16h VN). Lịch kéo mỗi máy lên trong khung (`plan_warday`), stepgate cho `warday` chạy, notify/rewards chạy kèm, fact `timed_login_at` để chỉ ghé 1 lần/khung.
- Lưu ý: 7 máy, tối đa 2 chạy cùng lúc, mỗi lượt ~19 phút → **1 giờ không đủ ghé hết 7 máy** (≈ 6 máy/giờ nếu chỉ làm việc ngắn). Xem "Việc cần quyết định".

### P7-12 Khiên (55efc94)
- Kiểm lại P6: thứ 7 dùng Hiệp ước hòa bình (`defense/row_8h`, miễn phí, chuẩn bị 1h, hồi 14h) **trước giờ G**, sau đó khiên tức thì (vật phẩm trước, hết thì mua) với `gem_cap: null` (không giới hạn); ngoài cửa sổ trần `defense.gem_cap_daily` 2000. Đúng.
- Thêm test mô phỏng 24h (ghé trễ 5 phút) → **không hở khiên**.
- Sửa: kim cương mua khiên ngày chiến tranh (`shield_war`) không còn ăn vào trần 2000/ngày thường (cửa sổ kéo sang 00:30 Chủ nhật); vẫn ghi `gem_ev` + `gems_spent_war`.

## Ảnh mẫu cần chủ dự án cắt (ADB 540×960)

Cắt bằng `python main.py --capture <idx>` rồi `python tools/snap.py cutmany SRC tên=x1,y1,x2,y2`. Tọa độ là **gợi ý** từ ảnh crop lệch vài px — kiểm lại trên ảnh ADB. Thiếu ảnh nào thì bước đó bỏ qua êm và log "thieu anh mau …".

| File | Màn hình | Vùng gợi ý (x1,y1,x2,y2) | Mô tả |
|---|---|---|---|
| `ally/tab_territory.png` | Liên minh | hàng tab trên | Tab "Lãnh thổ" (P7-2) |
| `ally/btn_contest.png` | Liên minh > Lãnh thổ | mục giữa | Mục "Tranh Đoạt Cứ Điểm" (P7-2) |
| `ally/btn_contest_claim.png` | Tranh Đoạt Cứ Điểm | nút dưới | Nút "Nhận" lợi nhuận (P7-2) |
| `ally/tech_vinh_cuu.png` | Khoa học liên minh | thẻ công nghệ | "Liên minh vĩnh cửu" (tùy chọn, P7-2) |
| `defense/alert_attack.png` | Thành phố khi bị đánh | cảnh báo | Biểu tượng/khung cảnh báo bị tấn công (P7-3) |
| `gather/msg_march_full.png` | Bản đồ | thông báo nổi giữa | "Hàng hành quân đã đầy" (P7-3) |
| `gather/msg_no_troops.png` | Bản đồ | thông báo nổi giữa | "Không đủ quân" (P7-3) |
| `intel/potion_10.png` | Bảng "Thuốc Thể Lực" | icon/chữ hàng bình 10 điểm (~40,y,140,y+60) | Xác định hàng bình 10 điểm (P7-4) |
| `intel/btn_buy_potion.png` | Bảng "Thuốc Thể Lực" | nút "Mua" bên phải (~400,y,530,y+45) | Chỉ để **loại trừ**, bot không bao giờ bấm (P7-4) |
| `play/btn_refresh.png` | Mỏ khoáng sản, tab xe người khác | ~465,180,515,228 | Nút làm mới mũi tên tròn (P7-6) |
| `play/item_crystal.png` | Popup xe (Tới cướp bóc) | ô vật phẩm đầu (~50,665,110,720) | Pha lê xanh, không gồm số (P7-6) |
| `play/res_loot_win.png` | Kết quả cướp | tiêu đề | Chữ "Thắng lợi" (P7-6) |
| `mission/icon.png` | Thành phố | ~488,280,536,330 | Icon "Sứ mệnh" cột phải, không gồm số đỏ (P7-7) |
| `mission/title.png` | Sứ mệnh | ~210,12,330,48 | Tiêu đề "Sứ mệnh" (P7-7) |
| `mission/tab_daily.png` | Sứ mệnh | ~360,195,520,232 | Tab "Nhiệm vụ hàng ngày" chưa chọn (P7-7) |
| `mission/gift_icon.png` | Sứ mệnh | ~150,80,230,160 | Icon hộp quà "Quà kỳ diệu" (P7-7) |
| `mission/free_chest.png` | Quà kỳ diệu | góc trên-trái trong 0,200,280,460 | Rương nhỏ có đồng hồ, không gồm chấm đỏ (P7-7) |
| `campaign/battle_hud_2.png` | Trong trận chiến dịch #1 | icon cố định HUD (vd ~10,30,75,95) | Chỉ khi vẫn log "Khong xac nhan duoc dang trong tran"; lấy từ `logs/inv/steer_no_battle/` (P7-9) |
| `steer/buff_soldiers.png`, `steer/buff_ammo.png` | Trong trận chạy đường | ~70×60 | Tùy chọn: icon buff lính "+N" / đạn "+%" (P7-9) |
| `rebels/chk_3min_off.png` | Bảng "Thời gian tập kết" | ô tick cạnh "3Phút" | Trạng thái **chưa chọn** (P7-10) |
| `rebels/chk_full_start_off.png` | Bảng "Thời gian tập kết" | ô tick "Đủ thành viên sẽ xuất phát" | Trạng thái **chưa chọn** (P7-10) |
| `play/btn_arena_refresh.png` | Đấu trường | nút "Làm mới" | Kiểm xem nút có số/kim cương không (P7-10) |
| `rebels/rally_mech.png` | Liên minh > Sự vụ | dòng tập kết | Chỉ cần nếu bật `join_mech_rally` |

Còn thiếu từ trước P7 (không đổi): `ally/btn_help_all`, `common/btn_help`, `common/btn_reward_close`, `common/msg_insufficient`, `gather/mine_occupied`, `hero/btn_exchange`, `research/btn_research_building`, `research/btn_research_enter`, `research/msg_no_res`, `rewards/city/claim_1`. Hướng dẫn chi tiết: `templates/mission/README.md`, `templates/steer/README.md`.

## Việc cần chủ dự án quyết định

1. **Bước `quests` trên #1**: hiện tắt trong cài đặt máy. Bot nay vẫn **chỉ nhận thưởng** khi tắt. Muốn #1 bấm "Đến" theo nhiệm vụ thì bật lại trên web; muốn tắt hẳn cả việc nhận thì đặt `quests.claim_when_off: false`.
2. **Hiệp ước hòa bình giữa ngày chiến tranh**: chủ dự án ghi "mọi loại khiên kể cả Hiệp ước". Bot dùng Hiệp ước **trước giờ G**; giữa ngày vẫn chưa dùng vì cần 1h chuẩn bị và chưa rõ game có thay khiên đang chạy không (quyết định P6). Nếu xác nhận dùng Hiệp ước khi khiên tức thì còn > 1h **không** làm mất khiên đó → có thể thêm (tiết kiệm kim cương).
3. **Đăng nhập hẹn giờ với 7 máy**: khung 1 giờ, tối đa 2 máy cùng lúc → khó ghé đủ 7 máy. Chọn: (a) giữ nguyên, máy không kịp thì bỏ khung đó; (b) trong khung chỉ làm lượt ngắn (warday + notify + rewards rồi tắt); (c) ưu tiên một số máy.
4. **Nút "Làm mới"** (đấu trường, mỏ khoáng sản): bot chỉ bấm khi chữ trên nút không có số/kim cương. Nếu nút làm mới miễn phí nhưng có hiện số lượt (vd "1/3"), cần nói để nới luật.
5. **Đấu trường "chỉ yếu hơn"** thay luật cũ "ưu tiên lực chiến màu đỏ" — muốn khôi phục ưu tiên đỏ thì đặt `arena.weaker_only: false`.
6. **Cướp xe chỉ pha lê**: khi chưa có ảnh `play/item_crystal` bot nhận pha lê theo màu (có thể bỏ sót). Muốn tạm cướp mọi xe SR/SSR thì đặt `loot.crystal_only: false`.

## Lần chạy kiểm chứng đề xuất (theo `aow-test-one-pass-recheck`)
1 lượt cố định trên #1 sau khi cắt ảnh mẫu, rồi 1 lượt kiểm lại; đọc log các dòng: "Buoc quests tat -> chi nhan", "Tinh bao: quan doan KHONG xuat phat", "Tinh bao: quet lai ban do", "Cuop boc: xe … dang chay", "Su menh:", "Khong xac nhan duoc dang trong tran", "Dang nhap hen gio", "KIM CUONG".
