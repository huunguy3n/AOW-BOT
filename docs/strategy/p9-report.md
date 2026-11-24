# Báo cáo P9 — sửa lỗi sau live-run-2 trên #1 (2026-11-24)

Nhánh `p7-live-fixes`, nối tiếp P8 (`d196618`). **Chưa push.** Không chạy bot thật, không bật LDPlayer / ADB / giả lập, không `pm clear` / gỡ app, không sửa `data/settings.json`.

Lượt làm bị cắt một lần vì hết hạn mức (sau P9-7). Lượt tiếp theo kiểm lại nhánh, `git log d196618..HEAD` và `git status`. Phần P9-8 đang làm dở (`notify.py` đã sửa, `hero_up.py` và test chưa commit) được giữ nguyên, hoàn tất rồi commit. Trong lúc đó sửa 1 test viết dở và 1 test cũ (`test_priority_queues`) bị vỡ vì có bước `_hero_exp` mới.

Kiểm tra trước mỗi commit: `python -m pytest` (toàn bộ), `python -m ruff check .`, `python -m ruff check bot web tools main.py --select E9,F63,F7,F82`, `python -m mypy`, `python main.py --check`, `trail check`. Lần chạy cuối thêm `lint-imports`.
Kết quả lần cuối: **1255 test pass, 0 fail** (P8 kết thúc ở 1144 → P9 thêm **111 test**, cả 111 đều pass trên máy này). Ruff sạch, mypy sạch (72 file), `lint-imports` giữ 8/8 hợp đồng, `--check` exit 0 (còn thiếu 17/250 ảnh mẫu, đều có từ trước P9), `trail check` không xung đột.

## Tổng quan

| Mục | Trạng thái | Commit | Test |
|---|---|---|---|
| P9-1 Máy treo + tạm dừng khi chủ chạm tay | XONG (offline) | 11f2b6c | 12 |
| P9-2 Khiên sớm + thứ tự bước | XONG (offline) | 084dd3a | 13 |
| P9-3 Nhận HẾT chấm đỏ / quà | PHẦN LỚN XONG — tab "Quà đặc biệt" và Rương Lv.17 làm theo mô tả vì không có ảnh | a941970 | 14 |
| P9-4 Sứ mệnh | XONG (offline) | dd12c7a | 11 |
| P9-5 Cướp xe: đúng popup + nút "Cướp bóc" | XONG (offline) | 76668c3 | 5 |
| P9-6 Xe khai thác của tôi | PHẦN LỚN XONG — tìm nút popup xe theo chữ, chưa có ảnh ADB | e525cbe | 12 |
| P9-7 Tập kết phản quân: bước cuối + ô Cấp | XONG (offline) | 6fcb92c | 9 |
| P9-8 Tăng cấp tướng | XONG (offline; nút tìm theo chữ trên ảnh điện thoại) | 231986b | 8 |
| P9-9 Tình báo từ bản đồ / 2 hộp / nhà chính đa skin / OCR nhiệm vụ | XONG (offline) | 158dca5 | 19 |
| P9-10 Trận chạy đường: né con lăn + nhặt buff | XONG (offline) | 57b4251 | 9 |

**Hoàn thành tổng: khoảng 85 %.** Mã + test xong cho cả 10 mục. Phần chưa xong là kiểm chứng trên máy thật (chưa phase nào chạy live) và 3 chỗ phải làm theo mô tả hoặc theo chữ vì thiếu ảnh ADB 540×960 (P9-3, P9-6, P9-8).

## Chi tiết

### P9-1 Máy treo + tạm dừng khi chủ chạm tay (11f2b6c) — XONG
- Rút timeout screencap từ 8/30/15 s xuống **5/15/10 s** (`bot.hang`). Máy treo bị phát hiện trong khoảng ≤ 30 s, không còn treo hàng phút.
- Khi gặp `Device.dead` hoặc 2 bước liền "mù" (không chụp được màn): gọi `ldconsole list2`. Máy không chạy → `launch`. Máy đang chạy mà treo → `quit` + `launch`. Sau đó chờ ADB, `runapp`, đóng popup, rồi **chạy tiếp từ bước KẾ TIẾP**, không bỏ cả lượt. Không có `pm clear`, không gỡ app, không xóa dữ liệu. Mỗi lượt chỉ cứu 1 lần (`ldplayer.recover_max`); hết lượt cứu thì bỏ máy như cũ.
- `HumanPause`: phát hiện ≥ 3 lần chạm tay của người trong 20 s (đã lọc chạm của bot) → `ctx.tap` và runner dừng trước mỗi bước, chờ tay yên 30 s (tối đa 10 phút), log `TAM DUNG`. Ngưỡng nằm trong `config.yaml` → `human_pause`.

