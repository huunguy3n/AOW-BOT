# Kế hoạch: ưu tiên theo việc và "giữ mọi hàng chờ luôn chạy"

Ngày: 2026-11-21 · Trạng thái: **Q0–Q6 đã làm 2026-11-21 (chủ dự án duyệt), chờ chạy thật** (ADR-0012) · Tiếp nối [screen-loop-plan.md](screen-loop-plan.md)

## 1. Yêu cầu của chủ dự án (2026-11-21)

1. **Thứ tự ưu tiên:** chấm đỏ (`reddots`) → lối chơi (mỏ khoáng sản, đấu trường) → tình báo → phản quân → thu thập. Làm tốt năm việc này là đã bao phủ khoảng 80 % thao tác trò chơi.
2. **Chấm đỏ mở ra tiến trình phụ thì làm luôn tiến trình đó** (lối chơi, tình báo, phản quân, thu thập), không chỉ nhận quà rồi đóng.
3. **Xây dựng:** thợ rảnh thì bấm vào nhà chính. Nhà chính thiếu điều kiện gì thì xây công trình đó (đi theo chuỗi "Nhảy").
4. **Nghiên cứu:** theo gợi ý của game, thứ tự nhánh Phát triển > Đào tạo > Quân sự, trong mỗi nhánh từ trên xuống dưới.
   - Yêu cầu nhánh phụ thì nghiên cứu nhánh phụ trước.
   - Yêu cầu cấp nhà chính thì chờ nhà chính xây xong rồi nghiên cứu tiếp.
5. **Luôn đảm bảo:**
   - Tình báo hoàn thành.
   - Mọi quân đoàn đi thu thập.
   - Huấn luyện ở 3 căn cứ (nhà lính) luôn chạy tới khi đạt giới hạn quân T3 đã đặt.
   - Xây dựng và nghiên cứu luôn chạy, chỉ dừng khi tới giới hạn.
6. **Có thương binh thì chữa ở bệnh viện.**

## 2. Mô hình: mỗi việc là một hàng chờ có giới hạn

Yêu cầu trên đúng là bài toán mà agent (`src/aowbot`) được thiết kế để giải: mỗi mục tiêu đo "hàng chờ X đang rảnh bao nhiêu", hành động lấp chỗ rảnh, và dừng khi tới giới hạn. Phần còn thiếu là **đọc trạng thái hàng chờ** và **kỹ năng lấp hàng chờ** cho từng việc.

| Mục tiêu (goal) | Trạng thái cần đọc | Giới hạn | Kỹ năng (skill) | Hiện có |
|---|---|---|---|---|
| Chấm đỏ | chấm đỏ trên thành phố / cột phải | hết chấm đỏ xử lý an toàn được | `reddots` + định tuyến sang tiến trình phụ | `reddots` chỉ nhận rồi đóng |
| Lối chơi | rương mỏ khoáng sản, lượt đấu trường miễn phí | 3 lượt/ngày; không mua lượt | `play` | có |
| Tình báo | nhiệm vụ tình báo còn lại, thể lực | hết nhiệm vụ hoặc hết thể lực (không mua bằng kim cương) | `intel` | có |
| Phản quân | lượt trong ngày, thể lực, đội rảnh | `rebels.daily_target`, HQ ≥ 15 | `rebels` | có, nhưng 0/15 lần có kết quả |
| Thu thập | "Hành quân x/y" | x = y | `gather` qua agent | có (agent vừa sửa) |
| Huấn luyện | hàng chờ huấn luyện (icon cột trái "0/3"), số lính T3 | đủ quân T3 đã đặt | `train` | có, giới hạn theo `troops_per_march` |
| Xây dựng | thợ xây "x/y" (icon búa cột trái) | hết thợ, hoặc nhà chính = `build.hq_max_level` | **mới:** nhà chính trước, rồi chuỗi "Nhảy" | đang đi qua nhiệm vụ "Đến" |
| Nghiên cứu | hàng chờ nghiên cứu "x/1" | hết nút nghiên cứu được, hoặc chờ cấp HQ | `research` + nhánh phụ + chặn chờ HQ | có thứ tự nhánh; chưa có nhánh phụ / chờ HQ |
| Bệnh viện | số thương binh | 0 thương binh | **mới:** chữa trị (chỉ dùng tài nguyên, không kim cương) | chưa có ảnh mẫu |

