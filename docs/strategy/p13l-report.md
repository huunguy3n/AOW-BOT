# P13l — Tình báo, bổ sung tài nguyên, mũi tên xanh, lớp ghim khi thua, chặn căn cứ người chơi

Ngày 27/11/2026. Yêu cầu chủ dự án t98u–t105u. **Chưa chạy bot sống**: mọi kết luận dưới đây kiểm trên ảnh đã lưu và test offline.

## 1. Khẩn cấp: bấm vào căn cứ người chơi (t104u, t105u)

**Nguyên nhân.** Sau "Đi", Tình báo bấm các điểm cố định giữa bản đồ (268,405), (268,438), (265,365) mà không nhìn xem ở đó là gì. Ảnh log thật 26/11 #1 (`intel_unknown_target`, lưu làm fixture `world_city_menu_adb.png`) đang mở đúng menu căn cứ `(LSS)MF006` có nút "Tấn công". Bước nhiệm vụ chính cũng bấm mù `TARGET` (272,445), mũi tên xanh bấm cố định dưới mũi tên 95 px.

**Sửa.**

| Lớp | Nội dung |
|---|---|
| Nhận menu (`bot/map_menu.py`) | ≥ 2 trong 4 nút tròn Trinh sát / Tập kết / Tin tức / Tấn công gần nhau → `city`; có "Chuyển thành" + "Chiếm lĩnh" → `land`; có nút "Thu thập" → không tính |
| Hàng rào `Ctx` | Mọi `tap` / `tap_tpl` / `tap_first`: menu đang hiện → **không bấm điểm nào**, đóng ngay. 3 khung chụp sau mỗi cú chạm cũng được kiểm; `close_popups` đóng menu |
| Cách đóng | Phím Back (tối đa 2 lần, hộp thoại thoát → Hủy), còn nữa thì nút "Thành phố". Không bấm 4 nút trên menu |
| Danh sách đen | Điểm vừa mở menu bị cấm hết lượt ghé (`tapguard` phạm vi `world`) |
| Tránh từ trước | `world_target.city_near`: cờ quốc gia cạnh biển tên, mái khiên, thẻ liên minh `(XXX)` (OCR). Áp cho điểm Tình báo, mũi tên xanh, mục tiêu giữa màn của nhiệm vụ chính |
| Log | `tap trung can cu nguoi choi -> dong` |

"Tấn công" dạng nút chữ nhật (phiến quân, Tình báo, chiến dịch) không khớp mẫu nút tròn nên vẫn bấm được. Luồng cướp xe không dùng menu này.

## 2. Mũi tên xanh (t100u–t102u)

**Nguyên nhân.** `find_green_chevron` xóa 110 px trên (mũi tên ở y ≈ 100 bị mất) và trả điểm bấm `y + h + 95` cố định → trúng đất trống, mở menu "Chuyển thành / Chiếm lĩnh". `_follow_known` thoát bản đồ thế giới "để bước khác làm".

**Sửa.** `bot/world_target.py` tìm vật thật dưới mũi tên theo thứ tự: nhãn "Phiến quân" / "Cơ giáp" → thanh máu đỏ → khối khác nền cỏ (chỉ khi chắc ở bản đồ thế giới). `bot/modules/arrow.py` làm tại chỗ:

| Bảng hiện ra | Xử lý |
|---|---|
| Phản quân Cơ giáp | Luồng `rebels`; nhà chính < 15 hoặc hết quân đoàn → đóng, bỏ |
| Phiến quân / "Tìm kiếm" | `mainquest.npc_engage` (kiểm cấp, lực chiến); thể lực chỉ "Dùng"; màn quân đoàn kiểu mới chỉ đi khi dự đoán thắng |
| "Thu thập" | `gather.run(limit=1)`: cấp 8 → 7 → 6, không hai quân một mỏ |
| Menu | Đóng, danh sách đen, thử vật kế; tối đa 3 lần |

**Tọa độ trên `arrow_miss_world.png` (340×314):** mũi tên (155, 117); **điểm bấm (127, 201)**, loại `unit`, nằm trong thân con cơ giáp (x 82–175, y 155–265); ngoài ô đỏ đất trống (145–185, 118–158) và cách hai nút (50,153), (260,153) hơn 40 px.

## 3. Thua Tình báo → bỏ đúng lớp ghim (t103u)

**Nguyên nhân.** Log 26/11: #3 thua 14 trận trong 12 lần ghé, #4 thua 10. Bản sửa dở lượt trước chặn **mọi** trận đội hình sau một lần thua.

**Sửa.** `bot/intel_pins.py` phân loại = biểu tượng (mặt nạ điểm trắng, `templates/intel/pin_icon_*`) + màu (hue vòng thân ghim). Thua → nhớ `{lớp: {power, at}}` theo máy (fact `intel_lost_classes`). Bỏ qua lớp đó, vẫn đánh lớp khác. Thử lại khi lực chiến ≥ lúc thua + `notify.intel_lose_power_pct` (5 %). Thắng lớp đó → quên. Không đọc được lực chiến lúc thua → lấy số đọc được đầu tiên làm mốc; không bao giờ đọc được → quên sau `notify.intel_lose_h` (24) giờ. Log: `Tinh bao: bo qua <lop> (thua luc chien X, nay Y)`.

**Ghim nhận ra trên `intel_icons_types.png` (423×455), 9/9:**