### P9-2 Khiên sớm + thứ tự bước (084dd3a) — XONG
- Bước mới `shield` (`bot/modules/shield.py`). Ngày thường, nếu khiên đang TẮT: Hiệp ước hòa bình `row_8h` miễn phí trước (bỏ qua nếu đang có), rồi vật phẩm khiên khác, rồi kim cương trong trần 2000/ngày (nguồn `shield_daily`, ghi `gem_ev`). Hiệp ước đang chuẩn bị 1h thì không mua thêm. Thứ 7 vẫn do `warday` lo theo luật cũ (mọi loại khiên, không trần).
- `ORDER`: `warday, tutorial, shield, alliance` chạy TRƯỚC `notify / reddots / intel`. `gather` vẫn chạy cuối lượt (Thứ 2 gửi hết quân đoàn còn lại). Trên web, `MODULES` hiện đúng thứ tự chạy thật.
- `reddots.max_s` tăng 90 → 240 s cho khớp vòng nhận hết chấm đỏ (P9-3). Có test thứ tự bước.

### P9-3 Nhận HẾT chấm đỏ / quà (a941970) — PHẦN LỚN XONG
- `bot/claimloop`: `until_clear` / `tabs_until_clear` dừng khi hết chấm đỏ, hoặc khi 1 vòng không nhận thêm được gì (chống lặp vô hạn).
- Chiêu mộ: bấm hết chấm đỏ ở tab hiện tại rồi mới chuyển giữa thường và cao cấp, lặp tới hết.
- TT phúc lợi: bấm ô phát sáng TRƯỚC khi lướt (live2 s105738: lướt trước làm ô ngày 2 trôi khỏi màn). Quà đăng nhập chỉ bấm cột **Miễn phí** (`epic_header` nhận ra cột Sử thi theo màu; bỏ banner và gói ₫25000). Điểm Danh 30 Ngày: bấm ô hào quang, không lướt.
- Hub Hoạt động vào lại tab con còn chấm đỏ nếu lần trước nhận được (tối đa 3 lần); `event_tiles`.
- Quà liên minh: Rương Lv.N có chấm đỏ thì nhận; tab "Quà đặc biệt" bấm "Nhận" từng món. **Không có ảnh** tab này và Rương Lv.17 nên làm theo mô tả, không bịa ảnh mẫu.
- Nút "Quà" ($) lặp tới hết chấm đỏ. Thanh "Có thể nhận Rương mỗi ngày" → `quest_rules` loại `chest` → `mainquest.daily_chest` (chỉ nút Nhận an toàn và chấm đỏ VIP).
- **Còn thiếu:** kiểm thật tab Quà đặc biệt / Rương Lv.17 trên máy, và cắt ảnh mẫu khi có ảnh ADB.

### P9-4 Sứ mệnh (dd12c7a) — XONG
- Nguyên nhân bị chiếm màn (live2 11:03:07): sau khi chủ mở Sứ mệnh, `_follow_guide` tưởng ô "+" xanh là bàn tay hướng dẫn nên chạm (211,401) và (163,589)/(61,772), ngay cạnh gói ₫125000. Thêm `tutorial.NO_FOLLOW` (`mission/title`, `mission/shop_title`) chặn cả `guide_visible` lẫn vòng follow.
- Rương mốc 10/30/50/80/120: đọc điểm (55), chỉ bấm mốc ≤ điểm và rương đang phát sáng. Rương đã nhận không còn làm vòng dừng (trước P9 bot dừng ở rương đầu). Logic này dùng chung cho `daily` và tab Nhiệm vụ hằng ngày của Sứ mệnh.
- Săn kho báu: icon xe đẩy có chấm đỏ → Cửa hàng xúc xắc → **chỉ** nút "Miễn phí" có chấm đỏ (`free_with_dot`). Không chơi bàn xúc xắc, không Thẻ thông hành, không gói ₫.
- Ảnh mẫu mới: `mission/cart` (`p8-adb/mis1.png` 486,296,516,326), `mission/shop_title` (`live2/auto/s110328.png` 110,12,330,44).

