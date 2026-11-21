# Chạy toàn bộ instance — kết quả 2026-11-18 23:19 → 11-19 00:28 (đã dừng theo yêu cầu)
Kế hoạch: [ke-hoach-hoan-thien-bot.md](../product/ke-hoach-hoan-thien-bot.md)

## 1. Theo máy [ĐO]
| Máy | Bản | Kết quả |
|---|---|---|
| #0 | .vn | Lượt đầy đủ (thứ tự cũ): gửi **1 đội** đi mỏ; NV chính thua 2 trận (`follow_lose`); **luyện quân lỗi** "không thấy icon đội ngũ huấn luyện"; kim loại cấp 6 "không tìm thấy". Lực chiến 522K → **604K** |
| #2, #4 | .vn (mới cài) | **Chưa chạy** (đã bật trên web, tân thủ bật) |
| #3 | .vn | Lần 1: lỗi ADB chụp màn hình rỗng (đã sửa: thử lại). Lần 2: tân thủ 34 phút, trận chạy đường **4 thắng / 15 thua / 5 bỏ dở**, thua 6 trận liền → dừng tân thủ; dừng khi đang ở bước chấm đỏ |
| #5 | .vn | Chấm đỏ: chiêu mộ 1, tướng 1. **Luyện quân và gửi quân không làm được** — tài khoản non (Xưởng cấp 3): chưa có icon huấn luyện, game khóa thao tác để dẫn (bàn tay xanh chỉ rương), "Tạo đội/Liên minh/Lối chơi" còn khóa |
| #6 | .vn | Tân thủ riêng (400 bước): **5 thắng / 12 thua**, tới "Mở ruộng 3 lãnh thổ", lực chiến 199K. Lượt đầy đủ sau đó: tân thủ **2 thắng / 10 thua** → dừng |

## 2. Vấn đề chính (theo mức ảnh hưởng)
1. **Lái quân trận chạy đường thua nhiều** (tổng ~11 thắng / 37 thua trên #3 + #6) → tân thủ không qua được, chặn mọi bước sau trên tài khoản mới. Màn thua gợi ý "Nhận nhiều Tướng hơn / Tăng lực chiến Tướng / Hoàn thành nhiệm vụ".
2. **Tài khoản non bị khóa tính năng** (huấn luyện, thu thập, tình báo) cho tới khi làm nhiệm vụ chính/Chương → thứ tự "chấm đỏ → tình báo → thu thập" chỉ có tác dụng khi tính năng đã mở.
3. **#0 không luyện quân** (icon đội ngũ huấn luyện không thấy — trước đó vẫn thấy).
4. **Thu thập #0**: kim loại cấp 6 "không tìm thấy", hợp kim cấp 6 "khóa" → nên hạ cấp mỏ khi không tìm thấy.

## 3. Thay đổi code trong phiên này (chưa kiểm chứng trên máy thật nếu ghi *)
- Thứ tự bước: tân thủ → chấm đỏ (notify, rewards, collect_city, daily) → **tình báo** (bước riêng `intel`*, chạy mỗi lượt) → thu thập → phần còn lại.
- Tình báo thiếu năng lượng: dùng Thuốc Thể Lực **từng viên** tới khi đủ, trần 20 viên + 20 nhiệm vụ/lượt*.
- Tối đa **2 máy chạy cùng lúc** (`ldplayer.max_running`)*.
- Nghiên cứu bỏ qua khi Xưởng kiến trúc < 8.
- Chụp màn hình tự thử lại khi ADB trả rỗng.
- `state.json`: 2 tiến trình song song không ghi đè nhau*.

## 4. Trạng thái để lại
Không còn tiến trình bot nào chạy; mọi instance đã tắt. Tân thủ đang bật cho #2, #3, #4, #6.
