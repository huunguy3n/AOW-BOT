# Đồ thị phụ thuộc task

Ngày: 2026-11-21 · Trạng thái: **chờ duyệt** · Thuộc [MASTER-IMPLEMENTATION-PLAN.md](MASTER-IMPLEMENTATION-PLAN.md)

Định nghĩa task (mô tả, file, nghiệm thu, công sức): xem [implementation-roadmap.md](implementation-roadmap.md). Sở hữu file: xem [workstream-ownership.md](workstream-ownership.md).

## 1. Đồ thị

Mũi tên `A --> B` nghĩa là **B cần A xong trước**. Nét đứt nghĩa là phụ thuộc vì **cùng sửa một file** (phải làm tuần tự), không phải phụ thuộc logic.

```mermaid
flowchart TD
  classDef safe fill:#fde2e2,stroke:#c0392b
  classDef found fill:#e3f2fd,stroke:#1565c0
  classDef fix fill:#fff3cd,stroke:#b8860b
  classDef agent fill:#e8f5e9,stroke:#2e7d32
  classDef owner fill:#eee,stroke:#555,stroke-dasharray: 4 3

  F0[F0 pyproject + dev tools]:::found
  F4L[F4L báo cáo chỉ-đọc]:::found
  F1[F1 hồi quy pytest]:::found
  F2[F2 import-linter + test AST]:::found
  F3[F3 CI]:::found
  F4[F4 benchmark aowbot]:::found

  S1[A-SAFE-1 khiên đóng khi lỗi]:::safe
  S2[A-SAFE-2 cổng reddots]:::safe
  S3[A-SAFE-3 đấu trường]:::safe
  S4[A-SAFE-4 chiêu mộ]:::safe

  R1[A-REL-1 log ngày/xoay]:::fix
  R2[A-REL-2 DB chỉ-đọc]:::fix
  R4[A-REL-4 log cấu hình hiệu lực]:::fix
  M1[A-MEAS-1 bảng perf]:::fix
  X1a[A-FIX-1a plan_gather]:::fix
  X1b[A-FIX-1b luật → domain]:::fix
  X2[A-FIX-2 _remember_facts]:::fix
  X3[A-FIX-3 plan_build backoff]:::fix
  INV[A-INV-1 điều tra 'none']:::fix
  O1[A-OPT-1 reddots - chờ chủ dự án]:::owner
  O2[A-OPT-2 lực chiến 1 lần]:::fix
  O3[A-OPT-3 screencap fail-fast]:::fix
  O4[A-OPT-4 wait_game]:::fix
  O5[A-OPT-5 human.py]:::fix
  O7[A-OPT-7 follow_guide/defense]:::fix
  RL3[A-REL-3 rò rỉ cfg]:::fix

  B2a[B2a freshness + marches]:::agent
  B2b[B2b world_view + CLI world]:::agent
  B1[B1 events + TimerRegistry shadow]:::agent
  B3[B3 goals]:::agent
  B4[B4 ActionSpec + adapters]:::agent
  POL[POL SafetyPolicy]:::agent
  B56[B5/6 planner + utility dry-run]:::agent
  B6s[B6s shadow so sánh]:::agent
  B9a[B9a DeviceSession + khóa]:::agent
  B7[B7 executor]:::agent
  SCHX[SCH-X runner/scheduler adapter]:::agent
  MVP((MVP #1 vòng hành quân)):::agent
  B9b[B9b keep-alive]:::agent
  BUI[B-UI dashboard]:::agent
  B3p[B3+ goals khác]:::agent
  B8[B8 học]:::agent

  F0 --> F1 & S1 & S2 & S3 & S4 & X1a & X2 & B2a
  F0 --> F2
  B2a --> F2
  F1 & F2 --> F3
  R1 & R2 & R4 & F4L --> M1
  X2 -.runner.py.-> M1
  R4 -.runner.py.-> X2
  F4L --> X1a & X3
  X1a -.scheduler.py.-> X3
  X1a --> X1b
  B2a --> X1b
  F2 --> X1b
  M1 --> O2 & O3 & O4 & O5 & O7 & RL3
  S1 --> O7
  S2 & X3 --> O1

  B2a --> B2b
  F2 --> B2b
  B2b --> B1 & B3
  B2a --> B4
  B4 & S1 --> POL
  B1 & B3 & B4 & POL --> B56
  B56 & X1b & X3 --> B6s
  B4 --> B9a
  B6s & B9a & POL --> B7
  B7 --> SCHX --> MVP
  B2b & M1 --> F4
  MVP --> B9b & B3p & B8
  INV --> B3p
  B56 --> BUI
```

