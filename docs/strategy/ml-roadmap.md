# Lộ trình học máy (ML): từ "chạm mượt" tới tự quản mạng lưới farm

Ngày lập: 27/11/2026 · Trạng thái: **M0 + M1 đã duyệt 27/11/2026 và đã làm (chưa chạy thật, xem §7)**; M2–M4 chờ duyệt · Làm theo giai đoạn (ADR-0012): duyệt từng giai đoạn, không tự sang giai đoạn kế.

Mục tiêu chủ dự án (27/11/2026): bot thao tác mượt như người, hoàn thành nhiệm vụ xuất sắc, tự chủ việc nuôi farm và duy trì mạng lưới farm tăng dần — trong giới hạn **7 instance, tối đa 2 chạy song song**.

---

## 1. Hiện trạng (số đo 24/11–27/11/2026)

| Lớp | Đã có | Đang dùng để quyết định? |
|---|---|---|
| Luật cứng | Module theo `ORDER` ([bot/runner.py](../../bot/runner.py)) | Có — toàn bộ hành vi |
| Học nhỏ | [bot/learn.py](../../bot/learn.py): nhật ký chạm `exp`, ảnh vùng chạm, kNN màn hình, biến thể ảnh mẫu, thời gian chờ, chỗ chết | Một phần: thời gian chờ, điều hướng `goto`; từ J1 (27/11) chặn chỗ chết ở mọi lần chạm |
| Làm theo mẫu | [bot/imitate.py](../../bot/imitate.py), chỉ máy #3 | Có, riêng #3 |
| Agent | `src/aowbot` (planner, utility) | Tắt mặc định; chỉ chọn *khi nào* ghé máy |

Số đo nền (3 ngày gần nhất, `memory.db`):

- Chạm: ~31.600 lần/ngày, **94 % ăn**, 6 % trượt. 45 chỗ chết.
- Lượt ghé: ~86 lượt/ngày, trung bình 10–19 phút/lượt → **~22 máy-giờ/ngày trên ngân sách 48** (2 luồng × 24 h).
- Thời gian theo bước (3 ngày): `reddots` 14,7 h, `quests` 12,9 h, `upgrade` 6,8 h, `observe` 6,3 h, `intel` 5,8 h. `construct` 365/372 lần trả 0, `upgrade` 347/488 lần trả 0.
- Cấp nhà chính: #1 = 30 (tài khoản chính), #0 = 9, **#2–#6 đứng ở 7**.

Kết luận: bot chạm khá chuẩn nhưng **dồn thời gian vào việc ít giá trị** (quét chấm đỏ, nhiệm vụ trả 0), và farm **không lên cấp**. ML nên nhắm vào "chọn việc đáng làm" trước khi nhắm vào "chạm đẹp hơn".

---

## 2. Nguyên tắc chung (áp dụng mọi giai đoạn)

1. **Luật an toàn luôn thắng ML.** ML chỉ được chọn trong tập hành động đã an toàn; không bao giờ học/bấm: nút kim cương, tiền thật, "… ngay" (trừ "Miễn phí"), menu căn cứ người chơi (P13l), "Đến" của popup mở khóa (P13k), chat. `pm clear`, gỡ app, ghi dữ liệu app: ngoài phạm vi ML hoàn toàn (ADR-0010).
2. **"Như người" = hiệu quả, đúng ý, không thừa.** Không ngẫu nhiên hóa / giả hành vi để qua mặt anti-cheat (quy tắc 7 CLAUDE.md).
3. **Không học tăng cường thuần (RL).** Không có trình giả lập, chỉ 2 luồng chạy thật → quá ít mẫu. Dùng: học theo mẫu tay chủ dự án + học có giám sát từ kết quả thật + bandit (Thompson) trên các lựa chọn an toàn.
4. **Mỗi quyết định ML có công tắc tắt** trong `config.yaml` / web, ghi lý do vào log hoặc bảng `decisions`, và có số đo trước/sau (`tools/report_ro.py --split`).
5. **Thu dữ liệu trước, quyết định sau:** phần cần dữ liệu mới thì chạy chế độ "bóng" (shadow: chỉ ghi dự đoán, không hành động) tối thiểu 3 ngày, so với kết quả thật rồi mới bật.
6. Kiểm chứng như chủ dự án đã chốt: 1 lượt chạy đầy đủ + 1 lượt kiểm lại trên máy thật, tối đa 2 máy cùng lúc.

---

## 3. Các giai đoạn

### M0 — Nền số đo (nhỏ, làm trước)

