# Phase 3 — kết quả benchmark (2026-11-22)

Công cụ: `python -u tools/perception_phase3_bench.py` (chỉ đọc ảnh đã lưu); kết quả thô `data/perception/phase3_{ac,b}.json`. Cùng giới hạn Phase 2: neo là mẫu cắt từ chính khung (đo độ bền, không phải độ chính xác thật), biến đổi tổng hợp, "vắng mặt" = inpaint.

## A. Phạm vi áp dụng của ORB (121 mẫu có neo)
| edgeThreshold/patchSize | mẫu có ≥12 điểm | ≥20 điểm | trung vị điểm |
|---|---|---|---|
| 31 (mặc định OpenCV) | 2 | 2 | 0 |
| 15 (đang dùng) | **32 (26 %)** | 27 | 0 |
→ ORB chỉ dùng được cho ~1/4 mẫu (icon phẳng ít góc thì không). `applicable()` chặn, không trả "không thấy".

## B. Template đa tỉ lệ (ms) vs ORB, trong ROI ±40 px, 32 mẫu ORB dùng được
| Biến đổi | ms | ORB min_inliers=6 | =8 | =10 | =12 |
|---|---|---|---|---|---|
| clean | 1,00 | 1,00 | 0,97 | 0,94 | 0,91 |
| che 25 % | 0,28 | **0,88** | 0,78 | 0,72 | 0,66 |
| che 40 % | 0,03 | **0,53** | 0,47 | 0,41 | 0,41 |
| che 60 % | 0,00 | 0,25 | 0,19 | 0,16 | 0,12 |
| mờ σ1,2 | **1,00** | 0,81 | 0,69 | 0,62 | 0,59 |
| mờ σ2,0 | **0,41** | 0,28 | 0,16 | 0,06 | 0,03 |
| nhiễu σ8 | 0,97 | 1,00 | 0,97 | 0,91 | 0,88 |
| vắng mặt, báo nhầm | 0/32 | 0/32 | 0/32 | 0/32 | 0/32 |
Bổ trợ nhau: ORB cứu che khuất (0,28→0,88 ở 25 %), ms tốt hơn khi mờ. Chọn `min_inliers=6` (retention cao nhất, 0 báo nhầm); n=32 nên cận trên báo nhầm còn ~10 % → phải kiểm lại bằng hard-negative ở Phase 5.

## C. Shape (thành phần liên thông)
Tổng hợp (200 cảnh, IoU≥0,5, ba mức sáng): Otsu P 0,997 / R 0,992 ở cả sáng thường, tối, sáng; mở 3×3 không đổi; adaptive P 0,75 (vỡ trên nền kết cấu); ngưỡng cố định 128 hỏng hoàn toàn khi tối (P=R=0). → mặc định Otsu.
Thực: chấm đỏ HSV + thành phần liên thông tìm lại 457/501 chấm của `bot.badges.red_dots` (91 %) trên 194 khung, nhưng ra 676 blob (nhiều hơn): chưa có nhãn nên không biết phần dư là đúng hay báo nhầm.
