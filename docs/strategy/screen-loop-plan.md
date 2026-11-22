# Kế hoạch: vòng phản ứng theo màn hình (Screen Loop)

Ngày: 2026-11-21 · Trạng thái: **S1 + S2 đã làm (chủ dự án duyệt 2026-11-21), chờ chạy thật 1 lượt + 1 lần kiểm**; S0, S3–S6 chờ duyệt (ADR-0012) · Nhánh: `roadmap-impl`

## 1. Vì sao cần

Chủ dự án nhận xét: "thuật toán agent đã bổ sung, còn hoạt động thì vẫn như cũ. Bỏ lỡ hầu hết các việc cần làm, độ thích nghi với màn hình là 0 %". Đánh giá lại thấy nhận xét này đúng:

- **[OBSERVED] Agent chưa từng chạy.** Bảng `decisions` và `events` có 0 dòng; log có 63 lỗi luồng SQLite từ 14:29. Lỗi này đã được sửa (chưa commit). Các máy để chế độ agent mất luôn bước `gather`.
- **[OBSERVED] Thiết kế:** agent chỉ quyết định *khi nào* ghé máy và chỉ có 3 hành động. Trong lần ghé, *cách làm* vẫn là các module cũ chạy theo `ORDER`. Mỗi module là một chuỗi cố định "tìm ảnh mẫu → chạm → chờ N giây → tìm ảnh mẫu tiếp". Màn hình khác dự kiến thì module trả 0 và thoát. Nó không đọc màn hình để biết chuyện gì xảy ra.
- **[INFERRED] Gốc sai của kế hoạch tổng:** nhận diện màn hình bị xếp vào nhóm "giữ nguyên" (A1), còn ưu tiên đặt vào lập lịch. Số đo giờ máy phí là đúng, nhưng chỗ hỏng chính nằm ở vòng trong: nhận ra màn hình rồi hành động.

### Bằng chứng (24 giờ tới 2026-11-21 17:00, `memory.db` mở `mode=ro`)

| Chỉ số | Giá trị | Nhãn |
|---|---|---|
| Lần ghé / lần chạm của bot | 240 / 8.600 | MEASURED |
| `quests`: lần có kết quả / tổng | 10/130 (264 phút) | MEASURED |
| `mainquest` | 8/143 (152 phút) | MEASURED |
| `reddots` kết thúc "ổn" | 11/170 (466 phút) | MEASURED |
| Dòng nhiệm vụ "Chính" → "Đến" → `none` | **363 lần** | MEASURED (log) |
| Màn `unknown` trong các bước điều hướng có hành động | 26,4 % | MEASURED (`nav`) |
| Chạm không đổi màn (`exp.outcome = none`) | 1.107 | MEASURED |

### Hai ca điển hình từ ảnh điều tra A-INV-1 (`logs/inv/`)

1. **Kiểm tra quá sớm.** Ảnh `quests_tab_2_main_row1`, máy #0/#2/#4: sau "Đến", game di camera tới công trình và hiện nút "Tăng cấp" phát sáng. Khi chụp lại, ảnh mẫu `build/btn_upgrade_icon` khớp **0,93–0,97**. Lúc `upgrade_here` kiểm tra thì camera còn đang trượt, nên không thấy nút và trả `none`. Nguyên nhân là module đợi một khoảng cố định 2,5 s thay vì đợi màn hình đứng yên rồi mới đọc.
2. **Game nói rõ lý do, bot không đọc.** Ảnh `quests_tab_2_main_row2..5`: game hiện thông báo "Khu vực tòa nhà này chưa được mở khóa, vui lòng mở khóa lô đất trước". Bot không đọc thông báo nên lần ghé nào cũng thử lại đúng dòng đó. Ở góc dưới còn có thanh "Nhiệm vụ đã hoàn thành – Nhận thưởng", nhưng luồng này bỏ qua nó.

Cả hai ca đều không cần thêm ảnh mẫu. Cái thiếu là **đọc màn hình sau mỗi thao tác và hiểu kết quả**.

## 2. Mục tiêu và tiêu chí đạt

Mục tiêu: mỗi thao tác đi theo vòng **Nhìn → Hiểu → Làm → Kiểm**. Việc cần làm được phát hiện từ màn hình, không lấy từ danh sách cố định.

