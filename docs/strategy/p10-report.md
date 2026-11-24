# Báo cáo P10 — sửa lỗi sau live-run-3 trên #1 (2026-11-24)

Nhánh `p7-live-fixes`, nối tiếp P9 (`26dde4b`). **Chưa push.** Không chạy bot thật, không bật LDPlayer / ADB / giả lập, không `pm clear` / gỡ app, không sửa `data/settings.json`.

Nguồn lỗi: `logs/pm-live3.txt`, `logs/pm-live3-report.txt`, khung ADB 540×960 `data/pm-shots/owner-20261124/live3/auto/s*.png`, ảnh bot tự lưu `logs/shots/20261124-15*-i1-*.png`.

Kiểm tra trước mỗi commit: `python -m pytest` (toàn bộ), `python -m ruff check .`, `python -m ruff check bot web tools main.py --select E9,F63,F7,F82`, `python -m mypy`, `python main.py --check`, `trail check`. Lần cuối thêm `lint-imports`.
Kết quả lần cuối: **1305 test pass, 0 fail** (P9 kết thúc ở 1255, P10 thêm **50 test**). Ruff sạch, mypy sạch (72 file), `lint-imports` giữ 8/8 hợp đồng, `--check` exit 0 (vẫn thiếu 17/250 ảnh mẫu, đều có từ trước P9), `trail check` không xung đột.

## Tổng quan

| Mục | Trạng thái | Commit | Test |
|---|---|---|---|
| P10-1 Cướp bóc: nhận popup theo nút "Cướp bóc" + so lực chiến | XONG (offline) | 6074a6f | 6 |
| P10-2 Chiêu mộ: nút "Miễn phí" + thứ tự tab | XONG (offline) | 5283ea6 | 5 |
| P10-3 Phản quân: ô Cấp + hạ cấp | XONG (offline), gõ số còn phải kiểm trên máy | e87eb1c | 12 |
| P10-4 Xe khai thác của tôi | XONG phần nguyên nhân live3; nút trong popup xe vẫn tìm theo chữ (như P9-6) | d404731 | 5 |
| P10-5 Chấm đỏ còn sót | XONG (offline) | 6949da6 | 8 |
| P10-6 Điểm danh / Quà đăng nhập | XONG (offline) | 29f20e5 | 7 |
| P10-7 Gia hạn khiên | XONG (offline); 1 chỗ lệch thứ tự so với yêu cầu, xem mục P10-7 | 2c1900b | 8 |

**Hoàn thành tổng: khoảng 85 %.** Cả 7 mục đã có mã và test, và mỗi lỗi đều tìm ra nguyên nhân trên ảnh/log thật. Phần còn thiếu là chạy thử trên máy (chưa có lượt live nào sau P10) và hai chỗ chỉ kiểm được trên máy: gõ số qua bàn phím ảo (P10-3) và popup xe khai thác bản ADB (P10-4).

## Chi tiết

### P10-1 Cướp bóc (6074a6f) — XONG
- **Nguyên nhân:** `world_popup_kind` coi có toast là `server_change`, kể cả khi popup có nút. Ảnh `logs/shots/20261124-153909-i1-loot_popup_server_change.png` là popup SSR đúng (Lực Chiến 108031985, nút "Cướp bóc" ở (347,574)), nhưng toast "Đã chuyển đổi sang sv ServerID #6" đè lên nên xe bị bỏ.
- **Sửa:** phân loại theo việc có nút "Cướp bóc" bên phải hay không (`loot_button`, tìm theo chữ, x ≥ 300 nên không bao giờ trúng "Xem"). Toast chỉ được tính khi **không có** nút. `world_popup` chụp lại liên tục tới hết thời gian chờ để toast kịp mờ. Live2 s110411 (xe N, chỉ có "Xem" + toast) vẫn bị coi là `server_change` và bị đóng.
- **So lực chiến:** log cũ ghi "CHON DUOC" vì bot chưa biết lực đội. `pre_check` mới: nếu đã biết lực đội hành quân (đọc ở màn đội hình lần trước) thì dùng `power_check`. Nếu chưa biết mà hộ tống ≥ **tổng** lực chiến tài khoản (108.031.985 ≥ 79.829.544) thì bỏ, vì lực đội luôn ≤ tổng lực. Còn lại ghi "CHON TAM" rồi kiểm lại bằng lực đội thật sau "Đội hình đề xuất", trước khi bấm Chiến đấu (giữ luật P8-2). OCR hỏng thì bỏ.
- Giữ các luật cũ: chỉ xe SR/SSR có pha lê, không đánh xe đang cháy, đọc X/4, làm mới theo luật, không bấm "Xem".

