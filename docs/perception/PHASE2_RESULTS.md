# Phase 2 — kết quả benchmark (2026-11-22)

Công cụ: `python -u tools/perception_phase2_bench.py` (chỉ đọc ảnh đã lưu). Kết quả thô: `data/perception/phase2_{a,b2}.json` (ngoài git).
**Giới hạn:** 121 neo = mẫu cắt từ chính khung fixtures (điểm legacy ≥0,95) → số đo *độ bền với biến đổi*, KHÔNG phải độ chính xác thật; biến đổi là tổng hợp; "vắng mặt" = inpaint vùng mẫu (40 neo); chưa có hard-negative (vật giống nhau).

## A. Biến thể khớp mẫu (retention = còn điểm ≥0,82 đúng chỗ; rank_ok = điểm đúng > điểm cao nhất khi vắng mặt)
| Biến đổi | bgr (legacy) | gray | clahe | grad (Sobel) | ms (bgr đa tỉ lệ 0,90–1,10) |
|---|---|---|---|---|---|
| clean | 1,00 | 1,00 | 0,96 | 0,93 | 1,00 |
| gamma 0,7 / 1,5 | 1,00 / 1,00 | 1,00 / 1,00 | 0,94 / 0,98 | 0,93 / 0,92 | 1,00 / 1,00 |
| glow +120 (sáng cục bộ) | 0,97 | 0,98 | 0,73 | 0,79 | 0,97 |
| blur σ1,2 / σ2,0 | 0,88 / 0,29 | 0,88 / 0,30 | 0,37 / 0,12 | 0,46 / 0,00 | 0,95 / 0,43 |
| scale 0,90 / 0,95 | 0,17 / 0,40 | 0,19 / 0,40 | 0,08 / 0,17 | 0,01 / 0,16 | **1,00 / 1,00** |
| scale 1,05 / 1,10 | 0,47 / 0,22 | 0,46 / 0,24 | 0,20 / 0,07 | 0,17 / 0,04 | **1,00 / 1,00** |
| che 25 % | 0,44 | 0,58 | 0,28 | 0,25 | 0,44 |
| rank_ok scale 0,90 / 1,10 | 0,80 / 0,78 | 0,75 / 0,72 | 0,72 / 0,75 | 0,62 / 0,57 | **1,00 / 1,00** |
| FP khi vắng mặt (≥0,82), clean | 0,03 | 0,03 | 0,03 | **0,33** | 0,03 |

Kết luận có số: (1) CLAHE và gradient/Sobel làm khớp mẫu **tệ hơn** legacy (retention thấp hơn, gradient FP 33 %) → không dùng làm tiền xử lý khớp. (2) Chuyển xám không đổi gì → màu không phải nhân tố. (3) Đa tỉ lệ cứu hoàn toàn lỗi lệch tỉ lệ ±10 % (0,17–0,47 → 1,00) và mờ nhẹ, không tăng FP đáng kể (0,03 → 0,03–0,05, n=40). (4) Che 25 % không biến thể nào cứu → cần đặc trưng cục bộ (ORB) ở Phase 3.

## B. `detect_change` (độ sáng), 715 cặp khung từ 65 khung thật
Mặc định chọn **k=4, min_area=0,01** (nhiễu σ≤8 báo nhầm ≤2 %; mảng sáng 80×80 phát hiện 100 %; gain/bias toàn cục nhận 89–100 %). Điểm yếu đã đo: gain 1,1 báo "cục bộ" nhầm 22 % (bão hòa 255 phá mô hình affine); dịch chuyển kết cấu 10 px chỉ phát hiện 25 % (đổi độ sáng ít); bias −12 báo cục bộ nhầm 31 % (cắt tại 0).
Lỗi đã sửa nhờ benchmark: ước lượng nhiễu bằng MAD tụt thấp trên số nguyên (σ=2 → 1,48) làm nhiễu bị báo là thay đổi cục bộ 100 %; đổi sang (p95−p5)/3,29 + bù mô hình gain/bias.
