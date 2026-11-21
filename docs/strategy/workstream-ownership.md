# Ma trận sở hữu file theo workstream

Ngày: 2026-11-21 · Trạng thái: **chờ duyệt** · Thuộc [MASTER-IMPLEMENTATION-PLAN.md](MASTER-IMPLEMENTATION-PLAN.md)

## 1. Luật
1. **Mỗi file có đúng một task giữ khóa** tại một thời điểm. Task khác muốn sửa phải chờ task đang giữ merge xong.
2. **Workstream A** sở hữu `bot/`, `web/`, `tools/` (trừ file mới của F), `main.py`, `config.yaml`.
   **Workstream B và nền F** sở hữu `src/aowbot/**`, `tests/**`, `pyproject.toml`, `.github/**`.
3. **B không sửa `bot/`**, trừ ba trường hợp, đều được ghi rõ ở bảng dưới:
   - SCH-X: thêm `_loop_agent`, loại trừ gather cho máy ở chế độ agent.
   - A-FIX-1b: scheduler gọi luật trong domain.
   - POL: `defense.py` gọi lại hàm quyết định mua khiên đã chuyển sang `domain.policy`. Việc sửa này nằm trong chuỗi giữ khóa của `defense.py`, **sau** A-OPT-7.
4. **A không sửa `src/aowbot`**, trừ A-FIX-1b. Luật nghiệp vụ mà A cần thì do B2a viết, và A-FIX-1b chỉ nối vào.
5. `docs/**` dùng chung. Mỗi task cập nhật tài liệu của chính nó.
6. Khi hai luồng cần cùng một file trong cùng một sóng, chạy tuần tự theo thứ tự trong cột "Chuỗi giữ khóa".

## 2. Ma trận

| File / vùng | Chủ | Chuỗi giữ khóa (theo thứ tự) | Điểm tích hợp |
|---|---|---|---|
| `bot/scheduler.py` | A → B | A-FIX-1a → A-FIX-3 → A-FIX-1b → (A-OPT-1 nếu duyệt) → SCH-X | B6s đọc nhưng không sửa |
| `bot/runner.py` | A → B | A-REL-4 → A-FIX-2 → A-MEAS-1 → A-OPT-4 → A-OPT-7 → (A-OPT-1) → SCH-X | `_loop_agent` (SCH-X) là adapter duy nhất của B |
| `bot/memory.py` | A | A-REL-2 → A-MEAS-1 (bảng `perf`) | Bảng `events`/`decisions` do B tạo **trong `src/aowbot/infrastructure/sqlite`**, không sửa `memory.py` |
| `bot/device.py` | A | A-MEAS-1 → A-OPT-3 | B9a chỉ bọc lại, không sửa |
| `bot/ctx.py` | A | A-MEAS-1 (`_ocr_tesseract`) → A-REL-3 → A-OPT-2 → A-DUP-1 | B4 chỉ bọc lại |
| `bot/ocr.py`, `bot/screens.py` | A | A-MEAS-1 → A-OPT-6 | Parse thuần chuyển sang domain khi B cần (chỉ di chuyển, `bot` import lại) |
| `bot/human.py` | A | A-MEAS-1 → A-OPT-5 | – |
| `bot/build.py` | A | A-INV-1 | – |
| `bot/learn.py`, `web/server.py` | A | A-DUP-2 → (B-UI thêm endpoint mới) | B-UI chỉ thêm route gọi use case |
| `bot/modules/defense.py` | A → B | A-SAFE-1 → A-OPT-7 → POL (nối vào `domain.policy`) | Luật mua khiên chỉ ở một chỗ |
| `bot/modules/reddots.py` | A | A-SAFE-2 → (A-OPT-1) | – |
| `bot/modules/play.py` | A | A-SAFE-3 → A-DEAD-1 | – |
| `bot/modules/notify.py` | A | A-SAFE-4 → A-DEAD-1 | – |
| `bot/modules/quests.py`, `mainquest.py`, `tutorial.py` | A | A-INV-1 (quests) → A-OPT-2 | – |
| `bot/modules/train.py`, `city.py`, `alliance.py` | A | A-SAFE-5 (alliance) → A-REL-3 | – |
| `bot/modules/gather.py`, `observe.py` | A (đóng băng) | Không sửa cho tới B4. B4 **bọc** `try_dispatch` / readers | Điểm tích hợp chính của MVP |
| `bot/stream.py`, `bot/vision.py`, `web/index.v1.html` | A | A-DEAD-1 | – |
| `main.py` | A | F0 (1 dòng `sys.path`) → A-REL-1 | Lệnh mới của B đi qua `python -m aowbot`, không qua `main.py` |
| `config.yaml` | A | A-FIX-3 (cờ) → A-MEAS-1 (`perf.enabled`) → A-CFG-1 → B2b (khối `agent:`) → B9b | Khối `agent:` do B sở hữu |
| `data/settings.json` | Chủ dự án (qua web) | MVP: bật `mode: agent` cho #1 | – |
| `tools/report_ro.py` (mới) | F | F4L | Thay bằng F4 sau |
| `tools/sim_schedule.py` | F/A | F0 (`sys.path`) | Dùng để nghiệm thu A-FIX |
| `tools/baseline.py`, `tools/learn.py` | A | A-REL-2 | – |
| `pyproject.toml` | F | F0 → F2 → (B thêm cấu hình khi cần) | – |
| `src/aowbot/domain/**` | B | B2a → B3 → B4 → POL → B3+ | A-FIX-1b là nơi dùng duy nhất từ `bot/` |
| `src/aowbot/application/**` | B | B2b → B1 → B5/6 → B7 → B8 | – |
| `src/aowbot/infrastructure/legacy/**` | B | B4 → B9a → B9b | Cửa duy nhất vào `bot/*` |
| `src/aowbot/infrastructure/sqlite/**` | B | B2b → B1 → B5/6 (`decisions`) → F4 | – |
| `src/aowbot/app/composition.py` | B | Tuần tự theo thứ tự merge | Điểm nghẽn: một task tại một thời điểm |
| `tests/**` | F/B (+ A viết test cho task của A) | Thư mục test riêng theo task: `tests/legacy/test_<module>_*.py` cho A; `tests/unit`, `contract`, `integration` cho B | `conftest.py` do F sở hữu |
| `.github/workflows/ci.yml` | F | F3 | – |
| `CLAUDE.md`, `README.md` | chung | Cập nhật sau F0, F3, MVP | – |

## 3. Điểm tích hợp giữa hai workstream
| Điểm | A cung cấp | B dùng | Hợp đồng |
|---|---|---|---|
| Luật đội hành quân | A-FIX-1a (bảng chân trị) | B2a hiện thực, A-FIX-1b nối vào | `domain.marches` (module-contracts §2) |
| Số đo | F4L, A-MEAS-1 (`perf`) | F4, B8 (ước lượng thời lượng) | Bảng `perf` và các cột của nó |
| Hành vi gửi quân | `gather.try_dispatch` (không đổi) | `DispatchGatherAction` | Mã kết quả `ok/notfound/full/notroops/toobig/locked/nosearch/error` |
| Chính sách kim cương | A-SAFE-1 (hàm quyết định thuần) | POL dùng cùng luật | Một luật một chỗ: POL chuyển hàm của A-SAFE-1 sang `domain.policy`, `defense.py` gọi lại |
| Chế độ chạy | – | SCH-X | `schedule.mode` theo máy |
