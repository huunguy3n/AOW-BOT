# Chiến lược kiểm thử, công cụ và CI

Ngày: 2026-11-21 · Trạng thái: **Đề xuất** · Liên quan: [ADR-0015](../adr/0015-cong-cu-chat-luong-va-ci.md)

## 1. Hiện trạng [MEASURED]
- Không có pytest, ruff, mypy, import-linter hay coverage trong môi trường (pip list chỉ có Flask, numpy, opencv-python, pytesseract, PyYAML).
- Hồi quy offline có sẵn, chạy được và đang pass:
  - `tools/check_screens.py`: **13/13**, 189 ms/ảnh
  - `tools/check_tutorial.py`: **34/34** ca
- `tools/sim_schedule.py` giả lập lập lịch 24 h; `tools/replay_tutorial.py` phát lại bản ghi.
- `tests/fixtures/` (97 MB) và `data/` bị `.gitignore`, nên máy khác hay CI không có dữ liệu để chạy hồi quy ảnh.
- Kiểm chứng chính hiện nay vẫn là chạy thật trên instance (memory `aow-test-one-pass-recheck`).

## 2. Các loại test

| Loại | Phạm vi | Ví dụ đầu tiên | Thiết bị/ảnh cần |
|---|---|---|---|
| **Unit** | `aowbot.domain`, `aowbot.application` với fake | `freshness` ở ranh giới TTL; `MarchBoard.free_slots` với slot UNKNOWN | Không |
| **Contract** | Mỗi port: hiện thực thật và fake chạy chung một bộ test | `AccountStateSource`: `LegacyMemoryReader` (SQLite tạm) và `InMemoryStateSource` | Không (SQLite file tạm) |
| **Integration** | Adapter hạ tầng + use case, không có máy ảo | `world_view` trên **bản sao rút gọn** của `memory.db` (tạo bằng script từ dữ liệu ẩn danh); CLI `world` trả exit 0 | Không |
| **Regression** | Hành vi cũ không đổi khi tách hàm thuần | pytest bọc `check_screens`, `check_tutorial`; ca B11 (11/15 lần ghé sai) cố định thành dữ liệu test | Ảnh fixture (tự skip nếu thiếu) |
| **Architecture** | Luật phụ thuộc | `lint-imports`; test AST cho D9/D10/D1 bổ sung | Không |
| **Device (thủ công)** | Chạy thật 1 lượt + 1 lần chạy lại | Khi bật agent Phase 4 trên #1 | LDPlayer |

Marker pytest: `@pytest.mark.fixtures` (cần `tests/fixtures/`), `@pytest.mark.ocr` (cần Tesseract), `@pytest.mark.device` (không bao giờ chạy trong CI). Test tự `skip` kèm lý do khi thiếu điều kiện, không fail.

## 3. Công cụ hỗ trợ (deterministic)
- `FakeClock(now)` với `advance(seconds)`: mọi use case nhận `Clock` qua port.
- Ngẫu nhiên: tham số `rng: random.Random` truyền vào. Thompson/bandit trong test dùng seed cố định.
- `FakeDeviceSession` (Phase 4): phát lại chuỗi ảnh từ thư mục fixture, ghi lại các lần chạm thay vì gửi adb.
- Không bao giờ mở `data/memory.db` thật trong test. Integration dùng DB tạm sinh từ schema của `bot/memory.py`.

## 4. Đánh giá công cụ

| Công cụ | Quyết định | Lý do | Phạm vi |
|---|---|---|---|
| **pytest** | Dùng (dev) | Chuẩn de facto; marker/skip/fixture; bọc được script hồi quy cũ | toàn repo |
| **ruff** (lint + format) | Dùng (dev) | Một công cụ thay flake8 + isort + pyupgrade; có luật `C901` (độ phức tạp 10), `PLR0913` (5 tham số), `BLE001` (except rộng), `S110` (try-except-pass) | **Nghiêm** cho `src/aowbot`; `bot/`, `web/`, `tools/` chỉ `E9,F63,F7,F82` (lỗi cú pháp, tên chưa định nghĩa) |
| **mypy** vs pyright | **mypy** (dev) | Cài bằng pip, không cần Node; đủ cho `--strict` | `--strict` cho `src/aowbot`; không kiểm `bot/` |
| **import-linter** | Dùng (dev) | Hợp đồng lớp và cấm import khai báo được (dependency-rules §3.1) | `aowbot`, `bot`, `web` |
| **coverage** | Dùng (dev, `coverage run -m pytest`) | Không cần plugin pytest-cov | Ngưỡng: `aowbot.domain` ≥ 90 %, `aowbot.application` ≥ 80 %; không đặt ngưỡng cho mã cũ |
| hypothesis, tox, pre-commit | **Chưa** dùng | Chưa có nhu cầu đo được; thêm khi có | – |

Mọi công cụ nằm trong nhóm `[project.optional-dependencies] dev`. Không thêm dependency runtime.

## 5. Fixture và quyền riêng tư (cần chủ dự án quyết định)
Ảnh fixture chụp màn hình game có tên nhân vật/liên minh (vd `MF001`, `bn1/MF002`). Ba phương án:
- **A (đề xuất):** commit tập con nhỏ (< 5 MB) đã chọn tay vào `tests/fixtures_ci/` cho hồi quy cốt lõi (màn, tân thủ). Che tên trước nếu chủ dự án muốn. Phần còn lại vẫn chỉ ở local.
- **B:** không commit ảnh. CI chỉ chạy unit/contract/architecture; hồi quy ảnh chỉ chạy local.
- **C:** Git LFS cho toàn bộ fixture: nặng, tốn hạn mức, không cần thiết.

## 6. CI (GitHub Actions, đề xuất)
- Runner `windows-latest`, Python 3.12, khớp môi trường thật (đường dẫn Windows, wheel OpenCV).
- Các bước, dừng ở bước đầu tiên lỗi:
  1. `pip install -e .[dev]`
  2. `ruff check` + `ruff format --check`
  3. `mypy src/aowbot`
  4. `lint-imports`
  5. `coverage run -m pytest -m "not device and not ocr"` + `coverage report` (theo ngưỡng §4)
- Kích hoạt khi push và pull request. Workflow chỉ có tác dụng sau khi chủ dự án **push** lên GitHub; việc push do chủ dự án quyết định.
- Local: `run.bat` không đổi; thêm lệnh tương đương CI để chạy trước khi commit (ghi trong README khi S0 xong).

## 7. Checklist nghiệm thu mỗi thay đổi (bản rút gọn của checklist review)
1. Có một trách nhiệm rõ ràng và đặt đúng lớp chưa?
2. Đã có hiện thực tương tự chưa (tìm trong `bot/` trước khi viết)?
3. Có cách đơn giản hơn không?
4. Phụ thuộc đã tường minh (qua constructor/tham số) chưa?
5. Trạng thái do ai sở hữu?
6. Test được mà không cần thiết bị thật không?
7. Lỗi có được trả về tường minh không?
8. Có thêm coupling không cần thiết không?
9. CI (ruff, mypy, lint-imports, pytest) có xanh không?
10. Thay đổi này giúp lần sửa sau dễ hơn, hay chỉ thêm file?
