# P6-4 — Rà soát an toàn: mọi đường tiêu kim cương / vật phẩm trả phí

Ngày: 23/11/2026, nhánh `p6-agent-24h`. Rà bằng tìm kiếm mã (không chạy máy): mọi chỗ bấm nút có thể tốn kim cương, mua, tăng tốc, dùng vật phẩm, "… ngay", "Xác nhận", phím Back.

Cổng A-SAFE (tên gọi trong kế hoạch): A-SAFE-1 khiên đóng khi lỗi (`aowbot.domain.policy.shield_decision`), A-SAFE-2 `reddots.allowed`, A-SAFE-3 `play.arena_eligible`, A-SAFE-4 `notify.recruit_choice`, cùng các chặn chữ `bot/buttons.is_danger` / `bot/imitate.is_danger` và `SafetyPolicy` của agent.

## 1. Đường tiêu kim cương được phép (đã qua cổng)

| Đường | Cổng | Ghi sổ |
|---|---|---|
| Khiên khi bị tấn công (`defense.shield`) | A-SAFE-1: không đọc được số vật phẩm / kim cương → không bấm; không đủ → không bấm; trần `defense.gem_cap_daily` (2000/ngày, ngày UTC) | `gem_ev` nguồn `shield` + log `KIM CUONG:` |
| Khiên ngày chiến tranh (`warday.ensure` → `defense.war_shield`) | A-SAFE-1 với `daily_cap=None` (không giới hạn) **chỉ** khi đang trong cửa sổ chiến tranh (chủ dự án 2026-11-23); vẫn đóng khi lỗi | `gem_ev` nguồn `shield_war` + log `MUA khien` |
| Bị tấn công trong ngày chiến tranh (`defense.run`) | như trên, chỉ khi `warday.window()` khác None | `shield_war` |

`python tools/report_ro.py --24h` cộng `gem_ev` theo nguồn; nguồn khác `shield`/`shield_war` → **KHÔNG ĐẠT**. Ngoài ra so sánh kim cương giảm giữa các lần `observe` với sổ: giảm mà không có trong sổ → dòng "CAN XEM".

## 2. Đường dùng vật phẩm (không tốn kim cương, chủ dự án đã cho phép)

| Đường | Điều kiện |
|---|---|
| Hiệp ước hòa bình (`defense.peace`) | Chỉ bấm khi OCR thấy chữ "Miễn phí" phía trên nút; kiểm lại sau khi bấm |
| Vật phẩm "Thời gian VIP" (`rewards`, `ctx` VIP) | `rewards.use_vip_items` (2026-11-20); không bấm "Đến" thẻ tháng |
| Thuốc thể lực tình báo (`notify.intel_potions`) | `notify.intel_use_potions`, tối đa `intel_max_potions`/lượt; nút ảnh mẫu `intel/btn_use_potion` ("Dùng") — **xem mục 4.2** |
| Phiếu chiêu mộ 10 lần | A-SAFE-4: chỉ khi nút có chấm đỏ |

## 3. Nút "… ngay" / có giá — đã chặn