| Tâm đầu ghim | Lớp | Ghim trong yêu cầu |
|---|---|---|
| (104, 121) | `guns-purple` | súng chéo tím trên-trái |
| (57, 185) | `guns-purple` | súng chéo tím giữa-trái |
| (134, 215) | `guns-blue` | súng chéo xanh dương |
| (347, 198) | `guns-green` | súng chéo xanh lá |
| (244, 272) | `skull-green` | đầu lâu xanh lá |
| (278, 314) | `skull-purple` | đầu lâu tím |
| (346, 94) | `badge-gold` | huy hiệu đầu lâu vàng |
| (152, 185) | `crate-gold` | hòm cam/nâu |
| (172, 303) | `crate-grey` | hòm xám có tick |

Giới hạn: ghim không in số cấp nên lớp **không gồm cấp**. Hòm cam bị ghim khác che vòng chân (`intel/pin_base`) nên phân loại được nhưng chưa được chọn để bấm (như trước).

## 4. Bổ sung tài nguyên (t99u)

`bot/resources.py`, nối vào huấn luyện, nâng cấp (cả nhà chính), xây mới, nghiên cứu:

1. Popup "Thiếu tài nguyên" → chỉ nút **trái** "Dùng đạo cụ" (xanh đậm, không có icon kim cương).
2. Màn "Bổ sung tài nguyên" → nút "Dùng" trên cùng (gói nhỏ nhất còn hàng) → hộp số lượng giữ số điền sẵn → "Dùng".
3. "Lưu trữ" tăng (đọc số, không đọc được thì ô phải đổi) → mũi tên Quay lại → làm lại thao tác; còn thiếu thì lặp, tối đa `resources.max_per_action` (4) gói / thao tác, `max_per_visit` (20) / lượt ghé.
4. Hết gói miễn phí → đóng, bỏ qua (sau 3 lần mở mà trống thì thôi mở cả lượt).

`Ctx` chặn mọi cú chạm vào nửa phải hàng nút của popup và vào nút teal giá kim cương ở màn bổ sung. Mọi "Dùng đạo cụ" + kim cương vẫn cấm.

## 5. Lịch Tình báo và phần còn lại

- Nguyên nhân: Tình báo là bước chạy kèm, chu kỳ 180 phút nhân 2/4 khi trắng tay; log gộp "bước tắt" với "bước không nằm trong lượt".
- Nhà chính < `schedule.intel_priority_hq` (15) hoặc chưa biết cấp: Tình báo vào **mọi** lượt ghé, chạy sớm (sau bước xây nếu thợ rảnh); không giãn chu kỳ khi trả 0. Log tách hai loại.
- Nút "Đi" / "Nhặt" xám → `locked`, đóng, không bấm "Đến". Hết thể lực: bảng thuốc chỉ "Dùng"; hết thuốc → dừng vòng ghim. Hết quân đoàn → dừng cả lượt.
- Ghim mờ bỏ qua; ghim bấm hụt / khóa không chọn lại trong lượt. Ô đỏ địch trong thành sau "Đi" được bấm (`guide_tile.find_enemy`).
- Chiến dịch Tướng: nút "Chiến đấu" hiện trễ vẫn phải qua kiểm dự đoán thắng.
- OCR cấp hỏng không còn bỏ phiến quân thường (vẫn chỉ xuất chinh khi dự đoán thắng).
- **Đổi mặc định cần chủ dự án xác nhận:** `rebels.intel_rally_min_hq` 0 → **15** theo câu "HQ<15 chỉ bỏ rally cơ giáp" (trước đó ghim Cơ giáp Tình báo được tự mở tập kết ở mọi cấp). Muốn như cũ: đặt 0.

## 6. Luật an toàn (tóm tắt)

- Không bao giờ bấm Trinh sát / Tấn công / Tập kết / Tin tức trên menu căn cứ người chơi.
- Không bao giờ "Chuyển thành" / "Chiếm lĩnh" trên ô trống.
- Không bao giờ nút kim cương, "Mua", "Đến" mua gói.
- Không đụng IMEI / model, không ghi dữ liệu app.

## 7. Kiểm tra

- `pytest`: 1589 qua, 197 bỏ qua (thiếu ảnh chỉ có ở máy chạy thật).
- `ruff check .` và bộ luật mã cũ: sạch. `mypy`: sạch. `lint-imports`: 8/8.
- `main.py --check`: thiếu 15/273 (trước 16/264).
- Test mới: `tests/legacy/test_p13l_{intel,resources,world}.py`, ảnh ở `tests/fixtures/p13l/`.

## 8. Chưa kiểm / rủi ro

- Mẫu nút menu, nhãn "Phiến quân", biểu tượng ghim cắt từ ảnh chủ dự án; menu căn cứ đã khớp thêm 1 khung ADB thật, menu đất trống khớp 4 khung ADB thật. Phần còn lại cần xem log lần chạy đầu.
- Phát hiện cờ chỉ theo cờ đỏ sao vàng; cờ nước khác dựa vào mái khiên, thẻ liên minh và hàng rào menu.
- Menu có Trinh sát + Tấn công ở mỏ / cứ điểm của người khác cũng bị đóng (cố ý, an toàn).
- Mỗi cú chạm tốn thêm khoảng 50 ms cho hai hàng rào.
- Hai luồng thao tác trong `arrow.py` (đánh phiến quân, thu thập tại chỗ) mới kiểm bằng máy giả.