## 2. Chuỗi tới hạn (dài nhất tới MVP)
**F0 → B2a → F2 → B2b → B1 → B5/6 → B6s → B7 → SCH-X → MVP**

Tổng công sức tương đối: 1 + 2 + 1 + 3 + 3 + 3 + 2 + 3 + 2 + 1 = **21 đơn vị**.

Các nhánh nhập vào chuỗi, phải xong kịp:
- **B4 → POL → B5/6:** B4 bắt đầu được ngay sau B2a, song song với B2b/B1/B3.
- **B4 → B9a → B7:** B9a làm song song với B5/6/B6s.
- **A-FIX-1a → A-FIX-1b, A-FIX-3 → B6s:** shadow phải so với scheduler **đã sửa**, đồng thời so offline với bản **chưa sửa**.

## 3. Các nhóm chạy song song an toàn
Điều kiện song song: **không cùng file**, không task nào cần kết quả của task kia (ma trận sở hữu).

| Nhóm | Task chạy song song | Vì sao an toàn |
|---|---|---|
| P1 (W1) | F0 ‖ A-SAFE-1 (`defense.py`) ‖ A-SAFE-3 (`play.py`) ‖ F4L (`tools/report_ro.py` mới) ‖ A-REL-1 (`main.py` logging*) | File khác nhau. *F0 cũng sửa `main.py` (1 dòng `sys.path`): làm A-REL-1 **sau** F0, hoặc gộp chung một người làm |
| P2 (W1) | A-SAFE-2 (`reddots.py`) ‖ A-SAFE-4 (`notify.py`) ‖ A-REL-2 (`memory.py`, `tools/baseline.py`, `tools/learn.py`) | File khác nhau |
| P3 (W2) | A-FIX-1a → A-FIX-3 (`scheduler.py`, tuần tự) ‖ A-REL-4 → A-FIX-2 → A-MEAS-1 (`runner.py`, tuần tự) ‖ B2a (`src/aowbot`) ‖ A-INV-1 (`quests.py`, `build.py`) | Mỗi chuỗi giữ một nhóm file riêng |
| P4 (W3) | B2b → B1/B3 (`src/aowbot`) ‖ B4 (`domain/actions.py`, `infrastructure/legacy`) ‖ A-OPT-3 (`device.py`) ‖ A-OPT-5 (`human.py`) | B2b/B1/B3 và B4 sửa các module khác nhau trong `src/aowbot`; điểm chung duy nhất là `app/composition.py`, chỉ một task sửa tại một thời điểm |
| P5 (W4) | B5/6 ‖ B9a ‖ A-OPT-2 (`ctx.py` + 3 module) ‖ A-CFG-1 (`config.yaml`) | Như trên |

**Không bao giờ chạy song song** hai task cùng chạm `bot/scheduler.py`, `bot/runner.py`, `bot/memory.py`, `bot/ctx.py`, `bot/device.py`, `config.yaml` hoặc `src/aowbot/app/composition.py`.

## 4. Thứ tự bắt buộc (không đảo được)
1. Hợp đồng chung (`domain.marches`, `ActionSpec`, ports) có trước nơi dùng chúng.
2. World Model (B2b) có trước khi đánh giá goal (B3, B5/6).
3. Action Registry (B4) có trước khi Planner thực thi.
4. Planner dry-run + shadow (B6s) có trước khi tự hành (B7, MVP).
5. Có hồi quy cho hành vi cũ (F1, test của A-SAFE/A-FIX) trước khi thay hành vi cũ quan trọng.
6. Đo (F4L, A-MEAS-1) có trước mọi task A-OPT.
