# RECOGNITION_BASELINE (Stage A — số đo hiện có, KHÔNG phải độ chính xác)

Nguồn: `data/memory.db` (đọc ở chế độ chỉ-đọc) ngày 2026-11-21; `tools/check_screens.py`; `pytest`. Chưa có nhãn người → **chưa có Precision/Recall/F1**. Các số dưới đây chỉ là *tín hiệu gián tiếp*.

## A. Kết quả chạm theo template (bảng `exp`, 13 715 dòng)
Đã khớp rồi mới chạm → chỉ đo được "khớp thì có tác dụng không" (≈ precision gián tiếp, bị thiên lệch).

| Loại chạm | n | màn đổi / có phản ứng |
|---|---|---|
| `first` (tap_first) | 2116 | 98,5 % |
| `tpl` | 3088 | 93,0 % |
| `tap` (toạ độ cố định) | 5927 | 86,5 % |
| `back` | 526 | 94,9 % |
| `human` (người chơi) | 2077 | 95,0 % |
| Tổng chạm có `tpl` | 6602 | **95,3 %** |

| Dải điểm khớp | n | tác dụng |
|---|---|---|
| 0,82–0,90 | 667 | 95,4 % |
| 0,90–0,95 | 184 | 90,2 % |
| ≥ 0,95 | 4353 | 95,5 % |

Điểm bất thường: `gather/btn_recommended` 127 lần, 0 % đổi màn (khớp 1,0): nút làm thay đổi cục bộ, không phải lỗi nhận diện — cho thấy "màn đổi" là nhãn yếu.
Điểm khớp **không đơn điệu** với tác dụng (0,90–0,95 thấp hơn 0,82–0,90) → điểm không phải xác suất đã hiệu chuẩn.

## B. Phân loại màn hình
- `nav`: 10 673 lần; unknown 592 (**5,5 %**); city 73 %, panel 9 %, popup 5 %, world 3,7 %, loading 2,9 %.
- `tools/check_screens.py`: 13/13 đúng, 206 ms/ảnh (tập fixture nhỏ, chỉ 6 lớp).
- `pytest -m "not fixtures"`: 369 passed, 34 deselected (hồi quy ảnh chỉ chạy local).

## C. Độ trễ (bảng `perf`, p50/p90 ms, nguồn `bot`)
`screencap` raw 0,5/1,0 · `identify` 0,3/0,3 (trung bình theo nhóm, có prior ROI) · `ocr` 0,2/0,2 · full-screen `identify` trên fixture 206 ms/ảnh. Chưa đo CPU/RAM.

## D. Dữ liệu sẵn có để dựng benchmark (đếm thật)
| Nguồn | Số lượng | Nhãn có sẵn | Ghi chú |
|---|---|---|---|
| `logs/human/20261121` | 2057 bộ before/after/mark | điểm chạm của người (nhãn "đây là chỗ bấm") | gần như chưa có lớp đối tượng |
| `data/exp/crops` | 6224 crop quanh điểm chạm | `tpl`, `score`, `outcome` (nhãn yếu) | thiên lệch theo template hiện có |
| `logs/shots` | 701 | ảnh lỗi | chủ yếu ca khó (tốt cho negative/hard) |
| `logs/rec/…tan_thu` | 199 + 9 sheets | bản ghi tân thủ | một phiên |
| `tests/fixtures/*` | ~400 (screens 13, taught 144, screen_loop 19, tutorial 30…) | nhãn loại màn | không có trong git |
| `screen_samples` | 1954 | `label` loại màn (+ tọa độ) | dùng cho kNN |
| `templates/` | 211 | tên lớp = tên file | 18 <20 px, 139 20–39 px |

Không có: bbox theo lớp, che khuất/hiện diện, nhãn "vắng mặt" (negative) rõ ràng, nhãn theo bản game (VN 2.5.16 / Global 3.6.0).

## E. Điều chưa biết (phải đo ở Stage B giai đoạn 1)
Precision/Recall/F1 theo lớp; false-positive rate; false negative do ngưỡng; ảnh hưởng bản game/lớp phủ tối tân thủ; CPU/RAM; con số "~10 %" của chủ dự án.

---

# P1b — dataset v0 và số đo "độ phủ mục tiêu người chọn" (2026-11-21)

Công cụ: `python tools/perception_build_dataset.py --n 5000` → `data/perception/v0/` (ngoài git). Nguồn: `logs/human/20261121` (1437 chạm tay, 627 vuốt; 1134 chạm dùng được: ảnh `before` đủ 540×960). Mỗi chạm tay là bằng chứng **độc lập** rằng (x, y) là chỗ bấm được. Hỏi: ảnh mẫu cũ (189 lớp, ngưỡng 0,82) có khớp ngay chỗ đó không (cửa sổ quanh điểm chạm; điểm khớp tại mỗi vị trí như khớp cả màn).

| | n | có mẫu khớp tại điểm chạm |
|---|---|---|
| Tất cả | 1134 | 411 = **36,2 %** |
| #0 | 89 | 31,5 % |
| #1 | 283 | 39,2 % |
| #2 | 86 | 38,4 % |
| #3 | 594 | 34,7 % |
| #4 | 55 | 38,2 % |
| #6 | 27 | 44,4 % |

**Đọc đúng con số:** đây KHÔNG phải recall. Nó là "tỉ lệ chạm tay rơi vào chỗ đã có mẫu". Xem [uncovered_sample.png](uncovered_sample.png) (24 chạm đầu trong số 723 chạm không phủ): đa số là **đối tượng bản đồ** (cột mốc cờ/đầu lâu, mỏ, công trình, quái), icon menu (thư, "Chiến lược", "Tài nguyên"), thẻ tướng và nút chữ chưa có mẫu ("Đến", "Cướp bóc"). Tức phần lớn khoảng trống là **thiếu lớp / vật thể động**, không phải mẫu có sẵn mà khớp trượt. Không tách được từ dữ liệu này: chạm "lấy nét/đóng bằng cách chạm trống" (không có đối tượng), nên 36 % là cận dưới thô.

**Giả thuyết cập nhật:**
- H3 (bản game): độ phủ #1–#6 giống nhau (31–44 %, mẫu nhỏ #4, #6) → chưa thấy dấu hiệu bản Global kém hơn; nhưng ánh xạ instance → bản game chưa được ghi nhận trong dữ liệu, mọi mẫu đang `game_build="unknown"`. **Chủ dự án cần điền.**
- Có bằng chứng mới cho "thiếu lớp + đối tượng bản đồ động" (template cứng khó hợp) — ứng viên cho provider đặc trưng/phát hiện ở P4, quyết định sau khi có nhãn.
- H1/H2/H4/H5 vẫn chưa kiểm: cần nhãn lớp do người duyệt.

**Dataset v0:** 1134 mẫu, `source=bootstrap`, `complete=false`, split train 840 / val 294 / test **0** (cố ý: test chỉ nhận nhãn người). 411 mẫu có nhãn lớp gợi ý từ mẫu cũ (circular → **không** dùng để đo độ chính xác của mẫu cũ). 723 chạm chưa phủ đã xuất `data/perception/v0/review/*.png` (crop 120 px) + `review.csv` (cột `class` để trống).

**Chưa làm / chưa đo:** Precision, Recall, F1, FPR của Vision cũ (cần test do người duyệt); CPU/RAM.
**Việc cần người (chặn P1b hoàn tất):** (1) điền `game_build` theo instance; (2) đặt tên lớp cho các chạm trong `review.csv` (hoặc đánh dấu "không có đối tượng"); (3) duyệt tối thiểu ~300 ảnh test gồm ≥30 % negative.
