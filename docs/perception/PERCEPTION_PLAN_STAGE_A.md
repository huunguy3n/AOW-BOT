# Kế hoạch Perception Engine — Stage A (chờ duyệt, chưa viết mã)

Căn cứ: [AUDIT](RECOGNITION_AUDIT.md) · [DEPENDENCY MAP](RECOGNITION_DEPENDENCY_MAP.md) · [BASELINE](RECOGNITION_BASELINE.md). Làm theo giai đoạn, chủ dự án duyệt từng phase (ADR-0012).

## 1. Đánh giá kiến trúc hiện tại
Matching một thuật toán (TM_CCOEFF_NORMED màu, không mask/đa tỉ lệ) nằm trong `Vision`, kết quả `(x,y,score)|None` dùng thẳng làm lệnh chạm. Không có hợp đồng kết quả, không có trạng thái "không chắc/không biết", ngưỡng rải 13 giá trị, 3 bản matching ngoài lõi, 3 bộ phân loại màn song song, OCR + tiền xử lý lặp. Bằng chứng ở AUDIT §3–§5.

## 2. Giả thuyết nguyên nhân (xếp theo khả năng; **tất cả chưa kiểm chứng**)
| # | Giả thuyết | Bằng chứng hiện có | Cách kiểm |
|---|---|---|---|
| H0 | Con số ~10 % đến từ phạm vi hẹp (một lớp/bản game), không phải toàn hệ | `exp`: 95,3 % chạm có tác dụng; nhưng thiên lệch người sống sót | hỏi chủ dự án + benchmark theo lớp/bản |
| H1 | Mẫu nhỏ/ít kết cấu (66 % <40 px, 18 <20 px) làm tương quan chuẩn hóa không ổn định | thống kê kích thước mẫu | phân bố điểm vs kích thước/độ lệch chuẩn mẫu |
| H2 | Mẫu chứa nền/hoạt ảnh; không dùng mask | README ("tránh nền thay đổi"), tutorial dùng `mask=` | thử mask/gradient/viền trên tập nhãn |
| H3 | Mẫu cắt từ VN 2.5.16, nhưng #2–#6 chạy Global 3.6.0 | CLAUDE.md §Môi trường | benchmark tách theo bản game |
| H4 | Ngưỡng tay, không hiệu chuẩn; điểm không đơn điệu với tác dụng | BASELINE §A | đường cong hiệu chuẩn theo lớp |
| H5 | Lớp phủ tối/độ sáng (tân thủ), `prior` khóa vị trí cũ | `badges min_v`, `Vision.prior` | tập negative/hard, tắt prior |
| H6 | Thiếu nhãn/đo FN: không biết mình sai ở đâu | `exp` chỉ ghi khi khớp | dataset Phase 1 |

Không chọn thuật toán nào trước khi có benchmark.

## 3. Kiến trúc đích
Gói mới `src/aowbot/perception/` (tách khỏi `bot/*` và khỏi quyết định game):

```
perception/
  contract.py      # thuần: Status{Confirmed,Uncertain,Unknown,NotDetected,InvalidFrame}, Detection, RecognitionResult,
                   #   FrameId, Candidate, Diagnostics   (không import cv2)
  calibration.py   # thuần: ánh xạ điểm→xác suất theo (provider, lớp) từ dữ liệu benchmark (isotonic/Platt, bảng tra có phiên bản)
  fusion.py        # thuần: quy tắc hợp nhất, bất đồng, margin top-1 vs top-2, ngưỡng theo lớp, được phép "abstain"
  config.py        # thuần: cấu hình có phiên bản (YAML → dataclass), không ngưỡng hard-code
  ports.py         # Protocol: FrameSource, Provider, Preprocessor, Clock
  coordinator.py   # điều phối provider theo lớp/vùng, đo thời gian, gom kết quả; không biết OpenCV
  adapters/        # cv2: frame_validation, preprocess (một nơi duy nhất), regions, providers/{template,multiscale_template,feature,...}
  state.py         # PerceptionState (kết quả theo frame, hết hạn)
  diagnostics.py   # lưu provider-raw, ảnh crop khi Uncertain/Unknown
  eval/            # dataset loader, metrics (P/R/F1/FPR/confusion/latency), compare old-vs-new, gate
```
Quy tắc: `contract/calibration/fusion/config/coordinator` thuần (kiểm bằng import-linter như D1/D2); `adapters` mới được dùng `cv2`. Provider chỉ nhận ảnh + vùng, trả điểm thô; **quyết định game (chạm gì, khi nào) ở lại module/agent**. `Unknown ≠ NotDetected`: `Unknown` = chưa đủ bằng chứng (mẫu thiếu, frame lạ), `NotDetected` = đã tìm đủ và vắng mặt. Điểm thô không bao giờ ghi thành xác suất; chỉ `calibration` mới sinh `confidence`.

