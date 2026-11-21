# Roadmap triển khai

Ngày: 2026-11-21 · Trạng thái: **chờ duyệt** · Thuộc [MASTER-IMPLEMENTATION-PLAN.md](MASTER-IMPLEMENTATION-PLAN.md)

Đồ thị phụ thuộc: [task-dependency-graph.md](task-dependency-graph.md). Sở hữu file: [workstream-ownership.md](workstream-ownership.md).

**Quy ước công sức (tương đối):** 1 = nhỏ (≤ nửa ngày, 1 commit) · 2 = vừa · 3 = lớn (nhiều commit, có thể chia nhỏ khi làm) · 5 = rất lớn (phải chia nhỏ trước khi làm).

**Luật thực thi:**
- Mỗi task chỉ bắt đầu khi chủ dự án duyệt (ADR-0012).
- Mỗi task là 1 nhánh và 1–n commit nhỏ, có test, có số đo trước/sau (F4-lite hoặc A-MEAS-1).
- Task nào cần chạy máy ảo thì **chủ dự án bật máy** (tối đa 2 instance, CLAUDE.md quy tắc 4).

## 1. Công thức ưu tiên
`Ưu tiên ≈ Tác động nghiệp vụ × Giảm rủi ro × Giá trị phụ thuộc / Chi phí`. Đây là heuristic, không phải phép tính chính xác.

Thứ tự lớp ưu tiên:
1. An toàn tài khoản và kim cương
2. Chặn đo đạc/test
3. Bottleneck lập lịch đã đo
4. Nền kiến trúc + hợp đồng chung
5. Lát dọc agent (MVP)
6. Điều phối đa tài khoản
7. Học máy nâng cao

## 2. Danh sách task

### 2.1 Nền tảng (F)
| ID | Mô tả | File | Tiền đề | Sản phẩm | Nghiệm thu | Rủi ro | Công |
|---|---|---|---|---|---|---|---|
| F0 ✅ | `pyproject.toml` (dev: pytest, ruff, mypy, import-linter, coverage); cấu hình công cụ. **Đã làm 2026-11-21.** Khác kế hoạch: chưa đóng gói package nào (`packages = []`), vì `bot`/`web` là tên top-level quá chung để cài vào site-packages. Dòng `sys.path` cho `src` dời sang B2a, khi có package `aowbot` | `pyproject.toml` (mới), `.gitignore`, README, CLAUDE.md | – | Cài editable được | Đạt: `pip install -e .[dev]` OK; `--check` cho kết quả y hệt; 13/13, 34/34; `pytest` chạy (0 test, exit 5); ruff nghiêm và ruff mã cũ (51 file) xanh; `git diff bot/ web/ tools/ main.py config.yaml` rỗng | Thấp | 1 |
| F4L ✅ | (Đã làm 2026-11-21: `tools/report_ro.py`, có `--since/--until/--split/--inst/--json`; baseline toàn bộ dữ liệu: 257 lần ghé, 31,62 h, bật máy → bước đầu trung vị 75,3 s; **lần ghé smart vô ích 124 / 17,43 h**.) Script đo **chỉ-đọc** Q1–Q10 + chỉ số theo task (lần ghé theo lý do, bước trả 0, phút VM) | `tools/report_ro.py` (mới) | – | Báo cáo trước/sau cho mọi task A-* | Kết quả khớp performance-baseline §2; mtime của `memory.db` không đổi | Thấp | 1 |
| F1 | pytest bọc `check_screens`, `check_tutorial` (marker `fixtures`, skip khi thiếu ảnh); `conftest.py` | `tests/regression/*`, `tests/conftest.py` | F0 | Hồi quy chạy qua pytest | Local 13/13, 34/34; CI: skip có lý do | Thấp | 1 |
| F2 | Hợp đồng import-linter (dependency-rules §3.1) + test AST D9/D10/D1 | `pyproject.toml`, `tests/architecture/*` | F0, B2a (cần package `aowbot`) | Luật phụ thuộc thành cổng tự động | `lint-imports` xanh; test AST xanh; cố ý thêm import vi phạm thì fail | Thấp | 1 |
| F3 | GitHub Actions `windows-latest`: ruff, mypy, lint-imports, coverage + pytest (`not device and not ocr`) | `.github/workflows/ci.yml` | F1, F2 | CI | Xanh trên nhánh (chỉ có hiệu lực sau khi **chủ dự án push**) | Thấp | 1 |
| F4 | Benchmark chung trong `aowbot`: metrics thuần + reader chỉ-đọc + `python -m aowbot bench` | `src/aowbot/application/metrics.py`, `infrastructure/sqlite/*`, `interfaces/cli.py` | B2b, A-MEAS-1 | Một khung đo cho cả A và B | Cùng số với F4L trên cùng DB; có thêm chỉ số `perf` | Thấp | 2 |