### P10-2 Chiêu mộ (5283ea6) — XONG
- **Nguyên nhân:** chạy thử `_recruit_once` trên chính ảnh `recruit_dot_left` thì bot bấm đúng "Miễn phí" (ảnh mẫu `recruit/btn_free` khớp 1.0). Vậy lỗi là ở **thứ tự tab**: màn mở sẵn tab thường, nhưng `tabs_until_clear` chuyển sang tab cao cấp trước rồi mới quay lại, và khi đó bộ chọn thẻ có thể chưa trượt xong. Có khoảng 30 ảnh `recruit_dot_left` trong `logs/shots` từ 21/11, đều khớp `btn_free` 1.0, tức là lỗi này đã có từ lâu.
- **Sửa:** thêm `claimloop.current_then_tabs`: nhận hết ở tab **hiện tại** trước, sau đó chỉ vào tab nào có chấm đỏ (`recruit_tab_dot`, chấm ở góc trên phải thẻ tab, +87,−84), lặp tới khi hết chấm đỏ hoặc không còn tiến triển. Chờ thẻ trượt yên tối đa 6 lần. Nếu ảnh mẫu không khớp thì tìm nút "Miễn phí" theo chữ (`FREE_BTN_ROI`). Không có nút kim cương nào được bấm.

### P10-3 Phản quân: ô Cấp (e87eb1c) — XONG (cần kiểm trên máy)
- **Nguyên nhân (khung s154328 / s154354):** ô vẫn còn "1" sau khi gõ 9/8. DEL gửi liên tiếp bị mất (từ "10" chỉ xóa được "0"), số gõ vào không ăn, và game nhận số qua nút **"OK"** của thanh nhập liệu chứ không qua Enter. Sau đó +/- bỏ cuộc ngay lần chạm đầu không đổi số (lần chạm đó chỉ đóng bàn phím). Dòng log "cap da thang cao nhat None" gây hiểu nhầm: thật ra ô Cấp không đổi nên tìm kiếm lại ra Lv.10, mà Lv.10 vừa bị dự đoán thua.
- **Sửa:** `type_digits` gửi MOVE_END rồi DEL ×4 từng phím có nghỉ, gõ số, không Enter. `type_level` bấm "OK" của thanh nhập liệu (`keyboard_bar`: nền trắng y 870–950, OK ở (511,910)) rồi OCR xác nhận. Sai thì `set_level` bấm +/- và đọc lại sau mỗi lần, cho phép 2 lần chạm hụt. Không đặt được cấp thì **không** bấm Tìm kiếm. Log ghi lý do thật (`target_why`). Hạ cấp không cần lịch sử thắng (`search_levels` khi `best=None`, Lv.10 vừa thua → [9, 8, 7]).
- Giữ nguyên: 3Phút + "Đủ thành viên sẽ xuất phát" + Xác nhận → "Đội hình đề xuất" → Xuất chinh; nhà chính < 15 không tập kết cơ giáp; thuốc thể lực chỉ "Dùng".
- **Chưa chắc:** `input text` có vào được ô nhập của game hay không. Lượt live3 chỉ cho thấy DEL bị mất, không cho thấy chữ bị mất. Nếu lần chạy tới vẫn đọc ra số khác, bot sẽ tự chuyển sang +/- có đọc lại.

### P10-4 Xe khai thác của tôi (d404731) — XONG phần lỗi live3
- **Nguyên nhân (khung s153857):** sau khi nhận rương, bảng "Chúc mừng nhận được" vẫn đè lên màn. `mine_trucks.run` không thấy `play/mine_title` nên trả 0 mà **không ghi log**: không mở tab, không đọc X/4.
- **Sửa:** `back_to_mine` đóng bảng quà và chờ tiêu đề (tối đa 4 lần). Vẫn không về được thì ghi log và lưu ảnh `mine_trucks_no_title`. Mỗi xe đều log "con X/4 luot, N xe trong" và kết quả "luot a/4 -> b/4", cuối bước log "dua di N xe". Có test bảo đảm `mine_trucks.run` được gọi sau rương và trước cướp xe.
- Luồng P9-6 giữ nguyên: làm mới chỉ khi Miễn phí hoặc còn lượt ("1/0" là hết); xe SR/SSR có tinh thể → Hỗ trợ, chọn người > 400M, không ai thì để trống; xe thường → Đội hình đề xuất → Lưu → Xuất phát; hộp "Chú ý" chỉ bấm "Xác nhận", không bao giờ chạm ô tick.
- **Còn thiếu:** live3 chưa có khung nào của popup xe trong tab "Xe khai thác của tôi", vì bot chưa từng vào được tab này. Các nút vẫn tìm theo chữ.