Provider ứng viên (chọn theo benchmark, không làm hết): template hiện tại (giữ làm baseline), template đa tỉ lệ + mask, ORB/AKAZE (cho vật thể nhiều kết cấu), ảnh tương đồng/embedding (cho phân loại màn, nối kNN sẵn có). Object detection chỉ xét nếu các cách trên không đạt gate cho lớp hoạt ảnh.

## 4. Chiến lược di trú (không phá hủy)
1. **Adapter tương thích**: `bot/vision.py` giữ API `find/best/find_all/has`; nội bộ ủy quyền cho service mới sau cờ `perception.mode` (`legacy` mặc định). Do luật D7, `bot` chỉ được import `aowbot.domain` → cần quyết định ở §9-Q2.
2. **Shadow mode**: `mode=shadow`: legacy vẫn quyết định; engine mới chạy song song, ghi cặp (cũ, mới, lệch) vào bảng `perception_shadow` (memory.db) + ảnh diagnostics. Không bao giờ chạm theo kết quả mới.
3. **Di trú theo lớp**: bật `mode=new` cho từng lớp (danh sách trắng) khi đạt gate; ưu tiên nút an toàn (đóng/quay lại) → nút nhận thưởng → còn lại. Lớp có hành động không đảo ngược (khiên/kim cương/xây/mua) **chỉ** chuyển cuối cùng và cần `Confirmed` + chặn OCR hiện có.
4. **Rollback**: một cờ cấu hình + `settings.json`; legacy vẫn nguyên vẹn đến hết giai đoạn, xóa ở phase riêng sau khi chủ dự án duyệt.
5. Hành động không đảo ngược không bao giờ chạy trên `Uncertain/Unknown/InvalidFrame`.

## 5. Dataset & benchmark (Phase 1)
- Vị trí: `data/perception/` (gitignore, giống `tests/fixtures`) + `manifest.json` có băm SHA-256 và phiên bản đưa vào git. Mỗi ảnh: `capture_session`, `instance`, `game_build`, `ui_state`, chụp lúc nào.
- Nhãn (JSON/COCO-like): lớp, bbox, `visible/occluded/animated`, `present=false` cho negative. Công cụ gắn nhãn tận dụng `tools/snap.py` + chạm của người (`logs/human`, 2057 bộ) để gợi ý bbox; **nhãn do người xác nhận** (nhãn gợi ý từ template hiện tại chỉ là bootstrap, đánh dấu `src=bootstrap`, không được dùng làm tập test để tránh đo mình bằng chính mình).
- Chia train/val/test **theo phiên chụp/instance**, không theo ảnh; bắt buộc có negative và hard-negative (màn gần giống).
- Số đo: confusion matrix, P/R/F1 theo lớp, FPR, abstention rate, latency p50/p95, CPU/RAM; so sánh legacy vs mới trên cùng split; báo cáo kèm commit + phiên bản dataset để tái lập.
- Không công bố "cải thiện độ chính xác" nếu không có báo cáo benchmark.

## 6. Kế hoạch file (đánh số theo thứ tự làm)
| Bước | File mới/đổi | Phụ thuộc |
|---|---|---|
| P1a | `src/aowbot/perception/eval/{dataset,metrics,compare}.py`, `tools/perception_label.py`, `tools/perception_bench.py`, schema `docs/perception/dataset-schema.md` | — |
| P1b | Dựng v0 dataset từ nguồn sẵn có + chạy legacy → `RECOGNITION_BASELINE.md` bản thật | P1a |
| P2a | `contract.py`, `config.py`, import-linter contract mới | P1b |
| P2b | `adapters/preprocess.py` (gộp tiền xử lý lặp), `frame_validation.py`, `regions.py` | P2a |
| P2c | `adapters/providers/template.py` (tái hiện đúng hành vi legacy, kiểm tương đương số học) | P2b |
| P3 | `calibration.py`, `fusion.py` + test thuần | P1b, P2a |
| P4 | provider mới được chọn theo benchmark | P2c, P3 |
| P5a | `coordinator.py`, `state.py`, `diagnostics.py`, adapter `bot/vision.py` sau cờ | P2c |
| P5b | shadow mode + bảng `perception_shadow` + trang/báo cáo so sánh (mở rộng `tools/report_ro.py`) | P5a |
| P5c | di trú theo lớp, rollback test | P5b + gate đạt |
| P6 | test hiệu năng, release gates, ADR | song song |
Không động vào: modules game, agent, runner (ngoài móc cờ), web.

