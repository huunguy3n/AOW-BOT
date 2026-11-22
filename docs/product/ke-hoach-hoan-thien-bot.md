# Kế hoạch hoàn thiện bot farm — theo ngày, theo tính năng
Lập: 2026-11-18 · Bắt đầu dự kiến: **N1 = 2026-11-19** · Tổng: **18 ngày làm việc** (6 pha)

> Làm theo [ADR-0012](../adr/0012-lam-viec-theo-giai-doan.md): cuối mỗi pha có báo cáo ngắn trong `docs/bot/` (số liệu **[ĐO] / [CHƯA ĐO]**), chủ dự án duyệt rồi mới sang pha sau. Ngày trong bảng là ước lượng; ngày nào phụ thuộc "tình huống phải xuất hiện trong game" thì ghi rõ.

## 1. Mục tiêu cuối
Một tài khoản **mới tạo** được bot đưa đi hết đường, không cần người can thiệp:

```
Tân thủ  →  Nhiệm vụ chính / xây dựng  →  Nhà chính cấp 22  →  Farm ổn định
(tutorial)   (mainquest, quests, build,     (build.hq_max_level)   (gather, intel, trinh sát,
              research, train, rewards)                             rewards, daily, alliance)
```

**Tiêu chí "xong":** 3 tài khoản mới liên tiếp qua tân thủ không can thiệp; 1 tài khoản tự lên HQ 22; vòng 6 instance chạy 48 h với tỉ lệ bước không lỗi ≥ 95 %.

## 2. Hiện trạng thật (khảo sát 2026-11-18)
Roadmap ghi nhiều mục ✅ nhưng khi đối chiếu code + `python main.py --check` + log thì còn hổng:

| Tính năng | Bằng chứng | Mức độ |
|---|---|---|
| **Tân thủ** | `logs/shots/`: 4× `tutorial_lose`, 3× `tutorial_stuck`, 1× `tutorial_maxsteps` (instance #5); chưa có điểm kết thúc rõ để chuyển sang `mainquest`; thiếu `tutorial/zone_green.png` | 🔴 chưa chạy hết |
| **Nghiên cứu** | `templates/research/` **trống** (6/6 ảnh mẫu thiếu) → module luôn "Không thấy tòa nhà nghiên cứu" | 🔴 không hoạt động |
| **Nhận vật phẩm** | thiếu `rewards/signin/*`, `rewards/free_chest/*`, `rewards/city/claim_1`, `common/btn_free`, `common/btn_help`, `common/btn_reward_close`, `common/msg_insufficient` → 3/5 tuyến bỏ qua | 🟠 một phần |
| **Thu thập** | thiếu `gather/msg_not_found`, `msg_no_troops`, `msg_march_full`, `mine_occupied`, `lv/9`, `digits/0,2–9`; shots `no_march_panel` ×4, `dry*` ×11 (mỏ cạn/đọc trữ lượng) | 🟠 chạy nhưng hay hụt |
| **Nhiệm vụ / lên cấp** | `quests` + `mainquest` + `build` có, nhưng không có "kế hoạch lên cấp" (biết HQ đang cấp mấy, cần xây gì kế tiếp); `build_blocked`, `campaign_result` ×4, `campaign_timeout` | 🟠 đi theo nhiệm vụ, chưa chủ động |
| **Huấn luyện** | thiếu `train/btn_max` | 🟡 |
| **Tình báo** (`notify.intel`) | có code + ảnh mẫu `intel/*` | 🟡 cần chạy thử đo |
| **Trinh sát / do thám** | **chưa có code** | ⚪ chưa bắt đầu |
| **Phòng thủ / Phản quân** | thiếu `defense/alert_attack`, `rebels/rally_mech`, `ally/btn_help_all` | 🟡 chờ tình huống |
| **Đo lường** | `data/state.json` đang **rỗng** (`instances: {}`), log hôm nay 0 dòng → chưa có số liệu lỗi theo bước | 🔴 cần trước tiên |

## 3. Lộ trình

### Pha 0 — Nền tảng đo & công cụ (N1)
Không có số đo thì không biết sửa đúng chưa → làm trước.

| Ngày | Việc | Xong khi |
|---|---|---|
| **N1** ✅ | 1. Ghi thống kê theo bước vào `state.json`: số lần chạy / lỗi / ảnh `shots` gần nhất mỗi module; hiện trên web<br>2. Watchdog: màn hình không đổi > N phút → lưu ảnh, force-stop game, mở lại<br>3. `tools/snap.py`: thêm chế độ "cắt hàng loạt theo danh sách thiếu" từ `--check` để cắt ảnh mẫu nhanh khi tình huống xuất hiện<br>4. Chốt instance thử (xem câu hỏi §5) | Web hiện bảng lỗi theo bước; chạy `--once` trên 1 instance ra được số — **xong phần code 2026-11-18**, báo cáo [00-pha0-nen-tang.md](../bot/00-pha0-nen-tang.md); còn chốt instance + đo trên máy thật |

### Pha 1 — Tân thủ chạy hết (N2–N5)
| Ngày | Việc | Xong khi |
|---|---|---|
| **N2** ✅ | Phân tích 8 ảnh lỗi tân thủ (`*tutorial_lose/stuck/maxsteps*`), ghi bản ghi mới cho đoạn kẹt (`tools/record.py`), phân loại nguyên nhân: thiếu ảnh mẫu / `decide()` chọn sai / lái quân thua | Bảng nguyên nhân từng ảnh trong `docs/bot/02-tan-thu-loi.md` — **xong 2026-11-18**; thêm: chuyển giao tân thủ → nhiệm vụ chính chạy thật trên #5 |
| **N3** | Sửa `decide()` cho các điểm kẹt; cắt `zone_green` và mẫu còn thiếu; trận thua: tinh chỉnh `steer` (né cổng đỏ, "CẢNH BÁO!") + giới hạn "Bắt đầu lại"; bổ sung case vào `tools/replay_tutorial.py` | Replay offline qua hết các bản ghi không sai quyết định |
| **N4** 🟡 | Đoạn cuối tân thủ: dọn phế tích 1/2/3, chương 1–2, cảnh phim; **điều kiện kết thúc** (không còn V-marker/bàn tay + thanh nhiệm vụ thường) → ghi `tutorial_done` vào state, tự tắt `tutorial` và để `mainquest` chạy | Một tài khoản chạy từ "Bắt đầu trò chơi" tới hết, bot tự chuyển bước — **chuyển giao + bảng Chương sau tân thủ xong trên #5 (2026-11-18)**; còn chạy từ đầu trên TK mới |
| **N5** | Chạy 3 tài khoản mới liên tiếp (tạo tài khoản mới: **chủ dự án làm**), ghi tỉ lệ hoàn thành, thời gian, số lần thua | **≥ 2/3 không can thiệp** → báo cáo pha 1, chờ duyệt |

### Pha 2 — Nhận vật phẩm đủ tuyến (N6–N7)
| Ngày | Việc | Xong khi |
|---|---|---|
| **N6** ✅ | Cắt ảnh mẫu `rewards/signin`, `free_chest`, `city`, `common/btn_free`, `btn_help`, `btn_reward_close`, `msg_insufficient` (cần tài khoản có quà chưa nhận — nên chạy lúc đầu ngày mới); `daily/chapter_claim` | `--check` không còn thiếu mục nhóm rewards/common — **2026-11-18: khảo sát xong, thêm tuyến Buổi lễ + ô quà phát sáng, sửa đếm sai VIP**; còn `rewards/city`, 4 mẫu `common/*` chờ tình huống → [03-nhan-qua.md](../bot/03-nhan-qua.md) |
| **N7** ✅ | Chạy `--modules rewards,daily,notify` trên 2 tài khoản; thêm "đã nhận hôm nay" vào state để không mở lại các bảng vô ích; đóng popup lạ an toàn | 5/5 tuyến nhận được, 0 lần kẹt trong 3 lượt — **2026-11-18: thêm 9 nguồn quà theo chấm đỏ, lượt cuối không lỗi** ([03-nhan-qua.md §5](../bot/03-nhan-qua.md)) |

### Pha 3 — Nhiệm vụ & lên nhà chính cấp 22 (N8–N11)
| Ngày | Việc | Xong khi |
|---|---|---|
| **N8** | **Nghiên cứu**: cắt 6 ảnh mẫu `research/*`, kiểm tra luồng vào nhánh thu thập + trợ giúp/miễn phí; `train/btn_max` | `research` + `train` chạy thành công 3 lượt liên tiếp |
| **N9** | **Kế hoạch lên cấp** (module mới `progress`, hàm thuần): đọc cấp HQ + thợ xây rảnh → nếu `quests` không có việc xây thì chủ động nâng HQ / đi theo nút "Nhảy" tới điều kiện; không bao giờ bấm "Tăng cấp ngay" | Thợ xây không rảnh quá 1 lượt khi còn tài nguyên |
| **N10** | Sửa `mainquest`/`campaign`: ảnh `campaign_result` ×4, `campaign_timeout`, `build_blocked`; boss khó → hoãn theo `power_gain_pct`; thiếu tài nguyên → ghi lý do, sang việc khác | Không còn lỗi lặp lại trong 5 lượt |
| **N11** | Cho 1 tài khoản (vừa qua tân thủ ở N5) chạy liên tục 24 h; đo: cấp HQ/ngày, % thời gian thợ xây bận, lỗi theo bước | Báo cáo tốc độ lên cấp + ước lượng ngày đạt HQ 22 → chờ duyệt |

### Pha 4 — Thu thập ổn định (N12–N13)
| Ngày | Việc | Xong khi |
|---|---|---|
| **N12** | Cắt `gather/msg_*`, `mine_occupied`, `lv/9`, `digits/0–9`; xử lý `no_march_panel`; mỏ cạn/bị chiếm → đổi mỏ thay vì bỏ cả loại | `--check` sạch nhóm gather/digits |
| **N13** | Đọc thời gian về (`return_at`) → web hiện đúng; tối ưu thứ tự: lượt sau ưu tiên tài khoản có đội sắp về; chạy 6 instance | Mọi đội hành quân được lấp đầy trong ≥ 90 % lượt |

### Pha 5 — Tình báo, trinh sát, do thám (N14–N16)
| Ngày | Việc | Xong khi |
|---|---|---|
| **N14** | **Tình báo** (`notify.intel` đã có): tách thành bước riêng `intel`, chạy thử, đo số nhiệm vụ/lượt, dùng thuốc thể lực (không mua) | 5 nhiệm vụ/lượt không kẹt |
| **N15** | **Trinh sát** (module mới `scout`): ghi bản ghi người chơi làm thao tác trinh sát, cắt ảnh mẫu, viết `decide()` thuần + replay | Replay offline đúng; chạy thật 1 lượt |
| **N16** | Kết nối trinh sát với các bước khác (vd trinh sát trước khi đánh/tập kết; nhận báo cáo trong thư); thêm tùy chọn web | Báo cáo pha 5 → chờ duyệt |

### Pha 6 — Ổn định toàn vòng (N17–N18)
| Ngày | Việc | Xong khi |
|---|---|---|
| **N17** | Chạy vòng đủ 6 instance liên tục; sửa lỗi phát sinh theo bảng thống kê Pha 0; cắt mẫu phòng thủ/phản quân nếu tình huống xuất hiện | — |
| **N18** | Chạy 48 h, tổng hợp số liệu, cập nhật `vision-roadmap.md` (hiện trạng đúng thực tế), `CLAUDE.md`, `web/options.py` | Tỉ lệ bước không lỗi ≥ 95 %, 0 kim cương tiêu ngoài khiên |

## 4. Rủi ro & phụ thuộc
- **Ảnh mẫu chỉ cắt được khi tình huống xuất hiện** (quà chưa nhận, mỏ bị chiếm, bị tấn công…) → các ngày N6, N12, N17 có thể trượt; việc khác trong pha vẫn làm song song.
- **Tạo tài khoản mới để thử tân thủ**: chủ dự án làm tay (quy tắc tạo tài khoản). Không `pm clear` tài khoản thật — dùng instance riêng hoặc slot đã snapshot ([ADR-0010](../adr/0010-an-toan-tai-khoan-khach.md)).
- Không có test tự động: mỗi quyết định mới viết dạng **hàm thuần + replay** ([ADR-0011](../adr/0011-tan-thu-ham-quyet-dinh-thuan.md)) để không phải chạy thật mới biết đúng sai.
- Account Manager (Phase 2+) **không nằm trong kế hoạch này**; tạm dừng tới khi bot ổn định, trừ khi chủ dự án muốn chạy song song.

## 5. Câu hỏi cần chủ dự án trả lời trước N1
| # | Câu hỏi | Ảnh hưởng |
|---|---|---|
| 1 | "Trinh sát" và "do thám" cụ thể là thao tác nào trong game? (vd: trinh sát căn cứ người chơi khác / phản quân trên bản đồ; do thám = nhiệm vụ Tình báo/Radar?) — **vẫn chưa trả lời (2026-11-23)**; câu hỏi chi tiết ở `docs/strategy/implementation-roadmap.md` mục 0f. Chưa viết code trinh sát | Phạm vi Pha 5 |
| 2 | ✅ Đã trả lời 2026-11-18: chỉ còn **#0, #2–#6**. Đo bot trên #0 (farm, bản `.vn`), tân thủ trên #5 | Pha 0–1 |
| 3 | Sau HQ 22 bot chỉ farm (thu thập + nhận quà) hay vẫn xây công trình khác / nghiên cứu nhánh khác? | Pha 3 |
| 4 | Có tài khoản nào đang gần HQ 22 để đo Pha 3 nhanh hơn không? | N11 |
