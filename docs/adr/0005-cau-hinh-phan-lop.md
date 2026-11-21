# ADR-0005: Cấu hình phân lớp: config.yaml ← settings.json (global ← instance)

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-11-16
- **Liên quan:** `config.yaml`, `bot/state.py` (`Store.cfg_for`), `data/settings.json`, `data/state.json`

## Bối cảnh
Cần mặc định cho kỹ thuật viên (đường dẫn, ROI, ngưỡng) và tùy chọn người dùng chỉnh nhanh trên web, có thể khác nhau theo từng tài khoản (vd chỉ bật `tutorial` cho TK mới).

## Quyết định
Ba lớp, lớp sau đè lớp trước (merge sâu):
1. `config.yaml` — mặc định + tham số kỹ thuật (có comment).
2. `data/settings.json → global` — tùy chọn chung từ web.
3. `data/settings.json → instances.<idx>` — tùy chọn riêng từng máy.

Trạng thái quan sát (tài nguyên, hành quân, lỗi, trạng thái runner) tách riêng ở `data/state.json`. Ghi JSON atomic (`.tmp` + `os.replace`) dưới `RLock`.

## Hệ quả
- Tốt: web không sửa `config.yaml`; xóa `settings.json` là về mặc định.
- Xấu: khó biết giá trị hiệu lực cuối cùng → web hiển thị giá trị đã merge.
- Khi chuyển sang mô hình theo tài khoản (ADR-0009), khóa `instances.<idx>` sẽ cần đổi sang khóa theo tài khoản/slot.