### P9-5 Cướp xe: đúng popup + nút "Cướp bóc" (76668c3) — XONG
- Sau "Tới cướp bóc", chờ popup bản đồ và xác nhận bằng `world_popup_kind`: độ hiếm SR/SSR theo màu header (`world_rarity`), nút "Cướp bóc" **bên phải** tìm theo chữ (`loot_button`; ảnh `btn_loot` chỉ được chấp nhận khi x ≥ 300 nên không bao giờ trúng "Xem"), và không có thông báo đổi server.
- Live2 s110411 (xe N, có thông báo "Đã chuyển đổi sang sv…", chỉ thấy nút Xem) → trả `server_change`, lưu ảnh, đóng popup, nhớ xe đã bỏ, chọn xe khác.
- Vẫn giữ các luật cũ: so lực chiến sau "Đội hình đề xuất", chỉ xe SR/SSR có pha lê, không đánh xe đang cháy, đọc bộ đếm X/4.

### P9-6 Xe khai thác của tôi (e525cbe) — PHẦN LỚN XONG
- `bot/modules/mine_trucks.py`, gọi từ `play.mine` trước bước cướp xe: tab "Xe khai thác của tôi" → đọc "Số lần khai thác còn lại X/4" (0 → dừng) → bấm dấu "+" xanh.
- Làm mới (vòng vàng) **chỉ** khi có chữ "Miễn phí" hoặc còn lượt. Đọc ra "1/0" = hết lượt; không đọc được thì không bấm.
- Xe SR/SSR có tinh thể → nút bắt tay → tab "Đội quân hỗ trợ liên minh" → lướt danh sách → chỉ "Mời xuất phát" người > 400M. Không có ai > 400M thì để xe trống, **không** xuất phát.
- Xe thường → bánh răng → Đội hình đề xuất → Lưu → Xuất phát. Hộp "Chú ý": **chỉ** bấm "Xác nhận", không bao giờ chạm ô tick "Hôm nay không hiển thị lại". Thành công = X/4 giảm.
- **Còn thiếu:** chưa có ảnh ADB 540×960 của popup xe. Mọi nút đang tìm theo chữ, tọa độ suy từ ảnh điện thoại của chủ, nên cần chạy thử trên máy.

### P9-7 Tập kết phản quân (6fcb92c) — XONG
- Ô "Cấp" bị đọc trống (live2: gõ 10/9/8 đều ra `None`) là do ảnh chữ số `gather/lv/1..9` chỉ nhận được 1 chữ số trong ô 30 px. Đã chuyển sang OCR ô rộng hơn, canh theo nút "-" (s110928 = 20, s110937 = 30).
- `type_level` chạm đúng Ô "Cấp". Trước P9 bot chạm vào giữa nút - và + — đó là **thanh trượt**, nên làm đổi cấp. Gõ xong mà đọc lại trống thì giữ số đã gõ; nếu đọc ra số khác thì dùng +/-.
- Màn "Cài đặt Quân đoàn": bấm "Đội hình đề xuất" rồi mới dự đoán thắng và bấm "Xuất chinh". Nhận ra trạng thái "Đang tập kết" trên khung Hành quân (ghi log).
- Giữ 3Phút + "Đủ thành viên sẽ xuất phát" + Xác nhận. Nhà chính < 15 không tham gia tập kết cơ giáp.

### P9-8 Tăng cấp tướng (231986b) — XONG
- Danh sách Tướng: ngoài chấm đỏ, bot còn nhận thẻ có **mũi tên xanh lớn** (`hero_up.big_arrows`, 15–24 px ở góc phải dưới thẻ). Mũi tên nhỏ cạnh quyển sách là "Câu chuyện" nên bị bỏ qua.
- Chi tiết tướng: nút "Tăng cấp" không có chấm đỏ mà số EXP màu đỏ (thiếu EXP, `tuong_3`) → mở ô EXP → bảng "EXP Tướng" → "Dùng" 1 lần cho hiện "Dùng tất cả" → "Dùng tất cả" từng hàng → đóng → Tăng cấp lại. Lặp tới hết (`hero_detail` gọi `_hero_exp` khi một vòng không nhận được gì).
- **Không bao giờ** bấm từ dòng "Dùng đạo cụ" (kim cương) trở xuống: OCR tìm dòng đó (`dao_cu_y`). Nút có số hoặc chữ nguy hiểm cũng bị loại (`plan_exp_taps`, hàm thuần).
- Ảnh `tuong_1..5` là ảnh điện thoại nên nút tìm theo chữ, không cắt ảnh mẫu.