| Chỗ | Cách chặn |
|---|---|
| Xây/nâng cấp "… ngay" (`build.free_instant_button`) | Chỉ khi dòng dưới ghi "Miễn phí" và **không có số** (OCR) |
| Bước nhanh tân thủ (`tutorial` 5a) | Ảnh mẫu `tutorial/label_free` ("Miễn phí") trong vùng nút trái — chỉ ảnh, không OCR số (xem 4.3) |
| Nghiên cứu (`research.start_buttons`) | Ảnh mẫu nút phải "Nghiên cứu" (khớp nút "Nghiên cứu ngay" chỉ 0,41 < ngưỡng 0,85, test trên ảnh #1); dự phòng chữ qua `buttons.with_text` (chặn "ngay") |
| Huấn luyện, hồi phục (`train`, `heal`) | Nút theo chữ qua `buttons.with_text` → `is_danger` chặn "ngay", "mua", "nạp", "tăng tốc", giá tiền |
| Làm theo mẫu (`imitate`) | `imitate.is_danger` + OCR chữ quanh chỗ chạm; "… ngay" chỉ khi kèm "Miễn phí" |
| Quà / chấm đỏ (`notify`, `reddots`) | Chỉ nút "Nhận"/"Miễn phí" xanh; A-SAFE-2 tôn trọng tùy chọn |
| Đấu trường | A-SAFE-3; không mua lượt / Làm mới |
| Quyên góp liên minh | Ảnh mẫu nút vàng; **P6 thêm vùng nửa phải** `alliance.DONATE_ROI` (nút trái là kim cương) — đóng A-SAFE-5 ở mức mã, chưa kiểm trên ảnh thật |
| Agent (`src/aowbot`) | `SafetyPolicy.check` trước mọi hành động: `premium_cost > 0` mà không có trong whitelist (rỗng) → từ chối |
| Hộp thoại "Rời trò chơi?" | `ctx.press_back` không bấm Back ở thành phố/bản đồ; **P6 thêm `ctx.cancel_exit`** trong `close_popups` và `dismiss_reward` (trước đó `dismiss_reward` có `common/btn_confirm` trong danh sách đóng → có thể bấm "Xác nhận" thoát game) |

## 4. Đường chưa qua cổng / cần chủ dự án biết

1. **Nút "Xác nhận" sau khi bấm dòng khiên** (`defense.shield`, `defense.peace`: `ctx.tap_tpl("common/btn_confirm")`). Quyết định mua đã qua A-SAFE-1 trước đó, nên hộp thoại này là xác nhận của chính lần mua được phép. Rủi ro còn lại: nếu bấm nhầm dòng (ảnh mẫu dòng lệch) thì xác nhận dòng khác — giá thực có thể khác `PRICE`; sổ vẫn ghi theo kim cương đọc trước/sau.
2. **Thuốc thể lực** (`notify` dòng ~174): không có kiểm chữ "Miễn phí"/giá trước khi bấm `intel/btn_use_potion`. Nếu hết thuốc mà bảng hiện nút mua cùng chỗ thì chỉ ảnh mẫu "Dùng" bảo vệ. Đề xuất: thêm OCR chặn `is_danger` quanh nút (chưa làm — cần ảnh bảng thuốc lúc hết thuốc).
3. **Tân thủ "… ngay (Miễn phí)"**: chỉ dựa ảnh mẫu `label_free`, không đọc số kim cương. Đề xuất: dùng chung `build.free_instant_button` (OCR) — chưa làm vì cần chạy lại hồi quy `tools/check_tutorial.py` trên khung có ảnh.
4. **Biến thể ảnh mẫu tự học** (`templates/<tên>@auto<N>.png`, `bot/learn.py`): chỉ các nút đóng / quay lại / Hủy thoát trong `learn.LEARNABLE` được học biến thể — không nút nào có giá. Rủi ro còn lại: biến thể học sai của nút đóng khớp nhầm nút khác (đã gặp 21/11 với nút quay lại); xem tab "Học & Agent" khi duyệt.
5. **Phím Back trên bản đồ khi đóng menu ô đất** (`gather.close_map_menu`): cố ý (đã kiểm màn đổi), luôn bấm Hủy nếu hộp thoại thoát hiện.

Không tìm thấy đường nào bấm: "Tăng tốc" bằng kim cương, mua đồ tiệm, "Nạp", "Mở khóa", gói 3 ngày khiên (không có trong `shield_options` mua).

## 5. Kiểm chứng tự động

- `tests/legacy/test_defense_shield.py`, `tests/unit/test_warday_week.py::test_policy_unlimited_only_when_cap_none`: không đọc được → không mua, kể cả khi không giới hạn.
- `tests/legacy/test_warday_shield.py`: Hiệp ước chỉ bấm khi "Miễn phí"; ngoài ngày chiến tranh đi đường có trần.
- `tests/legacy/test_p6_templates.py`: nút nghiên cứu không khớp "Nghiên cứu ngay"; hộp thoại thoát luôn Hủy trước "Xác nhận".
- `tests/legacy/test_p6_report.py`: báo cáo 24h đánh KHÔNG ĐẠT khi có nguồn kim cương lạ.
