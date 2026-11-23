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

## Sửa đổi 2026-11-23 — ngày chiến tranh (quyết định của chủ dự án)
- **Thứ 7 = ngày chiến tranh:** căn cứ phải có khiên **liên tục** cả ngày. Bot được dùng mọi loại khiên: Hiệp ước hòa bình (miễn phí, chuẩn bị 1 giờ, bảo hộ 8 giờ, hồi 14 giờ — chỉ bấm khi thấy chữ "Miễn phí"), vật phẩm 1h / 12h / 3 ngày, và **được mua khiên bằng kim cương KHÔNG giới hạn** trong cửa sổ ngày chiến tranh (`warday.buy_gems: true`, `warday.gem_cap: null`). Không mua gói 3 ngày (đắt nhất); mua 1h hoặc 12h, cái nào rẻ hơn cho phần thời gian còn lại.
- **Ngoài ngày chiến tranh** giữ nguyên ngoại lệ cũ: khiên khi bị tấn công, trần `defense.gem_cap_daily` (2000) / tài khoản / ngày.
- Vẫn **đóng khi lỗi**: không đọc được số vật phẩm hoặc số kim cương thì không bấm, không đủ kim cương thì không bấm.
- Mỗi lần mua: log `MUA khien ...` + `KIM CUONG: may #N tieu X (nguon shield_war)` và ghi bảng `gem_ev` (memory.db). `python tools/report_ro.py --24h` cộng theo nguồn; nguồn khác `shield` / `shield_war` = vi phạm.
- Phát hiện ngày chiến tranh: lịch (`warday.weekdays`, `warday.reset_hour_utc`) + công tắc tay `warday.mode` (auto / on / off, có trên web) + bảng thông báo / banner "Giai đoạn N" (tùy chọn). Dấu hiệu chỉ **thêm** ngày, không bớt; cửa sổ mở sớm `lead_h` giờ và đóng muộn `tail_min` phút (không chắc → giữ khiên).