Mục tiêu: mọi giai đoạn sau có thước đo chung.

- Bảng điểm web "ML" (tab Học & Agent): % chạm ăn, số chạm ML chặn (J1, đã có), phút/lượt ghé, máy-giờ dùng/ngày, cấp nhà chính & lực chiến theo máy theo ngày, số lần kẹt/cứu kẹt.
- `tools/report_ro.py --ml` in cùng bộ số đo, có `--split` trước/sau.

Xong khi: bảng điểm hiện đủ 7 máy, số khớp với log 1 ngày.

### M1 — "Tay": chạm mượt, không thừa, không kẹt

| Việc | Dữ liệu | Cách học |
|---|---|---|
| M1-1 Đoán chạm vô ích theo **ảnh vùng chạm** | `exp` + `data/exp/crops` (đã có) | kNN theo từng ảnh mẫu: vùng trông như này → chạm có ăn không. Ví dụ `ally/tab_main` khớp 0,994 nhưng trượt 421 lần (tab đã mở sẵn) |
| M1-2 Ngưỡng khớp riêng từng ảnh mẫu | `exp.score` × `changed` | Chọn ngưỡng tối đa hóa ăn/trượt; chỉ **nâng** ngưỡng, không hạ dưới mặc định |
| M1-3 Màn lạ → làm theo thao tác tay đã dạy, **mọi máy** | `logs/human`, `taught.jsonl`, `imitate` | Mở rộng `imitate` từ #3 ra 7 máy, chỉ cho màn `unknown`/kẹt, vẫn qua `blocked_tap` |
| M1-4 Thời gian chờ đã học (H1) cho mọi chuỗi thao tác | `exp.react` | Đã có; mở rộng sang `wait_for` |

Số đo mục tiêu: chạm ăn 94 % → **≥ 97 %**; kẹt/cứu kẹt giảm ≥ 50 %; phút/lượt giảm ≥ 20 %.
Quyết định chủ dự án: cho `imitate` chạy ngoài #3 hay không.

### M2 — "Đầu": làm nhiệm vụ xuất sắc

| Việc | Dữ liệu | Cách học |
|---|---|---|
| M2-1 Bảng `battle_ev`: loại trận, lực chiến ta/địch, dự đoán, kết quả | **Mới** — ghi ở campaign, rebels, intel, play (đấu trường, cướp xe), expand | Thu 3–7 ngày ở chế độ bóng |
| M2-2 Xác suất thắng theo tỉ lệ lực chiến từng loại trận | `battle_ev` | Hồi quy logistic; thay hệ số cố định (`loot.power_margin`, `campaign.power_gain_pct`, `notify.intel_lose_power_pct`) khi đủ mẫu; vẫn giữ "dự đoán Thắng toàn diện" của game làm điều kiện cần |
| M2-3 Chọn bước trong lượt ghé theo lợi ích | `runs` (thời gian, ret), `queue_obs`, `march_obs`, cấp nhà/lực chiến | Bandit theo ngữ cảnh: bước X ở máy Y sau Z phút có ra việc không / đáng bao nhiêu phút. Thay `ORDER` cố định bằng thứ tự động; **bước an toàn bắt buộc** (warday, defense, khung đăng nhập hẹn giờ, gather cuối lượt) giữ luật cứng |
| M2-4 Nhà chính đứng yên → tìm nguyên nhân | `hqlevel`, log "Nhảy", thiếu tài nguyên | Phân loại lý do kẹt (thiếu điều kiện / thiếu tài nguyên / thợ bận / lỗi màn) → đề xuất hành động; trước mắt báo lên web |

Số đo mục tiêu: farm #2–#6 lên **nhà chính cấp 9 trong 7 ngày** (hiện đứng 7); thời gian `reddots` + `quests` giảm ≥ 40 % mà số quà nhận không giảm; tỉ lệ thua trận ≤ 5 %.
Quyết định chủ dự án: cho phép thứ tự bước động (bỏ `ORDER` cố định) trên mấy máy trước.

### M3 — Tự quản 7 máy, 2 luồng

- **Ngân sách máy-giờ:** 2 luồng × 24 h = 48 máy-giờ/ngày; hiện dùng ~22. Agent (`src/aowbot`) chia ngân sách theo giá trị dự kiến của lượt ghé (hàng chờ sắp xong, khung đăng nhập hẹn giờ, thể lực đầy, máy tụt lại) thay vì xoay vòng.
- **Phát hiện máy chững** (nhà chính/lực chiến không tăng N ngày) → web cảnh báo + ưu tiên lượt ghé chẩn đoán.
- **Dồn tài nguyên về #1** (kế hoạch cũ, chưa làm) — cần chủ dự án chốt cách chuyển hợp lệ trong game (liên minh, hỗ trợ…), không đụng dữ liệu app.
- Bật agent theo `aowbot.domain.rollout` (trần cứng 2 máy), chạy bóng → 1 máy → 2 máy → toàn bộ.

