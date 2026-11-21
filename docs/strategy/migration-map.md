# Bản đồ migration: mã cũ → kiến trúc đích

Ngày: 2026-11-21 · Trạng thái: **chờ duyệt** · Thuộc [MASTER-IMPLEMENTATION-PLAN.md](MASTER-IMPLEMENTATION-PLAN.md)

Kiến trúc đích: [../architecture/code-organization.md](../architecture/code-organization.md). Luật phụ thuộc: [../architecture/dependency-rules.md](../architecture/dependency-rules.md).

## 1. Nguyên tắc
1. **Một luật, một chỗ.** Luật nghiệp vụ mới viết trong `aowbot.domain`. `bot/*` gọi lại luật đó (luật D7 cho phép `bot` → `aowbot.domain`). Không giữ hai bản cùng một luật.
2. **Kiến trúc mới quyết định chiến lược.** Về lâu dài, module cũ chỉ còn là **adapter thực thi**, không tự quyết.
3. **Strangler 10 bước** cho mỗi thành phần:
   1. Hợp đồng
   2. Adapter
   3. Test hành vi cũ
   4. Nối vào kiến trúc mới
   5. Chạy shadow / dry-run
   6. So sánh quyết định và kết quả
   7. Bật có kiểm soát (theo máy)
   8. Theo dõi lỗi và hiệu năng
   9. Mở rộng
   10. Gỡ phần điều phối cũ
4. **Mọi bước đảo ngược được:**
   - `schedule.mode` có ba giá trị `fixed | smart | agent`, đặt theo máy qua `settings.json`.
   - Mỗi task là một commit nhỏ.
   - Bảng DB mới chỉ thêm, không sửa.
5. **Không tối ưu mã sắp bị thay** nếu chưa tính chi phí migration. Ngoại lệ: sửa an toàn và sửa lỗi chặn đo đạc hoặc chặn test.

## 2. Bản đồ theo thành phần

Cột "Quyết định": Keep (A1) · Optimize (A2) · Refactor (A3) · Wrap (A4) · Replace (A5) · Remove (A6).

| Thành phần cũ | Quyết định | Đích | Điều kiện để gỡ phần cũ | Task |
|---|---|---|---|---|
| `Runner._loop`, `_loop_smart` | Replace dần | `aowbot.app.lifecycle` + `accounts` (B9) | Mọi máy chạy `agent` ổn định ≥ 7 ngày | MVP → mở rộng |
| `Runner.run_account` (vòng đời VM, mở game) | Wrap rồi Replace | `infrastructure.legacy.session` (B9a), sau đó là `DeviceSession` | B9 ổn định | B9a |
| `Runner._remember_facts` | Refactor (sửa) | Bị bỏ khi World Model đọc trực tiếp quan sát | B2b dùng thay | A-FIX-2 |
| Cổng nghiệp vụ trong `run_account` (HQ8 / rebels / world / `march_full`) | Replace | `domain.goals` / tiền điều kiện của `ActionSpec` | B4 + B5 bao phủ | B4 |
| `scheduler.plan_gather` | Refactor (A-FIX-1a) → luật chuyển sang `domain.marches` (A-FIX-1b) | `domain.marches` + `application.scheduling` | Shadow B6s đạt | A-FIX-1a/b, B6s |
| `scheduler.plan_build` | Refactor (A-FIX-3) | `domain.goals.ContinuousConstruction` | B3+ | A-FIX-3 |
| `scheduler.decide`, `extra_due`, `value_factor` | Keep cho farm (smart) → Replace | `application.scheduling` + `decision` | Farm chuyển sang agent | B5/B6 |
| `scheduler.ALWAYS`, `ORDER` | **Chờ chủ dự án** (thứ tự do chủ dự án chốt 2026-11-21) | Agent không dùng ORDER | – | A-OPT-1 (đề xuất) |
| `Ctx` (I/O, điều hướng, học) | Wrap qua port hẹp | `infrastructure.legacy.*` | Không gỡ (vẫn là lớp thực thi) | B4 |
| `Ctx.claim_loop` (chính sách VIP) | Replace phần chính sách | `domain.policy` | Policy có test | POL |
| `Ctx.read_marches`, `ocr.marches`, `observe.*` | Wrap + tách parse thuần | `infrastructure.legacy.marches` + domain parse | – | B2b, B4 |
| `Device`, `LDConsole` | Optimize (đo, fail-fast) → Wrap | `infrastructure.legacy.session` | – | A-MEAS-1, A-OPT-3, B9a |
| `memory.Memory` | Keep schema; Refactor mở chỉ-đọc | `infrastructure.sqlite` (repository mới đọc/ghi bảng mới) | – | A-REL-2, B1 |
| `state.Store` | Keep cho web | World Model là nơi lưu dữ kiện; `state.json` chỉ còn là bản chiếu cho web | Web đọc World Model | B2b, sau MVP |
| `learn.Learner` | Keep → Wrap | `application.learning` + adapter | – | B8 |
| `gather.try_dispatch` | **Wrap** | `DispatchGatherAction` | – | B4 |
| `gather.run` (vòng lặp tới khi đầy) | Replace trên #1 khi chạy agent; Keep cho farm | Agent lặp Action theo sự kiện | Mọi máy chạy agent | MVP |
| `observe.run` | Wrap thành các Action quan sát nhỏ | `ObserveMarchesAction`, … | – | B4 |
| `defense.shield` | Refactor ngay (S1) → Policy | `domain.policy` (premium chỉ khi được whitelist, có trần) | POL | A-SAFE-1, POL |
| `reddots._handle` | Refactor (S2) → Wrap | Agent chọn trực tiếp Action con | – | A-SAFE-2 |
| `play.arena`, `notify.recruit` | Refactor (S3, S4) → Wrap | `LegacyStep` | – | A-SAFE-3/4 |
| 15 module bước còn lại | Wrap thô | `LegacyStep` | Không gỡ | B4 |
| `tutorial.decide` | Keep | Giữ nguyên (đã có 34 ca hồi quy) | – | – |
| `steer`, `touch`, `stream` | Keep (gỡ `stream.Shell`) | – | – | A-DEAD-1 |
| `_power()` ×3, `dhash` ×2, ảnh thu nhỏ ×4, `builders` ×2, Tesseract ×3 | Refactor khi động tới (gom về một chỗ) | Hàm thuần trong domain/perception | grep không còn bản sao | A-OPT-2, A-DUP-1 |
| `web/server.py` logic lẻ | Replace dần bằng use case | `interfaces` | – | sau B5/B6 |
| `web/index.v1.html`, `Vision.prior_hits`, import thừa | Remove | – | grep = 0 nơi dùng | A-DEAD-1 |
| `rebels.join` (thiếu ảnh mẫu) | **Hỏi chủ dự án**: cắt ảnh mẫu hay gỡ | – | – | A-DEAD-1 |
| `tools/check_*.py` | Wrap thành pytest | `tests/regression` | Giữ script cũ | F1 |
| `tools/baseline.py` | Replace | F4-lite, rồi F4 (`aowbot bench`) | F4 có đủ chỉ số | F4-lite, F4 |