### P10-5 Chấm đỏ còn sót (6949da6) — XONG
- **Nguyên nhân:** chấm đỏ Tình báo ăn khoảng 4 phút (15:34 → 15:37:49) trong ngân sách 240 s. Sau đó các trận tình báo, đấu trường và thu thập lại sinh thư báo cáo **mới** khi bước reddots đã xong. Tab Quà đặc biệt bị bỏ 2 món (s153317 → s153326): bấm "Nhận" xong, chụp lại sau 1,2 s thấy màn chưa đổi (hiệu ứng nhận chậm) nên nút bị coi là chết.
- **Sửa:**
  - Chấm đỏ của tiến trình dài (intel / play / rally / campaign) mà bước riêng **còn chờ** trong lượt thì để bước riêng làm (`ctx.visit_pending`, `defer_to_step`).
  - Hết `max_s` thì các loại nhận quà (thư, quà liên minh, VIP, Quà, chiêu mộ, tướng) vẫn được thêm `claim_grace_s` = 90 s.
  - **Quét nhận quà cuối lượt** trước observe (`reddots.final_claims`): quà liên minh (Rương Lv.N, Quà đặc biệt, Quà thường) → thư ở mọi tab có chấm đỏ, kể cả Báo cáo → chiêu mộ.
  - Thư: "Đọc & nhận nhanh" chỉ tìm ở vùng phải dưới (không bao giờ bấm "Xóa tất cả đã đọc"), bấm lại tối đa 3 lần nếu dòng thư còn chấm đỏ (s153252).
  - Quà đặc biệt: màn chưa đổi thì chờ thêm 1 s; 2 lần bấm không đổi mới bỏ nút đó.
- Hộp quà ≈(437,815) số 12 chính là icon Quà tặng liên minh (`ally/icon_gift` khớp 0,91 trên s155258). Icon trợ lý robot (số 5) chưa xử lý: không có quy tắc nào và không có ảnh màn bên trong.

### P10-6 Điểm danh / Quà đăng nhập (29f20e5) — XONG
- **Nguyên nhân:** không phải lỗi lịch. TT phúc lợi chỉ được mở khi icon có chấm đỏ và chỉ vào tab có chấm đỏ. Hai mục này đã nhận ở live2 (10:56), nên live3 (15:30) không có gì để làm và cũng không ghi log.
- **Sửa:** `notify.run` gọi `welfare_daily` **mỗi lượt**. Lượt này vừa nhận được gì thì ghi đã nhận hôm nay. Đã nhận hoặc đã kiểm trong ngày (reset 0h UTC) thì log "da nhan hom nay" và bỏ qua nhanh. Chưa kiểm thì mở TT phúc lợi 1 lần trong ngày. Luật giữ nguyên: ô hào quang không lướt, chỉ cột Miễn phí, không cột Sử thi / gói ₫.

### P10-7 Gia hạn khiên (2c1900b) — XONG, 1 chỗ lệch yêu cầu
- `shield.plan` đọc thời gian còn lại của khiên. Khiên tắt hoặc còn < `shield.renew_below_min` (60) phút thì gia hạn. Còn ≥ 60 phút hoặc không đọc được giờ thì không bật chồng. Bước `shield` chạy **đầu** lượt như cũ, và chạy thêm **cuối** lượt (runner, trước observe).
- Thứ tự: Hiệp ước row_8h miễn phí → vật phẩm (`extend`) → kim cương trong trần 2000/ngày (nguồn `shield_daily`, ghi `gem_ev`, log kim cương trước/sau). Thứ 7 vẫn do `warday` lo như cũ.
- **Lệch so với yêu cầu:** khi **gia hạn** (khiên còn đang bật), Hiệp ước chỉ được dùng nếu khiên còn ≥ 60 phút. Lý do: Hiệp ước cần 1h chuẩn bị và không bảo hộ trong lúc đó, nên dùng khi khiên còn 0h35 sẽ để trống ~25 phút (cùng lý do learning 2026-11-23 bỏ Hiệp ước giữa ngày chiến tranh). Khi khiên **tắt** thì Hiệp ước vẫn được thử đầu tiên như P9-2.

