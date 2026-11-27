# AOW-BOT: Kế hoạch triển khai tổng thể

Ngày: 2026-11-21 · Trạng thái: **Đề xuất, chờ chủ dự án duyệt** (ADR-0012) · Đây là tài liệu lập kế hoạch: chưa có thay đổi code nào.

Hai workstream dùng chung một kiến trúc đích, một chuẩn code, một chiến lược hợp đồng, một chiến lược test, một khung benchmark và một chiến lược migration:
- **A:** tối ưu mã cũ
- **B:** agent theo mục tiêu và sự kiện

## Mục lục tài liệu
| # | Mục bắt buộc | Ở đâu |
|---|---|---|
| 1 | Audit repository | [master-audit.md](master-audit.md), [phase-0-audit.md](phase-0-audit.md) |
| 2 | Đánh giá kiến trúc hiện tại | [../architecture/system-overview.md](../architecture/system-overview.md) §1 |
| 3 | Kiến trúc đích | [../architecture/system-overview.md](../architecture/system-overview.md) §2 |
| 4 | Cấu trúc mã nền | [../architecture/code-organization.md](../architecture/code-organization.md), [../architecture/dependency-rules.md](../architecture/dependency-rules.md) |
| 5 | Ma trận trách nhiệm module | [master-audit.md](master-audit.md) §4, [../architecture/module-contracts.md](../architecture/module-contracts.md) |
| 6 | Kiểm kê tối ưu mã cũ | [implementation-roadmap.md](implementation-roadmap.md) §2.2–2.3 |
| 7 | Kiểm kê phát triển agent | [implementation-roadmap.md](implementation-roadmap.md) §2.4 |
| 8 | Bản đồ migration cũ → mới | [migration-map.md](migration-map.md) |
| 9 | Đồ thị phụ thuộc task | [task-dependency-graph.md](task-dependency-graph.md) §1–2 |
| 10 | Chiến lược chạy song song | [task-dependency-graph.md](task-dependency-graph.md) §3 |
| 11 | Ma trận sở hữu file | [workstream-ownership.md](workstream-ownership.md) |
| 12 | Baseline hiệu năng | [performance-baseline.md](performance-baseline.md) |
| 13 | Test và CI | [../architecture/testing-strategy.md](../architecture/testing-strategy.md) |
| 14 | Sổ rủi ro | §11 bên dưới |
| 15 | Tiêu chí nghiệm thu | §12 bên dưới + [implementation-roadmap.md](implementation-roadmap.md) §4 |
| 16 | Roadmap có ưu tiên | [implementation-roadmap.md](implementation-roadmap.md) §3 + §10 bên dưới |
| 17 | Rollback và migration | [migration-map.md](migration-map.md) §4 |
| 18 | Lộ trình học máy M0–M4 (đề xuất 27/11/2026, chờ duyệt) | [ml-roadmap.md](ml-roadmap.md) |

ADR liên quan: 0008 (kim cương), 0010 (tài khoản khách), 0012 (làm theo phase), 0013–0015 (kiến trúc, luật phụ thuộc, công cụ; Đề xuất).

## Quyết định của chủ dự án (2026-11-21)
- **Farm:** khi nhà chính < `gather.min_hq_level` (9) thì ưu tiên `ContinuousConstruction`; từ cấp 9 trở lên thì farm. #1 (HQ30) farm ngay.
- **MVP agent:** bật trên #1, nhưng chỉ sau khi shadow/dry-run trên dữ liệu thật đạt; chế độ cũ là đường lui.
- **Không đưa ảnh fixture vào git.** Hồi quy ảnh chỉ chạy local và là cổng bắt buộc cho task chạm perception.
- **Mã mới trong `src/aowbot`:** định danh tiếng Anh; comment tiếng Việt không dấu, chỉ giải thích "vì sao".

---

## 1. Tóm tắt điều hành
- **Bot chậm chủ yếu vì lập lịch và chọn việc sai, không phải vì thao tác chậm.** [MEASURED]
  - 223 lần ghé (24,9 h VM) chỉ cho ra 9 lần bắt đầu nâng cấp.
  - 13,3 h VM là lần ghé "thợ rảnh" không xây được.
  - Chuỗi nhiệm vụ trả 0 ở 288/312 lần (415 phút).
  - `reddots` chạy mỗi lần ghé, tốn 426 phút.
