# Báo cáo P12 — sửa lỗi live-run-4 + góp ý t55u / t56u / t57u

Nhánh `p7-live-fixes`, từ `f0ac32e` (P11). Không push, không chạy bot thật / LDPlayer / ADB. Mọi kiểm chứng dựa trên log và ảnh ADB 540×960 của live-run-4 (24/11/2026 18:08–20:49 giờ VN).

**Tổng hoàn thành: ~87 %.** 6 commit, **1378 test pass** (P11: 1324; thêm 54), `ruff` sạch, `mypy` sạch, `python main.py --check` OK trước mỗi commit.

## Từng mục

| Mục | Trạng thái | Commit |
|---|---|---|
| P12-1 Khiên: Hiệp ước chuẩn bị / hồi chiêu → vật phẩm ngay | XONG (100 %) | `bc97c54` |
| P12-2 Chấm đỏ: danh sách đen tọa độ vô hiệu | XONG (~90 %) | `de57ddb` |
| P12-3 VIP: "Dùng" vật phẩm điểm VIP (t57u) | XONG (~90 %) | `7fc3fe8` |
| P12-4 Phản quân: "Tìm kiếm", HQ thấp đánh lẻ, ô Cấp (t55u) | XONG phần lớn (~80 %) | `4712a0c` |
| P12-5 Xây đường (t56u) | XONG (~85 %) | `3897599` |
| P12-6 Popup kẹt + thử lại bước sau khi máy treo | XONG phần lớn (~75 %) | `80ed024` |

