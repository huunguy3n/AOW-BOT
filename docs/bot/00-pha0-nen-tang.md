# Báo cáo Pha 0 (N1) — Nền tảng đo & công cụ
Ngày: 2026-11-18 · Kế hoạch: [ke-hoach-hoan-thien-bot.md](../product/ke-hoach-hoan-thien-bot.md)

## 1. Đã làm
| Việc | File | Ghi chú |
|---|---|---|
| Thống kê kết quả từng bước | `bot/state.py` (`step_result`, `reset_stats`), `bot/runner.py` | Mỗi bước ghi: **ổn** / **có ảnh lỗi** (module tự gọi `save_debug`) / **lỗi** (exception) / **kẹt** (watchdog). Giữ 20 lần gần nhất (`stats.<buoc>.hist`), lần lỗi gần nhất + ảnh. |
| Bảng thống kê trên web | `web/index.html`, `web/server.py` | Bảng bước × máy: % ổn trên 20 lần gần nhất + dải màu; bấm ô để mở ảnh lỗi (`/shots/<file>`, chỉ đọc trong `logs/shots/`); nút "Đặt lại"; ↻N = số lần watchdog khởi động lại game. |
| Watchdog | `bot/ctx.py` (`Stuck`, `wd_reset`, `_watch`), `bot/device.py` (`force_stop`), `config.yaml` → `watchdog` | Kiểm tra mỗi lần `ctx.shot()`: màn hình đứng yên > `still_min` phút, hoặc một bước chạy quá `step_max_min` phút (tân thủ 120, NV chính 30) → lưu ảnh `*_stuck.png`, **`am force-stop`** (không xóa dữ liệu), mở lại game, sang bước kế. Quá `max_restarts` lần/lượt → bỏ tài khoản đó. `Stuck` kế thừa `BaseException` để `except Exception` trong module không nuốt mất. Chỉ bật trong runner; `tools/*` không bị ảnh hưởng. Chỉnh được trên web (nhóm "Vòng chạy"). |
| Kiểm tra ảnh mẫu đầy đủ hơn | `bot/tplcheck.py`, `main.py --check` | Quét mọi nhóm thư mục `templates/` (trước chỉ 6 nhóm) + `digits/0–9`, `gather/lv/N`. Kết quả: **thiếu 33/155** (trước báo 20/75 vì bỏ sót ally/defense/rebels/digits). |
| Công cụ cắt ảnh mẫu | `tools/snap.py` | `todo [nhóm]` (danh sách thiếu + lệnh gợi ý), `grid SRC` (ảnh ×2 có lưới tọa độ), `cutmany SRC tên=x1,y1,x2,y2 …` (cắt nhiều mẫu, báo khớp lại/khớp nhiều chỗ). |

## 2. Kiểm chứng
- **[ĐO] offline** bằng thiết bị giả (không chạm LDPlayer): màn hình đứng yên → `Stuck`; màn hình đổi liên tục → không kẹt; quá giờ bước → `Stuck`; `except Exception` không nuốt `Stuck`; runner ghi đúng ok/warn/err/stuck, gọi `force_stop` 1 lần, lượt vẫn kết thúc `idle`.
- **[ĐO]** web: bảng thống kê hiển thị đúng (dữ liệu giả tiêm vào trình duyệt, không ghi `state.json`), 3 tùy chọn watchdog hiện trong "Vòng chạy", `/shots/../…` trả 404.
- **[CHƯA ĐO]** trên máy thật: ngưỡng `diff_th = 2.0` (hoạt ảnh thành phố có bị coi là "đổi" không), thời gian bước thực tế để chỉnh `step_max_min`. → đo ở lượt chạy đầu tiên của N2.

## 3. Trạng thái để lại
- Không bật/tắt instance nào, không chạm dữ liệu app. `data/state.json` không bị ghi dữ liệu thử.
- Mục 4 của N1 (chốt instance thử) **chưa xong**: chờ chủ dự án trả lời câu hỏi §5.2 trong kế hoạch.
