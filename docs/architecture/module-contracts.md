# Hợp đồng module

Ngày: 2026-11-21 · Trạng thái: **Đề xuất** · Liên quan: [code-organization.md](code-organization.md), [dependency-rules.md](dependency-rules.md)

Tài liệu này có 3 phần: (1) quy tắc chung cho hợp đồng mới, (2) các port đề xuất cho lát dọc đầu tiên, (3) hợp đồng **thực tế** của từng module cũ (trách nhiệm, phụ thuộc, hiệu ứng phụ, nơi dùng, hợp đồng đích). Hợp đồng chỉ có giá trị khi có **test hợp đồng** đi kèm (testing-strategy §2).

## 1. Quy tắc chung
- Hợp đồng = **kiểu** (chữ ký có type hint) + **tiền điều kiện kiểm tra được** + **kết quả tường minh** + **test**.
- Event, decision, outcome, value object: `@dataclass(frozen=True, slots=True)`, có kiểm tra bất biến trong `__post_init__` khi bất biến quan trọng (vd `0 <= used <= total`).
- Thời gian luôn là tham số (`now: float` epoch giây, hoặc qua port `Clock`). Domain không tự đọc đồng hồ.
- Không trả `None` để báo "không biết": dùng `Freshness.UNKNOWN` hoặc một biến thể kết quả. `None` chỉ dùng cho trường tùy chọn thật sự.
- Lỗi hạ tầng (ADB, OCR, SQLite) được dịch thành kết quả tường minh tại adapter, kèm log có cấu trúc. Không nuốt im lặng.

## 2. Port và model cho lát dọc S1 (chỉ những gì có consumer)

```python
# aowbot/domain/freshness.py
class Freshness(Enum):
    OBSERVED = "observed"     # doc truc tiep tu man hinh, con trong TTL
    INFERRED = "inferred"     # suy ra (vd di = ve), con trong TTL
    STALE = "stale"           # qua TTL
    UNKNOWN = "unknown"       # chua tung co / khong doc duoc

@dataclass(frozen=True, slots=True)
class Fact(Generic[T]):
    value: T
    source: str               # vd "ocr:march_counter", "est:travel"
    observed_at: float
    confidence: float         # 0..1, bat bien kiem tra trong __post_init__
    inferred: bool = False

def freshness(fact: Fact[T] | None, now: float, ttl_s: float) -> Freshness: ...
```

```python
# aowbot/domain/marches.py
class SlotState(Enum): FREE, BUSY, UNKNOWN

@dataclass(frozen=True, slots=True)
class MarchSlot:
    index: int
    state: SlotState
    free_at: Fact[float] | None     # luc doi ranh lai (neu biet)

@dataclass(frozen=True, slots=True)
class MarchBoard:
    total: Fact[int] | None
    slots: tuple[MarchSlot, ...]
    def free_slots(self) -> int: ...          # chi dem FREE; UNKNOWN khong bao gio tinh la ranh
    def next_free_at(self) -> float | None: ...  # chi tu Fact co confidence >= nguong
```

```python
# aowbot/application/ports.py
class Clock(Protocol):
    def now(self) -> float: ...

class AccountStateSource(Protocol):
    """Nguon quan sat da ghi lai (hien: memory.db + state.json, chi doc)."""
    def march_observations(self, account: int) -> MarchObservationSet: ...
```

```python
# aowbot/application/world_view.py
def build_account_state(account: int, source: AccountStateSource, clock: Clock, ttl: FreshnessPolicy) -> AccountState: ...
```

**Test hợp đồng bắt buộc:**
- `freshness` phân loại đúng ở ranh giới TTL, kể cả khi thời gian quan sát nằm ở tương lai.
- `MarchBoard.free_slots()` = 0 khi mọi slot là `UNKNOWN`. Đây là tái hiện lỗi B11 trong audit: 11/15 lần ghé sai.
- `build_account_state` trả cùng kết quả trên cùng nguồn + `FakeClock`. Hiện thực `LegacyMemoryReader` và `InMemoryStateSource` (fake) qua **cùng một bộ test hợp đồng**.

Các port tương lai (`DeviceSession`, `MarchReader`, `GatherDispatcher`, `EventStore`, `DecisionLog`, `AccountLock`, `ActionRunner`) chỉ được khai báo khi phase dùng chúng bắt đầu.

## 3. Hợp đồng thực tế của module cũ [OBSERVED + MEASURED]

Hợp đồng chung hiện tại: `run(ctx) -> int` ("số việc làm được"). Runner suy kết quả bước từ ngoại lệ, số ảnh `save_debug` và `Vision.miss_hits`. Mọi module tự điều hướng (`ensure_city`/`ensure_world`) và đọc `ctx.cfg`.