Số đo mục tiêu: dùng ≥ 40 máy-giờ/ngày; không máy nào quá 4 giờ không được ghé; số máy cùng lúc luôn ≤ 2 (`report_ro --24h`).
Quyết định chủ dự án: bật agent theo từng bậc.

### M4 — Mở rộng mạng lưới vượt 7 máy (Account Manager)

Với trần 7 instance, cách duy nhất để tăng số farm là **nhiều tài khoản trên 1 instance** (ADR-0009, snapshot/restore dữ liệu app).

Điều kiện **bắt buộc** trước khi bắt đầu (ADR-0010):
1. M3 chạy ổn ≥ 7 ngày.
2. Chủ dự án chốt **instance thử** riêng cho Account Manager (hiện chưa có).
3. Mỗi tài khoản có snapshot đã verify SHA-256, ≥ 2 bản trên 2 ổ (E: và D:).
4. Quy trình ghi: `pm disable-user` → force-stop → kiểm uid → ghi → verify → `pm enable`; sai thì rollback.

Sau đó (mỗi bước duyệt riêng):
- Xoay vòng N tài khoản/instance trong ngân sách máy-giờ của M3 (chuyển tài khoản = một hành động có chi phí thời gian, agent tính vào).
- Tạo tài khoản khách mới + qua tân thủ (`tutorial`) — chủ dự án duyệt **từng lần** tạo tài khoản.
- Chỉ số "farm đáng nuôi": tài khoản không tăng giá trị sau N ngày → đề xuất ngừng nuôi (không xóa: snapshot giữ nguyên).

Quyết định chủ dự án: instance thử, số tài khoản tối đa/instance, có tạo tài khoản mới hay không.

---

## 4. Thứ tự và phụ thuộc

```
M0 ──► M1 ──► M2-1 (thu battle_ev, chạy bóng song song với M1)
              M2-2..4 ──► M3 ──► M4 (cần quyết định instance thử)
```

M1 và M2-1 chạy song song được (không đụng cùng file: M1 ở `bot/ctx.py`/`bot/learn.py`, M2-1 ở các module trận).

## 5. Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| ML chặn nhầm chạm cần thiết → bước kẹt | Thử lại thưa dần (J1), công tắc `skip_exempt`, số đo kẹt trên web |
| Thứ tự bước động bỏ sót việc hằng ngày | Bước bắt buộc giữ luật cứng; trần thời gian bỏ bước (`max_skip_h`) |
| Dự đoán thắng học sai khi ít mẫu | Chạy bóng, cần tối thiểu N mẫu/loại trận, game phải dự đoán thắng mới đánh |
| Account Manager làm mất tài khoản | Không bắt đầu khi chưa đủ điều kiện M4; không bao giờ trên tài khoản thật trước khi thử trên instance thử |

## 6. Cần chủ dự án duyệt

- [ ] Duyệt lộ trình M0–M4 nói chung
- [x] Bắt đầu M0 + M1 (27/11/2026)
- [x] M1-3: cho làm theo mẫu chạy ngoài #3 — chỉ cho màn lạ trong điều hướng (gồm trong duyệt M1)
- [ ] M2-3: máy nào thử thứ tự bước động trước
- [ ] M4: instance thử cho Account Manager, có tạo tài khoản mới không

---

## 7. Kết quả M0 + M1 (27/11/2026, chưa chạy thật)

| Mục | Trạng thái | Số đo offline |
|---|---|---|
| M0 số đo | Xong: `learn.scoreboard`, web "Số đo ML theo ngày", `python tools/report_ro.py --ml 7` | — |
| M1-1 đoán chạm vô ích theo ảnh vùng chạm | Xong, **bật** (`learn.skip_noop`) | 14 ngày, bỏ-ra 30 % mới nhất: bỏ 608/1631 lần trượt, đúng 98,2 % |
| M1-2 theo điểm khớp | Xong, gộp vào M1-1 làm luật dự phòng | riêng luật này: bỏ 397, đúng 99,2 % |
| M1-3 màn lạ → làm theo mẫu tay mọi máy | Có code, **tắt** (`learn.imitate_unknown` false) | bỏ-1-máy trên 206 màn lạ: đoán 16 lần, **sai 13** → không đủ tin |
| M1-4 chờ đã học cho `wait_for` | **Không làm** | `wait_for` đã hỏi màn mỗi 0,6 s nên chỉ lợi ≤ 0,3 s/lần; mọi chạm qua Ctx đã có chờ đã học (H1) |

