# Đề xuất: vòng lặp "xả việc theo phiên" (session drain)

Trạng thái: **G0 đã đo (2026-11-22); G1 trở đi chờ chủ dự án duyệt** (ADR-0012). Liên quan:
[priority-queues-plan.md](priority-queues-plan.md), [screen-loop-plan.md](screen-loop-plan.md), [performance-baseline.md](performance-baseline.md).

## 1. Vấn đề (chủ dự án, 2026-11-22)
Bot chưa bao giờ xong hết việc trong 1 lần login; ra vào thành phố lặp vô nghĩa; tiến trình gần tới thì dừng; nhà chính lên ~1 cấp/ngày.

## 2. Nguyên nhân cấu trúc
| Triệu chứng | Nguyên nhân |
|---|---|
| Ra vào thành phố vô nghĩa | Mỗi bước tự `ensure_city()` và tự điều hướng; chi phí chuyển màn không nằm trong quyết định xếp lịch; việc cùng màn không được gom. |
| Gần xong thì dừng | Việc dài (nhà chính cần chuỗi công trình điều kiện) bị cắt qua nhiều lần ghé; không lưu cây phụ thuộc nên mỗi lần phải khám phá lại bằng "Nhảy"; bị chặn thì khóa mù (`no_effect` tới +2h) không có điều kiện mở khóa. |
| Không xong hết 1 lần login | Mỗi lần ghé chạy danh sách bước cố định rồi tắt máy; không hỏi "còn việc sẵn sàng không". Stuck/watchdog kết thúc cả lượt. |
| 1 thợ xây bị tranh | `upgrade`, `quests`, `mainquest`, `construct` đều tự xây thứ riêng; không ai biết nhà chính là đường găng. |
| "started" không chắc | Thành công suy từ giao diện, không đối chiếu hàng chờ thực. |

## 3. Thuật toán đề xuất
1. **Mô hình theo ô tài nguyên**, không theo module: thợ xây, nghiên cứu, huấn luyện, đội hành quân. Mục tiêu: giảm tổng thời gian rảnh của các ô. Mỗi ô có `free_at`.
2. **Cây mục tiêu bền (goal DAG)** trong `memory.db`: nhà chính cấp N+1 cần công trình nào ở cấp nào; đọc một lần từ màn điều kiện. Thợ rảnh → lấy nút chưa bị chặn nằm trên đường găng.
3. **Tác vụ khai báo đủ**: màn cần đứng, ô chiếm, điều kiện sẵn sàng, giá trị kỳ vọng, **hậu điều kiện kiểm chứng** (vd hàng chờ xây +1). Chỉ tính thành công khi hậu điều kiện đúng.
4. **Phiên = xả đến cạn**: lặp { lấy tác vụ sẵn sàng → gom theo vị trí (thành phố / panel / thế giới) → xếp theo giá trị/chi phí → chạy → kiểm hậu điều kiện → tính lại }. Dừng khi hết việc sẵn sàng hoặc hết ngân sách thời gian. Cuối phiên hẹn lần ghé lại đúng lúc ô tiếp theo rảnh.
5. **Điều hướng theo đồ thị màn hình** (`screen_types`): biết đang ở đâu, đi đường ngắn nhất; chỉ reset về thành phố khi không nhận ra màn.
6. **Phân xử thợ xây**: ưu tiên nút đường găng nhà chính; quests/mainquest chỉ dùng thợ khi trùng nút đó hoặc nhà chính bị chặn tài nguyên. Bị chặn → ghi `lý do + điều kiện mở khóa + giờ thức dậy`.
7. **Lỗi không kết thúc phiên**: lỗi/Stuck → ghi, nhận diện màn để phục hồi, bỏ tác vụ đó, sang tác vụ khác; chỉ khởi động lại game khi mất màn nhiều lần.

