# Tổ chức mã nguồn

Ngày: 2026-11-21 · Trạng thái: **Đề xuất** · Liên quan: [ADR-0013](../adr/0013-modular-monolith-phan-lop-src-aowbot.md), [dependency-rules.md](dependency-rules.md)

## 1. Cây thư mục đích (`src/aowbot/`)

> Đây là **bản đồ đích**, không phải danh sách file phải tạo ngay. Một file/thư mục chỉ được tạo khi đã có code dùng nó và test cho nó (luật A5). Các mục đánh dấu `(S1)` là lát dọc đầu tiên đề xuất ở §4.

```text
pyproject.toml                       metadata, deps runtime + nhóm dev, cấu hình ruff/mypy/pytest/importlinter
src/aowbot/
  domain/                            THUẦN: không I/O, không đồng hồ thật, không log ra file
    freshness.py          (S1)       Fact[T], Freshness(observed|inferred|stale|unknown), TTL → phân loại theo `now`
    marches.py            (S1)       MarchSlot, MarchBoard; luật: unknown ≠ rảnh, đi = về, slot rảnh/đầy
    resources.py                     Resources (value object), so sánh / thiếu hụt
    mines.py                         MineCandidate, luật chọn mỏ (tải trọng ≥ trữ lượng, ưu tiên loại/cấp)
    construction.py                  BuilderQueue, điều kiện nâng nhà chính (khi có dữ liệu)
    account.py                       AccountId, AccountRole (main/farm), giới hạn theo tài khoản
    goals.py                         Goal (frozen) + hàm `deficit(state) -> GoalDeficit`
    actions.py                       ActionSpec (tiền điều kiện, hiệu ứng, chi phí, rủi ro, xác minh, retry)
    policy.py                        SafetyPolicy: cấm premium (ADR-0008), ngưỡng tin cậy màn, trần retry
    events.py                        DomainEvent (frozen): MarchReturnDue, MarchDispatched, …
  application/                       điều phối; chỉ phụ thuộc domain + port của chính nó
    ports.py              (S1)       Protocol: Clock, AccountStateSource, … (chỉ port đã có ≥ 1 consumer)
    world_view.py         (S1)       use case: dựng AccountState từ nguồn quan sát tại thời điểm `now`
    planning.py                      sinh ứng viên + giải phụ thuộc
    scoring.py                       utility + lời giải thích
    decide.py                        use case: event + state → Decision (frozen)
    execute.py                       use case: Decision → khóa tài khoản → chạy → xác minh → Outcome
    scheduling.py                    TimerRegistry, chống trùng sự kiện, đánh thức
    learning.py                      cập nhật ước lượng thời lượng/xác suất từ Outcome
  infrastructure/                    hiện thực port; KHÔNG chứa chiến lược
    clock.py                         SystemClock
    sqlite/
      legacy_memory_reader.py (S1)   đọc memory.db (facts/timers/observations) → bản ghi thô cho world_view
      event_store.py                 bảng events/decisions (thêm mới, backward-compatible)
    legacy/                          adapter duy nhất được import `bot.*`
      session.py                     LDConsole + Device + Ctx → DeviceSession
      marches.py                     ctx.read_marches / ocr.marches → MarchObservation
      gather.py                      gather.try_dispatch → GatherDispatcher
      steps.py                       module.run(ctx) → LegacyStep (bọc thô 18 module)
  interfaces/
    cli.py                (S1)       `python -m aowbot world <idx> [--db PATH]` (chỉ đọc, dry-run)
  app/
    config.py             (S1)       schema khối `agent:` trong config.yaml (dataclass frozen + kiểm tra)
    composition.py        (S1)       dựng đồ thị đối tượng từ config; nơi DUY NHẤT gọi constructor hạ tầng
    lifecycle.py                     start/stop vòng agent (khi có Phase 4)
tests/
  unit/  integration/  regression/  architecture/  contract/   (xem testing-strategy.md)
```

`bot/`, `web/`, `tools/`, `main.py` **giữ nguyên vị trí** trong toàn bộ quá trình migration.

## 2. Bản đồ trách nhiệm