### 2.2 Workstream A: an toàn, độ tin cậy, đo đạc
| ID | Mô tả | File / hàm | Bằng chứng | Tiền đề | Nghiệm thu | Rollback | Công |
|---|---|---|---|---|---|---|---|
| A-SAFE-1 ✅ | (Đã làm 2026-11-21: `shield_choice`, `spent_amount`, `parse_owned`, `spent_today` + 28 test trong `tests/legacy/test_defense_shield.py`; nếu dùng vật phẩm mà kim cương vẫn giảm thì cũng tính vào trần.) Mua khiên **đóng khi lỗi**: không đọc được kim cương hoặc số vật phẩm thì không mua; ghi chi tiêu ước tính theo `PRICE` khi lần đọc sau hỏng; ngày theo UTC; `shield_hours` ngoài {1, 12, 72} thì báo lỗi rõ. Tách hàm quyết định thuần | `bot/modules/defense.py:shield` | master-audit S1 (OBSERVED) | F0 | Test thuần: mọi tổ hợp OCR None → không mua; trần ngày không bị vượt khi lần đọc sau hỏng | `defense.shield_buy_gems: false` + revert | 1 |
| A-SAFE-2/3/4 ✅ | (Đã làm 2026-11-21: `reddots.allowed`, `play.arena_eligible`, `notify.recruit_choice` + 33 test trong `tests/legacy/test_safety_gates.py`.) | | | | | | |
| A-SAFE-2 | `reddots._handle` áp cùng cổng `modules.*`/`notify.*` như `notify.run` | `bot/modules/reddots.py:75-99` | S2 | F0 | Test: module bị tắt thì không được gọi; `check_tutorial` 34/34 | revert | 1 |
| A-SAFE-3 | Đấu trường: `own` None → bỏ lượt | `bot/modules/play.py:arena` | S3 | F0 | Test thuần chọn đối thủ | revert | 1 |
| A-SAFE-4 | Chiêu mộ "1 lần" chỉ khi có **bằng chứng dương** là miễn phí | `bot/modules/notify.py:recruit` | S4 | F0 | Test trên fixture chiêu mộ (local) + test thuần | revert | 1 |
| A-SAFE-5 | Điều tra `btn_donate_gold` không ROI | `bot/modules/alliance.py:35` | S5 (INFERRED) | – | Báo cáo khớp trên fixture `ally_tech_i1.png`; thêm ROI nếu cần | revert | 1 |
| A-REL-1 | Log có ngày + `TimedRotatingFileHandler` | `main.py:23-31` | master-audit §5 | – | Log chạy qua nửa đêm sang file mới, có ngày | revert | 1 |
| A-REL-2 ✅ | (Đã làm 2026-11-21; `tools/learn.py train` vẫn ghi vì đó là mục đích của lệnh.) Công cụ báo cáo mở DB chỉ-đọc; `Memory` có tham số `readonly` (không chạy schema/PRAGMA) | `bot/memory.py:_conn`, `tools/baseline.py`, `tools/learn.py report` | master-audit §4.3 | – | Chạy báo cáo, mtime/`user_version` DB không đổi | revert | 1 |
| A-REL-3 | Bỏ ghi `ctx.cfg["_use_help"/"_use_free"]`; truyền tham số cho `help_and_free` | `bot/ctx.py:help_and_free`, `modules/train.py:93`, `city.py:22`, `alliance.py:65` | OBSERVED | A-MEAS-1 (cùng file `ctx.py`) | Test: thứ tự module không đổi hành vi help/free | revert | 1 |
| A-REL-4 | Runner log cấu hình hiệu lực (`mode`, `parallel`, `wait_scale`) khi khởi động và khi đổi | `bot/runner.py:_loop` | settings ghi 1, log ghi 2 | – | Dòng log xuất hiện | revert | 1 |
| A-MEAS-1 | Bộ đếm hiệu năng (performance-baseline §4) → bảng `perf` | `bot/perf.py` (mới), `device.py`, `ocr.py`, `screens.py`, `ctx.py:_ocr_tesseract`, `human.py:_shot`, `runner.py:run_account`, `memory.py` | Các chỉ số UNKNOWN | A-REL-1, A-REL-2, A-REL-4, A-FIX-2 (cùng `runner.py`), F4L | 10 lần ghé có duyệt: mọi bước có dòng `perf`; Σ ≤ `runs.dur`; tỉ lệ `runs.result` không đổi | `perf.enabled: false` | 2 |
| A-CFG-1 | Bổ sung khóa thiếu vào `config.yaml` (có comment), thống nhất default, bỏ khóa chết | `config.yaml`, các `cfg.get(...)` liên quan | master-audit §5 | – | grep: mọi khóa đọc đều có trong YAML; hành vi không đổi | revert | 1 |
| A-DUP-2 | Race `meta.json` giữa `server.learn_candidate` và `Learner.candidate`: dùng chung một hàm có khóa | `web/server.py:205`, `bot/learn.py:candidate` | OBSERVED | – | Test đồng thời 2 luồng | revert | 1 |
| A-DEAD-1 | Gỡ `stream.Shell`, `Vision.prior_hits`, `web/index.v1.html`, import thừa, `play.py:357-358`; `rebels.join` **theo quyết định của chủ dự án** | các file liên quan | grep = 0 nơi dùng | F1 | Hồi quy xanh; grep lại = 0 | revert | 1 |