Cách chặn: chạm bị đoán vô ích thì **không gửi** nhưng trả về như đã chạm (kết quả dự đoán y hệt: màn không đổi) → module không đổi hành vi, chỉ bớt thời gian. Mỗi ảnh mẫu / hàm tự kiểm bỏ-ra, chỉ chặn khi đúng ≥ 95 % trên ≥ 5 lần đoán; 5 % lần đoán vẫn chạm thật để học tiếp. Nút đóng / quay lại (`common/*`) không bao giờ chặn.

Khóa đang được chặn (27/11): `gather/btn_recommended` (đúng 99,2 %), `ally/tab_main` (97,7 %), `notify.claim_content`, `notify.heroes`, `alliance.show_tab` (100 %).

Việc còn lại để nghiệm thu M1 (theo cách kiểm chủ dự án đã chốt: 1 lượt đầy đủ + 1 lượt kiểm lại, ≤ 2 máy):
- Chạy thật, so `report_ro.py --ml` trước/sau: chạm ăn % (mục tiêu ≥ 97 %), phút/lượt ghé, lỗi bước.
- Theo dõi log `ML bo qua cham vo ich` — bước nào kẹt vì chặn thì thêm vào `learn.skip_exempt`.
- M1-3: cần thêm mẫu tay có nhãn loại màn trước khi đo lại.

---

## 8. M2 đã tích hợp (28/11/2026, chủ dự án "tích hợp M2") — chế độ bóng, chưa đổi hành vi

Chủ dự án duyệt M2 khi M1 chưa nghiệm thu. Để không làm lệch số đo M1, **mọi phần M2 chỉ ghi và báo cáo**; không phần nào đổi quyết định đánh/bỏ hay thứ tự bước của runner.

| Mục | Đã làm | Bật quyết định thật khi |
|---|---|---|
| M2-1 ghi trận | Bảng `battle_ev` (memory.db). `bot/battles.py` bọc từ bên ngoài `campaign.battle` (chiến dịch, Tình báo, mở rộng lãnh thổ, phiến quân nhiệm vụ…), `play.fight` (đấu trường), `play.power_check` + `play._loot_result` (cướp xe: có cả lực chiến hộ vệ và ta), `notify.legion_march` (màn quân đoàn kiểu mới). Hàm gốc không sửa; công tắc `ml.battle_log` | — (chỉ ghi) |
| M2-2 xác suất thắng | `aowbot.domain.battle_model`: hồi quy logistic theo ln(ta/địch), từng loại trận, cần ≥ 20 trận có kết quả + đủ hai lực chiến (≥ 3 thắng, ≥ 3 thua). Ghi `p_win` kèm mỗi trận, web hiện "cần ta/địch ≈ X để thắng 80 %" và độ chuẩn | Có độ chuẩn trên ≥ 50 trận mỗi loại; chủ dự án duyệt thay hệ số cố định (`loot.power_margin`…) |
| M2-3 giá trị bước | `aowbot.domain.stepvalue`: lần làm được việc / phút chạy, thứ tự đề xuất giữ luật cứng (warday/shield/tutorial đầu, gather/observe cuối). Web + `report_ro --ml` | Chủ dự án chọn máy thử. Lưu ý: chỉ số "việc / phút" đánh giá thấp bước xây dựng (ít lần ra việc nhưng là đích chính) → cần trọng số theo mục tiêu nhà chính trước khi dùng |
| M2-4 nhà chính đứng yên | `aowbot.domain.hqstall` + trạng thái `hq_plan`: giờ chưa lên cấp, đứng yên (≥ 24 h, cấp < 30), kế hoạch hiện tại. Web "Nhà chính (M2-4)" | — (chỉ báo cáo) |

Số liệu đầu tiên (28/11): #2–#6 đứng cấp 7 khoảng 40 giờ. Kế hoạch nhà chính: #3, #4, #6 **thiếu tài nguyên**, #2 chờ thợ, #5 **không tới được màn nâng cấp**, #0 (cấp 9) đang xây tiếp. Bảng `battle_ev` bắt đầu có dữ liệu sau khi khởi động lại bot.
