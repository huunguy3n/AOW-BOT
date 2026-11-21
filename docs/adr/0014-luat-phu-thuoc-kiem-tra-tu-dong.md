# ADR-0014: Luật phụ thuộc giữa các lớp, kiểm tra tự động bằng import-linter và test kiến trúc

- **Trạng thái:** Đề xuất
- **Ngày:** 2026-11-21
- **Liên quan:** ADR-0013, [dependency-rules.md](../architecture/dependency-rules.md)

## Bối cảnh
[ĐO] Mã cũ không có vòng import độ dài 2, nhưng có phụ thuộc đảo tầng và gọi chéo:
- `bot.build` → `bot.modules.observe`
- `bot.ctx` → `bot.scheduler`
- `runner` gọi hàm riêng `quests._battle_blocked`
- `reddots` gọi 6 module khác
- `web.server` tự tính nghiệp vụ

48 import trong thân hàm làm các phụ thuộc này khó thấy. Nếu luật lớp chỉ nằm trên giấy, mã mới sẽ trượt về cùng hình dạng.

## Quyết định
Áp dụng 10 luật D1–D10 trong `dependency-rules.md`. Luật nào khai báo được thì kiểm bằng **import-linter** (hợp đồng `layers` + `forbidden`). D9 (không trạng thái global có thể thay đổi), D10 (import trong hàm phải có lý do) và phần bổ sung của D1 (domain không đọc đồng hồ, file hay ngẫu nhiên) kiểm bằng **test AST trong pytest**. Cả hai chạy trong CI. Vi phạm trong mã cũ được ghi lại, không sửa hàng loạt.

## Phương án đã cân nhắc
- **A. Chỉ review thủ công.** Nhược: không bền khi dự án lớn dần.
- **B. Chỉ test AST tự viết.** Ưu: không thêm công cụ. Nhược: tự viết lại phân tích đồ thị import mà import-linter đã làm tốt.
- **C. import-linter + test AST cho phần còn lại (chọn).** Một dependency dev nhẹ, cấu hình khai báo trong `pyproject.toml`.

## Hệ quả
- Tốt: vi phạm bị chặn ngay ở CI; bản đồ phụ thuộc là tài liệu sống.
- Xấu / chi phí: thêm 1 dependency dev; mỗi lớp/package mới cần cập nhật hợp đồng.
- Việc phải làm theo: thêm cấu hình vào `pyproject.toml` ở bước S0; test kiến trúc ở `tests/architecture/`.