### 2.3 Workstream A: sửa lập lịch và tối ưu (có số đo)
| ID | Mô tả | File / hàm | Bằng chứng | Tiền đề | Nghiệm thu (benchmark) | Rollback | Công |
|---|---|---|---|---|---|---|---|
| A-FIX-1a | `plan_gather`: số đội rảnh lấy từ `march_used/march_total` quan sát gần nhất (facts có `observed_at`). Đội không có đồng hồ thì ước lượng giờ về = `observed_at + unknown_return_min` (khởi tạo từ lịch sử gather), **không** coi là rảnh hay bận vô hạn. Timer `march:` quá hạn coi là rảnh. Hàm thuần cục bộ + bảng chân trị | `bot/scheduler.py:plan_gather` | B11: 5/15 lần ghé gửi 0 đội | F0, F4L | Phát lại 15 lần ghé của #1: chặn ≥ 4/5 lần gửi 0 đội; 10 lần có gửi không bị trễ quá `gather_retry_min`. Live: số `gather.ret=0`/ngày giảm | revert | 1 |
| A-FIX-1b | Chuyển luật sang `aowbot.domain.marches`, scheduler gọi lại, xóa hàm cục bộ | `bot/scheduler.py`, `src/aowbot/domain/marches.py` | Một luật một chỗ | A-FIX-1a, B2a, F2 | Cùng bảng chân trị xanh ở domain; `run.bat`/web/`sim_schedule` import được; hợp đồng "Ma cu chi duoc dung domain moi" xanh | revert | 1 |
| A-FIX-2 | `_remember_facts` chỉ ghi khi giá trị đổi hoặc chưa có | `bot/runner.py:_remember_facts` | B4 | F0 | Test: `seen_at` không đổi khi giá trị không đổi. Live: ~1 dòng "Nha chinh … cap N" / máy / 6 h VM | revert | 1 |
| A-FIX-3 | `plan_build`: đếm lần chạy `mainquest`+`quests` có `ret == 0` liên tiếp **bất kể kết quả**; giãn chu kỳ theo cấp số, trần `build_every_min`; reset khi tài nguyên, nhà chính hoặc lực chiến thay đổi | `bot/scheduler.py:plan_build` | B1: 111 lần ghé, 13,3 h | A-FIX-1a (cùng file), F4L | `sim_schedule` + phát lại: lần ghé "thợ rảnh"/farm-ngày giảm ≥ 50 %; "Đã bắt đầu nâng cấp"/ngày không giảm | `schedule.build_backoff: false` | 2 |
| A-INV-1 | Lưu 1 ảnh/dòng/ngày ở nhánh `none` của `quests` và cuối chuỗi "Nhảy"; phân tích | `bot/modules/quests.py`, `bot/build.py:upgrade_here` (chỉ thêm `save_debug`) | 391 lần `none` | – | Có ≥ 10 ảnh phân loại được nguyên nhân; đề xuất task sửa | revert | 1 |
| A-OPT-1 | **Đề xuất, chờ chủ dự án quyết:** `reddots` ra khỏi `ALWAYS` → `extra_due` theo giá trị; đặt cuối `ORDER` | `bot/scheduler.py`, `bot/runner.py:ORDER` | 426 phút, ok 7 % | A-SAFE-2, A-FIX-3, quyết định của chủ dự án | Phút `reddots`/lần ghé giảm; tổng `ret` của notify+rewards+daily+reddots/ngày giảm ≤ 10 % | revert | 1 |
| A-OPT-2 | Một hàm đọc lực chiến (cache theo lần ghé), thay 3 bản `_power` | `bot/ctx.py`, `modules/quests.py`, `mainquest.py`, `tutorial.py` | 1.057 ms/lần | A-MEAS-1 | `perf`: số OCR mỗi bước có cổng lực chiến giảm; `check_tutorial` 34/34 | revert | 2 |
| A-OPT-3 | Screencap fail-fast: lỗi lần 2 trong cùng bước → ném ngay, **giữ** chuỗi "Khong chup duoc man hinh" (runner `blind` so chuỗi này); bỏ qua lỗi của `HumanWatch._shot` | `bot/device.py:screencap` | 264–418 s rồi lỗi | A-MEAS-1 (cùng file) | `perf`: p99 tổng thời gian screencap giảm; số lần ghé bỏ dở do "máy không phản hồi" không tăng | revert | 1 |
| A-OPT-4 | `_wait_game`: hạ sàn khi `identify` xác nhận game sẵn sàng; `close_popups` dừng sớm khi màn ổn định | `bot/runner.py:_wait_game`, `run_account` | 30 + 19 s/lần ghé | A-MEAS-1 | `perf` `_wait_game`+`_popups` giảm; số "game chưa mở → mở lại" không tăng | config | 2 |
| A-OPT-5 | `human.py`: lọc chạm của bot **trước** khi chụp | `bot/human.py:99,105` | cơ chế OBSERVED | A-MEAS-1 | `perf src=human` ảnh do bot chạm ≈ 0; chủ dự án chạm tay 3 lần vẫn ghi đủ 3 | `learn.watch_human` | 1 |
| A-OPT-7 | `_follow_guide`/`defense` tái dùng khung vừa chụp; bỏ qua khi màn không đổi | `bot/runner.py`, `modules/defense.py:under_attack`, `tutorial.guide_visible` | UNKNOWN → đo | A-MEAS-1, A-SAFE-1 | `perf` span `follow_guide`, `defense_check` giảm; không bỏ sót hướng dẫn (fixture tutorial) | `guide_follow` | 2 |
| A-OPT-6 | ROI cho 9 mẫu không ROI trong `screens.identify` | `bot/screens.py` | 129 ms | F1 (local) | 13/13 giữ nguyên; ms/ảnh giảm | revert | 2 (ưu tiên thấp) |
| A-DUP-1 | Gom các bản trùng (dhash, ảnh thu nhỏ, Tesseract, danh sách nút) **khi chạm tới** trong task khác | nhiều | master-audit §6 | – | grep còn 1 bản | revert | – |

