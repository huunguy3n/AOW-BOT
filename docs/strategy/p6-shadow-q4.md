# P6-Q4 — Shadow agent trên dữ liệu thật (offline, chỉ đọc)

Ngày chạy: 23/11/2026. Dữ liệu: `data/memory.db` từ 19/11 00:29 đến 22/11 23:18 (442 lần ghé, 2.076 lần chạy bước, 183 quyết định agent đã ghi).

Lệnh (không bật LDPlayer, không ghi DB — test `test_shadow_all_reads_decisions_and_reports_risks` kiểm file DB không đổi):

```bash
python -m aowbot shadow all                       # mọi máy trong config.yaml
python -m aowbot shadow 1 --since "2026-11-22 00:00"
```

## Cách đọc

- **Phát lại** (`replay`): đưa lần lượt các lần quan sát "Hành quân x/y" + giờ đội về vào `decide()` của agent, đếm agent sẽ thức dậy bao nhiêu lần và quyết định gì. So với lần ghé thật của lịch cũ: lần ghé có gửi quân được agent "phủ" nếu agent cũng thức dậy trong ± `gather_retry_min`.
- **Phiên agent thật**: các quyết định agent đã ghi trong bảng `decisions` (dry_run = 0) — trên máy đã đặt chế độ Agent trước P6.
- **Rủi ro**: hàm thuần `shadow_risks` ([src/aowbot/application/shadow.py](../../src/aowbot/application/shadow.py)): bỏ sót, ghé thêm, thức dậy nhiều, sai luật, tỉ lệ lỗi phiên thật > 20 % (≥ 3 lần).
- Giới hạn (INFERRED): phát lại chỉ mô phỏng **hành quân** (agent chỉ có dữ liệu x/y + giờ về theo thời gian). Xây / huấn luyện / nghiên cứu của agent (`legacy_*`) không phát lại được vì quá khứ không ghi trạng thái thợ / hàng chờ theo thời gian → chỉ đánh giá qua phiên thật. Số lần thức dậy là cận trên (sự kiện gộp theo khung `DEDUP_BUCKET_S`).

## Kết quả

| Máy | HQ | Quan sát | Agent thức dậy (phát lại) | Lịch cũ ghé | Lịch cũ gửi quân được | Agent phủ | Agent gửi khi lịch cũ không ghé | Phiên thật |
|---|---|---|---|---|---|---|---|---|
| #0 | 7 | 64 | 58, tất cả "không làm gì" | 97 / 3,7 ngày | 2 | 0/2 | 0 | build ok 7; research ok 3 / lỗi 3; train ok 2 |
| #1 | 30 | 122 | 153: gửi quân 88, quan sát 28, không 37 | 85 / 1,7 ngày | 19 | 16/19 | 21 | gửi quân ok 39 / lỗi 12 / chưa ghi 7; train lỗi 2; quan sát ok 14 |
| #2 | 5 | 45 | 44 không | 59 | 0 | – | 0 | build ok 3 / lỗi 1 |
| #3 | 5 | 45 | 44 không | 53 | 0 | – | 0 | build ok 7; train ok 3 |
| #4 | 4 | 59 | 59 không | 82 | 0 | – | 0 | không làm gì 7 |
| #5 | 4 | 26 | 26 không | 32 | 0 | – | 0 | không làm gì 6 |
| #6 | 4 | 24 | 24 không | 34 | 0 | – | 0 | không làm gì 6 |

## Khác biệt và rủi ro

1. **#1 — gửi quân lỗi "không đọc được x/y trước khi gửi" 12/51 lần** (24 %). Từ 22/11 còn 3/28. Nguyên nhân đã biết (khung "Hành quân x/y" ẩn khi 0 đội, learning 21/11) và P3 đã đọc bằng ảnh chữ số `templates/mdigits`; cần kiểm lại khi chạy thật (chỉ số `agent lỗi` trong báo cáo 24 giờ).
2. **#1 — agent ghé thêm**: 21 lần agent sẽ gửi quân lúc lịch cũ không ghé; ngày 22/11 agent thức dậy ~68 lần/ngày so với lịch cũ 19 lần/ngày (cận trên). Rủi ro: tốn giờ máy, chiếm 1 trong 2 suất chạy song song của các farm. Theo dõi `gio may` / `lan ghe` mỗi máy trong báo cáo 24 giờ.
3. **#1 — bỏ sót 3/19** lần lịch cũ gửi được quân mà agent không thức dậy gần đó (lệch > `gather_retry_min` = 10 phút). Có thể gửi chậm hơn vài phút, không mất quân.
4. **#0 — khác biệt theo luật, không phải lỗi**: 2 lần lịch cũ gửi quân ngày 19/11 là trước luật `gather.min_hq_level` = 9; nay nhà chính 7 nên agent đúng là không gửi.
5. **#0 — nghiên cứu (agent gọi bước cũ) lỗi 3/6** "bắt đầu nghiên cứu: 0": cùng nguyên nhân hàng chờ nghiên cứu ở P2 (thiếu tài nguyên / không đọc được "1/1").
6. **Farm cấp thấp #2–#6**: agent không gửi quân (HQ < 9) và hầu hết "không làm gì" vì dữ liệu thợ / hàng chờ **cũ (stale)** → agent không tác động khi độ tin thấp (đúng chính sách `min_state_confidence`). Nghĩa là trên farm thấp, agent chủ yếu chỉ quyết định *khi nào ghé*, còn việc trong lần ghé vẫn do `ORDER` cũ làm (learning 21/11: chế độ agent không thay ORDER).
7. **Không thấy** quyết định nào tốn kim cương (không có `ActionSpec` nào `premium_cost > 0`; `SafetyPolicy.premium_whitelist` rỗng).

## Kết luận cho P6

- Agent chưa sẵn sàng thay lịch cũ trên farm cấp thấp: lợi ích chỉ có ở máy HQ ≥ 9 (#1). Đề nghị khi chủ dự án duyệt: bật **công tắc chung** + chế độ Agent **chỉ #1** trước, chạy 24 giờ, đọc báo cáo `report_ro --since 24 --day24`.
- Trước P6 `data/settings.json` đang đặt chế độ Agent cho cả #0–#6. Từ P6 có công tắc chung `agent.enabled` (mặc định `false`): khi tắt, các máy này chạy theo lịch chung (smart) cho tới khi chủ dự án bật — xem [huong-dan-chay-that.md](../product/huong-dan-chay-that.md).