**Nguồn đọc rẻ nhất:** cột icon bên trái màn thành phố hiện sẵn thợ xây "1/2", nghiên cứu "0/1", huấn luyện "0/3", mỗi icon có chấm đỏ khi rảnh (xem ảnh `logs/inv/quests_tab_2_main_row1`). Một ảnh chụp thành phố cho biết trạng thái cả ba hàng chờ, không cần mở bảng nào. Ảnh mẫu `build/icon_builder`, `research/icon_queue`, `train/queue_icon` đã có.

## 3. Mức đạt hiện tại (24 giờ tới 17:00, `runs`, MEASURED)

| Bước | Lần có kết quả / lần chạy | Phút |
|---|---|---|
| `reddots` | 83/170 có nhận (chỉ 11 lần kết thúc "ổn") | 466 |
| `play` | 2/30 | 22 |
| `intel` | 10/44 | 25 |
| `rebels` | 0/15 | 2 |
| `gather` | 19/37 | 52 |
| `train` | 9/32 | 12 |
| `research` | 0/14 | 2 |
| `construct` / `quests` / `mainquest` | 3/11 · 10/130 · 8/143 | 6 · 264 · 152 |

Chưa có số đo "thời gian hàng chờ rảnh" (thợ, nghiên cứu, huấn luyện, quân đoàn). Q0 bổ sung số này. Đây mới là chỉ số đúng với yêu cầu "luôn hoạt động".

## 4. Các giai đoạn

Mỗi giai đoạn là 1–3 commit, có test, có số đo trước/sau, và chủ dự án duyệt trước khi bắt đầu.

