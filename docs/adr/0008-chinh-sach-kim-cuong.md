# ADR-0008: Không tự tiêu kim cương / đường trả phí (trừ khiên có trần)

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-11-16
- **Liên quan:** `bot/build.py`, `bot/modules/defense.py`, `notify.py`, `train.py`, README "Không tự động"

## Bối cảnh
Kim cương là tài nguyên hiếm/trả tiền. Một lần bấm nhầm "Tăng cấp ngay" có thể đốt hàng nghìn kim cương; vòng lặp lỗi có thể đốt hết.

## Quyết định
Bot **không bao giờ** bấm: nút tốn kim cương ("Huấn luyện ngay", "Tăng cấp ngay", quyên góp kim cương, "Mua" năng lượng), chiêu mộ cao cấp, đường trả phí ("Mở khóa", "Cấp mùa", "Tiếp tục nhận", "Nạp thẻ"), mua đồ tiệm, "Tăng tốc"/"Dùng thử" thợ xây. Chiêu mộ chỉ miễn phí (`recruit.use_tickets` mặc định false). Liên minh chỉ quyên góp **vàng**.

**Ngoại lệ duy nhất:** khiên khi bị tấn công — dùng vật phẩm trước, hết thì kim cương nếu `defense.shield_buy_gems: true`, tối đa `defense.gem_cap_daily` mỗi tài khoản/ngày.

## Hệ quả
- Tốt: không có kịch bản mất kim cương ngoài ý muốn.
- Xấu: tiến độ chậm hơn người chơi tiêu kim cương.
- Code mới phải phân biệt nút miễn phí/tốn phí (vd `build.py` chỉ bấm nút "Tăng cấp" bên phải có đồng hồ; `notify` kiểm tra màu nút "Nhận" để bỏ nút xám).
