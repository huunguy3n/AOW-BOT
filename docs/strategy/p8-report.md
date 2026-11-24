# Báo cáo P8 — nối ảnh mẫu ADB, cướp xe so lực chiến, đăng nhập hẹn giờ 7 máy, nhiệm vụ #1 (2026-11-24)

Nhánh `p7-live-fixes` (sau commit ảnh mẫu 9cc0c25 của PM). **Chưa push.** Không chạy bot thật, không bật LDPlayer, không sửa `data/settings.json`.

Kiểm tra trước mỗi commit: `python -m pytest` (toàn bộ), `python -m ruff check .`, `python -m ruff check bot web tools main.py --select E9,F63,F7,F82`, `python -m mypy`, `python main.py --check`, `lint-imports`.
Lần cuối: **1144 test pass** (P7 kết thúc ở 1047, P8 thêm 97 test), ruff sạch, mypy sạch (72 file), `lint-imports` 8/8 hợp đồng, `--check` exit 0.

## Tổng quan

| Mục | Trạng thái | Commit |
|---|---|---|
| P8-1 Nối ảnh mẫu mới | XONG (+ sửa 1 lỗi thật: chấm đỏ rương Quà kỳ diệu) | cac27fd |
| P8-2 Cướp xe: so lực chiến | XONG (chưa kiểm trên máy thật) | c5a2600 |
| P8-3 Đăng nhập hẹn giờ cho 7 máy | XONG (mô phỏng, chưa chạy thật) | b9b48d3 |
| P8-4 Bật lại nhiệm vụ #1 | XONG | ef9e3d8 |

## Chi tiết

### P8-1 Nối ảnh mẫu (cac27fd)
- Tên/đường dẫn 14 ảnh mẫu khớp với code P7, không phải đổi tên.
- `tests/legacy/test_p8_templates.py`: khớp ảnh trên chính ảnh ADB gốc `data/pm-shots/owner-20261124/p8-adb/` với **đúng ROI code đang dùng** (lệch ≤ 3 px): icon Sứ mệnh (p8_a), tab_daily + gift_icon (mis1), free_chest (mis2), tab_territory (ally1/ally2), btn_contest (ally2), btn_contest_claim (ally3), tech_vinh_cuu (ally5), potion_10 + btn_buy_potion (intel2), btn_refresh (mine2), item_crystal trong vùng popup (truck1), btn_arena_refresh (arena1). Có test âm: không khớp trên màn sai (vd `item_crystal` trên thẻ Lối chơi nằm ngoài vùng popup).
- An toàn: bảng Thuốc Thể Lực chọn đúng nút "Dùng" hàng 10 điểm (438,340), không bao giờ nút "Mua" (439,782). Gói ₫125000/₫250000 ở Quà kỳ diệu không được `claim_safe` nhận ở cả màn Săn kho báu lẫn màn Quà kỳ diệu.
- **Lỗi thật đã sửa:** chấm đỏ rương miễn phí Quà kỳ diệu trên ADB #1 có H ≈ 8, V 130–170, tối hơn chấm thông báo thường, nên `red_dots` (H ≤ 6, V ≥ 190) không thấy. Hậu quả: rương sẽ **không bao giờ** được nhận. Thêm `mission.chest_dot` (dò ô 65×50 px cạnh rương).
- Thêm tên hiển thị tiếng Việt cho 14 ảnh và nhóm "Sứ mệnh" (test cũ `test_perception_names` đã fail ngay sau commit 9cc0c25).
- Ảnh ADB nằm trong `data/` (gitignore) → các test này tự skip trên máy không có ảnh.