| Thành phần | Trách nhiệm duy nhất | Vào | Ra | Phụ thuộc |
|---|---|---|---|---|
| `domain.freshness` | Phân loại độ tươi của một dữ kiện tại thời điểm cho trước | `Fact`, `now` | `Freshness` | – |
| `domain.marches` | Luật về đội hành quân: slot rảnh/bận/chưa biết, thời điểm về dự kiến | quan sát đội, `now` | `MarchBoard` | `freshness` |
| `domain.mines` | Chọn mỏ hợp lệ theo luật tải trọng và ưu tiên | ứng viên mỏ, tải trọng, cấu hình ưu tiên | danh sách đã lọc/xếp | `resources` |
| `domain.goals` | Định nghĩa mục tiêu đo được và độ thiếu hụt | `AccountState` | `GoalDeficit` | `marches`, `resources`, `construction` |
| `domain.policy` | Quyết định cho phép hay cấm một hành động | `ActionSpec`, `AccountState` | `PolicyVerdict` (có lý do) | `actions` |
| `application.world_view` | Ghép quan sát rời rạc thành `AccountState` nhất quán | `AccountStateSource`, `Clock` | `AccountState` | domain |
| `application.decide` | Chọn một hành động cho một sự kiện, kèm lời giải thích | event, state | `Decision` | planning, scoring, policy |
| `application.execute` | Thực hiện đúng một hành động có kiểm soát và xác minh | `Decision` | `Outcome` | port `ActionRunner`, `AccountLock` |
| `application.scheduling` | Hẹn và chống trùng sự kiện tương lai | Outcome, state | event mới | port `EventStore`, `Clock` |
| `infrastructure.legacy.*` | Dịch giữa port mới và API `bot.*` | port call | dữ liệu domain | `bot.*` |
| `infrastructure.sqlite.*` | Đọc/ghi `memory.db`, chỉ thêm bảng/cột | bản ghi | bản ghi | sqlite3 |
| `interfaces.cli` | Phân tích tham số, gọi use case, in kết quả | argv | stdout/exit code | application (qua `app.composition`) |
| `app.composition` | Dựng và nối các đối tượng | config | đồ thị đối tượng | mọi lớp |

## 3. Quy ước đặt tên và cấu trúc
- Tên module là **danh từ nghiệp vụ** (`marches`, `mines`, `freshness`) hoặc **use case** (`decide`, `execute`). Cấm `manager`, `common`, `helper`, `utils`, `misc`, `base`, `processor`, trừ khi phạm vi đã rõ trong tên (vd `legacy_memory_reader`).
- Mỗi module có một trách nhiệm. Ngưỡng **xem xét lại** (không tự động tách): hàm ~40 dòng, lớp ~200, module ~400, độ phức tạp vòng 10, 5 tham số. Nhóm tham số liên quan thành dataclass.
- Model dữ liệu dùng `@dataclass(frozen=True, slots=True)` cho event, decision, outcome, value object. Chỉ dùng `Protocol` khi có ≥ 2 hiện thực (vd thật + fake trong test) hoặc khi cần đảo phụ thuộc giữa lớp.
- Không trả `None` mơ hồ: dùng kiểu kết quả tường minh (vd `Freshness.UNKNOWN`, `Outcome(status=...)`).
- Lỗi: bắt ngoại lệ **cụ thể**. Nếu phải bắt rộng ở ranh giới (vòng lặp chính, adapter), thì phải log có cấu trúc và trả kết quả lỗi tường minh, không im lặng.
- Log có cấu trúc: `logging` thư viện chuẩn, thông điệp ngắn + `extra={"event": ..., "account": ...}`. Quyết định của agent ghi vào bảng `decisions` (không chỉ log text).

## 4. Đóng gói và cùng tồn tại với mã cũ
- Thêm `pyproject.toml` (setuptools, `src` layout). Package `aowbot` từ `src/`, giữ `bot`/`web` là package phẳng ở gốc như hiện nay. Cài `pip install -e .[dev]`.
- `python main.py …` và `run.bat` phải chạy y như cũ. Nếu chưa cài editable, `main.py` thêm `src` vào `sys.path` (một dòng, có comment lý do). Đây là `sys.path` hack duy nhất được phép, và được xóa khi mọi môi trường đã cài editable.
- `requirements.txt` giữ nguyên cho người đang dùng; nguồn sự thật mới là `pyproject.toml`.

## 5. Ngôn ngữ trong code
- Định danh (tên hàm/lớp/biến) trong `src/aowbot`: **tiếng Anh**, vì tên phải nói lên ý định và khớp thuật ngữ kiến trúc (port, event, outcome). Mã cũ không đổi tên.
- Comment và docstring: theo CLAUDE.md (**tiếng Việt không dấu**), và **chỉ** giải thích *vì sao*, ràng buộc, hoặc quyết định không hiển nhiên. Luật nghiệp vụ "chủ dự án yyyy-mm-dd" phải nằm trong **code + test** (tên test ghi rõ luật); comment chỉ trỏ tới ADR/ngày.
- Tài liệu `docs/`: tiếng Việt có dấu (giữ quy ước).

> Đây là điểm cần chủ dự án xác nhận: đặt tên tiếng Anh trong `src/aowbot` là quy ước mới.

## 6. Bản đồ migration mã cũ → đích

Cột "Bước" theo §7. "Bọc" = tạo adapter, không sửa file cũ. "Tách" = chuyển hàm thuần sang `domain`, file cũ import lại (không sao chép), có test hồi quy trước khi chuyển.

