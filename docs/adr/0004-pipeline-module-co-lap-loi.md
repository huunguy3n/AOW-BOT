# ADR-0004: Pipeline module theo thứ tự, cô lập lỗi từng bước

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-11-16
- **Liên quan:** `bot/runner.py` (`ORDER`), `bot/modules/*`, `bot/ctx.py`

## Bối cảnh
Mỗi lượt tài khoản gồm nhiều việc độc lập (nhận quà, nghiên cứu, huấn luyện, gửi quân…). Game hay hiện popup bất ngờ; một màn lạ không được làm hỏng cả lượt.

## Quyết định
- Mỗi tính năng = một module `run(ctx)`; thứ tự cố định trong `ORDER`, bật/tắt bằng `modules.*`.
- Thứ tự có chủ đích: `mainquest` đầu (ưu tiên tiến trình) → nhận tài nguyên/quà **trước** khi tiêu (nghiên cứu, huấn luyện) → `rebels` trước `gather` (cần đội rảnh) → `daily` cuối (sau khi các bước khác đã tăng tiến độ) → `observe` luôn chạy cuối.
- Trước mỗi bước: `defense.under_attack()`; nếu có thì chạy phòng thủ trước.
- Exception trong một bước: ghi log + ảnh `logs/shots/`, `ctx.ensure_city()`, chạy bước tiếp theo.

## Hệ quả
- Tốt: thêm tính năng = thêm 1 file + đăng ký; lỗi khoanh vùng theo bước; web hiển thị bước đang chạy.
- Xấu: các module ngầm phụ thuộc trạng thái màn hình ban đầu (thành phố) → mỗi module phải tự về thành phố khi xong.
- Đăng ký module mới ở 3 nơi: `ORDER`, `config.yaml → modules`, `web/options.py → MODULES`.