| Module | Trách nhiệm thật | Phụ thuộc (ngoài `ctx`) | Hiệu ứng phụ: dữ liệu ghi | Nơi dùng | Giá trị trả về | Hợp đồng đích |
|---|---|---|---|---|---|---|
| `gather` | Gửi đội đi mỏ tới khi đầy hành quân | `ocr` | facts `march_load`, `mine_cap:{loai}:{cap}`; state `marches`, `dispatches`, `march_used` | runner, `defense` | số đội gửi | `GatherDispatcher.dispatch(MineChoice) -> DispatchOutcome` bọc `try_dispatch`; luật `plausible`/tải trọng → `domain.mines` |
| `observe` | Đọc nhà chính, thợ, tài nguyên, hành quân, khiên | `ocr` | facts `builders_busy`, `shield_until`, `march_*`, `resources`, `observed_at`; timers `build:*`, `march:*`, `arrive:*`; state `hq_level` + nhiều khóa | runner, `build` (`progress_bars`) | `dict` | Tách thành các `Observe*Action` nhỏ, mỗi cái trả `Observation` có `Fact` |
| `mainquest` | Đi theo thanh nhiệm vụ chính (đánh/xây/chiến dịch) | `build`, `campaign`, `tutorial`, `ocr` | state `mainquest_need_power`, `mainquest_busy_until`; fact cùng tên; timer `build:quest` | runner | số bước thắng/xây | `LegacyStep` (thô); sau này tách thành Action "đi tới mục tiêu nhiệm vụ" |
| `quests` | Nhiệm vụ Chương/Chính qua nút "Đến" → nâng cấp | `build`, `tutorial`, `ocr` | state `quests_need_power` | runner (cả hàm riêng `_battle_blocked`) | số nâng cấp bắt đầu | `LegacyStep`; cổng lực chiến → `domain.goals` |
| `construct` | Xây công trình mới bằng icon búa | `badges`, `ocr` | – | runner | số công trình | `LegacyStep` |
| `research` | Nghiên cứu nhánh thu thập | `ocr` | timer `research`; state `research` | runner | số lần bắt đầu | `LegacyStep` → Action khi có Goal ContinuousResearch |
| `train` | Huấn luyện lính T3 | `ocr` | – | runner | số đợt | `LegacyStep` → Action khi có Goal ContinuousTraining |
| `rebels` | Tập kết phản quân | `alliance`, `ocr` | fact `rebels_levels` | runner | số lượt | `LegacyStep` |
| `alliance` | Quyên góp vàng, trợ giúp, rương boss, mỏ liên minh | `badges`, `ocr` | fact `rebels_attacks_game` | runner, `rebels`, `reddots` | số việc | `LegacyStep` |
| `notify` | Chấm đỏ: phúc lợi, hoạt động, tình báo, chiêu mộ, tướng | `badges`, `campaign`, `screens`, `ocr` | – | runner, `intel`, `reddots` | `dict` | `LegacyStep`; trả `int` thống nhất qua adapter |
| `intel` | Tình báo | `notify` | – | runner, `reddots` | số nhiệm vụ | `LegacyStep` |
| `reddots` | Quét chấm đỏ còn lại, gọi module khác | notify, rewards, intel, campaign, daily, alliance, `badges` | fact `reddots_dead` | runner | số lần nhận | `LegacyStep`; agent sẽ chọn trực tiếp Action con thay vì gọi qua `reddots` |
| `rewards` | Thư, VIP, lễ hội, quà nổi | `badges` | – | runner, `reddots` | số lần nhận | `LegacyStep`; chính sách VIP → `domain.policy` |
| `daily` | Nhận thưởng nhiệm vụ ngày + rương năng động | – | – | runner, `reddots` | số lần nhận | `LegacyStep` |
| `campaign` | Đánh màn chiến dịch khi dự đoán thắng | `steer` | – | runner, mainquest, notify, play, reddots, tutorial | số trận thắng | `LegacyStep`; `predicted_win` là hàm nhận diện thuần |
| `play` | Mỏ khoáng sản, đấu trường, cướp xe | `campaign`, `steer`, `ocr` | facts `arena_lost`, `loot_mem` | runner | số việc | `LegacyStep` |
| `city` | Nhặt tài nguyên nổi trên thành phố | – | – | runner | số lần chạm | `LegacyStep` |
| `defense` | Phát hiện bị tấn công, bật khiên (có thể tốn kim cương, có trần) | `gather`, `screens`, `ocr` | state `last_attack`, `last_defense`, `gems_spent` | runner (trước mỗi bước + nút web) | kết quả | Tách: `under_attack` → Observation; bật khiên → Action với `cost.premium` **chỉ** được `SafetyPolicy` cho phép theo ADR-0008 |
| `tutorial` | Tân thủ; `decide()` thuần | `build`, `campaign`, `steer`, `touch`, `badges`, `ocr` | state `tutorial_done`, `tutorial_need_power` | runner, mainquest, quests, tools | chuỗi/bool | Giữ nguyên (đã có hồi quy 34 ca) |

Lõi:

| File | Trách nhiệm thật | Ghi chú hợp đồng |
|---|---|---|
| `runner.Runner` | vòng lặp, lịch, vòng đời VM, cổng nghiệp vụ, phục hồi | Không có hợp đồng tường minh; độ phức tạp `run_account` 52 |
| `scheduler` | luật lập lịch thuần trên `Memory` | Thuần nhưng nhận `mem` (đọc SQL trực tiếp), nên test cần DB thật |
| `ctx.Ctx` | toàn bộ thao tác UI + học + watchdog | `Stuck(BaseException)` là hợp đồng duy nhất được ghi rõ |
| `memory.Memory` | kho SQLite; nuốt mọi lỗi ghi | Cố ý: "lỗi DB không làm hỏng lượt". Giữ cho mã cũ; repository mới báo lỗi tường minh |
| `state.Store` | state.json + settings.json | Mỗi `update` ghi lại toàn file (~11 ms) |
| `device.Device`/`LDConsole` | adb / ldconsole qua subprocess | `screencap` có thể chặn ~75 s khi máy treo |
