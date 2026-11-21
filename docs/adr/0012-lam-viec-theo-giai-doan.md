# ADR-0012: Làm việc theo giai đoạn, chủ dự án duyệt từng phase

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-11-17
- **Liên quan:** `docs/account-manager/*`, `docs/product/vision-roadmap.md`

## Bối cảnh
Một số việc (Account Manager, gom tài khoản, bật root trên instance chính) có thể gây mất dữ liệu không đảo ngược được.

## Quyết định
- Công việc rủi ro chia **phase**; mỗi phase kết thúc bằng báo cáo trong `docs/` với số liệu phân loại **[ĐO] / [CHƯA ĐO] / [LÝ THUYẾT]**.
- **Không sang phase tiếp theo khi chủ dự án chưa xác nhận rõ ràng.**
- Phase khảo sát ưu tiên lệnh chỉ đọc; thao tác ghi chỉ trên instance thử nghiệm đã thống nhất, có `.ldbk` trước.
- Mỗi báo cáo ghi rõ trạng thái để lại (root bật/tắt, user phụ, slot, instance đang chạy) để có thể dọn hoặc khôi phục.

## Hệ quả
- Tốt: quyết định dựa trên số đo, không có bất ngờ phá hủy.
- Xấu: chậm hơn; cần chờ phản hồi giữa các phase.