## Ảnh mẫu
**Không thêm ảnh mẫu mới.** Các chỗ cần nhận diện đều đã có cách khác dùng được trên khung thật:
- nút "Miễn phí" chiêu mộ: ảnh mẫu cũ `recruit/btn_free` khớp 1.0 trên ảnh live3, có thêm dự phòng theo chữ;
- nút "Cướp bóc": tìm theo chữ (đã kiểm trên ảnh live3);
- thanh nhập liệu bàn phím ảo: nhận theo màu;
- ô Cấp: OCR (đọc đúng 1/10/5 trên s154328/s154337/s154411).

Test dùng trực tiếp các khung ADB 540×960 thật: `logs/shots/20261124-153909-i1-loot_popup_server_change.png`, `logs/shots/20261124-153117-i1-recruit_dot_left.png`, `live3/auto/s153252`, `s154328`, `s154337`, `s154354`, `s154411`, `live2/auto/s110411`.

**Vẫn thiếu** (như P9): ảnh ADB của popup xe khai thác, bảng Hỗ trợ liên minh, hộp "Chú ý", Rương Lv.17 khi có chấm đỏ. `--check` thiếu 17/250, danh sách y như báo cáo P9.

## Khoảng trống còn lại
1. Chưa chạy thật sau P10. Nên chạy 1 lượt đầy đủ + 1 lượt kiểm lại trên #1 và xem các dòng log mới: `O Cap: ... OK`, `Xe khai thac cua toi: con X/4`, `Nhan qua cuoi luot`, `Diem Danh 30 Ngay`, `Khien cuoi luot`, `CHON TAM`.
2. Gõ số vào ô Cấp (P10-3) chưa kiểm được offline. Nếu vẫn hụt, bot dùng +/- có đọc lại (chậm hơn nhưng đúng cấp).
3. Popup xe khai thác (P10-4) chưa có khung ADB.
4. Icon trợ lý robot (số 5) và các chấm đỏ "generic" khác vẫn chỉ được mở và nhận nút "Nhận" an toàn.
5. Bước reddots không còn tự làm tình báo / lối chơi khi bước riêng của chúng còn chờ trong lượt. Nếu chủ dự án tắt các bước đó trên một máy thì reddots vẫn tự làm như cũ (vì bước không nằm trong hàng chờ).

## Việc cần chủ dự án quyết định
1. **Hiệp ước khi gia hạn khiên** (P10-7): hiện chỉ dùng khi khiên còn ≥ 1h (để không bị hở lúc chuẩn bị). Muốn bắt buộc dùng Hiệp ước trước kể cả khi bị hở ~25 phút, hay nâng `shield.renew_below_min` lên 90 để Hiệp ước được dùng khi khiên còn 60–90 phút?
2. `reddots.claim_grace_s` = 90 s và quét nhận quà cuối lượt làm mỗi lượt dài thêm khoảng 1–2 phút. Có chấp nhận được với khung đăng nhập hẹn giờ cho 7 máy không? (Lượt ngắn `mode=timed` không chạy phần này.)
3. Thời điểm chạy live-run-4 trên #1 để kiểm P10.

## Commit P10
```
6074a6f P10-1 cuop boc: phan loai popup theo nut 'Cuop boc' + loc luc chien pre_check
5283ea6 P10-2 chieu mo: tab hien tai truoc, cham do tab, 'Mien phi' theo chu
e87eb1c P10-3 phan quan o Cap: xoa sach, OK ban phim, OCR xac nhan, +/- doc lai
d404731 P10-4 xe khai thac cua toi: dong bang qua truoc khi mo tab, log X/4
6949da6 P10-5 cham do con sot: de buoc rieng, grace nhan qua, quet cuoi luot
29f20e5 P10-6 Diem Danh / Qua dang nhap: kiem moi luot, log da nhan
2c1900b P10-7 gia han khien dau + cuoi luot (< 1h)
```