### 2.4 Workstream B: agent
| ID | Mô tả | File (đích) | Tiền đề | Nghiệm thu | Rủi ro | Công |
|---|---|---|---|---|---|---|
| B2a | `domain.freshness` (Fact, Freshness, TTL), `domain.marches` (bảng chân trị dùng chung với A-FIX-1a) | `src/aowbot/domain/*`, `tests/unit/*` | F0 | Test xanh; không `time.time()` trong domain; mypy strict | Thấp | 2 |
| B2b | `application.ports` (Clock, AccountStateSource), `world_view`, `infrastructure.sqlite.legacy_memory_reader` (chỉ-đọc), `app.config` (khối `agent:`), `app.composition`, CLI `world <idx> [--db]` | `src/aowbot/**` | B2a, F2 | `python -m aowbot world 1 --db <bản sao>` gắn nhãn observed/inferred/stale/unknown, chạy nhiều lần cho cùng kết quả; test hợp đồng cho reader thật và fake | Thấp | 3 |
| B1 | `domain.events` (frozen), `application.scheduling` (TimerRegistry, khóa chống trùng `(account, type, subject, due_bucket)`), `infrastructure.sqlite.event_store` (bảng `events`); shadow: sinh sự kiện "lẽ ra phát" | `src/aowbot/**` | B2b | Shadow trên bản sao DB: 0 khóa trùng; số sự kiện so với số lần ghé thật được báo cáo | Trung bình | 3 |
| B3 | `domain.goals`: `MarchUtilization`, `ResourceFarming`, `ContinuousConstruction` (trọng số cao nhất khi HQ < `gather.min_hq_level`, theo quyết định chủ dự án), độ thiếu hụt đo được | `src/aowbot/domain/goals.py` | B2b | Test: mỗi goal có điều kiện thỏa mãn, tiền điều kiện, phụ thuộc, ưu tiên | Thấp | 2 |
| B4 | `domain.actions` (`ActionSpec`: tiền điều kiện, hiệu ứng, chi phí, thời lượng, rủi ro, xác minh, retry, idempotency) + adapter `ObserveMarchesAction`, `DispatchGatherAction` (bọc `gather.try_dispatch`), `LegacyStep` | `src/aowbot/domain/actions.py`, `infrastructure/legacy/*` | B2a | Test hợp đồng với `FakeDeviceSession`; adapter chỉ import `bot` trong `infrastructure.legacy` | Trung bình | 3 |
| POL | `domain.policy.SafetyPolicy`: cấm premium (whitelist khiên có trần, ADR-0008), cấm tác động khi độ tin màn thấp, trần retry; lý do có cấu trúc | `src/aowbot/domain/policy.py` | B4, A-SAFE-1 | Test bảng quyết định; không Action nào có `premium > 0` qua được nếu không nằm trong whitelist | Thấp | 2 |
| B5/6 | `application.planning` (chuỗi khả thi, tiền điều kiện thiếu, goal bất khả), `scoring` (utility, trọng số `agent.weights`), `decide` → `Decision` (frozen, giải thích có cấu trúc) → bảng `decisions`; CLI `plan <idx>` (dry-run) | `src/aowbot/**` | B1, B3, B4, POL | Tất định với cùng World + FakeClock; 100 % quyết định có giải thích | Trung bình | 3 |
| B6s | So sánh shadow 3 nguồn (scheduler chưa sửa / đã sửa / agent) trên dữ liệu #1 | `src/aowbot/interfaces/cli.py` (`shadow`) | B5/6, A-FIX-1b, A-FIX-3 | Đạt tiêu chí bật trong migration-map §3 | Trung bình | 2 |
| B9a | `DeviceSession` (bọc `LDConsole`/`Device`/`Ctx` + mở game), khóa liên tiến trình theo tài khoản, ≤ `max_running` | `src/aowbot/infrastructure/legacy/session.py` | B4 | Test với fake; 2 tiến trình không giữ cùng một tài khoản | Trung bình | 3 |
| B7 | `application.execute`: một hành động mỗi lần, xác minh "Hành quân x/y" tăng, trần retry, phục hồi `events.claimed` sau khi restart | `src/aowbot/application/execute.py` | B6s, B9a, POL | Test: sự kiện trùng → 1 hành động; restart giữa chừng → kiểm idempotent trước khi gửi lại | Cao | 3 |
| SCH-X | Runner thêm `_loop_agent` (adapter); scheduler smart **bỏ** `gather` cho máy đang ở chế độ agent | `bot/runner.py`, `bot/scheduler.py` | B7 | Máy ở `agent` không bị smart kéo lên vì gather; máy khác giữ nguyên hành vi | Trung bình | 2 |
| MVP | Bật `schedule.mode: agent` cho vòng hành quân trên #1; 1 lượt + 1 lần chạy lại, rồi 24 h | `data/settings.json` (qua web) | SCH-X | Đội về → chọn mỏ → gửi → xác minh → hẹn sự kiện, không chạy `ORDER`; S-main-24h không kém scheduler đã sửa | Cao | 1 |
| B9b | Giữ VM bật khi sự kiện kế gần (`agent.keep_alive_min`, **chủ dự án duyệt ngưỡng**) | `infrastructure/legacy/session.py`, `application/scheduling.py` | MVP | Phút VM/đội gửi giảm; không vượt `max_running` | Trung bình | 2 |
| B-UI | Dashboard: goal hiện tại, blocker, kế hoạch, Action đã chọn, điểm/lý do, kết quả kỳ vọng và thực tế, lần đánh giá kế, độ tin | `web/server.py` (endpoint mới gọi use case), `web/index.html` | B5/6 | Mọi quyết định trả lời được "vì sao làm việc này" | Thấp | 3 |
| B3+ | Goals Construction (đầy đủ, sau A-INV-1), Research, Training, ResourceBalance, AccountMaintenance; mở rộng ra farm | `src/aowbot/**` + adapter | MVP, A-INV-1 | Mỗi goal qua shadow trước khi bật | Cao | 5 |
| B8 | Học: ước lượng thời lượng Action, xác suất thành công, contextual bandit chọn (loại, cấp) mỏ trong tập an toàn; analytics | `src/aowbot/application/learning.py` | MVP + đủ dữ liệu | Không vượt qua Planner/Policy; cải thiện đo được so với luật cố định | Trung bình | 3 |