### P8-2 Cướp xe: so lực chiến (c5a2600)
- `play.guard_power` đọc lực chiến hộ vệ trong popup xe (vùng 155,634,120,24, đọc đúng 98565656 trên truck1). `play.own_power` đọc lực chiến đội hình ta trên màn "Chiến đấu" (vùng 68,360; dự phòng quét dải 60–280 × 330–470), đọc đúng 220020045 trên fixture `loot_legion_i1`.
- Đổi thứ tự: bấm **"Đội hình đề xuất" trước**, rồi mới đọc lực chiến ta (đội hình đề xuất làm lực chiến thay đổi; trước P8 bot đọc trước khi bấm).
- `play.power_check(guard, ours, margin)`: chỉ đánh khi đọc được cả hai số, hộ vệ < ta và ta ≥ hộ vệ × (1 + `loot.power_margin`, mặc định 0.0). Không đạt → **không bấm Chiến đấu**, `back_out`, log `Cuop boc: ho ve X > ta Y -> bo`, nhớ xe đã bỏ 12h (`loot_mem.skip`), quay lại Mỏ khoáng sản thử xe khác (`loot.max_attempts` 2). Không đọc được lực chiến ta → bỏ xe và lưu ảnh `loot_own_power`.
- Lọc sớm trong popup bằng lực chiến ta lần trước (đỡ phải mở màn đội hình cho xe chắc chắn thua).
- Luật cũ vẫn giữ: chỉ SR/SSR, pha lê xanh, không đánh xe đang cháy, X/4 = 0 thì bỏ.
- Test: 243560931 vs 222749681 → bỏ, 98565656 vs 222749681 → đánh, bỏ xe mạnh rồi đánh xe yếu ở lần thử 2, không đọc được số → bỏ.

### P8-3 Đăng nhập hẹn giờ cho 7 máy (b9b48d3)
- Luật thuần trong `aowbot.domain.warday`: `timed_login_pending` (máy chưa nhận trong khung, xếp theo idx), `timed_login_missed`, `simulate_waves` / `waves_fit`, `timed_login_yield`, `next_window_start`, `last_closed_window`.
- Runner (cả vòng `fixed` lẫn `smart`/`agent`): trong khung 18–19h / 8–9h UTC, máy chưa nhận được ưu tiên hơn mọi lượt khác (sau "Chạy ngay" của chủ dự án), bật máy **ngay đầu khung**, tối đa 2 máy cùng lúc. Lượt **ngắn** (`mode="timed"`):
  1. mở game → rương "Đăng nhập hẹn giờ" **đầu tiên** (`notify.timed_login_chest`: icon Hoạt động → chỉ các tab có chấm đỏ → thấy `event/timed_login` thì chạm rương). Còn trong `timed_login_delay_min` đầu khung thì chờ hết delay.
  2. `warday` (khiên ngày chiến tranh) → `notify` → `rewards` nếu còn trong `timed_login_visit_max_min` (12) phút, tính từ lúc bật máy.
  3. tắt máy, nhường luồng cho máy sau. Lượt ngắn không chạy ưu tiên ô rỗng, xả việc hay chế độ "chỉ nhận" của quests.
- Máy đang chạy lượt dài khi khung mở: nhận rương ở **bước kế tiếp**; nếu còn máy khác đang chờ luồng thì kết thúc lượt sớm, chỉ còn `observe` (`timed_login_yield`).
- Vòng `fixed` nghỉ 30 phút giữa hai vòng → nay thức dậy đúng đầu khung. Mỗi máy thử tối đa 2 lần/khung. Hết khung → log `Dang nhap hen gio: may X LO khung HH:MM UTC`.
- Test mô phỏng: 7 máy, 2 luồng, lượt 12 phút → cả 7 nhận trong khung (xong lúc 48 phút), không lúc nào quá 2 máy; 2 máy đang chạy lượt dài, nhường lúc 10 phút → vẫn đủ; lượt 19 phút → **không** đủ (giải thích vì sao cần lượt ngắn).

### P8-4 Nhiệm vụ #1 (ef9e3d8)
- Test đọc `data/settings.json` thật (chỉ đọc, kiểm cả mtime không đổi): `instances."1".modules.quests = true` → `quests_mode` = `full` (bấm "Đến"); stepgate cho `quests` chạy; lịch `smart` và `piggyback` đều xếp `quests` cho #1.
- Thêm nhóm nhiệm vụ **cấm** (`quest_rules.FORBIDDEN`): mua / nạp / kim cương / thanh toán / thẻ tháng / gói quà / đặc quyền, tấn công người chơi / căn cứ / thành, phá hủy, đánh bại chỉ huy. Không bao giờ bấm "Đến", kể cả trong `mainquest` (qua `delegated`). "Cướp bóc" giao cho bước `play` (có so lực chiến P8-2).
- Luồng quests đầy đủ đã kiểm: nhận dòng đã xong trên cùng trước (bảng không cuộn, giữ từ P7-5), rồi chỉ bấm "Đến" dòng xây an toàn; nâng cấp qua `build.upgrade_here` (không "Tăng cấp ngay").

## Ảnh mẫu