- **Chi phí cố định ~73 s mỗi lần ghé** (bật VM 24 s, chờ game 30 s, popup ~19 s), tổng ~5,4 h. [MEASURED]
- **4 rủi ro an toàn đang tồn tại trong code chạy thật** [OBSERVED]. Bốn việc này được xử lý **đầu tiên**:
  - mua khiên bằng kim cương vẫn tiếp tục khi OCR hỏng
  - `reddots` bỏ qua tùy chọn của chủ dự án
  - đấu trường chọn đối thủ mạnh nhất khi không đọc được lực chiến
  - chiêu mộ bấm "1 lần" khi không chắc là miễn phí
- **Nhiều chỉ số then chốt còn UNKNOWN:** độ trễ ADB, số ảnh/OCR mỗi bước, screencap thừa do `human.py`. Task đo A-MEAS-1 phải đi trước mọi tối ưu thao tác.
- **Lộ trình 6 sóng:**
  1. An toàn + nền
  2. Sửa lập lịch + đo
  3. World Model + sự kiện
  4. Quyết định dry-run + shadow
  5. MVP vòng hành quân tự hành trên #1
  6. Mở rộng goal, điều phối, học

  Chuỗi tới hạn tới MVP: ~21 đơn vị công sức.

## 2. Tình trạng kỹ thuật
- 51 file, 9.176 dòng Python.
- Không có pytest/ruff/mypy. Fixture 97 MB và `data/` bị gitignore.
- 2 script hồi quy đang pass (13/13, 34/34).
- God classes: `Runner` 420 dòng (`run_account` CC 52), `Ctx` 596 dòng.
- 57 `except` rộng (25 im lặng), 48 import trong hàm, 72 hàm có CC > 10.
- Trùng lặp đáng kể: `_power` ×3, Tesseract ×3 đường, ảnh thu nhỏ ×4, đoạn gửi quân ×4.
- Mã chết nhỏ: `stream.Shell`, `index.v1.html`, `rebels.join` thiếu ảnh mẫu…
- Logging không có ngày, không xoay file. Không có schema cấu hình. Công cụ báo cáo ghi vào DB thật.

Chi tiết: [master-audit.md](master-audit.md).

## 3. Vấn đề kiến trúc chính
- Runner và Ctx gánh quá nhiều trách nhiệm.
- Luật nghiệp vụ rải ở 4 nơi.
- Hai kho trạng thái (`state.json` và `facts`) không rõ ai sở hữu, nên dữ liệu cũ bị làm tươi.
- Hợp đồng `run(ctx) -> int` mơ hồ.
- Module gọi chéo nhau; lõi phụ thuộc ngược vào module.
- Trạng thái global ẩn.
- Lớp web chứa logic.
- Runtime ghi vào cây mã nguồn.

Chi tiết P1–P13: [system-overview.md](../architecture/system-overview.md).

## 4. Kiến trúc đích
- Modular monolith trong `src/aowbot`: `domain` → `application` → `infrastructure` / `interfaces` → `app`.
- Ports & adapters, DI tường minh.
- `infrastructure.legacy` là cửa duy nhất vào `bot/*`; `bot/*` chỉ được import `aowbot.domain`.
- Luật kiểm bằng import-linter + test AST.
- Chu trình agent: sự kiện → chống trùng → cập nhật World → đánh giá goal → sinh ứng viên → lập kế hoạch → chấm điểm → Policy → thực thi một Action → xác minh → cập nhật → học → hẹn sự kiện kế.

## 5. Kế hoạch Workstream A
Phân loại A1–A6 cho từng thành phần: [master-audit.md](master-audit.md) §4 và [migration-map.md](migration-map.md) §2.

| Nhóm | Task |
|---|---|
| An toàn | A-SAFE-1..5 |
| Độ tin cậy / đo | A-REL-1..4, A-MEAS-1, A-CFG-1, A-DUP-2 |
| Lập lịch (đã đo) | A-FIX-1a/1b, A-FIX-2, A-FIX-3 |
| Điều tra | A-INV-1 (391 lần `none`) |
| Tối ưu sau khi đo | A-OPT-2..7 |
| Chờ chủ dự án | `rebels.join` (A-OPT-1 đã quyết 2026-11-23: giới hạn tần suất/thời gian, làm ở giai đoạn P1 — xem [implementation-roadmap.md](implementation-roadmap.md) mục 0b) |
| Dọn dẹp | A-DEAD-1, A-DUP-1 |

