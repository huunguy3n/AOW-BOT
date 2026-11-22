# Phase 4–6 — kết quả benchmark (2026-11-22)

Công cụ: `tools/perception_phase4_bench.py` (theo dõi), `tools/perception_calibrate.py` (hiệu chuẩn + hợp nhất),
`tools/perception_phase6_ms_bench.py` (tùy chọn tăng tốc), `tools/perception_perf_bench.py` (độ trễ/CPU/RAM, shadow offline, tần suất thích nghi).
**Giới hạn chung:** dữ liệu tổng hợp hoặc neo cắt từ chính khung; KHÔNG có nhãn người; chưa chạy trong vòng lặp bot thật.

## Phase 4 — theo dõi
Tracker thuần (30 hạt giống × 5 kịch bản, dt=0,2 s): baseline "gán gần nhất theo vị trí cũ" vs Kalman+Hungarian (accel 200, gate 80, max_misses 6):
IDF1 trung bình 0,50 → **0,86**, ID switch trung bình/chuỗi 20,5 → **1,4**, MOTA 0,71 → 0,80. Che khuất (S4): IDF1 0,71 → 0,92. Kịch bản sạch: MOTA 0,98 (mất khung xác nhận đầu).
Đầu–cuối (sprite thật trên nền khung thật, MotionDetector → TrackManager): sạch MOTA 0,64 / IDF1 0,82 / recall 0,81 (nền trung vị 9 khung + min_area 400; trước đó 0,29 recall, MOTA −0,57). **Nhấp nháy sáng toàn màn mỗi khung (±15 %/±15) vẫn yếu**: recall ~0,33, MOTA âm. Hai vật cắt nhau gộp thành 1 blob (giới hạn của phát hiện theo chuyển động). Lỗi đã sửa nhờ benchmark: bù sáng affine thất bại khi bão hòa → hàm chuyển cường độ + loại điểm bão hòa.

## Phase 5 — hiệu chuẩn, hợp nhất (nguồn `synthetic-anchors-v1`, tách train/test THEO MẪU)
Trên tập test (448 hàng, 221 dương): AUC điểm thô 0,995 → hợp nhất 0,997; ECE 0,03. Ngưỡng chọn trên train (precision ≥0,99 / loại ≤1 % dương): `confirm_p=0,898`, `reject_p=0,062`.
Trên test: CONFIRMED precision **1,00**, recall **0,887** (legacy th 0,82: precision 1,00, recall 0,833); 12 % rơi vào UNCERTAIN (legacy không có trạng thái này); loại nhầm dương 0 %.
**Chưa phải xác suất thật** (không nhãn người); vùng test là cùng phân bố tổng hợp, nên chỉ chứng minh hiệu chuẩn không tệ hơn điểm thô, không chứng minh độ chính xác trên bản Global 3.6.0.
Shadow offline (`data/perception/shadow.jsonl`, 40 khung × 20 lớp `common/`, ROI như screens.py): legacy "thấy" 48 → mới CONFIRMED cả 48; legacy "vắng" 752 → mới NOT_DETECTED 559, UNCERTAIN 181, **CONFIRMED 12** (lệch chờ người xem: có thể là phát hiện đúng khi lệch tỉ lệ hoặc báo nhầm).

