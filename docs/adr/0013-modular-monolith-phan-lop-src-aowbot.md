# ADR-0013: Modular monolith phân lớp trong `src/aowbot`, cùng tồn tại với `bot/` cũ

- **Trạng thái:** Đề xuất
- **Ngày:** 2026-11-21
- **Liên quan:** ADR-0004, ADR-0011, ADR-0012, [docs/architecture/](../architecture/system-overview.md)

## Bối cảnh
Agent theo mục tiêu (phase-0-audit, Phần B) cần WorldModel, Planner, Decision, Executor, Scheduler, và tất cả phải test được không cần máy ảo. Mã hiện tại không có ranh giới lớp:
- [ĐO] `Runner` 420 dòng, `run_account` có độ phức tạp vòng 52; `Ctx` 596 dòng.
- [ĐO] 57 `except` rộng (25 im lặng), 48 import trong thân hàm, 72 hàm có độ phức tạp > 10.
- [ĐO] Luật nghiệp vụ nằm ở 4 nơi; trạng thái global ẩn (`learn._inst`, `steer._battle_*`, `screens._tl`).
- [ĐO] Hai script hồi quy cũ đang pass (13/13, 34/34): hành vi UI hiện tại đáng giữ.

## Quyết định
Code mới viết trong package `aowbot` (`src/aowbot/`), chia 5 lớp: `domain` → `application` → `infrastructure` / `interfaces` → `app` (composition root). `bot/` được coi là **hạ tầng cũ**, chỉ được truy cập qua `aowbot.infrastructure.legacy`. Migration theo kiểu strangler: bọc, test hồi quy, chuyển dần nơi dùng, chỉ xóa mã cũ khi chứng minh không còn ai dùng.

## Phương án đã cân nhắc
- **A. Viết lại toàn bộ theo kiến trúc mới.** Ưu: sạch ngay. Nhược: mất hành vi UI đã được tinh chỉnh qua nhiều ngày chạy thật; rủi ro mất tài khoản; trái ADR-0012.
- **B. Sửa dần trực tiếp trong `bot/`.** Ưu: không thêm package. Nhược: không kiểm được luật lớp, vì mã mới và cũ trộn lẫn và các vi phạm sẵn có sẽ lây sang mã mới.
- **C. Package mới phân lớp + adapter (chọn).** Ưu: luật lớp kiểm tra tự động được trên mã mới; mã cũ chạy nguyên trạng; có đường lui (`schedule.mode`). Nhược: trong thời kỳ chuyển tiếp có hai chỗ để tìm code; cần kỷ luật để không sao chép luật.
- **D. Microservice / tách tiến trình.** Loại: [ĐO] chi phí quyết định ~0,1 s so với bật VM ~75 s; không có nhu cầu phân tán.

## Hệ quả
- Tốt: domain/application test tất định bằng fake; mỗi lớp có trách nhiệm rõ; mã cũ không bị động tới cho tới khi có test hồi quy.
- Xấu / chi phí: thêm `pyproject.toml` và cài editable; định danh tiếng Anh trong `src/aowbot` là quy ước mới (cần chủ dự án xác nhận); thời kỳ chuyển tiếp kéo dài theo phase.
- Việc phải làm theo: S0–S3 trong [code-organization.md](../architecture/code-organization.md) §7; cập nhật CLAUDE.md (phần kiến trúc, mục "Không có test tự động", "chưa phải git repo") sau khi S0 xong.
