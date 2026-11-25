# P13d — báo cáo (nhánh p13d, 2026-11-26)

Làm trên worktree `E:\AOW-BOT-p13d`. **Không chạy live, không mở LDPlayer/ADB**; mọi thứ dưới đây chỉ kiểm bằng test offline + ảnh chủ dự án gửi. Việc nào chưa được chứng minh trên máy thật được ghi rõ.

## P13d-1 Chấm đỏ (`bot/modules/reddots.py`, `bot/runner.py`)
- Trí nhớ "vô ích" gắn với **lần ghé** (`ctx.visit`, fact `reddots_dead_visit`); sang lần ghé mới thì bỏ. Vị trí đã nhận được thì xóa khỏi trí nhớ.
- Loại **bảo vệ** `PROTECTED` (liên minh, tình báo, chiến dịch, quà liên minh, thư, "Nhận", xây): không bị `already_idle`, `stepgate`, trí nhớ vô ích chặn; mỗi lần quét mở ít nhất một lần.
- Trần mỗi chấm `reddots.dot_max_s` (75 s) — hết thì chấm đó bị đưa vào `dead` của lần quét, sang chấm khác; vẫn còn trần vòng / thời gian cũ nên không có vòng vô hạn.
- Loại mới: `nhan` (icon "Nhận" cạnh Chiêu mộ, ảnh `reddot_con_sot.png`, vùng `NHAN_ZONE`) và `construct` (nút búa góc phải dưới → `construct.run`). Dò chấm búa bằng ngưỡng lỏng hơn (`hammer_dots`).
- Cuối lượt: `reddots.run(ctx, final=True)` ngay sau `final_claims`, bỏ qua giãn tần suất + trí nhớ (`reddots.final_sweep`, `final_max_s` 90).
- **Chưa chứng minh trên máy**: vùng `NHAN_ZONE` suy từ một ảnh; tọa độ chạm icon "Nhận" (`x-22, y+17`) là suy đoán theo các icon khác.

## P13d-2 Runner (`bot/steer.py`, `bot/stream.py`)
- `detect()` nhận thêm **vòng tím/hồng** (test trên `runner_khong_dieu_khien.png`: bảng +5% + 3 vòng). Luật cổng đỏ giữ nguyên.
- `DragWatch`: lệnh kéo mà đội quân không đi theo `need` lần → nhấc tay, đặt lại ngón (tự chữa khi sendevent mất hiệu lực), không báo động giả khi đội sát mép.
- `FrameStream`: `restart()`, `fps()`; vòng lái phát hiện không có khung mới > 1,5 s → khởi động lại luồng (tối đa 4 lần rồi bỏ lái, trả `error`). Log cuối trận ghi fps, số lần restart, số lần đặt lại tay.
- **Chưa chứng minh**: nguyên nhân gốc "bot không điều khiển" trên máy thật chưa xác định được (không chạy live, không có `logs/steer/*_trace.csv` mới). Đây là phát hiện + tự chữa, không phải sửa nguyên nhân đã biết. Nút bỏ qua góc phải dưới và "Tiếp tục Chiến dịch" đã có từ P13-10 (`campaign.py`), không đổi.

## P13d-3 Xây dựng (`bot/build.py`, `src/aowbot/domain/hqplan.py`)
- `hqplan.reserve`: `WAIT_BUILDER` **trước giờ thức dậy không còn nhường thợ** (live6c #5: plan "wait_builder" nhưng cuối lượt thợ 0/2 rảnh → construct bị nhường cả lượt). Tới giờ nhà chính cần thợ thì vẫn nhường.
- `should_quick_wait`: không đứng chờ công trình ngắn khi còn bước khác trong lượt (làm bước khác, drain chạy lại `upgrade`/`construct` sau); chỉ chờ khi chẳng còn việc nào khác.
- `free_speedup`: chạm thanh tiến độ, **chỉ** bấm nút có chữ "Miễn phí" không kèm số (nút kim cương, "Tăng tốc", "Dùng", "Mua" không bao giờ khớp). Gọi đầu `quick_wait`.
- Công trình xong → xây tiếp ngay: dựa trên `drain` (upgrade tự lặp ≤ 6, construct sau khi có việc) đã có; không đổi.
- **Không đổi** `build.max_builders` mặc định (1): chưa biết tài khoản nào có thợ thứ hai; đặt 2 theo từng máy trên web nếu có. **Chưa chứng minh trên máy**: bảng "Tăng tốc" có hiện nút "Miễn phí" khi chạm thanh tiến độ hay không.

## P13d-4 Đọc cấp nhà chính (`bot/modules/observe.py`)
- Ghi chú: ở game này nhà chính **chính là** Xưởng kiến trúc; dòng log "Nha chinh (Xuong kien truc)" là chuỗi cố định nên không chứng minh được nhãn. Hướng xử lý: `ocr_hq_ex` trả (cấp, có nhãn "Xưởng kiến trúc", text); `judge_hq` ghi cấp chỉ khi bằng cấp cũ hoặc +1; **nhảy >1 hoặc giảm** cần ≥ 2 lần đọc độc lập (mở lại bảng, tối đa 3 lần), đều có nhãn; không thì giữ cấp cũ, lưu ảnh `hq_suspect`.
- Nếu 4→7 là thật (xây nhanh nhiều cấp trong 1 lượt) thì cần 2 lần đọc cùng 7 có nhãn mới ghi.

## P13d-5 Quán quân tuần (`bot/modules/champion.py`)
- Pure: `bar_split` (tỉ lệ từ thanh đỏ/xanh, không cần OCR), `pick_side`, `handle_center`, `drag_plan` (kẹp 0..539), `verified`, `bet_buttons` (chỉ chữ "Đặt cược", qua `buttons.is_danger`).
- Luồng: "Cược của tôi" → "Đặt cược" → màn trận → "Đặt cược" → hộp "Cược và đặt cược": kéo hết về bên % cao hơn, đọc lại số tiền hai đầu = "Sở hữu" mới bấm "Đặt cược". Không thấy chữ "Sở hữu" → không đặt. Không nút kim cương.
- Hook: `reddots._open_dot` gọi `champion.handle` khi icon vừa mở là màn cược. **Chưa có đường vào riêng** (không biết biểu tượng sự kiện nằm đâu); vùng OCR tiêu đề và `ROI` suy từ ảnh `cuoc_1/2` (≈ toàn màn) — `cuoc_3` là ảnh cắt nên vị trí hộp hiện dò theo màu, chưa thử trên máy thật.

## P13d-6 Auto tất cả (`main.py`, `run.bat`)
- `python main.py --web --auto-all`: `launch_web()` gọi `runner.start()` **trước** `serve()`; runner vẫn chỉ xử lý máy đang bật auto, tối đa `ldplayer.max_running`/`HARD_MAX_RUNNING` = 2 song song. `run.bat` truyền `--auto-all %*`. Nút Bắt đầu/Dừng trên web, `--once/--only` không đổi. Chỉ `--web` thì **không** tự chạy.

## Kiểm
Xem số test cuối báo cáo trong stdout lúc hoàn thành (pytest toàn bộ, ruff, mypy, `main.py --check` xanh; `--check` báo thiếu 16 ảnh mẫu như trước). Ba test cũ `test_p13b_cham_do_khong_doi` cần ảnh `data/owner-feedback/p13/quan_quan_tuan_bam_sai.png` (gitignore) — đã chép bản đọc từ cây chính vào worktree để chạy.