**Đã có (9cc0c25, kiểm ở P8-1):** `mission/icon`, `mission/title`, `mission/tab_daily`, `mission/gift_icon`, `mission/free_chest`, `ally/tab_territory`, `ally/btn_contest`, `ally/btn_contest_claim`, `ally/tech_vinh_cuu`, `intel/potion_10`, `intel/btn_buy_potion`, `play/btn_refresh`, `play/item_crystal`, `play/btn_arena_refresh`.

**Còn thiếu** (`python main.py --check`: 17/245):
- Từ P7: `play/res_loot_win` (chữ "Thắng lợi" sau khi cướp), `rebels/chk_3min_off`, `rebels/chk_full_start_off` (ô tick chưa chọn ở bảng "Thời gian tập kết"), `defense/alert_attack`, `gather/msg_march_full`, `gather/msg_no_troops`, `rebels/rally_mech` (chỉ cần khi bật `join_mech_rally`). Tùy chọn: `campaign/battle_hud_2`, `steer/buff_soldiers`, `steer/buff_ammo`.
- Từ trước P7: `ally/btn_help_all`, `common/btn_help`, `common/btn_reward_close`, `common/msg_insufficient`, `gather/mine_occupied`, `hero/btn_exchange`, `research/btn_research_building`, `research/btn_research_enter`, `research/msg_no_res`, `rewards/city/claim_1`.
- Nên có thêm cho P8-2: một ảnh ADB 540×960 **màn đội hình cướp xe sau "Đội hình đề xuất"** trên #1 để xác nhận vùng OCR lực chiến ta (hiện mới kiểm trên fixture `loot_legion_i1` chụp 2026-11-21).

Bảng ảnh mẫu trong `docs/strategy/p7-report.md` đã thêm cột "Trạng thái (P8)".

## Chưa xong / chưa kiểm
- Chưa chạy trên máy thật (theo quy tắc). Cần một lượt có kiểm tra lại trên #1 để xác nhận: OCR lực chiến ta trên màn đội hình, rương Quà kỳ diệu (`chest_dot`), rương "Đăng nhập hẹn giờ" qua `notify.timed_login_chest`.
- P8-3 chỉ kiểm bằng mô phỏng. Lượt ngắn thật có thể lâu hơn 12 phút nếu khởi động máy chậm (≈ 70 s bật máy + mở game); quá 12 phút thì bỏ các bước sau rương, nên rương vẫn nhận kịp. Thứ 7 bước `warday` có thể lâu hơn vì phải bật khiên.

## Việc cần chủ dự án quyết định
1. **`loot.power_margin`**: mặc định 0.0 (đánh khi ta > hộ vệ). Nếu muốn chắc thắng hơn (vd chênh lệch ±5 % do tướng / khắc chế) thì đặt 0.05–0.10.
2. **Nhường luồng trong khung hẹn giờ** (`warday.timed_login_yield: true`): máy đang chạy lượt dài sẽ dừng sớm (bỏ các bước còn lại của lượt đó) để máy khác kịp nhận rương. Nếu muốn ưu tiên lượt dài thì tắt, nhưng khi đó 7 máy có thể không kịp.
3. **Thứ tự máy trong khung**: hiện theo số máy (#0 → #6). Muốn #1 (tài khoản chính) luôn đi đầu thì nói để thêm thứ tự ưu tiên.
4. **Nhóm nhiệm vụ cấm**: khớp theo từ khóa đã bỏ dấu. Từ "mua" có thể trùng "mùa", nên một số nhiệm vụ mùa sẽ không được bấm "Đến" (an toàn nhưng có thể bỏ sót). Nếu thấy log `KHONG AN TOAN` ở nhiệm vụ hợp lệ thì gửi chữ nhiệm vụ để nới luật.
5. Còn mở từ P7: Hiệp ước hòa bình giữa ngày chiến tranh, nút "Làm mới" có số lượt (P7 mục 2, 4).

## Lần chạy kiểm chứng đề xuất
Một lượt cố định trên #1, rồi một lượt kiểm lại. Đọc log các dòng: `Cuop boc: ho ve`, `loot_own_power`, `Su menh: nhan ruong mien phi`, `Dang nhap hen gio`, `LO khung`, `KHONG AN TOAN`, `Nhiem vu chuong dong`, `Nhiem vu main dong`. Nếu chạy trong khung 01–02h hoặc 15–16h giờ VN thì xem log `Dang nhap hen gio: ghe may …` để biết thứ tự các máy.
