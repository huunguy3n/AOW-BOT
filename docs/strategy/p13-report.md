# Báo cáo P13 — tiến độ thật trong game (live-run-5 → sửa)

Nhánh `p7-live-fixes`, từ `74976cf` (P12). Không push, không chạy bot / LDPlayer / ADB. **1428 test pass** (P12: 1378; +50), `ruff`, `mypy`, `python main.py --check` xanh trước mỗi commit (xem "Sự cố gate" cuối báo cáo).

## Lưu ý trung thực
Tiêu chí P13 là **tiến độ thật** (nhà chính lên cấp, thợ xây bận, thao tác đúng luật), **không** phải "% bước không lỗi". Live5 báo 100 % bước không lỗi nhưng nhà chính #3/#4 cấp 5, #5/#6 cấp 4, 0 cấp/ngày. **P13 chưa chứng minh được nhà chính sẽ lên cấp** — không chạy máy thật nên mọi thứ dưới đây là sửa theo log + ảnh + test, chưa có kết quả trong game. Chủ chạy live6 rồi đo `hq_history` (nhà chính/ngày), không dùng tỉ lệ bước.

Chẩn đoán live5 (log `pm-live5-#N.txt`): nhà chính **có thấy** (0.87–0.99) và hay `started` (chuỗi `chain`), nhưng (1) #0 / #2 / #5 → `unreached` (`Nhay` → `jump_none_d2`, hoặc không thấy nhà chính ở #2), kèm lùi lịch 30 phút → 4 giờ; (2) cuối mỗi lượt `Tho xay: 0/2 dang xay` — thợ **rảnh lúc kết thúc lượt** ở cả 7 máy; (3) #3–#6 (HQ 4–5) `world_ready=false` nên mẹo "ra thế giới rồi vào lại" **chưa bao giờ chạy** ở các máy đang cần nhất.

## Từng mục