Không tối ưu `gather.run`/`observe.run`, vì hai phần này sẽ bị bọc rồi thay trên #1.

## 6. Kế hoạch Workstream B
| Bước | Nội dung |
|---|---|
| B2a | `domain.freshness`, `domain.marches` (unknown ≠ rảnh) |
| B2b | World view + CLI `world` |
| B1 | Sự kiện + TimerRegistry + chống trùng (shadow) |
| B3 | Goals |
| B4 | `ActionSpec` + adapter `DispatchGatherAction`/`ObserveMarchesAction`/`LegacyStep` |
| POL | `SafetyPolicy` |
| B5/6 | Planner + utility có giải thích (dry-run) |
| B6s | So sánh shadow |
| B9a | `DeviceSession` + khóa liên tiến trình |
| B7 | Executor (xác minh, idempotent, trần retry, phục hồi) |
| SCH-X | Adapter trong runner/scheduler |
| MVP | Bật trên #1 |
| Sau MVP | B9b keep-alive, B-UI dashboard, B3+ goals khác, B8 học |

Chi tiết từng task: [implementation-roadmap.md](implementation-roadmap.md) §2.4.

## 7. Tích hợp và migration
- Strangler 10 bước cho mỗi thành phần.
- Một luật một chỗ (`aowbot.domain`).
- Shadow so 3 nguồn: scheduler chưa sửa, scheduler đã sửa, agent.
- Tiêu chí bật agent được định lượng.
- Rollback theo task (`git revert`), theo máy (`schedule.mode`), theo dữ liệu (bảng chỉ thêm), theo cấu hình (default giữ hành vi cũ).

Chi tiết: [migration-map.md](migration-map.md).

## 8. Cơ hội chạy song song
- P1: F0 ‖ A-SAFE-1 ‖ A-SAFE-3 ‖ F4L
- P2: A-SAFE-2 ‖ A-SAFE-4 ‖ A-REL-2
- P3: chuỗi `scheduler.py` ‖ chuỗi `runner.py` ‖ B2a ‖ A-INV-1
- P4: B2b/B1/B3 ‖ B4 ‖ A-OPT-3 ‖ A-OPT-5
- P5: B5/6 ‖ B9a ‖ A-OPT-2 ‖ A-CFG-1

Không bao giờ chạy song song hai task cùng chạm `scheduler.py`, `runner.py`, `memory.py`, `ctx.py`, `device.py`, `config.yaml` hoặc `composition.py`.

Chi tiết: [task-dependency-graph.md](task-dependency-graph.md) §3, [workstream-ownership.md](workstream-ownership.md).

## 9. Chuỗi phụ thuộc tới hạn
**F0 → B2a → F2 → B2b → B1 → B5/6 → B6s → B7 → SCH-X → MVP**

Các nhánh nhập vào:
- B4 → POL / B9a
- A-FIX-1a → A-FIX-1b, A-FIX-3 → B6s

## 10. 10 task đầu tiên (theo ưu tiên)
| # | Task | Vì sao đứng đây | Công |
|---|---|---|---|
| 1 | **F0** pyproject + công cụ dev | Mọi test sau đều cần; không đổi runtime | 1 |
| 2 | **A-SAFE-1** khiên đóng khi lỗi | Rủi ro kim cương đang sống (`shield_buy_gems: true`) | 1 |
| 3 | **A-SAFE-2/3/4** cổng `reddots`, đấu trường, chiêu mộ | Tôn trọng tùy chọn và chính sách tài nguyên | 2 |
| 4 | **F4L + A-REL-2** báo cáo chỉ-đọc, `Memory` chỉ-đọc | Mọi task A cần số trước/sau mà không ghi DB | 1 |
| 5 | **A-REL-1 + A-REL-4** log có ngày, xoay file, cấu hình hiệu lực | Điều kiện để đo bằng log | 1 |
| 6 | **A-FIX-2** `_remember_facts` | Sửa dữ liệu cũ bị làm tươi; mở đường cho A-MEAS-1 (cùng `runner.py`) | 1 |
| 7 | **A-FIX-1a** `plan_gather` ước lượng giờ về | 5 lần ghé gửi 0 đội / 10 h ở #1 | 1 |
| 8 | **A-FIX-3** `plan_build` backoff theo kết quả | 13,3 h VM vô ích, tác động lớn nhất đã đo | 2 |
| 9 | **A-MEAS-1** bảng `perf` | Lấp UNKNOWN; điều kiện của mọi A-OPT | 2 |
| 10 | **A-INV-1** điều tra 391 lần `none` | Xây dựng là ưu tiên của 6/7 tài khoản; task chỉ thêm log | 1 |

