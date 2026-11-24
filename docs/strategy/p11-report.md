# P11 — Nhận quà liên minh lặp đến hết (2026-11-24)

Góp ý chủ dự án (t52u): *"Nhận quà liên minh có rất nhiều, nhưng hệ thống chụp và nhận đúng số lượng trên 1 trang mà không nhìn lại số lượng thực tế. Thực tế quà phát sinh liên tục."*

## Nguyên nhân (live-run-3, máy #1)

- Bot coi **"Có thể nhận:243"** là số quà đang chờ. Thực ra đó là **trần nhận trong ngày**: sau "Nhận toàn bộ" 43 quà, số này còn 200 và nút biến mất ("Chưa có quà", s153334). Vòng cũ vì thế dừng sau đúng một lần nhận.
- Số quà đang chờ thật nằm ở **chấm đỏ có số trên mỗi tab** (s152956: Quà đặc biệt 8, Quà thường 43; s153326: còn 2).
- Tab Quà đặc biệt chỉ được nhận một lần cho các món đang thấy trên trang, không mở lại để đọc số. Quà mới đến sau đó (cuối lượt s155258 vẫn còn badge Liên minh 26) không được nhận.

## Đã sửa

`bot/modules/alliance.py`:

| Hàm | Làm gì |
|---|---|
| `gift_loop(ctx)` | Vòng P11 chạy trên cả hai tab: Rương Lv (có chấm đỏ) → mỗi tab: mở tab và làm mới → đọc số → nhận → làm mới (chuyển tab đi rồi về) → đọc lại → log `Qua lien minh <tab> vong N: con A -> B (<cách>, nhan k)`. Vòng lặp chỉ dừng khi cả hai tab đã rỗng **và** ảnh mới không còn chấm đỏ trên tab nào. Có trần `alliance.gift_loop_rounds` (30) vòng hoặc `gift_loop_max_s` (180) giây; khi chạm trần, bot log còn bao nhiêu quà mỗi tab rồi thoát. |
| `gift_panel` | Mọi đường vào đều gọi `gift_loop`: icon quà trên thành phố (`gifts`), `reddots` (`_handle('ally_gift')`), `rewards.ally_gift_until_clear`, ô Liên minh (`gifts_tile`). Nhánh "nhận một trang rồi thôi" đã bị xóa. |
| `gift_count(img, tab)` (thuần) | Số quà chờ. Bằng 0 khi tab hiện "Chưa có quà" hoặc không có nút và không có chấm đỏ. Đọc được số đỏ thì lấy max(số đỏ, số nút đang thấy). Không đọc được thì lấy số nút. Có chấm đỏ mà chưa thấy nút thì trả `None`. |
| `active_tab`, `tab_dot`, `badge_number`, `list_buttons`, `gift_empty`, `show_tab`, `claim_all_once`, `claim_tab`, `gift_progress` | Tab đang chọn (màu nền); chấm đỏ trên tab; số trong chấm đỏ (OCR 5 cách, chỉ nhận khi ≥ 2 cách trùng nhau); đếm nút xanh trong cột "Nhận"; nhận diện "Chưa có quà"; làm mới tab; "Nhận toàn bộ" chỉ trong vùng đáy bảng `CLAIM_ALL_ROI` và chỉ tính khi màn hình đổi; ưu tiên "Nhận toàn bộ", không có thì "Nhận" từng món (`special_claim(claim_all=False)`). |
| Chống kẹt | Một tab mà số không giảm **và** không nhận được gì trong `gift_stall_rounds` (2) vòng liền → lưu ảnh `logs/shots/*-ally_gift_stall_<tab>.png`, log cảnh báo, bỏ tab đó. Nếu chấm đỏ vẫn hiện nhưng danh sách rỗng 2 vòng liền thì coi là badge cũ và dừng. |
| "Có thể nhận: 0" | Bỏ tab Quà thường (hết lượt trong ngày); tab Quà đặc biệt vẫn nhận. |
| An toàn | Bot chỉ chạm vào: 2 tab, nút xanh có chữ "Nhận" trong cột phải (`GIFT_LIST_ROI`, y < 840, lọc chữ trả phí bằng `buttons.with_text`), ảnh mẫu "Nhận toàn bộ" trong vùng đáy. Không bao giờ bấm "Gửi Quà Thường", "Tặng quà ẩn danh" (~30,928, ngoài mọi vùng chạm) hay gói trả phí. |

`config.yaml` → `alliance`: bỏ `gift_rounds` và thêm `gift_loop_rounds: 30`, `gift_loop_max_s: 180`, `gift_stall_rounds: 2`. CLAUDE.md (dòng `alliance`) đã cập nhật.

## Test

- Thêm `tests/legacy/test_p11_ally_gift_loop.py` (21 test):
  - Hàm thuần chạy trên khung live3 thật (540×960). Gồm: s152956 (tab thường 43, "Nhận toàn bộ"), s153301 / s153309 / s153326 (Quà đặc biệt, danh sách co dần 8 → 5 → 2), s153334 ("Chưa có quà", "Có thể nhận" 200 vẫn > 0). Test tự bỏ qua khi thiếu ảnh hoặc thiếu Tesseract.
  - Mô phỏng bảng quà có quà phát sinh thêm giữa các vòng: bot vẫn lặp tiếp, dừng khi rỗng, dừng ở trần vòng, dừng ở trần thời gian, dừng khi số không giảm (có ảnh debug), bỏ tab thường khi "Có thể nhận: 0", không chạm vùng gửi quà / ẩn danh, và mọi đường vào đều gọi `gift_loop`.
- Bỏ 2 test P7 cũ (`test_gift_panel_repeats_claim_all_until_zero`, `test_gift_panel_skips_normal_when_zero`). Chúng kiểm hành vi cũ dựa vào "Có thể nhận" mà P11 thay thế.
- Kết quả: `pytest` **1324 pass** (trước 1305); `ruff check .` sạch; `mypy` sạch; `python main.py --check` OK.

## Ảnh mẫu

- Không thêm ảnh mẫu mới. Phần nhận diện mới dùng màu (tab, chấm đỏ, nút xanh) và OCR. Ảnh mẫu dùng lại: `ally/gift_title`, `ally/btn_gift_claim_all` (nay giới hạn trong vùng đáy bảng).
- Tọa độ và ROI đo trên khung ADB 540×960 `data/pm-shots/owner-20261124/live3/auto/` gồm s152939, s152956, s153301, s153309, s153317, s153326, s153334.

## Khoảng trống còn lại

- **Chưa chạy thật trên máy.** Cần một lượt live trên #1 để xác nhận: chuyển tab có tải lại danh sách không, và badge Liên minh về 0 cuối lượt.
- OCR số trong chấm đỏ còn yếu (s153309: số 5 có cách đọc ra "3"). Hiện bot chỉ nhận số khi ≥ 2 cách đọc trùng nhau, nếu không thì dùng số nút đang thấy. Số đọc chỉ dùng để log và phát hiện tiến triển. Quyết định dừng dựa vào "Chưa có quà" / không còn nút / không còn chấm đỏ, nên OCR sai chỉ làm log lệch, không làm bỏ sót quà. Nếu cần số chính xác: cắt ảnh chữ số trắng trên nền đỏ (như `templates/qdigits` của P2).
- Rương Lv chỉ được kiểm ở đầu và cuối `gift_loop`, chưa kiểm mỗi vòng.
- Trần 180 s tính cho một lần mở bảng. `rewards.ally_gift_until_clear` có thể mở lại bảng tối đa `rewards.repeat_rounds` (4) lần khi icon thành phố vẫn còn số đỏ.