| Mục | Trạng thái | Commit | Kiểm chứng | Rủi ro còn lại |
|---|---|---|---|---|
| P13-1 Nhà chính | **LÀM MỘT PHẦN** | `644a8c6` | 5 test (`test_p13_hq_recenter`, `test_hqplan`); log live5 | Chưa biết có tăng cấp thật không (xem trên). Với HQ<6 mẹo thế giới là **thử 1 lần/6 giờ** (`goto("world", 3 vòng)`), nếu game thật sự khóa bản đồ thì vô dụng. Nguyên nhân `jump_none_d2` (Nhảy tới ô đất chưa xây) **chưa sửa tận gốc**, chỉ rút lùi lịch 30 phút→5 phút (trần 4 h→1 h) để thử lại nhanh sau `construct` |
| P13-2 Tốc độ | **LÀM MỘT PHẦN** | `2dc8d43` | 5 test; log #3 | `visit.py`: rewards (mail/vip/ally_gift) + mission không mở lại cái reddots vừa xử lý (ước tính ~1–1.5 phút/lượt từ log #3, **chưa đo**); `settle` 0.35→0.25 s, `skip_recheck_s` 3→6. `wait_scale 0.75 / wait_s 1.2 / adaptive_wait` **đã có từ trước**, không đổi. Khối lớn nhất (`generic @526,172 làm 18` = 87 s; activity 58 s; screencap ~25 % thời gian) **chưa đụng** |
| P13-3 Chấm đỏ | **XONG** | `33ad61c` | 5 test; `pick` chỉ `(y//30, x)`, `KIND_PRIO` xóa; `defer_to_steps` mặc định tắt | `reddots` đặt **ngay sau Liên minh** (giữ mỏ liên minh gửi sớm), trước notify/rewards/mission/play/intel. `notify.run` đầu vòng vẫn xử lý icon notify trước (chưa theo thứ tự vị trí). Rewards/mission/play/intel vẫn là bước riêng cho việc không có chấm đỏ |
| P13-4 Khiên | **XONG** (huy hiệu: LÀM MỘT PHẦN) | `9140c01` | 10 test; ảnh chủ | Ngày thường: **chỉ** Hiệp ước 8h miễn phí; không item, không kim cương, không gia hạn bằng item; bị tấn công ngày thường cũng chỉ Hiệp ước (nút "Bật khiên" tay trên web cũng vậy). Thứ 7: chỉ chạy khi thấy huy hiệu. **Vị trí huy hiệu `BADGE_ROI (196,60,44,40)` ước lượng từ ảnh điện thoại, chưa kiểm trên ảnh ADB** (chưa có khung thứ 7 thật); phát hiện bằng màu vàng, test dùng ảnh chủ dán vào canvas. Nếu ROI lệch → thứ 7 **không bật khiên** (an toàn nhưng hở); `warday.mode: on` trên web vẫn ép bật |
| P13-5 Tình báo | **XONG** | `e1e7101` | 2 test | SKIP / mất tiêu đề → `close_popups`, không `ensure_city`; về thành phố tối đa 1 lần; `intel.run` về city 1 lần cuối |
| P13-6 Cướp xe 2/2 | **XONG** | `df87304` | 3 test; fixture `loot_world_i1.png` đọc đúng 2/2 | OCR ROI `(255,522,135,32)` kiểm trên 1 ảnh; không đọc được → **bỏ xe** (an toàn nhưng có thể bỏ nhầm); chưa thấy ảnh ADB 1/2 hay 0/2 thật |
| P13-7 Dưỡng Tướng | **XONG** | `288b738` | 4 test; ảnh chủ: 5/5 ô khóa bị loại | Dò ổ khóa trắng góc ô (14×14 px); chưa chạy trên ADB thật. Luồng không có Cấp mua/Mở khóa/Nhận điểm |
| P13-8 Tướng Có thể đổi | **XONG** (chưa thử thật) | `a6eb656` | 3 test; `full_shard_cards` ra (80,166) đúng thẻ 11/10 | Luồng `unlock_heroes` đã có, **thiếu ảnh mẫu `hero/btn_exchange`** nên trước đây chỉ lưu ảnh; nay có (cắt từ ảnh chủ, khớp 1.0). Chưa thử nhấn thật |
| P13-9 Chiến Khu mạnh nhất | **XONG** (chưa thử thật) | `5885ab7` | 4 test; ảnh chủ: 3 rương 6M/12M/24M, rương xám bỏ | Nhận tab bằng OCR tiêu đề lỏng ("khu"), dễ trượt → khi trượt thì dùng đường chung cũ |
| P13-10 Chiến dịch | **LÀM MỘT PHẦN** | `e5b72a4` | 6 test | (a) nút thoát/bỏ qua trận `Lượt n/25`; (b) "Tiếp tục Chiến dịch" thay "Trở lại" (+ steer nhận màn Thắng lợi); (c) cổng đỏ -1..-3 chưa đo tốc độ → giả định bắn 1/giây rồi lao vào khi dương. **3 ảnh mẫu cắt từ ảnh điện thoại, không có bản ADB** → ngưỡng khớp có thể trượt. **Chưa biết** nút thoát có hộp xác nhận / có tính thua không. Cổng đỏ lớn hơn -3 vẫn dùng luật P7-8 (cần đo tốc độ thật) — chưa kiểm tra có "dùng buff đỏ" hiệu quả không |
| P13-11 Mở rộng thành phố | **LÀM MỘT PHẦN** | `61b8491` | 6 test; mẫu `plot_unlock` khớp ảnh chủ 1.0 | Bước mới `expand`: lướt vòng quanh thành phố (xấp xỉ "kéo dọc viền sáng") tìm ổ khóa mở; dòng NV "mở rộng" (thanh + bảng) → chạy ngay. **Chưa biết hộp thoại sau khi bấm icon trông thế nào** — chỉ bấm nút "Đến/Nhảy/Mở rộng/Xây dựng" (không giá, không kim cương), không có thì đóng + lưu ảnh `logs/inv/plot_unlock_dialog` |
| P13-12 Phản quân HQ<15 | **XONG** (lựa chọn tạm) | `3cd87eb` | 6 test | Đánh lẻ từ nhiệm vụ chỉ giữ nếu thành công; thất bại → lùi 2 h gấp đôi tới 24 h. HQ<15 vẫn không tham gia/tự mở tập kết Cơ giáp. Live5: `npc_none` mỗi lượt (~15 s) ở #2/#3/#4/#6 |
| P13-13 Nhỏ | **XONG** | `ad56e38` (+ mẫu ở `a6eb656`) | 3 test | Screencap: sau dò lại địa chỉ thử đúng 1 lần timeout gấp đôi (≤12 s) rồi mới `dead` |
| P13-14 Kiểm tra + báo cáo | XONG | (commit này) | | |

## Ảnh mẫu thêm (tất cả cắt từ **ảnh điện thoại của chủ** — không có bản ADB tương ứng)
`hero/btn_exchange`, `build/plot_unlock` (khớp 1.0), `campaign/btn_continue`, `campaign/btn_back_victory`, `campaign/btn_skip_battle`. Còn thiếu / cần ảnh ADB 540×960 thật: huy hiệu "cần khiên" thứ 7, hộp thoại sau icon ổ khóa mở, hộp thoại sau nút thoát trận, cổng đỏ "+N" sau khi bắn, ảnh xe 1/2 và 0/2 trên ADB.

## Việc chủ cần quyết
1. Đánh lẻ phiến quân từ nhiệm vụ khi HQ<15: giữ cơ chế "thành công thì giữ, thất bại lùi 2–24 h" hay tắt hẳn?
2. Nút "Bật khiên" tay trên web giờ chỉ dùng Hiệp ước miễn phí ngày thường (không item). Có muốn nút này được ngoại lệ không?
3. Thứ 7 chỉ bật khiên khi thấy huy hiệu — chấp nhận rủi ro hở nếu ROI lệch, hay giữ thêm cờ `warday.require_badge: false` cho tới khi kiểm bằng ảnh ADB thứ 7?
4. Cho phép chạy live6 trên **#3 hoặc #4** để đo `hq_history` (nhà chính/ngày) — tiêu chí nghiệm thu thật.

## Sự cố gate (nêu rõ)
Hai commit (P13-4 lần đầu, P13-6 lần đầu) bị commit khi `ruff`/`pytest` còn lỗi vì script gate của tôi nuốt mã thoát; đã `--amend` sửa trước khi làm tiếp, commit cuối cùng đều qua đủ gate (`GATE OK`).
