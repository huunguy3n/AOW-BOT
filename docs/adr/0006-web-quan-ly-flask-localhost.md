# ADR-0006: Web quản lý Flask, chỉ nghe localhost

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-11-16
- **Liên quan:** `web/server.py`, `web/index.html`, `web/options.py`, `run.bat`

## Bối cảnh
Người dùng cần bật/tắt auto, chạy ngay một máy, chỉnh tùy chọn và xem tài nguyên/hành quân mà không sửa file.

## Quyết định
Flask một tiến trình chung với Runner (runner chạy luồng nền), một trang HTML tĩnh gọi JSON API (`/api/state`, `/api/runner`…). Mặc định chỉ nghe `127.0.0.1:8080`. Danh sách tùy chọn khai báo dữ liệu trong `web/options.py` (`GROUPS`, cờ `ready` cho tính năng "sắp có").

## Hệ quả
- Tốt: không cần build frontend; thêm tùy chọn chỉ cần khai báo.
- Xấu: **không có xác thực** — mở `--host 0.0.0.0` cho LAN là ai cũng điều khiển được. Không mở ra Internet.
- Web và runner chung tiến trình: tắt web là dừng bot.