## 3. Shadow và so sánh (bước 5–6)
- **Đầu vào:** bản sao chỉ-đọc của `memory.db` (offline), và sau đó là chính `memory.db` khi bot đang chạy (agent chỉ ghi vào bảng của nó: `events`, `decisions`).
- **So sánh 3 nguồn trên cùng dòng thời gian:**
  1. Scheduler cũ **chưa sửa** (bản trước commit A-FIX-1, chạy offline)
  2. Scheduler đã sửa
  3. Agent ở chế độ dry-run
- **Chỉ số so sánh:**
  - số lần ghé hoặc đánh thức theo lý do
  - lần ghé vô ích (gửi 0 đội / bước trigger trả 0)
  - giờ đội rảnh tới lần ghé kế
  - số quyết định không có giải thích (phải bằng 0)
- **Tiêu chí bật agent trên #1:**
  - Mọi lần ghé hữu ích của scheduler đã sửa đều có quyết định tương ứng của agent, trễ không quá `gather_retry_min`.
  - Số lần đánh thức vô ích của agent không nhiều hơn scheduler đã sửa.
  - 0 quyết định vi phạm Policy.

## 4. Rollback
| Mức | Cách |
|---|---|
| Một task | `git revert <commit>`. Test của task giữ lại, đánh dấu `xfail` có lý do nếu cần |
| Một máy | `settings.json` → `instances.<idx>.schedule.mode = "smart"` (web có sẵn ô tùy chọn) |
| Dữ liệu | Bảng mới (`perf`, `events`, `decisions`) để nguyên hoặc bỏ qua, không ảnh hưởng mã cũ. Không bao giờ sửa hay xóa bảng cũ |
| Cấu hình | Mọi khóa mới đều có giá trị mặc định giữ nguyên hành vi cũ |
| An toàn | A-SAFE có đường lui cấu hình (`defense.shield_buy_gems: false`) trong lúc chờ sửa |

## 5. Những gì KHÔNG migrate
- `poc/*` (Account Manager): dự án con riêng, theo ADR-0009/0010.
- Lái quân trong trận (`steer`): thời gian thực, đang ổn định, nằm ngoài vòng quyết định.
- `tutorial.decide`: đã là hàm thuần và có hồi quy.