## 4. Lộ trình (duyệt từng giai đoạn)
- **G0 – Đo (chỉ đọc)**: `python tools/measure_g0.py [--since H] [--json]`. Xong, kết quả ở §5.
- **G1 – Kế hoạch nhà chính + phân xử thợ xây.** Đã cài đặt (2026-11-22), CHƯA chạy thật trên máy: xem §6.
- **G2 – Vòng xả việc.** Đã cài đặt (2026-11-22): xem §7. Chưa làm: gom theo vị trí, hậu điều kiện kiểm chứng.
- **G3 – Bỏ `ensure_city` thừa.** Đã cài đặt (2026-11-22): xem §7. (Đồ thị màn hình đã có sẵn trong `bot/screens.py` + `ctx.goto`; G3 chỉ cắt kiểm tra lặp.) Không có G4 trong tài liệu.

Số đo thành công: % rảnh của thợ xây/nghiên cứu/huấn luyện; thao tác điều hướng trên mỗi tác vụ xong; tác vụ xong trên mỗi phiên; tốc độ nhà chính theo giờ thực.

## 5. Baseline G0 (data/memory.db, 2026-11-19 → 2026-11-22 17:50)
Cách đọc / hạn chế: ô rảnh là **cận trên** (chỉ quan sát được khi ghé máy). `%loi` gồm cả kết quả `warn`. Cột `nav` 'done' là bản ghi "đang ở màn", không phải một lần chuyển màn.

**Downtime**: 402 lần ghé trong 89h; **53h (60%) không có lần ghé nào** (khoảng >30 phút). Lớn nhất: 19/11 21:13→20/11 20:23 (23h), 19/11 13:01→20:07 (7h), 22/11 02:14→08:31 (6h), 22/11 09:49→13:22 (3.6h).

**Kết quả lần ghé**: ok 256, interrupted 78 (TB 2.9 phút), error 48, stopped 19. Chỉ 64% lần ghé chạy trọn.

**Ô rảnh (cận trên)**: #0 nghiên cứu 100%, huấn luyện 99% (hàng chờ có nhưng không đầy); #4 xây 94%, #6 xây 100%, #5 xây 53%; #2 xây 24%, #3 xây 18%, #1 xây 0%.

**Điều hướng**: 15.258 thao tác/402 lần ghé (trung vị 43/lần). Nhiều nhất: `reddots` 5179 (20.7/lần ghé), `quests` 3532 (17.6/lần), `observe` 1339, `mainquest` 1014, `notify` 883.

**Bước tốn thời gian mà ít hiệu quả** (phút tổng; % lần trả 0 = không làm gì):
| Bước | Lần | % trả 0 | % lỗi/warn | Phút |
|---|---|---|---|---|
| reddots | 250 | 48 | 96 | 679 |
| quests | 204 | 76 | 36 | 395 |
| mainquest | 224 | 95 | 50 | 211 |
| tutorial | 19 | 32 | 79 | 184 |
| notify | 124 | 1 | 22 | 135 |