### P9-9 Tình báo / 2 hộp / nhà chính đa skin / OCR nhiệm vụ (158dca5) — XONG
- **Tình báo từ bản đồ thế giới:** `campaign/btn_open` khớp 0,95–0,97 trên bản đồ (s110646, `tinh_bao_tu_world_map`). `notify.open_intel` bấm ngay từ màn hiện tại, chỉ về thành phố khi không thấy icon. `intel.run` không còn ép về thành phố trước khi vào (cuối bước vẫn về thành phố theo quy ước).
- **3 hộp liên tiếp 11:06:57–11:07:05:** đó là 3 lần **nhận thưởng ghim đã xong** (tick xanh, khung s110655 "Chúc mừng nhận được"), không phải 3 đơn vị nhặt hộp cùng lúc → **không vi phạm** luật tối đa 2 hộp. Nhưng khi đọc code tìm ra lỗi tiềm ẩn: mọi tick (kể cả tick của trận thắng) đều gọi `Pickups.done()` và giải phóng 1 chỗ của hộp còn đang nhặt, nên có thể gửi hộp thứ 3. Đã sửa: `Pickups` nhớ vị trí ghim, `done(pos)` chỉ giải phóng khi tick nằm đúng ghim hộp đó. Có test chặn.
- **Nhà chính đa skin:** giữ `hq_emblem_a/b`, thêm `build/hq_emblem_halloween` (sân tròn tím; bí ngô có hoạt ảnh nên không cắt phần đó), kèm `TAP_DY` để chạm vào thân nhà. Không khớp skin nào → chạm vị trí giữa màn `HQ_TAP` và kiểm nhãn "Xưởng kiến trúc" (không phụ thuộc skin). Luật nhà chính < 15 không tham gia tập kết cơ giáp dựa vào fact `hq_level`, không dựa vào skin.
- **OCR thanh nhiệm vụ chính:** thanh trong suốt nên nền thành phố bên phải chữ bị đọc thành rác. `text_extent` chỉ OCR phần có chữ, `clean_text` bỏ token rác ở đầu và cuối. Live2: `'} C6 thé nhan Ruong moi ngay : 8. S. N | P Cothénhan…'` → `'Co thé nhan Ruong moi ngay | …'` (loại `chest`). So trên 261 khung: 237 giữ nguyên loại, **15 từ unknown thành nhận được**, 9 ngược lại. Cả 9 khung đó không có thanh nhiệm vụ (bảng Quà liên minh / bảng tăng tốc đè lên), nên đọc cũ ra "loại" cũng chỉ là trùng hợp.

### P9-10 Trận chạy đường / chiến dịch: né + nhặt buff (57b4251) — XONG
- Ảnh chủ `runner_ne_vat_can` có con lăn gai bị lửa che: `detect()` cũ chỉ thấy cột lửa (`danger`), không thấy vật cản (`block`).
- Thêm ảnh mẫu `steer/block_roller` (khung 540×960 của bot) và `steer/block_roller_fire` (ảnh của chủ, nửa trái không bị lửa che). `template_blocks` / `merge_blocks` dùng ngưỡng 0,62, đưa kết quả vào `det['block']` (trừ điểm −2,5 = né mạnh nhất). `_run_battle` dò ở mọi khung. Trên 8817 khung `logs/steer`: mọi khớp ≥ 0,62 đều là con lăn thật (đã kiểm bằng mắt), nền p99 ≈ 0,59.
- Buff "+N" trên mũi tên xanh lá nhạt giờ được nhận là buff.
- Cổng đỏ giữ luật P7-8: lật kịp thì lao vào, không thì né.
- Test: trên ảnh của chủ, đội quân ở làn con lăn chuyển ra ngoài thân con lăn (không đứng im); mô phỏng né 2 phía; nhặt buff đứng cạnh con lăn; luật cổng.

## Ảnh mẫu

