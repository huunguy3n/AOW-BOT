# RECOGNITION_AUDIT — kiểm toán hệ nhận diện ảnh AOW-BOT

Ngày: 2026-11-21 · Giai đoạn: Stage A (chỉ đọc, chưa sửa mã sản xuất) · Nhánh: `roadmap-impl`

Quy ước: **[ĐÃ ĐO]** = có số liệu từ repo/DB; **[ĐỌC MÃ]** = thấy trực tiếp trong mã; **[GIẢ THUYẾT]** = chưa có bằng chứng, cần benchmark.

## 1. Công nghệ

Python 3.12, OpenCV (`cv2`), NumPy, Tesseract (`bot/ocr.py`), ADB screencap raw. Màn hình cố định 540×960 DPI 240 (ADR-0003). `cv2` được import trong ~38 file. Kiến trúc mới `src/aowbot` có luật import-linter: `domain`/`application` cấm `cv2` (D1, D2); `bot/*` chỉ được import `aowbot.domain` (D7).

## 2. Nơi lấy ảnh và nhận diện

| Mục | Vị trí | Ghi chú |
|---|---|---|
| Lấy ảnh | `bot/device.py` (`screencap_raw`), `bot/ctx.py:54 shot()`, `bot/stream.py` | 5135 lần/`bot` p50 0,5 ms p90 1,0 ms [ĐÃ ĐO, bảng `perf`] |
| Template matching (lõi) | `bot/vision.py` `Vision.best` / `find_all` (`cv2.matchTemplate TM_CCOEFF_NORMED`, ảnh màu BGR, không mask, không đa tỉ lệ) | 2 điểm gọi `matchTemplate` |
| Template matching (ngoài lõi) | `bot/imitate.py:143` (crop demo, th_crop 0,85), `bot/modules/tutorial.py:234` (có `mask=`), `bot/badges.py:127` (chữ "Miễn phí", ngưỡng 0,3) | 3 bản sao logic matching riêng |
| Nhận diện theo màu | `bot/badges.py` (chấm đỏ, ô sáng, ô "Nhận"), `bot/steer.py` (trận chạy đường), `bot/buttons.py` (nút theo hình) | HSV hard-code |
| OCR | `bot/ocr.py` (152 dòng) **và** `bot/ctx.py:617-660` (`_parse`, `_ocr_tesseract*`, `_ocr_digits`) | trùng lặp [ĐỌC MÃ] |
| Phân loại màn hình | `bot/screens.py identify()` (thứ bậc template + ROI), `bot/screen_types.py`, `bot/learn.py` (kNN trên `feat()` 1632 chiều) | 3 cơ chế song song |
| Học | `bot/learn.py`: nhật ký `exp`, biến thể `templates/<tên>@autoN.png` | ngưỡng/hồi quy riêng |

## 3. Số lượng ảnh mẫu và điểm gọi

- 211 PNG trong `templates/` (23 nhóm), chưa có biến thể `@auto` nào. Kích thước cạnh nhỏ nhất: **18 ảnh <20 px, 139 ảnh 20–39 px, 53 ảnh ≥40 px** [ĐÃ ĐO]. 66% mẫu có cạnh nhỏ <40 px.
- Điểm gọi `find / tap_tpl / tap_first / wait_for / find_all / best`: nhiều nhất `notify.py` (63), `tutorial.py` (44), `play.py` (42), `gather.py` (27), `ctx.py` (25), `alliance.py` (24) [ĐÃ ĐO bằng grep, đếm cả lời gọi không liên quan nhận diện].
- Ngưỡng `th=` rải rác: 0,85 (35 lần), 0,80 (31), 0,90 (30), 0,75 (11), 0,70/0,65 (3+3), và 8 giá trị lẻ khác; mặc định toàn cục `match_threshold: 0.82` (`config.yaml:16`). **Không có chỗ nào hiệu chuẩn ngưỡng theo lớp.** [ĐỌC MÃ]
- ROI hard-code: dict `ROI` trong `bot/screens.py:34-39`, các `*_roi` trong `config.yaml`, hàng chục tọa độ/ROI trong module.

