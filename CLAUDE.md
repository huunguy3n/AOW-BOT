# CLAUDE.md — AOW-BOT

Bot farm tự động cho game **Age of Warpath: Global Warzone** chạy trên **LDPlayer 9** (nhiều instance), điều khiển qua ADB + nhận diện ảnh (OpenCV) + OCR (Tesseract). Kèm một dự án con: **Account Manager**, để gom nhiều tài khoản về 1 instance bằng snapshot/restore dữ liệu app.

Đọc thêm: [README.md](README.md) (hướng dẫn cài đặt/chạy), [docs/product/vision-roadmap.md](docs/product/vision-roadmap.md) (định hướng), [docs/adr/](docs/adr/README.md) (các quyết định kiến trúc).

---

## ⚠ Quy tắc an toàn — đọc trước khi làm bất cứ gì

1. **Tài khoản game là tài khoản khách cục bộ.** Dữ liệu app (`/data/user/0/<pkg>`, `shared_prefs/<pkg>.v2.playerprefs.xml`) **chính là** tài khoản. `pm clear`, gỡ app, restore sai, xóa slot = **mất tài khoản vĩnh viễn**. → [ADR-0010](docs/adr/0010-an-toan-tai-khoan-khach.md)
2. Không bao giờ chạy `pm clear` / `uninstall` / xóa slot / ghi đè dữ liệu app trên tài khoản thật nếu chưa có snapshot **đã verify, ≥2 bản sao trên 2 ổ đĩa** (E: và D:).
3. Không ghi dữ liệu app khi game đang chạy: `pm disable-user` → force-stop → kiểm tra tiến trình theo **uid** → ghi → verify SHA-256 → `pm enable`. Sai thì rollback.
4. **Tối đa 2 instance chạy cùng lúc** (`ldplayer.max_running`, kể cả máy bật tay để thử). Instance hiện có: **#0, #1, #2, #3, #4, #5, #6**. **#1 = TÀI KHOẢN CHÍNH** (bản VN, nhà chính cấp 30, đủ tính năng; thêm 2026-11-21): bot vẫn chạy auto như các farm, đồng thời là nơi thu thập màn/tính năng mà farm cấp thấp chưa mở; sau này là căn cứ nhận tài nguyên từ các farm (chưa làm). (#1 cũ, #7, #8 đã xóa 2026-11-17; `.ldbk` của #7/#8 còn trong `backups/`). Bot chạy bình thường trên các máy này; thử nghiệm Account Manager (ghi dữ liệu app, root) **chưa có instance thử** — phải thống nhất instance mới trước khi làm.
5. **Không log giá trị** `JOY_ACCOUNT_ID` / `JOY_ACCOUNT_PASSWORD` / `account_uuid`… — chỉ in hash ngắn. Slot chứa thông tin xác thực.
6. **Không tự tiêu kim cương / không đi đường trả phí.** Ngoại lệ duy nhất: khiên — khi bị tấn công (`defense.shield_buy_gems`, trần `defense.gem_cap_daily` 2000/ngày) và trong **ngày chiến tranh** (thứ 7, không giới hạn, chủ dự án 2026-11-23). Mọi lần mua ghi bảng `gem_ev`. → [ADR-0008](docs/adr/0008-chinh-sach-kim-cuong.md)
7. Không bypass license check, anti-cheat, hay sửa nội dung file game. Chỉ snapshot/restore nguyên trạng.
8. **Làm theo giai đoạn:** chủ dự án duyệt từng phase; không tự sang phase tiếp theo. → [ADR-0012](docs/adr/0012-lam-viec-theo-giai-doan.md)

---

## Tính năng sản phẩm

### 1. Bot farm (đã chạy)
Runner xử lý **2 instance cùng lúc** (`schedule.parallel`, mỗi máy một luồng, không vượt `max_running`; ADR-0002 sửa đổi 2026-11-20), mỗi instance bật auto: bật máy → mở game → đóng popup → các bước theo thứ tự → `observe` → tắt máy → máy kế tiếp. Hết vòng thì nghỉ `cycle.pause_between_cycles_min` phút. Trước **mỗi** bước kiểm tra có đang bị tấn công không (`defense`).

Thứ tự bước (`ORDER` trong [bot/runner.py](bot/runner.py)), chủ dự án chốt lại 2026-11-21 (lần 2): **tân thủ → chấm đỏ (notify, reddots) + nhận quà (rewards, mission, collect_city) → lối chơi (`play`: mỏ khoáng sản, đấu trường) → tình báo → phản quân (`rebels`, từ nhà chính cấp `rebels.min_hq_level` 15, `rebels.daily_target` 5 lượt/ngày) → huấn luyện → xây dựng (mainquest, construct, quests) → nghiên cứu → liên minh, chiến dịch → daily → thu thập (`gather`) **cuối lượt mọi ngày** (P7-1, chủ dự án 2026-11-24: gather chạy sớm chiếm 5/5 quân đoàn → cướp xe, phản quân, tình báo bị bỏ; xả việc `drain` chạy lại trước gather)**. Chấm đỏ dẫn tới lối chơi / tình báo / phản quân / hàng chờ rảnh (nghiên cứu, huấn luyện) thì làm luôn tiến trình đó; tính năng chưa biết thì lưu vào mục học (web). Kế hoạch "giữ mọi hàng chờ luôn chạy": [docs/strategy/priority-queues-plan.md](docs/strategy/priority-queues-plan.md). Thu thập: lịch hẹn ghé lại lúc đội cuối cùng tới mỏ (giờ thu thập chỉ hiện khi đã tới mỏ); thời gian về = thời gian đi. Bảng dưới liệt kê theo nhóm chức năng:

| Bước (`modules.*`) | File | Làm gì |
|---|---|---|
| `warday` | [warday.py](bot/modules/warday.py) | Chạy đầu lượt. **Lịch tuần sự kiện (chủ dự án 2026-11-23):** thứ 7 = ngày chiến tranh (lịch `warday.weekdays` + giờ reset `warday.reset_hour_utc`; công tắc tay `warday.mode` auto/on/off trên web; bảng thông báo `warday/notice`, banner "Giai đoạn N" tùy chọn `banner_ocr`): giữ khiên **liên tục** — Hiệp ước hòa bình (miễn phí, chuẩn bị 1h) trước giờ G, rồi khiên tức thì (vật phẩm trước, hết thì **mua bằng kim cương không giới hạn** trong cửa sổ, `warday.gem_cap` null), gia hạn trước khi hết `renew_before_min` phút; cửa sổ mở sớm `lead_h`, đóng muộn `tail_min` (không chắc → giữ khiên); cấm thu thập trong cửa sổ (phản quân được phép). P7-12: đã kiểm lại (test mô phỏng 24h không hở khiên); kim cương mua khiên ngày chiến tranh ghi `gem_ev` + `gems_spent_war`, **không** ăn vào trần 2000/ngày thường. Thứ 2 = ngày thu thập (`gather_weekdays`): gather vẫn chạy **cuối lượt** nhưng gửi **hết** quân đoàn còn lại, không để dành cho phản quân (P7-1). Ghi nhận mốc thể lực 0h/8h/15h UTC. P7-11: **"Đăng nhập hẹn giờ"** (5 thể lực/khung) — lịch hẹn giờ cố định kéo mỗi máy lên trong 18–19h và 8–9h UTC (01–02h, 15–16h VN; `warday.timed_login_windows_utc`), lần ghé trong khung chạy kèm notify/rewards (fact `timed_login_at`). P8-3 (chủ dự án 2026-11-24: khung 1 giờ đủ cho cả 7 máy): runner bật máy **ngay đầu khung**, tối đa 2 máy cùng lúc, lượt **ngắn** (`mode=timed`): rương "Đăng nhập hẹn giờ" **đầu tiên** (`notify.timed_login_chest`) → `warday.timed_login_steps` nếu còn trong `timed_login_visit_max_min` (12) phút → tắt máy; máy đang chạy lượt dài khi khung mở → nhận rương ở bước kế tiếp rồi nhường luồng nếu còn máy chờ (`timed_login_yield`); thử tối đa 2 lần/máy/khung; máy lỡ khung → log cảnh báo "LO khung" |
| `tutorial` | [tutorial.py](bot/modules/tutorial.py) | Qua tân thủ: V-marker vàng, hội thoại, CONGRATULATIONS, bảng Chương, trận chạy đường (mặc định tắt, chỉ bật cho TK mới) |
| `mainquest` | [mainquest.py](bot/modules/mainquest.py) | OCR chữ thanh nhiệm vụ → loại ([quest_rules.py](bot/quest_rules.py)): xây/tướng/chiến dịch → chạm, làm (đánh chỉ khi dự đoán thắng; boss khó hoãn tới khi lực chiến tăng `power_gain_pct`%); "Kích sát phiến quân" → mục tiêu giữa màn → "Tấn công" → Xuất chinh (chỉ phiến quân NPC, P4); tập kết/huấn luyện/tình báo/đấu trường… → **không chạm** (việc của bước khác). Kiểm kết quả thật = chữ nhiệm vụ đổi; cùng nhiệm vụ thất bại ≥ 2 lần → chờ `same_retry_h`×2ⁿ giờ |
| `collect_city` | [city.py](bot/modules/city.py) | Chạm biểu tượng tài nguyên nổi trên công trình |
| `rewards` | [rewards.py](bot/modules/rewards.py) | Thư, điểm danh, VIP, rương miễn phí, quà nổi (theo `rewards.routes`). Rương ngày VIP cần VIP → dùng vật phẩm "Thời gian VIP" (nút "Dùng", `rewards.use_vip_items`, chủ dự án cho phép 2026-11-20); **không** bấm "Đến" mua thẻ tháng. P7-3: thư nhận ở tab **đầu tiên** trước rồi tab có chấm đỏ, mở lại tới khi icon thư hết số đỏ; icon quà liên minh (số đỏ) lặp tới khi hết (`rewards.repeat_until_clear`, `ally_gift`) |
| `alliance` | [alliance.py](bot/modules/alliance.py) | Quyên góp công nghệ liên minh bằng **vàng** (nút phải "100", chỉ nửa phải-nửa dưới bảng; không nút kim cương "40", không nút ngón cái), trợ giúp; P7-2: mỗi lần đăng nhập Lãnh thổ → "Tranh Đoạt Cứ Điểm" → "Nhận" lợi nhuận tài nguyên; "Quà tặng liên minh" → P11 (`gift_loop`, mọi đường vào — icon thành phố, `reddots`, `rewards`, ô Liên minh): **cả hai tab** Quà đặc biệt + Quà thường (+ Rương Lv có chấm đỏ) nhận ("Nhận toàn bộ", không có thì "Nhận" từng món) → chuyển tab đi rồi về → đọc lại số đỏ trên tab / số nút "Nhận" / "Chưa có quà" → lặp tới khi cả hai tab rỗng ("Có thể nhận" là trần ngày, không phải số quà chờ; = 0 thì bỏ tab thường); trần `alliance.gift_loop_rounds` 30 vòng / `gift_loop_max_s` 180 s, số không giảm `gift_stall_rounds` 2 vòng → ảnh `logs/shots` + dừng; không bấm "Gửi Quà Thường" / "Tặng quà ẩn danh" |
| `construct` | [construct.py](bot/modules/construct.py) | Xây công trình **mới**: icon búa góc phải dưới có chấm đỏ → bảng "Xây dựng" → nhóm có chấm đỏ (bỏ "Con đường") → kéo thẻ chưa khóa ra bản đồ, tìm ô cỏ trống tới khi ô đặt xanh → tick → nút phải "Xây dựng" (**không** bấm "Xây dựng ngay"). Thẻ đặt hỏng (`construct_no_spot`…) → hủy bằng nút X, nhớ thẻ và bỏ qua 2 giờ (gấp đôi, tối đa 24 giờ), thử thẻ/nhóm khác; hết thẻ hợp lệ → không mở bảng tới khi hết hạn (P2) |
| `quests` | [quests.py](bot/modules/quests.py) | Nhiệm vụ Chương/Chính: tab có chấm đỏ → Nhận; OCR tên dòng, dòng của bước khác → không bấm "Đến" (P4); "Đến" → nâng cấp công trình (nhà chính ≤ `build.hq_max_level`); dưới `build.hq_targets` (9, 15) dòng "Xưởng kiến trúc" làm trước. P7-5: bảng nhiệm vụ **không cuộn** (xong luôn ở trên, cả `daily`); bước tắt trên máy (live #1: `modules.quests` false ở #1 → chưa chạy lần nào) → vẫn **chỉ nhận** thưởng, không bấm "Đến" (`quests.claim_when_off`). P8-4: #1 đã bật lại `quests` (PM sửa `data/settings.json`) → làm nhiệm vụ đầy đủ; dòng nhiệm vụ **cấm** (`quest_rules.FORBIDDEN`: mua/nạp/kim cương/gói, tấn công người chơi/căn cứ) không bao giờ bấm "Đến", cướp bóc → bước `play` |
| `campaign` | [campaign.py](bot/modules/campaign.py) | Đánh màn kế tiếp khi dự đoán "Thắng toàn diện" + nhận treo máy (tính là làm việc). P7-9: live #1 thua vì **không lái** (không xác nhận được đang trong trận sau 10 s) → nhận trận rộng hơn (`steer.campaign_battle`: `battle_hud`, biến thể `campaign/battle_hud_*`, dấu hiệu trận tân thủ), chờ `battle.enter_wait_s` (25 s), lưu khung `logs/inv/steer_no_battle/`; buff thêm theo ảnh mẫu `templates/steer/buff_*` (giữ ngón tay sendevent, không `input swipe`). Màn "Cài đặt quân đoàn" kiểu mới → "Đội hình đề xuất" rồi "Chiến đấu" (P4). Không dự đoán thắng → chỉ mở lại khi lực chiến tăng `campaign.power_gain_pct`% hoặc treo máy tích đủ `campaign.idle_claim_h` giờ |
| `notify` | [notify.py](bot/modules/notify.py) | Chấm đỏ: phúc lợi, online, hoạt động, tình báo, chiêu mộ miễn phí, tăng cấp tướng |
| `intel` | [intel.py](bot/modules/intel.py) | Tình báo (logic `notify.intel`): nhận ghim đã xong (tick xanh), làm ghim còn lại khi đủ năng lượng (thuốc thể lực nếu `notify.intel_use_potions`, không mua). P5: chờ bảng nhiệm vụ / bảng quà tới 3 s, ghim mục tiêu chỉ tìm giữa màn, màn quân đoàn kiểu mới chỉ Xuất chinh khi dự đoán thắng; không nhận ra → `unknown_panel/target/attack` + ảnh `logs/inv/intel_*` ([intel_rules.py](bot/intel_rules.py)). P13j (chủ dự án 2026-11-26): sau "Đi" trong **thành phố**, bấm **vật** trong ô sáng xanh lá (cột sáng xanh / bàn tay trắng `intel/point_hand`, [guide_tile.py](bot/guide_tile.py)) — không bấm lính (ô xanh lam), không bấm bong bóng; chạm không đổi màn → danh sách đen tọa độ; đang ở thành phố thì **không** dùng tọa độ ghim bản đồ thế giới. `no_march` (hết quân đoàn rảnh) → **dừng bước Tình báo hết lượt ghé** (mọi đường gọi: bước `intel`, chấm đỏ, notify). P7-4: sau Xuất chinh / Tiếp tế **kiểm quân đoàn thật sự đi** (nút biến mất + "Hành quân x/y" tăng), không thì bấm lại 1 lần rồi `not_departed`; hộp quà mọi màu tối đa `notify.intel_pickup_max` (2) hộp cùng lúc, chờ nhặt xong; làm xong → quét lại bản đồ (`intel_rescans`); thuốc thể lực: nút "Dùng" hàng bình 10 điểm (`intel/potion_10`), **không bao giờ "Mua"** |
| `research` | [research.py](bot/modules/research.py) | "Khuyến khích" trước, rồi nhánh theo `research.branch_order` (Phát triển > Đào tạo > Quân sự), trên → dưới; bấm "Nghiên cứu" rồi **kiểm lại** đã bắt đầu; thiếu tài nguyên → `research_nores` giãn chu kỳ (lịch + agent); trợ giúp/miễn phí. Thiếu ảnh mẫu bảng node → log "thieu anh mau", dùng màu + chữ (P2) |
| `train` | [train.py](bot/modules/train.py) | Huấn luyện lính T3 đến đủ `số đội × troops_per_march`; icon cột trái đầy → bỏ qua; thanh số lượng mặc định đã tối đa (không cần nút/ảnh `train/btn_max`, `train.use_max_button` false — chủ dự án 2026-11-23); không bắt đầu được (thiếu tài nguyên) → `train_nores` giãn chu kỳ (P2) |
| `rebels` | [rebels.py](bot/modules/rebels.py) | Từ nhà chính cấp 15, 5 lượt/ngày: **tự mở tập kết** Phản quân Cơ giáp trên bản đồ (3 phút, quân đoàn `rebels.legion`, chỉ Xuất chinh khi dự đoán "Thắng toàn diện"); nhớ cấp cao nhất đã đánh → lần sau thử cấp +1, dự đoán thua thì lùi; P5: 1 lượt thử tối đa `rebels.search_tries` (3) cấp, hạ dần. Tham gia tập kết liên minh `rebels.join_mech_rally` **mặc định tắt** (chủ dự án chưa quyết; cần ảnh `rally_mech`/`btn_join`); P7-10: nhà chính < `min_hq_level` (15) **không bao giờ** tham gia dù bật; tìm Cơ giáp **gõ số** vào ô "Cấp" (`rebels.type_level`, đọc lại sai → +/-); bảng thời gian tập kết tick "3Phút" + "Đủ thành viên sẽ xuất phát" (ảnh ô chưa chọn `rebels/chk_*_off`) → Xác nhận → Xuất chinh |
| `upgrade` | [upgrade.py](bot/modules/upgrade.py) | P13i (chủ dự án 2026-11-26): thợ rảnh thì **trước tiên** bấm bong bóng tròn vàng **cờ lê** nổi trên công trình ("nâng được ngay", [wrench.py](bot/wrench.py), `templates/build/wrench_bubble.png`, `build.wrench`; không phải bong bóng bàn tay thu tài nguyên) — trên nhà chính trước, không có thì nhà khác; `construct` cũng thử trước khi xây mới; bấm không ra màn nâng cấp → danh sách đen tọa độ. Cấp nhà chính chỉ ghi qua [hqlevel.py](bot/hqlevel.py): **không bao giờ hạ từ một lần đọc** (cần 2 lần đọc màn chi tiết khớp nhau, log WARNING). Sau đó: thợ rảnh → về thành phố từ thế giới (camera giữa nhà chính) → chạm (270,440), kiểm nhãn "Xưởng kiến trúc" → nâng cấp; thiếu điều kiện → "Nhảy" sang công trình điều kiện. HQ = `build.hq_max_level` (30) thì bỏ nhà chính. P13f (chủ dự án 2026-11-26): số thợ dùng được = `build.max_builders` theo máy (farm 1, #1 = 2) — **không** lấy y trong "x/y" (ô 2 phải mua bằng tiền thật, bot không thuê/mua); thợ rảnh thì xây tiếp ngay (tối đa `build.chain_max`); nhà chính không làm được ngay → nâng nhà tài nguyên (`templates/build/res_*.png`, `build.other_when_blocked`); runner đọc hàng chờ xây **sau mỗi bước**, thợ rảnh thì chạy upgrade/construct/mainquest/quests trước bước kế (`build.fill_rounds`); chỉ "nhường thợ cho nhà chính" khi thợ đang bận |
| `heal` | [heal.py](bot/modules/heal.py) | Bệnh viện (chữ thập đỏ trên mái) → "Hồi phục" bằng tài nguyên; không bao giờ "Hồi phục ngay". Chỉ chạy khi `observe` thấy bong bóng chữa trị hoặc trong lượt vừa có trận (`stepgate`); P5: không thấy bong bóng và chưa có trận → không chạm bệnh viện (`heal.open_without_bubble` false) |
| `gather` | [gather.py](bot/modules/gather.py) | Gửi quân đi mỏ đến khi "Hành quân x/y" đầy; ưu tiên alloy > metal > food, cấp cao → thấp, **tải trọng đội ≥ trữ lượng mỏ** (đội chở hết mỏ; không đọc được số thì không gửi); trước nhà chính cấp `gather.min_hq_level` (9, đủ 3 nhà lính) thì bỏ qua thu thập để làm nhiệm vụ căn cứ; nhớ dung tích mỏ theo cấp (`memory.db`) để bỏ cấp quá sức chở. Mỗi loại dò **từ cấp 8 hạ dần** 8 → 7 → 6 … tới cấp thỏa tải trọng (P13g, chủ dự án 2026-11-26; bỏ trí nhớ `gather_top` bắt đầu thấp hơn); mỏ biết chắc quá tải mọi quân đoàn thì bỏ qua không mở bản đồ; loại bị khóa theo nhà chính được nhớ tới khi nhà chính hoặc tướng đổi (`gather_sig`). P13g **không bao giờ gửi 2 quân đoàn tới 1 mỏ**: đọc tọa độ "X/Y" của mỏ vừa tìm, trùng ô đã gửi (`own_tile_block_min` 8 giờ) → bỏ, hạ cấp; trùng `same_mine_type_limit` (2) lần → loại ưu tiên kế tiếp; ô "Cấp" đọc ra khác cấp cần tìm → không bấm Tìm; không đọc được cấp → không dùng bảng dung tích. P3 (2026-11-23): hộp thoại "Có Chỉ huy trưởng khác đang hành quân đến…" sau Xuất chinh → **Hủy, không bao giờ Tiếp tục**; không tìm/gửi lại mỏ đội mình đang tới (cùng loại/cấp + cùng thời gian đi); mỏ bị chiếm / không tìm thấy / tranh chấp → tạm bỏ (loại, cấp) (`gather_hold`); trữ lượng OCR hỏng → dung tích mỏ đầy `gather.mine_caps` ([gather_rules.py](bot/gather_rules.py)) |
| `daily` | [daily.py](bot/modules/daily.py) | Nhận thưởng nhiệm vụ + rương điểm năng động |
| `mission` | [mission.py](bot/modules/mission.py) | P7-7 sự kiện **"Sứ mệnh"** (icon cột phải màn thành, ngay sau `rewards`): **chỉ** tab "Nhiệm vụ hằng ngày" → nút "Nhận" xanh; "Quà kỳ diệu" → rương nhỏ góc trên-trái nhận **miễn phí** khi có chấm đỏ. Mỗi lần chạm qua vùng cho phép theo màn (`tap_ok`) + lọc chữ trả phí: **không bao giờ** "Thẻ thông hành" (₫250000), "Săn kho báu" (xúc xắc), gói ₫250000/₫500000/₫1250000. `reddots` chuyển chấm đỏ icon này sang module (thiếu ảnh `mission/*` → bỏ qua êm) |
| `play` | [play.py](bot/modules/play.py) | Lối chơi (TK cấp cao): nhận rương Mỏ khoáng sản; Đấu trường 3 lượt miễn phí: P7-10 **chỉ đối thủ lực chiến yếu hơn** mình (`arena.weaker_only`, màu đỏ không miễn), không có thì "Làm mới" (`play/btn_arena_refresh`, tối đa `arena.refresh_max`, nút có số/kim cương → không bấm); luôn bấm "Đội hình đề xuất", nhớ đối thủ đã thua (`arena.*`); cướp xe cam/tím (`loot.*`) — P7-6: đọc "Số lần cướp bóc còn lại X/4" (0 → bỏ), **không bao giờ đánh xe đang cháy** (dấu X đỏ), chỉ xe SR/SSR chở **pha lê xanh** (`loot.crystal_only`), chưa có → nút làm mới (`play/btn_refresh`, tối đa `loot.refresh_max`, hiện hộp thoại lạ → đóng, dừng); P8-2: **so lực chiến** hộ vệ (popup xe) với đội hình ta (màn "Chiến đấu", sau "Đội hình đề xuất") — hộ vệ ≥ ta (hoặc ta < hộ vệ×(1+`loot.power_margin`)) hay không đọc được số → **không bấm Chiến đấu**, thoát, nhớ xe đã bỏ 12h, thử xe khác (`loot.max_attempts`). Chạy lần đầu sau reset ngày; không mua lượt |
| `reddots` | [reddots.py](bot/modules/reddots.py) | Quét lại chấm đỏ còn trên thành phố → mở, chỉ nhận nút "Nhận" xanh; bỏ icon "Quà" ($). P7-3: số đỏ **có thể nhận** (thư, quà liên minh, VIP, nhiệm vụ ngày) xử lý trước; xóa huy hiệu chat chạy **cuối**, chỉ khi còn thời gian. **Không chạy mỗi lần ghé** (PM 2026-11-23, A-OPT-1): mỗi máy tối đa 1 lần / `reddots.min_interval_min` (30) phút, sớm hơn chỉ khi `notify` vừa nhận được quà hoặc có chấm đỏ mới; tối đa `reddots.max_s` (90) giây / lần; icon mở ra vô ích bỏ qua `dead_h` giờ, lặp lại thì gấp đôi (tối đa `dead_cap_h`) |
| `observe` | [observe.py](bot/modules/observe.py) | Luôn chạy cuối: OCR tài nguyên, lực chiến, trạng thái hành quân → `data/state.json` |
| (phòng thủ) | [defense.py](bot/modules/defense.py) | Bị tấn công → khiên (vật phẩm, hết thì kim cương trong trần), tùy chọn sơ tán quân (cần ảnh mẫu cảnh báo). P5: thiếu ảnh mẫu dòng khiên (`row_8h`) / icon → `missing_tpl`, không mở bảng; thiếu `alert_attack` → chỉ dựa vào mép đỏ nhấp nháy |

**Kiểm điều kiện + giãn chu kỳ** ([bot/stepgate.py](bot/stepgate.py), giai đoạn P1 2026-11-23): trước `heal`, `campaign`, `warday`, `mainquest` runner kiểm điều kiện từ trí nhớ (không mở màn hình); bước chạy xong mà trả 0 liên tiếp ≥ `stepgate.after` lần thì tạm bỏ `base_min` × 2ⁿ phút (tối đa `cap_h`), lưu theo máy (fact `idle:<bước>`, `state.json` → `idle_backoff`); làm được việc thì xóa. Bỏ vì điều kiện quá `max_skip_h` giờ thì vẫn chạy 1 lần kiểm tra. `--modules` trên dòng lệnh bỏ qua cổng này.

**Máy treo** (A-OPT-3): chụp màn hình timeout ngắn (`ldplayer.screencap.*`); không cứu được sau 1 lần dò lại địa chỉ ADB → `Device.dead` → runner bỏ lượt máy đó ngay, sang máy kế tiếp.

**Lái quân trong trận chạy đường** ([steer.py](bot/steer.py), [touch.py](bot/touch.py), [stream.py](bot/stream.py)): giữ ngón tay bằng `sendevent /dev/input/event2` suốt trận, đọc khung hình liên tục, trượt ngang để nhặt buff xanh (cả cổng nhạt), bắn bảng đỏ có số khi còn xa và né khi đã gần, né hàng rào gai sắt (né mạnh nhất), vòng đỏ ném bom, vệt xe lao. P7-8: cổng đỏ "-X" (bảng đỏ có số, rộng ≥ 60 px) đọc số qua các khung → tốc độ tăng do bắn; dự đoán lật thành "+" kịp trước khi chạm đội quân (`steer.flip_ok`, an toàn 80 %) → lao vào như buff, không thì né.

**Quân đoàn:** số quân đoàn tối đa = số việc ngoài thế giới cùng lúc (tình báo, phản quân, thu thập, mỏ liên minh, cướp xe). "Hành quân x/y" đầy thì dừng các việc này (`ctx.march_full()`). → [ADR-0007](docs/adr/0007-lai-quan-bang-sendevent.md)

**Giao diện web** ([web/server.py](web/server.py), [web/index.html](web/index.html)) — `run.bat` hoặc `python main.py --web` → http://localhost:8080:
- Mỗi máy: bật/tắt auto, "Chạy ngay", bật/tắt từng bước, nút "Bật khiên".
- Mọi giờ hiển thị theo **GMT+7, định dạng dd/MM/yyyy HH:mm:ss** (hàm `clock` trong index.html). Tên nghiên cứu OCR sai dấu được sửa bằng [bot/vnames.py](bot/vnames.py) (bảng từ vựng `VOCAB`, thêm từ khi gặp tên lỗi).
- Hiển thị tài nguyên, lực chiến, hành quân (đang đi / xong lúc / về lúc), lỗi gần nhất, log.
- Tùy chọn chung + theo máy lưu `data/settings.json` (đè lên `config.yaml`). Danh sách tùy chọn ở [web/options.py](web/options.py); `ready=False` = "sắp có".

**Cố ý KHÔNG tự động:** nút tốn kim cương ("Huấn luyện ngay", "Tăng cấp ngay"…) — ngoại lệ: nút "… ngay" ghi **"Miễn phí"** (mốc miễn phí, 0 kim cương) thì được bấm (chủ dự án 2026-11-21; chế độ làm theo mẫu kiểm bằng OCR, đọc ra số kim cương hoặc không đọc được thì vẫn chặn), chiêu mộ cao cấp bằng kim cương (chiêu mộ bằng **phiếu** chỉ khi nút "10 lần" có chấm đỏ: qua `notify`, hoặc ở chế độ `follow` khi chữ V chỉ vào nút đó, tối đa 1 lần — chủ dự án 2026-11-18, 2026-11-20), chat liên minh (chỉ được MỞ rồi thoát để xóa huy hiệu tin nhắn chưa đọc — `bot/modules/chat.py`, chủ dự án 2026-11-22; không gõ, không gửi, không bấm liên kết), mua đồ tiệm, xây cờ, "Tăng tốc"/"Dùng thử" thợ xây, đường trả phí ("Mở khóa", "Cấp mùa", "Nạp thẻ"…).

### 2. Account Manager (đang PoC)
Mục tiêu: **1 instance LDPlayer, nhiều tài khoản**, chuyển qua lại bằng snapshot/restore dữ liệu app (Option C, root mode LDPlayer). Đã đạt 10/10 lần chuyển đúng danh tính trên #7, đã chuyển chéo #7→#8 (hai instance này đã xóa sau PoC). Script: [poc/slot.sh](poc/slot.sh), [poc/ident.sh](poc/ident.sh), [poc/switch_test.sh](poc/switch_test.sh), [poc/inventory.sh](poc/inventory.sh). → [ADR-0009](docs/adr/0009-da-tai-khoan-snapshot-du-lieu-app.md)

Tài liệu: [Phase 0](docs/account-manager/Phase0-Technical-Feasibility-Report.md) · [Phase 1 PoC](docs/account-manager/Phase1-PoC-Results.md) · [Kiểm kê tài khoản](docs/account-manager/Account-Inventory.md).

---

## Kiến trúc mã nguồn

```
main.py              CLI: --once --only --modules --capture --check --web
bot/runner.py        Runner (luồng nền), ORDER các bước, vòng lặp instance, Stop an toàn giữa 2 bước
bot/ldconfig.py      P13h: đọc/kiểm file cấu hình máy LDPlayer, ghi đúng khóa adbDebug
bot/ctx.py           Ctx mỗi tài khoản: shot/find/tap_tpl/wait_for, ensure_city, close_popups, save_debug
bot/device.py        LDConsole (ldconsole.exe: launch/quit/runapp/list2) + Device (adb: tap/swipe/screencap)
bot/vision.py        Template matching OpenCV; thiếu ảnh mẫu → cảnh báo 1 lần, coi như không thấy
bot/ocr.py           Tesseract (chỉ gói 'eng' → tiếng Việt mất dấu, so khớp theo từ khóa gần đúng); ROI cố định
bot/badges.py        Tìm chấm đỏ theo màu HSV
bot/build.py         Nâng cấp công trình (đi theo nút "Nhảy" tới điều kiện), KHÔNG bấm "Tăng cấp ngay"
bot/learn.py         Học máy mini (giai đoạn E+F): nhật ký kinh nghiệm mỗi lần chạm (bảng `exp`), kNN màn hình, biến thể ảnh mẫu tự học (`templates/<tên>@auto<N>.png`), "chỗ chết"
bot/steer.py         Lái quân theo màu; touch.py = Finger (sendevent); stream.py = FrameStream (screencap liên tục)
bot/stepgate.py      P1: điều kiện trước khi chạy + giãn chu kỳ khi trả 0 (heal/campaign/warday/mainquest), hàm thuần trên trí nhớ
bot/queues.py        Q0/P2: đọc hàng chờ "x/y" cột icon trái: ảnh chữ số templates/qdigits → OCR bỏ phiếu → chấm đỏ = rảnh
bot/march_count.py   P3: đọc "Hành quân x/y" bằng ảnh chữ số templates/mdigits; khung "Hành quân" vắng trên bản đồ = 0 đội
bot/gather_rules.py  P3: luật thuần thu thập (dung tích mỏ đầy, mỏ đội mình đang tới, phân loại thông báo OCR, tạm bỏ)
bot/intel_rules.py   P5: luật thuần tình báo (bảng nhiệm vụ / bảng quà, vùng ghim mục tiêu, lý do unknown_*, đếm log)
bot/quest_rules.py   P4: luật thuần nhiệm vụ (phân loại chữ OCR → bước phụ trách, phiến quân NPC, thử lại cùng nhiệm vụ) + màn follow
bot/tplneed.py       P2: ảnh mẫu chưa có → bỏ qua nhanh + log "thieu anh mau <tên>" (1 lần/giờ)
bot/unlock_popup.py  P13k: popup "Mở khóa Binh chủng này" → chỉ bấm "Xác nhận" (tiêu đề + nút), không bao giờ "Đến";
                     gắn ở close_popups / goto / back_out / skip_dialogs / dismiss_reward / tutorial.decide; Ctx chặn
                     mọi lần chạm vào vùng "Đến" khi popup đang hiện; 2 lần không đóng → danh sách đen hết lượt ghé
bot/map_menu.py      P13l (chủ dự án 2026-11-26): menu vòng tròn bản đồ. Menu CĂN CỨ NGƯỜI CHƠI (Trinh sát / Tập kết /
                     Tin tức / Tấn công — bấm "Tấn công" là khai chiến) và menu ô đất trống (Chuyển thành / Chiếm lĩnh)
                     → Ctx không bấm điểm nào, đóng bằng Back, danh sách đen điểm vừa chạm
bot/world_target.py  P13l: mũi tên xanh → vật thật bên dưới (nhãn "Phiến quân" → thanh máu → vật khác nền), không offset
                     cố định; loại căn cứ người chơi (cờ, mái khiên, thẻ "(XXX)"); kiểm cả cú bấm mù giữa bản đồ.
                     Thao tác tại chỗ: bot/modules/arrow.py (phiến quân / tập kết Cơ giáp / thu thập 1 quân đoàn)
bot/intel_pins.py    P13l: phân loại ghim Tình báo = biểu tượng + màu; thua → bỏ đúng lớp đó tới khi lực chiến tăng
                     `notify.intel_lose_power_pct`% (fact `intel_lost_classes`). Nhà chính < `schedule.intel_priority_hq`
                     (15) → Tình báo mọi lượt ghé, chạy sớm
bot/resources.py     P13l: popup "Thiếu tài nguyên" → "Dùng đạo cụ" (nút TRÁI) → gói nhỏ nhất trong túi → "Dùng" → làm
                     lại (huấn luyện / nâng cấp / xây / nghiên cứu); Ctx chặn nút kim cương của 2 màn này
bot/state.py         Store: data/state.json (quan sát) + data/settings.json (tùy chọn web), ghi atomic
bot/modules/*.py     Mỗi bước = module có run(ctx)
web/                 Flask, chỉ nghe 127.0.0.1 (trang /agent: quyết định của agent, chỉ đọc)
src/aowbot/          Kiến trúc mới (ADR-0013): domain (luật thuần) → application (world view, planner, utility,
                     executor, điều phối sự kiện) → infrastructure (SQLite, khóa, adapter `legacy` vào bot/*) /
                     interfaces (CLI) → app (composition). Luật phụ thuộc kiểm bằng `lint-imports` (pyproject.toml).
                     bot/* chỉ được import aowbot.domain. Agent TẮT mặc định: chạy trên máy khi CẢ HAI — công tắc chung `agent.enabled`
                     (web, P6) và máy chọn chế độ "Agent"; tắt công tắc = dừng khẩn cấp agent mọi máy. Trần cứng 2 máy: aowbot.domain.rollout.
templates/<nhóm>/    Ảnh mẫu PNG cắt từ màn 540×960 (xem templates/README.md)
tools/               snap.py (chụp/cắt ảnh mẫu), record.py (ghi thao tác người chơi), replay_tutorial.py, run_tutorial.py
poc/                 Script bash Account Manager (Git Bash, MSYS_NO_PATHCONV=1)
backups/             .ldbk toàn VM + slot tài khoản gốc — KHÔNG xóa
logs/                bot-YYYYMMDD.log, shots/ (ảnh lỗi), rec/ (bản ghi), live/ (trace chạy thử)
```

### Quy ước khi viết code
- **Màn hình cố định 540×960 dọc, DPI 240.** Mọi tọa độ/ROI trong code & config theo hệ này. Máy lỡ chạy độ phân giải khác cùng tỉ lệ (vd 720×1280) thì `bot/device.py` tự thu nhỏ khung và nhân tọa độ chạm, kèm cảnh báo (P13g) — vẫn nên đặt lại 540×960. **P13h:** trước khi bật máy, `LDConsole.launch` đọc `vms/config/leidian{idx}.config`; sai độ phân giải / DPI (`ldplayer.resolution`/`dpi`, riêng máy: `instances.N.ldplayer.*`) hoặc `adbDebug` ≠ 1 thì sửa **chỉ khi máy đã tắt hẳn** (`ldconsole modify --resolution` + đúng khóa `basicSettings.adbDebug`); không bao giờ đụng khóa định danh (`propertySettings.*`); `ldplayer.fix_display` false để tắt. → [ADR-0003](docs/adr/0003-he-toa-do-540x960.md)
- Module mới: thêm file `bot/modules/<ten>.py` có `run(ctx)`, đăng ký vào `ORDER` ([runner.py](bot/runner.py)), `modules` trong [config.yaml](config.yaml) và `MODULES` trong [web/options.py](web/options.py).
- Lỗi trong một bước không được làm chết cả lượt: runner bắt exception, lưu ảnh `logs/shots/`, gọi `ctx.ensure_city()` rồi sang bước tiếp. Module nên tự thoát về thành phố khi xong. 2 bước liên tiếp không về được thành phố → runner cứu kẹt (đóng popup, rồi khởi động lại game; `nav.rescue_max`), chỉ bỏ lượt khi cứu không được.
- Kết quả mỗi bước (ổn / có ảnh lỗi / lỗi / kẹt) ghi vào `state.json` → `stats`, hiện bảng trên web. Watchdog (`config.yaml` → `watchdog`) ném `ctx.Stuck` (BaseException) khi màn hình đứng yên/bước quá giờ → runner `force-stop` + mở lại game. Không bắt `BaseException` trong module.
- Ảnh mẫu thiếu = bỏ qua thao tác (không crash). Kiểm tra: `python main.py --check`.
- Ưu tiên nhận diện bằng màu/hình (như `steer`, `badges`) cho phần tử có hoạt ảnh; dùng ảnh mẫu cho nút tĩnh.
- Logic quyết định nên là **hàm thuần** (nhận ảnh → trả hành động) để test offline bằng bản ghi (`tutorial.decide()` + `tools/replay_tutorial.py`). → [ADR-0011](docs/adr/0011-tan-thu-ham-quyet-dinh-thuan.md)
- Code & comment Python viết **tiếng Việt không dấu** (giữ nhất quán với code hiện có); tài liệu `docs/` viết tiếng Việt có dấu; text hiển thị web có dấu.
- Cấu hình mới: thêm vào `config.yaml` kèm comment; nếu người dùng cần chỉnh trên web thì thêm vào `GROUPS` của `web/options.py`.

### Chạy & kiểm tra
```bash
python main.py --check                 # ảnh mẫu còn thiếu (bot/tplcheck.py)
python tools/snap.py todo research     # ảnh mẫu thiếu theo nhóm; grid SRC / cutmany SRC tên=x1,y1,x2,y2 để cắt
python main.py --once --only 0         # 1 lượt cho instance 0
python main.py --modules gather --once --only 0
python main.py --capture 0             # chụp màn hình → logs/
python tools/run_tutorial.py --idx 5   # chạy riêng bước tân thủ (game đang mở) → logs/live/
python tools/replay_tutorial.py        # kiểm tra offline decide() với bản ghi mới nhất
python tools/check_tutorial.py         # hồi quy decide() trên các khung từng kẹt (tests/fixtures/tutorial/)
python tools/learn.py report           # (hoặc web http://localhost:8080/#hoc, tab "Học & Agent") bot học được gì: tỉ lệ chạm ăn/trượt, chỗ chết, mẫu kNN, biến thể ảnh mẫu
python tools/learn.py train / eval     # nạp mẫu kNN từ ảnh cũ / đo độ chính xác
python tools/imitate_eval.py --idx 3   # đo offline bộ "làm theo mẫu" (bot/imitate.py) trên thao tác tay đã ghi của máy #3
python main.py --web                   # web quản lý (launch config: .claude/launch.json "aow-web")
python tools/report_ro.py [--split "YYYY-mm-dd HH:MM"]   # số đo chỉ-đọc trước/sau (lần ghé vô ích, perf ADB/ảnh/OCR, follow kẹt, cấp nhà chính/ngày)
python tools/report_ro.py --24h       # P6: tổng hợp 24 giờ — bước không lỗi ≥ 95 %, kim cương theo nguồn (bảng gem_ev, chỉ khiên), số máy cùng lúc ≤ 2, chỉ số P1-P5; hướng dẫn chạy thật: docs/strategy/p6-huong-dan-chay-that.md
python tools/follow_stats.py [--replay] [--human] [--since YYYY-mm-dd]   # P4: follow kẹt theo loại màn, phát lại decide() trên ảnh kẹt, thao tác tay
python -m aowbot world|plan|shadow <idx>                 # agent dry-run: trạng thái + độ tươi / quyết định + lý do / phát lại
```
Công cụ dev (từ F0, 2026-11-21): `pip install -e .[dev]` → `python -m pytest`, `python -m ruff check .` (luật nghiêm cho mã mới), `python -m ruff check bot web tools main.py --select E9,F63,F7,F82` (mã cũ). Cấu hình trong `pyproject.toml`. Test tự động mới bắt đầu có; ảnh fixture không có trong git (hồi quy ảnh chỉ chạy local). Kiểm chứng chính vẫn là chạy thật trên instance + đọc `logs/` và ảnh `logs/shots/`. Kế hoạch tổng: [docs/strategy/MASTER-IMPLEMENTATION-PLAN.md](docs/strategy/MASTER-IMPLEMENTATION-PLAN.md).

### Môi trường
- Windows 11, Python 3.12, LDPlayer 9 tại `D:\LDPlayer\LDPlayer9\` (`ldconsole.exe`, `adb.exe`).
- ADB serial: `emulator-<5554 + 2·idx>` (vd #0 = `emulator-5554`, #5 = `emulator-5564`).
- Game: bản VN `com.ageofwarpath.globalwarzone.vn` 2.5.16 (bot dùng bản này) và bản Global `com.ageofwarpath.globalwarzone` 3.6.0 trên #2–#6.
- Tesseract: `C:\Program Files\Tesseract-OCR\tesseract.exe`.
- Git repo (remote `origin` trên GitHub). `data/`, `logs/`, `backups/`, `tests/fixtures/` bị gitignore.
