# Roadmap triển khai

Ngày: 2026-11-21 · Trạng thái: **chờ duyệt** · Thuộc [MASTER-IMPLEMENTATION-PLAN.md](MASTER-IMPLEMENTATION-PLAN.md)

Đồ thị phụ thuộc: [task-dependency-graph.md](task-dependency-graph.md). Sở hữu file: [workstream-ownership.md](workstream-ownership.md).

**Quy ước công sức (tương đối):** 1 = nhỏ (≤ nửa ngày, 1 commit) · 2 = vừa · 3 = lớn (nhiều commit, có thể chia nhỏ khi làm) · 5 = rất lớn (phải chia nhỏ trước khi làm).

**Luật thực thi:**
- Mỗi task chỉ bắt đầu khi chủ dự án duyệt (ADR-0012).
- Mỗi task là 1 nhánh và 1–n commit nhỏ, có test, có số đo trước/sau (F4-lite hoặc A-MEAS-1).
- Task nào cần chạy máy ảo thì **chủ dự án bật máy** (tối đa 2 instance, CLAUDE.md quy tắc 4).

## 0. Trạng thái (cập nhật 2026-11-21, nhánh `roadmap-impl`)

| Nhóm | Đã xong (có test, có commit) | Còn lại và vì sao |
|---|---|---|
| Nền F | F0, F1, F2, F3, F4L | F4 (benchmark trong `aowbot`) chờ có số liệu `perf` thật; CI chỉ chạy khi chủ dự án push |
| An toàn | A-SAFE-1..4 | A-SAFE-5: điều tra thêm trên fixture |
| Độ tin cậy / đo | A-REL-1..4, A-MEAS-1, A-INV-1, A-CFG-1, A-DUP-2, A-DEAD-1 | Cần **1 lượt chạy thật** (chủ dự án bật máy) để bảng `perf` và `logs/inv/` có dữ liệu |
| Lập lịch | A-FIX-1a/1b, A-FIX-2, A-FIX-3 | Đo trước/sau bằng `tools/report_ro.py --split` sau 24 h chạy thật |
| Tối ưu A-OPT-2..7 | – | **Chưa làm có chủ đích**: luật "không tối ưu khi chưa đo"; chờ dữ liệu `perf` |
| A-OPT-1, `rebels.join` | A-OPT-1 (P1, 2026-11-23, xem mục 0b) | `rebels.join` chờ chủ dự án quyết định |
| Agent | B2a, B2b, B1, B3, B4, POL, B5/6, B6s, B7, B9a, SCH-X, B-UI | **MVP chưa bật**: chủ dự án đặt `schedule.mode: agent` cho #1 rồi chạy 1 lượt + 1 lần chạy lại; B9b (giữ máy bật) chờ ngưỡng `keep_alive_min`; B3+, B8 sau MVP |

Kiểm tra trên nhánh: 283 test pass; `mypy --strict src/aowbot` sạch; 6/6 hợp đồng import-linter; ruff sạch; hồi quy ảnh 13/13, 34/34.

## 0b. Giai đoạn P1 "Ổn định nền" (PM duyệt 2026-11-23, nhánh `p1-on-dinh-nen`)

Nguồn: báo cáo rà soát `logs/pm-audit-1.txt` (21/11 23:00 → 22/11 23:39: ~28 % lần ghé lỗi/bỏ dở, `reddots` ~30 % thời gian máy, chụp màn hình lỗi mất 39 phút, các bước luôn trả 0 mất ~25 phút).

| Việc | Đã làm | File | Tham số (`config.yaml`) |
|---|---|---|---|
| A-OPT-3 | Chụp màn hình: timeout 8 s/lệnh (trước 20 s), 3 lần thử, ngân sách 30 s, 2 lần timeout liên tiếp = máy treo, dò lại địa chỉ ADB 1 lần 15 s; không cứu được → `Device.dead` → runner bỏ lượt máy ngay, sang máy kế tiếp (không backoff bước) | `bot/device.py`, `bot/runner.py` | `ldplayer.screencap.*` |
| Lỗi agent `gather` | `'tuple' object has no attribute 'fact'`: biến trí nhớ `m` bị ghi đè bởi `read_marches()`; đã sửa từ b5a7106 (đổi tên `mem`/`mv`), nay thêm test hồi quy qua `LegacyActionRunner` | `tests/legacy/test_agent_gather_dispatch.py` | – |
| Bước luôn trả 0 | `bot/stepgate.py`: điều kiện trước khi chạy (warday: mốc thể lực / ngày chiến tranh; mainquest: đang xây / chờ lực chiến; campaign: chờ lực chiến hoặc tới hạn nhận treo máy; heal: thấy bong bóng chữa trị hoặc vừa có trận) + trả 0 liên tiếp thì giãn chu kỳ theo máy (fact `idle:<bước>`, `state.json` → `idle_backoff`); lịch không kéo máy cho bước bị bỏ | `bot/stepgate.py`, `bot/runner.py`, `bot/scheduler.py`, `observe.py`, `campaign.py` | `stepgate.*`, `campaign.power_gain_pct`, `campaign.idle_claim_h` |
| A-OPT-1 | `reddots` không chạy mỗi lần ghé: tối đa 1 lần / 30 phút / máy (sớm hơn khi `notify` vừa nhận được quà hoặc có chấm đỏ mới), tối đa 90 s / lần, icon mở ra vô ích bỏ qua 2 giờ rồi gấp đôi (tối đa 24 giờ) | `bot/modules/reddots.py` | `reddots.max_s`, `reddots.min_interval_min`, `reddots.dead_h`, `reddots.dead_cap_h` |