Ngay sau đó: B2a, F1, F2, A-FIX-1b, B2b.

## 11. Sổ rủi ro
| # | Rủi ro | Khả năng | Ảnh hưởng | Giảm thiểu |
|---|---|---|---|---|
| R1 | Mất tài khoản khách | Rất thấp (không task nào ghi dữ liệu app) | Nghiêm trọng | ADR-0010; review từng task |
| R2 | Tiêu kim cương ngoài chính sách | **Đang có** (S1) | Cao | A-SAFE-1 đầu tiên; POL đứng trước Executor; đường lui `shield_buy_gems: false` |
| R3 | Hai workstream sửa cùng file | Trung bình | Trung bình | Ma trận sở hữu, chuỗi giữ khóa |
| R4 | Luật nghiệp vụ bị nhân đôi giữa cũ và mới | Trung bình | Cao (lệch hành vi) | A-FIX-1a → B2a → A-FIX-1b; POL nối `defense.py` |
| R5 | Không có ảnh trên CI | Chắc chắn (theo quyết định) | Trung bình | Cổng local bắt buộc; dữ liệu số cho ca B11 |
| R6 | Sửa lập lịch làm giảm tận dụng hành quân | Trung bình | Trung bình | Ước lượng giờ về, không coi là bận vô hạn; nghiệm thu "không trễ quá `gather_retry_min`" |
| R7 | A-FIX-3 bỏ lỡ lúc có thể xây | Trung bình | Trung bình | Reset backoff khi tài nguyên/HQ/lực chiến đổi; trần `build_every_min`; đo "nâng cấp/ngày" |
| R8 | Shadow khác scheduler | Trung bình | Thấp | Chỉ bật khi đạt tiêu chí; bật theo máy |
| R9 | Đo ADB cần máy thật | Chắc chắn | Thấp | Chủ dự án bật máy; ≤ 2 instance; 10 lần ghé |
| R10 | Quá thiết kế | Trung bình | Trung bình | Không tạo thư mục hay Protocol khi chưa có nơi dùng; checklist review |
| R11 | Hai tiến trình runner | Thấp | Trung bình | A-REL-4 log cấu hình hiệu lực; B9a khóa liên tiến trình |
| R12 | Mốc 4 h thủ công không so được | Cao | Thấp | Chỉ tham khảo; cần chủ dự án mô tả điều kiện đầu |
| R13 | Định danh tiếng Anh lệch CLAUDE.md | Thấp | Thấp | Cập nhật CLAUDE.md sau F0 |

## 12. Tiêu chí nghiệm thu
- **Mỗi task:** cổng chất lượng ở [implementation-roadmap.md](implementation-roadmap.md) §4, gồm code (ruff, mypy, lint-imports), test, runtime, hiệu năng so baseline, bảo trì, an toàn. Kèm nghiệm thu riêng trong bảng task.
- **MVP:**
  - Trên #1, agent phát hiện đội về, cập nhật trạng thái, chọn mỏ hợp lệ (tải trọng ≥ trữ lượng), gửi quân, xác minh "Hành quân x/y" tăng, rồi hẹn sự kiện kế mà **không** chạy chuỗi `ORDER`.
  - 0 hành động trùng.
  - 0 vi phạm Policy.
  - Qua 24 h (S-main-24h), đội gửi/giờ và thời gian đội nằm không không kém scheduler đã sửa, và phút VM/đội gửi thấp hơn.
- **Chương trình:** giờ VM vô ích (lần ghé mà bước trigger trả 0) giảm ≥ 50 % sau sóng W2, đo bằng F4L trên cùng cách tính.

---

**Chờ chủ dự án duyệt.** Sau khi duyệt, việc triển khai bắt đầu từ task #1 (F0), mỗi task một lần duyệt riêng.