| Chỉ số (cùng truy vấn trước/sau) | Hiện tại | Đích sau S4 |
|---|---|---|
| Dòng nhiệm vụ trả `none` / ngày | 363 | ≤ 30 |
| Lặp lại một thao tác đã biết là thất bại (cùng lý do, chưa hết TTL) | không đo được | 0 |
| Màn `unknown` trong điều hướng có hành động | 26,4 % | ≤ 10 % |
| Bước có kết quả / phút máy (`quests`+`mainquest`+`reddots`) | 18 / 882 phút | gấp ≥ 3 lần |
| Chạm không đổi màn | 1.107 / 8.600 | giảm ≥ 50 % |

Mọi số đo do `tools/report_ro.py` sinh ra, kèm thêm truy vấn mới ở S0.

## 3. Thiết kế

```
            ┌──────────── Perception (hàm thuần, ảnh → ScreenReading) ────────────┐
 screencap ─┤ loại màn (identify + kNN + screen_types)   thông báo game (OCR dải giữa) │
 (đã đứng   │ cơ hội: nút Nhận xanh, chấm đỏ, thanh nhiệm vụ "hoàn thành"            │
  yên)      │ nút nguy hiểm (imitate.is_danger)   độ tin cậy                           │
            └──────────────────────────────┬──────────────────────────────────────┘
                                           ▼
   World view (aowbot) ← dữ kiện có TTL: "việc đang có" + "việc bị chặn, lý do, tới khi nào"
                                           ▼
   Planner/Utility (đã có) → Skill (kỹ năng): tiền điều kiện màn + thao tác + hậu điều kiện màn
                                           ▼
   Executor: làm 1 thao tác → đợi màn đứng yên → đọc lại → so với hậu điều kiện
             khớp → tiếp · lệch → diễn giải ScreenReading (thông báo / popup / unknown) → ghi dữ kiện → quyết định lại
```

Nguyên tắc:
- **Perception là hàm thuần** `read_screen(img) -> ScreenReading`, test offline trên ảnh `logs/inv`, `logs/shots`, `logs/human`, `tests/fixtures` (chỉ chạy local, theo quyết định "không đưa ảnh vào git"). Tuân theo ADR-0011.
- **Đợi đứng yên thay vì ngủ cố định:** sau mỗi lần chạm, chụp tới khi 2 khung liên tiếp giống nhau (`screens.same`) hoặc hết trần thời gian. Dùng chung cho mọi module qua `Ctx`.
- **Thông báo game là dữ kiện:** bảng ánh xạ "mẫu chữ → kết quả" (chưa mở khóa lô đất, thiếu tài nguyên, hết thợ, đạt cấp tối đa, cần điều kiện tiên quyết...) → ghi `blocked(subject, reason, until)` vào world view. Planner không chọn lại việc đó trước `until`.
- **Cơ hội phát hiện ở mọi màn**, không chỉ trong bước tương ứng. Ví dụ đang ở thành phố mà thấy thanh "Nhận thưởng" thì đó là một việc ứng viên.
- **An toàn không đổi:** Policy đứng trước Executor; nút nguy hiểm luôn chặn (dùng lại `imitate.is_danger` và luật "Miễn phí"); không tiêu kim cương; tối đa 2 máy.
- **Không thay toàn bộ một lần:** module cũ được bọc thành Skill. Skill nào đã có hậu điều kiện rõ thì Executor kiểm; chưa có thì giữ hành vi cũ.

### Quan hệ với chế độ "học mẫu" (#3)
`bot/imitate.py`, `bot/screen_types.py`, `bot/demo.py` (đang làm ở luồng khác, chưa commit) cung cấp: loại màn chi tiết + mục đích chạm (close/claim/progress/open), mẫu kNN và bộ chặn nút nguy hiểm. Vòng màn hình **dùng các thành phần này làm nguồn chính sách thứ hai** (sau luật cứng). Không viết lại chúng, và không sửa song song các file đó (ma trận sở hữu).

## 4. Các giai đoạn

Mỗi giai đoạn là 1–3 commit, có test, có số đo trước/sau, và chủ dự án duyệt trước khi bắt đầu.

