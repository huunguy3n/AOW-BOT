# P13k — Popup "Mở khóa Binh chủng này" (26/11/2026)

Nhánh `p13k`, tách từ `p7-live-fixes` @ bd4de37. Chỉ kiểm bằng ảnh chủ gửi và test, **chưa chạy trên máy thật**.

## 1. Trước khi sửa (đo trên ảnh chủ)

- Thanh nút dưới vẫn lộ ra, `common/btn_to_world` khớp 0,9999: bot coi là đang ở thành phố, không đóng gì.
- `tutorial.decide` (dùng cả khi "làm theo hướng dẫn") trả "ô đỏ dưới chân mục tiêu" và chạm (246,198) ở bản cắt
  540 px, tức vào tiêu đề.
- Mẫu `intel/btn_go` khớp nút **"Đến"** 0,92: bước Tình báo có thể đã bấm "Đến".
- `common/btn_confirm` khớp nút "Xác nhận" 0,87, sát ngưỡng 0,82 hơn mẫu riêng.

## 2. Cách nhận (`bot/unlock_popup.py`)

Cần **cả hai**:

- nút "Xác nhận": mẫu mới `templates/common/btn_confirm_unlock.png`, chỉ tìm ở nửa phải (x ≥ 270, y 660–860), ≥ 0,85;
- tiêu đề: mẫu mới `templates/common/unlock_troop_title.png` là **mặt nạ chữ vàng** (nền sau chữ là thành phố đang
  sống nên không so ảnh màu), ≥ 0,7. Đo: ảnh chủ 0,97; ba ảnh P13i/P13j ≤ 0,09. Khi cắt mẫu đã xóa vệt sáng của nền
  giữa "Binh" và "chủng". Không lấy khung đỏ khoanh tay.

Nếu thấy nút Hủy của hộp "Rời trò chơi?" thì coi như không phải popup này. Không dùng OCR.

## 3. Chỗ gắn

`close_popups` (cả lúc chờ popup kế tiếp), `screens.identify` → `goto` / `ensure_city`, `back_out` (trước `is_home`),
`skip_dialogs`, `dismiss_reward`, `tutorial.decide` + `tutorial.run`. `common/btn_confirm` **không** được thêm vào
`POPUP_CLOSERS`.

- Trước mỗi lần bấm "Xác nhận" đều gọi `cancel_exit`.
- Sau khi bấm, chụp lại. Còn popup thì bấm thêm 1 lần; 2 lần không đóng → `TapGuard` đưa tọa độ vào danh sách đen,
  lưu ảnh `unlock_troop_stuck`. `goto` trả False, không bấm Back, không chạm ra ngoài.
- Chặn "Đến": `Ctx.tap`, `tap_tpl`, `tap_first` rơi vào vùng x 40–265, y 690–815 khi popup đang hiện → không chạm,
  đóng popup bằng "Xác nhận".

## 4. Test

`tests/legacy/test_p13k_unlock_popup.py`: 37 test, dùng ảnh chủ (`tests/fixtures/p13k/`, thêm bằng `git add -f`).
Ảnh chỉ khoanh đỏ tiêu đề và nút "Xác nhận", **không** khoanh "Đến"; vùng "Đến" trong test là tọa độ đo trên ảnh
(x 78–227, y 721–781). Không có ảnh thật của hộp "Rời trò chơi?" trong git nên test dán mẫu nút Hủy lên khung dựng.

| Cổng | Kết quả |
|---|---|
| `pytest` trong worktree | 1528 pass, 197 skip, **3 fail** ở `test_p13b_cham_do_khong_doi.py` |
| 3 test đó khi chép tạm ảnh chúng cần từ cây chính (chỉ đọc, đã xóa bản chép) | file chạy 7/7 pass |
| `ruff` (cả hai lệnh), `mypy`, `lint-imports` | sạch |
| `main.py --check` | thiếu 16/264 ảnh mẫu (16 ảnh thiếu từ trước, 2 mẫu mới đã có) |

Ba test fail vì cần `data/owner-feedback/p13/quan_quan_tuan_bam_sai.png`, không có trong git.

## 5. Chưa làm / chưa chắc

- Chưa chạy live. Mẫu cắt từ ảnh chụp 543×957 của chủ (lệch khung vài px; test lệch tới 6 px vẫn nhận), chưa đối
  chiếu với khung ADB thật của popup này.
- Chỉ có một ảnh (bậc 2). Popup mở khóa bậc khác dự kiến cùng tiêu đề và nút; popup mở khóa thứ khác (tiêu đề khác)
  không được nhận.
- Chặn "Đến" chỉ ở ba hàm chạm của `Ctx`. Các chỗ gọi thẳng `dev.tap` (nút "Nhận" trong `claim_buttons`, bong bóng
  tài nguyên, +/- cấp mỏ) và các thao tác vuốt không đi qua chốt này.
- Popup kẹt thì tọa độ bị cấm đến hết lượt ghé: runner khởi động lại game theo luật cứu kẹt có sẵn; nếu popup hiện lại
  trong cùng lượt thì bot không bấm nữa.
- Nếu từ 3 popup mở khóa hiện nối tiếp nhau, hai lần bấm đầu xong vẫn còn popup nên bị tính là "không đóng": cái
  thứ ba không được bấm trong lượt ghé đó.
