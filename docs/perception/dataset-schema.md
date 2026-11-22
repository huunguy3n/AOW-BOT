# Dataset nhận diện — schema v1

Ảnh nằm ngoài git: `data/perception/<phiên bản>/images/…` (đã gitignore cùng `data/`). Chỉ `manifest.json` (có băm SHA-256 từng ảnh) cần đưa vào git khi dataset ổn định. Mã: [dataset.py](../../src/aowbot/perception/eval/dataset.py).

```json
{ "schema": 1, "version": "v0", "classes": ["common/btn_close", "..."],
  "samples": [{
    "id": "i1-20261121-0001", "path": "images/i1/20261121/0001.png", "sha256": "…",
    "session": "i1-20261121-a", "instance": 1, "game_build": "vn-2.5.16",
    "ui_state": "popup", "split": "test", "source": "human", "complete": true,
    "annotations": [{"cls": "common/btn_close", "box": [x, y, w, h], "visible": true, "occlusion": 0.0, "animated": false}]
  }] }
```

Luật (kiểm bởi `validate()`):
- Split gán theo **phiên chụp** (`assign_splits`, băm xác định) — một phiên không được nằm ở 2 split.
- `source=bootstrap` (nhãn gợi ý từ nhận diện cũ) **không** được vào `test`; test chỉ nhận nhãn người xác nhận.
- `complete=true`: mọi lớp quan tâm đã gắn nhãn → lớp vắng mặt là **negative thật** (dùng tính FPR). `false` thì không dùng làm negative.
- `visible=false`: biết có nhưng bị che hoàn toàn → không tính false negative.
- Toạ độ theo hệ 540×960 (ADR-0003). `game_build` bắt buộc để tách VN 2.5.16 / Global 3.6.0.

Metrics ([metrics.py](../../src/aowbot/perception/eval/metrics.py)): khớp tham lam theo điểm giảm dần, cùng lớp, IoU ≥ 0,5; P/R/F1 theo lớp (`None` khi không xác định, không đổi thành 0); FPR = tỉ lệ ảnh negative bị báo; confusion nhãn × dự đoán kèm `<none>`; độ trễ p50/p95 nearest-rank; `compare(cũ, mới)` cho chênh lệch theo lớp.

## Gắn nhãn trong web
Tab **Nhận diện** (`#nhandien`, [web/perception_api.py](../../web/perception_api.py)): ô nào cũng là ảnh cắt quanh chỗ chạm tay → gõ tên lớp (Enter = lưu + sang ô kế; bấm ảnh = xem cả màn có vòng đỏ tại điểm chạm; "Không có" = chỗ đó không có vật thể), nhập bản game theo máy, rồi "Tạo v1" → `data/perception/v1/` (mẫu có nhãn người, chia theo phiên; test chỉ gồm mẫu đã gắn). Nhãn lưu ở `data/perception/v0/labels.json` (ghi atomic, tự lưu mỗi lần sửa). CLI tương đương: `python tools/perception_apply_labels.py`. Cần khởi động lại web (`run.bat`) để có tab mới.