| # | Việc | File chính | Nghiệm thu |
|---|---|---|---|
| **S0** | Đo nền: thêm vào `report_ro` các chỉ số ở mục 2; dựng bộ ảnh đánh giá local từ `logs/inv`, `logs/shots`, `logs/human` kèm nhãn tay tối thiểu | `tools/report_ro.py`, `tools/screen_eval.py` (mới) | Bảng mục 2 tái lập được bằng 1 lệnh |
| **S1** | Đợi đứng yên + kiểm hậu điều kiện cho "Đến" (nhiệm vụ) và `upgrade_here`. Đọc lại màn tới khi ổn định trước khi trả `none` | `bot/ctx.py` (hàm `settle()`), `bot/build.py`, `bot/modules/quests.py` | Phát lại ảnh row1: thấy nút Tăng cấp; chạy thật 1 lượt + 1 lần kiểm: `none` của dòng "Chính" giảm rõ |
| **S2** | Đọc thông báo game (OCR dải giữa, có cache) → bảng lý do → dữ kiện `blocked` có TTL; nhiệm vụ/công trình bị chặn thì không thử lại trước hạn | `src/aowbot/domain/blockers.py` (mới, luật thuần), `bot/game_msg.py` (mới, đọc), adapter | Test thuần bảng ánh xạ; ảnh row2..5 → "lô đất chưa mở"; số lần lặp cùng lý do = 0 |
| **S3** | `read_screen()`: loại màn + cơ hội (nút Nhận xanh theo màu, chấm đỏ, thanh nhiệm vụ "hoàn thành", nút Đến) + nút nguy hiểm + độ tin cậy | `src/aowbot/domain/screen.py` (kiểu), `bot/perception.py` (cài đặt), tái dùng `screens`, `badges`, `imitate` | Trên bộ ảnh S0: độ chính xác loại màn ≥ 90 %, cơ hội "Nhận" recall ≥ 90 % / precision ≥ 95 %; `unknown` ≤ 10 % |
| **S4** | World view nhận "việc đang có" + "việc bị chặn"; thêm goal `ClaimRewards`, `QuestProgress`; Skill có tiền/hậu điều kiện màn; Executor kiểm hậu điều kiện, lệch thì diễn giải | `src/aowbot/application/*`, `infrastructure/legacy/skills.py` | Shadow trên #1: agent nêu được ≥ 90 % việc mà ORDER làm được, và thêm các việc ORDER bỏ sót |
| **S5** | Bật vòng màn hình trên **#1** thay cho ORDER (các farm giữ `smart`); 1 lượt + 1 lần kiểm | `data/settings.json` (chủ dự án bật) | Các chỉ số mục 2 đạt đích; không có thao tác nguy hiểm nào trong `exp` |
| **S6** | Mở rộng sang farm; gỡ dần các nhánh trong module cũ mà Skill đã thay | theo migration-map | Chỉ gỡ khi grep + số đo xác nhận |

Chuỗi phụ thuộc: S0 → S1 → S2 → S3 → S4 → S5 → S6. S1 và S2 có giá trị ngay cả khi chưa có agent (sửa thẳng ca 363 lần `none`).

## 5. Rủi ro

- **Đợi đứng yên làm chậm** những màn có hoạt ảnh liên tục (bản đồ, hiệu ứng): đặt trần thời gian và so sánh trên vùng ROI thay vì cả màn. Đo bằng bảng `perf`.
- **OCR thông báo đọc sai** vì Tesseract chỉ có gói `eng` (mất dấu): so khớp gần đúng theo từ khóa không dấu, như `ocr.py` đang làm. Không khớp thì coi là "lý do không rõ" và không chặn lâu.
- **Phát hiện "Nhận" nhầm nút trả phí:** Policy và `is_danger` luôn chạy trước khi chạm; ở S3 precision phải ≥ 95 % mới được bật.
- **Hai luồng sửa cùng file** (`ctx.py`, `quests.py` với chế độ học mẫu): làm tuần tự, commit phần đang dở của luồng học mẫu trước khi bắt đầu S1.

## 6. Cần chủ dự án quyết

1. **Chế độ máy ngay bây giờ:** `data/settings.json` đang để `agent` cho cả #0–#6, trong khi kế hoạch là chỉ #1. Đề xuất: farm về `smart`, #1 giữ `agent` sau khi khởi động lại với bản sửa luồng.
2. **Thứ tự làm:** S1 + S2 trước (sửa thẳng lỗi đang tốn giờ máy), rồi mới S3–S5.
3. **Máy thử S5:** #1 (tài khoản chính, nhiều màn nhất) hay #3 (đã có dữ liệu học mẫu).
4. **Phần chưa commit của chế độ học mẫu** (`imitate`, `screen_types`, `demo`, `human_review`...): commit trước để S1 không đụng vào thay đổi đang dở.