Kiểm chứng (chủ dự án bật máy): 1 lượt chạy thật đầy đủ + 1 lần chạy lại, rồi `python tools/report_ro.py --split "<giờ bắt đầu P1>"`. Tiêu chí: lần ghé lỗi/bỏ dở < 5 %; `reddots` < 15 % thời gian máy; không còn lần chụp màn hình lỗi > 60 s; heal/campaign/warday/mainquest không còn chạy trả 0 ở mọi lần ghé.

## 0c. Giai đoạn P2 "Hàng chờ luôn chạy" (PM duyệt 2026-11-23, nhánh `p2-hang-cho` tách từ `p1-on-dinh-nen`)

Mục tiêu (theo `logs/pm-audit-1.txt`): thời gian bỏ trống xây < 25 % (đang 54 %), nghiên cứu < 30 % (đang 71 %), huấn luyện < 20 % (đang 37 %).

| Việc | Đã làm | File | Tham số (`config.yaml`) |
|---|---|---|---|
| P2-1 đọc "1/1" | Đọc số "x/y" của cột icon trái bằng **ảnh chữ số** `templates/qdigits/` (0, 1, 1b, 2, 3, slash; cắt từ ảnh thật, khớp xám, ~1 ms) trước, OCR bỏ phiếu sau; **chấm đỏ** trên icon = còn chỗ rảnh → không đọc được số nhưng biết tổng (nghiên cứu luôn 1, hoặc tổng lần trước) thì coi là `(tổng−1)/tổng`; đọc "đầy" mà có chấm đỏ → bỏ (mâu thuẫn). Trên 291 ô icon trong `tests/fixtures` + `logs/` đọc đúng 290 (1 ô bị icon quà che → không rõ, đúng); OCR cũ hụt 62 ô (18 ô "1/1" nghiên cứu, 4 ô "3/3", 27 ô "0/1" huấn luyện) | `bot/queues.py`, `bot/modules/observe.py` (`known_totals`), `bot/runner.py` | – |
| P2-2 `construct_no_spot` | Kéo thẻ hỏng (không chỗ / không tick / không xác nhận / thiếu tài nguyên) → hủy đặt bằng nút X (`build/btn_bar_close`), nhớ thẻ theo (nhóm, cột) và bỏ qua 2 giờ, hỏng lại gấp đôi (tối đa 24 giờ; thiếu tài nguyên chỉ 1 giờ); mở lại nhóm để thử **thẻ khác**, rồi nhóm khác; tối đa 2 lần hỏng / lượt; xem hết nhóm có chấm đỏ mà không còn thẻ hợp lệ → không mở bảng Xây dựng tới khi thẻ sớm nhất hết hạn (thợ để cho `upgrade`/`quests`). Nhà chính lên cấp → thử lại ngay | `bot/modules/construct.py` | `construct.max_fail_per_run`, `nospot_backoff_h`, `nospot_cap_h`, `empty_recheck_h` |
| P2-3 chọn mục nghiên cứu | "Khuyến khích" trước, rồi nhánh theo `branch_order` (Phát triển > Đào tạo > Quân sự), trong nhánh trên → dưới; bỏ node vừa hỏng (`research_skip`, 6 giờ); tối đa 3 node / lượt, 150 s. Sau khi bấm "Nghiên cứu" **kiểm lại** (hộp thoại thiếu tài nguyên / nút còn nguyên / thanh tiến độ) thay vì tin 1 lần bấm. Thiếu tài nguyên → `research_nores` 60 phút, gấp đôi tới 6 giờ; lịch (`plan_research`) và agent (`legacy_research`) cùng tôn trọng. Hàng nghiên cứu đọc được "0/1" → lịch kéo máy sớm (giãn khi bấm mà không bắt đầu được). Thiếu ảnh mẫu bảng node → log `thieu anh mau research/...` (1 lần/giờ), dùng màu + chữ (chặn "… ngay") | `bot/modules/research.py`, `bot/tplneed.py`, `bot/scheduler.py`, `src/aowbot/application/planning.py` | `research.branch_order`, `pages_per_branch`, `max_nodes_per_run`, `node_skip_h`, `nores_backoff_min`, `nores_cap_h`, `max_s` |
| P2-4 huấn luyện | `use_max_button` mặc định bật: có `train/btn_max` thì bấm, thiếu thì log `thieu anh mau train/btn_max` và giữ số mặc định (không bấm mò thanh trượt). Icon cột trái báo đầy (3/3, 1/1) → bỏ qua không mở bảng. Sau "Huấn luyện" kiểm nút còn không (2 lần) → thiếu tài nguyên → `train_nores` 30 phút, gấp đôi tới 4 giờ | `bot/modules/train.py` | `train.use_max_button`, `nores_backoff_min`, `nores_cap_h` |