## 4. Luồng tiêu thụ kết quả

`Ctx.find()` → `Vision.find()` → `(cx, cy, score)|None` → module (`gather`, `notify`, …) quyết định ngay trong cùng hàm rồi `ctx.tap()`. Không có tầng quyết định nào ở giữa: **điểm khớp cao-hơn-ngưỡng = hành động**. Không có trạng thái "không chắc" / "không biết". Mất mẫu = `None` = "không thấy" (không phân biệt "mẫu thiếu", "màn hình khác", "không có vật thể").

Hệ quả an toàn: `None` bị coi như "NotDetected" ở mọi nơi; chặn nút nguy hiểm dựa vào danh sách (`buttons.is_danger`, `demo`/`imitate` block) chứ không dựa vào độ tin cậy.

## 5. Phát hiện kiến trúc

1. `Vision` ôm 5 việc: nạp ảnh, biến thể học, bộ nhớ vị trí (`prior`, G2), matching, đếm `miss_hits` theo luồng.
2. `Ctx` (665 dòng) trộn chụp ảnh, tìm, chạm, OCR, nhật ký học, điều hướng.
3. Ba cơ chế phân loại màn hình độc lập (template/ROI, kNN, "screen_types" dạy tay) không có hợp đồng chung.
4. Điểm số TM_CCOEFF_NORMED được dùng như xác suất (`score ≥ th`), kể cả để học biến thể mới (`learn.py`) và ghi `exp.score`.
5. OCR lặp ở 2 nơi; tiền xử lý (resize/gray/threshold) lặp ở `ocr.py`, `ctx.py`, `imitate.py`, `learn.py`.
6. Phụ thuộc vòng: `learn.py` ↔ `ctx.py` ↔ `vision.py` (Vision có `var/extra/prior` chỉ để phục vụ `learn`). Xem DEPENDENCY_MAP.

## 6. Việc "~10% độ chính xác" — CHƯA XÁC MINH

Repo **không** chứa con số 10% hay bộ nhãn để tính nó. Số đo gần nhất [ĐÃ ĐO] cho thấy điều ngược lại *trên các lần khớp đã bắn*:

- 6602 lần chạm do template (kind `tpl`/`first`/`tap` có `tpl`) → **95,3 % làm màn hình đổi**; dải điểm 0,82–0,90: 95,4 %, 0,90–0,95: 90,2 %, ≥0,95: 95,5 %.
- `identify()` trên `tests/fixtures/screens`: 13/13 đúng, 206 ms/ảnh. Hồi quy `pytest -m "not fixtures"`: 369 passed.
- `nav`: 592/10673 = **5,5 % màn "unknown"**.

Nhưng các số này có **thiên lệch người sống sót**: `exp` chỉ ghi khi đã khớp; không ghi lần *đáng lẽ khớp mà không khớp* (false negative) hay khớp sai nhưng "đổi màn" tình cờ. Vì vậy 10% có thể đúng cho một lớp/biến thể cụ thể (ví dụ bản Global 3.6.0 trên #2–#6 dùng mẫu cắt từ bản VN 2.5.16, hoặc vật thể hoạt ảnh). **Cần chủ dự án cho biết nguồn con số 10%** (lớp nào, máy nào, đo bằng cách nào) — xem PLAN §Câu hỏi.

## 7. Cái chưa kiểm tra (không suy đoán)

- Tỉ lệ false negative / false positive thật (cần nhãn người).
- Phân bố điểm khớp của lần *không bắn*.
- Khác biệt UI giữa bản VN 2.5.16 và Global 3.6.0.
- Hiệu năng CPU/RAM của matching (đã đo thời gian `identify` nhưng không đo theo từng lớp).