## 7. Chiến lược kiểm thử
Unit thuần (contract, calibration, fusion: cực trị, bất đồng, abstain, Unknown≠NotDetected, điểm thô không thành xác suất); preprocessing có ảnh tổng hợp; provider test với ảnh tổng hợp + vài ảnh thật trong repo; **tương đương legacy**: provider template mới phải ra cùng `(x,y,score)` với `Vision.best` trên cùng ảnh; benchmark test (đánh dấu `fixtures`/`bench`, skip khi thiếu dữ liệu); hồi quy `check_screens`/`check_tutorial`; hiệu năng p50/p95 + CPU/RAM; import-linter; shadow-mode test (không có đường chạm).

## 8. Rủi ro
| Rủi ro | Giảm |
|---|---|
| Không có nhãn người → đo sai | P1b bắt buộc người duyệt tập test; đánh dấu bootstrap |
| Tập test nhỏ/thiên lệch (nhiều `city`) | stratify theo lớp, thu hard-negative, báo khoảng tin cậy |
| Dữ liệu không có trong git, khó tái lập | manifest + băm + lệnh dựng lại |
| Vi phạm luật lớp D7 | quyết định Q2 trước P2a |
| Chạy 2 luồng song song + 2 instance giới hạn CPU | đo CPU/RAM từ P1, provider nặng chỉ chạy khi cần |
| Hành động không đảo ngược bị kích bởi nhận diện sai | cổng `Confirmed` + chặn hiện có + shadow trước |
| Chạy trên máy thật (tối đa 2 instance, tài khoản khách) | chỉ dùng ảnh đã lưu cho benchmark; shadow dùng chính lượt chạy bình thường, không mở thêm máy |

## 9. Quyết định / câu hỏi cần chủ dự án duyệt
1. **Nguồn con số ~10 %**: lớp nào, máy/bản game nào, đo thế nào? (BASELINE cho 95,3 % chạm có tác dụng; chưa có FN.)
2. **Vị trí gói & luật import**: đề xuất `src/aowbot/perception/` + cho `bot/vision.py` import `aowbot.perception.api` (thêm ngoại lệ vào D7, ADR mới). Cách khác: để adapter trong `infrastructure/legacy` và tiêm vào `Ctx` từ `main.py`.
3. **Ai gắn nhãn**: chủ dự án duyệt tối thiểu bao nhiêu ảnh test (đề xuất ≥300 ảnh, ≥20 lớp ưu tiên, ≥30 % negative)?
4. Cho phép lưu dataset ngoài git ở `data/perception/` (≈ vài trăm MB)?
5. Xếp ưu tiên lớp: đề xuất bắt đầu từ nhóm `common/*` (đóng/quay lại, 1800+ chạm) và `identify`.

## 10. Tiêu chí chấp nhận & release gates (đặt sau P1b, theo số đo thật)
Cố định *dạng* gate ngay, *giá trị* điền sau khi có baseline: (a) với mỗi lớp được di trú: Precision ≥ legacy và Recall ≥ legacy trên test, FPR ≤ X; (b) lớp hành động không đảo ngược: Precision ≥ 0,99 trên test + 0 FP ở shadow ≥ N lượt; (c) p95 latency ≤ legacy × 1,5; (d) CPU/RAM trong ngân sách 2 instance song song; (e) toàn bộ test + import-linter xanh; (f) rollback diễn tập thành công. Không đạt → lớp ở lại legacy.

## 11. Thứ tự thực hiện
P1a → P1b → (dừng, báo cáo baseline thật, duyệt) → P2a→P2c → P3 → P4 (chọn theo benchmark) → P5a→P5b (shadow, duyệt) → P5c → P6. Mỗi mốc kết thúc bằng test xanh + báo cáo số đo; không sang phase sau khi chưa được duyệt.