**Lưu ý đo:** `queue_obs` chỉ ghi lần quan sát **đọc được số**. Trước P2, "1/1" (nghiên cứu bận) và "3/3" thường không đọc được nên bị bỏ khỏi mẫu, còn "0/1" (rảnh) đọc được → tỉ lệ bỏ trống cũ (nghiên cứu 71 %, huấn luyện 37 %) **bị thổi phồng**. So trước/sau phải tính cả phần này.

Ảnh mẫu chủ dự án cần chụp (trên #1, máy 540×960; `python tools/snap.py todo research` / `todo train` để xem lại): `research/btn_research`, `research/node_panel`, `research/msg_no_res`, `train/btn_max` (`common/msg_insufficient` dùng chung). Thiếu ảnh thì code vẫn chạy (đường màu + chữ / số mặc định).

Kiểm chứng (chủ dự án bật máy): 1 lượt chạy thật đầy đủ + 1 lần chạy lại, rồi `python tools/report_ro.py --split "<giờ bắt đầu P2>"`, xem mục "hang cho (lan quan sat con cho ranh)".

## 0d. Giai đoạn P3 "Thu thập đầy hành quân" (PM duyệt 2026-11-23, nhánh `p3-thu-thap` tách từ `p2-hang-cho`)

Mục tiêu (theo `logs/pm-audit-1.txt`): "Hành quân x/y" luôn đầy — trên máy #1 đầy ≥ 90 % số lần quan sát; **0 lần Hủy oan**.

| Việc | Đã làm | File | Tham số (`config.yaml`) |
|---|---|---|---|
| P3-1 đọc "Hành quân x/y" | Đọc bằng **ảnh chữ số** `templates/mdigits/` (1–5, slash; cắt từ ảnh thật, dùng chung `queues.read_glyph_box`) → Tesseract → `digits/`. Khung "Hành quân" (`gather/march_header`) **chỉ hiện khi có đội đang đi**: trên bản đồ thế giới (thấy kính lúp) mà vắng khung + biết tổng → 0 đội. Đo trên 547 ảnh bản đồ có khung: ảnh chữ số đúng 544, sai 0, 3 ảnh mờ → không rõ; Tesseract cũ sai 3 (5/5 → 3/5) và hụt 7; 2214 ảnh khác: 0 đọc nhầm. `observe` ghi `march_obs` (used/total/reserve/nguồn) | `bot/march_count.py`, `bot/ctx.py` (`read_marches`), `bot/queues.py`, `bot/modules/observe.py`, `bot/memory.py` | `gather.ocr: auto`, `gather.infer_zero` |
| P3-2 hộp thoại sau "Xuất chinh" | Hộp thoại là **"Chú ý! Có Chỉ huy trưởng khác đang hành quân đến điểm tài nguyên này… muốn tiếp tục xuất chinh? [Hủy] [Tiếp tục]"**. Log #1 22/11 16:44–16:48: cả 7 lần là đội **của mình** (cùng loại/cấp, cùng thời gian đi 1008 s, gửi 51 s trước) — mỏ đầy gần nhất chỉ hết "đầy" khi đội tới nơi nên "Tìm kiếm" trả lại đúng mỏ đó. Giờ: (loại, cấp) có đội mình đang đi tới → không tìm (`own_skip`); cùng loại/cấp + cùng thời gian đi → không bấm Xuất chinh (`own`); hộp thoại vẫn hiện (ảnh `gather/dlg_contested` hoặc OCR) → **Hủy, không bao giờ Tiếp tục**, tạm bỏ (loại, cấp) | `bot/gather_rules.py` (`own_target`), `bot/modules/gather.py` | `gather.contested_skip_min` (20) |
| P3-3 mỏ bị chiếm / thông báo | `mine_occupied`, `msg_not_found`, `msg_march_full`, `msg_no_troops`: thiếu ảnh mẫu → `tplneed` log `thieu anh mau <tên>` (1 lần/giờ) + OCR thông báo (`gather_rules.classify_msg`) chỉ ở nhánh thất bại; mỏ bị chiếm / không tìm thấy → tạm bỏ (loại, cấp) qua các lần ghé (fact `gather_hold:<loại>:<cấp>`), thử cấp/loại khác; không bấm nút nào trên mỏ người khác | `bot/gather_rules.py`, `bot/modules/gather.py` | `gather.occupied_skip_min` (30), `notfound_skip_min` (30) |
| P3-4 giảm `gather_unread` | 111/111 lần `gather_unread` (21–22/11) là **trữ lượng None** (OCR trên nền cây sáng), tải trọng đọc được cả 111. Bảng dung tích mỏ đầy `gather.mine_caps` (đo từ `memory.db` + log + chủ dự án): chỉ mỏ đầy + OCR hỏng/lệch [0,9; 1,25]× dung tích → dùng dung tích (số lớn nhất = an toàn cho luật tải trọng ≥ mỏ); biết dung tích thì đọc 1 lần thay vì 3 | `bot/gather_rules.py` (`choose_amount`), `bot/modules/gather.py` | `gather.mine_caps` |

Ảnh mẫu chủ dự án cần chụp (trên #1, `python tools/snap.py todo gather`): `gather/msg_not_found` (thông báo nổi giữa màn sau "Tìm kiếm" khi không có mỏ), `gather/mine_occupied` (chạm mỏ đang có đội người khác: menu không có xe tải "Thu thập"), `gather/msg_march_full` (bấm "Thu thập" khi hành quân đã đầy), `gather/msg_no_troops` (bấm "Thu thập"/"Xuất chinh" khi hết lính). Chi tiết vùng cắt: [templates/README.md](../../templates/README.md). Thiếu ảnh thì code vẫn chạy bằng OCR thông báo.

Kiểm chứng (chủ dự án bật máy): 1 lượt chạy thật đầy đủ + 1 lần chạy lại trên #1, rồi `python tools/report_ro.py --split "<giờ bắt đầu P3>"`, xem mục `march` (% lần quan sát hành quân đầy, mục tiêu ≥ 90 %) và `gather_ev` (`own_dialog` = Hủy oan, mục tiêu 0; `contested`, `occupied`, `cap_table`, `own_skip`).

## 0e. Giai đoạn P4 "Nhiệm vụ và lên cấp farm" (PM duyệt 2026-11-23, nhánh `p4-nhiem-vu` tách từ `p3-thu-thap`)

Mục tiêu (theo `logs/pm-audit-1.txt`): farm tự lên nhà chính 9 rồi 15. Tiêu chí: `follow_stuck` giảm ≥ 70 %; mỗi farm lên ≥ 1 cấp nhà chính mỗi ngày.

**Phân tích (P4-1, `python tools/follow_stats.py [--replay] [--human]`, chỉ đọc log/ảnh):**
- Log 20–22/11: follow dừng vì "không nhận ra màn hình" 117 lần, "đạt giới hạn bước" 63, "Back không qua" 2. Theo bước gọi: `mainquest` kẹt 76 / hết bước 30 / idle 59; `quests` idle 137 / weak 71 / kẹt 47 / hết bước 38. 85/117 lần kẹt là follow **bắt đầu** trên màn mà `decide()` không biết (chờ 2 nhịp → chạm giữa 3 lần → dừng).
- 129 ảnh `follow_stuck` theo loại màn: **bản đồ thế giới 52** (thanh nhiệm vụ "Tham gia tập kết tấn công 1 lần phản quân Cơ giáp" đưa ra bản đồ; chạm giữa mở menu ô đất "Chuyển thành / Chiếm lĩnh"), **bảng nhiệm vụ kiểu mới 38** (nút X đỏ góc trên-phải thay cho nút đóng cũ → luật bảng Chương không khớp, nút "Nhận toàn bộ" ngay trước mặt), **bản đồ Tình báo 24**, bảng có nút "<" 6, popup X 4 ("Gia nhập liên minh!"), chiêu mộ 3, tướng 1, khác 1.
- 78 ảnh `follow_maxsteps`: 58 ở **chế độ xây** (kéo thẻ 8 lần không ra ô xanh → "chế độ xây: chờ" tới hết 40 bước), thành phố 11, bảng "<" 7.
- Tab Chính: 472 lần "Đến" → `none` — các dòng là huấn luyện / giết phản quân / tướng / đấu trường, không phải xây.
- Chiến dịch 14/14 trả 0: 8/8 ảnh `campaign_no_fight` là màn **"Cài đặt quân đoàn" kiểu mới** ("Đội hình đề xuất" + "Chiến đấu" đỏ; `campaign/btn_fight` chỉ khớp 0,77); nhận Lợi ích treo máy không được tính là làm việc.
- Nhà chính: 7/7 ảnh `build_blocked` ngày 22/11 thực ra là **"Tăng cấp thành công!"** (nâng ngay miễn phí) → bị tính `blocked` → kế hoạch nhà chính lùi 1 giờ và giữ thợ 2 giờ vô lý.
- Thao tác tay `logs/human` (2 531): trong bước mainquest/quests có 719 thao tác, trong đó 492 lần "kéo" 3–7 giây từ (80,860) là **chính bot** (sendevent kéo thẻ công trình) bị bộ ghi bắt lại — loại khỏi phân tích. Chuỗi tay thật: (a) "Kích sát phiến quân Lv.1": chạm thanh nhiệm vụ → mục tiêu giữa màn → bảng "Phiến quân Lv.1" (Đề xuất 5 000) → "Tấn công" → màn quân đoàn → Xuất chinh (#3 21/11 00:20); (b) bảng nhiệm vụ: tab có chấm đỏ → "Nhận" → X; (c) bản đồ thế giới / Tình báo: mũi tên "<" góc trên-trái; (d) tập kết Phản quân Cơ giáp Lv.1 trên #4 (nhà chính 4): "Tập kết tấn công" → 3 phút → Xác nhận — **chưa tự động** (bước `rebels` chỉ từ nhà chính 15, cần chủ dự án quyết).

| Việc | Đã làm | File | Tham số (`config.yaml`) |
|---|---|---|---|
| P4-1 phân tích | Công cụ chỉ-đọc: kết quả follow theo bước gọi, ảnh kẹt theo loại màn, phát lại `decide()` mới trên ảnh kẹt cũ, thao tác tay theo loại màn; `report_ro` thêm `follow` (đếm ảnh theo khoảng) + `hq` (cấp nhà chính đầu/cuối khoảng, cấp/ngày từ fact `hq_history`) | `tools/follow_stats.py`, `tools/report_ro.py` | — |
| P4-2 luật follow (học từ ảnh kẹt + thao tác tay) | `bot/quest_rules.py` (hàm thuần): `classify()` chữ nhiệm vụ OCR (mất dấu, sai ký tự) → loại + bước phụ trách; `follow_screen()`; `decide()` ở chế độ follow: bảng nhiệm vụ kiểu mới → Nhận toàn bộ / Nhận / X; bản đồ thế giới, Tình báo → ra (**không bao giờ chạm giữa bản đồ**); bảng "<" → quay lại; popup X góc trên → đóng (không bấm "Gia nhập"); chế độ xây hết kéo → hủy bằng X (`build_no_spot`) để bước `construct` làm. Phát lại offline: **126/129** ảnh kẹt và 75/78 ảnh hết bước nay có lối ra (tutorial thường không đổi: `check_tutorial` 34/34) | `bot/quest_rules.py`, `bot/modules/tutorial.py` | — |
| P4-3 nhiệm vụ chính / chương | `mainquest`: OCR thanh nhiệm vụ → loại; việc của bước khác (tập kết, huấn luyện, tình báo, đấu trường, thu thập, nghiên cứu, chiêu mộ, liên minh) → **không chạm**, trả 0 (stepgate giãn chu kỳ); "Kích sát phiến quân" → chuỗi học từ tay (chỉ khi tiêu đề OCR là "Phiến quân Lv.N", không phải Cơ giáp / người chơi, cấp ≤ `npc_max_level`, đề xuất ≤ lực chiến × `npc_max_ratio`; hộp thoại tranh chấp → Hủy); kiểm kết quả thật sau mỗi bước = chữ thanh nhiệm vụ đổi hoặc xây/thắng/xuất chinh; cùng nhiệm vụ thất bại ≥ 2 lần → không chạm lại trong `same_retry_h` × 2ⁿ giờ. `quests`: OCR tên dòng trên nút "Đến", dòng của bước khác → không bấm | `bot/modules/mainquest.py`, `bot/modules/quests.py`, `bot/quest_rules.py` | `mainquest.read_banner`, `npc_rebels`, `npc_max_level` (10), `npc_max_ratio` (0.3), `same_retry_h` (1), `same_retry_cap_h` (8); `quests.read_rows` |
| P4-4 chiến dịch | Màn "Cài đặt quân đoàn" kiểu mới: dùng ảnh mẫu `play/btn_arena_recommend` + `play/btn_arena_fight` (khớp 1,00) — luôn "Đội hình đề xuất" trước; chỉ đánh khi bảng màn đã dự đoán "Thắng toàn diện" (`pre_checked`), không thì thoát. Nhận Lợi ích treo máy tính là làm được việc | `bot/modules/campaign.py` | — |
| P4-5 ưu tiên nhà chính | `upgrade_here` nhận "Tăng cấp thành công!" (OCR) = `started`; `build.hq_targets` [9, 15]: dưới mục tiêu → dòng nhiệm vụ "Xưởng kiến trúc" làm trước; `mainquest` nhiệm vụ xây nhường thợ khi kế hoạch nhà chính đang giữ thợ (`hqplan.yield_builder`, cùng hàng chờ xây P2); `observe` ghi `hq_history` (log "Nhà chính: cấp a -> b (mục tiêu kế tiếp c)") | `bot/build.py`, `bot/modules/observe.py`, `src/aowbot/domain/hqplan.py` (`next_target`, `hq_rush`), `bot/modules/quests.py`, `bot/modules/mainquest.py` | `build.hq_targets` |

Ảnh mẫu: không bắt buộc chụp thêm — `rebels/npc_attack` đã cắt từ thao tác tay (chủ dự án nên kiểm lại trên một phiến quân cấp khác); thiếu ảnh thì bước "Kích sát phiến quân" bỏ qua nhanh + log `thieu anh mau rebels/npc_attack`. Màn cần chủ dự án **làm mẫu tay** (`tools/record.py`, máy farm): tập kết Phản quân Cơ giáp trên farm nhà chính < 15 (có cho bot làm không?), đặt công trình khi không có ô xanh (Bệnh viện trên vùng tối chưa mở rộng), màn "Nâng cấp chiến cơ", nhiệm vụ "Huấn luyện N Tank bậc X" (bậc khác T3).

Kiểm chứng (chủ dự án bật máy, tối đa 2 máy): 1 lượt chạy thật đầy đủ trên 2 farm (vd #3, #4) + 1 lần chạy lại, rồi `python tools/report_ro.py --split "<giờ bắt đầu P4>"` (mục `follow`: ảnh kẹt/hết bước so với trước; bảng bước: `mainquest`, `campaign`, `quests` trả 0; mục `hq` sau ≥ 1 ngày) và `python tools/follow_stats.py --since <ngày>` (kết quả follow + loại màn còn kẹt).

## 0f. Giai đoạn P5 "Chiến đấu và tình huống hiếm" (PM duyệt 2026-11-23, nhánh `p5-chien-dau` tách từ `p4-nhiem-vu`)

Mục tiêu (theo `logs/pm-audit-1.txt`): phản quân, tình báo, bệnh viện, phòng thủ có kết quả. Tiêu chí: phản quân có kết quả ≥ 50 % khi đủ điều kiện; tình báo "unknown" dưới 10 %.

**Phân tích (chỉ đọc log, ảnh, bảng `exp` trong `data/memory.db`):**
- Tình báo 22/11: 92 ghim, **64 "unknown" (69,6 %)**; cả 20–22/11: 172/249 (69,1 %). Phân loại theo nhật ký chạm sau nút "Đi": **31** lần bấm "Tấn công" rồi không nhận ra màn kế (không có "Chiến đấu" / "Xuất chinh" kiểu cũ, phần lớn ở #1 nhà chính 30); **22** lần ảnh mẫu ghim mục tiêu `intel/marker_fight` (ngưỡng 0,55, tìm cả màn) khớp nhầm góc trái dưới → chạm (97,805), rồi 3 điểm cố định đều trượt; **3** lần không thấy ghim; **11/11** ảnh `intel_panel_unknown` là bảng "Chúc mừng nhận được" (ghim hộp quà) — ảnh mẫu `common/msg_reward` khớp 0,79–0,93 trên ảnh lưu sau đó, nhưng lúc kiểm tra bảng còn đang hiện (hiệu ứng tia sáng đè tiêu đề).
- Phản quân: 33 lần chạy, 0 có kết quả. Chỉ #1 đủ nhà chính 15; Lv.10 dự đoán không thắng → cả lượt trả 0 (mỗi lượt chỉ thử 1 cấp, rồi chạm lại cùng mục tiêu 2 lần). `rebels.join_mech_rally` trong `config.yaml` đang là `true` nhưng không có tác dụng vì thiếu ảnh mẫu.
- Bệnh viện: 59 lần chạy (13 + 15 phút), 0 có kết quả; P1 đã thêm cổng điều kiện, nhưng khi cổng cho chạy thì vẫn mở bệnh viện ra xem. **42 ảnh `heal_no_target` không thuộc bước `heal`** mà là sự kiện "chữa thương" (`notify.heal_event`); bộ dò vòng vàng hiện tại đã bắt được 35/42 ảnh (bản sửa ac6ef78 tối 22/11); thử nới rộng thì bắt thêm 1/7 nhưng báo nhầm 65/120 ảnh khác → giữ nguyên.
- Phòng thủ: thiếu `defense/alert_attack`, `defense/row_8h`; `shield(hours=8)` (ngày chiến tranh) mở bảng rồi mới báo "Không thấy dòng khiên 8h".

| Việc | Đã làm | File | Tham số (`config.yaml`) |
|---|---|---|---|
| P5-1 tình báo | `intel_rules.panel_kind()` + chờ tới 3 s bảng nhiệm vụ / bảng quà (thay vì xét 1 khung); ghim mục tiêu chỉ tìm giữa màn (`MARKER_ROI`, ngưỡng 0,6); sau "Tấn công" nhận thêm màn "Cài đặt Quân đoàn" kiểu mới (`rebels/btn_march_out`), **chỉ Xuất chinh khi dự đoán "Thắng toàn diện"** (không thì `lose_pred`, bỏ ghim); "unknown" tách lý do `unknown_panel` / `unknown_target` / `unknown_attack` + 1 ảnh/ngày/máy `logs/inv/intel_*`; chỉ `unknown_panel` mới thử 1 viên thuốc thể lực (trước: mọi unknown). `report_ro`: mục `intel` (% unknown từ log, đọc cả định dạng log cũ) + `combat` | `bot/intel_rules.py`, `bot/modules/notify.py`, `tools/report_ro.py` | — |
| P5-2 phản quân | 1 lượt thử tối đa `search_tries` cấp (cấp kế tiếp rồi hạ dần, bỏ cấp vừa dự đoán thua); dự đoán thua → sang cấp thấp hơn ngay; ô tìm kiếm hỏng / không có tab Cơ giáp → dừng; `join` **mặc định TẮT**, thiếu `rally_mech`/`btn_join` → log "thieu anh mau", không mở bảng liên minh; ghim tình báo Phản quân Cơ giáp: `intel_rally_min_hq` (0 = như cũ) chờ chủ dự án quyết | `bot/modules/rebels.py`, `bot/modules/notify.py`, `web/options.py` | `rebels.join_mech_rally` (**false**), `rebels.search_tries` (3), `rebels.intel_rally_min_hq` (0) |
| P5-3 bệnh viện | Không thấy bong bóng chữa trị (`build/heal_bubble`) và lượt ghé chưa có trận (rebels / bị tấn công) → trả 0 ngay, **không chạm bệnh viện**; runner ghi `done["defense"]` khi bị đánh để heal bắt buộc. Vẫn chỉ nút "Hồi phục" bằng tài nguyên | `bot/modules/heal.py`, `bot/runner.py` | `heal.open_without_bubble` (false) |
| P5-4 phòng thủ | `shield()` kiểm ảnh mẫu icon khiên / tiêu đề / dòng khiên **trước khi mở bảng** → `missing_tpl`; `alert_attack` qua `tplneed` (log 1 lần/giờ), vẫn dùng mép đỏ nhấp nháy. Luật khiên giữ nguyên (A-SAFE-1, ADR-0008): ngày chiến tranh chỉ vật phẩm; mua bằng kim cương chỉ khi `defense.shield_buy_gems` và trong trần ngày | `bot/modules/defense.py` | — |
| P5-5 trinh sát / do thám | **Không viết code** (chưa có câu trả lời §5.1). Câu hỏi ở dưới | — | — |

**Phát lại offline:** 11/11 ảnh `intel_panel_unknown` → `reward` (test `test_replay_intel_panel_unknown_shots_are_reward`, chỉ chạy local). Ước tính tỉ lệ "unknown" sau sửa (22/11, 92 ghim): chắc chắn bớt 11 (bảng quà) → ≤ 57,6 %; nếu màn quân đoàn kiểu mới đúng là màn sau "Tấn công" (31) và ghim giữa màn tìm được mục tiêu (22) thì còn ~3–5 %. Hai giả thuyết này **chưa kiểm được offline** (không có ảnh) — bot sẽ tự lưu ảnh `logs/inv/intel_unknown_attack|target/` ở lượt chạy thật.

**Câu hỏi cần chủ dự án quyết:**
1. `rebels.join_mech_rally`: có cho bot **tham gia tập kết của người khác** (đồng minh mở) đánh Phản quân Cơ giáp không? (mặc định tắt; bật cần 2 ảnh mẫu ở trên; bot chỉ vào dòng có dấu hiệu Cơ giáp, không bao giờ tập kết đánh người chơi)
2. Ghim tình báo "Phản quân Cơ giáp" trên **farm nhà chính < 15**: bot hiện vẫn tự mở tập kết (khi dự đoán thắng) như hướng dẫn 2026-11-22. Giữ (`rebels.intel_rally_min_hq: 0`) hay chỉ từ cấp 15 (đặt 15)?
3. Phản quân: số cấp thử mỗi lượt (`search_tries` 3) và cấp bắt đầu (`start_level` 10) có ổn với #1 không? Quân đoàn mặc định `Odin` có đúng đội mạnh nhất?
4. Trinh sát / do thám (§5.1 kế hoạch hoàn thiện, câu 1 — vẫn chưa trả lời): (a) "trinh sát" là trinh sát **căn cứ người chơi khác**, Phản quân/NPC, hay mỏ trên bản đồ? (b) "do thám" có phải nhiệm vụ Tình báo / Radar đã có (`intel`) không? (c) Nếu là người chơi: được trinh sát ai (chỉ khi bị đánh? chỉ ngoài liên minh? giới hạn lực chiến?) và để làm gì — bot **không tấn công người chơi** (CLAUDE.md), báo cáo trinh sát dùng vào việc gì? (d) Trinh sát tốn tài nguyên/vật phẩm gì, trần mỗi ngày? (e) Có cần nhận/đọc báo cáo trinh sát trong thư không? (f) Phòng thủ: khi bị **trinh sát** (không phải tấn công) có bật khiên không?
5. Phòng thủ: `defense.shield_buy_gems` đang `true` (trần 2000 kim cương/ngày) — giữ nguyên ngoại lệ ADR-0008?
6. Bệnh viện: `heal.open_without_bubble: false` — đồng ý chỉ mở bệnh viện khi thấy bong bóng chữa trị hoặc vừa có trận?

Ảnh mẫu cần chụp: xem `templates/README.md` mục P5 (`rebels/rally_mech`, `rebels/btn_join`, `defense/alert_attack`, `defense/row_8h`) + ảnh tay bảng chữa trị khi có thương binh.

Kiểm chứng (chủ dự án bật máy, tối đa 2 máy): 1 lượt chạy thật đầy đủ trên #1 (nhà chính 30: tình báo, phản quân) + 1 farm có tình báo (vd #0) + 1 lần chạy lại, rồi `python tools/report_ro.py --split "<giờ bắt đầu P5>"`: mục `tinh bao` (% unknown, mục tiêu < 10 %; xem lý do `unknown_*`), mục `chien dau` (rebels có kết quả ≥ 50 % số lần chạy; heal: số phút giảm), bảng bước (`heal` thời gian). Mở `logs/inv/intel_unknown_*` nếu còn unknown; grep log `thieu anh mau`.

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
| A-OPT-1 | **Đã làm (P1, PM 2026-11-23) theo cách khác đề xuất: giữ vị trí trong `ORDER`, giới hạn tần suất/thời gian trong module.** Đề xuất cũ: `reddots` ra khỏi `ALWAYS` → `extra_due` theo giá trị; đặt cuối `ORDER` | `bot/scheduler.py`, `bot/runner.py:ORDER` | 426 phút, ok 7 % | A-SAFE-2, A-FIX-3, quyết định của chủ dự án | Phút `reddots`/lần ghé giảm; tổng `ret` của notify+rewards+daily+reddots/ngày giảm ≤ 10 % | revert | 1 |
| A-OPT-2 | Một hàm đọc lực chiến (cache theo lần ghé), thay 3 bản `_power` | `bot/ctx.py`, `modules/quests.py`, `mainquest.py`, `tutorial.py` | 1.057 ms/lần | A-MEAS-1 | `perf`: số OCR mỗi bước có cổng lực chiến giảm; `check_tutorial` 34/34 | revert | 2 |
| A-OPT-3 | **Đã làm (P1, 2026-11-23).** Screencap fail-fast: lỗi lần 2 trong cùng bước → ném ngay, **giữ** chuỗi "Khong chup duoc man hinh" (runner `blind` so chuỗi này); bỏ qua lỗi của `HumanWatch._shot` | `bot/device.py:screencap` | 264–418 s rồi lỗi | A-MEAS-1 (cùng file) | `perf`: p99 tổng thời gian screencap giảm; số lần ghé bỏ dở do "máy không phản hồi" không tăng | revert | 1 |
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