**Kết luận từ số đo**
1. 60% thời gian không có ai ghé máy → thợ xây các máy farm thấp (#4, #6) ngồi rảnh. Đây là chỗ mất nhiều nhất, trước cả thuật toán.
2. `reddots`, `quests`, `mainquest` ăn ~1300 phút và ~9700 thao tác nhưng phần lớn trả 0 hoặc cảnh báo → gom/chặn theo điều kiện sẵn sàng (G2) sẽ cắt mạnh.
3. 36% lần ghé không chạy trọn (interrupted/error/stopped) → cần "lỗi không kết thúc phiên" (G2) và tìm nguyên nhân `interrupted` (có thể do khởi động lại web/runner).
4. Việc cần làm ngay, không cần thuật toán mới: tìm vì sao runner không chạy 53h (xem log hệ thống/khởi động web).

## 6. G1 đã làm (2026-11-22) — phạm vi và giới hạn
- [src/aowbot/domain/hqplan.py](../../src/aowbot/domain/hqplan.py) (hàm thuần, 9 test ở `tests/unit/test_hqplan.py`) + cầu nối [bot/hqplan.py](../../bot/hqplan.py) lưu fact `hq_plan` trong `memory.db`.
- `upgrade` ghi kết quả mỗi lần chạy: `started` → CHAIN (giữ thợ cho nhà chính 15 phút sau khi thợ rảnh); `busy/no_builder` → WAIT_BUILDER (thức dậy theo thời gian còn lại nếu đọc được, mặc định 30 phút); `blocked` → WAIT_RESOURCES (thử lại sau 1h, giữ thợ tối đa 2h để khỏi deadlock); `none` (không tới được màn nâng cấp) → UNREACHED, **lùi lịch 30p, 1h, 2h… tối đa 4h**, không giữ thợ.
- `quests` và `construct` bỏ qua khi kế hoạch đang giữ thợ **và** thợ đang rảnh (thợ bận thì họ không xây được gì, nên không gây tranh). Chỉ áp dụng khi `build.max_builders <= 1`.
- **Chưa làm** so với đề xuất: cây phụ thuộc đầy đủ (công trình nào, cấp nào) — cần đọc danh sách điều kiện trên màn "Nhảy" bằng OCR, phải kiểm trên máy thật; mainquest chưa bị chặn thợ (còn đánh chiến dịch).
- Chưa kiểm chứng trên máy: cần chạy 1 lượt + kiểm lại (xem log "Ke hoach nha chinh:" và "Bo buoc quests/construct").
- Ghi chú test: `tests/legacy/test_priority_queues.py::test_research_waits_for_hq_and_scheduler_skips` pass khi chạy riêng, fail khi chạy cả bộ (ảnh giả là chuỗi 'hq' đưa vào OCR trong `research.py`); không do G1, chưa sửa.

## 7. G2 + G3 đã làm (2026-11-22)
**G2 – xả việc** ([drain.py](../../src/aowbot/domain/drain.py), 6 test; nối vào vòng bước ở `bot/runner.py`, cấu hình `drain:` trong `config.yaml`):
- Sau lượt ORDER, trước `observe`, nếu một bước làm được việc (`ret` > 0) thì chạy lại các bước đã chạy TRƯỚC nó mà việc đó có thể mở khóa (tài nguyên/quà vừa nhận → `upgrade/construct/train/research/heal/quests/mainquest`; `construct` → `upgrade`). Mỗi bước chạy lại tối đa 1 lần, riêng `upgrade` lặp tới 6 lần miễn là còn trả > 0 (nâng cấp tức thì miễn phí dồn chuỗi điều kiện nhà chính vào 1 lần ghé). Tối đa 8 lần chạy lại và 30 phút mỗi lần ghé; tắt bằng `drain.enabled: false`.
- Chạy thật trên #4 (bước rewards, train, upgrade, construct, daily): `daily` xong → chạy lại `train, upgrade, construct`; `upgrade` chạy lại bắt đầu thêm 1 nút điều kiện nhà chính trong cùng lần ghé; lần sau dừng đúng khi thợ bận.

**G3 – kiểm tra thành phố thừa** (`Ctx.ensure_city`, `Device.act_seq`, 4 test): 8155/15806 bản ghi `nav` là `done` liền sau `done` (reddots 4090, quests 1881, notify 632…) → mỗi lần ~1 giây chụp + quét popup. Nay `ensure_city` bỏ qua nếu lần kiểm trước xác nhận đúng thành phố, không có thao tác (tap/swipe/Back) nào ở giữa, và chưa quá `nav.skip_recheck_s` (3 giây; 0 = tắt). Ước lượng tiết kiệm ~4–5% thời gian ghé (136 phút/2922 phút trong dữ liệu 3 ngày); 

**Đo G3 trên #4 (2026-11-22, notify + reddots + rewards, 9,9 phút):** `ensure_city` được gọi 74 lần: kiểm tra thật 22 lần (trung bình 1,36 s), **bỏ qua 52 lần (70%) → tiết kiệm ~71 s trên ~594 s chạy (~12%)**. Con số này cao hơn ước lượng 4–5% vì lượt đo toàn bước nặng chấm đỏ. Dòng log `G3: kiem tra thanh pho ...` in cuối mỗi lần ghé. Lượt đầy đủ 17 bước (19:19–19:36, 18,6 phút) xong trọn trong 1 lần đăng nhập; `reddots` vẫn là điểm nghẽn (709 s ở lượt đầu, 404 s ở lượt sau) — cần xử lý riêng.
