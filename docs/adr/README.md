# Architecture Decision Records (ADR)

Mỗi ADR ghi lại **một** quyết định: bối cảnh, quyết định, hệ quả. ADR đã "Chấp nhận" không sửa nội dung; muốn đổi thì viết ADR mới và đánh dấu ADR cũ là "Thay thế bởi ADR-xxxx".

Trạng thái: **Đề xuất** · **Chấp nhận** · **Thay thế** · **Loại bỏ**

| # | Quyết định | Trạng thái | Ngày |
|---|---|---|---|
| [0001](0001-dieu-khien-qua-adb-va-nhan-dien-anh.md) | Điều khiển game qua ADB + nhận diện ảnh, không can thiệp bộ nhớ/mạng | Chấp nhận | 2026-11-16 |
| [0002](0002-chay-tuan-tu-tung-instance.md) | Chạy tuần tự từng instance (bật → làm → tắt) | Chấp nhận | 2026-11-16 |
| [0003](0003-he-toa-do-540x960.md) | Hệ tọa độ cố định 540×960 dọc | Chấp nhận | 2026-11-16 |
| [0004](0004-pipeline-module-co-lap-loi.md) | Pipeline module theo thứ tự, cô lập lỗi từng bước | Chấp nhận | 2026-11-16 |
| [0005](0005-cau-hinh-phan-lop.md) | Cấu hình phân lớp: config.yaml ← settings.json (global ← instance) | Chấp nhận | 2026-11-16 |
| [0006](0006-web-quan-ly-flask-localhost.md) | Web quản lý Flask, chỉ nghe localhost | Chấp nhận | 2026-11-16 |
| [0007](0007-lai-quan-bang-sendevent.md) | Lái quân trong trận bằng sendevent + luồng khung hình | Chấp nhận | 2026-11-17 |
| [0008](0008-chinh-sach-kim-cuong.md) | Không tự tiêu kim cương / đường trả phí (trừ khiên có trần) | Chấp nhận | 2026-11-16 |
| [0009](0009-da-tai-khoan-snapshot-du-lieu-app.md) | Đa tài khoản bằng snapshot/restore dữ liệu app (Option C) | Chấp nhận | 2026-11-17 |
| [0010](0010-an-toan-tai-khoan-khach.md) | Tài khoản khách = dữ liệu app: quy tắc bảo toàn | Chấp nhận | 2026-11-17 |
| [0011](0011-tan-thu-ham-quyet-dinh-thuan.md) | Tân thủ: hàm quyết định thuần + kiểm tra offline bằng bản ghi | Chấp nhận | 2026-11-17 |
| [0012](0012-lam-viec-theo-giai-doan.md) | Làm việc theo giai đoạn, chủ dự án duyệt từng phase | Chấp nhận | 2026-11-17 |
| [0013](0013-modular-monolith-phan-lop-src-aowbot.md) | Modular monolith phân lớp trong `src/aowbot`, cùng tồn tại với `bot/` cũ | Đề xuất | 2026-11-21 |
| [0014](0014-luat-phu-thuoc-kiem-tra-tu-dong.md) | Luật phụ thuộc giữa các lớp, kiểm tra bằng import-linter + test kiến trúc | Đề xuất | 2026-11-21 |
| [0015](0015-cong-cu-chat-luong-va-ci.md) | Công cụ chất lượng (pytest, ruff, mypy, import-linter, coverage) và CI | Đề xuất | 2026-11-21 |

Mẫu ADR mới: [template.md](template.md).
