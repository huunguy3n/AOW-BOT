# ADR-0002: Chạy tuần tự từng instance (bật → làm → tắt)

- **Trạng thái:** Sửa đổi 2026-11-20 — chủ dự án yêu cầu xử lý **2 instance cùng lúc** (xem mục Sửa đổi)
- **Ngày:** 2026-11-16
- **Liên quan:** `bot/runner.py`, `config.yaml` → `instances`, `cycle`

## Bối cảnh
Có 9 instance (mỗi instance 4 CPU / 4 GB RAM). Chạy song song tốn tài nguyên máy host, adb/screencap chậm và khó debug.

## Quyết định
Runner chạy **lần lượt**: `ldconsole launch` → chờ ADB → mở game → các bước → `observe` → `ldconsole quit` (luôn trong `finally`) → instance kế. Hết vòng thì nghỉ `pause_between_cycles_min`. "Chạy ngay" trên web chèn instance lên đầu hàng đợi. Dừng chỉ có hiệu lực **giữa hai bước**, không cắt ngang thao tác.

## Hệ quả
- Tốt: chỉ 1 VM chạy tại một thời điểm → host nhẹ, log tuần tự dễ đọc; trạng thái rõ ràng (`starting/running/idle/error/stopped`).
- Xấu: thời gian vòng = tổng thời gian các tài khoản; tài khoản cuối chờ lâu. Mỗi lượt tốn thời gian boot + load game (~45 s+).
- Khi khởi động lại bot, trạng thái `running` sót lại được đặt về `stopped` kèm ghi chú.
- Định hướng: khi Account Manager hoàn thành, vòng lặp chuyển từ **theo instance** sang **theo tài khoản** (1 instance, đổi slot giữa các lượt).

## Sửa đổi 2026-11-20: 2 máy song song
Chủ dự án: "hiện tại chỉ mới chạy 1 instance. tôi muốn mở và xử lý 2 instance cùng lúc".
- Mỗi instance chạy trong **luồng riêng** (`run_account` độc lập); số luồng = `schedule.parallel` (mặc định 2), không vượt `ldplayer.max_running` (2).
- `LDConsole.launch` giữ khóa từ lúc đếm số máy đang chạy đến khi máy mới hiện "đang chạy" → hai luồng không cùng bật vượt giới hạn; máy bật tay vẫn được tính.
- Máy thứ hai bật cách máy đầu `schedule.parallel_stagger_s` (20 s). `Vision.miss_hits` tách theo luồng.
- Áp dụng cho cả chế độ `fixed` (hàng đợi lần lượt, 2 thợ) và `smart` (lịch bỏ qua máy đang chạy).
- `schedule.parallel: 1` = quay về chạy tuần tự như cũ.