| Mã cũ | Trách nhiệm thật | Đích | Cách | Bước |
|---|---|---|---|---|
| `bot/runner.py` `Runner._loop*`, `run_account` | vòng đời + lập lịch + cổng nghiệp vụ + phục hồi | `app.lifecycle` + `application.execute` + `domain.policy` | Bọc khi có agent; cổng nghiệp vụ tách sang domain | Agent P4 |
| `bot/scheduler.py` | luật lập lịch (thuần) | `domain.marches`, `domain.goals`, `application.scheduling` | Tách dần (đã là hàm thuần); giữ `decide()` cho chế độ smart | S2 → Agent P1–3 |
| `bot/memory.py` | kho SQLite | `infrastructure.sqlite` | Đọc qua adapter mới; ghi bảng mới ở repository riêng; không sửa schema cũ | S1 |
| `bot/state.py` | state.json + settings.json | `infrastructure` (đọc), web cũ vẫn dùng | Bọc chỉ-đọc | Agent P2 |
| `bot/ctx.py` | I/O, vision, điều hướng, học, watchdog, nhận thưởng | `infrastructure.legacy` (port hẹp) | Bọc; chính sách VIP trong `claim_loop` → `domain.policy` sau | Agent P2/P4 |
| `bot/device.py` | ldconsole + adb | `infrastructure.legacy.session` | Bọc | Agent P4 |
| `bot/vision.py`, `screens.py`, `badges.py`, `ocr.py` | nhận diện | `infrastructure` (perception) | Bọc; hàm parse thuần (`ocr.amount/seconds`, `observe.parse_dur`) → domain | S2 |
| `bot/learn.py` | kinh nghiệm, kNN, bandit | `application.learning` + `infrastructure` | Bọc; singleton `_inst` → đối tượng do composition root tạo | Agent P5 |
| `bot/steer.py`, `touch.py`, `stream.py` | lái quân trận | giữ nguyên (hạ tầng chuyên biệt) | Không đụng | – |
| `bot/build.py` | nâng cấp công trình qua UI | `infrastructure.legacy` | Bọc; sửa đảo tầng `build → modules.observe` bằng cách tách `progress_bars` (thuần) | S2 |
| `bot/modules/gather.py` | gửi quân | `infrastructure.legacy.gather` (`try_dispatch`) + `domain.mines` (`plausible`, luật tải trọng) | Bọc + tách | Agent P2 |
| `bot/modules/observe.py` | quan sát cuối lượt | `infrastructure.legacy.marches` + domain parse | Bọc + tách | Agent P2 |
| `bot/modules/tutorial.py` | tân thủ, `decide()` thuần | giữ nguyên; `decide` đã có hồi quy | Bọc khi cần | – |
| 15 module còn lại | mỗi bước UI | `infrastructure.legacy.steps` | Bọc thô `LegacyStep` | Agent P2 |
| `web/server.py` | API + logic lẻ | `interfaces` | Giữ; logic lẻ (`rebels_done_today`) chuyển sang gọi use case khi có | Agent P3+ |
| `tools/check_*.py` | hồi quy | `tests/regression` (pytest) | Bọc thành test, script cũ giữ lại | S0 |
| `main.py` | CLI + composition | `interfaces.cli` + `app.composition` (cho phần mới) | Giữ; thêm lệnh mới qua `python -m aowbot` | S1 |

## 7. Lộ trình nền tảng (trước agent Phase 1)

| Bước | Nội dung | Thay đổi hành vi runtime | Xong khi |
|---|---|---|---|
| **S0 – Công cụ** | `pyproject.toml`, cấu hình ruff/mypy/pytest/import-linter, workflow CI; bọc `check_screens`/`check_tutorial` thành pytest (tự skip khi thiếu fixture) | Không | `pytest`, `ruff`, `mypy`, `lint-imports` chạy xanh local |
| **S1 – Lát dọc đầu tiên** | `domain.freshness`, `domain.marches` (luật "unknown ≠ rảnh"), `application.world_view`, `infrastructure.sqlite.legacy_memory_reader`, `app.config/composition`, `interfaces.cli world` | Không (chỉ đọc bản sao DB) | Test unit + integration + architecture xanh; `world 1` in ra trạng thái đội có nhãn tươi/cũ/chưa biết |
| **S2 – Tách hàm thuần** | `parse_dur`, `ocr.amount/seconds`, `gather.plausible`, `progress_bars` → domain; `bot` import lại | Không (hồi quy chứng minh) | Hồi quy cũ + test mới xanh |
| **S3 – Rà comment/doc** | Sửa chỗ tài liệu lệch code (P10), cập nhật CLAUDE.md | Không | Review |

Sau S0–S3 mới vào agent Phase 1 ([phase-0-audit.md](../strategy/phase-0-audit.md) B7).