**Đã thêm (P9):**
| Ảnh | Nguồn |
|---|---|
| `mission/cart.png` | `p8-adb/mis1.png` 486,296,516,326 (ADB) |
| `mission/shop_title.png` | `live2/auto/s110328.png` 110,12,330,44 (ADB) |
| `build/hq_emblem_halloween.png` | `live2/00-before.png` 200,420,340,490 (ADB) |
| `steer/block_roller.png` | `logs/steer/1795203553_024.jpg` 17,415,150,492 (khung 540×960 của bot) |
| `steer/block_roller_fire.png` | `live2-feedback/runner_ne_vat_can.png` (ảnh điện thoại 541×956 → 540×960) 142,388,235,465 — không có khung ADB nào có con lăn bị lửa che |

**Vẫn thiếu (ảnh cho P9, làm theo chữ / mô tả thay thế):** tab "Quà đặc biệt" và Rương Lv.17 (P9-3); popup xe khai thác, bảng Hỗ trợ liên minh, hộp "Chú ý" bản 540×960 (P9-6); bảng "EXP Tướng" bản 540×960 (P9-8).
**`--check` còn thiếu 17 ảnh, đều có từ trước P9:** `ally/btn_help_all`, `common/btn_help`, `common/btn_reward_close`, `common/msg_insufficient`, `defense/alert_attack`, `gather/mine_occupied`, `gather/msg_march_full`, `gather/msg_no_troops`, `hero/btn_exchange`, `play/res_loot_win`, `rebels/chk_3min_off`, `rebels/chk_full_start_off`, `rebels/rally_mech`, `research/btn_research_building`, `research/btn_research_enter`, `research/msg_no_res`, `rewards/city/claim_1`.

## Khoảng trống còn lại
1. **Chưa chạy thật:** chưa phase nào được kiểm trên #1. Nên chạy 1 lượt đầy đủ + 1 lượt kiểm lại (theo cách thử đã thống nhất), xem `logs/` và `logs/inv/` (`steer_no_battle`, `intel_*`, `upgrade_*`).
2. Nút trong popup xe khai thác (P9-6) và bảng EXP Tướng (P9-8) tìm theo chữ; tọa độ suy từ ảnh điện thoại. Cần ảnh ADB để cắt ảnh mẫu.
3. Tab Quà đặc biệt / Rương Lv.17 chưa có ảnh (P9-3).
4. Con lăn gai mới có 2 ảnh mẫu. Vật cản kiểu khác (nếu có) vẫn chỉ dựa vào nhận diện theo màu cũ (hàng rào gai, vòng bom, vệt xe lao).
5. Ngưỡng khớp skin Halloween (0,68) cách nền gần nhất 0,66, khá sát. Đã có lưới an toàn là kiểm nhãn "Xưởng kiến trúc" trước khi nâng cấp.
6. P9-1 cứu máy treo mới thử bằng mô phỏng `ldconsole` / ADB, chưa thử trên máy treo thật.

## Việc cần chủ dự án quyết định
1. **Tham gia tập kết Cơ giáp liên minh** (`rebels.join_mech_rally`) vẫn TẮT mặc định và còn thiếu ảnh `rebels/rally_mech`. Có bật cho #1 không?
2. **Ngưỡng 400M** người hỗ trợ xe khai thác SR/SSR (P9-6) và **ngưỡng tạm dừng khi chạm tay** (P9-1: 3 lần / 20 s, chờ 30 s, tối đa 10 phút). Giữ nguyên hay chỉnh?
3. `reddots.max_s` 240 s (P9-2): lượt dài hơn khoảng 2,5 phút mỗi máy. Có chấp nhận được với khung đăng nhập hẹn giờ cho 7 máy không?
4. Có cho phép dùng ảnh điện thoại làm ảnh mẫu khi không có bản ADB không (đang dùng 1 lần: `steer/block_roller_fire`)? Nếu không, cần một khung ADB có con lăn bị lửa che.
5. Thời điểm chạy live-run-3 trên #1 để kiểm P9 (tối đa 2 máy cùng lúc).

## Commit P9
`11f2b6c` P9-1 · `084dd3a` P9-2 · `a941970` P9-3 · `dd12c7a` P9-4 · `76668c3` P9-5 · `e525cbe` P9-6 · `6fcb92c` P9-7 · `231986b` P9-8 · `158dca5` P9-9 · `57b4251` P9-10 (+ commit báo cáo này). Tổng: 52 file, +2898 / −145 dòng (tính đến P9-10).