### P12-1 — Khiên
- Nguyên nhân live4: `shield.plan` coi "Hiệp ước vừa dùng (đang chuẩn bị 1h)" là đã có khiên → cuối lượt "đang chuẩn bị – bỏ qua", khiên TẮT (#0/#2–#6).
- Sửa: khiên tắt + Hiệp ước đang chuẩn bị → vẫn bật, **bỏ dòng 8h**, dùng vật phẩm (12h/3d/1h), hết thì mua kim cương trong trần 2000/ngày (log kim cương trước/sau, `gem_ev` nguồn `shield_daily`). Dùng Hiệp ước xong thì **đọc lại khiên**; chưa "on" (đang chuẩn bị) → dùng vật phẩm ngay trong lượt. `defense.peace_label_status` phân biệt Miễn phí / Chuẩn bị / hồi chiêu; `peace()` trả `preparing`. Log trạng thái Hiệp ước + loại khiên đã dùng.
- Giữ: không chồng khiên khi còn ≥ 1h; gia hạn khi còn < 60 phút; thứ 7 (warday) không đổi.
- Test: `tests/legacy/test_p12_shield_prep.py` (12) + cập nhật `test_p9_shield_order.py` (luật cũ "chuẩn bị = bỏ qua" đã bị thay).

### P12-2 — Chấm đỏ
- Nguyên nhân thật của trần 240 s: không phải vòng ngoài (mỗi chấm đã bị loại sau 1 lần vô ích trong bước), mà là **thao tác lặp bên trong**: VIP @414,175 "nhận 0" ở reddots + rewards, ô phúc lợi @139,530 bấm 4–5 lần (20–40 s/lần) mỗi khi `notify.run` chạy lại.
- Sửa: `bot/tapguard.py` — `TapGuard` theo lần ghé (runner tạo mới), cùng (phạm vi, ô 30 px) 2 lần không hiệu ứng → danh sách đen tới hết lần ghé, log tọa độ + lý do. Áp vào: chấm đỏ thành phố (`reddot`), chấm trang VIP (`vip`), ô quà phát sáng (`glow`: ô vẫn sáng sau khi bấm). Vòng reddots dừng khi chỉ còn chấm trong danh sách đen (`reddots.remaining`). Trần 240 s giữ làm an toàn.
- Khoảng trống: các handler khác (hub thông báo, sự kiện) chưa gắn guard riêng.

### P12-3 — VIP (t57u)
- Nguyên nhân: chấm đỏ @414,175 mở bảng **"Tăng cấp VIP"**, bot chỉ tìm nút "Nhận" → 0.
- Sửa: `rewards.vip_point_buttons` (hàm thuần) — tiêu đề `title_upgrade` + nút `btn_use_points` (nền xanh đậm, th 0.92, cột nút) + lọc OCR `safe_vip_use` (nhãn "Mua và dùng" hoặc chữ có số → không bấm). `vip_points` lặp tới khi hết nút; màn không đổi 2 lần → danh sách đen. Config `rewards.use_vip_points` (web).
- Đã kiểm: hàng "Mua và dùng" 20/1000/2000/10000 không bao giờ được trả về (test trên khung thật + ảnh chủ dự án).
- Khoảng trống: chưa thấy màn sau khi bấm "Dùng" (có hộp số lượng không) — bot bấm `common/btn_confirm` nếu có.

### P12-4 — Phản quân (t55u)
- (a) `mainquest.npc_popup_action` / `npc_search`: popup "Phiến quân Lv.N" + "Tối đa có thể tấn công phản quân cấp X!" → bấm "Tìm kiếm" → chạm mục tiêu giữa màn → "Tấn công" → luồng cũ (Đội hình đề xuất → Xuất chinh).
- (b) Live4 #3–#6 (nhà chính 4–5) trả `npc_skip` ngay vì `world.min_hq_level` 6 — không phải luật HQ 15. Nay nhiệm vụ phiến quân vẫn theo thanh nhiệm vụ, **đánh lẻ**. HQ < 15 vẫn **không** tham gia / tự mở tập kết Cơ giáp (`join_hq_ok`, `rebels_ready` giữ nguyên).
- (c) Ảnh #1 `s184116`/`s184141`: ô "Cấp" Cơ giáp mỗi lần +/- đổi **5 cấp** (5 ↔ 10) → cấp 7/8/9 không tồn tại; đó là lý do "không vào được lv.7". `gather.snap_level` + `set_level` học `ctx.level_step`, `type_level` gõ bội số; `rebels.snap_levels` bỏ cấp trùng (trước: 3 cấp × ~70 s đều "KHÔNG đạt"); nhớ bước trong `rebels_levels.step`.
- Khoảng trống: dòng nhiệm vụ phiến quân trong **bảng** Nhiệm vụ (`quests`, #6 "dòng 3/4: rebels") vẫn chuyển cho bước khác, chỉ thanh nhiệm vụ chính được làm. Vì sao "input text 9" ra "1" (khung `s184059`) chưa rõ — có thể do game kẹp về bội số 5 rồi OCR đọc sai; snap giải quyết hệ quả.

### P12-5 — Xây đường (t56u)
- `construct.roads` chạy đầu bước `construct` (không tốn thợ, chạy cả khi xây mới đang bị chặn): `road_icon` → `confirm_dialog` ("Xác nhận" th 0.93 + nút "Hủy" bên trái cùng hàng) → `gold_cost` (icon chi phí vàng cam) → bấm. Kim cương / không chắc → **Hủy**, ảnh `logs/shots/*road_gem_cost`, không bấm Xác nhận. Config `construct.roads`.
- Khoảng trống: dòng chữ "Nhấp trên mặt đất để thi công đường" và chế độ "Làm đường / Xóa đường" — chưa biết bấm Xác nhận có đủ hay cần chạm mặt đất; cần một lần chạy thật để xác nhận.

### P12-6 — Popup kẹt / máy treo
- (a) Khung thật #5 (`live4/#5/auto/s202258`) là popup **"Chiến dịch 1"** có mũi tên V hướng dẫn ở "Tấn công" (game chặn X và Back), **không phải** gói trả phí như mô tả. Sửa chung: `ctx.popup_escape` — popup/bảng không đổi sau 3 lần X → Back, rồi xen kẽ Back / chạm **ra ngoài** popup (`ctx.OUTSIDE` mép trái 12,480). Không bao giờ chạm nút mua / giá / kim cương (chỉ X, Back, mép màn).
- (b) `runner.retry_after_recover`: cứu máy thành công khi bước lỗi/kẹt → chèn lại **đúng 1 lần** bước đó (không `observe`, không lặp vô hạn), log "THU LAI buoc".
- Khoảng trống: với popup hướng dẫn kiểu #5, cách thoát đúng có thể là **làm theo V** (bấm "Tấn công", có dự đoán "Thắng toàn diện") — chưa làm, cần chủ dự án quyết.

## Ảnh mẫu đã thêm (nguồn ADB 540×960 thật, trừ khi ghi khác)
| Ảnh mẫu | Nguồn |
|---|---|
| `rewards/vip/title_upgrade` | `logs/shots/20261124-181950-i0-vip_dot.png` (192,138–348,166) |
| `rewards/vip/btn_use_points` | cùng ảnh (410,401–494,432); khớp ảnh chủ `vip_tang_cap_dung_100.png` 0.93 |
| `rebels/npc_btn_search` | `live4/#3/auto/s193422.png` (190,714–346,762); khớp ảnh chủ 0.95 |
| `rebels/npc_max_text` | cùng ảnh (80,660–300,688) |
| `build/road_icon` | `live4/#0/auto/s181238.png` (145,150–181,186) |
| `build/road_icon@i3` | `live4/#3/auto/s191903.png` (86,290–122,326) |
| `build/road_confirm` | `live4/#3/auto/s193839.png` (300,668–422,694); khớp ảnh chủ 0.999 |
| `build/road_cancel` | cùng ảnh (140,680–215,712) |

Fixture test (gitignored, chỉ chạy local): `tests/fixtures/p12/*.png` (bản sao các khung trên). **Còn thiếu:** khung màn sau khi bấm "Dùng" điểm VIP; khung sau "Xác nhận" xây đường; khung popup gói trả phí thật bị kẹt (nếu có).

## Việc cần chủ dự án quyết định
1. Popup hướng dẫn chặn X/Back (#5 "Chiến dịch 1"): cho phép bot **làm theo mũi tên V** khi nút là "Tấn công" và dự đoán "Thắng toàn diện"?
2. Bảng Nhiệm vụ (`quests`): dòng "Kích sát phiến quân Lv.N" có nên bấm "Đến" và đánh lẻ như thanh nhiệm vụ chính?
3. Khiên: dùng vật phẩm 1h ngay sau Hiệp ước (đang chuẩn bị) — cần chạy thật để xem vật phẩm có hủy Hiệp ước không.
4. P10 learning: gia hạn bằng Hiệp ước chỉ khi khiên còn ≥ 60 phút — vẫn giữ.