## 3. Thứ tự đề xuất (theo sóng)
| Sóng | Task | Điều kiện kết thúc sóng |
|---|---|---|
| **W1: An toàn + nền** | F0, A-SAFE-1..4, F4L, A-REL-1, A-REL-2, A-REL-4 | Không còn rủi ro kim cương/tùy chọn bị bỏ qua; đo được trước/sau |
| **W2: Sửa lập lịch + đo** | A-FIX-1a, A-FIX-2, A-FIX-3, A-INV-1, A-MEAS-1, B2a, F1, F2 | Giờ VM vô ích giảm (S-replay + live); baseline không còn UNKNOWN về ADB |
| **W3: World + sự kiện** | A-FIX-1b, B2b, B1, B3, B4, F3, A-OPT-3, A-OPT-5 | `world`/shadow sự kiện chạy trên dữ liệu thật |
| **W4: Quyết định (dry-run)** | POL, B5/6, B6s, B9a, A-OPT-2, A-OPT-4, A-OPT-7, A-REL-3, A-CFG-1 | Shadow đạt tiêu chí |
| **W5: MVP** | B7, SCH-X, MVP, F4 | Vòng hành quân tự hành trên #1 |
| **W6: Mở rộng** | B9b, B-UI, B3+, B8, A-OPT-1 (nếu duyệt), A-OPT-6, A-DEAD-1, A-DUP-* | Theo từng goal |