## Phase 6 — hiệu năng
Tùy chọn khớp mẫu (80 neo, 7 biến đổi): xám cho retention/FP/rank bằng BGR (1,00/≤0,01 ở scale ±10 %); thoát sớm khi điểm ở tỉ lệ 1,0 ≥0,95: toàn màn **310 → 11 ms**, ROI 6,1 → 0,3 ms. Chọn mặc định `gray=True, early_exit=0,95`. Cắt tỉa tỉ lệ khi vắng mặt KHÔNG an toàn (điểm ở tỉ lệ 1,0 của vật đúng p1=0,27 chồng lấn với vắng mặt p95=0,55) → vắng mặt vẫn tốn ~100 ms/lớp toàn màn.
Đo 40 khung × 20 lớp: legacy ROI 338 ms/khung; **service ms ROI 1166 ms**, +ORB điều kiện 1227 ms, toàn màn 1851 ms (legacy toàn màn 567 ms). → mới chậm ~3,4× legacy khi phần lớn lớp vắng mặt: **chưa đạt gate "p95 ≤ legacy×1,5"**. Giảm nhẹ: ROI, tần suất thích nghi, bỏ ORB khi đã CONFIRMED, tùy chọn `SCALES_5` (gần gấp đôi nhanh).
Tần suất thích nghi (so sánh trên ROI, 2724 truy vấn từ cặp before/after của người chơi, 146 truy vấn đổi kết quả): diff TB<1 → bỏ qua 20 %, 0 đổi; <2 → 37 %, 0 đổi; nhưng test tổng hợp cho thấy diff TB làm loãng thay đổi nhỏ (che 25 % vật trong ROI 160×150 chỉ diff 1,1) → mặc định bảo thủ `skip_below=1,0`; đặt `None` để tắt.
RAM: đỉnh Python 2–8 MB/lần xử lý (RSS đo không thấy tăng); CPU gần bằng thời gian tường (1 luồng).

## Release gates (đề xuất, đối chiếu)
| Gate | Kết quả |
|---|---|
| Precision ≥ legacy (test tổng hợp) | đạt (1,00 vs 1,00) |
| Recall ≥ legacy | đạt (0,887 vs 0,833) |
| Lớp không đảo ngược: precision ≥0,99 + 0 FP ở shadow thật | **chưa kiểm** (chưa có shadow trong vòng bot thật, 12 lệch chờ người) |
| p95 độ trễ ≤ legacy ×1,5 | **chưa đạt** (~3,4×) |
| CPU/RAM trong ngân sách 2 instance | RAM ổn; CPU chưa đo khi chạy song song |
| Toàn bộ test + import-linter xanh | đạt |
| Diễn tập rollback | chưa (chưa nối vào bot; legacy vẫn nguyên) |

## Hiệu chỉnh sau khi xem 12 ca lệch shadow (2026-11-22)
Xem ảnh thật cho thấy **5 trong 12 ca là báo nhầm do chính thay đổi của tôi**, benchmark tổng hợp không bắt được vì tập "vắng mặt" chỉ là inpaint (không có vật giống-mà-khác-màu, D6):
- Khớp xám (Phase 6) làm nút **X xanh-trắng (`btn_x_offer`, `btn_x`) khớp X đỏ** (xám ~0,92, BGR ~0,72): 5 ca. Sửa: tìm bằng xám rồi **xác minh màu bằng BGR tại đúng chỗ** (`TemplateDetector._gray_then_verify`; BGR thấp hơn xám >0,10 → tìm lại BGR đầy đủ). Test hard-negative có sẵn trong `test_perception_detectors.py`.
- **ORB đẩy `btn_rebuild` ("Xây dựng lại", xanh dương) lên CONFIRMED trên nút "Bắt đầu lại" (xanh lá)**: template chỉ 0,55 nhưng 9 inlier ORB (chữ "lại" chung) → p 0,93. Sửa: `ConfidenceEvaluator.primary` — detector phụ chỉ được giữ ở UNCERTAIN, không CONFIRMED một mình (cần p template ≥0,5).
Số mới (test tổng hợp): CONFIRMED precision 1,00, **recall 0,829 (≈ legacy 0,833)**; UNCERTAIN 14 %. Tức mức tăng recall 0,887 báo trước đó chủ yếu là các xác nhận chỉ-nhờ-ORB, nay bị chặn: lợi ích còn lại là dải UNCERTAIN (không bị coi là vắng mặt), không phải recall cao hơn legacy.
Còn lại 7 ca lệch: toàn `btn_back`/`btn_back2` (mũi tên quay lại, ở góc trái trên/dưới) khớp BGR 0,91–0,92 ở tỉ lệ 0,9 / 1,1, trong khi legacy ra 0,80–0,82 ở tỉ lệ 1,0 (sát ngưỡng). Nhiều khả năng là **phát hiện đúng** (cùng nút, lệch kích thước/độ sáng), nhưng **chưa có nhãn người** để khẳng định.
