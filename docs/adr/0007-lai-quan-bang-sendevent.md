# ADR-0007: Lái quân trong trận bằng sendevent + luồng khung hình

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-11-17
- **Liên quan:** `bot/steer.py`, `bot/touch.py`, `bot/stream.py`, `config.yaml → battle`

## Bối cảnh
Trận "chạy đường" (tân thủ, nhiệm vụ chính, Mở rương lãnh thổ…) yêu cầu **giữ ngón tay liên tục** và trượt ngang để nhặt buff / né nerf. `adb shell input swipe` thả tay khi kết thúc → đội quân dừng. `adb screencap` từng ảnh quá chậm để phản ứng.

## Quyết định
- **Chạm:** `Finger` gửi `sendevent` trực tiếp vào `/dev/input/event2` (multitouch protocol B: tracking id, BTN_TOUCH, ABS_MT_POSITION), mỗi thao tác một lệnh `adb shell` riêng (shell giữ qua stdin bị adb Windows đệm lại). Trạng thái chạm tồn tại trên thiết bị giữa các lệnh.
- **Nhìn:** `FrameStream` chạy `adb exec-out "while true; do screencap; done"` và đọc raw RGBA liên tục ở luồng riêng.
- **Quyết định:** theo màu, không cần ảnh mẫu — buff xanh dương/xanh lá đặc, bảng đỏ đặc hình chữ nhật, vòng đỏ rỗng (ném bom), vệt đỏ xe lao. Chọn làn tốt nhất trong `LANES`, giới hạn bước, hệ số `GAIN≈0.4` (lính đi 0.4× độ kéo ngón tay, đo 2026-11-18).
- Chỉ đặt ngón tay khi đã xác nhận trong trận (`campaign/battle_hud`, không có nút Chiến đấu).

## Hệ quả
- Tốt: trận chạy đường thắng được mà không cần đội mạnh hơn; có thể lưu khung debug (`battle.debug_dir`).
- Xấu: phụ thuộc đường dẫn thiết bị cảm ứng và tỉ lệ trục của LDPlayer (ADR-0003); đổi phiên bản LDPlayer có thể phải đo lại. Ngưỡng màu cần tinh chỉnh theo từng loại trận.