## 4. Cổng chất lượng (áp dụng cho mọi task)
| Nhóm | Cổng |
|---|---|
| Code | `ruff check` + `ruff format --check` (nghiêm cho `src/aowbot`, cơ bản cho `bot/`); `mypy --strict src/aowbot`; `lint-imports`; không vòng import; không abstraction chưa có người dùng; độ phức tạp tăng thì phải giải thích trong PR |
| Test | unit / contract / integration / regression (local nếu cần ảnh) / architecture xanh. Task chạm perception: **bắt buộc** chạy hồi quy ảnh local (vì CI không có ảnh) |
| Runtime | Không hành động trùng do sự kiện trùng; một thao tác UI mỗi tài khoản tại một thời điểm; mọi retry có trần; không tác động khi độ tin màn dưới ngưỡng; phục hồi được sau restart; trạng thái thực thi bền vững khi cần |
| Hiệu năng | So với baseline (F4L/F4): hành động hữu ích/giờ, tài nguyên/giờ, thời gian đội nằm không, ADB call / hành động hữu ích, overhead ảnh/OCR/điều hướng, tỉ lệ retry, phút VM / lần ghé, chi phí đổi máy. **Không tuyên bố tối ưu nếu không có số đo** |
| Bảo trì | Một chủ sở hữu rõ ràng; hợp đồng tường minh; không god class mới; không module "dump"; test không cần thiết bị thật khi có thể |
| An toàn | Không ghi dữ liệu app (ADR-0010); không tiêu kim cương ngoài Policy (ADR-0008); ≤ 2 instance |
