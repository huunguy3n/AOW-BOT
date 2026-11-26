# P13f — số thợ đúng theo máy, xây tiếp ngay trong lượt, chuyển tiếp nhanh hơn

Yêu cầu chủ dự án (t90u, 26/11/2026 08:37). Nhánh `p13f` từ `2aaf70e`. **Chưa chạy trên máy thật**: kiểm bằng test, mô phỏng và ảnh / log đã lưu (chỉ đọc).

## 1. Số thợ (sửa P13e-1)

- Nguyên nhân: P13e lấy `y` trong "x/y" làm số thợ dùng được. Game báo tổng 2 cả khi ô thứ 2 chưa mua.
- Nay: số thợ = `build.max_builders` theo máy (config 1; #1 = 2 đã có trong `data/settings.json` của cây chính). `y` chỉ để kẹp xuống. Bỏ `use_game_slots`, `max_builders_cap`.
- Farm 1/2 = đầy: `construct`, dòng xây của `quests` / `mainquest` và `upgrade` không bấm gì. Không có mã mua / thuê thợ.

## 2. Nhà xong thì xây tiếp ngay

Nguyên nhân (log 26/11, #3 #4 #5):

- `should_quick_wait` được gọi với `busy_total=None` nên cứ còn bước khác là "lam truoc, quay lai xay sau".
- `_fill_builders` chỉ chạy trước `observe`, và chỉ gồm các bước có trong lượt lịch.
- "Nhường thợ cho nhà chính" bỏ `construct` / `quests` cả khi thợ rảnh.

Sửa:

- `quick_wait` đọc số thợ thật; còn rảnh thì xây tiếp (`upgrade` nối chuỗi, tối đa `build.chain_max` 6).
- Runner đọc hàng chờ xây **sau mỗi bước** (trừ `warday` / `tutorial` / `shield` đầu lượt) và sau phần nhận quà cuối lượt. Thợ rảnh → `upgrade`, `construct`, `mainquest`, `quests` chạy trước bước kế, kể cả bước không nằm trong lượt lịch. Thợ đầy giữa chừng → hàng đợi trở về thứ tự cũ.
- Chống lặp: lần chèn không xây được gì thì chỉ thử lại khi thêm thợ vừa xong, hoặc (tối đa `fill_retries` 2) vừa nhận thêm tài nguyên. Trần `fill_rounds` 8 lần / lượt.
- Chỉ nhường thợ khi mọi thợ dùng được đang bận.
- Nhà chính không làm được ngay (thiếu điều kiện / tài nguyên / đang xây / đã cấp 30) → nâng nhà tài nguyên theo ảnh mẫu `templates/build/res_food.png`, `res_tower.png`. Không nâng được gì → 30 phút sau mới tìm lại.
- Đọc số thợ bằng ảnh chữ số (`queues.read_count`) trước, OCR vùng cố định sau. 18/18 ảnh thành phố đã lưu đọc ra số hợp lý.

Giới hạn cần biết:

- Không tìm thấy màn danh sách nâng cấp / "Đề xuất" nào có ảnh mẫu, nên đường dự phòng chỉ có 2 loại nhà. Ngưỡng 0,66 kiểm trên 253 ảnh đã lưu (đúng nhà ≥ 0,69, chỗ khác ≤ 0,59); **việc chạm và nâng trên máy thật chưa thử**.
- Không còn giữ thợ / tài nguyên cho nhà chính khi thợ rảnh, nên nhà khác có thể dùng tài nguyên nhà chính đang chờ.

## 3. Chuyển tiếp

Nguyên nhân chính: chụp thừa (mỗi lần ~0,28 s, chiếm khoảng 1/3 thời gian lượt theo bảng `perf`) và vài chỗ ngủ cố định.

| Thao tác (mô phỏng `python tools/bench_transitions.py`, trung vị 41 lần) | Trước (s) | Sau (s) |
|---|---|---|
| `ensure_city` khi đang ở thành phố | 0,85 | 0,28 |
| `ensure_city` từ một bảng | 1,81 | 1,25 |
| `back_out` bằng nút "<" | 1,47 | 1,19 |
| `back_out` bằng phím Back | 3,26 | 2,61 |
| `back_out` khi đang ở thành phố | 0,28 | 0,28 |
| Chờ popup lúc vào game, không có popup | 4,13 | 2,49 |
| Hai popup nối tiếp lúc vào game | 10,08 | 6,04 |
| **Trung vị 7 loại thao tác (không tính theo tần suất)** | **1,81** | **1,25** |

Mô phỏng không tính chi phí khớp ảnh; số lần chạm cũ và mới bằng nhau.

Khác: bước không chạm gì thì không kiểm hướng dẫn game (47/229 lần hôm nay, mỗi lần ~1,5 s); lần chạm nhà chính kế tiếp trong cùng chuỗi không ra thế giới lại nếu nhà chính còn giữa màn (lần đầu vẫn ra / vào như luật cũ).

Giữ nguyên: chờ sau chạm (`_after_tap` đã chờ theo màn; dưới 0,5 s thì poll còn chậm hơn ngủ), `wait_for`, `_wait_game`, các lần chờ xây / thu thập. Đánh đổi: popup hiện muộn hơn 1,5 s sau khi thành phố đã yên không còn được `close_popups` lúc vào game bắt; lần `ensure_city` kế tiếp đóng nó.

### Thời gian mỗi lượt (ước lượng)

- Mốc "trước": trung vị **548 s** (log 26/11 sau 07:00, bỏ lượt 0 bước). Đo theo cách khác trên 6 lượt đầy đủ (dòng `Instance` → dòng `G3`) ra 1 085 s; `ensure_city` trung vị 2,28 s / lần.
- Tiết kiệm ước tính: `ensure_city` 36–50 lần × 0,57 s ≈ 21–29 s; popup lúc vào game 2–4 s; Back / nút "<" ≈ 4 s; hướng dẫn game ≈ 2 s → **khoảng 29–39 s / lượt**.
- "Sau" ước tính: **≈ 510–520 s** (giảm khoảng 6 %); `ensure_city` ≈ 1,7 s / lần.
- Chưa tính: đọc thợ sau mỗi bước (thêm tối đa vài giây / lượt) và **thời gian xây thêm** khi thợ rảnh (mỗi lần chèn cỡ 30–90 s). Lượt có nhà vừa xong có thể dài hơn trước; đó là việc xây được yêu cầu.

## Kiểm tra

`python -m pytest -q`: 1454 pass, 84 skip (thiếu ảnh chỉ có ở cây chính). `ruff`, `mypy`: sạch. `main.py --check`: còn 16 ảnh mẫu thiếu sẵn có.

Worktree mới không có `data/owner-feedback` (gitignore) nên 3 test `p13b_cham_do` hỏng cho tới khi chép thư mục đó (và `data/pm-shots`) từ cây chính.

## Khi chạy thật cần xem

- `Tho ranh sau buoc ...: xay NGAY` xuất hiện sau công trình ngắn; không còn "lam truoc, quay lai xay sau" lúc thợ rảnh.
- Farm: `Tho xay: 1/2 dang xay (dung toi da 1)` và không có "Het tho xay ranh" / bảng thuê thợ.
- `Nang nha khac: nha tai nguyen @x,y (...) -> ...`: kiểm chạm đúng nhà.