| # | Việc | Nghiệm thu |
|---|---|---|
| **Q0** | **Đọc hàng chờ** (hàm thuần `queues(img)`): thợ xây, nghiên cứu, huấn luyện x/y + chấm đỏ rảnh, từ một ảnh thành phố. Ghi vào `facts` + world view. Thêm chỉ số "phút rảnh của từng hàng chờ / giờ máy bật" vào `report_ro`. | Đúng trên ≥ 20 ảnh thành phố thật (#0–#6); báo cáo có cột phút rảnh |
| **Q1** | **Thứ tự mới + định tuyến chấm đỏ:** `ORDER` thành chấm đỏ → lối chơi → tình báo → phản quân → thu thập → huấn luyện → xây → nghiên cứu → phần còn lại. Bảng định tuyến trong `reddots`: icon/bảng nhận ra là tính năng của lối chơi, tình báo, phản quân, thu thập thì gọi module đó tại chỗ thay vì đóng. | Log cho thấy chấm đỏ của lối chơi/tình báo dẫn vào module tương ứng; `reddots` kết thúc "ổn" ≥ 50 % |
| **Q2** ✅ | **Xây dựng: nhà chính trước** (bước `upgrade`, [bot/modules/upgrade.py](../../bot/modules/upgrade.py); từ thế giới về thành phố thì camera nằm giữa nhà chính, chạm (270, 440), kiểm nhãn "Xưởng kiến trúc"). Thợ rảnh (Q0) → chạm nhà chính → `upgrade_here` (đã có chuỗi "Nhảy" tới điều kiện, S1 đã sửa thời điểm đọc). Trần `build.hq_max_level`. Nhiệm vụ "Đến" chỉ còn là nguồn phụ. | Thợ rảnh trong lúc máy bật giảm rõ; số lần bắt đầu nâng cấp/ngày tăng (hiện 9/24,9 h máy) |
| **Q3** | **Nghiên cứu có nhánh phụ và chờ HQ.** Theo thứ tự nhánh/từ trên xuống. Yêu cầu nhánh phụ → nghiên cứu nhánh đó trước. Yêu cầu cấp HQ → dữ kiện chặn (S2 `blockers`) tới khi nâng HQ xong. | Hàng nghiên cứu rảnh khi máy bật giảm; không thử lại node chờ HQ |
| **Q4** | **Agent điều phối theo hàng chờ:** goal cho từng dòng ở mục 2, điểm ưu tiên theo thứ tự chủ dự án. Agent chọn việc từ trạng thái hàng chờ thay cho `ORDER` cố định (trước hết trên #1, chạy shadow trước). | Shadow #1: agent nêu đúng hàng chờ rảnh ≥ 90 %; sau khi bật, phút rảnh mỗi hàng chờ giảm |
| **Q5** | **Bệnh viện.** Cần ảnh: thương binh / bệnh viện / nút chữa trị (chủ dự án làm mẫu trên #3 hoặc chụp màn). Chỉ chữa bằng tài nguyên; nút "Chữa ngay" bằng kim cương luôn chặn (ADR-0008). | Có thương binh → chữa xong ở lần ghé kế; không chạm nút kim cương |
| **Q6** | **Phản quân 0/15:** điều tra bằng ảnh (giống A-INV-1) rồi sửa. | `rebels` có kết quả ≥ 50 % khi đủ điều kiện |

Thứ tự đề xuất: Q0 → Q1 → Q2 → Q3 → Q4, còn Q5 và Q6 chen vào khi có ảnh. Q0 là nền chung: mọi mục "luôn hoạt động" đều cần biết hàng chờ nào đang rảnh.

### Trạng thái từng giai đoạn (2026-11-21)

- **Q0:** đọc "x/y" thợ xây / nghiên cứu / huấn luyện ([bot/queues.py](../../bot/queues.py)). Hạn chế đã biết: "1/1" (chữ số 1 mảnh) Tesseract không đọc được → giá trị "không rõ", agent không hành động theo giá trị đó.
- **Q1:** thứ tự mới + chấm đỏ dẫn vào tiến trình phụ; nút "Nhận" theo màu + chữ ([bot/buttons.py](../../bot/buttons.py)).
- **Q2:** bước `upgrade` ([bot/modules/upgrade.py](../../bot/modules/upgrade.py)).
- **Q3:** bảng node nghiên cứu ([bot/modules/research.py](../../bot/modules/research.py) `node()`): nút "Nghiên cứu" theo màu + chữ (chặn "… ngay"); thiếu nhánh phụ → "Đến" sang node điều kiện (tối đa 4 bước); "Đến" dẫn tới màn nâng cấp nhà chính → ghi `research_wait_hq`, không thử lại tới khi HQ lên cấp. **Chưa có ảnh bảng node** (#1 đang nghiên cứu 13 ngày, farm HQ < 8) → lần đầu chạy thật lưu `logs/inv/research_node/` nếu chưa nhận ra.
- **Q4:** agent có mục tiêu `training` / `research` theo hàng chờ (ưu tiên sau thu thập); hành động `legacy_train`, `legacy_research`; `legacy_build` gọi `upgrade` trước.
- **Q5:** bước `heal` ([bot/modules/heal.py](../../bot/modules/heal.py)): tìm chữ thập đỏ 46×24 trên mái bệnh viện, kiểm nhãn "Bệnh Viện", icon "Hồi phục" = icon Tăng cấp + (80, −15), nút "Hồi phục" theo màu + chữ (chặn "Hồi phục ngay"). Chưa có ảnh bảng chữa trị khi có thương binh.
- **Q6:** phản quân không thấy quanh căn cứ → ô tìm kiếm bản đồ, tab Cơ giáp, cấp = đã thắng + 1 (chưa thắng: `rebels.start_level` 10), dự đoán thua thì lùi cấp.

## 5. Quyết định của chủ dự án (2026-11-21)

1. **Giới hạn quân T3:** dùng `train.troops_per_march` (web: "Số T3 cần cho mỗi đội thu thập") = **30.000 / loại / quân đoàn** (đã đặt trong `data/settings.json`).
2. **Xây theo nhà chính:** mọi máy, mọi cấp. Nhà chính cấp 30 (tối đa) thì bỏ mục tiêu xây dựng. → `build.hq_max_level` mặc định đổi 22 → 30.
3. **Bệnh viện:** công trình "Bệnh Viện" trên thành phố → chạm → vòng tròn có nút "Hồi phục" (ảnh chủ dự án gửi; nút xám khi chưa có thương binh). Cần cắt ảnh mẫu từ ảnh chụp máy 540×960 (ảnh gửi qua chat bị cắt/thu phóng) ở Q5.
4. **Chấm đỏ dẫn tới tính năng chưa có cách xử lý:** lưu màn đó vào mục học (web tab "Học & Agent", danh sách màn lạ) để chủ dự án dạy. Đã làm trong Q1.

## 6. Câu hỏi cũ (đã trả lời ở mục 5)

1. **Giới hạn quân T3:** dùng cấu hình hiện có (`train.only_for_gather`, `troops_per_march` 1200 × số quân đoàn), hay thêm `train.t3_target` (tổng số lính T3 cố định cho từng máy)?
2. **Xây theo nhà chính** áp dụng cho mọi máy, hay chỉ từ HQ ≥ 9 (trước đó vẫn theo nhiệm vụ tân thủ/chương)?
3. **Bệnh viện:** cần ảnh màn có thương binh và bảng chữa trị.
4. **Chấm đỏ dẫn tới tính năng chưa có module** (ví dụ sự kiện mới): giữ hành vi hiện tại (nhận nút "Nhận" xanh rồi đóng, lưu ảnh để bổ sung), hay dùng chế độ "làm theo mẫu" khi đã có mẫu?
